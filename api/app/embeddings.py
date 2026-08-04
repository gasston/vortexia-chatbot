"""Batch embeddings via Azure OpenAI (text-embedding-3-small, 1536 dim)."""
import asyncio

from openai import APIConnectionError, APIStatusError, RateLimitError

from .config import settings
from .llm import client

BATCH = 100
MAX_RETRIES = 5


async def _create(texts: list[str]):
    for attempt in range(MAX_RETRIES):
        try:
            return await client().embeddings.create(
                model=settings.embedding_model,
                input=texts,
            )
        except (RateLimitError, APIConnectionError, APIStatusError):
            if attempt == MAX_RETRIES - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # exponential backoff


async def embed(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        resp = await _create(texts[i:i + BATCH])
        out.extend(d.embedding for d in resp.data)
    return out


async def embed_one(text: str) -> list[float]:
    return (await embed([text]))[0]
