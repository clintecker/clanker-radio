"""Tests for show generation pipeline."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from ai_radio.show_generator import research_topics, generate_interview_script, generate_discussion_script, synthesize_show_audio
from ai_radio.voice_synth import AudioFile


@patch('ai_radio.show_generator.genai.Client')
def test_research_topics(mock_client_class):
    """Test researching topics for a show."""
    # Mock the Gemini API response
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = '''[
        "Bitcoin reaches new all-time high above $100,000",
        "SEC approves multiple Bitcoin ETFs for retail investors",
        "DeFi protocols see surge in total value locked"
    ]'''
    mock_client.models.generate_content.return_value = mock_response

    topics = research_topics(
        topic_area="Bitcoin news",
        content_guidance="Latest price movements and regulatory updates"
    )

    assert isinstance(topics, list)
    assert len(topics) > 0
    assert all(isinstance(t, str) for t in topics)
    assert len(topics) == 3


def test_research_topics_empty_input():
    """Test that empty topic_area raises ValueError."""
    with pytest.raises(ValueError, match="Cannot research topics without a topic area"):
        research_topics("")

    with pytest.raises(ValueError, match="Cannot research topics without a topic area"):
        research_topics("   ")


def test_research_topics_input_too_long():
    """Test that topic_area longer than 500 chars raises ValueError."""
    long_topic = "a" * 501
    with pytest.raises(ValueError, match="Topic area too long"):
        research_topics(long_topic)


def test_research_topics_content_guidance_too_long():
    """Test that content_guidance longer than 1000 chars raises ValueError."""
    long_guidance = "a" * 1001
    with pytest.raises(ValueError, match="Content guidance too long"):
        research_topics("Bitcoin news", content_guidance=long_guidance)


@patch('ai_radio.show_generator.config')
def test_research_topics_missing_api_key(mock_config):
    """Test that missing API key raises ValueError."""
    mock_config.api_keys.gemini_api_key = None
    with pytest.raises(ValueError, match="RADIO_GEMINI_API_KEY not configured"):
        research_topics("Bitcoin news")


@patch('ai_radio.show_generator.genai.Client')
def test_research_topics_invalid_json(mock_client_class):
    """Test that malformed JSON response raises ValueError."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = "This is not valid JSON"
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(ValueError, match="Invalid JSON response from Gemini"):
        research_topics("Bitcoin news")


@patch('ai_radio.show_generator.genai.Client')
def test_research_topics_not_a_list(mock_client_class):
    """Test that non-list response raises ValueError."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = '{"error": "not a list"}'
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(ValueError, match="Response is not a list"):
        research_topics("Bitcoin news")


@patch('ai_radio.show_generator.genai.Client')
def test_research_topics_empty_list(mock_client_class):
    """Test that empty list response raises ValueError."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = '[]'
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(ValueError, match="No topics returned"):
        research_topics("Bitcoin news")


@patch('ai_radio.show_generator.genai.Client')
def test_research_topics_non_string_items(mock_client_class):
    """Test that list with non-string items raises ValueError."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = '[1, 2, 3]'
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(ValueError, match="Not all topics are strings"):
        research_topics("Bitcoin news")


@patch('ai_radio.show_generator.genai.Client')
def test_research_topics_api_failure(mock_client_class):
    """Test that general API error raises RuntimeError."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_client.models.generate_content.side_effect = Exception("API connection failed")

    with pytest.raises(RuntimeError, match="Failed to research topics"):
        research_topics("Bitcoin news")


