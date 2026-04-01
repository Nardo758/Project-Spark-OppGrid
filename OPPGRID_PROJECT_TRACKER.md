# 🚀 OPPGRID PROJECT TRACKER

**Project:** OppGrid - Opportunity Discovery & Business Intelligence Platform
**Status:** 60-70% Complete (Up from 67% with detailed assessment)
**Last Updated:** 2026-04-01 06:58 AM PT
**Owner:** Leon D

---

## 📊 CURRENT STATUS DASHBOARD

| Component | Status | Completion | Blocker |
|-----------|--------|-----------|---------|
| **Frontend Pages** | ✅ Built | 95% | None |
| **Backend APIs** | ✅ Built | 85% | Missing API Keys |
| **Database** | ✅ Ready | 100% | None |
| **Authentication** | ✅ Complete | 100% | None |
| **Consultant Studio** | 🟡 Partial | 65% | Data + Workflow (Design DONE) |
| **Payment Gating** | ✅ Endpoints Wired | 85% | Phase 2B: Stripe Webhook TODO |
| **Stripe Integration** | 🟡 In Progress | 30% | Checkout + Webhook TODO |
| **Admin Pricing Controls** | ❌ Backlog | 0% | Post-Launch Feature |
| **Custom Report Types** | ❌ Backlog | 0% | Post-Launch Feature |
| **Google Scraper** | ⚠️ Stub | 40% | SERPAPI_KEY + Job Scheduling |
| **Reddit Scraper** | ❌ Missing | 0% | Not Implemented |
| **Frontend-Backend Wiring** | ⚠️ Partial | 70% | Integration Testing |
| **Production Readiness** | ⚠️ Dev Only | 30% | Optimization + Security |

**Overall Progress: 72% Complete (April 1, 2026 - Phase 2A Payment Gating DONE, Phase 2B Stripe TODO)**

---

## 💳 PAYMENT GATING & REPORT ALLOCATION MODEL (April 1, 2026 - NEW)

**Status:** 🔴 **NEEDS IMPLEMENTATION** (Specification finalized)  
**Owner:** Leon D  
**Priority:** 🔴 HIGH  

### User Types & Access Model

```
┌─────────────────────────────────────────────────────────────┐
│  GUESTS (Not Signed Up)                                     │
├─────────────────────────────────────────────────────────────┤
│  ✓ CAN purchase reports via guest checkout                  │
│  💰 Pay-per-report model (no account required upfront)      │
│  ├─ Layer 1: $15/report                                     │
│  ├─ Layer 2: $25/report                                     │
│  └─ Layer 3: $35/report                                     │
│  📌 Account auto-created at checkout                        │
│  ✓ Report delivered immediately to email                    │
│  ✓ Account ready to use with login after payment            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  FREE MEMBERS (Signed Up, No Subscription)                  │
├─────────────────────────────────────────────────────────────┤
│  💰 Pay-per-report model (charged per generate)             │
│  ├─ Layer 1 Overview: $15/report                            │
│  ├─ Layer 2 Deep Dive: $25/report                           │
│  └─ Layer 3 Execution: $35/report                           │
│  📊 No allocation/quota system                              │
│  ✓ Can access Consultant Studio (Validate Idea, etc.)      │
│  ✓ Can generate analyses (if they pay per report)           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  PRO MEMBERS (Paid Subscription - $99/mo)                   │
├─────────────────────────────────────────────────────────────┤
│  📌 Allocated quota per month:                              │
│  ├─ Layer 1 Overview: 5 free reports/month                  │
│  ├─ Layer 2 Deep Dive: 2 free reports/month                 │
│  └─ Layer 3 Execution: 0 (must purchase)                    │
│  💰 Can purchase additional reports at discounted rate      │
│  ├─ Layer 1: $10/report (vs $15 for free members)           │
│  ├─ Layer 2: $18/report (vs $25 for free members)           │
│  └─ Layer 3: $25/report (vs $35 for free members)           │
│  ✓ Full access to Consultant Studio features                │
│  ✓ Quota resets monthly on billing date                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  BUSINESS MEMBERS (Paid Subscription - $299/mo)             │
├─────────────────────────────────────────────────────────────┤
│  📌 Allocated quota per month:                              │
│  ├─ Layer 1 Overview: 15 free reports/month                 │
│  ├─ Layer 2 Deep Dive: 8 free reports/month                 │
│  └─ Layer 3 Execution: 3 free reports/month                 │
│  💰 Can purchase additional reports at best rate            │
│  ├─ Layer 1: $8/report (vs $15 for free)                    │
│  ├─ Layer 2: $15/report (vs $25 for free)                   │
│  └─ Layer 3: $20/report (vs $35 for free)                   │
│  ✓ Full access to Consultant Studio features                │
│  ✓ Quota resets monthly on billing date                     │
│  ✓ Priority support + custom report requests                │
└─────────────────────────────────────────────────────────────┘
```

### Key Rules

