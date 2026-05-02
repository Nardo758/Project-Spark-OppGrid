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


class RestaurantAnalyzer(IndustryAnalyzer):
    """
    Restaurant Facility Analyzer
    
    Supply metrics:
    - Benchmark: varies by segment (casual vs fine dining)
    - Oversaturated: > 50 seats per 1,000 population (too much supply)
    - Balanced: 30-50 seats per 1,000 population (healthy market)
    - Undersaturated: < 30 seats per 1,000 population (growth opportunity)
    
    This analyzer:
    1. Counts restaurant facilities
    2. Estimates total seats (average 50 seats per facility)
    3. Calculates seats per 1,000 population
    4. Compares to segment-specific benchmark
    5. Returns verdict + confidence
    """
    
    INDUSTRY_CODE = "restaurant"
    DESCRIPTION = "Food service facilities and restaurants"
    
    # Industry-specific constants
    BENCHMARK_SEATS_PER_1K = 40.0  # Standard supply metric
    AVG_SEATS_PER_FACILITY = 50.0  # Assumed average
    OVERSATURATED_THRESHOLD = 50.0
    BALANCED_MIN = 30.0
    BALANCED_MAX = 50.0
    UNDERSATURATED_THRESHOLD = 30.0
    
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
        Analyze restaurant supply for a metro.
        """
        
        # Estimate total seats from facility count and sqft
        estimated_seats = self._estimate_total_seats(
            total_facilities,
            total_building_sqft
        )
        
        # Calculate key metrics
        seats_per_1k = self._calculate_seats_per_1k(estimated_seats, population)
        facilities_per_100k = self._calculate_facilities_per_100k(
            total_facilities,
            population
        )
        
        # Determine verdict
        verdict = self._determine_verdict(seats_per_1k)
        
        logger.info(
            f"Restaurant Analysis: {metro}, {state} - "
            f"{seats_per_1k:.1f} seats/1000 → {verdict.value}"
        )
        
        # Build metrics
        metrics = FacilitySupplyMetrics(
            metro=metro.lower(),
            state=state.upper(),
            industry=self.INDUSTRY_CODE,
            total_facilities=total_facilities,
            total_building_sqft=total_building_sqft,
            population=population,
            sqft_per_capita=estimated_seats / population,  # Use seats as proxy for sqft metric
            facilities_per_100k_population=facilities_per_100k,
            verdict=verdict,
            benchmark_sqft_per_capita=self.BENCHMARK_SEATS_PER_1K,
            confidence=confidence,
            data_source=data_source,
            coverage_percentage=coverage_percentage,
        )
        
        return metrics
    
    @staticmethod
    def _estimate_total_seats(total_facilities: int, total_sqft: int) -> int:
        """
        Estimate total seating capacity.
        Method: Use sqft if available (assume 15 sqft per seat), otherwise use facility count
        """
        if total_sqft > 0:
            # ~15 sqft per seat (includes kitchen, storage, etc.)
            return int(total_sqft / 15.0)
        return int(total_facilities * RestaurantAnalyzer.AVG_SEATS_PER_FACILITY)
    
    @staticmethod
    def _calculate_seats_per_1k(total_seats: int, population: int) -> float:
        """Calculate seats per 1,000 population"""
        if population <= 0:
            return 0.0
        return (total_seats / population) * 1_000
    
    @staticmethod
    def _calculate_facilities_per_100k(total_facilities: int, population: int) -> float:
        """Calculate number of facilities per 100,000 population"""
        if population <= 0:
            return 0.0
        return (total_facilities / population) * 100_000
    
    @staticmethod
    def _determine_verdict(seats_per_1k: float) -> SupplyVerdict:
        """
        Determine supply verdict based on seats per 1,000 population.
        
        Thresholds:
        - Oversaturated: > 50
        - Balanced: 30-50
        - Undersaturated: < 30
        """
        if seats_per_1k > 50.0:
            return SupplyVerdict.OVERSATURATED
        elif seats_per_1k >= 30.0:
            return SupplyVerdict.BALANCED
        else:
            return SupplyVerdict.UNDERSATURATED


class FitnessAnalyzer(IndustryAnalyzer):
    """
    Fitness Studio/Facility Analyzer
    
    Supply metrics:
    - Benchmark: 10.0 sq ft per capita (typical market)
    - Oversaturated: > 10.0 sq ft per capita
    - Balanced: 6.0-10.0 sq ft per capita
    - Undersaturated: < 6.0 sq ft per capita
    
    This analyzer:
    1. Counts fitness facilities
    2. Calculates sq ft per capita
    3. Calculates facilities per 100k population
    4. Compares to benchmark
    5. Returns verdict + confidence
    """
    
    INDUSTRY_CODE = "fitness"
    DESCRIPTION = "Fitness studios and gymnasiums"
    
    # Industry-specific constants
    BENCHMARK_SQFT_PER_CAPITA = 10.0
    OVERSATURATED_THRESHOLD = 10.0
    BALANCED_MIN = 6.0
    BALANCED_MAX = 10.0
    UNDERSATURATED_THRESHOLD = 6.0
    
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
        Analyze fitness supply for a metro.
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
            f"Fitness Analysis: {metro}, {state} - "
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
        - Oversaturated: > 10.0
        - Balanced: 6.0-10.0
        - Undersaturated: < 6.0
        """
        if sqft_per_capita > 10.0:
            return SupplyVerdict.OVERSATURATED
        elif sqft_per_capita >= 6.0:
            return SupplyVerdict.BALANCED
        else:
            return SupplyVerdict.UNDERSATURATED


