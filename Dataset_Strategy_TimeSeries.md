# OppGrid Dataset Strategy — Time-Series Edition

## Guiding Principle

Every dataset we sell must be **data that the platform already generates to power its own features**. We do not resell generic third-party data. We sell **the same structured intelligence** that makes OppGrid's Consultant Studio, Report Library, and AI recommendations work.

This guarantees three things:
1. **Provenance is real** — every row came from a platform pipeline
2. **Quality is self-validating** — if the data is bad, the platform breaks first
3. **Value is immediate** — the buyer gets the same intelligence the AI uses

---

## Time-Series Architecture

All datasets are **append-only, immutable, time-indexed**. Every row is a snapshot in time. We never overwrite data — we create new rows with new `effective_date` values.

### Core Time-Series Fields (Every Table)

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `snapshot_id` | string | Unique batch identifier | `snap-2026-06-15-001` |
| `effective_date` | date | The date this record represents | `2026-06-15` |
| `first_seen_date` | date | When this entity first appeared | `2026-05-20` |
| `is_latest` | boolean | Fast current-state filter | `true` |
| `supersedes_id` | string | Previous version of this entity | `sig-abc123-v1` |
| `collected_at` | datetime | Exact timestamp | `2026-06-15T14:00:00Z` |
| `data_source_label` | string | Human-readable origin | `RedditScraper` |
| `data_quality_score` | int | 0-100 freshness + reliability + AI confidence | `94` |
| `refresh_cadence` | string | `daily`, `weekly`, `monthly`, `quarterly` | `daily` |
| `period_type` | string | `daily`, `weekly`, `monthly`, `quarterly`, `annual` | `daily` |
| `change_7d` | float | % change from 7 days ago | `+6.1%` |
| `change_30d` | float | % change from 30 days ago | `+16.0%` |
| `change_90d` | float | % change from 90 days ago | `+27.9%` |
| `percentile_rank` | int | 0-100 relative standing in dataset | `91` |
| `trend_direction` | string | `accelerating`, `growing`, `stable`, `decelerating`, `declining` | `accelerating` |
| `seasonality_index` | float | 1.0 = normal, >1.0 = peak season | `1.15` |
| `forecast_7d` | float | AI-predicted value | `91` |
| `forecast_30d` | float | AI-predicted value | `94` |

### Query Patterns Supported

```sql
-- 1. Current state (fast: only latest)
SELECT * FROM signal_matrix WHERE is_latest = true AND city = 'Austin';

-- 2. Time-series trend (for forecasting)
SELECT effective_date, AVG(signal_strength) 
FROM signal_matrix 
WHERE vertical = 'coffee_shop' AND city = 'Austin'
GROUP BY effective_date ORDER BY effective_date;

-- 3. Momentum analysis (which signals are accelerating)
SELECT signal_id, change_7d, change_30d, change_90d, trend_direction
FROM signal_matrix WHERE is_latest = true
ORDER BY change_30d DESC LIMIT 50;

-- 4. Seasonality detection
SELECT EXTRACT(MONTH FROM effective_date) as month, AVG(signal_strength)
FROM signal_matrix WHERE city = 'Austin' AND vertical = 'coffee_shop'
GROUP BY month ORDER BY month;

-- 5. Point-in-time comparison (what did the market look like on March 1?)
SELECT * FROM market_data
WHERE effective_date = '2026-03-01' AND city = 'Austin' AND vertical = 'coffee_shop';

-- 6. Change tracking (how has this opportunity evolved)
SELECT effective_date, opportunity_score, competition_density, market_size_estimate
FROM opportunity_feed WHERE opportunity_id = 'opp-xyz789'
ORDER BY effective_date;
```

---

## Tier 1: Opportunity Signal Data (Time-Series)

**What:** Raw, validated demand signals from every scraper and signal detector. These are the inputs that feed the AI's opportunity scoring.

**Why it's valuable to new business creation:**
- Shows **proven demand** before spending money on a location
- Reveals **pain points** consumers are actually expressing
- Gives **momentum indicators** — is demand growing or shrinking?
- Enables **time-series forecasting** — predict where the market will be in 30 days

**Datasets:**

### 1.1 — Signal Matrix: Demand Signals by City/Vertical (Time-Series)

| Field | Type | Example |
|-------|------|---------|
| `signal_id` | string | `sig-abc123` |
| `snapshot_id` | string | `snap-2026-06-15-001` |
| `effective_date` | date | `2026-06-15` |
| `first_seen_date` | date | `2026-05-20` |
| `is_latest` | boolean | `true` |
| `supersedes_id` | string | `sig-abc123-v1` |
| `signal_type` | string | `reddit_demand` |
| `vertical` | string | `coffee_shop` |
| `city` | string | `Austin` |
| `state` | string | `TX` |
| `signal_strength` | float | `87` |
| `signal_strength_7d` | float | `82` |
| `signal_strength_30d` | float | `75` |
| `signal_strength_90d` | float | `68` |
| `change_7d` | float | `+6.1%` |
| `change_30d` | float | `+16.0%` |
| `change_90d` | float | `+27.9%` |
| `trend_direction` | string | `accelerating` |
| `percentile_rank` | int | `91` |
| `seasonality_index` | float | `1.15` |
| `forecast_7d` | float | `91` |
| `forecast_30d` | float | `94` |
| `pain_intensity` | float | `8.2` |
| `urgency_level` | string | `high` |
| `keyword_density` | int | `12` |
| `source_url` | string | `reddit.com/r/Austin/...` |
| `collected_at` | datetime | `2026-06-15T14:00:00Z` |
| `data_source_label` | string | `RedditScraper` |
| `data_quality_score` | int | `94` |
| `refresh_cadence` | string | `daily` |
| `period_type` | string | `daily` |

**Provenance:** Direct from `ScrapeJob` → `DetectedTrend` → AI enrichment pipeline
**Refresh:** Daily (nightly scraper runs)
**Price:** $49/city or $199/month unlimited
**Powers:** Consultant Studio "Validate Idea", discovery feed ranking, AI opportunity scoring, trend forecasting

### 1.2 — Enriched Opportunity Feed (Time-Series)

| Field | Type | Example |
|-------|------|---------|
| `opportunity_id` | string | `opp-xyz789` |
| `snapshot_id` | string | `snap-2026-06-15-001` |
| `effective_date` | date | `2026-06-15` |
| `first_seen_date` | date | `2026-04-10` |
| `is_latest` | boolean | `true` |
| `supersedes_id` | string | `opp-xyz789-v1` |
| `title` | string | `Coffee Shop Gap in East Austin` |
| `category` | string | `coffee_shop` |
| `city` | string | `Austin` |
| `state` | string | `TX` |
| `ai_opportunity_score` | float | `84` |
| `ai_opportunity_score_7d` | float | `80` |
| `ai_opportunity_score_30d` | float | `72` |
| `ai_opportunity_score_90d` | float | `65` |
| `change_7d` | float | `+5.0%` |
| `change_30d` | float | `+16.7%` |
| `change_90d` | float | `+29.2%` |
| `trend_direction` | string | `accelerating` |
| `percentile_rank` | int | `88` |
| `pain_intensity` | float | `8.2` |
| `urgency_level` | string | `high` |
| `market_size_estimate` | string | `$1.2M-$2.8M` |
| `market_size_usd_7d` | float | `1,100,000` |
| `market_size_usd_30d` | float | `1,000,000` |
| `market_size_usd_90d` | float | `900,000` |
| `market_size_growth_30d_pct` | float | `+20.0%` |
| `competition_density` | string | `low` |
| `competitor_count` | int | `34` |
| `competitor_count_7d` | int | `33` |
| `competitor_count_30d` | int | `30` |
| `competitor_count_90d` | int | `27` |
| `competition_growth_30d_pct` | float | `+13.3%` |
| `feasibility_score` | float | `78` |
| `feasibility_score_30d` | float | `72` |
| `data_freshness` | string | `live` |
| `signals_count` | int | `23` |
| `signals_count_7d` | int | `21` |
| `signals_count_30d` | int | `18` |
| `forecast_7d` | float | `87` |
| `forecast_30d` | float | `91` |
| `collected_at` | datetime | `2026-06-15T14:00:00Z` |
| `data_source_label` | string | `HubOpportunityEnriched` |
| `data_quality_score` | int | `92` |
| `refresh_cadence` | string | `daily` |
| `period_type` | string | `daily` |

