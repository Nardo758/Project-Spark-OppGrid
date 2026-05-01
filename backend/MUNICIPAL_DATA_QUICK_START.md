# Municipal Data Client - Quick Start

Get up and running with the Municipal Data API Client in 5 minutes.

## Installation

The client uses only standard dependencies (already in requirements.txt):
- `httpx` - Async HTTP client
- `pydantic` - Data validation

No additional installation needed!

## Basic Usage

### 1. Query Supply Metrics

```python
from app.services.municipal_data import MunicipalDataClient

async def check_market():
    client = MunicipalDataClient()
    
    # Query Miami self-storage supply
    result = await client.query_facilities(
        metro="Miami",
        state="FL",
        industry="self-storage",
    )
    
    if result.success:
        metrics = result.metrics
        print(f"Metro: {metrics.metro}")
        print(f"Facilities: {metrics.total_facilities}")
        print(f"Total Sq Ft: {metrics.total_building_sqft:,}")
        print(f"Supply: {metrics.sqft_per_capita:.2f} sqft/capita")
        print(f"Verdict: {metrics.verdict}")  # oversaturated/balanced/undersaturated
    else:
        print(f"Error: {result.error}")
    
    await client.close()

# Run in async context
import asyncio
asyncio.run(check_market())
```

**Output:**
```
Metro: miami
Facilities: 145
Total Sq Ft: 3,500,000
Supply: 5.74 sqft/capita
Verdict: balanced
```

### 2. Check Multiple Metros

```python
async def check_all_metros():
    client = MunicipalDataClient()
    
    metros = [
        ("Miami", "FL"),
        ("Chicago", "IL"),
        ("NYC", "NY"),
        ("Seattle", "WA"),
        ("Denver", "CO"),
    ]
    
    for metro, state in metros:
        result = await client.query_facilities(
            metro=metro,
            state=state,
            industry="self-storage",
        )
        
        if result.success:
            v = result.metrics.verdict
            sqft = result.metrics.sqft_per_capita
            print(f"{metro:12} | {sqft:5.2f} sqft/capita | {v}")
        else:
            print(f"{metro:12} | ERROR: {result.error}")
    
    await client.close()
```

**Output:**
```
Miami        |  5.74 sqft/capita | balanced
Chicago      |  8.51 sqft/capita | oversaturated
NYC          |  5.94 sqft/capita | balanced
Seattle      |  5.48 sqft/capita | balanced
Denver       |  5.86 sqft/capita | balanced
```

### 3. Interpret Results

```python
from app.services.municipal_data.industry_analyzers import SelfStorageAnalyzer
from app.services.municipal_data.schemas import SupplyVerdict

async def interpret_market():
    client = MunicipalDataClient()
    analyzer = SelfStorageAnalyzer()
    
    result = await client.query_facilities(
        metro="Miami",
        state="FL",
        industry="self-storage",
    )
    
    if result.success:
        metrics = result.metrics
        interpretation = analyzer.get_interpretation(metrics)
        print(interpretation)
    
    await client.close()
```

**Output:**
```
This market is BALANCED with 5.74 sqft per capita (within the 5.0-7.0 range). 
Healthy competitive environment.
```

## Integration with Identify Location Service

### In `identify_location_service.py`

```python
from app.services.municipal_data import MunicipalDataClient
from app.services.municipal_data.schemas import SupplyVerdict

class IdentifyLocationService:
    def __init__(self, db: Session):
        self.db = db
        self.municipal_client = MunicipalDataClient()
    
    async def identify_location(self, category: str, target_market: TargetMarket, ...):
        # ... existing candidate discovery logic ...
        
        # For each candidate, weight by supply
        for candidate in candidates:
            supply = await self.municipal_client.query_facilities(
                metro=candidate.metro,
                state=candidate.state,
                industry="self-storage",  # or from category mapping
            )
            
            if supply.success:
                # Apply supply weighting
                if supply.metrics.verdict == SupplyVerdict.UNDERSATURATED:
                    weight = 1.5  # Boost score for growth opportunities
                elif supply.metrics.verdict == SupplyVerdict.BALANCED:
                    weight = 1.0  # No change
                else:  # OVERSATURATED
                    weight = 0.5  # Reduce score for saturated markets
                
                candidate.overall_score *= weight
                candidate.supply_metrics = supply.metrics
        
        # Sort by weighted score
        candidates.sort(key=lambda c: c.overall_score, reverse=True)
        
        return candidates
```

