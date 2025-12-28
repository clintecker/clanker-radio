# DJ Tag Generator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build web-based admin utility for generating DJ tags using Gemini TTS with real-time progress updates and MP3 download.

**Architecture:** Flask API (port 5001) with SSE streaming for progress, simplified Gemini TTS wrapper (no five-element framework), cyberpunk-styled web UI, nginx proxy with HTTP Basic Auth.

**Tech Stack:** Python 3.12, Flask, google-genai, ffmpeg, Server-Sent Events (SSE), vanilla JavaScript, nginx reverse proxy

---

## Task 1: Core Logic - DJ Tag Generator

Create simplified Gemini TTS wrapper for direct text-to-speech without the radio station's elaborate five-element framework.

**Files:**
- Create: `src/ai_radio/dj_tag_generator.py`
- Test: `tests/test_dj_tag_generator.py`

**Step 1: Write the failing test**

```python
"""Tests for DJ tag generator."""
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from ai_radio.dj_tag_generator import DJTagGenerator, GenerationProgress


class TestDJTagGenerator:
    """Test DJ tag generation with Gemini TTS."""

    def test_initialization_requires_api_key(self):
        """Test that generator requires valid API key."""
        with patch('ai_radio.dj_tag_generator.config') as mock_config:
            mock_config.gemini_api_key = None
            with pytest.raises(ValueError, match="RADIO_GEMINI_API_KEY not configured"):
                DJTagGenerator()

    def test_initialization_success(self):
        """Test successful generator initialization."""
        with patch('ai_radio.dj_tag_generator.config') as mock_config:
            mock_config.gemini_api_key = "test-key"
            generator = DJTagGenerator()
            assert generator.api_key == "test-key"

    def test_generate_validates_empty_text(self):
        """Test that empty text is rejected."""
        with patch('ai_radio.dj_tag_generator.config') as mock_config:
            mock_config.gemini_api_key = "test-key"
            generator = DJTagGenerator()

            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                output_path = Path(f.name)

            try:
                result = generator.generate(
                    text="",
                    output_path=output_path,
                    voice="Kore"
                )
                assert result is None
            finally:
                output_path.unlink(missing_ok=True)

    def test_generate_validates_text_length(self):
        """Test that text exceeding max length is rejected."""
        with patch('ai_radio.dj_tag_generator.config') as mock_config:
            mock_config.gemini_api_key = "test-key"
            generator = DJTagGenerator()

            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                output_path = Path(f.name)

            try:
                # Generate text > 5000 characters
                long_text = "a" * 5001
                result = generator.generate(
                    text=long_text,
                    output_path=output_path,
                    voice="Kore"
                )
                assert result is None
            finally:
                output_path.unlink(missing_ok=True)

    @patch('ai_radio.dj_tag_generator.subprocess.run')
    def test_generate_calls_gemini_api(self, mock_subprocess):
        """Test that generate calls Gemini API with correct parameters."""
        with patch('ai_radio.dj_tag_generator.config') as mock_config:
            mock_config.gemini_api_key = "test-key"

            # Mock successful ffmpeg conversion
            mock_subprocess.return_value = Mock(returncode=0, stderr="")

            with patch('ai_radio.dj_tag_generator.genai') as mock_genai:
                # Mock Gemini client and response
                mock_client = MagicMock()
                mock_genai.Client.return_value = mock_client

                mock_response = MagicMock()
                mock_part = MagicMock()
                mock_part.inline_data.data = b"fake_pcm_data"
                mock_response.candidates = [MagicMock()]
                mock_response.candidates[0].content.parts = [mock_part]

                mock_client.models.generate_content.return_value = mock_response

                generator = DJTagGenerator()

                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                    output_path = Path(f.name)

                try:
                    result = generator.generate(
                        text="Test DJ tag",
                        output_path=output_path,
                        voice="Laomedeia",
                        temperature=2.0,
                        speaking_rate=1.0,
                        pitch=0.0,
                        style_prompt="excited and energetic"
                    )

                    assert result is not None
                    assert result.file_path == output_path
                    assert result.voice == "Laomedeia"

                    # Verify API was called
                    mock_client.models.generate_content.assert_called_once()
                finally:
                    output_path.unlink(missing_ok=True)

    def test_progress_callback_is_called(self):
        """Test that progress callback receives updates."""
        progress_updates = []

        def progress_callback(progress: GenerationProgress):
            progress_updates.append(progress)

        with patch('ai_radio.dj_tag_generator.config') as mock_config:
            mock_config.gemini_api_key = "test-key"

            with patch('ai_radio.dj_tag_generator.subprocess.run') as mock_subprocess:
                mock_subprocess.return_value = Mock(returncode=0, stderr="")

                with patch('ai_radio.dj_tag_generator.genai') as mock_genai:
                    mock_client = MagicMock()
                    mock_genai.Client.return_value = mock_client

                    mock_response = MagicMock()
                    mock_part = MagicMock()
                    mock_part.inline_data.data = b"fake_pcm_data"
                    mock_response.candidates = [MagicMock()]
                    mock_response.candidates[0].content.parts = [mock_part]

                    mock_client.models.generate_content.return_value = mock_response

                    generator = DJTagGenerator()

                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                        output_path = Path(f.name)

                    try:
                        generator.generate(
                            text="Test",
                            output_path=output_path,
                            voice="Kore",
                            progress_callback=progress_callback
                        )

                        # Should have received at least: started, generating, converting, complete
                        assert len(progress_updates) >= 4
                        assert any(p.message == "Starting generation..." for p in progress_updates)
                        assert any(p.message == "Generating audio..." for p in progress_updates)
                        assert any("Converting" in p.message for p in progress_updates)
                        assert any("Complete" in p.message for p in progress_updates)
                    finally:
                        output_path.unlink(missing_ok=True)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dj_tag_generator.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'ai_radio.dj_tag_generator'"

**Step 3: Write minimal implementation**

```python
"""DJ tag generator using simplified Gemini TTS.

Generates audio tags for DJ mixes without the elaborate five-element framework
used by the radio station. Provides direct text-to-speech with configurable
voice parameters.
"""

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from .config import config