**Provenance:** `HubOpportunityEnriched` — aggregated from all scrapers + AI analysis
**Refresh:** Daily
**Price:** $99/city or $299/month unlimited
**Powers:** Discovery feed, Consultant Studio "Search Ideas", AI recommendations, trend forecasting

---

## Tier 2: Market Intelligence (4P's Time-Series)

**What:** The same structured 4P's data that powers every report, but indexed over time.

**Why it's valuable:**
- Gives **the same structured market data** the AI uses to write business plans
- Shows **how the market is changing** — not just a snapshot
- Enables **AI modeling** — time-series training data for forecasting models

**Datasets:**

### 2.1 — 4P's Product: Demand (Time-Series)

| Field | Type | Example |
|-------|------|---------|
| `market_id` | string | `mkt-austin-tx-coffee` |
| `snapshot_id` | string | `snap-2026-06-15-001` |
| `effective_date` | date | `2026-06-15` |
| `is_latest` | boolean | `true` |
| `city` | string | `Austin` |
| `state` | string | `TX` |
| `vertical` | string | `coffee_shop` |
| `opportunity_score` | float | `84` |
| `opportunity_score_30d` | float | `78` |
| `opportunity_score_90d` | float | `72` |
| `change_30d` | float | `+7.7%` |
| `change_90d` | float | `+16.7%` |
| `trend_direction` | string | `accelerating` |
| `percentile_rank` | int | `88` |
| `pain_intensity` | float | `8.2` |
| `pain_intensity_30d` | float | `7.8` |
| `trend_strength` | float | `76` |
| `trend_strength_30d` | float | `70` |
| `signal_density` | float | `34%` |
| `signal_density_30d` | float | `30%` |
| `validation_confidence` | float | `91` |
| `google_trends_interest` | float | `78` |
| `google_trends_interest_30d` | float | `72` |
| `google_trends_direction` | string | `rising` |
| `top_consumer_demands` | JSON | `["wifi", "outdoor_seating", "parking"]` |
| `collected_at` | datetime | `2026-06-15T14:00:00Z` |
| `data_source_label` | string | `ReportDataService.Product` |
| `data_quality_score` | int | `91` |
| `refresh_cadence` | string | `weekly` |
| `period_type` | string | `daily` |

**Provenance:** `ReportDataService.get_product_data()` — from scrapers + Google Trends + AI analysis
**Refresh:** Weekly
**Price:** $149/city/vertical or $499/month unlimited
**Powers:** Consultant Studio reports, AI report generation, business plan data context

### 2.2 — 4P's Price: Economics (Time-Series)

| Field | Type | Example |
|-------|------|---------|
| `market_id` | string | `mkt-austin-tx-coffee` |
| `snapshot_id` | string | `snap-2026-06-15-001` |
| `effective_date` | date | `2026-06-15` |
| `is_latest` | boolean | `true` |
| `city` | string | `Austin` |
| `state` | string | `TX` |
| `vertical` | string | `coffee_shop` |
| `market_size_estimate` | string | `$1.2M-$2.8M` |
| `market_size_usd` | float | `1,200,000` |
| `market_size_usd_30d` | float | `1,150,000` |
| `market_size_usd_90d` | float | `1,050,000` |
| `market_size_growth_30d_pct` | float | `+13.0%` |
| `addressable_market_value` | float | `890,000` |
| `median_income` | float | `72,000` |
| `median_income_30d` | float | `71,500` |
| `median_income_90d` | float | `70,800` |
| `income_growth_30d_pct` | float | `+0.7%` |
| `revenue_benchmark` | float | `420,000` |
| `revenue_benchmark_30d` | float | `410,000` |
| `capital_required` | float | `85,000` |
| `median_rent` | float | `2,800` |
| `median_rent_30d` | float | `2,750` |
| `rent_growth_30d_pct` | float | `+1.8%` |
| `spending_power_index` | float | `68` |
| `spending_power_index_30d` | float | `67` |
| `collected_at` | datetime | `2026-06-15T14:00:00Z` |
| `data_source_label` | string | `Census + BLS + AI` |
| `data_quality_score` | int | `93` |
| `refresh_cadence` | string | `monthly` |
| `period_type` | string | `daily` |