@patch('ai_radio.show_generator.config')
@patch('ai_radio.show_generator.genai.Client')
def test_generate_interview_script(mock_client_class, mock_config):
    """Test generating interview-format script with multiple speakers."""
    # Mock API key
    mock_api_key = Mock()
    mock_api_key.get_secret_value.return_value = "fake-api-key"
    mock_config.api_keys.gemini_api_key = mock_api_key

    # Mock the Gemini API response
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = '''[speaker: Sarah] Welcome to Crypto Insights. Today we're joined by blockchain expert Dr. Chen to discuss recent Bitcoin developments. Dr. Chen, what's driving the current price surge?

[speaker: Dr. Chen] Thanks for having me, Sarah. The primary factor is institutional adoption. We're seeing major corporations adding Bitcoin to their treasury reserves.

[speaker: Sarah] That's fascinating. How does this compare to previous market cycles?

[speaker: Dr. Chen] This cycle is fundamentally different because the buyers are sophisticated institutional investors with long-term horizons, not retail speculators.'''
    mock_client.models.generate_content.return_value = mock_response

    script = generate_interview_script(
        topics=["Bitcoin institutional adoption", "Market cycle analysis"],
        personas=[
            {"name": "Sarah", "traits": "curious, engaging host"},
            {"name": "Dr. Chen", "traits": "analytical blockchain expert"}
        ]
    )

    assert isinstance(script, str)
    assert len(script) > 0
    assert "[speaker: Sarah]" in script
    assert "[speaker: Dr. Chen]" in script
    assert "Bitcoin" in script or "bitcoin" in script


def test_generate_interview_script_empty_topics():
    """Test that empty topics list raises ValueError."""
    with pytest.raises(ValueError, match="Cannot generate script without topics"):
        generate_interview_script(
            topics=[],
            personas=[{"name": "Host", "traits": "engaging"}]
        )


def test_generate_interview_script_empty_personas():
    """Test that empty personas list raises ValueError."""
    with pytest.raises(ValueError, match="Cannot generate script without personas"):
        generate_interview_script(
            topics=["Bitcoin news"],
            personas=[]
        )


@patch('ai_radio.show_generator.config')
def test_generate_interview_script_missing_api_key(mock_config):
    """Test that missing API key raises ValueError."""
    mock_config.api_keys.gemini_api_key = None
    with pytest.raises(ValueError, match="RADIO_GEMINI_API_KEY not configured"):
        generate_interview_script(
            topics=["Bitcoin news"],
            personas=[{"name": "Host", "traits": "engaging"}]
        )


@patch('ai_radio.show_generator.config')
@patch('ai_radio.show_generator.genai.Client')
def test_generate_interview_script_api_failure(mock_client_class, mock_config):
    """Test that general API error raises RuntimeError."""
    # Mock API key
    mock_api_key = Mock()
    mock_api_key.get_secret_value.return_value = "fake-api-key"
    mock_config.api_keys.gemini_api_key = mock_api_key

    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_client.models.generate_content.side_effect = Exception("API connection failed")

    with pytest.raises(RuntimeError, match="Failed to generate interview script"):
        generate_interview_script(
            topics=["Bitcoin news"],
            personas=[{"name": "Host", "traits": "engaging"}]
        )


@patch('ai_radio.show_generator.config')
@patch('ai_radio.show_generator.genai.Client')
def test_generate_interview_script_invalid_format(mock_client_class, mock_config):
    """Test that response without speaker tags raises ValueError."""
    # Mock API key
    mock_api_key = Mock()
    mock_api_key.get_secret_value.return_value = "fake-api-key"
    mock_config.api_keys.gemini_api_key = mock_api_key

    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = "This is just plain text without any speaker tags."
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(ValueError, match="No speaker tags found in response"):
        generate_interview_script(
            topics=["Bitcoin news"],
            personas=[{"name": "Host", "traits": "engaging"}]
        )


