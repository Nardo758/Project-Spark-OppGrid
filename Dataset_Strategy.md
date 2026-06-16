# OppGrid Dataset Strategy — Valuable to New Business Creation, AI Modeling, and Consultant Studio

## Guiding Principle

Every dataset we sell must be **data that the platform already generates to power its own features**. We do not resell generic third-party data. We sell **the same structured intelligence** that makes OppGrid's Consultant Studio, Report Library, and AI recommendations work.

This guarantees three things:
1. **Provenance is real** — every row came from a platform pipeline
2. **Quality is self-validating** — if the data is bad, the platform breaks first
3. **Value is immediate** — the buyer gets the same intelligence the AI uses

---

## Tier 1: Opportunity Signal Data (Platform's Core Intelligence)

**What:** Raw, validated demand signals from every scraper and signal detector the platform runs. These are the inputs that feed the AI's opportunity scoring.

**Why it's valuable to new business creation:**
- Shows **proven demand** before a user spends money on a location
- Reveals **pain points** consumers are actually expressing (Reddit complaints, Craigslist gaps, Google search trends)
- Gives **momentum indicators** — is demand growing or shrinking?

**Datasets:**

### 1.1 — Signal Matrix: Demand Signals by City/Vertical
| Field | Source | Example |
|-------|--------|---------|
| signal_id | Platform generated | `sig-abc123` |
| signal_type | Reddit, Craigslist, Google Trends, News, Apify | `reddit_demand` |
| vertical | AI-classified | `coffee_shop`, `fitness_center` |
| city | Extracted from post | `Austin` |
| state | Extracted from post | `TX` |
| signal_strength | AI-scored 0-100 | `87` |
| pain_intensity | NLP sentiment + keyword density | `8.2` |
| urgency_level | Time-sensitive language detection | `high` |
| trend_direction | `growing`, `stable`, `declining` | `growing` |
| keyword_density | How many demand keywords appear | `12` |
| source_url | Original URL | `reddit.com/r/Austin/...` |
| collected_at | Scraper timestamp | `2026-06-15T14:00:00Z` |
| data_source_label | `RedditScraper`, `CraigslistScraper`, `SerpAPI` | `RedditScraper` |

**Provenance:** Direct from `ScrapeJob` → `DetectedTrend` → AI enrichment pipeline
**Refresh:** Daily (nightly scraper runs)
**Price:** $49/city or $199/month unlimited
**Powers:** Consultant Studio "Validate Idea" mode, discovery feed ranking, AI opportunity scoring

### 1.2 — Enriched Opportunity Feed
| Field | Source | Example |
|-------|--------|---------|
| opportunity_id | Platform generated | `opp-xyz789` |
| title | AI-generated from signals | `Coffee Shop Gap in East Austin` |
| category | AI-classified | `coffee_shop` |
| city | `Austin` | `Austin` |
| state | `TX` | `TX` |
| ai_opportunity_score | 0-100 composite | `84` |
| pain_intensity | 1-10 | `8.2` |
| urgency_level | `low`, `medium`, `high` | `high` |
| market_size_estimate | AI-estimated | `$1.2M-$2.8M` |
| competition_density | `low`, `moderate`, `high` | `low` |
| trend_momentum | `accelerating`, `stable`, `decelerating` | `accelerating` |
| feasibility_score | 0-100 | `78` |
| data_freshness | `live`, `recent`, `stale` | `live` |
| signals_count | How many raw signals fed this opp | `23` |
| data_source_label | `HubOpportunityEnriched (real)` | `HubOpportunityEnriched` |

**Provenance:** `HubOpportunityEnriched` — aggregated from all scrapers + AI analysis
**Refresh:** Daily
**Price:** $99/city or $299/month unlimited
**Powers:** Discovery feed, Consultant Studio "Search Ideas", AI recommendations

---

## Tier 2: Market Intelligence (4P's Structured Data)

**What:** The same structured data that powers the 4P's (Product, Price, Place, Promotion) analysis in every report.

**Why it's valuable to new business creation:**
- Gives the **same structured market data** the AI uses to write business plans and location analyses
- Shows **demographic fit**, **competition density**, **economic health**, and **consumer spending power**
- Can be used for **AI modeling** — training custom models on real market data

**Datasets:**

### 2.1 — 4P's Market Data: Product (Demand)
| Field | Source | Example |
|-------|--------|---------|
| market_id | Platform generated | `mkt-austin-tx` |
| city | `Austin` | `Austin` |
| state | `TX` | `TX` |
| vertical | `coffee_shop` | `coffee_shop` |
| opportunity_score | 0-100 | `84` |
| pain_intensity | 1-10 | `8.2` |
| urgency_level | `high` | `high` |
| trend_strength | 0-100 | `76` |
| signal_density | % of posts with demand keywords | `34%` |
| validation_confidence | 0-100 | `91` |
| google_trends_interest | Relative search volume | `78` |
| google_trends_direction | `rising`, `stable`, `falling` | `rising` |
| top_consumer_demands | JSON array of amenities | `["wifi", "outdoor_seating", "parking"]` |
| data_source_label | `ReportDataService.Product` | `ReportDataService.Product` |

