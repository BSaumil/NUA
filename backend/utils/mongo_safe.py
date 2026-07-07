"""
Mongo-safe reading utilities.

Legacy documents in the NUA POS database occasionally violate current
Pydantic schemas (invalid emails, string-based dict fields, missing required
keys). A single bad row must never 500 the whole list endpoint.

`safe_parse_list(cursor_or_docs, Model, ...)` centralises the try/except
pattern so route files stop growing bespoke defenders.
"""
from typing import Iterable, List, Type, TypeVar, Callable, Optional, Any
import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)

M = TypeVar("M", bound=BaseModel)


def safe_parse_list(
    docs: Iterable[dict],
    model: Type[M],
    *,
    coerce: Optional[Callable[[dict], dict]] = None,
    fallback: Optional[Callable[[dict, Exception], Optional[M]]] = None,
    where: str = "",
) -> List[dict]:
    """Parse an iterable of Mongo docs into `model` — dropping/repairing any
    that fail validation instead of raising.

    Args:
        docs: raw Mongo documents.
        model: pydantic Model to parse each doc into.
        coerce: optional (doc → doc) fixer applied BEFORE validation. Use for
                legacy field renames or type coercion (e.g. `timings` → `hours`).
        fallback: optional (doc, error) → Model|None hook. Called when
                  validation still fails; return a model instance to keep the
                  row, or `None` to drop it.
        where: free-text tag for warning logs (e.g. "locations", "customers").

    Returns:
        List of `.dict()`-serialised model instances. Never raises for a bad row.
    """
    out: List[dict] = []
    for doc in docs:
        # Strip Mongo's internal id — never JSON-serialisable and never useful downstream.
        try:
            doc.pop("_id", None)
        except Exception:
            pass
        try:
            if coerce is not None:
                doc = coerce(doc)
            out.append(model(**doc).dict())
        except Exception as e:
            logger.warning(f"[mongo_safe] skip malformed {where or model.__name__} id={doc.get('id')!r}: {e}")
            if fallback is not None:
                try:
                    repaired = fallback(doc, e)
                    if repaired is not None:
                        out.append(repaired.dict() if isinstance(repaired, BaseModel) else repaired)
                except Exception as ee:
                    logger.warning(f"[mongo_safe] fallback also failed for {where}: {ee}")
    return out


async def safe_find_list(
    collection: Any,
    model: Type[M],
    query: Optional[dict] = None,
    *,
    limit: int = 1000,
    sort: Optional[list] = None,
    coerce: Optional[Callable[[dict], dict]] = None,
    fallback: Optional[Callable[[dict, Exception], Optional[M]]] = None,
    where: str = "",
) -> List[dict]:
    """Thin wrapper: `collection.find(query).sort(...).to_list(limit)` + safe parse."""
    cursor = collection.find(query or {})
    if sort:
        cursor = cursor.sort(sort)
    docs = await cursor.to_list(limit)
    return safe_parse_list(docs, model, coerce=coerce, fallback=fallback, where=where or collection.name)
