# Municipal Data Integration Guide - Identify Location Service

This guide shows how to integrate the Municipal Data API Client with the Identify Location Service to weight candidates by supply metrics.

## Overview

The Municipal Data Client provides real supply metrics from government data. These metrics weight candidate locations by:
- **Undersaturated markets** (< 5.0 sqft/capita): 1.5x boost
- **Balanced markets** (5.0-7.0 sqft/capita): 1.0x (no change)
- **Oversaturated markets** (> 7.0 sqft/capita): 0.5x penalty

This ensures candidates in growth-opportunity markets are favored.

## Integration Steps

### 1. Add Municipal Data Client to IdentifyLocationService

```python
# File: app/services/success_profile/identify_location_service.py

from app.services.municipal_data import MunicipalDataClient
from app.services.municipal_data.schemas import SupplyVerdict

class IdentifyLocationService:
    def __init__(self, db: Session):
        self.db = db
        self.catalog = MicroMarketCatalog(db)
        self.gap_engine = GapDiscoveryEngine(db)
        self.profile_builder = CandidateProfileBuilder(db)
        
        # ADD THIS LINE:
        self.municipal_client = MunicipalDataClient()
    
    # Add cleanup method
    async def close(self):
        """Clean up resources"""
        await self.municipal_client.close()
```

### 2. Create Industry Mapping

Map your service categories to municipal data industries:

```python
# File: app/services/success_profile/identify_location_service.py

CATEGORY_TO_INDUSTRY_MAPPING = {
    "self_storage": "self-storage",
    "mini_storage": "self-storage",
    "storage_facility": "self-storage",
    # Add more as industries are supported
}

def _get_industry_code(self, category: str) -> str:
    """Map service category to municipal industry code"""
    industry = CATEGORY_TO_INDUSTRY_MAPPING.get(category.lower())
    if not industry:
        return None  # No municipal data for this industry yet
    return industry
```

### 3. Add Supply Weighting to Candidate Profiling

Modify the `identify_location()` method to weight candidates:

```python
async def identify_location(
    self,
    category: str,
    target_market: TargetMarket,
    business_description: Optional[str] = None,
    market_boundary: Optional[MarketBoundary] = None,
    archetype_preference: Optional[List[str]] = None,
    include_gap_discovery: bool = True,
    user_tier: UserTier = UserTier.FREE,
    user_id: Optional[int] = None,
) -> IdentifyLocationResult:
    """
    Main identify location orchestrator with supply metrics.
    """
    import time
    start_time = time.time()
    
    try:
        request_id = str(uuid.uuid4())
        
        # Check cache (existing code)
        cached_result = self._get_cached_result(
            category, target_market, market_boundary
        )
        if cached_result:
            logger.info(f"Cache hit for request {request_id}")
            return cached_result
        
        # Tier validation (existing code)
        tier_config = self.TIER_LIMITS.get(user_tier, self.TIER_LIMITS[UserTier.FREE])
        should_include_gaps = include_gap_discovery and tier_config["include_gaps"]
        
        # Discover candidates (existing code)
        named_candidates = self._discover_named_markets(target_market, market_boundary)
        gap_candidates = []
        if should_include_gaps:
            gap_candidates = self._discover_gaps(target_market, category)
        
        logger.info(f"Found {len(named_candidates)} named, {len(gap_candidates)} gap candidates")
        
        # Merge candidates
        all_candidates = self._merge_candidates(named_candidates, gap_candidates)
        
        # NEW: Apply supply weighting
        all_candidates = await self._apply_supply_weighting(all_candidates, category)
        
        # Filter by archetype preference (existing code)
        if archetype_preference:
            all_candidates = self._filter_by_archetype_preference(
                all_candidates, archetype_preference
            )
        
        # Group by archetype (existing code)
        grouped = self._group_by_archetype(all_candidates)
        
        # Apply tier limits (existing code)
        limited_groups = self._apply_tier_limits(grouped, tier_config)
        
        # ... rest of method unchanged ...
```

### 4. Implement Supply Weighting Method

Add this method to IdentifyLocationService:

