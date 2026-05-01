# OppGrid - Opportunity Intelligence Platform

## Overview
OppGrid is an AI-powered opportunity intelligence platform designed to help users discover, validate, and act on business opportunities. It provides a structured approach from identifying market frictions to connecting users with experts and resources. The platform aims to be an "AI Startup Factory," offering AI-driven analysis, expert marketplaces, subscription-based content gating, and pay-per-unlock features to foster innovation and entrepreneurial success, with a vision to democratize access to high-quality business intelligence.

## User Preferences
I want iterative development, with a focus on delivering core features quickly and refining them based on feedback. Prioritize modular and reusable code. I prefer clear, concise explanations and direct answers. Ask before making major architectural changes or introducing new external dependencies. Do not make changes to the `replit.nix` file.

## System Architecture
OppGrid utilizes a modern hybrid architecture with a React 18 frontend (Vite, TailwindCSS) on Port 5000 and a Python FastAPI backend (SQLAlchemy ORM) on Port 8000, backed by a Replit PostgreSQL database. Client-side state is managed with Zustand, and routing with React Router v6. The frontend proxies `/api/*` requests to the backend.

**Key Architectural Decisions & Features:**
*   **Monetization & Access Control:** Implements a 3-gate revenue model with multi-tier subscriptions, opportunity slot credits, and pay-per-report features, including white-label and commercial use rights.
*   **Team & Access Management:** Supports team creation, role-based access control (owner/admin/member), invitation systems, and API access for business track subscribers.
*   **AI Engine & Analysis:** Integrates with LLMs for idea generation, validation, expert matching, and detailed opportunity analysis, featuring an 8-stage "Signal-to-Opportunity" algorithm and automated data pipeline.
*   **Opportunity Reporting:** Provides 20 AI-generated report templates accessible via a Report Library and Consultant Studio, including a "Clone Success" feature.
*   **Authentication & Security:** Uses Replit's OIDC patterns with database-backed user authentication, including LinkedIn OAuth, password reset, and TOTP-based 2FA.
*   **User Interface & Experience:** Features a professional dark-themed design with a deep dive console, dynamic navigation, and interactive mapping.
*   **Content Moderation:** Implements a quality control workflow requiring admin approval for public visibility of opportunities.
*   **Unified Opportunity Hub & WorkHub (AI Co-Founder):** For paid users, combines research and workspace with a visual journey timeline and a chat-first conversational AI assistant with a 4-stage workflow (Validate/Research/Plan/Execute). Supports "Bring Your Own Key" (BYOK) for Anthropic Claude API keys.
*   **Expert Marketplace & Collaboration:** Features a Leads Marketplace and Network Hub with an intelligent Expert Recommendation Engine, facilitating expert interactions with Stripe Connect for payouts and an expert dashboard.
*   **Data Management:** Ensures complete signal traceability, indefinite data retention, and database-backed caching for AI-driven idea validation.
*   **Location Validation:** Centralized `location_utils.py` module for state bounding box validation and automatic fallback for map accuracy.
*   **Industry-Specific Supply Analyzer:** `consultant_studio.py` — `_infer_benchmark_key()` maps free-text business descriptions to 25+ specific industry categories (self_storage, restaurant, gym, dental, etc.) via alias matching. `_analyze_supply()` dispatches to the right viability metric per industry: `sqft_per_capita` for real estate/storage (vs SSA 7.0 sq ft/capita benchmark), `providers_per_100k` for healthcare (HRSA/SAMHSA thresholds), and `competitors_per_capita` for all other categories. Returns `intel_supply` block with real metric value, vs-national comparison, data source, and supply verdict (Undersupplied/Balanced/Oversupplied). Designed to accept `municipal_sqft` from the bot's forthcoming Socrata municipal API client for real sq ft data.
*   **Expanded Industry Benchmarks:** `report_data_service.py` — `INDUSTRY_BENCHMARKS` dict now covers 25+ categories (self_storage, restaurant, cafe, bakery, brewery, bar, grocery, gym, yoga_studio, spa, salon, barbershop, dental, medical, mental_health, pharmacy, daycare, tutoring, car_wash, auto_repair, gas_station, laundromat, pet_grooming, coworking, hotel, consulting, real_estate, ecommerce, saas, retail). Each entry includes `primary_metric`, `national_average`, `undersupplied_threshold`, `oversupplied_threshold`, `unit`, `typical_density_per_capita`, and `aliases` for fuzzy matching.
*   **Admin Panel:** Comprehensive tools for managing users, subscriptions, opportunities, leads, and platform statistics.
*   **Dual-Realm Workspace Architecture:** Supports both Physical (location-based) and Digital (online) business opportunities, incorporating Mapbox for physical realms and Excalidraw for digital wireframing. This includes an AI Provider Abstraction Layer for flexible LLM integration (Claude, OpenAI) and data services for map commands, census data, SerpAPI, and Excalidraw storage.
*   **Foot Traffic Analysis System:** Custom foot traffic analysis using SerpAPI Google Maps Popular Times data. Calculates area vitality scores (0-100) based on business density (30pts), foot traffic levels (35pts), business diversity (20pts), and current activity (15pts). Features 7-day caching, PostGIS geographic queries, and opportunity-level traffic insights. Database tables: `foot_traffic`, `area_traffic_aggregations`, `opportunity_foot_traffic`.
*   **DOT Traffic Data System:** Local PostgreSQL storage of state DOT AADT (Annual Average Daily Traffic) road data with PostGIS geometry support. Florida data includes 103,436 road segments across 4 years (2021-2024) with traffic counts ranging 20-301,000 AADT. Uses spatial queries (ST_DWithin, ST_AsGeoJSON) for fast road segment retrieval. Multi-year historical data enables real CAGR (Compound Annual Growth Rate) trend analysis showing traffic growth/decline patterns. Traffic visualization colors roads green→yellow→red based on intensity. Import script supports `--source historical` and `--source current` for multi-year data. Database table: `traffic_roads`. Note: GeoAlchemy2 was removed from the TrafficRoad model (geometry column is `Text` in SQLAlchemy) to avoid PostGIS DDL errors during deployment. All spatial queries use raw SQL with PostGIS functions directly. A global DDL filter in `alembic/env.py` intercepts any ALTER/CREATE/DROP on PostGIS system tables. The deployment build step runs `alembic upgrade head` before the frontend build.
*   **Mapbox Live Traffic Integration:** Real-time traffic congestion data via Mapbox Traffic v1 tilequery API serves as a leading indicator for emerging growth/decline patterns. Compares live congestion levels (low/moderate/heavy/severe) against expected baseline derived from DOT AADT thresholds. Signal strength (strong/moderate/weak) indicates confidence level. Growth signals: live congestion exceeds baseline expectation. Decline signals: live congestion falls below baseline. Service: `mapbox_traffic_service.py`, `traffic_comparison_service.py`. API endpoint: `POST /api/v1/maps/live-traffic`.
*   **Custom Polygon Drawing & Analysis:** Users can draw custom polygon shapes on the map to define analysis areas. Uses @mapbox/mapbox-gl-draw for drawing controls. Polygon analysis returns real DOT traffic data via PostGIS ST_Intersects queries, estimated demographics (marked as estimates), and area scoring. Component: `LocationFinderMap.tsx`. API endpoint: `POST /api/v1/maps/analyze-polygon`.

