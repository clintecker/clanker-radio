# Now Playing System - Sequence Diagram

## Current Flow (With Bugs)

```mermaid
sequenceDiagram
    participant Timer as Systemd Timer<br/>(every 10s)
    participant LS as Liquidsoap
    participant RP as record_play.py
    participant DB as Database<br/>(SQLite)
    participant EP as export_now_playing.py
    participant JSON as now_playing.json
    participant FE as Frontend<br/>(polls every 5s)

    Note over LS: Station ID scheduled at :29:00
    Note over LS: Music track playing...

    rect rgb(255, 200, 200)
        Note over LS: T0: Music track ends, Station ID starts
        LS->>LS: Switch to break_queue
        LS->>LS: Update radio.metadata

        Note over LS,RP: Liquidsoap callback fires (async)
        LS-->>RP: on_track callback<br/>filename=station_id_5.mp3

        activate RP
        RP->>DB: SELECT id FROM assets<br/>WHERE path = ?
        DB-->>RP: NULL (station IDs not in assets!)
        Note over RP: asset_id = "station_id_5"<br/>(filename stem)
        RP->>DB: INSERT INTO play_history<br/>(station_id_5, T0, bumper)
        DB-->>RP: ✓ Written

        Note over RP,EP: T0+100ms: Trigger export
        RP-->>EP: subprocess.Popen (detached)
        deactivate RP

        activate EP
        EP->>LS: query_socket("radio.metadata")
        LS-->>EP: filename=station_id_5.mp3 ✓

        Note over EP,DB: ❌ BUG: SQL Query
        EP->>DB: SELECT * FROM play_history ph<br/>LEFT JOIN assets a<br/>WHERE a.path = ?
        Note over DB: a.path is NULL!<br/>WHERE NULL = filename → FALSE
        DB-->>EP: ZERO ROWS ❌

        Note over EP: Falls to "not in play_history"<br/>Fabricates metadata!
        EP->>EP: Create fake record:<br/>- asset_id: None ❌<br/>- played_at: T0+500ms ❌<br/>- duration: ffprobe call
        EP->>JSON: Atomic write<br/>(fabricated data)
        deactivate EP
    end

    rect rgb(255, 220, 200)
        Note over Timer: T0+3s: Timer fires (race!)
        Timer->>EP: Run export_now_playing.py
        activate EP
        EP->>LS: query_socket("radio.metadata")
        LS-->>EP: filename=station_id_5.mp3
        EP->>DB: SELECT * FROM play_history<br/>WHERE a.path = ?
        DB-->>EP: ZERO ROWS ❌ (same bug!)
        EP->>EP: Fabricate AGAIN<br/>with DIFFERENT timestamp!
        EP->>JSON: Atomic write<br/>(different fabricated data)
        deactivate EP
    end

    rect rgb(200, 220, 255)
        Note over FE: T0+5s: Frontend polls
        FE->>JSON: fetch('/api/now_playing.json')
        JSON-->>FE: Returns fabricated data
        FE->>FE: Check asset_id changed?<br/>Old: "abc123music"<br/>New: None ❌
        Note over FE: Updates display but<br/>progress bar wrong!<br/>(timestamp off by 500ms)
    end

    Note over LS: T0+8s: Station ID ends
    LS->>LS: Switch to music_queue
    LS->>LS: Update radio.metadata

    rect rgb(200, 255, 200)
        LS-->>RP: on_track callback<br/>filename=music_track.mp3
        activate RP
        RP->>DB: SELECT id FROM assets<br/>WHERE path = ?
        DB-->>RP: "abc456music" ✓ (found!)
        RP->>DB: INSERT INTO play_history
        RP-->>EP: subprocess.Popen
        deactivate RP

        activate EP
        EP->>LS: query_socket("radio.metadata")
        LS-->>EP: filename=music_track.mp3 ✓
        EP->>DB: SELECT * FROM play_history<br/>WHERE a.path = ?
        DB-->>EP: Row found ✓ (music in assets!)
        EP->>JSON: Atomic write<br/>(correct data)
        deactivate EP
    end

    rect rgb(200, 220, 255)
        Note over FE: T0+10s: Frontend polls
        FE->>JSON: fetch('/api/now_playing.json')
        JSON-->>FE: Returns music metadata
        FE->>FE: Display updates to music
        Note over FE: User only saw station ID<br/>for 5 seconds!<br/>(might have missed it)
    end
```

