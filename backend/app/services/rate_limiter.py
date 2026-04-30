"""
In-Memory Rate Limiter for Agent API.

Tracks requests per key per minute using a rolling window counter.
For distributed systems, replace with Redis-based implementation.
"""
import time
import threading
from collections import defaultdict
from typing import Dict, List

# In-memory store: key_id -> list of request timestamps
_request_tracker: Dict[str, List[float]] = defaultdict(list)
_lock = threading.Lock()

# Cleanup interval: remove old entries every 60 seconds
_last_cleanup = time.time()
_cleanup_interval = 60


def check_rate_limit(key_id: str, limit_per_minute: int = 1000) -> bool:
    """
    Check if a request is within rate limit (requests per minute).
    
    Args:
        key_id: Unique identifier for the API key
        limit_per_minute: Maximum requests allowed per minute
        
    Returns:
        True if within limit, False if exceeded
    """
    global _last_cleanup
    
    current_time = time.time()
    cutoff_time = current_time - 60  # 1 minute window
    
    with _lock:
        # Cleanup old entries periodically
        if current_time - _last_cleanup > _cleanup_interval:
            _cleanup_old_entries(cutoff_time)
            _last_cleanup = current_time
        
        # Get timestamps for this key
        timestamps = _request_tracker[key_id]
        
        # Remove old entries outside the 1-minute window
        timestamps[:] = [ts for ts in timestamps if ts > cutoff_time]
        
        # Check if within limit
        if len(timestamps) >= limit_per_minute:
            return False
        
        # Add current request
        timestamps.append(current_time)
        return True


def get_remaining_requests(key_id: str, limit_per_minute: int = 1000) -> int:
    """
    Get the number of remaining requests for an API key.
    
    Args:
        key_id: Unique identifier for the API key
        limit_per_minute: Maximum requests allowed per minute
        
    Returns:
        Number of remaining requests (0 if none)
    """
    current_time = time.time()
    cutoff_time = current_time - 60
    
    with _lock:
        timestamps = _request_tracker.get(key_id, [])
        # Count requests within the 1-minute window
        recent_requests = len([ts for ts in timestamps if ts > cutoff_time])
        remaining = max(0, limit_per_minute - recent_requests)
        return remaining


def reset_key(key_id: str) -> None:
    """
    Reset rate limit counter for a specific key.
    Useful when revoking or resetting a key.
    """
    with _lock:
        _request_tracker.pop(key_id, None)


def _cleanup_old_entries(cutoff_time: float) -> None:
    """Remove old timestamps from all keys (internal function)"""
    keys_to_remove = []
    for key_id in _request_tracker:
        timestamps = _request_tracker[key_id]
        # Remove old entries
        timestamps[:] = [ts for ts in timestamps if ts > cutoff_time]
        # Remove key if no recent requests
        if not timestamps:
            keys_to_remove.append(key_id)
    
    for key_id in keys_to_remove:
        del _request_tracker[key_id]
