"""Shared Azure OpenAI async client (lazy singleton)."""
from openai import AsyncAzureOpenAI

from .config import settings

_client: AsyncAzureOpenAI | None = None


def client() -> AsyncAzureOpenAI:
    global _client
    if _client is None:
        _client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
    return _client