**Provenance:** `ReportDataService.get_price_data()` — from Census, BLS, FRED, AI estimation
**Refresh:** Monthly
**Price:** $149/city/vertical or $499/month unlimited
**Powers:** Financial report generation, pricing strategy, market sizing

### 2.3 — 4P's Place: Location Intelligence (Time-Series)

| Field | Type | Example |
|-------|------|---------|
| `market_id` | string | `mkt-austin-tx-coffee` |
| `snapshot_id` | string | `snap-2026-06-15-001` |
| `effective_date` | date | `2026-06-15` |
| `is_latest` | boolean | `true` |
| `city` | string | `Austin` |
| `state` | string | `TX` |
| `growth_score` | float | `82` |
| `growth_score_30d` | float | `78` |
| `growth_score_90d` | float | `74` |
| `change_30d` | float | `+5.1%` |
| `growth_category` | string | `hot` |
| `population` | int | `978,000` |
| `population_30d` | int | `973,000` |
| `population_90d` | int | `965,000` |
| `population_growth_30d_pct` | float | `+0.5%` |
| `job_growth_rate` | float | `3.4` |
| `job_growth_rate_30d` | float | `3.2` |
| `business_formation_rate` | float | `4.7` |
| `business_formation_rate_30d` | float | `4.5` |
| `traffic_aadt` | int | `45,000` |
| `traffic_aadt_30d` | int | `44,000` |
| `vacancy_rate` | float | `8.2` |
| `vacancy_rate_30d` | float | `8.5` |
| `unemployment_rate` | float | `3.1` |
| `unemployment_rate_30d` | float | `3.3` |
| `job_postings_count` | int | `12,400` |
| `job_postings_count_30d` | int | `12,100` |
| `foot_traffic_score` | float | `71` |
| `foot_traffic_score_30d` | float | `69` |
| `collected_at` | datetime | `2026-06-15T14:00:00Z` |
| `data_source_label` | string | `Census + BLS + DOT` |
| `data_quality_score` | int | `90` |
| `refresh_cadence` | string | `monthly` |
| `period_type` | string | `daily` |

**Provenance:** `ReportDataService.get_place_data()` — from Census, BLS, DOT, municipal data
**Refresh:** Monthly
**Price:** $199/city or $599/month unlimited
**Powers:** Location Analysis reports, Identify Location tool, map workspace, zone analysis

### 2.4 — 4P's Promotion: Competition (Time-Series)

| Field | Type | Example |
|-------|------|---------|
| `market_id` | string | `mkt-austin-tx-coffee` |
| `snapshot_id` | string | `snap-2026-06-15-001` |
| `effective_date` | date | `2026-06-15` |
| `is_latest` | boolean | `true` |
| `city` | string | `Austin` |
| `state` | string | `TX` |
| `vertical` | string | `coffee_shop` |
| `competition_level` | string | `moderate` |
| `competitor_count` | int | `34` |
| `competitor_count_7d` | int | `33` |
| `competitor_count_30d` | int | `30` |
| `competitor_count_90d` | int | `27` |
| `competition_growth_30d_pct` | float | `+13.3%` |
| `avg_competitor_rating` | float | `4.2` |
| `avg_competitor_rating_30d` | float | `4.1` |
| `success_factors` | JSON | `["quality", "location", "service"]` |
| `key_risks` | JSON | `["high_rent", "staffing"]` |
| `competitive_advantages` | JSON | `["wifi", "outdoor_seating", "parking"]` |
| `collected_at` | datetime | `2026-06-15T14:00:00Z` |
| `data_source_label` | string | `Google Maps + AI` |
| `data_quality_score` | int | `89` |
| `refresh_cadence` | string | `weekly` |
| `period_type` | string | `daily` |

