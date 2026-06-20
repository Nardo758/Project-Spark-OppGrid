# Report Structure Deep Research Plan

## Goal
Research industry-standard structures, data requirements, and best practices for all 8 report types. Map against our current data pipeline. Identify proprietary data gaps.

## Stage 1 — Research (deep-research-swarm, Route B: Focused Search)
Load `deep-research-swarm` skill. Deploy parallel research agents per report type.

Dimensions:
1. **Feasibility Study** — What sections, data points, frameworks do VCs/lenders expect? (SBA, SCORE, IBISWorld standards)
2. **Pitch Deck** — Sequoia/YC/Benchmark template standards. What data slides are mandatory?
3. **Strategic Assessment** — McKinsey/BCG/Bain frameworks. SWOT, Porter's Five Forces, Ansoff Matrix requirements.
4. **PESTLE Analysis** — Macro-environment scanning standards. Which indicators per factor? Data sources.
5. **Market Analysis** — TAM/SAM/SOM calculation standards. Competitive landscape mapping. Industry report structure (IBISWorld, Euromonitor, Forrester).
6. **Location Analysis** — Site selection methodology (CoStar, REIS, ESRI standards). Demographics, traffic, competition scoring.
7. **Financial Model** — 3-statement model standards. SaaS vs physical business unit economics. Cap table, DCF, sensitivity analysis.
8. **Business Plan** — SBA/SCORE/BPlan.com template. Executive summary, market analysis, operations, financials, appendices.
9. **Data Pipeline Audit** — What data sources do we currently have? What gaps exist for each report type?
10. **Proprietary Data Opportunities** — What unique data can OppGrid generate? Formula scores, signal database, competitor intelligence, opportunity ranking.

## Stage 2 — Synthesis
Cross-verify findings across all 8 reports. Identify:
- Common sections that appear in multiple reports (avoid duplication)
- Data dependencies (which data feeds which sections)
- Pipeline gaps (data we need but don't have)
- Proprietary differentiators (data only we can provide)

## Stage 3 — Integration
Produce final deliverable: `report_structures_research.md` with:
- Per-report: recommended sections, data requirements, sources, proprietary additions
- Pipeline gap matrix: what data is missing and how to get it
- Proprietary data roadmap: what unique data to build next

## Output
All files under `research/report_structures/` directory.
