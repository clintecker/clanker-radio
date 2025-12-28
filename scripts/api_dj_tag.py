#!/usr/bin/env python3
"""Flask API server for DJ tag generation.

Provides HTTP endpoints for generating DJ tags with real-time progress updates
via Server-Sent Events (SSE). Binds to 127.0.0.1:5001 for nginx proxy.
"""

import json
import logging
import os
import secrets
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue
from threading import Thread, Lock
from typing import Dict, Set

from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_radio.dj_tag_generator import DJTagGenerator, GenerationProgress
from src.ai_radio.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
CORS(app)  # Enable CORS for development

# Storage configuration
# Use base_path if writable, otherwise fall back to local tmp
try:
    base_tmp = Path(config.base_path) / "tmp" / "dj_tags"
    base_tmp.mkdir(parents=True, exist_ok=True)
    TMP_DIR = base_tmp
except (OSError, PermissionError):
    # Fall back to local temp directory for development
    TMP_DIR = Path("/tmp") / "ai_radio_dj_tags"
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    logger.warning(f"Using fallback temp directory: {TMP_DIR}")

MAX_FILES = 100
MAX_AGE_HOURS = 24

# Job tracking with thread safety
jobs: Dict[str, dict] = {}
jobs_lock = Lock()
active_threads: Set[Thread] = set()
shutdown_requested = False


def handle_shutdown(signum, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True

    # Wait for active threads to complete (with timeout)
    logger.info(f"Waiting for {len(active_threads)} active generation threads...")
    for thread in list(active_threads):
        thread.join(timeout=30.0)

    logger.info("Shutdown complete")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


def cleanup_old_files():
    """Remove DJ tag files older than 24 hours."""
    try:
        cutoff = datetime.now() - timedelta(hours=MAX_AGE_HOURS)
        removed = 0

        for file_path in TMP_DIR.glob("*.mp3"):
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_time < cutoff:
                file_path.unlink()
                removed += 1

        # Also enforce max file count
        files = sorted(TMP_DIR.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
        if len(files) > MAX_FILES:
            for old_file in files[MAX_FILES:]:
                old_file.unlink()
                removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} old DJ tag files")

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")


def generate_job_id() -> str:
    """Generate unique job ID."""
    return secrets.token_urlsafe(16)


def background_generation(job_id: str, params: dict, progress_queue: Queue):
    """Background thread for generating DJ tag.

    Args:
        job_id: Unique job identifier
        params: Generation parameters (text, voice, etc.)
        progress_queue: Queue for sending progress updates
    """
    try:
        # Send initial progress
        progress_queue.put({"percent": 0, "message": "Starting generation..."})

        # Create generator
        generator = DJTagGenerator()

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"dj_tag_{job_id}_{timestamp}.mp3"
        output_path = TMP_DIR / output_filename

        # Progress callback
        def progress_callback(progress: GenerationProgress):
            progress_queue.put({
                "percent": progress.percent,
                "message": progress.message
            })

        # Generate tag
        result = generator.generate(
            text=params["text"],
            output_path=output_path,
            voice=params.get("voice", "Kore"),
            model=params.get("model", "gemini-2.5-pro-preview-tts"),
            temperature=params.get("temperature", 2.0),
            speaking_rate=params.get("speaking_rate", 1.0),
            pitch=params.get("pitch", 0.0),
            style_prompt=params.get("style_prompt"),
            progress_callback=progress_callback,
        )

        if result:
            # Success
            with jobs_lock:
                jobs[job_id]["status"] = "complete"
                jobs[job_id]["output_file"] = output_filename
                jobs[job_id]["duration"] = result.duration_estimate

            progress_queue.put({
                "event": "complete",
                "download_url": f"/api/dj-tag/download/{output_filename}",
                "filename": output_filename,
            })
        else:
            # Failed
            with jobs_lock:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = "Generation failed"

            progress_queue.put({
                "event": "error",
                "error": "Audio generation failed. Check server logs.",
                "retry": True,
            })

    except Exception as e:
        logger.error(f"Generation error for job {job_id}: {e}")
        with jobs_lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)

        progress_queue.put({
            "event": "error",
            "error": str(e),
            "retry": True,
        })

    finally:
        # Signal completion
        progress_queue.put(None)


