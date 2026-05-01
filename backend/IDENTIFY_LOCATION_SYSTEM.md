# Identify Location Service - Implementation Guide

## Overview

The Identify Location Service is an advanced location discovery system for the OppGrid Consultant Studio Success Profile System. It helps users find optimal locations for their business ideas by combining two tiers of market analysis:

- **Tier A: Named Micro-Markets** - Curated, hand-picked neighborhoods and districts in top metros
- **Tier B: Gap Discovery** - AI-powered white-space identification using H3 hex grid analysis

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│         Identify Location Service (Orchestrator)         │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ├─ MicroMarketCatalog (Tier A)                         │
│  │  └─ Named Markets Database                           │
│  │     └─ 10 Metros × 5-15 Markets = ~100 Markets      │
│  │                                                       │
│  ├─ GapDiscoveryEngine (Tier B)                         │
│  │  └─ H3 Hex Grid (Resolution 8)                       │
│  │     └─ White-space Detection                         │
│  │        └─ Reverse Geocoding                          │
│  │                                                       │
│  ├─ CandidateProfileBuilder                            │
│  │  └─ 3-Signal Classification                          │
│  │     ├─ Foot Traffic Growth                           │
│  │     ├─ Demographic Fit                               │
│  │     └─ Competition Density                           │
│  │                                                       │
│  ├─ Archetype Classification Engine                     │
│  │  └─ 5 Archetypes:                                    │
│  │     ├─ Pioneer (emerging, low competition)           │
│  │     ├─ Mainstream (established, proven demand)       │
│  │     ├─ Specialist (niche, high-margin)               │
│  │     ├─ Anchor (destination-driver)                   │
│  │     └─ Experimental (test market)                    │
│  │                                                       │
│  └─ Cache & Storage                                     │
│     ├─ 7-Day Result Cache                               │
│     ├─ Success Profile Storage                          │
│     └─ Micro-Market Database                            │
└─────────────────────────────────────────────────────────┘
```

## API Endpoints

### 1. POST /api/consultant-studio/identify-location/search

Main search endpoint combining Tier A + B.

**Request:**
```json
{
  "category": "coffee_shop_premium",
  "business_description": "Upscale coffee with seating and WiFi",
  "target_market": {
    "market_type": "metro",
    "metro": "Miami",
    "state": "FL",
    "radius_miles": 10
  },
  "market_boundary": null,
  "archetype_preference": ["mainstream", "specialist"],
  "include_gap_discovery": true
}
```

**Response:**
```json
{
  "request_id": "uuid",
  "category": "coffee_shop_premium",
  "target_market": {...},
  "benchmark_summary": {
    "category": "coffee_shop_premium",
    "typical_archetypes": ["mainstream", "specialist"],
    "total_addressable_population": 10000000
  },
  "candidates_by_archetype": [
    {
      "archetype": "mainstream",
      "archetype_description": "...",
      "candidate_count": 5,
      "candidates": [...],
      "avg_score": 82.5,
      "score_range": {"min": 75, "max": 90}
    }
  ],
  "total_candidates": 25,
  "tier": "builder",
  "candidates_shown": 10,
  "candidates_limited": true,
  "map_data": {
    "type": "FeatureCollection",
    "center": {"latitude": 25.7617, "longitude": -80.1918},
    "features": [...]
  },
  "processing_time_ms": 2150,
  "named_markets_included": true,
  "gap_markets_included": true
}
```

**Performance:** < 12 seconds

### 2. GET /api/consultant-studio/identify-location/{request_id}

Retrieve cached result.

**Response:** Same as search endpoint

**TTL:** 7 days

### 3. GET /api/consultant-studio/identify-location/{request_id}/candidate/{candidate_id}

Get detailed candidate profile.

**Response:**
```json
{
  "candidate": {
    "candidate_id": "named_market_1_coffee_shop_premium",
    "location_name": "Brickell, Miami",
    "latitude": 25.7685,
    "longitude": -80.1922,
    "archetype": "mainstream",
    "archetype_confidence": 0.87,
    "measured_signals": [
      {
        "signal_name": "foot_traffic_score",
        "signal_value": 82.5,
        "percentile_rank": 85,
        "confidence": 0.85,
        "data_source": "foot_traffic_api"
      },
      ...
    ],
    "overall_score": 84.2
  },
  "demographics": {...},
  "local_competition": [...],
  "foot_traffic_trend": {...},
  "risk_summary": "..."
}
```

### 4. POST /api/consultant-studio/identify-location/{request_id}/promote/{candidate_id}

Convert candidate to SuccessProfile.

**Request:**
```json
{
  "notes": "Perfect location for our brand focus"
}
```

**Response:**
```json
{
  "success": true,
  "success_profile_id": "42",
  "message": "Successfully promoted Brickell, Miami to SuccessProfile"
}
```

## Data Models

### TargetMarket
Specifies the market area to search.

```python
class TargetMarket(BaseModel):
    market_type: TargetMarketType  # metro, city, point_radius
    metro: Optional[str]           # e.g., "Miami"
    city: Optional[str]            # e.g., "Brickell"
    state: str                     # "FL"
    latitude: Optional[float]      # For point_radius
    longitude: Optional[float]     # For point_radius
    radius_miles: float = 5.0      # Search radius
