# PLAN.md — Phased Roadmap (living doc)

Each phase gates on its test. Update checkboxes as phases complete.

## Phase 0 — Scaffold + DB + docs ✅
Repo structure, docker-compose Postgres 16, SQLAlchemy models + Alembic, `.env` config,
CLAUDE.md + ARCHITECTURE.md + PLAN.md + SOUL.md.
**Gate:** `docker compose up -d db && alembic upgrade head` → tables exist; psql insert/select round-trip; docs consistent.
- [x] passed (2026-07-08: 5 tables created, round-trip OK, 4 docs written)

## Phase 1 — Scraper MVP (first slice: "software company in Dhaka")
Botasaurus `@browser` headful task: Maps search → scroll `[role="feed"]` until stall → click cards →
extract via `app/scraper/selectors.py` → upsert by `place_key`. Politeness module (delays, daily cap,
checkpoint, CAPTCHA abort → `blocked` + cooldown). CLI `python -m app.scraper run --query ...` + `--smoke-test`.
**Gate:** 100+ Dhaka software companies in Postgres with category + phone/website; re-run = no dupes; smoke test green.
- [x] mechanism validated (2026-07-08): smoke test green; run stopped early at user request after 30 software
      leads (108 links were queued) — 30/30 category, 29/30 website, 30/30 phone; upsert idempotency proven
      (re-upsert = 0 new rows). Full 100+ sweep deferred to a later polite run.

## Phase 2 — API
FastAPI: `GET /leads` (filters: city, category, has_website, has_phone, min_rating, search; paginate/sort),
`GET /leads/{id}`, `GET /export.csv` (streamed, same filters), `POST/GET /jobs`. CORS for Vite dev.
**Gate:** curl each endpoint against phase-1 data; CSV opens clean in spreadsheet.
- [x] passed (2026-07-08): /leads (filters/sort/paginate), /leads/{id}, 404, /export.csv, /jobs all verified via curl.

## Phase 3 — Frontend
Vite + React SPA: TanStack Table leads view (filters/sort/pagination), detail drawer, Export CSV
(current filters), Jobs page (trigger + status poll via TanStack Query).
**Gate:** browse/filter/export in browser; UI-triggered job picked up by scraper poller → rows appear.
- [x] built + live-verified (2026-07-08). Starline light theme applied: pill sidebar (lime active,
      greyed future items), topbar w/ live lead count, panels, muted-grey table w/ Address column,
      lime pill pagination, detail drawer. `npm run build` green; browser walkthrough of Leads/Jobs/drawer OK.
      (Scraper-poller end-to-end from UI still deferred — one-life politeness.)

## Phase 4 — Coverage expansion
Query grid = category templates × locations (Dhaka areas; Kerala per-city: Kochi, Trivandrum, Kozhikode…).
Job fan-out (daily-cap aware), cross-query dedup by `place_key` (expect 20–40% overlap). Add schools + commercial categories.
**Gate:** 2 categories × 3 areas run; dedup rate logged; no cap violations; per-city/category counts in UI.
- [ ] passed

## Phase 5 — Enrichment
Async httpx crawler: homepage + ≤4 contact-ish pages → emails (mailto + regex + junk filter), socials
(footer links), tech stack (~20 fingerprints: WordPress, Shopify, Wix, Next.js, React, jQuery, Laravel, GA/GTM…).
Near-empty HTML → `needs_browser` → Botasaurus fallback. Runs as `enrich` job, concurrency ~20. UI columns + filters.
**Gate:** Dhaka software slice enriched; % email found reported; 10 spot-checks pass; fallback tier fires on a JS-only site.
- [ ] passed

## Phase 6 — Scoring
`rules.py`: weighted signals (phone, website presence/absence-as-opportunity, rating, reviews, category weight,
tech signals, email found) → 0–100 + factors[]. Batch `score` job. `llm.py`: OpenAI SDK → `LLM_BASE_URL` (GLM/Z.ai),
on-demand explain/re-score from enriched site text, graceful fallback. UI: score column + explain button.
**Gate:** all enriched leads scored; factors visible; GLM explain coherent for 5 samples; rules deterministic.
- [ ] passed

## Phase 7 — VPS deploy (when ready / proxies exist)
Dockerize API + built SPA (nginx) + Postgres on VPS; pg_dump cron. Scraper stays on Mac via SSH tunnel.
**Gate:** UI reachable on VPS; Mac scraper writes to VPS DB; backup restore verified.
- [ ] passed

## Out of scope (deferred)
Proxies/multi-worker, Redis/Celery, outreach content generation, CRM, auth/multi-user,
Kerala full-state sweep before pipeline validated.
