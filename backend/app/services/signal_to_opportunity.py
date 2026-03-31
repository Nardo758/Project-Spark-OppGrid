"""
Signal-to-Opportunity Conversion Service

Transforms raw scraped signals into validated, location-mapped business opportunities.
This service ENHANCES the existing OpportunityProcessor with:
1. Signal clustering (grouping similar problems)
2. Validation scoring with confidence tiers
3. Market sizing estimates
4. Deduplication logic

Uses existing: google_maps_keyword_matrix.py for pattern matching
"""

import os
import re
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
from math import radians, cos, sin, asin, sqrt
from sqlalchemy.orm import Session
from sqlalchemy import text
from anthropic import Anthropic

from app.services.google_maps_keyword_matrix import (
    APARTMENT_PATTERNS,
    CHILDCARE_PATTERNS,
    RESTAURANT_PATTERNS,
    HOME_SERVICES_PATTERNS,
    HEALTHCARE_PATTERNS,
    COMPETITIVE_PATTERNS,
)
from app.models.opportunity import Opportunity

logger = logging.getLogger(__name__)

AI_INTEGRATIONS_ANTHROPIC_API_KEY = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
AI_INTEGRATIONS_ANTHROPIC_BASE_URL = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")

CONFIDENCE_TIERS = {
    'GOLDMINE': {'min_score': 0.85, 'description': 'High confidence, validated demand'},
    'VALIDATED': {'min_score': 0.70, 'description': 'Solid opportunity with good signals'},
    'WEAK_SIGNAL': {'min_score': 0.50, 'description': 'Potential opportunity, needs validation'},
    'NOISE': {'min_score': 0.0, 'description': 'Insufficient signal strength'}
}

CITY_POPULATIONS = {
    'San Francisco': 873965,
    'New York': 8336817,
    'Los Angeles': 3979576,
    'Chicago': 2693976,
    'Boston': 692600,
    'Seattle': 749256,
    'Denver': 715522,
    'Austin': 978908,
    'Portland': 652503,
    'Miami': 442241,
    'Staten Island': 495747,
}

CATEGORY_PENETRATION = {
    'transportation': 0.40,
    'childcare': 0.25,
    'home_services': 0.30,
    'healthcare': 0.35,
    'food_beverage': 0.50,
    'restaurant': 0.50,
    'product_marketplace': 0.20,
    'service_marketplace': 0.25,
    'apartment': 0.30,
    'retail': 0.35,
    'fitness': 0.20,
    'beauty': 0.25,
    'automotive': 0.30,
    'education': 0.15,
    'financial': 0.25,
    'professional': 0.20,
    'entertainment': 0.30,
    'travel': 0.25,
    'pet_services': 0.15,
    'technology': 0.35,
    # Niche categories
    'gaming_esports': 0.15,
    'creator_economy': 0.12,
    'coaching_consulting': 0.10,
    'community_social': 0.18,
    'personal_development': 0.12,
    'hobbies_crafts': 0.08,
}

DEFAULT_PRICES = {
    'transportation': 150,
    'childcare': 1500,
    'home_services': 200,
    'product_marketplace': 50,
    'service_marketplace': 100,
    'restaurant': 30,
    'apartment': 200,
    'healthcare': 150,
    'retail': 75,
    'fitness': 100,
    'beauty': 80,
    'automotive': 250,
    'education': 200,
    'financial': 300,
    'professional': 250,
    'entertainment': 50,
    'travel': 200,
    'pet_services': 75,
    'technology': 150,
    # Niche categories
    'gaming_esports': 75,
    'creator_economy': 100,
    'coaching_consulting': 150,
    'community_social': 25,
    'personal_development': 100,
    'hobbies_crafts': 50,
}