1. **Authentication Required First**
   - Non-members cannot purchase at all
   - "Sign up to generate reports" message displayed
   - Checkout must be preceded by account creation

2. **Quota-Based for Members**
   - Free Members: No quota (pay-per-report only)
   - Pro/Business: Monthly allocation + overage pricing
   - Quota resets on billing date each month
   - Overage charges applied automatically

3. **Payment Gating Logic**
   ```
   IF user is NOT logged in:
       → Show "Sign up to generate reports" message
   ELSE IF user is Free Member:
       → Show "Generate Report for $15" button
       → Charge immediately upon generation
   ELSE IF user is Pro Member:
       → Check if quota remaining for this tier
       → IF quota > 0: Generate free (decrement quota)
       → IF quota = 0: Show "Generate Report for $10" button
   ELSE IF user is Business Member:
       → Check if quota remaining for this tier
       → IF quota > 0: Generate free (decrement quota)
       → IF quota = 0: Show "Generate Report for $8" button
   ```

### Implementation Checklist

#### Phase 1: Gating Logic (Backend) - 🔴 TODO
- [ ] Add `user_id` requirement to all report endpoints (block non-members)
- [ ] Create `UserReportQuota` model:
  ```python
  class UserReportQuota(Base):
      user_id: int (FK)
      tier: str (layer_1, layer_2, layer_3)
      allocated: int
      used: int
      reset_date: datetime
      updated_at: datetime
  ```
- [ ] Create quota tracking service:
  ```python
  class ReportQuotaService:
      def get_remaining_quota(user, tier) → int
      def check_quota_available(user, tier) → bool
      def decrement_quota(user, tier) → bool
      def get_effective_price(user, tier) → float (or 0 if free)
  ```
- [ ] Update `generate_layer1_report()`, `generate_layer2_report()`, `generate_layer3_report()`:
  - Check: Is user logged in? (auth guard)
  - Check: Quota available or charge price?
  - Decrement quota if tier allows
  - Charge Stripe if overage
  - Generate report

#### Phase 2: Stripe Integration - ✅ IN PROGRESS
- [x] Wire quota service into endpoints (DONE April 1, 08:00 AM)
- [ ] Add one-time charge endpoint for overages (Phase 2B - TODO)
- [ ] Stripe checkout session endpoint
- [ ] Webhook handler for payment success
- [ ] Auto-account creation for guests
- [ ] Email delivery post-payment
- [ ] Update subscription webhook to reset quotas
- [ ] Handle failed payments gracefully

#### Phase 3: Frontend Display - 🔴 TODO
- [ ] Update report generation buttons to show:
  - For non-members: "Sign up to generate"
  - For free members: "Generate for $15"
  - For pro members: "Generate free (4/5 remaining)" or "Generate for $10"
  - For business members: "Generate free (12/15 remaining)" or "Generate for $8"
- [ ] Add quota display in user dashboard
- [ ] Create ReportGenerationButton component
- [ ] Wire to endpoint with payment flow

#### Phase 4: Admin Pricing Controls - 🔴 TODO (Post-Launch)
**Priority:** MEDIUM | **Effort:** 2-3 hours

Move pricing from hardcoded to configurable:

- [ ] Create `PricingConfig` model (store in DB)
  - Report layer prices (currently: $15, $25, $35)
  - Subscription tier prices (Pro $99/mo, Business $299/mo)
  - Quota allocations (Pro: 5/2/0, Business: 15/8/3)
  - Overage pricing (Pro discount: 33%, Business discount: 47%)

- [ ] Admin endpoints
  - `GET /admin/pricing/reports` - View all report prices
  - `PATCH /admin/pricing/reports` - Update report prices
  - `GET /admin/pricing/subscriptions` - View subscription pricing
  - `PATCH /admin/pricing/subscriptions` - Update subscription pricing
  - `GET /admin/pricing/quotas` - View quota allocations
  - `PATCH /admin/pricing/quotas` - Update quota allocations

- [ ] Update ReportQuotaService to fetch from DB (not hardcoded)
- [ ] Add admin panel UI forms (optional, can manage via API)
- [ ] Audit trail of pricing changes

#### Phase 5: New Report Types Management - 🔴 TODO (Post-Launch)
**Priority:** MEDIUM | **Effort:** 3-4 hours

Allow admins to create custom report types without code changes:

- [ ] Create `ReportType` configuration system (currently: Layer 1/2/3 hardcoded)
  - Dynamic report type definitions
  - Custom pricing per type
  - Custom quota allocations
  - Custom report generation templates

- [ ] Admin endpoints
  - `GET /admin/report-types` - List all report types
  - `POST /admin/report-types` - Create new report type
  - `PATCH /admin/report-types/{id}` - Update report type
  - `DELETE /admin/report-types/{id}` - Disable report type

- [ ] Report type fields
  - name (e.g., "Executive Summary")
  - slug (e.g., "executive-summary")
  - base_price_cents
  - tier_allocations (Pro, Business)
  - tier_overage_prices
  - description
  - enabled (true/false)

