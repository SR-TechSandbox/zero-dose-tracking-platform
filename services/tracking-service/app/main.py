from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.shared.auth import UserContext, require_roles

from .database import get_db
from .models import Beneficiary, Vaccination
from .schemas import (
    BeneficiaryCreate,
    BeneficiaryOut,
    VaccinationCreate,
    VaccinationOut,
)

app = FastAPI(title="Zero-Dose Tracking Service", version="1.0.0")


@app.get("/healthz")
def healthz(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "service": "tracking-service"}


@app.get("/api/v1/beneficiaries", response_model=list[BeneficiaryOut])
def list_beneficiaries(
    campaign_id: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_roles("admin", "field_worker")),
):
    query = db.query(Beneficiary)
    if campaign_id:
        query = query.filter(Beneficiary.campaign_id == campaign_id)
    if district:
        query = query.filter(Beneficiary.district == district)
    return query.order_by(Beneficiary.created_at.desc()).all()


@app.post(
    "/api/v1/beneficiaries",
    response_model=BeneficiaryOut,
    status_code=status.HTTP_201_CREATED,
)
def create_beneficiary(
    payload: BeneficiaryCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(require_roles("admin", "field_worker")),
):
    beneficiary = Beneficiary(
        campaign_id=payload.campaign_id,
        full_name=payload.full_name,
        age_months=payload.age_months,
        district=payload.district,
        registered_by=user.username,
    )
    db.add(beneficiary)
    db.commit()
    db.refresh(beneficiary)
    return beneficiary


@app.get("/api/v1/vaccinations", response_model=list[VaccinationOut])
def list_vaccinations(
    beneficiary_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_roles("admin", "field_worker")),
):
    query = db.query(Vaccination)
    if beneficiary_id:
        query = query.filter(Vaccination.beneficiary_id == beneficiary_id)
    return query.order_by(Vaccination.administered_at.desc()).all()


@app.post(
    "/api/v1/vaccinations",
    response_model=VaccinationOut,
    status_code=status.HTTP_201_CREATED,
)
def log_vaccination(
    payload: VaccinationCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(require_roles("admin", "field_worker")),
):
    beneficiary = (
        db.query(Beneficiary).filter(Beneficiary.id == payload.beneficiary_id).first()
    )
    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found"
        )

    vaccination = Vaccination(
        beneficiary_id=payload.beneficiary_id,
        vaccine_name=payload.vaccine_name,
        dose_number=payload.dose_number,
        administered_by=user.username,
    )
    db.add(vaccination)
    db.commit()
    db.refresh(vaccination)
    return vaccination