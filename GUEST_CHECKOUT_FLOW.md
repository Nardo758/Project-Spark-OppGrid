# Guest Checkout Flow - Option A Implementation

**Date:** April 1, 2026  
**Status:** ✅ Backend updated  
**Model:** No sign-up friction, auto-account creation at payment

---

## 🎯 Updated Payment Model

### User Journey

```
GUEST (No Account)
    ↓
    Clicks "Generate Report" (any tier)
    ↓
    Sees: "Generate Layer 1 Report for $15" (no login required)
    ↓
    Clicks "Generate for $15"
    ↓
    Stripe Checkout Modal
    • Email field (guest_email captured)
    • Card payment
    ↓
    Payment Successful
    ↓
    Account auto-created with that email
    ↓
    Report delivered to inbox
    ↓
    Email: "Your report is ready! Click here to login with [email]"
    ↓
    Guest can now login, access dashboard, see quota, etc.
```

### Payment Tiers

| User Type | Can Buy? | Pricing | Notes |
|-----------|----------|---------|-------|
| **Guest** | ✅ YES | $15/$25/$35 | No account needed |
| **Free Member** | ✅ YES | $15/$25/$35 | Always pays full price |
| **Pro Member** | ✅ YES | 5/2/0 free + $10/$18/$25 overage | Monthly allocation |
| **Business Member** | ✅ YES | 15/8/3 free + $8/$15/$20 overage | Monthly allocation |

**Key:** Everyone can generate reports. Guests and free members always pay full price. Paid members get monthly allocation.

---

## 🔧 Backend Implementation

### Database Changes

**ReportPurchaseLog** (Updated)
```python
class ReportPurchaseLog(Base):
    user_id: Optional[int]          # Null for guest purchases
    guest_email: Optional[str]      # "john@example.com" for guests
    report_tier: str                # "layer_1", "layer_2", "layer_3"
    payment_type: str               # "stripe" for all paid
    amount_cents: int               # 1500, 2500, 3500
    stripe_charge_id: str           # Stripe transaction ID
    guest_converted_to_user_id: int # User ID if guest later signed in
```

### Service Logic

**ReportQuotaService.check_access()**
```python
# Guest (no user object)
can_generate, message, price = quota_service.check_access(None, "layer_1")
# → True, "Generate report for $15", 1500

# Free member
can_generate, message, price = quota_service.check_access(free_user, "layer_1")
# → True, "Generate report for $15", 1500

# Pro member with quota
can_generate, message, price = quota_service.check_access(pro_user, "layer_1")
# → True, "Generate free (4/5 remaining)", 0

# Pro member, quota exhausted
can_generate, message, price = quota_service.check_access(pro_user, "layer_1")
# → True, "Generate report for $10 (quota exhausted)", 1000
```

---

## 🏗️ Endpoint Flow (When Integrated)

### POST /api/v1/reports/layer1/generate

```python
@router.post("/layer1/generate")
async def generate_layer1(
    request: GenerateReportRequest,
    current_user: Optional[User] = None,  # Can be None (guest)
    db: Session = Depends(get_db),
):
    """Generate a report. Guests can buy without account."""
    
    # 1. Check access (guest or member)
    quota_service = ReportQuotaService(db)
    can_gen, msg, price = quota_service.check_access(current_user, "layer_1")
    
    if not can_gen:
        return {"success": False, "error": msg}
    
    # 2. If price > 0, need payment
    if price > 0:
        return {
            "success": False,
            "requires_payment": True,
            "price_cents": price,
            "message": f"This report costs ${price/100:.2f}",
            "stripe_checkout_url": "/checkout?tier=layer_1&guest_email={guest_email}"
        }
    
    # 3. Generate report (quota available for free)
    report = generator.generate_layer1_report(...)
    
    # 4. Decrement quota if member
    if current_user and price == 0:
        quota_service.decrement_quota(current_user, "layer_1")
    
    # 5. Log purchase
    quota_service.log_purchase(
        report_tier="layer_1",
        amount_cents=price,
        user=current_user,
        guest_email=request.guest_email if not current_user else None,
        payment_type="stripe" if price > 0 else "quota"
    )
    
    return {"success": True, "report_id": report.id}
```

### POST /checkout (Stripe Handler)

```python
@router.post("/checkout")
async def create_checkout_session(
    guest_email: str,          # From guest (no account)
    report_tier: str,          # layer_1, layer_2, layer_3
    opportunity_id: int,
    db: Session = Depends(get_db),
):
    """
    Create Stripe checkout for guest or member.
    On success, auto-create account for guest.
    """
    
    # Determine price
    prices = {"layer_1": 1500, "layer_2": 2500, "layer_3": 3500}
    price_cents = prices[report_tier]
    
    # Create Stripe checkout session
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"OppGrid {report_tier.replace('_', ' ').title()} Report"
                },
                "unit_amount": price_cents,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=f"https://oppgrid.app/checkout-success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"https://oppgrid.app/reports",
        customer_email=guest_email,  # Pre-fill email
        metadata={
            "guest_email": guest_email,
            "report_tier": report_tier,
            "opportunity_id": opportunity_id,
        },
    )
    
    return {"checkout_url": session.url}
```

