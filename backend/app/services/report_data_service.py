"""
Report Data Service

Aggregates all 4 P's data for report generation according to REPORT_DATA_FRAMEWORK.md.

Data Sources:
- 🔵 OppGrid (Primary): opportunities, detected_trends, market_growth_trajectories, 
                        service_area_boundaries, success_patterns, traffic_roads, 
                        google_maps_businesses, census_*, location_analysis_cache
- 🟡 JediRE (Enrichment): demand signals, market economics, absorption rates, supply pipeline
- 🌐 Web (Live): Google Trends, Google Places/Reviews, Indeed jobs, Zillow, News APIs, BLS
"""
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta

# OppGrid models
from app.models.opportunity import Opportunity
from app.models.detected_trend import DetectedTrend
from app.models.census_demographics import (
    MarketGrowthTrajectory, 
    CensusPopulationEstimate,
    CensusMigrationFlow,
    ServiceAreaBoundary
)
from app.models.success_pattern import SuccessPattern
from app.models.google_scraping import GoogleMapsBusiness
from app.models.location_analysis_cache import LocationAnalysisCache
from app.models.idea_validation import IdeaValidation

# JediRE client for enrichment
from app.services.jedire_client import get_jedire_client, get_full_market_intelligence_sync

logger = logging.getLogger(__name__)


@dataclass
class ProductData:
    """PRODUCT: Demand Validation"""
    opportunity_score: Optional[float] = None
    pain_intensity: Optional[float] = None
    urgency_level: Optional[str] = None
    target_audience: Optional[str] = None
    trend_strength: Optional[float] = None
    confidence_score: Optional[float] = None
    opportunities_count: Optional[int] = None
    signal_density: Optional[float] = None
    validation_confidence: Optional[float] = None
    # JediRE enrichment
    amenity_demand: Optional[List[Dict]] = None
    unmet_demand: Optional[List[Dict]] = None
    # Web enrichment (Google Trends + News)
    google_trends_interest: Optional[int] = None  # 0-100
    google_trends_direction: Optional[str] = None  # rising, stable, declining
    related_search_queries: Optional[List[str]] = None
    market_news: Optional[List[Dict]] = None
    news_sentiment: Optional[float] = None  # -1 to 1


@dataclass
class PriceData:
    """PRICE: Economics"""
    market_size_estimate: Optional[str] = None
    addressable_market_value: Optional[float] = None
    revenue_benchmark: Optional[float] = None
    capital_required: Optional[float] = None
    median_income: Optional[int] = None
    income_growth_rate: Optional[float] = None
    income_differential: Optional[float] = None
    # JediRE enrichment
    median_rent: Optional[int] = None
    spending_power_index: Optional[int] = None
    rent_by_bedroom: Optional[Dict[str, int]] = None
    # Web enrichment (Zillow/Redfin)
    zillow_home_value: Optional[int] = None
    zillow_rent_estimate: Optional[int] = None
    home_value_change_yoy: Optional[float] = None
    real_estate_market_temp: Optional[str] = None  # hot, neutral, cold


@dataclass
class PlaceData:
    """PLACE: Location Intelligence"""
    growth_score: Optional[float] = None
    growth_category: Optional[str] = None
    population_growth_rate: Optional[float] = None
    job_growth_rate: Optional[float] = None
    business_formation_rate: Optional[float] = None
    net_migration_rate: Optional[float] = None
    traffic_aadt: Optional[int] = None
    site_recommendations: Optional[List[Dict]] = None
    claude_summary: Optional[str] = None
    population: Optional[int] = None
    total_households: Optional[int] = None
    # Location coordinates
    center_lat: Optional[float] = None
    center_lng: Optional[float] = None
    # Map URLs
    static_map_url: Optional[str] = None  # Map with 3mi/5mi radius
    # JediRE enrichment
    vacancy_rate: Optional[float] = None
    absorption_rate: Optional[float] = None
    supply_pipeline: Optional[List[Dict]] = None
    # JediRE growth indices (leading indicators)
    traffic_growth_index: Optional[float] = None  # (Realtime - Historical) / Historical × 100
    search_growth_index: Optional[float] = None   # Similar for online search volume
    # Web enrichment (Indeed/LinkedIn + BLS)
    job_postings_count: Optional[int] = None
    job_market_growth: Optional[str] = None  # growing, stable, limited
    top_hiring_companies: Optional[List[str]] = None
    unemployment_rate: Optional[float] = None
    labor_force_participation: Optional[float] = None


@dataclass
class PromotionData:
    """PROMOTION: Competition & Reach"""
    competition_level: Optional[str] = None
    competitive_advantages: Optional[List[str]] = None
    key_risks: Optional[List[str]] = None
    business_model_suggestions: Optional[List[str]] = None
    # Web enrichment (Google Places/Reviews)
    google_places_competitors: Optional[List[Dict]] = None
    google_avg_rating: Optional[float] = None
    google_total_reviews: Optional[int] = None
    google_review_sentiment: Optional[str] = None  # positive, neutral, negative
    google_price_levels: Optional[Dict] = None
    success_factors: Optional[List[str]] = None
    failure_points: Optional[List[str]] = None
    competitor_count: Optional[int] = None
    avg_competitor_rating: Optional[float] = None
    # JediRE enrichment
    search_trends: Optional[Dict] = None


