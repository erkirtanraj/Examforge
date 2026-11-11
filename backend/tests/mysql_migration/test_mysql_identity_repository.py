from datetime import datetime, timezone
from types import SimpleNamespace

from mysql_persistence.identity import utc_naive, user_to_dict


def sample_user(**overrides):
    values = {
        "id": "4df5d65c-32e0-4df3-89bb-29a13db0c020",
        "name": "Example Student",
        "email": "student@example.test",
        "password_hash": "$2b$12$example",
        "role": "student",
        "status": "active",
        "auth_provider": "email",
        "phone": "",
        "avatar_url": None,
        "created_at": datetime(2026, 1, 2, 3, 4, 5),
        "updated_at": None,
        "created_by": None,
        "tokens_valid_after": 0,
        "password_reset_at": datetime(2026, 1, 3, 4, 5, 6),
        "password_reset_by": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_utc_naive_converts_aware_datetime_to_utc():
    value = datetime(2026, 1, 2, 8, 30, tzinfo=timezone.utc)
    result = utc_naive(value)
    assert result == datetime(2026, 1, 2, 8, 30)
    assert result.tzinfo is None


def test_user_serializer_preserves_legacy_identity_fields_and_utc_timestamps():
    result = user_to_dict(sample_user())
    assert result["id"] == "4df5d65c-32e0-4df3-89bb-29a13db0c020"
    assert result["email"] == "student@example.test"
    assert result["created_at"] == "2026-01-02T03:04:05+00:00"
    assert result["password_reset_at"] == "2026-01-03T04:05:06+00:00"
    assert result["password_hash"] == "$2b$12$example"


def test_public_user_serializer_omits_password_hash():
    result = user_to_dict(sample_user(), include_password_hash=False)
    assert "password_hash" not in result
    assert result["role"] == "student"
    assert result["status"] == "active"
