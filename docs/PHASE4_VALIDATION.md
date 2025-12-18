# Phase 4: Content Generation - Validation Summary

**Date:** 2025-12-18
**Status:** ⚠️ REQUIRES FIXES (Critical Issues Found)
**Validation Method:** Multi-model code review (Gemini-3-Pro)

---

## Executive Summary

Phase 4 Content Generation plan has **excellent architecture** and correctly implements the producer pattern from Phase 3, but contains **2 critical SOW violations** and **1 high-priority SOW compliance gap** that must be fixed before implementation.

**Critical Issues:**
1. Wrong module import name (`.audio_processing` vs `.audio`)
2. Wrong output directory path (SOW Section 5 violation)
3. Missing `next.mp3` / `last_good.mp3` rotation (SOW Section 9 requirement)

**Recommendation:** Fix all CRITICAL and HIGH issues before proceeding to implementation.

---

## Issues Found

### 🔴 CRITICAL (Must Fix Before Implementation)

| # | Severity | Issue | Impact | Fix |
|---|----------|-------|--------|-----|
| 1 | **CRITICAL** | **Module Import Error** | ImportError on startup | Change `from .audio_processing` → `from .audio` |
| 2 | **CRITICAL** | **SOW Path Violation** | Wrong break output directory | Change `/media/breaks` → `/assets/breaks` |

#### Issue #1: Module Import Error (line 1219)

**Problem:** Phase 4 plan imports from `.audio_processing`, but Phase 2 created the module as `.audio`.

**Current (WRONG):**
```python
# In src/ai_radio/break_gen.py line 1219
from .audio_processing import normalize_audio
```

**Fixed:**
```python
from .audio import normalize_audio
```

**Fix:** Update import statement in Task 7 (Break Generation Orchestrator).

#### Issue #2: SOW Path Violation (line 1469)

**Problem:** Service script uses `/srv/ai_radio/media/breaks`, but SOW Section 5 mandates `/srv/ai_radio/assets/breaks`. The `media/` directory is not defined in the SOW architecture.

**Current (WRONG):**
```python
# In scripts/generate_break.py line 1469
breaks_dir = Path("/srv/ai_radio/media/breaks")
```

**Fixed:**
```python
breaks_dir = Path("/srv/ai_radio/assets/breaks")
```

**Fix:** Update all references from `media/breaks` → `assets/breaks` throughout Phase 4 plan.

---

### 🟠 HIGH (Should Fix Before Implementation)

| # | Severity | Issue | Impact | Fix |
|---|----------|-------|--------|-----|
| 3 | **HIGH** | **Missing SOW File Rotation** | Breaks SOW Section 9 fallback logic | Implement `next.mp3` / `last_good.mp3` rotation |
| 4 | **HIGH** | **Feedparser Blocking I/O** | Service can hang indefinitely | Use httpx with timeout before feedparser |

#### Issue #3: Missing SOW-Mandated File Rotation

**Problem:** SOW Section 9 requires `next.mp3` and `last_good.mp3` for fallback chain logic ("Prefer next.mp3... Else last_good.mp3"). Current plan generates timestamped files but never updates these pointers.

**Impact:** Without this, the Liquidsoap fallback chain defined in SOW cannot function correctly.

**Fix:** Add to end of `generate_break()` function in Task 7:

```python
# After successful normalization and atomic move to final_path
next_break = output_dir / "next.mp3"
last_good = output_dir / "last_good.mp3"

# Rotate: current next.mp3 → last_good.mp3
if next_break.exists():
    if last_good.exists():
        last_good.unlink()
    next_break.rename(last_good)

# Link new break as next.mp3
if next_break.exists():
    next_break.unlink()
next_break.symlink_to(final_path.name)

logger.info(f"Updated next.mp3 → {final_path.name}, rotated last_good.mp3")
```

#### Issue #4: Feedparser Blocking I/O (line 421)

**Problem:** `feedparser.parse(url)` doesn't have robust internal timeout and can hang indefinitely if server stalls, blocking the entire service.

**Current (RISKY):**
```python
feed = feedparser.parse(url)
```

**Fixed:**
```python
# Fetch with strict timeout first
response = httpx.get(url, timeout=timeout, follow_redirects=True)
feed = feedparser.parse(response.content)
```

**Fix:** Update Task 3 (News RSS Aggregation) to use httpx before feedparser.

---

### 🟡 MEDIUM (Operational Improvements)

| # | Severity | Issue | Impact | Fix |
|---|----------|-------|--------|-----|
| 5 | MEDIUM | No Liquidsoap Queue Integration | Breaks generated but not played | May be intentional for Phase 5 |
| 6 | MEDIUM | Audio Mixing amix Volume Behavior | Voice may be attenuated unexpectedly | Add explicit weights parameter |
| 7 | MEDIUM | No Retry Logic for API Failures | Transient failures cause missing breaks | Add retry with exponential backoff |
| 8 | MEDIUM | No Break Cleanup Strategy | Old breaks accumulate forever | Add cleanup of breaks >7 days old |

#### Issue #5: No Liquidsoap Queue Integration

**Problem:** Plan generates breaks to disk but doesn't push them to Liquidsoap's `break_queue`.

**Analysis:** This may be intentional - Phase 5 (Scheduling) should handle queue management. However, it creates a functional gap where breaks exist but aren't played until Phase 5 is implemented.