```

### CandidateProfile
Represents a single candidate location.

```python
class CandidateProfile(BaseModel):
    candidate_id: str
    location_name: str
    latitude: float
    longitude: float
    
    # Classification
    archetype: ArchetypeType      # pioneer, mainstream, etc.
    archetype_confidence: float   # 0-1
    archetype_rationale: str
    risk_factors: List[str]
    
    # Signals (3 key signals for candidate classification)
    measured_signals: List[MeasuredSignal]
    
    # Source
    source: CandidateSource       # named_market or gap_discovery
    source_id: Optional[str]      # ID in source system
    
    # Location details
    zip_code: Optional[str]
    neighborhood: Optional[str]
    city: str
    state: str
    
    # Score
    overall_score: float          # 0-100
```

### MeasuredSignal
A single measured characteristic.

```python
class MeasuredSignal(BaseModel):
    signal_name: str              # foot_traffic_score, demographic_fit, competition_density
    signal_value: float           # 0-100
    percentile_rank: Optional[int]  # 0-100
    confidence: float             # 0-1
    data_source: str              # Where data came from
```

## Classification Rules

### 3-Signal Model (Candidates)

Unlike the full 4-signal model used for SuccessProfiles, candidates use 3 signals:

1. **Foot Traffic Score** (0-100)
   - Daily average foot traffic
   - Growth trend
   - Recency of data
   - Weight: 35%

2. **Demographic Fit** (0-100)
   - Population density
   - Median income
   - Target demographic match
   - Weight: 40%

3. **Competition Density** (0-100)
   - Lower = higher score
   - Competitors per 10k population
   - Market saturation level
   - Weight: 25%

### Archetype Assignment

Based on signal ranges:

| Archetype | Competition | Demographic | Foot Traffic | Use Case |
|-----------|------------|-------------|--------------|----------|
| **Pioneer** | Low (0-40) | Good (60-100) | Moderate (30-70) | Emerging trends |
| **Mainstream** | Moderate (40-75) | Strong (70-100) | Good (60-100) | Proven demand |
| **Specialist** | Varies (30-80) | Focused (60-100) | Varies (20-80) | Niche markets |
| **Anchor** | Rare (0-50) | Excellent (80-100) | High (80-100) | Destination |
| **Experimental** | Any (0-100) | Lower (0-60) | Lower (0-50) | Test markets |

## Tier-Based Access Control

| Tier | Monthly Calls | Include Gaps | Per Archetype | Cost |
|------|--------------|-------------|---------------|------|
| **FREE** | 1 | ❌ | 3 | Free |
| **BUILDER** | 5 | ✅ | 5 | $29/mo |
| **SCALER** | 25 | ✅ | Unlimited | $99/mo |
| **ENTERPRISE** | Unlimited | ✅ | Unlimited | Custom |

## Tier A: Named Micro-Markets

### Coverage
- 10 Major Metros (Miami, Atlanta, Orlando, Tampa, NYC, LA, Houston, Dallas, Chicago, Austin)
- 5-15 curated markets per metro
- ~100 total named markets
- Polygon geometries for precise boundaries

### Named Markets (Examples)

**Miami:**
- Brickell (financial, high-rise)
- Wynwood (arts, trendy)
- Calle Ocho (cultural, dining)
- Coral Gables (upscale)
- South Beach (beach destination)

**NYC:**
- SoHo (upscale shopping)
- East Village (vibrant, diverse)
- Brooklyn Heights (historic)

**Austin:**
- South Congress (eclectic)
- Downtown Austin (music, tech)

## Tier B: Gap Discovery Engine

### Technology
- **H3 Hex Grid** (Resolution 8)
- Hexagon size: ~360 meters
- Granular enough for neighborhood-level analysis
- Efficient for computational analysis

### Scoring Algorithm
```
Viability Score = (Competition×0.4) + (Demographics×0.4) + (Traffic×0.2)
```

### White-Space Criteria
- Low competitor density
- Viable demographic profile
- Moderate to high foot traffic potential

### Reverse Geocoding
- Converts hex centers to human-readable location names
- Uses Census data + geocoding APIs

## Caching Strategy

### Cache Key
```
sha256(category|market_type|metro|state|boundary_type)
```

### TTL
- 7 days from creation
- Auto-expired via scheduled job
- Hit counter for analytics

### Benefits
- Sub-second result retrieval
- Reduced API calls to external data sources
- Consistent results during analysis period

## Public API Safety

### Benchmark Summary (Sanitized)
✅ **SAFE to expose:**
- Category name
- Typical archetypes
- Total addressable population

❌ **NEVER expose:**
- Company ticker symbols
- SEC filing references
- Raw thresholds
- Profit margins
- Revenue data
- Insider information

## Integration with SuccessProfile

### Promotion Flow
```
Candidate (from Identify Location)
        ↓
    [Promotion]
        ↓
