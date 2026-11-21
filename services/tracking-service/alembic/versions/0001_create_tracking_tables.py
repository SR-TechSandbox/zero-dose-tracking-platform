"""create beneficiaries and vaccinations tables

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
        "beneficiaries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("age_months", sa.Integer(), nullable=False),
        sa.Column("district", sa.String(length=120), nullable=False),
        sa.Column("registered_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_beneficiaries_campaign_id", "beneficiaries", ["campaign_id"])
    op.create_index("ix_beneficiaries_district", "beneficiaries", ["district"])

    op.create_table(
        "vaccinations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "beneficiary_id",
            sa.String(length=36),
            sa.ForeignKey("beneficiaries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("vaccine_name", sa.String(length=100), nullable=False),
        sa.Column("dose_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("administered_by", sa.String(length=120), nullable=False),
        sa.Column("administered_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vaccinations_beneficiary_id", "vaccinations", ["beneficiary_id"])


def downgrade() -> None:
    op.drop_index("ix_vaccinations_beneficiary_id", table_name="vaccinations")
    op.drop_table("vaccinations")
    op.drop_index("ix_beneficiaries_district", table_name="beneficiaries")
    op.drop_index("ix_beneficiaries_campaign_id", table_name="beneficiaries")
    op.drop_table("beneficiaries")