"""OppGrid Monthly launch: price mapping, entitlements, quota, and checkout."""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.database import get_db
from app.main import app
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTier
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User
from app.models.user_report_quota import UserReportQuota
from app.routers.consultant import _has_premium_deep_clone_access
from app.routers.stripe_webhook import _map_price_to_tier
from app.services.launch_entitlements import (
    DEEP_CLONE_CHECKOUT_PATH,
    DEEP_CLONE_PRICE_CENTS,
    MONTHLY_PRICE_CENTS,
    is_available_for_new_purchase,
    monthly_period_is_open,
    reject_monthly_alerts,
    stripe_price_id_for_tier,
    tier_unlocks_feature,
)
from app.services.report_quota_service import ReportQuotaService
from app.services.saved_search_alerts import should_send_alert
from app.services.stripe_service import StripeService, stripe_service

DEEP_CLONE_URL = "/api/v1/consultant/deep-clone"
CHECKOUT_URL = "/api/v1/subscriptions/checkout"
INTENT_URL = "/api/v1/subscriptions/subscription-intent"
DEEP_CLONE_BODY = {
    "source_business_name": "Acme Coffee",
    "source_business_address": "123 Main St, Austin, TX",
    "target_city": "Austin",
}
LEGACY_TIERS = ["starter", "growth", "pro", "team", "business", "enterprise"]
REPO_ROOT = Path(__file__).resolve().parents[2]
BUYER_PRICE_FILES = [
    "frontend/src/pages/Pricing.tsx",
    "frontend/src/pages/Signup.tsx",
    "frontend/src/components/UpgradeModal.tsx",
    "frontend/src/hooks/useInlinePayment.ts",
    "frontend/src/pages/StripeArchitecture.tsx",
    "frontend/src/pages/Home.tsx",
    "frontend/src/components/BlockMonthlyFeature.tsx",
]
FORBIDDEN_PRICE_PATTERNS = [
    re.compile(r"\$20(?!\d)"),
    re.compile(r"\$50(?!\d)"),
    re.compile(r"\$99(?!\d)"),
    re.compile(r"\$250(?!\d)"),
    re.compile(r"\$750(?!\d)"),
    re.compile(r"\$2,500"),
]


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    Subscription.__table__.create(engine)
    Transaction.__table__.create(engine)
    UserReportQuota.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _user(db, email: str) -> User:
    user = User(email=email, name=email.split("@")[0], is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth(user: User) -> dict:
    token = create_access_token(data={"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


def _analysis_result():
    return {
        "success": True,
        "target_city": "Austin",
        "match_score": 80,
        "key_factors": ["demand"],
    }


def _monthly_subscription(db, user: User, *, start: datetime, end: datetime, status=SubscriptionStatus.ACTIVE, cancel_at_period_end=False) -> Subscription:
    subscription = Subscription(
        user_id=user.id,
        tier=SubscriptionTier.MONTHLY,
        status=status,
        cancel_at_period_end=cancel_at_period_end,
        current_period_start=start,
        current_period_end=end,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def _post_report(client, user):
    with patch("app.routers.consultant.ConsultantStudioService") as service_cls:
        service_cls.return_value.deep_clone_analysis = AsyncMock(return_value=_analysis_result())
        response = client.post(DEEP_CLONE_URL, json=DEEP_CLONE_BODY, headers=_auth(user))
        called = service_cls.return_value.deep_clone_analysis.await_count
    return response, called


def test_monthly_maps_from_env_price_and_passes_premium(monkeypatch):
    monkeypatch.setenv("STRIPE_PRICE_MONTHLY", "price_test_monthly_from_env")
    assert _map_price_to_tier("price_test_monthly_from_env") == SubscriptionTier.MONTHLY
    assert stripe_price_id_for_tier(SubscriptionTier.MONTHLY) == "price_test_monthly_from_env"
    monkeypatch.delenv("STRIPE_PRICE_MONTHLY", raising=False)
    assert _map_price_to_tier("price_test_monthly_from_env") is None
    assert stripe_price_id_for_tier(SubscriptionTier.MONTHLY) is None

    assert _has_premium_deep_clone_access(SubscriptionTier.MONTHLY)
    assert _has_premium_deep_clone_access("monthly")
    assert tier_unlocks_feature(SubscriptionTier.MONTHLY, "premium")
    assert tier_unlocks_feature(SubscriptionTier.MONTHLY, "feed")
    assert stripe_service.can_access_opportunity_by_age(SubscriptionTier.MONTHLY, 0) is True

    config = StripeService.get_tier_config(SubscriptionTier.MONTHLY)
    limits = StripeService.get_tier_limits(SubscriptionTier.MONTHLY)
    assert config["name"] == "OppGrid Monthly"
    assert config["price"] == 39
    assert config["price_cents"] == MONTHLY_PRICE_CENTS == 3900
    assert limits["price_cents"] == 3900


def test_monthly_does_not_unlock_marketplace_workhub_datasets_or_alerts(db, client):
    locked = ("expert_marketplace", "workhub", "datasets", "alerts")
    for feature in locked:
        assert tier_unlocks_feature(SubscriptionTier.MONTHLY, feature) is False
        assert tier_unlocks_feature(SubscriptionTier.STARTER, feature) is True

    user = _user(db, "monthly-locked@example.com")
    now = datetime.now(timezone.utc)
    _monthly_subscription(
        db,
        user,
        start=now - timedelta(days=1),
        end=now + timedelta(days=20),
    )
    headers = _auth(user)

    experts = client.get("/api/v1/experts/", headers=headers)
    workhub = client.get("/api/v1/workhub/collections", headers=headers)
    datasets = client.get("/api/v1/datasets", headers=headers)
    for response, feature in (
        (experts, "expert marketplace"),
        (workhub, "workhub"),
        (datasets, "datasets"),
    ):
        assert response.status_code == 403
        assert feature in response.json()["detail"].lower()

    with pytest.raises(HTTPException) as exc:
        reject_monthly_alerts(db, user, {"email": True, "frequency": "daily"})
    assert exc.value.status_code == 403

    search = SimpleNamespace(
        user=SimpleNamespace(subscription=SimpleNamespace(tier=SubscriptionTier.MONTHLY)),
        notification_prefs={"email": True, "frequency": "daily"},
        last_notified_at=None,
    )
    assert should_send_alert(search) is False

    legacy = SimpleNamespace(
        user=SimpleNamespace(subscription=SimpleNamespace(tier=SubscriptionTier.STARTER)),
        notification_prefs={"email": True, "frequency": "daily"},
        last_notified_at=None,
    )
    assert should_send_alert(legacy) is True


def test_monthly_report_limit_resets_without_rollover(db, client):
    user = _user(db, "quota@example.com")
    now = datetime.now(timezone.utc)
    period_one_end = now + timedelta(days=5)
    subscription = _monthly_subscription(
        db,
        user,
        start=now - timedelta(days=20),
        end=period_one_end,
    )

    first, called = _post_report(client, user)
    assert first.status_code == 200
    assert first.json()["success"] is True
    assert called == 1

    period_two_end = now + timedelta(days=35)
    subscription.current_period_start = now - timedelta(minutes=1)
    subscription.current_period_end = period_two_end
    db.commit()

    for _ in range(2):
        response, called = _post_report(client, user)
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert called == 1

    third, called = _post_report(client, user)
    assert third.status_code == 200
    assert third.json()["success"] is False
    assert called == 0

    rows = db.query(UserReportQuota).filter(UserReportQuota.user_id == user.id).all()
    used_by_period = {row.reset_date.replace(microsecond=0): row.used for row in rows}
    service = ReportQuotaService(db)
    period_one_key = service.get_monthly_deep_clone_quota(user, period_one_end).reset_date
    period_two_key = service.get_monthly_deep_clone_quota(user, period_two_end).reset_date
    assert used_by_period[period_one_key.replace(tzinfo=None) if period_one_key.tzinfo else period_one_key] == 1
    assert used_by_period[period_two_key.replace(tzinfo=None) if period_two_key.tzinfo else period_two_key] == 2


def test_third_report_offers_49_dollar_deep_clone(db, client):
    user = _user(db, "third@example.com")
    now = datetime.now(timezone.utc)
    _monthly_subscription(
        db,
        user,
        start=now - timedelta(days=1),
        end=now + timedelta(days=20),
    )

    for _ in range(2):
        response, called = _post_report(client, user)
        assert response.json()["success"] is True
        assert called == 1

    third, called = _post_report(client, user)
    body = third.json()
    assert third.status_code == 200
    assert body["success"] is False
    assert body["requires_payment"] is True
    assert body["offer_single_report"] is True
    assert body["offer_amount_cents"] == DEEP_CLONE_PRICE_CENTS == 4900
    assert body["offer_amount_label"] == "$49"
    assert body["offer_checkout_path"] == DEEP_CLONE_CHECKOUT_PATH
    assert called == 0

    paid = Transaction(
        user_id=user.id,
        type=TransactionType.DEEP_CLONE,
        status=TransactionStatus.SUCCEEDED,
        amount_cents=4900,
        currency="usd",
        created_at=now,
        metadata_json='{"type": "deep_clone"}',
    )
    db.add(paid)
    db.commit()

    extra, called = _post_report(client, user)
    assert extra.json()["success"] is True
    assert called == 1

    blocked, called = _post_report(client, user)
    assert blocked.json()["offer_amount_cents"] == 4900
    assert called == 0


def test_access_continues_until_period_end_after_cancel(db, client):
    user = _user(db, "cancel@example.com")
    now = datetime.now(timezone.utc)
    subscription = _monthly_subscription(
        db,
        user,
        start=now - timedelta(days=5),
        end=now + timedelta(days=12),
        cancel_at_period_end=True,
    )
    assert monthly_period_is_open(subscription) is True

    allowed, called = _post_report(client, user)
    assert allowed.json()["success"] is True
    assert called == 1

    subscription.status = SubscriptionStatus.CANCELED
    db.commit()
    db.refresh(subscription)
    assert monthly_period_is_open(subscription) is True
    still_allowed, called = _post_report(client, user)
    assert still_allowed.json()["success"] is True
    assert called == 1

    subscription.current_period_end = now - timedelta(minutes=1)
    db.commit()
    db.refresh(subscription)
    assert monthly_period_is_open(subscription) is False
    ended, called = _post_report(client, user)
    assert ended.json()["success"] is False
    assert called == 0


@pytest.mark.parametrize("tier", LEGACY_TIERS)
def test_legacy_tiers_cannot_be_checked_out(db, client, tier):
    user = _user(db, f"{tier}-checkout@example.com")
    payload = {
        "tier": tier,
        "success_url": "https://example.com/ok",
        "cancel_url": "https://example.com/cancel",
    }
    checkout = client.post(CHECKOUT_URL, json=payload, headers=_auth(user))
    intent = client.post(INTENT_URL, json={"tier": tier}, headers=_auth(user))
    assert checkout.status_code == 400
    assert intent.status_code == 400
    assert "not available for new purchases" in checkout.json()["detail"]
    assert "not available for new purchases" in intent.json()["detail"]
    assert is_available_for_new_purchase(SubscriptionTier(tier.upper())) is False
    assert is_available_for_new_purchase(SubscriptionTier.MONTHLY) is True


def test_buyer_pricing_checkout_hides_retired_prices():
    offenders = []
    for relative in BUYER_PRICE_FILES:
        text = (REPO_ROOT / relative).read_text()
        for pattern in FORBIDDEN_PRICE_PATTERNS:
            if pattern.search(text):
                offenders.append(f"{relative} matches {pattern.pattern}")
    assert offenders == []