- [ ] Update endpoint routing to support dynamic types
- [ ] Update frontend to dynamically load report types
- [ ] Add admin panel UI (optional)

### Files to Update

**Backend:**
- `app/models/user_report_quota.py` (new)
- `app/services/report_quota_service.py` (new)
- `app/routers/generated_reports.py` (update gating logic)
- `app/routers/reports.py` (update gating logic)
- `app/services/report_generator.py` (update tier check)

**Frontend:**
- `src/components/ReportGenerationButton.tsx` (new)
- `src/pages/build/ConsultantStudio.tsx` (update button displays)
- `src/pages/Dashboard.tsx` (add quota display)

---

## 🔍 CONSULTANT STUDIO GAP ASSESSMENT (April 1, 2026)

**Status:** ✅ Full gap analysis completed  
**Document:** `STUDIO_GAP_ASSESSMENT.md`  
**Key Finding:** Studio is 55% complete - design & data structuring needed

### Current vs Target Comparison

| Aspect | Current | Target | Gap | Priority | Effort |
|--------|---------|--------|-----|----------|--------|
| Header Design | Basic metadata | Institutional boxed | 🔴 Major | HIGH | 2-3h |
| Report Sections | 3/6 (50%) | 6/6 (100%) | 🔴 Major | HIGH | 6-8h |
| AI Workflow | References | DeepSeek→Opus explicit | 🟡 Medium | HIGH | 3-4h |
| PDF Export | Basic | Institutional styled | 🟡 Medium | MEDIUM | 4-5h |
| Data Fields | ~60% | ~95% | 🟡 Medium | MEDIUM | 4-6h |
| Guest Access | ✅ Works | ✅ Works | ✅ COMPLETE | - | - |

### Gaps Identified

#### Gap #1: Header Design (🔴 HIGH PRIORITY)
- **Missing:** Institutional boxed layout with OppGrid branding
- **Target:** Formatted header with report name, date, ID, verdict box
- **Files:** `ConsultantStudio.tsx`, create `ReportHeader.tsx`
- **Effort:** 2-3 hours

#### Gap #2: Report Sections (🔴 HIGH PRIORITY)
- **Missing:** 6 full sections (only 3 partial sections shown)
- **Sections Needed:**
  1. Executive Summary (2-3 paragraph verdict)
  2. Market Opportunity (market size, growth, saturation, audience)
  3. Business Model (rationale, success factors, pitfalls)
  4. Financial Viability (startup cost, margins, time to profit)
  5. Risk Assessment (categorized risks with mitigation)
  6. Similar Opportunities (proof-of-concept examples)
- **Files:** Create folder `ReportSections/` with 6 components
- **Effort:** 6-8 hours

#### Gap #3: AI Workflow (🟡 MEDIUM PRIORITY)
- **Missing:** Explicit two-step workflow (DeepSeek draft → Opus polish)
- **Current:** References to AI, but not structured
- **Needed:** Separate draft & polish services with progress tracking
- **Files:** `ai_orchestrator.py`, create draft/polish services
- **Effort:** 3-4 hours

#### Gap #4: PDF Export (🟡 MEDIUM PRIORITY)
- **Missing:** Institutional styling in PDF
- **Target:** Matches header design, professional typography, colors
- **Files:** `report_export_service.py`, print CSS
- **Effort:** 4-5 hours

#### Gap #5: Data Population (🟡 MEDIUM PRIORITY)
- **Missing:** ~35% of fields from REPORT_DESIGN_SPEC
- **Issue:** Data exists but not fully structured/enriched
- **Files:** `report_data_service.py`, `consultant_studio.py`
- **Effort:** 4-6 hours

### Implementation Roadmap

**Phase 1: Foundation (Days 1-2, ~10 hours)** 🔴 CRITICAL

**Status: 📍 IN PROGRESS (2/3 components done)**

- [x] **Fix header design** ✅ DONE (April 1, 06:57 AM)
  - [x] Created `ReportHeader.tsx` component
  - [x] Institutional boxed layout with OppGrid branding
  - [x] Report name, date, ID display
  - [x] Verdict box with confidence + risk scores
  - [x] Integrated into ConsultantStudio validate tab
  - [x] Helper functions: generateReportId, formatDate, formatTime
  - Commit: `9cc3c17`

- [x] **Create 6 section components** ✅ DONE (April 1, 07:09 AM)
  - [x] ExecutiveSummary.tsx (verdict paragraph + metrics)
  - [x] MarketOpportunity.tsx (market size, growth, saturation, demographics)
  - [x] BusinessModel.tsx (recommendation + success factors + pitfalls)
  - [x] FinancialViability.tsx (startup cost, margins, time to profit, funding)
  - [x] RiskAssessment.tsx (4 risk categories with color-coded levels)
  - [x] NextSteps.tsx (4-phase validation roadmap + quick wins)
  - [x] SimilarOpportunities.tsx (5 proof-of-concept companies)
  - [x] Created ReportSections/index.ts for easy imports
  - [x] Integrated all 6 components into ConsultantStudio validate tab
  - Commit: `9fa79d1`