@patch('ai_radio.show_generator.config')
@patch('ai_radio.show_generator.genai.Client')
def test_generate_discussion_script(mock_client_class, mock_config):
    """Test generating discussion-format script with two co-equal hosts."""
    # Mock API key
    mock_api_key = Mock()
    mock_api_key.get_secret_value.return_value = "fake-api-key"
    mock_config.api_keys.gemini_api_key = mock_api_key

    # Mock the Gemini API response
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = '''[speaker: Alex] I think Bitcoin's institutional adoption is actually a double-edged sword. Sure, it brings legitimacy, but we're seeing concentration of holdings in just a few corporate treasuries. That goes against the decentralization ethos.

[speaker: Jordan] I disagree completely. You're missing the bigger picture. Institutional adoption is exactly what Bitcoin needs to achieve global reserve currency status. Without major players, it remains a niche asset.

[speaker: Alex] But that's my point - becoming a reserve currency means becoming part of the system Bitcoin was designed to replace. We're watching it get co-opted.

[speaker: Jordan] That's idealistic thinking. Bitcoin can't change the world from the margins. It needs institutional buy-in to reach the scale where it actually matters.'''
    mock_client.models.generate_content.return_value = mock_response

    script = generate_discussion_script(
        topics=["Bitcoin institutional adoption", "Decentralization vs mainstream acceptance"],
        personas=[
            {"name": "Alex", "traits": "skeptical, idealistic, questions mainstream narratives"},
            {"name": "Jordan", "traits": "optimistic, pragmatic, focuses on real-world adoption"}
        ]
    )

    assert isinstance(script, str)
    assert len(script) > 0
    assert "[speaker: Alex]" in script
    assert "[speaker: Jordan]" in script
    assert "Bitcoin" in script or "bitcoin" in script


def test_generate_discussion_script_empty_topics():
    """Test that empty topics list raises ValueError."""
    with pytest.raises(ValueError, match="Cannot generate script without topics"):
        generate_discussion_script(
            topics=[],
            personas=[
                {"name": "Alex", "traits": "skeptical"},
                {"name": "Jordan", "traits": "optimistic"}
            ]
        )


def test_generate_discussion_script_empty_personas():
    """Test that empty personas list raises ValueError."""
    with pytest.raises(ValueError, match="Cannot generate script without personas"):
        generate_discussion_script(
            topics=["Bitcoin news"],
            personas=[]
        )


@patch('ai_radio.show_generator.config')
def test_generate_discussion_script_missing_api_key(mock_config):
    """Test that missing API key raises ValueError."""
    mock_config.api_keys.gemini_api_key = None
    with pytest.raises(ValueError, match="RADIO_GEMINI_API_KEY not configured"):
        generate_discussion_script(
            topics=["Bitcoin news"],
            personas=[
                {"name": "Alex", "traits": "skeptical"},
                {"name": "Jordan", "traits": "optimistic"}
            ]
        )


@patch('ai_radio.show_generator.config')
@patch('ai_radio.show_generator.genai.Client')
def test_generate_discussion_script_api_failure(mock_client_class, mock_config):
    """Test that general API error raises RuntimeError."""
    # Mock API key
    mock_api_key = Mock()
    mock_api_key.get_secret_value.return_value = "fake-api-key"
    mock_config.api_keys.gemini_api_key = mock_api_key

    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_client.models.generate_content.side_effect = Exception("API connection failed")

    with pytest.raises(RuntimeError, match="Failed to generate discussion script"):
        generate_discussion_script(
            topics=["Bitcoin news"],
            personas=[
                {"name": "Alex", "traits": "skeptical"},
                {"name": "Jordan", "traits": "optimistic"}
            ]
        )


@patch('ai_radio.show_generator.config')
@patch('ai_radio.show_generator.genai.Client')
def test_generate_discussion_script_invalid_format(mock_client_class, mock_config):
    """Test that response without speaker tags raises ValueError."""
    # Mock API key
    mock_api_key = Mock()
    mock_api_key.get_secret_value.return_value = "fake-api-key"
    mock_config.api_keys.gemini_api_key = mock_api_key

    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = "This is just plain text without any speaker tags."
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(ValueError, match="No speaker tags found in response"):
        generate_discussion_script(
            topics=["Bitcoin news"],
            personas=[
                {"name": "Alex", "traits": "skeptical"},
                {"name": "Jordan", "traits": "optimistic"}
            ]
        )


