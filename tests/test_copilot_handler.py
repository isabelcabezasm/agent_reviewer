"""Tests for the CopilotAIHandler module."""

from unittest.mock import MagicMock, patch

import pytest

from src.config import CopilotModelConfig
from src.copilot_handler import CopilotAIHandler, _get_gh_cli_token


class TestCopilotAIHandler:
    """Tests for the CopilotAIHandler class."""

    @patch("src.copilot_handler.OpenAI")
    def test_init_with_token(
        self,
        mock_openai: MagicMock,
    ) -> None:
        """Test handler initializes with a provided token."""
        config = CopilotModelConfig(
            github_token="ghp_test123",
            model_name="gpt-4.1",
        )
        handler = CopilotAIHandler(config)
        assert handler.model_name == "gpt-4.1"
        mock_openai.assert_called_once()

    @patch("src.copilot_handler._get_gh_cli_token", return_value="ghp_cli")
    @patch("src.copilot_handler.OpenAI")
    def test_init_falls_back_to_gh_cli(
        self,
        mock_openai: MagicMock,
        _mock_cli: MagicMock,
    ) -> None:
        """Test handler falls back to gh CLI when no token set."""
        config = CopilotModelConfig(github_token="", model_name="gpt-4o")
        handler = CopilotAIHandler(config)
        assert handler.model_name == "gpt-4o"
        mock_openai.assert_called_once()

    @patch("src.copilot_handler._get_gh_cli_token", return_value="")
    def test_init_raises_when_no_token(
        self,
        _mock_cli: MagicMock,
    ) -> None:
        """Test handler raises ValueError when no token available."""
        config = CopilotModelConfig(github_token="")
        with pytest.raises(ValueError, match="No GitHub token"):
            _ = CopilotAIHandler(config)

    @patch("src.copilot_handler.OpenAI")
    def test_chat_completion(
        self,
        mock_openai_cls: MagicMock,
    ) -> None:
        """Test chat_completion returns model response text."""
        mock_client = mock_openai_cls.return_value
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "review output"
        mock_client.chat.completions.create.return_value = mock_response

        config = CopilotModelConfig(
            github_token="ghp_test",
            model_name="gpt-4.1",
        )
        handler = CopilotAIHandler(config)
        result = handler.chat_completion(
            system_prompt="You are a reviewer.",
            user_prompt="Review this code.",
        )

        assert result == "review output"
        mock_client.chat.completions.create.assert_called_once()

    @patch("src.copilot_handler.OpenAI")
    def test_chat_completion_passes_temperature(
        self,
        mock_openai_cls: MagicMock,
    ) -> None:
        """Test that temperature is forwarded to the API call."""
        mock_client = mock_openai_cls.return_value
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "result"
        mock_client.chat.completions.create.return_value = mock_response

        config = CopilotModelConfig(
            github_token="ghp_test",
            model_name="gpt-4.1",
        )
        handler = CopilotAIHandler(config)
        _ = handler.chat_completion("sys", "user", temperature=0.5)

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["temperature"] == 0.5


class TestGetGhCliToken:
    """Tests for the _get_gh_cli_token helper."""

    @patch("src.copilot_handler.subprocess.run")
    def test_returns_token_from_cli(
        self,
        mock_run: MagicMock,
    ) -> None:
        """Test token retrieval from gh CLI."""
        mock_run.return_value.stdout = "ghp_from_cli\n"
        token = _get_gh_cli_token()
        assert token == "ghp_from_cli"

    @patch("src.copilot_handler.subprocess.run")
    def test_returns_empty_on_failure(
        self,
        mock_run: MagicMock,
    ) -> None:
        """Test empty string returned when gh CLI fails."""
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, "gh")
        token = _get_gh_cli_token()
        assert token == ""

    @patch("src.copilot_handler.subprocess.run")
    def test_returns_empty_when_gh_not_installed(
        self,
        mock_run: MagicMock,
    ) -> None:
        """Test empty string returned when gh is not found."""
        mock_run.side_effect = FileNotFoundError()
        token = _get_gh_cli_token()
        assert token == ""