- ⏳ **Enhance report_data_service** (TODO - ~2-3 hours)
  - [ ] Add missing data fields for all 6 sections
  - [ ] Ensure 4 P's data complete
  - [ ] Add similar opportunities lookup
  - [ ] Verify data population accuracy

**Phase 2: AI Workflow (Days 2-3, ~6 hours)** 🟡 HIGH
- [ ] Explicit DeepSeek draft step
- [ ] Explicit Opus polish step
- [ ] Frontend progress indicators

**Phase 3: Polish (Days 3-4, ~8 hours)** 🟢 MEDIUM
- [ ] Section styling
- [ ] PDF export
- [ ] Complete data population

**Total Estimated Effort: 24 hours (~3 days)**

---

## 🎯 CRITICAL BLOCKERS

### ✅ 1. RESOLVED - PostGIS Removed (April 1, 2026)

**Original Issue:** `ALTER TABLE 'spatial_ref_sys' ADD PRIMARY KEY ('srid')` error on Replit  
**Root Cause:** PostGIS wasn't actually needed - OppGrid uses simple lat/lng storage  
**Solution:** Removed all PostGIS references from codebase  

**What Changed:**
- ✅ Removed PostGIS migration hooks from `20251219_0004_bootstrap_schema.py`
- ✅ No Geometry columns in any models (confirmed)
- ✅ Location data stored as `latitude` + `longitude` floats
- ✅ Updated DOT traffic service docstring (no PostGIS mention)
- ✅ geoalchemy2 not in requirements.txt

**Impact:** ✅ **OppGrid now deploys cleanly to Replit**

**Distance Calculations (if needed):**
Use simple haversine function in Python instead of PostGIS:
```python
def haversine(lat1, lon1, lat2, lon2):
    """Calculate miles between two points"""
    from math import radians, cos, sin, asin, sqrt
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    mi = 3959 * c
    return mi
```

**Status:** 🟢 RESOLVED - Ready to deploy

---

### 2. 🔴 MISSING ENVIRONMENT VARIABLES

```
DEEPSEEK_API_KEY         ❌ NOT SET
ANTHROPIC_API_KEY        ❌ NOT SET
SERPAPI_KEY              ❌ NOT SET
STRIPE_SECRET_KEY        ❌ NOT SET
STRIPE_PUBLIC_KEY        ❌ NOT SET
DATABASE_URL             ❌ NEEDS CONFIG (See Blocker #1)
```

**Impact:** 
- Consultant Studio AI features disabled (DeepSeek/Claude)
- Google scraper disabled
- Stripe integration non-functional
- Reports can't be fully generated

---

## 📋 PHASE 1: CRITICAL FIXES (1-2 Days)

### Phase 1.0: Setup Environment Variables

**Priority: 🔴 CRITICAL**
**Effort: 15 minutes**
**Blocker: YES**

- [ ] **Task 1.0.1:** Collect API keys
  - [ ] Get DEEPSEEK_API_KEY from account
  - [ ] Get ANTHROPIC_API_KEY from Anthropic
  - [ ] Get SERPAPI_KEY from SerpAPI
  - [ ] Get Stripe keys from Stripe dashboard
  - [ ] Verify DATABASE_URL is correct

- [ ] **Task 1.0.2:** Create .env file with all keys
  ```bash
  # Copy backend/.env.example to backend/.env
  # Fill in all values
  ```

- [ ] **Task 1.0.3:** Verify environment variables loaded
  - [ ] Test: `python -c "import os; print(os.getenv('DEEPSEEK_API_KEY'))"`
  - [ ] Should return API key, not None

---

### Phase 1.1: Fix Consultant Studio

**Priority: 🔴 CRITICAL**
**Effort: 4-6 hours**
**Blocker: YES (blocking user testing)**

#### 1.1.1: Test Backend Endpoints Directly

- [ ] **Task 1.1.1.1:** Test validate-idea endpoint
  ```bash
  curl -X POST http://localhost:8000/api/v1/consultant/validate-idea \
    -H "Content-Type: application/json" \
    -d '{
      "idea_description": "A subscription service that delivers locally-roasted coffee beans to offices in downtown areas"
    }'
  ```
  - [ ] Expected: Returns online_score, physical_score, recommendation
  - [ ] Actual: ___________
  - [ ] Status: ✅ / ⚠️ / ❌

- [ ] **Task 1.1.1.2:** Test search-ideas endpoint
  ```bash
  curl -X POST http://localhost:8000/api/v1/consultant/search-ideas \
    -H "Content-Type: application/json" \
    -d '{"query": "coffee subscription"}'
  ```
  - [ ] Expected: Returns opportunities array
  - [ ] Actual: ___________
  - [ ] Status: ✅ / ⚠️ / ❌

