"""AI handler factory module.

Provides a factory function and a base class for creating
the appropriate AI handler (Azure OpenAI or GitHub Copilot)
based on the application configuration.
"""

from __future__ import annotations

import logging
import threading

from src.config import AIProvider, AppConfig

logger = logging.getLogger(__name__)


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


_cached_handler: ChatHandler | None = None
_cached_provider: AIProvider | None = None
_handler_lock = threading.Lock()


def create_handler(config: AppConfig) -> ChatHandler:
    """Create or return the cached AI handler for the active provider.

    Reuses the same handler instance across requests so that
    runtime state (e.g. Responses API fallback) is preserved.

    Parameters:
        config: Application configuration with provider info.

    Returns:
        ChatHandler: An AIHandler or CopilotAIHandler instance.

    Raises:
        ValueError: If the provider config is incomplete.
    """
    global _cached_handler, _cached_provider

    if _cached_handler is not None and _cached_provider == config.provider:
        return _cached_handler

    with _handler_lock:
        # Double-check after acquiring lock
        if _cached_handler is not None and _cached_provider == config.provider:
            return _cached_handler

        logger.info(
            "Creating AI handler for provider=%s",
            config.provider.value,
        )
        if config.provider == AIProvider.COPILOT:
            from src.copilot_handler import CopilotAIHandler

            if config.copilot is None:
                msg = "Copilot provider selected but no config provided."
                raise ValueError(msg)
            _cached_handler = CopilotAIHandler(config.copilot)  # type: ignore[return-value]
            _cached_provider = config.provider
            return _cached_handler

        # Default: Azure
        from src.ai_handler import AIHandler

        if config.azure is None:
            msg = "Azure provider selected but no config provided."
            raise ValueError(msg)
        _cached_handler = AIHandler(config.azure)  # type: ignore[return-value]
        _cached_provider = config.provider
        return _cached_handler
