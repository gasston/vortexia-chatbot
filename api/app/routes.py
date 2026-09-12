"""Public v1 API: sessions, tenant config, SSE chat."""
import asyncio
import json
import time
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import rag
from .config import settings
from .deps import client_ip, enforce_rate_limit, ip_hash, require_admin, resolve_tenant
from .observability import CHAT_LATENCY, CHAT_REQUESTS, log
from .provision import create_demo

router = APIRouter(prefix="/v1")

HISTORY_TURNS = 6


class ChatIn(BaseModel):
    session_id: str
    message: str


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(400, "invalid session_id")


@router.post("/sessions")
async def create_session(request: Request, tenant=Depends(resolve_tenant)):
    session_id = await request.app.state.pool.fetchval(
        "INSERT INTO sessions (tenant_id, ip_hash, user_agent) VALUES ($1, $2, $3) RETURNING id",
        tenant["id"], ip_hash(client_ip(request)), request.headers.get("user-agent"),
    )
    return {"session_id": str(session_id)}


@router.get("/tenants/{tenant_id}/config")
async def tenant_config(tenant_id: str, request: Request):
    pool = request.app.state.pool
    row = await pool.fetchrow("SELECT * FROM tenants WHERE id = $1", tenant_id)
    if row is None or row["status"] != "active":
        raise HTTPException(404, "tenant not found")

    suggestions, pages_count, sample_pages, scripted_qa = await asyncio.gather(
        pool.fetch("SELECT question FROM suggestions WHERE tenant_id = $1 ORDER BY position", tenant_id),
        pool.fetchval("SELECT COUNT(*) FROM sources WHERE tenant_id = $1", tenant_id),
        pool.fetch("SELECT title, url FROM sources WHERE tenant_id = $1 ORDER BY fetched_at LIMIT 6", tenant_id),
        pool.fetch("SELECT question, answer, source_url FROM scripted_qa WHERE tenant_id = $1 ORDER BY position", tenant_id),
    )

    return {
        "tenant_id": row["id"],
        "display_name": row["display_name"],
        "logo_url": row["logo_url"],
        "primary_color": row["primary_color"],
        "suggestions": [r["question"] for r in suggestions],
        "pages_count": pages_count or 0,
        "crawled_at": row["created_at"].date().isoformat() if row["created_at"] else None,
        "sample_pages": [{"title": r["title"], "url": r["url"]} for r in sample_pages],
        "scripted_qa": [
            {"question": r["question"], "answer": r["answer"], "source_url": r["source_url"]}
            for r in scripted_qa
        ],
    }


@router.post("/chat")
async def chat(body: ChatIn, request: Request, tenant=Depends(resolve_tenant)):
    pool = request.app.state.pool
    redis = request.app.state.redis
    session_id = _uuid(body.session_id)

    if await pool.fetchval(
        "SELECT 1 FROM sessions WHERE id = $1 AND tenant_id = $2", session_id, tenant["id"]
    ) is None:
        raise HTTPException(404, "session not found")

    try:
        await enforce_rate_limit(redis, tenant["id"], ip_hash(client_ip(request)))
    except HTTPException:
        CHAT_REQUESTS.labels(tenant["id"], "rate_limited").inc()
        raise

    # history = prior turns of this session (spec R6: kept during session)
    rows = await pool.fetch(
        "SELECT role, content FROM messages WHERE session_id = $1 "
        "ORDER BY created_at DESC LIMIT $2",
        session_id, HISTORY_TURNS,
    )
    history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    await pool.execute(
        "INSERT INTO messages (session_id, tenant_id, role, content) VALUES ($1, $2, 'user', $3)",
        session_id, tenant["id"], body.message,
    )
    await pool.execute("UPDATE sessions SET last_seen_at = NOW() WHERE id = $1", session_id)

    async def event_stream():
        start = time.time()
        parts, sources = [], []
        async for ev in rag.answer(pool, tenant, history, body.message):
            if ev["type"] == "token":
                parts.append(ev["delta"])
                yield _sse("token", {"delta": ev["delta"]})
            elif ev["type"] == "sources":
                sources = ev["sources"]
                yield _sse("sources", {"sources": sources})
            elif ev["type"] == "done":
                latency_ms = int((time.time() - start) * 1000)
                message_id = await pool.fetchval(
                    "INSERT INTO messages "
                    "(session_id, tenant_id, role, content, sources_cited, latency_ms) "
                    "VALUES ($1, $2, 'assistant', $3, $4::jsonb, $5) RETURNING id",
                    session_id, tenant["id"], "".join(parts), json.dumps(sources), latency_ms,
                )
                CHAT_REQUESTS.labels(tenant["id"], "ok").inc()
                CHAT_LATENCY.labels(tenant["id"]).observe(time.time() - start)
                log.info(
                    "chat_done", tenant_id=tenant["id"], session_id=str(session_id),
                    latency_ms=latency_ms, sources=len(sources),
                )
                yield _sse("done", {"message_id": str(message_id), "latency_ms": latency_ms})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class TenantPatch(BaseModel):
    status: str | None = None  # 'active' | 'inactive' → deactivation (US-A2)
    expires_at: datetime | None = None
    fallback_message: str | None = None


@router.patch("/admin/tenants/{tenant_id}", dependencies=[Depends(require_admin)])
async def admin_patch_tenant(tenant_id: str, body: TenantPatch, request: Request):
    # keys are whitelisted by TenantPatch fields → safe to interpolate as columns
    fields = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not fields:
        raise HTTPException(400, "no fields to update")
    sets = ", ".join(f"{k} = ${i + 2}" for i, k in enumerate(fields))
    res = await request.app.state.pool.execute(
        f"UPDATE tenants SET {sets} WHERE id = $1", tenant_id, *fields.values()
    )
    if res.endswith(" 0"):
        raise HTTPException(404, "tenant not found")
    return {"updated": list(fields)}


class DemoIn(BaseModel):
    url: str
    tenant: str
    name: str | None = None


@router.post("/admin/demos", dependencies=[Depends(require_admin)])
async def admin_create_demo(body: DemoIn, request: Request):
    result = await create_demo(request.app.state.pool, body.url, body.tenant, body.name)
    return {
        **result,
        "demo_url": f"https://demo.{settings.demo_domain}/?tenant={body.tenant}",
    }


@router.delete("/admin/tenants/{tenant_id}", dependencies=[Depends(require_admin)])
async def admin_delete_tenant(tenant_id: str, request: Request):
    # ON DELETE CASCADE purges sources, chunks, suggestions, sessions, messages
    res = await request.app.state.pool.execute("DELETE FROM tenants WHERE id = $1", tenant_id)
    if res.endswith(" 0"):
        raise HTTPException(404, "tenant not found")
    log.info("tenant_deleted", tenant_id=tenant_id)
    return {"deleted": tenant_id}
