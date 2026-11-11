"""Transactional MySQL identity repository used by M2 auth and admin services.

This module is deliberately independent of FastAPI and MongoDB. Callers must
switch related authentication and user-management routes together; do not
dual-write identity records.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import select, update
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


def user_to_dict(user: User, *, include_password_hash: bool = True) -> dict[str, Any]:
    """Convert an ORM identity to the legacy API's dictionary representation."""
    created_at = user.created_at.replace(tzinfo=timezone.utc) if user.created_at.tzinfo is None else user.created_at
    updated_at = user.updated_at
    if updated_at is not None and updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    result = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "auth_provider": user.auth_provider,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat() if updated_at else None,
        "created_by": user.created_by,
        "tokens_valid_after": user.tokens_valid_after,
        "password_reset_at": user.password_reset_at,
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
        try:
            async with self._sessions() as session, session.begin():
                user = User(**payload)
                session.add(user)
                await session.flush()
                return user_to_dict(user)
        except IntegrityError as exc:
            raise DuplicateIdentityEmail("Another account already uses this email") from exc

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
            raise DuplicateIdentityEmail("Another account already uses this email") from exc

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

    async def consume_reset_token(
        self, *, token_hash: str, new_password_hash: str, now: datetime | None = None,
    ) -> str:
        """Atomically consume a token, update password and invalidate sibling tokens."""
        instant = utc_naive(now)
        async with self._sessions() as session, session.begin():
            token = await session.scalar(
                select(PasswordResetToken)
                .where(
                    PasswordResetToken.token_hash == token_hash,
                    PasswordResetToken.used.is_(False),
                    PasswordResetToken.expires_at > instant,
                )
                .with_for_update()
            )
            if token is None:
                raise InvalidOrExpiredResetToken(
                    "This reset link is invalid or has expired. Please request a new one."
                )
            user = await session.scalar(select(User).where(User.id == token.user_id).with_for_update())
            if user is None:
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
