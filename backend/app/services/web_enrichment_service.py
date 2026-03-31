"""
Web Enrichment Service

Fetches live data from internet sources to enrich the 4 P's framework.

Sources:
- Google Trends → PRODUCT (demand validation)
- Google Places/Reviews → PROMOTION (competitor intelligence)
- Indeed → PLACE (job market)
- Zillow → PRICE (real estate economics)
- News APIs → PRODUCT (market trends)
- BLS/SBA → PLACE (labor stats, business formation)
"""
import os
import logging
import httpx

# Allow nested event loops (required when called from FastAPI async context)
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass  # nest_asyncio not installed, will fail if called from async context
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from functools import lru_cache
import json

logger = logging.getLogger(__name__)

# API Keys from environment
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
SERPAPI_KEY = os.environ.get("SERPAPI_API_KEY")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")


@dataclass
class GoogleTrendsData:
    """Google Trends search interest data."""
    keyword: str
    interest_over_time: List[Dict] = field(default_factory=list)
    related_queries: List[str] = field(default_factory=list)
    trend_direction: str = "stable"  # rising, declining, stable
    interest_score: int = 0  # 0-100
    fetched_at: str = ""


@dataclass
class GooglePlacesData:
    """Google Places competitor and review data."""
    competitors: List[Dict] = field(default_factory=list)
    total_competitors: int = 0
    avg_rating: float = 0.0
    total_reviews: int = 0
    review_sentiment: str = "neutral"  # positive, neutral, negative
    top_keywords: List[str] = field(default_factory=list)
    price_levels: Dict[str, int] = field(default_factory=dict)  # {1: count, 2: count, etc}
    fetched_at: str = ""


@dataclass
class JobMarketData:
    """Indeed/LinkedIn job market data."""
    total_postings: int = 0
    job_titles: List[str] = field(default_factory=list)
    avg_salary_min: int = 0
    avg_salary_max: int = 0
    hiring_companies: List[str] = field(default_factory=list)
    growth_indicator: str = "stable"  # growing, stable, declining
    fetched_at: str = ""


@dataclass
class RealEstateData:
    """Zillow/Redfin real estate data."""
    median_home_value: int = 0
    median_rent: int = 0
    home_value_change_yoy: float = 0.0
    rent_change_yoy: float = 0.0
    days_on_market: int = 0
    inventory_count: int = 0
    market_temperature: str = "neutral"  # hot, neutral, cold
    fetched_at: str = ""


@dataclass
class MarketNewsData:
    """News API market intelligence."""
    articles: List[Dict] = field(default_factory=list)
    sentiment_score: float = 0.0  # -1 to 1
    trending_topics: List[str] = field(default_factory=list)
    news_volume: int = 0
    fetched_at: str = ""


@dataclass
class LaborStatsData:
    """BLS/SBA labor and business stats."""
    unemployment_rate: float = 0.0
    labor_force_participation: float = 0.0
    business_applications: int = 0
    business_formations: int = 0
    industry_employment: Dict[str, int] = field(default_factory=dict)
    fetched_at: str = ""


@dataclass
class WebEnrichmentResult:
    """Complete web enrichment result for 4 P's."""
    city: str
    state: str
    business_type: Optional[str]
    
    # PRODUCT enrichment
    google_trends: Optional[GoogleTrendsData] = None
    market_news: Optional[MarketNewsData] = None
    
    # PRICE enrichment
    real_estate: Optional[RealEstateData] = None
    
    # PLACE enrichment
    job_market: Optional[JobMarketData] = None
    labor_stats: Optional[LaborStatsData] = None
    
    # PROMOTION enrichment
    google_places: Optional[GooglePlacesData] = None
    
    # Metadata
    fetched_at: str = ""
    sources_available: List[str] = field(default_factory=list)
    sources_failed: List[str] = field(default_factory=list)


