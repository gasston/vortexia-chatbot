"""RAG orchestration: embed query → retrieve → quality gate → stream answer.

Yields events matching the SSE contract (spec 4.4):
  {"type": "token",   "delta": str}
  {"type": "sources", "sources": [{"url","title"}]}
  {"type": "done"}
"""
from . import generator
from .embeddings import embed_one
from .retriever import retrieve

QUALITY_THRESHOLD = 0.3  # cosine similarity of best chunk (spec 4.6 étape 4)


async def answer(pool, tenant: dict, history: list[dict], question: str):
    q_emb = await embed_one(question)
    chunks = await retrieve(pool, tenant["id"], q_emb)

    if not chunks or chunks[0]["score"] < QUALITY_THRESHOLD:
        yield {"type": "token", "delta": tenant["fallback_message"]}
        yield {"type": "sources", "sources": []}
        yield {"type": "done"}
        return

    async for delta in generator.stream_answer(tenant, chunks, history, question):
        yield {"type": "token", "delta": delta}

    seen, sources = set(), []
    for c in chunks:  # dedupe by url, preserve retrieval order
        if c["url"] not in seen:
            seen.add(c["url"])
            sources.append({"url": c["url"], "title": c["title"]})
    yield {"type": "sources", "sources": sources}
    yield {"type": "done"}
