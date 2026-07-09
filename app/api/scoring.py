"""Scoring API: browse ranked leads + queue score jobs (optionally LLM-explained)."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Business, Job, Score

router = APIRouter()


def _serialize(b: Business, s: Score | None) -> dict:
    return {
        "id": b.id,
        "name": b.name,
        "main_category": b.main_category,
        "city": b.city,
        "rating": b.rating,
        "reviews_count": b.reviews_count,
        "website": b.website,
        "score": s.score if s else None,
        "factors": s.factors if s else None,
        "llm_summary": s.llm_summary if s else None,
        "has_llm": bool(s and s.llm_summary),
        "scored_at": s.scored_at.isoformat() if (s and s.scored_at) else None,
    }


@router.get("/scores")
def list_scores(
    db: Session = Depends(get_db),
    search: str | None = None,
    city: str | None = None,
    min_score: int | None = Query(default=None, ge=0, le=100),
    has_llm: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    q = (
        select(Business, Score)
        .join(Score, Score.business_id == Business.id)
    )
    if search:
        pattern = f"%{search}%"
        q = q.where(or_(Business.name.ilike(pattern), Business.main_category.ilike(pattern)))
    if city:
        q = q.where(Business.city.ilike(city))
    if min_score is not None:
        q = q.where(Score.score >= min_score)
    if has_llm is True:
        q = q.where(Score.llm_summary.is_not(None))
    elif has_llm is False:
        q = q.where(Score.llm_summary.is_(None))

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.execute(
        q.order_by(Score.score.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [_serialize(b, s) for b, s in rows]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


class ScoreJobCreate(BaseModel):
    business_ids: list[int] | None = Field(default=None, max_length=500)
    filter: dict | None = None  # subset of LeadFilters
    max: int = Field(default=100, ge=1, le=2000)
    explain: bool = False  # request an LLM summary per lead


@router.post("/jobs/score", status_code=201)
def create_score_job(body: ScoreJobCreate, db: Session = Depends(get_db)):
    params: dict = {"max": body.max, "explain": body.explain}
    if body.business_ids:
        params["business_ids"] = body.business_ids
    elif body.filter:
        params["filter"] = body.filter
    job = Job(type="score", params=params)
    db.add(job)
    db.commit()
    return {
        "id": job.id,
        "type": job.type,
        "params": job.params,
        "status": job.status,
    }
