"""
SerpAPI Fallback Provider

Fallback data source for metros not covered by Socrata or county assessor APIs.
Uses SerpAPI to search for facilities and estimate supply metrics.

This provider is used when:
- Primary Socrata/assessor endpoints are not available
- A metro is not configured in land_use_mapping
- Primary data source fails or returns insufficient results

Data quality: Lower confidence (0.60) due to web scraping and estimation.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
import httpx

from app.services.municipal_data.schemas import Parcel

logger = logging.getLogger(__name__)


class SerpAPIFallbackProvider:
    """
    Fallback provider using SerpAPI to discover facilities.
    
    Limitations:
    - No direct sq ft data (estimated from typical facility sizes)
    - Based on web search, not authoritative government data
    - Lower confidence scores (0.60)
    - May be incomplete
    """
    
    # Typical facility sizes by industry (in sq ft)
    TYPICAL_SIZES = {
        "self-storage": {
            "small": 5_000,      # Very small unit
            "medium": 20_000,    # Standard facility
            "large": 50_000,     # Large regional facility
            "default": 20_000,   # Use this for unknown
        },
        "restaurant": {
            "small": 1_500,      # Cafe/sandwich shop
            "medium": 3_500,     # Standard restaurant
            "large": 8_000,      # Large dining
            "default": 3_500,
        },
        "fitness": {
            "small": 3_000,      # Boutique studio
            "medium": 10_000,    # Standard gym
            "large": 20_000,     # Large facility
            "default": 10_000,
        },
        "gas_station": {
            "small": 2_000,
            "medium": 3_500,
            "large": 5_000,
            "default": 3_500,
        },
    }
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        """
        Initialize SerpAPI fallback provider.
        
        Args:
            api_key: SerpAPI key (if None, provider is disabled)
            timeout: HTTP timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://serpapi.com/search"
        self.enabled = bool(api_key)
        
        if not self.enabled:
            logger.warning(
                "SerpAPI fallback provider disabled: no API key configured. "
                "Only Socrata/county assessor data will be used."
            )
    
    async def query(
        self,
        metro: str,
        state: str,
        industry: str,
        limit: int = 100,
    ) -> List[Parcel]:
        """
        Query SerpAPI for facilities.
        
        Args:
            metro: Metro name (e.g., "Miami")
            state: State code (e.g., "FL")
            industry: Industry code (e.g., "self-storage")
            limit: Maximum results to return
        
        Returns:
            List of Parcel objects with estimated data
        """
        if not self.enabled:
            logger.warning(f"SerpAPI fallback disabled for {metro}, {state}")
            return []
        
        try:
            results = await self._search_facilities(metro, state, industry)
            
            # Convert search results to Parcel objects
            parcels = []
            for result in results[:limit]:
                parcel = self._convert_to_parcel(result, industry)
                if parcel:
                    parcels.append(parcel)
            
            logger.info(
                f"SerpAPI fallback: found {len(parcels)} facilities in "
                f"{metro}, {state} for {industry}"
            )
            
            return parcels
        
        except Exception as e:
            logger.error(f"SerpAPI fallback query failed: {e}")
            return []
    
    async def _search_facilities(
        self,
        metro: str,
        state: str,
        industry: str,
    ) -> List[Dict[str, Any]]:
        """
        Search SerpAPI for facilities in a metro.
        
        Args:
            metro: Metro name
            state: State code
            industry: Industry code
        
        Returns:
            List of search results
        """
        # Build search query based on industry
        search_queries = {
            "self-storage": f"self storage facilities in {metro}, {state}",
            "restaurant": f"restaurants in {metro}, {state}",
            "fitness": f"fitness gyms in {metro}, {state}",
            "gas_station": f"gas stations in {metro}, {state}",
            "pharmacy": f"pharmacies in {metro}, {state}",
            "grocery": f"grocery stores in {metro}, {state}",
        }
        
        query = search_queries.get(industry, f"{industry} in {metro}, {state}")
        
        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": "google",
            "type": "search",
            "num": 100,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Extract organic results
                results = data.get("organic_results", [])
                logger.debug(f"SerpAPI returned {len(results)} results")
                
                return results
        
        except httpx.HTTPError as e:
            logger.error(f"SerpAPI HTTP error: {e}")
            return []
        except Exception as e:
            logger.error(f"SerpAPI query error: {e}")
            return []
    
    def _convert_to_parcel(self, result: Dict[str, Any], industry: str) -> Optional[Parcel]:
        """
        Convert SerpAPI search result to Parcel object.
        
        Args:
            result: SerpAPI result dict
            industry: Industry code for sizing estimation
        
        Returns:
            Parcel object or None if conversion fails
        """
        try:
            title = result.get("title", "")
            position = result.get("position", 0)
            
            if not title:
                return None
            
            # Estimate building sq ft based on industry and position
            # Higher position = likely larger facility
            typical_size = self.TYPICAL_SIZES.get(industry, {}).get("default", 5_000)
            
            # Adjust size estimate based on position (top results often larger)
            size_multiplier = 1.0 + (0.1 * (position % 5))
            estimated_sqft = int(typical_size * size_multiplier)
            
            parcel = Parcel(
                facility_name=title,
                address=result.get("link", ""),
                building_sqft=estimated_sqft,
                land_sqft=estimated_sqft * 1.5,  # Estimate
                parcel_id=f"serpapi_{position}_{hash(title) % 1000000}",
                source="serpapi_fallback",
                data_quality="estimated",
                confidence=0.60,  # Lower confidence for fallback
            )
            
            return parcel
        
        except Exception as e:
            logger.warning(f"Failed to convert SerpAPI result: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get provider status"""
        return {
            "provider": "serpapi_fallback",
            "enabled": self.enabled,
            "timeout": self.timeout,
            "api_key_configured": bool(self.api_key),
            "confidence": 0.60,
            "data_quality": "estimated",
        }