class SignalToOpportunityProcessor:
    """
    Enhanced processor that converts raw scraped data into validated opportunities.
    Implements the 8-stage Signal-to-Opportunity algorithm.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.client = None
        if AI_INTEGRATIONS_ANTHROPIC_API_KEY and AI_INTEGRATIONS_ANTHROPIC_BASE_URL:
            self.client = Anthropic(
                api_key=AI_INTEGRATIONS_ANTHROPIC_API_KEY,
                base_url=AI_INTEGRATIONS_ANTHROPIC_BASE_URL
            )
    
    def process_scraped_data(self, limit: int = 500) -> Dict[str, Any]:
        """
        Main entry point: Process scraped_data table and generate opportunities.
        
        Pipeline stages:
        1. Load raw signals from scraped_data
        2. Apply pattern matching and scoring
        3. Cluster similar signals
        4. Extract business ideas
        5. Validate location
        6. Calculate validation score
        7. Deduplicate
        8. Estimate market size
        """
        stats = {
            'total_signals': 0,
            'passed_quality_filter': 0,
            'clusters_formed': 0,
            'opportunities_created': 0,
            'duplicates_merged': 0,
            'low_quality_processed': 0,
            'opportunities': []
        }
        
        batch_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        raw_signals = self._load_scraped_data(limit)
        stats['total_signals'] = len(raw_signals)
        
        if not raw_signals:
            return stats
        
        scored_signals = self._score_signals(raw_signals)
        high_quality = [s for s in scored_signals if s.get('signal_score', 0) >= 0.50]
        low_quality = [s for s in scored_signals if s.get('signal_score', 0) < 0.50]
        stats['passed_quality_filter'] = len(high_quality)
        
        if low_quality:
            self._mark_signals_processed(low_quality, batch_id)
            stats['low_quality_processed'] = len(low_quality)
        
        clusters = self._cluster_signals(high_quality)
        stats['clusters_formed'] = len(clusters)
        
        for cluster in clusters:
            if len(cluster) < 1:
                continue
            
            business_idea = self._extract_business_idea(cluster)
            location_data = self._validate_location(cluster)
            coverage_area = self._calculate_coverage_area(cluster, location_data)
            validation = self._validate_opportunity(business_idea, cluster, location_data)
            
            if not validation['passed']:
                self._mark_signals_processed(cluster, batch_id)
                continue
            
            existing = self._find_duplicates(business_idea)
            if existing:
                self._merge_with_existing(existing[0], cluster, validation)
                self._link_signals_to_opportunity(existing[0].id, cluster)
                self._mark_signals_processed(cluster, batch_id)
                stats['duplicates_merged'] += 1
                continue
            
            market_estimate = self._estimate_market_size(business_idea, location_data, cluster)
            opportunity = self._create_opportunity(
                business_idea, location_data, coverage_area, 
                validation, market_estimate, cluster, batch_id
            )
            
            if opportunity:
                stats['opportunities_created'] += 1
                stats['opportunities'].append({
                    'id': opportunity.id,
                    'title': opportunity.title,
                    'category': opportunity.category,
                    'city': opportunity.city,
                    'confidence_tier': validation['confidence_tier'],
                    'validation_score': validation['validation_score'],
                    'signal_count': len(cluster)
                })
        
        self.db.commit()
        
        logger.info(f"Signal processing complete: {stats['opportunities_created']} opportunities from {stats['total_signals']} signals")
        return stats
    
    def _load_scraped_data(self, limit: int) -> List[Dict]:
        """Load raw signals from scraped_data table (only unprocessed signals)"""
        query = text("""
            SELECT id, source, source_id, content_type, title, content, 
                   url, author, location, latitude, longitude, metadata, scraped_at
            FROM scraped_data
            WHERE processed = FALSE OR processed IS NULL
            ORDER BY scraped_at DESC
            LIMIT :limit
        """)
        
        result = self.db.execute(query, {"limit": limit})
        signals = []
        
        for row in result:
            metadata = row.metadata if isinstance(row.metadata, dict) else {}
            if isinstance(row.metadata, str):
                try:
                    metadata = json.loads(row.metadata)
                except:
                    metadata = {}
            
            signals.append({
                'id': f"{row.source}_{row.source_id}",
                'db_id': row.id,
                'source': row.source,
                'source_id': row.source_id,
                'content_type': row.content_type,
                'title': row.title or '',
                'text': f"{row.title or ''}\n{row.content or ''}",
                'content': row.content or '',
                'url': row.url,
                'author': row.author,
                'city': row.location or metadata.get('city', ''),
                'state': metadata.get('state', ''),
                'latitude': row.latitude,
                'longitude': row.longitude,
                'category': metadata.get('category', ''),
                'rating': metadata.get('rating'),
                'reviews_count': metadata.get('reviews_count', 0),
                'metadata': metadata,
                'scraped_at': row.scraped_at
            })
        
        return signals
    
    def _score_signals(self, signals: List[Dict]) -> List[Dict]:
        """Apply pattern matching and scoring to signals"""
        for signal in signals:
            text = signal.get('text', '') + ' ' + signal.get('content', '')
            category = self._detect_category(text, signal.get('category', ''))
            
            score = 0.5
            patterns_matched = []
            
            all_patterns = {
                'apartment': APARTMENT_PATTERNS,
                'childcare': CHILDCARE_PATTERNS,
                'restaurant': RESTAURANT_PATTERNS,
                'home_services': HOME_SERVICES_PATTERNS,
                'healthcare': HEALTHCARE_PATTERNS,
                'competitive': COMPETITIVE_PATTERNS,
            }
            
            for pattern_category, patterns in all_patterns.items():
                for pattern_name, pattern_data in patterns.items():
                    for pattern in pattern_data.get('patterns', []):
                        try:
                            if re.search(pattern, text, re.IGNORECASE):
                                patterns_matched.append({
                                    'category': pattern_category,
                                    'pattern': pattern_name,
                                    'confidence': pattern_data.get('confidence', 0.5)
                                })
                                score = max(score, pattern_data.get('confidence', 0.5))
                        except:
                            continue
            
            if signal.get('rating'):
                try:
                    rating = float(signal['rating'])
                    if rating <= 2.5:
                        score += 0.15
                    elif rating <= 3.5:
                        score += 0.05
                except (TypeError, ValueError):
                    pass
            
            reviews_count = signal.get('reviews_count') or 0
            if reviews_count >= 100:
                score += 0.10
            elif reviews_count >= 50:
                score += 0.05
            
            if signal.get('latitude') and signal.get('longitude'):
                score += 0.05
            
            signal['signal_score'] = min(1.0, score)
            signal['patterns_matched'] = patterns_matched
            signal['detected_category'] = category
        
        return signals
    
    def _detect_category(self, text: str, existing_category: str) -> str:
        """Detect business category from text and metadata"""
        text_lower = text.lower()
        existing_lower = existing_category.lower() if existing_category else ''
        
        if existing_lower in ['general', 'other', 'unknown', '']:
            existing_lower = ''
        
        category_keywords = {
            'restaurant': ['restaurant', 'food', 'dining', 'pizza', 'cafe', 'bar', 'grill', 'kitchen', 'deli', 'bakery', 'sushi', 'bistro'],
            'apartment': ['apartment', 'rental', 'lease', 'tenant', 'landlord', 'property management', 'residences', 'housing', 'realty'],
            'childcare': ['daycare', 'childcare', 'preschool', 'nursery', 'kids', 'children', 'montessori'],
            'healthcare': ['doctor', 'medical', 'clinic', 'hospital', 'dental', 'health', 'pharmacy', 'therapy', 'chiropractor'],
            'home_services': ['plumber', 'electrician', 'hvac', 'contractor', 'repair', 'cleaning', 'landscaping', 'roofing', 'pest'],
            'retail': ['store', 'shop', 'retail', 'mall', 'boutique', 'supermarket', 'grocery', 'outlet'],
            'transportation': ['parking', 'transit', 'uber', 'taxi', 'commute', 'train', 'bus', 'subway'],
            'fitness': ['gym', 'fitness', 'yoga', 'crossfit', 'workout', 'pilates', 'wellness'],
            'beauty': ['salon', 'barber', 'beauty', 'nail', 'spa', 'hair', 'grooming'],
            'automotive': ['auto', 'car', 'mechanic', 'tire', 'motor', 'vehicle', 'dealership', 'car wash'],
            'education': ['school', 'academy', 'university', 'college', 'tutor', 'learning', 'training'],
            'financial': ['bank', 'credit', 'finance', 'insurance', 'invest', 'tax', 'loan'],
            'professional': ['law', 'attorney', 'legal', 'accountant', 'consult', 'advisor'],
            'entertainment': ['theater', 'cinema', 'museum', 'amusement', 'bowling', 'arcade', 'entertainment'],
            'travel': ['hotel', 'motel', 'inn', 'resort', 'lodge', 'airbnb'],
            'pet_services': ['pet', 'vet', 'animal', 'groom', 'kennel', 'veterinary'],
            # Niche categories
            'gaming_esports': ['game', 'gaming', 'esports', 'twitch', 'stream', 'build', 'pokemon', 'console', 'playstation', 'xbox', 'nintendo', 'mmorpg', 'rpg', 'fps', 'madden', 'fifa', 'league', 'fortnite', 'valorant', 'discord'],
            'creator_economy': ['content', 'creator', 'youtube', 'influencer', 'podcast', 'streaming', 'monetize', 'subscribers', 'followers', 'tiktok', 'instagram', 'patreon', 'onlyfans', 'substack'],
            'coaching_consulting': ['coach', 'coaching', 'mentor', 'mentoring', 'consulting', 'advice', 'guidance', 'counseling', 'therapist', 'life coach', 'career coach'],
            'community_social': ['community', 'forum', 'subreddit', 'discord', 'slack', 'members', 'group', 'club', 'meetup', 'network', 'social'],
            'personal_development': ['self-improvement', 'productivity', 'habits', 'mindset', 'motivation', 'goals', 'success', 'growth', 'meditation', 'journaling', 'body image', 'confidence'],
            'hobbies_crafts': ['hobby', 'craft', 'diy', 'knitting', 'sewing', 'woodworking', 'collecting', 'vintage', 'antique', 'model', 'miniature', 'tabletop', 'board game', 'card game', 'magic gathering'],
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in existing_lower for kw in keywords):
                return category
            if any(kw in text_lower for kw in keywords):
                return category
        
        return 'retail'
    
    def _cluster_signals(self, signals: List[Dict]) -> List[List[Dict]]:
        """Group similar signals into clusters"""
        clusters = []
        processed = set()
        
        for i, signal_a in enumerate(signals):
            if signal_a['id'] in processed:
                continue
            
            cluster = [signal_a]
            processed.add(signal_a['id'])
            
            for j, signal_b in enumerate(signals):
                if i != j and signal_b['id'] not in processed:
                    similarity = self._calculate_similarity(signal_a, signal_b)
                    if similarity >= 0.55:
                        cluster.append(signal_b)
                        processed.add(signal_b['id'])
            
            clusters.append(cluster)
        
        return clusters
    
    def _calculate_similarity(self, signal_a: Dict, signal_b: Dict) -> float:
        """Calculate similarity between two signals"""
        similarity = 0.0
        
        cat_a = signal_a.get('detected_category', '')
        cat_b = signal_b.get('detected_category', '')
        if cat_a and cat_b and cat_a == cat_b:
            similarity += 0.40
        
        city_a = (signal_a.get('city') or '').lower().strip()
        city_b = (signal_b.get('city') or '').lower().strip()
        if city_a and city_b and city_a == city_b:
            similarity += 0.30
        elif signal_a.get('latitude') and signal_b.get('latitude'):
            distance = self._haversine_distance(
                signal_a['latitude'], signal_a['longitude'],
                signal_b['latitude'], signal_b['longitude']
            )
            if distance <= 25:
                similarity += 0.15
        
        keywords_a = set(signal_a.get('text', '').lower().split())
        keywords_b = set(signal_b.get('text', '').lower().split())
        if keywords_a and keywords_b:
            overlap = len(keywords_a & keywords_b)
            max_len = max(len(keywords_a), len(keywords_b))
            if max_len > 0:
                similarity += 0.20 * (overlap / max_len)
        
        date_a = signal_a.get('scraped_at')
        date_b = signal_b.get('scraped_at')
        if date_a and date_b:
            if isinstance(date_a, str):
                date_a = datetime.fromisoformat(date_a.replace('Z', '+00:00'))
            if isinstance(date_b, str):
                date_b = datetime.fromisoformat(date_b.replace('Z', '+00:00'))
            days_apart = abs((date_a - date_b).days)
            if days_apart <= 30:
                time_score = 1.0 - (days_apart / 30)
                similarity += 0.10 * time_score
        
        return similarity
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in miles"""
        R = 3959
        
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        return R * c
    
    def _extract_business_idea(self, cluster: List[Dict]) -> Dict:
        """Extract core problem and solution from signal cluster with sanitized keywords"""
        all_text = ' '.join([s.get('text', '') for s in cluster])
        
        business_names = set()
        for s in cluster:
            title = s.get('title', '')
            if title:
                for word in re.findall(r'\b\w+\b', title.lower()):
                    if len(word) > 3:
                        business_names.add(word)
        
        extended_stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'this', 'that', 'it', 'they', 'we', 'you', 'i', 'my', 'your', 'our', 'their', 'have', 'has', 'had', 'been', 'being',
            'will', 'would', 'could', 'should', 'can', 'may', 'might', 'must', 'shall', 'do', 'does', 'did', 'done',
            'here', 'there', 'where', 'when', 'what', 'which', 'who', 'whom', 'whose', 'how', 'why', 'very', 'really',
            'just', 'only', 'also', 'even', 'still', 'again', 'already', 'always', 'never', 'ever', 'often', 'sometimes',
            'about', 'above', 'after', 'before', 'between', 'into', 'through', 'during', 'without', 'within',
            'place', 'good', 'great', 'nice', 'best', 'worst', 'better', 'worse', 'more', 'most', 'less', 'least',
            'much', 'many', 'some', 'any', 'all', 'each', 'every', 'both', 'few', 'other', 'another', 'such',
            'like', 'just', 'come', 'came', 'goes', 'went', 'going', 'back', 'well', 'know', 'think', 'make', 'made',
            'time', 'year', 'years', 'day', 'days', 'week', 'weeks', 'month', 'months', 'first', 'last', 'next',
            'people', 'person', 'thing', 'things', 'something', 'nothing', 'everything', 'anything',
            'said', 'says', 'told', 'tell', 'asked', 'call', 'called', 'want', 'wanted', 'need', 'needed',
            'take', 'took', 'give', 'gave', 'find', 'found', 'look', 'looked', 'looking', 'seem', 'seemed',
            'category', 'google', 'maps', 'review', 'reviews', 'stars', 'star', 'rating', 'rated',
            'store', 'shop', 'location', 'address', 'phone', 'website', 'hours', 'open', 'closed',
            'york', 'brooklyn', 'manhattan', 'queens', 'bronx', 'staten', 'island', 'city', 'area', 'street',
            'avenue', 'road', 'drive', 'lane', 'place', 'floor', 'suite', 'unit', 'building',
            'inc', 'llc', 'corp', 'company', 'business', 'enterprise', 'group', 'services', 'service',
            'highstyle', 'style', 'high', 'home', 'long', 'away', 'okay', 'thank', 'thanks', 'please',
            'sorry', 'help', 'helped', 'helpful', 'amazing', 'awesome', 'terrible', 'horrible', 'awful',
            'definitely', 'absolutely', 'totally', 'completely', 'extremely', 'highly', 'super', 'pretty',
            'owner', 'manager', 'staff', 'team', 'employee', 'employees', 'worker', 'workers',
            'experience', 'experiences', 'visit', 'visited', 'visiting', 'went', 'been', 'tried',
            'recommend', 'recommended', 'recommends', 'suggest', 'suggested', 'love', 'loved', 'loves',
            'hate', 'hated', 'hates', 'enjoy', 'enjoyed', 'enjoys', 'felt', 'feel', 'feels', 'feeling',
            'event', 'events', 'rentals', 'rental', 'furniture', 'items', 'item', 'stuff', 'products',
            'friends', 'friend', 'family', 'families', 'everyone', 'anyone', 'someone', 'nobody'
        }
        
        words = re.findall(r'\b[a-z]+\b', all_text.lower())
        keywords = []
        for w in words:
            if len(w) < 4 or len(w) > 15:
                continue
            if w in extended_stop_words:
                continue
            if w in business_names:
                continue
            if w[0].isupper() and w not in all_text.lower():
                continue
            if re.match(r'^[0-9]+$', w):
                continue
            keywords.append(w)
        
        keyword_freq = Counter(keywords)
        top_keywords = [kw for kw, _ in keyword_freq.most_common(15)]
        
        detected_category = cluster[0].get('detected_category', 'general')
        location = cluster[0].get('city', 'Unknown')
        
        ai_analysis = self._ai_analyze_cluster_category(cluster, detected_category)
        category = ai_analysis.get('category', self._map_to_opportunity_category(detected_category))
        ai_title = ai_analysis.get('ai_title')
        primary_problem = ai_analysis.get('primary_problem')
        
        theme_keywords = {
            'apartment': ['rental', 'lease', 'tenant', 'landlord', 'maintenance', 'amenities', 'move', 'housing', 'rent', 'unit'],
            'restaurant': ['food', 'dining', 'menu', 'taste', 'portion', 'wait', 'reservation', 'cuisine', 'meal', 'order'],
            'healthcare': ['doctor', 'appointment', 'wait', 'care', 'treatment', 'staff', 'insurance', 'medical', 'patient', 'health'],
            'childcare': ['kids', 'children', 'daycare', 'program', 'staff', 'safety', 'learning', 'schedule', 'pickup', 'care'],
            'home_services': ['repair', 'install', 'plumber', 'electrician', 'contractor', 'quote', 'work', 'professional', 'quality', 'schedule'],
            'transportation': ['parking', 'traffic', 'commute', 'ride', 'driver', 'transit', 'subway', 'bus', 'train', 'uber']
        }
        
        category_themes = theme_keywords.get(category, [])
        primary_keyword = None
        for kw in top_keywords:
            if kw in category_themes:
                primary_keyword = kw
                break
        
        if not primary_keyword:
            primary_keyword = top_keywords[0] if top_keywords else category
        
        titles = [s.get('title', '') for s in cluster if s.get('title')]
        categories = [s.get('category', '') for s in cluster if s.get('category')]
        
        category_labels = {
            'apartment': 'residential housing',
            'restaurant': 'dining and food service',
            'healthcare': 'healthcare access',
            'childcare': 'childcare services',
            'home_services': 'home maintenance',
            'transportation': 'transportation and mobility',
            'general': 'local services'
        }
        category_label = category_labels.get(category, category)
        
        problem_statement = f"Market analysis reveals unmet demand for improved {primary_keyword} solutions in the {category_label} sector across {location}."
        solution_statement = f"Opportunity to address {primary_keyword} pain points for {category_label} consumers in {location}."
        
        return {
            'category': category,
            'subcategory': categories[0] if categories else None,
            'primary_keyword': primary_keyword,
            'top_keywords': top_keywords[:5],
            'location': location,
            'problem_statement': primary_problem or problem_statement,
            'solution_statement': solution_statement,
            'sample_titles': titles[:3],
            'signal_count': len(cluster),
            'ai_title': ai_title,
            'detected_category': detected_category
        }
    
    def _validate_location(self, cluster: List[Dict]) -> Dict:
        """Validate and aggregate location data from cluster"""
        locations = []
        
        for signal in cluster:
            if signal.get('city'):
                locations.append({
                    'city': signal['city'],
                    'state': signal.get('state', ''),
                    'lat': signal.get('latitude'),
                    'lng': signal.get('longitude'),
                    'confidence': 0.9 if signal.get('latitude') else 0.7
                })
        
        if not locations:
            return {
                'city': 'Unknown',
                'state': '',
                'confidence': 0.0,
                'signal_count': 0,
                'centroid': None
            }
        
        city_counts = Counter([loc['city'] for loc in locations])
        primary_city = city_counts.most_common(1)[0][0]
        
        city_locations = [loc for loc in locations if loc['city'] == primary_city]
        avg_confidence = sum(loc['confidence'] for loc in city_locations) / len(city_locations)
        
        lats = [loc['lat'] for loc in city_locations if loc.get('lat')]
        lngs = [loc['lng'] for loc in city_locations if loc.get('lng')]
        
        centroid = None
        if lats and lngs:
            centroid = {
                'lat': sum(lats) / len(lats),
                'lng': sum(lngs) / len(lngs)
            }
        
        return {
            'city': primary_city,
            'state': city_locations[0].get('state', ''),
            'confidence': avg_confidence,
            'signal_count': len(city_locations),
            'centroid': centroid
        }
    
    def _calculate_coverage_area(self, cluster: List[Dict], location_data: Dict) -> Dict:
        """Calculate geographic coverage radius"""
        points = []
        for signal in cluster:
            if signal.get('latitude') and signal.get('longitude'):
                points.append((signal['latitude'], signal['longitude']))
        
        if len(points) < 2 or not location_data.get('centroid'):
            return {
                'radius_miles': 5.0,
                'coverage_type': 'default',
                'neighborhoods': []
            }
        
        centroid = location_data['centroid']
        max_distance = 0
        for point in points:
            distance = self._haversine_distance(
                centroid['lat'], centroid['lng'],
                point[0], point[1]
            )
            max_distance = max(max_distance, distance)
        
        coverage_radius = max_distance * 1.2
        
        if len(points) >= 10:
            coverage_radius = min(coverage_radius, 10.0)
        elif len(points) >= 5:
            coverage_radius = min(coverage_radius, 15.0)
        else:
            coverage_radius = min(coverage_radius, 25.0)
        
        return {
            'radius_miles': round(max(1.0, coverage_radius), 1),
            'coverage_type': 'calculated',
            'neighborhoods': [],
            'signal_density': len(points) / (coverage_radius ** 2) if coverage_radius > 0 else 0
        }
    
    def _validate_opportunity(self, business_idea: Dict, cluster: List[Dict], location_data: Dict) -> Dict:
        """Apply validation scorecard"""
        validation = {
            'passed': False,
            'validation_score': 0.0,
            'confidence_tier': 'NOISE',
            'validation_criteria': {},
            'red_flags': [],
            'green_flags': []
        }
        
        signal_count = len(cluster)
        if signal_count >= 5:
            validation['validation_criteria']['signal_count'] = 1.0
            validation['green_flags'].append(f"{signal_count} signals (strong demand)")
        elif signal_count >= 3:
            validation['validation_criteria']['signal_count'] = 0.7
        elif signal_count >= 1:
            validation['validation_criteria']['signal_count'] = 0.4
        else:
            validation['validation_criteria']['signal_count'] = 0.0
            validation['red_flags'].append("No signals")
        
        scores = [s.get('signal_score', 0.5) for s in cluster]
        avg_score = sum(scores) / len(scores) if scores else 0.5
        validation['validation_criteria']['signal_quality'] = avg_score
        if avg_score >= 0.75:
            validation['green_flags'].append(f"High quality signals (avg {avg_score:.2f})")
        
        loc_confidence = location_data.get('confidence', 0)
        validation['validation_criteria']['location_confidence'] = loc_confidence
        if loc_confidence >= 0.85:
            validation['green_flags'].append("High location confidence")
        elif loc_confidence < 0.5:
            validation['red_flags'].append("Low location confidence")
        
        if business_idea.get('category') and business_idea['category'] != 'general':
            validation['validation_criteria']['category_identified'] = 1.0
            validation['green_flags'].append(f"Category: {business_idea['category']}")
        else:
            validation['validation_criteria']['category_identified'] = 0.3
        
        money_mentions = sum(
            1 for s in cluster
            if any(word in s.get('text', '').lower() for word in ['$', 'pay', 'cost', 'price', 'fee', 'expensive', 'afford'])
        )
        monetization_score = min(1.0, money_mentions / max(1, len(cluster)))
        validation['validation_criteria']['monetization'] = monetization_score
        if money_mentions >= 2:
            validation['green_flags'].append(f"{money_mentions} signals mention pricing")
        
        dates = [s.get('scraped_at') for s in cluster if s.get('scraped_at')]
        if dates:
            validation['validation_criteria']['time_span'] = 1.0
        else:
            validation['validation_criteria']['time_span'] = 0.5
        
        sources = set(s.get('source', '') for s in cluster)
        source_diversity = len(sources) / 3.0
        validation['validation_criteria']['source_diversity'] = min(1.0, source_diversity)
        
        weights = {
            'signal_count': 0.25,
            'signal_quality': 0.25,
            'location_confidence': 0.15,
            'category_identified': 0.10,
            'monetization': 0.15,
            'time_span': 0.05,
            'source_diversity': 0.05
        }
        
        validation_score = sum(
            validation['validation_criteria'].get(k, 0) * weights[k]
            for k in weights.keys()
        )
        
        validation['validation_score'] = round(validation_score, 2)
        
        if validation_score >= 0.85:
            validation['confidence_tier'] = 'GOLDMINE'
            validation['passed'] = True
        elif validation_score >= 0.60:
            validation['confidence_tier'] = 'VALIDATED'
            validation['passed'] = True
        elif validation_score >= 0.40:
            validation['confidence_tier'] = 'WEAK_SIGNAL'
            validation['passed'] = True
        else:
            validation['confidence_tier'] = 'NOISE'
            validation['passed'] = False
        
        return validation
    
    def _find_duplicates(self, business_idea: Dict) -> List[Opportunity]:
        """Find existing opportunities that might be duplicates"""
        category = business_idea.get('category', '')
        city = business_idea.get('location', '')
        
        if not category or not city:
            return []
        
        existing = self.db.query(Opportunity).filter(
            Opportunity.category.ilike(f"%{category}%"),
            Opportunity.city.ilike(f"%{city}%")
        ).limit(5).all()
        
        return existing
    
    def _merge_with_existing(self, existing: Opportunity, cluster: List[Dict], validation: Dict):
        """Merge new signals with existing opportunity"""
        existing.validation_count = (existing.validation_count or 0) + len(cluster)
        
        if validation['validation_score'] > (existing.ai_opportunity_score or 0) / 100:
            pass
        
        self.db.add(existing)
    
    def _estimate_market_size(self, business_idea: Dict, location_data: Dict, cluster: List[Dict]) -> Dict:
        """Estimate market potential"""
        market_size = {
            'potential_customers': None,
            'market_size_category': 'UNKNOWN',
            'revenue_potential': None,
            'competition_level': 'MEDIUM'
        }
        
        city = location_data.get('city', '')
        base_population = CITY_POPULATIONS.get(city, 500000)
        
        coverage_factor = 0.5
        reachable_population = int(base_population * coverage_factor)
        
        category = business_idea.get('category', 'general')
        penetration = CATEGORY_PENETRATION.get(category, 0.15)
        
        potential_customers = int(reachable_population * penetration)
        market_size['potential_customers'] = potential_customers
        
        if potential_customers >= 100000:
            market_size['market_size_category'] = 'LARGE'
        elif potential_customers >= 20000:
            market_size['market_size_category'] = 'MEDIUM'
        elif potential_customers >= 5000:
            market_size['market_size_category'] = 'SMALL'
        else:
            market_size['market_size_category'] = 'NICHE'
        
        avg_price = DEFAULT_PRICES.get(category, 100)
        estimated_customers = potential_customers * 0.05
        annual_revenue = int(estimated_customers * avg_price * 12)
        
        market_size['revenue_potential'] = {
            'annual_revenue_estimate': annual_revenue,
            'avg_customer_value': avg_price,
            'estimated_customers_year1': int(estimated_customers)
        }
        
        competition_keywords = ['already exists', 'similar to', 'like uber', 'competitor', 'other']
        competition_mentions = sum(
            1 for s in cluster
            if any(kw in s.get('text', '').lower() for kw in competition_keywords)
        )
        
        if competition_mentions >= 3:
            market_size['competition_level'] = 'HIGH'
        elif competition_mentions >= 1:
            market_size['competition_level'] = 'MEDIUM'
        else:
            market_size['competition_level'] = 'LOW'
        
        return market_size
    
    def _ai_analyze_cluster_category(self, cluster: List[Dict], detected_category: str) -> Dict[str, Any]:
        """Use Claude AI to analyze cluster signals and determine proper category and opportunity details"""
        
        if not self.client:
            logger.warning("Claude client not available, using keyword-based category")
            return {
                'category': self._map_to_opportunity_category(detected_category),
                'ai_title': None,
                'ai_description': None,
                'is_valid': True
            }
        
        sample_texts = []
        for s in cluster[:5]:
            text = s.get('text', s.get('content', ''))[:500]
            title = s.get('title', '')
            business_type = s.get('category', '')
            if text or title:
                sample_texts.append(f"Business: {title}\nType: {business_type}\nReview: {text}")
        
        combined_text = "\n\n---\n\n".join(sample_texts)[:3000]
        
        try:
            prompt = f"""Analyze these signals and determine the business opportunity. Look for BOTH traditional AND niche/alternative markets.

SIGNALS:
{combined_text}

DETECTED CATEGORY (from keywords): {detected_category}

Analyze the signals and return a JSON object:
{{
    "category": "One of: Technology, Health & Wellness, Money & Finance, Education & Learning, Shopping & Services, Home & Living, Transportation, Entertainment & Social, Work & Productivity, Food & Beverage, Real Estate, B2B Services, Gaming & Esports, Creator Economy, Coaching & Consulting, Community & Social, Personal Development, Hobbies & Crafts",
    "professional_title": "A clear, specific opportunity title (60-100 chars) describing what business could solve these pain points",
    "one_line_summary": "One sentence summary of the opportunity",
    "primary_problem": "The main pain point consumers are experiencing",
    "is_valid_opportunity": true (Always true - every frustrated user represents a potential customer)
}}

NICHE OPPORTUNITY RECOGNITION:
- Gaming complaints = coaching/optimization/community management services
- Content creator struggles = creator tools, monetization help, editing services
- Personal/relationship questions = coaching, counseling, advisory services
- Community management issues = moderation tools, engagement platforms
- Hobby frustrations = specialized equipment, repair services, marketplaces
- Technical setup issues = tech support, consulting services

IMPORTANT:
- Category must match one of the listed categories exactly
- Don't use generic categories like 'general' or 'local services'
- Every pain point is a business opportunity - find the angle
- Frame opportunities professionally for entrepreneurs/investors"""

            response = self.client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text.strip()
            
            if response_text.startswith('```'):
                response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)
            
            result = json.loads(response_text)
            
            return {
                'category': result.get('category', self._map_to_opportunity_category(detected_category)),
                'ai_title': result.get('professional_title'),
                'ai_description': result.get('one_line_summary'),
                'primary_problem': result.get('primary_problem'),
                'is_valid': result.get('is_valid_opportunity', True)
            }
            
        except Exception as e:
            logger.warning(f"AI cluster analysis failed: {e}")
            return {
                'category': self._map_to_opportunity_category(detected_category),
                'ai_title': None,
                'ai_description': None,
                'is_valid': True
            }
    
    def _map_to_opportunity_category(self, google_maps_category: str) -> str:
        """Map Google Maps industry categories to opportunity categories"""
        category_mapping = {
            'apartment': 'Real Estate',
            'restaurant': 'Food & Beverage',
            'healthcare': 'Health & Wellness',
            'childcare': 'Education & Learning',
            'home_services': 'Home & Living',
            'transportation': 'Transportation',
            'retail': 'Shopping & Services',
            'fitness': 'Health & Wellness',
            'beauty': 'Shopping & Services',
            'automotive': 'Transportation',
            'professional': 'B2B Services',
            'financial': 'Money & Finance',
            'entertainment': 'Entertainment & Social',
            'education': 'Education & Learning',
            'travel': 'Transportation',
            'pet_services': 'Shopping & Services',
            'general': 'Shopping & Services',
            'technology': 'Technology',
            'work': 'Work & Productivity',
            'other': 'Other',
            # Niche categories
            'gaming_esports': 'Gaming & Esports',
            'gaming': 'Gaming & Esports',
            'esports': 'Gaming & Esports',
            'creator_economy': 'Creator Economy',
            'content_creation': 'Creator Economy',
            'coaching_consulting': 'Coaching & Consulting',
            'coaching': 'Coaching & Consulting',
            'consulting': 'Coaching & Consulting',
            'community_social': 'Community & Social',
            'community': 'Community & Social',
            'personal_development': 'Personal Development',
            'self_improvement': 'Personal Development',
            'hobbies_crafts': 'Hobbies & Crafts',
            'hobbies': 'Hobbies & Crafts',
            'crafts': 'Hobbies & Crafts',
        }
        return category_mapping.get(google_maps_category.lower(), 'Shopping & Services')

    def _ai_polish_opportunity(
        self,
        title: str,
        description: str,
        business_idea: Dict,
        validation: Dict,
        market_estimate: Dict,
        city: str
    ) -> Tuple[str, str]:
        """Use AI to polish opportunity title and description into professional marketing copy"""
        
        if not self.client:
            logger.warning("Anthropic client not available, using template-based copy")
            return title, description
        
        try:
            category = business_idea.get('category', 'general')
            primary_keyword = business_idea.get('primary_keyword', 'service')
            signal_count = business_idea.get('signal_count', 1)
            confidence = validation.get('confidence_tier', 'WEAK_SIGNAL')
            market_size = market_estimate.get('market_size_category', 'Unknown')
            potential_customers = market_estimate.get('potential_customers', 0)
            competition = market_estimate.get('competition_level', 'Medium')
            
            sample_reviews = business_idea.get('sample_titles', [])[:3]
            reviews_context = "\n".join([f"- {r}" for r in sample_reviews]) if sample_reviews else "No sample reviews available"
            
            prompt = f"""You are a professional business analyst writing opportunity briefs for entrepreneurs and investors.

Analyze the underlying market signals and write a compelling business opportunity summary. Transform raw review/signal data into an actionable market opportunity.

SOURCE DATA TYPE: Consumer reviews and local business signals from {city}
CATEGORY: {category}
SIGNAL COUNT: {signal_count} data points analyzed
SAMPLE SIGNALS:
{reviews_context}

CURRENT DRAFT:
Title: {title}
Description: {description}

MARKET CONTEXT:
- Confidence tier: {confidence}
- Market size: {market_size}
- Potential customers: {potential_customers:,}
- Competition level: {competition}

YOUR TASK:
1. Identify the core consumer PAIN POINT or unmet need from the signals
2. Transform this into a clear BUSINESS OPPORTUNITY (what service/product could address this)
3. Write it like a professional market research brief

REQUIREMENTS:
1. Title: 8-12 words describing the SPECIFIC opportunity (e.g., "On-Demand Equipment Rental Service for Small Contractors in Brooklyn")
2. Description: 150-250 words with these sections:
   - Opening paragraph: What demand/pain point was identified and why it matters
   - Market Gap: What's missing in the current market
   - Opportunity: What business could fill this gap
   - Key Metrics: Include the numbers (signal count, potential customers, market size)
3. NO business names, brand names, or generic terms like "gap" or "demand" in the title
4. Be SPECIFIC about what the opportunity IS, not vague category labels
5. Write as if presenting to investors

Return ONLY valid JSON:
{{"title": "Your specific opportunity title here", "description": "Your professional description here"}}"""

            response = self.client.messages.create(
                model="claude-opus-4-5",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text.strip()
            
            if response_text.startswith('```'):
                response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)
            
            result = json.loads(response_text)
            
            polished_title = result.get('title', title)
            polished_description = result.get('description', description)
            
            if len(polished_title) < 10 or len(polished_title) > 200:
                polished_title = title
            if len(polished_description) < 50 or len(polished_description) > 3000:
                polished_description = description
                
            logger.info(f"AI polished opportunity: {polished_title[:50]}...")
            return polished_title, polished_description
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            return title, description
        except Exception as e:
            logger.warning(f"AI polish failed, using template: {e}")
            return title, description
    
    def _normalize_category_for_internal_use(self, ai_category: str) -> str:
        """Convert AI-generated category to internal category key for pricing/penetration lookups"""
        if not ai_category:
            return 'retail'
        
        ai_lower = ai_category.lower().strip()
        
        category_normalization = {
            'technology': 'technology',
            'health & wellness': 'healthcare',
            'health and wellness': 'healthcare',
            'healthcare': 'healthcare',
            'health': 'healthcare',
            'money & finance': 'financial',
            'money and finance': 'financial',
            'finance': 'financial',
            'financial': 'financial',
            'education & learning': 'education',
            'education and learning': 'education',
            'education': 'education',
            'shopping & services': 'retail',
            'shopping and services': 'retail',
            'shopping': 'retail',
            'retail': 'retail',
            'home & living': 'home_services',
            'home and living': 'home_services',
            'home': 'home_services',
            'transportation': 'transportation',
            'transport': 'transportation',
            'entertainment & social': 'entertainment',
            'entertainment and social': 'entertainment',
            'entertainment': 'entertainment',
            'work & productivity': 'professional',
            'work and productivity': 'professional',
            'productivity': 'professional',
            'food & beverage': 'restaurant',
            'food and beverage': 'restaurant',
            'food': 'restaurant',
            'real estate': 'apartment',
            'realestate': 'apartment',
            'property': 'apartment',
            'b2b services': 'professional',
            'b2b': 'professional',
            'business services': 'professional',
            'professional': 'professional',
            'other': 'retail',
            'general': 'retail',
            'fitness': 'fitness',
            'beauty': 'beauty',
            'automotive': 'automotive',
            'travel': 'travel',
            'pet services': 'pet_services',
            'pets': 'pet_services',
            # Niche categories
            'gaming & esports': 'gaming_esports',
            'gaming and esports': 'gaming_esports',
            'gaming': 'gaming_esports',
            'esports': 'gaming_esports',
            'creator economy': 'creator_economy',
            'content creation': 'creator_economy',
            'coaching & consulting': 'coaching_consulting',
            'coaching and consulting': 'coaching_consulting',
            'coaching': 'coaching_consulting',
            'consulting': 'coaching_consulting',
            'community & social': 'community_social',
            'community and social': 'community_social',
            'community': 'community_social',
            'personal development': 'personal_development',
            'self-improvement': 'personal_development',
            'hobbies & crafts': 'hobbies_crafts',
            'hobbies and crafts': 'hobbies_crafts',
            'hobbies': 'hobbies_crafts',
            'crafts': 'hobbies_crafts',
        }
        return category_normalization.get(ai_lower, 'retail')

    def _create_opportunity(
        self,
        business_idea: Dict,
        location_data: Dict,
        coverage_area: Dict,
        validation: Dict,
        market_estimate: Dict,
        cluster: List[Dict],
        batch_id: str = None
    ) -> Optional[Opportunity]:
        """Create opportunity record from processed data with professional copy"""
        
        ai_category = business_idea.get('category', 'Shopping & Services')
        category = self._normalize_category_for_internal_use(ai_category)
        primary_keyword = business_idea.get('primary_keyword', 'service')
        city = location_data.get('city', 'Unknown')
        signal_count = len(cluster)
        confidence = validation.get('confidence_tier', 'WEAK_SIGNAL')
        
        ai_title = business_idea.get('ai_title')
        
        actionable_keywords = {
            'apartment': ['property management', 'tenant services', 'rental solutions', 'housing access', 'lease services'],
            'restaurant': ['dining experience', 'food delivery', 'reservation services', 'meal prep', 'catering solutions'],
            'healthcare': ['patient care', 'appointment access', 'medical services', 'health coordination', 'wellness programs'],
            'childcare': ['daycare services', 'after-school programs', 'child supervision', 'family support', 'early education'],
            'home_services': ['home repair', 'maintenance services', 'contractor coordination', 'property upkeep', 'renovation services'],
            'transportation': ['ride services', 'parking solutions', 'commuter services', 'delivery logistics', 'mobility access'],
            'retail': ['shopping convenience', 'product availability', 'customer service', 'inventory access', 'local commerce'],
            'fitness': ['workout programs', 'gym access', 'personal training', 'wellness coaching', 'fitness classes'],
            'beauty': ['salon services', 'spa treatments', 'grooming appointments', 'beauty consultations', 'personal care'],
            'automotive': ['auto repair', 'vehicle service', 'maintenance scheduling', 'parts availability', 'car care'],
            'education': ['tutoring services', 'course access', 'skill development', 'learning programs', 'academic support'],
            'financial': ['financial planning', 'banking services', 'investment advice', 'tax preparation', 'money management'],
            'professional': ['consulting services', 'business support', 'legal assistance', 'advisory services', 'corporate solutions'],
            'entertainment': ['event booking', 'leisure activities', 'recreation access', 'entertainment venues', 'experience discovery'],
            'travel': ['accommodation booking', 'travel planning', 'hospitality services', 'tourism support', 'trip coordination'],
            'pet_services': ['pet care', 'grooming services', 'veterinary access', 'pet boarding', 'animal wellness'],
            'technology': ['tech support', 'software services', 'digital solutions', 'IT coordination', 'tech consulting'],
            'general': ['local services', 'consumer solutions', 'marketplace services', 'community needs', 'business services'],
            # Niche categories
            'gaming_esports': ['gaming coaching', 'build optimization', 'esports training', 'community management', 'streaming services'],
            'creator_economy': ['content creation', 'monetization tools', 'audience growth', 'editing services', 'creator platforms'],
            'coaching_consulting': ['life coaching', 'career guidance', 'relationship coaching', 'personal mentoring', 'advisory services'],
            'community_social': ['community building', 'moderation tools', 'engagement platforms', 'member management', 'event coordination'],
            'personal_development': ['self-improvement', 'habit coaching', 'productivity tools', 'mindset training', 'goal setting'],
            'hobbies_crafts': ['hobby supplies', 'craft services', 'collector platforms', 'repair services', 'enthusiast marketplaces']
        }
        
        category_keywords = actionable_keywords.get(category, actionable_keywords['general'])
        service_type = category_keywords[hash(primary_keyword) % len(category_keywords)]
        
        title_templates = {
            'apartment': [
                f"Property Management and Tenant Services Platform for {city}",
                f"Residential Rental Coordination Service in {city}",
                f"Housing Solutions and Lease Management for {city} Renters"
            ],
            'restaurant': [
                f"Restaurant Discovery and Reservation Platform for {city}",
                f"Food Service Booking and Delivery Coordination in {city}",
                f"Dining Experience Enhancement Service for {city} Consumers"
            ],
            'healthcare': [
                f"Healthcare Appointment and Access Coordination in {city}",
                f"Patient Care Navigation Service for {city} Residents",
                f"Medical Services Booking Platform for {city}"
            ],
            'childcare': [
                f"Childcare Discovery and Booking Service in {city}",
                f"Family Support and Daycare Coordination for {city}",
                f"Early Education and After-School Program Finder in {city}"
            ],
            'home_services': [
                f"Home Repair and Maintenance Coordination Service in {city}",
                f"Residential Contractor Matching Platform for {city}",
                f"Property Maintenance and Renovation Services in {city}"
            ],
            'transportation': [
                f"Urban Mobility and Ride Coordination Service in {city}",
                f"Commuter Solutions and Parking Services for {city}",
                f"Transportation Access Platform for {city} Residents"
            ],
            'retail': [
                f"Local Retail and Shopping Convenience Service in {city}",
                f"Product Availability and Commerce Platform for {city}",
                f"Consumer Shopping Solutions and Services in {city}"
            ],
            'fitness': [
                f"Fitness and Wellness Booking Platform for {city}",
                f"Gym and Personal Training Coordination Service in {city}",
                f"Health and Fitness Access Solutions for {city}"
            ],
            'beauty': [
                f"Beauty and Personal Care Booking Platform for {city}",
                f"Salon and Spa Appointment Coordination in {city}",
                f"Personal Grooming Services Marketplace for {city}"
            ],
            'automotive': [
                f"Auto Service and Repair Coordination Platform in {city}",
                f"Vehicle Maintenance and Care Services for {city}",
                f"Automotive Service Booking and Comparison in {city}"
            ],
            'education': [
                f"Education and Tutoring Services Platform for {city}",
                f"Learning and Skill Development Marketplace in {city}",
                f"Academic Support and Enrichment Services for {city}"
            ],
            'financial': [
                f"Financial Services and Advisory Platform for {city}",
                f"Personal Finance Solutions and Tools for {city}",
                f"Money Management and Planning Services in {city}"
            ],
            'professional': [
                f"Professional Services Marketplace for {city}",
                f"B2B Service Coordination Platform in {city}",
                f"Business Services and Consulting Finder for {city}"
            ],
            'entertainment': [
                f"Entertainment and Events Discovery Platform for {city}",
                f"Leisure Activities Booking Service in {city}",
                f"Local Entertainment and Recreation Guide for {city}"
            ],
            'travel': [
                f"Travel and Accommodation Booking Platform for {city}",
                f"Hospitality Services Coordination in {city}",
                f"Local Tourism and Visitor Services for {city}"
            ],
            'pet_services': [
                f"Pet Care and Services Platform for {city}",
                f"Pet Grooming and Veterinary Coordination in {city}",
                f"Animal Care Services Marketplace for {city}"
            ],
            'technology': [
                f"Tech Services and Solutions Platform for {city}",
                f"Technology Support and Coordination in {city}",
                f"Digital Services Marketplace for {city}"
            ],
            # Niche categories
            'gaming_esports': [
                f"Gaming Coaching and Optimization Services",
                f"Esports Training and Build Consulting Platform",
                f"Gaming Community Management and Streaming Services"
            ],
            'creator_economy': [
                f"Content Creator Tools and Monetization Platform",
                f"Creator Economy Services and Audience Growth",
                f"Digital Content Creation and Editing Services"
            ],
            'coaching_consulting': [
                f"Life Coaching and Personal Development Services",
                f"Career and Relationship Coaching Platform",
                f"Personal Mentoring and Advisory Services"
            ],
            'community_social': [
                f"Community Building and Moderation Platform",
                f"Online Community Management Services",
                f"Social Engagement and Event Coordination Tools"
            ],
            'personal_development': [
                f"Self-Improvement and Productivity Coaching",
                f"Personal Growth and Goal Setting Platform",
                f"Mindset Training and Habit Formation Services"
            ],
            'hobbies_crafts': [
                f"Hobby Enthusiast Marketplace and Services",
                f"Craft Supplies and Repair Services Platform",
                f"Collector and Enthusiast Community Services"
            ]
        }
        
        default_titles = [
            f"Local Service Coordination Platform for {city} Consumers",
            f"Consumer Solutions and Services Marketplace in {city}",
            f"Community Service Matching Platform for {city}"
        ]
        
        if ai_title and len(ai_title) >= 20:
            title = ai_title
        else:
            templates = title_templates.get(category, default_titles)
            title = random.choice(templates)
        
        market_size_cat = market_estimate.get('market_size_category', 'Unknown')
        potential_customers = market_estimate.get('potential_customers', 0)
        competition = market_estimate.get('competition_level', 'Medium')
        
        description = f"""**Market Opportunity Overview**

Consumer analysis across {signal_count} data points reveals a clear demand pattern for {primary_keyword} solutions in the {city} market. This represents a {market_size_cat.lower()} market opportunity with {competition.lower()} competition.

**Key Market Signals**
- {signal_count} consumer signals analyzed
- Confidence Level: {confidence}
- Primary demand driver: {primary_keyword}

**Market Size Estimate**
- Addressable customers: {potential_customers:,}
- Market classification: {market_size_cat}
- Competitive landscape: {competition}

**Opportunity Indicators**
{chr(10).join(['• ' + f for f in validation.get('green_flags', [])[:4]])}

**Considerations**
{chr(10).join(['• ' + f for f in validation.get('red_flags', [])[:3]]) if validation.get('red_flags') else '• No major risk factors identified'}
        """.strip()
        
        title, description = self._ai_polish_opportunity(title, description, business_idea, validation, market_estimate, city)
        
        source_ids = [s.get('source_id', s.get('id', '')) for s in cluster[:10]]
        
        revenue_data = market_estimate.get('revenue_potential', {})
        annual_rev = revenue_data.get('annual_revenue_estimate', 0)
        if annual_rev >= 1000000000:
            market_size_str = f"${annual_rev/1000000000:.1f}B"
        elif annual_rev >= 1000000:
            market_size_str = f"${annual_rev/1000000:.1f}M"
        elif annual_rev >= 1000:
            market_size_str = f"${annual_rev/1000:.0f}K"
        else:
            market_size_str = f"${annual_rev}"
        
        opportunity = Opportunity(
            title=title[:500],
            description=description[:5000],
            category=business_idea.get('category', 'General')[:100],
            subcategory=business_idea.get('subcategory'),
            severity=4 if validation['confidence_tier'] == 'GOLDMINE' else 3,
            market_size=market_estimate.get('market_size_category'),
            geographic_scope='local',
            country='USA',
            region=location_data.get('state'),
            city=location_data.get('city'),
            latitude=location_data.get('centroid', {}).get('lat') if location_data.get('centroid') else None,
            longitude=location_data.get('centroid', {}).get('lng') if location_data.get('centroid') else None,
            source_id=','.join(source_ids[:5]),
            source_platform='apify_google_maps',
            validation_count=len(cluster),
            ai_analyzed=True,
            ai_analyzed_at=datetime.utcnow(),
            ai_opportunity_score=int(validation['validation_score'] * 100),
            ai_summary=business_idea.get('problem_statement', '')[:500],
            ai_market_size_estimate=market_size_str,
            ai_competition_level=market_estimate.get('competition_level', 'medium').lower(),
            ai_urgency_level='high' if validation['confidence_tier'] == 'GOLDMINE' else 'medium',
            ai_target_audience=f"{business_idea['category']} consumers in {location_data['city']}",
            ai_pain_intensity=7 if validation['confidence_tier'] == 'GOLDMINE' else 5,
            ai_business_model_suggestions=json.dumps([
                f"{business_idea['category']} service platform",
                "Subscription model",
                "Marketplace/aggregator"
            ]),
            ai_key_risks=json.dumps([
                "Local market competition",
                "Customer acquisition cost",
                "Regulatory requirements"
            ]),
            ai_next_steps=json.dumps([
                f"Interview {business_idea['category']} consumers in {location_data['city']}",
                "Analyze competitor pricing",
                "Build MVP landing page"
            ]),
            ai_problem_statement=business_idea.get('problem_statement'),
            status='active'
        )
        
        self.db.add(opportunity)
        self.db.flush()
        
        self._link_signals_to_opportunity(opportunity.id, cluster)
        self._mark_signals_processed(cluster, batch_id)
        
        return opportunity
    
    def _link_signals_to_opportunity(self, opportunity_id: int, signals: List[Dict]) -> None:
        """Create links between opportunity and its source signals"""
        batch_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        for signal in signals:
            db_id = signal.get('db_id')
            if not db_id:
                continue
            
            try:
                insert_query = text("""
                    INSERT INTO opportunity_signals (opportunity_id, scraped_data_id, contribution_score, matched_pattern)
                    VALUES (:opp_id, :signal_id, :score, :pattern)
                    ON CONFLICT (opportunity_id, scraped_data_id) DO NOTHING
                """)
                
                pattern = None
                if signal.get('patterns_matched'):
                    pattern = signal['patterns_matched'][0].get('pattern', '') if signal['patterns_matched'] else None
                
                self.db.execute(insert_query, {
                    'opp_id': opportunity_id,
                    'signal_id': db_id,
                    'score': signal.get('signal_score', 0.5),
                    'pattern': pattern[:200] if pattern else None
                })
            except Exception as e:
                logger.warning(f"Failed to link signal {db_id} to opportunity {opportunity_id}: {e}")
    
    def _mark_signals_processed(self, signals: List[Dict], batch_id: str = None) -> None:
        """Mark signals as processed in scraped_data table"""
        db_ids = [s.get('db_id') for s in signals if s.get('db_id')]
        
        if not db_ids:
            return
        
        if not batch_id:
            batch_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        try:
            update_query = text("""
                UPDATE scraped_data 
                SET processed = TRUE, processed_at = :now, processing_batch_id = :batch_id
                WHERE id = ANY(:ids)
            """)
            
            self.db.execute(update_query, {
                'now': datetime.utcnow(),
                'ids': db_ids,
                'batch_id': batch_id
            })
        except Exception as e:
            logger.warning(f"Failed to mark signals as processed: {e}")


def get_signal_processor(db: Session) -> SignalToOpportunityProcessor:
    """Factory function to get signal processor instance"""
    return SignalToOpportunityProcessor(db)
