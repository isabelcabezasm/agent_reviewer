"""AI handler module for Azure OpenAI API communication.

Provides an async interface to send review prompts to the Azure
OpenAI service and retrieve structured responses.
"""

from openai import AzureOpenAI  # type: ignore[import-untyped]

from src.config import AzureModelConfig


class AIHandler:
    """Handles communication with the Azure OpenAI API.

    Wraps the Azure OpenAI client to provide a simple interface
    for sending system/user prompt pairs and receiving completions.

    Attributes:
        client: The Azure OpenAI client instance.
        model_name: The deployed model name to use.
    """

    def __init__(self, config: AzureModelConfig) -> None:
        """Initialize the AI handler with Azure OpenAI credentials.

        Parameters:
            config: Azure model configuration containing
                endpoint, API key, model name, and API version.
        """
        self.client: AzureOpenAI = AzureOpenAI(
            azure_endpoint=config.endpoint,
            api_key=config.api_key,
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
