from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BeneficiaryCreate(BaseModel):
    campaign_id: str = Field(..., min_length=1, max_length=36)
    full_name: str = Field(..., min_length=2, max_length=150)
    age_months: int = Field(..., ge=0, le=240)
    district: str = Field(..., min_length=2, max_length=120)


class BeneficiaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    full_name: str
    age_months: int
    district: str
    registered_by: str
    created_at: datetime


class VaccinationCreate(BaseModel):
    beneficiary_id: str = Field(..., min_length=1, max_length=36)
    vaccine_name: str = Field(..., min_length=2, max_length=100)
    dose_number: int = Field(1, ge=1, le=10)


class VaccinationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    beneficiary_id: str
    vaccine_name: str
    dose_number: int
    administered_by: str
    administered_at: datetime