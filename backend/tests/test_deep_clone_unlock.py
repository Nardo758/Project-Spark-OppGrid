"""Unlock checks for Consultant Studio Deep Clone analysis."""

from unittest.mock import AsyncMock, patch

import pytest
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
from app.routers.stripe_webhook import handle_checkout_completed, handle_payment_intent_failed

DEEP_CLONE_URL = "/api/v1/consultant/deep-clone"
DEEP_CLONE_BODY = {
    "source_business_name": "Acme Coffee",
    "source_business_address": "123 Main St, Austin, TX",
    "target_city": "Austin",
}


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


def _transaction(db, user: User, *, status: TransactionStatus, metadata: dict, tx_type: TransactionType):
    import json

    row = Transaction(
        user_id=user.id,
        type=tx_type,
        status=status,
        amount_cents=4900,
        currency="usd",
        metadata_json=json.dumps(metadata),
    )
    db.add(row)
    db.commit()
    return row


def test_paid_user_is_unlocked(db, client):
    user = _user(db, "paid@example.com")
    _transaction(
        db,
        user,
        status=TransactionStatus.SUCCEEDED,
        metadata={"type": "deep_clone", "user_id": str(user.id)},
        tx_type=TransactionType.PAY_PER_UNLOCK,
    )

    analysis = {
        "success": True,
        "target_city": "Austin",
        "match_score": 82,
        "requires_payment": False,
    }
    with patch("app.routers.consultant.ConsultantStudioService") as service_cls:
        service_cls.return_value.deep_clone_analysis = AsyncMock(return_value=analysis)
        response = client.post(DEEP_CLONE_URL, json=DEEP_CLONE_BODY, headers=_auth(user))

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["requires_payment"] is False
    assert body["match_score"] == 82
    service_cls.return_value.deep_clone_analysis.assert_awaited_once()


def test_unpaid_user_requires_payment(db, client):
    user = _user(db, "unpaid@example.com")
    other = _user(db, "other@example.com")
    _transaction(
        db,
        user,
        status=TransactionStatus.PENDING,
        metadata={"type": "deep_clone"},
        tx_type=TransactionType.PAY_PER_UNLOCK,
    )
    _transaction(
        db,
        user,
        status=TransactionStatus.SUCCEEDED,
        metadata={"type": "micro_payment"},
        tx_type=TransactionType.MICRO_PAYMENT,
    )
    _transaction(
        db,
        other,
        status=TransactionStatus.SUCCEEDED,
        metadata={"payment_type": "deep_clone"},
        tx_type=TransactionType.PAY_PER_UNLOCK,
    )

    with patch("app.routers.consultant.ConsultantStudioService") as service_cls:
        response = client.post(DEEP_CLONE_URL, json=DEEP_CLONE_BODY, headers=_auth(user))

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["requires_payment"] is True
    service_cls.assert_not_called()


def test_guest_is_unpaid_even_if_first_user_paid(db, client):
    """Guests are unauthenticated and must not inherit user id 1."""
    first_user = _user(db, "first@example.com")
    assert first_user.id == 1
    _transaction(
        db,
        first_user,
        status=TransactionStatus.SUCCEEDED,
        metadata={"type": "deep_clone"},
        tx_type=TransactionType.PAY_PER_UNLOCK,
    )

    with patch("app.routers.consultant.ConsultantStudioService") as service_cls:
        response = client.post(DEEP_CLONE_URL, json=DEEP_CLONE_BODY)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["requires_payment"] is True
    service_cls.assert_not_called()


def _paid_checkout(user, *, session_id, payment_intent, payment_status="paid"):
    return {
        "id": session_id,
        "payment_status": payment_status,
        "payment_intent": payment_intent,
        "amount_total": 4900,
        "currency": "usd",
        "metadata": {"type": "deep_clone", "user_id": str(user.id)},
    }


def _analysis_result():
    return {
        "success": True,
        "target_city": "Austin",
        "match_score": 82,
        "requires_payment": False,
    }