**Provenance:** `ReportDataService.get_product_data()` — from scrapers + Google Trends + AI analysis
**Refresh:** Weekly
**Price:** $149/city/vertical or $499/month unlimited
**Powers:** Consultant Studio reports, AI report generation, business plan data context

### 2.2 — 4P's Market Data: Price (Economics)
| Field | Source | Example |
|-------|--------|---------|
| market_id | Platform generated | `mkt-austin-tx` |
| city | `Austin` | `Austin` |
| state | `TX` | `TX` |
| vertical | `coffee_shop` | `coffee_shop` |
| market_size_estimate | AI-estimated | `$1.2M-$2.8M` |
| addressable_market_value | Computed from census + vertical | `$890,000` |
| median_income | Census ACS | `$72,000` |
| revenue_benchmark | BLS QCEW + SEC data | `$420,000/year` |
| capital_required | AI-estimated | `$85,000` |
| median_rent | Census/municipal | `$2,800/month` |
| spending_power_index | 0-100 composite | `68` |
| income_growth_rate | % YoY | `4.2%` |
| data_source_label | `Census + BLS + AI` | `Census + BLS + AI` |

**Provenance:** `ReportDataService.get_price_data()` — from Census, BLS, FRED, AI estimation
**Refresh:** Monthly (Census is annual, BLS is quarterly, FRED is monthly)
**Price:** $149/city/vertical or $499/month unlimited
**Powers:** Financial report generation, pricing strategy recommendations, market sizing

### 2.3 — 4P's Market Data: Place (Location Intelligence)
| Field | Source | Example |
|-------|--------|---------|
| market_id | Platform generated | `mkt-austin-tx` |
| city | `Austin` | `Austin` |
| state | `TX` | `TX` |
| growth_score | 0-100 composite | `82` |
| growth_category | `hot`, `warm`, `stable`, `cooling` | `hot` |
| population | Census | `978,000` |
| population_growth_rate | % YoY | `2.1%` |
| job_growth_rate | % YoY | `3.4%` |
| business_formation_rate | % YoY | `4.7%` |
| traffic_aadt | DOT data | `45,000` |
| vacancy_rate | Municipal | `8.2%` |
| unemployment_rate | BLS | `3.1%` |
| job_postings_count | Scraped | `12,400` |
| foot_traffic_score | 0-100 (if available) | `71` |
| data_source_label | `Census + BLS + DOT + Municipal` | `Census + BLS + DOT` |

**Provenance:** `ReportDataService.get_place_data()` — from Census, BLS, DOT, municipal data, traffic data
**Refresh:** Monthly
**Price:** $199/city or $599/month unlimited
**Powers:** Location Analysis reports, Identify Location tool, map workspace, zone analysis

### 2.4 — 4P's Market Data: Promotion (Competition)
| Field | Source | Example |
|-------|--------|---------|
| market_id | Platform generated | `mkt-austin-tx` |
| city | `Austin` | `Austin` |
| state | `TX` | `TX` |
| vertical | `coffee_shop` | `coffee_shop` |
| competition_level | `low`, `moderate`, `high`, `saturated` | `moderate` |
| competitor_count | Google Maps scraper | `34` |
| avg_competitor_rating | Google Maps | `4.2` |
| success_factors | AI-extracted from reviews | `["quality", "location", "service"]` |
| key_risks | AI-extracted from reviews | `["high_rent", "staffing"]` |
| competitive_advantages | AI-identified gaps | `["wifi", "outdoor_seating", "parking"]` |
| data_source_label | `Google Maps + AI` | `Google Maps + AI` |

**Provenance:** `ReportDataService.get_promotion_data()` — from Google Maps scraper + AI review analysis
**Refresh:** Weekly
**Price:** $99/city/vertical or $399/month unlimited
**Powers:** Competitive analysis, clone success analysis, Consultant Studio "Clone Success"

---

## Tier 3: Economic Intelligence (Macro Context for AI Modeling)

**What:** The same macroeconomic data that appears in the "Economic Intelligence Panel" of reports and the pre-generation economic preview.

**Why it's valuable:**
- Feeds **AI report generation** — the AI cites real economic indicators
- Enables **AI modeling** — time-series data for economic forecasting models
- Gives **new businesses** context on whether to enter a market now or wait

**Datasets:**

### 3.1 — Economic Snapshot by Date
| Field | Source | Example |
|-------|--------|---------|
| snapshot_date | Date of collection | `2026-06-15` |
| fed_funds_rate | FRED | `5.25%` |
| inflation_rate | FRED/BLS | `3.2%` |
| unemployment | BLS | `3.8%` |
| gdp_growth | FRED | `2.4%` |
| consumer_sentiment | FRED | `72.3` |
| mortgage_rate | FRED | `6.8%` |
| data_source_label | `FRED + BLS` | `FRED + BLS` |

