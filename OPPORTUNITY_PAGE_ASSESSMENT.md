# Opportunity Detail Page Assessment

## Current Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ HEADER                                                          │
│ Title, Score (59), Category, Unlock button                      │
├─────────────────────────────────────────────────────────────────┤
│ PROBLEM STATEMENT (violet box)                    [FREE]        │
│ + Insight badges (pain, trend, market, competition)             │
├─────────────────────────────────────────────────────────────────┤
│ PROBLEM DETAIL                                    [FREE]        │
│ - Geographic Market selector                                    │
│ - Market Size, Signals, Growth stats                            │
│ - Quick Validation Metrics (Urgency, Competition, Target, Feas) │
│ - Top Pain Points                                               │
├─────────────────────────────────────────────────────────────────┤
│ RESEARCH DASHBOARD (Tabs)                         [PRO/LOCKED]  │
│ - Market Validation tab                                         │
│ - Geographic tab                                                │
│ - Problem Analysis tab                                          │
│ - Market Sizing tab                                             │
│ - Solution Pathways tab                                         │
├─────────────────────────────────────────────────────────────────┤
│ TOOLS (new)                                       [FREE]        │
│ Validate | Report | Clone | WorkHub                             │
├─────────────────────────────────────────────────────────────────┤
│ EXPERTS                                           [FREE preview]│
│ Top 3 experts + Search link                                     │
├─────────────────────────────────────────────────────────────────┤
│ CTA: Deep Dive WorkHub                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Value Assessment: What's Worth Paying For?

### 🆓 FREE TIER (Hook them)

| Content | Why Free | Current State |
|---------|----------|---------------|
| **Problem Statement** | Hook - shows the opportunity | ✅ Good |
| **Insight Badges** | Teaser of data depth | ✅ Just added |
| **Basic Score** | Social proof | ✅ Good |
| **Category & Region** | Basic context | ✅ Good |
| **Validation Count** | Community signal | ✅ Good |
| **Pain Points (top 2)** | Taste of research | ⚠️ Shows all, limit to 2 |
| **Tools buttons** | Drive engagement | ✅ Just added |
| **Expert preview (3)** | Teaser of network | ✅ Just added |

**Free = "This is a real opportunity, here's proof. Want the details?"**

---

### 💰 PRO TIER ($15-29/mo) - Deep Research

| Content | Why Paid | Value |
|---------|----------|-------|
| **Full Demand Signals** | Real search volume, trend data | HIGH |
| **Competitive Analysis** | Actual competitor count, ratings, gaps | HIGH |
| **Solution Pathways** | Business model recommendations | MEDIUM |
| **Geographic Heatmap** | Where demand is concentrated | HIGH |
| **Market Sizing (TAM/SAM/SOM)** | Investment-grade numbers | HIGH |
| **All Pain Points** | Complete research | MEDIUM |
| **Key Risks** | Due diligence | MEDIUM |

**Pro = "Everything you need to validate and plan"**

---

### 💎 BUSINESS TIER ($49-99/mo) - Execution Intelligence

| Content | Why Premium | Value |
|---------|-------------|-------|
| **Census Demographics** | Real population, income, education | VERY HIGH |
| **Growth Scores** | Market trajectory data | VERY HIGH |
| **Job Market Data** | Economic health indicators | HIGH |
| **Purchasing Power Estimate** | Financial projections | VERY HIGH |
| **Expert Direct Contact** | Actually work with experts | VERY HIGH |
| **Full Reports** | Downloadable market analysis | HIGH |
| **Clone Success Data** | Proven business models | HIGH |

**Business = "Execute with confidence, real data for real decisions"**

---

## Recommended Paywall Structure

### FREE (No login required)

```
┌─────────────────────────────────────────┐
│ Problem Statement                       │
│ 🔥 Pain: 8/10  📈 Rising  💰 $800M+    │ ← Teaser badges
├─────────────────────────────────────────┤
│ Score: 59  |  412 signals  |  High Urg │
├─────────────────────────────────────────┤
│ Top 2 Pain Points                       │
│ "Finding reliable providers..."         │
│ "Pricing transparency..."              │
│ 🔒 +3 more pain points                  │ ← Locked hint
├─────────────────────────────────────────┤
│ 🔒 Research Dashboard                   │
│ "Unlock full market analysis"           │
│ [See what's inside] [Unlock $15]        │
├─────────────────────────────────────────┤
│ Tools: [Validate] [Report🔒] [Clone🔒]  │
├─────────────────────────────────────────┤
│ 👥 3 Experts matched                    │
│ [Search all →]                          │
└─────────────────────────────────────────┘
```

### PRO (Unlocked or $15 pay-per-unlock)

```
┌─────────────────────────────────────────┐
│ Everything in FREE +                    │
├─────────────────────────────────────────┤
│ ✅ Full Research Dashboard              │
│   - Demand Signals (real data)          │
│   - Competitive Landscape               │
│   - Solution Pathways                   │
│   - Market Sizing (TAM/SAM/SOM)         │
│   - All Pain Points + Risks             │
├─────────────────────────────────────────┤
│ ✅ Geographic Distribution Map          │
├─────────────────────────────────────────┤
│ 🔒 Demographics (Business only)         │
│ 🔒 Growth Scores (Business only)        │
├─────────────────────────────────────────┤
│ Tools: All unlocked                     │
└─────────────────────────────────────────┘
```

### BUSINESS ($49+/mo)

```
Everything in PRO +
✅ Census Demographics
✅ Growth Scores & Market Trajectory
✅ Job Market & Economic Data
✅ Purchasing Power Projections
✅ Expert Direct Messaging
✅ Downloadable Reports
✅ API Access
```

---

## Data Sources → Tier Mapping

| Data Source | Tier | Why |
|-------------|------|-----|
| AI Analysis (pain, urgency) | FREE (teaser) | Hook |
| Validation count | FREE | Social proof |
| Google Trends interest | PRO | Real demand data |
| Competitor count/ratings | PRO | Competitive intel |
| Business model suggestions | PRO | Actionable advice |
| Census population/income | BUSINESS | Premium data |
| Growth trajectories | BUSINESS | Investment-grade |
| Job market data | BUSINESS | Economic context |
| Web enrichment (Zillow, Indeed) | BUSINESS | Live data |

---

## Implementation Priority

1. **Fix placeholder data** - Replace hardcoded "127K/mo" with real data
2. **Gate correctly** - Some PRO content showing to FREE users
3. **Add lock hints** - "+3 more pain points 🔒" drives upgrades
4. **Show value preview** - Blurred/teaser of locked content
5. **Infuse real data** - Use `intel` object in all tabs

---

*Assessment created 2026-03-31*