@patch('ai_radio.show_generator.subprocess.run')
@patch('ai_radio.show_generator.config')
@patch('ai_radio.show_generator.genai.Client')
def test_synthesize_show_audio(mock_client_class, mock_config, mock_subprocess):
    """Test synthesizing multi-speaker audio from script."""
    # Mock API key
    mock_api_key = Mock()
    mock_api_key.get_secret_value.return_value = "fake-api-key"
    mock_config.api_keys.gemini_api_key = mock_api_key

    # Mock TTS config
    mock_config.tts.gemini_tts_model = "gemini-2.5-flash-preview-tts"
    mock_config.paths.beds_dir_resolved = None  # No beds for this test

    # Mock Gemini API response with audio data
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_part = Mock()
    mock_part.inline_data.data = b"fake_pcm_audio_data"
    mock_response.candidates = [Mock(content=Mock(parts=[mock_part]))]
    mock_client.models.generate_content.return_value = mock_response

    # Mock subprocess (ffmpeg and ffprobe) - success
    # First call is pcm->mp3 conversion, second would be ffprobe for duration
    mock_subprocess.return_value = Mock(returncode=0, stderr="", stdout="3.2")

    # Call function
    script = "[speaker: Sarah] Hello!\n[speaker: Dr. Chen] Hi there!"
    personas = [
        {"name": "Sarah", "traits": "engaging"},
        {"name": "Dr. Chen", "traits": "analytical"}
    ]
    output_path = Path("/tmp/test_audio.mp3")

    result = synthesize_show_audio(script, personas, output_path)

    # Verify result
    assert isinstance(result, AudioFile)
    assert result.file_path == output_path
    assert result.voice == "Sarah, Dr. Chen"
    assert result.model == "gemini-2.5-flash-preview-tts"
    assert result.duration_estimate > 0


def test_synthesize_show_audio_empty_script():
    """Test that empty script text raises ValueError."""
    personas = [
        {"name": "Sarah", "traits": "engaging"},
        {"name": "Dr. Chen", "traits": "analytical"}
    ]
    output_path = Path("/tmp/test_audio.mp3")

    with pytest.raises(ValueError, match="Cannot synthesize empty script"):
        synthesize_show_audio("", personas, output_path)

    with pytest.raises(ValueError, match="Cannot synthesize empty script"):
        synthesize_show_audio("   ", personas, output_path)


def test_synthesize_show_audio_no_speaker_tags():
    """Test that script without speaker tags raises ValueError."""
    script = "This is just plain text without any speaker tags."
    personas = [
        {"name": "Sarah", "traits": "engaging"},
        {"name": "Dr. Chen", "traits": "analytical"}
    ]
    output_path = Path("/tmp/test_audio.mp3")

    with pytest.raises(ValueError, match="No speaker tags found in script"):
        synthesize_show_audio(script, personas, output_path)


def test_synthesize_show_audio_empty_personas():
    """Test that empty personas list raises ValueError."""
    script = "[speaker: Sarah] Hello!"
    output_path = Path("/tmp/test_audio.mp3")

    with pytest.raises(ValueError, match="Cannot synthesize without personas"):
        synthesize_show_audio(script, [], output_path)


@patch('ai_radio.show_generator.config')
def test_synthesize_show_audio_missing_api_key(mock_config):
    """Test that missing API key raises ValueError."""
    mock_config.api_keys.gemini_api_key = None

    script = "[speaker: Sarah] Hello!"
    personas = [{"name": "Sarah", "traits": "engaging"}]
    output_path = Path("/tmp/test_audio.mp3")

    with pytest.raises(ValueError, match="RADIO_GEMINI_API_KEY not configured"):
        synthesize_show_audio(script, personas, output_path)


@patch('ai_radio.show_generator.subprocess.run')
@patch('ai_radio.show_generator.config')
@patch('ai_radio.show_generator.genai.Client')
def test_synthesize_show_audio_api_failure(mock_client_class, mock_config, mock_subprocess):
    """Test that API failure raises RuntimeError."""
    # Mock API key
    mock_api_key = Mock()
    mock_api_key.get_secret_value.return_value = "fake-api-key"
    mock_config.api_keys.gemini_api_key = mock_api_key

    # Mock API failure
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.side_effect = Exception("API connection failed")

    script = "[speaker: Sarah] Hello!"
    personas = [{"name": "Sarah", "traits": "engaging"}]
    output_path = Path("/tmp/test_audio.mp3")

    with pytest.raises(RuntimeError, match="Failed to synthesize audio"):
        synthesize_show_audio(script, personas, output_path)