## Problems Identified

### 🔴 Critical Bugs

1. **SQL Query Bug** (export_now_playing.py:586)
   - Uses `WHERE a.path = ?` after LEFT JOIN
   - Station IDs/breaks not in assets table → `a.path` is NULL
   - NULL comparison fails → query returns zero rows
   - Falls back to fabricated metadata with wrong timestamps

2. **Race Condition: Multiple Export Triggers**
   - Systemd timer runs every 10s
   - record_play.py also triggers export
   - Both can run simultaneously (lock prevents, but causes delays)
   - Timer can fire BEFORE database write completes

3. **Data Inconsistency**
   - Music tracks: SHA256 asset_id, in assets table
   - Station IDs/breaks: filename stem asset_id, NOT in assets table
   - Query logic assumes all tracks are in assets table

### 🟡 Architecture Issues

1. **Polling Latency**
   - Frontend polls every 5s
   - Export runs every 10s (timer) + immediate (trigger)
   - Total lag: up to 15 seconds worst case
   - Short tracks (3-5s) might be missed entirely

2. **Fabricated Metadata**
   - Missing asset_ids
   - Wrong timestamps (off by 100-500ms)
   - Progress bar calculations incorrect
   - Frontend can't properly detect track changes

## Proposed Fixed Flow

```mermaid
sequenceDiagram
    participant LS as Liquidsoap
    participant RP as record_play.py
    participant DB as Database
    participant EP as export_now_playing.py
    participant JSON as now_playing.json
    participant FE as Frontend<br/>(polls every 2s)

    Note over LS: T0: Station ID starts
    LS->>LS: Update radio.metadata
    LS-->>RP: on_track callback

    activate RP
    RP->>DB: Write to play_history<br/>(asset_id=station_id_5)
    DB-->>RP: ✓
    RP-->>EP: subprocess.Popen
    deactivate RP

    activate EP
    EP->>LS: query_socket("radio.metadata")
    LS-->>EP: filename=station_id_5.mp3

    Note over EP,DB: ✅ FIXED: Direct query
    EP->>DB: SELECT * FROM play_history<br/>WHERE asset_id = ?<br/>OR (SELECT id FROM assets WHERE path = ?)
    DB-->>EP: Row found ✓
    Note over EP: Uses REAL play_history data<br/>- Correct asset_id<br/>- Accurate timestamp<br/>- No fabrication
    EP->>JSON: Atomic write (correct data)
    deactivate EP

    Note over FE: T0+2s: Frontend polls
    FE->>JSON: fetch()
    JSON-->>FE: Correct metadata
    FE->>FE: Display updates immediately<br/>Progress bar accurate!

    Note over LS: T0+8s: Station ID ends
    LS->>LS: Switch to music
    LS-->>RP: on_track callback
    RP->>DB: Write play_history
    RP-->>EP: Trigger export
    EP->>EP: Same fixed query logic
    EP->>JSON: Update

    Note over FE: T0+10s: Frontend polls
    FE->>JSON: fetch()
    FE->>FE: Smooth transition to music
```

## Key Improvements

### ✅ Correctness Fixes

1. **Fix SQL Query**
   - Query play_history directly for station IDs/breaks
   - Fall back to assets table join only for music
   - No more fabricated metadata
   - Accurate timestamps from play_history

2. **Timer as Fallback**
   - Change systemd timer from 10s to 2-minute fallback
   - Primary exports triggered immediately by record_play.py
   - Eliminates race conditions (2min vs 10s)
   - Timer provides resilience if triggered export fails

### ✅ Real-Time Improvements

3. **Reduce Frontend Polling**
   - Change from 5s to 2s interval
   - Catches track changes faster
   - Better UX for short tracks
   - Still efficient (no excessive load)

4. **Future: Server-Sent Events (SSE)**
   - Push updates instead of polling
   - Sub-second latency
   - Efficient (no unnecessary requests)
   - Requires more changes (later phase)
