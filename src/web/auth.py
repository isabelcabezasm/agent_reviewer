"""Authentication module for the Agent Reviewer API and Web UI.

Provides API key validation for REST endpoints and session-based
authentication for the web interface. The API key is configured
via the AGENT_REVIEWER_API_KEY environment variable.
"""

import hashlib
import hmac
import os
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, APIKeyQuery


# ---------------------------------------------------------------------------
# API Key configuration
# ---------------------------------------------------------------------------

def get_api_key() -> str:
    """Get the configured API key from environment.

    Returns:
        str: The API key, or empty string if not set.
    """
    return os.getenv("AGENT_REVIEWER_API_KEY", "")


def is_auth_enabled() -> bool:
    """Check if authentication is enabled.

    Authentication is enabled when AGENT_REVIEWER_API_KEY is set
    and non-empty.

    Returns:
        bool: True if auth is enabled.
    """
    return bool(get_api_key())


# ---------------------------------------------------------------------------
# API Key authentication (for REST endpoints)
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_api_key_query = APIKeyQuery(name="api_key", auto_error=False)


def _constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks.

    Parameters:
        a: First string.
        b: Second string.

    Returns:
        bool: True if the strings are equal.
    """
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


async def verify_api_key(
    request: Request,
    header_key: Annotated[str | None, Depends(_api_key_header)] = None,
    query_key: Annotated[str | None, Depends(_api_key_query)] = None,
) -> str | None:
    """Validate the API key from header, query parameter, or session cookie.

    If authentication is disabled (no AGENT_REVIEWER_API_KEY set),
    all requests are allowed through.

    The key can be provided via:
    - Header: X-API-Key: <key>
    - Query: ?api_key=<key>
    - Session cookie (set by the Web UI login page)

    Parameters:
        request: The incoming HTTP request (for cookie access).
        header_key: API key from X-API-Key header.
        query_key: API key from api_key query parameter.

    Returns:
        The validated API key, or None if auth is disabled.

    Raises:
        HTTPException: 401 if the key is missing or invalid.
    """
    expected_key = get_api_key()

    # If no API key is configured, auth is disabled
    if not expected_key:
        return None

    # Check API key from header or query
    provided_key = header_key or query_key
    if provided_key and _constant_time_compare(provided_key, expected_key):
        return provided_key

    # Also accept a valid session cookie (for Web UI)
    session_token = request.cookies.get("session_token", "")
    if session_token and validate_session(session_token):
        return None

    if provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing API key. Provide via X-API-Key header or api_key query parameter.",
    )

    return provided_key


# ---------------------------------------------------------------------------
# Session-based authentication (for Web UI)
# ---------------------------------------------------------------------------

# In-memory session store (simple for single-instance deployment)
_active_sessions: dict[str, bool] = {}


def create_session() -> str:
    """Create a new authenticated session.

    Returns:
        str: A secure random session token.
    """
    token = secrets.token_urlsafe(32)
    # Store hash of token for security
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    _active_sessions[token_hash] = True
    return token


def validate_session(token: str) -> bool:
    """Check if a session token is valid.

    Parameters:
        token: The session token to validate.

    Returns:
        bool: True if the session is valid.
    """
    if not token:
        return False
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return _active_sessions.get(token_hash, False)


def invalidate_session(token: str) -> None:
    """Remove a session token.

    Parameters:
        token: The session token to invalidate.
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    _ = _active_sessions.pop(token_hash, None)


async def verify_web_session(request: Request) -> bool:
    """Validate session from cookie for web UI routes.

    If authentication is disabled, all requests pass through.

    Parameters:
        request: The incoming HTTP request.

    Returns:
        bool: True if authenticated or auth is disabled.

    Raises:
        HTTPException: 401 if session is invalid.
    """
    if not is_auth_enabled():
        return True

    token = request.cookies.get("session_token", "")
    if not validate_session(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
        )
    return True
