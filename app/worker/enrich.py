"""Website enrichment — browser-only crawl of business websites.

For each business with a website, open the page in a Botasaurus browser and
extract contact + tech signals:
  * emails (from mailto: links and visible text regex)
  * socials (facebook / instagram / linkedin / x / tiktok / youtube handles)
  * tech_stack (heuristic: WordPress, Shopify, Wix, Squarespace, React/Next/Vue)

Sites are crawled inside a single browser session for efficiency. Results are
upserted into the ``enrichments`` table (1:1 per business). A business with no
website is skipped (no enrichment row). Statuses: ok | empty | failed.

This module deliberately reuses Botasaurus (already a dependency) rather than
spawning a second Chrome profile, and it is invoked from the unified worker
dispatcher (``app.worker``), never run as a standalone process.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.models import Business, Enrichment
from app.db.session import SessionLocal

log = logging.getLogger(__name__)

# --- Extraction heuristics -------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_SOCIAL_HOSTS = {
    "facebook.com": "facebook",
    "fb.com": "facebook",
    "instagram.com": "instagram",
    "linkedin.com": "linkedin",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "tiktok.com": "tiktok",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
}

# tech signature: (name, predicate on html-lowercased or set of script srcs)
def _detect_tech(html: str) -> list[str]:
    h = html.lower()
    found: list[str] = []
    if "/wp-content/" in h or 'name="generator" content="wordpress' in h:
        found.append("wordpress")
    if "cdn.shopify.com" in h or "shopify.theme" in h or "myshopify.com" in h:
        found.append("shopify")
    if "static.parastorage.com" in h or "wix.com" in h or "wixstatic" in h:
        found.append("wix")
    if "squarespace" in h:
        found.append("squarespace")
    if "squarespace" not in h and "_next/static" in h or "__next" in h:
        found.append("next.js")
    if "_build/" in h and "phoenix" in h:
        pass
    if "react" in h and ("data-reactroot" in h or "react-dom" in h):
        found.append("react")
    if "vue." in h or 'data-v-' in h:
        found.append("vue")
    # de-dup, preserve order
    seen: set[str] = set()
    out: list[str] = []
    for t in found:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _extract_emails(html: str, mailto_hrefs: list[str]) -> list[str]:
    emails: list[str] = set()
    for href in mailto_hrefs:
        m = _EMAIL_RE.search(href)
        if m:
            emails.add(m.group(0).lower())
    for m in _EMAIL_RE.finditer(html):
        addr = m.group(0).lower()
        # filter obvious image-file false positives
        if not addr.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            emails.add(addr)
    # drop generic role-mailbox noise we don't want ranked
    return sorted(emails)


def _extract_socials(html: str, links: list[str]) -> dict[str, str]:
    socials: dict[str, str] = {}
    combined = [urlparse(l).netloc.lower().lstrip("www.") for l in links]
    combined += [urlparse(a).netloc.lower().lstrip("www.") for a in re.findall(r'href=["\']([^"\']+)["\']', html)]
    for host in combined:
        for key, name in _SOCIAL_HOSTS.items():
            if host.endswith(key) and name not in socials:
                # store the first matching link we saw for that platform
                socials[name] = f"https://{host}"
    return socials


# --- Browser task ----------------------------------------------------------

def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _crawl_one(driver, business: dict) -> dict:
    """Crawl a single business site in the given driver session.

    Returns a result dict: {status, emails, socials, tech_stack}.
    Never raises — failures are recorded as status="failed".
    """
    url = _normalize_url(business.get("website") or "")
    try:
        driver.get(url, timeout=25)
        driver.sleep(2)
        html = driver.page_html or ""
        # collect <a> hrefs + mailto links
        link_hrefs: list[str] = []
        mailto: list[str] = []
        for el in driver.select_all("a", wait=None) or []:
            try:
                href = el.get_attribute("href") or ""
            except Exception:
                href = ""
            if href:
                link_hrefs.append(href)
                if href.lower().startswith("mailto:"):
                    mailto.append(href)
        emails = _extract_emails(html, mailto)
        socials = _extract_socials(html, link_hrefs)
        tech = _detect_tech(html)
        has_anything = bool(emails or socials or tech)
        return {
            "status": "ok" if has_anything else "empty",
            "emails": emails,
            "socials": socials,
            "tech_stack": tech,
        }
    except Exception as e:  # noqa: BLE001 — record, don't crash the batch
        log.warning("enrich failed for business %s (%s): %s", business.get("id"), url, e)
        return {"status": "failed", "emails": [], "socials": {}, "tech_stack": []}


def _upsert_enrichment(business_id: int, result: dict) -> None:
    row = {
        "business_id": business_id,
        "emails": result.get("emails") or None,
        "socials": result.get("socials") or None,
        "tech_stack": result.get("tech_stack") or None,
        "status": result.get("status", "ok"),
    }
    stmt = insert(Enrichment).values(**row)
    update_cols = {k: stmt.excluded[k] for k in row if k != "business_id"}
    stmt = stmt.on_conflict_do_update(
        index_elements=[Enrichment.business_id], set_=update_cols
    )
    with SessionLocal() as session:
        session.execute(stmt)
        session.commit()


def _load_targets(business_ids: list[int] | None, max_n: int) -> list[Business]:
    with SessionLocal() as session:
        q = select(Business).where(Business.website.is_not(None))
        if business_ids:
            q = q.where(Business.id.in_(business_ids))
        # skip businesses already enriched unless an explicit id list was given
        if not business_ids:
            q = q.outerjoin(Enrichment, Enrichment.business_id == Business.id).where(
                Enrichment.id.is_(None)
            )
        q = q.order_by(Business.id).limit(max_n)
        return list(session.scalars(q))


def run_enrich(business_ids: list[int] | None = None, max_n: int = 50) -> dict:
    """Enrich up to ``max_n`` businesses (optionally a fixed id set).

    Uses one Botasaurus browser session for the whole batch. Imported lazily so
    importing the worker package never pays the browser/Chrome cost.
    """
    from app.config import settings
    from botasaurus.browser import Driver, browser

    targets = _load_targets(business_ids, max_n)
    if not targets:
        log.info("enrich: no targets (all enriched or none with websites)")
        return {"enriched": 0, "skipped": 0}

    @browser(
        headless=settings.scrape_headless,
        block_images=True,
        block_images_and_css=False,  # need CSS/scripts for tech detection
        reuse_driver=True,
        output=None,
        close_on_crash=True,
    )
    def _enrich_batch(driver: Driver, data: dict):
        businesses: list[dict] = data["businesses"]
        results: list[tuple[int, dict]] = []
        for b in businesses:
            bdict = {
                "id": b.id,
                "name": b.name,
                "website": b.website,
            }
            res = _crawl_one(driver, bdict)
            results.append((b.id, res))
        return results

    log.info("enrich: crawling %d sites", len(targets))
    results = _enrich_batch({"businesses": targets})

    ok = empty = failed = 0
    for bid, res in results:
        _upsert_enrichment(bid, res)
        if res["status"] == "ok":
            ok += 1
        elif res["status"] == "empty":
            empty += 1
        else:
            failed += 1
    log.info("enrich done: ok=%d empty=%d failed=%d", ok, empty, failed)
    return {"enriched": ok, "empty": empty, "failed": failed}
