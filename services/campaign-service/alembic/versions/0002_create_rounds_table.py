"""create rounds table

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
        "rounds",
        sa.Column("round_id", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("rounds")