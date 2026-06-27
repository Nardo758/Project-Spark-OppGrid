# Platform Assessment Plan

## Objective
Comprehensive audit of all OppGrid platform features to identify bugs, gaps, incomplete implementations, and improvement opportunities.

## Phase 1: Parallel Discovery (5 agents)
Each agent explores one domain of the platform and reports findings.

### Agent 1 — Frontend Explorer
Explore all frontend pages, routes, components. Identify:
- Broken routes / 404s
- Missing pages (linked but not implemented)
- UI/UX issues (layout breaks, missing mobile support)
- Components that don't render data correctly
- Console error patterns

### Agent 2 — Backend API Explorer
Audit all FastAPI routers, endpoints, and services:
- Endpoints that return 500 errors or incomplete data
- Missing CRUD operations
- Auth/permission gaps
- Services with TODO comments or stub implementations
- External integration failures (Stripe, Google Maps, etc.)

### Agent 3 — Database & Data Model Explorer
Audit all SQLAlchemy models, migrations, and data flow:
- Models without relationships defined
- Missing indexes on queried columns
- Columns with wrong types
- Data integrity issues (orphaned records, nulls where required)
- Missing migrations for model changes

### Agent 4 — Feature Completeness Auditor
Check each major feature against its intended scope:
- **Marketplace**: datasets, signals, checkout, purchases
- **Reports**: Layer 1/2/3, Consultant Studio, Report Studio
- **Opportunities**: creation, validation, scoring, discovery
- **Expert Marketplace**: profiles, bookings, payments
- **Workspaces**: maps, notes, tasks, documents
- **Admin**: dashboard, analytics, user management
- **Google Pipeline**: scraping, keyword groups, catalog
- **Integrations**: Stripe, Mapbox, Census, AI APIs

### Agent 5 — Security & Performance Auditor
- Missing auth checks on endpoints
- Open redirect vulnerabilities
- SQL injection risks (raw SQL strings)
- N+1 query patterns
- Missing rate limits
- Hardcoded secrets or API keys
- CORS misconfiguration

## Phase 2: Synthesis
Orchestrator merges all findings, deduplicates, and prioritizes:
- P0: Critical (data loss, security, crashes)
- P1: Important (broken features, bad UX)
- P2: Nice to have (missing polish, incomplete implementations)

## Phase 3: Report
Deliver a structured markdown report with:
- Executive summary (top 10 issues)
- Per-domain findings with severity
- Recommended fixes with file paths
- Estimated effort per fix
