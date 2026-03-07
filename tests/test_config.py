"""Tests for the configuration module."""

import os
from unittest.mock import patch

import pytest

from src.config import AppConfig, AzureModelConfig, ReviewConfig, load_config


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
            "AZURE_MODEL_API_NAME": "gpt-5-pro",
            "AZURE_MODEL_API_VERSION": "2024-12-01-preview",
        },
    )
    def test_raises_with_partial_missing_variables(self) -> None:
        """Test that error message lists specific missing variables."""
        with pytest.raises(ValueError, match="AZURE_MODEL_API_KEY"):
            _ = load_config()
