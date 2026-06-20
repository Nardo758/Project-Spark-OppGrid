# OppGrid Report Structure Deep Research — Synthesis & Roadmap

> **Research Date:** 2026-06-20
> **Sources:** 4 parallel research agents analyzing industry standards for all 8 report types against OppGrid's current implementation. 33+ academic and industry sources cited.
> **Research Directory:** `research/report_structures/`

---

## Executive Summary

**We did NOT previously deep-research industry-standard report structures.** Our prior audit mapped what each report *currently* generates, but not what it *should* contain. This research closes that gap.

**Bottom line:** Our reports have strong raw data inputs (Census, BLS, FRED, SEC, Google Maps, Signal Database, 8 proprietary formulas) but **weak structural frameworks**. Industry standards expect specific methodologies, scored matrices, and auditable calculations that our current templates do not provide. The gap is bridgeable — our data pipeline is richer than most competitors, but we need to add structured frameworks on top of it.

---

## Cross-Cutting Critical Gaps (🔴)

These gaps appear in **3+ reports** and are the highest-priority fixes:

| Gap | Affected Reports | Severity | Why It Matters |
|-----|-----------------|----------|----------------|
| **No formal TAM/SAM/SOM methodology** | Market Analysis, Pitch Deck, Business Plan | 🔴 Critical | Investors/lenders reject market-sizing claims without top-down + bottom-up validation |
| **No DSCR calculation** | Feasibility Study, Financial Model, Business Plan | 🔴 Critical | SBA SOP 50 10 8 requires DSCR ≥ 1.25x; missing this blocks SBA lending use case |
| **No structured 3-statement model** | Financial Model, Business Plan | 🔴 Critical | Professional financial models require integrated Income Statement, Balance Sheet, Cash Flow |
| **No competitor financial estimation** | Market Analysis, Strategic Assessment, Location Analysis | 🔴 Critical | Ratings-only analysis is superficial; revenue/employee estimates are expected |
| **No regulatory/permit data** | PESTLE, Location Analysis, Feasibility Study | 🔴 Critical | Physical businesses cannot operate without zoning, permits, licenses |
| **No sensitivity analysis with structured inputs** | Financial Model, Business Plan, Feasibility Study | 🔴 Critical | Lenders/investors require scenario planning (base/bull/bear) with explicit assumptions |
| **No risk assessment matrix (probability × impact)** | Feasibility Study, Strategic Assessment, Business Plan | 🔴 Critical | Generic risk lists are rejected; scored matrices are the standard |
| **No lease comparables** | Location Analysis, Feasibility Study | 🔴 Critical | Site selection without lease cost data is incomplete |
| **No daytime population / traffic counts** | Location Analysis | 🔴 Critical | LODES and AADT data are free and essential for physical businesses |
| **No structured Porter's Five Forces / Ansoff Matrix** | Strategic Assessment, Market Analysis | 🔴 Critical | Consulting-grade strategic assessments require formal frameworks |

---

## Per-Report Status: Current vs. Standard

### 1. Feasibility Study ($25 — Tier 1)
**Current:** Template-only with zero data injection. 5 generic sections.
**Standard:** TELOS + Management framework (6 pillars): Market, Technical, Financial, Operational, Legal/Regulatory, Management feasibility. SBA requires DSCR ≥ 1.15x, break-even analysis, sensitivity analysis, risk matrix.
**Verdict:** ❌ **Would not pass SBA scrutiny.** Our cheapest report is also our weakest — it uses no data despite having the SecretSauce block built.

### 2. Business Plan ($149 — Tier 3)
**Current:** 10 sections with full economic intelligence (FRED, BLS, SEC). Good data foundation.
**Standard:** SBA 12-section standard (SOP 50 10 8). Requires 3-statement model, DSCR, funding request, equity injection, customer concentration analysis, risk matrix, branching by stage (startup vs. acquisition vs. expansion).
**Verdict:** ⚠️ **Data-rich but framework-poor.** Has the most data but missing lender-critical sections (DSCR, funding request, stage branching). Could become our strongest report with framework additions.

