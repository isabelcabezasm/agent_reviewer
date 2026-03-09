"""Tests for the configuration module."""

import os
from unittest.mock import patch

import pytest

from src.config import (
    AIProvider,
    AppConfig,
    AzureModelConfig,
    CopilotModelConfig,
    ReviewConfig,
    load_config,
)
from src.handler_factory import create_handler


class TestAzureModelConfig:
    """Tests for AzureModelConfig dataclass."""

    def test_creates_config_with_all_fields(self) -> None:
        """Test that config is created with all required fields."""
        config = AzureModelConfig(
            endpoint="https://example.openai.azure.com/",
            api_key="test-key",
            model_name="gpt-5-pro",
            api_version="2024-12-01-preview",
        )
        assert config.endpoint == "https://example.openai.azure.com/"
        assert config.api_key == "test-key"
        assert config.model_name == "gpt-5-pro"
        assert config.api_version == "2024-12-01-preview"

    def test_config_is_frozen(self) -> None:
        """Test that config is immutable (frozen dataclass)."""
        config = AzureModelConfig(
            endpoint="https://example.openai.azure.com/",
            api_key="test-key",
            model_name="gpt-5-pro",
            api_version="2024-12-01-preview",
        )
        with pytest.raises(AttributeError):
            config.api_key = "new-key"  # type: ignore[misc]


class TestReviewConfig:
    """Tests for ReviewConfig dataclass."""

    def test_default_values(self) -> None:
        """Test that review config has sensible defaults."""
        config = ReviewConfig()
        assert config.require_security_review is True
        assert config.require_tests_review is True
        assert config.require_score is True
        assert config.num_max_findings == 5
        assert config.extra_instructions == ""

    def test_custom_values(self) -> None:
        """Test that review config accepts custom values."""
        config = ReviewConfig(
            require_security_review=False,
            num_max_findings=10,
            extra_instructions="Focus on performance",
        )
        assert config.require_security_review is False
        assert config.num_max_findings == 10
        assert config.extra_instructions == "Focus on performance"


class TestLoadConfig:
    """Tests for the load_config function."""

    @patch.dict(
        os.environ,
        {
            "AZURE_MODEL_API_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_MODEL_API_KEY": "test-key-123",
            "AZURE_MODEL_API_NAME": "gpt-5-pro",
            "AZURE_MODEL_API_VERSION": "2024-12-01-preview",
        },
    )
    def test_loads_config_from_environment(self) -> None:
        """Test that config loads correctly from environment variables."""
        config = load_config()
        assert config.provider == AIProvider.AZURE
        assert config.azure is not None
        assert config.azure.endpoint == "https://test.openai.azure.com/"
        assert config.azure.api_key == "test-key-123"
        assert config.azure.model_name == "gpt-5-pro"
        assert config.azure.api_version == "2024-12-01-preview"
        assert isinstance(config, AppConfig)

    @patch.dict(
        os.environ,
        {
            "AZURE_MODEL_API_ENDPOINT": "",
            "AZURE_MODEL_API_KEY": "",
            "AZURE_MODEL_API_NAME": "",
            "AZURE_MODEL_API_VERSION": "",
        },
    )
    def test_raises_on_missing_variables(self) -> None:
        """Test that ValueError is raised when variables are missing."""
        with pytest.raises(ValueError, match="Missing required environment"):
            _ = load_config()

    @patch.dict(
        os.environ,
        {
            "AZURE_MODEL_API_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_MODEL_API_KEY": "",
            "AZURE_MODEL_API_NAME": "",
            "AZURE_MODEL_API_VERSION": "2024-12-01-preview",
        },
    )
    def test_raises_with_partial_missing_variables(self) -> None:
        """Test that error message lists specific missing variables."""
        with pytest.raises(ValueError, match="AZURE_MODEL_API_NAME"):
            _ = load_config()

    @patch.dict(
        os.environ,
        {
            "AI_PROVIDER": "copilot",
            "GITHUB_TOKEN": "ghp_test123",
            "COPILOT_MODEL_NAME": "gpt-4.1",
        },
    )
    def test_loads_copilot_config(self) -> None:
        """Test that load_config detects Copilot provider."""
        config = load_config()
        assert config.provider == AIProvider.COPILOT
        assert config.copilot is not None
        assert config.copilot.github_token == "ghp_test123"
        assert config.copilot.model_name == "gpt-4.1"

    @patch.dict(
        os.environ,
        {
            "AI_PROVIDER": "",
            "GITHUB_TOKEN": "ghp_auto",
            "AZURE_MODEL_API_ENDPOINT": "",
            "AZURE_MODEL_API_NAME": "",
            "AZURE_MODEL_API_VERSION": "",
        },
    )
    def test_auto_detects_copilot_from_github_token(self) -> None:
        """Test auto-detection when only GITHUB_TOKEN is set."""
        config = load_config()
        assert config.provider == AIProvider.COPILOT
        assert config.copilot is not None


class TestCopilotModelConfig:
    """Tests for CopilotModelConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default Copilot config values."""
        cfg = CopilotModelConfig()
        assert cfg.github_token == ""
        assert cfg.model_name == "gpt-4.1"

    def test_custom_values(self) -> None:
        """Test custom Copilot config values."""
        cfg = CopilotModelConfig(
            github_token="ghp_custom",
            model_name="claude-sonnet-4",
        )
        assert cfg.github_token == "ghp_custom"
        assert cfg.model_name == "claude-sonnet-4"

    def test_config_is_frozen(self) -> None:
        """Test that Copilot config is immutable."""
        cfg = CopilotModelConfig(github_token="ghp_test")
        with pytest.raises(AttributeError):
            cfg.github_token = "new"  # type: ignore[misc]


class TestCreateHandler:
    """Tests for the create_handler factory function."""

    @patch("src.ai_handler.AzureOpenAI")
    def test_creates_azure_handler(
        self,
        _mock_client: MagicMock,
    ) -> None:
        """Test that Azure handler is created for AZURE provider."""
        from src.ai_handler import AIHandler

        config = AppConfig(
            provider=AIProvider.AZURE,
            azure=AzureModelConfig(
                endpoint="https://test.openai.azure.com/",
                api_key="key",
                model_name="gpt-5-pro",
                api_version="2024-12-01",
            ),
        )
        handler = create_handler(config)
        assert isinstance(handler, AIHandler)

    @patch("src.copilot_handler.OpenAI")
    def test_creates_copilot_handler(
        self,
        _mock_client: MagicMock,
    ) -> None:
        """Test that Copilot handler is created for COPILOT provider."""
        from src.copilot_handler import CopilotAIHandler

        config = AppConfig(
            provider=AIProvider.COPILOT,
            copilot=CopilotModelConfig(
                github_token="ghp_test123",
                model_name="gpt-4.1",
            ),
        )
        handler = create_handler(config)
        assert isinstance(handler, CopilotAIHandler)

    def test_raises_when_azure_config_missing(self) -> None:
        """Test error when Azure selected but no config."""
        config = AppConfig(provider=AIProvider.AZURE)
        with pytest.raises(ValueError, match="Azure provider"):
            _ = create_handler(config)

    def test_raises_when_copilot_config_missing(self) -> None:
        """Test error when Copilot selected but no config."""
        config = AppConfig(provider=AIProvider.COPILOT)
        with pytest.raises(ValueError, match="Copilot provider"):
            _ = create_handler(config)
