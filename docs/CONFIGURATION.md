# Configuration Guide

**Purpose:** Complete reference for all 100+ environment variables that control your station's personality

**Time estimate:** 45-60 minutes (to understand and customize)

---

## Overview

AI Radio Station is **configuration-driven**. Almost everything about your station's personality, content, and behavior is controlled through environment variables in a `.env` file.

This guide organizes all configuration options by purpose, explains what they do, how they work together, and why they exist.

**Configuration philosophy:**
- Defaults are generic and safe (tropical island theme)
- Every setting has a purpose - no arbitrary knobs
- Settings work together to create coherent personality
- You can go deep on customization (see LAST BYTE RADIO for inspiration)

---

## Quick Start

```bash
# Copy the example config
cd /srv/ai_radio
cp .env.example .env

# Edit with your settings
nano .env
```

**Minimum required changes:**
1. API keys (Claude, Gemini)
2. Station coordinates (for weather)
3. Station name and location

Everything else has sensible defaults, but customizing personality settings is where the magic happens.

---

## Base Configuration

### Core Settings

```bash
# Installation directory
RADIO_BASE_PATH=/srv/ai_radio

# Timezone (IANA format)
RADIO_STATION_TZ=America/Chicago
```

**RADIO_BASE_PATH:**
- Where the radio station code lives
- All file paths are relative to this
- Default: `/srv/ai_radio`

**RADIO_STATION_TZ:**
- Affects break scheduling, timestamps, "current time" references
- Use IANA format: `America/Chicago`, `Europe/London`, `Asia/Tokyo`
- Find yours: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

---

## Station Identity

These settings define your station's public-facing identity:

```bash
RADIO_STATION_NAME="WKRP Coconut Island"
RADIO_STATION_LOCATION="Coconut Island"
```

**RADIO_STATION_NAME:**
- Your station's call sign or brand name
- Appears in stream metadata, station IDs, Icecast
- Examples: "WKRP Coconut Island", "LAST BYTE RADIO", "KOOL 108 FM"

**RADIO_STATION_LOCATION:**
- Where your station "broadcasts from"
- Used in weather context, news framing
- Can be real or fictional

---

## Location for Weather

```bash
RADIO_STATION_LAT=21.3099
RADIO_STATION_LON=-157.8581
```

**Required for weather data** from National Weather Service.

**How to find your coordinates:**
1. Go to https://www.latlong.net/
2. Enter your location
3. Copy decimal lat/lon values

**National Weather Service Grid** (US only):
```bash
RADIO_NWS_OFFICE=HNL        # Your local NWS office code
RADIO_NWS_GRID_X=67         # Grid X coordinate
RADIO_NWS_GRID_Y=51         # Grid Y coordinate
```

**How to find your NWS grid:**
1. Go to https://www.weather.gov/
2. Enter your location
3. Look at the URL - it contains the office code
4. The grid coordinates are in the API endpoint (check browser dev tools)

**Not in the US?** You'll need to modify the weather fetcher to use a different weather API. NWS is US-only.

---

## API Keys

### Claude (LLM for script generation)

```bash
RADIO_LLM_API_KEY=sk-ant-api03-...
RADIO_LLM_MODEL=claude-sonnet-4-5
```

**RADIO_LLM_API_KEY:**
- Get from https://console.anthropic.com/
- Used for generating news/weather scripts
- **Cost:** ~$0.10-0.50 per break depending on model and temperature

**RADIO_LLM_MODEL:**
- Which Claude model to use
- Options: `claude-sonnet-4-5`, `claude-opus-4`, `claude-haiku-3-5`
- Trade-off: Better models = more creative, but more expensive
- Recommended: `claude-sonnet-4-5` (best balance)

### Gemini (TTS for voice synthesis)

```bash
RADIO_TTS_PROVIDER=gemini
RADIO_GEMINI_API_KEY=AIza...
RADIO_GEMINI_TTS_MODEL=gemini-2.5-pro-preview-tts
RADIO_GEMINI_TTS_VOICE=Kore
```