@patch('ai_radio.show_generator.subprocess.run')
@patch('ai_radio.show_generator.config')
@patch('ai_radio.show_generator.genai.Client')
def test_synthesize_show_audio_ffmpeg_failure(mock_client_class, mock_config, mock_subprocess):
    """Test that ffmpeg conversion failure raises RuntimeError."""
    # Mock API key
    mock_api_key = Mock()
    mock_api_key.get_secret_value.return_value = "fake-api-key"
    mock_config.api_keys.gemini_api_key = mock_api_key

    # Mock Gemini API response with audio data
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_part = Mock()
    mock_part.inline_data.data = b"fake_pcm_audio_data"
    mock_response.candidates = [Mock(content=Mock(parts=[mock_part]))]
    mock_client.models.generate_content.return_value = mock_response

    # Mock subprocess (ffmpeg) - failure
    mock_subprocess.return_value = Mock(returncode=1, stderr="ffmpeg error: invalid format")

    script = "[speaker: Sarah] Hello!"
    personas = [{"name": "Sarah", "traits": "engaging"}]
    output_path = Path("/tmp/test_audio.mp3")

    with pytest.raises(RuntimeError, match="Failed to synthesize audio"):
        synthesize_show_audio(script, personas, output_path)


# Tests for find_exact_phrase_timestamps()
def test_find_exact_phrase_timestamps_perfect_match():
    """Test exact phrase matching with perfect STT transcription."""
    from ai_radio.show_generator import find_exact_phrase_timestamps

    word_timestamps = [
        {'word': 'Hello', 'start': 0.0, 'end': 0.5},
        {'word': 'everyone', 'start': 0.5, 'end': 1.0},
        {'word': 'Nice', 'start': 5.0, 'end': 5.3},
        {'word': 'try', 'start': 5.3, 'end': 5.6},
        {'word': 'corps', 'start': 5.6, 'end': 6.0},
        {'word': 'Back', 'start': 10.0, 'end': 10.3},
        {'word': 'to', 'start': 10.3, 'end': 10.5},
        {'word': 'topic', 'start': 10.5, 'end': 11.0},
    ]

    acknowledgment_phrases = [
        {'phrase': 'Nice try corps', 'timestamp': None, 'follows_segment': 1}
    ]

    result = find_exact_phrase_timestamps(word_timestamps, acknowledgment_phrases)

    assert len(result) == 1
    assert result[0]['timestamp'] == 5.0
    assert result[0]['phrase'] == 'Nice try corps'


def test_find_exact_phrase_timestamps_with_stt_errors():
    """Test fuzzy matching handles STT transcription errors."""
    from ai_radio.show_generator import find_exact_phrase_timestamps

    # STT mistranscribed "corps" as "corpse"
    word_timestamps = [
        {'word': 'Hello', 'start': 0.0, 'end': 0.5},
        {'word': 'everyone', 'start': 0.5, 'end': 1.0},
        {'word': 'Nice', 'start': 5.0, 'end': 5.3},
        {'word': 'try', 'start': 5.3, 'end': 5.6},
        {'word': 'corpse', 'start': 5.6, 'end': 6.0},  # STT error
        {'word': 'Back', 'start': 10.0, 'end': 10.3},
        {'word': 'to', 'start': 10.3, 'end': 10.5},
        {'word': 'topic', 'start': 10.5, 'end': 11.0},
    ]

    acknowledgment_phrases = [
        {'phrase': 'Nice try corps', 'timestamp': None, 'follows_segment': 1}
    ]

    result = find_exact_phrase_timestamps(word_timestamps, acknowledgment_phrases, threshold=85)

    assert len(result) == 1
    assert result[0]['timestamp'] == 5.0
    assert result[0]['phrase'] == 'Nice try corps'


