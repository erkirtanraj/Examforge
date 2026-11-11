from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import email_routes
from email_routes import GENERIC, build_email_router
from mysql_persistence.identity import InvalidOrExpiredResetToken


class FakeSettings:
    async def find_one(self, *_args, **_kwargs):
        return {
            "host": "smtp.example.test",
            "port": 587,
            "security": "starttls",
            "from_email": "no-reply@example.test",
            "site_url": "https://examforge.example.test",
        }


class FakeDatabase:
    settings = FakeSettings()


class FakeResetRepository:
    def __init__(self, user=None, allow_request=True, valid_tokens=None):
        self.user = user
        self.allow_request = allow_request
        self.valid_tokens = set(valid_tokens or [])
        self.created = []
        self.checked = []
        self.consumed = []

    async def get_by_email(self, email, *, include_password_hash):
        assert include_password_hash is False
        if self.user and self.user["email"] == email:
            return dict(self.user)
        return None

    async def create_reset_token_if_below_limit(self, **values):
        self.created.append(values)
        return self.allow_request

    async def get_valid_reset_token(self, *, token_hash):
        self.checked.append(token_hash)
        if token_hash in self.valid_tokens:
            return {"user_id": "user-1"}
        return None

    async def consume_reset_token(self, *, token_hash, new_password_hash):
        self.consumed.append((token_hash, new_password_hash))
        if token_hash == "invalid":
            raise InvalidOrExpiredResetToken("invalid")


def make_client(repository):
    app = FastAPI()
    app.state.identity_repository = repository

    def require_roles(*_roles):
        async def dependency():
            return {"id": "admin-1", "role": "admin"}
        return dependency

    async def get_brand():
        return "ExamForge"

    app.include_router(build_email_router(FakeDatabase(), require_roles, get_brand, lambda value: f"hashed:{value}"))
    return TestClient(app)


def test_forgot_password_uses_mysql_repository_and_sends_generic_response(monkeypatch):
    repository = FakeResetRepository({
        "id": "user-1", "name": "Student", "email": "student@example.test", "status": "active",
    })
    sent = []
    monkeypatch.setattr(email_routes, "_send_sync", lambda *args: sent.append(args))
    response = make_client(repository).post(
        "/api/auth/forgot-password", json={"email": "STUDENT@example.test"},
    )
    assert response.status_code == 200
    assert response.json() == GENERIC
    assert len(repository.created) == 1
    assert repository.created[0]["user_id"] == "user-1"
    assert len(sent) == 1
    assert "token=" in sent[0][4]


def test_forgot_password_does_not_disclose_unknown_or_suspended_accounts(monkeypatch):
    monkeypatch.setattr(email_routes, "_send_sync", lambda *_args: pytest.fail("email must not be sent"))
    unknown = FakeResetRepository()
    response = make_client(unknown).post(
        "/api/auth/forgot-password", json={"email": "missing@example.test"},
    )
    assert response.status_code == 200
    assert response.json() == GENERIC
    suspended = FakeResetRepository({
        "id": "user-2", "name": "Suspended", "email": "suspended@example.test", "status": "suspended",
    })
    response = make_client(suspended).post(
        "/api/auth/forgot-password", json={"email": "suspended@example.test"},
    )
    assert response.status_code == 200
    assert response.json() == GENERIC
    assert suspended.created == []


def test_forgot_password_enforces_repository_rate_limit(monkeypatch):
    repository = FakeResetRepository({
        "id": "user-1", "name": "Student", "email": "student@example.test", "status": "active",
    }, allow_request=False)
    monkeypatch.setattr(email_routes, "_send_sync", lambda *_args: pytest.fail("email must not be sent"))
    response = make_client(repository).post(
        "/api/auth/forgot-password", json={"email": "student@example.test"},
    )
    assert response.status_code == 200
    assert response.json() == GENERIC
    assert len(repository.created) == 1


def test_check_reset_token_uses_mysql_token_lookup():
    repository = FakeResetRepository({
        "id": "user-1", "name": "Student", "email": "student@example.test", "status": "active",
    })
    client = make_client(repository)
    response = client.get("/api/auth/reset-password/this-is-a-long-reset-token-value")
    assert response.status_code == 200
    assert response.json() == {"valid": False}


def test_reset_password_consumes_token_and_updates_password_through_repository():
    raw_token = "this-is-a-long-reset-token-value"
    repository = FakeResetRepository(valid_tokens={email_routes._hash(raw_token)})
    response = make_client(repository).post(
        "/api/auth/reset-password",
        json={"token": raw_token, "password": "new-password"},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert repository.consumed == [
        (email_routes._hash("this-is-a-long-reset-token-value"), "hashed:new-password"),
    ]


def test_reset_password_rejects_invalid_or_expired_token():
    repository = FakeResetRepository()
    response = make_client(repository).post(
        "/api/auth/reset-password",
        json={"token": "invalid-reset-token-value-123456", "password": "new-password"},
    )
    assert response.status_code == 400
    assert "invalid or has expired" in response.json()["detail"]
