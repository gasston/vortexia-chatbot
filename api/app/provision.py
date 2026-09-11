"""Core demo provisioning logic shared by CLI and HTTP endpoint."""
import hashlib

from . import rag, suggestions
from .embeddings import embed
from .ingest.chunker import chunk, count_tokens
from .ingest.crawler import crawl
from .ingest.extractor import extract
from .retriever import to_vector


async def create_demo(pool, url: str, tenant: str, name: str | None = None) -> dict:
    """Crawl url, embed, persist tenant + chunks, activate. Returns demo metadata."""
    pages = await crawl(url)
    docs = [d for d in (extract(u, h) for u, h in pages.items()) if d]

    await pool.execute(
        """INSERT INTO tenants (id, display_name, source_url) VALUES ($1, $2, $3)
           ON CONFLICT (id) DO UPDATE SET source_url = EXCLUDED.source_url,
                                          display_name = EXCLUDED.display_name""",
        tenant, name or tenant, url,
    )
    await pool.execute("DELETE FROM sources WHERE tenant_id = $1", tenant)

    n_chunks = 0
    for d in docs:
        chunks = chunk(d["markdown"])
        content_hash = hashlib.sha256(d["markdown"].encode()).hexdigest()
        source_id = await pool.fetchval(
            """INSERT INTO sources (tenant_id, url, title, content_hash)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (tenant_id, content_hash) DO NOTHING RETURNING id""",
            tenant, d["url"], d["title"], content_hash,
        )
        if source_id is None:
            continue
        embeddings = await embed(chunks)
        for i, (c, e) in enumerate(zip(chunks, embeddings)):
            await pool.execute(
                """INSERT INTO chunks
                   (tenant_id, source_id, chunk_index, content, tokens, embedding)
                   VALUES ($1, $2, $3, $4, $5, $6::vector)""",
                tenant, source_id, i, c, count_tokens(c), to_vector(e),
            )
            n_chunks += 1

    h2s = suggestions.extract_h2s([d["markdown"] for d in docs])
    questions = await suggestions.generate(tenant, h2s)
    await pool.execute("DELETE FROM suggestions WHERE tenant_id = $1", tenant)
    for i, q in enumerate(questions, start=1):
        await pool.execute(
            "INSERT INTO suggestions (tenant_id, question, position) VALUES ($1, $2, $3)",
            tenant, q, i,
        )

    await pool.execute(
        "UPDATE tenants SET status = 'active', expires_at = NOW() + INTERVAL '30 days' WHERE id = $1",
        tenant,
    )

    return {
        "tenant": tenant,
        "pages_crawled": len(pages),
        "chunks": n_chunks,
        "suggestions": questions,
    }
