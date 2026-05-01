# Identify Location Service - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependency
```bash
pip install h3
```
(Optional: Gap discovery will work without H3, but with reduced functionality)

### Step 2: Run Migrations
```bash
cd /path/to/oppgrid/backend
alembic upgrade head
```

This will:
- Create `micro_markets` table
- Create `success_profiles` table
- Create `identify_location_cache` table
- Seed 100 micro-markets across 10 metros

### Step 3: Verify Installation
```bash
# Check that tables exist
sqlite3 oppgrid.db "SELECT name FROM sqlite_master WHERE type='table';" | grep -E "micro_markets|success_profiles|identify_location_cache"

# Expected output:
# micro_markets
# success_profiles
# identify_location_cache

# Check seed data
sqlite3 oppgrid.db "SELECT COUNT(*) FROM micro_markets;"
# Expected: 100
```

### Step 4: Run Tests
```bash
pytest tests/test_identify_location_service.py -v
```

### Step 5: Start Server
```bash
uvicorn app.main:app --reload
```

## 📡 API Usage Examples

### Example 1: Find Locations in Miami for Premium Coffee Shop

**Request:**
```bash
curl -X POST "http://localhost:8000/api/consultant-studio/identify-location/search" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "coffee_shop_premium",
    "business_description": "Upscale coffee with seating and WiFi",
    "target_market": {
      "market_type": "metro",
      "metro": "Miami",
      "state": "FL",
      "radius_miles": 10
    },
    "include_gap_discovery": true
  }'
```

**Response:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "category": "coffee_shop_premium",
  "candidates_by_archetype": [
    {
      "archetype": "mainstream",
      "candidate_count": 3,
      "avg_score": 82.5,
      "candidates": [
        {
          "candidate_id": "named_market_1_coffee_shop_premium",
          "location_name": "Brickell, Miami",
          "latitude": 25.7685,
          "longitude": -80.1922,
          "archetype": "mainstream",
          "overall_score": 84.2,
          "measured_signals": [
            {
              "signal_name": "foot_traffic_score",
              "signal_value": 82.5,
              "data_source": "foot_traffic_api"
            },
            {
              "signal_name": "demographic_fit",
              "signal_value": 85.0,
              "data_source": "census_data"
            },
            {
              "signal_name": "competition_density",
              "signal_value": 75.0,
              "data_source": "business_database"
            }
          ]
        }
      ]
    }
  ],
  "total_candidates": 10,
  "tier": "free",
  "candidates_shown": 3,
  "map_data": {
    "type": "FeatureCollection",
    "features": [...]
  },
  "processing_time_ms": 2150
}
```

### Example 2: Get Cached Result

**Request:**
```bash
curl "http://localhost:8000/api/consultant-studio/identify-location/550e8400-e29b-41d4-a716-446655440000"
```

**Response:** (same as above, with `from_cache: true`)

### Example 3: Get Candidate Details

**Request:**
```bash
curl "http://localhost:8000/api/consultant-studio/identify-location/550e8400-e29b-41d4-a716-446655440000/candidate/named_market_1_coffee_shop_premium"
```

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
    "overall_score": 84.2,
    "measured_signals": [...]
  },
  "demographics": null,
  "local_competition": null,
  "foot_traffic_trend": null,
  "risk_summary": "Location analysis complete"
}
```

### Example 4: Promote to SuccessProfile

**Request:**
```bash
curl -X POST "http://localhost:8000/api/consultant-studio/identify-location/550e8400-e29b-41d4-a716-446655440000/promote/named_market_1_coffee_shop_premium" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Perfect location for our premium brand. Strong foot traffic and demographics match."
  }'
```

**Response:**
```json
{
  "success": true,
  "success_profile_id": "42",
  "message": "Successfully promoted Brickell, Miami to SuccessProfile"
}
```

## 🏙️ Available Markets

### Miami, FL
- Brickell (mainstream, anchor)
- Wynwood (pioneer, specialist)
- Calle Ocho (specialist, mainstream)
- Coral Gables (mainstream, specialist)
- South Beach (anchor, mainstream)

### Atlanta, GA
- Midtown (mainstream, pioneer)
- Virginia Highland (specialist, pioneer)
- Buckhead (mainstream, anchor)

### Orlando, FL
- Downtown Orlando (mainstream, anchor)
- Winter Park (specialist, mainstream)

### Tampa, FL
- Downtown Tampa (mainstream, anchor)
- Hyde Park (pioneer, specialist)

### New York, NY
- SoHo (mainstream, specialist)
- East Village (pioneer, mainstream)
- Brooklyn Heights (mainstream, anchor)

