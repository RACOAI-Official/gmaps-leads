"""DB writes for the scraper: place_key derivation + idempotent upsert."""

import hashlib
import re

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.models import Business
from app.db.session import SessionLocal

# Maps place URLs embed a stable data id like !1s0x3755b8...:0xabc...
_DATA_ID_RE = re.compile(r"0x[0-9a-f]+:0x[0-9a-f]+")


def derive_place_key(url: str | None, name: str | None, address: str | None) -> str:
    if url:
        m = _DATA_ID_RE.search(url)
        if m:
            return m.group(0)
    digest = hashlib.sha1(f"{name}|{address}".encode()).hexdigest()
    return f"sha1:{digest}"


def existing_place_keys() -> set[str]:
    with SessionLocal() as session:
        return set(session.scalars(select(Business.place_key)))


def upsert_business(record: dict) -> None:
    stmt = insert(Business).values(**record)
    update_cols = {
        k: stmt.excluded[k] for k in record if k not in ("place_key",)
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=[Business.place_key], set_=update_cols
    )
    with SessionLocal() as session:
        session.execute(stmt)
        session.commit()
