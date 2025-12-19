# Phase 4: Content Generation (LLM/TTS)

Automated radio break generation using AI services for weather, news, script writing, and voice synthesis.

## Overview

Phase 4 implements the complete content generation pipeline:

1. **Data Collection**: Fetch weather (NWS) and news headlines (RSS)
2. **Script Generation**: Create natural bulletin scripts using Claude LLM
3. **Voice Synthesis**: Convert scripts to audio using OpenAI TTS
4. **Audio Mixing**: Combine voice with background beds using ducking
5. **Broadcast Integration**: Save normalized breaks ready for Liquidsoap

## Architecture

```
┌─────────────┐
│   Weather   │ NWS API (LOT 76,73)
│   (NWS)     │ → 20°F, Mostly Sunny
└──────┬──────┘
       │
       ├──────────────┐
       │              │
┌──────▼──────┐  ┌───▼────────┐
│    News     │  │  Script    │
│   (RSS)     │  │ Generator  │ Claude Sonnet 4.5
│ NPR, Tribune│──▶│  (Claude)  │ → "Good morning..."
└─────────────┘  └──────┬─────┘
                        │
                  ┌─────▼─────┐
                  │   Voice   │
                  │ Synthesis │ OpenAI TTS-1
                  │  (OpenAI) │ → voice.mp3
                  └─────┬─────┘
                        │
                  ┌─────▼─────┐
                  │   Audio   │
                  │  Mixer    │ ffmpeg ducking
                  │  (ffmpeg) │ + loudness norm
                  └─────┬─────┘
                        │
                  ┌─────▼─────┐
                  │  Breaks   │
                  │ Directory │ → break_YYYYMMDD_HHMMSS.mp3
                  └───────────┘
```

## Components

### 1. Weather Data (`ai_radio/weather.py`)
- **Service**: National Weather Service (weather.gov)
- **Endpoint**: `/gridpoints/LOT/76,73/forecast`
- **Output**: Temperature, conditions, short forecast
- **Error Handling**: Returns None on failure, pipeline continues
- **Timeout**: 10 seconds

### 2. News Headlines (`ai_radio/news.py`)
- **Services**: NPR, Chicago Tribune RSS feeds
- **Processing**: Aggregation, deduplication (case-insensitive)
- **Limits**: 5 headlines per feed
- **Error Handling**: Graceful degradation, continues with available feeds
- **Timeout**: 10 seconds per feed

### 3. Script Generation (`ai_radio/script_writer.py`)
- **Service**: Anthropic Claude API
- **Model**: claude-3-5-sonnet-20241022 (configurable)
- **Style**: Conversational, 60-90 seconds (150-225 words)
- **Fallback**: Template-based script on API failure
- **Error Handling**: Never returns None, always provides usable script

### 4. Voice Synthesis (`ai_radio/voice_synth.py`)
- **Service**: OpenAI TTS API
- **Model**: tts-1 (standard quality)
- **Voice**: alloy (configurable: alloy, echo, fable, onyx, nova, shimmer)
- **Format**: MP3, 24kHz
- **Duration**: Estimated from word count (150 words/min)

### 5. Audio Mixing (`ai_radio/audio_mixer.py`)
- **Tool**: ffmpeg
- **Technique**: Sidechain compression (ducking)
- **Parameters**:
  - Bed volume: -18 dB (configurable)
  - Threshold: 0.02
  - Ratio: 3:1
  - Attack: 5ms
  - Release: 200ms
- **Normalization**: EBU R128 (-18 LUFS, -1.0 dBTP)
- **Output**: High-quality MP3 (libmp3lame q:a 2)

### 6. Break Generator (`ai_radio/break_generator.py`)
- **Role**: Pipeline orchestrator
- **Bed Selection**: Random from `assets/beds/*.mp3`
- **Output Naming**: `break_YYYYMMDD_HHMMSS.mp3`
- **Freshness**: 50 minutes (configurable)

## Configuration

Environment variables (`.env` file):

```ini
# Required for production
RADIO_LLM_API_KEY=sk-ant-...           # Anthropic API key
RADIO_TTS_API_KEY=sk-...                # OpenAI API key

# Optional overrides
RADIO_LLM_MODEL=claude-3-5-sonnet-20241022  # Claude model
RADIO_TTS_VOICE=alloy                        # OpenAI voice
RADIO_BED_VOLUME_DB=-18.0                    # Bed volume in dB
RADIO_BREAK_FRESHNESS_MINUTES=50             # Producer freshness

# Weather/News (defaults configured)
RADIO_NWS_OFFICE=LOT                         # NWS office code
RADIO_NWS_GRID_X=76                          # Grid X coordinate
RADIO_NWS_GRID_Y=73                          # Grid Y coordinate
```

