"""M2 identity and authorization schema.

Revision ID: 0002_m2_identity_authz
Revises: 0001_m1_baseline
Create Date: 2026-11-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_m2_identity_authz"
down_revision: Union[str, None] = "0001_m1_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=20), server_default=sa.text("'student'"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'active'"), nullable=False),
        sa.Column("auth_provider", sa.String(length=20), server_default=sa.text("'email'"), nullable=False),
        sa.Column("phone", sa.String(length=20), server_default=sa.text("''"), nullable=False),
        sa.Column("avatar_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("tokens_valid_after", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("password_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_reset_by", sa.String(length=36), nullable=True),
        sa.CheckConstraint(
            "role IN ('super_admin', 'admin', 'teacher', 'student', 'support')",
            name="ck_users_valid_role",
        ),
        sa.CheckConstraint("status IN ('active', 'suspended')", name="ck_users_valid_status"),
        sa.CheckConstraint(
            "auth_provider IN ('email', 'google')",
            name="ck_users_valid_auth_provider",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_users_created_by_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["password_reset_by"], ["users.id"], name="fk_users_password_reset_by_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_role_status", "users", ["role", "status"], unique=False)

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("used", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_password_reset_tokens_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_password_reset_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
    )
    op.create_index(
        "ix_password_reset_tokens_user_created",
        "password_reset_tokens",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_password_reset_tokens_expires_at",
        "password_reset_tokens",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_expires_at", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_created", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ix_users_role_status", table_name="users")
    op.drop_table("users")
