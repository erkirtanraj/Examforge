from fastapi import HTTPException
import pytest

from mysql_persistence.auth import (
    login_google_identity,
    login_identity,
    register_identity,
)
from mysql_persistence.identity import DuplicateIdentityEmail


class FakeIdentityRepository:
    def __init__(self, users=None):
        self.users = {user["email"]: dict(user) for user in (users or [])}
        self.created = []
        self.updated = []

    async def get_by_email(self, email):
        user = self.users.get(email.strip().lower())
        return dict(user) if user else None

    async def create_user(self, values):
        email = values["email"].strip().lower()
        if email in self.users:
            raise DuplicateIdentityEmail("duplicate")
        user = {
            "id": values["id"],
            "name": values["name"],
            "email": email,
            "password_hash": values.get("password_hash"),
            "role": values.get("role", "student"),
            "status": values.get("status", "active"),
            "auth_provider": values.get("auth_provider", "email"),
            "avatar_url": values.get("avatar_url"),
        }
        self.users[email] = user
        self.created.append(dict(user))
        return dict(user)

    async def update_user(self, user_id, values):
        user = next(item for item in self.users.values() if item["id"] == user_id)
        user.update(values)
        self.updated.append((user_id, dict(values)))
        return dict(user)


def token_for(user_id, role):
    return f"token:{user_id}:{role}"


@pytest.mark.asyncio
async def test_register_creates_student_in_mysql_repository_and_returns_legacy_shape():
    repository = FakeIdentityRepository()
    result = await register_identity(
        repository,
        name=" New Student ",
        email=" STUDENT@EXAMPLE.TEST ",
        password="secret",
        hash_password=lambda value: f"hashed:{value}",
        make_token=token_for,
    )
    assert result["user"]["name"] == "New Student"
    assert result["user"]["email"] == "student@example.test"
    assert result["user"]["role"] == "student"
    assert result["token"].endswith(":student")
    assert repository.created[0]["password_hash"] == "hashed:secret"
    assert repository.created[0]["auth_provider"] == "email"


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email():
    repository = FakeIdentityRepository([{
        "id": "existing", "name": "Existing", "email": "student@example.test",
        "password_hash": "hash", "role": "student", "status": "active",
    }])
    with pytest.raises(HTTPException) as error:
        await register_identity(
            repository, name="Student", email="STUDENT@example.test", password="pw",
            hash_password=lambda value: value, make_token=token_for,
        )
    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_login_uses_mysql_identity_and_returns_legacy_shape():
    repository = FakeIdentityRepository([{
        "id": "user-1", "name": "Student", "email": "student@example.test",
        "password_hash": "hashed:secret", "role": "student", "status": "active",
    }])
    result = await login_identity(
        repository, email="STUDENT@example.test", password="secret",
        verify_password=lambda password, hashed: hashed == f"hashed:{password}",
        make_token=token_for,
    )
    assert result["user"] == {
        "id": "user-1", "name": "Student", "email": "student@example.test", "role": "student",
    }
    assert result["token"] == "token:user-1:student"


@pytest.mark.asyncio
async def test_login_rejects_unknown_user_and_wrong_password_with_same_response():
    repository = FakeIdentityRepository()
    with pytest.raises(HTTPException) as error:
        await login_identity(
            repository, email="missing@example.test", password="wrong",
            verify_password=lambda *_: False, make_token=token_for,
        )
    assert error.value.status_code == 401
    assert error.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_blocks_suspended_account():
    repository = FakeIdentityRepository([{
        "id": "user-1", "name": "Student", "email": "student@example.test",
        "password_hash": "hashed:secret", "role": "student", "status": "suspended",
    }])
    with pytest.raises(HTTPException) as error:
        await login_identity(
            repository, email="student@example.test", password="secret",
            verify_password=lambda *_: True, make_token=token_for,
        )
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_google_login_creates_google_identity():
    repository = FakeIdentityRepository()
    result = await login_google_identity(
        repository,
        profile={"email": "GOOGLE@example.test", "name": "Google User", "picture": "https://img.test/a.png"},
        make_token=token_for,
    )
    assert result["user"]["email"] == "google@example.test"
    assert repository.created[0]["auth_provider"] == "google"
    assert repository.created[0]["password_hash"] is None
    assert repository.created[0]["avatar_url"] == "https://img.test/a.png"


@pytest.mark.asyncio
async def test_google_login_updates_missing_avatar_for_existing_identity():
    repository = FakeIdentityRepository([{
        "id": "user-1", "name": "Existing", "email": "google@example.test",
        "password_hash": None, "role": "student", "status": "active", "avatar_url": None,
    }])
    result = await login_google_identity(
        repository, profile={"email": "google@example.test", "picture": "https://img.test/a.png"},
        make_token=token_for,
    )
    assert result["user"]["id"] == "user-1"
    assert repository.updated == [("user-1", {"avatar_url": "https://img.test/a.png"})]


@pytest.mark.asyncio
async def test_google_login_rejects_suspended_identity():
    repository = FakeIdentityRepository([{
        "id": "user-1", "name": "Existing", "email": "google@example.test",
        "password_hash": None, "role": "student", "status": "suspended",
    }])
    with pytest.raises(HTTPException) as error:
        await login_google_identity(
            repository, profile={"email": "google@example.test"}, make_token=token_for,
        )
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_google_login_requires_verified_email():
    repository = FakeIdentityRepository()
    with pytest.raises(HTTPException) as error:
        await login_google_identity(repository, profile={"name": "No Email"}, make_token=token_for)
    assert error.value.status_code == 401