## Deployment

### 1. Install Dependencies

```bash
cd /srv/ai_radio
uv pip install -e .
```

### 2. Configure API Keys

```bash
# Create .env file
cat > /srv/ai_radio/.env <<EOF
RADIO_LLM_API_KEY=your-anthropic-key
RADIO_TTS_API_KEY=your-openai-key
EOF

# Secure permissions
chmod 600 /srv/ai_radio/.env
chown radio:radio /srv/ai_radio/.env
```

### 3. Validate Configuration

```bash
# Test weather fetching
uv run python -c "from ai_radio.weather import get_weather; print(get_weather())"

# Test news fetching
uv run python -c "from ai_radio.news import get_news; print(get_news())"
```

### 4. Create Bed Files

```bash
# Add background music beds
cp *.mp3 /srv/ai_radio/assets/beds/

# Verify permissions
chown -R radio:radio /srv/ai_radio/assets/beds
chmod 644 /srv/ai_radio/assets/beds/*.mp3
```

### 5. Install Systemd Timer

```bash
# Copy unit files
sudo cp systemd/generate-break.* /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable generate-break.timer
sudo systemctl start generate-break.timer
```

### 6. Verify Operation

```bash
# Check timer status
systemctl status generate-break.timer

# Manual break generation
sudo systemctl start generate-break.service

# View logs
journalctl -u generate-break.service -f

# Check breaks directory
ls -lh /srv/ai_radio/assets/breaks/
```

## Testing

### Unit Tests

```bash
# Run all Phase 4 tests
uv run pytest tests/test_weather.py tests/test_news.py tests/test_script_writer.py tests/test_voice_synth.py tests/test_audio_mixer.py tests/test_break_generator.py -v

# With coverage
uv run pytest tests/ --cov=src/ai_radio --cov-report=term-missing
```

### Integration Testing

```bash
# Test full pipeline (requires API keys)
uv run python scripts/generate_break.py

# Expected output:
# - Weather fetched: XX°F, Conditions
# - News aggregated: N headlines from M feeds
# - Script generated: XXX words
# - Voice synthesized: XX.Xs
# - Break saved: break_YYYYMMDD_HHMMSS.mp3
```

### Manual API Testing

```bash
# Test Claude API
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $RADIO_LLM_API_KEY" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":100,"messages":[{"role":"user","content":"Test"}]}'

# Test OpenAI TTS
curl https://api.openai.com/v1/audio/speech \
  -H "Authorization: Bearer $RADIO_TTS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","input":"Test","voice":"alloy"}' \
  --output test.mp3
```

## Troubleshooting

### Weather Fetch Fails

**Symptoms**: "Failed to fetch NWS forecast"

**Causes**:
- Network connectivity to weather.gov
- Invalid NWS office/grid coordinates
- Rate limiting (unlikely with 50min intervals)

**Solutions**:
```bash
# Test NWS API directly
curl "https://api.weather.gov/gridpoints/LOT/76,73/forecast"

# Verify config
python -c "from ai_radio.config import config; print(config.nws_office, config.nws_grid_x, config.nws_grid_y)"

# Check logs
journalctl -u generate-break.service | grep "NWS"
```

### News Fetch Fails

**Symptoms**: "No headlines fetched from any RSS feed"

**Causes**:
- Network connectivity
- RSS feed format changes
- Timeout (slow feeds)

**Solutions**:
```bash
# Test RSS feeds
curl -L "https://feeds.npr.org/1001/rss.xml"
curl -L "https://www.chicagotribune.com/arcio/rss/"

# Check logs
journalctl -u generate-break.service | grep "RSS"
```

### Script Generation Fails

**Symptoms**: "Failed to generate bulletin script"

**Causes**:
- Invalid API key
- Rate limiting
- Model not available
- Network issues

