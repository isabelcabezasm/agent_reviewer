"""Tests for the MCP server module.

Validates that MCP tools correctly delegate to the underlying
review logic and handle edge cases (empty diffs, missing files).
Also tests the HTTP transport auth middleware and transport parsing.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.mcp_server import (
    _build_http_app,
    _parse_transport,
    review_branch_changes,
    review_code_snippet,
    review_commit,
    review_current_branch,
    review_diff,
    review_files,
    review_repository,
    review_staged_changes,
    review_uncommitted_changes,
)

# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

FAKE_REVIEW = "```yaml\nreview:\n  score: 85\n```"

# AIHandler is imported lazily inside helper functions, so we
# patch it at its definition module.
_AI_HANDLER = "src.ai_handler.AIHandler"


@pytest.fixture(autouse=True)
def _mock_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables for every test."""
    monkeypatch.setenv("AZURE_MODEL_API_ENDPOINT", "https://test.openai.azure.com/")
    monkeypatch.setenv("AZURE_MODEL_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_MODEL_API_NAME", "gpt-5-pro")
    monkeypatch.setenv("AZURE_MODEL_API_VERSION", "2024-12-01-preview")


# -------------------------------------------------------------------
# review_staged_changes
# -------------------------------------------------------------------


class TestReviewStagedChanges:
    """Tests for the review_staged_changes tool."""

    @patch(_AI_HANDLER)
    @patch("src.mcp_server.get_staged_diff", return_value="+ new code")
    def test_returns_review_when_diff_exists(
        self,
        _mock_diff: MagicMock,
        mock_ai_cls: MagicMock,
    ) -> None:
        """Tool should return a review when staged diff exists."""
        mock_ai_cls.return_value.chat_completion.return_value = FAKE_REVIEW
        result = review_staged_changes(repo_path=".")
        assert "review:" in result

    @patch("src.mcp_server.get_staged_diff", return_value="")
    def test_returns_message_when_no_staged_changes(
        self,
        _mock_diff: MagicMock,
    ) -> None:
        """Tool should return a friendly message for empty diff."""
        result = review_staged_changes()
        assert "No staged changes" in result


# -------------------------------------------------------------------
# review_uncommitted_changes
# -------------------------------------------------------------------


class TestReviewUncommittedChanges:
    """Tests for the review_uncommitted_changes tool."""

    @patch(_AI_HANDLER)
    @patch("src.mcp_server.get_all_uncommitted_diff", return_value="+ change")
    def test_returns_review_when_diff_exists(
        self,
        _mock_diff: MagicMock,
        mock_ai_cls: MagicMock,
    ) -> None:
        """Tool should return a review for uncommitted changes."""
        mock_ai_cls.return_value.chat_completion.return_value = FAKE_REVIEW
        result = review_uncommitted_changes(repo_path=".")
        assert "review:" in result

    @patch("src.mcp_server.get_all_uncommitted_diff", return_value="")
    def test_returns_message_when_no_changes(
        self,
        _mock_diff: MagicMock,
    ) -> None:
        """Tool should return a friendly message when no changes."""
        result = review_uncommitted_changes()
        assert "No uncommitted changes" in result


# -------------------------------------------------------------------
# review_branch_changes
# -------------------------------------------------------------------


class TestReviewBranchChanges:
    """Tests for the review_branch_changes tool."""

    @patch(_AI_HANDLER)
    @patch("src.mcp_server.get_branch_diff", return_value="+ branch diff")
    def test_returns_review_for_branch_diff(
        self,
        _mock_diff: MagicMock,
        mock_ai_cls: MagicMock,
    ) -> None:
        """Tool should return a review for branch differences."""
        mock_ai_cls.return_value.chat_completion.return_value = FAKE_REVIEW
        result = review_branch_changes(branch="main", repo_path=".")
        assert "review:" in result

    @patch("src.mcp_server.get_branch_diff", return_value="")
    def test_returns_message_when_no_branch_diff(
        self,
        _mock_diff: MagicMock,
    ) -> None:
        """Tool should indicate no changes vs branch."""
        result = review_branch_changes(branch="main")
        assert "No changes found" in result


# -------------------------------------------------------------------
# review_commit
# -------------------------------------------------------------------


class TestReviewCommit:
    """Tests for the review_commit tool."""

    @patch(_AI_HANDLER)
    @patch("src.mcp_server.get_commit_diff", return_value="+ commit diff")
    def test_returns_review_for_commit(
        self,
        _mock_diff: MagicMock,
        mock_ai_cls: MagicMock,
    ) -> None:
        """Tool should return a review for commit changes."""
        mock_ai_cls.return_value.chat_completion.return_value = FAKE_REVIEW
        result = review_commit(commit="HEAD~1", repo_path=".")
        assert "review:" in result

    @patch("src.mcp_server.get_commit_diff", return_value="")
    def test_returns_message_when_no_commit_changes(
        self,
        _mock_diff: MagicMock,
    ) -> None:
        """Tool should indicate no changes for the commit."""
        result = review_commit(commit="HEAD~1")
        assert "No changes found" in result


# -------------------------------------------------------------------
# review_files
# -------------------------------------------------------------------


class TestReviewFiles:
    """Tests for the review_files tool."""

    @patch(_AI_HANDLER)
    @patch("src.mcp_server.read_files", return_value="file contents here")
    def test_returns_review_for_files(
        self,
        _mock_read: MagicMock,
        mock_ai_cls: MagicMock,
    ) -> None:
        """Tool should return a review for given files."""
        mock_ai_cls.return_value.chat_completion.return_value = FAKE_REVIEW
        result = review_files(file_paths=["src/main.py"])
        assert "review:" in result

    def test_returns_message_for_empty_list(self) -> None:
        """Tool should return a message when no paths given."""
        result = review_files(file_paths=[])
        assert "No file paths" in result


