"""
Cache Manager for OppGrid API
Provides in-memory caching with TTL support for performance optimization
"""

import hashlib
import json
import time
from typing import Any, Callable, Optional, Dict
from datetime import datetime, timedelta


class CacheEntry:
    """A single cache entry with TTL tracking"""
    
    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0
        self.last_accessed = time.time()
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return (time.time() - self.created_at) > self.ttl_seconds
    
    def get_value(self) -> Any:
        """Get value and update access info"""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value
    
    def get_remaining_ttl(self) -> float:
        """Get remaining TTL in seconds"""
        elapsed = time.time() - self.created_at
        return max(0, self.ttl_seconds - elapsed)


class SimpleCacheManager:
    """Simple in-memory cache manager for API responses"""
    
    def __init__(self, max_entries: int = 1000, cleanup_interval: int = 300):
        self._cache: Dict[str, CacheEntry] = {}
        self.max_entries = max_entries
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_bytes": 0,
        }
    
    def _generate_key(self, key_str: str) -> str:
        """Generate a cache key"""
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        if (current_time - self.last_cleanup) < self.cleanup_interval:
            return
        
        expired_keys = [
            k for k, v in self._cache.items()
            if v.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self.stats["evictions"] += len(expired_keys)
        
        self.last_cleanup = current_time
    
    def _enforce_max_entries(self):
        """Evict least recently used entry if cache is full"""
        if len(self._cache) >= self.max_entries:
            # Find least recently accessed entry
            lru_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].last_accessed
            )
            del self._cache[lru_key]
            self.stats["evictions"] += 1
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set a cache entry"""
        self._cleanup_expired()
        self._enforce_max_entries()
        
        cache_key = self._generate_key(key)
        self._cache[cache_key] = CacheEntry(value, ttl_seconds)
        
        # Update size estimate
        try:
            size = len(json.dumps(value, default=str))
            self.stats["total_bytes"] += size
        except:
            pass
    
    def get(self, key: str) -> Optional[Any]:
        """Get a cache entry"""
        cache_key = self._generate_key(key)
        
        if cache_key not in self._cache:
            self.stats["misses"] += 1
            return None
        
        entry = self._cache[cache_key]
        
        if entry.is_expired():
            del self._cache[cache_key]
            self.stats["misses"] += 1
            self.stats["evictions"] += 1
            return None
        
        self.stats["hits"] += 1
        return entry.get_value()
    
    def delete(self, key: str):
        """Delete a cache entry"""
        cache_key = self._generate_key(key)
        if cache_key in self._cache:
            del self._cache[cache_key]
    
    def clear(self):
        """Clear entire cache"""
        self._cache.clear()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_bytes": 0,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
            "entries_count": len(self._cache),
            "entries_max": self.max_entries,
            "estimated_memory_bytes": self.stats["total_bytes"],
        }
    
    def get_etag(self, key: str) -> Optional[str]:
        """Generate ETag for a cache entry (for HTTP cache headers)"""
        cache_key = self._generate_key(key)
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if not entry.is_expired():
                # Create ETag from content hash
                content_hash = hashlib.md5(
                    json.dumps(entry.value, default=str, sort_keys=True).encode()
                ).hexdigest()
                return f'"{content_hash}"'
        return None


# Global cache instance
_cache_instance: Optional[SimpleCacheManager] = None


def get_cache_manager() -> SimpleCacheManager:
    """Get or create global cache manager"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SimpleCacheManager(max_entries=1000)
    return _cache_instance


def cache_with_ttl(
    key_prefix: str,
    ttl_seconds: int = 300,
    key_func: Optional[Callable] = None
):
    """
    Decorator to cache function results with TTL
    
    Args:
        key_prefix: Prefix for cache key
        ttl_seconds: Time to live in seconds
        key_func: Function to generate cache key from arguments
    
    Usage:
        @cache_with_ttl("search_ideas", ttl_seconds=300)
        async def search_ideas(query: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Use function name + args as key
                cache_key = f"{key_prefix}:{json.dumps({
                    'args': str(args),
                    'kwargs': str(kwargs)
                }, default=str)}"
            
            # Try to get from cache
            cache = get_cache_manager()
            cached_value = cache.get(cache_key)
            
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            
            return result
        
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{key_prefix}:{json.dumps({
                    'args': str(args),
                    'kwargs': str(kwargs)
                }, default=str)}"
            
            # Try to get from cache
            cache = get_cache_manager()
            cached_value = cache.get(cache_key)
            
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            
            return result
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Cache key generators for common patterns

def search_ideas_cache_key(query: Optional[str] = None, category: Optional[str] = None, **kwargs) -> str:
    """Generate cache key for search-ideas endpoint"""
    return f"search_ideas:{query}:{category}"


def trending_searches_cache_key() -> str:
    """Generate cache key for trending searches"""
    return "trending_searches"


def opportunity_cache_key(opportunity_id: int) -> str:
    """Generate cache key for specific opportunity"""
    return f"opportunity:{opportunity_id}"


def list_cache_key(endpoint: str, limit: int = 20, offset: int = 0, **filters) -> str:
    """Generate cache key for list endpoints"""
    filter_str = ":".join(f"{k}={v}" for k, v in sorted(filters.items()))
    return f"{endpoint}:limit={limit}:offset={offset}:{filter_str}"
