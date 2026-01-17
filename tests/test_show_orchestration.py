"""Tests for ShowGenerator orchestration logic.

These tests validate the complete pipeline from research → script → audio → ingest → database.
The ShowGenerator orchestrates the entire flow and handles state machine transitions.
"""
import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, call, ANY

from ai_radio.show_models import ShowSchedule, GeneratedShow
from ai_radio.voice_synth import AudioFile
from ai_radio.show_generator import ShowGenerator


@pytest.fixture
def mock_repository():
    """Create mock repository with update methods."""
    repo = Mock()
    repo.update_show_status = Mock()
    repo.update_show_script = Mock()
    repo.update_show_asset = Mock()
    repo.update_show_error = Mock()
    return repo


@pytest.fixture
def interview_schedule():
    """Create sample interview show schedule."""
    return ShowSchedule(
        id=1,
        name="Tech Talk",
        format="interview",
        topic_area="AI developments",
        days_of_week=json.dumps([1, 3, 5]),
        start_time="14:00",
        duration_minutes=8,
        timezone="America/Chicago",
        personas=json.dumps([
            {"name": "Sarah", "traits": "curious, engaging host"},
            {"name": "Dr. Chen", "traits": "analytical blockchain expert"}
        ]),
        content_guidance="Latest AI news and ethical implications",
        regenerate_daily=True,
        active=True,
        created_at="2026-01-17 10:00:00",
        updated_at="2026-01-17 10:00:00"
    )


@pytest.fixture
def discussion_schedule():
    """Create sample discussion show schedule."""
    return ShowSchedule(
        id=2,
        name="Crypto Debates",
        format="two_host_discussion",
        topic_area="Bitcoin news",
        days_of_week=json.dumps([2, 4]),
        start_time="16:00",
        duration_minutes=10,
        timezone="America/Chicago",
        personas=json.dumps([
            {"name": "Alex", "traits": "skeptical, idealistic, questions mainstream narratives"},
            {"name": "Jordan", "traits": "optimistic, pragmatic, focuses on real-world adoption"}
        ]),
        content_guidance="Controversial takes on cryptocurrency",
        regenerate_daily=True,
        active=True,
        created_at="2026-01-17 10:00:00",
        updated_at="2026-01-17 10:00:00"
    )


@pytest.fixture
def pending_show():
    """Create pending generated show."""
    return GeneratedShow(
        id=1,
        schedule_id=1,
        air_date="2026-01-18",
        status="pending",
        retry_count=0,
        script_text=None,
        asset_id=None,
        generated_at=None,
        error_message=None,
        created_at="2026-01-17 12:00:00",
        updated_at="2026-01-17 12:00:00"
    )


@pytest.fixture
def script_complete_show():
    """Create show with completed script."""
    return GeneratedShow(
        id=2,
        schedule_id=1,
        air_date="2026-01-18",
        status="script_complete",
        retry_count=0,
        script_text="[speaker: Sarah] Welcome to the show!\n[speaker: Dr. Chen] Thanks for having me!",
        asset_id=None,
        generated_at="2026-01-17 12:30:00",
        error_message=None,
        created_at="2026-01-17 12:00:00",
        updated_at="2026-01-17 12:30:00"
    )


