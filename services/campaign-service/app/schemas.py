from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    district: str = Field(..., min_length=2, max_length=120)
    target_beneficiaries: int = Field(..., ge=0)
    status: Literal["planned", "active", "completed"] = "active"


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    target_beneficiaries: Optional[int] = Field(None, ge=0)
    status: Optional[Literal["planned", "active", "completed"]] = None


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    district: str
    target_beneficiaries: int
    status: str
    created_by: str
    created_at: datetime