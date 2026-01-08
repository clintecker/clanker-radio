# Fix News Breaks Timing - Design Document

**Issue:** #8 - News breaks playing at wrong time (2pm break at 5pm)
**Date:** 2026-01-08
**Branch:** fix/issue-8-news-breaks-timing

## Problem

`schedule_break.py` selects the most recent break by modification time only - there's no freshness check. If break generation fails, the scheduler plays stale content.

**Failure scenario:**
1. Break generated at 2pm
2. Generation fails at 2:50pm (API error, quota, etc.)
3. At 5pm scheduler picks the 2pm break → stale content plays

The `break_freshness_minutes` config (50 min) exists but isn't used in the scheduler.

## Solution

Add a freshness check to `schedule_break.py` that rejects breaks older than `break_freshness_minutes`. Exit with code 1 to trigger systemd alerts.

### Design Decisions

1. **Skip and log error** rather than generate on-demand
   - Clean separation of concerns
   - Generation failures should be visible, not masked
   - Not enough time for on-demand generation anyway

2. **Use file mtime** for freshness check (not filename parsing)
   - Simpler, already available
   - Less fragile than parsing filename conventions

3. **Exit code 1** when stale break detected
   - Triggers systemd failure alerts
   - Ops team notified that generation is failing

## Implementation

### Change 1: `scripts/schedule_break.py`

Add freshness check after line 53 (`next_break = breaks[0]`):

```python
import time

# After finding next_break...
age_seconds = time.time() - next_break.stat().st_mtime
freshness_seconds = config.operational.break_freshness_minutes * 60

if age_seconds > freshness_seconds:
    age_minutes = int(age_seconds / 60)
    logger.error(
        f"Stale break detected: {next_break.name} is {age_minutes} minutes old "
        f"(threshold: {config.operational.break_freshness_minutes} minutes). "
        "Break generation may be failing."
    )
    sys.exit(1)
```

### Change 2: `tests/test_schedule_break.py` (new file)

Add tests for:
1. Stale break detection - mock old mtime, verify exit 1
2. Fresh break passes - mock recent mtime, verify proceeds to scheduling

## Behavior Change

| Before | After |
|--------|-------|
| Always plays newest break regardless of age | Rejects breaks older than 50 min with exit 1 |

## Files Changed

| File | Change |
|------|--------|
| `scripts/schedule_break.py` | Add ~10 lines freshness check |
| `tests/test_schedule_break.py` | New file, ~50 lines |

## Config

No changes needed - uses existing `config.operational.break_freshness_minutes` (default: 50).
