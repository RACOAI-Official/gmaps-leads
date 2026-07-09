import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Business

router = APIRouter()

SORTABLE = {"name", "rating", "reviews_count", "scraped_at", "city", "main_category"}

CSV_COLUMNS = [
    "id", "name", "main_category", "address", "city", "phone",
    "website", "rating", "reviews_count", "source_query", "scraped_at",
]


def _filtered_query(
    city: str | None,
    category: str | None,
    has_website: bool | None,
    has_phone: bool | None,
    min_rating: float | None,
    search: str | None,
    source_query: str | None = None,
) -> Select:
    q = select(Business)
    if source_query:
        q = q.where(Business.source_query.ilike(source_query))
    if city:
        q = q.where(Business.city.ilike(city))
    if category:
        q = q.where(Business.main_category.ilike(f"%{category}%"))
    if has_website is not None:
        q = q.where(
            Business.website.is_not(None) if has_website else Business.website.is_(None)
        )
    if has_phone is not None:
        q = q.where(
            Business.phone.is_not(None) if has_phone else Business.phone.is_(None)
        )
    if min_rating is not None:
        q = q.where(Business.rating >= min_rating)
    if search:
        pattern = f"%{search}%"
        q = q.where(
            or_(Business.name.ilike(pattern), Business.address.ilike(pattern))
        )
    return q


def _serialize(b: Business) -> dict:
    return {
        "id": b.id,
        "place_key": b.place_key,
        "name": b.name,
        "main_category": b.main_category,
        "categories": b.categories,
        "address": b.address,
        "city": b.city,
        "phone": b.phone,
        "website": b.website,
        "rating": b.rating,
        "reviews_count": b.reviews_count,
        "socials": b.socials,
        "source_query": b.source_query,
        "scraped_at": b.scraped_at.isoformat() if b.scraped_at else None,
    }


@router.get("/leads")
def list_leads(
    db: Session = Depends(get_db),
    city: str | None = None,
    category: str | None = None,
    has_website: bool | None = None,
    has_phone: bool | None = None,
    min_rating: float | None = None,
    search: str | None = None,
    sort: str = "scraped_at",
    order: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    q = _filtered_query(city, category, has_website, has_phone, min_rating, search)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    if sort not in SORTABLE:
        sort = "scraped_at"
    col = getattr(Business, sort)
    q = q.order_by(col.desc().nulls_last() if order == "desc" else col.asc().nulls_last())
    rows = db.scalars(q.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize(b) for b in rows],
    }


@router.get("/leads/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    b = db.get(Business, lead_id)
    if not b:
        raise HTTPException(404, "lead not found")
    return _serialize(b)


@router.get("/export.csv")
def export_csv(
    db: Session = Depends(get_db),
    city: str | None = None,
    category: str | None = None,
    has_website: bool | None = None,
    has_phone: bool | None = None,
    min_rating: float | None = None,
    search: str | None = None,
):
    q = _filtered_query(city, category, has_website, has_phone, min_rating, search)
    q = q.order_by(Business.name.asc())

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(CSV_COLUMNS)
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)
        for b in db.scalars(q).yield_per(200):
            writer.writerow(
                [
                    b.id, b.name, b.main_category, b.address, b.city, b.phone,
                    b.website, b.rating, b.reviews_count, b.source_query,
                    b.scraped_at.isoformat() if b.scraped_at else "",
                ]
            )
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )
