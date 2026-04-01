# Payment Gating & Report Allocation - Implementation Status

**Date:** April 1, 2026  
**Status:** ✅ **Phase 1 COMPLETE** | ⏳ Phase 2 & 3 TODO  
**Owner:** Leon D

---

## 📋 New Payment Model (Finalized)

### User Types & Access

```
┌──────────────────────────────────────────────────────────────┐
│ NON-MEMBERS (Not Signed Up)                                  │
│ ❌ CANNOT generate reports                                   │
│ 📌 "Must sign up to generate reports" message               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ FREE MEMBERS (Signed Up, No Subscription)                    │
│ 💰 Pay-per-report (no allocation)                            │
│ • Layer 1: $15 per report                                   │
│ • Layer 2: $25 per report                                   │
│ • Layer 3: $35 per report                                   │
│ ✓ Full Consultant Studio access (Validate Idea, etc.)       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ PRO MEMBERS ($99/month)                                      │
│ 📌 Monthly Allocation:                                       │
│ • Layer 1: 5 free reports/month                             │
│ • Layer 2: 2 free reports/month                             │
│ • Layer 3: 0 (must purchase)                                │
│ 💰 Overage Pricing (33% discount):                           │
│ • Layer 1: $10 per additional                               │
│ • Layer 2: $18 per additional                               │
│ • Layer 3: $25 per additional                               │
│ ✓ Full Consultant Studio access                             │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ BUSINESS MEMBERS ($299/month)                                │
│ 📌 Monthly Allocation:                                       │
│ • Layer 1: 15 free reports/month                            │
│ • Layer 2: 8 free reports/month                             │
│ • Layer 3: 3 free reports/month                             │
│ 💰 Overage Pricing (47% discount):                           │
│ • Layer 1: $8 per additional                                │
│ • Layer 2: $15 per additional                               │
│ • Layer 3: $20 per additional                               │
│ ✓ Full Consultant Studio access                             │
│ ✓ Priority support                                          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ ENTERPRISE MEMBERS (Custom)                                  │
│ 📌 Monthly Allocation:                                       │
│ • Layer 1: 50 free reports/month                            │
│ • Layer 2: 25 free reports/month                            │
│ • Layer 3: 10 free reports/month                            │
│ 💰 Overage Pricing (66% discount):                           │
│ • Layer 1: $5 per additional                                │
│ • Layer 2: $10 per additional                               │
│ • Layer 3: $15 per additional                               │
│ ✓ Full Consultant Studio access                             │
│ ✓ Dedicated support                                         │
│ ✓ Custom integrations                                       │
└──────────────────────────────────────────────────────────────┘
```

### Key Rules

1. **Authentication Required First**
   - Non-members cannot purchase at all
   - Must sign up before accessing any report features
   - Error: "Must sign up to generate reports"

2. **Quota-Based for Members**
   - Free members: No quota (always pay)
   - Paid members: Monthly allocation + overage pricing
   - Quota resets on billing date each month

3. **Automatic Enforcement**
   - Check user tier before generating report
   - Check remaining quota automatically
   - Charge immediately if quota exhausted (for paid members) or free member

---

## 🔧 Implementation Status

### ✅ PHASE 1: Backend Models & Service (COMPLETE)

**Files Created:**

1. **`app/models/user_report_quota.py`** ✅
   - `UserReportQuota` model: Stores monthly allocation/usage per user+tier
   - `ReportPurchaseLog` model: Audit trail for all purchases
   - Timestamps, composite unique constraints, helper methods

2. **`app/services/report_quota_service.py`** ✅
   - Full quota management logic
   - Pricing calculation (free vs overage)
   - Quota tracking and decrement
   - Usage summary generation

3. **`app/models/user.py`** ✅ (Updated)
   - Added `report_quotas` relationship

**Key Methods in ReportQuotaService:**
```python
# Check if user can generate for free
can_generate_free(user, report_tier) → bool

# Get price for this user (0 if free, $ amount if overage)
get_price_for_user(user, report_tier) → int (cents)

# Check access and get message + price
check_access(user, report_tier) → (bool, str, int)

# Decrement quota when report generated
decrement_quota(user, report_tier) → bool

# Get usage summary
get_usage_summary(user) → Dict[str, Dict]

# Log purchase for auditing
log_purchase(user, tier, payment_type, amount_cents, stripe_id) → Log
```

---

### ⏳ PHASE 2: Wire Into Report Endpoints (TODO - HIGH PRIORITY)

**Files to Update:**

1. **`app/routers/generated_reports.py`** 
   - Update `generate_layer1_report()` endpoint:
     ```python
     @router.post("/layer1/{opportunity_id}")
     async def generate_layer1_report(
         opportunity_id: int,
         current_user: User = Depends(get_current_user),  # ← ADD: Auth guard
         db: Session = Depends(get_db),
     ):
         # 1. Check: Is user logged in?
         if not current_user:
             raise HTTPException(403, "Must sign up to generate reports")
         
         # 2. Check quota and pricing
         quota_service = ReportQuotaService(db)
         can_generate, message, price_cents = quota_service.check_access(
             current_user, "layer_1"
         )
         
         if not can_generate:
             raise HTTPException(403, message)
         
         # 3. If price > 0 and not yet charged, initiate Stripe charge
         if price_cents > 0:
             # TODO: Charge via Stripe
             charge_result = stripe_charge_payment(current_user, price_cents)
             if not charge_result["success"]:
                 raise HTTPException(402, "Payment failed")
         
         # 4. Generate report
         generator = ReportGenerator(db)
         report = generator.generate_layer1_report(...)
         
         # 5. Decrement quota if free
         if price_cents == 0:
             quota_service.decrement_quota(current_user, "layer_1")
         
         # 6. Log purchase
         quota_service.log_purchase(
             current_user,
             "layer_1",
             payment_type="quota" if price_cents == 0 else "stripe",
             amount_cents=price_cents,
             stripe_charge_id=charge_result.get("charge_id"),
             report_id=report.id,
         )
         
         return {success: True, report_id: report.id, ...}
     ```
   
   - Same pattern for `generate_layer2_report()` and `generate_layer3_report()`

2. **`app/routers/consultant.py`**
   - Update `validate_idea()` endpoint (Consultant Studio analysis):
     ```python
     # Add auth guard - non-members blocked
     if not user_id or not db.query(User).get(user_id):
         return {"success": False, "requires_auth": True}
     ```

---

### ⏳ PHASE 3: Frontend Display (TODO - MEDIUM PRIORITY)

**Files to Update:**

1. **`src/components/ReportGenerationButton.tsx`** (new)
   ```tsx
   interface ReportGenerationButtonProps {
     opportunityId: number
     reportTier: "layer_1" | "layer_2" | "layer_3"
     isLoggedIn: boolean
     userTier: "free" | "pro" | "business" | "enterprise"
     remainingQuota: number
     isQuotaExhausted: boolean
     price: number  // in cents (0 if free from quota)
     onGenerate: () => void
   }
   
   export default function ReportGenerationButton({...}) {
     if (!isLoggedIn) {
       return <SignUpButton text="Sign up to generate reports" />
     }
     
     if (isQuotaExhausted) {
       return (
         <Button onClick={onGenerate} variant="primary">
           Generate for ${price / 100} (quota exhausted)
         </Button>
       )
     }
     
     return (
       <Button onClick={onGenerate} variant="success">
         Generate free ({remainingQuota} remaining this month)
       </Button>
     )
   }
   ```

2. **`src/pages/build/ConsultantStudio.tsx`**
   - Replace hard-coded report generation with:
     ```tsx
     {/* In the report generation section */}
     {!isLoggedIn && (
       <div className="alert alert-info">
         Sign up to access report generation features
       </div>
     )}
     
     {isLoggedIn && (
       <ReportGenerationButton
         opportunityId={opportunityId}
         reportTier={selectedTier}
         userTier={userSubscriptionTier}
         remainingQuota={quotaSummary[selectedTier].remaining}
         price={quotaService.get_price_for_user(...)}
       />
     )}
     ```

3. **`src/pages/Dashboard.tsx`** (Quota display)
   - Add quota widget:
     ```tsx
     <div className="quota-summary">
       <h3>Monthly Report Quota</h3>
       Layer 1: 3/5 remaining ({remaining}%)
       Layer 2: 1/2 remaining ({remaining}%)
       Layer 3: 0/0 (purchase to use)
       
       <p className="reset-info">Resets: Apr 15, 2026</p>
     </div>
     ```

---

## 📊 Database Schema

### UserReportQuota Table
```sql
CREATE TABLE user_report_quotas (
  id INT PRIMARY KEY,
  user_id INT NOT NULL,
  report_tier VARCHAR(20) NOT NULL,  -- layer_1, layer_2, layer_3
  allocated INT DEFAULT 0,           -- 5/2/0 for Pro, 15/8/3 for Business, etc.
  used INT DEFAULT 0,                -- Number generated this month
  reset_date DATETIME NOT NULL,      -- When quota resets
  subscription_tier VARCHAR(50),     -- free, pro, business, enterprise
  created_at DATETIME DEFAULT NOW,
  updated_at DATETIME DEFAULT NOW,
  
  UNIQUE(user_id, report_tier, reset_date)
)

CREATE TABLE report_purchase_logs (
  id INT PRIMARY KEY,
  user_id INT NOT NULL,
  opportunity_id INT,
  report_tier VARCHAR(20) NOT NULL,
  payment_type VARCHAR(20) NOT NULL, -- quota, stripe, free
  amount_cents INT DEFAULT 0,
  stripe_charge_id VARCHAR(255),
  report_id INT,
  created_at DATETIME DEFAULT NOW
)
```

---

## 🚀 Implementation Order

### Priority 1 (CRITICAL)
1. ✅ Models & service layer (DONE)
2. Wire into report generation endpoints
3. Add auth guards (non-member check)
4. Integrate Stripe for overage charges

### Priority 2 (HIGH)
5. Frontend button updates
6. Quota display in dashboard
7. Payment confirmation flow

### Priority 3 (MEDIUM)
8. Analytics dashboard for purchases
9. Quota reset automation (cron job)
10. Usage notifications

---

## 🧪 Testing Checklist

- [ ] Non-member tries to generate report → sees "Sign up" error
- [ ] Free member generates report → charged $15, report created
- [ ] Pro member with quota generates → free (quota decremented)
- [ ] Pro member quota exhausted → charged $10 (overage)
- [ ] Business member with allocation → generates free
- [ ] Quota resets on billing date → allocation replenished
- [ ] Purchase log tracks all transactions
- [ ] Stripe charges succeed/fail properly
- [ ] Frontend displays correct buttons for each tier
- [ ] Dashboard shows quota usage

---

## 📝 Summary

**What's Done:**
✅ Payment model designed and finalized with Leon
✅ Database models created (UserReportQuota, ReportPurchaseLog)
✅ Core service logic implemented (ReportQuotaService)
✅ Pricing tiers and allocations defined

**What's Next:**
⏳ Wire service into report generation endpoints (2-3 hours)
⏳ Integrate Stripe payments for overages (1-2 hours)
⏳ Update frontend to display quota/pricing (2-3 hours)
⏳ Quota reset automation with cron jobs (1 hour)

**Total Remaining: 6-9 hours of development**
