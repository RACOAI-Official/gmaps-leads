"""Scraper CLI.

  python -m app.scraper run --query "software company in Dhaka" --city Dhaka [--max 120]
  python -m app.scraper smoke-test

Job polling for all job types (scrape | enrich | score) now lives in
``app.worker`` (``python -m app.worker poll``), the single unified worker.
"""

import argparse
import logging
import sys
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import Business
from app.db.session import SessionLocal

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("scraper.cli")


def cmd_run(args) -> int:
    from app.scraper.maps_task import run_query

    result = run_query(args.query, args.city, args.max)
    log.info("result: %s", result)
    return 2 if result.get("blocked") else 0


def cmd_smoke_test(_args) -> int:
    """Scrape 3 places for a stable query; assert core fields extract (SOUL.md #3)."""
    from app.scraper.maps_task import run_query
    from app.db.models import Business

    query = "coffee shop in Dhaka"
    before = datetime.now(timezone.utc)
    result = run_query(query, "Dhaka", max_results=3)
    if result.get("blocked"):
        log.error("SMOKE TEST: BLOCKED — do not scrape today. %s", result["error"])
        return 2

    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(Business).where(
                    Business.source_query == query, Business.scraped_at >= before
                )
            )
        )
    ok = 0
    for b in rows:
        has_core = bool(b.name and b.main_category)
        has_contact = bool(b.phone or b.website)
        log.info(
            "  %s | category=%s phone=%s website=%s -> %s",
            b.name, b.main_category, b.phone, bool(b.website),
            "OK" if has_core and has_contact else "WEAK",
        )
        if has_core and has_contact:
            ok += 1
    fresh = len(rows) + result.get("skipped_existing", 0)
    if fresh == 0:
        log.error("SMOKE TEST FAILED: nothing extracted — selectors are broken.")
        return 1
    if len(rows) > 0 and ok == 0:
        log.error("SMOKE TEST FAILED: rows extracted but core fields empty — selector rot.")
        return 1
    log.info("SMOKE TEST PASSED (%d/%d rows with core+contact fields)", ok, len(rows))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.scraper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="scrape one query now")
    p_run.add_argument("--query", required=True)
    p_run.add_argument("--city", default=None)
    p_run.add_argument("--max", type=int, default=120)
    p_run.set_defaults(fn=cmd_run)

    p_smoke = sub.add_parser("smoke-test", help="verify selectors on 3 known places")
    p_smoke.set_defaults(fn=cmd_smoke_test)

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
