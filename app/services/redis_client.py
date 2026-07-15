import redis
from app.config import settings

_client = None


def get_redis_client():
    global _client
    if _client is None:
        if not settings.redis_url:
            return None
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client