def test_find_exact_phrase_timestamps_with_emotion_tags():
    """Test phrase matching strips emotion tags before matching."""
    from ai_radio.show_generator import find_exact_phrase_timestamps

    word_timestamps = [
        {'word': 'Damn', 'start': 5.0, 'end': 5.3},
        {'word': 'corp', 'start': 5.3, 'end': 5.6},
        {'word': 'jammers', 'start': 5.6, 'end': 6.0},
        {'word': 'where', 'start': 6.5, 'end': 6.7},
        {'word': 'was', 'start': 6.7, 'end': 6.9},
        {'word': 'I', 'start': 6.9, 'end': 7.0},
    ]

    acknowledgment_phrases = [
        {'phrase': '[frustrated] Damn corp jammers... where was I?', 'timestamp': None, 'follows_segment': 1}
    ]

    result = find_exact_phrase_timestamps(word_timestamps, acknowledgment_phrases)

    assert len(result) == 1
    assert result[0]['timestamp'] == 5.0


def test_find_exact_phrase_timestamps_constrained_search():
    """Test sequential search finds first occurrence when starting from beginning."""
    from ai_radio.show_generator import find_exact_phrase_timestamps

    # Same phrase appears twice at 2.0s and 8.0s
    # Sequential search starts from 0.0s, so should find first occurrence at 2.0s
    word_timestamps = [
        {'word': 'Nice', 'start': 2.0, 'end': 2.3},
        {'word': 'try', 'start': 2.3, 'end': 2.6},
        {'word': 'corps', 'start': 2.6, 'end': 3.0},
        {'word': 'More', 'start': 3.5, 'end': 4.0},
        {'word': 'content', 'start': 4.0, 'end': 4.5},
        {'word': 'Nice', 'start': 8.0, 'end': 8.3},
        {'word': 'try', 'start': 8.3, 'end': 8.6},
        {'word': 'corps', 'start': 8.6, 'end': 9.0},
    ]

    acknowledgment_phrases = [
        {'phrase': 'Nice try corps', 'timestamp': None, 'follows_segment': 1}
    ]

    result = find_exact_phrase_timestamps(word_timestamps, acknowledgment_phrases)

    # Should find the first occurrence (sequential search starts from 0.0s)
    assert len(result) == 1
    assert result[0]['timestamp'] == 2.0


def test_find_exact_phrase_timestamps_multiple_phrases():
    """Test matching multiple acknowledgment phrases."""
    from ai_radio.show_generator import find_exact_phrase_timestamps

    word_timestamps = [
        {'word': 'Hello', 'start': 0.0, 'end': 0.5},
        {'word': 'Nice', 'start': 5.0, 'end': 5.3},
        {'word': 'try', 'start': 5.3, 'end': 5.6},
        {'word': 'corps', 'start': 5.6, 'end': 6.0},
        {'word': 'More', 'start': 10.0, 'end': 10.5},
        {'word': 'words', 'start': 10.5, 'end': 11.0},
        {'word': 'Damn', 'start': 15.0, 'end': 15.3},
        {'word': 'jammers', 'start': 15.3, 'end': 15.8},
    ]

    acknowledgment_phrases = [
        {'phrase': 'Nice try corps', 'timestamp': None, 'follows_segment': 1},
        {'phrase': 'Damn jammers', 'timestamp': None, 'follows_segment': 3}
    ]

    result = find_exact_phrase_timestamps(word_timestamps, acknowledgment_phrases)

    assert len(result) == 2
    assert result[0]['timestamp'] == 5.0
    assert result[1]['timestamp'] == 15.0


def test_find_exact_phrase_timestamps_phrase_not_found():
    """Test graceful failure when phrase not found in transcript."""
    from ai_radio.show_generator import find_exact_phrase_timestamps

    word_timestamps = [
        {'word': 'Hello', 'start': 0.0, 'end': 0.5},
        {'word': 'everyone', 'start': 0.5, 'end': 1.0},
    ]

    acknowledgment_phrases = [
        {'phrase': 'Nice try corps', 'timestamp': None, 'follows_segment': 1}
    ]

    result = find_exact_phrase_timestamps(word_timestamps, acknowledgment_phrases)

    # Should return phrase with timestamp still None
    assert len(result) == 1
    assert result[0]['timestamp'] is None
    assert result[0]['phrase'] == 'Nice try corps'


