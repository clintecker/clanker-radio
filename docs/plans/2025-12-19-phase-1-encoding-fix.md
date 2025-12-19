# Phase 1 Encoding Fix - Implementation Plan

> **For Claude:** This plan corrects the MP3 encoding gap discovered during Phase 1 implementation.

**Generated:** 2025-12-19
**Status:** Ready for Implementation
**Related:** docs/plans/2025-12-18-phase-1-core-infrastructure.md

---

## Executive Summary

**Problem:** Phase 1 implementation successfully deployed streaming infrastructure, but audio stream broadcasts in headerless raw PCM format (176 KB/s) instead of MP3 (24 KB/s) as specified in the original plan.

**Root Cause:** Original Phase 1 Task 1 installed system encoder libraries and base Liquidsoap via OPAM, but did not install OPAM encoder packages (mad, lame, ffmpeg). OPAM's Liquidsoap package requires explicit encoder package installation.

**Solution:** Install OPAM encoder packages and verify availability before applying MP3 configuration.

**Impact:**
- Proper MP3 encoding (192kbps)
- 87% bandwidth reduction (176 KB/s → 24 KB/s)
- Standard player compatibility (no format specification needed)

---

## Problem Analysis

### What Went Wrong

**Original Task 1 (line 59-68 of phase-1-core-infrastructure.md):**
```bash
opam install -y liquidsoap
```

**Original Task 5 (line 559 of phase-1-core-infrastructure.md):**
```liquidsoap
%mp3(bitrate=192, samplerate=44100, stereo=true)
```

**The Gap:**
- System libraries installed: libmp3lame-dev, libmad0-dev ✓
- Base Liquidsoap installed: version 2.4.0 ✓
- Encoder packages installed: MISSING ✗
- Result: Only basic encoders available (wav, avi, ndi)

### Current State
- Stream URL: https://radio.clintecker.com/radio
- Format: Headerless raw PCM (s16le, 44100Hz, stereo)
- Bandwidth: 176 KB/s
- Player compatibility: Requires explicit format specification
- Infrastructure: All components operational (Icecast, Liquidsoap, systemd, Cloudflare tunnel)

### Why This Happened

OPAM's Liquidsoap package architecture:
1. Base `liquidsoap` package provides core functionality
2. Encoder support comes from separate packages (mad, lame, ffmpeg)
3. System libraries (libmp3lame-dev) are prerequisites but not sufficient
4. Encoders must be explicitly installed after base package

This is by design (modularity) but wasn't documented in Phase 1 plan.

---

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION FLOW                       │
└─────────────────────────────────────────────────────────────┘

Step 1: Install Encoder Packages
    ↓
[GATE 1] Verify encoders available
    ↓ (pass)
Step 2: Update Configuration
    ↓
[GATE 2] Syntax check passes
    ↓ (pass)
Step 3: Apply Changes
    ↓
[GATE 3] Verify stream format
    ↓ (pass)
SUCCESS: MP3 stream operational

