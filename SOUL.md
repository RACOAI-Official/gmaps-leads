# SOUL.md — The Scraper's Character

These are the scraper's non-negotiable operating principles. Every scraping feature,
fix, or "optimization" must preserve all six. If a change violates one, the change is wrong.

## 1. Polite by default
- Randomized 3–8s delay between place-detail visits (`SCRAPE_DELAY_MIN_S`/`MAX_S`).
- Hard daily cap ~300–500 places (`SCRAPE_DAILY_CAP`). The cap is a config knob, never a code constant, never bypassed.
- Runs during human hours, not 3am hammering.
- Cache everything scraped: a place already in the DB is never re-fetched in the same sweep.

## 2. One life
- We scrape from a single residential IP with no proxy pool. That IP is the project's most valuable asset.
- On CAPTCHA / "unusual traffic" / consent-wall anomaly: **abort the job immediately**, mark it `blocked`,
  and cool down (`SCRAPE_COOLDOWN_HOURS`, default 6h). Never retry through a block. Never "try once more".

## 3. Breakage-honest
- Google WILL change the DOM. All selectors live in ONE file: `app/scraper/selectors.py`.
- Smoke test (`--smoke-test`: scrape 3 known places, assert name/category/phone-or-website non-null)
  runs before every scraping session. Red smoke test = stop, fix selectors, never scrape garbage.
- A field that can't be extracted is a logged `null` — never a silent empty string, never invented data.

## 4. Resumable
- Checkpoint per query: processed `place_key`s are recorded as they land.
- Crash, Ctrl-C, block, or laptop lid — nothing is lost; rerun continues where it stopped.

## 5. Traceable
- Every row carries `source_query`, `scraped_at`, and the `raw` extraction blob.
- Any datum in the UI can be traced back to which query found it and when.

## 6. Read-only ethics
- Public listing data only. No login-walled scraping, no review-author harvesting, no personal data beyond
  published business contact info.
- We acknowledge this violates Google's ToS; the response is minimal footprint, not evasion escalation:
  polite rates, caching, no parallel hammering, stop when told to stop (blocks).
