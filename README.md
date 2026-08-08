# Vortexia Chatbot (V0)

Widget de chat IA basé **RAG**, embarquable, strictement anti-hallucination
(« je ne sais pas » plutôt qu'inventer). Double usage : démo de prospection +
livrable client. Spec complète : Notion.

## Architecture

```
Nuxt (web/, page démo)  ─┐
Widget Lit (widget/)    ─┼─► FastAPI (api/) ─► Postgres+pgvector ─ Redis ─ OpenAI
CLI (app.cli)           ─┘        /v1, /health, /metrics
```

- **api/** — FastAPI (Python 3.11) : SSE chat, RAG (embed → pgvector → LLM), admin
- **web/** — Nuxt 3 SPA, page démo par sous-domaine `{tenant}.demo.vortexia.agency`
- **widget/** — Web Component Lit 3 (`<vortexia-chat>`), bundle `< 40 KB` gzip
- **db/init.sql** — schéma Postgres + pgvector (appliqué au 1er boot)

## Démarrage local

```bash
cp .env.example .env      # remplir OPENAI_API_KEY, ADMIN_API_KEY, IP_SALT
docker compose up -d db redis api
curl localhost:8000/health           # 200 {"status":"ok"} si db+redis+openai OK
```

Front (contre l'API locale) :

```bash
cd web    && pnpm install && pnpm dev   # http://localhost:3000/?tenant=vortexia
cd widget && pnpm install && pnpm dev   # http://localhost:5173/ (widget en bas à droite)
```

## CLI (provisioning & debug)

Toutes les commandes tournent dans le conteneur api :

```bash
# Ingestion seule (crawl → extract → chunk → embed → suggestions → warm-up)
docker compose run --rm api python -m app.cli ingest --url=https://acme.com --tenant=acme

# Démo complète (ingestion + activation 30j + URL + suggestions à coller dans un mail)
docker compose run --rm api python -m app.cli demo create --url=https://acme.com --tenant=acme --name="ACME"

# REPL de chat contre un tenant ingéré
docker compose run --rm api python -m app.cli chat --tenant=acme

# Dry-run (crawl + chunk, sans embed ni DB)
docker compose run --rm api python -m app.cli ingest --url=https://acme.com --tenant=acme --dry-run
```

## API

### Public (widget & démo)
| Méthode | Endpoint | Note |
|---|---|---|
| `POST` | `/v1/sessions` | header `X-Tenant-Id`, retourne `session_id` |
| `GET`  | `/v1/tenants/{id}/config` | nom, logo, couleur, suggestions |
| `POST` | `/v1/chat` | header `X-Tenant-Id`, body `{session_id, message}`, **SSE** |

SSE : events `token {delta}`, `sources {sources[]}`, `done {message_id, latency_ms}`.

### Admin (header `X-Admin-Key`)
| Méthode | Endpoint | Note |
|---|---|---|
| `PATCH`  | `/v1/admin/tenants/{id}` | `status` (désactivation), `expires_at`, `fallback_message` |
| `DELETE` | `/v1/admin/tenants/{id}` | purge cascade (sources, chunks, sessions, messages) |

> Création de tenant + ingestion = via CLI (`demo create`). Les endpoints admin
> `POST tenants` / `POST ingest` async ne sont pas en V0 (le CLI foreground couvre le besoin).

## Observabilité

- **`GET /health`** — db + redis + présence clé OpenAI (`200 ok` / `503 degraded`)
- **`GET /metrics`** — Prometheus : `vortexia_chat_requests_total{tenant,status}`,
  `vortexia_chat_latency_seconds{tenant}`. (tokens LLM / pages ingérées : à ajouter
  avec l'ingestion in-process, cf. `observability.py`.)
- **Logs** — `structlog` JSON (`event`, `tenant_id`, `session_id`, `latency_ms`)

## Sécurité (V0)

- Rate limit Redis sliding-window : 30 msg/h/IP, 500 msg/j/tenant
- IP hashée SHA-256 + `IP_SALT` (aucune IP brute stockée)
- CORS `*` (widget) — à durcir en allowlist par tenant en V1
- Admin par clé statique `ADMIN_API_KEY`
- Anti-injection : instructions + délimiteurs dans le system prompt, pas de tools LLM

## Déploiement

Overlay Traefik wildcard + demo (Nuxt) + widget CDN :

```bash
# Requiert DNS *.demo.${DEMO_DOMAIN} + api.${DEMO_DOMAIN} + token DNS-01
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Variables prod (`.env`) : `DEMO_DOMAIN`, `ACME_EMAIL`, `CF_DNS_API_TOKEN`.
Le bundle widget se build via `widget/Dockerfile` (à servir sur `cdn.vortexia.agency/widget/v0/`).

## État V0

Soirées 1→9 faites. Reste avant prod : déploiement réel (DNS wildcard, TLS
Traefik, CDN widget) — le code est prêt et validé en local.
