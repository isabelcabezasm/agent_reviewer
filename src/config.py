"""Configuration module for loading environment variables.

Loads Azure OpenAI credentials and review settings from a .env file.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AzureModelConfig:
    """Azure OpenAI model configuration.

    Attributes:
        endpoint: The Azure OpenAI API endpoint URL.
        api_key: The Azure OpenAI API key.
        model_name: The deployed model name (e.g., gpt-5-pro).
        api_version: The Azure OpenAI API version string.
    """

    endpoint: str
    api_key: str
    model_name: str
    api_version: str


@dataclass(frozen=True)
class ReviewConfig:
    """Review configuration settings.

    Attributes:
        require_security_review: Whether to include security analysis.
        require_tests_review: Whether to check for test coverage.
        require_score: Whether to include a quality score.
        num_max_findings: Maximum number of key issues to report.
        extra_instructions: Additional user-provided review instructions.
    """

    require_security_review: bool = True
    require_tests_review: bool = True
    require_score: bool = True
    num_max_findings: int = 5
    extra_instructions: str = ""


@dataclass(frozen=True)
class AppConfig:
    """Application-wide configuration.

    Attributes:
        azure: Azure OpenAI model configuration.
        review: Review-specific settings.
    """

    azure: AzureModelConfig
    review: ReviewConfig = field(default_factory=ReviewConfig)


def load_config(env_path: str | None = None) -> AppConfig:
    """Load application configuration from environment variables.

    Reads the .env file (or a custom path) and constructs the
    full application configuration.

    Parameters:
        env_path: Optional path to a .env file. Defaults to
            the .env file in the project root.

    Returns:
        AppConfig: The fully populated application configuration.

    Raises:
        ValueError: If any required Azure environment variable
            is missing.
    """
    if env_path:
        _ = load_dotenv(env_path)
    else:
        # Look for .env in project root
        project_root = Path(__file__).parent.parent
        _ = load_dotenv(project_root / ".env")

    endpoint = os.getenv("AZURE_MODEL_API_ENDPOINT", "")
    api_key = os.getenv("AZURE_MODEL_API_KEY", "")
    model_name = os.getenv("AZURE_MODEL_API_NAME", "")
    api_version = os.getenv("AZURE_MODEL_API_VERSION", "")

    if not all([endpoint, api_key, model_name, api_version]):
        missing: list[str] = []
        if not endpoint:
            missing.append("AZURE_MODEL_API_ENDPOINT")
        if not api_key:
            missing.append("AZURE_MODEL_API_KEY")
        if not model_name:
            missing.append("AZURE_MODEL_API_NAME")
        if not api_version:
            missing.append("AZURE_MODEL_API_VERSION")
        msg = (
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Please configure your .env file."
        )
        raise ValueError(msg)

    azure_config = AzureModelConfig(
        endpoint=endpoint,
        api_key=api_key,
        model_name=model_name,
        api_version=api_version,
    )

    return AppConfig(azure=azure_config)
