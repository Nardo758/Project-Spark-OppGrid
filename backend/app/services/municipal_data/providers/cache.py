"""
Caching provider for Municipal Data queries.

Supports in-memory caching with 7-day TTL.
Can be extended to support Redis.

Cache key format: "{metro}_{industry}_{boundary_hash}"
TTL: 7 days (86400 * 7 seconds)
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from app.services.municipal_data.schemas import FacilitySupplyMetrics

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 86400 * 7  # 7 days


class CacheProvider(ABC):
    """Abstract base class for cache implementations"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[FacilitySupplyMetrics]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: FacilitySupplyMetrics,
        ttl_seconds: int = CACHE_TTL_SECONDS
    ) -> bool:
        """Set value in cache"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear entire cache"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass


class InMemoryCache(CacheProvider):
    """
    In-memory cache implementation.
    
    Simple dict-based cache with TTL support.
    Good for development/testing. For production, use Redis.
    
    Thread-safe with basic locking if needed.
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }
    
    async def get(self, key: str) -> Optional[FacilitySupplyMetrics]:
        """
        Get value from cache.
        
        Returns None if:
        - Key not found
        - Value expired
        """
        if key not in self._cache:
            self._stats["misses"] += 1
            return None
        
        entry = self._cache[key]
        
        # Check expiration
        expires_at = entry.get("expires_at")
        if expires_at and datetime.utcnow() > expires_at:
            logger.info(f"Cache entry expired: {key}")
            del self._cache[key]
            self._stats["misses"] += 1
            return None
        
        # Hit
        entry["access_count"] += 1
        entry["last_accessed"] = datetime.utcnow()
        self._stats["hits"] += 1
        
        logger.debug(f"Cache hit: {key} (access #{entry['access_count']})")
        return entry["value"]
    
    async def set(
        self,
        key: str,
        value: FacilitySupplyMetrics,
        ttl_seconds: int = CACHE_TTL_SECONDS
    ) -> bool:
        """Set value in cache with TTL"""
        try:
            self._cache[key] = {
                "value": value,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(seconds=ttl_seconds),
                "access_count": 0,
                "last_accessed": None,
            }
            self._stats["sets"] += 1
            logger.debug(f"Cache set: {key} (TTL: {ttl_seconds}s)")
            return True
        except Exception as e:
            logger.error(f"Error setting cache {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        try:
            if key in self._cache:
                del self._cache[key]
                self._stats["deletes"] += 1
                logger.debug(f"Cache deleted: {key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting cache {key}: {e}")
            return False
    
    async def clear(self) -> bool:
        """Clear entire cache"""
        try:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared ({count} entries)")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
        {
            'hits': int,
            'misses': int,
            'hit_rate': float (0.0-1.0),
            'sets': int,
            'deletes': int,
            'size': int,
        }
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0.0
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "sets": self._stats["sets"],
            "deletes": self._stats["deletes"],
            "size": len(self._cache),
        }


def generate_cache_key(metro: str, industry: str, boundary: Optional[Dict] = None) -> str:
    """
    Generate cache key from request parameters.
    
    Format: "{metro}_{industry}_{boundary_hash}"
    
    Args:
        metro: Metro identifier
        industry: Industry code
        boundary: Optional boundary parameters
    
    Returns:
        Cache key string
    """
    parts = [metro.lower(), industry.lower()]
    
    if boundary:
        # Hash boundary to create deterministic key
        boundary_str = json.dumps(boundary, sort_keys=True)
        boundary_hash = hashlib.sha256(boundary_str.encode()).hexdigest()[:8]
        parts.append(boundary_hash)
    
    return "_".join(parts)