**RADIO_TTS_PROVIDER:**
- Which TTS service to use
- Options: `gemini` (recommended) or `openai`
- Gemini has better voice quality and lower cost

**RADIO_GEMINI_API_KEY:**
- Get from https://ai.google.dev/
- Used for text-to-speech
- **Cost:** Very low, ~$0.01-0.05 per break

**RADIO_GEMINI_TTS_MODEL:**
- Flash (faster, cheaper) or Pro (better quality)
- Recommended: `gemini-2.5-pro-preview-tts`

**RADIO_GEMINI_TTS_VOICE:**
- Voice persona
- Options: `Kore` (firm), `Puck` (upbeat), `Aoede` (breezy), `Enceladus` (tired), `Umbriel` (relaxed)
- Test different voices to find your station's sound
- See: `scripts/test_gemini_voices.py` (if available in your version)

### Script Generation Temperature

```bash
RADIO_WEATHER_SCRIPT_TEMPERATURE=0.8
RADIO_NEWS_SCRIPT_TEMPERATURE=0.6
```

**What is temperature?**
- Controls LLM creativity/randomness
- 0.0 = deterministic, repetitive
- 1.0 = highly creative, unpredictable
- Sweet spot: 0.6-0.8

**RADIO_WEATHER_SCRIPT_TEMPERATURE:**
- Higher = more creative weather descriptions
- Lower = more consistent, predictable
- Recommended: 0.7-0.9 (weather can be playful)

**RADIO_NEWS_SCRIPT_TEMPERATURE:**
- Higher = more editorializing, creative framing
- Lower = straighter delivery
- Recommended: 0.5-0.7 (news should be grounded)

---

## News Configuration

```bash
RADIO_NEWS_RSS_FEEDS='{"local": ["..."], "national": ["..."], "tech": ["..."]}'
```

**Format:** JSON object with categories as keys, RSS feed URLs as values

**Example:**
```json
{
  "local": [
    "https://local-news-site.com/feed/"
  ],
  "national": [
    "https://feeds.npr.org/1001/rss.xml",
    "https://www.theguardian.com/us-news/rss"
  ],
  "tech": [
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://news.ycombinator.com/rss"
  ]
}
```

**Tips:**
- Categorize feeds by topic (helps the AI frame stories)
- Mix local + national + niche interests
- Quality over quantity (3-5 feeds per category)
- Check that RSS feeds are active and valid

### Hallucinated News

```bash
RADIO_HALLUCINATE_NEWS=true
RADIO_HALLUCINATION_CHANCE=1.0
RADIO_HALLUCINATION_KERNELS='["Megacorp merger", "Power outage", ...]'
```

**RADIO_HALLUCINATE_NEWS:**
- Mix AI-generated fake news with real headlines
- Creates world-building opportunities
- Set `false` for purely real news

**RADIO_HALLUCINATION_CHANCE:**
- Probability (0.0-1.0) of including a fake story
- 1.0 = always include fake story in each break
- 0.5 = 50% chance
- Recommended: 0.3-1.0 depending on your vibe

**RADIO_HALLUCINATION_KERNELS:**
- JSON array of seed topics for fake news
- The AI expands these into full stories
- Customize to your station's world-building

**Example kernels (cyberpunk dystopia):**
```json
[
  "Megacorp merger affects infrastructure",
  "Underground mesh network activity",
  "Corporate security forces deployed",
  "Rogue AI incident at data center",
  "Black market supply shortage"
]
```

**Example kernels (tropical paradise):**
```json
[
  "Perfect weather streak continues",
  "Record coconut harvest",
  "Beach cleanup volunteer success",
  "Surf conditions ideal",
  "Sunset rated 'spectacular'"
]
```

---

## Audio Settings

```bash
RADIO_BED_VOLUME_DB=-18.0
RADIO_BED_PREROLL_SECONDS=3.0
RADIO_BED_FADEIN_SECONDS=2.0
RADIO_BED_POSTROLL_SECONDS=5.4
RADIO_BED_FADEOUT_SECONDS=3.0
RADIO_BREAK_FRESHNESS_MINUTES=50
```

