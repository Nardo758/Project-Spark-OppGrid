# Current Report Implementation Summary — OppGrid

## Data Pipeline (What We Currently Have)

### Data Sources
1. **U.S. Census Bureau ACS 5-Year Estimates** — demographics, income, population, households
2. **Google Maps Places API** — competitor scan within 5-mile radius
3. **OppGrid Signal Database** — aggregated consumer demand signals, amenity demand
4. **Google Trends** — search interest index
5. **Zillow Research** — real estate market data (home values, rents)
6. **FRED (Federal Reserve Bank of St. Louis)** — macroeconomic indicators (Fed funds rate, inflation, unemployment, GDP growth, consumer sentiment, mortgage rates)
7. **BLS QCEW / OES** — industry labor data (employment, wages, establishments) by NAICS code
8. **SEC 10-K filings via sec-api.io** — public company financial benchmarks (operating margins, revenue growth)

### Proprietary Formulas (8 scores)
1. **Traffic Anomaly Index (TAI)** — traffic pattern deviation from baseline
2. **Wealth Migration Momentum (WMM)** — net migration of high-income households
3. **Demand Velocity Score (DVS)** — rate of change in consumer demand signals
4. **Competitive Whitespace Index (CWI)** — low-competition opportunity zones
5. **Business Formation Velocity (BFV)** — rate of new business registrations
6. **Affordability Trend Index (ATI)** — housing affordability trajectory
7. **First-Mover Window (FMW)** — estimated days before market saturation
8. **Demographic Shift Index (DSI)** — population composition change velocity

**Composite Location Score (CLS)** — weighted combination of all 8, normalized 0-100.

### Tier Differentiation
- **Tier 1 ($25):** Feasibility Study — basic competitor count + 3 core formulas (DVS, CWI, BFV)
- **Tier 2 ($79-$99):** Pitch Deck, Strategic Assessment, PESTLE, Market Analysis, Location Analysis — full competitor table + all 8 formulas + signal evidence
- **Tier 3 ($129-$149):** Financial Model, Business Plan — everything + FRED macro + BLS labor + SEC 10-K benchmarks

## Per-Report Current Implementation

### 1. Feasibility Study (`generate_feasibility_study`)
**Generator:** `ReportGenerator.generate_feasibility_study()` (layer_0.py)
**Current data fed:** None — pure template with no data injection
**Template structure:** 5 sections — Executive Summary, Market Overview, Financial Projections, Risk Analysis, Recommendations
**Claude prompt:** General prompt asking for feasibility analysis with no specific data context
**Gap:** No real data is passed to the generator. The tier-1 SecretSauce block is built but not explicitly injected into this generator's prompt.

### 2. Business Plan (`generate_business_plan`)
**Generator:** `ReportGenerator.generate_business_plan()` (layer_0.py)
**Current data fed:** Full SecretSauce block (Tier 3) + economic intelligence + static maps
**Template structure:** 10 sections — Executive Summary, Business Description, Market Analysis, Competitive Analysis, Marketing Strategy, Operations Plan, Management Team, Financial Projections, Risk Analysis, Appendices
**Claude prompt:** Receives full intelligence context block + FRED + BLS + SEC data
**Map injection:** Static Google Maps embedded for business location + 5-mile competitor radius
**Status:** Most data-rich report. All economic intelligence is injected.

### 3. Financial Model (`generate_financial_projections`)
**Generator:** `ReportGenerator.generate_financial_projections()` (layer_0.py)
**Current data fed:** Full SecretSauce block (Tier 3) + BLS labor data + SEC 10-K benchmarks
**Template structure:** 5 sections — Revenue Model, Cost Structure, Unit Economics, 5-Year Projections, Sensitivity Analysis
**Claude prompt:** Receives financial context including BLS wage data and SEC operating margins
**Status:** Has real labor cost data and public-comp benchmarks. Good data foundation.