- [ ] **Task 1.1.1.3:** Test identify-location endpoint
  ```bash
  curl -X POST http://localhost:8000/api/v1/consultant/identify-location \
    -H "Content-Type: application/json" \
    -d '{"city": "Miami, FL", "business_description": "coffee shop with drive-thru"}'
  ```
  - [ ] Expected: Returns market_report, site_recommendations
  - [ ] Actual: ___________
  - [ ] Status: ✅ / ⚠️ / ❌

- [ ] **Task 1.1.1.4:** Test clone-success endpoint
  ```bash
  curl -X POST http://localhost:8000/api/v1/consultant/clone-success \
    -H "Content-Type: application/json" \
    -d '{
      "business_name": "Starbucks",
      "business_address": "123 Main St, New York, NY",
      "target_city": "Miami"
    }'
  ```
  - [ ] Expected: Returns matching_locations array
  - [ ] Actual: ___________
  - [ ] Status: ✅ / ⚠️ / ❌

#### 1.1.2: Debug AI Orchestrator

- [ ] **Task 1.1.2.1:** Check AI orchestrator error handling
  - [ ] Review: `backend/app/services/ai_orchestrator.py`
  - [ ] Check timeout values (currently 30s)
  - [ ] Verify fallback logic to Claude
  - [ ] Add logging for API calls

- [ ] **Task 1.1.2.2:** Increase timeout values if needed
  - [ ] Current: 40s timeout for validate-idea
  - [ ] Proposed: 60s timeout for initial requests
  - [ ] Add progress indicators to frontend

- [ ] **Task 1.1.2.3:** Implement retry logic
  - [ ] Add exponential backoff (1s, 2s, 4s, 8s)
  - [ ] Max 3 retries before failing
  - [ ] Better error messages

#### 1.1.3: Fix Frontend ConsultantStudio Component

- [ ] **Task 1.1.3.1:** Add error boundary
  - [ ] File: `frontend/src/pages/build/ConsultantStudio.tsx`
  - [ ] Wrap mutations in try-catch
  - [ ] Display error messages to user

- [ ] **Task 1.1.3.2:** Improve loading states
  - [ ] Add spinner for validate-idea (40s wait)
  - [ ] Show "Analyzing your business model..." message
  - [ ] Disable button during submission

- [ ] **Task 1.1.3.3:** Add result validation
  - [ ] Check if response has required fields
  - [ ] Handle partial data gracefully
  - [ ] Show warning if scores are mock data

- [ ] **Task 1.1.3.4:** Test all 4 tabs manually
  - [ ] Tab 1: Validate Idea ✅ / ❌
  - [ ] Tab 2: Search Ideas ✅ / ❌
  - [ ] Tab 3: Identify Location ✅ / ❌
  - [ ] Tab 4: Clone Success ✅ / ❌

#### 1.1.4: Create Test Report

- [ ] **Task 1.1.4.1:** Document test results
  - [ ] Which endpoints work?
  - [ ] Which fail?
  - [ ] What are error messages?

- [ ] **Task 1.1.4.2:** Update status in tracker
  - [ ] Update "Consultant Studio" status
  - [ ] Mark blockers as resolved/remaining

---

### Phase 1.2: Quick Stripe Setup

**Priority: 🟡 HIGH**
**Effort: 2-3 hours**
**Blocker: YES (for payment features)**

- [ ] **Task 1.2.1:** Add Stripe keys to .env
  - [ ] STRIPE_SECRET_KEY=___________
  - [ ] STRIPE_PUBLIC_KEY=___________

- [ ] **Task 1.2.2:** Test Stripe webhook
  - [ ] Verify webhook endpoint: `/api/v1/stripe-webhook`
  - [ ] Test with Stripe CLI: `stripe listen --forward-to localhost:8000/api/v1/stripe-webhook`
  - [ ] Create test payment event

- [ ] **Task 1.2.3:** Create basic checkout button
  - [ ] File: `frontend/src/components/CheckoutButton.tsx`
  - [ ] Integrate Stripe elements
  - [ ] Test payment flow

---

## 📋 PHASE 2: STRIPE INTEGRATION (2-3 Days)

**Priority: 🟠 HIGH**
**Effort: 16-20 hours**
**Depends On:** Phase 1 Complete

### 2.1: Frontend Checkout Flow

- [ ] **Task 2.1.1:** Create BillingPage component
  - [ ] Current plan display
  - [ ] Plan comparison table
  - [ ] Upgrade button per plan

- [ ] **Task 2.1.2:** Create CheckoutModal
  - [ ] Show plan details
  - [ ] Stripe card input
  - [ ] Submit button with loading state

- [ ] **Task 2.1.3:** Implement payment success flow
  - [ ] Redirect to success page
  - [ ] Update user subscription status
  - [ ] Show confirmation

- [ ] **Task 2.1.4:** Implement payment error handling
  - [ ] Display error to user
  - [ ] Retry button
  - [ ] Contact support link

### 2.2: Backend Payment Gating

- [ ] **Task 2.2.1:** Add subscription check middleware
  - [ ] File: `backend/app/middleware/subscription_check.py`
  - [ ] Check user tier for protected endpoints
  - [ ] Return 402 if payment required