def test_find_exact_phrase_timestamps_flexible_window():
    """Test flexible N±1 word window matching."""
    from ai_radio.show_generator import find_exact_phrase_timestamps

    # Phrase is 4 words, should match in 3-5 word windows
    word_timestamps = [
        {'word': 'Damn', 'start': 5.0, 'end': 5.3},
        {'word': 'those', 'start': 5.3, 'end': 5.5},  # Extra word
        {'word': 'corp', 'start': 5.5, 'end': 5.7},
        {'word': 'jammers', 'start': 5.7, 'end': 6.0},
        {'word': 'again', 'start': 6.0, 'end': 6.3},
    ]

    acknowledgment_phrases = [
        {'phrase': 'Damn corp jammers again', 'timestamp': None, 'follows_segment': 1}
    ]

    result = find_exact_phrase_timestamps(word_timestamps, acknowledgment_phrases, threshold=85)

    # Should match even with "those" inserted
    assert len(result) == 1
    assert result[0]['timestamp'] == 5.0


def test_find_exact_phrase_timestamps_with_punctuation():
    """Test phrase matching ignores punctuation."""
    from ai_radio.show_generator import find_exact_phrase_timestamps

    word_timestamps = [
        {'word': 'Nice', 'start': 5.0, 'end': 5.3},
        {'word': 'try,', 'start': 5.3, 'end': 5.6},  # With comma
        {'word': 'corps!', 'start': 5.6, 'end': 6.0},  # With exclamation
    ]

    acknowledgment_phrases = [
        {'phrase': 'Nice try, corps!', 'timestamp': None, 'follows_segment': 1}
    ]

    result = find_exact_phrase_timestamps(word_timestamps, acknowledgment_phrases)

    assert len(result) == 1
    assert result[0]['timestamp'] == 5.0


def test_find_exact_phrase_timestamps_sequential_search_prevents_false_matches():
    """Test sequential search prevents matching same phrase twice when it appears multiple times."""
    from ai_radio.show_generator import find_exact_phrase_timestamps

    # "Nice try corps" appears at 2.0s and 10.0s
    # Two acknowledgments should match BOTH occurrences: first at 2.0s, second at 10.0s
    # Without sequential search, both would match 2.0s (first match always wins)
    word_timestamps = [
        {'word': 'Nice', 'start': 2.0, 'end': 2.3},
        {'word': 'try', 'start': 2.3, 'end': 2.6},
        {'word': 'corps', 'start': 2.6, 'end': 3.0},
        {'word': 'Some', 'start': 3.5, 'end': 4.0},
        {'word': 'content', 'start': 4.0, 'end': 4.5},
        {'word': 'here', 'start': 4.5, 'end': 5.0},
        {'word': 'More', 'start': 6.0, 'end': 6.5},
        {'word': 'content', 'start': 6.5, 'end': 7.0},
        {'word': 'Nice', 'start': 10.0, 'end': 10.3},
        {'word': 'try', 'start': 10.3, 'end': 10.6},
        {'word': 'corps', 'start': 10.6, 'end': 11.0},
    ]

    acknowledgment_phrases = [
        {'phrase': 'Nice try corps', 'timestamp': None, 'follows_segment': 1},
        {'phrase': 'Nice try corps', 'timestamp': None, 'follows_segment': 3}
    ]

    result = find_exact_phrase_timestamps(word_timestamps, acknowledgment_phrases)

    # First phrase should match at 2.0s
    # Second phrase should search starting 2s after first match (4.0s+) and find at 10.0s
    assert len(result) == 2
    assert result[0]['timestamp'] == 2.0
    assert result[0]['phrase'] == 'Nice try corps'
    assert result[1]['timestamp'] == 10.0, f"Expected second phrase at 10.0s but got {result[1]['timestamp']}"
    assert result[1]['phrase'] == 'Nice try corps'
