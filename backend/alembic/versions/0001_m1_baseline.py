"""M1 baseline: establish Alembic history without application tables.

Revision ID: 0001_m1_baseline
Revises:
Create Date: 2026-11-11
"""
from typing import Sequence, Union

revision: str = "0001_m1_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Application tables are introduced only after the entity model is reviewed.
    pass

def downgrade() -> None:
    pass