(fail) → Contingency Plans A-D
```

**Critical Gates:**
- Gate 1: Prevents configuration changes without encoder support
- Gate 2: Prevents bad config from taking service offline
- Gate 3: Confirms actual stream output is correct

---

## Task 1 (REVISED): Encoder Package Installation

### Purpose
Install OPAM encoder packages to provide MP3 encoding support.

### Prerequisites
- VM accessible: 10.10.0.86 / 100.85.213.117
- Phase 1 Tasks 1-4 already completed
- Base Liquidsoap 2.4.0 already installed via OPAM
- System encoder libraries already installed

### Implementation

**Step 1: Switch to ai-radio user**

```bash
sudo -i -u ai-radio
cd /srv/ai_radio
```

**Step 2: Verify OPAM environment**

```bash
eval $(opam env)
opam --version  # Should show OPAM version
which liquidsoap  # Should show /srv/ai_radio/.opam/5.2.0/bin/liquidsoap
```

**Step 3: Install encoder packages** (CRITICAL - THIS WAS MISSING)

```bash
opam install -y mad lame ffmpeg taglib flac
```

Expected: All packages install successfully

**What these provide:**
- `mad` - MP3 decoding support (reads MP3 files)
- `lame` - MP3 encoding support (creates %mp3 encoder)
- `ffmpeg` - FFmpeg integration (versatile encoding/decoding)
- `taglib` - Metadata reading (ID3, Vorbis comments)
- `flac` - FLAC encoding/decoding

**If installation fails:**
- Individual failures for `taglib` or `flac` are acceptable (optional)
- `mad` and `lame` are REQUIRED - if either fails, STOP and execute Contingency Plan A
- Error "no package named X" → Execute Contingency Plan A immediately

**Step 4: Verify encoder availability** (CRITICAL - THIS WAS MISSING)

```bash
liquidsoap --list-plugins | grep -E "mp3|lame|mad|ffmpeg"
```

**Expected output must include:**
```
%mp3           - MP3 encoder
mad            - MAD MP3 decoder
ffmpeg         - FFmpeg decoder/encoder
```

**If verification fails:**
- `%mp3` not listed → Encoder installation failed, execute Contingency Plan B
- `mad` not listed → Decoder installation failed, execute Contingency Plan B
- Both missing → Execute Contingency Plan A (switch to Debian packages)

**Step 5: Verify Liquidsoap version**

```bash
liquidsoap --version
```

Expected: Should still show Liquidsoap 2.4.0 (or 2.4.x)

**Step 6: Exit ai-radio user**

```bash
exit
```

**Verification:**
```bash
sudo -u ai-radio bash -c 'eval $(opam env) && liquidsoap --list-plugins | grep mp3'
```

Expected: Should show `%mp3` encoder

**Note for Future:** This step should be added to Phase 1 Task 1 after line 68 (after base Liquidsoap installation).

---

## Task 5 (REVISED): Liquidsoap Configuration with MP3 Encoding

### Purpose
Configure Liquidsoap to stream in MP3 format using newly installed encoders.

### Prerequisites
- Task 1 REVISED completed (encoders installed and verified)
- Original Phase 1 Tasks 2-4 completed (Icecast, safety assets, wrapper script)
- Stream currently operational with WAV format

### Files
- Modify: `/srv/ai_radio/config/radio.liq`

### Implementation

**Step 1: Backup current working configuration**

```bash
sudo cp /srv/ai_radio/config/radio.liq /srv/ai_radio/config/radio.liq.backup-wav
sudo ls -lh /srv/ai_radio/config/radio.liq*
```

Expected: Both files exist

**Why:** Current config works (streaming, fallback, normalization all operational). Keep it for rollback if MP3 config has issues.

**Step 2: Update radio.liq with MP3 encoding**

```bash
sudo nano /srv/ai_radio/config/radio.liq
```

Complete configuration:

```liquidsoap
#!/usr/bin/env liquidsoap

# AI Radio Station - Liquidsoap Configuration
# Phase 1: MP3 Streaming with Fallback Chain

# =============================================================================
# Logging Configuration
# =============================================================================

log.level.set(3)  # Info level (4=debug, 3=info, 2=warning, 1=error)
log.file.set(true)
log.file.path.set("/srv/ai_radio/logs/liquidsoap.log")

# =============================================================================
# Icecast Configuration
# =============================================================================

# Read Icecast password from secrets file
icecast_password_file = "/srv/ai_radio/.icecast_secrets"
def icecast_password() =
  list.hd(default="", file.lines(icecast_password_file))
end

icecast_host = "127.0.0.1"
icecast_port = 8000

# =============================================================================
# Station Metadata
# =============================================================================

station_name = "AI Radio Station"
station_description = "24/7 AI-Powered Radio Stream"
station_genre = "Various"
station_url = "https://radio.clintecker.com"

# =============================================================================
# Audio Sources
# =============================================================================

# Emergency safety tone (last resort fallback)
emergency_tone = single("/srv/ai_radio/assets/safety/safety_tone.wav")

# Safety playlist (evergreen content, fallback when no other source)
safety_playlist = playlist(
  mode="randomize",
  reload=3600,
  "/srv/ai_radio/assets/safety/evergreen.m3u"
)

# =============================================================================
# Fallback Chain
# =============================================================================

# Fallback order: safety_playlist -> emergency_tone
# track_sensitive=false means it switches immediately if source fails
radio = fallback(
  track_sensitive=false,
  [safety_playlist, emergency_tone]
)

# =============================================================================
# Audio Processing
# =============================================================================

