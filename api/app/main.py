from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.asyncio import Redis

from .config import settings
from .observability import configure_logging
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    app.state.pool = await asyncpg.create_pool(settings.database_url)
    app.state.redis = Redis.from_url(settings.redis_url)
    yield
    await app.state.pool.close()
    await app.state.redis.aclose()


app = FastAPI(title="Vortexia Chatbot API", lifespan=lifespan)

# CORS: open for the embeddable widget in V0 (spec 4.10 — tighten to per-tenant allowlist in V1)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    checks = {}

    try:
        async with app.state.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"

    try:
        await app.state.redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # ponytail: config-presence only — don't burn OpenAI tokens on every probe.
    # Add a live embeddings ping if you need to detect key revocation.
    checks["openai"] = "ok" if settings.openai_api_key else "unconfigured"

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return JSONResponse(
        {"status": status, "checks": checks},
        status_code=200 if status == "ok" else 503,
    )


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
