#!/usr/bin/env python3
"""Securely create the first ExamForge administrator or rotate an existing admin password.

Examples:
  python backend/create_admin.py --email admin@example.com --name "Site Administrator"
  python backend/create_admin.py --email admin@lms.com --reset-existing

The password is prompted interactively and is never accepted through command-line arguments.
"""
import argparse
import getpass
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Administrator email address")
    parser.add_argument("--name", default="ExamForge Administrator", help="Display name for a new administrator")
    parser.add_argument(
        "--reset-existing",
        action="store_true",
        help="Rotate the password of an existing account and invalidate its sessions",
    )
    args = parser.parse_args()

    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        print("ERROR: Set MONGO_URL and DB_NAME in backend/.env or the environment.", file=sys.stderr)
        return 2

    email = args.email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        print("ERROR: Enter a valid email address.", file=sys.stderr)
        return 2
    if not args.name.strip() or len(args.name.strip()) > 120:
        print("ERROR: Name must be 1–120 characters.", file=sys.stderr)
        return 2

    password = getpass.getpass("New admin password (minimum 10 characters): ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("ERROR: Passwords do not match.", file=sys.stderr)
        return 2
    if len(password) < 10:
        print("ERROR: Password must contain at least 10 characters.", file=sys.stderr)
        return 2
    if len(password.encode("utf-8")) > 72:
        print("ERROR: Password must be 72 UTF-8 bytes or fewer.", file=sys.stderr)
        return 2

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    now = datetime.now(timezone.utc).isoformat()
    try:
        with MongoClient(mongo_url, serverSelectionTimeoutMS=5000) as client:
            client.admin.command("ping")
            db = client[db_name]
            users = db.users
            existing = users.find_one({"email": email}, {"id": 1, "role": 1})
            if existing:
                if not args.reset_existing:
                    print("ERROR: This email already exists. Use --reset-existing to rotate its password.", file=sys.stderr)
                    return 2
                users.update_one(
                    {"id": existing["id"]},
                    {"$set": {
                        "password_hash": password_hash,
                        "tokens_valid_after": int(time.time()) + 1,
                        "password_reset_at": now,
                        "updated_at": now,
                    }},
                )
                print("Account password rotated. Existing sessions have been invalidated.")
                return 0

            if args.reset_existing:
                print("ERROR: No existing admin account was found for that email.", file=sys.stderr)
                return 2
            if users.find_one({"role": {"$in": ["admin", "super_admin"]}}, {"_id": 1}):
                print("ERROR: An administrator already exists. Use the admin UI or --reset-existing for password rotation.", file=sys.stderr)
                return 2
            users.create_index("email", unique=True)
            users.insert_one({
                "id": str(uuid.uuid4()),
                "name": args.name.strip(),
                "email": email,
                "password_hash": password_hash,
                "role": "super_admin",
                "status": "active",
                "auth_provider": "email",
                "avatar_url": None,
                "created_at": now,
                "tokens_valid_after": int(time.time()) + 1,
            })
            print("Initial super administrator created successfully.")
            return 0
    except PyMongoError as exc:
        print(f"ERROR: Database operation failed: {exc.__class__.__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
