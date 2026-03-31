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

## Recent Fixes
*   **Web Enrichment Async Fix:** `enrich_with_web_data_sync` in `web_enrichment_service.py` was crashing with "this event loop is already running" when called from FastAPI's async context. Fixed by creating a fresh `WebEnrichmentService` instance in a separate thread via `ThreadPoolExecutor` + `asyncio.run()`, avoiding shared `AsyncClient` across event loops.
*   **Consultant Studio Report Save UX:** Replaced auth-prompt logic (unnecessary since page requires login) with proper error/success feedback banners. The "Save as Report" button now shows "Generating..." while pending and displays clear error messages or a success confirmation.
*   **Deployment PostGIS Fix:** Added `drizzle.config.ts` with `tablesFilter` to exclude PostGIS system tables from Replit's internal schema sync. Removed GeoAlchemy2 from `traffic_road.py` model. Added DDL filter in `alembic/env.py` to block PostGIS system table modifications.