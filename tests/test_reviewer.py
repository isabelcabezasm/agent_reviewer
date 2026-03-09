"""Tests for the CodeReviewer module."""

from unittest.mock import MagicMock, patch

import pytest

from src.config import AppConfig, AzureModelConfig, ReviewConfig
from src.reviewer import CodeReviewer


@pytest.fixture
def mock_config() -> AppConfig:
    """Create a mock application configuration for testing."""
    return AppConfig(
        azure=AzureModelConfig(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            model_name="gpt-5-pro",
            api_version="2024-12-01-preview",
        ),
        review=ReviewConfig(),
    )


class TestCodeReviewer:
    """Tests for the CodeReviewer class."""

    @patch("src.reviewer.create_handler")
    def test_review_staged_with_diff(
        self,
        mock_handler_factory: MagicMock,
        mock_config: AppConfig,
    ) -> None:
        """Test that staged review works with valid diff."""
        mock_handler = mock_handler_factory.return_value
        mock_handler.chat_completion.return_value = "```yaml\nreview:\n  score: 85\n```"

        with patch("src.reviewer.get_staged_diff", return_value="+ new code"):
            reviewer = CodeReviewer(mock_config)
            result = reviewer.review_staged()

        assert "review:" in result
        mock_handler.chat_completion.assert_called_once()

    @patch("src.reviewer.create_handler")
    def test_review_staged_raises_on_empty_diff(
        self,
        mock_handler_factory: MagicMock,
        mock_config: AppConfig,
    ) -> None:
        """Test that empty staged diff raises ValueError."""
        with patch("src.reviewer.get_staged_diff", return_value=""):
            reviewer = CodeReviewer(mock_config)
            with pytest.raises(ValueError, match="No staged changes"):
                _ = reviewer.review_staged()

    @patch("src.reviewer.create_handler")
    def test_review_uncommitted_with_diff(
        self,
        mock_handler_factory: MagicMock,
        mock_config: AppConfig,
    ) -> None:
        """Test that uncommitted review works with valid diff."""
        mock_handler = mock_handler_factory.return_value
        mock_handler.chat_completion.return_value = "review output"

        with patch("src.reviewer.get_all_uncommitted_diff", return_value="diff content"):
            reviewer = CodeReviewer(mock_config)
            result = reviewer.review_uncommitted()

        assert result == "review output"

    @patch("src.reviewer.create_handler")
    def test_review_uncommitted_raises_on_empty(
        self,
        mock_handler_factory: MagicMock,
        mock_config: AppConfig,
    ) -> None:
        """Test that empty uncommitted diff raises ValueError."""
        with patch("src.reviewer.get_all_uncommitted_diff", return_value=""):
            reviewer = CodeReviewer(mock_config)
            with pytest.raises(ValueError, match="No uncommitted changes"):
                _ = reviewer.review_uncommitted()

    @patch("src.reviewer.create_handler")
    def test_review_files_raises_on_empty_list(
        self,
        mock_handler_factory: MagicMock,
        mock_config: AppConfig,
    ) -> None:
        """Test that empty file list raises ValueError."""
        reviewer = CodeReviewer(mock_config)
        with pytest.raises(ValueError, match="No files specified"):
            _ = reviewer.review_files([])

    @patch("src.reviewer.create_handler")
    def test_review_branch_raises_on_empty(
        self,
        mock_handler_factory: MagicMock,
        mock_config: AppConfig,
    ) -> None:
        """Test that empty branch diff raises ValueError."""
        with patch("src.reviewer.get_branch_diff", return_value=""):
            reviewer = CodeReviewer(mock_config)
            with pytest.raises(ValueError, match="No changes found"):
                _ = reviewer.review_branch(branch="main")

    @patch("src.reviewer.create_handler")
    def test_review_commit_raises_on_empty(
        self,
        mock_handler_factory: MagicMock,
        mock_config: AppConfig,
    ) -> None:
        """Test that empty commit diff raises ValueError."""
        with patch("src.reviewer.get_commit_diff", return_value=""):
            reviewer = CodeReviewer(mock_config)
            with pytest.raises(ValueError, match="No changes found"):
                _ = reviewer.review_commit(commit="HEAD~1")
