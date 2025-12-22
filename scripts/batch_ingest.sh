#!/bin/bash
# Batch ingest all music files from staging directory

set -euo pipefail

STAGING_DIR="${1:-/srv/ai_radio/staging}"
PYTHON="/srv/ai_radio/.venv/bin/python"
DB_PATH="/srv/ai_radio/db/radio.sqlite3"
MUSIC_DIR="/srv/ai_radio/assets/music"

echo "=== Batch Music Ingest ==="
echo "Staging directory: $STAGING_DIR"
echo

# Count files
total_files=$(find "$STAGING_DIR" -type f \( -name "*.mp3" -o -name "*.flac" -o -name "*.wav" -o -name "*.m4a" \) | wc -l)
echo "Found $total_files music files to ingest"
echo

if [ "$total_files" -eq 0 ]; then
    echo "No music files found in staging directory"
    exit 0
fi

# Ingest each file
success=0
failed=0

find "$STAGING_DIR" -type f \( -name "*.mp3" -o -name "*.flac" -o -name "*.wav" -o -name "*.m4a" \) | while read -r file; do
    echo "Processing: $(basename "$file")"

    if $PYTHON -m ai_radio.ingest "$file" --kind music --db "$DB_PATH" --music-dir "$MUSIC_DIR"; then
        success=$((success + 1))
        echo "  ✓ Success"
    else
        failed=$((failed + 1))
        echo "  ✗ Failed"
    fi
    echo
done

echo "=== Ingest Complete ==="
echo "Files processed: $total_files"
echo

# Show final count
final_count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM assets WHERE kind='music';")
echo "Total music assets in database: $final_count"
