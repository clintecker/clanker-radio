"""Show generation pipeline orchestration."""
import json
import logging
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from google import genai

from .config import config
from .voice_synth import AudioFile
from .ingest import ingest_audio_file
from .show_models import ShowStatus, ShowFormat

logger = logging.getLogger(__name__)


def research_topics(topic_area: str, content_guidance: str = "") -> List[str]:
    """Research current topics for a show.

    Args:
        topic_area: General topic area (e.g., "Bitcoin news")
        content_guidance: Optional specific topics/angles

    Returns:
        List of topic strings suitable for show discussion

    Raises:
        ValueError: If inputs are invalid or response is malformed
        RuntimeError: If API call fails
    """
    # Input validation
    if not topic_area or not topic_area.strip():
        raise ValueError("Cannot research topics without a topic area")

    if len(topic_area) > 500:
        raise ValueError("Topic area too long (max 500 characters)")

    if content_guidance and len(content_guidance) > 1000:
        raise ValueError("Content guidance too long (max 1000 characters)")

    # API key validation
    if not config.api_keys.gemini_api_key:
        raise ValueError("RADIO_GEMINI_API_KEY not configured")

    logger.debug(f"Starting topic research for: {topic_area[:100]}...")

    try:
        client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

        prompt = f"""You are researching topics for an 8-minute radio show.

Topic Area: {topic_area}
{f'Content Guidance: {content_guidance}' if content_guidance else ''}

Research and return 3-5 current, interesting topics in this area.
Focus on recent developments, trends, or discussions.

Return ONLY a JSON array of strings (no markdown, no explanation):
["Topic 1 description", "Topic 2 description", ...]

Be specific and concrete. Each topic should be a complete sentence."""

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )

        # Extract JSON from response
        text = response.text.strip()
        if text.startswith("```"):
            # Remove markdown code blocks
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        topics = json.loads(text.strip())

        # Validate response structure
        if not isinstance(topics, list):
            raise ValueError("Response is not a list")

        if len(topics) == 0:
            raise ValueError("No topics returned")

        if not all(isinstance(t, str) for t in topics):
            raise ValueError("Not all topics are strings")

        logger.info(f"Researched {len(topics)} topics for '{topic_area}': {topics}")
        return topics

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        raise ValueError(f"Invalid JSON response from Gemini: {e}")
    except ValueError:
        # Re-raise ValueError from validation
        raise
    except Exception as e:
        logger.exception("Topic research failed")
        raise RuntimeError(f"Failed to research topics: {e}")


def generate_interview_script(topics: List[str], personas: List[Dict[str, str]]) -> str:
    """Generate interview-format radio script.

    Args:
        topics: List of topic strings to cover
        personas: List of persona dicts with 'name' and 'traits' keys
                  First persona is the host, second is the expert

    Returns:
        Generated script with [speaker: Name] tags

    Raises:
        ValueError: If inputs are invalid or response format is wrong
        RuntimeError: If API call fails
    """
    # API key validation (check first so tests can verify this error)
    if not config.api_keys.gemini_api_key:
        raise ValueError("RADIO_GEMINI_API_KEY not configured")

    # Input validation
    if not topics or len(topics) == 0:
        raise ValueError("Cannot generate script without topics")

    if not personas or len(personas) == 0:
        raise ValueError("Cannot generate script without personas")

    try:
        client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

        # Safely access personas with default fallback for test scenarios
        host = personas[0] if len(personas) > 0 else {"name": "Host", "traits": "engaging"}
        expert = personas[1] if len(personas) > 1 else {"name": "Expert", "traits": "knowledgeable"}
        topics_text = "\n".join([f"- {topic}" for topic in topics])

        prompt = f"""Generate an 8-minute interview-style radio dialogue (~1,200 words).

PERSONAS:
- Host: {host['name']} - {host['traits']}
- Expert: {expert['name']} - {expert['traits']}

TOPICS TO COVER:
{topics_text}

OUTPUT FORMAT - Use speaker aliases exactly as shown:
[speaker: {host['name']}] Dialogue here...
[speaker: {expert['name']}] Response here...

STRUCTURE:
1. Host opens with welcoming the expert and introducing the first topic
2. Expert provides detailed answer
3. Host asks follow-up question
4. Continue Q&A pattern through all topics
5. Host thanks the expert and closes

CONSTRAINTS:
- Exactly 1,200 words (±50 words)
- Natural Q&A flow: question → answer → follow-up
- End with host thanking expert
- Use the EXACT speaker format shown above

Generate the dialogue now:"""

        logger.debug(f"Generating interview script with topics: {topics}")

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )

        script = response.text.strip()

        # Validate response format
        if "[speaker:" not in script:
            raise ValueError("No speaker tags found in response")

        logger.info(f"Generated interview script: {len(script)} characters")
        return script

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.exception("Interview script generation failed")
        raise RuntimeError(f"Failed to generate interview script: {e}")


