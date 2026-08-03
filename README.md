# Vortexia Chatbot (V0)

Widget de chat IA basé RAG, embarquable, anti-hallucination. Voir la spec Notion.

## Démarrage

```bash
cp .env.example .env      # remplir les clés Azure
docker compose up --build
curl localhost:8000/health
```

`/health` renvoie `200 {"status":"ok"}` quand Postgres, Redis et la config Azure
sont OK, sinon `503 degraded` avec le détail par check.

## Stack

- **api/** — FastAPI (Python 3.11), asyncpg, redis
- **db/init.sql** — schéma Postgres + pgvector (appliqué au 1er boot)
- Redis 7 — cache & rate limit

## Roadmap

Suivre la roadmap 3 semaines de la spec. Fait : Soirée 1 (infra + /health).
