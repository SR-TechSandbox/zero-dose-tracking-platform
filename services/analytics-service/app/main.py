import os
from typing import Any

import httpx
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, status

from services.shared.auth import UserContext, require_roles

CAMPAIGN_SERVICE_URL = os.getenv("CAMPAIGN_SERVICE_URL", "http://campaign-service:8001")
TRACKING_SERVICE_URL = os.getenv("TRACKING_SERVICE_URL", "http://tracking-service:8002")

app = FastAPI(title="Zero-Dose Analytics Service", version="1.0.0")


def _fetch_json(url: str, token: str) -> list[dict[str, Any]]:
    try:
        resp = httpx.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream error from {url}: {exc.response.status_code}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to reach upstream service {url}: {exc}",
        ) from exc


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "analytics-service"}


@app.get("/api/v1/analytics/summary")
def analytics_summary(
    user: UserContext = Depends(require_roles("admin", "field_worker")),
):
    campaigns = _fetch_json(f"{CAMPAIGN_SERVICE_URL}/api/v1/campaigns", user.raw_token)
    beneficiaries = _fetch_json(
        f"{TRACKING_SERVICE_URL}/api/v1/beneficiaries", user.raw_token
    )
    vaccinations = _fetch_json(
        f"{TRACKING_SERVICE_URL}/api/v1/vaccinations", user.raw_token
    )

    total_target = sum(c.get("target_beneficiaries", 0) for c in campaigns)
    vaccinated_ids = {v["beneficiary_id"] for v in vaccinations}
    coverage_pct = (
        round((len(vaccinated_ids) / total_target) * 100, 2) if total_target > 0 else 0.0
    )

    return {
        "total_campaigns": len(campaigns),
        "total_target_beneficiaries": total_target,
        "total_beneficiaries": len(beneficiaries),
        "total_vaccinations": len(vaccinations),
        "unique_vaccinated_beneficiaries": len(vaccinated_ids),
        "coverage_percentage": coverage_pct,
    }


@app.get("/api/v1/metrics/coverage")
def district_coverage_metrics(
    user: UserContext = Depends(require_roles("admin")),
):
    campaigns = _fetch_json(f"{CAMPAIGN_SERVICE_URL}/api/v1/campaigns", user.raw_token)
    beneficiaries = _fetch_json(
        f"{TRACKING_SERVICE_URL}/api/v1/beneficiaries", user.raw_token
    )
    vaccinations = _fetch_json(
        f"{TRACKING_SERVICE_URL}/api/v1/vaccinations", user.raw_token
    )

    if not campaigns:
        return {"districts": []}

    camp_df = pd.DataFrame(campaigns)
    targets_by_district = (
        camp_df.groupby("district", as_index=False)["target_beneficiaries"].sum()
    )

    if beneficiaries:
        ben_df = pd.DataFrame(beneficiaries)
        reg_by_district = (
            ben_df.groupby("district", as_index=False)["id"]
            .count()
            .rename(columns={"id": "registered_beneficiaries"})
        )
        vaccinated_ids = {v["beneficiary_id"] for v in vaccinations}
        ben_df["is_vaccinated"] = ben_df["id"].isin(vaccinated_ids)
        vax_by_district = (
            ben_df.groupby("district", as_index=False)["is_vaccinated"]
            .sum()
            .rename(columns={"is_vaccinated": "vaccinated_beneficiaries"})
        )
    else:
        reg_by_district = pd.DataFrame(columns=["district", "registered_beneficiaries"])
        vax_by_district = pd.DataFrame(columns=["district", "vaccinated_beneficiaries"])

    merged = targets_by_district.merge(reg_by_district, on="district", how="left").merge(
        vax_by_district, on="district", how="left"
    )
    merged["registered_beneficiaries"] = (
        merged["registered_beneficiaries"].fillna(0).astype(int)
    )
    merged["vaccinated_beneficiaries"] = (
        merged["vaccinated_beneficiaries"].fillna(0).astype(int)
    )
    merged["coverage_percentage"] = merged.apply(
        lambda r: round(
            (r["vaccinated_beneficiaries"] / r["target_beneficiaries"]) * 100, 2
        )
        if r["target_beneficiaries"] > 0
        else 0.0,
        axis=1,
    )

    return {"districts": merged.to_dict(orient="records")}