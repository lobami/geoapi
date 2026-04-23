"""
Reference place resolution.

Place data lives in the `reference_places` table. On app startup, warm_cache()
is called once to pull all rows into memory. The heuristic parser uses these
in-memory dicts to avoid a DB round-trip on every /ask request.

Spatial queries (nearest_to_place, farthest_from_place) retrieve the authoritative
lat/lon from the DB via get_reference_place(), so cache and DB stay in sync.
"""

import unicodedata
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.intervention import ReferencePlace


# Module-level cache — populated at startup via warm_cache()
_places: dict[str, dict] = {}  # key → {name, lat, lon, type}
_aliases: dict[str, str] = {}  # alias string → canonical key


def warm_cache(db: Session) -> None:
    global _places, _aliases
    rows = db.execute(select(ReferencePlace)).scalars().all()
    _places = {row.key: {"name": row.name, "lat": row.lat, "lon": row.lon, "type": row.type} for row in rows}
    _aliases = {}
    for row in rows:
        for alias in (row.aliases or []):
            _aliases[alias] = row.key


def get_reference_place(key: str, db: Session) -> dict | None:
    row = db.get(ReferencePlace, key)
    if not row:
        return None
    return {"key": row.key, "name": row.name, "lat": row.lat, "lon": row.lon, "type": row.type}


def list_reference_places(db: Session) -> list[dict]:
    rows = db.execute(select(ReferencePlace).order_by(ReferencePlace.name)).scalars().all()
    seen: set[str] = set()
    result = []
    for row in rows:
        if row.name in seen:
            continue
        seen.add(row.name)
        result.append({"key": row.key, "name": row.name, "lat": row.lat, "lon": row.lon, "type": row.type})
    return result


def normalize_place(value: str | None) -> str | None:
    if not value:
        return None
    normalized = _strip_accents(value).lower().strip().replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    key = _aliases.get(normalized, normalized.replace(" ", "_"))
    return key if key in _places else None


def find_place_in_text(text: str) -> str | None:
    normalized_text = _strip_accents(text).lower().replace("_", " ")

    for alias, key in _aliases.items():
        if alias in normalized_text:
            return key

    for key, place in _places.items():
        candidates = {key.replace("_", " "), place["name"].lower()}
        if any(candidate in normalized_text for candidate in candidates):
            return key

    return None


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))
