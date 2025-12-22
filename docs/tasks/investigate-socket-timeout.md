# Task: Investigate Liquidsoap Socket Timeout Issue

## Problem Statement

The `export_now_playing.py` script consistently times out when querying Liquidsoap socket for queue metadata, even though manual queries via `socat` work instantly.

## Current Symptoms

- **Manual query**: Works instantly (`echo "request.metadata 13" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock`)
- **Python script**: Times out after 15 seconds consistently
- **Queue query**: Works fine in Python (returns list of IDs)
- **Metadata query**: Always times out in Python

## Current Implementation

```python
# Python script uses:
sock.settimeout(15.0)
sock.connect(SOCKET_PATH)

# Then queries:
1. music.queue -> Returns: "13 14 15 16 ... END\n" (works)
2. request.metadata 13 -> Times out (fails)
```

## Questions to Investigate

### 1. Is the socket truly timing out?
- Add detailed logging to see exactly where it hangs
- Log timestamps for each operation
- Check if it's waiting on recv() or somewhere else

### 2. Is there a socket lock/contention issue?
- Check if Liquidsoap limits concurrent socket connections
- Try using a fresh socket for each query instead of reusing
- Check Liquidsoap logs for socket errors

### 3. Is the response format different?
- Metadata responses might be larger than queue responses
- Maybe the `END\n` marker isn't being sent correctly
- Try capturing raw bytes to see what we're receiving

### 4. Is there a permissions/environment issue?
- Script works differently under systemd vs manual execution
- Check if systemd PrivateTmp or other sandboxing affects socket access
- Compare environment variables between manual and systemd execution

### 5. Are there alternative approaches?
- **Option A**: Use Liquidsoap telnet protocol instead of raw socket
- **Option B**: Query metadata directly from database (if stored)
- **Option C**: Use Liquidsoap's built-in JSON export features
- **Option D**: Parse Icecast metadata feed instead
- **Option E**: Use Liquidsoap harbor.http to expose REST API

## Investigation Steps

1. **Add verbose logging**
   ```python
   logger.info(f"Connecting to socket...")
   logger.info(f"Connected, sending command: {command}")
   logger.info(f"Command sent, waiting for response...")
   logger.info(f"Received {len(buffer)} bytes so far...")
   ```

2. **Test with strace**
   ```bash
   sudo strace -u ai-radio -e trace=connect,sendto,recvfrom python /srv/ai_radio/scripts/export_now_playing.py
   ```

3. **Check Liquidsoap socket configuration**
   - Look at radio.liq for socket settings
   - Check if there are connection limits
   - Review Liquidsoap logs during timeout

4. **Try alternative socket approach**
   ```python
   # Maybe use telnetlib instead
   import telnetlib
   tn = telnetlib.Telnet()
   tn.open(SOCKET_PATH)
   ```

5. **Test with separate connection per query**
   ```python
   # Instead of reusing socket, create new one each time
   def get_metadata(rid):
       with socket.socket(socket.AF_UNIX) as sock:
           sock.connect(SOCKET_PATH)
           return query_socket(sock, f"request.metadata {rid}")
   ```

## Alternative Solutions

### Short-term Workaround
- Display "Queue has N tracks" instead of showing next track title
- Query just the filename from queue, parse from path

### Long-term Solutions
1. **Use Liquidsoap Harbor HTTP API**
   - Expose queue/metadata via HTTP endpoints
   - More robust than socket queries
   - Better error handling

2. **Track changes in database**
   - Pre-compute next track when current track starts
   - Store in database or separate cache file
   - Update via Liquidsoap on_track callback

3. **Use Icecast metadata**
   - Parse Icecast stream metadata
   - May already include queue information

## Success Criteria

- Python script reliably gets next track metadata in < 1 second
- Or: Alternative solution implemented that shows next track
- No timeouts in systemd service logs

## References

- Liquidsoap socket protocol docs: https://www.liquidsoap.info/doc-dev/protocols.html
- Current script: `/srv/ai_radio/scripts/export_now_playing.py`
- Service logs: `journalctl -u ai-radio-export-nowplaying.service`
