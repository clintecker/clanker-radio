# AI Radio Station - Future Ideas

## Random Ads System

**Goal**: Insert random ads between tracks for authentic radio station feel

**Architecture Approach**:
- Pre-rendered ad pool stored in `/ads` folder
- Ads are just another audio source for Liquidsoap (doesn't break "never dead air" rule)
- If ad system fails, music keeps playing

**Implementation Options**:

1. **Weighted Random Selection**
   - Liquidsoap randomly picks from ad pool between tracks
   - Config file controls frequency/weight (e.g., 10% chance after each track)
   - Simple, low-maintenance

2. **Time-Based Insertion**
   - Ads at fixed intervals (every 15-20 min)
   - Python brain schedules and renders next ad to disk
   - More predictable, like real radio

3. **Contextual/Thematic**
   - Match ad themes to time of day or track mood
   - Morning ads vs evening ads
   - Requires more logic but could be funnier

**Content Ideas**:
- LLM-generated parody ads for fake products
- Station IDs and bumpers
- Deadpan PSAs
- Fake sponsorship announcements
- Absurdist product pitches

**Example Fake Products**:
- "Void Coffee - Tastes like the existential dread you've been avoiding"
- "Time Crystals - Finally, a supplement that does nothing, scientifically"
- "Cloud Insurance - Because eventually, everything fails"

**Technical Notes**:
- Use same pipeline as news breaks (LLM script → TTS → music bed → normalize)
- Ads stored as normalized MP3s (-18 LUFS, -1 dBTP)
- Liquidsoap handles fallback automatically
- No single point of failure

---

## Other Future Ideas

(Add more ideas here as they come up)
