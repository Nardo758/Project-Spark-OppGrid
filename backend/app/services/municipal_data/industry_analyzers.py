"""
Industry-Specific Analyzers

Implements analysis logic for different facility types.
Each analyzer knows how to interpret supply metrics for its industry.

Currently implemented:
- SelfStorageAnalyzer: Self-storage facilities analysis
"""

import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from app.services.municipal_data.schemas import (
    FacilitySupplyMetrics,
    SupplyVerdict,
    MunicipalQueryResult,
)
from app.services.municipal_data.land_use_mapping import (
    SUPPLY_BENCHMARKS,
    get_benchmark,
)

logger = logging.getLogger(__name__)


class IndustryAnalyzer(ABC):
    """
    Abstract base class for industry analyzers.
    
    Each industry has different supply metrics and verdict logic.
    """
    
    INDUSTRY_CODE = None
    DESCRIPTION = None
    
    @abstractmethod
    async def analyze(
        self,
        metro: str,
        state: str,
        total_facilities: int,
        total_building_sqft: int,
        population: int,
        confidence: float = 0.95,
        data_source: str = "socrata",
    ) -> FacilitySupplyMetrics:
        """
        Analyze supply metrics for the industry.
        
        Returns FacilitySupplyMetrics with verdict.
        """
        pass


