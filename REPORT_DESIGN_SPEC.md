# 📋 OppGrid Report Design Specification

**Version:** 1.0  
**Date:** 2026-03-31  
**Status:** ACTIVE  
**Owner:** Leon D

---

## Overview

This document defines the design, layout, and content structure for all OppGrid reports, particularly the **Validate Idea Report** generated in the Consultant Studio.

All reports follow a consistent visual and structural template for **institutional, professional presentation** with:
- **OppGrid branding** prominently displayed in header
- **Report name/type** clearly labeled (e.g., "Validate Idea Analysis")
- **Report date** clearly visible (e.g., "March 31, 2026")
- **Professional layout** that looks like a corporate report
- **Consistent styling** across all sections

---

## Design Philosophy

**Goal:** Reports should look institutional and professional—the kind of document you'd send to investors, advisors, or co-founders.

**Key Principles:**
1. **Branded Header** - OppGrid logo/name top-center, unmistakable
2. **Clear Metadata** - Date, report type, ID all immediately visible
3. **Professional Typography** - Clean, serious fonts (no playful emojis in text)
4. **Structured Layout** - Clear sections with visual hierarchy
5. **Institutional Feel** - Look like a consulting report, not a casual document
6. **Print-Ready** - Looks good on paper and screen

---

## 1. REPORT HEADER TEMPLATE

### Visual Layout (Institutional Design)

