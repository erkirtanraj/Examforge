#!/usr/bin/env python3
"""Read-only reconciliation of Mongo collections against the ef_documents staging table.

Run after mongo_to_mysql_staging.py. This script never writes to either database.
It checks collection row counts, staged IDs, and payload JSON validity. It does not
prove that BSON types or application behaviour are preserved by the JSON staging layer.
"""
from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict

from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from mongo_to_mysql_staging import COLLECTIONS


async def main() -> int:
    mongo_url = os.getenv("MONGO_URL")
    mongo_db = os.getenv("MONGO_DB_NAME") or os.getenv("DB_NAME")
    mysql_url = os.getenv("DATABASE_URL", "")
    if not mongo_url or not mongo_db:
        raise SystemExit("Set MONGO_URL and MONGO_DB_NAME (or DB_NAME).")
    if not mysql_url.startswith(("mysql+asyncmy://", "mysql+aiomysql://")):
        raise SystemExit("Set DATABASE_URL to a mysql+asyncmy:// or mysql+aiomysql:// URL.")

    client = AsyncIOMotorClient(mongo_url)
    engine = create_async_engine(mysql_url, pool_pre_ping=True, pool_recycle=1800)
    failures = []
    summary = []

    try:
        async with engine.connect() as conn:
            exists = await conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_name = 'ef_documents'
            """))
            if exists.scalar_one() != 1:
                raise SystemExit("ef_documents does not exist. Run the staging importer first.")

            for collection in COLLECTIONS:
                source = client[mongo_db][collection]
                source_count = await source.count_documents({})
                staged_count_result = await conn.execute(
                    text("SELECT COUNT(*) FROM ef_documents WHERE collection_name=:name"),
                    {"name": collection},
                )
                staged_count = staged_count_result.scalar_one()

                source_ids = set()
                async for doc in source.find({}, {"_id": 1, "id": 1}):
                    key = str(doc.get("id", doc.get("_id", "")))
                    if key:
                        source_ids.add(key)
                    else:
                        failures.append(f"{collection}: source document missing id/_id")

                staged_ids = set()
                invalid_json = 0
                offset = 0
                while True:
                    rows = (await conn.execute(text("""
                        SELECT id, payload FROM ef_documents
                        WHERE collection_name=:name
                        ORDER BY id LIMIT 500 OFFSET :offset
                    """), {"name": collection, "offset": offset})).all()
                    if not rows:
                        break
                    for row in rows:
                        staged_ids.add(row.id)
                        try:
                            if isinstance(row.payload, (str, bytes, bytearray)):
                                json.loads(row.payload)
                            elif not isinstance(row.payload, (dict, list)):
                                invalid_json += 1
                        except (TypeError, ValueError):
                            invalid_json += 1
                    offset += len(rows)

                missing = source_ids - staged_ids
                extra = staged_ids - source_ids
                ok = source_count == staged_count and not missing and not extra and invalid_json == 0
                summary.append({
                    "collection": collection,
                    "source_count": source_count,
                    "staged_count": staged_count,
                    "missing_ids": len(missing),
                    "extra_ids": len(extra),
                    "invalid_json": invalid_json,
                    "ok": ok,
                })
                if not ok:
                    failures.append(
                        f"{collection}: source={source_count}, staged={staged_count}, "
                        f"missing_ids={len(missing)}, extra_ids={len(extra)}, invalid_json={invalid_json}"
                    )

        print(json.dumps({"ok": not failures, "collections": summary, "failures": failures}, indent=2))
        return 0 if not failures else 2
    finally:
        client.close()
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
