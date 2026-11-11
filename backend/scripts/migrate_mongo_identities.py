"""Dry-run-first MongoDB -> MySQL identity importer for the M2 migration.

Default mode is read-only. --apply is intentionally restricted to the local
examforge_local database. This script never updates or deletes MongoDB records.
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from mysql_persistence.config import load_mysql_settings
from mysql_persistence.database import create_database_runtime
from mysql_persistence.models import PasswordResetToken, User


VALID_ROLES = {"super_admin", "admin", "teacher", "student", "support"}
VALID_STATUSES = {"active", "suspended"}
VALID_PROVIDERS = {"email", "google"}
HEX_64 = re.compile(r"^[a-fA-F0-9]{64}$")


class ImportPreflightError(ValueError):
    """Raised when source identities cannot be imported without data loss."""


def as_utc_naive(value: Any, field: str, *, required: bool = False) -> datetime | None:
    if value is None or value == "":
        if required:
            raise ImportPreflightError(f"{field} is missing")
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ImportPreflightError(f"{field} is not a valid ISO datetime") from exc
    if not isinstance(value, datetime):
        raise ImportPreflightError(f"{field} must be a datetime")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def normalize_user(source: dict[str, Any]) -> dict[str, Any]:
    user_id = source.get("id")
    if not isinstance(user_id, str) or not re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        user_id,
    ):
        raise ImportPreflightError("user id must be a UUID string")
    email = source.get("email")
    if not isinstance(email, str) or "@" not in email.strip():
        raise ImportPreflightError(f"user {user_id} has an invalid email")
    email = email.strip().lower()
    name = source.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
        raise ImportPreflightError(f"user {user_id} has a missing or invalid name")
    role = source.get("role", "student")
    status = source.get("status", "active")
    provider = source.get("auth_provider") or ("email" if source.get("password_hash") else "google")
    if role not in VALID_ROLES:
        raise ImportPreflightError(f"user {user_id} has unsupported role")
    if status not in VALID_STATUSES:
        raise ImportPreflightError(f"user {user_id} has unsupported status")
    if provider not in VALID_PROVIDERS:
        raise ImportPreflightError(f"user {user_id} has unsupported auth provider")
    password_hash = source.get("password_hash")
    if password_hash is not None and not isinstance(password_hash, str):
        raise ImportPreflightError(f"user {user_id} has invalid password hash field")
    tokens_valid_after = source.get("tokens_valid_after", 0) or 0
    if isinstance(tokens_valid_after, bool) or not isinstance(tokens_valid_after, (int, float)):
        raise ImportPreflightError(f"user {user_id} has invalid session invalidation timestamp")
    created_at = as_utc_naive(source.get("created_at"), f"user {user_id} created_at", required=True)
    return {
        "id": user_id,
        "name": name.strip(),
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "status": status,
        "auth_provider": provider,
        "phone": str(source.get("phone") or "")[:20],
        "avatar_url": source.get("avatar_url"),
        "created_at": created_at,
        "updated_at": as_utc_naive(source.get("updated_at"), f"user {user_id} updated_at"),
        "created_by": source.get("created_by"),
        "tokens_valid_after": int(tokens_valid_after),
        "password_reset_at": as_utc_naive(source.get("password_reset_at"), f"user {user_id} password_reset_at"),
        "password_reset_by": source.get("password_reset_by"),
    }


def normalize_reset_token(source: dict[str, Any], user_ids: set[str]) -> dict[str, Any]:
    token_hash = source.get("token_hash")
    if not isinstance(token_hash, str) or not HEX_64.fullmatch(token_hash):
        raise ImportPreflightError("reset token has invalid token_hash")
    user_id = source.get("user_id")
    if user_id not in user_ids:
        raise ImportPreflightError("reset token references a user absent from the source users collection")
    if not isinstance(source.get("used", False), bool):
        raise ImportPreflightError(f"reset token for user {user_id} has invalid used flag")
    return {
        "token_hash": token_hash.lower(),
        "user_id": user_id,
        "used": source.get("used", False),
        "created_at": as_utc_naive(source.get("created_at"), "reset token created_at", required=True),
        "expires_at": as_utc_naive(source.get("expires_at"), "reset token expires_at", required=True),
        "used_at": as_utc_naive(source.get("used_at"), "reset token used_at"),
    }


def build_import_plan(user_docs: list[dict], token_docs: list[dict]) -> dict:
    users: list[dict] = []
    errors: list[str] = []
    for index, doc in enumerate(user_docs):
        try:
            users.append(normalize_user(doc))
        except ImportPreflightError as exc:
            errors.append(f"user row {index + 1}: {exc}")
    ids = [u["id"] for u in users]
    emails = [u["email"] for u in users]
    for value, label in ((ids, "user id"), (emails, "normalized email")):
        duplicates = [v for v, count in Counter(value).items() if count > 1]
        if duplicates:
            errors.append(f"duplicate {label} values in MongoDB source: {len(duplicates)}")
    id_set = set(ids)
    for user in users:
        for field in ("created_by", "password_reset_by"):
            ref = user[field]
            if ref is not None and ref not in id_set:
                errors.append(f"user {user['id']} has {field} reference outside source users")
    tokens: list[dict] = []
    for index, doc in enumerate(token_docs):
        try:
            tokens.append(normalize_reset_token(doc, id_set))
        except ImportPreflightError as exc:
            errors.append(f"reset-token row {index + 1}: {exc}")
    hashes = [t["token_hash"] for t in tokens]
    if len(set(hashes)) != len(hashes):
        errors.append("duplicate token_hash values in MongoDB source")
    return {"users": users, "tokens": tokens, "errors": errors}


async def run(apply: bool) -> int:
    mongo_url = __import__("os").environ.get("MONGO_URL")
    mongo_db_name = __import__("os").environ.get("DB_NAME")
    if not mongo_url or not mongo_db_name:
        raise ImportPreflightError("MONGO_URL and DB_NAME must be configured in backend/.env")
    settings = load_mysql_settings()
    if apply and settings.database_name != "examforge_local":
        raise ImportPreflightError(
            "Refusing --apply: target database must be exactly examforge_local; production imports are not supported by this tool"
        )

    mongo = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=10000)
    runtime = create_database_runtime(settings)
    try:
        await mongo.admin.command("ping")
        source_db = mongo[mongo_db_name]
        user_docs = await source_db.users.find({}, {"_id": 0}).to_list(length=None)
        token_docs = await source_db.password_reset_tokens.find({}, {"_id": 0}).to_list(length=None)
        plan = build_import_plan(user_docs, token_docs)

        async with runtime.sessions() as session, session.begin():
            target_users = (await session.scalars(select(User))).all()
            target_tokens = (await session.scalars(select(PasswordResetToken))).all()
            target_by_id = {u.id: u for u in target_users}
            target_by_email = {u.email.strip().lower(): u for u in target_users}
            target_by_hash = {t.token_hash.lower(): t for t in target_tokens}

            new_users, already_users = [], 0
            for source in plan["users"]:
                by_id = target_by_id.get(source["id"])
                by_email = target_by_email.get(source["email"])
                if by_id:
                    same = all(getattr(by_id, key) == source[key] for key in (\n                        "name", "email", "password_hash", "role", "status", "auth_provider", "phone",\n                        "avatar_url", "created_at", "updated_at", "created_by", "tokens_valid_after",\n                        "password_reset_at", "password_reset_by",\n                    ))
                    if not same:
                        plan["errors"].append(f"target MySQL identity conflict for user id {source['id']}")
                    else:
                        already_users += 1
                elif by_email:
                    plan["errors"].append(f"target MySQL email already belongs to a different user: {source['email']}")
                else:
                    new_users.append(source)

            new_tokens, already_tokens = [], 0
            for source in plan["tokens"]:
                existing = target_by_hash.get(source["token_hash"])
                if existing:
                    same = all(getattr(existing, key) == source[key] for key in (\n                        "user_id", "used", "created_at", "expires_at", "used_at",\n                    ))
                    if not same:
                        plan["errors"].append("target MySQL reset-token record conflicts with MongoDB source")
                    else:
                        already_tokens += 1
                else:
                    new_tokens.append(source)

            print("IDENTITY MIGRATION PREFLIGHT")
            print(f"Mongo users: {len(user_docs)} | valid: {len(plan['users'])}")
            print(f"Mongo reset tokens: {len(token_docs)} | valid: {len(plan['tokens'])}")
            print(f"MySQL users already present: {already_users} | new: {len(new_users)}")
            print(f"MySQL reset tokens already present: {already_tokens} | new: {len(new_tokens)}")
            print(f"Conflicts/errors: {len(plan['errors'])}")
            for issue in plan["errors"][:30]:
                print(f" - {issue}")
            if len(plan["errors"]) > 30:
                print(f" - ... {len(plan['errors']) - 30} additional issues")
            if plan["errors"]:
                print("RESULT: BLOCKED. Resolve all conflicts; no records were written.")
                return 2
            if not apply:
                print("RESULT: DRY RUN ONLY. No database records were written.")
                print("Review this report, then use --apply only against examforge_local.")
                return 0

            # Insert user rows with self-references deferred to the second pass.\n            for row in new_users:\n                row = dict(row)\n                row["created_by"] = None\n                row["password_reset_by"] = None\n                session.add(User(**row))\n            await session.flush()\n            for row in new_users:\n                if row["created_by"] or row["password_reset_by"]:\n                    await session.execute(\n                        User.__table__.update().where(User.id == row["id"]).values(\n                            created_by=row["created_by"], password_reset_by=row["password_reset_by"]\n                        )\n                    )\n            for row in new_tokens:\n                session.add(PasswordResetToken(**row))\n            await session.flush()

            print("RESULT: IMPORT COMMITTED to examforge_local.")
            print("MongoDB source records were not modified or deleted.")
            return 0
    except IntegrityError:
        print("RESULT: BLOCKED by a database integrity conflict. Transaction rolled back.")
        return 2
    finally:
        mongo.close()
        await runtime.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Read-only preflight (default)")
    mode.add_argument("--apply", action="store_true", help="Import only into examforge_local")
    args = parser.parse_args()
    try:
        return asyncio.run(run(apply=args.apply))
    except ImportPreflightError as exc:
        print(f"Preflight configuration error: {exc}")
        return 2
    except Exception as exc:
        # Avoid printing exception strings that could contain connection details.
        print(f"Migration failed safely ({type(exc).__name__}); inspect local configuration/logs.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
