"""Transactional MySQL identity repository used by M2 auth and admin services.

This module is deliberately independent of FastAPI and MongoDB. Callers must
switch related authentication and user-management routes together; do not
dual-write identity records.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from .models import PasswordResetToken, User


class DuplicateIdentityEmail(ValueError):
    """Raised when an email address is already assigned to an identity."""


class IdentityNotFound(LookupError):
    """Raised when a requested identity does not exist."""


class InvalidOrExpiredResetToken(ValueError):
    """Raised when a reset token is missing, used, or expired."""


def utc_naive(value: datetime | None = None) -> datetime:
    """Normalize an instant to UTC-naive for MySQL DATETIME storage."""
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        return current
    return current.astimezone(timezone.utc).replace(tzinfo=None)


def _aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def user_to_dict(user: User, *, include_password_hash: bool = True) -> dict[str, Any]:
    """Convert an ORM identity to the legacy API's dictionary representation."""
    created_at = _aware_utc(user.created_at)
    updated_at = _aware_utc(user.updated_at)
    password_reset_at = _aware_utc(user.password_reset_at)
    result = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "auth_provider": user.auth_provider,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
        "created_by": user.created_by,
        "tokens_valid_after": user.tokens_valid_after,
        "password_reset_at": password_reset_at.isoformat() if password_reset_at else None,
        "password_reset_by": user.password_reset_by,
    }
    if include_password_hash:
        result["password_hash"] = user.password_hash
    return result


