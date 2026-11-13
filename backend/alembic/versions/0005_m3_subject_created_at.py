"""Preserve subject creation timestamps in the legacy API contract.

Revision ID: 0005_m3_subject_created_at
Revises: 0004_m3_question_import_batches
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005_m3_subject_created_at"
down_revision: Union[str, None] = "0004_m3_question_import_batches"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subjects", sa.Column(
        "created_at", sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
    ))


def downgrade() -> None:
    op.drop_column("subjects", "created_at")
