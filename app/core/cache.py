import hashlib
import json
from typing import Optional, Dict, Any

from app.config import settings
from app.services.redis_client import get_redis_client


def _normalize(query: str) -> str:
    return " ".join(query.lower().strip().split())


def _cache_key(query: str) -> str:
    normalized = _normalize(query)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"faq_cache:{digest}"


def get_cached_response(query: str) -> Optional[Dict[str, Any]]:
    client = get_redis_client()
    if client is None:
        return None
    raw = client.get(_cache_key(query))
    if raw is None:
        return None
    return json.loads(raw)


def set_cached_response(query: str, response: Dict[str, Any]) -> None:
    client = get_redis_client()
    if client is None:
        return
    client.setex(
        _cache_key(query),
        settings.cache_ttl_seconds,
        json.dumps(response),
    )