**What are "beds"?** Background music that plays under the DJ's voice during breaks.

**RADIO_BED_VOLUME_DB:**
- Volume of background music (negative dB)
- -18.0 = clearly audible but not overpowering
- More negative = quieter (-24.0 = subtle, -12.0 = loud)

**RADIO_BED_PREROLL_SECONDS:**
- Music starts this many seconds *before* voice
- Creates anticipation, professional "ride in"
- Recommended: 2-4 seconds

**RADIO_BED_FADEIN_SECONDS:**
- How long the bed takes to fade in
- Recommended: 1-3 seconds

**RADIO_BED_POSTROLL_SECONDS:**
- Music continues this many seconds *after* voice ends
- Professional "ride out"
- Recommended: 4-6 seconds

**RADIO_BED_FADEOUT_SECONDS:**
- How long the bed takes to fade out
- Recommended: 2-4 seconds

**RADIO_BREAK_FRESHNESS_MINUTES:**
- How long before a break can be replayed
- Prevents repetition if generation fails
- Recommended: 45-60 minutes

---

## Streaming Configuration

The station broadcasts in three quality levels simultaneously, allowing listeners to choose based on their bandwidth:

### Stream Endpoints

| Endpoint | Bitrate | Sample Rate | Use Case |
|----------|---------|-------------|----------|
| `/radio` | 192 kbps | 48000 Hz | High quality (default for direct listeners) |
| `/radio-128` | 128 kbps | 44100 Hz | Balanced quality/bandwidth (website default) |
| `/radio-96` | 96 kbps | 44100 Hz | Low bandwidth (mobile/slow connections) |

**All streams:**
- MP3 format (stereo)
- Same synchronized content (single Liquidsoap source)
- Same programming schedule
- Play at exactly the same time

### Icecast Configuration

Multi-bitrate streaming requires increasing Icecast's source limit:

```xml
<!-- /etc/icecast2/icecast.xml -->
<limits>
    <sources>5</sources>  <!-- Allow multiple bitrate streams -->
    <!-- other limits... -->
</limits>
```

After changing, restart Icecast: `sudo systemctl restart icecast2`

### Nginx Configuration

Each stream should be optimized for long-duration audio:

```nginx
location /radio-128 {
    proxy_buffering off;           # No delays
    proxy_request_buffering off;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_set_header Accept-Encoding "";  # No compression of MP3
    proxy_read_timeout 3600s;      # 1 hour timeout
    send_timeout 3600s;
    proxy_cache off;
    proxy_pass http://icecast_server;
    add_header Access-Control-Allow-Origin *;
    add_header Cache-Control "no-cache, no-store";
}
```

### Liquidsoap Configuration

Streams are defined in `config/radio.liq` using multiple `output.icecast()` blocks:

```liquidsoap
# High quality (192 kbps)
output.icecast(
  %mp3(bitrate=192, samplerate=48000, stereo=true),
  mount="/radio",
  name="#{station_name}",
  radio
)

# Medium quality (128 kbps) - Recommended default
output.icecast(
  %mp3(bitrate=128, samplerate=44100, stereo=true),
  mount="/radio-128",
  name="#{station_name} (128kbps)",
  radio
)

# Low bandwidth (96 kbps)
output.icecast(
  %mp3(bitrate=96, samplerate=44100, stereo=true),
  mount="/radio-96",
  name="#{station_name} (96kbps)",
  radio
)
```

### Website Quality Selector

The web interface (`nginx/index.html`) defaults to 128 kbps and includes a dropdown selector for quality switching. When users change quality, the player:

1. Preserves playback state (playing/muted)
2. Switches to new stream endpoint
3. Resumes from live broadcast point

No additional configuration needed - quality selector is built into the website.

---

## World-Building

This is where your station's personality really comes alive. These settings control the universe your station exists in and how content is filtered through that lens.

