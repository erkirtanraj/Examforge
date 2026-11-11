from datetime import datetime, timezone
import pytest

from scripts.migrate_mongo_identities import (
    ImportPreflightError,
    as_utc_naive,
    build_import_plan,
    normalize_user,
)


USER_ID = "4df5d65c-32e0-4df3-89bb-29a13db0c020"


def valid_user(**overrides):
    row = {
        "id": USER_ID,
        "name": "Example Student",
        "email": " Student@Example.Test ",
        "password_hash": "$2b$12$existing-bcrypt-hash",
        "role": "student",
        "status": "active",
        "auth_provider": "email",
        "created_at": "2026-01-02T03:04:05Z",
        "tokens_valid_after": 0,
    }
    row.update(overrides)
    return row


def test_normalize_user_preserves_hash_and_normalizes_email_and_utc():
    result = normalize_user(valid_user())
    assert result["email"] == "student@example.test"
    assert result["password_hash"] == "$2b$12$existing-bcrypt-hash"
    assert result["created_at"] == datetime(2026, 1, 2, 3, 4, 5)


@pytest.mark.parametrize("field,value", [
    ("role", "owner"),
    ("status", "deleted"),
    ("auth_provider", "unknown"),
    ("tokens_valid_after", True),
])
def test_normalize_user_rejects_unsupported_identity_values(field, value):
    with pytest.raises(ImportPreflightError):
        normalize_user(valid_user(**{field: value}))


def test_normalize_user_rejects_missing_created_at():
    with pytest.raises(ImportPreflightError):
        normalize_user(valid_user(created_at=None))


def test_build_import_plan_detects_case_insensitive_duplicate_emails():
    other_id = "8c6f7d30-2b9c-4b53-9bd5-1e4d8f7a1234"
    plan = build_import_plan(
        [valid_user(), valid_user(id=other_id, email="student@example.test")],
        [],
    )
    assert any("duplicate normalized email" in error for error in plan["errors"])


def test_build_import_plan_accepts_valid_reset_token_and_preserves_usage_state():
    token = {
        "token_hash": "a" * 64,
        "user_id": USER_ID,
        "used": True,
        "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        "expires_at": datetime(2026, 1, 2, 1, tzinfo=timezone.utc),
        "used_at": datetime(2026, 1, 2, 0, 30, tzinfo=timezone.utc),
    }
    plan = build_import_plan([valid_user()], [token])
    assert plan["errors"] == []
    assert plan["tokens"][0]["used"] is True
    assert plan["tokens"][0]["used_at"] == datetime(2026, 1, 2, 0, 30)


def test_as_utc_naive_rejects_non_datetime():
    with pytest.raises(ImportPreflightError):
        as_utc_naive(123, "created_at", required=True)
