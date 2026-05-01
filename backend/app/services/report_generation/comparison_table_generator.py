"""
Comparison Table Generator - Creates formatted comparison tables for report
Handles data normalization and formatting for professional table display
"""

import logging
from typing import Dict, List, Any, Optional, Union
from decimal import Decimal

logger = logging.getLogger(__name__)


class ComparisonTableGenerator:
    """Generate comparison tables with normalized data and formatting"""

    @staticmethod
    def format_value(value: Any, value_type: str = 'text') -> str:
        """
        Format a value for display in table
        
        Args:
            value: Value to format
            value_type: Type of value ('text', 'score', 'currency', 'percent', 'number')
        
        Returns:
            Formatted string value
        """
        if value is None:
            return "—"
        
        if value_type == 'score':
            if isinstance(value, (int, float)):
                return f"{int(value)}/100"
            return str(value)
        
        elif value_type == 'currency':
            if isinstance(value, (int, float)):
                return f"${int(value):,}"
            return str(value)
        
        elif value_type == 'percent':
            if isinstance(value, (int, float)):
                return f"{value:.1f}%"
            return str(value)
        
        elif value_type == 'number':
            if isinstance(value, (int, float, Decimal)):
                return f"{int(value):,}"
            return str(value)
        
        else:  # text
            text = str(value)
            # Truncate long text for table display
            if len(text) > 50:
                return text[:47] + "..."
            return text
    
    @staticmethod
    def create_identify_location_table(
        candidates: List[Dict[str, Any]],
        sort_by: str = 'score',
        descending: bool = True,
    ) -> tuple[List[str], List[List[str]]]:
        """
        Create comparison table for Identify Location report
        
        Args:
            candidates: List of candidate locations
            sort_by: Column to sort by ('score', 'name', 'population', etc.)
            descending: Sort descending if True
        
        Returns:
            Tuple of (headers, rows)
        """
        # Sort candidates
        candidates_sorted = sorted(
            candidates,
            key=lambda x: x.get(sort_by, 0),
            reverse=descending,
        )
        
        headers = [
            'Rank',
            'Location Name',
            'Fit Score',
            'Population',
            'Median Income',
            'Competition',
            'Demand Signal',
            'Avg Rent',
            'Risk Level',
        ]
        
        rows = []
        for rank, candidate in enumerate(candidates_sorted, 1):
            row = [
                str(rank),
                ComparisonTableGenerator.format_value(
                    candidate.get('name'), 'text'
                ),
                ComparisonTableGenerator.format_value(
                    candidate.get('score', 0), 'score'
                ),
                ComparisonTableGenerator.format_value(
                    candidate.get('population'), 'number'
                ),
                ComparisonTableGenerator.format_value(
                    candidate.get('median_income'), 'currency'
                ),
                ComparisonTableGenerator.format_value(
                    candidate.get('competition_count', 0), 'number'
                ),
                ComparisonTableGenerator.format_value(
                    candidate.get('demand_signal', 0), 'percent'
                ),
                ComparisonTableGenerator.format_value(
                    candidate.get('avg_rent'), 'currency'
                ),
                ComparisonTableGenerator.format_value(
                    candidate.get('risk_level', 'medium'), 'text'
                ).upper(),
            ]
            rows.append(row)
        
        return headers, rows
    
    @staticmethod
    def create_clone_success_table(
        matching_locations: List[Dict[str, Any]],
        sort_by: str = 'similarity_score',
        descending: bool = True,
    ) -> tuple[List[str], List[List[str]]]:
        """
        Create comparison table for Clone Success report
        
        Args:
            matching_locations: List of matching locations
            sort_by: Column to sort by ('similarity_score', 'demographics_match', etc.)
            descending: Sort descending if True
        
        Returns:
            Tuple of (headers, rows)
        """
        # Sort locations
        locations_sorted = sorted(
            matching_locations,
            key=lambda x: x.get(sort_by, 0),
            reverse=descending,
        )
        
        headers = [
            'Rank',
            'Location',
            'Similarity',
            'Demographics',
            'Competition',
            'Population',
            'Median Income',
            'Replicability',
        ]
        
        rows = []
        for rank, location in enumerate(locations_sorted, 1):
            location_name = f"{location.get('city', 'Unknown')}, {location.get('state', '')}"
            
            row = [
                str(rank),
                ComparisonTableGenerator.format_value(location_name, 'text'),
                ComparisonTableGenerator.format_value(
                    location.get('similarity_score', 0), 'score'
                ),
                ComparisonTableGenerator.format_value(
                    location.get('demographics_match', 0), 'score'
                ),
                ComparisonTableGenerator.format_value(
                    location.get('competition_match', 0), 'score'
                ),
                ComparisonTableGenerator.format_value(
                    location.get('population'), 'number'
                ),
                ComparisonTableGenerator.format_value(
                    location.get('median_income'), 'currency'
                ),
                ComparisonTableGenerator._calculate_replicability(location),
            ]
            rows.append(row)
        
        return headers, rows
    
    @staticmethod
    def _calculate_replicability(location: Dict[str, Any]) -> str:
        """
        Calculate replicability label based on location metrics
        
        Args:
            location: Location data
        
        Returns:
            Replicability label
        """
        similarity = location.get('similarity_score', 0)
        
        if similarity >= 85:
            return "✓ High"
        elif similarity >= 70:
            return "✓ Moderate"
        else:
            return "⚠ Low"
    
    @staticmethod
    def create_risk_summary_table(
        candidates: List[Dict[str, Any]],
    ) -> tuple[List[str], List[List[str]]]:
        """
        Create risk summary table for report
        
        Args:
            candidates: List of candidates with risk data
        
        Returns:
            Tuple of (headers, rows)
        """
        headers = [
            'Location',
            'Risk Level',
            'Primary Risk Factor',
            'Secondary Risk',
            'Mitigation',
        ]
        
        rows = []
        for candidate in candidates:
            risk_factors = candidate.get('risk_factors', [])
            
            row = [
                ComparisonTableGenerator.format_value(
                    candidate.get('name'), 'text'
                ),
                ComparisonTableGenerator.format_value(
                    candidate.get('risk_level', 'medium'), 'text'
                ).upper(),
                ComparisonTableGenerator.format_value(
                    risk_factors[0] if risk_factors else 'None',
                    'text'
                ),
                ComparisonTableGenerator.format_value(
                    risk_factors[1] if len(risk_factors) > 1 else 'None',
                    'text'
                ),
                ComparisonTableGenerator.format_value(
                    candidate.get('risk_mitigation', 'See detailed analysis'),
                    'text'
                ),
            ]
            rows.append(row)
        
        return headers, rows
    
    @staticmethod
    def create_metrics_summary(
        data: Dict[str, Any],
        metric_keys: List[str],
        metric_types: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Create formatted metrics summary
        
        Args:
            data: Source data dictionary
            metric_keys: Keys to extract
            metric_types: Mapping of key to value_type for formatting
        
        Returns:
            Dictionary of formatted metrics
        """
        metric_types = metric_types or {}
        result = {}
        
        for key in metric_keys:
            value = data.get(key)
            value_type = metric_types.get(key, 'text')
            result[key] = ComparisonTableGenerator.format_value(value, value_type)
        
        return result
    
    @staticmethod
    def build_archetype_summary(
        candidates_by_archetype: Dict[str, List[Dict[str, Any]]],
    ) -> List[tuple[str, int, float]]:
        """
        Build summary of candidates grouped by archetype
        
        Args:
            candidates_by_archetype: Dict of archetype -> list of candidates
        
        Returns:
            List of (archetype, count, avg_score)
        """
        summary = []
        
        for archetype, candidates in candidates_by_archetype.items():
            count = len(candidates)
            avg_score = (
                sum(c.get('score', 0) for c in candidates) / count
                if count > 0
                else 0
            )
            summary.append((archetype, count, avg_score))
        
        return sorted(summary, key=lambda x: x[2], reverse=True)
