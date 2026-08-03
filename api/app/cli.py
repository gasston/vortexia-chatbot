"""Vortexia CLI. V0: ingestion pipeline (crawl → extract → chunk → JSONL).

Persistence (embeddings + DB insert) lands Soirée 3.
"""
import asyncio
import json

import typer

from .ingest.chunker import chunk, count_tokens
from .ingest.crawler import crawl
from .ingest.extractor import extract

app = typer.Typer(help="Vortexia chatbot admin CLI")


@app.callback()
def _main():
    """Keep sub-command naming even with a single command registered."""


async def _run(url: str, tenant: str, out: str):
    pages = await crawl(url)
    typer.echo(f"crawled {len(pages)} pages")

    docs = [d for d in (extract(u, h) for u, h in pages.items()) if d]
    typer.echo(f"kept {len(docs)} pages (>200 chars after extraction)")

    records = []
    for d in docs:
        for i, c in enumerate(chunk(d["markdown"])):
            records.append({
                "tenant": tenant,
                "url": d["url"],
                "title": d["title"],
                "chunk_index": i,
                "tokens": count_tokens(c),
                "content": c,
            })

    with open(out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    toks = [r["tokens"] for r in records]
    typer.echo(f"produced {len(records)} chunks → {out}")
    if toks:
        typer.echo(f"tokens: min={min(toks)} max={max(toks)} avg={sum(toks) // len(toks)}")


@app.command()
def ingest(
    url: str = typer.Option(..., help="Root URL to crawl"),
    tenant: str = typer.Option(..., help="Tenant id"),
    out: str = typer.Option("chunks.jsonl", help="Output JSONL path"),
):
    """Crawl a site, extract + chunk its content, write chunks to JSONL."""
    asyncio.run(_run(url, tenant, out))


if __name__ == "__main__":
    app()