```bash
RADIO_WORLD_SETTING="laid-back tropical island paradise"
RADIO_WORLD_TONE="relaxed, friendly, warm, good vibes only, island time"
RADIO_WORLD_FRAMING="Broadcasting from our little slice of paradise. The news and weather filtered through the lens of island living - warm sun, cool breezes, and the sound of waves. We keep it real but keep it chill."
```

**RADIO_WORLD_SETTING:**
- The universe/setting your station exists in
- Examples:
  - "laid-back tropical island paradise"
  - "post-capitalist dystopian cyber future"
  - "1980s college radio station"
  - "underground resistance broadcast"
  - "cozy coffee shop vibes"

**RADIO_WORLD_TONE:**
- Emotional vibe of your station
- Keywords that define the feeling
- Examples:
  - Tropical: "relaxed, friendly, warm, good vibes only"
  - Cyberpunk: "bleak but resilient, dark humor, defiant"
  - College: "enthusiastic, nerdy, inclusive, DIY energy"

**RADIO_WORLD_FRAMING:**
- The meta-narrative of your station
- How you explain your existence to listeners
- How you filter current events through your world
- This is the "voice of god" instruction to the AI

**Deep dive: Creating coherent worlds**

Your world-building settings should reinforce each other:

- **Tropical paradise station:**
  - Setting: Beach paradise
  - Tone: Relaxed, warm, positive
  - Framing: "Broadcasting from paradise, keeping it chill"
  - News framing: Local beach events, weather as gift, tech news with beach metaphors

- **Cyberpunk dystopia station:**
  - Setting: Post-capitalist collapse, neon wasteland
  - Tone: Bleak but resilient, dark humor, we're all in this together
  - Framing: "Broadcasting from the ruins, still here, still coding"
  - News framing: Megacorp failures, infrastructure collapse, small resistance victories

The AI uses these settings to consistently frame ALL content (news, weather, time checks) through your world's lens.

---

## Announcer Personality

Control your DJ's personality with precision:

```bash
RADIO_ANNOUNCER_NAME="DJ Coco"
RADIO_ENERGY_LEVEL=5
RADIO_VIBE_KEYWORDS="laid-back, friendly, warm, easygoing, tropical"
```

**RADIO_ANNOUNCER_NAME:**
- Your DJ's persona name
- Used in promos, self-references
- Can be a call sign, nickname, or description
- Examples: "DJ Coco", "The Last Byte Host", "Your Beach Buddy"

**RADIO_ENERGY_LEVEL (1-10):**
- 1-3: Chill, ASMR vibes, late night
- 4-6: Conversational, friendly, approachable
- 7-9: Enthusiastic, upbeat, morning show energy
- 10: EXTREME (usually too much)
- Recommended: 5-7 for most stations

**RADIO_VIBE_KEYWORDS:**
- 3-5 keywords defining personality
- The AI uses these to maintain consistent voice
- Be specific: "witty" not just "funny", "sardonic" not just "sarcastic"

### Chaos Budget

```bash
RADIO_MAX_RIFFS_PER_BREAK=1
RADIO_MAX_EXCLAMATIONS_PER_BREAK=2
RADIO_UNHINGED_PERCENTAGE=20
```

**Why limit chaos?** AI can get carried away. These settings keep personality fun without becoming exhausting.

**RADIO_MAX_RIFFS_PER_BREAK:**
- Maximum playful tangents per segment
- 0 = straight delivery
- 1-2 = occasional personality (recommended)
- 3+ = very chatty

**RADIO_MAX_EXCLAMATIONS_PER_BREAK:**
- Limits "Wow!" "Amazing!" type reactions
- 1-2 = expressive but not overdone
- 3+ = overly enthusiastic

**RADIO_UNHINGED_PERCENTAGE (0-100):**
- What % of a segment can be "off the rails"
- 0% = strictly on-topic
- 20% = occasional wild cards (recommended)
- 50%+ = unpredictable, experimental

---

## Humor & Style Guardrails

