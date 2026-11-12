"""Explicit, bounded retention cleanup for MySQL password-reset token rows.

Dry-run is the default. Deletion requires both --apply and an exact
--confirm-database match for the configured MySQL database.
Run from backend after configuring backend/.env:
    python scripts/purge_password_reset_tokens.py
    python scripts/purge_password_reset_tokens.py --retention-days 30
    python scripts/purge_password_reset_tokens.py --apply --confirm-database examforge_local
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import and_, delete, func, or_, select

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")

from mysql_persistence.config import load_mysql_settings
from mysql_persistence.database import create_database_runtime
from mysql_persistence.models import PasswordResetToken


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer greater than zero") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def cleanup_criteria(cutoff: datetime):
    """Select only tokens that have been terminal for at least the retention period."""
    return or_(
        and_(
            PasswordResetToken.used.is_(True),
            func.coalesce(PasswordResetToken.used_at, PasswordResetToken.created_at) < cutoff,
        ),
        and_(
            PasswordResetToken.used.is_(False),
            PasswordResetToken.expires_at < cutoff,
        ),
    )


def validate_apply_confirmation(database_name: str, confirmation: str | None) -> None:
    """Require an exact database-name acknowledgement before destructive work."""
    if not confirmation or confirmation != database_name:
        raise ValueError(
            "Refusing --apply: pass --confirm-database with the exact configured "
            f"database name ({database_name!r})"
        )


async def count_eligible_tokens(runtime, cutoff: datetime) -> int:
    async with runtime.sessions() as session:
        value = await session.scalar(
            select(func.count(PasswordResetToken.id)).where(cleanup_criteria(cutoff))
        )
        return int(value or 0)


async def purge_eligible_tokens(runtime, cutoff: datetime, batch_size: int) -> int:
    """Delete eligible rows in independently committed, bounded batches."""
    deleted_total = 0
    criteria = cleanup_criteria(cutoff)

    while True:
        async with runtime.sessions() as session, session.begin():
            token_ids = list(await session.scalars(
                select(PasswordResetToken.id)
                .where(criteria)
                .order_by(PasswordResetToken.id)
                .limit(batch_size)
            ))
            if not token_ids:
                break

            # Recheck eligibility in the DELETE in case a row changed after selection.
            result = await session.execute(
                delete(PasswordResetToken).where(
                    PasswordResetToken.id.in_(token_ids),
                    criteria,
                )
            )
            deleted_total += max(0, int(result.rowcount or 0))

    return deleted_total


async def run(args: argparse.Namespace) -> int:
    settings = load_mysql_settings()
    if args.apply:
        validate_apply_confirmation(settings.database_name, args.confirm_database)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(days=args.retention_days)
    runtime = create_database_runtime(settings)
    try:
        eligible = await count_eligible_tokens(runtime, cutoff)
        print(f"Database: {settings.database_name}")
        print(f"Retention: {args.retention_days} days")
        print(f"Cutoff (UTC): {cutoff.isoformat(sep=' ')}")
        print(f"Eligible password-reset token rows: {eligible}")

        if not args.apply:
            print("DRY RUN ONLY — no rows were deleted.")
            print("To delete these rows, rerun with --apply --confirm-database <exact database name>.")
            return eligible

        deleted = await purge_eligible_tokens(runtime, cutoff, args.batch_size)
        print(f"Deleted rows: {deleted}")
        print("Cleanup completed.")
        return deleted
    finally:
        await runtime.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Purge old, unusable MySQL password-reset token rows.")
    parser.add_argument("--retention-days", type=positive_int, default=30)
    parser.add_argument("--batch-size", type=positive_int, default=500)
    parser.add_argument("--apply", action="store_true", help="perform deletion; default is a read-only dry run")
    parser.add_argument(
        "--confirm-database",
        help="exact configured MySQL database name; required together with --apply",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        asyncio.run(run(args))
    except (ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
