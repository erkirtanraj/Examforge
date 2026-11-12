from datetime import datetime
import argparse

import pytest
from sqlalchemy.dialects import mysql
from sqlalchemy import select

from mysql_persistence.models import PasswordResetToken
from scripts.purge_password_reset_tokens import (
    build_parser,
    cleanup_criteria,
    positive_int,
    validate_apply_confirmation,
)


def test_cleanup_criteria_targets_used_and_expired_tokens_only():
    cutoff = datetime(2026, 1, 1, 0, 0, 0)
    statement = select(PasswordResetToken.id).where(cleanup_criteria(cutoff))
    sql = str(statement.compile(dialect=mysql.dialect())).lower()

    assert "used_at" in sql
    assert "expires_at" in sql
    assert "password_reset_tokens.used" in sql
    assert "coalesce(password_reset_tokens.used_at, password_reset_tokens.created_at)" in sql
    assert "password_reset_tokens.id" in sql


def test_used_tokens_without_used_at_fall_back_to_created_at_for_retention():
    cutoff = datetime(2026, 1, 1, 0, 0, 0)
    statement = select(PasswordResetToken.id).where(cleanup_criteria(cutoff))
    sql = str(statement.compile(dialect=mysql.dialect())).lower()

    # Legacy imported rows may have used=True but no used_at timestamp.
    # created_at provides a deterministic retention anchor for those rows.
    assert "coalesce(password_reset_tokens.used_at, password_reset_tokens.created_at)" in sql


def test_apply_requires_exact_configured_database_confirmation():
    validate_apply_confirmation("examforge_local", "examforge_local")

    with pytest.raises(ValueError, match="exact configured database name"):
        validate_apply_confirmation("examforge_local", None)

    with pytest.raises(ValueError, match="exact configured database name"):
        validate_apply_confirmation("examforge_local", "examforge")


def test_cleanup_cli_is_dry_run_by_default_and_supports_explicit_apply():
    parser = build_parser()
    dry_run = parser.parse_args([])
    assert dry_run.apply is False
    assert dry_run.retention_days == 30
    assert dry_run.batch_size == 500

    apply = parser.parse_args([
        "--apply", "--confirm-database", "examforge_local",
        "--retention-days", "45", "--batch-size", "100",
    ])
    assert apply.apply is True
    assert apply.confirm_database == "examforge_local"
    assert apply.retention_days == 45
    assert apply.batch_size == 100


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_cleanup_numeric_arguments_must_be_positive_integers(value):
    with pytest.raises(argparse.ArgumentTypeError):
        positive_int(value)
