# LAST BYTE RADIO Database TUI

A beautiful terminal user interface for browsing the LAST BYTE RADIO database built with [Bubble Tea](https://github.com/charmbracelet/bubbletea), [Bubbles](https://github.com/charmbracelet/bubbles), and [Lipgloss](https://github.com/charmbracelet/lipgloss).

## Features

- 🎵 **Track Browser**: Browse all music tracks with sortable columns
- 📊 **Detailed View**: View comprehensive track metadata (duration, loudness, energy, plays)
- 📈 **Statistics**: Station-wide stats (total tracks, plays, top artists)
- 📜 **Play History**: Recent play history with timestamps and source tracking
- 🎨 **Cyberpunk Aesthetic**: Neon-colored interface matching LAST BYTE RADIO's dystopian vibe

## Installation

```bash
# Install dependencies
go mod download

# Sync database from production
./scripts/sync_db.sh

# Run the TUI
go run ./cmd/radiotui
```

## Usage

### Navigation

- `1` - Track List View
- `2` - Track Detail View (shows details of selected track)
- `3` - Statistics View
- `4` - Play History View
- `r` - Refresh data from database
- `↑/↓` or `j/k` - Navigate through lists
- `q` - Quit

### Syncing Database

The database lives on the production server at `10.10.0.86`. To sync it locally:

```bash
./scripts/sync_db.sh
```

This will:
1. Copy `radio.sqlite3` from `/srv/ai_radio/db/` on the server
2. Place it in `./db/radio.sqlite3` locally
3. Display stats about the synced database

### Views

#### 1. Track List View
- Shows all music tracks in a sortable table
- Columns: Artist, Title, Album, Duration, Energy Level, Play Count
- Navigate with arrow keys or vim keybindings

#### 2. Track Detail View
- Displays comprehensive metadata for the selected track:
  - Title, Artist, Album
  - Duration, Loudness (LUFS), True Peak (dBTP)
  - Energy level (0-100)
  - Play count
  - File path and SHA256 ID

#### 3. Statistics View
- **Total Tracks**: Number of music tracks in library
- **Total Plays**: All-time play count
- **Total Duration**: Combined length of all tracks
- **Average Energy**: Mean energy level across library
- **Plays (24h)**: Recent play activity
- **Top Artist**: Most played artist
- **Most Played Track**: Highest play count

#### 4. Play History View
- Last 50 plays with timestamps
- Shows source (music, break, bumper, bed)
- Track identification

## Database Schema

### assets table
```sql
- id (TEXT): SHA256 hash of file
- path (TEXT): File system path
- kind (TEXT): music, break, bed, safety
- duration_sec (REAL): Duration in seconds
- loudness_lufs (REAL): Integrated loudness in LUFS
- true_peak_dbtp (REAL): True peak in dBTP
- energy_level (INTEGER): 0-100 scale
- title, artist, album (TEXT): Metadata
- created_at (TEXT): ISO8601 timestamp
```

### play_history table
```sql
- id (INTEGER): Primary key
- asset_id (TEXT): Foreign key to assets
- played_at (TEXT): ISO8601 UTC timestamp
- source (TEXT): music, override, break, bumper, bed
- hour_bucket (TEXT): Hour-aggregated timestamp
```

## Color Palette

The TUI uses a cyberpunk-inspired color scheme:

- **Magenta (#FF00FF)**: Headers, selected items, primary accents
- **Cyan (#00FFFF)**: Text, borders, secondary accents
- **Green (#00FF00)**: Stats, success indicators
- **Dark backgrounds (#1a1a1a, #2a2a2a)**: Containers, selected rows

## Development

### Building

```bash
go build -o radiotui ./cmd/radiotui
```

### Running with custom database

```bash
go run ./cmd/radiotui /path/to/custom.sqlite3
```

## Troubleshooting

**"Error opening database"**
- Ensure you've synced the database with `./scripts/sync_db.sh`
- Check that `./db/radio.sqlite3` exists and is readable

**Empty views**
- The database might be empty on the server
- Check server logs at `/srv/ai_radio/logs/`

**SSH connection failed during sync**
- Ensure you have SSH access to `ai-radio@10.10.0.86`
- Check VPN connection if required

## License

Part of the LAST BYTE RADIO project. Broadcasting from the neon-lit wasteland of Chicago. 🌃