### 3. Financial Model ($129 — Tier 3)
**Current:** 5 sections (Revenue, Cost, Unit Economics, 5-Year Projections, Sensitivity). BLS labor + SEC margins injected.
**Standard:** 3-statement integrated model (IS + BS + CFS), assumptions tab, SaaS metrics (MRR/ARR/LTV/CAC) or physical business cost structure (COGS, inventory, occupancy), DCF valuation, cap table, sensitivity scenarios.
**Verdict:** ⚠️ **Missing the core model structure.** Has data but not the financial architecture. Needs explicit Balance Sheet, Cash Flow Statement, and supporting schedules.

### 4. Market Analysis ($99 — Tier 2)
**Current:** 4 sections with competitor data, demographics, formula scores, signal evidence.
**Standard:** 10 sections including dual-methodology TAM/SAM/SOM, Porter's Five Forces, strategic group mapping, barrier-to-entry assessment, consumer psychographics, channel analysis, data methodology transparency.
**Verdict:** ⚠️ **Strong inputs, weak methodology.** Competitor table is good but lacks Porter's Five Forces and revenue estimation. TAM/SAM/SOM claim is unverifiable.

### 5. Strategic Assessment ($89 — Tier 2)
**Current:** 4 sections (SWOT, Competitive Positioning, Strategic Recommendations, Action Plan). Formula scores + competitor data.
**Standard:** 5-phase consulting methodology (Discovery → Strategy → Validation → Execution → Monitoring). Requires Porter's Five Forces, Ansoff Matrix, TOWS Matrix, Blue Ocean/Value Disciplines, competitive benchmarking table, scenario planning, KPI monitoring.
**Verdict:** ❌ **Missing all formal frameworks.** SWOT is a list, not a strategy engine. No quantified scoring, no action mapping.

### 6. PESTLE Analysis ($99 — Tier 2)
**Current:** 6 sections with demographic and economic context per factor.
**Standard:** Structured indicators per factor (8–12 each), quantitative scoring (1–5), industry-specific weighting, cross-impact analysis, scenario planning, time-horizon differentiation.
**Verdict:** ⚠️ **Template-based with no indicator mapping.** Each factor is narrative, not scored. Missing regulatory data integration.

### 7. Pitch Deck ($79 — Tier 2)
**Current:** 8 sections (Problem, Solution, Market, Business Model, Traction, Competitive Advantage, Team, Ask). Market data + formula scores.
**Standard:** Sequoia/YC 10–12 slide structure. Requires "Why Now?", Company Purpose, Product detail, Appendix, formal TAM/SAM/SOM, unit economics (CAC/LTV/payback), stage-specific traction metrics, 30-point font discipline.
**Verdict:** ⚠️ **Missing key slides and unit economics.** No "Why Now?" breaks narrative arc. No CAC/LTV data despite being the #1 investor metric.

### 8. Location Analysis ($119 — Tier 2)
**Current:** 4 sections with pre-calculated formula scores, demographics, competition. "USE pre-calculated values" instruction prevents hallucination.
**Standard:** 10-layer site selection methodology (market demand, trade area, competition, demographics, site characteristics, traffic, economic cost, zoning, supply chain, incentives). Requires daytime population, AADT traffic counts, lease comparables, Huff Gravity Model market share, zoning analysis, tax incentives.
**Verdict:** ⚠️ **Best data foundation among Tier 2 but missing critical site-specific data.** Pre-calculated scores are a strength. Missing traffic, zoning, lease, and incentive data.

---

## Data Pipeline: What We Have vs. What We Need