## External Dependencies
*   **PostgreSQL:** Managed database provided by Replit.
*   **Stripe:** Payment gateway for subscriptions, pay-per-unlock, and expert service transactions (including Stripe Connect).
*   **Resend:** Email service for transactional emails.
*   **Apify:** Web scraping platform.
*   **SerpAPI:** Google Search, Google Maps Reviews, and Google Maps Popular Times API for foot traffic analysis.
*   **OpenAI/Anthropic (LLMs):** Integrated for various AI capabilities.
*   **LinkedIn OAuth:** For professional network authentication.
*   **Census Bureau ACS 5-Year API:** Provides demographic data.
*   **Mapbox:** Used for map visualizations.
*   **SBA (Small Business Administration):** Provides curated loan program data and financing course information.

## Required Replit Secrets
The following secrets must be configured in Replit → Secrets for full platform functionality:

| Secret Key | Purpose | Pipeline |
|---|---|---|
| `SERPAPI_KEY` | Google Maps + Search scraping via SerpAPI | Google opportunity pipeline (`google_scraping_service.py`) |
| `APIFY_API_TOKEN` | Triggers Reddit actor runs via Apify | Reddit signal pipeline (`apify_service.py`) |
| `APIFY_WEBHOOK_SECRET` | Verifies Apify completion webhooks | Reddit webhook handler (`webhooks.py`) |
| `BLS_API_KEY` | Bureau of Labor Statistics economic data | Economic intelligence appendix in reports |
| `FRED_API_KEY` | Federal Reserve economic data | Economic intelligence appendix in reports |
| `SEC_API_KEY` | SEC filings access | Market intelligence |
| `OPPGRID_AGENT_KEY` | Internal agent authentication | Clawdbot agent API |

