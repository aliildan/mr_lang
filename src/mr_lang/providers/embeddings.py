"""Embedding provider factory."""

from __future__ import annotations

from typing import Any

from langchain_core.embeddings import Embeddings

from mr_lang.exceptions import ProviderError


def get_embeddings(provider: str, model: str, **kwargs: Any) -> Embeddings:
    """Create an embeddings instance from provider name and model ID.

    Args:
        provider: Provider name (ollama, openai)
        model: Embedding model name
        **kwargs: Additional provider-specific parameters
    """
    if provider == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings
        except ImportError as err:
            raise ProviderError("Install langchain-ollama: pip install mr-lang[ollama]") from err
        return OllamaEmbeddings(model=model, **kwargs)

    if provider == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as err:
            raise ProviderError("Install langchain-openai: pip install mr-lang[openai]") from err
        return OpenAIEmbeddings(model=model, **kwargs)

    raise ProviderError(f"Unknown embedding provider: {provider}. Supported: ollama, openai")
