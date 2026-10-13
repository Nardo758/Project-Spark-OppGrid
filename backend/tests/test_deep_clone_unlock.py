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
from app.models.subscription import Subscription
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User

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
