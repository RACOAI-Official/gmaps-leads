"""Scoring worker — runs the rules engine over businesses and optionally asks
the LLM to narrate the result.

For each business it: loads any existing enrichment, computes the deterministic
score (``app.scoring.rules``), and when ``explain=True`` asks the LLM for a short
natural-language summary stored in ``scores.llm_summary``. Results upsert into
the ``scores`` table (1:1 per business).
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import Business, Enrichment, Score
from app.db.session import SessionLocal
from app.scoring import llm, rules

log = logging.getLogger(__name__)

_EXPLAIN_SYSTEM = (
    "You are a concise B2B lead-scoring analyst. Given a scored business lead, "
    "write 2-3 short sentences explaining the main strengths and weaknesses of "
    "this lead for an outbound sales team. Be specific and concrete. No fluff, "
    "no preamble, no markdown headings."
)


def _load_targets(business_ids: list[int] | None, max_n: int, session: Session) -> list[Business]:
    q = select(Business)
    if business_ids:
        q = q.where(Business.id.in_(business_ids))
    q = q.order_by(Business.id).limit(max_n)
    return list(session.scalars(q))


def _enrichment_for(business_id: int, session: Session) -> dict | None:
    e = session.scalar(select(Enrichment).where(Enrichment.business_id == business_id))
    if not e:
        return None
    return {
        "emails": e.emails,
        "socials": e.socials,
        "tech_stack": e.tech_stack,
    }


def _business_dict(b: Business) -> dict:
    return {
        "name": b.name,
        "main_category": b.main_category,
        "city": b.city,
        "rating": b.rating,
        "reviews_count": b.reviews_count,
        "website": b.website,
        "phone": b.phone,
    }


def _upsert_score(business_id: int, score: int, factors: list[dict], llm_summary: str | None) -> None:
    row = {
        "business_id": business_id,
        "score": score,
        "factors": factors,
        "llm_summary": llm_summary,
    }
    stmt = insert(Score).values(**row)
    update_cols = {k: stmt.excluded[k] for k in row if k != "business_id"}
    stmt = stmt.on_conflict_do_update(
        index_elements=[Score.business_id], set_=update_cols
    )
    with SessionLocal() as session:
        session.execute(stmt)
        session.commit()


def run_score(
    business_ids: list[int] | None = None,
    max_n: int = 100,
    explain: bool = False,
) -> dict:
    """Score up to ``max_n`` businesses. When ``explain``, request an LLM summary."""
    with SessionLocal() as session:
        targets = _load_targets(business_ids, max_n, session)

    if not targets:
        log.info("score: no targets")
        return {"scored": 0, "explained": 0}

    explained = 0
    llm_ready = explain and llm.is_configured()
    for b in targets:
        with SessionLocal() as session:
            bdict = _business_dict(b)
            enrichment = _enrichment_for(b.id, session)
        factors, score = rules.score_business(bdict, enrichment)
        summary: str | None = None
        if llm_ready:
            prompt = rules.summarize_for_llm(bdict, factors, score)
            summary = llm.complete(prompt, system=_EXPLAIN_SYSTEM, max_tokens=220)
            if summary:
                explained += 1
        _upsert_score(b.id, score, factors, summary)
        log.info("scored [%d] %s = %d%s", b.id, b.name, score, " (explained)" if summary else "")
    return {"scored": len(targets), "explained": explained}
