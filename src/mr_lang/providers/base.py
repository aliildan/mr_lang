"""Model provider factory."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel

from mr_lang.exceptions import ProviderError


def get_chat_model(provider: str, model: str, **kwargs: Any) -> BaseChatModel:
    """Create a chat model instance from provider name and model ID.

    Args:
        provider: Provider name (ollama, openai, anthropic)
        model: Model name/ID
        **kwargs: Additional provider-specific parameters

    Returns:
        Configured BaseChatModel instance
    """
    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError as err:
            raise ProviderError("Install langchain-ollama: pip install mr-lang[ollama]") from err
        return ChatOllama(model=model, **kwargs)

    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as err:
            raise ProviderError("Install langchain-openai: pip install mr-lang[openai]") from err
        return ChatOpenAI(model=model, **kwargs)

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as err:
            raise ProviderError(
                "Install langchain-anthropic: pip install mr-lang[anthropic]"
            ) from err
        return ChatAnthropic(model=model, **kwargs)

    raise ProviderError(f"Unknown provider: {provider}. Supported: ollama, openai, anthropic")