**Provenance:** `FREDService.get_macro_context()` — from FRED API + BLS API
**Refresh:** Daily (nightly cron job)
**Price:** $49/month (all dates) or $199 for 12-month historical
**Powers:** Economic Intelligence Panel, report generation, AI context injection

### 3.2 — Industry Benchmarks by Vertical
| Field | Source | Example |
|-------|--------|---------|
| vertical | `coffee_shop` | `coffee_shop` |
| naics_code | BLS | `722515` |
| avg_revenue | BLS QCEW | `$420,000` |
| avg_payroll | BLS QCEW | `$180,000` |
| employment_count | BLS | `12,400` |
| employment_trend | % YoY | `+2.1%` |
| wage_trend | % YoY | `+3.4%` |
| growth_rate | % YoY | `+4.2%` |
| top_performing_states | SEC-API + BLS | `["TX", "FL", "NC"]` |
| data_source_label | `BLS QCEW + SEC-API` | `BLS QCEW + SEC-API` |

**Provenance:** `ReportDataService` + BLS QCEW + SEC-API
**Refresh:** Quarterly
**Price:** $199/vertical or $599/month unlimited
**Powers:** Industry analysis reports, financial model benchmarks, competitive benchmarking

---

## Tier 4: Traffic & Foot Traffic Data (Physical Location Intelligence)

**What:** Drive-by traffic (AADT) and foot traffic data for physical location analysis.

**Why it's valuable:**
- Critical for **retail, restaurant, and service businesses**
- Feeds the **Location DeepDive** and **Identify Location** tools
- Enables **zone analysis** and **optimal location scoring**

**Datasets:**

### 4.1 — Drive-By Traffic by Road Segment
| Field | Source | Example |
|-------|--------|---------|
| road_id | DOT + platform | `rd-ih35-austin-001` |
| road_name | DOT | `IH-35` |
| city | `Austin` | `Austin` |
| state | `TX` | `TX` |
| aadt | Annual Average Daily Traffic | `145,000` |
| trend_direction | `increasing`, `stable`, `decreasing` | `increasing` |
| growth_rate | % YoY | `+2.3%` |
| peak_hours | `morning`, `midday`, `evening` | `morning, evening` |
| data_source_label | `State DOT + Google Traffic` | `State DOT` |

**Provenance:** State DOT APIs + Google Traffic API
**Refresh:** Monthly (DOT data) + real-time (Google)
**Price:** $99/city or $399/month unlimited
**Powers:** Traffic layer on map, location analysis, drive-by visibility scoring

### 4.2 — Foot Traffic Heatmap Points
| Field | Source | Example |
|-------|--------|---------|
| location_id | Platform | `loc-downtown-austin-001` |
| lat | Geocoded | `30.2672` |
| lng | Geocoded | `-97.7431` |
| foot_traffic_score | 0-100 | `78` |
| peak_days | JSON | `["Friday", "Saturday"]` |
| peak_hours | JSON | `["12:00-14:00", "18:00-21:00"]` |
| dwell_time_minutes | Avg | `45` |
| visitor_demographics | JSON | `{age: "25-34", income: "70k-100k"}` |
| data_source_label | `Placer.ai / SafeGraph / Municipal` | `Municipal` |

**Provenance:** Municipal data + third-party foot traffic providers (if licensed)
**Refresh:** Weekly
**Price:** $149/city or $499/month unlimited
**Powers:** Foot traffic layer, zone analysis, optimal location finder

---

## Data Provenance & Quality Guarantees

Every dataset row must include:
- `data_source_label` — human-readable origin (e.g., `RedditScraper`, `Census ACS 2024`, `BLS QCEW Q1 2026`)
- `collected_at` — exact timestamp
- `refresh_cadence` — `daily`, `weekly`, `monthly`, `quarterly`
- `data_quality_score` — 0-100 computed from freshness + source reliability + AI confidence

**Quality tiers:**
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

1. **Validate the catalog** — Which datasets above exist in the DB already? Which need new pipelines?
2. **Check scraper status** — Are the SerpAPI, Reddit, Craigslist, Google Trends scrapers still running and populating tables?
3. **Add provenance fields** — Add `data_source_label`, `collected_at`, `data_quality_score` to all data hub models
4. **Create dataset definitions** — Create `Dataset` records in the DB that map to these schemas
5. **Test CSV generation** — Verify each dataset type generates real CSVs from real DB data
6. **Re-enable marketplace** — Remove the 503 once we have > 100 real rows per table

**Which tier do you want to start with?** I recommend validating Tier 1 first (Opportunity Signal Data) since it's the platform's core value proposition.
