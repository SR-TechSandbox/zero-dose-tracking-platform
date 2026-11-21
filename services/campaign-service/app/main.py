from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.shared.auth import UserContext, require_roles

from .database import get_db
from .models import Campaign
from .schemas import CampaignCreate, CampaignOut, CampaignUpdate

app = FastAPI(title="Zero-Dose Campaign Service", version="1.0.0")


@app.get("/healthz")
def healthz(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "service": "campaign-service"}


@app.get("/api/v1/campaigns", response_model=list[CampaignOut])
def list_campaigns(
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_roles("admin", "field_worker")),
):
    return db.query(Campaign).order_by(Campaign.created_at.desc()).all()


@app.post(
    "/api/v1/campaigns",
    response_model=CampaignOut,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(require_roles("admin")),
):
    campaign = Campaign(
        name=payload.name,
        district=payload.district,
        target_beneficiaries=payload.target_beneficiaries,
        status=payload.status,
        created_by=user.username,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@app.get("/api/v1/campaigns/{campaign_id}", response_model=CampaignOut)
def get_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_roles("admin", "field_worker")),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )
    return campaign


@app.patch("/api/v1/campaigns/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_roles("admin")),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)

    db.commit()
    db.refresh(campaign)
    return campaign