"""Shared HTTP dependencies: tenant resolution, IP hashing, rate limiting, admin auth."""
import hashlib
import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Header, HTTPException, Request

from .config import settings

# Rate limits (spec R3): (limit, window_seconds)
RL_IP = (30, 3600)        # 30 messages / hour / IP
RL_TENANT = (500, 86400)  # 500 messages / day / tenant


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")  # set by Traefik
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def ip_hash(ip: str) -> str:
    return hashlib.sha256((settings.ip_salt + ip).encode()).hexdigest()


async def resolve_tenant(request: Request, x_tenant_id: str = Header(...)) -> dict:
    row = await request.app.state.pool.fetchrow(
        "SELECT * FROM tenants WHERE id = $1", x_tenant_id
    )
    if row is None:
        raise HTTPException(404, "tenant not found")
    tenant = dict(row)
    if tenant["status"] != "active":
        raise HTTPException(403, "tenant inactive")
    if tenant["expires_at"] is not None and tenant["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(403, "tenant expired")
    return tenant


async def require_admin(x_admin_key: str | None = Header(None)):
    # missing OR wrong key → 401 (not 422): both are "unauthenticated" at this trust boundary
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(401, "invalid admin key")


async def _sliding_window(redis, key: str, limit: int, window: int) -> bool:
    """True if under limit. Redis sorted-set sliding window (spec 4.10)."""
    now = time.time()
    async with redis.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zadd(key, {f"{now}-{uuid4().hex}": now})
        pipe.zcard(key)
        pipe.expire(key, window)
        res = await pipe.execute()
    return res[2] <= limit


async def enforce_rate_limit(redis, tenant_id: str, iph: str):
    ok_ip = await _sliding_window(redis, f"rl:ip:{iph}", *RL_IP)
    ok_tenant = await _sliding_window(redis, f"rl:tenant:{tenant_id}", *RL_TENANT)
    if not (ok_ip and ok_tenant):
        raise HTTPException(429, "rate limit exceeded")