Prevent AI cringe and maintain authenticity:

```bash
RADIO_HUMOR_PRIORITY="observational > analogy > wordplay > weather-roast > character-voice"
RADIO_ALLOWED_COMEDY="relatable complaints, tech metaphors (light), quick punchlines, playful hyperbole"
RADIO_BANNED_COMEDY="meme recitation (POV/tell-me-you), dated slang, 'fellow kids' energy, extended sketches >10sec, self-congratulation"
RADIO_UNHINGED_TRIGGERS="hurricanes, tsunami warnings, volcanic activity, coconut shortages, extreme surf conditions, tourist invasions"
```

**RADIO_HUMOR_PRIORITY:**
- Ranked list of preferred humor types
- AI tries left-to-right first
- Prevents falling into lowest-common-denominator jokes

**RADIO_ALLOWED_COMEDY:**
- Specific comedy devices that work
- Based on testing and user feedback
- Examples from your station's vibe

**RADIO_BANNED_COMEDY:**
- Comedy devices that sound AI-generated or cringe
- Common AI failure modes
- Add to this list as you discover new failure modes

**Deep dive: Why these guardrails exist**

AI tends toward:
- Meme recitation ("POV: you're...", "Tell me you... without telling me...")
- Dated slang ("yeet", "slay", etc.)
- "Fellow kids" energy (trying too hard to be relatable)
- Extended sketches (loses pacing)
- Self-congratulation ("I'm so random!")

These guardrails evolved from extensive testing. Your mileage may vary - customize based on what sounds authentic for YOUR station.

**RADIO_UNHINGED_TRIGGERS:**
- Specific events that justify going wild
- Makes chaos feel reactive, not random
- Customize to your world (coconut shortages for tropical, megacorp buyouts for cyberpunk)

---

## Anti-Robot Authenticity Rules

Make AI sound human:

```bash
RADIO_SENTENCE_LENGTH_TARGET="6-14 words average, vary rhythm"
RADIO_MAX_ADJECTIVES_PER_SENTENCE=2
RADIO_NATURAL_DISFLUENCY="0-1 per break (e.g., 'okay—so...', 'wait, my sensor just refreshed')"
RADIO_BANNED_AI_PHRASES="'as an AI', 'according to my data', 'in today's world', 'stay tuned for more', ..."
```

**RADIO_SENTENCE_LENGTH_TARGET:**
- Prevents AI's tendency toward long, complex sentences
- Natural speech: short, punchy, varied
- Format: guideline string for the AI

**RADIO_MAX_ADJECTIVES_PER_SENTENCE:**
- Prevents purple prose
- "The beautiful, gorgeous, stunning sunset" → "The stunning sunset"
- 1-2 adjectives = punchy and clear

**RADIO_NATURAL_DISFLUENCY:**
- Conversational fillers and self-corrections
- Makes speech sound spontaneous
- 0-1 per break = subtle authenticity
- Examples: "okay—so...", "wait, let me check...", "uh, right..."

**RADIO_BANNED_AI_PHRASES:**
- Phrases that scream "I'm an AI!"
- Telltale patterns Claude tends toward
- Add new ones as you discover them
- **Long list provided in .env.example**

**Common AI tells:**
- "As an AI..." (self-referential)
- "In today's world..." (generic framing)
- "Stay tuned for more..." (template radio)
- "It seems..." (hedging)
- Overuse of "cutting through you", "stabbing cold" (melodramatic weather)

---

## Weather Style

Control how weather is delivered:

```bash
RADIO_WEATHER_STRUCTURE="Give the current conditions and forecast in 20-30 seconds. Vary your approach - sometimes lead with temperature, sometimes with conditions, sometimes with a consequence. Not every weather report needs advice or a joke. Just tell people what it's like outside in a way that feels natural to the moment."

RADIO_WEATHER_TRANSLATION_RULES="Translate weather through the dystopian lens but keep it conversational. When relevant, mention specific impacts (servers overheating, satellites going wonky, cyberdecks freezing, batteries draining, fog on displays). But don't force it - sometimes just saying the conditions is enough. Vary structure: lead with temp, or conditions, or impact, or forecast. Mix it up."
```

**RADIO_WEATHER_STRUCTURE:**
- High-level guidance on weather format
- Target length (20-30 seconds is professional)
- Variation instructions (prevents template feel)
- Permission to be straightforward (not every report needs a joke)

**RADIO_WEATHER_TRANSLATION_RULES:**
- How to filter weather through your world
- Specific impacts relevant to your setting
- Examples:
  - Tropical: beach conditions, outdoor plans, boat weather
  - Cyberpunk: electronics effects, infrastructure impacts, dystopian framing
  - College: study spot weather, campus event impacts

**Key principle: VARY THE APPROACH**

Don't force a template. Sometimes:
- Lead with temperature: "67 degrees and cloudy"
- Lead with conditions: "Rain moving in this afternoon"
- Lead with consequence: "Grab a jacket, it's cold out there"
- Lead with forecast: "Weather changes coming tomorrow"

---

## News Style

Control how news is delivered and when to get serious:

```bash
RADIO_NEWS_TONE="Normal: laid-back, friendly, conversational. Serious mode: respectful, minimal jokes, no snark. Trigger serious mode for: deaths, disasters, violence, accidents. Keep it real and relatable."

RADIO_NEWS_FORMAT="Cover the provided headlines (typically 3-4 stories). Keep it natural and conversational. Vary how you treat each story - some get one sentence, some get two, some get a casual observation. Mix it up naturally. Skip stories if redundant or low-value. Ethical boundaries: no joking about victims, no punching down, no conspiracy framing, no unsourced hot takes."
```

**RADIO_NEWS_TONE:**
- Normal mode: Your station's usual personality
- Serious mode: Respectful coverage of tragedy
- Clear triggers for serious mode (deaths, disasters, violence)

**Why serious mode matters:** Joking about tragedies destroys credibility. The AI needs explicit permission to drop the persona when appropriate.

**RADIO_NEWS_FORMAT:**
- Story selection (3-4 headlines typical)
- Treatment variation (not every story gets same length)
- Permission to skip redundant/low-value stories
- Ethical guardrails

**Ethical boundaries explained:**

- **No joking about victims:** Self-explanatory
- **No punching down:** Jokes at expense of vulnerable groups
- **No conspiracy framing:** Stick to reported facts
- **No unsourced hot takes:** Frame news, don't editorialize without basis

These guardrails maintain credibility while allowing personality.

---

## Vocal/Accent Characteristics

Control TTS voice characteristics:

```bash
RADIO_ACCENT_STYLE="Light transatlantic or coastal US/Canadian - subtle, globally legible. Internet-native 'streamer' sound. Mid-20s to mid-30s vibe. Crisp enunciation with subtle tech slang fluency. NOT cartoonish accents or heavy caricature"

RADIO_DELIVERY_STYLE="Medium-fast with purposeful pauses, crisp consonants, smile in voice, varied pacing with micro-pauses, occasional self-referential asides ('okay, nerd alert, but...')"
```

**RADIO_ACCENT_STYLE:**
- Recommended accent/vocal quality
- Passed to TTS system as guidance
- Results may vary by TTS provider

**RADIO_DELIVERY_STYLE:**
- Pacing, rhythm, energy
- Micro-elements that create personality
- TTS systems interpret these differently

**Note:** These are guidance, not guarantees. TTS systems have limitations. Gemini TTS does a reasonable job interpreting these, but you're not going to get perfect regional accents or dramatic character voices.

---

## Radio Fundamentals

Professional radio best practices:

```bash
RADIO_RADIO_RESETS="Station ID at start and end of each break (required). Time reference somewhere in the break (required for listener orientation). HOW you work these in is up to you - be natural, don't force a template."

RADIO_LISTENER_RELATIONSHIP="Talking to neighbors and friends, not a crowd. 'We're all here living the island life together' not 'performing at you'. Casual, warm, like chatting at the beach."
```

**RADIO_RADIO_RESETS:**
- FCC requirement: Station ID every hour (US law)
- Best practice: ID at start and end of breaks
- Time reference: Listeners need to know when it is
- Natural delivery: Don't template it ("You're listening to...")

**RADIO_LISTENER_RELATIONSHIP:**
- Tone with audience
- Intimacy level
- Examples:
  - Tropical: "Neighbors and friends, chatting at the beach"
  - Cyberpunk: "Fellow survivors, we're in this together"
  - College: "Your fellow students, we get it"

---

## Liquidsoap Environment Variables

Separate from RADIO_* variables - these go directly to Liquidsoap:

```bash
LIQUIDSOAP_STATION_NAME="WKRP Coconut Island"
LIQUIDSOAP_STATION_DESCRIPTION="Broadcasting from the beach"
LIQUIDSOAP_STATION_URL="https://radio.yourdomain.com"
```

**These appear in:**
- Icecast stream metadata
- Stream players (shows current station info)
- Public stream directories (if listed)

**Note:** These can differ from RADIO_STATION_NAME if you want internal vs external branding to differ, but usually they should match.

---

## Example Configuration

Here's a complete minimal `.env` for a tropical island station:

```bash
# Base
RADIO_BASE_PATH=/srv/ai_radio
RADIO_STATION_TZ=Pacific/Honolulu

# Identity
RADIO_STATION_NAME="WKRP Coconut Island"
RADIO_STATION_LOCATION="Coconut Island"

# Weather location (Honolulu)
RADIO_STATION_LAT=21.3099
RADIO_STATION_LON=-157.8581
RADIO_NWS_OFFICE=HNL
RADIO_NWS_GRID_X=67
RADIO_NWS_GRID_Y=51

# API Keys (replace with yours!)
RADIO_LLM_API_KEY=sk-ant-api03-...
RADIO_LLM_MODEL=claude-sonnet-4-5
RADIO_WEATHER_SCRIPT_TEMPERATURE=0.8
RADIO_NEWS_SCRIPT_TEMPERATURE=0.6

RADIO_TTS_PROVIDER=gemini
RADIO_GEMINI_API_KEY=AIza...
RADIO_GEMINI_TTS_MODEL=gemini-2.5-pro-preview-tts
RADIO_GEMINI_TTS_VOICE=Puck

# News
RADIO_NEWS_RSS_FEEDS='{"local": ["https://www.hawaiinewsnow.com/rss/"], "national": ["https://feeds.npr.org/1001/rss.xml"]}'
RADIO_HALLUCINATE_NEWS=false

# Audio
RADIO_BED_VOLUME_DB=-18.0
RADIO_BED_PREROLL_SECONDS=3.0
RADIO_BED_FADEIN_SECONDS=2.0
RADIO_BED_POSTROLL_SECONDS=5.4
RADIO_BED_FADEOUT_SECONDS=3.0
RADIO_BREAK_FRESHNESS_MINUTES=50

# World-building
RADIO_WORLD_SETTING="laid-back tropical island paradise"
RADIO_WORLD_TONE="relaxed, friendly, warm, good vibes only, island time"
RADIO_WORLD_FRAMING="Broadcasting from our little slice of paradise."

# Personality
RADIO_ANNOUNCER_NAME="DJ Coco"
RADIO_ENERGY_LEVEL=5
RADIO_VIBE_KEYWORDS="laid-back, friendly, warm, easygoing, tropical"
RADIO_MAX_RIFFS_PER_BREAK=1
RADIO_MAX_EXCLAMATIONS_PER_BREAK=2
RADIO_UNHINGED_PERCENTAGE=20

# Humor (use defaults from .env.example)
RADIO_HUMOR_PRIORITY="observational > analogy > wordplay > weather-roast > character-voice"
RADIO_ALLOWED_COMEDY="relatable complaints, tech metaphors (light), quick punchlines, playful hyperbole"
RADIO_BANNED_COMEDY="meme recitation (POV/tell-me-you), dated slang, 'fellow kids' energy"
RADIO_UNHINGED_TRIGGERS="hurricanes, tsunami warnings, volcanic activity, coconut shortages"

# See .env.example for complete settings
```

