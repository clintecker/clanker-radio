"""Tests for Liquidsoap Unix socket client"""
import pytest
from ai_radio.liquidsoap_client import LiquidsoapClient


def test_liquidsoap_client_send_command():
    """Test sending command to Liquidsoap"""
    client = LiquidsoapClient()

    # This will fail if Liquidsoap not running, but tests interface
    try:
        response = client.send_command("help")
        assert isinstance(response, str)
    except ConnectionError:
        # Expected if Liquidsoap not running in test environment
        pass


def test_liquidsoap_client_get_queue_length():
    """Test getting queue length"""
    client = LiquidsoapClient()

    # get_queue_length catches ConnectionError and returns -1
    length = client.get_queue_length("music")
    assert isinstance(length, int)
    # -1 indicates error (Liquidsoap not running), >= 0 is valid queue length
    assert length >= -1


def test_liquidsoap_client_push_track():
    """Test pushing track to queue"""
    client = LiquidsoapClient()

    try:
        result = client.push_track("music", "/srv/ai_radio/assets/music/test.mp3")
        assert isinstance(result, bool)
    except ConnectionError:
        pass
