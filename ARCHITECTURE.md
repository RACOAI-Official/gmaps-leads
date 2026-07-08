# ARCHITECTURE.md

## Components

```
┌──────────────────────── Mac (now) / VPS (later) ────────────────────────┐
│                                                                          │
│  ┌─────────────┐   polls jobs    ┌──────────────┐    HTTP    ┌────────┐  │
│  │  Scraper     │◄───────────────│  PostgreSQL  │◄───────────│FastAPI │◄─┼── Browser
│  │  process     │───upserts─────►│  (Docker,    │            │  API   │  │   (Vite/React SPA:
│  │  (Botasaurus │                │   port 5433) │            └────────┘  │    table, filters,
│  │   headful    │                │  businesses  │                        │    jobs, CSV export)
│  │   Chrome)    │                │  jobs        │                        │
│  └─────────────┘                │  enrichments │                        │
│         │                        │  scores      │                        │
│  ┌─────────────┐                └──────────────┘                        │
│  │ Enrichment   │  (phase 5) httpx+BS4 crawl of lead websites;          │
│  │ worker       │  browser fallback tier for JS-only sites              │
│  └─────────────┘                                                        │
│  ┌─────────────┐  (phase 6) rules score all leads; GLM endpoint         │
│  │ Scoring      │  (OpenAI-compatible, LLM_BASE_URL) explains on demand │
│  └─────────────┘                                                        │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Scraper process** (`app/scraper/`): separate long-running/CLI process. Never inside the API request
  cycle (browser jobs run minutes–hours). Polls `jobs` for `pending` scrape jobs, or is invoked directly:
  `python -m app.scraper run --query "..."`.
- **FastAPI** (`app/api/`): read/serve layer — leads list + filters, CSV export, job create/list. Serves built SPA in prod.
- **React SPA** (`frontend/`): Vite + React, TanStack Table (filter/sort/paginate), TanStack Query (API + job status polling), Tailwind + shadcn/ui.
- **PostgreSQL**: single source of truth AND the job queue (a `jobs` row = a queued job). No Redis/Celery —
  single IP means effectively one polite scrape worker; a real queue buys nothing yet.

## Data flow

query → scrape (Maps search → scroll feed → click card → extract via `selectors.py`) →
upsert `businesses` by `place_key` → [phase 5] enrich (crawl lead website → emails/socials/tech_stack) →
[phase 6] score (rules for all, GLM explain on demand) → browse/filter in SPA → export CSV.

## Data model

| Table | Purpose | Key columns |
|---|---|---|
| `businesses` | one row per unique place | `place_key` (unique; from Maps place URL id, fallback sha1(name\|address)), name, main_category, categories JSONB, address, city, area, lat/lng, phone, website, rating, reviews_count, socials JSONB, raw JSONB, source_query, scraped_at |
| `jobs` | queue + history | type (scrape/enrich/score), params JSONB, status (pending/running/done/failed/blocked), progress, error, timestamps |
| `enrichments` | 1:1 per enriched business | emails JSONB, socials JSONB, tech_stack JSONB, status (ok/empty/needs_browser/failed) |
| `scores` | 1:1 per scored business | score 0–100, factors JSONB, llm_summary |

Field targets follow `reference/google-maps-scraper/fields.md` (subset). Email is NOT a Maps field — enrichment only.

## Deployment topology

- **Now (all-local)**: everything on the Mac — Postgres in Docker (5433), FastAPI dev server, Vite dev server,
  scraper headful Chrome on the residential IP.
- **Later (phase 7)**: API + built SPA (nginx) + Postgres dockerized on VPS with pg_dump cron backups.
  Scraper STAYS on the Mac (residential IP survives longest without proxies), polling VPS Postgres via SSH tunnel.
  When proxy budget exists, the scraper can move to the VPS behind residential proxies — only the polling
  process's location changes.

## Why these choices (brief)

- **Botasaurus browser mode**: single IP, no proxies → anti-detection is the binding constraint; that is
  Botasaurus's entire purpose. Worst-case exit cost is low (extraction = selectors + scroll loop).
- **Postgres now**: user decision — kills the migration question, JSONB for enrichment blobs, concurrent writers forever.
- **Jobs table over Redis queue**: one polite worker by physics (one IP). A table gives UI trigger + status +
  history at one table's complexity. If proxies/multi-worker arrive, swap dispatch layer only.
- **Vite SPA over Next.js**: internal tool, no SEO; app = filterable table + drawer + export. Static build, no JS server runtime.

## Scraper characteristics

Defined in SOUL.md (polite, one-life, breakage-honest, resumable, traceable, read-only ethics).
Politeness knobs live in `.env` → `app/config.py`. Selectors ONLY in `app/scraper/selectors.py`.