### ✅ Already Connected (Strong Foundation)
| Data Source | Reports Using It | Quality |
|-------------|-----------------|---------|
| U.S. Census ACS | All 8 | ✅ Real, cited |
| Google Maps Places API | Market, Strategic, Location, Feasibility | ✅ Real competitor data |
| OppGrid Signal Database | Market, Location, Pitch | ✅ Proprietary demand signals |
| Google Trends | Market, Location | ✅ Real search interest |
| Zillow Research | Location, Financial, Business Plan | ✅ Real estate data |
| FRED (macro) | Business Plan, Financial, PESTLE | ✅ Federal Reserve data |
| BLS QCEW/OES | Financial, Business Plan | ✅ Labor data by NAICS |
| SEC 10-K | Financial, Business Plan | ✅ Public-comp benchmarks |
| 8 Proprietary Formulas | All 8 (tiered) | ✅ Unique to OppGrid |

### ❌ Missing (Critical for Industry Standard Compliance)
| Data Source | Needed For | Cost | Priority |
|-------------|-----------|------|----------|
| IBISWorld / RMA industry benchmarks | Market Analysis, Financial Model, Business Plan | Paid ($$$) | 🔴 High |
| CoStar / LoopNet lease comparables | Location Analysis, Feasibility Study | Paid ($$$) | 🔴 High |
| State DOT AADT traffic data | Location Analysis | Free | 🔴 High |
| Census LEHD/LODES daytime population | Location Analysis | Free | 🔴 High |
| FEMA flood maps / EPA brownfields | Location Analysis | Free | 🟡 Medium |
| Municipal zoning / permit APIs | Location Analysis, PESTLE | Mixed | 🟡 Medium |
| State tax incentive databases | Location Analysis, PESTLE | Free | 🟡 Medium |
| USPTO patent data | PESTLE (Technological) | Free | 🟡 Medium |
| Federal Register / regulatory data | PESTLE (Legal) | Free | 🟡 Medium |
| Walk Score / transit APIs | Location Analysis | Freemium | 🟡 Medium |
| ESRI Tapestry / Nielsen PRIZM | Location Analysis | Paid ($$) | 🟢 Low |

---

## Top 10 Proprietary Data Differentiators

OppGrid can leapfrog generic AI report generators by leveraging our **unique data assets** (8 formulas + signal database + competitive intelligence) to produce outputs no template can replicate.

| # | Differentiator | Description | Reports |
|---|---------------|-------------|---------|
| 1 | **OppGrid Opportunity Score** | Composite of all 8 formula scores + signal strength + data quality. A single headline metric that summarizes market viability. | All 8 |
| 2 | **Signal-Driven TAM/SAM** | Use actual consumer demand signals from our database to estimate Serviceable Obtainable Market, not generic percentages. | Market, Pitch, Business Plan |
| 3 | **Competitor Vulnerability Score** | Combine ratings, review sentiment, review velocity, and business age to quantify how "weak" the incumbent field is. | Market, Strategic, Location, Pitch |
| 4 | **First-Mover Urgency Rating** | Convert FMW + BFV trends into a countdown-based urgency metric. | Market, Strategic, Pitch, Location |
| 5 | **Demand Gap Map** | Unmet demand by geography + category from signal database. A visual "white space" map. | Market, Strategic, Location |
| 6 | **OppGrid DSCR Predictor** | Pre-calculate projected DSCR using OppGrid-derived revenue and cost assumptions. Tell users their lender-readiness before they apply. | Financial, Business Plan, Feasibility |
| 7 | **Location-Adjusted Revenue Benchmark** | Use CLS + CWI + DVS to estimate revenue potential for a specific address, not just generic industry averages. | Financial, Location, Business Plan |
| 8 | **Success Probability Model (ML)** | Train ML on historical outcomes + formula scores. A risk-adjusted probability of business success per location/category. | Feasibility, Strategic, Pitch |
| 9 | **Market Heat Index** | Real-time signal velocity showing demand acceleration/deceleration. A dynamic, time-series market view. | Market, Pitch, Strategic |
| 10 | **SBA Pre-Qualification Score** | Composite of DSCR predictor, equity injection feasibility, and OppGrid data quality to estimate SBA approval likelihood. | Business Plan, Feasibility |

