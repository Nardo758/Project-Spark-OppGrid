"""
Municipal Data API Client

Provides access to government municipal data (Socrata endpoints) for market analysis.
Enables real, defensible supply analysis using county property databases instead of web scrapes.

Main exports:
- MunicipalDataClient: Main entry point
- SelfStorageAnalyzer: Industry-specific analyzer
- SocrataProvider: Low-level Socrata API handler
- SerpAPIFallbackProvider: Fallback for uncovered metros
"""

from app.services.municipal_data.client import MunicipalDataClient
from app.services.municipal_data.industry_analyzers import SelfStorageAnalyzer
from app.services.municipal_data.providers.socrata_provider import SocrataProvider
from app.services.municipal_data.providers.fallback_provider import SerpAPIFallbackProvider
from app.services.municipal_data.schemas import (
    FacilitySupplyMetrics,
    SupplyVerdict,
    MunicipalQueryResult,
    CensusPopulationData,
)

__all__ = [
    "MunicipalDataClient",
    "SelfStorageAnalyzer",
    "SocrataProvider",
    "SerpAPIFallbackProvider",
    "FacilitySupplyMetrics",
    "SupplyVerdict",
    "MunicipalQueryResult",
    "CensusPopulationData",
]