**Provenance:** `ReportDataService.get_promotion_data()` — from Google Maps scraper + AI review analysis
**Refresh:** Weekly
**Price:** $99/city/vertical or $399/month unlimited
**Powers:** Competitive analysis, clone success analysis, Consultant Studio "Clone Success"

---

## Tier 3: Economic Intelligence (Time-Series)

### 3.1 — Economic Snapshot (Time-Series)

| Field | Type | Example |
|-------|------|---------|
| `snapshot_id` | string | `snap-2026-06-15-001` |
| `effective_date` | date | `2026-06-15` |
| `is_latest` | boolean | `true` |
| `fed_funds_rate` | float | `5.25` |
| `fed_funds_rate_30d` | float | `5.25` |
| `fed_funds_rate_90d` | float | `5.50` |
| `inflation_rate` | float | `3.2` |
| `inflation_rate_30d` | float | `3.3` |
| `inflation_rate_90d` | float | `3.5` |
| `unemployment` | float | `3.8` |
| `unemployment_30d` | float | `3.9` |
| `gdp_growth` | float | `2.4` |
| `gdp_growth_30d` | float | `2.3` |
| `consumer_sentiment` | float | `72.3` |
| `consumer_sentiment_30d` | float | `70.1` |
| `mortgage_rate` | float | `6.8` |
| `mortgage_rate_30d` | float | `6.9` |
| `economic_stress_index` | float | `42.0` |
| `economic_stress_index_30d` | float | `44.0` |
| `change_30d` | float | `+0.0%` (composite) |
| `collected_at` | datetime | `2026-06-15T14:00:00Z` |
| `data_source_label` | string | `FRED + BLS` |
| `data_quality_score` | int | `98` |
| `refresh_cadence` | string | `daily` |
| `period_type` | string | `daily` |

**Provenance:** `FREDService.get_macro_context()` — from FRED API + BLS API
**Refresh:** Daily (nightly cron job)
**Price:** $49/month (all dates) or $199 for 12-month historical
**Powers:** Economic Intelligence Panel, report generation, AI context injection

### 3.2 — Industry Benchmarks (Time-Series)

| Field | Type | Example |
|-------|------|---------|
| `vertical` | string | `coffee_shop` |
| `naics_code` | string | `722515` |
| `snapshot_id` | string | `snap-2026-06-15-001` |
| `effective_date` | date | `2026-06-15` |
| `is_latest` | boolean | `true` |
| `avg_revenue` | float | `420,000` |
| `avg_revenue_30d` | float | `415,000` |
| `avg_revenue_90d` | float | `405,000` |
| `avg_revenue_growth_30d_pct` | float | `+1.2%` |
| `avg_payroll` | float | `180,000` |
| `employment_count` | int | `12,400` |
| `employment_count_30d` | int | `12,300` |
| `employment_trend` | float | `+2.1%` |
| `wage_trend` | float | `+3.4%` |
| `growth_rate` | float | `+4.2%` |
| `top_performing_states` | JSON | `["TX", "FL", "NC"]` |
| `collected_at` | datetime | `2026-06-15T14:00:00Z` |
| `data_source_label` | string | `BLS QCEW + SEC-API` |
| `data_quality_score` | int | `95` |
| `refresh_cadence` | string | `quarterly` |
| `period_type` | string | `quarterly` |

**Provenance:** `ReportDataService` + BLS QCEW + SEC-API
**Refresh:** Quarterly
**Price:** $199/vertical or $599/month unlimited
**Powers:** Industry analysis reports, financial model benchmarks, competitive benchmarking

---

## Tier 4: Traffic & Foot Traffic (Time-Series)

### 4.1 — Drive-By Traffic by Road Segment (Time-Series)

