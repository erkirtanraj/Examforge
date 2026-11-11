from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from admin_routes import build_admin_router
from mysql_persistence.identity import DuplicateIdentityEmail, IdentityNotFound, ProtectedIdentity


class FakeIdentityRepository:
    def __init__(self, users=None):
        self.users = {item["id"]: dict(item) for item in (users or [])}
        self.created = []
        self.updated = []
        self.deleted = []

    async def list_users(self, *, search="", role=None, status=None, offset=0, limit=50):
        rows = list(self.users.values())
        if search:
            rows = [u for u in rows if search.lower() in u["name"].lower()
                    or search.lower() in u["email"].lower()]
        if role:
            rows = [u for u in rows if u["role"] == role]
        if status:
            rows = [u for u in rows if u["status"] == status]
        total = len(rows)
        return [dict(u) for u in rows[offset:offset + limit]], total

    async def get_by_id(self, user_id, *, include_password_hash=True):
        user = self.users.get(user_id)
        if not user:
            return None
        result = dict(user)
        if not include_password_hash:
            result.pop("password_hash", None)
        return result

    async def create_user(self, values):
        if any(u["email"] == values["email"] for u in self.users.values()):
            raise DuplicateIdentityEmail("duplicate")
        user = {
            **values,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": None,
            "tokens_valid_after": 0,
            "password_reset_at": None,
            "password_reset_by": None,
        }
        self.users[user["id"]] = user
        self.created.append(dict(user))
        return dict(user)

    async def update_user(self, user_id, values, *, actor_role=None):
        user = self.users.get(user_id)
        if user is None:
            raise IdentityNotFound("missing")
        if actor_role is not None and actor_role != "super_admin" and (
            user["role"] == "super_admin" or values.get("role") == "super_admin"
        ):
            raise ProtectedIdentity("protected")
        if "email" in values and any(
            other["id"] != user_id and other["email"] == values["email"]
            for other in self.users.values()
        ):
            raise DuplicateIdentityEmail("duplicate")
        user.update(values)
        user["updated_at"] = "2026-01-02T00:00:00+00:00"
        self.updated.append((user_id, dict(values)))
        return dict(user)

    async def delete_user(self, user_id, *, actor_role=None):
        if user_id not in self.users:
            return False
        if actor_role is not None and actor_role != "super_admin" and self.users[user_id]["role"] == "super_admin":
            raise ProtectedIdentity("protected")
        del self.users[user_id]
        self.deleted.append(user_id)
        return True


class FakeCollection:
    def __init__(self):
        self.deleted = []

    async def count_documents(self, query):
        return 2

    async def delete_many(self, query):
        self.deleted.append(query)
        return type("DeleteResult", (), {"deleted_count": 2})()


class FakeDatabase:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        return self.collections.setdefault(name, FakeCollection())


def make_client(repository, actor=None):
    app = FastAPI()
    app.state.identity_repository = repository
    actor = actor or {"id": "admin-1", "role": "admin"}

    def require_roles(*_roles):
        async def dependency():
            return actor
        return dependency

    app.include_router(build_admin_router(
        FakeDatabase(), require_roles, lambda value: f"hashed:{value}", lambda _ids: None,
    ))
    return TestClient(app)


def user(user_id="user-1", role="student", **extra):
    return {
        "id": user_id, "name": "Student", "email": f"{user_id}@example.com",
        "role": role, "status": "active", "phone": "", "avatar_url": None,
        "auth_provider": "email", "password_hash": "stored-hash",
        "tokens_valid_after": 0, **extra,
    }


def test_admin_user_list_preserves_array_contract_and_hides_credentials():
    repository = FakeIdentityRepository([user(), user("user-2")])
    response = make_client(repository).get("/api/admin/users")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 2
    assert "password_hash" not in payload[0]
    assert "tokens_valid_after" not in payload[0]


def test_legacy_role_endpoint_updates_mysql_identity():
    repository = FakeIdentityRepository([user()])
    response = make_client(repository).put(
        "/api/admin/users/user-1/role", json={"role": "teacher"},
    )
    assert response.status_code == 200
    assert repository.users["user-1"]["role"] == "teacher"
    changes = repository.updated[-1][1]
    assert changes["role"] == "teacher"
    assert changes["tokens_valid_after"] > 0


def test_legacy_role_endpoint_blocks_admin_from_granting_super_admin():
    repository = FakeIdentityRepository([user()])
    response = make_client(repository).put(
        "/api/admin/users/user-1/role", json={"role": "super_admin"},
    )
    assert response.status_code == 403
    assert repository.users["user-1"]["role"] == "student"


def test_legacy_role_endpoint_blocks_self_role_change():
    repository = FakeIdentityRepository([user("admin-1", "admin")])
    response = make_client(repository).put(
        "/api/admin/users/admin-1/role", json={"role": "teacher"},
    )
    assert response.status_code == 400
    assert repository.updated == []


