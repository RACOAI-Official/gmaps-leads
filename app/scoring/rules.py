"""Deterministic lead-quality scorer.

Produces a 0–100 score from objective business signals plus enrichment data.
The rules engine is the source of truth for the score; the LLM only narrates it
(see ``app.scoring.llm``). Factors are intentionally simple, explainable, and
additive so a sales rep can see *why* a lead ranks where it does.

Usage::

    factors, score = score_business(business_dict, enrichment_dict)
"""

from __future__ import annotations

import math


def _sigmoid(x: float) -> float:
    if x < 0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def score_business(business: dict, enrichment: dict | None = None) -> tuple[list[dict], int]:
    """Score a single business.

    Args:
        business: a dict with the Business fields (name, phone, website,
            rating, reviews_count, categories, city, ...).
        enrichment: optional dict with keys emails (list), socials (dict),
            tech_stack (list) — improves the score when enrichment exists.

    Returns:
        (factors, score) where factors is a list ordered by contribution desc,
        each ``{name, weight, raw, contribution}``, and score is an int 0–100.
    """
    enrichment = enrichment or {}
    emails = enrichment.get("emails") or []
    socials = enrichment.get("socials") or {}
    tech = enrichment.get("tech_stack") or []

    rating = business.get("rating")
    reviews = business.get("reviews_count") or 0
    has_website = bool(business.get("website"))
    has_phone = bool(business.get("phone"))
    has_email = bool(emails)
    has_social = bool(socials)

    factors = []

    def add(name: str, weight: int, raw: float, norm: float) -> None:
        norm = max(0.0, min(1.0, norm))
        factors.append(
            {
                "name": name,
                "weight": weight,
                "raw": round(raw, 3) if isinstance(raw, float) else raw,
                "contribution": round(weight * norm),
            }
        )

    # 1. Rating — stars in [1,5]; sigmoid centred on 4.0 so 4★ already scores well.
    if rating is not None:
        add("rating", 30, float(rating), _sigmoid((rating - 3.8) * 1.6))
    else:
        add("rating", 30, None, 0.0)

    # 2. Review volume — log-scaled, ~plateaus past a few hundred reviews.
    add("reviews", 20, reviews, _sigmoid((math.log10(reviews + 1) - 1.5) * 1.8))

    # 3. Online presence (website + phone) — core contactability.
    add("has_website", 20, has_website, 1.0 if has_website else 0.0)
    add("has_phone", 15, has_phone, 1.0 if has_phone else 0.0)

    # 4. Enrichment depth — direct contact + social proof.
    add("has_email", 10, has_email, 1.0 if has_email else 0.0)
    add("has_socials", 5, has_social, 1.0 if has_social else 0.0)

    score = min(100, sum(f["contribution"] for f in factors))
    factors.sort(key=lambda f: f["contribution"], reverse=True)
    return factors, score


def summarize_for_llm(business: dict, factors: list[dict], score: int) -> str:
    """Build the prompt payload describing a lead, for the LLM explainer."""
    lines = [
        f"Business: {business.get('name', 'unknown')}",
        f"Category: {business.get('main_category') or 'unknown'}",
        f"City: {business.get('city') or 'unknown'}",
        f"Rating: {business.get('rating')} ({business.get('reviews_count') or 0} reviews)",
        f"Website: {'yes' if business.get('website') else 'no'}",
        f"Phone: {'yes' if business.get('phone') else 'no'}",
        f"Score: {score}/100",
        "Top factors:",
    ]
    for f in factors[:4]:
        lines.append(f"  - {f['name']}: {f['contribution']}/{f['weight']}")
    return "\n".join(lines)
