"""Tests for Liquidsoap Unix socket client"""
import socket
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from ai_radio.liquidsoap_client import LiquidsoapClient


def test_liquidsoap_client_send_command_success():
    """Test successful command sending to Liquidsoap"""
    client = LiquidsoapClient()

    with patch('socket.socket') as mock_socket_class:
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock
        # Mock the context manager
        mock_sock.__enter__.return_value = mock_sock
        mock_sock.__exit__.return_value = None
        mock_sock.recv.return_value = b"OK\nEND\n"

        with patch.object(Path, 'exists', return_value=True):
            response = client.send_command("help")

        assert response == "OK\nEND"
        mock_sock.connect.assert_called_once()
        mock_sock.sendall.assert_called_once_with(b"help\n")


def test_liquidsoap_client_send_command_timeout():
    """Test socket timeout handling"""
    client = LiquidsoapClient()

    with patch('socket.socket') as mock_socket_class:
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock
        # Mock the context manager
        mock_sock.__enter__.return_value = mock_sock
        mock_sock.__exit__.return_value = None
        mock_sock.recv.side_effect = socket.timeout()

        with patch.object(Path, 'exists', return_value=True):
            with pytest.raises(ConnectionError, match="timeout"):
                client.send_command("help")


def test_liquidsoap_client_send_command_socket_not_found():
    """Test error when socket file doesn't exist"""
    client = LiquidsoapClient()

    with patch.object(Path, 'exists', return_value=False):
        with pytest.raises(ConnectionError, match="not found"):
            client.send_command("help")


def test_liquidsoap_client_get_queue_length_success():
    """Test getting queue length with valid response"""
    client = LiquidsoapClient()

    # Simulate Liquidsoap response with 3 tracks (space-separated IDs)
    mock_response = "123 124 125\nEND\n"

    with patch.object(client, 'send_command', return_value=mock_response):
        length = client.get_queue_length("music")

    assert length == 3


def test_liquidsoap_client_get_queue_length_empty():
    """Test getting queue length for empty queue"""
    client = LiquidsoapClient()

    with patch.object(client, 'send_command', return_value="END\n"):
        length = client.get_queue_length("music")

    assert length == 0


def test_liquidsoap_client_get_queue_length_connection_error():
    """Test get_queue_length returns -1 on connection error"""
    client = LiquidsoapClient()

    with patch.object(client, 'send_command', side_effect=ConnectionError("test")):
        length = client.get_queue_length("music")

    assert length == -1


def test_liquidsoap_client_push_track_success():
    """Test successfully pushing track to queue"""
    client = LiquidsoapClient()

    with patch.object(client, 'send_command', return_value="OK"):
        result = client.push_track("music", "/path/to/track.mp3")

    assert result is True


def test_liquidsoap_client_push_track_error():
    """Test push_track returns False on error response"""
    client = LiquidsoapClient()

    with patch.object(client, 'send_command', return_value="ERROR: invalid file"):
        result = client.push_track("music", "/path/to/track.mp3")

    assert result is False


def test_liquidsoap_client_push_track_connection_error():
    """Test push_track returns False on connection error"""
    client = LiquidsoapClient()

    with patch.object(client, 'send_command', side_effect=ConnectionError("test")):
        result = client.push_track("music", "/path/to/track.mp3")

    assert result is False