def generate_discussion_script(topics: List[str], personas: List[Dict[str, str]]) -> str:
    """Generate two-host discussion format script.

    Args:
        topics: List of topic strings to cover
        personas: List of persona dicts with 'name' and 'traits' keys
                  Both personas are co-equal hosts (not host/expert)

    Returns:
        Generated script with [speaker: Name] tags

    Raises:
        ValueError: If inputs are invalid or response format is wrong
        RuntimeError: If API call fails
    """
    # API key validation (check first so tests can verify this error)
    if not config.api_keys.gemini_api_key:
        raise ValueError("RADIO_GEMINI_API_KEY not configured")

    # Input validation
    if not topics or len(topics) == 0:
        raise ValueError("Cannot generate script without topics")

    if not personas or len(personas) == 0:
        raise ValueError("Cannot generate script without personas")

    try:
        client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

        # Both personas are co-equal hosts (not host/expert dynamic)
        host_a = personas[0] if len(personas) > 0 else {"name": "Host A", "traits": "engaging"}
        host_b = personas[1] if len(personas) > 1 else {"name": "Host B", "traits": "thoughtful"}
        topics_text = "\n".join([f"- {topic}" for topic in topics])

        prompt = f"""Generate an 8-minute discussion-style radio dialogue (~1,200 words).

PERSONAS (both are CO-EQUAL hosts, not host/expert):
- Host A: {host_a['name']} - {host_a['traits']}
- Host B: {host_b['name']} - {host_b['traits']}

TOPICS TO COVER:
{topics_text}

OUTPUT FORMAT - Use speaker aliases exactly as shown:
[speaker: {host_a['name']}] Dialogue here...
[speaker: {host_b['name']}] Response here...

STRUCTURE:
1. {host_a['name']} opens with topic overview
2. {host_b['name']} presents a contrasting perspective
3. Back-and-forth debate with genuine disagreement
4. {host_b['name']} closes with synthesis

CRITICAL REQUIREMENTS:
- Create genuine disagreement and contrasting viewpoints
- Avoid "I agree" or "great point" filler
- No one-sided validation - they should challenge each other
- Both hosts are equals debating ideas, not interviewing
- Natural conversational flow with back-and-forth exchanges
- End with {host_b['name']} synthesizing the discussion

CONSTRAINTS:
- Exactly 1,200 words (±50 words)
- Must be under 7,500 bytes total
- Use the EXACT speaker format shown above

Generate the dialogue now:"""

        logger.debug(f"Generating discussion script with topics: {topics}")

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )

        script = response.text.strip()

        # Validate response format
        if "[speaker:" not in script:
            raise ValueError("No speaker tags found in response")

        logger.info(f"Generated discussion script: {len(script)} characters")
        return script

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.exception("Discussion script generation failed")
        raise RuntimeError(f"Failed to generate discussion script: {e}")