### 4. Market Analysis (`generate_market_analysis_report`)
**Generator:** `ReportGenerator.generate_market_analysis_report()` (layer_0.py)
**Current data fed:** Full SecretSauce block (Tier 2) + demographics + competitor data + signal evidence
**Template structure:** 4 sections — Market Size (TAM/SAM/SOM), Competitive Landscape, Consumer Trends, Growth Opportunities
**Claude prompt:** Receives competitor table + demographics + formula scores + signal evidence
**Status:** Has real competitor data and demand signals. Missing formal TAM/SAM/SOM calculation methodology.

### 5. Strategic Assessment (`generate_strategic_assessment`)
**Generator:** `ReportGenerator.generate_strategic_assessment()` (layer_0.py)
**Current data fed:** Full SecretSauce block (Tier 2) + competitor data + formula scores
**Template structure:** 4 sections — SWOT Analysis, Competitive Positioning, Strategic Recommendations, Action Plan
**Claude prompt:** Receives competitor data + formula scores for strategic context
**Status:** Has competitive data but no formal strategic frameworks (Porter's Five Forces, Ansoff Matrix, etc.)

### 6. PESTLE Analysis (`generate_pestle_analysis`)
**Generator:** `ReportGenerator.generate_pestle_analysis()` (layer_0.py)
**Current data fed:** Full SecretSauce block (Tier 2) + demographics + macro context (if available)
**Template structure:** 6 sections — Political, Economic, Social, Technological, Legal, Environmental
**Claude prompt:** Receives demographic and economic context for each factor
**Status:** Has economic data but no structured PESTLE framework or specific regulatory data per industry.

### 7. Pitch Deck (`generate_pitch_deck_content`)
**Generator:** `ReportGenerator.generate_pitch_deck_content()` (layer_0.py)
**Current data fed:** Full SecretSauce block (Tier 2) + competitor data + formula scores + signal evidence
**Template structure:** 8 sections — Problem, Solution, Market Opportunity, Business Model, Traction, Competitive Advantage, Team, Ask
**Claude prompt:** Receives market data + competitive positioning for investor pitch
**Status:** Has market data but no formal investor deck structure (Sequoia/YC standards). Missing traction metrics and team slide guidance.

### 8. Location Analysis (`_generate_location_analysis`)
**Generator:** `ReportGenerator.generate_location_analysis()` (layer_0.py)
**Current data fed:** Full SecretSauce block (Tier 2) + demographics + formula scores + location data
**Template structure:** 4 sections — Location Overview, Demographic Profile, Competitive Landscape, Recommendation
**Claude prompt:** Explicitly instructed to "USE pre-calculated values" — no formula recomputation
**Status:** Uses pre-calculated formula scores. Good data foundation. Missing site-specific data (traffic counts, lease rates, zoning).

## Key Gaps Across All Reports

1. **No formal TAM/SAM/SOM methodology** — Market Analysis claims TAM/SAM/SOM but uses no structured calculation
2. **No industry-specific NAICS mapping** — BLS data fetched but not matched to specific business types
3. **No structured risk matrix** — Risk sections are generic, no probability/impact scoring
4. **No sensitivity analysis formulas** — Financial Model claims sensitivity but no structured scenario inputs
5. **No competitor financial data** — Only Google Maps ratings/reviews, no revenue/employee estimates
6. **No customer acquisition cost (CAC) data** — No marketing channel cost data
7. **No regulatory/permit data** — Location Analysis and PESTLE lack industry-specific regulations
8. **No supply chain data** — Missing for physical businesses
9. **No local tax incentive data** — Missing for location decisions
10. **No lease comparables** — Missing for Location Analysis

## Proprietary Data We Can Add

1. **OppGrid Opportunity Score** — Composite of formula scores + signal strength + data quality
2. **Market Heat Index** — Real-time signal velocity from our database
3. **Competitor Vulnerability Score** — Derived from competitor ratings, review sentiment, age of business
4. **First-Mover Urgency Rating** — Time-decay based on FMW + BFV trends
5. **Location Rankings** — Multi-factor scored location list (already have for Location Analysis)
6. **Demand Gap Map** — Unmet demand by geography + category (from signal database)
7. **Expert Network Insights** — Aggregated expert opinions on market viability
8. **Success Probability Model** — ML model trained on historical outcomes + formula scores
