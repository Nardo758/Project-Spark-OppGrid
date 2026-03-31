# OppGrid Report Studio Data Framework

> **Principle:** OppGrid owns the intelligence. External sources (JediRE + Web) enrich but don't replace.

## Data Sources

| Source | Type | Data |
|--------|------|------|
| **OppGrid** | 🔵 Primary | Opportunities, trends, success patterns, Census, traffic |
| **JediRE** | 🟡 Enrichment | Demand signals, rent data, vacancy, absorption |
| **Google Trends** | 🌐 Web | Search interest, trend direction, related queries |
| **Google Places** | 🌐 Web | Competitors, ratings, reviews, price levels |
| **Indeed/Jobs** | 🌐 Web | Job postings, hiring velocity, top employers |
| **Zillow/Redfin** | 🌐 Web | Home values, rent estimates, market temperature |
| **News APIs** | 🌐 Web | Market news, sentiment, trending topics |
| **BLS** | 🌐 Web | Unemployment, labor force participation |

---

## 4 P's Data Framework

### PRODUCT (Demand Validation)
*"Is there demand for this?"*

| Data | Source | Type |
|------|--------|------|
| `ai_opportunity_score` (0-100) | opportunities | 🔵 OppGrid |
| `ai_pain_intensity` (1-10) | opportunities | 🔵 OppGrid |
| `ai_urgency_level` | opportunities | 🔵 OppGrid |
| `ai_target_audience` | opportunities | 🔵 OppGrid |
| `trend_strength` | detected_trends | 🔵 OppGrid |
| `confidence_score` | detected_trends | 🔵 OppGrid |
| `opportunities_count` | detected_trends | 🔵 OppGrid |
| `signal_density` | service_area_boundaries | 🔵 OppGrid |
| `validation_confidence` | idea_validations | 🔵 OppGrid |
| Amenity Demand | JediRE `/oppgrid/demand-signals` | 🟡 Enrichment |
| Unmet Demand | JediRE `/jedi/search-trends` | 🟡 Enrichment |

---

### PRICE (Economics)
*"What can the market bear?"*

| Data | Source | Type |
|------|--------|------|
| `ai_market_size_estimate` | opportunities | 🔵 OppGrid |
| `addressable_market_value` | service_area_boundaries | 🔵 OppGrid |
| `revenue_generated` | success_patterns | 🔵 OppGrid |
| `capital_spent` | success_patterns | 🔵 OppGrid |
| `median_income` | census_population_estimates | 🔵 OppGrid |
| `income_growth_rate` | market_growth_trajectories | 🔵 OppGrid |
| `income_differential` | census_migration_flows | 🔵 OppGrid |
| Median Rent | JediRE `/oppgrid/market-economics` | 🟡 Enrichment |
| Spending Power Index | JediRE (computed) | 🟡 Enrichment |

---

### PLACE (Location)
*"Where should I locate?"*

| Data | Source | Type |
|------|--------|------|
| `growth_score` (0-100) | market_growth_trajectories | 🔵 OppGrid |
| `growth_category` | market_growth_trajectories | 🔵 OppGrid |
| `population_growth_rate` | market_growth_trajectories | 🔵 OppGrid |
| `job_growth_rate` | market_growth_trajectories | 🔵 OppGrid |
| `business_formation_rate` | market_growth_trajectories | 🔵 OppGrid |
| `aadt` (traffic) | traffic_roads | 🔵 OppGrid |
| `site_recommendations` | location_analysis_cache | 🔵 OppGrid |
| `claude_summary` | location_analysis_cache | 🔵 OppGrid |
| Vacancy Rate | JediRE `/oppgrid/market-economics` | 🟡 Enrichment |
| Absorption Rate | JediRE `/jedi/absorption-rate` | 🟡 Enrichment |
| Supply Pipeline | JediRE `/jedi/supply-pipeline` | 🟡 Enrichment |

---

### PROMOTION (Competition)
*"How will customers find me?"*

| Data | Source | Type |
|------|--------|------|
| `ai_competition_level` | opportunities | 🔵 OppGrid |
| `ai_competitive_advantages` | opportunities | 🔵 OppGrid |
| `ai_key_risks` | opportunities | 🔵 OppGrid |
| `ai_business_model_suggestions` | opportunities | 🔵 OppGrid |
| `success_factors` | success_patterns | 🔵 OppGrid |
| `failure_points` | success_patterns | 🔵 OppGrid |
| `rating`, `reviews` | google_maps_businesses | 🔵 OppGrid |
| Search Trends | JediRE `/jedi/search-trends` | 🟡 Enrichment |

---

## Report × Data Matrix