# -------------------------------------------------------------------
# review_code_snippet
# -------------------------------------------------------------------


class TestReviewCodeSnippet:
    """Tests for the review_code_snippet tool."""

    @patch(_AI_HANDLER)
    def test_returns_review_for_code(
        self,
        mock_ai_cls: MagicMock,
    ) -> None:
        """Tool should return a review for raw code input."""
        mock_ai_cls.return_value.chat_completion.return_value = FAKE_REVIEW
        result = review_code_snippet(code="def foo(): pass", language="Python")
        assert "review:" in result


# -------------------------------------------------------------------
# review_diff
# -------------------------------------------------------------------


class TestReviewDiff:
    """Tests for the review_diff tool."""

    @patch(_AI_HANDLER)
    def test_returns_review_for_diff(
        self,
        mock_ai_cls: MagicMock,
    ) -> None:
        """Tool should return a review for a raw diff."""
        mock_ai_cls.return_value.chat_completion.return_value = FAKE_REVIEW
        result = review_diff(diff="+ new line\n- old line")
        assert "review:" in result

    def test_returns_message_for_empty_diff(self) -> None:
        """Tool should return a message for empty diff."""
        result = review_diff(diff="")
        assert "Empty diff" in result

    def test_returns_message_for_whitespace_only_diff(self) -> None:
        """Tool should return a message for whitespace-only diff."""
        result = review_diff(diff="   \n  \n")
        assert "Empty diff" in result


# -------------------------------------------------------------------
# review_repository
# -------------------------------------------------------------------


class TestReviewRepository:
    """Tests for the review_repository tool."""

    @patch(_AI_HANDLER)
    @patch(
        "src.mcp_server.get_repo_files",
        return_value=["/tmp/repo/main.py", "/tmp/repo/utils.py"],
    )
    @patch("src.mcp_server.read_files", return_value="file contents")
    def test_returns_review_for_repo(
        self,
        _mock_read: MagicMock,
        _mock_files: MagicMock,
        mock_ai_cls: MagicMock,
    ) -> None:
        """Tool should return a review when repo has code files."""
        mock_ai_cls.return_value.chat_completion.return_value = FAKE_REVIEW
        result = review_repository(repo_path="/tmp/repo")
        assert "review:" in result

    @patch("src.mcp_server.get_repo_files", return_value=[])
    def test_returns_message_when_no_files(
        self,
        _mock_files: MagicMock,
    ) -> None:
        """Tool should indicate no code files found."""
        result = review_repository(repo_path="/tmp/empty")
        assert "No code files found" in result


# -------------------------------------------------------------------
# review_current_branch
# -------------------------------------------------------------------


class TestReviewCurrentBranch:
    """Tests for the review_current_branch tool."""

    @patch(_AI_HANDLER)
    @patch("src.mcp_server.get_branch_diff", return_value="+ branch change")
    def test_returns_review_for_current_branch(
        self,
        _mock_diff: MagicMock,
        mock_ai_cls: MagicMock,
    ) -> None:
        """Tool should return a review for current branch changes."""
        mock_ai_cls.return_value.chat_completion.return_value = FAKE_REVIEW
        result = review_current_branch(base_branch="main")
        assert "review:" in result

    @patch("src.mcp_server.get_branch_diff", return_value="")
    def test_returns_message_when_no_branch_changes(
        self,
        _mock_diff: MagicMock,
    ) -> None:
        """Tool should indicate no changes on branch."""
        result = review_current_branch(base_branch="main")
        assert "No changes found" in result


# -------------------------------------------------------------------
# _parse_transport
# -------------------------------------------------------------------


class TestParseTransport:
    """Tests for the _parse_transport helper."""

    def test_defaults_to_stdio(self) -> None:
        """Should default to stdio when no args given."""
        with patch("src.mcp_server.sys") as mock_sys:
            mock_sys.argv = ["mcp_server"]
            result = _parse_transport()
        assert result == "stdio"

    def test_detects_sse(self) -> None:
        """Should detect --sse flag."""
        with patch("src.mcp_server.sys") as mock_sys:
            mock_sys.argv = ["mcp_server", "--sse"]
            result = _parse_transport()
        assert result == "sse"

    def test_detects_streamable_http(self) -> None:
        """Should detect --streamable-http flag."""
        with patch("src.mcp_server.sys") as mock_sys:
            mock_sys.argv = ["mcp_server", "--streamable-http"]
            result = _parse_transport()
        assert result == "streamable-http"


# -------------------------------------------------------------------
# _build_http_app (auth middleware)
# -------------------------------------------------------------------


class TestBuildHttpApp:
    """Tests for the HTTP app builder and auth middleware."""

    def test_builds_app_without_auth(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should build an app when no API key is set."""
        monkeypatch.setenv("AGENT_REVIEWER_API_KEY", "")
        with patch("src.mcp_server.sys") as mock_sys:
            mock_sys.argv = ["mcp_server", "--streamable-http"]
            app = _build_http_app()
        assert app is not None

    def test_builds_app_with_auth(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should build an app with auth middleware when key is set."""
        monkeypatch.setenv("AGENT_REVIEWER_API_KEY", "test-key-123")
        with patch("src.mcp_server.sys") as mock_sys:
            mock_sys.argv = ["mcp_server", "--streamable-http"]
            app = _build_http_app()
        assert app is not None

    def test_builds_sse_app(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should build an SSE app when transport is sse."""
        monkeypatch.setenv("AGENT_REVIEWER_API_KEY", "")
        with patch("src.mcp_server.sys") as mock_sys:
            mock_sys.argv = ["mcp_server", "--sse"]
            app = _build_http_app()
        assert app is not None