@dataclass
class PillarQuality:
    """Quality metrics for a single P (pillar)"""
    name: str  # product, price, place, promotion
    completeness: float = 0.0  # 0-1, percentage of key fields filled
    confidence: float = 0.0  # 0-1, reliability of available data
    fields_filled: int = 0
    fields_total: int = 0
    primary_sources: int = 0  # OppGrid fields
    enrichment_sources: int = 0  # JediRE fields
    freshness_score: float = 1.0  # 0-1, 1.0 = fresh
    warnings: List[str] = field(default_factory=list)


@dataclass
class DataQuality:
    """Data quality metrics"""
    completeness: float = 0.0  # 0-1 overall
    confidence: float = 0.0  # 0-1 overall
    oppgrid_fields_filled: int = 0
    jedire_enrichment_available: bool = False
    stale_data_warnings: List[str] = field(default_factory=list)
    
    # Per-pillar breakdown
    product_quality: Optional[PillarQuality] = None
    price_quality: Optional[PillarQuality] = None
    place_quality: Optional[PillarQuality] = None
    promotion_quality: Optional[PillarQuality] = None
    
    # Report-specific
    report_readiness: float = 0.0  # 0-1, is data sufficient for this report type
    weakest_pillar: Optional[str] = None  # which P needs more data
    recommended_actions: List[str] = field(default_factory=list)  # what to fetch/improve
    
    # Source breakdown
    primary_data_pct: float = 0.0  # % from OppGrid
    enrichment_data_pct: float = 0.0  # % from JediRE
    
    # Freshness
    avg_freshness: float = 1.0  # 0-1
    oldest_data_age_days: Optional[int] = None


@dataclass
class ReportDataContext:
    """Complete data context for report generation"""
    city: str
    state: str
    business_type: Optional[str]
    report_type: str
    product: ProductData
    price: PriceData
    place: PlaceData
    promotion: PromotionData
    data_quality: DataQuality
    fetched_at: str


