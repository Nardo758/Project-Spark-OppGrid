# OppGrid Report Studio Data Framework

## Overview

This framework defines the data sources that power each report type in OppGrid's Report Studio. Data is organized using the **4 P's Framework** (Product, Price, Place, Promotion) to ensure comprehensive business intelligence coverage.

---

## Data Source Registry

### 🔵 OppGrid-Generated Intelligence (Primary)

These are signals OppGrid creates through its own AI analysis, user behavior, and data processing.

| Source | Table | Key Fields | What It Represents |
|--------|-------|------------|-------------------|
| **AI Opportunity Analysis** | `opportunities` | `ai_opportunity_score` (0-100), `ai_pain_intensity` (1-10), `ai_competition_level`, `ai_urgency_level`, `ai_market_size_estimate`, `ai_target_audience` | OppGrid's AI assessment of each opportunity |
| **AI Business Intelligence** | `opportunities` | `ai_business_model_suggestions`, `ai_competitive_advantages`, `ai_key_risks`, `ai_next_steps`, `ai_problem_statement` | Strategic recommendations |
| **Opportunity Demographics** | `opportunities` | `demographics` (JSONB), `search_trends` (JSONB), `feasibility_score` | Per-opportunity market data |
| **Detected Trends** | `detected_trends` | `trend_name`, `trend_strength`, `growth_rate`, `confidence_score`, `opportunities_count`, `keywords` | Emerging market trends |
| **Market Growth Trajectories** | `market_growth_trajectories` | `growth_score` (0-100), `growth_category`, `population_growth_rate`, `job_growth_rate`, `income_growth_rate`, `business_formation_rate`, `net_migration_rate` | OppGrid's market heat assessment |
| **Signal Density** | `market_growth_trajectories` | `opportunity_signal_count`, `avg_opportunity_score`, `signal_density_percentile`, `housing_growth_rate`, `commercial_growth_rate` | Demand concentration metrics |
| **Service Areas** | `service_area_boundaries` | `total_population`, `total_households`, `median_income`, `signal_count`, `signal_density`, `market_penetration_estimate`, `addressable_market_value` | Computed trade areas + TAM |
| **Success Patterns** | `success_patterns` | `revenue_generated`, `capital_spent`, `success_factors` (JSON), `failure_points` (JSON), `timeline` | Learnings from outcomes |
| **Idea Validations** | `idea_validations` | `opportunity_score`, `competition_level`, `urgency_level`, `market_size_estimate`, `validation_confidence` | User idea assessments |
| **Location Analysis** | `location_analysis_cache` | `demographic_data` (JSONB), `market_metrics` (JSONB), `site_recommendations` (JSONB), `claude_summary` | AI location intelligence |

### 🟢 OppGrid-Collected Data (Scraped/Imported)

Data OppGrid actively collects from external sources.

| Source | Table | Key Fields | Collection Method |
|--------|-------|------------|-------------------|
| **Competitor Intel** | `google_maps_businesses` | `name`, `rating`, `user_ratings_total`, `price_level`, `types`, `website`, `phone_number` | Google Maps scraping |
| **Traffic Data** | `traffic_roads` | `aadt`, `k_factor`, `d_factor`, `t_factor`, `road_name`, `geometry` | State DOT imports |
| **Census Demographics** | `census_population_estimates` | `population`, `births`, `deaths`, `natural_increase`, `net_domestic_migration`, `net_international_migration`, `yoy_growth_rate`, `five_year_growth_rate`, `median_age`, `median_income` | Census API |
| **Migration Flows** | `census_migration_flows` | `flow_count`, `origin_median_income`, `destination_median_income`, `income_differential`, `migration_type` | Census ACS |
| **Scraped Sources** | `scraped_sources` | Opportunity data from Reddit, Twitter, etc. | Platform scraping |

### 🟡 External API Sources (JediRE + Others)

