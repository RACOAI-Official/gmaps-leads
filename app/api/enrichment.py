"""Enrichment API: browse enriched businesses + queue enrich jobs."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Business, Enrichment, Job

router = APIRouter()


def _serialize(b: Business, e: Enrichment | None) -> dict:
    return {
        "id": b.id,
        "name": b.name,
        "website": b.website,
        "city": b.city,
        "main_category": b.main_category,
        "status": e.status if e else None,
        "emails": e.emails if e else None,
        "socials": e.socials if e else None,
        "tech_stack": e.tech_stack if e else None,
        "crawled_at": e.crawled_at.isoformat() if (e and e.crawled_at) else None,
    }


@router.get("/enrichments")
def list_enrichments(
    db: Session = Depends(get_db),
    search: str | None = None,
    city: str | None = None,
    category: str | None = None,
    status: str | None = None,
    min_emails: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    q = (
        select(Business, Enrichment)
        .outerjoin(Enrichment, Enrichment.business_id == Business.id)
        .where(Business.website.is_not(None))
    )
    if search:
        pattern = f"%{search}%"
        q = q.where(or_(Business.name.ilike(pattern), Business.website.ilike(pattern)))
    if city:
        q = q.where(Business.city.ilike(city))
    if category:
        q = q.where(Business.main_category.ilike(f"%{category}%"))
    if status:
        q = q.where(Enrichment.status == status)
    if min_emails is not None:
        # JSONB array length >= min_emails
        q = q.where(func.jsonb_array_length(Enrichment.emails) >= min_emails)

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.execute(
        q.order_by(Business.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [_serialize(b, e) for b, e in rows]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


class EnrichJobCreate(BaseModel):
    business_ids: list[int] | None = Field(default=None, max_length=500)
    filter: dict | None = None  # subset of LeadFilters
    max: int = Field(default=50, ge=1, le=500)


@router.post("/jobs/enrich", status_code=201)
def create_enrich_job(body: EnrichJobCreate, db: Session = Depends(get_db)):
    params: dict = {"max": body.max}
    if body.business_ids:
        params["business_ids"] = body.business_ids
    elif body.filter:
        params["filter"] = body.filter
    job = Job(type="enrich", params=params)
    db.add(job)
    db.commit()
    return {
        "id": job.id,
        "type": job.type,
        "params": job.params,
        "status": job.status,
    }
