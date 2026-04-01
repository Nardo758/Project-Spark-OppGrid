"""
Data Hub Aggregation Service

Populates hub tables with real data from OppGrid platform.
Runs 3x daily: 2 AM, 10 AM, 6 PM PST

Aggregates from:
- Opportunity (323 records with AI scores)
- DetectedTrend (platform signals)
- MarketGrowthTrajectory (city/state growth)
- CensusPopulationEstimate (demographics)
- GoogleMapsBusiness (competition)
- User, Subscription, GeneratedReport (analytics)
- IdeaValidation (validation scores)
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, text
from sqlalchemy.orm import Session
import json
import hashlib

logger = logging.getLogger(__name__)

# Import models
from app.models.opportunity import Opportunity
from app.models.detected_trend import DetectedTrend
from app.models.trend_opportunity_mapping import TrendOpportunityMapping
from app.models.census_demographics import (
    CensusPopulationEstimate,
    MarketGrowthTrajectory,
)
from app.models.google_scraping import GoogleMapsBusiness
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionTier, SubscriptionStatus
from app.models.generated_report import GeneratedReport
from app.models.idea_validation import IdeaValidation


class DataHubAggregationService:
    """Aggregates all platform data into hub tables."""
    
    def __init__(self, db: Session):
        self.db = db
        self.now = datetime.utcnow()
    
    async def run_full_aggregation(self):
        """Run all aggregation steps."""
        logger.info("🔄 Starting Data Hub Aggregation...")
        
        try:
            await self.aggregate_opportunities_enriched()
            await self.aggregate_markets_by_geography()
            await self.aggregate_industries_insights()
            await self.aggregate_market_signals()
            await self.aggregate_validation_insights()
            await self.aggregate_user_cohorts()
            await self.aggregate_financial_snapshot()
            
            logger.info("✅ Data Hub Aggregation Complete")
        except Exception as e:
            logger.error(f"❌ Aggregation failed: {e}", exc_info=True)
            raise
    
    # =========================================================================
    # 1. OPPORTUNITIES ENRICHED
    # =========================================================================
    
    async def aggregate_opportunities_enriched(self):
        """Populate hub_opportunities_enriched from Opportunity model."""
        logger.info("📊 Aggregating opportunities enriched...")
        
        # Get all active opportunities
        opportunities = self.db.query(Opportunity).filter(
            Opportunity.status == 'active'
        ).all()
        
        logger.info(f"   Processing {len(opportunities)} opportunities...")
        
        inserted = 0
        for opp in opportunities:
            try:
                # Get trends for this category
                trends = self.db.query(DetectedTrend).join(
                    TrendOpportunityMapping,
                    DetectedTrend.id == TrendOpportunityMapping.trend_id
                ).filter(
                    func.lower(TrendOpportunityMapping.category) == func.lower(opp.category or 'general')
                ).all()
                
                trend_momentum = 0.0
                if trends:
                    growth_rates = [t.growth_rate for t in trends if t.growth_rate]
                    if growth_rates:
                        avg_growth = sum(growth_rates) / len(growth_rates)
                        # Normalize to -1 to 1
                        trend_momentum = min(1.0, max(-1.0, avg_growth / 100))
                
                # Get competition count
                competition_query = self.db.query(func.count(GoogleMapsBusiness.id))
                if opp.city and opp.region:
                    competition_query = competition_query.filter(
                        func.lower(GoogleMapsBusiness.city) == func.lower(opp.city),
                        func.upper(GoogleMapsBusiness.state) == func.upper(opp.region)
                    )
                competition_count = competition_query.scalar() or 0
                
                # Determine market tier
                market_tier = self._classify_market_tier(
                    opp.ai_opportunity_score or 50,
                    trend_momentum
                )
                
                # Extract risks/advantages from JSON
                advantages = []
                risks = []
                if opp.ai_competitive_advantages:
                    try:
                        advantages = json.loads(opp.ai_competitive_advantages) if isinstance(opp.ai_competitive_advantages, str) else opp.ai_competitive_advantages
                    except:
                        advantages = []
                
                if opp.ai_key_risks:
                    try:
                        risks = json.loads(opp.ai_key_risks) if isinstance(opp.ai_key_risks, str) else opp.ai_key_risks
                    except:
                        risks = []
                
                # Insert into hub
                sql = text("""
                    INSERT INTO hub_opportunities_enriched (
                        opportunity_id, title, description, category, subcategory, 
                        source_platform, city, state, region, latitude, longitude,
                        ai_opportunity_score, market_tier, trend_momentum, 
                        competition_density, difficulty_score, market_readiness_score,
                        direct_competitors_count, competitive_advantages, key_risks,
                        technical_difficulty, market_risk,
                        aggregated_at, last_updated_at, data_freshness, confidence_score
                    ) VALUES (
                        :opp_id, :title, :description, :category, :subcategory,
                        :source, :city, :state, :region, :lat, :lng,
                        :score, :tier, :momentum,
                        :comp_density, :difficulty, :readiness,
                        :competitors, :advantages, :risks,
                        :tech_diff, :market_risk,
                        :now, :now, :freshness, :confidence
                    )
                    ON CONFLICT (opportunity_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        market_tier = EXCLUDED.market_tier,
                        trend_momentum = EXCLUDED.trend_momentum,
                        competition_density = EXCLUDED.competition_density,
                        direct_competitors_count = EXCLUDED.direct_competitors_count,
                        last_updated_at = EXCLUDED.last_updated_at
                """)
                
                self.db.execute(sql, {
                    'opp_id': opp.id,
                    'title': opp.title[:500],
                    'description': opp.description[:2000] if opp.description else None,
                    'category': opp.category,
                    'subcategory': opp.subcategory,
                    'source': opp.source_platform,
                    'city': opp.city,
                    'state': opp.region,
                    'region': opp.region,
                    'lat': opp.latitude,
                    'lng': opp.longitude,
                    'score': opp.ai_opportunity_score,
                    'tier': market_tier,
                    'momentum': trend_momentum,
                    'comp_density': self._classify_competition(competition_count),
                    'difficulty': 100 - (opp.ai_opportunity_score or 50),
                    'readiness': opp.feasibility_score or 50,
                    'competitors': competition_count,
                    'advantages': json.dumps(advantages) if advantages else None,
                    'risks': json.dumps(risks) if risks else None,
                    'tech_diff': opp.ai_competition_level or 'medium',
                    'market_risk': 'medium',
                    'now': self.now,
                    'freshness': 'fresh',
                    'confidence': 0.9,
                })
                
                inserted += 1
                
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to aggregate opportunity {opp.id}: {e}")
                continue
        
        self.db.commit()
        logger.info(f"   ✅ Inserted/updated {inserted} opportunities")
    
    # =========================================================================
    # 2. MARKETS BY GEOGRAPHY
    # =========================================================================
    
    async def aggregate_markets_by_geography(self):
        """Populate hub_markets_by_geography from Opportunity + Census + GoogleMaps."""
        logger.info("🌍 Aggregating markets by geography...")
        
        # Get unique cities from opportunities
        cities_states = self.db.query(
            func.distinct(Opportunity.city),
            Opportunity.region
        ).filter(
            Opportunity.city.isnot(None),
            Opportunity.region.isnot(None)
        ).all()
        
        logger.info(f"   Processing {len(cities_states)} cities...")
        
        inserted = 0
        for city, state in cities_states:
            try:
                # Opportunity stats
                opps = self.db.query(Opportunity).filter(
                    func.lower(Opportunity.city) == func.lower(city),
                    func.upper(Opportunity.region) == func.upper(state)
                ).all()
                
                # Category breakdown
                categories = {}
                for opp in opps:
                    cat = opp.category or 'general'
                    categories[cat] = categories.get(cat, 0) + 1
                
                # Census data
                census = self.db.query(CensusPopulationEstimate).filter(
                    func.lower(CensusPopulationEstimate.geography_name).like(f'%{city.lower()}%'),
                    func.upper(CensusPopulationEstimate.state_code) == state.upper()
                ).order_by(CensusPopulationEstimate.year.desc()).first()
                
                # Market growth trajectory
                trajectory = self.db.query(MarketGrowthTrajectory).filter(
                    func.lower(MarketGrowthTrajectory.city) == func.lower(city),
                    func.upper(MarketGrowthTrajectory.state) == state.upper()
                ).first()
                
                # Business competition
                businesses = self.db.query(GoogleMapsBusiness).filter(
                    func.lower(GoogleMapsBusiness.city) == func.lower(city),
                    func.upper(GoogleMapsBusiness.state) == state.upper()
                ).all()
                
                # New opportunities
                now = datetime.utcnow()
                new_30d = sum(1 for o in opps if o.created_at and o.created_at >= (now - timedelta(days=30)))
                new_90d = sum(1 for o in opps if o.created_at and o.created_at >= (now - timedelta(days=90)))
                
                sql = text("""
                    INSERT INTO hub_markets_by_geography (
                        city, state, country, total_opportunities, categories,
                        avg_opportunity_score, total_businesses, active_businesses,
                        avg_business_rating, population, population_growth_percent,
                        median_household_income, median_age,
                        growth_trajectory, new_opportunities_30d, new_opportunities_90d,
                        aggregated_at, last_updated_at
                    ) VALUES (
                        :city, :state, 'USA', :total_opps, :categories,
                        :avg_score, :total_biz, :active_biz,
                        :avg_rating, :population, :pop_growth,
                        :income, :age,
                        :growth, :new_30d, :new_90d,
                        :now, :now
                    )
                    ON CONFLICT (city, state) DO UPDATE SET
                        total_opportunities = EXCLUDED.total_opportunities,
                        avg_opportunity_score = EXCLUDED.avg_opportunity_score,
                        growth_trajectory = EXCLUDED.growth_trajectory,
                        last_updated_at = EXCLUDED.last_updated_at
                """)
                
                avg_score = sum(o.ai_opportunity_score or 50 for o in opps) / len(opps) if opps else 50
                avg_rating = sum(b.rating for b in businesses if b.rating) / len([b for b in businesses if b.rating]) if businesses else None
                
                self.db.execute(sql, {
                    'city': city,
                    'state': state,
                    'total_opps': len(opps),
                    'categories': json.dumps(categories) if categories else None,
                    'avg_score': avg_score,
                    'total_biz': len(businesses),
                    'active_biz': sum(1 for b in businesses if b.is_active),
                    'avg_rating': avg_rating,
                    'population': census.population if census else None,
                    'pop_growth': census.yoy_growth_rate if census else None,
                    'income': census.median_income if census else None,
                    'age': census.median_age if census else None,
                    'growth': trajectory.growth_category.value if trajectory and trajectory.growth_category else 'stable',
                    'new_30d': new_30d,
                    'new_90d': new_90d,
                    'now': self.now,
                })
                
                inserted += 1
                
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to aggregate {city}, {state}: {e}")
                continue
        
        self.db.commit()
        logger.info(f"   ✅ Inserted/updated {inserted} markets")
    
    # =========================================================================
    # 3. MARKET SIGNALS
    # =========================================================================
    
    async def aggregate_market_signals(self):
        """Populate hub_market_signals from DetectedTrend."""
        logger.info("📡 Aggregating market signals...")
        
        trends = self.db.query(DetectedTrend).all()
        
        logger.info(f"   Processing {len(trends)} trends...")
        
        inserted = 0
        for trend in trends:
            try:
                # Get affected industries/opportunities
                mappings = self.db.query(TrendOpportunityMapping).filter(
                    TrendOpportunityMapping.trend_id == trend.id
                ).all()
                
                affected_categories = [m.category for m in mappings]
                
                sql = text("""
                    INSERT INTO hub_market_signals (
                        signal_type, signal_name, category, signal_date,
                        signal_strength, trend_direction, momentum,
                        data_source, confidence_level,
                        discovered_at, applies_globally
                    ) VALUES (
                        :type, :name, :category, :date,
                        :strength, :direction, :momentum,
                        :source, :confidence,
                        :discovered, :global
                    )
                    ON CONFLICT (signal_id) DO UPDATE SET
                        signal_strength = EXCLUDED.signal_strength,
                        last_updated_at = EXCLUDED.last_updated_at
                """)
                
                self.db.execute(sql, {
                    'type': 'trend',
                    'name': trend.trend_name,
                    'category': affected_categories[0] if affected_categories else None,
                    'date': datetime.utcnow().date(),
                    'strength': (trend.trend_strength or 50) / 100.0,
                    'direction': 'rising' if trend.growth_rate and trend.growth_rate > 5 else 'stable',
                    'momentum': trend.growth_rate or 0,
                    'source': trend.source_type or 'oppgrid',
                    'confidence': (trend.confidence_score or 50) / 100.0,
                    'discovered': trend.detected_at or self.now,
                    'global': True,
                })
                
                inserted += 1
                
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to aggregate trend {trend.id}: {e}")
                continue
        
        self.db.commit()
        logger.info(f"   ✅ Inserted/updated {inserted} signals")
    
    # =========================================================================
    # 4. VALIDATION INSIGHTS
    # =========================================================================
    
    async def aggregate_validation_insights(self):
        """Populate hub_validation_insights from IdeaValidation."""
        logger.info("✅ Aggregating validation insights...")
        
        validations = self.db.query(IdeaValidation).filter(
            IdeaValidation.result_json.isnot(None)
        ).all()
        
        logger.info(f"   Processing {len(validations)} validations...")
        
        inserted = 0
        for val in validations:
            try:
                # Hash the idea for dedup
                idea_hash = hashlib.sha256(
                    (val.idea or "").encode()
                ).hexdigest()
                
                # Parse result JSON
                try:
                    result = json.loads(val.result_json) if isinstance(val.result_json, str) else val.result_json
                except:
                    result = {}
                
                sql = text("""
                    INSERT INTO hub_validation_insights (
                        idea_hash, industry, business_model,
                        online_viability_score, physical_viability_score, overall_score,
                        go_no_go_recommendation, recommendation_confidence,
                        cached_at, cache_validity_days
                    ) VALUES (
                        :hash, :industry, :model,
                        :online, :physical, :overall,
                        :recommendation, :confidence,
                        :now, 7
                    )
                    ON CONFLICT (idea_hash) DO UPDATE SET
                        overall_score = EXCLUDED.overall_score
                """)
                
                self.db.execute(sql, {
                    'hash': idea_hash,
                    'industry': val.category,
                    'model': result.get('business_model', 'unknown'),
                    'online': result.get('online_viability_score', 50),
                    'physical': result.get('physical_viability_score', 50),
                    'overall': val.opportunity_score or 50,
                    'recommendation': 'GO' if (val.opportunity_score or 50) >= 70 else 'NO-GO',
                    'confidence': (val.validation_confidence or 50) / 100.0,
                    'now': self.now,
                })
                
                inserted += 1
                
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to aggregate validation {val.id}: {e}")
                continue
        
        self.db.commit()
        logger.info(f"   ✅ Inserted/updated {inserted} validations")
    
    # =========================================================================
    # 5. USER COHORTS
    # =========================================================================
    
    async def aggregate_user_cohorts(self):
        """Populate hub_user_insights_cohorts."""
        logger.info("👥 Aggregating user cohorts...")
        
        # Define cohorts by subscription tier
        cohorts = {
            'free': SubscriptionTier.FREE,
            'pro': SubscriptionTier.PRO,
            'business': SubscriptionTier.BUSINESS,
        }
        
        inserted = 0
        for cohort_name, tier in cohorts.items():
            try:
                users = self.db.query(User).join(
                    Subscription,
                    User.id == Subscription.user_id
                ).filter(
                    Subscription.tier == tier
                ).all()
                
                user_count = len(users)
                
                if user_count == 0:
                    continue
                
                # Get reports for these users
                user_ids = [u.id for u in users]
                reports = self.db.query(GeneratedReport).filter(
                    GeneratedReport.user_id.in_(user_ids)
                ).all()
                
                avg_reports = len(reports) / user_count if user_count > 0 else 0
                
                # Report types
                report_types = {}
                for report in reports:
                    rt = report.report_type or 'unknown'
                    report_types[rt] = report_types.get(rt, 0) + 1
                
                sql = text("""
                    INSERT INTO hub_user_insights_cohorts (
                        cohort_name, user_count, 
                        avg_reports_generated_per_month,
                        preferred_report_types,
                        created_at, last_updated
                    ) VALUES (
                        :name, :count,
                        :avg_reports,
                        :types,
                        :now, :now
                    )
                    ON CONFLICT (cohort_name) DO UPDATE SET
                        user_count = EXCLUDED.user_count,
                        avg_reports_generated_per_month = EXCLUDED.avg_reports_generated_per_month
                """)
                
                self.db.execute(sql, {
                    'name': cohort_name,
                    'count': user_count,
                    'avg_reports': avg_reports,
                    'types': json.dumps(report_types) if report_types else None,
                    'now': self.now,
                })
                
                inserted += 1
                
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to aggregate cohort {cohort_name}: {e}")
                continue
        
        self.db.commit()
        logger.info(f"   ✅ Inserted/updated {inserted} cohorts")
    
    # =========================================================================
    # 6. FINANCIAL SNAPSHOT
    # =========================================================================
    
    async def aggregate_financial_snapshot(self):
        """Populate hub_financial_snapshot."""
        logger.info("💰 Aggregating financial snapshot...")
        
        try:
            # User counts
            total_users = self.db.query(func.count(User.id)).scalar() or 0
            paid_users = self.db.query(func.count(User.id)).join(
                Subscription
            ).filter(
                Subscription.tier != SubscriptionTier.FREE
            ).scalar() or 0
            free_users = total_users - paid_users
            
            # Active users (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            active_users = self.db.query(func.count(func.distinct(User.id))).join(
                GeneratedReport
            ).filter(
                GeneratedReport.created_at >= thirty_days_ago
            ).scalar() or 0
            
            # Revenue
            subscriptions = self.db.query(Subscription).all()
            mrr = sum(self._get_tier_price(s.tier) for s in subscriptions if s.status == SubscriptionStatus.ACTIVE) / 100
            
            # Reports
            total_reports = self.db.query(func.count(GeneratedReport.id)).scalar() or 0
            reports_this_month = self.db.query(func.count(GeneratedReport.id)).filter(
                GeneratedReport.created_at >= thirty_days_ago
            ).scalar() or 0
            
            sql = text("""
                INSERT INTO hub_financial_snapshot (
                    total_users, active_users_30d, paid_users, free_users,
                    mrr_recurring_revenue_usd, arr_recurring_revenue_usd,
                    total_reports_generated, reports_this_month,
                    snapshot_date, snapshot_period
                ) VALUES (
                    :total_users, :active_users, :paid_users, :free_users,
                    :mrr, :arr,
                    :total_reports, :reports_month,
                    :today, 'daily'
                )
                ON CONFLICT (snapshot_id) DO UPDATE SET
                    total_users = EXCLUDED.total_users,
                    mrr_recurring_revenue_usd = EXCLUDED.mrr_recurring_revenue_usd
            """)
            
            self.db.execute(sql, {
                'total_users': total_users,
                'active_users': active_users,
                'paid_users': paid_users,
                'free_users': free_users,
                'mrr': mrr,
                'arr': mrr * 12,
                'total_reports': total_reports,
                'reports_month': reports_this_month,
                'today': datetime.utcnow().date(),
            })
            
            self.db.commit()
            logger.info(f"   ✅ Financial snapshot recorded")
            
        except Exception as e:
            logger.warning(f"   ⚠️ Failed to aggregate financial snapshot: {e}")
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _classify_market_tier(self, score: float, momentum: float) -> str:
        """Classify market tier based on score and momentum."""
        if score >= 80:
            return 'hot'
        elif score >= 60 and momentum > 0:
            return 'growing'
        elif score >= 40:
            return 'mature'
        else:
            return 'declining'
    
    def _classify_competition(self, count: int) -> str:
        """Classify competition density."""
        if count <= 5:
            return 'sparse'
        elif count <= 20:
            return 'moderate'
        else:
            return 'saturated'
    
    def _get_tier_price(self, tier: SubscriptionTier) -> float:
        """Get monthly price in cents for tier."""
        prices = {
            SubscriptionTier.STARTER: 2000,
            SubscriptionTier.GROWTH: 5000,
            SubscriptionTier.PRO: 9900,
            SubscriptionTier.TEAM: 25000,
            SubscriptionTier.BUSINESS: 75000,
            SubscriptionTier.ENTERPRISE: 250000,
            SubscriptionTier.FREE: 0,
        }
        return prices.get(tier, 0)