```python
async def _apply_supply_weighting(
    self,
    candidates: List[CandidateProfile],
    category: str
) -> List[CandidateProfile]:
    """
    Weight candidates by supply metrics from municipal data.
    
    Weights:
    - Undersaturated: 1.5x (growth opportunity)
    - Balanced: 1.0x (no change)
    - Oversaturated: 0.5x (high competition)
    
    Args:
        candidates: List of candidate profiles
        category: Service category (e.g., "self_storage")
    
    Returns:
        Weighted candidates with supply metrics attached
    """
    
    # Get industry mapping
    industry = CATEGORY_TO_INDUSTRY_MAPPING.get(category.lower())
    if not industry:
        logger.warning(f"No industry mapping for category '{category}'")
        return candidates  # Return unweighted
    
    weighted_candidates = []
    
    for candidate in candidates:
        try:
            # Query supply metrics for candidate's metro
            supply_result = await self.municipal_client.query_facilities(
                metro=candidate.metro,
                state=candidate.state,
                industry=industry,
            )
            
            # Determine weight based on verdict
            supply_weight = 1.0  # Default
            
            if supply_result.success and supply_result.metrics:
                verdict = supply_result.metrics.verdict
                
                if verdict == SupplyVerdict.UNDERSATURATED:
                    supply_weight = 1.5
                    supply_impact = "Growth opportunity"
                elif verdict == SupplyVerdict.BALANCED:
                    supply_weight = 1.0
                    supply_impact = "Healthy market"
                elif verdict == SupplyVerdict.OVERSATURATED:
                    supply_weight = 0.5
                    supply_impact = "High competition"
                else:
                    supply_weight = 1.0
                    supply_impact = "Unknown"
                
                # Attach supply metrics to candidate
                candidate.supply_metrics = {
                    "verdict": supply_result.metrics.verdict,
                    "sqft_per_capita": supply_result.metrics.sqft_per_capita,
                    "total_facilities": supply_result.metrics.total_facilities,
                    "impact": supply_impact,
                    "weight": supply_weight,
                    "confidence": supply_result.metrics.confidence,
                }
                
                logger.info(
                    f"Supply weighting: {candidate.location_name} "
                    f"({candidate.metro}) → {supply_impact} ({supply_weight}x)"
                )
            else:
                logger.warning(
                    f"No supply data for {candidate.metro}, {candidate.state}: "
                    f"{supply_result.error}"
                )
                candidate.supply_metrics = {
                    "weight": 1.0,
                    "impact": "No data",
                }
            
            # Apply weight to overall score
            candidate.overall_score *= supply_weight
            candidate.supply_weight = supply_weight
            
            weighted_candidates.append(candidate)
        
        except Exception as e:
            logger.error(
                f"Error applying supply weighting to {candidate.location_name}: {e}"
            )
            # Continue with unweighted candidate
            candidate.supply_weight = 1.0
            weighted_candidates.append(candidate)
    
    return weighted_candidates
```

### 5. Update CandidateProfile Schema

Add supply weighting fields to the CandidateProfile (if not already present):

```python
# File: app/schemas/identify_location.py

from typing import Optional, Dict, Any

class CandidateProfile(BaseModel):
    # ... existing fields ...
    
    # NEW: Supply metrics
    supply_metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Municipal supply metrics for this location"
    )
    
    supply_weight: Optional[float] = Field(
        default=1.0,
        description="Supply-based weighting factor (0.5-1.5)"
    )
```

### 6. Update Response Schema

Include supply metrics in the response:

```python
# File: app/schemas/identify_location.py

class IdentifyLocationResult(BaseModel):
    # ... existing fields ...
    
    # NEW: Data quality note
    data_quality: Dict[str, Any] = Field(
        default_factory=lambda: {
            "sources": ["micro_market_catalog", "foot_traffic_api", "census_data", "business_database", "municipal_data"],
            "coverage": "high",
        }
    )
```

## Usage Examples

### Example 1: Basic Integration

```python
# In your FastAPI endpoint or service

from app.services.success_profile.identify_location_service import IdentifyLocationService

async def get_location_candidates(
    category: str,
    metro: str,
    state: str,
    db: Session
):
    service = IdentifyLocationService(db)
    
    try:
        result = await service.identify_location(
            category=category,
            target_market=TargetMarket(
                market_type=TargetMarketType.METRO,
                metro=metro,
                state=state,
            ),
            user_tier=UserTier.BUILDER,
            include_gap_discovery=True,
        )
        
        # Candidates are now weighted by supply metrics
        return result
    
    finally:
        await service.close()
```

### Example 2: Display Supply Metrics to User

```python
# In your response formatting

def format_candidate_for_display(candidate: CandidateProfile) -> Dict:
    """Format candidate with supply metrics for display"""
    
    result = {
        "location_name": candidate.location_name,
        "metro": candidate.metro,
        "state": candidate.state,
        "score": candidate.overall_score,
        "archetype": candidate.archetype,
    }
    
    # Add supply metrics if available
    if candidate.supply_metrics:
        metrics = candidate.supply_metrics
        result["supply_analysis"] = {
            "verdict": metrics.get("verdict"),
            "sqft_per_capita": metrics.get("sqft_per_capita"),
            "impact": metrics.get("impact"),
            "confidence": f"{metrics.get('confidence', 0.0):.0%}",
        }
    
    return result
```

### Example 3: Conditional Logic Based on Supply

```python
async def should_include_candidate(
    candidate: CandidateProfile,
    minimum_score: float = 70.0,
    exclude_oversaturated: bool = False
) -> bool:
    """
    Determine if candidate should be included based on
    score and supply constraints.
    """
    
    # Check score
    if candidate.overall_score < minimum_score:
        return False
    
    # Check supply (if enabled)
    if exclude_oversaturated and candidate.supply_metrics:
        verdict = candidate.supply_metrics.get("verdict")
        if verdict == "oversaturated":
            return False
    
    return True
```