def test_completed_checkout_unlocks_buyer_only(db, client):
    """A paid deep_clone checkout writes one succeeded row and unlocks that user."""
    buyer = _user(db, "buyer@example.com")
    other = _user(db, "locked@example.com")
    session = _paid_checkout(
        buyer,
        session_id="cs_deep_clone_paid",
        payment_intent="pi_deep_clone_paid",
    )

    handle_checkout_completed(session, db)
    handle_checkout_completed(session, db)

    rows = db.query(Transaction).filter(Transaction.user_id == buyer.id).all()
    assert len(rows) == 1
    assert rows[0].type == TransactionType.DEEP_CLONE
    assert rows[0].status == TransactionStatus.SUCCEEDED
    assert rows[0].stripe_payment_intent_id == "pi_deep_clone_paid"
    assert db.query(Transaction).filter(Transaction.user_id == other.id).count() == 0
    assert db.query(Subscription).count() == 0

    analysis = _analysis_result()
    with patch("app.routers.consultant.ConsultantStudioService") as service_cls:
        service_cls.return_value.deep_clone_analysis = AsyncMock(return_value=analysis)
        buyer_response = client.post(DEEP_CLONE_URL, json=DEEP_CLONE_BODY, headers=_auth(buyer))
        other_response = client.post(DEEP_CLONE_URL, json=DEEP_CLONE_BODY, headers=_auth(other))

    assert buyer_response.status_code == 200
    buyer_body = buyer_response.json()
    assert buyer_body["success"] is True
    assert buyer_body["requires_payment"] is False
    assert other_response.status_code == 200
    other_body = other_response.json()
    assert other_body["success"] is False
    assert other_body["requires_payment"] is True
    service_cls.return_value.deep_clone_analysis.assert_awaited_once()


def test_pending_or_failed_payment_stays_locked(db, client):
    """Unpaid checkout and a failed payment intent do not unlock Deep Clone."""
    user = _user(db, "pending@example.com")
    unpaid = _paid_checkout(
        user,
        session_id="cs_deep_clone_unpaid",
        payment_intent="pi_deep_clone_unpaid",
        payment_status="unpaid",
    )
    handle_checkout_completed(unpaid, db)
    assert db.query(Transaction).count() == 0

    with patch("app.routers.consultant.ConsultantStudioService") as service_cls:
        unpaid_response = client.post(DEEP_CLONE_URL, json=DEEP_CLONE_BODY, headers=_auth(user))
    assert unpaid_response.status_code == 200
    unpaid_body = unpaid_response.json()
    assert unpaid_body["success"] is False
    assert unpaid_body["requires_payment"] is True
    service_cls.assert_not_called()

    pending = Transaction(
        user_id=user.id,
        type=TransactionType.DEEP_CLONE,
        status=TransactionStatus.PENDING,
        amount_cents=4900,
        currency="usd",
        stripe_payment_intent_id="pi_failed",
        metadata_json='{"type": "deep_clone"}',
    )
    db.add(pending)
    db.commit()

    handle_payment_intent_failed(
        {"id": "pi_failed", "metadata": {"type": "deep_clone"}},
        db,
    )
    db.refresh(pending)
    assert pending.status == TransactionStatus.FAILED

    with patch("app.routers.consultant.ConsultantStudioService") as service_cls:
        failed_response = client.post(DEEP_CLONE_URL, json=DEEP_CLONE_BODY, headers=_auth(user))
    assert failed_response.status_code == 200
    failed_body = failed_response.json()
    assert failed_body["success"] is False
    assert failed_body["requires_payment"] is True
    service_cls.assert_not_called()


@pytest.mark.parametrize(
    "tier",
    [
        SubscriptionTier.GROWTH,
        SubscriptionTier.PRO,
        SubscriptionTier.TEAM,
        SubscriptionTier.BUSINESS,
        SubscriptionTier.ENTERPRISE,
    ],
)
def test_active_premium_subscriber_unlocks(db, client, tier):
    """An active subscriber on a premium tier unlocks without a one-time purchase."""
    user = _user(db, f"{tier.value.lower()}@example.com")
    db.add(Subscription(user_id=user.id, tier=tier, status=SubscriptionStatus.ACTIVE))
    db.commit()

    analysis = _analysis_result()
    with patch("app.routers.consultant.ConsultantStudioService") as service_cls:
        service_cls.return_value.deep_clone_analysis = AsyncMock(return_value=analysis)
        response = client.post(DEEP_CLONE_URL, json=DEEP_CLONE_BODY, headers=_auth(user))

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["requires_payment"] is False
    service_cls.return_value.deep_clone_analysis.assert_awaited_once()
