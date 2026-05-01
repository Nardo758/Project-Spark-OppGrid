"""
Success Profile Services

Location identification and candidate discovery services for the OppGrid Consultant Studio.
Includes Tier A (named micro-markets) and Tier B (gap discovery) functionality.
"""

from .identify_location_service import IdentifyLocationService
from .micro_market_catalog import MicroMarketCatalog
from .gap_discovery import GapDiscoveryEngine
from .candidate_profile_builder import CandidateProfileBuilder

__all__ = [
    "IdentifyLocationService",
    "MicroMarketCatalog",
    "GapDiscoveryEngine",
    "CandidateProfileBuilder",
]