# Normalize audio to -18 LUFS target, -1.0 dBTP true peak
radio = normalize(
  target=-18.0,
  threshold=-40.0,
  radio
)

# =============================================================================
# Icecast Output - MP3 Format
# =============================================================================

output.icecast(
  %mp3(bitrate=192, samplerate=44100, stereo=true),
  host=icecast_host,
  port=icecast_port,
  password=icecast_password(),
  mount="/radio",
  name=station_name,
  description=station_description,
  genre=station_genre,
  url=station_url,
  radio
)
```

**Key change:** Line with `output.icecast` now uses:
```liquidsoap
%mp3(bitrate=192, samplerate=44100, stereo=true)
```

Instead of previous:
```liquidsoap
%wav(stereo=true, samplerate=44100)
```

**Step 3: Verify configuration syntax** (CRITICAL)

```bash
sudo -u ai-radio bash -c 'eval $(opam env) && liquidsoap --check /srv/ai_radio/config/radio.liq'
```

**Expected:** "OK" or no error messages

**If check fails:**
- Error mentions "mp3" or "lame" or "unsupported format" → Encoder installation issue, return to Task 1 verification
- Syntax error (line number, unexpected token) → Configuration syntax issue, review error and fix
- Other error → Review error message carefully before proceeding

**Do not proceed if check fails** - fix errors first or execute Contingency Plan C

**Step 4: Test configuration in foreground** (OPTIONAL but RECOMMENDED)

```bash
sudo systemctl stop ai-radio-liquidsoap
sudo -u ai-radio bash -c 'cd /srv/ai_radio && eval $(opam env) && liquidsoap config/radio.liq'
```

Watch output for:
- ✓ Log initialization messages
- ✓ "Output started" message for Icecast mount
- ✓ No encoder errors
- ✓ Stream connects successfully

Press Ctrl+C after ~10 seconds if no errors appear.

**Skip this step if:**
- Very confident in configuration check
- Need to minimize downtime
- Already tested similar config

**Step 5: Restart Liquidsoap service with new configuration**

```bash
sudo systemctl restart ai-radio-liquidsoap
```

**Step 6: Verify service is running**

```bash
sudo systemctl status ai-radio-liquidsoap
```

Expected:
- Status: "active (running)" in green
- No error messages in recent logs
- "Output started" in log output

**If service fails:**
```bash
journalctl -u ai-radio-liquidsoap -n 50
```

Review logs, execute rollback if necessary.

**Step 7: Verify stream format**

```bash
# Check stream headers
curl -I https://radio.clintecker.com/radio

# Check stream format and bandwidth (10 second test)
timeout 10s curl -s https://radio.clintecker.com/radio | wc -c
```

**Expected:**
- HTTP/2 200 OK
- Content-Type: audio/mpeg (NOT application/octet-stream)
- Bytes received: ~24,000-30,000 (192 kbps = 24,000 bytes/second)

**Current broken format shows:**
- Content-Type: application/octet-stream
- Bytes received: ~176,000 (raw PCM at 44.1kHz * 2 channels * 2 bytes)

**If wrong format:**
- Check Liquidsoap logs for encoder errors
- Execute Contingency Plan D

**Step 8: Test with standard audio player**

```bash
ffplay https://radio.clintecker.com/radio
```

**Expected:**
- Audio plays immediately
- No format detection warnings
- Sound is clear and correct

**Current broken format requires:**
```bash
ffplay -f s16le -ar 44100 -ac 2 https://radio.clintecker.com/radio
```

If this is still required, MP3 encoding is not working → Execute Contingency Plan D

**Step 9: Listen and verify audio quality**

Play for 30-60 seconds and verify:
- Audio sounds correct (music/tones play properly)
- No distortion or artifacts
- Volume seems normalized
- Transitions between tracks work

**Commit:**
```bash
cd /Users/clint/code/clintecker/clanker-radio
git add config/radio.liq
git commit -m "fix: enable MP3 encoding for stream output

- Configure %mp3 encoder (192kbps, 44.1kHz, stereo)
- Resolves headerless PCM issue from Phase 1 implementation
- Reduces bandwidth from 176 KB/s to 24 KB/s
- Enables standard player compatibility

