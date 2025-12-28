# Gemini TTS Voice Enhancement Design

**Date:** 2025-12-28
**Status:** Implemented
**Components:** voice_synth.py

## Overview

Enhanced voice direction for Gemini TTS 2.5 Pro using Google's official five-element prompting framework. Goal: achieve "weary but unbroken" post-collapse survivor tone with energy level 5/10.

## Problem Statement

Previous voice direction used basic director's notes format:
- Minimal audio profile (just announcer name)
- No scene setting
- Basic vocal guidance without industry terms
- No sample context for warm-up
- Result: default TTS brightness, insufficient control over pacing and affect

## Research Foundation

Based on official Google Gemini TTS documentation (December 2025):

**Five-Element Framework:**
1. Audio Profile - Character identity, archetype, age, background
2. Scene - Physical environment + emotional atmosphere
3. Director's Notes - Performance guidance with industry vocal terms
4. Sample Context - Warm-up line for natural scene entry
5. Transcript - The actual text to speak

**Key Industry Terms:**
- Vocal smile (raising soft palate for brightness) - we avoid this
- Relaxed soft palate (flat affect, neutral tone)
- Chest voice (lower register, grounded delivery)
- Vocal fry (acoustic texture indicating fatigue)
- Pitch contour (narrow range avoids monotone)

## Design Decision

**Hybrid Approach (4 of 5 elements):**
- Implement Audio Profile, Scene, Director's Notes, Transcript
- Skip Sample Context (script already has structured opening with station ID + time)
- Add 7 specific vocal techniques to Director's Notes
- Keep all existing config values (no new environment variables)

**Rationale:**
- Sample Context would duplicate script's formal opening
- Google research warns against over-specification
- All vocal techniques are synergistic (push same direction)
- Backward compatible - easy to revert if needed

## Implementation

### Audio Profile Enhancement
```
# AUDIO PROFILE: {config.announcer_name}
Post-collapse radio operator. Solo overnight shifts, mid-30s. Seen some things, still showing up.
```

**Added:** Character archetype with specific age and context

### Scene Component (NEW)
```
## SCENE
Late-night broadcast booth. Flickering LED panels casting blue-white light. Low equipment hum,
occasional static pop. Converted server room, stripped cables along the walls. Solo shift,
city settling outside. That 2am energy.
```

**Purpose:** Grounds performance in sensory environment, informs acoustic "feel"

### Director's Notes Enhancement

**Vocal Technique Section (NEW):**
1. Relaxed soft palate (no vocal smile, avoid brightness)
2. Flat affect with occasional dry warmth
3. Chest voice, lower-middle register
4. Natural micro-pauses between thoughts
5. Measured breath - let exhaustion show in pacing
6. Employ occasional vocal fry on tail-ends of phrases
7. Maintain narrow pitch range with slight downward inflection on terminal phrases

**Techniques #6 and #7 added based on PAL critical review:**
- Vocal fry = classic fatigue indicator
- Pitch contour = avoids monotone while keeping flat affect

### Sample Context (NEW)
```
### SAMPLE CONTEXT
(Sighs softly) Alright... another hour. Let's see what we've got.
```

**Purpose:** Establishes weary "running start" before formal script opening

**PAL Recommendation:** Despite script having structured opening, Sample Context serves different purpose - sets emotional/rhythmic state before performance begins.

## Critical Analysis (PAL Review)

**Strengths:**
- All vocal techniques are synergistic (not contradictory)
- Scene description is specific without being excessive
- Low risk of over-constraining model
- Techniques directly map to "weary but unbroken" archetype

**Concerns Addressed:**
- Initial plan skipped Sample Context - PAL recommended adding it back
- Added vocal fry and pitch contour techniques based on PAL suggestions
- All constraints push performance in same direction (lower energy, flatter affect)

**Validation Method:**
If output seems off, use incremental tuning:
1. Foundation: chest voice + flat affect + measured breath
2. Refinement: add relaxed soft palate
3. Texture: add vocal fry + pitch contour

## Expected Impact

**Voice Characteristics:**
- Flatter affect (avoiding default TTS brightness)
- Slower, more deliberate pacing with natural pauses
- Lower register, grounded delivery
- Subtle fatigue indicators (vocal fry, measured breath)
- "Weary but unbroken" survivor tone

**Alignment with Config:**
- Energy level 5/10 (down from default brightness)
- Vibe: "weary but unbroken, clear-eyed, quietly defiant"
- Tone: "quiet resignation with steel underneath"

## Testing Strategy

1. Deploy enhanced prompt to server ✅
2. Wait for next scheduled news break (top of hour)
3. Compare audio to previous breaks
4. Listen for: flatter affect, slower pacing, less brightness, more weariness
5. Tune constraints if needed using incremental approach

## Rollback Plan

Changes isolated to single file (voice_synth.py:154-196). Git history preserved. Simple revert if enhancement doesn't achieve desired effect.

## References

**Research Sources:**
- [Gemini TTS Documentation](https://ai.google.dev/gemini-api/docs/speech-generation)
- [Gemini 2.5 TTS Blog Post](https://blog.google/technology/developers/gemini-2-5-text-to-speech/)
- [Emotion-Controlled TTS Deep Dive](https://mabd9714.medium.com/i-tested-gemini-2-5-pros-emotion-controlled-tts-and-it-blew-my-mind-02fd497965dc)

**Internal:**
- PAL critical review (gemini-2.5-pro validation)
- voice_synth.py:154-196 (implementation)
- config.py (personality configuration)

## Future Enhancements

**Potential Additions:**
- Inline emotion tags `[weary]`, `[matter-of-fact]` for granular control
- Per-segment vocal adjustments (weather vs news)
- Dynamic scene descriptions based on time of day
- A/B testing different vocal technique combinations

**Not Recommended:**
- Adding more vocal constraints (risk over-specification)
- Changing Sample Context frequently (consistency matters)
- Inline tags in script generation (adds complexity, current direction sufficient)