```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│                         🎯 OPPGRID                                 │
│                    CONSULTANT STUDIO REPORT                        │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  REPORT: Validate Idea Analysis                                   │
│  SUBJECT: Mental Health Clinic                                    │
│  DATE: March 31, 2026                                             │
│  REPORT ID: REPT-2026-03-31-001                                   │
│  TIME GENERATED: 10:45 PM PT                                      │
│                                                                    │
│  KEY VERDICT: HYBRID (Online + Physical) ✓ RECOMMENDED            │
│  CONFIDENCE: 89%                                                  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### PDF Header (Full Professional Layout)

```
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║                      ████  ██████  ████  ██████                  ║
║                      █   █ █       █   █ █                        ║
║                      ████  ██████  ████  ██████                  ║
║                      █   █      █  █ █        █                   ║
║                      ████  ██████  █  █ ██████                  ║
║                                                                    ║
║                    CONSULTANT STUDIO REPORT                        ║
║                                                                    ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  REPORT NAME:           Validate Idea Analysis                    ║
║  BUSINESS IDEA:         Mental Health Clinic                      ║
║  REPORT ID:             REPT-2026-03-31-001                       ║
║                                                                    ║
║  REPORT DATE:           March 31, 2026                            ║
║  GENERATED AT:          10:45 PM Pacific Time                     ║
║  TIME TO GENERATE:      47 seconds                                ║
║                                                                    ║
║  ────────────────────────────────────────────────────────────    ║
║                                                                    ║
║  RECOMMENDATION:        HYBRID (Online + Physical)                ║
║  CONFIDENCE SCORE:      89%                                       ║
║  OVERALL RISK LEVEL:    MEDIUM (6.2/10)                           ║
║                                                                    ║
║  VERDICT:               ✓ PROCEED WITH VALIDATION                 ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
```

### Header Fields

| Field | Type | Max Length | Required | Display | Notes |
|-------|------|-----------|----------|---------|-------|
| `oppgrid_logo` | image | N/A | Yes | Top center | OppGrid branding |
| `report_type_display` | string | 60 | Yes | Top | "CONSULTANT STUDIO REPORT" |
| `report_name` | string | 100 | Yes | Line 1 | "Validate Idea Analysis" / "Market Analysis" / etc. |
| `subject` | string | 200 | Yes | Line 2 | User's business idea or subject |
| `report_id` | string | 20 | Yes | Line 3 | Unique: REPT-YYYY-MM-DD-NNN |
| `report_date` | date | N/A | Yes | Line 4 | "March 31, 2026" (formatted) |
| `generated_at` | datetime | N/A | Yes | Line 5 | "10:45 PM PT" (user's timezone) |
| `generation_time_ms` | integer | N/A | Yes | Line 6 | "47 seconds" |
| `recommendation` | enum | N/A | Yes | Verdict section | online, physical, hybrid |
| `confidence_score` | integer | N/A | Yes | Verdict section | 0-100, shown as % |
| `risk_score` | float | N/A | Yes | Verdict section | 0-10 scale |
| `verdict_recommendation` | enum | N/A | Yes | Bottom | proceed, proceed_with_caution, do_not_proceed |

---

## 2. VALIDATE IDEA REPORT STRUCTURE

### Overall Organization

```
┌─────────────────────────────────────────────┐
│  HEADER                                     │
│  - Report Title                             │
│  - Business Idea                            │
│  - Key Metrics (recommendation, confidence) │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  EXECUTIVE SUMMARY                          │
│  (2-3 paragraph verdict)                    │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  SECTION 1: MARKET OPPORTUNITY              │
│  - Market Size & Growth                     │
│  - Target Customer Profile                  │
│  - Competitive Saturation                   │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  SECTION 2: BUSINESS MODEL                  │
│  - Recommendation Rationale                 │
│  - Key Success Factors                      │
│  - Common Pitfalls to Avoid                 │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  SECTION 3: FINANCIAL VIABILITY             │
│  - Startup Cost Range                       │
│  - Time to Profitability                    │
│  - Revenue Potential                        │
│  - Margin Potential                         │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  SECTION 4: RISK ASSESSMENT                 │
│  - Market Risk                              │
│  - Execution Risk                           │
│  - Competition Risk                         │
│  - Regulatory Risk                          │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  SECTION 5: NEXT STEPS (VALIDATION ROADMAP) │
│  - What to Validate First                   │
│  - Resources Needed                         │
│  - Timeline Estimate                        │
│  - Quick Wins                               │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  SECTION 6: SIMILAR OPPORTUNITIES           │
│  - 3-5 existing businesses with similar     │
│    model showing success patterns           │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│  FOOTER                                     │
│  - Disclaimer                               │
│  - Data Sources                             │
│  - Contact Info                             │
└─────────────────────────────────────────────┘
```

---

## 3. SECTION-BY-SECTION CONTENT SCHEMA

### SECTION 1: MARKET OPPORTUNITY

**Purpose:** Understand the market demand, size, and growth potential for this business idea.

**Visual Mockup:**
```
┌──────────────────────────────────────────────────────────────┐
│ 📊 MARKET OPPORTUNITY                                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ Market Size: $5.2B - $8.4B (2025 est.)                      │
│ Growth Rate: +13.5% CAGR (2025-2030)                        │
│                                                               │
│ Your Target Market:                                          │
│ • Primary: Urban professionals 25-45, high-income ($75k+)   │
│ • Secondary: Health-conscious millennials seeking wellness   │
│ • Size: ~2.3M people in metro areas (US-wide)              │
│                                                               │
│ Market Saturation: MEDIUM                                    │
│ • Established players: 15-25 per metro                       │
│ • New entrants: 2-3 per year in major cities               │
│ • Consolidation trend: Yes (larger groups acquiring independ │
│                                                               │
│ Key Trend: Telehealth adoption + hybrid models rising        │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Data Schema:**

| Field | Type | Example | Required | Notes |
|-------|------|---------|----------|-------|
| `market_size_low` | number | 5200000000 | Yes | Low estimate in USD |
| `market_size_high` | number | 8400000000 | Yes | High estimate in USD |
| `market_year` | integer | 2025 | Yes | Year estimate is from |
| `cagr_rate` | float | 13.5 | Yes | Compound annual growth rate % |
| `cagr_period_years` | integer | 5 | Yes | Years for CAGR projection |
| `primary_audience` | string | 200 | Yes | Primary target demographic |
| `secondary_audience` | string | 200 | No | Secondary target demographic |
| `target_market_size` | number | 2300000 | Yes | Addressable market in units/people |
| `saturation_level` | enum | medium | Yes | low, medium, high |
| `competitors_per_market` | string | 15-25 | Yes | Range of competitors in metro |
| `new_entrants_per_year` | integer | 2 | No | Annual new business formation |
| `consolidation_trend` | boolean | true | No | Is market consolidating? |
| `key_trend` | string | 200 | Yes | Major tailwind or headwind |

---

### SECTION 2: BUSINESS MODEL

**Purpose:** Explain why the recommended model (online/physical/hybrid) is right, what makes it succeed, and what could derail it.

**Visual Mockup:**
```
┌──────────────────────────────────────────────────────────────┐
│ 💼 BUSINESS MODEL RECOMMENDATION                              │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ RECOMMENDED: HYBRID (40% Online / 60% Physical)              │
│                                                               │
│ Why Hybrid?                                                   │
│ Mental health services require trust + personal connection,  │
│ but digital access removes geographic barriers. A hybrid     │
│ model lets you offer:                                         │
│ • Initial consultations & follow-ups online (low friction)   │
│ • Intensive therapy sessions in-person (high trust)          │
│ • Community events & workshops (physical anchor)             │
│                                                               │
│ KEY SUCCESS FACTORS:                                          │
│ ✓ Licensed therapists with at least 5+ years experience     │
│ ✓ Secure HIPAA-compliant telehealth platform                │
│ ✓ Strong brand around "accessible mental health"            │
│ ✓ Network effect (referral-driven, word of mouth)           │
│ ✓ Insurance partnerships (billing integration)              │
│                                                               │
│ COMMON PITFALLS TO AVOID:                                    │
│ ✗ Underestimating regulatory burden (licensing varies by     │
│   state/country)                                              │
│ ✗ Over-automating diagnosis/treatment (liability risk)       │
│ ✗ Poor therapist retention (burnout, low pay)               │
│ ✗ Pricing too low to sustain quality (race to bottom)       │
│ ✗ Ignoring mental health crisis protocols (serious liability)│
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Data Schema:**

| Field | Type | Example | Required | Notes |
|-------|------|---------|----------|-------|
| `recommended_model` | enum | hybrid | Yes | online, physical, hybrid |
| `online_percentage` | integer | 40 | Conditional | If hybrid, % online |
| `physical_percentage` | integer | 60 | Conditional | If hybrid, % physical |
| `recommendation_reasoning` | text | 300-500 | Yes | Why this model works |
| `success_factors` | array[string] | [...] | Yes | 4-6 key success factors |
| `pitfalls` | array[string] | [...] | Yes | 4-6 common pitfalls |
| `competitive_advantage` | string | 200 | No | What differentiates this |

---

### SECTION 3: FINANCIAL VIABILITY

**Purpose:** Give realistic expectations about capital needs, runway, and profit potential.

**Visual Mockup:**
```
┌──────────────────────────────────────────────────────────────┐
│ 💰 FINANCIAL VIABILITY                                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ STARTUP CAPITAL REQUIRED: LOW ($25K - $75K)                  │
│ ├─ Office/clinic space setup: $15K-$25K                      │
│ ├─ Telehealth platform & compliance: $5K-$10K               │
│ ├─ Legal/licensing/insurance: $3K-$5K                        │
│ ├─ Marketing & brand launch: $2K-$5K                         │
│ └─ Initial operating costs (3 months): $0-$30K              │
│                                                               │
│ TIME TO PROFITABILITY: 12-18 MONTHS                          │
│ • Assuming 5-10 clients per month ramp                       │
│ • Breakeven at ~15-20 active clients                         │
│                                                               │
│ REVENUE POTENTIAL: MEDIUM-HIGH                               │
│ • Average therapist billing rate: $80-150/hour              │
│ • With 20 clients @ 4 hours/week: $16K-30K/month            │
│ • With 2-3 therapists: $48K-90K/month                       │
│                                                               │
│ MARGIN POTENTIAL: 35-50%                                     │
│ • Therapist cost: 50-60% of revenue                          │
│ • Platform/overhead: 10-15% of revenue                       │
│ • Net margin: 25-40% (healthy for service business)          │
│                                                               │
│ FUNDING OPTIONS:                                              │
│ • Founder capital ($25K savings) - Fastest                   │
│ • Small business loan ($50K SBA) - 6-8 weeks                │
│ • Friends & family round ($100K) - 4-12 weeks               │
│ • Angel investor ($250K-$1M) - 3-6 months                   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Data Schema:**

| Field | Type | Example | Required | Notes |
|-------|------|---------|----------|-------|
| `startup_cost_range_low` | number | 25000 | Yes | Low estimate in USD |
| `startup_cost_range_high` | number | 75000 | Yes | High estimate in USD |
| `startup_cost_breakdown` | array[object] | [...] | Yes | Line items with costs |
| `time_to_profitability_months` | integer | 15 | Yes | Estimated months |
| `breakeven_volume` | string | "15-20 active clients" | Yes | Units/customers to breakeven |
| `revenue_potential_level` | enum | medium_high | Yes | low, medium, medium_high, high |
| `monthly_revenue_potential_low` | number | 16000 | Yes | Conservative monthly estimate |
| `monthly_revenue_potential_high` | number | 90000 | Yes | Optimistic monthly estimate |
| `margin_potential_low` | integer | 35 | Yes | Low % margin |
| `margin_potential_high` | integer | 50 | Yes | High % margin |
| `funding_options` | array[object] | [...] | No | Potential funding sources |

**Startup Cost Breakdown Object:**
```json
{
  "category": "Office/Clinic Space Setup",
  "low": 15000,
  "high": 25000,
  "notes": "Depends on city and build-out needs"
}
```

---

### SECTION 4: RISK ASSESSMENT

**Purpose:** Highlight key risks and how to mitigate them.

**Visual Mockup:**
```
┌──────────────────────────────────────────────────────────────┐
│ ⚠️ RISK ASSESSMENT                                            │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ MARKET RISK: MEDIUM ⚠️                                        │
│ • Risk: Telehealth adoption plateau or recession              │
│ • Likelihood: Medium (20-30%)                                │
│ • Impact: High (-30% revenue if market contracts)            │
│ • Mitigation: Diversify service offerings, build strong      │
│              relationships with corporate wellness programs  │
│                                                               │
│ EXECUTION RISK: LOW ✓                                         │
│ • Risk: Difficulty recruiting quality therapists             │
│ • Likelihood: Medium (40-50%)                                │
│ • Impact: Medium (-20% capacity initially)                   │
│ • Mitigation: Offer competitive pay, remote work options,    │
│              partnership with therapy schools/networks       │
│                                                               │
│ COMPETITION RISK: MEDIUM ⚠️                                   │
│ • Risk: Well-funded competitors (BetterHelp, Talkspace)      │
│ • Likelihood: High (will compete nationally)                 │
│ • Impact: Medium (pricing pressure, CAC inflation)           │
│ • Mitigation: Go niche/local, superior therapist retention,  │
│              community-focused model, white-label partnerships│
│                                                               │
│ REGULATORY RISK: MEDIUM-HIGH ⚠️⚠️                             │
│ • Risk: Changing telehealth regulations, licensing issues    │
│ • Likelihood: Medium (50%)                                   │
│ • Impact: High (could require full business pivot)           │
│ • Mitigation: Stay current on state regulations, consult      │
│              healthcare legal experts, build in licensing    │
│              for multiple states proactively                 │
│                                                               │
│ FINANCIAL RISK: LOW ✓                                         │
│ • Risk: Cash flow gap during growth phase                     │
│ • Likelihood: Low (10-20% if planning properly)              │
│ • Impact: Medium (inability to hire/expand)                  │
│ • Mitigation: Keep 6-month runway, secure credit line,       │
│              monthly revenue targets, gradual scaling         │
│                                                               │
│ RISK SCORE: 6.2 / 10 (Moderate Risk)                          │
│ Overall Assessment: Manageable with proper planning           │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Data Schema:**

| Field | Type | Example | Required | Notes |
|-------|------|---------|----------|-------|
| `risks` | array[object] | [...] | Yes | 4-6 risk assessments |

**Risk Object:**
```json
{
  "risk_type": "market",
  "risk_name": "Telehealth Adoption Plateau",
  "likelihood": "medium",
  "likelihood_pct": 25,
  "impact_level": "high",
  "impact_pct": 30,
  "description": "Market growth could slow if adoption plateaus",
  "mitigation_strategies": [
    "Diversify service offerings",
    "Build strong corporate partnerships"
  ]
}
```

**Risk Likelihood:** low (0-20%), medium (30-60%), high (70-100%)  
**Risk Impact:** low (-10%), medium (-30%), high (-50%)

---

### SECTION 5: NEXT STEPS (VALIDATION ROADMAP)

**Purpose:** Give actionable, prioritized steps to move forward.

**Visual Mockup:**
```
┌──────────────────────────────────────────────────────────────┐
│ 🎯 NEXT STEPS - VALIDATION ROADMAP                            │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ PHASE 1: MARKET VALIDATION (Week 1-4)                        │
│ └─ Conduct 20-30 customer interviews with target demographic │
│    • Do they have the pain point? (Urgency check)            │
│    • Would they pay for solution? (Pricing check)            │
│    • What's your competitive advantage? (Positioning check)  │
│    • Acceptance Criteria: 70%+ say "yes, I'd pay for this"  │
│                                                               │
│ PHASE 2: COMPETITIVE ANALYSIS (Week 2-5)                    │
│ └─ Deep dive on 5-8 direct competitors                       │
│    • Pricing structure and packages                          │
│    • Customer satisfaction (reviews, NPS)                    │
│    • Positioning and messaging                              │
│    • What are they missing? (Your angle)                     │
│    • Document: 1-page competitive matrix                     │
│                                                               │
│ PHASE 3: MVP CONCEPT (Week 4-8)                              │
│ └─ Define minimum viable product                             │
│    • Service packages (e.g., 30-min, 1-hour sessions)        │
│    • Delivery model (online, in-person, hybrid)              │
│    • Tech stack (video platform, booking, payments)          │
│    • Build simple landing page (Webflow/Bubble)              │
│    • Document: 1-page MVP spec                               │
│                                                               │
│ PHASE 4: PILOT TESTING (Week 8-16)                           │
│ └─ Validate with real paying customers                       │
│    • Recruit 5-10 beta customers (discounted rate)           │
│    • Run for 4-6 weeks and gather feedback                   │
│    • Measure: Customer satisfaction, retention, churn        │
│    • Acceptance Criteria: 80%+ would recommend               │
│                                                               │
│ QUICK WINS (Can do immediately):                             │
│ • Research state licensing requirements (2 hours)            │
│ • Brainstorm therapist recruitment strategy (1 hour)         │
│ • List 10 potential corporate wellness partners (1 hour)     │
│ • Find 5 telehealth platforms to evaluate (2 hours)          │
│                                                               │
│ RESOURCES NEEDED:                                             │
│ • $5K: Legal review (licensing, compliance)                  │
│ • $2K: Market research (surveys, interviews)                 │
│ • $3K: Tech setup (landing page, basic tools)                │
│ • Your time: 10-15 hours/week for 8 weeks                    │
│                                                               │
│ ESTIMATED TIMELINE:                                           │
│ Week 1-4:   Market validation (Parallel: Legal review)       │
│ Week 5-8:   Competitive analysis + MVP design                │
│ Week 9-16:  Pilot with beta customers                        │
│ Month 5:    Go/no-go decision                                │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Data Schema:**

| Field | Type | Example | Required | Notes |
|-------|------|---------|----------|-------|
| `next_steps` | array[object] | [...] | Yes | 4-6 phases/steps |
| `quick_wins` | array[string] | [...] | Yes | 3-5 things to do today |
| `resources_needed` | array[object] | [...] | No | Budget/time requirements |
| `timeline_weeks` | integer | 16 | Yes | Estimated weeks to market |

**Next Step Object:**
```json
{
  "phase": 1,
  "phase_name": "Market Validation",
  "weeks": "1-4",
  "objective": "Confirm customer problem and willingness to pay",
  "tasks": [
    "Conduct 20-30 customer interviews",
    "Validate pricing expectations",
    "Identify competitive advantages"
  ],
  "acceptance_criteria": "70%+ say 'I would pay for this'",
  "estimated_cost": 2000
}
```

---

### SECTION 6: SIMILAR OPPORTUNITIES

**Purpose:** Show social proof by highlighting existing successful businesses with similar model.

**Visual Mockup:**
```
┌──────────────────────────────────────────────────────────────┐
│ 📈 SIMILAR OPPORTUNITIES - PROOF OF CONCEPT                   │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ 1. BetterHelp (Online Mental Health Platform)                │
│    ├─ Model: Pure Online (Telehealth)                        │
│    ├─ Founded: 2013                                          │
│    ├─ Status: Public (AACQ), $1.2B+ revenue (2024)          │
│    ├─ Key Success: Low friction (mobile-first, affordable)   │
│    └─ What they did right: Scale, brand, insurance accepted  │
│                                                               │
│ 2. Ginger (Telehealth + Coaching)                            │
│    ├─ Model: Online therapy + behavioral coaching            │
│    ├─ Founded: 2015                                          │
│    ├─ Funding: $170M raised (Series C)                       │
│    ├─ Key Success: Corporate B2B partnerships (high LTV)     │
│    └─ What they did right: Focus on ROI for employers        │
│                                                               │
│ 3. Headspace (Meditation + Mental Wellness)                  │
│    ├─ Model: Online subscription (app + content)             │
│    ├─ Founded: 2010                                          │
│    ├─ Status: Series D, $3B valuation (2021)                │
│    ├─ Key Success: Product-first (not therapists), scalable  │
│    └─ What they did right: Content library, habit formation  │
│                                                               │
│ 4. TherapyWorks (Hybrid - Local Clinics + Telehealth)       │
│    ├─ Model: 40% in-person, 60% online (your model!)        │
│    ├─ Founded: 2008                                          │
│    ├─ Status: Local chains in 15 US states                   │
│    ├─ Key Success: Local brand trust + telehealth scale      │
│    └─ What they did right: Community integration + efficiency │
│                                                               │
│ 5. Talkspace (Asynchronous Therapy + Live Sessions)         │
│    ├─ Model: Text + video therapy (lower therapist cost)    │
│    ├─ Founded: 2012                                          │
│    ├─ Status: Public (TALK), recovering from challenges      │
│    ├─ Key Success: Unique async model reduced cost           │
│    └─ What to learn: Licensing, compliance is critical       │
│                                                               │
│ KEY PATTERNS:                                                 │
│ ✓ All founded 2008-2015 (market existed then)                │
│ ✓ All heavily funded ($50M-$300M+)                           │
│ ✓ All scaled to national/global presence                     │
│ ✓ All focus on either scale (pure online) or corporate B2B   │
│ ✓ Telehealth adoption accelerated post-COVID                 │
│                                                               │
│ DIFFERENTIATION OPPORTUNITY:                                 │
│ These players are either:                                    │
│ • National/global scale (impersonal)                         │
│ • Corporate-focused (high LTV but B2B sales cycle)           │
│                                                               │
│ Your angle could be:                                         │
│ • LOCAL + PERSONAL (community-focused, word-of-mouth)        │
│ • SPECIALIZED (e.g., therapists for startups, parents)       │
│ • HYBRID (avoiding pure online commoditization)              │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Data Schema:**

| Field | Type | Example | Required | Notes |
|-------|------|---------|----------|-------|
| `similar_opportunities` | array[object] | [...] | Yes | 3-5 proven examples |

**Similar Opportunity Object:**
```json
{
  "name": "BetterHelp",
  "category": "Mental Health Telehealth",
  "model": "Pure Online",
  "founded_year": 2013,
  "status": "Public (AACQ)",
  "revenue": "$1.2B+ (2024)",
  "funding_raised": "Public",
  "key_success_factors": [
    "Low friction (mobile-first)",
    "Affordable ($65-90/week)",
    "Insurance accepted",
    "Brand recognition"
  ],
  "what_they_did_right": "Scaled nationally, captured market early",
  "relevance": "Proves telehealth mental health market viability",
  "lessons": "Scale and brand matter, but local/niche can still compete"
}
```

---

## 4. EXECUTIVE SUMMARY TEMPLATE

**Purpose:** Condensed verdict (2-3 paragraphs) that can stand alone.

**Visual Mockup:**
```
┌──────────────────────────────────────────────────────────────┐
│ EXECUTIVE SUMMARY                                             │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ A hybrid mental health clinic combining in-person therapy    │
│ with telehealth accessibility is a VIABLE business with      │
│ MEDIUM-HIGH potential. The market is large ($5.2B-$8.4B),    │
│ growing at 13.5% annually, and proven successful by players  │
│ like BetterHelp ($1.2B revenue) and local chains across the  │
│ US. A hybrid model (40% online / 60% physical) balances      │
│ trust-building with geographic reach—a competitive advantage │
│ over pure-online competitors.                                │
│                                                               │
│ Financial outlook is favorable: initial capital needs are    │
│ modest ($25K-$75K), breakeven is achievable in 12-18 months  │
│ with 15-20 active clients, and long-term margins of 35-50%   │
│ are healthy for a services business. Key success factors are  │
│ licensed therapists (non-negotiable), regulatory compliance   │
│ (vary by state), and strong brand positioning around         │
│ "accessible, personalized mental health care."               │
│                                                               │
│ Primary risks are regulatory complexity and competition from  │
│ well-funded national players. These are MEDIUM-level risks    │
│ mitigated through localization, niche positioning, and early │
│ mover advantage in underserved regions. Overall risk score:   │
│ 6.2/10 (Moderate). Recommended next step: Validate customer  │
│ demand through 20-30 interviews with your target demographic  │
│ in Week 1-4.                                                  │
│                                                               │
│ VERDICT: PROCEED WITH VALIDATION (Low-Risk Exploration)      │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Data Schema:**

| Field | Type | Max Length | Required | Notes |
|-------|------|-----------|----------|-------|
| `verdict_summary` | string | 500 | Yes | 2-3 paragraphs, plain language |
| `verdict_recommendation` | enum | N/A | Yes | proceed_with_validation, proceed_with_caution, do_not_proceed |
| `recommendation_explanation` | string | 200 | Yes | 1-2 sentences on why |

---

## 5. FOOTER TEMPLATE

**Visual Mockup:**
```
═══════════════════════════════════════════════════════════════════

DISCLAIMERS & DATA SOURCES

This report is generated by OppGrid's AI analysis engine and should
not be considered professional business advice. The assessments are
based on publicly available data, industry trends, and historical
patterns—not proprietary or confidential information.

Always consult with legal, financial, and industry experts before
making business decisions.

DATA SOURCES:
• Market sizing: IBISWorld, Statista, market research databases
• Competitive data: Public company filings, press releases, websites
• Financial benchmarks: SBA Small Business Resources, Stripe Atlas
• Trend data: Google Trends, industry reports, news sources
• Your idea text: Analyzed by Claude AI (3-token analysis)

REPORT METADATA:
Generated by: OppGrid Consultant Studio
Generation time: March 31, 2026 at 10:45 PM PT
Analysis duration: 47 seconds
API calls: DeepSeek (pattern analysis) + Claude (report generation)
Data freshness: 2025 (most data), real-time (some market signals)

CONTACT & SUPPORT:
Questions about this report? Contact: support@oppgrid.ai
Need expert consultation? Book a consultant: /experts/booking

═══════════════════════════════════════════════════════════════════
```

---

## 6. PDF EXPORT STYLING

### Design System

**Colors:**
- Primary Brand: #D97757 (Coral/Rust)
- Success: #0F6E56 (Dark Green)
- Warning: #BA7517 (Orange)
- Critical: #CC3333 (Red)
- Neutral: #1C1917 (Dark Gray)
- Light Background: #F5F5F4 (Off-White)

**Typography:**
- Header Title: 28px, Bold, #1C1917
- Section Title: 18px, Bold, #D97757
- Body: 11px, Regular, #4B5563
- Metric Values: 24px, Bold, #1C1917
- Small text: 9px, Regular, #8B8B8B

**Spacing:**
- Page margins: 1 inch (25.4mm) all sides
- Section padding: 12pt top/bottom, 8pt left/right
- Line height: 1.5 for body text

**Page Layout:**
- Page size: A4 (8.27" × 11.69")
- Orientation: Portrait
- Font: Inter or Helvetica

**Header Styling:**
```css
.report-header {
  border: 2px solid #1C1917;
  border-radius: 8px;
  padding: 24px;
  background: #FFFFFF;
  page-break-after: avoid;
  margin-bottom: 24px;
}

.report-header-top {
  text-align: center;
  margin-bottom: 20px;
  border-bottom: 1px solid #E5E5E5;
  padding-bottom: 16px;
}

.report-logo {
  font-size: 32px;
  font-weight: bold;
  color: #D97757;
  margin-bottom: 8px;
  letter-spacing: 2px;
}

.report-type {
  font-size: 14px;
  font-weight: 600;
  color: #1C1917;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.report-metadata {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  font-size: 11px;
  color: #4B5563;
  margin: 12px 0;
}

.metadata-row {
  display: flex;
  justify-content: space-between;
}

.metadata-label {
  font-weight: 600;
  color: #1C1917;
  min-width: 140px;
}

.report-verdict {
  background: #F5F5F4;
  border-left: 4px solid #D97757;
  padding: 16px;
  margin-top: 16px;
  border-radius: 4px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.verdict-item {
  font-size: 11px;
}

.verdict-label {
  font-weight: 600;
  color: #1C1917;
  margin-bottom: 4px;
  display: block;
}

.verdict-value {
  font-size: 18px;
  font-weight: bold;
  color: #D97757;
}

.verdict-recommendation {
  grid-column: 1 / -1;
  background: #DCFCE7;
  border-left: 4px solid #0F6E56;
  padding: 12px;
  border-radius: 4px;
  color: #15803D;
  font-weight: 600;
  text-align: center;
}
```

**Section Styling:**
```css
h1 {
  font-size: 28px;
  font-weight: bold;
  color: #1C1917;
  margin-bottom: 24px;
}

h2 {
  font-size: 18px;
  font-weight: bold;
  color: #D97757;
  margin-top: 20px;
  margin-bottom: 12px;
  border-bottom: 2px solid #E5E5E5;
  padding-bottom: 8px;
}

p {
  font-size: 11px;
  line-height: 1.5;
  color: #4B5563;
  margin-bottom: 12px;
}

.metric-box {
  background: #F5F5F4;
  border-left: 4px solid #D97757;
  padding: 12px;
  margin: 12px 0;
  border-radius: 4px;
}

.success-factor {
  display: flex;
  align-items: center;
  margin: 8px 0;
  padding: 8px;
  background: #DCFCE7;
  border-radius: 4px;
  color: #15803D;
}

.pitfall {
  display: flex;
  align-items: center;
  margin: 8px 0;
  padding: 8px;
  background: #FEE2E2;
  border-radius: 4px;
  color: #991B1B;
}

.risk-high {
  background: #FEE2E2;
  border-left: 4px solid #CC3333;
}

.risk-medium {
  background: #FEF3C7;
  border-left: 4px solid #BA7517;
}

.risk-low {
  background: #DCFCE7;
  border-left: 4px solid #0F6E56;
}
```

---

## 7. COMPLETE EXAMPLE REPORT

### Full "Mental Health Clinic" Report

```
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║                         🎯 OPPGRID                                 ║
║                    CONSULTANT STUDIO REPORT                        ║
║                                                                    ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  REPORT NAME:           Validate Idea Analysis                    ║
║  SUBJECT:               Mental Health Clinic                      ║
║  REPORT ID:             REPT-2026-03-31-001                       ║
║                                                                    ║
║  DATE:                  March 31, 2026                            ║
║  TIME GENERATED:        10:45 PM Pacific Time                     ║
║  ANALYSIS DURATION:     47 seconds                                ║
║                                                                    ║
║  ────────────────────────────────────────────────────────────    ║
║                                                                    ║
║  RECOMMENDATION:        HYBRID (Online + Physical)                ║
║  CONFIDENCE SCORE:      89%                                       ║
║  RISK LEVEL:            MEDIUM (6.2/10)                           ║
║                                                                    ║
║  VERDICT:               ✓ PROCEED WITH VALIDATION                 ║
║                         (Low-Risk Exploration Phase)              ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝

───────────────────────────────────────────────────────────────────

EXECUTIVE SUMMARY

A hybrid mental health clinic combining in-person therapy with
telehealth accessibility is a VIABLE business with MEDIUM-HIGH
potential. The market is large ($5.2B-$8.4B), growing at 13.5%
annually, and proven successful by players like BetterHelp ($1.2B
revenue) and local chains across the US. A hybrid model (40% online
/ 60% physical) balances trust-building with geographic reach—a
competitive advantage over pure-online competitors.

Financial outlook is favorable: initial capital needs are modest
($25K-$75K), breakeven is achievable in 12-18 months with 15-20
active clients, and long-term margins of 35-50% are healthy for a
services business. Key success factors are licensed therapists
(non-negotiable), regulatory compliance (varies by state), and
strong brand positioning around "accessible, personalized mental
health care."

Primary risks are regulatory complexity and competition from
well-funded national players. These are MEDIUM-level risks mitigated
through localization, niche positioning, and early mover advantage
in underserved regions. Overall risk score: 6.2/10 (Moderate).
Recommended next step: Validate customer demand through 20-30
interviews with your target demographic in Week 1-4.

VERDICT: PROCEED WITH VALIDATION (Low-Risk Exploration Phase)

───────────────────────────────────────────────────────────────────

📊 MARKET OPPORTUNITY

Market Size: $5.2B - $8.4B (2025 est.)
Growth Rate: +13.5% CAGR (2025-2030)

Your Target Market:
• Primary: Urban professionals 25-45, high-income ($75k+)
• Secondary: Health-conscious millennials seeking wellness
• Size: ~2.3M people in metro areas (US-wide)

Market Saturation: MEDIUM
• Established players: 15-25 per metro
• New entrants: 2-3 per year in major cities
• Consolidation trend: Yes (larger groups acquiring independent)

Key Trend: Telehealth adoption + hybrid models rising
The mental health market saw a massive shift post-COVID. While
telehealth adoption has plateaued slightly (reaching 40-50% of
consumers), hybrid and localized models are gaining traction as
customers value personal connection alongside convenience.

───────────────────────────────────────────────────────────────────

💼 BUSINESS MODEL RECOMMENDATION

RECOMMENDED: HYBRID (40% Online / 60% Physical)

Why Hybrid?
Mental health services require trust + personal connection, but
digital access removes geographic barriers. A hybrid model lets you
offer:
• Initial consultations & follow-ups online (low friction)
• Intensive therapy sessions in-person (high trust)
• Community events & workshops (physical anchor)

KEY SUCCESS FACTORS:
✓ Licensed therapists with at least 5+ years experience
✓ Secure HIPAA-compliant telehealth platform
✓ Strong brand around "accessible mental health"
✓ Network effect (referral-driven, word of mouth)
✓ Insurance partnerships (billing integration)
✓ Local community presence and trust-building

COMMON PITFALLS TO AVOID:
✗ Underestimating regulatory burden (licensing varies by state/country)
✗ Over-automating diagnosis/treatment (liability risk)
✗ Poor therapist retention (burnout, low pay)
✗ Pricing too low to sustain quality (race to bottom)
✗ Ignoring mental health crisis protocols (serious liability)
✗ Assuming pure-online scales without local brand

───────────────────────────────────────────────────────────────────

💰 FINANCIAL VIABILITY

STARTUP CAPITAL REQUIRED: LOW ($25K - $75K)
├─ Office/clinic space setup: $15K-$25K (rent deposit + furnishings)
├─ Telehealth platform & compliance: $5K-$10K (tech stack)
├─ Legal/licensing/insurance: $3K-$5K (LLC, liability insurance)
├─ Marketing & brand launch: $2K-$5K (website, Google Ads)
└─ Initial operating costs (3 months): $0-$30K (payroll buffer)

TIME TO PROFITABILITY: 12-18 MONTHS
• Assuming 5-10 new clients per month ramp
• Breakeven at ~15-20 active clients at $100/hour

REVENUE POTENTIAL: MEDIUM-HIGH
• Average therapist billing rate: $80-150/hour
• With 20 clients @ 4 hours/week: $16K-30K/month (1 therapist)
• With 2-3 therapists: $48K-90K/month (scaled)

MARGIN POTENTIAL: 35-50%
• Therapist cost: 50-60% of revenue (salaries/contractor fees)
• Platform/overhead: 10-15% of revenue (tech, insurance)
• Net margin: 25-40% (healthy for service business)

FUNDING OPTIONS:
• Founder capital ($25K savings) - Fastest (weeks)
• Small business loan ($50K SBA) - 6-8 weeks
• Friends & family round ($100K) - 4-12 weeks
• Angel investor ($250K-$1M) - 3-6 months (if scaling nationally)

───────────────────────────────────────────────────────────────────

⚠️ RISK ASSESSMENT

MARKET RISK: MEDIUM ⚠️
Risk: Telehealth adoption plateau or recession
Likelihood: Medium (25%)
Impact: High (-30% revenue if market contracts)
Mitigation: Diversify service offerings, build strong relationships
with corporate wellness programs

EXECUTION RISK: LOW ✓
Risk: Difficulty recruiting quality therapists
Likelihood: Medium (40-50%)
Impact: Medium (-20% capacity initially)
Mitigation: Offer competitive pay, remote work options, partner
with therapy schools/networks

COMPETITION RISK: MEDIUM ⚠️
Risk: Well-funded competitors (BetterHelp, Talkspace)
Likelihood: High (will compete nationally)
Impact: Medium (pricing pressure, customer acquisition cost inflation)
Mitigation: Go niche/local, superior therapist retention, community-
focused model, white-label partnerships

REGULATORY RISK: MEDIUM-HIGH ⚠️⚠️
Risk: Changing telehealth regulations, licensing issues
Likelihood: Medium (50%)
Impact: High (could require full business pivot)
Mitigation: Stay current on state regulations, consult healthcare
legal experts, build licensing for multiple states proactively

FINANCIAL RISK: LOW ✓
Risk: Cash flow gap during growth phase
Likelihood: Low (15%)
Impact: Medium (inability to hire/expand)
Mitigation: Keep 6-month runway, secure credit line, monthly revenue
targets, gradual scaling

RISK SCORE: 6.2 / 10 (Moderate Risk)
Overall Assessment: Manageable with proper planning and legal review

───────────────────────────────────────────────────────────────────

🎯 NEXT STEPS - VALIDATION ROADMAP

PHASE 1: MARKET VALIDATION (Week 1-4)
Conduct 20-30 customer interviews with target demographic
• Do they have the pain point? (Urgency check)
• Would they pay for solution? (Pricing check)
• What's your competitive advantage? (Positioning check)
Acceptance Criteria: 70%+ say "yes, I'd pay for this"

PHASE 2: COMPETITIVE ANALYSIS (Week 2-5)
Deep dive on 5-8 direct competitors
• Pricing structure and packages
• Customer satisfaction (reviews, NPS)
• Positioning and messaging
• What are they missing? (Your angle)
Document: 1-page competitive matrix

PHASE 3: MVP CONCEPT (Week 4-8)
Define minimum viable product
• Service packages (30-min, 1-hour sessions, packages)
• Delivery model (online, in-person, hybrid ratios)
• Tech stack (video platform, booking, payments)
• Build simple landing page (Webflow/Bubble)
Document: 1-page MVP spec

PHASE 4: PILOT TESTING (Week 8-16)
Validate with real paying customers
• Recruit 5-10 beta customers (discounted rate $50-75/session)
• Run for 4-6 weeks and gather feedback
• Measure: Customer satisfaction, retention, NPS
Acceptance Criteria: 80%+ would recommend

QUICK WINS (Can do today):
• Research state licensing requirements (2 hours)
• Brainstorm therapist recruitment strategy (1 hour)
• List 10 potential corporate wellness partners (1 hour)
• Evaluate 5 telehealth platforms (2 hours)

RESOURCES NEEDED:
• $5K: Legal review (licensing, compliance)
• $2K: Market research (surveys, interviews)
• $3K: Tech setup (landing page, basic tools)
• Your time: 10-15 hours/week for 8 weeks

ESTIMATED TIMELINE:
Week 1-4:   Market validation (parallel: Legal review)
Week 5-8:   Competitive analysis + MVP design
Week 9-16:  Pilot with beta customers
Month 5:    Go/no-go decision point

───────────────────────────────────────────────────────────────────

📈 SIMILAR OPPORTUNITIES - PROOF OF CONCEPT

1. BetterHelp (Online Mental Health Platform)
   Founded: 2013
   Status: Public (AACQ), $1.2B+ revenue (2024)
   Model: Pure Online Therapy
   Key Success: Low friction, mobile-first, affordable ($65-90/week)
   What they did right: Scale, brand recognition, insurance accepted
   Relevance: Proves the market and model work at scale

2. Ginger (Telehealth + Coaching)
   Founded: 2015
   Status: Private, $170M raised (Series C)
   Model: Online therapy + behavioral coaching
   Key Success: B2B corporate partnerships (high LTV per client)
   What they did right: Focus on ROI for employers, retention

3. Headspace (Meditation + Mental Wellness)
   Founded: 2010
   Status: Unicorn, $3B valuation (2021)
   Model: Online subscription (app + content library)
   Key Success: Product-first (not therapists), highly scalable
   What they did right: Content library, habit formation, UX

4. TherapyWorks (Hybrid - Local Clinics + Telehealth)
   Founded: 2008
   Status: Local chains in 15 US states
   Model: 40% in-person, 60% online (YOUR EXACT MODEL!)
   Key Success: Local brand trust + telehealth scale
   What they did right: Community integration, operational efficiency

5. Talkspace (Asynchronous Therapy + Live Sessions)
   Founded: 2012
   Status: Public (TALK)
   Model: Text + video therapy (lower therapist cost structure)
   Key Success: Unique async model reduced operating costs
   What to learn: Licensing and compliance are critical

KEY PATTERNS:
✓ All founded 2008-2015 (market existed then)
✓ All heavily funded ($50M-$300M+)
✓ All scaled to national/global presence
✓ All focus on either scale (pure online) or corporate B2B
✓ Telehealth adoption accelerated post-COVID (2020+)

DIFFERENTIATION OPPORTUNITY:
These players are either:
• National/global scale (impersonal, commoditized)
• Corporate-focused (high LTV but B2B sales cycle)

Your angle could be:
• LOCAL + PERSONAL (community-focused, word-of-mouth)
• SPECIALIZED (e.g., therapists for startups, new parents, etc.)
• HYBRID (avoiding pure online commoditization)

───────────────────────────────────────────────────────────────────

═══════════════════════════════════════════════════════════════════

DISCLAIMERS & DATA SOURCES

This report is generated by OppGrid's AI analysis engine and should
not be considered professional business advice. The assessments are
based on publicly available data, industry trends, and historical
patterns—not proprietary or confidential information.

Always consult with legal, financial, and industry experts before
making business decisions.

DATA SOURCES:
• Market sizing: IBISWorld, Statista, market research databases
• Competitive data: Public company filings, press releases, websites
• Financial benchmarks: SBA Small Business Resources, Stripe Atlas
• Trend data: Google Trends, industry reports, news sources
• Your idea text: Analyzed by Claude AI (multi-token analysis)

REPORT METADATA:
Generated by: OppGrid Consultant Studio
Generation time: March 31, 2026 at 10:45 PM PT
Analysis duration: 47 seconds
API calls: DeepSeek (pattern analysis) + Claude (report generation)
Data freshness: 2025 (market), real-time (some signals)

CONTACT & SUPPORT:
Questions about this report? Contact: support@oppgrid.ai
Need expert consultation? Book a consultant: /experts/booking
Want to iterate? Save and share this report: /reports/view/001

═══════════════════════════════════════════════════════════════════
```

---

## 8. IMPLEMENTATION CHECKLIST

### Backend Implementation
- [ ] Create `ReportDesignFormatter` service to format data into sections
- [ ] Implement `ValidateIdeaResponse` with all 6 sections filled
- [ ] Add `report_design_service.py` to generate section-by-section content
- [ ] Create PDF generation templates using ReportLab or weasyprint
- [ ] Test with sample ideas (mental health clinic, SaaS, etc.)

### Frontend Implementation
- [ ] Create `ReportViewer.tsx` component with all 6 sections
- [ ] Add CSS styling to match design system (colors, fonts, spacing)
- [ ] Implement PDF export button
- [ ] Create print-friendly CSS
- [ ] Add section collapsing/expanding UI
- [ ] Test responsive layout on mobile

### Content Implementation
- [ ] Update `consultant_studio.py` to generate all 6 sections
- [ ] Create AI prompts for each section
- [ ] Add data fetching from `report_data_service.py`
- [ ] Implement similar opportunities lookup
- [ ] Add validation checks (all required fields present)

---

## 9. MAINTENANCE & UPDATES

**Review Cycle:** Quarterly
**Last Reviewed:** 2026-03-31
**Next Review:** 2026-06-30

**Changelog:**
- v1.0 (2026-03-31): Initial specification document created

---

**Document Status:** ✅ READY FOR IMPLEMENTATION

**Questions?** Open an issue in GitHub or contact the team.