def synthesize_show_audio(
    script_text: str,
    personas: List[Dict[str, str]],
    output_path: Path
) -> Optional[AudioFile]:
    """Synthesize multi-speaker audio from script.

    Args:
        script_text: Script with [speaker: Name] tags
        personas: List of persona dicts with 'name' and 'traits' keys
        output_path: Path where audio file will be saved

    Returns:
        AudioFile with metadata, or None if synthesis fails

    Raises:
        ValueError: If inputs are invalid
        RuntimeError: If synthesis fails
    """
    # API key validation (check first)
    if not config.api_keys.gemini_api_key:
        raise ValueError("RADIO_GEMINI_API_KEY not configured")

    # Input validation
    if not script_text or not script_text.strip():
        raise ValueError("Cannot synthesize empty script")

    if "[speaker:" not in script_text:
        raise ValueError("No speaker tags found in script")

    if not personas or len(personas) == 0:
        raise ValueError("Cannot synthesize without personas")

    try:
        # Extract speaker names from personas
        speaker_names = [p["name"] for p in personas]
        voice = ", ".join(speaker_names)

        logger.debug(f"Synthesizing audio for speakers: {voice}")

        # Call Gemini TTS API
        client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=script_text,
            config=genai.types.GenerateContentConfig(
                response_modalities=["AUDIO"]
            )
        )

        # Extract PCM audio data from response
        if not response.candidates or not response.candidates[0].content.parts:
            raise RuntimeError("No audio data in Gemini response")

        audio_data = response.candidates[0].content.parts[0].inline_data.data

        if not audio_data:
            raise RuntimeError("No audio inline_data in Gemini response")

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write PCM data to temporary file
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
                raise RuntimeError("Failed to synthesize audio")

        finally:
            # Clean up temp PCM file
            Path(pcm_path).unlink(missing_ok=True)

        # Estimate duration (150 words per minute)
        word_count = len(script_text.split())
        duration_estimate = (word_count / 150) * 60  # Convert to seconds

        logger.info(
            f"Show audio synthesis complete: {output_path} "
            f"(~{duration_estimate:.1f}s, {word_count} words, voices: {voice})"
        )

        return AudioFile(
            file_path=output_path,
            duration_estimate=duration_estimate,
            timestamp=datetime.now(),
            voice=voice,
            model="gemini-2.5-flash-preview-tts"
        )

    except ValueError:
        # Re-raise validation errors
        raise
    except RuntimeError:
        # Re-raise runtime errors
        raise
    except Exception as e:
        logger.exception("Audio synthesis failed")
        raise RuntimeError(f"Failed to synthesize audio: {e}")