class WebEnrichmentService:
    """
    Fetches live data from internet sources to enrich market intelligence.
    
    Usage:
        service = WebEnrichmentService()
        result = await service.enrich(city="Atlanta", state="GA", business_type="coffee_shop")
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = timedelta(hours=6)  # Cache for 6 hours
    
    def _cache_key(self, city: str, state: str, business_type: str) -> str:
        return f"{city}:{state}:{business_type}".lower()
    
    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache:
            return False
        cached_at = self._cache[key].get('_cached_at')
        if not cached_at:
            return False
        return datetime.utcnow() - cached_at < self._cache_ttl
    
    async def enrich(
        self,
        city: str,
        state: str,
        business_type: Optional[str] = None,
        skip_cache: bool = False
    ) -> WebEnrichmentResult:
        """
        Fetch all available web enrichment data for a location/business type.
        
        Args:
            city: City name
            state: State code (e.g., "GA")
            business_type: Business category for targeted searches
            skip_cache: Force fresh fetch
        
        Returns:
            WebEnrichmentResult with all available data
        """
        cache_key = self._cache_key(city, state, business_type or "general")
        
        if not skip_cache and self._is_cache_valid(cache_key):
            logger.info(f"[WebEnrich] Cache hit for {city}, {state}")
            return self._cache[cache_key]['data']
        
        logger.info(f"[WebEnrich] Fetching data for {city}, {state} - {business_type}")
        
        result = WebEnrichmentResult(
            city=city,
            state=state,
            business_type=business_type,
            fetched_at=datetime.utcnow().isoformat()
        )
        
        # Fetch all sources in parallel
        import asyncio
        
        tasks = {
            'google_trends': self._fetch_google_trends(city, state, business_type),
            'google_places': self._fetch_google_places(city, state, business_type),
            'job_market': self._fetch_job_market(city, state, business_type),
            'real_estate': self._fetch_real_estate(city, state),
            'market_news': self._fetch_market_news(city, state, business_type),
            'labor_stats': self._fetch_labor_stats(city, state),
        }
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        for (source_name, _), data in zip(tasks.items(), results):
            if isinstance(data, Exception):
                logger.warning(f"[WebEnrich] {source_name} failed: {data}")
                result.sources_failed.append(source_name)
            elif data:
                setattr(result, source_name, data)
                result.sources_available.append(source_name)
        
        # Cache the result
        self._cache[cache_key] = {
            'data': result,
            '_cached_at': datetime.utcnow()
        }
        
        logger.info(f"[WebEnrich] Completed: {len(result.sources_available)} sources, {len(result.sources_failed)} failed")
        return result
    
    async def _fetch_google_trends(
        self,
        city: str,
        state: str,
        business_type: Optional[str]
    ) -> Optional[GoogleTrendsData]:
        """Fetch Google Trends data via SerpAPI."""
        if not SERPAPI_KEY:
            return None
        
        try:
            keyword = business_type or f"business {city}"
            geo = f"US-{state}"
            
            response = await self.client.get(
                "https://serpapi.com/search",
                params={
                    "engine": "google_trends",
                    "q": keyword,
                    "geo": geo,
                    "data_type": "TIMESERIES",
                    "api_key": SERPAPI_KEY
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Parse trends data
            interest_data = data.get("interest_over_time", {}).get("timeline_data", [])
            
            # Calculate trend direction
            if len(interest_data) >= 2:
                recent = sum(d.get("values", [{}])[0].get("extracted_value", 0) for d in interest_data[-4:]) / 4
                older = sum(d.get("values", [{}])[0].get("extracted_value", 0) for d in interest_data[:4]) / 4
                if recent > older * 1.1:
                    trend_direction = "rising"
                elif recent < older * 0.9:
                    trend_direction = "declining"
                else:
                    trend_direction = "stable"
            else:
                trend_direction = "stable"
            
            # Get interest score (most recent value)
            interest_score = 0
            if interest_data:
                interest_score = interest_data[-1].get("values", [{}])[0].get("extracted_value", 0)
            
            # Get related queries
            related = data.get("related_queries", {}).get("rising", [])
            related_queries = [q.get("query", "") for q in related[:10]]
            
            return GoogleTrendsData(
                keyword=keyword,
                interest_over_time=interest_data[-12:],  # Last 12 data points
                related_queries=related_queries,
                trend_direction=trend_direction,
                interest_score=interest_score,
                fetched_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.warning(f"[WebEnrich] Google Trends error: {e}")
            return None
    
    async def _fetch_google_places(
        self,
        city: str,
        state: str,
        business_type: Optional[str]
    ) -> Optional[GooglePlacesData]:
        """Fetch Google Places competitor data."""
        if not GOOGLE_API_KEY:
            # Fallback to SerpAPI Google Maps
            return await self._fetch_google_places_serpapi(city, state, business_type)
        
        try:
            # Text search for competitors
            query = f"{business_type or 'business'} in {city}, {state}"
            
            response = await self.client.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params={
                    "query": query,
                    "key": GOOGLE_API_KEY
                }
            )
            response.raise_for_status()
            data = response.json()
            
            places = data.get("results", [])
            
            competitors = []
            ratings = []
            total_reviews = 0
            price_levels = {}
            
            for place in places[:20]:
                comp = {
                    "name": place.get("name"),
                    "address": place.get("formatted_address"),
                    "rating": place.get("rating", 0),
                    "reviews": place.get("user_ratings_total", 0),
                    "price_level": place.get("price_level"),
                    "types": place.get("types", []),
                    "place_id": place.get("place_id")
                }
                competitors.append(comp)
                
                if place.get("rating"):
                    ratings.append(place["rating"])
                total_reviews += place.get("user_ratings_total", 0)
                
                pl = place.get("price_level")
                if pl:
                    price_levels[pl] = price_levels.get(pl, 0) + 1
            
            avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
            
            # Determine sentiment from avg rating
            if avg_rating >= 4.2:
                sentiment = "positive"
            elif avg_rating >= 3.5:
                sentiment = "neutral"
            else:
                sentiment = "negative"
            
            return GooglePlacesData(
                competitors=competitors,
                total_competitors=len(places),
                avg_rating=round(avg_rating, 2),
                total_reviews=total_reviews,
                review_sentiment=sentiment,
                price_levels=price_levels,
                fetched_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.warning(f"[WebEnrich] Google Places error: {e}")
            return None
    
    async def _fetch_google_places_serpapi(
        self,
        city: str,
        state: str,
        business_type: Optional[str]
    ) -> Optional[GooglePlacesData]:
        """Fallback: Fetch Google Places via SerpAPI."""
        if not SERPAPI_KEY:
            return None
        
        try:
            query = f"{business_type or 'business'} in {city}, {state}"
            
            response = await self.client.get(
                "https://serpapi.com/search",
                params={
                    "engine": "google_maps",
                    "q": query,
                    "type": "search",
                    "api_key": SERPAPI_KEY
                }
            )
            response.raise_for_status()
            data = response.json()
            
            places = data.get("local_results", [])
            
            competitors = []
            ratings = []
            total_reviews = 0
            
            for place in places[:20]:
                comp = {
                    "name": place.get("title"),
                    "address": place.get("address"),
                    "rating": place.get("rating", 0),
                    "reviews": place.get("reviews", 0),
                    "price": place.get("price"),
                    "type": place.get("type"),
                    "place_id": place.get("place_id")
                }
                competitors.append(comp)
                
                if place.get("rating"):
                    ratings.append(place["rating"])
                total_reviews += place.get("reviews", 0)
            
            avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
            
            sentiment = "positive" if avg_rating >= 4.2 else "neutral" if avg_rating >= 3.5 else "negative"
            
            return GooglePlacesData(
                competitors=competitors,
                total_competitors=len(places),
                avg_rating=round(avg_rating, 2),
                total_reviews=total_reviews,
                review_sentiment=sentiment,
                fetched_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.warning(f"[WebEnrich] SerpAPI Google Maps error: {e}")
            return None
    
    async def _fetch_job_market(
        self,
        city: str,
        state: str,
        business_type: Optional[str]
    ) -> Optional[JobMarketData]:
        """Fetch job market data via Indeed/LinkedIn APIs or SerpAPI."""
        if not SERPAPI_KEY:
            return None
        
        try:
            query = business_type or "jobs"
            location = f"{city}, {state}"
            
            response = await self.client.get(
                "https://serpapi.com/search",
                params={
                    "engine": "google_jobs",
                    "q": query,
                    "location": location,
                    "api_key": SERPAPI_KEY
                }
            )
            response.raise_for_status()
            data = response.json()
            
            jobs = data.get("jobs_results", [])
            
            job_titles = []
            companies = []
            salaries_min = []
            salaries_max = []
            
            for job in jobs[:20]:
                job_titles.append(job.get("title", ""))
                companies.append(job.get("company_name", ""))
                
                # Parse salary if available
                salary = job.get("detected_extensions", {})
                if salary.get("salary"):
                    # Try to extract min/max from salary string
                    pass  # Complex parsing, skip for now
            
            # Determine growth based on job count
            total = len(jobs)
            growth = "growing" if total > 15 else "stable" if total > 5 else "limited"
            
            return JobMarketData(
                total_postings=total,
                job_titles=list(set(job_titles))[:10],
                hiring_companies=list(set(companies))[:10],
                growth_indicator=growth,
                fetched_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.warning(f"[WebEnrich] Job market error: {e}")
            return None
    
    async def _fetch_real_estate(
        self,
        city: str,
        state: str
    ) -> Optional[RealEstateData]:
        """Fetch real estate data via Zillow/Redfin APIs or RapidAPI."""
        if not RAPIDAPI_KEY:
            return None
        
        try:
            # Try Zillow via RapidAPI
            response = await self.client.get(
                "https://zillow-com1.p.rapidapi.com/locationSuggestions",
                params={"q": f"{city}, {state}"},
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"
                }
            )
            response.raise_for_status()
            locations = response.json().get("results", [])
            
            if not locations:
                return None
            
            region_id = locations[0].get("metaData", {}).get("regionId")
            if not region_id:
                return None
            
            # Get market data
            response = await self.client.get(
                "https://zillow-com1.p.rapidapi.com/regionChildren",
                params={"regionId": region_id},
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"
                }
            )
            response.raise_for_status()
            market_data = response.json()
            
            # Extract metrics (structure varies)
            home_value = market_data.get("regionStats", {}).get("medianListingPrice", 0)
            
            return RealEstateData(
                median_home_value=home_value,
                fetched_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.warning(f"[WebEnrich] Real estate error: {e}")
            return None
    
    async def _fetch_market_news(
        self,
        city: str,
        state: str,
        business_type: Optional[str]
    ) -> Optional[MarketNewsData]:
        """Fetch market news via NewsAPI or Google News."""
        # Try NewsAPI first
        if NEWS_API_KEY:
            try:
                query = f"{business_type or 'business'} {city}"
                
                response = await self.client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": query,
                        "sortBy": "relevancy",
                        "pageSize": 10,
                        "apiKey": NEWS_API_KEY
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                articles = []
                for article in data.get("articles", [])[:10]:
                    articles.append({
                        "title": article.get("title"),
                        "source": article.get("source", {}).get("name"),
                        "published": article.get("publishedAt"),
                        "url": article.get("url")
                    })
                
                return MarketNewsData(
                    articles=articles,
                    news_volume=data.get("totalResults", 0),
                    fetched_at=datetime.utcnow().isoformat()
                )
                
            except Exception as e:
                logger.warning(f"[WebEnrich] NewsAPI error: {e}")
        
        # Fallback to SerpAPI Google News
        if SERPAPI_KEY:
            try:
                query = f"{business_type or 'business'} {city} {state}"
                
                response = await self.client.get(
                    "https://serpapi.com/search",
                    params={
                        "engine": "google_news",
                        "q": query,
                        "api_key": SERPAPI_KEY
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                articles = []
                for item in data.get("news_results", [])[:10]:
                    articles.append({
                        "title": item.get("title"),
                        "source": item.get("source", {}).get("name"),
                        "published": item.get("date"),
                        "url": item.get("link")
                    })
                
                return MarketNewsData(
                    articles=articles,
                    news_volume=len(articles),
                    fetched_at=datetime.utcnow().isoformat()
                )
                
            except Exception as e:
                logger.warning(f"[WebEnrich] SerpAPI News error: {e}")
        
        return None
    
    async def _fetch_labor_stats(
        self,
        city: str,
        state: str
    ) -> Optional[LaborStatsData]:
        """Fetch BLS labor statistics."""
        # BLS API is free but requires series IDs
        # For now, return None - can implement with proper series mapping
        try:
            # BLS API endpoint
            # Would need state-specific series IDs for unemployment, labor force, etc.
            # Example series: LASST010000000000003 (Alabama unemployment)
            
            # This requires a mapping of state codes to BLS series IDs
            # For now, return None
            return None
            
        except Exception as e:
            logger.warning(f"[WebEnrich] BLS error: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
_web_enrichment_service: Optional[WebEnrichmentService] = None


def get_web_enrichment_service() -> WebEnrichmentService:
    """Get or create the web enrichment service singleton."""
    global _web_enrichment_service
    if _web_enrichment_service is None:
        _web_enrichment_service = WebEnrichmentService()
    return _web_enrichment_service


async def enrich_with_web_data(
    city: str,
    state: str,
    business_type: Optional[str] = None
) -> WebEnrichmentResult:
    """Convenience function to fetch web enrichment."""
    service = get_web_enrichment_service()
    return await service.enrich(city, state, business_type)


def enrich_with_web_data_sync(
    city: str,
    state: str,
    business_type: Optional[str] = None
) -> WebEnrichmentResult:
    """Synchronous wrapper for web enrichment that works inside an async event loop."""
    import asyncio
    import concurrent.futures

    async def _run():
        service = WebEnrichmentService()
        try:
            return await service.enrich(city, state, business_type)
        finally:
            await service.close()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, _run())
            return future.result(timeout=45)
    else:
        return asyncio.run(_run())