Requires: OPAM encoder packages (mad, lame) installed per Task 1 revision"
```

---

## Contingency Plans

### Contingency Plan A: OPAM Encoder Packages Don't Exist

**Trigger:** `opam install mad lame` fails with "no package named mad/lame" or similar error

**Decision:** Switch from OPAM to Debian packages

**Implementation:**

```bash
# Stop Liquidsoap service
sudo systemctl stop ai-radio-liquidsoap

# Switch to ai-radio user and remove OPAM Liquidsoap
sudo -i -u ai-radio
eval $(opam env)
opam remove liquidsoap
exit

# Install Liquidsoap from Debian repository
sudo apt-get update
sudo apt-get install -y liquidsoap liquidsoap-plugin-all

# Verify installation
liquidsoap --version  # Will show 2.1.x or 2.2.x (older than 2.4.0)
liquidsoap --list-plugins | grep mp3  # Should show MP3 encoder

# Update wrapper script to use system Liquidsoap
sudo nano /srv/ai_radio/bin/liquidsoap-wrapper.sh
```

**Changes to wrapper script:**

```bash
# BEFORE:
LIQUIDSOAP_BIN="/srv/ai_radio/.opam/5.2.0/bin/liquidsoap"

# AFTER:
LIQUIDSOAP_BIN="/usr/bin/liquidsoap"

# ALSO: Remove or comment out all OPAM environment variables:
# - OPAM_SWITCH_PREFIX
# - CAML_LD_LIBRARY_PATH
# - OCAML_TOPLEVEL_PATH
# - PATH modification
# - MANPATH modification
```

**Restart service:**
```bash
sudo systemctl restart ai-radio-liquidsoap
sudo systemctl status ai-radio-liquidsoap
```

**Verify stream:**
```bash
curl -I https://radio.clintecker.com/radio
timeout 10s curl -s https://radio.clintecker.com/radio | wc -c
```

**Trade-offs:**
- ✓ Get MP3 encoding support (primary goal)
- ✓ Well-tested, stable Debian packages
- ✓ All encoders included by default (mp3, ogg, flac, etc.)
- ✗ Downgrade from Liquidsoap 2.4.0 to 2.1.x or 2.2.x
- ✗ May have slightly different syntax (though 2.1+ is mostly compatible)
- ✗ Lose OPAM package management benefits (easy updates to latest)

**Configuration adjustments that may be needed for Liquidsoap 2.1:**
- Encoder syntax might use `samplerate` instead of `samplerate` parameter
- Some newer 2.4 features may not be available
- Check configuration with `liquidsoap --check` after switch

**When to use:** If OPAM encoder packages genuinely don't exist or consistently fail to install.

---

### Contingency Plan B: Encoders Install But Don't Work

**Trigger:** After `opam install mad lame`, verification shows no `%mp3` encoder:
```bash
liquidsoap --list-plugins | grep mp3  # Returns nothing
```

**Possible Causes:**
1. OPAM environment not properly loaded during verification
2. System libraries missing or incompatible version
3. Packages installed but not linked/built correctly
4. OCaml version incompatibility

**Investigation Steps:**

**Step 1: Verify OPAM environment**
```bash
sudo -i -u ai-radio
eval $(opam env)

# Check OPAM is working
opam --version
opam switch

# Check packages are actually installed
opam list | grep -E "mad|lame|ffmpeg"
```

Expected: Should show mad, lame, and ffmpeg packages with version numbers

**Step 2: Verify system libraries are accessible**
```bash
ldconfig -p | grep -E "libmp3lame|libmad"
```

Expected:
```
libmp3lame.so.0 (libc6,x86-64) => /usr/lib/x86_64-linux-gnu/libmp3lame.so.0
libmad.so.0 (libc6,x86-64) => /usr/lib/x86_64-linux-gnu/libmad.so.0
```

If libraries are missing:
```bash
sudo apt-get install -y libmp3lame0 libmad0
```

**Step 3: Rebuild Liquidsoap with encoder support**
```bash
# Still as ai-radio user with OPAM env loaded
opam reinstall liquidsoap

