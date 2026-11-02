from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import (
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import Base, get_db
from app.models import User, UserRole


@pytest.fixture
def auth_client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-bytes")
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app = FastAPI()
    app.dependency_overrides[get_db] = override_get_db

    @app.get("/protected")
    def protected(user: User = Depends(get_current_user)):
        return {"id": str(user.id), "role": user.role.value}

    with Session(engine) as session:
        user = User(
            username="alice",
            email="alice@example.test",
            password_hash=hash_password("correct horse battery staple"),
            role=UserRole.VIEWER,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

    with TestClient(app) as client:
        yield client, engine, user_id

    engine.dispose()


def test_password_hashing_and_verification():
    password_hash = hash_password("correct horse battery staple")

    assert password_hash != "correct horse battery staple"
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)
    assert not verify_password("password", "not-an-argon2-hash")


def test_empty_password_is_rejected():
    with pytest.raises(ValueError, match="must not be empty"):
        hash_password("")


def test_valid_token_authenticates_user_from_database(auth_client):
    client, _engine, user_id = auth_client
    token = create_access_token(user_id)

    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"id": str(user_id), "role": UserRole.VIEWER.value}


def test_client_supplied_role_claim_does_not_change_database_role(
    auth_client, monkeypatch
):
    client, _engine, user_id = auth_client
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-bytes")
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "jti": str(uuid4()),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "role": UserRole.ADMIN.value,
        },
        "test-secret-key-with-at-least-32-bytes",
        algorithm=JWT_ALGORITHM,
    )

    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["role"] == UserRole.VIEWER.value


def test_expired_and_malformed_tokens_are_rejected(auth_client):
    client, _engine, user_id = auth_client
    expired_token = create_access_token(user_id, expires_delta=timedelta(seconds=-1))

    unauthenticated = client.get("/protected")
    assert unauthenticated.status_code == 401

    for token in (expired_token, "malformed.token.value"):
        response = client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"


def test_token_for_nonexistent_user_is_rejected(auth_client):
    client, _engine, _user_id = auth_client
    token = create_access_token(uuid4())

    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_inactive_account_is_rejected_on_every_authenticated_request(auth_client):
    client, engine, user_id = auth_client
    with Session(engine) as session:
        user = session.get(User, user_id)
        assert user is not None
        user.is_active = False
        session.commit()

    token = create_access_token(user_id)
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_missing_or_weak_jwt_secret_fails_closed(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY must be set"):
        create_access_token(uuid4())

    monkeypatch.setenv("JWT_SECRET_KEY", "too-short")
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        create_access_token(uuid4())
