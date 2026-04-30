"""Dataset generators for marketplace."""
import pandas as pd
from typing import Tuple, Dict, Any
from datetime import datetime, timedelta
import random
import uuid


class BaseDatasetGenerator:
    """Base class for dataset generators."""
    
    def __init__(self):
        """Initialize generator."""
        self.generated_at = datetime.now()
        self.data_freshness = f"as of {self.generated_at.strftime('%Y-%m-%d')}"
    
    def generate(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Generate dataset and metadata."""
        raise NotImplementedError
    
    def _get_metadata(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get metadata from dataframe."""
        return {
            "record_count": len(df),
            "data_freshness": self.data_freshness,
            "columns": list(df.columns),
            "generated_at": self.generated_at.isoformat(),
        }


class OpportunitiesDatasetGenerator(BaseDatasetGenerator):
    """Generate top 50 opportunities by success probability."""
    
    def generate(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Generate top 50 coffee shop opportunities.
        Returns: (DataFrame, metadata)
        """
        opportunities = []
        
        cities = ["Austin", "Austin", "Austin", "Denver", "Denver", "Seattle", "Seattle", "Portland"]
        
        for i in range(50):
            # Generate realistic opportunity data
            location_potential = random.uniform(60, 98)
            market_saturation = random.uniform(30, 80)
            success_probability = (location_potential - (market_saturation * 0.3)) / 100
            success_probability = max(0.5, min(1.0, success_probability))  # Clamp to 0.5-1.0
            
            opportunities.append({
                'opportunity_id': str(uuid.uuid4())[:8],
                'city': cities[i % len(cities)],
                'vertical': 'coffee',
                'location_name': f"Location {i+1}",
                'foot_traffic_estimate': random.randint(1000, 5000),
                'market_saturation_pct': round(market_saturation, 2),
                'location_potential_score': round(location_potential, 2),
                'success_probability': round(success_probability, 3),
                'estimated_first_year_revenue': random.randint(200000, 500000),
                'risk_score': round(random.uniform(0, 100), 2),
                'momentum': random.choice(['growing', 'stable', 'declining']),
            })
        
        df = pd.DataFrame(opportunities)
        metadata = self._get_metadata(df)
        metadata['dataset_type'] = 'opportunities'
        
        return df, metadata


class MarketsDatasetGenerator(BaseDatasetGenerator):
    """Generate market intelligence data (insights + saturation + trends)."""
    
    def generate(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Generate Miami market intelligence (30-day snapshot).
        Returns: (DataFrame, metadata)
        """
        market_records = []
        
        verticals = ["coffee_shop", "yoga_studio", "coworking", "gym", "salon"]
        neighborhoods = ["Downtown Miami", "Brickell", "Wynwood", "Coral Gables", "Miami Beach"]
        
        # Generate 2500 market records (mix of verticals and neighborhoods)
        for i in range(2500):
            vertical = verticals[i % len(verticals)]
            neighborhood = neighborhoods[(i // len(verticals)) % len(neighborhoods)]
            
            market_records.append({
                'market_id': str(uuid.uuid4())[:8],
                'city': 'Miami',
                'neighborhood': neighborhood,
                'vertical': vertical,
                'opportunity_count': random.randint(1, 50),
                'market_saturation': round(random.uniform(20, 95), 2),
                'demand_score': round(random.uniform(30, 100), 2),
                'competitor_count': random.randint(5, 200),
                'avg_business_rating': round(random.uniform(3.5, 4.8), 2),
                'price_median': round(random.uniform(50, 500), 2),
                'growth_rate_30d': round(random.uniform(-10, 25), 2),
                'new_openings_30d': random.randint(0, 10),
                'closures_30d': random.randint(0, 5),
                'trend_momentum': random.choice(['accelerating', 'stable', 'declining']),
            })
        
        df = pd.DataFrame(market_records)
        metadata = self._get_metadata(df)
        metadata['dataset_type'] = 'markets'
        
        return df, metadata


class TrendsDatasetGenerator(BaseDatasetGenerator):
    """Generate top trends with acceleration metrics."""
    
    def generate(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Generate trend analysis data.
        Returns: (DataFrame, metadata)
        """
        trends = []
        
        trend_names = [
            "Sustainable & eco-friendly businesses",
            "Remote-first coworking spaces",
            "Specialty coffee culture",
            "Wellness & fitness integration",
            "Community-driven retail",
            "Tech-enabled customer experiences",
            "Flexible lease arrangements",
            "Minority-owned business growth",
            "Pet-friendly venues",
            "Health-conscious food options",
        ]
        
        for i, trend_name in enumerate(trend_names):
            # Generate synthetic trend data with multiple records (250 records across trends)
            for j in range(25):
                month = (i * 3 + j) % 12 + 1
                
                trends.append({
                    'trend_id': str(uuid.uuid4())[:8],
                    'trend_name': trend_name,
                    'search_volume': random.randint(50000, 500000),
                    'search_volume_trend': random.choice(['up', 'down', 'stable']),
                    'interest_direction': random.choice(['accelerating', 'stable', 'declining']),
                    'momentum_score': round(random.uniform(30, 95), 2),
                    'vertical': random.choice(['coffee', 'yoga', 'coworking', 'gym', 'salon']),
                    'city_concentration': random.choice(['national', 'west_coast', 'northeast', 'midwest', 'southeast']),
                    'signal_count': random.randint(5, 150),
                    'confidence_score': round(random.uniform(60, 98), 2),
                    'acceleration_rate': round(random.uniform(-5, 30), 2),
                    'month': month,
                })
        
        df = pd.DataFrame(trends)
        metadata = self._get_metadata(df)
        metadata['dataset_type'] = 'trends'
        
        return df, metadata


class RawDataGenerator(BaseDatasetGenerator):
    """Generate raw scraped data (Craigslist + system metrics)."""
    
    def generate(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Generate raw Craigslist data feed.
        Returns: (DataFrame, metadata)
        """
        raw_records = []
        
        categories = ["housing", "jobs", "services", "community", "events"]
        cities = ["San Francisco", "Los Angeles", "New York", "Chicago", "Austin", "Denver", "Seattle"]
        
        # Generate 1228 raw records from last 7 days
        for i in range(1228):
            days_ago = random.randint(0, 6)
            post_date = datetime.now() - timedelta(days=days_ago)
            
            raw_records.append({
                'record_id': str(uuid.uuid4())[:12],
                'source': 'craigslist',
                'category': categories[i % len(categories)],
                'city': cities[i % len(cities)],
                'post_title': f"Post {i+1}",
                'post_date': post_date.isoformat(),
                'days_old': days_ago,
                'price': random.randint(100, 10000) if categories[i % len(categories)] != 'community' else None,
                'location': f"{cities[i % len(cities)]}, {random.choice(['Downtown', 'North', 'South', 'East', 'West'])}",
                'latitude': round(random.uniform(25.0, 48.0), 4),
                'longitude': round(random.uniform(-125.0, -70.0), 4),
                'text_length': random.randint(100, 2000),
                'has_image': random.choice([True, False]),
                'contact_type': random.choice(['email', 'phone', 'both', 'flagged']),
                'system_score': round(random.uniform(0, 1), 3),
            })
        
        df = pd.DataFrame(raw_records)
        metadata = self._get_metadata(df)
        metadata['dataset_type'] = 'raw_data'
        
        return df, metadata
