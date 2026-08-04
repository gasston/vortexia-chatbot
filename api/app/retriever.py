"""pgvector retrieval, always filtered by tenant_id (multi-tenancy)."""

TOP_K = 5

_SQL = """
    SELECT c.content, s.url, s.title,
           1 - (c.embedding <=> $2::vector) AS score
    FROM chunks c
    JOIN sources s ON s.id = c.source_id
    WHERE c.tenant_id = $1
    ORDER BY c.embedding <=> $2::vector
    LIMIT $3
"""


def to_vector(embedding: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in embedding) + "]"


async def retrieve(pool, tenant_id: str, query_embedding: list[float], k: int = TOP_K):
    rows = await pool.fetch(_SQL, tenant_id, to_vector(query_embedding), k)
    return [dict(r) for r in rows]