@app.route("/api/dj-tag/generate", methods=["POST"])
def generate():
    """Start DJ tag generation.

    Request body:
        {
            "text": "Tag text to synthesize",
            "voice": "Laomedeia",
            "model": "gemini-2.5-pro-preview-tts",
            "temperature": 2.0,
            "speaking_rate": 1.0,
            "pitch": 0.0,
            "style_prompt": "excited and energetic"
        }

    Returns:
        {
            "job_id": "abc123",
            "stream_url": "/api/dj-tag/stream/abc123"
        }
    """
    try:
        data = request.json

        # Validate required fields
        if not data or "text" not in data:
            return jsonify({"error": "Missing required field: text"}), 400

        text = data["text"].strip()
        if not text:
            return jsonify({"error": "Text cannot be empty"}), 400

        if len(text) > 5000:
            return jsonify({"error": "Text exceeds maximum length (5000 characters)"}), 400

        # Cleanup old files before starting new job
        cleanup_old_files()

        # Create job
        job_id = generate_job_id()
        with jobs_lock:
            jobs[job_id] = {
                "status": "generating",
                "created_at": datetime.now().isoformat(),
                "params": data,
            }

        logger.info(f"Created job {job_id} for text: {text[:50]}...")

        return jsonify({
            "job_id": job_id,
            "stream_url": f"/api/dj-tag/stream/{job_id}",
        })

    except Exception as e:
        logger.error(f"Generate endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/dj-tag/stream/<job_id>")
def stream(job_id: str):
    """Stream generation progress via Server-Sent Events.

    SSE Events:
        - progress: {"percent": 45, "message": "Converting..."}
        - complete: {"download_url": "/api/.../file.mp3", "filename": "..."}
        - error: {"error": "...", "retry": true/false}
    """
    with jobs_lock:
        if job_id not in jobs:
            return jsonify({"error": "Job not found"}), 404
        job = jobs[job_id]

    def event_stream():
        """Generate SSE events."""
        progress_queue = Queue()

        # Start background generation (non-daemon for graceful shutdown)
        thread = Thread(
            target=background_generation,
            args=(job_id, job["params"], progress_queue),
        )

        # Track thread for graceful shutdown
        active_threads.add(thread)
        thread.start()

        try:
            # Stream progress updates
            while True:
                update = progress_queue.get()

                if update is None:
                    # Generation complete
                    break

                # Determine event type
                event_type = update.pop("event", "progress")

                # Format as SSE
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(update)}\n\n"
                time.sleep(0.1)  # Small delay for browser parsing
        finally:
            # Clean up thread tracking
            active_threads.discard(thread)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@app.route("/api/dj-tag/download/<filename>")
def download(filename: str):
    """Download generated DJ tag MP3 file.

    Args:
        filename: MP3 filename (dj_tag_*.mp3)

    Returns:
        MP3 file with appropriate headers
    """
    # Security: validate filename format
    if not filename.startswith("dj_tag_") or not filename.endswith(".mp3"):
        return jsonify({"error": "Invalid filename"}), 400

    # Security: prevent path traversal - no directory separators allowed
    if "/" in filename or "\\" in filename:
        return jsonify({"error": "Invalid filename"}), 400

    # Construct and resolve path
    file_path = (TMP_DIR / filename).resolve()

    # Security: verify resolved path is within TMP_DIR
    try:
        file_path.relative_to(TMP_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Invalid filename"}), 400

    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404

    return send_file(
        file_path,
        mimetype="audio/mpeg",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/api/dj-tag/health")
def health():
    """Health check endpoint."""
    with jobs_lock:
        active_jobs = len([j for j in jobs.values() if j["status"] == "generating"])

    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "active_jobs": active_jobs,
        "tmp_dir": str(TMP_DIR),
        "tmp_files": len(list(TMP_DIR.glob("*.mp3"))),
    })


if __name__ == "__main__":
    logger.info("Starting DJ Tag Generator API on 127.0.0.1:5001")
    logger.info(f"Storage directory: {TMP_DIR}")

    # Cleanup on startup
    cleanup_old_files()

    # Run Flask app
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=False,  # Production mode
        threaded=True,
    )
