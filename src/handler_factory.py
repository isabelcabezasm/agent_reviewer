"""AI handler factory module.

Provides a factory function and a base class for creating
the appropriate AI handler (Azure OpenAI or GitHub Copilot)
based on the application configuration.
"""

from __future__ import annotations

from src.config import AIProvider, AppConfig


class ChatHandler:
    """Protocol-like base for AI handler implementations.

    Both ``AIHandler`` (Azure) and ``CopilotAIHandler`` (GitHub)
    implement the ``chat_completion`` method with this signature.
    """

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """Send a chat completion request.

        Parameters:
            system_prompt: The system-level instruction.
            user_prompt: The user-level prompt.
            temperature: Sampling temperature.

        Returns:
            str: The model's response text.
        """
        raise NotImplementedError


def create_handler(config: AppConfig) -> ChatHandler:
    """Create the appropriate AI handler for the active provider.

    Parameters:
        config: Application configuration with provider info.

    Returns:
        ChatHandler: An AIHandler or CopilotAIHandler instance.

    Raises:
        ValueError: If the provider config is incomplete.
    """
    if config.provider == AIProvider.COPILOT:
        from src.copilot_handler import CopilotAIHandler

        if config.copilot is None:
            msg = "Copilot provider selected but no config provided."
            raise ValueError(msg)
        return CopilotAIHandler(config.copilot)  # type: ignore[return-value]

    # Default: Azure
    from src.ai_handler import AIHandler

    if config.azure is None:
        msg = "Azure provider selected but no config provided."
        raise ValueError(msg)
    return AIHandler(config.azure)  # type: ignore[return-value]