@patch('ai_radio.show_generator.ingest_audio_file')
@patch('ai_radio.show_generator.synthesize_show_audio')
@patch('ai_radio.show_generator.generate_interview_script')
@patch('ai_radio.show_generator.generate_discussion_script')
@patch('ai_radio.show_generator.research_topics')
def test_generate_interview_happy_path(
    mock_research,
    mock_discussion,
    mock_interview,
    mock_synthesize,
    mock_ingest,
    mock_repository,
    interview_schedule,
    pending_show
):
    """Test complete interview show generation from pending to ready.

    Given: A pending show with format='interview'
    Verifies:
    - research_topics called with schedule's topic_area and content_guidance
    - generate_interview_script called (NOT generate_discussion_script)
    - synthesize_show_audio called with script and personas
    - ingest_audio_file called with kind='break'
    - Database updates: pending → script_complete → ready
    """
    # Setup mocks
    mock_research.return_value = [
        "AI Ethics Debate: Should we pause development?",
        "OpenAI releases GPT-5 with reasoning capabilities",
        "EU passes comprehensive AI regulation"
    ]

    mock_interview.return_value = "[speaker: Sarah] Welcome!\n[speaker: Dr. Chen] Thanks!"

    mock_audio_file = AudioFile(
        file_path=Path("/tmp/show_audio.mp3"),
        duration_estimate=420.0,
        timestamp=datetime(2026, 1, 17, 12, 30),
        voice="Sarah, Dr. Chen",
        model="gemini-2.5-flash-preview-tts"
    )
    mock_synthesize.return_value = mock_audio_file

    mock_ingest.return_value = {"id": "abc123def456", "path": "/path/to/asset.mp3"}  # Asset dict

    # Create generator and execute
    generator = ShowGenerator(mock_repository)
    generator.generate(interview_schedule, pending_show)

    # Verify research was called with schedule parameters
    mock_research.assert_called_once_with(
        topic_area="AI developments",
        content_guidance="Latest AI news and ethical implications"
    )

    # Verify interview script was generated (NOT discussion)
    personas = [
        {"name": "Sarah", "traits": "curious, engaging host"},
        {"name": "Dr. Chen", "traits": "analytical blockchain expert"}
    ]
    mock_interview.assert_called_once_with(
        topics=mock_research.return_value,
        personas=personas
    )
    mock_discussion.assert_not_called()

    # Verify audio synthesis
    mock_synthesize.assert_called_once_with(
        script_text=mock_interview.return_value,
        personas=personas,
        output_path=ANY  # Path will be generated
    )

    # Verify audio ingestion with kind='break'
    mock_ingest.assert_called_once()
    call_args = mock_ingest.call_args
    assert call_args[1]['kind'] == 'break' or call_args[0][1] == 'break'

    # Verify database updates for state transitions
    update_calls = mock_repository.update_show_status.call_args_list
    assert len(update_calls) == 2

    # First update: pending → script_complete
    assert update_calls[0] == call(pending_show.id, 'script_complete')

    # Second update: script_complete → ready
    assert update_calls[1] == call(pending_show.id, 'ready')

    # Verify script was saved
    mock_repository.update_show_script.assert_called_once_with(
        pending_show.id,
        mock_interview.return_value
    )

    # Verify asset ID was saved
    mock_repository.update_show_asset.assert_called_once_with(
        pending_show.id,
        "abc123def456"
    )


@patch('ai_radio.show_generator.ingest_audio_file')
@patch('ai_radio.show_generator.synthesize_show_audio')
@patch('ai_radio.show_generator.generate_interview_script')
@patch('ai_radio.show_generator.generate_discussion_script')
@patch('ai_radio.show_generator.research_topics')
def test_generate_discussion_happy_path(
    mock_research,
    mock_discussion,
    mock_interview,
    mock_synthesize,
    mock_ingest,
    mock_repository,
    discussion_schedule,
    pending_show
):
    """Test complete discussion show generation from pending to ready.

    Given: A pending show with format='two_host_discussion'
    Verifies:
    - research_topics called with schedule's topic_area and content_guidance
    - generate_discussion_script called (NOT generate_interview_script)
    - synthesize_show_audio called with script and personas
    - ingest_audio_file called with kind='break'
    - Database updates: pending → script_complete → ready
    """
    # Setup mocks
    mock_research.return_value = [
        "Bitcoin hits new all-time high above $100k",
        "SEC approves Bitcoin ETFs",
        "Institutional adoption accelerates"
    ]

    mock_discussion.return_value = "[speaker: Alex] I think this is concerning.\n[speaker: Jordan] I disagree!"

    mock_audio_file = AudioFile(
        file_path=Path("/tmp/discussion_audio.mp3"),
        duration_estimate=540.0,
        timestamp=datetime(2026, 1, 17, 14, 0),
        voice="Alex, Jordan",
        model="gemini-2.5-flash-preview-tts"
    )
    mock_synthesize.return_value = mock_audio_file

    mock_ingest.return_value = {"id": "fedcba987654", "path": "/path/to/discussion.mp3"}

    # Create generator and execute
    generator = ShowGenerator(mock_repository)
    generator.generate(discussion_schedule, pending_show)

    # Verify research
    mock_research.assert_called_once_with(
        topic_area="Bitcoin news",
        content_guidance="Controversial takes on cryptocurrency"
    )

    # Verify discussion script was generated (NOT interview)
    personas = [
        {"name": "Alex", "traits": "skeptical, idealistic, questions mainstream narratives"},
        {"name": "Jordan", "traits": "optimistic, pragmatic, focuses on real-world adoption"}
    ]
    mock_discussion.assert_called_once_with(
        topics=mock_research.return_value,
        personas=personas
    )
    mock_interview.assert_not_called()

    # Verify audio synthesis
    mock_synthesize.assert_called_once_with(
        script_text=mock_discussion.return_value,
        personas=personas,
        output_path=ANY
    )

    # Verify ingestion
    mock_ingest.assert_called_once()

    # Verify database state transitions
    update_calls = mock_repository.update_show_status.call_args_list
    assert len(update_calls) == 2
    assert update_calls[0] == call(pending_show.id, 'script_complete')
    assert update_calls[1] == call(pending_show.id, 'ready')

    # Verify script and asset saved
    mock_repository.update_show_script.assert_called_once()
    mock_repository.update_show_asset.assert_called_once()


@patch('ai_radio.show_generator.ingest_audio_file')
@patch('ai_radio.show_generator.synthesize_show_audio')
@patch('ai_radio.show_generator.generate_interview_script')
@patch('ai_radio.show_generator.generate_discussion_script')
@patch('ai_radio.show_generator.research_topics')
def test_resume_from_script_complete(
    mock_research,
    mock_discussion,
    mock_interview,
    mock_synthesize,
    mock_ingest,
    mock_repository,
    interview_schedule,
    script_complete_show
):
    """Test resuming generation from script_complete state.

    Given: A show with status='script_complete' and existing script_text
    Verifies:
    - research_topics NOT called (skip research phase)
    - generate_*_script NOT called (skip script generation phase)
    - synthesize_show_audio called with EXISTING script from show.script_text
    - ingest_audio_file called
    - Database update: script_complete → ready (single transition)
    """
    # Setup mocks for audio synthesis only
    mock_audio_file = AudioFile(
        file_path=Path("/tmp/resumed_audio.mp3"),
        duration_estimate=300.0,
        timestamp=datetime(2026, 1, 17, 15, 0),
        voice="Sarah, Dr. Chen",
        model="gemini-2.5-flash-preview-tts"
    )
    mock_synthesize.return_value = mock_audio_file

    mock_ingest.return_value = {"id": "123abc456def", "path": "/path/to/resumed.mp3"}

    # Create generator and execute
    generator = ShowGenerator(mock_repository)
    generator.generate(interview_schedule, script_complete_show)

    # Verify research and script generation were SKIPPED
    mock_research.assert_not_called()
    mock_interview.assert_not_called()
    mock_discussion.assert_not_called()

    # Verify synthesis used EXISTING script
    personas = [
        {"name": "Sarah", "traits": "curious, engaging host"},
        {"name": "Dr. Chen", "traits": "analytical blockchain expert"}
    ]
    mock_synthesize.assert_called_once_with(
        script_text=script_complete_show.script_text,  # Existing script!
        personas=personas,
        output_path=ANY
    )

    # Verify ingestion still happened
    mock_ingest.assert_called_once()

    # Verify ONLY ONE status update (script_complete → ready)
    mock_repository.update_show_status.assert_called_once_with(
        script_complete_show.id,
        'ready'
    )

    # Script should NOT be updated (already exists)
    mock_repository.update_show_script.assert_not_called()

    # Asset ID should be saved
    mock_repository.update_show_asset.assert_called_once_with(
        script_complete_show.id,
        "123abc456def"
    )


@patch('ai_radio.show_generator.ingest_audio_file')
@patch('ai_radio.show_generator.synthesize_show_audio')
@patch('ai_radio.show_generator.generate_interview_script')
@patch('ai_radio.show_generator.generate_discussion_script')
@patch('ai_radio.show_generator.research_topics')
def test_script_generation_failure(
    mock_research,
    mock_discussion,
    mock_interview,
    mock_synthesize,
    mock_ingest,
    mock_repository,
    interview_schedule,
    pending_show
):
    """Test handling of research/script generation failure.

    Given: A pending show where research_topics raises exception
    Verifies:
    - Exception during research_topics is caught
    - synthesize_show_audio NOT called (pipeline stops early)
    - ingest_audio_file NOT called
    - Database updated with status='script_failed' and error_message
    """
    # Setup mock to fail during research
    mock_research.side_effect = RuntimeError("Gemini API rate limit exceeded")

    # Create generator and execute
    generator = ShowGenerator(mock_repository)
    generator.generate(interview_schedule, pending_show)

    # Verify research was attempted
    mock_research.assert_called_once()

    # Verify pipeline stopped (no subsequent calls)
    mock_interview.assert_not_called()
    mock_discussion.assert_not_called()
    mock_synthesize.assert_not_called()
    mock_ingest.assert_not_called()

    # Verify error was recorded
    mock_repository.update_show_status.assert_called_once_with(
        pending_show.id,
        'script_failed'
    )

    mock_repository.update_show_error.assert_called_once()
    error_call = mock_repository.update_show_error.call_args
    assert error_call[0][0] == pending_show.id
    assert "Gemini API rate limit exceeded" in error_call[0][1]