### Los Angeles, CA
- Santa Monica (mainstream, pioneer)
- Silver Lake (pioneer, specialist)

### Houston, TX
- Montrose (pioneer, mainstream)
- Midtown (mainstream, anchor)

### Dallas, TX
- Uptown (mainstream, anchor)
- Bishop Arts District (pioneer, specialist)

### Chicago, IL
- River North (mainstream, anchor)
- Wicker Park (pioneer, mainstream)

### Austin, TX
- South Congress (pioneer, specialist)
- Downtown Austin (mainstream, anchor)

## 🔐 User Tiers

### FREE (Default)
- 1 request/month
- Named markets only (no gaps)
- Top 3 candidates per archetype

### BUILDER
- 5 requests/month
- Named + gap discovery
- Top 5 candidates per archetype

### SCALER
- 25 requests/month
- Named + gap discovery
- Unlimited candidates

### ENTERPRISE
- Unlimited requests
- Named + gap discovery
- Unlimited candidates

## 🎯 Archetype Guide

**MAINSTREAM**
- Established locations with proven demand
- Moderate competition
- Strong demographics
- Good foot traffic
- → Best for proven business models

**PIONEER**
- Early-stage, emerging trend locations
- Low competition
- Good demographics
- Moderate foot traffic
- → Best for innovative concepts

**SPECIALIST**
- Niche, high-margin locations
- Focused demographics
- Varies on competition/traffic
- → Best for boutique/specialty businesses

**ANCHOR**
- Destination-driving locations
- Rare competition
- Excellent demographics
- Very high foot traffic
- → Best for flagship locations

**EXPERIMENTAL**
- Test market locations
- Lower demographics OK
- Lower traffic acceptable
- → Best for pilots/testing

## 📊 Signal Explanations

### Foot Traffic Score (35% weight)
- Daily average pedestrian/customer traffic
- Growth trend over time
- 0-100 scale

### Demographic Fit (40% weight)
- Population density
- Median income match
- Target customer alignment
- 0-100 scale

### Competition Density (25% weight)
- Number of competitors
- Market saturation
- Inverse scale: lower competition = higher score
- 0-100 scale

## 🔧 Troubleshooting

### Tables don't exist
```bash
alembic upgrade head
```

### No micro-markets in database
```bash
sqlite3 oppgrid.db "DELETE FROM alembic_version; alembic upgrade head"
```

### H3 not installed (gap discovery unavailable)
```bash
pip install h3
```

### API returns 404
Ensure you're using the correct URL:
- `/api/consultant-studio/identify-location/search` (POST)
- `/api/consultant-studio/identify-location/{request_id}` (GET)

### Results contain fewer candidates than expected
Check your tier:
- FREE: max 3 per archetype
- BUILDER: max 5 per archetype
- SCALER/ENTERPRISE: unlimited

## 📈 Performance Tips

### Cache Hits (1-2s)
Same request twice? Second is served from cache:
```bash
# First request: 2-3s
curl "..." # 2150ms

# Second request: <100ms
curl "..." # 45ms (cached)
```

### Optimize Query
- Use METRO instead of POINT_RADIUS for faster results
- Exclude gap discovery if not needed: `include_gap_discovery: false`
- Filter by archetype: `archetype_preference: ["mainstream"]`

## 🧪 Testing

### Run Full Test Suite
```bash
pytest tests/test_identify_location_service.py -v

# Output: 45+ tests, ~2 min runtime
# Expected: All passing ✓
```

### Run Specific Test
```bash
pytest tests/test_identify_location_service.py::TestIdentifyLocationService::test_identify_location_basic -v
```

### Generate Coverage Report
```bash
pytest tests/test_identify_location_service.py --cov=app/services/success_profile --cov=app/schemas/identify_location
```

## 📞 Support

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Request timed out" | Reduce market area or disable gaps |
| "No candidates found" | Check market has seed data, use SCALER tier |
| "Cache miss" | Expected for new searches, try same request twice |
| "Invalid archetype" | Use: pioneer, mainstream, specialist, anchor, experimental |

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Monitor Performance

Check processing time in response:
```json
{
  "processing_time_ms": 2150,  // Should be < 12000
  "from_cache": false,
  "tier": "free"
}
```

## 🎓 Next Steps

1. **Explore Candidates:** Use GET endpoints to explore detailed candidate info
2. **Promote Locations:** Convert promising candidates to SuccessProfiles
3. **Build Strategy:** Use SuccessProfiles as starting point for market strategy
4. **Iterate:** Run more searches with different archetypes/preferences

## 📚 Full Documentation

See `IDENTIFY_LOCATION_SYSTEM.md` for:
- Complete architecture
- Database schema
- API reference
- Classification rules
- Integration guide
