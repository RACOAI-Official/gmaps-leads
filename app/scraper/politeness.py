"""Politeness enforcement — see SOUL.md. Limits come from config, never constants."""

import logging
import random
import time
from datetime import datetime, time as dtime, timezone

from sqlalchemy import func, select

from app.config import settings
from app.db.models import Business
from app.db.session import SessionLocal

log = logging.getLogger(__name__)


class BlockedError(Exception):
    """Raised when Google shows a CAPTCHA/interstitial. Abort — never retry through."""


class DailyCapReached(Exception):
    pass


def polite_delay() -> None:
    delay = random.uniform(settings.scrape_delay_min_s, settings.scrape_delay_max_s)
    time.sleep(delay)


def scraped_today() -> int:
    start_of_day = datetime.combine(
        datetime.now(timezone.utc).date(), dtime.min, tzinfo=timezone.utc
    )
    with SessionLocal() as session:
        return session.scalar(
            select(func.count(Business.id)).where(Business.scraped_at >= start_of_day)
        )


def check_daily_cap() -> None:
    count = scraped_today()
    if count >= settings.scrape_daily_cap:
        raise DailyCapReached(
            f"daily cap reached: {count}/{settings.scrape_daily_cap} places today"
        )


def check_blocked(current_url: str, page_text: str) -> None:
    from app.scraper import selectors

    url = (current_url or "").lower()
    text = (page_text or "").lower()
    if any(frag in url for frag in selectors.BLOCK_URL_FRAGMENTS) or any(
        marker in text for marker in selectors.BLOCK_TEXT_MARKERS
    ):
        raise BlockedError(
            f"block/interstitial detected at {current_url}; "
            f"cool down {settings.scrape_cooldown_hours}h before rerunning"
        )