# This will rebuild Liquidsoap against the installed encoder packages
```

**Step 4: Verify again**
```bash
liquidsoap --list-plugins | grep -E "mp3|lame|mad"
```

**If still fails after reinstall:**
- Check OPAM logs for build errors: `opam install liquidsoap --verbose`
- Check OCaml version compatibility: `ocaml --version` (should be 4.x or 5.x)
- Consider executing Contingency Plan A (switch to Debian packages)

**When to use:** When packages appear to install but encoders aren't available in Liquidsoap.

---

### Contingency Plan C: MP3 Configuration Syntax Errors

**Trigger:** `liquidsoap --check radio.liq` fails with syntax error related to MP3 encoder

**Possible Causes:**
1. Liquidsoap 2.4 changed encoder parameter names
2. Encoder syntax different than documentation
3. Typo in configuration

**Investigation and Fixes:**

**Try Alternative Syntax 1: channels instead of stereo**
```liquidsoap
output.icecast(
  %mp3(bitrate=192, samplerate=44100, channels=2),
  # ... rest of parameters
)
```

Test: `liquidsoap --check /srv/ai_radio/config/radio.liq`

**Try Alternative Syntax 2: Explicit CBR mode**
```liquidsoap
output.icecast(
  %mp3.cbr(bitrate=192, samplerate=44100, stereo=true),
  # ... rest of parameters
)
```

Test: `liquidsoap --check /srv/ai_radio/config/radio.liq`

**Try Alternative Syntax 3: FFmpeg-based MP3 encoder**
```liquidsoap
output.icecast(
  %ffmpeg(
    format="mp3",
    %audio(
      codec="libmp3lame",
      b="192k",
      samplerate=44100,
      channels=2
    )
  ),
  # ... rest of parameters
)
```

Test: `liquidsoap --check /srv/ai_radio/config/radio.liq`

**Try Alternative Syntax 4: Minimal parameters**
```liquidsoap
output.icecast(
  %mp3(bitrate=192),
  # ... rest of parameters
)
```

Let Liquidsoap use defaults for samplerate and channels.

**Debugging approach:**
1. Start with minimal syntax
2. Add parameters one at a time
3. Test with `--check` after each addition
4. Identify which parameter causes failure

**Check Liquidsoap 2.4 documentation:**
```bash
liquidsoap --help-encoder mp3
```

This will show the exact syntax and parameters supported.

**When to use:** When encoders are installed and verified, but configuration syntax doesn't work.

---

### Contingency Plan D: Stream Still Wrong Format After Changes

**Trigger:** After all changes applied, stream still shows:
- Content-Type: application/octet-stream (not audio/mpeg)
- Bandwidth: ~176,000 bytes in 10 seconds (not ~24,000)

**Investigation Steps:**

**Step 1: Check Liquidsoap is actually using new configuration**
```bash
sudo systemctl status ai-radio-liquidsoap
ps aux | grep liquidsoap
```

Verify process is running and using correct config file: `/srv/ai_radio/config/radio.liq`

**Step 2: Check Liquidsoap logs for encoder errors**
```bash
sudo tail -50 /srv/ai_radio/logs/liquidsoap.log
```

Look for:
- "unsupported format" errors → Encoder not available, return to Contingency Plan B
- "encoder initialization failed" → Encoder syntax issue, return to Contingency Plan C
- "Output started" for /radio mount → Good, encoder initialized
- Mention of which encoder is being used

**Step 3: Check what Liquidsoap is actually sending to Icecast**
```bash
# Check Icecast mount point info
curl http://localhost:8000/admin/listmounts.xsl \
  -u admin:$(sudo grep '<admin-password>' /etc/icecast2/icecast.xml | sed -E 's/.*<admin-password>([^<]+)<.*/\1/')
