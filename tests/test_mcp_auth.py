"""Integration tests for the MCP HTTP server auth middleware.

Tests the bearer-token authentication middleware by sending
real HTTP requests to the ASGI app via httpx.
"""

import os
from unittest.mock import patch

import httpx
import pytest

from src.mcp_server import _build_http_app


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required Azure env vars for all tests."""
    monkeypatch.setenv("AZURE_MODEL_API_ENDPOINT", "https://test.openai.azure.com/")
    monkeypatch.setenv("AZURE_MODEL_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_MODEL_API_NAME", "gpt-5-pro")
    monkeypatch.setenv("AZURE_MODEL_API_VERSION", "2024-12-01-preview")


class TestMCPAuthMiddleware:
    """Tests for the bearer-token auth middleware on HTTP transport."""

    def _build_app(
        self,
        monkeypatch: pytest.MonkeyPatch,
        api_key: str = "secret-key-123",
    ) -> object:
        """Build the ASGI app with a given API key."""
        monkeypatch.setenv("AGENT_REVIEWER_API_KEY", api_key)
        with patch("src.mcp_server.sys") as mock_sys:
            mock_sys.argv = ["mcp_server", "--streamable-http"]
            return _build_http_app()

    @pytest.mark.anyio
    async def test_health_always_accessible(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Health endpoint should work without auth."""
        app = self._build_app(monkeypatch)
        transport = httpx.ASGITransport(
            app=app,  # type: ignore[arg-type]
            raise_app_exceptions=False,
        )
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.anyio
    async def test_rejects_missing_auth_header(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should return 401 when no Authorization header."""
        app = self._build_app(monkeypatch)
        transport = httpx.ASGITransport(
            app=app,  # type: ignore[arg-type]
            raise_app_exceptions=False,
        )
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get("/mcp")
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_rejects_invalid_token(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should return 403 for wrong Bearer token."""
        app = self._build_app(monkeypatch)
        transport = httpx.ASGITransport(
            app=app,  # type: ignore[arg-type]
            raise_app_exceptions=False,
        )
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/mcp",
                headers={"Authorization": "Bearer wrong-key"},
            )
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_accepts_valid_token(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should pass through auth with a valid Bearer token."""
        app = self._build_app(monkeypatch)
        transport = httpx.ASGITransport(
            app=app,  # type: ignore[arg-type]
            raise_app_exceptions=False,
        )
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            # The MCP endpoint itself returns 500 because the
            # session manager isn't running in tests. The key
            # check is that auth does NOT block the request.
            response = await client.get(
                "/mcp",
                headers={"Authorization": "Bearer secret-key-123"},
            )
        # Auth passed — not 401 or 403
        assert response.status_code not in (401, 403)

    @pytest.mark.anyio
    async def test_no_auth_when_key_empty(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should allow all requests when API key is empty."""
        monkeypatch.setenv("AGENT_REVIEWER_API_KEY", "")
        with patch("src.mcp_server.sys") as mock_sys:
            mock_sys.argv = ["mcp_server", "--streamable-http"]
            app = _build_http_app()

        transport = httpx.ASGITransport(
            app=app,  # type: ignore[arg-type]
            raise_app_exceptions=False,
        )
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            # No auth header — should not be blocked by auth
            # (MCP itself may error without session, but that's OK)
            response = await client.get("/mcp")
        assert response.status_code not in (401, 403)
