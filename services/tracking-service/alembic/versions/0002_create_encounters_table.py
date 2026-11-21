"""create encounters table

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "encounters",
        sa.Column("event_id", sa.String(length=32), primary_key=True),
        sa.Column("child_id", sa.String(length=32), nullable=False),
        sa.Column("round_id", sa.String(length=32), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("zero_dose_answer", sa.Boolean(), nullable=True),
        sa.Column("vaccinated_since_last", sa.String(length=16), nullable=True),
        sa.Column("vaccinated_elsewhere", sa.Boolean(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
    )
    op.create_index("ix_encounters_child_id", "encounters", ["child_id"])
    op.create_index("ix_encounters_round_id", "encounters", ["round_id"])
    op.create_index("ix_encounters_recorded_at", "encounters", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_encounters_recorded_at", table_name="encounters")
    op.drop_index("ix_encounters_round_id", table_name="encounters")
    op.drop_index("ix_encounters_child_id", table_name="encounters")
    op.drop_table("encounters")