- [ ] **Task 2.2.2:** Gate premium features
  - [ ] Deep Clone Analysis (requires payment)
  - [ ] Advanced reports (Pro+ only)
  - [ ] Expert consultation (Business+ only)

- [ ] **Task 2.2.3:** Implement free trial logic
  - [ ] 7 days free for new users
  - [ ] Track trial start date
  - [ ] Disable features on trial expiry

### 2.3: Subscription Management

- [ ] **Task 2.3.1:** Create subscription API endpoints
  - [ ] GET `/api/v1/billing/subscription` - Current subscription
  - [ ] POST `/api/v1/billing/upgrade` - Change plan
  - [ ] POST `/api/v1/billing/cancel` - Cancel subscription

- [ ] **Task 2.3.2:** Add webhook handling for Stripe events
  - [ ] `customer.subscription.updated`
  - [ ] `customer.subscription.deleted`
  - [ ] `invoice.payment_succeeded`
  - [ ] `invoice.payment_failed`

- [ ] **Task 2.3.3:** Display subscription status in UI
  - [ ] Show current plan on dashboard
  - [ ] Show renewal date
  - [ ] Show usage limits

---

## 📋 PHASE 3: GOOGLE SCRAPER ACTIVATION (2-3 Days)

**Priority: 🟠 HIGH**
**Effort: 12-16 hours**
**Depends On:** Phase 1 Complete

### 3.1: Scraper Setup

- [ ] **Task 3.1.1:** Set SERPAPI_KEY in .env
  - [ ] Verify key is valid
  - [ ] Test API call

- [ ] **Task 3.1.2:** Test GoogleScrapingService
  ```python
  # Test script
  from app.services.google_scraping_service import GoogleScrapingService
  service = GoogleScrapingService(db)
  results = service.search_google_maps("coffee shops", "Miami, FL")
  print(results)
  ```

- [ ] **Task 3.1.3:** Create LocationCatalog seed data
  - [ ] Add 10 test cities
  - [ ] Add 5 test business types
  - [ ] Verify in database

### 3.2: Admin Dashboard for Scraping

- [ ] **Task 3.2.1:** Create admin scrape dashboard
  - [ ] File: `frontend/src/pages/AdminScraping.tsx`
  - [ ] List available locations
  - [ ] List available business types
  - [ ] Button to start scrape job

- [ ] **Task 3.2.2:** Create scrape job endpoints
  - [ ] POST `/api/v1/admin/scrape-jobs` - Start job
  - [ ] GET `/api/v1/admin/scrape-jobs` - List jobs
  - [ ] GET `/api/v1/admin/scrape-jobs/{id}` - Job status

- [ ] **Task 3.2.3:** Implement scrape job tracking
  - [ ] File: `backend/app/models/scrape_job.py`
  - [ ] Track status: pending, running, completed, failed
  - [ ] Track results count
  - [ ] Track errors

### 3.3: Background Job Scheduling

- [ ] **Task 3.3.1:** Set up APScheduler or Celery
  - [ ] (Recommend APScheduler for simplicity)
  - [ ] Configure background task runner

- [ ] **Task 3.3.2:** Create scheduled scrape jobs
  - [ ] Run daily at 2 AM
  - [ ] Scrape 5 locations × 5 business types
  - [ ] Update GoogleMapsBusiness table

- [ ] **Task 3.3.3:** Add monitoring
  - [ ] Log job start/end
  - [ ] Alert on failures
  - [ ] Track data freshness

### 3.4: Frontend Integration

- [ ] **Task 3.4.1:** Create location analysis page
  - [ ] File: `frontend/src/pages/LocationAnalysis.tsx`
  - [ ] Search form: city + business type
  - [ ] Display top results map
  - [ ] Show metrics: competition count, foot traffic estimate

- [ ] **Task 3.4.2:** Add to Consultant Studio
  - [ ] Integration with "Identify Location" tab
  - [ ] Show actual Google Maps data (not mock)

---

## 📋 PHASE 4: BACKEND-FRONTEND INTEGRATION (3-5 Days)

**Priority: 🟡 MEDIUM**
**Effort: 20-28 hours**
**Depends On:** Phase 1 Complete

### 4.1: Expert Marketplace

- [ ] **Task 4.1.1:** Wire expert list API
  - [ ] File: `frontend/src/pages/ExpertMarketplace.tsx`
  - [ ] GET `/api/v1/experts` - List all experts
  - [ ] Pagination, filtering, search

- [ ] **Task 4.1.2:** Create expert detail page
  - [ ] Display expert profile
  - [ ] Show services offered
  - [ ] Book consultation button

- [ ] **Task 4.1.3:** Implement booking system
  - [ ] Calendar integration
  - [ ] Payment collection
  - [ ] Confirmation email

### 4.2: Leads Marketplace

