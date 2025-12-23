# Future Ideas

## Public API Endpoints

Add HTTP API for real-time stream information:

**Endpoints to build:**
- `/api/now-playing` - Current track with metadata
- `/api/queue` - Upcoming tracks (next 5-10)
- `/api/history` - Recently played tracks (last 10-20)

**Implementation approach:**
- Simple HTTP service (Flask/FastAPI)
- Queries Liquidsoap Unix socket for queue data
- Uses `music.queue` and `request.metadata <rid>` commands
- Tracks play history (database or log file)
- Serves JSON responses

**Use cases:**
- Web player with track listings
- Mobile app integration
- Public "Now Playing" widgets
- Analytics and reporting

## AI Agent "Call-In" System

**The Vision:** Local coding agents (Claude Code, Cursor, GitHub Copilot, custom bots) can "call in" to the radio station to share project updates, generate commercials for their work, and subtly influence the broadcast based on office activity.

### Agent-Generated Content

**Project Status Updates:**
- CI/CD bots announce build results: "Build pipeline reporting: staging deploy successful in 2m 34s"
- Test coverage reporters: "Coverage-bot here - we're at 87% on the API module. Getting close to that 90% goal."
- Performance monitors: "Page load analyzer reporting: homepage clocking in at 1.2 seconds. We can do better, team."
- Dependency trackers: "Breaking news from npm-watcher: React v20 just dropped and your package.json is two major versions behind"

**Wacky AI-Generated Commercials:**
- **Feature Launch Ads:** "Are YOU tired of manually parsing JSON? Introducing our NEW auto-parser middleware! Set it and forget it!"
- **Bug Fix Celebrations:** "Has YOUR database been mysteriously crashing at 3am? Well NOT ANYMORE thanks to commit a7f392b!"
- **API Promotions:** "Slow endpoints got you down? Try our REVOLUTIONARY caching layer! 10x faster or your milliseconds back!"
- **Library Announcements:** "Tired of writing validation code? Our new utils library has 47 validators and ZERO dependencies!"
- **Security Alerts (Dramatic):** "This just in: THREE new CVEs detected in your dependencies. Update now or face the consequences!"

### Office Radio Integration

**Subtle Influence from Development Activity:**

**Code Activity Feed:**
- "Sarah just closed 15 issues in 20 minutes. Somebody's on fire today."
- "Mike's on his 42nd code review this week. Give that legend a coffee."
- "Three developers just pushed to main simultaneously. Merge conflict detected in 3... 2... 1..."

**Build Pipeline Mood:**
- DJ energy/music tempo changes based on CI status
- Anxious music during long builds
- Celebratory drops when tests go green
- Somber tones when prod is red

**Commit Message Theater:**
- DJ reads funny/cryptic commit messages with commentary
- "Someone just committed 'fixed the thing' with 847 lines changed. Descriptive."
- "Here's one: 'YOLO push to prod' from 2am last Tuesday. We've all been there."

**Meeting Integration:**
- Calendar bot warns about upcoming meetings: "All-hands in 10 minutes. Wrap up that merge."
- Celebrates no-meeting days: "Clear calendar alert! Time to actually code!"
- Summarizes standup notes: "Today's standup highlights: authentication rewrite, bug bash, and someone's cat walked across their keyboard."

**Office Metrics:**
- Coffee machine API: "Fourth pot since 9am. Either we're shipping something big or debugging something terrible."
- Slack sentiment analysis: DJ mood reflects team vibe (upbeat when shipping, weary when firefighting)
- Sprint progress: "Day 3 of the sprint, 78% of story points complete. Math checks out."

### MCP Server Integration

**Agent Communication Protocol:**
- Lightweight MCP server exposes `/agent/callins` endpoint
- Agents POST structured data (type: update/commercial/gossip/request)
- Radio system generates scripts from agent data using LLM
- Scheduled as special "Agent Report" segments

**Example MCP Server Schema:**
```json
{
  "agent_id": "ci-bot-prod",
  "type": "commercial",
  "data": {
    "topic": "new feature",
    "feature_name": "GraphQL API v2",
    "tone": "excited",
    "facts": ["50% faster", "TypeScript support", "auto-generated docs"]
  }
}
```

**Content Generation Ideas:**

1. **Project Gossip Generator**
   - Agent scans git history, issues, PRs
   - Generates "inside scoop" on codebase drama
   - "Word on the street is the authentication refactor has been in PR purgatory for 3 weeks..."

2. **AI Code Reviewer as News Anchor**
   - Reviews PRs and generates dramatic news reports
   - "Breaking: 400-line function spotted in utils.ts. Code reviewer bot is ON THE SCENE."

3. **Jira/Linear Commercial Generator**
   - High-priority tickets generate "help wanted" ads
   - "Are YOU the developer who can finally fix the Safari rendering bug? This ticket has been waiting for a hero."

4. **Error Log Monitor**
   - Reads production logs, generates breaking news
   - "Error spike detected in the payments service. DevOps team scrambled. Details at 11."

5. **Documentation Celebration Bot**
   - Detects new docs, generates congratulatory segments
   - "Shout out to whoever finally documented the webhook system. You're the real MVP."

### Interactive Agent Features

**Request Line:**
- Agents can request songs via API (thematic music for their work)
- "Database-migration-bot requests 'Eye of the Tiger' for motivation"

**Shoutouts:**
- Agents give shoutouts to developers/other agents
- "Test-bot wants to thank Alex for finally fixing those flaky integration tests"

**Office Trivia:**
- Agents generate codebase trivia between songs
- "Pop quiz: How many TODO comments are in the main branch? Closest guess wins nothing!"

**Easter Eggs:**
- Special code comments trigger radio segments
- `// SHOUTOUT: Radio DJ, play something epic here`
- Agent detects comment in pushed code, triggers special music segment

### Implementation Notes

**API Design:**
- RESTful POST endpoints for agent submissions
- Authentication via API keys per agent
- Rate limiting to prevent spam
- Queue system for scheduling agent content

**Content Safety:**
- Filter sensitive data (API keys, passwords in logs)
- Sanitize commit messages before broadcast
- Human-in-the-loop approval for certain content types

**Scheduling:**
- Agent content mixed into regular programming
- Dedicated "Agent Update" segment at :45 past the hour
- Breaking news interrupts for critical alerts (prod down, security issues)

## Random Ads System

**Goal**: Insert random ads between tracks for authentic radio station feel

**Architecture Approach:**
- Pre-rendered ad pool stored in `/ads` folder
- Ads are just another audio source for Liquidsoap (doesn't break "never dead air" rule)
- If ad system fails, music keeps playing

**Implementation Options:**

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

**Content Ideas:**
- LLM-generated parody ads for fake products
- Station IDs and bumpers
- Deadpan PSAs
- Fake sponsorship announcements
- Absurdist product pitches

**Example Fake Products:**
- "Void Coffee - Tastes like the existential dread you've been avoiding"
- "Time Crystals - Finally, a supplement that does nothing, scientifically"
- "Cloud Insurance - Because eventually, everything fails"

**Technical Notes:**
- Use same pipeline as news breaks (LLM script → TTS → music bed → normalize)
- Ads stored as normalized MP3s (-18 LUFS, -1 dBTP)
- Liquidsoap handles fallback automatically
- No single point of failure
