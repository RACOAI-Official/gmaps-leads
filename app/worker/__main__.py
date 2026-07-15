"""Unified worker CLI.

  python -m app.worker poll [--interval 10]   # process pending jobs of any type
  python -m app.worker enrich [--max 50]      # run enrichment now (no job row)
  python -m app.worker score [--max 100] [--explain]  # run scoring now
  python -m app.worker smoke-test             # delegate to the scraper smoke test

The ``poll`` loop is the long-running process started by ``scripts/start_all.sh``.
It handles ``scrape`` | ``enrich`` | ``score`` jobs sequentially — one process,
one Botasaurus driver at a time, so there is no Chrome-profile contention.
"""

import argparse
import logging
import sys
import time

from app.worker import dispatch

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("worker.cli")


def cmd_poll(args) -> int:
    log.info("worker poller started (interval %ds)", args.interval)
    while True:
        job, params = dispatch.claim_next_job()
        if not job:
            time.sleep(args.interval)
            continue
        log.info("job %d (%s): %s", job.id, job.type, params)
        status = dispatch.run_job(job, params)
        log.info("job %d finished: %s", job.id, status)
        if status == "blocked":
            log.error("blocked — poller stopping; cool down before restart.")
            return 2
    return 0


def cmd_enrich(args) -> int:
    from app.worker.enrich import run_enrich

    result = run_enrich(max_n=args.max)
    log.info("enrich result: %s", result)
    return 0


def cmd_score(args) -> int:
    from app.worker.score import run_score

    result = run_score(max_n=args.max, explain=args.explain)
    log.info("score result: %s", result)
    return 0


def cmd_smoke_test(args) -> int:
    # delegate to the scraper's selector smoke test
    from app.scraper.__main__ import cmd_smoke_test as scraper_smoke

    return scraper_smoke(args)


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.worker")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_poll = sub.add_parser("poll", help="process pending jobs (any type)")
    p_poll.add_argument("--interval", type=int, default=10)
    p_poll.set_defaults(fn=cmd_poll)

    p_enrich = sub.add_parser("enrich", help="run enrichment now (no job row)")
    p_enrich.add_argument("--max", type=int, default=50)
    p_enrich.set_defaults(fn=cmd_enrich)

    p_score = sub.add_parser("score", help="run scoring now (no job row)")
    p_score.add_argument("--max", type=int, default=100)
    p_score.add_argument("--explain", action="store_true", help="also request LLM summary")
    p_score.set_defaults(fn=cmd_score)

    p_smoke = sub.add_parser("smoke-test", help="verify scraper selectors")
    p_smoke.set_defaults(fn=cmd_smoke_test)

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