**Google Opportunity Pipeline activation** (`SERPAPI_KEY`): Without this secret, all `GoogleScrapeJob` runs will fail with an authentication error. The key is read by `backend/app/services/serpapi_service.py` (env var name: `SERPAPI_KEY`). A startup log line confirms presence: `"SERPAPI_KEY is configured — Google opportunity pipeline is active"`. Default keyword groups (10 categories) and US metro locations (top 20 cities) are seeded automatically on first startup if the tables are empty (`backend/app/services/startup_seeder.py`).

**Reddit Signal Pipeline activation** (`APIFY_API_TOKEN` + `APIFY_WEBHOOK_SECRET`):
- Actor: `trudax/reddit-scraper-lite` (default, configured in `backend/app/services/apify_service.py`)
- Default subreddits: `entrepreneur`, `smallbusiness`, `startups`, `sidehustle`, `business`, `mildlyinfuriating`, `firstworldproblems`, `Showerthoughts`, `somebodymakethis`, `doesanybodyelse`
- Webhook URL to register in Apify: `https://<your-app>.replit.app/api/v1/webhook/apify`
- Configure this webhook on the `trudax/reddit-scraper-lite` actor in Apify Console → Webhooks, set the secret to the same value as `APIFY_WEBHOOK_SECRET`
- Trigger a run: admin `POST /api/v1/command-center/apify/reddit/run` (uses default config)
- Daily background job auto-triggers runs when `APIFY_API_TOKEN` is present (interval: `APIFY_IMPORT_JOB_INTERVAL_SECONDS`, default 24h)
- When Apify completes, it POSTs to the webhook → `receive_apify_webhook()` in `webhooks.py` fetches the dataset, stores items as `ScrapedSource` records, and triggers `OpportunityProcessor` in background
- Startup log confirms status: `"APIFY_API_TOKEN + APIFY_WEBHOOK_SECRET configured — Reddit pipeline active"`

## Report Studio (`/build/reports`)
Redesigned Report Studio page with:
- **4 input mode tabs**: Validate Idea, Search Ideas, Identify Location, Clone Success
- **Single CTA**: "Analyze & Generate Reports" coral button triggers `/api/v1/consultant/validate-idea` (or search/location/clone endpoints)
- **Analysis results**: ScoreRing (overall confidence), FourPsHorizontalBar (Product/Price/Place/Promotion), advantages/risks lists
- **Free reports**: "Just Generated" section with Idea Validation + Feasibility Study cards (auto-generated via `/api/v1/report-pricing/generate-free-report` for authenticated users; guests see sign-in prompt)
- **27 purchasable reports**: Compact accordion across 4 categories (Strategy & Analysis, Marketing & Growth, Product & Launch, Research) with expandable detail panels showing sections, delivery time, and pricing
- **Entitlement-aware purchase flow**: Checks `/api/v1/reports/check-access` first; if user has tier access, generates directly via `/api/v1/reports/generate`; otherwise redirects to Stripe checkout via `/api/v1/report-pricing/template-checkout`
- **Modal report viewer**: Supports JSON structured data, HTML content (dangerouslySetInnerHTML), and markdown section rendering with PDF/Word export
- **Guest vs authenticated UX**: Guests see sign-in prompt instead of Report History; free report generation skipped for guests with amber sign-in banner

