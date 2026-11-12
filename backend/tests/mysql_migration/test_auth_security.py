import pytest

from auth_security import (
    has_valid_identity_claims,
    can_manage_target_role,
    is_production_environment,
    resolve_jwt_secret,
)


def test_development_keeps_legacy_local_fallback():
    assert resolve_jwt_secret({}) == "dev-secret"
    assert resolve_jwt_secret({"APP_ENV": "development"}) == "dev-secret"


@pytest.mark.parametrize("marker", ["production", "prod", "Production"])
def test_production_requires_strong_jwt_secret(marker):
    with pytest.raises(RuntimeError, match="Production requires JWT_SECRET"):
        resolve_jwt_secret({"APP_ENV": marker})


def test_production_accepts_configured_secret():
    secret = "a" * 48
    assert resolve_jwt_secret({"APP_ENV": "production", "JWT_SECRET": secret}) == secret


def test_production_rejects_legacy_default_even_if_longer_policy_is_bypassed():
    with pytest.raises(RuntimeError):
        resolve_jwt_secret({"ENVIRONMENT": "prod", "JWT_SECRET": "dev-secret"})


def test_environment_detection_supports_common_environment_names():
    assert is_production_environment({"NODE_ENV": "production"})
    assert is_production_environment({"ENVIRONMENT": "prod"})
    assert not is_production_environment({"APP_ENV": "staging"})


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"uid": "user-1"},
        {"iat": 123},
        {"uid": "", "iat": 123},
        {"uid": "user-1", "iat": True},
        {"uid": "user-1", "iat": "123"},
        {"uid": "user-1", "iat": float("nan")},
        {"uid": "user-1", "iat": float("inf")},
    ],
)
def test_identity_claim_validation_rejects_malformed_payloads(payload):
    assert not has_valid_identity_claims(payload)


def test_identity_claim_validation_accepts_valid_payload():
    assert has_valid_identity_claims({"uid": "user-1", "iat": 123})


@pytest.mark.parametrize("actor,target,expected", [
    ("admin", "student", True),
    ("admin", "admin", True),
    ("admin", "super_admin", False),
    ("super_admin", "super_admin", True),
])
def test_super_admin_target_role_protection(actor, target, expected):
    assert can_manage_target_role(actor, target) is expected