SuccessProfile (owned by user)
        ↓
    [Strategy Building]
        ↓
Action Plans, Market Research, etc.
```

### SuccessProfile Fields
- `user_id`: Owner
- `category`: Business category
- `location_name`: Location details
- `archetype`: Classified type
- `candidate_profile`: Full candidate data snapshot
- `user_notes`: Custom notes
- `promoted_at`: Promotion timestamp

## Database Schema

### micro_markets
```sql
CREATE TABLE micro_markets (
    id INT PRIMARY KEY,
    market_name VARCHAR(255),
    metro VARCHAR(100),
    state VARCHAR(2),
    center_latitude FLOAT,
    center_longitude FLOAT,
    polygon_geojson JSON,
    description TEXT,
    typical_archetypes JSON,
    demographic_profile JSON,
    avg_foot_traffic INT,
    avg_demographic_fit FLOAT,
    avg_competition_density FLOAT,
    is_active INT,
    created_at DATETIME,
    updated_at DATETIME,
    
    INDEX ix_metro_state (metro, state),
    INDEX ix_name (market_name)
);
```

### success_profiles
```sql
CREATE TABLE success_profiles (
    id INT PRIMARY KEY,
    user_id INT NOT NULL,
    request_id VARCHAR(100),
    candidate_id VARCHAR(100),
    category VARCHAR(100),
    location_name VARCHAR(255),
    latitude FLOAT,
    longitude FLOAT,
    city VARCHAR(100),
    state VARCHAR(2),
    archetype VARCHAR(50),
    archetype_confidence FLOAT,
    candidate_profile JSON,
    user_notes TEXT,
    status VARCHAR(50),
    created_at DATETIME,
    promoted_at DATETIME,
    
    INDEX ix_user_id (user_id),
    INDEX ix_category (category)
);
```

### identify_location_cache
```sql
CREATE TABLE identify_location_cache (
    id INT PRIMARY KEY,
    cache_key VARCHAR(255) UNIQUE,
    request_id VARCHAR(100),
    category VARCHAR(100),
    target_market JSON,
    market_boundary JSON,
    result JSON,
    hit_count INT,
    created_at DATETIME,
    expires_at DATETIME,
    
    INDEX ix_category (category),
    INDEX ix_expires_at (expires_at)
);
```

## Testing

### Unit Tests
- Schemas and data models
- Micro-market catalog queries
- Signal computation
- Archetype classification
- Score calculations

### Integration Tests
- End-to-end identify location flow
- Tier-based limiting
- Caching behavior
- Candidate promotion
- Miami coffee shop scenario

### Performance Tests
- <12s requirement for typical metro + gaps
- Cache hit performance
- Parallel profile building

### Test Coverage
Target: ≥80% code coverage

## Deployment Checklist

- [ ] Run migrations: `alembic upgrade head`
  - Creates micro_markets table
  - Creates success_profiles table
  - Creates identify_location_cache table
  - Seeds 100 named micro-markets
- [ ] Install H3 dependency: `pip install h3`
- [ ] Run tests: `pytest tests/test_identify_location_service.py`
- [ ] Load seed data (automatic via migration)
- [ ] Deploy consultant router updates
- [ ] Test endpoints manually
- [ ] Monitor performance in production

## Troubleshooting

### "H3 not available"
Install h3: `pip install h3`
Gap discovery will use fallback mode without H3.

### Cache not working
Check `identify_location_cache` table:
```sql
SELECT * FROM identify_location_cache 
WHERE expires_at > NOW();
```

### Missing micro-markets
Run migration: `alembic upgrade 20250430_0002`

## Future Enhancements

1. **Real-time Data Integration**
   - Live foot traffic APIs
   - Real-time competitor data
   - Market sentiment analysis

2. **Advanced Filtering**
   - Rent price ranges
   - Parking availability
   - Public transit access
   - Zoning restrictions

3. **Competitive Intelligence**
   - Specific competitor tracking
   - Market share estimation
   - Customer demographic profiling

4. **Predictive Analytics**
   - 12-month revenue projections
   - Market growth forecasting
   - Cannibalization risk analysis

5. **Custom Micro-Markets**
   - User-drawn polygons
   - Custom market definitions
   - Private market libraries