- [ ] **Task 4.2.1:** Wire leads list API
  - [ ] File: `frontend/src/pages/LeadsMarketplace.tsx`
  - [ ] GET `/api/v1/leads` - List available leads
  - [ ] Filter by category, price, quality

- [ ] **Task 4.2.2:** Add to cart / bulk purchase
  - [ ] Add leads to cart
  - [ ] Bulk discount pricing
  - [ ] Checkout flow

- [ ] **Task 4.2.3:** Show lead details
  - [ ] Lead description
  - [ ] Contact info (if purchased)
  - [ ] Follow-up date

### 4.3: Real-time Features

- [ ] **Task 4.3.1:** Activate WebSocket notifications
  - [ ] File: `backend/app/websocket/websocket_router.py`
  - [ ] Test WebSocket connection
  - [ ] Send test message

- [ ] **Task 4.3.2:** Add notification listener on frontend
  - [ ] Connect to WebSocket
  - [ ] Receive real-time updates
  - [ ] Display notifications

- [ ] **Task 4.3.3:** Create activity feed
  - [ ] File: `frontend/src/components/ActivityFeed.tsx`
  - [ ] Show recent activities
  - [ ] Real-time updates

### 4.4: Admin Dashboard Completion

- [ ] **Task 4.4.1:** Complete admin stats
  - [ ] Total users
  - [ ] Total opportunities
  - [ ] Revenue metrics
  - [ ] API usage

- [ ] **Task 4.4.2:** Add user management
  - [ ] List all users
  - [ ] Edit user details
  - [ ] Suspend/delete users

- [ ] **Task 4.4.3:** Add moderation tools
  - [ ] Review flagged opportunities
  - [ ] Approve/reject
  - [ ] Ban bad actors

---

## 📋 PHASE 5: REDDIT SCRAPER (3-5 Days)

**Priority: 🟡 MEDIUM (Optional)**
**Effort: 16-20 hours**
**Depends On:** Phase 1, 3 Complete

### 5.1: Setup PRAW

- [ ] **Task 5.1.1:** Install PRAW (Python Reddit API Wrapper)
  ```bash
  pip install praw
  ```

- [ ] **Task 5.1.2:** Create Reddit app credentials
  - [ ] Go to reddit.com/prefs/apps
  - [ ] Create script app
  - [ ] Get client_id, client_secret

- [ ] **Task 5.1.3:** Add to .env
  ```
  REDDIT_CLIENT_ID=___________
  REDDIT_CLIENT_SECRET=___________
  REDDIT_USER_AGENT=oppgrid/1.0
  ```

### 5.2: Build Reddit Service

- [ ] **Task 5.2.1:** Create RedditScraperService
  - [ ] File: `backend/app/services/reddit_scraper_service.py`
  - [ ] Connect to Reddit API
  - [ ] Scrape problems from subreddits

- [ ] **Task 5.2.2:** Define target subreddits
  - [ ] r/NoStupidQuestions
  - [ ] r/EverythingDesign
  - [ ] r/AskSmallBusiness
  - [ ] r/Entrepreneur
  - [ ] r/startups

- [ ] **Task 5.2.3:** Parse problem statements
  - [ ] Extract title + description
  - [ ] Get upvotes (as relevance metric)
  - [ ] Get comment count (as validation signal)
  - [ ] Get timestamp

### 5.3: Store Reddit Data

- [ ] **Task 5.3.1:** Create RedditProblem model
  - [ ] File: `backend/app/models/reddit_problem.py`
  - [ ] Store title, description, URL
  - [ ] Store upvotes, comments, timestamp
  - [ ] Link to Opportunity (if matched)

- [ ] **Task 5.3.2:** Implement problem-to-opportunity mapping
  - [ ] Use Claude to categorize Reddit post
  - [ ] Find matching opportunity
  - [ ] Create new opportunity if no match

### 5.4: Scheduling & Admin

- [ ] **Task 5.4.1:** Create scheduled Reddit scrape job
  - [ ] Run every 4 hours
  - [ ] Scrape new posts from last 4 hours
  - [ ] Update validation signals

- [ ] **Task 5.4.2:** Add admin monitoring
  - [ ] Show scrape job status
  - [ ] Show data quality metrics
  - [ ] Show trending Reddit problems

---

## 📋 PHASE 6: PRODUCTION OPTIMIZATION (2-3 Days)

**Priority: 🟢 MEDIUM (Do Last)**
**Effort: 12-16 hours**
**Depends On:** All phases complete

### 6.1: Performance

- [ ] **Task 6.1.1:** Database query optimization
  - [ ] Profile slow queries
  - [ ] Add indexes on frequently searched columns
  - [ ] Implement caching (Redis)

- [ ] **Task 6.1.2:** Frontend performance
  - [ ] Minify JS/CSS
  - [ ] Implement code splitting
  - [ ] Add image optimization
  - [ ] Test Lighthouse score (target: 90+)

- [ ] **Task 6.1.3:** API response caching
  - [ ] Cache opportunity searches (5 min)
  - [ ] Cache location analysis (1 hour)
  - [ ] Cache expert profiles (24 hours)

