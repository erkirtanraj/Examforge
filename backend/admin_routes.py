"""Admin: paginated question bank with bulk delete, and full user management."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field
from typing import List, Literal, Optional
from datetime import datetime, timezone
import re, uuid, time, logging

from mysql_persistence.identity import DuplicateIdentityEmail, IdentityNotFound, ProtectedIdentity

PAGE_SIZES = (10, 50, 100, 500, 1000, 5000)
Role = Literal["super_admin", "admin", "teacher", "student", "support"]
USER_COLLECTIONS = ("test_attempts", "test_results", "orders", "entitlements", "lesson_progress")
log = logging.getLogger(__name__)


class QuestionFilter(BaseModel):
    search: str = ""
    category_id: str = ""
    subject_id: str = ""
    difficulty: str = ""
    type: str = ""


class BulkDeleteIn(BaseModel):
    ids: List[str] = []
    all_matching: bool = False
    filters: QuestionFilter = QuestionFilter()


class DuplicateIn(BaseModel):
    ids: List[str] = Field(min_length=1)
    copies: int = Field(1, ge=1, le=20)


class TestBulkIn(BaseModel):
    ids: List[str] = Field(min_length=1)
    action: Literal["assign", "publish", "unpublish", "delete"]
    series_id: Optional[str] = None


def _numbered(title: str, taken: set, n: int) -> list:
    """Next n titles after the highest existing number for this title's prefix."""
    m = re.match(r"^(.*?)(\d+)\s*$", title)
    if m:
        prefix = m.group(1)
        rx = re.compile(r"^" + re.escape(prefix) + r"(\d+)\s*$")
        top = max([int(x.group(1)) for t in taken if (x := rx.match(t))] + [int(m.group(2))])
        return [f"{prefix}{top + i}" for i in range(1, n + 1)]
    base, out, k = f"{title} (Copy)", [], 1
    while len(out) < n:
        cand = base if k == 1 else f"{title} (Copy {k})"
        if cand not in taken:
            out.append(cand)
            taken.add(cand)
        k += 1
    return out


class UserUpdateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str = Field("", max_length=20)
    role: Role


class UserCreateIn(UserUpdateIn):
    password: str = Field(min_length=6, max_length=128)


