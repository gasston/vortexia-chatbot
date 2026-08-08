"""Vortexia admin CLI: ingest (crawl→extract→chunk→embed→DB) and chat (REPL)."""
import asyncio
import hashlib

import asyncpg
import typer
from rich.progress import track

from . import rag, suggestions
from .config import settings
from .embeddings import embed
from .ingest.chunker import chunk, count_tokens
from .ingest.crawler import crawl
from .ingest.extractor import extract
from .retriever import to_vector

app = typer.Typer(help="Vortexia chatbot admin CLI")


@app.callback()
def _main():
    """Keep sub-command naming even with a single command registered."""


async def _ingest(
    url: str, tenant: str, dry_run: bool, activate: bool = False, name: str | None = None
) -> list[str]:
    pages = await crawl(url)
    typer.echo(f"crawled {len(pages)} pages")
    docs = [d for d in (extract(u, h) for u, h in pages.items()) if d]
    typer.echo(f"kept {len(docs)} pages (>200 chars after extraction)")

    if dry_run:
        total = sum(len(chunk(d["markdown"])) for d in docs)
        typer.echo(f"[dry-run] would produce {total} chunks (no embed, no DB)")
        return []

    pool = await asyncpg.create_pool(settings.database_url)
    await pool.execute(
        """INSERT INTO tenants (id, display_name, source_url) VALUES ($1, $2, $3)
           ON CONFLICT (id) DO UPDATE SET source_url = EXCLUDED.source_url,
                                          display_name = EXCLUDED.display_name""",
        tenant, name or tenant, url,
    )
    await pool.execute("DELETE FROM sources WHERE tenant_id = $1", tenant)  # fresh re-ingest

    n_chunks = 0
    for d in track(docs, description="Embedding pages"):
        chunks = chunk(d["markdown"])
        content_hash = hashlib.sha256(d["markdown"].encode()).hexdigest()
        source_id = await pool.fetchval(
            """INSERT INTO sources (tenant_id, url, title, content_hash)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (tenant_id, content_hash) DO NOTHING RETURNING id""",
            tenant, d["url"], d["title"], content_hash,
        )
        if source_id is None:  # duplicate content within this crawl
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

    typer.echo(f"persisted {len(docs)} sources, {n_chunks} chunks for tenant '{tenant}'")

    # Suggestions: 3 visitor questions from the site's H2 headings (spec 4.5 étape 6)
    h2s = suggestions.extract_h2s([d["markdown"] for d in docs])
    questions = await suggestions.generate(tenant, h2s)
    await pool.execute("DELETE FROM suggestions WHERE tenant_id = $1", tenant)
    for i, q in enumerate(questions, start=1):
        await pool.execute(
            "INSERT INTO suggestions (tenant_id, question, position) VALUES ($1, $2, $3)",
            tenant, q, i,
        )
    typer.echo(f"generated {len(questions)} suggestions from {len(h2s)} H2 headings")

    # Warm-up: run each suggestion through RAG, log quality (spec 4.5 étape 7)
    tenant_row = dict(await pool.fetchrow("SELECT * FROM tenants WHERE id = $1", tenant))
    for q in questions:
        cited = False
        async for ev in rag.answer(pool, tenant_row, [], q):
            if ev["type"] == "sources" and ev["sources"]:
                cited = True
        typer.echo(f"  warm-up [{'ok' if cited else 'FALLBACK'}] {q}")

    # Activation (spec 4.5 étape 7): default active on ingest, 30-day auto-expiry for demos
    if activate:
        await pool.execute(
            "UPDATE tenants SET status = 'active', expires_at = NOW() + INTERVAL '30 days' "
            "WHERE id = $1",
            tenant,
        )
        typer.echo("activated (expires in 30 days)")

    await pool.close()
    return questions


@app.command()
def ingest(
    url: str = typer.Option(..., help="Root URL to crawl"),
    tenant: str = typer.Option(..., help="Tenant id"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Crawl+chunk only, skip embed+DB"),
):
    """Crawl a site, extract + chunk, embed, and persist to Postgres/pgvector."""
    asyncio.run(_ingest(url, tenant, dry_run))


demo = typer.Typer(help="Provisioning de démos prospect")
app.add_typer(demo, name="demo")


@demo.command("create")
def demo_create(
    url: str = typer.Option(..., help="URL racine du site à ingérer"),
    tenant: str = typer.Option(..., help="Tenant id (= sous-domaine de la démo)"),
    name: str = typer.Option(None, help="Nom affiché (défaut: tenant id)"),
):
    """Provisionne une démo de bout en bout et affiche l'URL + suggestions à coller dans un mail."""
    questions = asyncio.run(_ingest(url, tenant, dry_run=False, activate=True, name=name))
    demo_url = f"https://{tenant}.{settings.demo_domain}"
    typer.echo("\n" + "─" * 52)
    typer.secho(f"✅ Démo prête : {demo_url}", fg=typer.colors.GREEN, bold=True)
    if questions:
        typer.echo("Questions suggérées (à coller dans le cold email) :")
        for q in questions:
            typer.echo(f"  • {q}")
    typer.echo("─" * 52)


async def _chat(tenant_id: str):
    pool = await asyncpg.create_pool(settings.database_url)
    row = await pool.fetchrow("SELECT * FROM tenants WHERE id = $1", tenant_id)
    if row is None:
        typer.echo(f"tenant '{tenant_id}' introuvable — lance d'abord `ingest`")
        await pool.close()
        return
    tenant = dict(row)
    history: list[dict] = []
    typer.echo(f"Chat « {tenant['display_name']} » — Ctrl-D pour quitter")

    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            continue

        answer, sources = "", []
        async for ev in rag.answer(pool, tenant, history, question):
            if ev["type"] == "token":
                print(ev["delta"], end="", flush=True)
                answer += ev["delta"]
            elif ev["type"] == "sources":
                sources = ev["sources"]
        print()
        if sources:
            typer.echo("Sources : " + ", ".join(s["url"] for s in sources))
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})

    await pool.close()


@app.command()
def chat(tenant: str = typer.Option(..., help="Tenant id")):
    """Interactive RAG REPL against an ingested tenant."""
    asyncio.run(_chat(tenant))


if __name__ == "__main__":
    app()
