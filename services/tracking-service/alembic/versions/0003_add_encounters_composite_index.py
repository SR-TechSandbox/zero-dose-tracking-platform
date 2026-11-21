"""add composite index on encounters

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-22
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_encounters_child_round_recorded",
        "encounters",
        ["child_id", "round_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_encounters_child_round_recorded", table_name="encounters")