```

Look for /radio mount, check reported format/codec.

**Step 4: Test direct connection to Liquidsoap output**

Stop Icecast temporarily to isolate issue:
```bash
sudo systemctl stop icecast2
```

Check if Liquidsoap reports connection error (it should):
```bash
journalctl -u ai-radio-liquidsoap -n 20
```

Start Icecast:
```bash
sudo systemctl start icecast2
```

Watch Liquidsoap logs for reconnection:
```bash
tail -f /srv/ai_radio/logs/liquidsoap.log
```

**Step 5: Verify OPAM environment in systemd service**

Check that wrapper script is being used:
```bash
sudo systemctl cat ai-radio-liquidsoap
```

Should show: `ExecStart=/srv/ai_radio/bin/liquidsoap-wrapper.sh`

Verify wrapper script loads OPAM environment:
```bash
cat /srv/ai_radio/bin/liquidsoap-wrapper.sh
```

Should have `eval $(opam env)` or explicit OPAM environment variables.

**Step 6: Test configuration manually with OPAM environment**
```bash
sudo -i -u ai-radio
cd /srv/ai_radio
eval $(opam env)
liquidsoap --check config/radio.liq  # Should pass
liquidsoap config/radio.liq  # Run in foreground
# Watch output, press Ctrl+C after confirming no encoder errors
```

**Common Issues and Solutions:**

**Issue:** Logs show "Output started" but format is still wrong
**Solution:** Icecast might be caching metadata. Restart Icecast:
```bash
sudo systemctl restart icecast2
sudo systemctl restart ai-radio-liquidsoap
```

**Issue:** Encoder errors in logs
**Solution:** Return to Contingency Plan B (encoder installation verification)

**Issue:** Syntax errors in logs
**Solution:** Return to Contingency Plan C (try alternative syntax)

**When to use:** When all previous steps succeeded but stream format is still incorrect.

---

## Verification Checklist

After implementation, ALL items in this checklist must pass before declaring success:

### Installation Verification

```bash
# Switch to ai-radio user
sudo -i -u ai-radio
eval $(opam env)

# Verify encoder packages installed
opam list | grep -E "mad|lame"
```
- [ ] `mad` package listed with version number
- [ ] `lame` package listed with version number

```bash
# Verify encoder availability in Liquidsoap
liquidsoap --list-plugins | grep mp3
```
- [ ] `%mp3` encoder shown in output

```bash
# Verify Liquidsoap version
liquidsoap --version
```
- [ ] Shows version 2.4.x (not downgraded)

```bash
exit  # Return to ubuntu user
```

### Configuration Verification

```bash
# Verify configuration syntax
sudo -u ai-radio bash -c 'eval $(opam env) && liquidsoap --check /srv/ai_radio/config/radio.liq'
```
- [ ] Returns "OK" or no error messages

```bash
# Verify backup exists
ls -lh /srv/ai_radio/config/radio.liq*
```
- [ ] `radio.liq.backup-wav` exists

```bash
# Verify configuration uses MP3 encoder
grep "%mp3" /srv/ai_radio/config/radio.liq
```
- [ ] Shows `%mp3(bitrate=192, samplerate=44100, stereo=true)` or similar

### Service Verification

```bash
# Check service status
sudo systemctl status ai-radio-liquidsoap
```
- [ ] Status shows "active (running)" in green
- [ ] No error messages in status output

```bash
# Check recent service logs
journalctl -u ai-radio-liquidsoap -n 50
```
- [ ] No error messages
- [ ] Shows "Output started" for Icecast

```bash
# Check Liquidsoap application logs
sudo tail -30 /srv/ai_radio/logs/liquidsoap.log
```
- [ ] No encoder errors
- [ ] Shows successful Icecast connection

### Stream Format Verification

```bash
# Check stream HTTP headers
curl -I https://radio.clintecker.com/radio
```
- [ ] HTTP status: 200 OK
- [ ] Content-Type: `audio/mpeg` (NOT `application/octet-stream`)
- [ ] Icecast headers present

```bash
# Check stream bandwidth (10 second test)
timeout 10s curl -s https://radio.clintecker.com/radio | wc -c
```
- [ ] Bytes received: 24,000-30,000 (NOT ~176,000)
- [ ] Calculates to approximately 192 kbps

```bash
# Test with standard audio player
ffplay https://radio.clintecker.com/radio
```
- [ ] Audio plays immediately without errors
- [ ] No format detection warnings in output
- [ ] No need to specify format with `-f`, `-ar`, `-ac` flags

### Audio Quality Verification

Listen to stream for 30-60 seconds:
- [ ] Audio sounds correct (music/tones play properly)
- [ ] No distortion, crackling, or artifacts
- [ ] Volume seems normalized (not too quiet or too loud)
- [ ] Transitions between tracks are smooth

### Functionality Preservation

```bash
# Verify fallback chain still works
# Temporarily rename safety playlist to test fallback
sudo mv /srv/ai_radio/assets/safety/evergreen.m3u /srv/ai_radio/assets/safety/evergreen.m3u.test
sleep 5
# Should hear emergency tone instead of playlist
# Restore playlist
sudo mv /srv/ai_radio/assets/safety/evergreen.m3u.test /srv/ai_radio/assets/safety/evergreen.m3u
```
- [ ] Emergency tone played when playlist unavailable
- [ ] Returned to playlist after restoration

### Documentation

- [ ] `/tmp/phase1-status.md` updated to reflect resolution
- [ ] Commit created with encoding fix
- [ ] Implementation notes documented

---

## Rollback Procedures

If problems occur during implementation, use these procedures to return to the previous working state:

### Rollback During Encoder Installation

If encoder installation fails or causes issues:

```bash
# Switch to ai-radio user
sudo -i -u ai-radio
eval $(opam env)