class ReportDataService:
    """
    Aggregates all 4 P's data for report generation.
    
    Usage:
        service = ReportDataService(db)
        context = service.get_report_data(
            city="Atlanta",
            state="GA", 
            business_type="coffee_shop",
            report_type="market_analysis"
        )
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.jedire_client = get_jedire_client()
    
    def get_report_data(
        self,
        city: str,
        state: str,
        business_type: Optional[str] = None,
        report_type: str = "market_analysis",
        opportunity_id: Optional[int] = None
    ) -> ReportDataContext:
        """
        Fetch all data for a report.
        
        Args:
            city: City name
            state: State code (e.g., "GA")
            business_type: Business category for filtering
            report_type: Type of report being generated
            opportunity_id: Specific opportunity ID if available
        
        Returns:
            ReportDataContext with all 4 P's data
        """
        logger.info(f"[ReportData] Fetching data for {city}, {state} - {report_type}")
        
        # Fetch OppGrid data (primary)
        product = self._fetch_product_data(city, state, business_type, opportunity_id)
        price = self._fetch_price_data(city, state, business_type)
        place = self._fetch_place_data(city, state)
        promotion = self._fetch_promotion_data(city, state, business_type, opportunity_id)
        
        # Fetch JediRE enrichment
        self._enrich_with_jedire(city, state, business_type, product, price, place, promotion)
        
        # Fetch Web enrichment (Google Trends, Places, Jobs, Zillow, News)
        self._enrich_with_web(city, state, business_type, product, price, place, promotion)
        
        # Calculate data quality
        data_quality = self._calculate_data_quality(product, price, place, promotion, report_type)
        
        context = ReportDataContext(
            city=city,
            state=state,
            business_type=business_type,
            report_type=report_type,
            product=product,
            price=price,
            place=place,
            promotion=promotion,
            data_quality=data_quality,
            fetched_at=datetime.utcnow().isoformat()
        )
        
        logger.info(f"[ReportData] Data quality: {data_quality.completeness:.0%} complete")
        return context
    
    def _fetch_product_data(
        self, 
        city: str, 
        state: str, 
        business_type: Optional[str],
        opportunity_id: Optional[int]
    ) -> ProductData:
        """Fetch PRODUCT data from OppGrid."""
        data = ProductData()
        
        # Get specific opportunity if ID provided
        if opportunity_id:
            opp = self.db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
            if opp:
                data.opportunity_score = opp.ai_opportunity_score
                data.pain_intensity = opp.ai_pain_intensity
                data.urgency_level = opp.ai_urgency_level
                data.target_audience = opp.ai_target_audience
        
        # Get aggregated opportunity data for location
        opps = self.db.query(Opportunity).filter(
            func.lower(Opportunity.city) == city.lower(),
            Opportunity.status == 'active'
        )
        if business_type:
            opps = opps.filter(func.lower(Opportunity.category) == business_type.lower())
        opps = opps.all()
        
        if opps and not opportunity_id:
            scores = [o.ai_opportunity_score for o in opps if o.ai_opportunity_score]
            pains = [o.ai_pain_intensity for o in opps if o.ai_pain_intensity]
            data.opportunity_score = sum(scores) / len(scores) if scores else None
            data.pain_intensity = sum(pains) / len(pains) if pains else None
            data.opportunities_count = len(opps)
        
        # Get detected trends
        trends = self.db.query(DetectedTrend).filter(
            DetectedTrend.category == business_type if business_type else True
        ).order_by(DetectedTrend.trend_strength.desc()).limit(5).all()
        
        if trends:
            data.trend_strength = trends[0].trend_strength
            data.confidence_score = trends[0].confidence_score
        
        # Get signal density from service area
        service_area = self.db.query(ServiceAreaBoundary).filter(
            func.lower(ServiceAreaBoundary.included_cities.cast(str)).contains(city.lower())
        ).first()
        
        if service_area:
            data.signal_density = service_area.signal_density
        
        # Get validation confidence
        validations = self.db.query(IdeaValidation).filter(
            IdeaValidation.category == business_type if business_type else True
        ).order_by(IdeaValidation.created_at.desc()).limit(10).all()
        
        if validations:
            confidences = [v.validation_confidence for v in validations if v.validation_confidence]
            data.validation_confidence = sum(confidences) / len(confidences) if confidences else None
        
        return data
    
    def _fetch_price_data(
        self, 
        city: str, 
        state: str, 
        business_type: Optional[str]
    ) -> PriceData:
        """Fetch PRICE data from OppGrid."""
        data = PriceData()
        
        # Get market size from opportunities
        opps = self.db.query(Opportunity).filter(
            func.lower(Opportunity.city) == city.lower(),
            Opportunity.ai_market_size_estimate.isnot(None)
        ).limit(10).all()
        
        if opps:
            # Take most common market size estimate
            sizes = [o.ai_market_size_estimate for o in opps if o.ai_market_size_estimate]
            if sizes:
                data.market_size_estimate = max(set(sizes), key=sizes.count)
        
        # Get service area TAM
        service_area = self.db.query(ServiceAreaBoundary).filter(
            func.lower(ServiceAreaBoundary.included_cities.cast(str)).contains(city.lower())
        ).first()
        
        if service_area:
            data.addressable_market_value = float(service_area.addressable_market_value) if service_area.addressable_market_value else None
        
        # Get success pattern benchmarks
        patterns = self.db.query(SuccessPattern).filter(
            SuccessPattern.opportunity_type == business_type if business_type else True
        ).all()
        
        if patterns:
            revenues = [float(p.revenue_generated) for p in patterns if p.revenue_generated]
            capitals = [float(p.capital_spent) for p in patterns if p.capital_spent]
            data.revenue_benchmark = sum(revenues) / len(revenues) if revenues else None
            data.capital_required = sum(capitals) / len(capitals) if capitals else None
        
        # Get census income data
        census = self.db.query(CensusPopulationEstimate).filter(
            func.lower(CensusPopulationEstimate.geography_name).contains(city.lower())
        ).order_by(CensusPopulationEstimate.year.desc()).first()
        
        if census:
            data.median_income = census.median_income
        
        # Get income growth from trajectories
        trajectory = self.db.query(MarketGrowthTrajectory).filter(
            func.lower(MarketGrowthTrajectory.city) == city.lower()
        ).first()
        
        if trajectory:
            data.income_growth_rate = float(trajectory.income_growth_rate) if trajectory.income_growth_rate else None
        
        # Get migration income differential
        migration = self.db.query(CensusMigrationFlow).filter(
            func.lower(CensusMigrationFlow.destination_name).contains(city.lower())
        ).first()
        
        if migration:
            data.income_differential = migration.income_differential
        
        return data
    
    def _fetch_place_data(self, city: str, state: str) -> PlaceData:
        """Fetch PLACE data from OppGrid."""
        data = PlaceData()
        
        # Get growth trajectory
        trajectory = self.db.query(MarketGrowthTrajectory).filter(
            func.lower(MarketGrowthTrajectory.city) == city.lower(),
            MarketGrowthTrajectory.is_active == True
        ).first()
        
        if trajectory:
            data.growth_score = float(trajectory.growth_score) if trajectory.growth_score else None
            data.growth_category = trajectory.growth_category.value if trajectory.growth_category else None
            data.population_growth_rate = float(trajectory.population_growth_rate) if trajectory.population_growth_rate else None
            data.job_growth_rate = float(trajectory.job_growth_rate) if trajectory.job_growth_rate else None
            data.business_formation_rate = float(trajectory.business_formation_rate) if trajectory.business_formation_rate else None
            data.net_migration_rate = float(trajectory.net_migration_rate) if trajectory.net_migration_rate else None
        
        # Get traffic data (simplified - would need geo query in production)
        # For now, get average AADT for the city
        try:
            from app.models.traffic_road import TrafficRoad
            traffic = self.db.query(func.avg(TrafficRoad.aadt)).filter(
                func.lower(TrafficRoad.county).contains(city.lower())
            ).scalar()
            if traffic:
                data.traffic_aadt = int(traffic)
        except Exception:
            pass  # Traffic table may not exist
        
        # Get location analysis cache
        cache = self.db.query(LocationAnalysisCache).filter(
            func.lower(LocationAnalysisCache.city) == city.lower()
        ).order_by(LocationAnalysisCache.updated_at.desc()).first()
        
        if cache:
            data.site_recommendations = cache.site_recommendations
            data.claude_summary = cache.claude_summary
        
        # Get service area population and coordinates
        service_area = self.db.query(ServiceAreaBoundary).filter(
            func.lower(ServiceAreaBoundary.included_cities.cast(str)).contains(city.lower())
        ).first()
        
        if service_area:
            data.population = service_area.total_population
            data.total_households = service_area.total_households
            data.center_lat = service_area.center_latitude
            data.center_lng = service_area.center_longitude
        
        # Fallback to census
        if not data.population:
            census = self.db.query(CensusPopulationEstimate).filter(
                func.lower(CensusPopulationEstimate.geography_name).contains(city.lower())
            ).order_by(CensusPopulationEstimate.year.desc()).first()
            if census:
                data.population = census.population
        
        # Generate static map with radius circles if we have coordinates
        if data.center_lat and data.center_lng:
            try:
                from app.services.report_generator import build_static_map_with_radius
                data.static_map_url = build_static_map_with_radius(
                    center_lng=data.center_lng,
                    center_lat=data.center_lat,
                    radii=[3, 5],  # 3 and 5 mile radius
                    recommended_sites=data.site_recommendations
                )
            except Exception as e:
                logger.warning(f"[ReportData] Could not generate static map: {e}")
        
        return data
    
    def _fetch_promotion_data(
        self, 
        city: str, 
        state: str, 
        business_type: Optional[str],
        opportunity_id: Optional[int]
    ) -> PromotionData:
        """Fetch PROMOTION data from OppGrid."""
        data = PromotionData()
        
        # Get opportunity-level competition data
        if opportunity_id:
            opp = self.db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
            if opp:
                data.competition_level = opp.ai_competition_level
                data.competitive_advantages = self._parse_json_field(opp.ai_competitive_advantages)
                data.key_risks = self._parse_json_field(opp.ai_key_risks)
                data.business_model_suggestions = self._parse_json_field(opp.ai_business_model_suggestions)
        
        # Get success patterns
        patterns = self.db.query(SuccessPattern).filter(
            SuccessPattern.opportunity_type == business_type if business_type else True
        ).all()
        
        if patterns:
            all_success = []
            all_failures = []
            for p in patterns:
                all_success.extend(self._parse_json_field(p.success_factors) or [])
                all_failures.extend(self._parse_json_field(p.failure_points) or [])
            data.success_factors = list(set(all_success))[:10] if all_success else None
            data.failure_points = list(set(all_failures))[:10] if all_failures else None
        
        # Get competitor data from Google Maps
        competitors = self.db.query(GoogleMapsBusiness).filter(
            GoogleMapsBusiness.types.contains([business_type]) if business_type else True,
            GoogleMapsBusiness.is_active == True
        ).limit(50).all()
        
        if competitors:
            data.competitor_count = len(competitors)
            ratings = [c.rating for c in competitors if c.rating]
            data.avg_competitor_rating = sum(ratings) / len(ratings) if ratings else None
        
        return data
    
    def _enrich_with_jedire(
        self,
        city: str,
        state: str,
        business_type: Optional[str],
        product: ProductData,
        price: PriceData,
        place: PlaceData,
        promotion: PromotionData
    ) -> None:
        """Enrich data with JediRE market intelligence."""
        try:
            jedire_data = get_full_market_intelligence_sync(city, state, business_type)
            
            if not jedire_data.get('has_data'):
                logger.info(f"[ReportData] No JediRE data available for {city}, {state}")
                return
            
            # Enrich PRODUCT
            if jedire_data.get('product'):
                product.amenity_demand = jedire_data['product'].get('demand_signals')
            
            # Enrich PRICE
            if jedire_data.get('price'):
                price.median_rent = jedire_data['price'].get('median_rent')
                price.spending_power_index = jedire_data['price'].get('spending_power_index')
                price.rent_by_bedroom = jedire_data['price'].get('rent_by_bedroom')
            
            # Enrich PLACE
            if jedire_data.get('place'):
                place.vacancy_rate = jedire_data['place'].get('vacancy_rate')
                place.absorption_rate = jedire_data['place'].get('monthly_absorption_rate')
            
            # Fetch growth indices (leading indicators)
            try:
                growth_indices = self.jedire_client.get_growth_indices_sync(city, state)
                if growth_indices:
                    place.traffic_growth_index = growth_indices.get('traffic_growth_index')
                    place.search_growth_index = growth_indices.get('search_growth_index')
                    logger.info(f"[ReportData] Growth indices: traffic={place.traffic_growth_index}, search={place.search_growth_index}")
            except Exception as e:
                logger.debug(f"[ReportData] Growth indices not available: {e}")
            
            logger.info(f"[ReportData] JediRE enrichment applied for {city}, {state}")
            
        except Exception as e:
            logger.warning(f"[ReportData] JediRE enrichment failed: {e}")
    
    def _enrich_with_web(
        self,
        city: str,
        state: str,
        business_type: Optional[str],
        product: ProductData,
        price: PriceData,
        place: PlaceData,
        promotion: PromotionData
    ) -> None:
        """Enrich data with live web sources (Google, Zillow, Indeed, News)."""
        try:
            from app.services.web_enrichment_service import enrich_with_web_data_sync
            
            web_data = enrich_with_web_data_sync(city, state, business_type)
            
            if not web_data.sources_available:
                logger.info(f"[ReportData] No web enrichment available for {city}, {state}")
                return
            
            # Enrich PRODUCT with Google Trends + News
            if web_data.google_trends:
                product.google_trends_interest = web_data.google_trends.interest_score
                product.google_trends_direction = web_data.google_trends.trend_direction
                product.related_search_queries = web_data.google_trends.related_queries
            
            if web_data.market_news:
                product.market_news = web_data.market_news.articles
                product.news_sentiment = web_data.market_news.sentiment_score
            
            # Enrich PRICE with Zillow/Redfin
            if web_data.real_estate:
                price.zillow_home_value = web_data.real_estate.median_home_value
                price.zillow_rent_estimate = web_data.real_estate.median_rent
                price.home_value_change_yoy = web_data.real_estate.home_value_change_yoy
                price.real_estate_market_temp = web_data.real_estate.market_temperature
            
            # Enrich PLACE with Job Market + Labor Stats
            if web_data.job_market:
                place.job_postings_count = web_data.job_market.total_postings
                place.job_market_growth = web_data.job_market.growth_indicator
                place.top_hiring_companies = web_data.job_market.hiring_companies
            
            if web_data.labor_stats:
                place.unemployment_rate = web_data.labor_stats.unemployment_rate
                place.labor_force_participation = web_data.labor_stats.labor_force_participation
            
            # Enrich PROMOTION with Google Places/Reviews
            if web_data.google_places:
                promotion.google_places_competitors = web_data.google_places.competitors
                promotion.google_avg_rating = web_data.google_places.avg_rating
                promotion.google_total_reviews = web_data.google_places.total_reviews
                promotion.google_review_sentiment = web_data.google_places.review_sentiment
                promotion.google_price_levels = web_data.google_places.price_levels
                
                # Update competitor count if we got more from Google
                if web_data.google_places.total_competitors > (promotion.competitor_count or 0):
                    promotion.competitor_count = web_data.google_places.total_competitors
                
                # Update avg rating if not already set
                if not promotion.avg_competitor_rating and web_data.google_places.avg_rating:
                    promotion.avg_competitor_rating = web_data.google_places.avg_rating
            
            logger.info(f"[ReportData] Web enrichment applied: {', '.join(web_data.sources_available)}")
            
        except Exception as e:
            logger.warning(f"[ReportData] Web enrichment failed: {e}")
    
    def _calculate_data_quality(
        self,
        product: ProductData,
        price: PriceData,
        place: PlaceData,
        promotion: PromotionData,
        report_type: str = "market_analysis"
    ) -> DataQuality:
        """
        Calculate comprehensive data quality metrics.
        
        Scoring Methodology:
        - Completeness: % of key fields filled for each pillar
        - Confidence: weighted by data source (OppGrid=1.0, JediRE=0.8) and recency
        - Freshness: penalize stale data (>30 days = warning, >90 days = critical)
        - Report Readiness: weighted by report type requirements
        """
        quality = DataQuality()
        
        # Define key fields per pillar (primary = OppGrid, enrichment = JediRE + Web)
        pillar_fields = {
            'product': {
                'primary': ['opportunity_score', 'pain_intensity', 'urgency_level', 
                           'trend_strength', 'confidence_score', 'signal_density', 
                           'validation_confidence', 'opportunities_count'],
                'enrichment': ['amenity_demand', 'unmet_demand',
                              # Web: Google Trends + News
                              'google_trends_interest', 'google_trends_direction',
                              'related_search_queries', 'market_news'],
                'critical': ['opportunity_score', 'trend_strength'],
            },
            'price': {
                'primary': ['market_size_estimate', 'addressable_market_value', 
                           'revenue_benchmark', 'capital_required', 'median_income',
                           'income_growth_rate', 'income_differential'],
                'enrichment': ['median_rent', 'spending_power_index', 'rent_by_bedroom',
                              # Web: Zillow/Redfin
                              'zillow_home_value', 'zillow_rent_estimate', 
                              'home_value_change_yoy', 'real_estate_market_temp'],
                'critical': ['market_size_estimate', 'median_income'],
            },
            'place': {
                'primary': ['growth_score', 'growth_category', 'population_growth_rate',
                           'job_growth_rate', 'business_formation_rate', 'population',
                           'traffic_aadt', 'site_recommendations'],
                'enrichment': ['vacancy_rate', 'absorption_rate', 'supply_pipeline',
                              # Web: Indeed/LinkedIn + BLS
                              'job_postings_count', 'job_market_growth', 
                              'top_hiring_companies', 'unemployment_rate'],
                'critical': ['growth_score', 'population'],
            },
            'promotion': {
                'primary': ['competition_level', 'competitive_advantages', 'key_risks',
                           'success_factors', 'failure_points', 'competitor_count',
                           'avg_competitor_rating'],
                'enrichment': ['search_trends',
                              # Web: Google Places/Reviews
                              'google_places_competitors', 'google_avg_rating',
                              'google_total_reviews', 'google_review_sentiment'],
                'critical': ['competition_level', 'competitor_count'],
            }
        }
        
        # Report type weights - which pillars matter most for each report
        report_weights = {
            'market_analysis': {'product': 0.3, 'price': 0.2, 'place': 0.35, 'promotion': 0.15},
            'feasibility': {'product': 0.2, 'price': 0.35, 'place': 0.25, 'promotion': 0.2},
            'business_plan': {'product': 0.25, 'price': 0.25, 'place': 0.25, 'promotion': 0.25},
            'financial': {'product': 0.15, 'price': 0.45, 'place': 0.2, 'promotion': 0.2},
            'competitive': {'product': 0.2, 'price': 0.15, 'place': 0.15, 'promotion': 0.5},
            'pitch_deck': {'product': 0.35, 'price': 0.3, 'place': 0.15, 'promotion': 0.2},
        }
        
        weights = report_weights.get(report_type, report_weights['market_analysis'])
        
        # Calculate per-pillar quality
        pillar_data = {
            'product': product,
            'price': price,
            'place': place,
            'promotion': promotion
        }
        
        pillar_qualities = {}
        all_warnings = []
        total_primary = 0
        total_enrichment = 0
        
        for pillar_name, fields in pillar_fields.items():
            data = pillar_data[pillar_name]
            data_dict = asdict(data)
            
            pq = PillarQuality(name=pillar_name)
            
            # Count filled fields
            primary_filled = sum(1 for f in fields['primary'] if data_dict.get(f) is not None)
            enrichment_filled = sum(1 for f in fields['enrichment'] if data_dict.get(f) is not None)
            
            pq.primary_sources = primary_filled
            pq.enrichment_sources = enrichment_filled
            pq.fields_filled = primary_filled + enrichment_filled
            pq.fields_total = len(fields['primary']) + len(fields['enrichment'])
            
            total_primary += primary_filled
            total_enrichment += enrichment_filled
            
            # Completeness = filled / total
            pq.completeness = pq.fields_filled / pq.fields_total if pq.fields_total > 0 else 0.0
            
            # Check critical fields
            critical_missing = [f for f in fields['critical'] if data_dict.get(f) is None]
            if critical_missing:
                warning = f"⚠️ {pillar_name.upper()}: Missing critical fields: {', '.join(critical_missing)}"
                pq.warnings.append(warning)
                all_warnings.append(warning)
            
            # Confidence: weighted by source quality
            # Primary sources = 1.0 weight, Enrichment = 0.8 weight
            if pq.fields_filled > 0:
                weighted_score = (primary_filled * 1.0 + enrichment_filled * 0.8)
                max_weighted = len(fields['primary']) * 1.0 + len(fields['enrichment']) * 0.8
                pq.confidence = weighted_score / max_weighted if max_weighted > 0 else 0.0
            else:
                pq.confidence = 0.0
            
            # Apply penalty for missing critical fields
            if critical_missing:
                penalty = 0.15 * len(critical_missing)
                pq.confidence = max(0, pq.confidence - penalty)
            
            pillar_qualities[pillar_name] = pq
        
        # Assign pillar qualities to DataQuality
        quality.product_quality = pillar_qualities['product']
        quality.price_quality = pillar_qualities['price']
        quality.place_quality = pillar_qualities['place']
        quality.promotion_quality = pillar_qualities['promotion']
        
        # Overall completeness (weighted by report type)
        quality.completeness = sum(
            pillar_qualities[p].completeness * weights[p] 
            for p in weights
        )
        
        # Overall confidence (weighted by report type)
        quality.confidence = sum(
            pillar_qualities[p].confidence * weights[p] 
            for p in weights
        )
        
        # Source breakdown
        total_filled = total_primary + total_enrichment
        if total_filled > 0:
            quality.primary_data_pct = total_primary / total_filled
            quality.enrichment_data_pct = total_enrichment / total_filled
        
        quality.oppgrid_fields_filled = total_primary
        quality.jedire_enrichment_available = total_enrichment > 0
        
        # Find weakest pillar (lowest completeness among high-weight pillars)
        relevant_pillars = {p: q for p, q in pillar_qualities.items() if weights[p] >= 0.2}
        if relevant_pillars:
            quality.weakest_pillar = min(relevant_pillars, key=lambda p: relevant_pillars[p].completeness)
        
        # Report readiness thresholds
        # 0.7+ = good, 0.5-0.7 = marginal, <0.5 = insufficient
        if quality.completeness >= 0.7 and quality.confidence >= 0.6:
            quality.report_readiness = min(1.0, (quality.completeness + quality.confidence) / 2 + 0.1)
        elif quality.completeness >= 0.5:
            quality.report_readiness = (quality.completeness + quality.confidence) / 2
        else:
            quality.report_readiness = quality.completeness * 0.8
        
        # Generate recommended actions
        quality.recommended_actions = self._generate_recommendations(
            pillar_qualities, report_type, pillar_fields
        )
        
        quality.stale_data_warnings = all_warnings
        
        return quality
    
    def _generate_recommendations(
        self,
        pillar_qualities: Dict[str, PillarQuality],
        report_type: str,
        pillar_fields: Dict
    ) -> List[str]:
        """Generate actionable recommendations to improve data quality."""
        recommendations = []
        
        # Check each pillar
        for pillar_name, pq in pillar_qualities.items():
            if pq.completeness < 0.5:
                # Critical gap
                missing_critical = [
                    f for f in pillar_fields[pillar_name]['critical']
                    if f not in [w.split(': ')[-1] for w in pq.warnings]
                ]
                if pq.primary_sources < 2:
                    recommendations.append(
                        f"🔴 {pillar_name.upper()}: Run opportunity analysis to populate core data"
                    )
                elif pq.enrichment_sources == 0:
                    recommendations.append(
                        f"🟡 {pillar_name.upper()}: Enable JediRE enrichment for rental market context"
                    )
            elif pq.completeness < 0.7:
                # Moderate gap
                if pq.enrichment_sources == 0:
                    recommendations.append(
                        f"💡 {pillar_name.upper()}: JediRE enrichment would improve confidence"
                    )
        
        # Report-specific recommendations
        if report_type == 'financial' and pillar_qualities['price'].completeness < 0.6:
            recommendations.append("📊 Financial report: Consider fetching success patterns for revenue benchmarks")
        
        if report_type == 'competitive' and pillar_qualities['promotion'].completeness < 0.6:
            recommendations.append("🎯 Competitive report: Run Google Maps competitor analysis")
        
        if report_type in ['market_analysis', 'feasibility'] and pillar_qualities['place'].completeness < 0.7:
            recommendations.append("📍 Location report: Fetch traffic data and growth trajectories")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _parse_json_field(self, field: Any) -> Optional[List]:
        """Parse JSON string field to list."""
        if field is None:
            return None
        if isinstance(field, list):
            return field
        if isinstance(field, str):
            try:
                import json
                return json.loads(field)
            except:
                return None
        return None
    
    def to_dict(self, context: ReportDataContext) -> Dict[str, Any]:
        """Convert ReportDataContext to dictionary for AI prompts."""
        # Convert data quality with nested pillar qualities
        dq = context.data_quality
        data_quality_dict = {
            "completeness": dq.completeness,
            "confidence": dq.confidence,
            "report_readiness": dq.report_readiness,
            "weakest_pillar": dq.weakest_pillar,
            "oppgrid_fields_filled": dq.oppgrid_fields_filled,
            "jedire_enrichment_available": dq.jedire_enrichment_available,
            "primary_data_pct": dq.primary_data_pct,
            "enrichment_data_pct": dq.enrichment_data_pct,
            "stale_data_warnings": dq.stale_data_warnings,
            "recommended_actions": dq.recommended_actions,
            "pillars": {
                "product": asdict(dq.product_quality) if dq.product_quality else None,
                "price": asdict(dq.price_quality) if dq.price_quality else None,
                "place": asdict(dq.place_quality) if dq.place_quality else None,
                "promotion": asdict(dq.promotion_quality) if dq.promotion_quality else None,
            }
        }
        
        return {
            "city": context.city,
            "state": context.state,
            "business_type": context.business_type,
            "report_type": context.report_type,
            "product": asdict(context.product),
            "price": asdict(context.price),
            "place": asdict(context.place),
            "promotion": asdict(context.promotion),
            "data_quality": data_quality_dict,
            "fetched_at": context.fetched_at,
        }
    
    def get_quality_summary(self, context: ReportDataContext) -> str:
        """Generate human-readable quality summary for reports."""
        dq = context.data_quality
        
        # Overall status
        if dq.report_readiness >= 0.8:
            status = "✅ **Excellent** - Data is comprehensive and reliable"
        elif dq.report_readiness >= 0.6:
            status = "🟡 **Good** - Data is sufficient with minor gaps"
        elif dq.report_readiness >= 0.4:
            status = "🟠 **Fair** - Report may have limited depth"
        else:
            status = "🔴 **Limited** - Consider gathering more data"
        
        lines = [
            f"## Data Quality Assessment",
            f"",
            f"**Overall Status:** {status}",
            f"",
            f"| Metric | Score |",
            f"|--------|-------|",
            f"| Completeness | {dq.completeness:.0%} |",
            f"| Confidence | {dq.confidence:.0%} |",
            f"| Report Readiness | {dq.report_readiness:.0%} |",
            f"",
            f"### Source Breakdown",
            f"- OppGrid (Primary): {dq.primary_data_pct:.0%} of data",
            f"- JediRE (Enrichment): {dq.enrichment_data_pct:.0%} of data",
        ]
        
        # Per-pillar breakdown
        lines.extend([
            f"",
            f"### Pillar Analysis",
            f"",
            f"| Pillar | Completeness | Confidence | Fields |",
            f"|--------|--------------|------------|--------|",
        ])
        
        for pq in [dq.product_quality, dq.price_quality, dq.place_quality, dq.promotion_quality]:
            if pq:
                emoji = "✅" if pq.completeness >= 0.7 else ("🟡" if pq.completeness >= 0.4 else "🔴")
                lines.append(
                    f"| {emoji} {pq.name.title()} | {pq.completeness:.0%} | {pq.confidence:.0%} | {pq.fields_filled}/{pq.fields_total} |"
                )
        
        # Weakest pillar callout
        if dq.weakest_pillar:
            lines.extend([
                f"",
                f"**Weakest Area:** {dq.weakest_pillar.title()} - focus additional research here",
            ])
        
        # Warnings
        if dq.stale_data_warnings:
            lines.extend([
                f"",
                f"### ⚠️ Warnings",
            ])
            for warning in dq.stale_data_warnings:
                lines.append(f"- {warning}")
        
        # Recommendations
        if dq.recommended_actions:
            lines.extend([
                f"",
                f"### 💡 Recommendations",
            ])
            for rec in dq.recommended_actions:
                lines.append(f"- {rec}")
        
        return "\n".join(lines)
    
    # =========================================================================
    # 4 P's API Methods - For platform-wide integration
    # =========================================================================
    
    def get_four_ps_for_opportunity(self, opportunity_id: int) -> Optional[ReportDataContext]:
        """
        Get 4 P's data for a specific opportunity.
        
        This is the primary method for powering idea cards, detail pages,
        and workspace intelligence with unified 4 P's data.
        """
        opp = self.db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if not opp:
            return None
        
        # Extract location from opportunity
        city = opp.city or "Unknown"
        state = opp.region or opp.country or "US"
        business_type = opp.category
        
        return self.get_report_data(
            city=city,
            state=state,
            business_type=business_type,
            report_type="market_analysis",
            opportunity_id=opportunity_id
        )
    
    def get_pillar_scores(self, context: ReportDataContext) -> Dict[str, int]:
        """
        Calculate 0-100 scores for each pillar.
        
        Score formula:
        - Base from data completeness (40% weight)
        - Boost from key metrics (40% weight)
        - Confidence adjustment (20% weight)
        """
        scores = {}
        
        # PRODUCT score
        product_base = (context.data_quality.product_quality.completeness * 40) if context.data_quality.product_quality else 0
        product_boost = 0
        if context.product.opportunity_score:
            product_boost += min(20, context.product.opportunity_score / 5)  # 0-100 → 0-20
        if context.product.pain_intensity:
            product_boost += min(10, context.product.pain_intensity)  # 1-10 → 1-10
        if context.product.trend_strength:
            product_boost += min(10, context.product.trend_strength * 10)  # 0-1 → 0-10
        product_conf = (context.data_quality.product_quality.confidence * 20) if context.data_quality.product_quality else 0
        scores['product'] = min(100, int(product_base + product_boost + product_conf))
        
        # PRICE score
        price_base = (context.data_quality.price_quality.completeness * 40) if context.data_quality.price_quality else 0
        price_boost = 0
        if context.price.median_income:
            # Higher income = better market
            if context.price.median_income > 100000:
                price_boost += 20
            elif context.price.median_income > 70000:
                price_boost += 15
            elif context.price.median_income > 50000:
                price_boost += 10
            else:
                price_boost += 5
        if context.price.market_size_estimate:
            size = context.price.market_size_estimate.lower()
            if 'b' in size:  # Billions
                price_boost += 20
            elif 'm' in size:  # Millions
                price_boost += 10
        price_conf = (context.data_quality.price_quality.confidence * 20) if context.data_quality.price_quality else 0
        scores['price'] = min(100, int(price_base + price_boost + price_conf))
        
        # PLACE score
        place_base = (context.data_quality.place_quality.completeness * 40) if context.data_quality.place_quality else 0
        place_boost = 0
        if context.place.growth_score:
            place_boost += min(25, context.place.growth_score / 4)  # 0-100 → 0-25
        if context.place.population_growth_rate:
            if context.place.population_growth_rate > 2:
                place_boost += 15
            elif context.place.population_growth_rate > 1:
                place_boost += 10
            elif context.place.population_growth_rate > 0:
                place_boost += 5
        place_conf = (context.data_quality.place_quality.confidence * 20) if context.data_quality.place_quality else 0
        scores['place'] = min(100, int(place_base + place_boost + place_conf))
        
        # PROMOTION score
        promo_base = (context.data_quality.promotion_quality.completeness * 40) if context.data_quality.promotion_quality else 0
        promo_boost = 0
        if context.promotion.competition_level:
            level = context.promotion.competition_level.lower()
            if level == 'low':
                promo_boost += 25
            elif level == 'medium':
                promo_boost += 15
            elif level == 'high':
                promo_boost += 5
        if context.promotion.competitive_advantages:
            promo_boost += min(15, len(context.promotion.competitive_advantages) * 5)
        promo_conf = (context.data_quality.promotion_quality.confidence * 20) if context.data_quality.promotion_quality else 0
        scores['promotion'] = min(100, int(promo_base + promo_boost + promo_conf))
        
        return scores
    
    def get_mini_response(self, opportunity_id: int) -> Optional[Dict[str, Any]]:
        """
        Get lightweight 4 P's response for cards.
        
        Returns only scores and key insight - minimal payload.
        """
        context = self.get_four_ps_for_opportunity(opportunity_id)
        if not context:
            return None
        
        scores = self.get_pillar_scores(context)
        overall = int(sum(scores.values()) / 4)
        
        # Generate top insight
        insights = []
        if context.product.trend_strength and context.product.trend_strength > 0.7:
            insights.append("Strong upward trend")
        if context.place.growth_score and context.place.growth_score > 70:
            insights.append("High-growth market")
        if context.promotion.competition_level and context.promotion.competition_level.lower() == 'low':
            insights.append("Low competition")
        if context.price.median_income and context.price.median_income > 80000:
            insights.append("High spending power")
        
        top_insight = insights[0] if insights else "Data analysis available"
        
        return {
            "opportunity_id": opportunity_id,
            "scores": scores,
            "overall": overall,
            "quality": round(context.data_quality.completeness, 2),
            "top_insight": top_insight
        }
    
    def get_full_response(self, opportunity_id: int) -> Optional[Dict[str, Any]]:
        """
        Get full 4 P's response for detail pages.
        """
        context = self.get_four_ps_for_opportunity(opportunity_id)
        if not context:
            return None
        
        scores = self.get_pillar_scores(context)
        
        return {
            "opportunity_id": opportunity_id,
            "city": context.city,
            "state": context.state,
            "business_type": context.business_type,
            "scores": scores,
            "overall": int(sum(scores.values()) / 4),
            "product": asdict(context.product),
            "price": asdict(context.price),
            "place": asdict(context.place),
            "promotion": asdict(context.promotion),
            "data_quality": {
                "completeness": round(context.data_quality.completeness, 2),
                "confidence": round(context.data_quality.confidence, 2),
                "report_readiness": round(context.data_quality.report_readiness, 2),
                "weakest_pillar": context.data_quality.weakest_pillar,
                "recommended_actions": context.data_quality.recommended_actions[:3],
                "pillar_quality": {
                    "product": {
                        "completeness": round(context.data_quality.product_quality.completeness, 2) if context.data_quality.product_quality else 0,
                        "confidence": round(context.data_quality.product_quality.confidence, 2) if context.data_quality.product_quality else 0,
                    },
                    "price": {
                        "completeness": round(context.data_quality.price_quality.completeness, 2) if context.data_quality.price_quality else 0,
                        "confidence": round(context.data_quality.price_quality.confidence, 2) if context.data_quality.price_quality else 0,
                    },
                    "place": {
                        "completeness": round(context.data_quality.place_quality.completeness, 2) if context.data_quality.place_quality else 0,
                        "confidence": round(context.data_quality.place_quality.confidence, 2) if context.data_quality.place_quality else 0,
                    },
                    "promotion": {
                        "completeness": round(context.data_quality.promotion_quality.completeness, 2) if context.data_quality.promotion_quality else 0,
                        "confidence": round(context.data_quality.promotion_quality.confidence, 2) if context.data_quality.promotion_quality else 0,
                    },
                }
            },
            "fetched_at": context.fetched_at
        }


# Convenience function
def get_report_data(
    db: Session,
    city: str,
    state: str,
    business_type: Optional[str] = None,
    report_type: str = "market_analysis",
    opportunity_id: Optional[int] = None
) -> ReportDataContext:
    """Get report data context."""
    service = ReportDataService(db)
    return service.get_report_data(city, state, business_type, report_type, opportunity_id)
