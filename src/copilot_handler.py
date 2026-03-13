"""GitHub Copilot AI handler module.

Provides an interface to send review prompts to the GitHub
Models API. Uses the OpenAI SDK pointed at GitHub's inference
endpoint with a GitHub token for authentication.

The GitHub token can come from:
1. GITHUB_TOKEN environment variable
2. The ``gh auth token`` CLI command (GitHub CLI)

Compatible models include ``gpt-4o``, ``gpt-4.1``, ``o3-mini``,
``claude-sonnet-4``, etc. — whatever your GitHub subscription
provides access to.
"""

import logging
import subprocess

from openai import OpenAI

from src.config import CopilotModelConfig
from src.ssl_utils import build_httpx_client

logger = logging.getLogger(__name__)

# GitHub Models inference endpoint (OpenAI-compatible).
# Works with standard GitHub PATs (unlike api.githubcopilot.com
# which requires internal Copilot extension session tokens).
COPILOT_API_BASE = "https://models.inference.ai.azure.com"


class CopilotAIHandler:
    """Handles communication with the GitHub Copilot API.

    Wraps the OpenAI client pointed at GitHub Copilot's
    Chat Completions endpoint. Authenticates via a GitHub
    token (PAT or ``gh`` CLI).

    Attributes:
        client: The OpenAI client instance.
        model_name: The model to use for completions.
    """

    def __init__(self, config: CopilotModelConfig) -> None:
        """Initialize the handler with GitHub Copilot credentials.

        Parameters:
            config: Copilot model configuration containing
                the GitHub token and model name.
        """
        token = config.github_token or _get_gh_cli_token()
        if not token:
            msg = (
                "No GitHub token found. Set GITHUB_TOKEN "
                "or log in with `gh auth login`."
            )
            raise ValueError(msg)

        logger.info(
            "Initializing Copilot handler: "
            "model=%s base_url=%s",
            config.model_name, COPILOT_API_BASE,
        )
        self.client: OpenAI = OpenAI(
            base_url=COPILOT_API_BASE,
            api_key=token,
            http_client=build_httpx_client(),
        )
        self.model_name = config.model_name

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """Send a chat completion request to GitHub Copilot.

        Parameters:
            system_prompt: The system-level instruction for
                the model.
            user_prompt: The user-level prompt containing the
                code and review context.
            temperature: Sampling temperature for the model.
                Lower values produce more deterministic output.

        Returns:
            str: The model's response text.

        Raises:
            openai.APIError: If the API request fails.
        """
        logger.debug(
            "Copilot request: model=%s temp=%.2f "
            "system_prompt_len=%d user_prompt_len=%d",
            self.model_name, temperature,
            len(system_prompt), len(user_prompt),
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception:
            logger.exception(
                "Copilot API call failed: model=%s",
                self.model_name,
            )
            raise
        result: str = str(response.choices[0].message.content)
        logger.debug(
            "Copilot response: %d chars", len(result),
        )
        return result


def _get_gh_cli_token() -> str:
    """Retrieve a GitHub token from the ``gh`` CLI.

    Returns:
        str: The token string, or empty string if the CLI
            is not installed or the user is not logged in.
    """
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
