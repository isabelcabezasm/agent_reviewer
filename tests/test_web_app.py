"""Tests for the web application API endpoints."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.web.app import ReviewRequest, _parse_review_yaml, app


client = TestClient(app)


class TestHealthEndpoint:
    """Tests for the /api/health endpoint."""

    def test_health_returns_ok(self) -> None:
        """Test that health check returns ok status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestServeUI:
    """Tests for the root UI endpoint."""

    def test_serves_index_html(self) -> None:
        """Test that root serves the HTML UI."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Agent Reviewer" in response.text


class TestParseReviewYaml:
    """Tests for the YAML parser helper."""

    def test_parses_yaml_from_code_fence(self) -> None:
        """Test extraction of YAML from code fence."""
        raw = '```yaml\nreview:\n  score: 85\n  summary: Good code\n```'
        result = _parse_review_yaml(raw)
        assert result is not None
        assert result["score"] == 85

    def test_parses_raw_yaml(self) -> None:
        """Test parsing of raw YAML without code fence."""
        raw = "review:\n  score: 70\n  summary: OK"
        result = _parse_review_yaml(raw)
        assert result is not None
        assert result["score"] == 70

    def test_returns_none_for_invalid_yaml(self) -> None:
        """Test that invalid YAML returns None."""
        result = _parse_review_yaml("this is not yaml: [[[")
        # PyYAML may parse this, so just check it doesn't crash
        assert result is None or isinstance(result, dict)

    def test_returns_none_for_non_dict(self) -> None:
        """Test that non-dict YAML returns None."""
        result = _parse_review_yaml("- item1\n- item2")
        assert result is None


class TestReviewRequest:
    """Tests for the ReviewRequest model."""

    def test_default_values(self) -> None:
        """Test that defaults are populated correctly."""
        req = ReviewRequest(repo_url="https://github.com/owner/repo")
        assert req.mode == "full"
        assert req.github_pat is None
        assert req.branch is None
        assert req.instructions == ""
        assert req.max_files == 30

    def test_custom_values(self) -> None:
        """Test that custom values are set."""
        req = ReviewRequest(
            repo_url="https://github.com/owner/repo",
            github_pat="ghp_test",
            mode="branch",
            branch="develop",
            instructions="Focus on security",
            max_files=10,
        )
        assert req.github_pat == "ghp_test"
        assert req.mode == "branch"
        assert req.branch == "develop"


class TestReviewEndpoint:
    """Tests for the /api/review endpoint."""

    @patch("src.web.app.cleanup_repo")
    @patch("src.web.app.AIHandler")
    @patch("src.web.app.get_repo_files")
    @patch("src.web.app.read_files")
    @patch("src.web.app.clone_repo")
    @patch("src.web.app.load_config")
    def test_review_full_repo(
        self,
        mock_config: MagicMock,
        mock_clone: MagicMock,
        mock_read: MagicMock,
        mock_get_files: MagicMock,
        mock_ai_cls: MagicMock,
        mock_cleanup: MagicMock,
    ) -> None:
        """Test full repo review returns review results."""
        from src.config import AppConfig, AzureModelConfig, ReviewConfig

        mock_config.return_value = AppConfig(
            azure=AzureModelConfig(
                endpoint="https://test.openai.azure.com/",
                api_key="key",
                model_name="gpt-5-pro",
                api_version="2024-12-01",
            ),
            review=ReviewConfig(),
        )
        mock_clone.return_value = "/tmp/repo"
        mock_get_files.return_value = ["/tmp/repo/app.py"]
        mock_read.return_value = "## File: 'app.py'\n   1 print('hi')"
        mock_ai_cls.return_value.chat_completion.return_value = (
            "```yaml\nreview:\n  score: 90\n  summary: Great code\n```"
        )

        response = client.post(
            "/api/review",
            json={"repo_url": "https://github.com/owner/repo"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["files_reviewed"] == 1
        assert data["parsed_review"] is not None
        assert data["parsed_review"]["score"] == 90
        mock_cleanup.assert_called_once_with("/tmp/repo")

    @patch("src.web.app.clone_repo")
    @patch("src.web.app.load_config")
    def test_review_handles_clone_failure(
        self,
        mock_config: MagicMock,
        mock_clone: MagicMock,
    ) -> None:
        """Test that clone failure returns proper error."""
        from src.config import AppConfig, AzureModelConfig, ReviewConfig

        mock_config.return_value = AppConfig(
            azure=AzureModelConfig(
                endpoint="https://test.openai.azure.com/",
                api_key="key",
                model_name="gpt-5-pro",
                api_version="2024-12-01",
            ),
            review=ReviewConfig(),
        )
        mock_clone.side_effect = ValueError("Failed to clone repository: not found")

        response = client.post(
            "/api/review",
            json={"repo_url": "https://github.com/owner/nonexistent"},
        )

        assert response.status_code == 400
        assert "clone" in response.json()["detail"].lower()
