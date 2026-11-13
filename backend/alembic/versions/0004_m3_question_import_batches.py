"""Add durable question import batch IDs for atomic import undo.

Revision ID: 0004_m3_question_import_batches
Revises: 0003_m3_catalog_content
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004_m3_question_import_batches"
down_revision: Union[str, None] = "0003_m3_catalog_content"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("import_batch", sa.String(36), nullable=True))
    op.create_index("ix_questions_import_batch", "questions", ["import_batch"])


def downgrade() -> None:
    op.drop_index("ix_questions_import_batch", table_name="questions")
    op.drop_column("questions", "import_batch")