class IdentityRepository:
    """Persistence operations for users and one-time password reset tokens."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        self._sessions = sessions

    async def get_by_id(self, user_id: str, *, include_password_hash: bool = True) -> dict | None:
        async with self._sessions() as session:
            user = await session.scalar(select(User).where(User.id == user_id))
            return user_to_dict(user, include_password_hash=include_password_hash) if user else None

    async def get_by_email(self, email: str, *, include_password_hash: bool = True) -> dict | None:
        normalized = email.strip().lower()
        async with self._sessions() as session:
            user = await session.scalar(select(User).where(User.email == normalized))
            return user_to_dict(user, include_password_hash=include_password_hash) if user else None

    async def create_user(self, values: Mapping[str, Any]) -> dict:
        """Create one identity; unique-email races are translated consistently."""
        allowed = {
            "id", "name", "email", "password_hash", "role", "status", "auth_provider",
            "phone", "avatar_url", "created_by",
        }
        payload = {key: value for key, value in values.items() if key in allowed}
        payload["email"] = str(payload["email"]).strip().lower()
        payload.setdefault("role", "student")
        payload.setdefault("status", "active")
        payload.setdefault("auth_provider", "email")
        payload.setdefault("phone", "")
        payload.setdefault("created_at", utc_naive())
        try:
            async with self._sessions() as session, session.begin():
                user = User(**payload)
                session.add(user)
                await session.flush()
                return user_to_dict(user)
        except IntegrityError as exc:
            original = getattr(exc, "orig", None)
            message = str(original or exc)
            if "uq_users_email" in message or (getattr(original, "args", ()) and original.args[0] == 1062):
                raise DuplicateIdentityEmail("Another account already uses this email") from exc
            raise

    async def update_user(self, user_id: str, values: Mapping[str, Any]) -> dict:
        allowed = {
            "name", "email", "role", "status", "auth_provider", "phone",
            "avatar_url", "tokens_valid_after", "password_hash",
            "password_reset_at", "password_reset_by",
        }
        payload = {key: value for key, value in values.items() if key in allowed}
        if "email" in payload:
            payload["email"] = str(payload["email"]).strip().lower()
        try:
            async with self._sessions() as session, session.begin():
                user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
                if user is None:
                    raise IdentityNotFound("User not found")
                for key, value in payload.items():
                    setattr(user, key, value)
                user.updated_at = utc_naive()
                await session.flush()
                return user_to_dict(user)
        except IntegrityError as exc:
            original = getattr(exc, "orig", None)
            message = str(original or exc)
            if "uq_users_email" in message or (getattr(original, "args", ()) and original.args[0] == 1062):
                raise DuplicateIdentityEmail("Another account already uses this email") from exc
            raise

    async def delete_user(self, user_id: str) -> bool:
        async with self._sessions() as session, session.begin():
            user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
            if user is None:
                return False
            await session.delete(user)
            return True

    async def create_reset_token(
        self, *, token_hash: str, user_id: str, expires_at: datetime,
    ) -> int:
        async with self._sessions() as session, session.begin():
            token = PasswordResetToken(
                token_hash=token_hash,
                user_id=user_id,
                used=False,
                created_at=utc_naive(),
                expires_at=utc_naive(expires_at),
            )
            session.add(token)
            await session.flush()
            return token.id

    async def create_reset_token_if_below_limit(
        self, *, token_hash: str, user_id: str, expires_at: datetime,
        since: datetime, max_requests: int,
    ) -> bool:
        """Lock the identity row so concurrent requests cannot bypass the rate limit."""
        instant = utc_naive()
        window_start = utc_naive(since)
        async with self._sessions() as session, session.begin():
            user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
            if user is None or user.status != "active":
                return False
            recent_count = await session.scalar(
                select(func.count(PasswordResetToken.id)).where(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.created_at > window_start,
                )
            )
            if int(recent_count or 0) >= max_requests:
                return False
            session.add(PasswordResetToken(
                token_hash=token_hash,
                user_id=user_id,
                used=False,
                created_at=instant,
                expires_at=utc_naive(expires_at),
            ))
            await session.flush()
            return True

    async def get_valid_reset_token(self, *, token_hash: str, now: datetime | None = None) -> dict | None:
        """Return only a currently usable token; never expose the stored token hash."""
        instant = utc_naive(now)
        async with self._sessions() as session:
            token = await session.scalar(
                select(PasswordResetToken).where(
                    PasswordResetToken.token_hash == token_hash,
                    PasswordResetToken.used.is_(False),
                    PasswordResetToken.expires_at > instant,
                )
            )
            if token is None:
                return None
            return {
                "user_id": token.user_id,
                "expires_at": _aware_utc(token.expires_at),
            }

    async def consume_reset_token(
        self, *, token_hash: str, new_password_hash: str, now: datetime | None = None,
    ) -> str:
        """Atomically consume a token, update password and invalidate sibling tokens."""
        instant = utc_naive(now)
        async with self._sessions() as session, session.begin():
            # Read the owner without locking, then always lock the user row
            # before any reset-token rows. This consistent lock order avoids
            # deadlocks between simultaneous resets for the same identity.
            candidate = await session.scalar(
                select(PasswordResetToken).where(
                    PasswordResetToken.token_hash == token_hash,
                    PasswordResetToken.used.is_(False),
                    PasswordResetToken.expires_at > instant,
                )
            )
            if candidate is None:
                raise InvalidOrExpiredResetToken(
                    "This reset link is invalid or has expired. Please request a new one."
                )
            user = await session.scalar(
                select(User).where(User.id == candidate.user_id).with_for_update()
            )
            if user is None or user.status != "active":
                raise InvalidOrExpiredResetToken(
                    "This reset link is invalid or has expired. Please request a new one."
                )
            token = await session.scalar(
                select(PasswordResetToken)
                .where(
                    PasswordResetToken.token_hash == token_hash,
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.used.is_(False),
                    PasswordResetToken.expires_at > instant,
                )
                .with_for_update()
            )
            if token is None:
                raise InvalidOrExpiredResetToken(
                    "This reset link is invalid or has expired. Please request a new one."
                )
            token.used = True
            token.used_at = instant
            user.password_hash = new_password_hash
            user.password_reset_at = instant
            user.tokens_valid_after = int(instant.replace(tzinfo=timezone.utc).timestamp())
            user.updated_at = instant
            await session.execute(
                update(PasswordResetToken)
                .where(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.used.is_(False),
                )
                .values(used=True, used_at=instant)
            )
            return user.id
