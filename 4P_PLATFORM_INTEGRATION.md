# 4 P's Platform Integration Plan

> **Goal:** Use the ReportDataService 4 P's framework to power the entire platform, not just reports.

## Current State

### ✅ Already Built
- `ReportDataService` — Aggregates all 4 P's data (PRODUCT, PRICE, PLACE, PROMOTION)
- `WebEnrichmentService` — Live internet data (Trends, Places, Zillow, Indeed, News)
- `DataQuality` scoring — Completeness, confidence, recommendations
- Report generators — Wired to use full 4 P's context

### 🔴 Not Connected
| Component | Current Data | Missing |
|-----------|--------------|---------|
| **OpportunityCard** | Basic: score, market_size, growth_rate | No 4 P's mini-scores, no quality indicator |
| **OpportunityDetail** | AI fields + demographics (separate fetch) | Not unified via ReportDataService |
| **Workspace** | Basic opportunity info | No 4 P's context for AI copilot |
| **IdeaEngine** | Search results only | No 4 P's preview data |
| **ConsultantStudio** | Validates → Report | Could show live 4 P's while exploring |

---

## Integration Plan

### Phase 1: Backend API Layer (~2 hours)

**1.1 Create `/api/v1/opportunities/{id}/four-ps` endpoint**
```python
# Returns ReportDataContext for an opportunity
GET /api/v1/opportunities/{id}/four-ps
Response: {
  "product": { "score": 78, "pain_intensity": 8, "trend_strength": 0.85, ... },
  "price": { "market_size": "$50M-$200M", "median_income": 72000, ... },
  "place": { "growth_score": 82, "population_growth_rate": 2.3, ... },
  "promotion": { "competition_level": "medium", "competitive_advantages": [...], ... },
  "data_quality": { "completeness": 0.75, "confidence": 0.82, "weakest_pillar": "PRICE" },
  "summary": { "pillar_scores": { "product": 85, "price": 62, "place": 78, "promotion": 71 } }
}
```

**1.2 Create `/api/v1/opportunities/{id}/four-ps/mini` endpoint**
```python
# Lightweight version for cards (less data, faster)
GET /api/v1/opportunities/{id}/four-ps/mini
Response: {
  "scores": { "product": 85, "price": 62, "place": 78, "promotion": 71 },
  "overall": 74,
  "quality": 0.75,
  "top_insight": "Strong demand signals in growing market"
}
```

**1.3 Batch endpoint for card lists**
```python
POST /api/v1/opportunities/four-ps/batch
Body: { "ids": [1, 2, 3, 4, 5] }
Response: { "1": {...}, "2": {...}, ... }
```

---

### Phase 2: Frontend Components (~3 hours)

**2.1 Create `FourPsIndicator` component**
```tsx
// Mini 4-bar indicator for cards
<FourPsIndicator 
  scores={{ product: 85, price: 62, place: 78, promotion: 71 }}
  size="sm"
/>
// Shows 4 colored bars with hover tooltips
```

**2.2 Create `FourPsPanel` component**
```tsx
// Full panel for detail pages
<FourPsPanel 
  opportunityId={123}
  showQuality={true}
/>
// 4 expandable sections with all data
```

**2.3 Update OpportunityCard**
```tsx
// Add FourPsIndicator below existing metrics
<div className="grid grid-cols-3 gap-3 mb-4">
  {/* existing metrics */}
</div>
<FourPsIndicator scores={fourPsScores} size="sm" />
```

**2.4 Update OpportunityDetail**
- Replace separate demographics fetch with unified 4 P's call
- Add FourPsPanel as new tab or section
- Show data quality indicator

---

### Phase 3: Workspace Intelligence (~2 hours)

**3.1 Add 4 P's context to workspace**
```python
# When creating workspace, cache 4 P's context
POST /api/v1/workspaces
Body: { opportunity_id: 123, cache_four_ps: true }
```

**3.2 Wire AI Copilot to 4 P's**
```python
# Copilot gets 4 P's context in system prompt
def get_copilot_context(workspace_id):
    four_ps = get_four_ps_data(workspace.opportunity_id)
    return f"""
    ## Market Intelligence (4 P's)
    
    ### PRODUCT (Demand): Score {four_ps.product.score}/100
    - Pain Intensity: {four_ps.product.pain_intensity}/10
    - Trend: {four_ps.product.trend_direction}
    
    ### PRICE (Economics): Score {four_ps.price.score}/100
    - Market Size: {four_ps.price.market_size}
    - Median Income: ${four_ps.price.median_income:,}
    
    ...
    """
```

**3.3 Smart task suggestions**
- Suggest tasks based on weakest pillar
- "Your PRICE data is 45% complete. Consider: Research competitor pricing"

---

### Phase 4: IdeaEngine & Discovery (~1.5 hours)

**4.1 Add 4 P's to search results**
- Batch fetch mini scores for search results
- Sort/filter by individual P scores

**4.2 ConsultantStudio live preview**
- As user explores ideas, show live 4 P's mini panel
- Before generating full report, show what data exists

---

## File Changes Summary

| File | Change |
|------|--------|
| `backend/app/routers/opportunities.py` | Add `/four-ps`, `/four-ps/mini`, batch endpoint |
| `backend/app/services/report_data_service.py` | Add `get_mini_scores()`, `get_pillar_score()` methods |
| `frontend/src/components/FourPs/FourPsIndicator.tsx` | NEW — Mini 4-bar component |
| `frontend/src/components/FourPs/FourPsPanel.tsx` | NEW — Full expandable panel |
| `frontend/src/components/FourPs/index.ts` | NEW — Exports |
| `frontend/src/components/Discovery/OpportunityCard.tsx` | Add FourPsIndicator |
| `frontend/src/pages/OpportunityDetail.tsx` | Replace demographics with unified 4 P's |
| `frontend/src/pages/Workspace.tsx` | Add 4 P's context panel |
| `backend/app/routers/enhanced_workspaces.py` | Wire 4 P's to copilot |

---

## Priority Order

1. ✅ **Backend API** — Foundation for everything else
2. ✅ **OpportunityDetail** — Highest impact, most visible
3. ✅ **OpportunityCard** — Differentiates every card
4. **Workspace** — Makes AI copilot smarter
5. **IdeaEngine** — Search/discovery improvements

---

## Estimated Time

| Phase | Time | Status |
|-------|------|--------|
| Phase 1: Backend API | 2 hours | ✅ DONE |
| Phase 2: Frontend Components | 3 hours | ✅ DONE |
| Phase 3: Workspace Intelligence | 2 hours | 🔲 Next |
| Phase 4: IdeaEngine & Discovery | 1.5 hours | 🔲 Pending |
| **Total** | **~8.5 hours** | **~5h done** |

---

*Created 2026-03-31*
