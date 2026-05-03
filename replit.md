# OppGrid - Opportunity Intelligence Platform

## Overview
OppGrid is an AI-powered opportunity intelligence platform designed to discover, validate, and act on business opportunities. It aims to be an "AI Startup Factory" by providing AI-driven analysis, an expert marketplace, subscription-based content, and pay-per-unlock features. The platform's vision is to democratize access to high-quality business intelligence and foster innovation.

## User Preferences
I want iterative development, with a focus on delivering core features quickly and refining them based on feedback. Prioritize modular and reusable code. I prefer clear, concise explanations and direct answers. Ask before making major architectural changes or introducing new external dependencies. Do not make changes to the `replit.nix` file.

## System Architecture
OppGrid utilizes a modern hybrid architecture with a React 18 frontend (Vite, TailwindCSS) on Port 5000 and a Python FastAPI backend (SQLAlchemy ORM) on Port 8000, backed by a Replit PostgreSQL database. Client-side state is managed with Zustand, and routing with React Router v6. The frontend proxies `/api/*` requests to the backend.

**Key Architectural Decisions & Features:**
*   **Monetization & Access Control:** Implements a 3-gate revenue model with multi-tier subscriptions, opportunity slot credits, and pay-per-report features, including white-label and commercial use rights.
*   **Team & Access Management:** Supports team creation, role-based access control, invitation systems, and API access.
*   **AI Engine & Analysis:** Integrates with LLMs for idea generation, validation, expert matching, and detailed opportunity analysis, featuring an 8-stage "Signal-to-Opportunity" algorithm and automated data pipeline.
*   **Opportunity Reporting:** Provides 20 AI-generated report templates accessible via a Report Library and Consultant Studio.
*   **Authentication & Security:** Uses Replit's OIDC patterns with database-backed user authentication, including LinkedIn OAuth, password reset, and TOTP-based 2FA.
*   **User Interface & Experience:** Features a professional dark-themed design with a deep dive console, dynamic navigation, and interactive mapping.
*   **Content Moderation:** Implements a quality control workflow requiring admin approval for public visibility of opportunities.
*   **Unified Opportunity Hub & WorkHub (AI Co-Founder):** For paid users, combines research and workspace with a visual journey timeline and a chat-first conversational AI assistant with a 4-stage workflow (Validate/Research/Plan/Execute). Supports "Bring Your Own Key" (BYOK) for Anthropic Claude API keys.
*   **Expert Marketplace & Collaboration:** Features a Leads Marketplace and Network Hub with an intelligent Expert Recommendation Engine, facilitating expert interactions with Stripe Connect for payouts and an expert dashboard.
*   **Data Management:** Ensures complete signal traceability, indefinite data retention, and database-backed caching for AI-driven idea validation.
*   **Location Validation:** Centralized `location_utils.py` module for state bounding box validation and automatic fallback for map accuracy.
*   **Industry-Specific Supply Analyzer:** Maps free-text business descriptions to 25+ specific industry categories via alias matching and dispatches to the right viability metric (e.g., `sqft_per_capita` for real estate, `providers_per_100k` for healthcare).
*   **Expanded Industry Benchmarks:** `report_data_service.py` includes `INDUSTRY_BENCHMARKS` for 25+ categories with primary metrics, national averages, thresholds, and aliases for fuzzy matching.
*   **Admin Panel:** Comprehensive tools for managing users, subscriptions, opportunities, leads, and platform statistics.
*   **Dual-Realm Workspace Architecture:** Supports both Physical (location-based, Mapbox) and Digital (online, Excalidraw) business opportunities. Includes an AI Provider Abstraction Layer for flexible LLM integration (Claude, OpenAI) and data services.
*   **Foot Traffic Analysis System:** Custom foot traffic analysis using SerpAPI Google Maps Popular Times data. Calculates area vitality scores (0-100) based on business density, foot traffic, diversity, and activity. Uses PostGIS geographic queries.
*   **DOT Traffic Data System:** Local PostgreSQL storage of state DOT AADT (Annual Average Daily Traffic) road data with PostGIS geometry support. Enables CAGR trend analysis and traffic visualization. Spatial queries use raw SQL with PostGIS functions.
*   **Mapbox Live Traffic Integration:** Provides real-time traffic congestion data via Mapbox Traffic v1 tilequery API as a leading indicator for emerging growth/decline patterns, comparing live congestion against expected baselines.
*   **Custom Polygon Drawing & Analysis:** Allows users to draw custom polygon shapes on the map for analysis. Returns DOT traffic data via PostGIS ST_Intersects, estimated demographics, and area scoring.

## External Dependencies
*   **PostgreSQL:** Managed database provided by Replit.
*   **Stripe:** Payment gateway for subscriptions, pay-per-unlock, and expert service transactions (including Stripe Connect).
*   **Resend:** Email service for transactional emails.
*   **Apify:** Web scraping platform.
*   **SerpAPI:** Google Search, Google Maps Reviews, and Google Maps Popular Times API.
*   **OpenAI/Anthropic (LLMs):** Integrated for various AI capabilities.
*   **LinkedIn OAuth:** For professional network authentication.
*   **Census Bureau ACS 5-Year API:** Provides demographic data.
*   **Mapbox:** Used for map visualizations.
*   **SBA (Small Business Administration):** Provides curated loan program data and financing course information.