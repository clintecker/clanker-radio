"""Show generation pipeline orchestration."""
import json
import logging
from typing import Dict, List
from google import genai

from .config import config

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