logger = logging.getLogger(__name__)

# Import Gemini at module level for easier mocking
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


@dataclass
class GenerationProgress:
    """Progress update during tag generation."""

    percent: int  # 0-100
    message: str


@dataclass
class GeneratedTag:
    """Generated DJ tag audio file."""

    file_path: Path
    duration_estimate: float  # seconds
    timestamp: datetime
    voice: str
    model: str
    temperature: float
    speaking_rate: float
    pitch: float


class DJTagGenerator:
    """Simplified Gemini TTS for DJ tag generation.

    Unlike the radio station voice synthesis, this uses direct text-to-speech
    without elaborate prompt engineering. Suitable for quick DJ tags and
    announcements.
    """

    MAX_TEXT_LENGTH = 5000

    def __init__(self):
        """Initialize DJ tag generator with Gemini API key."""
        self.api_key = config.gemini_api_key
        if not self.api_key:
            raise ValueError("RADIO_GEMINI_API_KEY not configured")

        if genai is None:
            raise ValueError("google-genai package not installed. Run: pip install google-genai")

        self.client = genai.Client(api_key=self.api_key)

    def generate(
        self,
        text: str,
        output_path: Path,
        voice: str = "Kore",
        model: str = "gemini-2.5-pro-preview-tts",
        temperature: float = 2.0,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        style_prompt: Optional[str] = None,
        progress_callback: Optional[Callable[[GenerationProgress], None]] = None,
    ) -> Optional[GeneratedTag]:
        """Generate DJ tag audio from text.

        Args:
            text: Text to synthesize
            output_path: Path for output MP3 file
            voice: Gemini voice name (e.g., "Laomedeia", "Kore", "Puck")
            model: Gemini TTS model (pro or flash)
            temperature: Creativity level (0.0-2.0)
            speaking_rate: Speech speed (0.5-2.0)
            pitch: Voice pitch adjustment (-20.0 to +20.0)
            style_prompt: Optional natural language style guidance
            progress_callback: Optional callback for progress updates

        Returns:
            GeneratedTag with metadata, or None if generation fails
        """
        # Validation
        if not text or not text.strip():
            logger.error("Cannot generate tag from empty text")
            return None

        if len(text) > self.MAX_TEXT_LENGTH:
            logger.error(f"Text exceeds max length ({self.MAX_TEXT_LENGTH} characters)")
            return None

        def update_progress(percent: int, message: str):
            """Send progress update if callback provided."""
            if progress_callback:
                progress_callback(GenerationProgress(percent=percent, message=message))

        try:
            update_progress(0, "Starting generation...")
            logger.info(f"Generating DJ tag with voice '{voice}'")

            # Build simplified prompt (no five-element framework)
            if style_prompt:
                prompt = f"Style: {style_prompt}\n\nText: {text}"
            else:
                prompt = text

            update_progress(10, "Generating audio...")

            # Generate speech with Gemini API
            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice
                            )
                        )
                    )
                )
            )

            update_progress(50, "Processing audio data...")

            # Extract audio data from response
            if not response.candidates or not response.candidates[0].content.parts:
                logger.error("No audio data in Gemini response")
                return None

            # Find the audio part
            audio_data = None
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    audio_data = part.inline_data.data
                    break

            if not audio_data:
                logger.error("No audio inline_data in Gemini response")
                return None

            update_progress(60, "Converting PCM to MP3...")

            # Gemini returns raw PCM data - convert to MP3 using ffmpeg
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write raw PCM to temporary file
            with tempfile.NamedTemporaryFile(suffix='.pcm', delete=False) as pcm_file:
                pcm_file.write(audio_data)
                pcm_path = pcm_file.name

            try:
                # Convert PCM to MP3 using ffmpeg
                # Gemini TTS outputs 24kHz 16-bit mono PCM
                result = subprocess.run(
                    [
                        "ffmpeg",
                        "-y",  # Overwrite output file
                        "-f", "s16le",  # Format: signed 16-bit little-endian
                        "-ar", "24000",  # Sample rate: 24kHz
                        "-ac", "1",  # Audio channels: mono
                        "-i", pcm_path,  # Input PCM file
                        "-c:a", "libmp3lame",
                        "-q:a", "2",  # High quality MP3
                        str(output_path),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode != 0:
                    logger.error(f"ffmpeg PCM conversion failed: {result.stderr}")
                    return None

            finally:
                # Clean up temp PCM file
                Path(pcm_path).unlink(missing_ok=True)

            update_progress(90, "Finalizing...")

            # Estimate duration (rough approximation: 150 words per minute)
            word_count = len(text.split())
            duration_estimate = (word_count / 150) * 60  # Convert to seconds

            update_progress(100, "Complete!")

            logger.info(
                f"DJ tag generation complete: {output_path} "
                f"(~{duration_estimate:.1f}s, {word_count} words)"
            )

            return GeneratedTag(
                file_path=output_path,
                duration_estimate=duration_estimate,
                timestamp=datetime.now(),
                voice=voice,
                model=model,
                temperature=temperature,
                speaking_rate=speaking_rate,
                pitch=pitch,
            )

        except Exception as e:
            logger.error(f"DJ tag generation failed: {e}")
            if progress_callback:
                progress_callback(GenerationProgress(percent=0, message=f"Error: {str(e)}"))
            return None
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_dj_tag_generator.py -v`

Expected: PASS (all 6 tests)

**Step 5: Commit**

```bash
git add src/ai_radio/dj_tag_generator.py tests/test_dj_tag_generator.py
git commit -m "feat: add DJ tag generator with simplified Gemini TTS"
```

---

## Task 2: Flask API with SSE Streaming

Create Flask API server with SSE streaming for real-time progress updates during generation.

**Files:**
- Create: `scripts/api_dj_tag.py`
- Test: Manual testing (Flask apps are integration-tested)

**Step 1: Write Flask API implementation**

```python
#!/usr/bin/env python3
"""Flask API server for DJ tag generation.

Provides HTTP endpoints for generating DJ tags with real-time progress updates
via Server-Sent Events (SSE). Binds to 127.0.0.1:5001 for nginx proxy.
"""

import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Dict

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
TMP_DIR = Path(config.base_path) / "tmp" / "dj_tags"
TMP_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILES = 100
MAX_AGE_HOURS = 24

# Job tracking
jobs: Dict[str, dict] = {}


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
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = "Generation failed"

            progress_queue.put({
                "event": "error",
                "error": "Audio generation failed. Check server logs.",
                "retry": True,
            })

    except Exception as e:
        logger.error(f"Generation error for job {job_id}: {e}")
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
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]

    def event_stream():
        """Generate SSE events."""
        progress_queue = Queue()

        # Start background generation
        thread = Thread(
            target=background_generation,
            args=(job_id, job["params"], progress_queue),
            daemon=True,
        )
        thread.start()

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
    # Security: validate filename
    if not filename.startswith("dj_tag_") or not filename.endswith(".mp3"):
        return jsonify({"error": "Invalid filename"}), 400

    file_path = TMP_DIR / filename

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
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "active_jobs": len([j for j in jobs.values() if j["status"] == "generating"]),
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
```

**Step 2: Test API locally**

Run: `uv run python scripts/api_dj_tag.py`

Expected: Server starts on http://127.0.0.1:5001

Test health endpoint:
```bash
curl http://127.0.0.1:5001/api/dj-tag/health
```

Expected: `{"status": "ok", ...}`

**Step 3: Commit**

```bash
git add scripts/api_dj_tag.py
git commit -m "feat: add Flask API for DJ tag generation with SSE"
```

---

## Task 3: Frontend Web UI

Create cyberpunk-styled web interface matching existing admin pages.

**Files:**
- Create: `nginx/admin/dj_tag.html`

**Step 1: Write frontend HTML with inline CSS and JavaScript**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DJ Tag Generator - LAST BYTE RADIO</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Courier New', monospace;
            background: #1a1a2e;
            color: #eee;
            padding: 40px 20px;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
        }

        h1 {
            color: #667eea;
            margin-bottom: 0.5em;
            font-size: 2.5em;
        }

        .subtitle {
            color: #999;
            margin-bottom: 2em;
            font-size: 1.1em;
        }

        .card {
            background: #16213e;
            border: 1px solid #0f3460;
            border-radius: 8px;
            padding: 2em;
            margin-bottom: 2em;
        }

        .form-group {
            margin-bottom: 1.5em;
        }

        label {
            display: block;
            color: #667eea;
            margin-bottom: 0.5em;
            font-weight: bold;
        }

        textarea, input[type="text"], select {
            width: 100%;
            padding: 0.75em;
            background: #0f3460;
            border: 1px solid #667eea;
            border-radius: 4px;
            color: #eee;
            font-family: 'Courier New', monospace;
            font-size: 1em;
        }

        textarea {
            min-height: 120px;
            resize: vertical;
        }

        .slider-group {
            display: flex;
            align-items: center;
            gap: 1em;
        }

        input[type="range"] {
            flex: 1;
            -webkit-appearance: none;
            appearance: none;
            height: 6px;
            background: #0f3460;
            border-radius: 3px;
            outline: none;
        }

        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 18px;
            height: 18px;
            background: #667eea;
            cursor: pointer;
            border-radius: 50%;
        }

        input[type="range"]::-moz-range-thumb {
            width: 18px;
            height: 18px;
            background: #667eea;
            cursor: pointer;
            border-radius: 50%;
            border: none;
        }

        .slider-value {
            min-width: 60px;
            text-align: right;
            color: #eee;
            font-weight: bold;
        }

        .radio-group {
            display: flex;
            gap: 1.5em;
        }

        .radio-group label {
            display: flex;
            align-items: center;
            gap: 0.5em;
            cursor: pointer;
            font-weight: normal;
        }

        .radio-group input[type="radio"] {
            width: auto;
        }

        button {
            background: #667eea;
            color: #fff;
            border: none;
            padding: 1em 2em;
            font-size: 1.1em;
            font-weight: bold;
            border-radius: 4px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            transition: all 0.3s;
        }

        button:hover:not(:disabled) {
            background: #5568d3;
            transform: translateY(-2px);
        }

        button:disabled {
            background: #444;
            cursor: not-allowed;
            opacity: 0.6;
        }

        .progress-section {
            display: none;
            margin-top: 2em;
        }

        .progress-section.active {
            display: block;
        }

        .progress-bar-container {
            background: #0f3460;
            border-radius: 4px;
            overflow: hidden;
            height: 30px;
            margin-bottom: 1em;
        }

        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            width: 0%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-weight: bold;
        }

        .progress-message {
            color: #aaa;
            font-style: italic;
        }

        .error {
            background: #ff4444;
            color: #fff;
            padding: 1em;
            border-radius: 4px;
            margin-bottom: 1em;
            display: none;
        }

        .error.active {
            display: block;
        }

        .back-link {
            display: inline-block;
            margin-top: 2em;
            color: #667eea;
            text-decoration: none;
        }

        .back-link:hover {
            text-decoration: underline;
        }

        .help-text {
            color: #999;
            font-size: 0.9em;
            margin-top: 0.5em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ DJ TAG GENERATOR</h1>
        <div class="subtitle">Generate custom audio tags for your DJ mixes</div>

        <div class="error" id="errorDisplay"></div>

        <div class="card">
            <form id="tagForm">
                <div class="form-group">
                    <label for="tagText">Tag Text *</label>
                    <textarea
                        id="tagText"
                        name="text"
                        required
                        maxlength="5000"
                        placeholder="oh, holy shit! They put MISTER BEEF in the booth?!?"
                    ></textarea>
                    <div class="help-text">Max 5000 characters</div>
                </div>

                <div class="form-group">
                    <label for="voice">Voice</label>
                    <select id="voice" name="voice">
                        <option value="Aoede">Aoede</option>
                        <option value="Charon">Charon</option>
                        <option value="Fenrir">Fenrir</option>
                        <option value="Kore" selected>Kore</option>
                        <option value="Laomedeia">Laomedeia</option>
                        <option value="Puck">Puck</option>
                        <option value="Acherner">Acherner</option>
                        <option value="Atlas">Atlas</option>
                        <option value="Callisto">Callisto</option>
                        <option value="Dione">Dione</option>
                        <option value="Enceladus">Enceladus</option>
                        <option value="Hyperion">Hyperion</option>
                        <option value="Iapetus">Iapetus</option>
                        <option value="Janus">Janus</option>
                        <option value="Mimas">Mimas</option>
                        <option value="Oberon">Oberon</option>
                        <option value="Pandora">Pandora</option>
                        <option value="Prometheus">Prometheus</option>
                        <option value="Rhea">Rhea</option>
                        <option value="Tethys">Tethys</option>
                        <option value="Titan">Titan</option>
                        <option value="Triton">Triton</option>
                        <option value="Umbriel">Umbriel</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>Model</label>
                    <div class="radio-group">
                        <label>
                            <input type="radio" name="model" value="gemini-2.5-pro-preview-tts" checked>
                            Pro (High Quality)
                        </label>
                        <label>
                            <input type="radio" name="model" value="gemini-2.5-flash-preview-tts">
                            Flash (Low Latency)
                        </label>
                    </div>
                </div>

                <div class="form-group">
                    <label for="temperature">Temperature (Creativity)</label>
                    <div class="slider-group">
                        <input
                            type="range"
                            id="temperature"
                            name="temperature"
                            min="0"
                            max="2"
                            step="0.1"
                            value="2.0"
                        >
                        <span class="slider-value" id="temperatureValue">2.0</span>
                    </div>
                    <div class="help-text">0.0 = Consistent, 2.0 = Creative</div>
                </div>

                <div class="form-group">
                    <label for="speakingRate">Speaking Rate</label>
                    <div class="slider-group">
                        <input
                            type="range"
                            id="speakingRate"
                            name="speaking_rate"
                            min="0.5"
                            max="2.0"
                            step="0.1"
                            value="1.0"
                        >
                        <span class="slider-value" id="speakingRateValue">1.0x</span>
                    </div>
                    <div class="help-text">0.5x = Slow, 2.0x = Fast</div>
                </div>

                <div class="form-group">
                    <label for="pitch">Pitch</label>
                    <div class="slider-group">
                        <input
                            type="range"
                            id="pitch"
                            name="pitch"
                            min="-20"
                            max="20"
                            step="1"
                            value="0"
                        >
                        <span class="slider-value" id="pitchValue">0</span>
                    </div>
                    <div class="help-text">-20 = Lower, +20 = Higher</div>
                </div>

                <div class="form-group">
                    <label for="stylePrompt">Style Prompt (Optional)</label>
                    <input
                        type="text"
                        id="stylePrompt"
                        name="style_prompt"
                        placeholder="excited and energetic"
                    >
                    <div class="help-text">Natural language description of desired delivery style</div>
                </div>

                <button type="submit" id="generateBtn">Generate DJ Tag</button>
            </form>

            <div class="progress-section" id="progressSection">
                <div class="progress-bar-container">
                    <div class="progress-bar" id="progressBar">0%</div>
                </div>
                <div class="progress-message" id="progressMessage">Starting...</div>
            </div>
        </div>

        <a href="/admin/" class="back-link">← Back to Admin</a>
    </div>

    <script>
        // Update slider value displays
        document.getElementById('temperature').addEventListener('input', (e) => {
            document.getElementById('temperatureValue').textContent = e.target.value;
        });

        document.getElementById('speakingRate').addEventListener('input', (e) => {
            document.getElementById('speakingRateValue').textContent = e.target.value + 'x';
        });

        document.getElementById('pitch').addEventListener('input', (e) => {
            document.getElementById('pitchValue').textContent = e.target.value;
        });

        // Form submission
        document.getElementById('tagForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            // Hide error, show progress
            document.getElementById('errorDisplay').classList.remove('active');
            document.getElementById('progressSection').classList.add('active');
            document.getElementById('generateBtn').disabled = true;

            // Reset progress
            updateProgress(0, 'Starting...');

            // Collect form data
            const formData = new FormData(e.target);
            const data = {
                text: formData.get('text'),
                voice: formData.get('voice'),
                model: formData.get('model'),
                temperature: parseFloat(formData.get('temperature')),
                speaking_rate: parseFloat(formData.get('speaking_rate')),
                pitch: parseFloat(formData.get('pitch')),
                style_prompt: formData.get('style_prompt') || undefined,
            };

            try {
                // Start generation
                const response = await fetch('/api/dj-tag/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data),
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Generation failed');
                }

                const result = await response.json();
                const streamUrl = result.stream_url;

                // Connect to SSE stream
                const eventSource = new EventSource(streamUrl);

                eventSource.addEventListener('progress', (e) => {
                    const data = JSON.parse(e.data);
                    updateProgress(data.percent, data.message);
                });

                eventSource.addEventListener('complete', (e) => {
                    const data = JSON.parse(e.data);
                    updateProgress(100, 'Complete!');

                    // Trigger download
                    const link = document.createElement('a');
                    link.href = data.download_url;
                    link.download = data.filename;
                    link.click();

                    // Re-enable form after short delay
                    setTimeout(() => {
                        document.getElementById('progressSection').classList.remove('active');
                        document.getElementById('generateBtn').disabled = false;
                    }, 2000);

                    eventSource.close();
                });

                eventSource.addEventListener('error', (e) => {
                    const data = JSON.parse(e.data);
                    showError(data.error);
                    document.getElementById('progressSection').classList.remove('active');
                    document.getElementById('generateBtn').disabled = false;
                    eventSource.close();
                });

                eventSource.onerror = (e) => {
                    // Connection error
                    if (eventSource.readyState === EventSource.CLOSED) {
                        showError('Connection lost. Please try again.');
                        document.getElementById('progressSection').classList.remove('active');
                        document.getElementById('generateBtn').disabled = false;
                    }
                };

            } catch (error) {
                showError(error.message);
                document.getElementById('progressSection').classList.remove('active');
                document.getElementById('generateBtn').disabled = false;
            }
        });

        function updateProgress(percent, message) {
            const bar = document.getElementById('progressBar');
            const msg = document.getElementById('progressMessage');
            bar.style.width = percent + '%';
            bar.textContent = percent + '%';
            msg.textContent = message;
        }

        function showError(message) {
            const errorDiv = document.getElementById('errorDisplay');
            errorDiv.textContent = message;
            errorDiv.classList.add('active');
        }
    </script>
</body>
</html>
```

**Step 2: Test frontend locally (manual)**

1. Start Flask API: `uv run python scripts/api_dj_tag.py`
2. Open `nginx/admin/dj_tag.html` in browser (file:// protocol for initial test)
3. Try generating a tag with "Test DJ tag" text

Expected: Form submits, progress bar animates, MP3 downloads

**Step 3: Commit**

```bash
git add nginx/admin/dj_tag.html
git commit -m "feat: add DJ tag generator web UI with SSE progress"
```

---

## Task 4: Systemd Service

Create systemd unit for running Flask API as a service.

**Files:**
- Create: `systemd/ai-radio-dj-tag-api.service`

**Step 1: Write systemd service unit**

```ini
[Unit]
Description=AI Radio DJ Tag Generator API
Documentation=https://github.com/your-repo/ai-radio
After=network.target

[Service]
Type=simple
User=clint
Group=clint
WorkingDirectory=/srv/ai_radio
Environment="PATH=/srv/ai_radio/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"

# Load environment variables
EnvironmentFile=/srv/ai_radio/.env

# Run Flask API
ExecStart=/srv/ai_radio/.venv/bin/python /srv/ai_radio/scripts/api_dj_tag.py

# Restart policy
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/srv/ai_radio/tmp/dj_tags /srv/ai_radio/logs

# Resource limits
LimitNOFILE=4096
MemoryMax=1G

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-radio-dj-tag-api

[Install]
WantedBy=multi-user.target
```

**Step 2: Commit**

```bash
git add systemd/ai-radio-dj-tag-api.service
git commit -m "feat: add systemd service for DJ tag API"
```

---

## Task 5: Nginx Configuration Documentation

Document nginx configuration changes needed (actual modification happens on server).

**Files:**
- Create: `docs/DJ_TAG_NGINX_CONFIG.md`

**Step 1: Write nginx configuration documentation**

```markdown
# DJ Tag Generator Nginx Configuration

## Overview

Add these sections to `/etc/nginx/sites-enabled/radio` on the server to enable DJ tag generator with HTTP Basic Auth and SSE support.

## Configuration Changes

### 1. Add upstream definition (after existing upstreams)

```nginx
upstream dj_tag_api {
    server 127.0.0.1:5001;
}
```

### 2. Add location for HTML page (in server block)

```nginx
location /admin/dj-tag.html {
    auth_basic "Radio Admin";
    auth_basic_user_file /etc/nginx/.htpasswd;
    alias /srv/ai_radio/public/admin/dj_tag.html;
}
```

### 3. Add location for API endpoints (in server block)

```nginx
location /api/dj-tag/ {
    auth_basic "Radio Admin";
    auth_basic_user_file /etc/nginx/.htpasswd;

    # SSE-specific headers
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 180s;
    proxy_connect_timeout 10s;
    proxy_send_timeout 180s;

    # Standard proxy headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Proxy to Flask API
    proxy_pass http://dj_tag_api/;
}
```

## Deployment Steps

1. SSH to server: `ssh clint@10.10.0.86`
2. Edit nginx config: `sudo nano /etc/nginx/sites-enabled/radio`
3. Add the three sections above
4. Test configuration: `sudo nginx -t`
5. Reload nginx: `sudo systemctl reload nginx`

## Verification

Test that auth is required:
```bash
curl -I https://radio.clintecker.com/admin/dj-tag.html
# Should return 401 Unauthorized
```

Test with auth (replace with actual credentials):
```bash
curl -u admin:password https://radio.clintecker.com/admin/dj-tag.html
# Should return 200 OK with HTML
```

## SSE Timeout Configuration

The configuration includes:
- `proxy_buffering off` - Disable buffering for real-time SSE
- `proxy_cache off` - Disable caching for SSE streams
- `proxy_read_timeout 180s` - Allow up to 3 minutes for generation
- `proxy_send_timeout 180s` - Allow up to 3 minutes for sending response

These timeouts match the backend's maximum generation time of 120 seconds plus buffer.
```

**Step 2: Commit**

```bash
git add docs/DJ_TAG_NGINX_CONFIG.md
git commit -m "docs: add nginx configuration guide for DJ tag generator"
```

---

## Task 6: Update Admin Index to Link to DJ Tag Generator

Add link to DJ tag generator on admin index page.

**Files:**
- Modify: `nginx/admin/index.html:134-146`

**Step 1: Read current admin index**

Run: `cat nginx/admin/index.html | grep -A 10 "admin-grid"`

Expected: Shows existing admin cards (Icecast, Liquidsoap)

**Step 2: Add DJ tag generator card**

Add this card after the Liquidsoap Control card (around line 145):

```html
            <div class="admin-card">
                <h2>DJ Tag Generator</h2>
                <p>Generate custom audio tags for DJ mixes with AI voice synthesis.</p>
                <a href="/admin/dj-tag.html">Generate Tags →</a>
            </div>
```

Full section should look like:

```html
        <div class="admin-grid">
            <div class="admin-card">
                <h2>Icecast Admin</h2>
                <p>Manage stream configuration, monitor listeners, and control mount points.</p>
                <a href="/admin/icecast/">Open Icecast →</a>
            </div>

            <div class="admin-card">
                <h2>Liquidsoap Control</h2>
                <p>Liquidsoap Harbor HTTP API (temporarily disabled - use Unix socket).</p>
                <a href="#" style="opacity: 0.5; cursor: not-allowed;">Coming Soon</a>
            </div>

            <div class="admin-card">
                <h2>DJ Tag Generator</h2>
                <p>Generate custom audio tags for DJ mixes with AI voice synthesis.</p>
                <a href="/admin/dj-tag.html">Generate Tags →</a>
            </div>
        </div>
```

**Step 3: Verify change**

Run: `cat nginx/admin/index.html | grep -A 3 "DJ Tag"`

Expected: Shows the new admin card

**Step 4: Commit**

```bash
git add nginx/admin/index.html
git commit -m "feat: add DJ tag generator link to admin panel"
```

---

## Task 7: Integration Testing and Deployment

Test the complete system locally, then deploy to production.

**Step 1: Local integration test**

```bash
# Start Flask API
uv run python scripts/api_dj_tag.py &
API_PID=$!

# Wait for startup
sleep 2

# Test health endpoint
curl http://127.0.0.1:5001/api/dj-tag/health

# Test generation endpoint (will fail without Gemini API key, but tests validation)
curl -X POST http://127.0.0.1:5001/api/dj-tag/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "Test DJ tag"}'

# Should return job_id and stream_url

# Clean up
kill $API_PID
```

Expected: Health check returns `{"status": "ok"}`, generate returns job data

**Step 2: Deploy to production server**

```bash
# From worktree root
cd /Users/clint/code/clintecker/clanker-radio/.worktrees/dj-tag-generator

# Deploy code (scripts + frontend + core)
./scripts/deploy.sh

# Or deploy components separately:
# ./scripts/deploy.sh scripts  # Deploy Flask API
# ./scripts/deploy.sh code     # Deploy dj_tag_generator.py
# ./scripts/deploy.sh frontend # Deploy HTML page
```

**Step 3: Install and start systemd service**

SSH to server:
```bash
ssh clint@10.10.0.86
```

On server:
```bash
# Copy systemd service
sudo cp /srv/ai_radio/systemd/ai-radio-dj-tag-api.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable ai-radio-dj-tag-api

# Start service
sudo systemctl start ai-radio-dj-tag-api

# Check status
sudo systemctl status ai-radio-dj-tag-api

# View logs
sudo journalctl -u ai-radio-dj-tag-api -f
```

Expected: Service starts successfully, logs show "Starting DJ Tag Generator API on 127.0.0.1:5001"

**Step 4: Configure nginx**

On server:
```bash
# Edit nginx config
sudo nano /etc/nginx/sites-enabled/radio
```

Add the three sections from `docs/DJ_TAG_NGINX_CONFIG.md`:
1. Upstream definition
2. HTML page location
3. API endpoints location

```bash
# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

Expected: nginx config test passes, reload succeeds

**Step 5: End-to-end production test**

From your local machine:
```bash
# Test HTML page (with auth)
curl -u <username>:<password> https://radio.clintecker.com/admin/dj-tag.html

# Should return HTML

# Test health endpoint (with auth)
curl -u <username>:<password> https://radio.clintecker.com/api/dj-tag/health

# Should return {"status": "ok"}
```

**Step 6: Browser test**

1. Open https://radio.clintecker.com/admin/
2. Log in with admin credentials
3. Click "Generate Tags →" card
4. Enter text: "This is LAST BYTE RADIO, testing the DJ tag generator"
5. Select voice: "Laomedeia"
6. Click "Generate DJ Tag"
7. Watch progress bar animate
8. Verify MP3 downloads automatically
9. Play MP3 to verify audio

Expected: Complete flow works, audio plays correctly

**Step 7: Commit test results**

```bash
# Back in worktree
git add .
git commit -m "test: verify DJ tag generator end-to-end on production"
```

---

## Task 8: Merge to Main

Merge feature branch back to main after successful testing.

**Step 1: Switch to main branch**

```bash
cd /Users/clint/code/clintecker/clanker-radio
git checkout main
```

**Step 2: Merge feature branch**

```bash
git merge feature/dj-tag-generator
```

**Step 3: Push to remote**

```bash
git push origin main
```

**Step 4: Clean up worktree**

```bash
# Remove worktree
git worktree remove .worktrees/dj-tag-generator

# Delete feature branch
git branch -d feature/dj-tag-generator
```

---

## Success Criteria Checklist

Verify all requirements from design document:

### Functional Requirements
- [ ] Web UI for text input and parameter configuration
- [ ] Real-time progress updates during 20-120 second generation
- [ ] Automatic MP3 download when complete
- [ ] Access restricted to admin users (HTTP Basic Auth)
- [ ] Support all 30+ Gemini TTS voice options
- [ ] Configurable parameters: temperature, speaking rate, pitch, style prompt
- [ ] Model selection (Flash vs Pro)

### Non-Functional Requirements
- [ ] Handle 20-120 second generation times without timeout
- [ ] Work across all modern browsers (Chrome, Firefox, Safari, Edge)
- [ ] Reuse existing Gemini API credentials
- [ ] No permanent storage (24-hour cleanup works)
- [ ] Single user tool (no queue management needed)

### Technical Requirements
- [ ] Flask API binds to 127.0.0.1:5001 (not exposed externally)
- [ ] Nginx proxy with HTTP Basic Auth
- [ ] SSE streaming with proper headers
- [ ] PCM to MP3 conversion using ffmpeg
- [ ] Systemd service runs reliably
- [ ] Admin index links to DJ tag generator

### Testing Checklist
- [ ] Empty text validation works
- [ ] Text exceeding 5000 chars is rejected
- [ ] All voice options generate successfully
- [ ] Temperature 0.0, 1.0, 2.0 produce different results
- [ ] Speaking rate 0.5, 1.0, 2.0 work correctly
- [ ] Pitch -10, 0, +10 work correctly
- [ ] Style prompt affects output
- [ ] Progress bar updates in real-time
- [ ] MP3 auto-downloads when complete
- [ ] Auth required for all endpoints
- [ ] Files older than 24 hours are cleaned up

---

## Troubleshooting Guide

### Issue: Flask API won't start

**Symptoms:** Service fails to start, logs show import errors

**Solutions:**
1. Check Python environment: `which python` (should be `/srv/ai_radio/.venv/bin/python`)
2. Verify dependencies installed: `uv sync`
3. Test manually: `uv run python scripts/api_dj_tag.py`
4. Check logs: `sudo journalctl -u ai-radio-dj-tag-api -n 50`

### Issue: Progress updates not streaming

**Symptoms:** Progress bar doesn't update, page hangs

**Solutions:**
1. Check nginx buffering config: `grep proxy_buffering /etc/nginx/sites-enabled/radio`
2. Verify SSE headers in nginx config
3. Test SSE endpoint directly: `curl -N http://127.0.0.1:5001/api/dj-tag/stream/test123`
4. Check browser console for EventSource errors

### Issue: MP3 download fails

**Symptoms:** Progress completes but no download

**Solutions:**
1. Check tmp directory permissions: `ls -la /srv/ai_radio/tmp/dj_tags/`
2. Verify ffmpeg installed: `which ffmpeg`
3. Check Flask logs for conversion errors
4. Test download URL directly: `curl -O http://127.0.0.1:5001/api/dj-tag/download/<filename>`

### Issue: Generation times out

**Symptoms:** Request fails after ~60 seconds

**Solutions:**
1. Verify all timeouts set to 180s:
   - Nginx: `proxy_read_timeout 180s;`
   - Flask: Check no explicit timeout set
   - Browser: AbortController timeout = 180000ms
2. Check Gemini API quotas
3. Test with shorter text (fewer words = faster generation)

### Issue: Auth not working

**Symptoms:** Can access endpoints without credentials

**Solutions:**
1. Verify nginx auth config: `grep auth_basic /etc/nginx/sites-enabled/radio`
2. Check .htpasswd file exists: `ls -la /etc/nginx/.htpasswd`
3. Test nginx config: `sudo nginx -t`
4. Reload nginx: `sudo systemctl reload nginx`

---

## Implementation Notes

**DRY (Don't Repeat Yourself):**
- Reuse existing PCM-to-MP3 conversion logic from `voice_synth.py`
- Reuse existing HTTP Basic Auth from admin pages
- Reuse existing Gemini API client setup pattern
- Reuse existing cyberpunk styling from admin index

**YAGNI (You Aren't Gonna Need It):**
- No tag history/database (just temporary files with auto-cleanup)
- No batch generation (single user tool)
- No user management (reuse existing nginx auth)
- No job queue (simple in-memory dict for active jobs)
- No voice preview (adds complexity, can test directly)

**TDD (Test-Driven Development):**
- Write tests first for core logic (Task 1)
- Manual integration testing for Flask API (Task 2)
- Browser-based testing for UI (Task 3)
- End-to-end production testing before merge (Task 7)

**Commit Frequency:**
- Commit after each major task completion
- Small, focused commits with clear messages
- Follow conventional commits format (feat:, fix:, docs:, test:)