| Field | Type | Example |
|-------|------|---------|
| `road_id` | string | `rd-ih35-austin-001` |
| `snapshot_id` | string | `snap-2026-06-15-001` |
| `effective_date` | date | `2026-06-15` |
| `is_latest` | boolean | `true` |
| `road_name` | string | `IH-35` |
| `city` | string | `Austin` |
| `state` | string | `TX` |
| `aadt` | int | `145,000` |
| `aadt_30d` | int | `142,000` |
| `aadt_90d` | int | `138,000` |
| `traffic_growth_30d_pct` | float | `+2.1%` |
| `trend_direction` | string | `increasing` |
| `peak_hours` | JSON | `["morning", "evening"]` |
| `collected_at` | datetime | `2026-06-15T14:00:00Z` |
| `data_source_label` | string | `State DOT + Google Traffic` |
| `data_quality_score` | int | `88` |
| `refresh_cadence` | string | `monthly` |
| `period_type` | string | `daily` |

**Provenance:** State DOT APIs + Google Traffic API
**Refresh:** Monthly (DOT) + real-time (Google)
**Price:** $99/city or $399/month unlimited
**Powers:** Traffic layer on map, location analysis, drive-by visibility scoring

### 4.2 — Foot Traffic Heatmap (Time-Series)

| Field | Type | Example |
|-------|------|---------|
| `location_id` | string | `loc-downtown-austin-001` |
| `snapshot_id` | string | `snap-2026-06-15-001` |
| `effective_date` | date | `2026-06-15` |
| `is_latest` | boolean | `true` |
| `lat` | float | `30.2672` |
| `lng` | float | `-97.7431` |
| `foot_traffic_score` | float | `78` |
| `foot_traffic_score_30d` | float | `75` |
| `foot_traffic_growth_30d_pct` | float | `+4.0%` |
| `peak_days` | JSON | `["Friday", "Saturday"]` |
| `peak_hours` | JSON | `["12:00-14:00", "18:00-21:00"]` |
| `dwell_time_minutes` | float | `45` |
| `dwell_time_minutes_30d` | float | `43` |
| `visitor_demographics` | JSON | `{age: "25-34", income: "70k-100k"}` |
| `collected_at` | datetime | `2026-06-15T14:00:00Z` |
| `data_source_label` | string | `Municipal` |
| `data_quality_score` | int | `82` |
| `refresh_cadence` | string | `weekly` |
| `period_type` | string | `daily` |

**Provenance:** Municipal data + third-party foot traffic providers (if licensed)
**Refresh:** Weekly
**Price:** $149/city or $499/month unlimited
**Powers:** Foot traffic layer, zone analysis, optimal location finder

---

## Quality Tiers

- `LIVE` — < 24h old, direct API pull
- `RECENT` — < 7 days old, cached API pull
- `STALE` — > 7 days old, needs refresh
- `SIMULATED` — AI-generated fallback (only for empty markets, clearly labeled)

---

## Pricing Architecture

| Tier | Price Model | Target Buyer |
|------|-------------|--------------|
| **Starter** — 1 city, 1 vertical | $49 one-time | Individual entrepreneur testing an idea |
| **Growth** — 5 cities, 3 verticals | $199/month | Small business owner expanding |
| **Pro** — Unlimited cities, all verticals | $499/month | Consultant, franchise owner |
| **Enterprise** — API access + raw data | $1,999/month | Data team, AI model builder |

**Bundles:**
- **Opportunity Bundle** — Tiers 1.1 + 1.2 + 2.4 — $149/city
- **Market Intelligence Bundle** — Tiers 2.1 + 2.2 + 2.3 + 2.4 — $349/city
- **Complete Intelligence Bundle** — All tiers — $599/city or $999/month
- **Economic Intelligence Add-on** — Tier 3 — $49/month
- **Traffic Intelligence Add-on** — Tier 4 — $149/month

---

## Next Steps

1. **Validate the catalog** — Which datasets exist in the DB already? Which need new pipelines?
2. **Check scraper status** — Are the SerpAPI, Reddit, Craigslist, Google Trends scrapers still running and populating tables?
3. **Add time-series fields** — Add `snapshot_id`, `effective_date`, `is_latest`, `change_7d`, `change_30d`, `change_90d`, `percentile_rank` to all data hub models
4. **Create dataset definitions** — Create `Dataset` records in the DB that map to these schemas
5. **Test CSV generation** — Verify each dataset type generates real CSVs from real DB data
6. **Re-enable marketplace** — Remove the 503 once we have > 100 real rows per table with time-series depth
