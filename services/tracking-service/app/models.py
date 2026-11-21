import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    campaign_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    age_months: Mapped[int] = mapped_column(Integer, nullable=False)
    district: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    registered_by: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Vaccination(Base):
    __tablename__ = "vaccinations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    beneficiary_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("beneficiaries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vaccine_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dose_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    administered_by: Mapped[str] = mapped_column(String(120), nullable=False)
    administered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )