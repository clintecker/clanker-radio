# Adding New Music to AI Radio

## Quick Start (Local Development)

```bash
# Use the batch ingest script
./scripts/batch_ingest.sh /path/to/your/music/folder
```

## Quick Start (Remote Server)

```bash
# 1. Copy new music to staging directory
scp /path/to/new/music/*.mp3 user@your-server:/srv/ai_radio/staging/

# 2. SSH to server and run ingest
ssh user@your-server
sudo -u ai-radio /srv/ai_radio/scripts/liquidsoap-wrapper.sh /srv/ai_radio/.venv/bin/python /srv/ai_radio/scripts/ingest.py /srv/ai_radio/staging

# 3. Check results
sudo -u ai-radio /srv/ai_radio/scripts/liquidsoap-wrapper.sh /srv/ai_radio/.venv/bin/python /srv/ai_radio/scripts/list_assets.py
```

## Detailed Process

### Step 1: Prepare Music Files

Supported formats:
- **MP3** (recommended)
- **FLAC**
- **WAV**
- **M4A**
- **OGG**

The ingest script will:
- Extract metadata (title, artist, album)
- Normalize loudness to -18 LUFS
- Normalize true peak to -1.0 dBTP
- Generate SHA256 asset IDs
- Convert to MP3 if needed

### Step 2: Upload to Staging

```bash
# Create staging directory if it doesn't exist
ssh user@your-server "sudo -u ai-radio mkdir -p /srv/ai_radio/staging"

# Upload music files
scp ~/Music/new_tracks/*.mp3 user@your-server:/srv/ai_radio/staging/

# Or use rsync for larger collections
rsync -avz --progress ~/Music/collection/ user@your-server:/srv/ai_radio/staging/
```

### Step 3: Run Ingest Script

The ingest script processes files and adds them to the database:

```bash
ssh user@your-server

# Run ingest (processes all files in staging)
sudo -u ai-radio /srv/ai_radio/scripts/liquidsoap-wrapper.sh \
  /srv/ai_radio/.venv/bin/python \
  /srv/ai_radio/scripts/ingest.py \
  /srv/ai_radio/staging

# Ingest specific files
sudo -u ai-radio /srv/ai_radio/scripts/liquidsoap-wrapper.sh \
  /srv/ai_radio/.venv/bin/python \
  /srv/ai_radio/scripts/ingest.py \
  /srv/ai_radio/staging/album1/
```

### Step 4: Verify Ingestion

```bash
# List all music assets
sudo -u ai-radio /srv/ai_radio/scripts/liquidsoap-wrapper.sh \
  /srv/ai_radio/.venv/bin/python \
  /srv/ai_radio/scripts/list_assets.py

# Check database
sqlite3 /srv/ai_radio/db/radio.sqlite3 "SELECT COUNT(*) FROM assets WHERE kind='music';"

# View normalized files
ls -lh /srv/ai_radio/assets/music/
```

### Step 5: Automatic Playback

Once ingested, the music enqueue service (Phase 5) will automatically:
- Select tracks based on energy levels
- Avoid recent repeats
- Queue them for playback

**Note:** Phase 5 music enqueue service is not yet implemented. Currently, you can manually queue tracks:

```bash
# Manually queue a track via Liquidsoap socket
echo "music.push /srv/ai_radio/assets/music/ASSET_ID.mp3" | nc -U /run/liquidsoap/radio.sock
```

## Automation (Future Phase 5)

Once Phase 5 is complete, new music will be automatically:
1. Queued based on time of day and energy level
2. Scheduled to avoid repetition
3. Mixed with breaks and station IDs

## Troubleshooting

### Ingest fails with permission errors
```bash
# Fix ownership
sudo chown -R ai-radio:ai-radio /srv/ai_radio/staging
sudo chmod 755 /srv/ai_radio/staging
```

### Files not showing up
```bash
# Check ingest logs
journalctl -u ai-radio-ingest -n 50

# Verify database
sqlite3 /srv/ai_radio/db/radio.sqlite3 "SELECT id, title, artist FROM assets WHERE kind='music' ORDER BY id DESC LIMIT 10;"
```

### Audio quality issues
The normalization process ensures consistent loudness:
- Target: -18 LUFS (broadcast standard)
- True peak: -1.0 dBTP (headroom for encoding)

If source files are already normalized, they'll be copied with minimal processing.

## Batch Operations

### Import entire music library
```bash
# Sync entire collection
rsync -avz --progress ~/Music/Library/ user@your-server:/srv/ai_radio/staging/

# Ingest all at once
ssh user@your-server "sudo -u ai-radio /srv/ai_radio/scripts/liquidsoap-wrapper.sh \
  /srv/ai_radio/.venv/bin/python \
  /srv/ai_radio/scripts/ingest.py \
  /srv/ai_radio/staging"

# This may take a while for large libraries
```

### Re-ingest updated metadata
```bash
# Delete from database (keeps normalized files)
sqlite3 /srv/ai_radio/db/radio.sqlite3 "DELETE FROM assets WHERE id='ASSET_ID';"

# Re-ingest
sudo -u ai-radio /srv/ai_radio/.venv/bin/python /srv/ai_radio/scripts/ingest.py /path/to/file.mp3
```

## File Organization

After ingestion, files are organized as:

```
/srv/ai_radio/
├── staging/           # Upload new music here
│   └── *.mp3         # Files to be ingested
├── assets/
│   └── music/        # Normalized, ready-to-play files
│       └── ASSET_ID.mp3
└── db/
    └── radio.sqlite3 # Metadata database
```

The ingest script:
1. Reads files from staging
2. Normalizes audio
3. Saves to assets/music/ with SHA256 filename
4. Adds metadata to database
5. **Does not** delete staging files (do this manually)

## Cleanup

After successful ingestion:

```bash
# Remove staged files
ssh user@your-server "sudo rm -rf /srv/ai_radio/staging/*"
```
