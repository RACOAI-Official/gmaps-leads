"""Settings API: runtime config, queue health, scrape-knob edits, LLM test,
and data-management actions (retry failed jobs, re-score everything)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import get_runtime_config, settings, update_runtime_config
from app.db.models import Business, Enrichment, Job, Score
from app.scoring import llm

router = APIRouter()


def _mask(s: str) -> str:
    if not s:
        return ""
    if len(s) <= 4:
        return "••••"
    return "•" * (len(s) - 4) + s[-4:]


def _mask_db_url(url: str) -> str:
    # hide the password in a postgres URL
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        if ":" in rest.split("@", 1)[0]:
            creds, host = rest.split("@", 1)
            user = creds.split(":", 1)[0]
            return f"{scheme}://{user}:••••@{host}"
    return url


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    cfg = get_runtime_config()
    # live counts
    counts = {
        "leads": db.scalar(select(func.count(Business.id))) or 0,
        "with_website": db.scalar(
            select(func.count(Business.id)).where(Business.website.is_not(None))
        ) or 0,
        "enrichments": db.scalar(select(func.count(Enrichment.id))) or 0,
        "scores": db.scalar(select(func.count(Score.id))) or 0,
        "scores_with_llm": db.scalar(
            select(func.count(Score.id)).where(Score.llm_summary.is_not(None))
        ) or 0,
    }
    return {
        "database_url": _mask_db_url(settings.database_url),
        "llm": {
            "format": (settings.llm_api_format or "anthropic"),
            "base_url": settings.llm_base_url,
            "model": settings.llm_model,
            "api_key_present": bool(settings.llm_api_key),
            "api_key_masked": _mask(settings.llm_api_key),
            "configured": llm.is_configured(),
        },
        "scrape": {
            "delay_min_s": cfg["scrape_delay_min_s"],
            "delay_max_s": cfg["scrape_delay_max_s"],
            "daily_cap": cfg["scrape_daily_cap"],
            "cooldown_hours": settings.scrape_cooldown_hours,
            "headless": settings.scrape_headless,  # env-only (read-only)
            "editable": ["delay_min_s", "delay_max_s", "daily_cap"],
        },
        "counts": counts,
    }


@router.get("/settings/queue")
def queue_health(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Job.type, Job.status, func.count(Job.id))
        .group_by(Job.type, Job.status)
        .order_by(Job.type, Job.status)
    ).all()
    breakdown: dict[str, dict[str, int]] = {}
    for jtype, jstatus, cnt in rows:
        breakdown.setdefault(jtype, {})[jstatus] = cnt
    return {"breakdown": breakdown}


class ScrapeKnobs(BaseModel):
    delay_min_s: float | None = Field(default=None, ge=0, le=120)
    delay_max_s: float | None = Field(default=None, ge=0, le=120)
    daily_cap: int | None = Field(default=None, ge=0, le=10000)


@router.patch("/settings/scrape")
def patch_scrape_knobs(body: ScrapeKnobs, db: Session = Depends(get_db)):  # noqa: ARG001
    new = update_runtime_config(
        scrape_delay_min_s=body.delay_min_s,
        scrape_delay_max_s=body.delay_max_s,
        scrape_daily_cap=body.daily_cap,
    )
    return {"ok": True, "scrape": new}


class LLMTestBody(BaseModel):
    prompt: str = "Reply with the single word OK."


@router.post("/settings/llm-test")
def llm_test(body: LLMTestBody, db: Session = Depends(get_db)):  # noqa: ARG001
    return llm.ping(body.prompt)


@router.post("/settings/retry-failed")
def retry_failed(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Job).where(Job.status.in_(["failed", "blocked"]))
    ).all()
    n = 0
    for job in rows:
        job.status = "pending"
        job.error = None
        job.started_at = None
        job.finished_at = None
        n += 1
    db.commit()
    return {"ok": True, "requeued": n}


@router.post("/settings/rescore-all")
def rescore_all(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Business.id))) or 0
    job = Job(type="score", params={"max": min(int(total), 2000), "explain": True})
    db.add(job)
    db.commit()
    return {"ok": True, "job_id": job.id, "total_businesses": total}
