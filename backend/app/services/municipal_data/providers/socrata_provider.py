"""
Socrata API Provider

Low-level interface to Socrata-powered municipal data endpoints.
Handles HTTP requests, error handling, and response parsing.

Endpoints:
- Miami-Dade: https://data.miamidade.gov
- Chicago: https://data.cityofchicago.org
- NYC: https://data.cityofnewyork.us
- Seattle: https://data.seattle.gov
- Denver: https://denvergov.org/opendata
"""

import logging
import time
from typing import Optional, List, Dict, Any
import httpx

from app.services.municipal_data.schemas import SocrataEndpoint, SupplyVerdict

logger = logging.getLogger(__name__)

# Socrata endpoint configurations
SOCRATA_ENDPOINTS = {
    "miami": SocrataEndpoint(
        metro="Miami",
        state="FL",
        base_url="https://data.miamidade.gov",
        land_use_field="dor_code",
        sqft_field="building_square_feet",
    ),
    "chicago": SocrataEndpoint(
        metro="Chicago",
        state="IL",
        base_url="https://data.cityofchicago.org",
        land_use_field="land_use_code",
        sqft_field="building_square_feet",
    ),
    "nyc": SocrataEndpoint(
        metro="New York City",
        state="NY",
        base_url="https://data.cityofnewyork.us",
        land_use_field="bldg_class",
        sqft_field="lot_area",  # NYC uses lot area, may need adjustment
    ),
    "seattle": SocrataEndpoint(
        metro="Seattle",
        state="WA",
        base_url="https://data.seattle.gov",
        land_use_field="land_use_code",
        sqft_field="building_square_feet",
    ),
    "denver": SocrataEndpoint(
        metro="Denver",
        state="CO",
        base_url="https://denvergov.org/opendata",
        land_use_field="zoning_code",
        sqft_field="building_square_feet",
    ),
}


class SocrataProviderError(Exception):
    """Raised when Socrata query fails"""
    pass


class SocrataProvider:
    """
    Low-level Socrata API client.
    
    Handles:
    - Building SoQL queries
    - Making HTTP requests
    - Parsing responses
    - Error handling
    - Rate limiting
    """
    
    # API timeout
    TIMEOUT_SECONDS = 30
    
    # Rate limiting (conservative - Socrata allows ~60,000/day)
    RATE_LIMIT_DELAY = 0.1  # seconds between requests
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS)
        self._last_request_time = 0
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def query(
        self,
        metro: str,
        dataset_id: str,
        land_use_field: str,
        land_use_codes: List[str],
        sqft_field: str,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Query a Socrata dataset.
        
        Args:
            metro: Metro identifier (e.g., "miami")
            dataset_id: Socrata dataset ID
            land_use_field: Field name for land use codes
            land_use_codes: List of codes to filter by
            sqft_field: Field name for building square footage
            limit: Optional query limit
        
        Returns:
            {
                'total_facilities': int,
                'total_sqft': int,
                'rows': [...],
            }
        
        Raises:
            SocrataProviderError: If query fails
        """
        if metro.lower() not in SOCRATA_ENDPOINTS:
            raise SocrataProviderError(f"Unknown metro: {metro}")
        
        endpoint = SOCRATA_ENDPOINTS[metro.lower()]
        
        # Build SoQL query
        query = self._build_soql_query(
            land_use_field,
            land_use_codes,
            sqft_field,
            limit
        )
        
        # Build URL
        url = f"{endpoint.base_url}/resource/{dataset_id}.json"
        
        # Make request with rate limiting
        await self._apply_rate_limit()
        
        logger.info(f"Querying Socrata: {url}")
        logger.debug(f"Query: {query}")
        
        try:
            start_time = time.time()
            response = await self.client.get(url, params=query)
            query_time = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle both single result and array results
                if isinstance(data, dict):
                    # Aggregated result
                    return {
                        "total_facilities": data.get("facility_count", 0),
                        "total_sqft": data.get("total_sqft", 0),
                        "rows": [data],
                        "query_time_ms": query_time,
                    }
                elif isinstance(data, list):
                    # Array result
                    return {
                        "total_facilities": len(data),
                        "total_sqft": sum(row.get(sqft_field, 0) for row in data if isinstance(row.get(sqft_field), (int, float))),
                        "rows": data,
                        "query_time_ms": query_time,
                    }
                else:
                    raise SocrataProviderError(f"Unexpected response type: {type(data)}")
            
            elif response.status_code == 404:
                raise SocrataProviderError(f"Dataset not found: {dataset_id}")
            
            elif response.status_code == 429:
                raise SocrataProviderError("Rate limited by Socrata API")
            
            else:
                raise SocrataProviderError(
                    f"HTTP {response.status_code}: {response.text}"
                )
        
        except httpx.TimeoutException:
            raise SocrataProviderError(f"Query timeout after {self.TIMEOUT_SECONDS}s")
        except Exception as e:
            raise SocrataProviderError(f"Query failed: {str(e)}")
    
    def _build_soql_query(
        self,
        land_use_field: str,
        land_use_codes: List[str],
        sqft_field: str,
        limit: Optional[int] = None,
    ) -> Dict[str, str]:
        """
        Build SoQL query parameters.
        
        Returns dict suitable for httpx params.
        
        Query pattern:
        $select=COUNT(*) as facility_count, SUM(building_square_feet) as total_sqft
        $where=land_use_code IN ('39')
        """
        
        # Build WHERE clause
        codes_quoted = [f"'{code}'" for code in land_use_codes]
        where_clause = f"{land_use_field} IN ({', '.join(codes_quoted)})"
        
        # Build SELECT clause (aggregated)
        select_clause = f"COUNT(*) as facility_count, SUM({sqft_field}) as total_sqft"
        
        params = {
            "$select": select_clause,
            "$where": where_clause,
        }
        
        if limit:
            params["$limit"] = str(limit)
        
        return params
    
    async def _apply_rate_limit(self):
        """Apply rate limiting between requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            import asyncio
            await asyncio.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()
    
    async def test_connection(self, metro: str) -> bool:
        """
        Test connection to a Socrata endpoint.
        
        Args:
            metro: Metro identifier
        
        Returns:
            True if endpoint is reachable
        """
        if metro.lower() not in SOCRATA_ENDPOINTS:
            return False
        
        endpoint = SOCRATA_ENDPOINTS[metro.lower()]
        
        try:
            await self._apply_rate_limit()
            response = await self.client.get(
                f"{endpoint.base_url}/api/",
                timeout=5
            )
            return response.status_code < 400
        except Exception as e:
            logger.warning(f"Connection test failed for {metro}: {e}")
            return False
    
    def get_endpoint_config(self, metro: str) -> Optional[SocrataEndpoint]:
        """Get endpoint configuration"""
        return SOCRATA_ENDPOINTS.get(metro.lower())