---

## Implementation Roadmap

### Phase 1: Quick Wins (Week 1–2) — Close Critical Data Gaps
1. **Inject Tier 1 SecretSauce into Feasibility Study** — The block is built but not passed. Zero-effort data upgrade.
2. **Add free government data sources** — LEHD/LODES (daytime population), state DOT AADT (traffic), FEMA flood maps, EPA brownfields.
3. **Add structured indicator checklists to PESTLE** — 8–12 indicators per factor, industry-specific.
4. **Add DSCR calculation module** to Financial Model and Business Plan.
5. **Add TAM/SAM/SOM calculation module** to Market Analysis — top-down from Census/BLS + bottom-up from unit economics.

### Phase 2: Framework Build-Out (Week 3–6) — Add Industry Standards
6. **Add 3-statement model structure** to Financial Model (IS + BS + CFS + supporting schedules).
7. **Add Porter's Five Forces** to Strategic Assessment and Market Analysis.
8. **Add Ansoff Matrix + TOWS Matrix** to Strategic Assessment.
9. **Add "Why Now?" slide + unit economics** to Pitch Deck.
10. **Add Funding Request section** to Business Plan.
11. **Add scenario planning** (Conservative/Base/Optimistic) to Financial Model and Business Plan.
12. **Add risk assessment matrix** (probability × impact) to all reports with Risk Analysis sections.

### Phase 3: Proprietary Differentiation (Week 7–10) — Build Moats
13. **Launch OppGrid Opportunity Score** as headline metric on all reports.
14. **Build Competitor Vulnerability Score** from review sentiment + velocity + age.
15. **Build Demand Gap Map** visualization from signal database.
16. **Build OppGrid DSCR Predictor** for lender-readiness scoring.
17. **Add SBA Pre-Qualification Score** to Business Plan and Feasibility Study.
18. **Add stage branching** (startup vs. acquisition vs. expansion) to Business Plan.

### Phase 4: Premium Data (Month 3+) — Licensed Integrations
19. **Integrate IBISWorld or RMA** for industry revenue benchmarks and TAM/SAM top-down validation.
20. **Integrate CoStar/LoopNet** for commercial lease comparables.
21. **Build Success Probability Model (ML)** trained on historical outcomes + formula scores.
22. **Create real-time PESTLE dashboard** — continuously updated as new data flows in.

---

## Research Files Produced

| File | Content | Lines |
|------|---------|-------|
| `current_implementation_summary.md` | Audit of current pipeline, 8 report generators, data sources, gaps | 180 |
| `feasibility_market_research.md` | Feasibility Study (TELOS framework) + Market Analysis (TAM/SAM/SOM, Porter's) standards | 268 |
| `pitch_strategic_research.md` | Pitch Deck (Sequoia/YC/a16z) + Strategic Assessment (McKinsey/BCG frameworks) standards | 408 |
| `pestle_location_research.md` | PESTLE (indicator lists, scoring) + Location Analysis (10-layer site selection) standards | 484 |
| `financial_businessplan_research.md` | Financial Model (3-statement, DCF, SaaS) + Business Plan (SBA SOP 50 10 8) standards | 473 |
| **`synthesis_roadmap.md`** (this file) | Cross-verification, gap matrix, proprietary opportunities, implementation roadmap | — |

---

## Sources

All cited sources are preserved in their respective research files with [^id] footnotes. Key authoritative sources include:
- SBA SOP 50 10 8 (Effective June 1, 2025)
- SCORE / LivePlan / BPlans business plan templates
- Sequoia Capital / Y Combinator / Andreessen Horowitz pitch deck standards
- McKinsey / BCG / Bain strategic assessment frameworks
- Wall Street Prep / CFI / Breaking Into Wall Street financial modeling standards
- CoStar / REIS / ESRI site selection methodology
- IBISWorld / Euromonitor market analysis standards
- Academic literature on PESTLE, SWOT, Porter's Five Forces (30+ peer-reviewed sources)
