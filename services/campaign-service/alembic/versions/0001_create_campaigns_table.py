"""create campaigns table

Revision ID: 0001
Revises:
Create Date: 2026-11-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("district", sa.String(length=120), nullable=False),
        sa.Column("target_beneficiaries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_campaigns_district", "campaigns", ["district"])


def downgrade() -> None:
    op.drop_index("ix_campaigns_district", table_name="campaigns")
    op.drop_table("campaigns")