Key files: `frontend/src/components/ReportLibrary.tsx`, `frontend/src/pages/build/ReportStudio.tsx`
Shared components from `ResultCards.tsx`: `ScoreRing`, `FourPsHorizontalBar`, `OppRow`

## Consultant Studio Results UI
The Consultant Studio (`frontend/src/pages/build/ConsultantStudio.tsx`) features an enhanced results UI with:
- **BlurGate paywall overlays** on premium content (feasibility studies, competitor deep dives, deep clone analysis) with Stripe checkout integration via `/api/v1/report-pricing/template-checkout`
- **ScoreCard components** showing online/physical viability scores and overall confidence with progress bars
- **FourPsBar mini-bar charts** (Product/Price/Place/Promotion) displayed inline on search opportunity rows
- **AI synthesis narratives** with left-border accent styling for search results and market intelligence
- **Trending-now gradient cards** for detected trends with strength/growth metrics
- **Market score gauges** and demographic panels for location analysis results
- **Site recommendation priority badges** (High/Medium) for location site recommendations
- **Stripe trust signals** (Secure payment, Money-back guarantee, Powered by Stripe) on all action bars
- **ResultMetricCard** reusable component for labeled metric display in result sections

## Recent Fixes
*   **Web Enrichment Async Fix:** `enrich_with_web_data_sync` in `web_enrichment_service.py` was crashing with "this event loop is already running" when called from FastAPI's async context. Fixed by creating a fresh `WebEnrichmentService` instance in a separate thread via `ThreadPoolExecutor` + `asyncio.run()`, avoiding shared `AsyncClient` across event loops.
*   **Consultant Studio Report Save UX:** Replaced auth-prompt logic (unnecessary since page requires login) with proper error/success feedback banners. The "Save as Report" button now shows "Generating..." while pending and displays clear error messages or a success confirmation.
*   **Deployment PostGIS Fix:** Added `drizzle.config.ts` with `tablesFilter` to exclude PostGIS system tables from Replit's internal schema sync. Removed GeoAlchemy2 from `traffic_road.py` model. Added DDL filter in `alembic/env.py` to block PostGIS system table modifications.
*   **Agent Routes → Data Hub Wiring:** Connected Clawdbot agent API endpoints (`/api/v1/agent/*`) to the Data Hub aggregation tables (`hub_opportunities_enriched`, `hub_markets_by_geography`, `hub_market_signals`, `hub_financial_snapshot`, etc.) via SQLAlchemy models in `backend/app/models/data_hub.py`. Endpoints auto-detect whether hub tables are populated and gracefully fall back to raw table queries if not. New hub-specific endpoints: `/hub/dashboard`, `/hub/markets`, `/hub/signals`, `/hub/financial`, `/hub/industries`, `/hub/validations`.
*   **Report Generation Pipeline Fix:** Fixed `Subscription.status` enum case mismatch (`"active"` → `"ACTIVE"`) in `reports.py` `get_user_tier()` that caused 500 errors on report generation. Expanded `tier_has_access()` tier ordering to include all tiers (free, starter, growth, team). Made unknown required_tier fail-closed (deny access). Increased AI call timeout from 30s to 90s. Fixed FastAPI route ordering: moved `reports.router` before `generated_reports.router` in `main.py` to prevent `/{report_id}` from intercepting `/templates`. Removed duplicate `GET /{report_id}` endpoint from `reports.router`.