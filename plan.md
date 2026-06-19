# Consultant Studio — Plan

## Audit Findings

### What Exists ✅
- **Backend service**: `consultant_studio.py` (3,583 lines) — Three-path validation (Validate Idea, Search Ideas, Identify Location)
- **Report pricing**: `core/report_pricing.py` — 8 report products + 4 bundles
- **Report templates**: `data/report_templates_seed.py` — 30+ templates across 6 categories
- **Report API**: `routers/report_pricing.py` (2,288 lines), `routers/reports.py` (917 lines)
- **React component**: `ReportSelectionPanel.tsx` — fetches from `/api/v1/report-pricing/public`
- **Report generation**: AI-powered with Claude integration
- **Stripe checkout**: Wired for report purchases
- **ConsultantMap**: Location analysis map component exists

### What's Broken ❌
- **Missing page**: `frontend/src/pages/build/ConsultantStudio.tsx` — FILE DOES NOT EXIST
- **Broken route**: `/build/consultant-studio` → 404 error
- **No integration**: The three-path validation UI is not wired to the backend service

### Report Catalog (8 Products)
| Type | Name | Price | Tier |
|---|---|---|---|
| feasibility_study | Feasibility Study | $25 | — |
| business_plan | Business Plan | $149 | pro |
| financial_model | Financial Model | $129 | pro |
| market_analysis | Market Analysis | $99 | business |
| strategic_assessment | Strategic Assessment | $89 | pro |
| pestle_analysis | PESTLE Analysis | $99 | business |
| pitch_deck | Pitch Deck | $79 | pro |
| location_analysis | Location Analysis | $119 | — |

### Bundles (4)
| Type | Name | Price | Reports |
|---|---|---|---|
| starter | Starter Bundle | $329 | 4 reports |
| strategic | Strategic Bundle | $229 | 3 reports |
| professional | Professional Bundle | $549 | 7 reports |
| consultant_license | Consultant License | $2,499 | unlimited/yr |

## Build Plan

### Stage 1: Create ConsultantStudio.tsx page
- Three-tab layout: Validate Idea | Search Ideas | Identify Location
- Each tab connects to the backend `ConsultantStudioService`
- Report selection panel integrated into results
- Responsive design matching existing app style

### Stage 2: Wire routes
- Fix `/build/consultant-studio` route in App.tsx
- Ensure navigation from OpportunityDetail, Dashboard, etc.

### Stage 3: Test end-to-end
- Validate Idea flow → AI analysis → report selection
- Search Ideas flow → trend discovery → report selection
- Identify Location flow → location analysis → ConsultantMap

## Next Steps After Consultant Studio
1. Set up cron-job.org for scheduler
2. Onboard real experts (verification workflow)
3. Stripe Connect for expert payouts
4. Re-seed datasets with stricter thresholds