| Source | Endpoint | Key Fields | Use Case |
|--------|----------|------------|----------|
| **Demand Signals** | JediRE `/oppgrid/demand-signals` | amenity_type, demand_pct, trend | What residents want |
| **Market Economics** | JediRE `/oppgrid/market-economics` | median_rent, spending_power_index, vacancy_rate | Pricing power |
| **Rent Comps** | JediRE `/jedi/rent-comps` | rent, sqft, amenities, concessions | Competitive pricing |
| **Market Data** | JediRE `/jedi/market-data` | supply, pricing, demand, forecast | Full market picture |
| **Absorption Rate** | JediRE `/jedi/absorption-rate` | avg_days_to_lease, monthly_rate | Market velocity |
| **Supply Pipeline** | JediRE `/jedi/supply-pipeline` | upcoming properties, delivery dates | Competition timing |
| **Search Trends** | JediRE `/jedi/search-trends` | price_range_distribution, unmet_demand | Digital demand |
| **User Preferences** | JediRE `/jedi/user-preferences-aggregate` | top_amenities, deal_breakers, budget | Consumer insights |

---

## 4 P's Data Mapping

### PRODUCT (Demand Validation)
*"Is there demand for this?"*

| Data Point | 🔵 OppGrid Source | 🟡 External Enrichment | Report Sections |
|------------|-------------------|------------------------|-----------------|
| **Opportunity Score** | `opportunities.ai_opportunity_score` | — | Executive Summary, Feasibility |
| **Pain Intensity** | `opportunities.ai_pain_intensity` | — | Problem Analysis |
| **Urgency Level** | `opportunities.ai_urgency_level` | — | Priority Assessment |
| **Target Audience** | `opportunities.ai_target_audience` | — | Consumer Analysis |
| **Problem Statement** | `opportunities.ai_problem_statement` | — | Problem Analysis |
| **Trend Strength** | `detected_trends.trend_strength` | — | Market Forecast |
| **Trend Growth Rate** | `detected_trends.growth_rate` | — | Momentum Analysis |
| **Trend Confidence** | `detected_trends.confidence_score` | — | Validation |
| **Opportunity Count** | `detected_trends.opportunities_count` | — | Signal Density |
| **Signal Density** | `service_area_boundaries.signal_density` | — | TAM/SAM/SOM |
| **Market Penetration** | `service_area_boundaries.market_penetration_estimate` | — | Feasibility |
| **Validation Score** | `idea_validations.opportunity_score` | — | Idea Assessment |
| **Validation Confidence** | `idea_validations.validation_confidence` | — | Confidence Level |
| Amenity Demand | — | JediRE `/oppgrid/demand-signals` | Consumer Analysis |
| Unmet Demand | — | JediRE `/jedi/search-trends` | Market Gaps |

### PRICE (Economics)
*"What can the market bear?"*

| Data Point | 🔵 OppGrid Source | 🟡 External Enrichment | Report Sections |
|------------|-------------------|------------------------|-----------------|
| **Market Size Estimate** | `opportunities.ai_market_size_estimate` | — | TAM/SAM/SOM |
| **Addressable Market** | `service_area_boundaries.addressable_market_value` | — | Financial Projections |
| **Revenue Benchmarks** | `success_patterns.revenue_generated` | — | Financial Projections |
| **Capital Requirements** | `success_patterns.capital_spent` | — | Feasibility Study |
| **Median Income** | `census_population_estimates.median_income` | — | Demographics |
| **Income Growth** | `market_growth_trajectories.income_growth_rate` | — | Economic Analysis |
| **Income Differential** | `census_migration_flows.income_differential` | — | Migration Analysis |
| **Service Area Income** | `service_area_boundaries.median_income` | — | Trade Area |
| **Total Households** | `service_area_boundaries.total_households` | — | Market Sizing |
| Median Rent | — | JediRE `/oppgrid/market-economics` | Pricing Analysis |
| Spending Power Index | — | JediRE (computed) | Consumer Analysis |
| Concession Rate | — | JediRE `/jedi/market-data` | Competitive Pricing |

### PLACE (Location Intelligence)
*"Where should I locate?"*