class SelfStorageAnalyzer(IndustryAnalyzer):
    """
    Self-Storage Facility Analyzer
    
    Supply metrics:
    - Benchmark: 7.0 sq ft per capita (typical market)
    - Oversaturated: > 7.0 sq ft per capita (too much supply)
    - Balanced: 5.0-7.0 sq ft per capita (healthy market)
    - Undersaturated: < 5.0 sq ft per capita (growth opportunity)
    
    This analyzer:
    1. Calculates sq ft per capita
    2. Calculates facilities per 100k population
    3. Compares to benchmark
    4. Returns verdict + confidence
    """
    
    INDUSTRY_CODE = "self-storage"
    DESCRIPTION = "Self-storage and mini-warehouse facilities"
    
    # Industry-specific constants
    BENCHMARK_SQFT_PER_CAPITA = 7.0  # Standard supply metric
    OVERSATURATED_THRESHOLD = 7.0
    BALANCED_MIN = 5.0
    BALANCED_MAX = 7.0
    UNDERSATURATED_THRESHOLD = 5.0
    
    async def analyze(
        self,
        metro: str,
        state: str,
        total_facilities: int,
        total_building_sqft: int,
        population: int,
        confidence: float = 0.95,
        data_source: str = "socrata",
        coverage_percentage: float = 100.0,
    ) -> FacilitySupplyMetrics:
        """
        Analyze self-storage supply for a metro.
        
        Args:
            metro: Metro name
            state: State code
            total_facilities: Number of facilities found
            total_building_sqft: Total building square footage
            population: Metro population (Census)
            confidence: Confidence score (0.95 for Socrata, 0.60 for fallback)
            data_source: Source of data
            coverage_percentage: % of parcels covered by query
        
        Returns:
            FacilitySupplyMetrics with verdict
        """
        
        # Calculate key metrics
        sqft_per_capita = self._calculate_sqft_per_capita(
            total_building_sqft,
            population
        )
        
        facilities_per_100k = self._calculate_facilities_per_100k(
            total_facilities,
            population
        )
        
        # Determine verdict
        verdict = self._determine_verdict(sqft_per_capita)
        
        logger.info(
            f"Self-Storage Analysis: {metro}, {state} - "
            f"{sqft_per_capita:.2f} sqft/capita → {verdict.value}"
        )
        
        # Build metrics
        metrics = FacilitySupplyMetrics(
            metro=metro.lower(),
            state=state.upper(),
            industry=self.INDUSTRY_CODE,
            total_facilities=total_facilities,
            total_building_sqft=total_building_sqft,
            population=population,
            sqft_per_capita=sqft_per_capita,
            facilities_per_100k_population=facilities_per_100k,
            verdict=verdict,
            benchmark_sqft_per_capita=self.BENCHMARK_SQFT_PER_CAPITA,
            confidence=confidence,
            data_source=data_source,
            coverage_percentage=coverage_percentage,
        )
        
        return metrics
    
    @staticmethod
    def _calculate_sqft_per_capita(total_sqft: int, population: int) -> float:
        """Calculate building sq ft per capita"""
        if population <= 0:
            return 0.0
        return total_sqft / population
    
    @staticmethod
    def _calculate_facilities_per_100k(total_facilities: int, population: int) -> float:
        """Calculate number of facilities per 100,000 population"""
        if population <= 0:
            return 0.0
        return (total_facilities / population) * 100_000
    
    @staticmethod
    def _determine_verdict(sqft_per_capita: float) -> SupplyVerdict:
        """
        Determine supply verdict based on sq ft per capita.
        
        Thresholds:
        - Oversaturated: > 7.0
        - Balanced: 5.0-7.0
        - Undersaturated: < 5.0
        """
        if sqft_per_capita > 7.0:
            return SupplyVerdict.OVERSATURATED
        elif sqft_per_capita >= 5.0:
            return SupplyVerdict.BALANCED
        else:
            return SupplyVerdict.UNDERSATURATED
    
    def get_interpretation(self, metrics: FacilitySupplyMetrics) -> str:
        """
        Get human-readable interpretation of supply metrics.
        
        Returns: String description of what the metrics mean
        """
        verdict = metrics.verdict
        sqft_per_capita = metrics.sqft_per_capita
        benchmark = self.BENCHMARK_SQFT_PER_CAPITA
        
        if verdict == SupplyVerdict.OVERSATURATED:
            diff = sqft_per_capita - benchmark
            pct = (diff / benchmark) * 100
            return (
                f"This market is OVERSATURATED with {sqft_per_capita:.2f} sqft per capita "
                f"({pct:.1f}% above the {benchmark} benchmark). "
                f"Significant competition. High barriers to new entry."
            )
        
        elif verdict == SupplyVerdict.BALANCED:
            return (
                f"This market is BALANCED with {sqft_per_capita:.2f} sqft per capita "
                f"(within the {self.BALANCED_MIN}-{self.BALANCED_MAX} range). "
                f"Healthy competitive environment."
            )
        
        else:  # UNDERSATURATED
            diff = benchmark - sqft_per_capita
            pct = (diff / benchmark) * 100
            return (
                f"This market is UNDERSATURATED with {sqft_per_capita:.2f} sqft per capita "
                f"({pct:.1f}% below the {benchmark} benchmark). "
                f"Growth opportunity. Lower competition, potential for expansion."
            )


class IndustryAnalyzerFactory:
    """
    Factory for creating industry analyzers.
    
    Usage:
        analyzer = IndustryAnalyzerFactory.get_analyzer("self-storage")
        metrics = await analyzer.analyze(...)
    """
    
    _analyzers = {
        "self-storage": SelfStorageAnalyzer,
    }
    
    @classmethod
    def get_analyzer(cls, industry: str) -> Optional[IndustryAnalyzer]:
        """
        Get analyzer for industry.
        
        Args:
            industry: Industry code (e.g., "self-storage")
        
        Returns:
            Analyzer instance or None
        """
        industry_lower = industry.lower()
        
        analyzer_class = cls._analyzers.get(industry_lower)
        if not analyzer_class:
            logger.warning(f"No analyzer registered for industry '{industry}'")
            return None
        
        return analyzer_class()
    
    @classmethod
    def list_supported_industries(cls) -> list:
        """List all supported industries"""
        return list(cls._analyzers.keys())
    
    @classmethod
    def register_analyzer(cls, industry: str, analyzer_class: type):
        """Register a new analyzer"""
        cls._analyzers[industry.lower()] = analyzer_class
