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
    launch_report_catalog_enabled,
    launch_workhub_enabled,
    monthly_period_is_open,
    reject_monthly_alerts,
    report_catalog_launch_lock,
    stripe_price_id_for_tier,
    tier_unlocks_feature,
    workhub_launch_lock,
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
# Pages whose code stays in the repo but is not rendered for buyers while launch flags are off.
HIDDEN_BUYER_FILES = {
    "pages/Services.tsx",
    "pages/ApiPortal.tsx",
    "pages/build/ReportStudio.tsx",
    "pages/build/ConsultantStudio.tsx",
    "pages/WorkHub.tsx",
    "pages/OpportunityHub.tsx",
    "pages/LifecycleDashboard.tsx",
    "components/ReportLibrary.tsx",
    "components/ReportPurchaseModal.tsx",
    "components/ReportInputModal.tsx",
}
HIDDEN_BUYER_DIRS = {"workhub", "ReportSections", "ConsultantResults"}
# Existing-subscriber tier table. Buyer pages render LAUNCH_OFFERS, not these labels.
LEGACY_PRICE_CONFIG = "constants/pricing.ts"
PRICE_LITERAL = re.compile(r"\$\d[\d,]*(?:\.\d+)?")
SCALE_SUFFIX = re.compile(r"\s*[KMBTkmb]\b")
HIDDEN_LINK = re.compile(
    r"""(?:\bto\s*=|\bhref\s*=|\bnavigate\s*\(|\bpath\s*:|location\.href\s*=)"""
    r"""[^;\n]{0,180}"""
    r"""(?:['"`]/(?:services|developer|build/reports|build/business-plan|build/financials|build/pitch-deck|build/consultant-studio|consultant-studio)\b|/hub['"`])"""
)
ALLOWED_PRICE_VALUES = {39.0, 49.0}


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


def _buyer_source_files():
    root = REPO_ROOT / "frontend" / "src"
    files = []
    for path in root.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        if "__tests__" in path.parts or path.name.endswith((".test.ts", ".test.tsx")):
            continue
        relative = path.relative_to(root).as_posix()
        if relative == LEGACY_PRICE_CONFIG:
            continue
        if relative in HIDDEN_BUYER_FILES or path.name.startswith("Admin"):
            continue
        if any(part in HIDDEN_BUYER_DIRS for part in path.parts):
            continue
        files.append((relative, path))
    return files


def _price_is_allowed(line: str, match: re.Match) -> bool:
    rest = line[match.end(): match.end() + 4]
    if SCALE_SUFFIX.match(rest):
        return True
    number = match.group(0)[1:].replace(",", "")
    try:
        value = float(number)
    except ValueError:
        return False
    return value in ALLOWED_PRICE_VALUES


def test_buyer_surfaces_show_only_launch_prices_and_hide_retired_routes():
    """Buyers see $49 and $39. Hidden surfaces are not linked unless a launch flag is on."""
    app_source = (REPO_ROOT / "frontend/src/App.tsx").read_text()
    assert '<LaunchRoute flag="services">' in app_source
    assert '<LaunchRoute flag="apiPortal">' in app_source
    assert app_source.count('<LaunchRoute flag="reportCatalog">') >= 5
    assert app_source.count("<WorkHubRoute>") >= 3
    flags = (REPO_ROOT / "frontend/src/config/launchFlags.ts").read_text()
    assert "if (!value) return false" in flags

    pricing = (REPO_ROOT / "frontend/src" / LEGACY_PRICE_CONFIG).read_text()
    assert "priceLabel: '$49'" in pricing
    assert "priceLabel: '$39/mo'" in pricing

    index_html = (REPO_ROOT / "frontend/index.html").read_text()
    assert "/services" not in index_html
    assert "/developer" not in index_html
    assert "/build/reports" not in index_html
    assert "sitemap" not in index_html.lower()
    assert not list((REPO_ROOT / "frontend").rglob("sitemap*.xml"))

    offenders = []
    for relative, path in _buyer_source_files():
        # App.tsx declares the hidden routes so it can redirect them.
        if relative == "App.tsx":
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if "launchFlags" in line or "is_admin" in line:
                continue
            for match in PRICE_LITERAL.finditer(line):
                if not _price_is_allowed(line, match):
                    offenders.append(f"{relative}:{lineno} price {match.group(0)}")
            if HIDDEN_LINK.search(line):
                offenders.append(f"{relative}:{lineno} link {line.strip()[:160]}")
    assert offenders == []


def test_report_catalog_api_is_hidden_until_flag(client, monkeypatch):
    monkeypatch.delenv("LAUNCH_REPORT_CATALOG", raising=False)
    monkeypatch.delenv("VITE_LAUNCH_REPORT_CATALOG", raising=False)
    assert launch_report_catalog_enabled() is False
    hidden = client.get("/api/v1/report-pricing/public")
    assert hidden.status_code == 404

    monkeypatch.setenv("LAUNCH_REPORT_CATALOG", "true")
    assert launch_report_catalog_enabled() is True
    assert report_catalog_launch_lock() is None


def test_workhub_stays_available_for_admins_until_period_flag(monkeypatch):
    monkeypatch.delenv("LAUNCH_WORKHUB", raising=False)
    monkeypatch.delenv("VITE_LAUNCH_WORKHUB", raising=False)
    assert launch_workhub_enabled() is False

    buyer = SimpleNamespace(is_admin=False, id=1)
    with pytest.raises(HTTPException) as denied:
        workhub_launch_lock(current_user=buyer, db=SimpleNamespace())
    assert denied.value.status_code == 403
    assert "workhub" in denied.value.detail.lower()

    admin = SimpleNamespace(is_admin=True, id=2)
    workhub_launch_lock(current_user=admin, db=SimpleNamespace())

    monkeypatch.setenv("LAUNCH_WORKHUB", "true")
    assert launch_workhub_enabled() is True
