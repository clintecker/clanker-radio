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
