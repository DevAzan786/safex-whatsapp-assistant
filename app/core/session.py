import json
from app.services.redis_client import get_redis_client

# Thread-safe in-memory fallback for local environments
_in_memory_sessions = {}

def get_session(sender: str) -> dict:
    """
    Retrieve session for a given sender.
    Returns a dict with format: {"state": "idle", "data": {}, "lang": "en"}
    """
    redis_client = get_redis_client()
    if redis_client:
        try:
            val = redis_client.get(f"session:{sender}")
            if val:
                return json.loads(val)
        except Exception:
            pass  # Fallback to local memory on Redis errors
            
    # Default structure
    return _in_memory_sessions.get(
        sender, 
        {"state": "idle", "data": {}, "lang": "en"}
    )

def set_session(sender: str, state: str, data: dict = None, lang: str = None):
    """
    Update session state, data, and language for a given sender.
    """
    session = get_session(sender)
    session["state"] = state
    if data is not None:
        session["data"] = data
    if lang is not None:
        session["lang"] = lang
        
    redis_client = get_redis_client()
    if redis_client:
        try:
            redis_client.set(f"session:{sender}", json.dumps(session), ex=86400)  # 24-hour TTL
            return
        except Exception:
            pass
            
    _in_memory_sessions[sender] = session

def clear_session(sender: str):
    """
    Clear/reset session state for a given sender.
    """
    redis_client = get_redis_client()
    if redis_client:
        try:
            redis_client.delete(f"session:{sender}")
        except Exception:
            pass
            
    if sender in _in_memory_sessions:
        del _in_memory_sessions[sender]
