"""AI handler module for Azure OpenAI API communication.

Provides an interface to send review prompts to the Azure
OpenAI service and retrieve structured responses. Supports
both API key auth and Entra ID (Azure AD) token-based auth.
"""

import logging
import os

import httpx
from azure.identity import (
    DefaultAzureCredential,
    get_bearer_token_provider,
)
import openai
from openai import AzureOpenAI

from src.config import AzureModelConfig
from src.ssl_utils import build_httpx_client

logger = logging.getLogger(__name__)


class AIHandler:
    """Handles communication with the Azure OpenAI API.

    Wraps the Azure OpenAI client to provide a simple interface
    for sending system/user prompt pairs and receiving completions.
    Uses Entra ID token auth when no API key is provided, or API
    key auth when a key is available.

    Attributes:
        client: The Azure OpenAI client instance.
        model_name: The deployed model name to use.
    """

    def __init__(self, config: AzureModelConfig) -> None:
        """Initialize the AI handler with Azure OpenAI credentials.

        If the API key is set to a non-empty value, uses API key auth.
        Otherwise, falls back to Entra ID token-based auth via
        DefaultAzureCredential (supports managed identity, az login, etc.)

        Parameters:
            config: Azure model configuration containing
                endpoint, API key, model name, and API version.
        """
        if config.api_key:
            # API key authentication
            logger.info(
                "Initializing Azure OpenAI client "
                "(API key auth) endpoint=%s model=%s",
                config.endpoint, config.model_name,
            )
            self.client: AzureOpenAI = AzureOpenAI(
                azure_endpoint=config.endpoint,
                api_key=config.api_key,
                api_version=config.api_version,
                http_client=build_httpx_client(),
            )
        else:
            # Entra ID / Azure AD token-based authentication
            logger.info(
                "Initializing Azure OpenAI client "
                "(Entra ID auth) endpoint=%s model=%s",
                config.endpoint, config.model_name,
            )
            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential,
                "https://cognitiveservices.azure.com/.default",
            )
            self.client = AzureOpenAI(
                azure_endpoint=config.endpoint,
                azure_ad_token_provider=token_provider,
                api_version=config.api_version,
                http_client=build_httpx_client(),
            )
        self.model_name = config.model_name
        self._use_responses_api = True

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """Send a review request to Azure OpenAI.

        Tries the Responses API first. If the deployment only
        supports Chat Completions (older models), falls back
        automatically.

        Parameters:
            system_prompt: The system-level instruction for the model.
            user_prompt: The user-level prompt containing the code
                and review context.
            temperature: Sampling temperature for the model.
                Lower values produce more deterministic output.

        Returns:
            str: The model's response text.

        Raises:
            openai.APIError: If the API request fails.
        """
        logger.debug(
            "Azure OpenAI request: model=%s temp=%.2f "
            "system_prompt_len=%d user_prompt_len=%d",
            self.model_name, temperature,
            len(system_prompt), len(user_prompt),
        )
        if self._use_responses_api:
            try:
                result = self._responses_api(
                    system_prompt, user_prompt, temperature,
                )
            except openai.BadRequestError as e:
                if "OperationNotSupported" in str(e):
                    logger.info(
                        "Responses API not supported for model=%s, "
                        "using Chat Completions for all future requests",
                        self.model_name,
                    )
                    self._use_responses_api = False
                    result = self._chat_completions(
                        system_prompt, user_prompt, temperature,
                    )
                else:
                    logger.exception(
                        "Azure OpenAI API call failed: model=%s",
                        self.model_name,
                    )
                    raise
        else:
            result = self._chat_completions(
                system_prompt, user_prompt, temperature,
            )
        logger.debug(
            "Azure OpenAI response: %d chars", len(result),
        )
        return result

    def _responses_api(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> str:
        """Send a request using the Azure OpenAI Responses API."""
        response = self.client.responses.create(
            model=self.model_name,
            instructions=system_prompt,
            input=user_prompt,
        )
        return str(response.output_text)

    def _chat_completions(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> str:
        """Send a request using the Chat Completions API."""
        response = self.client.chat.completions.create(
            model=self.model_name,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return str(response.choices[0].message.content)