## Testing the Integration

### Unit Test

```python
# tests/test_identify_location_with_supply.py

import pytest
from app.services.success_profile.identify_location_service import IdentifyLocationService
from app.schemas.identify_location import TargetMarket, TargetMarketType, UserTier

@pytest.mark.asyncio
async def test_identify_location_with_supply_weighting(db):
    """Test that supply metrics are applied"""
    
    service = IdentifyLocationService(db)
    
    result = await service.identify_location(
        category="self_storage",
        target_market=TargetMarket(
            market_type=TargetMarketType.METRO,
            metro="Miami",
            state="FL",
        ),
        user_tier=UserTier.BUILDER,
        include_gap_discovery=True,
    )
    
    # Check that candidates have supply metrics
    for group in result.candidates_by_archetype:
        for candidate in group.candidates:
            assert hasattr(candidate, 'supply_metrics')
            assert hasattr(candidate, 'supply_weight')
    
    await service.close()
```

### Integration Test

```python
@pytest.mark.asyncio
async def test_supply_weighting_affects_ranking(db):
    """Test that supply weighting changes candidate ranking"""
    
    service = IdentifyLocationService(db)
    
    result = await service.identify_location(
        category="self_storage",
        target_market=TargetMarket(
            market_type=TargetMarketType.METRO,
            metro="Miami",
            state="FL",
        ),
        user_tier=UserTier.SCALER,
    )
    
    # Check that candidates are sorted by weighted score
    all_candidates = []
    for group in result.candidates_by_archetype:
        all_candidates.extend(group.candidates)
    
    # Verify ordering
    for i in range(len(all_candidates) - 1):
        assert all_candidates[i].overall_score >= all_candidates[i+1].overall_score
    
    await service.close()
```

## Monitoring & Debugging

### Check Cache Stats

```python
# In your monitoring/debugging code

service = IdentifyLocationService(db)

# Get municipal data cache stats
stats = await service.municipal_client.get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate']:.1%}")
print(f"Cache size: {stats['size']} entries")
```

### Log Supply Weighting

```python
# Adjust logging level in identify_location_service.py

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Shows supply weighting logs
```

### Verify Supported Industries

```python
# Check if category has industry mapping

service = IdentifyLocationService(db)

# Check what's available
industries = service.municipal_client.list_supported_industries()
print(f"Supported industries: {industries}")
# Output: ['self-storage']

# Check metros
metros = service.municipal_client.list_supported_metros('self-storage')
print(f"Metros with self-storage data: {metros}")
# Output: ['denver', 'chicago', 'miami', 'nyc', 'seattle']
```

## Performance Considerations

### Caching

Municipal data queries are cached for 7 days:
- **First request per metro**: ~2-5 seconds (Socrata query)
- **Cached requests**: <200ms (memory lookup)

### Batch Queries

When processing multiple candidates in different metros:

```python
# Good: Parallel queries (sorted by metro for cache efficiency)
candidates_by_metro = {}
for candidate in candidates:
    key = (candidate.metro, candidate.state)
    if key not in candidates_by_metro:
        candidates_by_metro[key] = []
    candidates_by_metro[key].append(candidate)

# Query once per unique metro
for (metro, state), metro_candidates in candidates_by_metro.items():
    result = await municipal_client.query_facilities(metro, state, industry)
    weight = get_weight(result)
    for candidate in metro_candidates:
        candidate.overall_score *= weight
```

### Rate Limiting

Socrata API has rate limits. The client respects these with:
- 0.1s delay between requests
- 30s request timeout
- Exponential backoff for rate limit responses (429)

## Troubleshooting

### Supply metrics not appearing

1. **Check industry mapping:**
   ```python
   industry = CATEGORY_TO_INDUSTRY_MAPPING.get(category.lower())
   if not industry:
       print(f"No industry mapping for '{category}'")
   ```

2. **Check municipality support:**
   ```python
   metros = municipal_client.list_supported_metros(industry)
   if metro not in metros:
       print(f"{metro} not supported for {industry}")
   ```

3. **Check logs:**
   ```python
   logger.setLevel(logging.DEBUG)
   # Look for "Supply weighting:" messages
   ```

### Performance degradation

1. **Monitor cache hit rate:**
   ```python
   stats = await municipal_client.get_cache_stats()
   if stats['hit_rate'] < 0.5:
       print("Low cache hit rate - check TTL")
   ```

2. **Batch queries by metro** to maximize cache hits

3. **Disable supply weighting** if performance is critical:
   ```python
   # In identify_location()
   all_candidates = self._merge_candidates(named_candidates, gap_candidates)
   # Skip: all_candidates = await self._apply_supply_weighting(...)
   ```

## Next Steps

1. [Quick Start Guide](./MUNICIPAL_DATA_QUICK_START.md)
2. [Architecture Overview](./MUNICIPAL_DATA_ARCHITECTURE.md)
3. Add support for more industries (retail, hospitality, etc.)
4. Verify Seattle & Denver land use codes
5. Set up Redis caching for production
