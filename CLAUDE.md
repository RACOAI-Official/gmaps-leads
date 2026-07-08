# gmaps-leads

Lead-gen pipeline: scrape Google Maps businesses (Dhaka + Kerala), store in Postgres,
browse/filter in React SPA, export CSV. Later: website enrichment (email/socials/tech) + hybrid fit scoring.

See ARCHITECTURE.md (system design), PLAN.md (phased roadmap + status), SOUL.md (scraper operating principles).

## Hard rules
- `reference/` is READ-ONLY inspiration. NEVER import from it, copy files out of it, or modify it.
- All Google Maps DOM selectors live ONLY in `app/scraper/selectors.py`. Never inline selectors elsewhere.
- Politeness limits (delays, daily cap) are config (`.env` → `app/config.py`) — never hardcode or bypass. See SOUL.md.
- LLM calls go through OpenAI-compatible client with configurable `base_url` (GLM/Z.ai endpoint). No hardcoded OpenAI.
- Python: use `.venv/bin/python` / `.venv/bin/pip` (venv + pip + requirements.txt). No global installs.

## Decisions (2026-07-08)
- Engine: Botasaurus browser mode (anti-detection; single residential IP, no proxies yet)
- Stack: Python (Botasaurus + FastAPI) + Vite/React SPA (TanStack Table/Query, Tailwind + shadcn)
- DB: PostgreSQL 16 (Docker local now, port 5433; VPS later). SQLAlchemy 2 + Alembic.
- Jobs: Postgres `jobs` table as queue; scraper = separate polling process. No Redis.
- Enrichment: httpx+BS4 async crawl, browser fallback for JS-only sites. No paid APIs.
- Scoring: rules engine for all + GLM on-demand explain/re-score. Built after enrichment.
- Deploy: all local on Mac until proxy budget; then web stack → VPS, scraper stays residential.
- Politeness: conservative — 3–8s random delays, ~300–500 places/day, cache, checkpoint resume,
  CAPTCHA detection → abort job + cooldown. Headful Chrome.
- Dedup key: `place_key` from Maps place URL id (fallback name+address hash).
- First slice: "software company in Dhaka".

## Reference repos (patterns only)
- reference/Google-Maps-Scrapper/main.py — DOM selectors + scroll-until-stall pattern
- reference/business-leads-ai-automation/ — rules scoring weights, jobs/processor shape, CSV escaping
- reference/google-maps-scraper/fields.md — target field schema; advanced.md — dedup/scale expectations
- scraper/botasaurus-starter/ — Botasaurus framework usage patterns (also reference, not imported)