# Remove encoder packages
opam remove mad lame ffmpeg taglib flac

# Verify base Liquidsoap still works
liquidsoap --version
liquidsoap --list-plugins  # Will show basic encoders only

exit
```

**Result:** System returns to Phase 1 state with WAV format. Stream continues to work (though with wrong format).

**Note:** This doesn't fix the encoding issue, but ensures system remains operational.

### Rollback After Configuration Update

If MP3 configuration causes problems:

```bash
# Stop service
sudo systemctl stop ai-radio-liquidsoap

# Restore backup configuration
sudo cp /srv/ai_radio/config/radio.liq.backup-wav /srv/ai_radio/config/radio.liq

# Verify backup restored
grep "%wav" /srv/ai_radio/config/radio.liq  # Should show WAV encoder

# Restart service
sudo systemctl start ai-radio-liquidsoap

# Verify service running
sudo systemctl status ai-radio-liquidsoap

# Verify stream accessible (even if wrong format)
curl -I https://radio.clintecker.com/radio
```

**Result:** Stream returns to headerless PCM format but remains operational.

### Complete Rollback (Nuclear Option)

If everything fails and system is broken:

```bash
# Stop services
sudo systemctl stop ai-radio-liquidsoap
sudo systemctl stop icecast2

# Restore configuration backup
sudo cp /srv/ai_radio/config/radio.liq.backup-wav /srv/ai_radio/config/radio.liq

# Remove encoder packages if they cause issues
sudo -i -u ai-radio
eval $(opam env)
opam remove mad lame ffmpeg taglib flac
exit

# Restart services
sudo systemctl start icecast2
sudo systemctl start ai-radio-liquidsoap

# Verify both running
sudo systemctl status icecast2
sudo systemctl status ai-radio-liquidsoap