class GasStationAnalyzer(IndustryAnalyzer):
    """
    Gas Station Analyzer
    
    Supply metrics:
    - Benchmark: 500-600 vehicles per station (typical market)
    - Oversaturated: < 400 vehicles per station (too much supply)
    - Balanced: 400-600 vehicles per station (healthy market)
    - Undersaturated: > 600 vehicles per station (growth opportunity)
    
    This analyzer:
    1. Counts gas stations
    2. Estimates vehicles per station (from population)
    3. Calculates facilities per 100k population
    4. Compares to benchmark
    5. Returns verdict + confidence
    """
    
    INDUSTRY_CODE = "gas_station"
    DESCRIPTION = "Gasoline/fuel stations and convenience stores"
    
    # Industry-specific constants
    BENCHMARK_VEHICLES_PER_STATION = 500.0  # Standard supply metric
    VEHICLES_PER_CAPITA = 0.8  # Estimate: 0.8 vehicles per capita
    OVERSATURATED_THRESHOLD = 400.0  # < 400 vehicles per station = oversaturated
    BALANCED_MIN = 400.0
    BALANCED_MAX = 600.0
    UNDERSATURATED_THRESHOLD = 600.0  # > 600 vehicles per station = undersaturated
    
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
        Analyze gas station supply for a metro.
        """
        
        # Estimate vehicles from population
        estimated_vehicles = self._estimate_vehicles(population)
        
        # Calculate key metrics
        vehicles_per_station = self._calculate_vehicles_per_station(
            estimated_vehicles,
            total_facilities
        )
        
        facilities_per_100k = self._calculate_facilities_per_100k(
            total_facilities,
            population
        )
        
        # Determine verdict
        verdict = self._determine_verdict(vehicles_per_station)
        
        logger.info(
            f"Gas Station Analysis: {metro}, {state} - "
            f"{vehicles_per_station:.0f} vehicles/station → {verdict.value}"
        )
        
        # Build metrics
        metrics = FacilitySupplyMetrics(
            metro=metro.lower(),
            state=state.upper(),
            industry=self.INDUSTRY_CODE,
            total_facilities=total_facilities,
            total_building_sqft=total_building_sqft,
            population=population,
            sqft_per_capita=vehicles_per_station / 1000.0,  # Use vehicles as proxy for sqft metric
            facilities_per_100k_population=facilities_per_100k,
            verdict=verdict,
            benchmark_sqft_per_capita=self.BENCHMARK_VEHICLES_PER_STATION,
            confidence=confidence,
            data_source=data_source,
            coverage_percentage=coverage_percentage,
        )
        
        return metrics
    
    @staticmethod
    def _estimate_vehicles(population: int) -> int:
        """Estimate number of vehicles from population"""
        return int(population * GasStationAnalyzer.VEHICLES_PER_CAPITA)
    
    @staticmethod
    def _calculate_vehicles_per_station(total_vehicles: int, total_stations: int) -> float:
        """Calculate vehicles per station"""
        if total_stations <= 0:
            return 0.0
        return total_vehicles / total_stations
    
    @staticmethod
    def _calculate_facilities_per_100k(total_facilities: int, population: int) -> float:
        """Calculate number of facilities per 100,000 population"""
        if population <= 0:
            return 0.0
        return (total_facilities / population) * 100_000
    
    @staticmethod
    def _determine_verdict(vehicles_per_station: float) -> SupplyVerdict:
        """
        Determine supply verdict based on vehicles per station.
        
        Note: Inverse logic - FEWER vehicles per station = OVERSATURATED
        
        Thresholds:
        - Oversaturated: < 400 vehicles/station (too many stations)
        - Balanced: 400-600 vehicles/station (healthy market)
        - Undersaturated: > 600 vehicles/station (too few stations)
        """
        if vehicles_per_station < 400.0:
            return SupplyVerdict.OVERSATURATED
        elif vehicles_per_station <= 600.0:
            return SupplyVerdict.BALANCED
        else:
            return SupplyVerdict.UNDERSATURATED


class IndustryAnalyzerFactory:
    """
    Factory for creating industry analyzers.
    
    Usage:
        analyzer = IndustryAnalyzerFactory.get_analyzer("self-storage")
        metrics = await analyzer.analyze(...)
    """
    
    _analyzers = {
        "self-storage": SelfStorageAnalyzer,
        "restaurant": RestaurantAnalyzer,
        "fitness": FitnessAnalyzer,
        "gas_station": GasStationAnalyzer,
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