## API Reference

### MunicipalDataClient

#### `query_facilities()`

Main method to query supply metrics.

```python
result = await client.query_facilities(
    metro="Miami",           # Required: Metro name
    state="FL",              # Required: State code
    industry="self-storage", # Required: Industry code
    population=None,         # Optional: Override Census population
    dataset_id=None,         # Optional: Socrata dataset ID
    use_cache=True,          # Optional: Use caching (default True)
    force_refresh=False,     # Optional: Bypass cache (default False)
)
```

**Returns:** `MunicipalQueryResult`

```python
result = MunicipalQueryResult(
    success=True,            # Query succeeded
    metro="miami",           # Normalized metro name
    state="FL",              # State code
    industry="self-storage", # Industry code
    metrics=FacilitySupplyMetrics(...),
    error=None,              # Error message if failed
    fallback_used=False,     # Whether fallback data was used
    request_id="abc123",     # Unique request ID
)
```

#### `list_supported_metros()`

```python
# All metros
metros = client.list_supported_metros()
# ['denver', 'miami', 'chicago', 'nyc', 'seattle']

# For specific industry
metros = client.list_supported_metros("self-storage")
# ['denver', 'miami', 'chicago', 'nyc', 'seattle']
```

#### `list_supported_industries()`

```python
industries = client.list_supported_industries()
# ['self-storage']
```

#### `is_configured()`

```python
configured = client.is_configured("self-storage", "miami")
# True
```

#### `get_cache_stats()`

```python
stats = await client.get_cache_stats()
# {
#     'hits': 10,
#     'misses': 2,
#     'hit_rate': 0.833,
#     'sets': 5,
#     'deletes': 0,
#     'size': 5,
# }
```

### FacilitySupplyMetrics

Result metrics object.

```python
metrics = result.metrics

metrics.metro                      # str: "miami"
metrics.state                      # str: "FL"
metrics.industry                   # str: "self-storage"
metrics.total_facilities           # int: 145
metrics.total_building_sqft        # int: 3,500,000
metrics.population                 # int: 6,091,747
metrics.sqft_per_capita            # float: 5.74
metrics.facilities_per_100k_population  # float: 2380
metrics.verdict                    # SupplyVerdict: "balanced"
metrics.benchmark_sqft_per_capita  # float: 7.0
metrics.confidence                 # float: 0.95
metrics.data_source                # str: "socrata"
metrics.coverage_percentage        # float: 100.0
metrics.last_updated               # datetime
metrics.query_time_ms              # int: 234
```

### SupplyVerdict

Enum for supply levels.

```python
from app.services.municipal_data.schemas import SupplyVerdict

SupplyVerdict.OVERSATURATED      # > 7.0 sqft/capita
SupplyVerdict.BALANCED            # 5.0-7.0 sqft/capita
SupplyVerdict.UNDERSATURATED     # < 5.0 sqft/capita
SupplyVerdict.UNKNOWN             # Insufficient data
```

## Supported Metros & Industries

### Self-Storage

| Metro | State | Population | Land Use Code | Status |
|-------|-------|-----------|---|--------|
| Miami | FL | 6,091,747 | 39 | ✅ Verified |
| Chicago | IL | 9,618,502 | 516 | ✅ Verified |
| NYC | NY | 20,201,249 | D4, E0, E1, E2 | ✅ Verified |
| Seattle | WA | 4,018,762 | WM | ⚠️ Unverified |
| Denver | CO | 3,154,794 | U3 | ⚠️ Unverified |