| Data Point | 🔵 OppGrid Source | 🟡 External Enrichment | Report Sections |
|------------|-------------------|------------------------|-----------------|
| **Growth Score** | `market_growth_trajectories.growth_score` | — | Market Assessment |
| **Growth Category** | `market_growth_trajectories.growth_category` | — | Executive Summary |
| **Population Growth** | `market_growth_trajectories.population_growth_rate` | — | Growth Forecast |
| **Job Growth** | `market_growth_trajectories.job_growth_rate` | — | Economic Analysis |
| **Business Formation** | `market_growth_trajectories.business_formation_rate` | — | Economic Health |
| **Net Migration** | `market_growth_trajectories.net_migration_rate` | — | Population Dynamics |
| **Housing Growth** | `market_growth_trajectories.housing_growth_rate` | — | Development Activity |
| **Commercial Growth** | `market_growth_trajectories.commercial_growth_rate` | — | Commercial Activity |
| **Avg Opportunity Score** | `market_growth_trajectories.avg_opportunity_score` | — | Market Quality |
| **Signal Density %ile** | `market_growth_trajectories.signal_density_percentile` | — | Demand Concentration |
| **AADT (Traffic)** | `traffic_roads.aadt` | — | Site Selection |
| **Traffic K-Factor** | `traffic_roads.k_factor` | — | Peak Hour Analysis |
| **Population** | `census_population_estimates.population` | — | Demographics |
| **5-Year Growth** | `census_population_estimates.five_year_growth_rate` | — | Long-term Trend |
| **Median Age** | `census_population_estimates.median_age` | — | Demographics |
| **Net Domestic Migration** | `census_population_estimates.net_domestic_migration` | — | Population Flow |
| **Service Area Pop** | `service_area_boundaries.total_population` | — | Trade Area |
| **Service Area Polygon** | `service_area_boundaries.geojson_polygon` | — | Map Visualization |
| **Site Recommendations** | `location_analysis_cache.site_recommendations` | — | Site Selection |
| **Claude Summary** | `location_analysis_cache.claude_summary` | — | Location Narrative |
| Vacancy Rate | — | JediRE `/oppgrid/market-economics` | Supply/Demand |
| Absorption Rate | — | JediRE `/jedi/absorption-rate` | Market Velocity |
| Supply Pipeline | — | JediRE `/jedi/supply-pipeline` | Competition Timing |

### PROMOTION (Competition & Reach)
*"How will customers find me?"*

| Data Point | 🔵 OppGrid Source | 🟡 External Enrichment | Report Sections |
|------------|-------------------|------------------------|-----------------|
| **Competition Level** | `opportunities.ai_competition_level` | — | Executive Summary |
| **Competitive Advantages** | `opportunities.ai_competitive_advantages` | — | Strategy |
| **Key Risks** | `opportunities.ai_key_risks` | — | Risk Analysis |
| **Business Model Ideas** | `opportunities.ai_business_model_suggestions` | — | Business Plan |
| **Next Steps** | `opportunities.ai_next_steps` | — | Action Plan |
| **Competitor Count** | `google_maps_businesses` (count) | — | Competitive Landscape |
| **Avg Rating** | `google_maps_businesses.rating` (avg) | — | Competitive Analysis |
| **Review Volume** | `google_maps_businesses.user_ratings_total` | — | Market Maturity |
| **Price Levels** | `google_maps_businesses.price_level` | — | Pricing Strategy |
| **Competitor Types** | `google_maps_businesses.types` | — | Category Analysis |
| **Success Factors** | `success_patterns.success_factors` | — | Best Practices |
| **Failure Points** | `success_patterns.failure_points` | — | Risk Avoidance |
| Search Trends | — | JediRE `/jedi/search-trends` | Digital Demand |
| User Preferences | — | JediRE `/jedi/user-preferences-aggregate` | Consumer Insights |

---

## Report Type × Data Matrix

### Executive Summary
```
Required:
├── PRODUCT: opportunity_score, pain_intensity, demand_signals[top_3]
├── PRICE: market_size_estimate, median_income, spending_power_index
├── PLACE: growth_category, population, population_growth_rate
└── PROMOTION: competition_level, competitor_count
```