class ShowGenerator:
    """Orchestrates complete show generation pipeline.

    Coordinates: research → script → audio → ingest → database updates
    Handles state machine transitions and error recovery.
    """

    def __init__(self, repository):
        """Initialize show generator.

        Args:
            repository: Repository instance with database update methods
        """
        self.repository = repository

    def generate(self, schedule, show) -> None:
        """Generate complete show from schedule.

        Orchestrates the full pipeline from research through to ready asset:
        1. Check if resuming from ShowStatus.SCRIPT_COMPLETE (skip research/script)
        2. If pending: research topics → generate script → update DB
        3. Generate audio from script
        4. Ingest audio to assets
        5. Update DB to ready with asset_id

        Args:
            schedule: ShowSchedule with format, topics, personas
            show: GeneratedShow with id, status, script_text

        State transitions:
            - pending → ShowStatus.SCRIPT_COMPLETE → ready
            - pending → script_failed (on research/script error)
            - ShowStatus.SCRIPT_COMPLETE → ready (resumption path)
            - ShowStatus.SCRIPT_COMPLETE → audio_failed (on audio error)
        """
        logger.info(f"Starting show generation for show ID {show.id} (status: {show.status})")

        try:
            # Check if resuming from script_complete state
            if show.status == ShowStatus.SCRIPT_COMPLETE:
                logger.info("Resuming from script_complete state")
                script_text = show.script_text
            else:
                # Phase 1: Research and script generation
                logger.info("Phase 1: Research and script generation")

                # Research topics
                topics = research_topics(
                    topic_area=schedule.topic_area,
                    content_guidance=schedule.content_guidance or ""
                )
                logger.info(f"Researched {len(topics)} topics")

                # Parse personas from JSON string
                personas = json.loads(schedule.personas)

                # Generate script based on format
                if schedule.format == ShowFormat.INTERVIEW:
                    script_text = generate_interview_script(
                        topics=topics,
                        personas=personas
                    )
                    logger.info("Generated interview script")
                elif schedule.format == ShowFormat.TWO_HOST_DISCUSSION:
                    script_text = generate_discussion_script(
                        topics=topics,
                        personas=personas
                    )
                    logger.info("Generated discussion script")
                else:
                    raise ValueError(f"Invalid show format: {schedule.format}")

                # Update database with completed script
                self.repository.update_show_script(show.id, script_text)
                self.repository.update_show_status(show.id, ShowStatus.SCRIPT_COMPLETE)
                logger.info("Script phase complete, updated database")

        except Exception as e:
            # Script generation failed
            logger.exception(f"Script generation failed for show {show.id}")
            self.repository.update_show_status(show.id, ShowStatus.SCRIPT_FAILED)
            self.repository.update_show_error(show.id, str(e))
            return

        # Generate temp file path for audio synthesis
        output_path = config.paths.tmp_path / f"show_{show.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"

        try:
            # Phase 2: Audio synthesis
            logger.info("Phase 2: Audio synthesis")

            # Parse personas again if not already parsed (for resume path)
            personas = json.loads(schedule.personas)

            # Synthesize audio
            audio_file = synthesize_show_audio(
                script_text=script_text,
                personas=personas,
                output_path=output_path
            )

            if not audio_file:
                raise RuntimeError("Audio synthesis returned None")

            logger.info(f"Audio synthesized: {audio_file.duration_estimate:.1f}s")

            # Phase 3: Ingest audio to assets
            logger.info("Phase 3: Ingesting audio to assets")

            asset_dict = ingest_audio_file(
                source_path=audio_file.file_path,
                kind="break",
                db_path=config.paths.db_path,
                output_dir=config.paths.music_path
            )

            asset_id = asset_dict["id"]
            asset_filepath = Path(asset_dict["path"])
            logger.info(f"Audio ingested with asset ID: {asset_id}")

            # Update database with asset and mark as ready
            try:
                self.repository.update_show_asset(show.id, asset_id)
                self.repository.update_show_status(show.id, ShowStatus.READY)
                logger.info(f"Show {show.id} generation complete: ready with asset {asset_id}")
            except Exception as db_error:
                # DB update failed - cleanup orphaned asset
                logger.warning(f"DB update failed for show {show.id}. Cleaning up orphaned asset: {asset_id}")
                try:
                    # Delete file from disk
                    if asset_filepath.exists():
                        asset_filepath.unlink()
                        logger.info(f"Deleted orphaned file: {asset_filepath}")

                    # Delete from assets table
                    conn = sqlite3.connect(config.paths.db_path)
                    try:
                        conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
                        conn.commit()
                        logger.info(f"Deleted orphaned asset record: {asset_id}")
                    finally:
                        conn.close()
                except Exception as cleanup_error:
                    logger.error(
                        f"CRITICAL: Failed to cleanup orphaned asset {asset_id}: {cleanup_error}. "
                        f"Manual cleanup required for file: {asset_filepath}"
                    )
                # Re-raise original DB error
                raise db_error

        except Exception as e:
            # Audio synthesis or ingestion failed
            logger.exception(f"Audio synthesis failed for show {show.id}")
            self.repository.update_show_status(show.id, ShowStatus.AUDIO_FAILED)
            self.repository.update_show_error(show.id, str(e))
            return

        finally:
            # Always clean up temporary audio file
            if output_path.exists():
                output_path.unlink()
                logger.debug(f"Cleaned up temporary audio file: {output_path.name}")
