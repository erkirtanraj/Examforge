"""Real MySQL integration coverage for M2 identity persistence.

These tests are deliberately pinned to the isolated examforge_test database.
They use unique it-* identities and clean up only those identities.
"""
from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from sqlalchemy import text

from mysql_persistence.config import (
    load_mysql_settings,
    require_approved_test_database,
)
from mysql_persistence.database import create_database_runtime
from mysql_persistence.identity import (
    DuplicateIdentityEmail,
    IdentityRepository,
    InvalidOrExpiredResetToken,
    ProtectedIdentity,
)


@pytest_asyncio.fixture
async def mysql_identity_repository():
    backend_dir = Path(__file__).resolve().parents[2]
    load_dotenv(backend_dir / ".env")
    base_settings = load_mysql_settings()
    test_settings = replace(
        base_settings,
        url=base_settings.url.set(database="examforge_test"),
    )
    require_approved_test_database(test_settings)

    runtime = create_database_runtime(test_settings)
    repository = IdentityRepository(runtime.sessions)
    try:
        yield repository
    finally:
        # Remove only rows created by this integration suite. The unique prefix
        # prevents touching application or developer data in the test schema.
        async with runtime.engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM password_reset_tokens WHERE user_id LIKE 'it-%'")
            )
            await connection.execute(
                text("DELETE FROM users WHERE id LIKE 'it-%'")
            )
        await runtime.dispose()


def identity_values(*, role: str = "student", email: str | None = None) -> dict:
    suffix = uuid.uuid4().hex
    return {
        "id": f"it-{suffix}",
        "name": "M2 Integration User",
        "email": email or f"it-{suffix}@example.test",
        "password_hash": "integration-hash",
        "role": role,
        "status": "active",
        "auth_provider": "email",
        "phone": "",
    }


@pytest.mark.asyncio
async def test_mysql_identity_create_read_and_duplicate_email(mysql_identity_repository):
    repository = mysql_identity_repository
    values = identity_values(email=f"it-{uuid.uuid4().hex}@example.test")
    created = await repository.create_user(values)

    assert created["id"] == values["id"]
    assert await repository.get_by_id(values["id"]) is not None
    assert (await repository.get_by_email(values["email"].upper()))["id"] == values["id"]
    listed = await repository.get_by_ids([values["id"], "missing-id"])
    assert [row["id"] for row in listed] == [values["id"]]
    assert "password_hash" not in listed[0]

    with pytest.raises(DuplicateIdentityEmail):
        await repository.create_user(identity_values(email=values["email"]))


@pytest.mark.asyncio
async def test_mysql_super_admin_row_lock_protects_update_and_delete(mysql_identity_repository):
    repository = mysql_identity_repository
    root = await repository.create_user(identity_values(role="super_admin"))

    with pytest.raises(ProtectedIdentity):
        await repository.update_user(
            root["id"], {"name": "Unauthorized change"}, actor_role="admin"
        )
    with pytest.raises(ProtectedIdentity):
        await repository.delete_user(root["id"], actor_role="admin")

    unchanged = await repository.get_by_id(root["id"])
    assert unchanged["role"] == "super_admin"
    assert unchanged["name"] == "M2 Integration User"


@pytest.mark.asyncio
async def test_mysql_super_admin_can_manage_super_admin(mysql_identity_repository):
    repository = mysql_identity_repository
    root = await repository.create_user(identity_values(role="super_admin"))

    updated = await repository.update_user(
        root["id"], {"name": "Authorized root update"}, actor_role="super_admin"
    )
    assert updated["name"] == "Authorized root update"
    assert await repository.delete_user(root["id"], actor_role="super_admin") is True
    assert await repository.get_by_id(root["id"]) is None


@pytest.mark.asyncio
async def test_mysql_password_reset_consumes_token_and_invalidates_siblings(mysql_identity_repository):
    repository = mysql_identity_repository
    user = await repository.create_user(identity_values())
    now = datetime.now(timezone.utc)
    first_hash = uuid.uuid4().hex * 2
    sibling_hash = uuid.uuid4().hex * 2
    await repository.create_reset_token(
        token_hash=first_hash,
        user_id=user["id"],
        expires_at=now + timedelta(hours=1),
    )
    await repository.create_reset_token(
        token_hash=sibling_hash,
        user_id=user["id"],
        expires_at=now + timedelta(hours=1),
    )

    assert await repository.get_valid_reset_token(token_hash=first_hash) is not None
    consumed_user_id = await repository.consume_reset_token(
        token_hash=first_hash, new_password_hash="new-integration-hash"
    )
    assert consumed_user_id == user["id"]
    assert await repository.get_valid_reset_token(token_hash=first_hash) is None
    assert await repository.get_valid_reset_token(token_hash=sibling_hash) is None

    updated = await repository.get_by_id(user["id"])
    assert updated["password_hash"] == "new-integration-hash"
    assert updated["password_reset_at"] is not None
    assert updated["tokens_valid_after"] > int(now.timestamp())
    with pytest.raises(InvalidOrExpiredResetToken):
        await repository.consume_reset_token(
            token_hash=first_hash, new_password_hash="replay-must-fail"
        )


@pytest.mark.asyncio
async def test_mysql_password_reset_rate_limit_is_persisted(mysql_identity_repository):
    repository = mysql_identity_repository
    user = await repository.create_user(identity_values())
    now = datetime.now(timezone.utc)

    for index in range(3):
        allowed = await repository.create_reset_token_if_below_limit(
            token_hash=uuid.uuid4().hex * 2,
            user_id=user["id"],
            expires_at=now + timedelta(hours=1),
            since=now - timedelta(minutes=15),
            max_requests=3,
        )
        assert allowed is True, f"request {index + 1} should be allowed"

    denied = await repository.create_reset_token_if_below_limit(
        token_hash=uuid.uuid4().hex * 2,
        user_id=user["id"],
        expires_at=now + timedelta(hours=1),
        since=now - timedelta(minutes=15),
        max_requests=3,
    )
    assert denied is False


@pytest.mark.asyncio
async def test_mysql_suspended_user_cannot_validate_reset_token(mysql_identity_repository):
    repository = mysql_identity_repository
    user = await repository.create_user(identity_values())
    token_hash = uuid.uuid4().hex * 2
    now = datetime.now(timezone.utc)
    await repository.create_reset_token(
        token_hash=token_hash,
        user_id=user["id"],
        expires_at=now + timedelta(hours=1),
    )

    await repository.update_user(user["id"], {"status": "suspended"})
    assert await repository.get_valid_reset_token(token_hash=token_hash) is None