### Market Analysis Report
```
Required:
├── PRODUCT: demand_signals, trend_strength, signal_density, unmet_demand
├── PRICE: median_rent, rent_by_bedroom, concession_rate, market_size
├── PLACE: population, population_growth, job_growth, vacancy, absorption_rate
└── PROMOTION: competitor_count, avg_rating, search_trends

Sections:
1. Executive Summary → All 4 P's summary
2. Industry Overview → PRODUCT trends + PLACE economics
3. Market Sizing → PRICE TAM/SAM/SOM + PLACE population
4. Market Segmentation → PRODUCT demand by type + PLACE demographics
5. Competitive Landscape → PROMOTION competitor analysis
6. Market Trends → PRODUCT trends + PLACE growth trajectories
7. Consumer Analysis → PRODUCT demand signals + PRICE spending power
8. Market Forecast → PLACE growth + PRODUCT trend momentum
9. Opportunity Assessment → Weighted score from all 4 P's
```

### Feasibility Study
```
Required:
├── PRODUCT: opportunity_score, pain_intensity, demand_validation
├── PRICE: capital_requirements, revenue_benchmarks, addressable_market
├── PLACE: traffic_aadt, population, growth_score, site_recommendations
└── PROMOTION: competition_level, success_factors, failure_points

Sections:
1. Viability Summary → PRODUCT score + PRICE economics
2. Market Demand → PRODUCT demand signals + validation
3. Location Analysis → PLACE traffic + demographics + growth
4. Financial Feasibility → PRICE capital + revenue + market size
5. Competitive Position → PROMOTION competitors + differentiation
6. Risk Assessment → PROMOTION failure_points + PLACE vacancy
7. Go/No-Go Recommendation → Weighted 4 P's decision
```

### Business Plan
```
Required:
├── PRODUCT: problem_statement, target_audience, demand_signals
├── PRICE: revenue_model, capital_required, financial_projections
├── PLACE: location_strategy, service_area, demographics
└── PROMOTION: marketing_strategy, competitive_advantages

Sections:
1. Executive Summary → All 4 P's
2. Problem & Solution → PRODUCT pain + demand
3. Market Opportunity → PRICE TAM + PLACE growth
4. Business Model → PRICE revenue streams
5. Go-to-Market → PROMOTION strategy + PLACE targeting
6. Competition → PROMOTION landscape + differentiators
7. Team & Operations → (User input)
8. Financial Plan → PRICE projections + benchmarks
9. Funding Ask → PRICE capital requirements
```

### Financial Projections
```
Required:
├── PRODUCT: market_size_estimate, demand_growth_rate
├── PRICE: revenue_benchmarks, capital_spent, addressable_market
├── PLACE: population, household_count, spending_power_index
└── PROMOTION: market_share_estimate (from competition density)

Outputs:
- 3-Year Revenue Projection
- Unit Economics
- Break-even Analysis
- Cash Flow Forecast
- Sensitivity Analysis
```

### PESTLE Analysis
```
Required:
├── Political: (External research)
├── Economic: PRICE rent_trends, income_growth, PLACE job_growth
├── Social: PRODUCT demand_signals, PLACE demographics, migration
├── Technological: PRODUCT trend_strength (tech categories)
├── Legal: (External research + zoning)
└── Environmental: (Climate data + sustainability trends)
```

### Strategic Assessment (SWOT)
```
Required:
├── Strengths: PRODUCT opportunity_score, unique_demand_gaps
├── Weaknesses: PROMOTION competition_level, PRICE capital_requirements
├── Opportunities: PLACE growth_trajectories, PRODUCT rising_trends
└── Threats: PLACE supply_pipeline, PROMOTION competitor_growth
```

### Competitive Analysis
```
Required:
├── Direct Competitors: google_maps_businesses (same category)
├── Indirect Competitors: google_maps_businesses (adjacent)
├── Market Share: Estimated from review volume distribution
├── Strengths/Weaknesses: Review sentiment analysis
├── Pricing: price_level comparison
└── Gaps: Unmet demand vs competitor offerings
```

