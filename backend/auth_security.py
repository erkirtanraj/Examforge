"""Small, side-effect-free authentication policy helpers."""
from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any


_DEVELOPMENT_SECRET = "dev-secret"
_PRODUCTION_MARKERS = {"production", "prod"}


def is_production_environment(environ: Mapping[str, str]) -> bool:
    values = (
        environ.get("APP_ENV", ""),
        environ.get("ENVIRONMENT", ""),
        environ.get("NODE_ENV", ""),
    )
    return any(value.strip().lower() in _PRODUCTION_MARKERS for value in values)


def resolve_jwt_secret(environ: Mapping[str, str]) -> str:
    """Keep local development convenient but fail closed in production."""
    secret = environ.get("JWT_SECRET", "")
    if is_production_environment(environ):
        if len(secret.strip()) < 32 or secret == _DEVELOPMENT_SECRET:
            raise RuntimeError(
                "Production requires JWT_SECRET with at least 32 characters."
            )
        return secret
    return secret or _DEVELOPMENT_SECRET


def has_valid_identity_claims(payload: Any) -> bool:
    """Require a non-empty uid and a numeric issued-at claim."""
    if not isinstance(payload, dict):
        return False
    user_id = payload.get("uid")
    issued_at = payload.get("iat")
    return (
        isinstance(user_id, str)
        and bool(user_id.strip())
        and isinstance(issued_at, (int, float))
        and not isinstance(issued_at, bool)
        and math.isfinite(issued_at)
    )


def can_manage_target_role(actor_role: str, target_role: str) -> bool:
    """Only a super admin may change the role of an existing super admin."""
    return target_role != "super_admin" or actor_role == "super_admin"
