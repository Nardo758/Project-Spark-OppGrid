# OppGrid Plumbing Fix Plan

## Problem Statement

The Dataset marketplace has **fake previews** and **silent mock fallbacks** on CSV downloads. The Hub tables that power datasets are **stale** (one-time backfill, never refreshed). The task scheduler is **in-process only** (dies on app restart). The expert marketplace has **synthetic profiles**.

## P0: Fix Dataset Deception (Priority: URGENT)

### 1. Fix Dataset Preview Endpoint
**File:** `backend/app/routers/datasets_api.py`
**Current:** `preview_dataset()` calls `_generate_mock_*()` for every dataset type
**Fix:** Query real Hub tables instead

```python
# BEFORE (fake):
if dt == DatasetType.OPPORTUNITIES:
    rows = delivery._generate_mock_opportunities(dataset)

# AFTER (real):
if dt == DatasetType.OPPORTUNITIES:
    rows = delivery.query_opportunities_for_preview(dataset, db)
```

### 2. Remove Mock Fallback in CSV Generation
**File:** `backend/app/services/dataset_delivery_service.py`
**Current:** `generate_csv_file()` falls back to `_export_mock_*()` silently
**Fix:** Return `None, 0` if no real data, let endpoint return 422

```python
# BEFORE:
if not real_data:
    logger.warning("No data, generating mock")
    return _export_mock_raw_data(dataset)

# AFTER:
if not real_data:
    return None, 0  # Let caller handle
```

### 3. Add "Last Updated" Timestamp to Dataset Response
**File:** `backend/app/routers/datasets_api.py`
**Add:** `last_updated` field to dataset detail response (max of Hub table updated_at)

### 4. Update Dataset List to Show Data Freshness
**File:** `frontend/src/components/marketplace/DatasetsTab.tsx`
**Add:** Show "Updated X hours ago" badge on each dataset card

## P1: Connect the Pipeline (Priority: HIGH)

### 5. Auto-Refresh Hub Tables on New Opportunity
**File:** `backend/app/services/opportunity_processor.py` or `signal_to_opportunity.py`
**Add:** After creating an opportunity, trigger Hub update for that city/category

```python
# After db.commit() in opportunity creation:
from app.scripts.populate_hub_tables import update_hub_for_opportunity
update_hub_for_opportunity(opp.id, db)
```

### 6. Make populate_hub_tables.py Incremental
**File:** `backend/scripts/populate_hub_tables.py`
**Current:** Skips tables with existing rows
**Fix:** Accept `--incremental` flag, update changed rows, append new ones

### 7. Add Hub Refresh API Endpoint
**File:** `backend/app/routers/datasets_api.py` (or new admin router)
**Add:** `POST /api/v1/admin/hub/refresh` — triggers incremental Hub refresh (admin only)

## P1: Build Scheduler (Priority: HIGH)

### 8. Replace In-Process Scheduler with Celery/Redis
**Current:** `APScheduler.BackgroundScheduler` in `google_scraper_scheduler.py`
**Options:**
- **Option A:** Celery + Redis (most robust, but requires Redis deployment)
- **Option B:** Simple cron job that hits a refresh endpoint (easiest for Replit)
- **Option C:** Inngest (already used in jedi_re, has cron support)

**Recommendation:** Option B for Replit — a simple script that runs `curl` to hit a refresh endpoint on a schedule.

### 9. Schedule Daily Hub Refresh
**Add:** Cron job or scheduled task that runs `populate_hub_tables.py --incremental` daily

### 10. Schedule Weekly Full Refresh
**Add:** Weekly deep refresh that recalculates all AI scores and TAM/SAM/SOM

## P2: Fix Expert Marketplace (Priority: MEDIUM)

### 11. Mark Fake Profiles as Demo
**File:** `backend/scripts/seed_experts.py` or `backend/app/routers/expert_collaboration.py`
**Add:** `is_demo=True` flag to sample profiles, filter them out of production marketplace

### 12. Fix Expert Application Flow
**Verify:** `POST /api/v1/expert-network/apply` actually creates a profile and notifies admin

## P2: Build Market Signals (Priority: MEDIUM — after plumbing)

### 13. Build Real Market Signals on Hub Data
**Once Hub tables are auto-refreshing:**
- Query `HubMarketByGeography` for business density changes
- Query `HubOpportunityEnriched` for sector momentum
- Query `HubIndustryInsight` for market size trends
- Generate weekly "Market Pulse" report

## Execution Order

```
Day 1 (P0):
1. Fix dataset preview (query real tables)
2. Remove mock fallback in CSV generation
3. Add last_updated timestamp
4. Test end-to-end with real data

Day 2 (P1):
5. Auto-refresh Hub on new opportunity
6. Make populate_hub_tables incremental
7. Add Hub refresh API endpoint
8. Build simple cron/scheduler

Day 3 (P1):
9. Schedule daily Hub refresh
10. Test full pipeline end-to-end
11. Deploy and verify on Replit

Day 4 (P2):
12. Fix expert marketplace demo flag
13. Start Market Signals design (with real data)
```

## Files to Edit

| File | Change | Priority |
|------|--------|----------|
| `backend/app/routers/datasets_api.py` | Fix preview, add timestamps | P0 |
| `backend/app/services/dataset_delivery_service.py` | Remove mock fallback | P0 |
| `backend/app/services/opportunity_processor.py` | Trigger Hub refresh | P1 |
| `backend/scripts/populate_hub_tables.py` | Make incremental | P1 |
| `backend/app/routers/expert_collaboration.py` | Demo flag for experts | P2 |
| `frontend/src/components/marketplace/DatasetsTab.tsx` | Show freshness badge | P0 |
| `backend/app/main.py` | Add scheduler or cron endpoint | P1 |

## Success Criteria

- [ ] Dataset preview shows real rows from Hub tables (not mock data)
- [ ] Dataset CSV download fails with 422 if no data (not silent mock)
- [ ] Each dataset shows "Last Updated: X hours ago"
- [ ] New opportunities automatically flow into Hub tables within 1 hour
- [ ] Hub tables refresh daily without manual intervention
- [ ] Expert marketplace clearly distinguishes demo vs. real profiles
- [ ] Market Signals are built on real, fresh data
