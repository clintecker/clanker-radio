#!/usr/bin/env bash
# Sync radio database from production server to local machine
#
# Usage: ./scripts/sync_db.sh [ssh_key_path]
# Example: ./scripts/sync_db.sh ~/.ssh/id_ed25519
#
# Configuration:
#   Set these environment variables or edit this script:
#   - RADIO_SERVER: Server hostname or IP
#   - RADIO_SERVER_USER: SSH username
#   - RADIO_REMOTE_DB: Remote database path
#   - RADIO_LOCAL_DB: Local database path

set -e

SERVER="${RADIO_SERVER:-your-server.com}"
SERVER_USER="${RADIO_SERVER_USER:-your-user}"
REMOTE_DB="${RADIO_REMOTE_DB:-/srv/ai_radio/db/radio.sqlite3}"
LOCAL_DB="${RADIO_LOCAL_DB:-./db/radio.sqlite3}"

# Check if SERVER is still default
if [ "$SERVER" = "your-server.com" ]; then
    echo "ERROR: Please configure database sync settings!"
    echo ""
    echo "Set environment variables:"
    echo "  export RADIO_SERVER='your-server.com'"
    echo "  export RADIO_SERVER_USER='your-user'"
    echo ""
    echo "Or edit scripts/sync_db.sh directly"
    exit 1
fi

# SSH options to prevent "too many authentication failures"
SSH_OPTS="-o IdentitiesOnly=yes -o NumberOfPasswordPrompts=0"

# If SSH key path provided, use it
if [ -n "$1" ]; then
    SSH_OPTS="$SSH_OPTS -i $1"
    echo "🔑 Using SSH key: $1"
fi

echo "🔄 Syncing database from $SERVER..."

# Ensure local db directory exists
mkdir -p "$(dirname "$LOCAL_DB")"

# Copy database from server with SSH options
scp $SSH_OPTS "${SERVER_USER}@${SERVER}:${REMOTE_DB}" "$LOCAL_DB"

# Get database stats
TRACK_COUNT=$(sqlite3 "$LOCAL_DB" "SELECT COUNT(*) FROM assets WHERE kind = 'music'")
PLAY_COUNT=$(sqlite3 "$LOCAL_DB" "SELECT COUNT(*) FROM play_history")
DB_SIZE=$(ls -lh "$LOCAL_DB" | awk '{print $5}')

echo "✅ Database synced successfully!"
echo "📊 Stats:"
echo "   - Tracks: $TRACK_COUNT"
echo "   - Total plays: $PLAY_COUNT"
echo "   - Database size: $DB_SIZE"
echo ""
echo "🎵 Run the TUI with: go run ./cmd/radiotui"