### 6.2: Security

- [ ] **Task 6.2.1:** Security audit
  - [ ] Check for SQL injection vulnerabilities
  - [ ] Check for XSS vulnerabilities
  - [ ] Check for CSRF protection
  - [ ] Review authentication flows

- [ ] **Task 6.2.2:** Add rate limiting
  - [ ] File: `backend/app/middleware/rate_limit.py`
  - [ ] 100 requests/min per user
  - [ ] 1000 requests/min per IP

- [ ] **Task 6.2.3:** Add logging & monitoring
  - [ ] File: Setup ELK stack or LogRocket
  - [ ] Log all API calls
  - [ ] Alert on errors (>5% failure rate)

### 6.3: Deployment

- [ ] **Task 6.3.1:** Create production Docker image
  - [ ] File: `Dockerfile`
  - [ ] Test locally with docker compose
  - [ ] Push to Docker Hub

- [ ] **Task 6.3.2:** Deploy to production
  - [ ] Choose platform (AWS, GCP, DigitalOcean, Heroku)
  - [ ] Configure database
  - [ ] Set up SSL certificate
  - [ ] Configure domain

- [ ] **Task 6.3.3:** Setup monitoring
  - [ ] Uptime monitoring (ping service)
  - [ ] Error tracking (Sentry)
  - [ ] Performance monitoring (DataDog)

- [ ] **Task 6.3.4:** Create runbook
  - [ ] How to deploy
  - [ ] How to roll back
  - [ ] How to handle emergencies

---

## 🎯 QUICK WINS (Do First!)

**Total Time: 1-2 hours**

Priority Order:
1. [ ] **15 min** - Set environment variables
2. [ ] **30 min** - Test consultant endpoints with curl
3. [ ] **30 min** - Check AI orchestrator logs
4. [ ] **15 min** - Verify database connection

---

## 📈 PROGRESS TRACKING

### Weekly Milestones

**Week 1 (Mar 31 - Apr 6):**
- [ ] Phase 1.0: Setup env variables ✅
- [ ] Phase 1.1: Fix Consultant Studio ✅
- [ ] Phase 1.2: Stripe setup ✅
- **Target: 75% Complete**

**Week 2 (Apr 7 - Apr 13):**
- [ ] Phase 2: Stripe integration complete
- [ ] Phase 3: Google scraper activated
- **Target: 85% Complete**

**Week 3 (Apr 14 - Apr 20):**
- [ ] Phase 4: Backend-frontend wiring
- [ ] Phase 5: Reddit scraper (optional)
- **Target: 95% Complete**

**Week 4 (Apr 21 - Apr 27):**
- [ ] Phase 6: Production optimization
- [ ] Testing & bug fixes
- **Target: 100% Complete - LAUNCH READY**

---

## 🔧 TECHNICAL DEBT LOG

| Issue | Severity | Phase to Fix |
|-------|----------|-------------|
| AI orchestrator error handling | 🔴 High | Phase 1 |
| Timeout on long-running AI tasks | 🔴 High | Phase 1 |
| No logging in consultant service | 🟠 Medium | Phase 1 |
| Stripe integration incomplete | 🟠 Medium | Phase 2 |
| No rate limiting | 🟠 Medium | Phase 6 |
| Frontend error boundaries missing | 🟡 Low | Phase 4 |
| No database indexes | 🟡 Low | Phase 6 |

---

## 📞 BLOCKERS & ESCALATIONS

**Current Blockers:**
1. 🔴 Missing DEEPSEEK_API_KEY → Blocks Consultant Studio
2. 🔴 Missing ANTHROPIC_API_KEY → Blocks AI features
3. 🔴 Missing SERPAPI_KEY → Blocks Google Scraper

**Status:** WAITING FOR API KEYS

---

## 📝 NOTES & DECISIONS

**Decision Log:**

**2026-03-31 - Initial Assessment:**
- Identified 67% completion rate
- Created 6-phase recovery plan
- Prioritized API key setup as critical blocker
- Estimated 4 weeks to production readiness

**Next Review:** 2026-04-07

---

## 🚀 LAUNCH CHECKLIST

Pre-launch Requirements:
- [ ] All phases complete
- [ ] Security audit passed
- [ ] Performance testing complete (90+ Lighthouse)
- [ ] Load testing (1000 concurrent users)
- [ ] User acceptance testing
- [ ] Legal/compliance review
- [ ] Documentation complete
- [ ] Incident response plan
- [ ] Monitoring & alerting active
- [ ] Backup & disaster recovery tested

---

## 📊 STATUS LEGEND

- ✅ Complete / Working
- ⚠️ In Progress / Partial
- 🔴 Blocked / Critical Issue
- ❌ Not Started / Missing
- 🟡 Medium Priority
- 🟠 High Priority
- 🟢 Low Priority

---

**Last Updated:** 2026-03-31 15:56 PDT
**Next Review:** 2026-04-07
**Owner:** Leon D
**Status:** IN PROGRESS