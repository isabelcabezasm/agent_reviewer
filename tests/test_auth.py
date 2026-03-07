"""Tests for the authentication module."""

import os
from unittest.mock import patch

from src.web.auth import (
    create_session,
    invalidate_session,
    is_auth_enabled,
    validate_session,
)


class TestIsAuthEnabled:
    """Tests for the is_auth_enabled function."""

    @patch.dict(os.environ, {"AGENT_REVIEWER_API_KEY": "test-key"})
    def test_returns_true_when_key_set(self) -> None:
        """Test that auth is enabled when key is configured."""
        assert is_auth_enabled() is True

    @patch.dict(os.environ, {"AGENT_REVIEWER_API_KEY": ""})
    def test_returns_false_when_key_empty(self) -> None:
        """Test that auth is disabled when key is empty."""
        assert is_auth_enabled() is False

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_false_when_key_missing(self) -> None:
        """Test that auth is disabled when key is not set."""
        assert is_auth_enabled() is False


class TestSessionManagement:
    """Tests for session create/validate/invalidate."""

    def test_create_and_validate_session(self) -> None:
        """Test that a created session is valid."""
        token = create_session()
        assert token
        assert validate_session(token) is True

    def test_invalid_session_rejected(self) -> None:
        """Test that a random token is rejected."""
        assert validate_session("fake-token-123") is False

    def test_empty_session_rejected(self) -> None:
        """Test that empty token is rejected."""
        assert validate_session("") is False

    def test_invalidate_session(self) -> None:
        """Test that invalidated session is no longer valid."""
        token = create_session()
        assert validate_session(token) is True
        invalidate_session(token)
        assert validate_session(token) is False

    def test_invalidate_nonexistent_session(self) -> None:
        """Test that invalidating a nonexistent session doesn't raise."""
        invalidate_session("nonexistent-token")