def test_admin_user_detail_uses_mysql_identity_and_keeps_mongo_stats():
    repository = FakeIdentityRepository([user()])
    response = make_client(repository).get("/api/admin/users/user-1")
    assert response.status_code == 200
    assert response.json()["stats"]["orders"] == 2
    assert "password_hash" not in response.json()


def test_admin_create_user_persists_in_mysql_and_hashes_password():
    repository = FakeIdentityRepository()
    response = make_client(repository).post("/api/admin/users", json={
        "name": "New Student", "email": "NEW@example.com", "phone": "12345",
        "role": "student", "password": "secret123",
    })
    assert response.status_code == 200
    created = repository.created[0]
    assert created["email"] == "new@example.com"
    assert created["password_hash"] == "hashed:secret123"
    assert created["created_by"] == "admin-1"
    assert "password_hash" not in response.json()


def test_admin_cannot_grant_super_admin():
    repository = FakeIdentityRepository()
    response = make_client(repository).post("/api/admin/users", json={
        "name": "Root", "email": "root@example.com", "phone": "",
        "role": "super_admin", "password": "secret123",
    })
    assert response.status_code == 403
    assert repository.created == []


def test_admin_update_user_invalidates_existing_sessions_on_role_or_email_change():
    repository = FakeIdentityRepository([user()])
    response = make_client(repository).put("/api/admin/users/user-1", json={
        "name": "Updated", "email": "updated@example.com", "phone": "999",
        "role": "teacher",
    })
    assert response.status_code == 200
    changes = repository.updated[-1][1]
    assert changes["role"] == "teacher"
    assert changes["tokens_valid_after"] > 0
    assert "password_hash" not in response.json()


def test_admin_cannot_change_own_role():
    repository = FakeIdentityRepository([user("admin-1", "admin")])
    response = make_client(repository).put("/api/admin/users/admin-1", json={
        "name": "Admin", "email": "admin-1@example.com", "phone": "",
        "role": "teacher",
    })
    assert response.status_code == 400
    assert repository.updated == []


def test_admin_reset_password_updates_mysql_and_invalidates_sessions():
    repository = FakeIdentityRepository([user()])
    response = make_client(repository).post(
        "/api/admin/users/user-1/reset-password", json={"password": "new-secret"},
    )
    assert response.status_code == 200
    changes = repository.updated[-1][1]
    assert changes["password_hash"] == "hashed:new-secret"
    assert changes["password_reset_by"] == "admin-1"
    assert changes["tokens_valid_after"] > 0


def test_admin_suspend_user_invalidates_sessions_and_reactivation_is_supported():
    repository = FakeIdentityRepository([user()])
    client = make_client(repository)
    suspended = client.put("/api/admin/users/user-1/status", json={"suspended": True})
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"
    assert repository.updated[-1][1]["tokens_valid_after"] > 0
    active = client.put("/api/admin/users/user-1/status", json={"suspended": False})
    assert active.status_code == 200
    assert active.json()["status"] == "active"


def test_admin_cannot_manage_super_admin_or_delete_self():
    repository = FakeIdentityRepository([user("root-1", "super_admin"), user("admin-1", "admin")])
    client = make_client(repository)
    protected = client.put("/api/admin/users/root-1/status", json={"suspended": True})
    self_delete = client.delete("/api/admin/users/admin-1")
    assert protected.status_code == 403
    assert self_delete.status_code == 400
    assert repository.deleted == []


def test_admin_delete_removes_legacy_associated_records_and_mysql_identity():
    repository = FakeIdentityRepository([user()])
    response = make_client(repository).delete("/api/admin/users/user-1")
    assert response.status_code == 200
    assert response.json()["removed"]["orders"] == 2
    assert repository.deleted == ["user-1"]


class RacePromotionRepository(FakeIdentityRepository):
    """Simulate a concurrent promotion after the route's initial read."""
    async def get_by_id(self, user_id, *, include_password_hash=True):
        result = await super().get_by_id(user_id, include_password_hash=include_password_hash)
        if result and user_id == "user-1":
            self.users[user_id]["role"] = "super_admin"
        return result


def test_admin_cannot_update_super_admin_if_role_changes_after_precheck():
    repository = RacePromotionRepository([user()])
    response = make_client(repository).put("/api/admin/users/user-1", json={
        "name": "Changed", "email": "student@example.com", "phone": "",
        "role": "teacher",
    })
    assert response.status_code == 403
    assert repository.updated == []


def test_admin_cannot_delete_super_admin_if_role_changes_after_precheck():
    repository = RacePromotionRepository([user()])
    response = make_client(repository).delete("/api/admin/users/user-1")
    assert response.status_code == 403
    assert repository.deleted == []