## Caching

Queries are cached for 7 days by default.

### Enable Caching (Default)

```python
result = await client.query_facilities(
    metro="Miami",
    state="FL",
    industry="self-storage",
    use_cache=True,  # Default
)
# First request: ~2-5 seconds (Socrata query)
# Cached requests: <200ms (memory lookup)
```

### Disable Caching

```python
result = await client.query_facilities(
    metro="Miami",
    state="FL",
    industry="self-storage",
    use_cache=False,  # Always query
)
```

### Force Refresh

```python
result = await client.query_facilities(
    metro="Miami",
    state="FL",
    industry="self-storage",
    force_refresh=True,  # Bypass cache, query live
)
```

## Error Handling

```python
result = await client.query_facilities(
    metro="Unknown",
    state="XX",
    industry="self-storage",
)

if not result.success:
    print(f"Error: {result.error}")
    # Error: Land use mapping error: Metro 'unknown' not configured...
```

## Performance Tips

1. **Enable caching** (default) for best performance
2. **Batch queries** if checking multiple metros
3. **Check `cache_stats()`** to monitor hit rate
4. **Use `is_configured()`** before querying unknown metros
5. **Call `close()`** when done to clean up resources

## Troubleshooting

### Error: "Metro 'xyz' not configured"

Ensure metro name is in the [Supported Metros](#supported-metros--industries) list. Use exact names:
- ✅ "Miami" not "Miami-Dade"
- ✅ "NYC" not "New York"
- ✅ "Chicago" not "Chicago, IL"

### Error: "Industry 'xyz' not supported"

Currently only "self-storage" is supported. More industries coming soon!

### Slow first request

Normal! First request queries Socrata API (~2-5 seconds). Subsequent requests hit cache (<200ms).

### Cache not working

Check cache stats:
```python
stats = await client.get_cache_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
```

If hit rate is 0%, cache may be disabled. Check `use_cache=True`.

## Examples

### Find Undersaturated Markets

```python
async def find_growth_opportunities():
    client = MunicipalDataClient()
    opportunities = []
    
    for metro in client.list_supported_metros("self-storage"):
        result = await client.query_facilities(
            metro=metro.title(),
            state="?",  # Map metro to state
            industry="self-storage",
        )
        
        if result.success and result.metrics.verdict == SupplyVerdict.UNDERSATURATED:
            opportunities.append({
                'metro': metro,
                'sqft_per_capita': result.metrics.sqft_per_capita,
                'facilities': result.metrics.total_facilities,
            })
    
    # Sort by lowest supply (most opportunity)
    opportunities.sort(key=lambda x: x['sqft_per_capita'])
    
    print("Growth Opportunities (lowest to highest supply):")
    for opp in opportunities:
        print(f"  {opp['metro']:12} | {opp['sqft_per_capita']:.2f} sqft/capita | {opp['facilities']} facilities")
    
    await client.close()
```

### Compare Markets

```python
async def compare_markets():
    client = MunicipalDataClient()
    
    results = {}
    for metro in ["Miami", "Chicago", "NYC"]:
        result = await client.query_facilities(
            metro=metro,
            state="?",
            industry="self-storage",
        )
        if result.success:
            results[metro] = result.metrics
    
    # Find most/least saturated
    sorted_metros = sorted(
        results.items(),
        key=lambda x: x[1].sqft_per_capita
    )
    
    print(f"Most undersaturated: {sorted_metros[0][0]} ({sorted_metros[0][1].sqft_per_capita:.2f})")
    print(f"Most oversaturated: {sorted_metros[-1][0]} ({sorted_metros[-1][1].sqft_per_capita:.2f})")
    
    await client.close()
```

## Next Steps

- Read [Architecture Guide](./MUNICIPAL_DATA_ARCHITECTURE.md)
- Check [Test Suite](../tests/test_municipal_data_client.py)
- Integrate with [Identify Location Service](./IDENTIFY_LOCATION_SYSTEM.md)