**Solutions**:
```bash
# Verify API key
echo $RADIO_LLM_API_KEY | cut -c1-10

# Test API directly
python -c "from anthropic import Anthropic; print(Anthropic(api_key='$RADIO_LLM_API_KEY').messages.create(model='claude-3-5-sonnet-20241022', max_tokens=10, messages=[{'role':'user','content':'Hi'}]))"

# Check for fallback usage
journalctl -u generate-break.service | grep "fallback"
```

### Voice Synthesis Fails

**Symptoms**: "Failed to synthesize voice"

**Causes**:
- Invalid API key
- Rate limiting
- Disk space

**Solutions**:
```bash
# Verify API key
echo $RADIO_TTS_API_KEY | cut -c1-10

# Check disk space
df -h /srv/ai_radio/tmp

# Test API
curl https://api.openai.com/v1/audio/speech \
  -H "Authorization: Bearer $RADIO_TTS_API_KEY" \
  -d '{"model":"tts-1","input":"test","voice":"alloy"}' \
  --output /tmp/test.mp3
```

### Audio Mixing Fails

**Symptoms**: "Failed to mix audio"

**Causes**:
- ffmpeg not installed
- No bed files available
- Disk space
- Invalid audio files

**Solutions**:
```bash
# Check ffmpeg
which ffmpeg
ffmpeg -version

# Check bed files
ls -lh /srv/ai_radio/assets/beds/*.mp3

# Check disk space
df -h /srv/ai_radio/assets/breaks

# Test ffmpeg directly
ffmpeg -i voice.mp3 -i bed.mp3 -filter_complex "[1:a][0:a]sidechaincompress[out]" -map "[out]" test.mp3
```

### Breaks Not Appearing in Liquidsoap

**Symptoms**: Breaks generated but not played

**Causes**:
- Liquidsoap not monitoring breaks directory
- File permissions
- Naming pattern mismatch

**Solutions**:
```bash
# Check break files
ls -lh /srv/ai_radio/assets/breaks/

# Check permissions
ls -la /srv/ai_radio/assets/breaks/ | grep "^-"

# Verify Liquidsoap config
grep "breaks" /srv/ai_radio/config/radio.liq

# Check Liquidsoap logs
journalctl -u liquidsoap-radio.service | grep "break"
```

## Performance

### Typical Generation Times

- Weather fetch: 100-300ms
- News fetch: 500-2000ms (2 feeds)
- Script generation: 1-3 seconds
- Voice synthesis: 2-5 seconds
- Audio mixing: 1-2 seconds
- **Total: 5-15 seconds**

### Resource Usage

- Memory: 200-400 MB peak
- CPU: 20-50% during generation
- Disk: ~500KB per break (MP3 @ 128kbps)
- Network: ~2MB per generation (API calls)

### Scaling

- **Break frequency**: 50 minutes (configurable)
- **Daily breaks**: ~30 breaks/day
- **Monthly storage**: ~15 MB/month
- **API costs**:
  - Claude: ~$0.02 per break
  - OpenAI TTS: ~$0.015 per break
  - **Total: ~$1/day**

## Maintenance

### Log Rotation

```bash
# Configure journald
cat > /etc/systemd/journald.conf.d/generate-break.conf <<EOF
[Journal]
SystemMaxUse=100M
SystemKeepFree=500M
MaxRetentionSec=7day
EOF

sudo systemctl restart systemd-journald
```

### Break Archival

```bash
# Archive breaks older than 7 days
find /srv/ai_radio/assets/breaks/ -name "break_*.mp3" -mtime +7 -exec mv {} /srv/ai_radio/assets/breaks/archive/ \;

# Add to cron (daily at 3am)
echo "0 3 * * * find /srv/ai_radio/assets/breaks/ -name 'break_*.mp3' -mtime +7 -exec mv {} /srv/ai_radio/assets/breaks/archive/ \;" | crontab -
```

### Monitoring

```bash
# Break generation success rate
journalctl -u generate-break.service --since "24 hours ago" | grep -c "Break generated successfully"

# Average generation time
journalctl -u generate-break.service --since "24 hours ago" | grep "Break generated" | # parse duration

# API errors
journalctl -u generate-break.service --since "24 hours ago" | grep -i "error"
```

## Future Enhancements

- Content freshness checking (avoid duplicate weather/news)
- Break template variations (multiple personalities)
- Time-of-day customization (morning vs evening tone)
- Multi-voice support (dialogue format)
- Music genre-aware bed selection
- Weather alerts integration
- Local events calendar integration
- Ad insertion points
- Analytics and A/B testing