class PasswordIn(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class StatusIn(BaseModel):
    suspended: bool


def _now():
    return datetime.now(timezone.utc).isoformat()


def _query(f: QuestionFilter) -> dict:
    q = {}
    if f.search.strip():
        rx = {"$regex": re.escape(f.search.strip()), "$options": "i"}
        q["$or"] = [{"text": rx}, {"text_hi": rx}]
    if f.category_id:
        q["category_id"] = None if f.category_id == "none" else f.category_id
    if f.subject_id:
        q["subject_id"] = None if f.subject_id == "none" else f.subject_id
    if f.difficulty:
        q["difficulty"] = f.difficulty
    if f.type:
        q["type"] = f.type
    return q


def _public_user(u: dict) -> dict:
    return {k: v for k, v in u.items() if k not in ("_id", "password_hash", "tokens_valid_after")}


def build_admin_router(db, require_roles, hash_pw, detach_questions):
    r = APIRouter(prefix="/api/admin")
    staff = Depends(require_roles("admin", "teacher"))
    admin = Depends(require_roles("admin"))

    # ---- Question bank ----
    @r.get("/questions")
    async def list_questions(page: int = Query(1, ge=1), page_size: int = 50, search: str = "", category_id: str = "",
                             subject_id: str = "", difficulty: str = "", type: str = "", _=staff):
        if page_size not in PAGE_SIZES:
            raise HTTPException(400, f"page_size must be one of {PAGE_SIZES}")
        q = _query(QuestionFilter(search=search, category_id=category_id, subject_id=subject_id, difficulty=difficulty, type=type))
        total = await db.questions.count_documents(q)
        items = await db.questions.find(q, {"_id": 0}).sort([("created_at", -1), ("id", 1)]) \
            .skip((page - 1) * page_size).limit(page_size).to_list(page_size)
        return {"items": items, "total": total, "page": page, "page_size": page_size,
                "pages": max(1, -(-total // page_size)), "grand_total": await db.questions.count_documents({})}

    @r.post("/questions/bulk-delete")
    async def bulk_delete(data: BulkDeleteIn, _=staff):
        if data.all_matching:
            q = _query(data.filters)
        elif data.ids:
            q = {"id": {"$in": data.ids}}
        else:
            raise HTTPException(400, "Nothing selected")
        ids = await db.questions.distinct("id", q)
        if ids:
            await db.questions.delete_many({"id": {"$in": ids}})
            await detach_questions(ids)
        return {"deleted": len(ids)}

    # ---- Tests: duplicate & bulk ----
    @r.post("/tests/duplicate")
    async def duplicate_tests(data: DuplicateIn, user=staff):
        src = await db.tests.find({"id": {"$in": data.ids}}, {"_id": 0}).to_list(len(data.ids))
        if not src:
            raise HTTPException(404, "Tests not found")
        created = []
        for t in sorted(src, key=lambda x: data.ids.index(x["id"])):
            taken = set(await db.tests.distinct("title", {"series_id": t["series_id"]}))
            for title in _numbered(t["title"], taken, data.copies):
                doc = {**t, "id": str(uuid.uuid4()), "title": title, "is_published": False, "live_start_at": None,
                       "duplicated_from": t["id"], "created_by": user["id"], "created_at": _now(), "updated_at": _now()}
                await db.tests.insert_one(doc)
                taken.add(title)
                created.append({"id": doc["id"], "title": title})
        return {"created": created}

    @r.post("/tests/bulk")
    async def bulk_tests(data: TestBulkIn, _=staff):
        q = {"id": {"$in": data.ids}}
        if data.action == "delete":
            res = await db.tests.delete_many(q)
            return {"affected": res.deleted_count}
        if data.action == "assign":
            if not data.series_id or not await db.test_series.find_one({"id": data.series_id}, {"_id": 1}):
                raise HTTPException(400, "Choose a valid test series")
            upd = {"series_id": data.series_id}
        else:
            upd = {"is_published": data.action == "publish"}
        res = await db.tests.update_many(q, {"$set": {**upd, "updated_at": _now()}})
        return {"affected": res.matched_count}

    # ---- MySQL-backed identity management ----
    def _identity_repository(request: Request):
        repository = getattr(request.app.state, "identity_repository", None)
        if repository is None:
            raise HTTPException(503, "Identity service unavailable")
        return repository

    async def _target(repository, user_id: str, actor: dict) -> dict:
        user = await repository.get_by_id(user_id, include_password_hash=False)
        if not user:
            raise HTTPException(404, "User not found")
        if user["role"] == "super_admin" and actor["role"] != "super_admin":
            raise HTTPException(403, "Only a super admin can manage a super admin")
        return user

    def _check_role(role: str, actor: dict):
        if role == "super_admin" and actor["role"] != "super_admin":
            raise HTTPException(403, "Only a super admin can grant super admin")

    def _public_identity(user: dict) -> dict:
        return {key: value for key, value in user.items()
                if key not in ("password_hash", "tokens_valid_after")}

    @r.get("/users")
    async def list_users(request: Request, actor=admin):
        # Preserve the existing API contract: GET /api/admin/users returns
        # an array of public users, while sourcing identities from MySQL.
        repository = _identity_repository(request)
        users, _total = await repository.list_users(offset=0, limit=1000)
        return [_public_identity(user) for user in users]

    @r.get("/users/{user_id}")
    async def get_user(user_id: str, request: Request, actor=admin):
        repository = _identity_repository(request)
        user = await _target(repository, user_id, actor)
        stats = {collection: await db[collection].count_documents({"user_id": user_id})
                 for collection in USER_COLLECTIONS}
        return {**_public_identity(user), "stats": stats}

    @r.post("/users")
    async def create_user(data: UserCreateIn, request: Request, actor=admin):
        repository = _identity_repository(request)
        _check_role(data.role, actor)
        try:
            user = await repository.create_user({
                "id": str(uuid.uuid4()),
                "name": data.name.strip(),
                "email": str(data.email).strip().lower(),
                "phone": data.phone.strip(),
                "role": data.role,
                "password_hash": hash_pw(data.password),
                "status": "active",
                "auth_provider": "email",
                "avatar_url": None,
                "created_by": actor["id"],
            })
        except DuplicateIdentityEmail as exc:
            raise HTTPException(400, "Another account already uses this email") from exc
        return _public_identity(user)

    @r.put("/users/{user_id}")
    async def update_user(user_id: str, data: UserUpdateIn, request: Request, actor=admin):
        repository = _identity_repository(request)
        user = await _target(repository, user_id, actor)
        if user_id == actor["id"] and data.role != user["role"]:
            raise HTTPException(400, "You cannot change your own role")
        if data.role != user["role"]:
            _check_role(data.role, actor)
        email = str(data.email).strip().lower()
        changes = {
            "name": data.name.strip(),
            "email": email,
            "phone": data.phone.strip(),
            "role": data.role,
        }
        if data.role != user["role"] or email != user["email"]:
            changes["tokens_valid_after"] = int(time.time())
        try:
            updated = await repository.update_user(user_id, changes, actor_role=actor["role"])
        except ProtectedIdentity as exc:
            raise HTTPException(403, str(exc)) from exc
        except IdentityNotFound as exc:
            raise HTTPException(404, "User not found") from exc
        except DuplicateIdentityEmail as exc:
            raise HTTPException(400, "Another account already uses this email") from exc
        return _public_identity(updated)

    @r.post("/users/{user_id}/reset-password")
    async def reset_user_password(user_id: str, data: PasswordIn, request: Request, actor=admin):
        repository = _identity_repository(request)
        await _target(repository, user_id, actor)
        try:
            await repository.update_user(user_id, {
                "password_hash": hash_pw(data.password),
                "password_reset_at": datetime.now(timezone.utc),
                "password_reset_by": actor["id"],
                "tokens_valid_after": int(time.time()),
            }, actor_role=actor["role"])
        except ProtectedIdentity as exc:
            raise HTTPException(403, str(exc)) from exc
        except IdentityNotFound as exc:
            raise HTTPException(404, "User not found") from exc
        return {"ok": True}

    @r.put("/users/{user_id}/status")
    async def set_status(user_id: str, data: StatusIn, request: Request, actor=admin):
        repository = _identity_repository(request)
        if user_id == actor["id"] and data.suspended:
            raise HTTPException(400, "You cannot suspend your own account")
        await _target(repository, user_id, actor)
        status_value = "suspended" if data.suspended else "active"
        changes = {"status": status_value}
        if data.suspended:
            changes["tokens_valid_after"] = int(time.time())
        try:
            await repository.update_user(user_id, changes, actor_role=actor["role"])
        except ProtectedIdentity as exc:
            raise HTTPException(403, str(exc)) from exc
        except IdentityNotFound as exc:
            raise HTTPException(404, "User not found") from exc
        return {"ok": True, "status": status_value}

    @r.delete("/users/{user_id}")
    async def delete_user(user_id: str, request: Request, actor=admin):
        repository = _identity_repository(request)
        if user_id == actor["id"]:
            raise HTTPException(400, "You cannot delete your own account")
        await _target(repository, user_id, actor)
        # Delete the MySQL identity first. If Mongo cleanup subsequently fails,
        # legacy operational records may remain orphaned, but we avoid deleting
        # those records while leaving a live identity behind after a MySQL error.
        try:
            deleted = await repository.delete_user(user_id, actor_role=actor["role"])
        except ProtectedIdentity as exc:
            raise HTTPException(403, str(exc)) from exc
        if not deleted:
            raise HTTPException(404, "User not found")
        removed = {}
        cleanup_pending = False
        for collection in USER_COLLECTIONS:
            try:
                result = await db[collection].delete_many({"user_id": user_id})
                removed[collection] = result.deleted_count
            except Exception:
                # The identity is already deleted and cannot authenticate. Keep
                # the API result explicit so clients do not retry as if deletion
                # had failed; an operator can safely retry this idempotent cleanup.
                cleanup_pending = True
                log.exception("Legacy Mongo cleanup failed for deleted identity %s in %s", user_id, collection)
                break
        return {"ok": True, "removed": removed, "cleanup_pending": cleanup_pending}

    return r
