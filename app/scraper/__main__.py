"""Scraper CLI.

  python -m app.scraper run --query "software company in Dhaka" --city Dhaka [--max 120]
  python -m app.scraper smoke-test
  python -m app.scraper poll          # process pending scrape jobs from the jobs table
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import Job
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


def cmd_poll(args) -> int:
    from app.scraper.maps_task import run_query

    log.info("job poller started (interval %ds)", args.interval)
    while True:
        with SessionLocal() as session:
            job = session.scalars(
                select(Job)
                .where(Job.status == "pending", Job.type == "scrape")
                .order_by(Job.id)
                .limit(1)
            ).first()
            if job:
                job.status = "running"
                job.started_at = datetime.now(timezone.utc)
                session.commit()
                job_id, params = job.id, dict(job.params or {})

        if not job:
            time.sleep(args.interval)
            continue

        log.info("job %d: %s", job_id, params)
        result = run_query(
            params.get("query", ""),
            params.get("city"),
            int(params.get("max_results", 120)),
        )
        status = "done"
        if result.get("blocked"):
            status = "blocked"
        elif result.get("cap_reached"):
            status = "failed"
        with SessionLocal() as session:
            job = session.get(Job, job_id)
            job.status = status
            job.error = result.get("error")
            job.progress = result.get("scraped", 0)
            job.finished_at = datetime.now(timezone.utc)
            session.commit()
        log.info("job %d finished: %s", job_id, status)
        if status == "blocked":
            log.error("blocked — poller stopping; cool down before restart.")
            return 2


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

    p_poll = sub.add_parser("poll", help="process pending scrape jobs")
    p_poll.add_argument("--interval", type=int, default=10)
    p_poll.set_defaults(fn=cmd_poll)

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
