"""
Municipal Data Providers

Handles different data sources:
- SocrataProvider: Queries Socrata API endpoints
- SerpAPIFallbackProvider: Fallback using SerpAPI web search
- CacheProvider: Redis/in-memory caching (7-day TTL)
"""

from app.services.municipal_data.providers.socrata_provider import SocrataProvider
from app.services.municipal_data.providers.fallback_provider import SerpAPIFallbackProvider
from app.services.municipal_data.providers.cache import CacheProvider, InMemoryCache

__all__ = [
    "SocrataProvider",
    "SerpAPIFallbackProvider",
    "CacheProvider",
    "InMemoryCache",
]