### Pitch Deck
```
Required:
├── Problem Slide: PRODUCT pain_intensity, demand_signals
├── Solution Slide: (User input)
├── Market Size: PRICE TAM/SAM/SOM
├── Traction: (User input) + PRODUCT validation_count
├── Competition: PROMOTION matrix
├── Business Model: PRICE revenue_benchmarks
├── Team: (User input)
├── Financials: PRICE projections summary
└── Ask: PRICE capital_required
```

---

## Data Fetch Priority

### Tier 1: Always Fetch (Critical)
```python
TIER_1_DATA = [
    "opportunity_context",      # From opportunity record
    "demand_signals",           # JediRE API
    "market_economics",         # JediRE API
    "demographics_basic",       # Census/cache
    "competitor_summary",       # Google Maps count/avg
]
```

### Tier 2: Report-Specific (Fetch if report type needs)
```python
TIER_2_DATA = {
    "market_analysis": ["rent_comps", "absorption_rate", "supply_pipeline", "search_trends"],
    "feasibility": ["traffic_aadt", "success_patterns", "site_recommendations"],
    "financial": ["revenue_benchmarks", "capital_benchmarks", "addressable_market"],
    "competitive": ["competitor_details", "review_sentiment", "price_levels"],
    "business_plan": ["service_area", "growth_trajectory", "migration_flows"],
}
```

### Tier 3: Enhancement (Nice to have)
```python
TIER_3_DATA = [
    "user_preferences_full",    # Full amenity breakdown
    "trend_details",            # Historical trend data
    "similar_opportunities",    # Pattern matching
    "success_stories",          # Case studies
]
```

---

## Implementation Checklist

### Phase 1: Data Aggregation Service
- [ ] Create `ReportDataService` class
- [ ] Implement 4 P's data aggregation
- [ ] Add caching layer (Redis/memory)
- [ ] Build fallback chains for missing data

### Phase 2: Report Generator Integration
- [ ] Update each `generate_*` method to accept full data context
- [ ] Add data availability indicators to prompts
- [ ] Implement dynamic section inclusion based on data

### Phase 3: Quality Scoring
- [ ] Score data completeness (0-100%)
- [ ] Flag low-confidence data points
- [ ] Show data sources in report footer

### Phase 4: Real-time Enhancement
- [ ] Background data refresh on report request
- [ ] Stale data indicators
- [ ] Manual refresh triggers

---

## Data Quality Rules

| Condition | Action |
|-----------|--------|
| Demand signals < 3 | Use detected_trends as fallback |
| Market economics missing | Use Census ACS income data |
| Competitors < 5 | Expand search radius |
| Traffic data missing | Estimate from population density |
| Growth trajectory stale > 30 days | Trigger refresh |
| Success patterns < 3 for category | Use adjacent category |

---

## API Contract

### ReportDataService.get_report_data()

```python
async def get_report_data(
    city: str,
    state: str,
    business_type: str,
    report_type: str,
    opportunity_id: int = None
) -> ReportDataContext:
    """
    Returns:
    {
        "product": {
            "opportunity_score": 78,
            "pain_intensity": 7,
            "demand_signals": [...],
            "trend_strength": 65,
            "unmet_demand": [...]
        },
        "price": {
            "market_size": "$10M-$50M",
            "median_rent": 1850,
            "spending_power_index": 72,
            "addressable_market": 2500000,
            "revenue_benchmark": 450000
        },
        "place": {
            "population": 245000,
            "population_growth": 2.3,
            "job_growth": 3.1,
            "growth_category": "growing",
            "traffic_aadt": 45000,
            "vacancy_rate": 5.2
        },
        "promotion": {
            "competitor_count": 12,
            "avg_competitor_rating": 4.1,
            "competition_level": "medium",
            "success_factors": [...]
        },
        "data_quality": {
            "completeness": 0.85,
            "freshness": "2 days",
            "confidence": 0.78
        }
    }
    """
```

---

*Last Updated: 2026-03-31*
*Version: 1.0*
