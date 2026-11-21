import asyncio
import os
from typing import Any

import httpx
import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, status

from services.shared.auth import UserContext, require_roles

from .replay import compute_round_transitions, replay_child_timeline

CAMPAIGN_SERVICE_URL = os.getenv(
    "CAMPAIGN_SERVICE_URL", "http://campaign-service:8001"
)
TRACKING_SERVICE_URL = os.getenv(
    "TRACKING_SERVICE_URL", "http://tracking-service:8002"
)

app = FastAPI(title="Zero-Dose Analytics Service", version="1.0.0")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "analytics-service"}


async def _fetch_json(url: str, authorization: str) -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers={"Authorization": authorization})
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Upstream error from {url}: {resp.status_code}",
            )
        return resp.json()


@app.get("/api/v1/analytics/summary")
async def analytics_summary(
    authorization: str = Header(default=""),
    _: UserContext = Depends(require_roles("admin", "field_worker")),
):
    campaigns, beneficiaries, vaccinations = await asyncio.gather(
        _fetch_json(f"{CAMPAIGN_SERVICE_URL}/api/v1/campaigns", authorization),
        _fetch_json(f"{TRACKING_SERVICE_URL}/api/v1/beneficiaries", authorization),
        _fetch_json(f"{TRACKING_SERVICE_URL}/api/v1/vaccinations", authorization),
    )

    total_campaigns = len(campaigns)
    total_target = sum(c.get("target_beneficiaries", 0) for c in campaigns)
    total_beneficiaries = len(beneficiaries)
    total_vaccinations = len(vaccinations)
    unique_vaccinated = len({v["beneficiary_id"] for v in vaccinations})
    coverage_pct = (
        round((unique_vaccinated / total_beneficiaries) * 100, 2)
        if total_beneficiaries > 0
        else 0.0
    )

    return {
        "total_campaigns": total_campaigns,
        "total_target_beneficiaries": total_target,
        "total_beneficiaries": total_beneficiaries,
        "total_vaccinations": total_vaccinations,
        "unique_vaccinated_beneficiaries": unique_vaccinated,
        "coverage_percentage": coverage_pct,
    }


@app.get("/api/v1/metrics/coverage")
async def district_coverage_metrics(
    authorization: str = Header(default=""),
    _: UserContext = Depends(require_roles("admin")),
):
    campaigns, beneficiaries, vaccinations = await asyncio.gather(
        _fetch_json(f"{CAMPAIGN_SERVICE_URL}/api/v1/campaigns", authorization),
        _fetch_json(f"{TRACKING_SERVICE_URL}/api/v1/beneficiaries", authorization),
        _fetch_json(f"{TRACKING_SERVICE_URL}/api/v1/vaccinations", authorization),
    )

    if not campaigns and not beneficiaries:
        return {"districts": []}

    camp_df = (
        pd.DataFrame(campaigns)
        if campaigns
        else pd.DataFrame(columns=["district", "target_beneficiaries"])
    )
    ben_df = (
        pd.DataFrame(beneficiaries)
        if beneficiaries
        else pd.DataFrame(columns=["id", "district"])
    )
    vax_ids = {v["beneficiary_id"] for v in vaccinations}

    districts = sorted(
        set(camp_df["district"].dropna().tolist())
        | set(ben_df["district"].dropna().tolist())
    )

    result = []
    for district in districts:
        target = (
            int(camp_df[camp_df["district"] == district]["target_beneficiaries"].sum())
            if not camp_df.empty
            else 0
        )
        d_bens = ben_df[ben_df["district"] == district] if not ben_df.empty else ben_df
        registered = len(d_bens)
        vaccinated = (
            int(d_bens["id"].isin(vax_ids).sum()) if not d_bens.empty else 0
        )
        coverage = round((vaccinated / registered) * 100, 2) if registered > 0 else 0.0
        result.append(
            {
                "district": district,
                "target_beneficiaries": target,
                "registered_beneficiaries": registered,
                "vaccinated_beneficiaries": vaccinated,
                "coverage_percentage": coverage,
            }
        )

    return {"districts": result}


@app.get("/api/v1/analytics/transitions")
async def round_transitions(
    authorization: str = Header(default=""),
    _: UserContext = Depends(require_roles("admin", "field_worker")),
):
    rounds, encounters = await asyncio.gather(
        _fetch_json(f"{CAMPAIGN_SERVICE_URL}/api/v1/rounds", authorization),
        _fetch_json(f"{TRACKING_SERVICE_URL}/api/v1/encounters", authorization),
    )
    return await asyncio.to_thread(compute_round_transitions, rounds, encounters)


@app.get("/api/v1/analytics/children/{child_id}/timeline")
async def child_timeline(
    child_id: str,
    authorization: str = Header(default=""),
    _: UserContext = Depends(require_roles("admin", "field_worker")),
):
    rounds, encounters = await asyncio.gather(
        _fetch_json(f"{CAMPAIGN_SERVICE_URL}/api/v1/rounds", authorization),
        _fetch_json(
            f"{TRACKING_SERVICE_URL}/api/v1/encounters?child_id={child_id}",
            authorization,
        ),
    )
    if not encounters:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No encounters found for child {child_id}",
        )
    return await asyncio.to_thread(replay_child_timeline, child_id, rounds, encounters)