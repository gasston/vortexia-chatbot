"""Shared OpenAI async client (lazy singleton).

ponytail: plain OpenAI in V0. Swap to AsyncAzureOpenAI here (+ endpoint/version
in config) when moving client data to Azure EU for RGPD in production.
"""
from openai import AsyncOpenAI

from .config import settings

_client: AsyncOpenAI | None = None


def client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client
