#!/usr/bin/env python3
"""Resumable staging importer. Never changes or deletes source MongoDB records."""
from __future__ import annotations
import argparse, asyncio, json, os
from datetime import date, datetime
from decimal import Decimal
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

COLLECTIONS = ("users", "password_reset_tokens", "categories", "subjects", "questions",
 "test_series", "tests", "test_attempts", "test_results", "courses", "course_sections",
 "lessons", "lesson_progress", "lesson_positions", "certificates", "study_materials",
 "orders", "entitlements", "coupons", "settings", "pages", "announcement_stats")

def json_default(value):
    if isinstance(value, (datetime, date)): return value.isoformat()
    if isinstance(value, Decimal): return str(value)
    return str(value)

async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--collections", nargs="*", choices=COLLECTIONS, default=list(COLLECTIONS))
    p.add_argument("--batch-size", type=int, default=200)
    args = p.parse_args()
    if not 1 <= args.batch_size <= 2000: p.error("--batch-size must be 1..2000")
    mongo_url, mongo_db = os.getenv("MONGO_URL"), os.getenv("MONGO_DB_NAME") or os.getenv("DB_NAME")
    mysql_url = os.getenv("DATABASE_URL", "")
    if not mongo_url or not mongo_db: raise SystemExit("Set MONGO_URL and MONGO_DB_NAME.")
    if not mysql_url.startswith(("mysql+asyncmy://", "mysql+aiomysql://")):
        raise SystemExit("Set DATABASE_URL to a mysql+asyncmy:// or mysql+aiomysql:// URL.")
    if not args.dry_run and os.getenv("ALLOW_STAGING_IMPORT") != "YES":
        raise SystemExit("Review the dry run first, then set ALLOW_STAGING_IMPORT=YES.")
    client = AsyncIOMotorClient(mongo_url)
    engine = create_async_engine(mysql_url, pool_pre_ping=True, pool_recycle=1800)
    try:
        async with engine.begin() as c:
            if not args.dry_run:
                await c.execute(text("""CREATE TABLE IF NOT EXISTS ef_documents (
                collection_name VARCHAR(64) NOT NULL, id VARCHAR(128) NOT NULL,
                payload JSON NOT NULL, created_at DATETIME(6) NULL, updated_at DATETIME(6) NULL,
                PRIMARY KEY (collection_name, id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""))
        counts = {}
        for name in args.collections:
            count, batch = 0, []
            async for doc in client[mongo_db][name].find({}):
                key = str(doc.get("id", doc.get("_id", "")))
                if not key: raise ValueError(f"{name}: document without id/_id")
                batch.append({"collection_name": name, "id": key,
                    "payload": json.dumps(doc, default=json_default, ensure_ascii=False, separators=(",", ":"))})
                count += 1
                if len(batch) >= args.batch_size:
                    if not args.dry_run:
                        async with engine.begin() as c:
                            await c.execute(text("""INSERT INTO ef_documents(collection_name,id,payload)
                            VALUES(:collection_name,:id,:payload)
                            ON DUPLICATE KEY UPDATE payload=VALUES(payload)"""), batch)
                    batch.clear()
            if batch and not args.dry_run:
                async with engine.begin() as c:
                    await c.execute(text("""INSERT INTO ef_documents(collection_name,id,payload)
                    VALUES(:collection_name,:id,:payload)
                    ON DUPLICATE KEY UPDATE payload=VALUES(payload)"""), batch)
            counts[name] = count
            print(f"{name}: {count} documents" + (" (dry run)" if args.dry_run else " staged"))
        print(json.dumps({"dry_run": args.dry_run, "counts": counts}, indent=2))
    finally:
        client.close()
        await engine.dispose()

if __name__ == "__main__": asyncio.run(main())
