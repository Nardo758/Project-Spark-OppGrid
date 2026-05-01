"""
Micro Market Catalog Service

Tier A: Named micro-markets query and management.
Provides curated named markets for top 10 metros with polygon geometries.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.micro_market import MicroMarket
from app.schemas.identify_location import TargetMarket, TargetMarketType, CandidateProfile, CandidateSource

logger = logging.getLogger(__name__)


class MicroMarketCatalog:
    """Manages Tier A named micro-markets"""

    def __init__(self, db: Session):
        self.db = db

    def get_markets_for_metro(self, metro: str, state: str) -> List[MicroMarket]:
        """
        Get all active micro-markets for a given metro/state.
        
        Example: get_markets_for_metro("Miami", "FL")
        Returns: [Brickell, Wynwood, Calle Ocho, ...]
        """
        try:
            markets = self.db.query(MicroMarket).filter(
                and_(
                    MicroMarket.metro == metro,
                    MicroMarket.state == state,
                    MicroMarket.is_active == 1
                )
            ).all()
            return markets
        except Exception as e:
            logger.error(f"Error fetching markets for {metro}, {state}: {e}")
            return []

    def get_markets_by_city(self, city: str, state: str) -> List[MicroMarket]:
        """
        Get micro-markets by city (may span multiple metros).
        For precision, use metro-based lookup instead.
        """
        try:
            markets = self.db.query(MicroMarket).filter(
                and_(
                    MicroMarket.state == state,
                    MicroMarket.is_active == 1
                )
            ).all()
            return markets
        except Exception as e:
            logger.error(f"Error fetching markets for {city}, {state}: {e}")
            return []

    def get_market_by_name(self, market_name: str, metro: str, state: str) -> Optional[MicroMarket]:
        """Get a specific market by exact name"""
        try:
            market = self.db.query(MicroMarket).filter(
                and_(
                    MicroMarket.market_name == market_name,
                    MicroMarket.metro == metro,
                    MicroMarket.state == state,
                    MicroMarket.is_active == 1
                )
            ).first()
            return market
        except Exception as e:
            logger.error(f"Error fetching market {market_name}: {e}")
            return None

    def search_markets(self, query: str, state: Optional[str] = None) -> List[MicroMarket]:
        """
        Search markets by name prefix.
        Useful for autocomplete or discovery.
        """
        try:
            q = self.db.query(MicroMarket).filter(
                MicroMarket.market_name.ilike(f"{query}%"),
                MicroMarket.is_active == 1
            )
            if state:
                q = q.filter(MicroMarket.state == state)
            return q.all()
        except Exception as e:
            logger.error(f"Error searching markets for '{query}': {e}")
            return []

    def get_all_metros(self) -> List[Dict[str, str]]:
        """Get list of all metros with markets"""
        try:
            results = self.db.query(
                MicroMarket.metro,
                MicroMarket.state
            ).filter(MicroMarket.is_active == 1).distinct().all()
            return [{"metro": r[0], "state": r[1]} for r in results]
        except Exception as e:
            logger.error(f"Error fetching metros: {e}")
            return []

    def markets_to_candidates(
        self,
        markets: List[MicroMarket],
        category: str,
    ) -> List[CandidateProfile]:
        """
        Convert micro-markets to candidate profiles.
        Markets don't have all signals, so we use placeholder measured_signals.
        """
        candidates = []
        for idx, market in enumerate(markets):
            candidate_id = f"named_market_{market.id}_{category}"
            
            # Placeholder signals based on market metadata
            measured_signals = []
            
            # Signal 1: Foot traffic (if available)
            if market.avg_foot_traffic is not None:
                measured_signals.append({
                    "signal_name": "foot_traffic_score",
                    "signal_value": float(market.avg_foot_traffic),
                    "percentile_rank": 75,  # Named markets are typically good locations
                    "confidence": 0.8,
                    "data_source": "micro_market_catalog"
                })
            else:
                measured_signals.append({
                    "signal_name": "foot_traffic_score",
                    "signal_value": 65.0,
                    "percentile_rank": 70,
                    "confidence": 0.6,
                    "data_source": "micro_market_catalog"
                })
            
            # Signal 2: Demographic fit
            if market.avg_demographic_fit is not None:
                measured_signals.append({
                    "signal_name": "demographic_fit",
                    "signal_value": market.avg_demographic_fit * 100,
                    "percentile_rank": 75,
                    "confidence": 0.75,
                    "data_source": "micro_market_catalog"
                })
            else:
                measured_signals.append({
                    "signal_name": "demographic_fit",
                    "signal_value": 70.0,
                    "percentile_rank": 70,
                    "confidence": 0.5,
                    "data_source": "micro_market_catalog"
                })
            
            # Signal 3: Competition density (inverse = lower is better)
            if market.avg_competition_density is not None:
                competition_score = 100 - (market.avg_competition_density * 100)
                measured_signals.append({
                    "signal_name": "competition_density",
                    "signal_value": competition_score,
                    "percentile_rank": 70,
                    "confidence": 0.75,
                    "data_source": "micro_market_catalog"
                })
            else:
                measured_signals.append({
                    "signal_name": "competition_density",
                    "signal_value": 65.0,
                    "percentile_rank": 60,
                    "confidence": 0.5,
                    "data_source": "micro_market_catalog"
                })

            # Calculate overall score as average of signals
            signal_values = [s["signal_value"] for s in measured_signals]
            overall_score = sum(signal_values) / len(signal_values)
            
            # Determine archetype based on typical_archetypes and overall score
            typical_archetypes = []
            if market.typical_archetypes:
                try:
                    import json
                    typical_archetypes = json.loads(market.typical_archetypes)
                except:
                    pass
            
            archetype = typical_archetypes[0] if typical_archetypes else "mainstream"
            
            candidate = CandidateProfile(
                candidate_id=candidate_id,
                location_name=market.market_name,
                latitude=market.center_latitude,
                longitude=market.center_longitude,
                archetype=archetype,
                archetype_confidence=0.85,
                archetype_rationale=f"Named market: {market.market_name} is a curated location in {market.metro}",
                risk_factors=["Competition present", "Market saturation possible"],
                measured_signals=measured_signals,
                source=CandidateSource.NAMED_MARKET,
                source_id=str(market.id),
                zip_code=None,
                neighborhood=market.market_name,
                city=market.metro,
                state=market.state,
                overall_score=overall_score
            )
            candidates.append(candidate)
        
        return candidates

    def seed_data(self, seed_records: List[Dict[str, Any]]) -> int:
        """
        Bulk seed micro-markets from seed data.
        Used for initial population of 10 metros.
        
        Expected format:
        {
            "metro": "Miami",
            "state": "FL",
            "market_name": "Brickell",
            "center_latitude": 25.7685,
            "center_longitude": -80.1922,
            "polygon_geojson": {...},
            "description": "...",
            "typical_archetypes": ["mainstream", "specialist"]
        }
        """
        count = 0
        for record in seed_records:
            try:
                # Check if already exists
                existing = self.db.query(MicroMarket).filter(
                    and_(
                        MicroMarket.market_name == record["market_name"],
                        MicroMarket.metro == record["metro"],
                        MicroMarket.state == record["state"]
                    )
                ).first()
                
                if existing:
                    logger.info(f"Market {record['market_name']} already exists, skipping")
                    continue
                
                # Create new record
                import json
                market = MicroMarket(
                    market_name=record["market_name"],
                    metro=record["metro"],
                    state=record["state"],
                    center_latitude=record["center_latitude"],
                    center_longitude=record["center_longitude"],
                    polygon_geojson=record.get("polygon_geojson", {}),
                    description=record.get("description"),
                    typical_archetypes=json.dumps(record.get("typical_archetypes", [])),
                    demographic_profile=json.dumps(record.get("demographic_profile", {})),
                )
                self.db.add(market)
                count += 1
            except Exception as e:
                logger.error(f"Error seeding market {record.get('market_name')}: {e}")
        
        try:
            self.db.commit()
            logger.info(f"Seeded {count} micro-markets")
        except Exception as e:
            logger.error(f"Error committing seed data: {e}")
            self.db.rollback()
        
        return count