### Stripe Webhook Handler

```python
@router.post("/webhook/checkout-completed")
async def checkout_completed(event: dict, db: Session = Depends(get_db)):
    """
    Stripe payment success.
    1. Create account for guest if needed
    2. Generate report
    3. Send to email
    4. Log purchase
    """
    session = event["data"]["object"]
    guest_email = session["metadata"]["guest_email"]
    report_tier = session["metadata"]["report_tier"]
    opportunity_id = session["metadata"]["opportunity_id"]
    stripe_charge_id = session["payment_intent"]
    
    # 1. Find or create user
    user = db.query(User).filter(User.email == guest_email).first()
    if not user:
        # Auto-create account for guest
        user = User(
            email=guest_email,
            name=guest_email.split("@")[0],  # Use email prefix as name
            hashed_password=None,  # No password yet (email login only)
            is_verified=True,  # Auto-verify since they paid
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Auto-created account for guest: {guest_email}")
    
    # 2. Generate report
    generator = ReportGenerator(db)
    report = generator.generate_layer1_report(...)
    
    # 3. Send report to email
    send_report_email(
        to=guest_email,
        report_id=report.id,
        tier=report_tier,
    )
    
    # 4. Log purchase
    quota_service = ReportQuotaService(db)
    quota_service.log_purchase(
        report_tier=report_tier,
        payment_type="stripe",
        amount_cents=session["amount_total"],
        stripe_charge_id=stripe_charge_id,
        user=user,
        report_id=report.id,
        opportunity_id=opportunity_id,
    )
    
    logger.info(f"Completed guest checkout: {guest_email} → {report_tier}")
    
    return {"success": True}
```

---

## 📊 User Journeys by Type

### Journey 1: Guest → One-Time Purchase

```
1. Guest: Click "Generate Layer 1 Report for $15"
2. Frontend: No login prompt, show price
3. Guest: Click "Proceed to Payment"
4. Stripe: Checkout with guest_email field
5. Guest: Pay with card
6. Webhook: Account auto-created, report generated
7. Email: "Your report is ready! Login: [email] (first time login)"
8. Guest: Receives report, can create password and login
9. Database: Purchase logged with guest_email → new user_id
```

### Journey 2: Free Member → Paid Report

```
1. Free Member: Logged in, click "Generate Layer 1 for $15"
2. Frontend: Show "Generate for $15" (member pricing)
3. Member: Click "Generate"
4. Stripe: Quick checkout (saved card or new)
5. Report: Generated immediately
6. Database: Purchase logged with user_id, amount=$15
7. Dashboard: Report appears in user's account
```

### Journey 3: Pro Member → Free Report (Quota Available)

```
1. Pro Member: Logged in, click "Generate Layer 1"
2. Frontend: Show "Generate free (4/5 remaining)"
3. Member: Click "Generate"
4. Backend: Check quota → has 4 remaining
5. Report: Generated immediately (no charge)
6. Database: Quota decremented (4 → 3)
7. Dashboard: Report appears, quota updated
```

### Journey 4: Pro Member → Overage Purchase

```
1. Pro Member: Logged in, quota exhausted (0/5)
2. Frontend: Show "Generate for $10 (quota exhausted)"
3. Member: Click "Generate"
4. Stripe: Quick checkout
5. Report: Generated immediately
6. Database: Purchase logged as overage ($10), quota stays at 0
7. Dashboard: Report appears, overage tracked
```

---

## ✅ Implementation Checklist

### Phase 2: Wire into Endpoints (TODO)
- [ ] Update `POST /api/v1/reports/layer1/generate`
- [ ] Update `POST /api/v1/reports/layer2/generate`
- [ ] Update `POST /api/v1/reports/layer3/generate`
- [ ] Create `POST /checkout` endpoint
- [ ] Create Stripe webhook handler
- [ ] Auto-account creation logic
- [ ] Email delivery on checkout success

### Phase 3: Frontend (TODO)
- [ ] "Generate for $X" button (works without login)
- [ ] Stripe checkout modal (captures guest_email)
- [ ] Success page after payment
- [ ] Account confirmation email
- [ ] First-time login flow

### Phase 4: Polish (TODO)
- [ ] Resend report email if needed
- [ ] Abandoned checkout recovery
- [ ] Guest email validation
- [ ] Account linking if guest logs in later with same email
- [ ] Analytics dashboard for guest conversions

---

## 🎁 Conversion Benefits

- **No friction:** Guests buy immediately without signup
- **Lower cart abandonment:** ~50% reduction from signup requirement
- **Account creation:** Automatically get accounts, better retention
- **Email list:** Capture guest emails at payment
- **Upsell opportunity:** After first purchase, offer subscription

---

## Summary

✅ **What's Done:**
- Quota service supports guests (returns full pricing)
- ReportPurchaseLog tracks guest_email
- Auto-account creation logic defined

⏳ **What's Next:**
- Wire service into endpoints (2-3 hours)
- Stripe checkout + webhook (2 hours)
- Frontend buttons & flow (1-2 hours)

🚀 **Result:** Zero-friction guest checkout with automatic account creation.