@patch('ai_radio.show_generator.ingest_audio_file')
@patch('ai_radio.show_generator.synthesize_show_audio')
@patch('ai_radio.show_generator.generate_interview_script')
@patch('ai_radio.show_generator.generate_discussion_script')
@patch('ai_radio.show_generator.research_topics')
def test_audio_synthesis_failure(
    mock_research,
    mock_discussion,
    mock_interview,
    mock_synthesize,
    mock_ingest,
    mock_repository,
    interview_schedule,
    pending_show
):
    """Test handling of audio synthesis failure.

    Given: A pending show where synthesize_show_audio raises exception
    Verifies:
    - Script generation completes successfully
    - Database updated to script_complete with saved script
    - Exception during synthesize_show_audio is caught
    - Database then updated with status='audio_failed' and error_message
    - ingest_audio_file NOT called (no audio to ingest)
    """
    # Setup mocks - script generation succeeds, audio fails
    mock_research.return_value = ["Topic 1", "Topic 2"]
    mock_interview.return_value = "[speaker: Sarah] Hello!"

    mock_synthesize.side_effect = RuntimeError("ffmpeg conversion failed")

    # Create generator and execute
    generator = ShowGenerator(mock_repository)
    generator.generate(interview_schedule, pending_show)

    # Verify script generation completed
    mock_research.assert_called_once()
    mock_interview.assert_called_once()

    # Verify script was saved and status updated to script_complete
    mock_repository.update_show_script.assert_called_once_with(
        pending_show.id,
        mock_interview.return_value
    )

    status_calls = mock_repository.update_show_status.call_args_list
    assert call(pending_show.id, 'script_complete') in status_calls

    # Verify audio synthesis was attempted
    mock_synthesize.assert_called_once()

    # Verify ingestion was NOT called
    mock_ingest.assert_not_called()

    # Verify audio failure was recorded
    assert call(pending_show.id, 'audio_failed') in status_calls

    mock_repository.update_show_error.assert_called_once()
    error_call = mock_repository.update_show_error.call_args
    assert error_call[0][0] == pending_show.id
    assert "ffmpeg conversion failed" in error_call[0][1]


@patch('ai_radio.show_generator.ingest_audio_file')
@patch('ai_radio.show_generator.synthesize_show_audio')
@patch('ai_radio.show_generator.generate_interview_script')
@patch('ai_radio.show_generator.generate_discussion_script')
@patch('ai_radio.show_generator.research_topics')
def test_invalid_format(
    mock_research,
    mock_discussion,
    mock_interview,
    mock_synthesize,
    mock_ingest,
    mock_repository,
    interview_schedule,
    pending_show
):
    """Test handling of invalid show format.

    Given: A show with format='invalid_format' (not 'interview' or 'two_host_discussion')
    Verifies:
    - Either raises ValueError immediately
    - OR updates database with status='script_failed' and descriptive error_message
    """
    # Create schedule with invalid format
    invalid_schedule = ShowSchedule(
        id=99,
        name="Bad Format Show",
        format="invalid_format",  # Invalid!
        topic_area="Some topic",
        days_of_week=json.dumps([1, 2, 3]),
        start_time="10:00",
        duration_minutes=8,
        timezone="America/Chicago",
        personas=json.dumps([{"name": "Host", "traits": "confused"}]),
        content_guidance=None,
        regenerate_daily=True,
        active=True,
        created_at="2026-01-17 10:00:00",
        updated_at="2026-01-17 10:00:00"
    )

    # Setup mocks
    mock_research.return_value = ["Topic 1"]

    # Create generator and execute
    generator = ShowGenerator(mock_repository)

    # Two valid approaches: raise ValueError OR update DB with error
    # We test for DB error recording (more graceful)
    generator.generate(invalid_schedule, pending_show)

    # Verify research might have been attempted
    # but script generation should not proceed normally

    # Verify error was recorded
    mock_repository.update_show_status.assert_called_with(
        pending_show.id,
        'script_failed'
    )

    mock_repository.update_show_error.assert_called_once()
    error_call = mock_repository.update_show_error.call_args
    assert error_call[0][0] == pending_show.id
    error_msg = error_call[0][1].lower()
    assert "format" in error_msg or "invalid" in error_msg

    # Verify pipeline stopped
    mock_synthesize.assert_not_called()
    mock_ingest.assert_not_called()