For a complete example with ALL settings, see `.env.example` in the repository root.

---

## Customization Tips

### Start Simple, Add Complexity

1. **First deployment:** Use defaults, just change API keys and location
2. **After a few hours:** Adjust energy level, vibe keywords
3. **After a few days:** Customize world-building, humor guardrails
4. **After a week:** Fine-tune banned phrases, triggers, temperatures

### Listen and Iterate

- Generate breaks manually: `cd /srv/ai_radio && .venv/bin/python scripts/generate_break.py`
- Listen to the output
- Adjust settings based on what sounds off
- Repeat

### Common Customizations

**Too robotic?**
- Add banned AI phrases
- Increase RADIO_UNHINGED_PERCENTAGE
- Add more RADIO_VIBE_KEYWORDS

**Too chaotic?**
- Decrease RADIO_MAX_RIFFS_PER_BREAK
- Decrease RADIO_UNHINGED_PERCENTAGE
- Lower RADIO_WEATHER_SCRIPT_TEMPERATURE

**Too generic?**
- Strengthen RADIO_WORLD_FRAMING
- Add specific RADIO_UNHINGED_TRIGGERS
- Customize RADIO_HALLUCINATION_KERNELS

**Weather too dramatic?**
- Add weather-specific banned phrases ("cutting through", "stabbing cold")
- Adjust RADIO_WEATHER_TRANSLATION_RULES

---

## Troubleshooting Configuration

### Changes not taking effect

**Problem:** Modified `.env` but station sounds the same

**Solution:** Configuration is read at script runtime. For breaks:
- New breaks will use new config automatically
- Old breaks in `/srv/ai_radio/assets/breaks/` still have old style
- Wait for fresh breaks to generate (hourly)

### API errors

**Problem:** Breaks fail to generate, errors about API keys

**Solution:**
```bash
# Test Claude API
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $RADIO_LLM_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-5","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'

# Check logs
journalctl -u ai-radio-break-gen.service -n 50
```

### Weather not working

**Problem:** Breaks skip weather or weather errors

**Solution:**
- Verify RADIO_STATION_LAT/LON are set
- Verify RADIO_NWS_GRID_* are correct for US locations
- Check: `curl "https://api.weather.gov/points/$RADIO_STATION_LAT,$RADIO_STATION_LON"`

### News empty/broken

**Problem:** No news in breaks

**Solution:**
- Verify RSS feeds are valid: `curl "https://your-rss-feed-url"`
- Check feed format (must be valid RSS/Atom)
- View logs: `journalctl -u ai-radio-break-gen.service -n 100`

---

## Next Steps

✅ **Station configured!**

Proceed to:
- **[Deployment Guide](DEPLOYMENT.md)** - Deploy the code and start streaming
- **[Scripts Reference](SCRIPTS.md)** - Understand what each script does
- **[Troubleshooting](TROUBLESHOOTING.md)** - If something's not working

---

## Reference: Complete Variable List

For a complete alphabetical list of ALL variables with descriptions, see `.env.example` in the repository root.

**Categories:**
1. Base Configuration (paths, timezone)
2. Station Identity (name, location)
3. Location (lat/lon, NWS grid)
4. API Keys (Claude, Gemini)
5. News (RSS feeds, hallucination)
6. Audio Settings (bed timing, volumes)
7. World-Building (setting, tone, framing)
8. Personality (announcer, energy, vibe)
9. Humor Guardrails (allowed, banned, triggers)
10. Authenticity Rules (sentence length, banned phrases)
11. Weather Style (structure, translation)
12. News Style (tone, format)
13. Vocal Style (accent, delivery)
14. Radio Fundamentals (IDs, listener relationship)
15. Liquidsoap Variables (stream metadata)
