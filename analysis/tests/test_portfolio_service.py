"""
Tests for RAM-only session management in Portfolio Service.
"""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import portfolio_service as portfolio_svc


@pytest.fixture(autouse=True)
def reset_ram_session():
    """Ensure the RAM session is cleared before and after each test."""
    portfolio_svc._RAM_SESSION["username"] = None
    portfolio_svc._RAM_SESSION["synced_at"] = None
    portfolio_svc._RAM_SESSION["login_result"] = None
    yield
    portfolio_svc._RAM_SESSION["username"] = None
    portfolio_svc._RAM_SESSION["synced_at"] = None
    portfolio_svc._RAM_SESSION["login_result"] = None


def test_save_session_marker():
    """Verify that _save_session_marker updates RAM and not disk."""
    login_res = {"access_token": "fake_token", "token_type": "Bearer"}
    portfolio_svc._save_session_marker("test_user@example.com", login_res)

    assert portfolio_svc._RAM_SESSION["username"] == "test_user@example.com"
    assert portfolio_svc._RAM_SESSION["login_result"] == login_res
    assert isinstance(portfolio_svc._RAM_SESSION["synced_at"], datetime)
    assert not portfolio_svc.SESSION_FILE.exists()


def test_is_connected_within_24_hours():
    """Verify that is_connected returns True when active within 24 hours."""
    portfolio_svc._RAM_SESSION["username"] = "test_user@example.com"
    portfolio_svc._RAM_SESSION["synced_at"] = datetime.now() - timedelta(hours=23)

    assert portfolio_svc.is_connected() is True


def test_is_connected_expired():
    """Verify that is_connected returns False and logs out when expired."""
    portfolio_svc._RAM_SESSION["username"] = "test_user@example.com"
    portfolio_svc._RAM_SESSION["synced_at"] = datetime.now() - timedelta(hours=25)

    with patch("portfolio_service.disconnect_robinhood") as mock_disconnect, \
         patch("db.clear_robinhood_holdings") as mock_clear_holdings:
        assert portfolio_svc.is_connected() is False
        mock_disconnect.assert_called_once()
        mock_clear_holdings.assert_called_once()


def test_disconnect_robinhood_clears_ram():
    """Verify that disconnect_robinhood clears the RAM session."""
    portfolio_svc._RAM_SESSION["username"] = "test_user@example.com"
    portfolio_svc._RAM_SESSION["synced_at"] = datetime.now()
    portfolio_svc._RAM_SESSION["login_result"] = {"token": "xyz"}

    with patch("robin_stocks.robinhood.logout") as mock_logout:
        portfolio_svc.disconnect_robinhood()
        assert portfolio_svc._RAM_SESSION["username"] is None
        assert portfolio_svc._RAM_SESSION["synced_at"] is None
        assert portfolio_svc._RAM_SESSION["login_result"] is None


def test_get_session_info():
    """Verify that get_session_info correctly returns RAM state."""
    # When disconnected
    info = portfolio_svc.get_session_info()
    assert info["connected"] is False
    assert info["username"] == ""
    assert info["synced_at"] is None

    # When connected
    now_time = datetime.now()
    portfolio_svc._RAM_SESSION["username"] = "test_user@example.com"
    portfolio_svc._RAM_SESSION["synced_at"] = now_time
    info = portfolio_svc.get_session_info()
    assert info["connected"] is True
    assert info["username"] == "test_user@example.com"
    assert info["synced_at"] == now_time.isoformat()


def test_cleanup_disk_tokens_deletes_files():
    """Verify that _cleanup_disk_tokens removes session files from disk."""
    # Create a mock session file
    portfolio_svc.SESSION_FILE.parent.mkdir(exist_ok=True)
    portfolio_svc.SESSION_FILE.write_text("{}")
    assert portfolio_svc.SESSION_FILE.exists()

    tokens_dir = Path.home() / ".tokens"
    tokens_dir.mkdir(exist_ok=True)
    mock_pickle = tokens_dir / "robinhood.pickle"
    mock_pickle.write_bytes(b"mock_pickle_data")
    assert mock_pickle.exists()

    portfolio_svc._cleanup_disk_tokens()

    assert not portfolio_svc.SESSION_FILE.exists()
    assert not mock_pickle.exists()
