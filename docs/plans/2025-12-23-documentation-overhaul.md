# Documentation Overhaul Plan

**Date:** 2025-12-23
**Status:** Planning
**Target Audience:** Intermediate users (comfortable with Linux, Python, command line)

## Goals

Transform the current documentation into a comprehensive, well-organized guide system that takes users from "I have SSH access to a server" to "I'm running a fully customized AI radio station."

## Structure

**Approach:** Separate focused guides with extensive cross-linking

**Critical Path (VM-first):**
1. VM Setup → 2. Configuration → 3. Deployment → 4. Administration

This order assumes users are starting from scratch with just SSH + sudo access.

## Core Documents

### README.md (Project Hub)
**Purpose:** Entry point and quick navigation hub

**Contents:**
- Project overview (what is this?)
- Feature highlights
- Quick links to all guides
- Prerequisites checklist
- Community/support links

**Cross-links:** Links to every other doc

---

### docs/VM_SETUP.md
**Purpose:** From bare Ubuntu server to production-ready environment

**Starting Assumption:** User has SSH access + sudo privileges to an Ubuntu 24.04 machine (cloud VM, bare metal, homelab - doesn't matter)

**Contents:**

1. **Prerequisites Verification**
   - OS version check
   - Network connectivity
   - Disk space requirements
   - Memory requirements

2. **System Package Installation**
   - APT updates and essential packages
   - OPAM (OCaml package manager for Liquidsoap)
   - FFmpeg for audio processing
   - Icecast2 for streaming
   - Nginx for web serving
   - SQLite for database
   - Python 3.12+ and uv for Python package management
   - Context: Why each package, what it does in the system

3. **User and Directory Setup**
   - Create ai-radio user (if needed)
   - Set up /srv/ai_radio directory structure
   - Permissions and ownership
   - Context: Security isolation, why /srv/ai_radio

4. **Liquidsoap Installation**
   - OPAM environment setup
   - Liquidsoap compilation with required modules
   - Verification steps
   - Deep dive: Why compile Liquidsoap vs system package

5. **Service User Configuration**
   - Create systemd service user
   - Set up proper permissions
   - Security considerations

6. **Firewall Configuration**
   - Open required ports (8000 for Icecast, 80/443 for web)
   - Security best practices
   - Context: What each port is for

7. **SSL/TLS Setup (Optional)**
   - Certbot installation
   - Certificate generation
   - Auto-renewal configuration
   - Context: When you need this, when you don't

8. **Verification Checklist**
   - [ ] All packages installed
   - [ ] Liquidsoap compiles and runs
   - [ ] Directories created with correct permissions
   - [ ] Firewall configured
   - [ ] System ready for code deployment

**Style:** Step-by-step with context explanations. Occasional deep dives on architectural decisions (like why Liquidsoap over alternatives).

**Cross-links:**
- Next: CONFIGURATION.md (configure your station)
- Related: DEPLOYMENT.md (getting code onto this server)

---

### docs/CONFIGURATION.md
**Purpose:** Complete guide to all 100+ environment variables, organized by function

**Contents:**

1. **Configuration Overview**
   - How configuration works (.env files)
   - Station-specific vs generic configs
   - The .env.example file (tropical island template)
   - Context: Configuration-driven architecture philosophy

2. **Base Configuration**
   - `RADIO_BASE_PATH` - Installation directory
   - `RADIO_STATION_TZ` - Timezone
   - Context: Why these matter, how they're used

3. **Station Identity**
   - `RADIO_STATION_NAME` - Your station's name
   - `RADIO_STATION_LOCATION` - Location for weather/identity
   - `RADIO_STATION_LAT/LON` - Coordinates for weather data
   - Context: These appear in streams, IDs, metadata

4. **API Keys**
   - `RADIO_LLM_API_KEY` - Anthropic API key for Claude
   - `RADIO_LLM_MODEL` - Which Claude model to use
   - `RADIO_GEMINI_API_KEY` - Google Gemini for TTS
   - `RADIO_GEMINI_TTS_MODEL` - TTS model selection
   - `RADIO_GEMINI_TTS_VOICE` - Voice selection (Kore, Puck, etc.)
   - Context: Cost considerations, model selection trade-offs
   - Deep dive: Why Claude for script generation, Gemini for TTS

5. **Weather Configuration**
   - `RADIO_NWS_OFFICE` - National Weather Service office code
   - `RADIO_NWS_GRID_X/Y` - Grid coordinates
   - `RADIO_WEATHER_SCRIPT_TEMPERATURE` - LLM creativity for weather
   - Context: How to find your NWS grid, why temperature matters

6. **News Configuration**
   - `RADIO_NEWS_RSS_FEEDS` - JSON structure of RSS feeds
   - `RADIO_NEWS_SCRIPT_TEMPERATURE` - LLM creativity for news
   - `RADIO_HALLUCINATE_NEWS` - Enable fake news mixing
   - `RADIO_HALLUCINATION_CHANCE` - Probability of fake news
   - `RADIO_HALLUCINATION_KERNELS` - Seed topics for fake news
   - Context: RSS feed categories, why mix real/fake news
   - Deep dive: Building a compelling news landscape

7. **World-Building**
   - `RADIO_WORLD_SETTING` - Your universe (dystopia, paradise, etc.)
   - `RADIO_WORLD_TONE` - Emotional vibe
   - `RADIO_WORLD_FRAMING` - How to filter content through your world
   - Context: Creating consistent station personality
   - Examples: Tropical paradise vs cyberpunk dystopia

8. **Announcer Personality**
   - `RADIO_ANNOUNCER_NAME` - DJ persona name
   - `RADIO_ENERGY_LEVEL` (1-10) - Enthusiasm level
   - `RADIO_VIBE_KEYWORDS` - 3-5 personality keywords
   - `RADIO_MAX_RIFFS_PER_BREAK` - Chaos budget
   - `RADIO_MAX_EXCLAMATIONS_PER_BREAK` - Enthusiasm limit
   - `RADIO_UNHINGED_PERCENTAGE` - % of segment that can be wild
   - Context: Balancing personality with listenability

9. **Humor & Style Guardrails**
   - `RADIO_HUMOR_PRIORITY` - Humor type ranking
   - `RADIO_ALLOWED_COMEDY` - What comedy devices to use
   - `RADIO_BANNED_COMEDY` - What to avoid (meme recitation, etc.)
   - `RADIO_UNHINGED_TRIGGERS` - When to go wild
   - Context: Preventing AI cringe, maintaining authenticity
   - Deep dive: Why these guardrails exist (learned from testing)

10. **Anti-Robot Authenticity Rules**
    - `RADIO_SENTENCE_LENGTH_TARGET` - Natural rhythm
    - `RADIO_MAX_ADJECTIVES_PER_SENTENCE` - Avoid purple prose
    - `RADIO_NATURAL_DISFLUENCY` - Conversational fillers
    - `RADIO_BANNED_AI_PHRASES` - Telltale AI phrases to avoid
    - Context: Making AI sound human
    - Deep dive: Common AI writing patterns to avoid

11. **Weather Style**
    - `RADIO_WEATHER_STRUCTURE` - How to structure weather reports
    - `RADIO_WEATHER_TRANSLATION_RULES` - Translating technical to conversational
    - Context: Varying weather delivery, avoiding templates

12. **News Style**
    - `RADIO_NEWS_TONE` - Normal vs serious mode triggers
    - `RADIO_NEWS_FORMAT` - Story treatment variation
    - Context: Ethical boundaries, credibility guardrails

13. **Vocal/Accent Characteristics**
    - `RADIO_ACCENT_STYLE` - Accent description for TTS
    - `RADIO_DELIVERY_STYLE` - Pacing and rhythm
    - Context: Subtle personality cues

14. **Radio Fundamentals**
    - `RADIO_RADIO_RESETS` - Station ID and time reference requirements
    - `RADIO_LISTENER_RELATIONSHIP` - Tone with audience
    - Context: Professional radio best practices

15. **Audio Settings**
    - `RADIO_BED_VOLUME_DB` - Background music volume
    - `RADIO_BED_PREROLL_SECONDS` - Lead-in time
    - `RADIO_BED_FADEIN_SECONDS` - Fade-in duration
    - `RADIO_BED_POSTROLL_SECONDS` - Lead-out time
    - `RADIO_BED_FADEOUT_SECONDS` - Fade-out duration
    - `RADIO_BREAK_FRESHNESS_MINUTES` - Break reuse threshold
    - Context: Professional mixing, why these values

16. **Liquidsoap Environment Variables**
    - `LIQUIDSOAP_STATION_NAME` - Stream metadata
    - `LIQUIDSOAP_STATION_DESCRIPTION` - Stream description
    - `LIQUIDSOAP_STATION_URL` - Station website
    - Context: These appear in Icecast, stream players

**Style:** Grouped by purpose with examples. Each section explains what the settings do, how they work together, and why they exist.

**Example Station:** WKRP Coconut Island (tropical paradise) - full .env.example provided

**Cross-links:**
- Previous: VM_SETUP.md (server is ready)
- Next: DEPLOYMENT.md (deploy configured station)
- Related: TROUBLESHOOTING.md (if config isn't working)

---

### docs/DEPLOYMENT.md
**Purpose:** Get code from GitHub onto server and start streaming

**Contents:**

1. **Deployment Overview**
   - What gets deployed (code, configs, scripts, assets)
   - Deployment vs configuration
   - Initial deployment vs updates

2. **Initial Deployment**
   - Clone repository to /srv/ai_radio
   - Set up Python virtual environment with uv
   - Install Python dependencies
   - Copy .env.example to .env and customize
   - Set file permissions
   - Context: Why these steps, what each does

3. **Directory Structure**
   - /srv/ai_radio/src - Python package
   - /srv/ai_radio/scripts - Operational scripts
   - /srv/ai_radio/config - Liquidsoap configuration
   - /srv/ai_radio/assets - Audio files (music, breaks, bumpers)
   - /srv/ai_radio/public - Web frontend
   - /srv/ai_radio/systemd - Service definitions
   - /srv/ai_radio/logs - Log files
   - /srv/ai_radio/db - SQLite database
   - Context: Why this structure, what goes where

4. **Asset Preparation**
   - Music ingestion (adding your music library)
   - Pre-generated station IDs (or generate your own)
   - Safety audio (fallback for emergencies)
   - Context: Asset requirements, formats

5. **Systemd Service Installation**
   - Copy service/timer files to /etc/systemd/system
   - Reload systemd daemon
   - Enable services
   - Service overview:
     - ai-radio-liquidsoap.service (main streaming)
     - ai-radio-break-gen.timer (news breaks at :00)
     - ai-radio-station-id.timer (IDs at :15, :30, :45)
     - ai-radio-export-nowplaying.timer (metadata updates)
     - ai-radio-enqueue-music.timer (queue management)
   - Context: What each service does, why timers vs cron

6. **Starting Services**
   - Start Liquidsoap (music starts immediately)
   - Verify Icecast stream
   - Check logs for errors
   - Verification checklist

7. **Deployment Script Usage**
   - Using scripts/deploy.sh for updates
   - Deploying frontend, scripts, code, config separately
   - Health checks
   - Context: Safe updates without downtime

8. **Verification**
   - [ ] Stream accessible at your URL
   - [ ] Music playing
   - [ ] Metadata updating
   - [ ] Services running and enabled
   - [ ] Logs clean (no errors)

**Style:** Step-by-step deployment guide with verification at each stage.

**Cross-links:**
- Previous: CONFIGURATION.md (station configured)
- Next: ADMINISTRATION.md (day-to-day operations)
- Related: SCRIPTS.md (what each script does)
- Related: TROUBLESHOOTING.md (if deployment fails)

---

### docs/ADMINISTRATION.md
**Purpose:** Day-to-day operations, maintenance, and common tasks

**Contents:**

1. **Daily Operations**
   - Checking stream health
   - Monitoring service status
   - Viewing logs
   - Queue management

2. **Music Management**
   - Adding new music
   - Music ingestion workflow
   - Removing music
   - Music selection algorithm tuning
   - Context: How track selection works

3. **Content Generation**
   - News break generation (manual trigger)
   - Testing break generation
   - Monitoring break quality
   - Adjusting personality settings

4. **Service Management**
   - Restarting services
   - Updating configuration (when to restart what)
   - Log rotation
   - Database maintenance

5. **Monitoring**
   - Health check script usage
   - Stream analytics
   - Listener statistics
   - Error tracking

6. **Updating the Station**
   - Pull latest code
   - Deploy updates
   - Database migrations
   - Configuration updates
   - Context: Safe update procedures

7. **Backup and Recovery**
   - What to backup (database, config, assets)
   - Backup schedule recommendations
   - Restoring from backup
   - Disaster recovery

8. **Performance Tuning**
   - Queue depth optimization
   - Break generation frequency
   - Resource monitoring (CPU, memory, disk)
   - Context: Expected resource usage

**Style:** Task-oriented with clear procedures for common operations.

**Cross-links:**
- Previous: DEPLOYMENT.md (station deployed)
- Related: SCRIPTS.md (detailed script documentation)
- Related: TROUBLESHOOTING.md (when things go wrong)

---

### docs/SCRIPTS.md
**Purpose:** Reference for all scripts in scripts/ directory

**Contents:**

For each script, document:
- **Purpose** - What it does
- **Trigger** - How it's invoked (systemd timer, manual, on_track callback)
- **Usage** - Command-line syntax
- **Parameters** - What arguments it accepts
- **Output** - What it produces
- **Logs** - Where it logs
- **Context** - Why it exists, when to use it manually

**Script Inventory:**

1. **enqueue_music.py**
   - Adds tracks to Liquidsoap music queue
   - Anti-repetition logic
   - Energy level selection
   - Timer: Every 5 minutes

2. **schedule_station_id.py**
   - Picks random station ID and queues it
   - Runs at :15, :30, :45 past the hour
   - Timer-triggered

3. **generate_break.py**
   - Generates news/weather break
   - AI script generation + TTS
   - Runs at :00 (news breaks)
   - Timer-triggered

4. **record_play.py**
   - Records play history to database
   - Called by Liquidsoap on_track callback
   - Triggers metadata export

5. **export_now_playing.py**
   - Exports current/next/history to JSON
   - Powers web frontend
   - Timer: Every 10 seconds

6. **health_check.py**
   - Verifies all systems operational
   - Service status, queue depth, stream health
   - Manual or scheduled

7. **deploy.sh**
   - Deployment automation
   - Component-specific deployment (frontend, scripts, code)
   - Health checks after deployment

8. **fix_timestamp_formats.py** (one-time migration)
   - Fixed timestamp format inconsistency
   - Historical note: Why this was needed

**Style:** Reference format with examples and context.

**Cross-links:**
- Related: ADMINISTRATION.md (when to run scripts manually)
- Related: TROUBLESHOOTING.md (script errors)

---

### docs/TROUBLESHOOTING.md
**Purpose:** Comprehensive issue diagnosis and resolution guide

**Contents:**

Organized by symptom (what the user observes):

1. **Stream Issues**
   - **Stream is silent / no audio**
     - Check Liquidsoap service status
     - Verify queue depth
     - Check music ingestion
     - Log analysis
   - **Stream stutters / buffer issues**
     - Check server resources
     - Network bandwidth
     - Icecast configuration
   - **Stream metadata stuck / wrong**
     - export_now_playing.py status
     - Database play_history check
     - Timestamp issues

2. **Music Queue Issues**
   - **Queue empty / runs out**
     - enqueue_music.py timer status
     - Music library check
     - Track selection errors
   - **Same songs repeating**
     - Anti-repetition settings
     - Music library size
     - Recently played tracking

3. **Break Generation Issues**
   - **Breaks not generating**
     - Timer status check
     - API key validation
     - LLM/TTS errors in logs
   - **Break quality poor**
     - Personality tuning
     - Temperature settings
     - Prompt engineering

4. **Station ID Issues**
   - **Station IDs not playing**
     - Timer status check
     - Bumper directory check
     - Queue insertion errors
   - **Station IDs at wrong times**
     - Timer schedule verification
     - Systemd timer debugging
   - **Queue rewind / metadata stuck after station ID** (Issue #1)
     - Known bug, investigating
     - Timestamp collision symptoms
     - Workaround if available

5. **Service Issues**
   - **Service won't start**
     - Log analysis
     - Permission issues
     - Configuration errors
   - **Service crashes / restarts**
     - Memory issues
     - Error patterns in logs
     - Stability troubleshooting

6. **Configuration Issues**
   - **Changes not taking effect**
     - Which service to restart
     - Configuration reload procedures
   - **API errors**
     - Key validation
     - Rate limiting
     - Model availability

7. **Database Issues**
   - **Database locked errors**
     - Concurrent access issues
     - Lock timeout tuning
   - **Play history missing**
     - record_play.py errors
     - Database corruption check

8. **Web Frontend Issues**
   - **Now playing not updating**
     - export_now_playing.py status
     - JSON file permissions
     - Nginx configuration
   - **Frontend not loading**
     - Nginx service status
     - File permissions
     - Network/firewall

9. **Debugging Techniques**
   - Reading logs effectively (journalctl usage)
   - Using health_check.py
   - Liquidsoap socket queries
   - Database queries for diagnosis
   - Service status interpretation
   - Context: General debugging philosophy

10. **Getting Help**
    - GitHub issues
    - Log collection for bug reports
    - Information to include

**Style:** Symptom → diagnosis → solution format. Each issue includes specific commands to run and what to look for.

**Cross-links:**
- Links to relevant sections in other docs for detailed context

---

## Implementation Order

1. **VM_SETUP.md** (foundation)
2. **CONFIGURATION.md** (most complex, most valuable)
3. **DEPLOYMENT.md** (get people to working state)
4. **README.md** (update with links to new docs)
5. **SCRIPTS.md** (reference material)
6. **ADMINISTRATION.md** (operational knowledge)
7. **TROUBLESHOOTING.md** (support material)

## Style Guide

**Tone:**
- Professional but friendly
- Assumes competence (intermediate users)
- Explains "why" not just "how"
- Occasional humor is fine (we're building AI radio stations, it's fun!)

**Formatting:**
- Use headers liberally for easy scanning
- Code blocks for all commands
- Checkboxes for verification steps
- Cross-links in every relevant section
- Examples where helpful

**Context Level:**
- Always explain what a command does before running it
- Provide context for design decisions
- Occasional deep dives on architecture (clearly marked)
- No assumed knowledge of Liquidsoap, Icecast, or broadcast engineering

**Examples:**
- Use the tropical island station (WKRP Coconut Island) as the example
- Real commands, real paths, real configurations
- Show expected output when helpful

## Success Criteria

Documentation is successful when:
- A competent Linux user can go from SSH access to streaming station in < 2 hours
- Users understand WHY the system is designed this way
- Troubleshooting is self-service 80% of the time
- Users feel empowered to customize and experiment
- The docs feel like they're written by someone who actually uses the system (because they are!)

## Maintenance

- Update docs whenever code changes
- Add troubleshooting entries as issues arise
- Keep cross-links current
- Review quarterly for accuracy

---

**Next Steps:**
1. Get plan approval
2. Start with VM_SETUP.md (foundation document)
3. Work through implementation order
4. Review and iterate
