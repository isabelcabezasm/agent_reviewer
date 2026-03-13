"""Configuration module for loading environment variables.

Loads AI provider credentials and review settings from
environment variables or a .env file. Supports two providers:

- **azure**: Azure OpenAI (requires endpoint, model, version)
- **copilot**: GitHub Copilot API (requires a GitHub token)

The provider is auto-detected from the ``AI_PROVIDER`` env var,
or inferred from which credentials are available.
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI provider backends.

    Attributes:
        AZURE: Azure OpenAI Service.
        COPILOT: GitHub Copilot Chat Completions API.
    """

    AZURE = "azure"
    COPILOT = "copilot"


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
class CopilotModelConfig:
    """GitHub Copilot model configuration.

    Attributes:
        github_token: GitHub token (PAT or Copilot session token).
            If empty, the handler will try ``gh auth token``.
        model_name: The model to request (e.g., gpt-4o, gpt-4.1,
            claude-sonnet-4). Defaults to gpt-4.1.
    """

    github_token: str = ""
    model_name: str = "gpt-4.1"


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

    Either ``azure`` or ``copilot`` will be populated depending
    on the chosen AI provider.

    Attributes:
        provider: The active AI provider backend.
        azure: Azure OpenAI model configuration (if provider is AZURE).
        copilot: GitHub Copilot configuration (if provider is COPILOT).
        review: Review-specific settings.
    """

    provider: AIProvider = AIProvider.AZURE
    azure: AzureModelConfig | None = None
    copilot: CopilotModelConfig | None = None
    review: ReviewConfig = field(default_factory=ReviewConfig)


def _detect_provider() -> AIProvider:
    """Auto-detect the AI provider from environment variables.

    Checks ``AI_PROVIDER`` first. If unset, falls back to
    checking whether Azure or GitHub credentials are present.

    Returns:
        AIProvider: The detected provider.
    """
    explicit = os.getenv("AI_PROVIDER", "").lower().strip()
    if explicit == "copilot":
        return AIProvider.COPILOT
    if explicit == "azure":
        return AIProvider.AZURE

    # Auto-detect: if Azure env vars are present, use Azure;
    # if a GitHub token exists, use Copilot.
    has_azure = bool(
        os.getenv("AZURE_MODEL_API_ENDPOINT")
        and os.getenv("AZURE_MODEL_API_NAME")
    )
    if has_azure:
        return AIProvider.AZURE

    has_github = bool(os.getenv("GITHUB_TOKEN"))
    if has_github:
        return AIProvider.COPILOT

    # Default to Azure for backward compatibility.
    return AIProvider.AZURE


def _load_azure_config() -> AzureModelConfig:
    """Load Azure OpenAI configuration from environment.

    Returns:
        AzureModelConfig: The Azure model configuration.

    Raises:
        ValueError: If required Azure env vars are missing.
    """
    endpoint = os.getenv("AZURE_MODEL_API_ENDPOINT", "")
    api_key = os.getenv("AZURE_MODEL_API_KEY", "")
    model_name = os.getenv("AZURE_MODEL_API_NAME", "")
    api_version = os.getenv("AZURE_MODEL_API_VERSION", "")

    if not all([endpoint, model_name, api_version]):
        missing: list[str] = []
        if not endpoint:
            missing.append("AZURE_MODEL_API_ENDPOINT")
        if not model_name:
            missing.append("AZURE_MODEL_API_NAME")
        if not api_version:
            missing.append("AZURE_MODEL_API_VERSION")
        msg = (
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Please configure your .env file."
        )
        raise ValueError(msg)

    return AzureModelConfig(
        endpoint=endpoint,
        api_key=api_key,
        model_name=model_name,
        api_version=api_version,
    )


def _load_copilot_config() -> CopilotModelConfig:
    """Load GitHub Copilot configuration from environment.

    Returns:
        CopilotModelConfig: The Copilot model configuration.
    """
    return CopilotModelConfig(
        github_token=os.getenv("GITHUB_TOKEN", ""),
        model_name=os.getenv("COPILOT_MODEL_NAME", "gpt-4.1"),
    )


def load_config(env_path: str | None = None) -> AppConfig:
    """Load application configuration from environment variables.

    Reads the .env file (or a custom path) and constructs the
    full application configuration. Auto-detects whether to use
    Azure OpenAI or GitHub Copilot as the AI backend.

    Parameters:
        env_path: Optional path to a .env file. Defaults to
            the .env file in the project root.

    Returns:
        AppConfig: The fully populated application configuration.

    Raises:
        ValueError: If required environment variables for the
            detected provider are missing.
    """
    if env_path:
        logger.debug("Loading env from: %s", env_path)
        _ = load_dotenv(env_path)
    else:
        # Look for .env in project root
        project_root = Path(__file__).parent.parent
        env_file = project_root / ".env"
        logger.debug("Loading env from: %s", env_file)
        _ = load_dotenv(env_file)

    provider = _detect_provider()
    logger.info("Detected AI provider: %s", provider.value)

    if provider == AIProvider.COPILOT:
        copilot_cfg = _load_copilot_config()
        return AppConfig(
            provider=provider,
            copilot=copilot_cfg,
        )

    # Default: Azure
    azure_cfg = _load_azure_config()
    return AppConfig(
        provider=provider,
        azure=azure_cfg,
    )
