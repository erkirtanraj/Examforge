"""MySQL-backed authentication operations for the staged M2 cutover.

These helpers intentionally have no MongoDB dependency. The caller owns the
OAuth session exchange and supplies the verified profile returned by that
provider; only the resulting identity is persisted here.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping
from uuid import uuid4

from fastapi import HTTPException

from auth_security import has_valid_identity_claims
from .identity import DuplicateIdentityEmail



async def load_session_identity(repository, claims: Any) -> dict[str, Any]:
    """Resolve and validate a decoded JWT against the current MySQL identity."""
    if not has_valid_identity_claims(claims):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = await repository.get_by_id(claims["uid"], include_password_hash=False)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.get("status") == "suspended":
        raise HTTPException(
            status_code=403,
            detail="Your account has been suspended. Please contact support.",
        )
    tokens_valid_after = user.pop("tokens_valid_after", 0) or 0
    if not isinstance(tokens_valid_after, (int, float)) or isinstance(tokens_valid_after, bool):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if claims["iat"] < tokens_valid_after:
        raise HTTPException(
            status_code=401,
            detail="Your session has expired. Please sign in again.",
        )
    # Return only the public identity fields expected by API consumers.
    public_fields = (
        "id", "name", "email", "role", "status", "auth_provider",
        "phone", "avatar_url", "created_at",
    )
    return {key: user[key] for key in public_fields if key in user}


def _public_identity(user: Mapping[str, Any]) -> dict[str, str]:
    return {
        "id": str(user["id"]),
        "name": str(user["name"]),
        "email": str(user["email"]),
        "role": str(user["role"]),
    }


async def register_identity(
    repository,
    *,
    name: str,
    email: str,
    password: str,
    hash_password: Callable[[str], str],
    make_token: Callable[[str, str], str],
) -> dict[str, Any]:
    normalized_email = email.strip().lower()
    try:
        user = await repository.create_user({
            "id": str(uuid4()),
            "name": name.strip(),
            "email": normalized_email,
            "password_hash": hash_password(password),
            "role": "student",
            "status": "active",
            "auth_provider": "email",
            "avatar_url": None,
        })
    except DuplicateIdentityEmail as exc:
        raise HTTPException(status_code=400, detail="Email already registered") from exc
    return {"token": make_token(user["id"], user["role"]), "user": _public_identity(user)}


async def login_identity(
    repository,
    *,
    email: str,
    password: str,
    verify_password: Callable[[str, str], bool],
    make_token: Callable[[str, str], str],
) -> dict[str, Any]:
    user = await repository.get_by_email(email)
    if not user or not verify_password(password, user.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.get("status") == "suspended":
        raise HTTPException(
            status_code=403,
            detail="Your account has been suspended. Please contact support.",
        )
    return {"token": make_token(user["id"], user["role"]), "user": _public_identity(user)}


async def login_google_identity(
    repository,
    *,
    profile: Mapping[str, Any],
    make_token: Callable[[str, str], str],
) -> dict[str, Any]:
    email = str(profile.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Google account has no email")
    email_verified = profile.get("email_verified")
    if email_verified is False or (
        isinstance(email_verified, str) and email_verified.strip().lower() in {"false", "0", "no"}
    ):
        raise HTTPException(status_code=401, detail="Google account email is not verified")

    user = await repository.get_by_email(email)
    if user is None:
        user_values = {
            "id": str(uuid4()),
            "name": str(profile.get("name") or email.split("@")[0]).strip(),
            "email": email,
            "password_hash": None,
            "role": "student",
            "status": "active",
            "auth_provider": "google",
            "avatar_url": profile.get("picture"),
        }
        try:
            user = await repository.create_user(user_values)
        except DuplicateIdentityEmail:
            # A concurrent Google sign-in or email registration won the unique
            # email race. Re-read the canonical account; never create a second.
            user = await repository.get_by_email(email)
            if user is None:
                raise HTTPException(status_code=409, detail="Unable to create identity") from None
    if user.get("status") == "suspended":
        raise HTTPException(
            status_code=403,
            detail="Your account has been suspended. Please contact support.",
        )
    if not user.get("avatar_url") and profile.get("picture"):
        user = await repository.update_user(user["id"], {"avatar_url": profile["picture"]})
    return {"token": make_token(user["id"], user["role"]), "user": _public_identity(user)}