# Test stream
curl -I https://radio.clintecker.com/radio
```

**Result:** Complete return to Phase 1 completion state with WAV format.

**When to use:**
- Multiple contingency plans failed
- System is not streaming at all
- Need operational stream immediately while investigating
- Planning to switch to Contingency Plan A (Debian packages) in next attempt

---

## Success Criteria Summary

**Implementation is COMPLETE when ALL of these pass:**

1. **Encoders verified**
   - `opam list` shows `mad` and `lame` packages
   - `liquidsoap --list-plugins` shows `%mp3` encoder
   - Version remains 2.4.x

2. **Configuration correct**
   - Syntax check passes
   - Uses `%mp3` encoder
   - Backup exists

3. **Service operational**
   - systemd shows "active (running)"
   - No errors in logs
   - Icecast connection established

4. **Stream format correct**
   - Content-Type: audio/mpeg
   - Bandwidth: ~24 KB/s (not 176 KB/s)
   - Standard players work without format specification

5. **Quality maintained**
   - Audio sounds correct
   - No distortion or artifacts
   - Fallback chain works
   - Normalization applied

6. **Documentation updated**
   - Phase 1 status updated
   - Changes committed to git
   - Lessons learned documented

**Only when ALL criteria pass:** Phase 1 is truly complete and ready for Phase 2 (Asset Management).

---

## Post-Implementation Actions

### Immediate (Within 1 Hour)

1. **Monitor service stability**
   ```bash
   # Watch logs for errors
   sudo journalctl -u ai-radio-liquidsoap -f
   ```

2. **Verify public access**
   ```bash
   # Test from external location (not VM)
   curl -I https://radio.clintecker.com/radio
   ffplay https://radio.clintecker.com/radio
   ```

3. **Document actual bandwidth**
   ```bash
   # 60 second test
   timeout 60s curl -s https://radio.clintecker.com/radio | wc -c
   # Should be ~144,000 bytes (192 kbps * 60 seconds / 8 bits per byte)
   ```

### Short-term (Within 24 Hours)

1. **Monitor for 24 hours**
   - Check service hasn't crashed
   - Verify no memory leaks
   - Confirm no encoding errors in logs

2. **Update Phase 1 status document**
   ```bash
   # Update /tmp/phase1-status.md
   # Change status from "Audio Format Issue" to "Audio Format: RESOLVED"
   ```

3. **Create troubleshooting documentation**
   ```bash
   # Document at docs/troubleshooting/liquidsoap-encoders.md
   # Include: OPAM encoder architecture, verification steps, common issues
   ```

### Medium-term (Within 1 Week)

1. **Gather listener feedback** (if applicable)
   - Stream quality
   - Compatibility with their players
   - Audio quality assessment

2. **Document bandwidth usage**
   - Average bandwidth per listener
   - Total bandwidth compared to previous PCM format
   - Cost implications (if relevant)

3. **Consider enhancements**
   - Variable bitrate (VBR) MP3 for better quality
   - Additional format outputs (Ogg Vorbis, AAC)
   - Bitrate optimization based on usage

4. **Prepare for Phase 2**
   - Review Phase 2 plan (Asset Management)
   - Ensure encoding is stable before adding complexity
   - Plan integration of real music tracks with MP3 encoding

---

## Lessons Learned

### What Went Wrong

1. **Assumption about OPAM packages:** Original plan assumed installing system libraries would provide encoder support. OPAM's modular architecture requires explicit encoder package installation.

2. **Missing verification step:** No verification of encoder availability after installation. Should have checked `liquidsoap --list-plugins` immediately.

3. **Documentation gap:** OPAM encoder architecture not documented in Phase 1 plan. Future plans should include architecture notes for critical dependencies.

### What Went Right

1. **Infrastructure design:** Fallback to WAV format kept stream operational despite encoding issue. Good safety design.

2. **Systemd service:** Service remained stable throughout investigation. Wrapper script design was correct.

3. **Modularity:** Issue isolated to encoding layer. Didn't affect Icecast, systemd, or networking.

### Best Practices Identified

1. **Always verify encoder availability:**
   ```bash
   liquidsoap --list-plugins | grep <encoder-name>
   ```

2. **Test configuration before applying:**
   ```bash
   liquidsoap --check <config-file>
   ```

3. **Backup working configurations:**
   ```bash
   cp config.liq config.liq.backup-$(date +%Y%m%d)
   ```

4. **Document package architecture:** When using modular systems (OPAM, Python packages, etc.), document the relationship between base packages and optional components.

5. **Gate critical changes:** Use verification gates between installation and configuration phases.

### Recommendations for Future Phases

1. **Include verification steps in all plans:** Every installation should have explicit verification of what was installed.

2. **Document assumptions:** If plan assumes something works, state it explicitly and verify it.

3. **Test in isolation:** When possible, test components independently before integration.

4. **Plan for rollback:** Every change should have a documented rollback procedure.

5. **Use staging when possible:** For critical changes, test in staging environment first (not applicable here, but good practice).

---

## Related Documentation

- **Original Plan:** `docs/plans/2025-12-18-phase-1-core-infrastructure.md`
- **Phase 1 Status:** `/tmp/phase1-status.md`
- **Liquidsoap Documentation:** https://www.liquidsoap.info/doc-2.4.0/
- **OPAM Documentation:** https://opam.ocaml.org/doc/Manual.html
- **Icecast Documentation:** https://icecast.org/docs/

---

## Implementation Checklist

Use this checklist during implementation:

- [ ] Read entire plan before starting
- [ ] Ensure VM is accessible
- [ ] Verify Phase 1 infrastructure is operational
- [ ] Execute Task 1 REVISED: Install encoder packages
- [ ] Verify encoders available (GATE 1)
- [ ] Execute Task 5 REVISED: Update configuration
- [ ] Syntax check passes (GATE 2)
- [ ] Restart service
- [ ] Verify stream format (GATE 3)
- [ ] Complete verification checklist
- [ ] Update documentation
- [ ] Monitor for 24 hours
- [ ] Declare Phase 1 complete

**Ready for Phase 2:** Asset Management (track ingestion, metadata, database integration)
