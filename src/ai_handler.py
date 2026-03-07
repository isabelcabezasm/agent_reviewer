"""AI handler module for Azure OpenAI API communication.

Provides an interface to send review prompts to the Azure
OpenAI service and retrieve structured responses. Supports
both API key auth and Entra ID (Azure AD) token-based auth.
"""

from azure.identity import DefaultAzureCredential, get_bearer_token_provider  # type: ignore[import-untyped]
from openai import AzureOpenAI  # type: ignore[import-untyped]

from src.config import AzureModelConfig


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
            self.client: AzureOpenAI = AzureOpenAI(
                azure_endpoint=config.endpoint,
                api_key=config.api_key,
                api_version=config.api_version,
            )
        else:
            # Entra ID / Azure AD token-based authentication
            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(  # pyright: ignore[reportUnknownVariableType]
                credential,
                "https://cognitiveservices.azure.com/.default",
            )
            self.client = AzureOpenAI(
                azure_endpoint=config.endpoint,
                azure_ad_token_provider=token_provider,  # pyright: ignore[reportUnknownArgumentType]
                api_version=config.api_version,
            )
        self.model_name = config.model_name

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """Send a chat completion request to Azure OpenAI.

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
        response = self.client.chat.completions.create(  # pyright: ignore[reportUnknownMemberType]
            model=self.model_name,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        result: str = str(
            response.choices[0].message.content  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        )
        return result