| Report Type | Required Data |
|-------------|---------------|
| **Market Analysis** | All 4 P's, heavy on PLACE + PRODUCT |
| **Feasibility** | PRICE benchmarks, PLACE traffic, PROMOTION risks |
| **Business Plan** | All 4 P's balanced |
| **Financial** | PRICE heavy (TAM, benchmarks, capital) |
| **Competitive** | PROMOTION heavy (competitors, gaps) |
| **PESTLE** | PLACE economics + external factors |
| **Pitch Deck** | PRODUCT problem, PRICE TAM, PROMOTION competition |

---

## Data Fetch Priority

### Tier 1: Always Fetch
```
opportunities.*              # Core opportunity data
detected_trends.*            # Market trends
market_growth_trajectories.* # Growth metrics
service_area_boundaries.*    # Trade area data
```

### Tier 2: Report-Specific
```
market_analysis  → traffic_roads, census_*, JediRE market data
feasibility      → success_patterns, location_analysis_cache
financial        → success_patterns (revenue/capital benchmarks)
competitive      → google_maps_businesses
```

### Tier 3: Enrichment (JediRE)
```
/oppgrid/demand-signals      # Amenity preferences
/oppgrid/market-economics    # Rent levels
/jedi/absorption-rate        # Market velocity
/jedi/supply-pipeline        # Competition timing
```

---

## ReportDataService Contract

```python
def get_report_data(city, state, business_type, report_type) -> ReportDataContext:
    return {
        "product": {
            "opportunity_score": 78,
            "pain_intensity": 7,
            "urgency_level": "high",
            "trend_strength": 65,
            "signal_density": 0.82,
            # + JediRE enrichment
        },
        "price": {
            "market_size": "$10M-$50M",
            "addressable_market": 2500000,
            "revenue_benchmark": 450000,
            "capital_required": 150000,
            "median_income": 62500,
            # + JediRE enrichment
        },
        "place": {
            "growth_score": 78,
            "growth_category": "growing",
            "population_growth": 2.3,
            "job_growth": 3.1,
            "traffic_aadt": 45000,
            # + JediRE enrichment
        },
        "promotion": {
            "competition_level": "medium",
            "competitor_count": 12,
            "avg_rating": 4.1,
            "success_factors": [...],
            "key_risks": [...],
        },
        "data_quality": {
            "completeness": 0.85,
            "confidence": 0.78,
        }
    }
```

---

## Data Quality Scoring

### Pillar-Level Quality (`PillarQuality`)

Each of the 4 P's gets individual quality scores:

| Metric | Description |
|--------|-------------|
| `completeness` | 0-1, % of key fields filled |
| `confidence` | 0-1, weighted by source (OppGrid=1.0, JediRE=0.8) |
| `fields_filled` / `fields_total` | Raw count |
| `primary_sources` | OppGrid fields filled |
| `enrichment_sources` | JediRE fields filled |
| `warnings` | Missing critical fields |

### Overall Quality (`DataQuality`)

| Metric | Description |
|--------|-------------|
| `completeness` | Weighted avg by report type |
| `confidence` | Weighted avg by report type |
| `report_readiness` | 0-1, is data sufficient for this report? |
| `weakest_pillar` | Which P needs more data |
| `recommended_actions` | Actionable improvement steps |
| `primary_data_pct` | % from OppGrid |
| `enrichment_data_pct` | % from JediRE |

### Report Type Weights

Different reports prioritize different pillars:

| Report Type | PRODUCT | PRICE | PLACE | PROMOTION |
|-------------|---------|-------|-------|-----------|
| market_analysis | 30% | 20% | **35%** | 15% |
| feasibility | 20% | **35%** | 25% | 20% |
| business_plan | 25% | 25% | 25% | 25% |
| financial | 15% | **45%** | 20% | 20% |
| competitive | 20% | 15% | 15% | **50%** |
| pitch_deck | **35%** | 30% | 15% | 20% |

### Readiness Thresholds

| Score | Status | Action |
|-------|--------|--------|
| 0.8+ | ✅ Excellent | Proceed with full report |
| 0.6-0.8 | 🟡 Good | Minor gaps, report viable |
| 0.4-0.6 | 🟠 Fair | Report will have limited depth |
| <0.4 | 🔴 Limited | Gather more data first |

### Critical Fields

Each pillar has critical fields that **must** be present:

- **PRODUCT:** `opportunity_score`, `trend_strength`
- **PRICE:** `market_size_estimate`, `median_income`
- **PLACE:** `growth_score`, `population`
- **PROMOTION:** `competition_level`, `competitor_count`

Missing critical fields triggers warnings and confidence penalties.

---

*OppGrid owns the intelligence. JediRE adds rental market context.*