**Recommendation:** Add note in documentation that breaks won't play until Phase 5 enqueue service is operational, OR add basic queue push to service script.

#### Issue #6: Audio Mixing amix Volume Behavior (line 1125)

**Problem:** The `amix` filter defaults to normalizing input weights, which can drastically reduce voice volume when bed is added.

**Fixed:**
```bash
# Add explicit weights to prevent voice attenuation
"[0:a][bed]amix=inputs=2:duration=first:dropout_transition=2:weights='1 1'"
```

**Fix:** Update Task 6 (Audio Mixing) ffmpeg command.

---

### 🟢 LOW (Nice-to-Have)

| # | Severity | Issue | Impact | Fix |
|---|----------|-------|--------|-----|
| 9 | LOW | Hardcoded NWS User-Agent Email | NWS requests valid contact | Make email configurable |
| 10 | LOW | No TTS Output Validation | Silent failures on corrupted TTS | Check file size/duration |
| 11 | LOW | No Audio Duration Error Handling | `get_audio_duration` can return 0 | Handle zero duration case |
| 12 | LOW | Secrets File Permissions | 600 is acceptable, 400 is better | Document chmod 400 option |

---

## Implementation Priority

### Must Fix (Blocking)

1. ✅ **Issue #1**: Fix module import (`.audio_processing` → `.audio`)
2. ✅ **Issue #2**: Fix output path (`/media/breaks` → `/assets/breaks`)
3. ✅ **Issue #3**: Implement `next.mp3` / `last_good.mp3` rotation
4. ✅ **Issue #4**: Add httpx timeout wrapper for feedparser

### Should Fix (Operational)

5. ✅ **Issue #6**: Add explicit weights to amix filter
6. ✅ **Issue #7**: Add retry logic for API calls
7. ⏸ **Issue #5**: Document Phase 5 dependency for playback (defer)
8. ⏸ **Issue #8**: Break cleanup strategy (defer - not critical)

### Can Defer (Nice-to-Have)

9. ⏸ **Issue #9**: Configurable NWS email
10. ⏸ **Issue #10**: TTS output validation
11. ⏸ **Issue #11**: Audio duration error handling
12. ⏸ **Issue #12**: Tighter secrets permissions

---

## SOW Compliance Status

**Before Fixes:**
- ❌ Section 5: File/Folder Layout (wrong directory: media vs assets)
- ❌ Section 9: Break fallback logic (`next.mp3`/`last_good.mp3` missing)
- ✅ Section 12: Weather integration (NWS API)
- ✅ Section 12: News aggregation (RSS)
- ✅ Section 12: LLM bulletin scripting
- ✅ Section 12: TTS voice synthesis
- ✅ Section 12: Bed audio mixing
- ✅ Section 8: Loudness normalization (-18 LUFS, -1.0 dBTP)
- ✅ Section 3: Non-Negotiable #5 (Atomic operations)
- ✅ Producer pattern (break freshness checking)

**After Fixes:**
- ✅ Section 5: File/Folder Layout
- ✅ Section 9: Break fallback logic
- ✅ Section 12: All content generation requirements
- ✅ Section 8: Loudness normalization
- ✅ Section 3: Non-Negotiable #5
- ✅ Producer pattern

---

## Positive Aspects

✅ **Producer Pattern:** Correctly implements freshness checking on producer side (per Phase 3 validation)
✅ **Atomic Operations:** Excellent usage of tempfile + rename throughout pipeline
✅ **Modern Stack:** Good use of uv, httpx, pydantic-settings
✅ **Error Handling:** Comprehensive fallback strategies for all API failures
✅ **Resource Isolation:** CPU nice level prevents starving Liquidsoap
✅ **Clean Architecture:** Clear separation of concerns (Weather/News/LLM/TTS/Mixing)
✅ **Testing Strategy:** Unit tests for each component
✅ **Security:** API keys in .secrets file with restrictive permissions

---

## Validation Methodology

**Tools Used:**
- Gemini-3-Pro (Google) - Code review and SOW compliance analysis

**Process:**
1. Systematic code review of all Phase 4 tasks
2. Cross-reference with Phase 2 module names
3. Path validation against SOW Section 5
4. Break fallback logic validation against SOW Section 9
5. API timeout and error handling analysis
6. Audio processing pipeline review

**Confidence Level:** Very High - All issues independently verified against SOW and previous phases

---

## Next Steps

1. ✅ Apply all CRITICAL fixes to Phase 4 plan
2. ✅ Apply HIGH priority fixes (file rotation, feedparser timeout)
3. ✅ Apply selected MEDIUM fixes (amix weights, retry logic)
4. ⏭️ Validate fixed plan (quick sanity check)
5. ⏭️ Commit and push Phase 4 fixes
6. ⏭️ Continue with Phase 5: Scheduling & Orchestration

---

## Sign-Off

**Phase 4: APPROVED with required fixes**

Core architecture is excellent and correctly implements producer pattern from Phase 3. Issues are primarily integration points (wrong module name, wrong path) and one missing SOW requirement (file rotation). Once CRITICAL and HIGH issues are addressed, plan is ready for implementation.

**Validation Complete:** 2025-12-18
**Validated By:** Gemini-3-Pro expert analysis
**Status:** ✅ Ready for fixes, then implementation
