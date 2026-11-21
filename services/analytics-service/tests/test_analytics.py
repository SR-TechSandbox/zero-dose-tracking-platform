import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from app import main as analytics_main  # noqa: E402
from services.shared.auth import UserContext, get_current_user  # noqa: E402

client = TestClient(analytics_main.app)


def _as_role(role: str):
    analytics_main.app.dependency_overrides[get_current_user] = lambda: UserContext(
        sub="u-1", username=f"{role}.user", roles=[role], raw_token="fake-token"
    )


@pytest.fixture(autouse=True)
def mock_upstreams(monkeypatch):
    def fake_fetch(url: str, token: str):
        if url.endswith("/api/v1/campaigns"):
            return [{"id": "c1", "district": "Mysuru", "target_beneficiaries": 100}]
        if url.endswith("/api/v1/beneficiaries"):
            return [
                {"id": "b1", "campaign_id": "c1", "district": "Mysuru"},
                {"id": "b2", "campaign_id": "c1", "district": "Mysuru"},
            ]
        if url.endswith("/api/v1/vaccinations"):
            return [{"id": "v1", "beneficiary_id": "b1", "vaccine_name": "DTP1"}]
        return []

    monkeypatch.setattr(analytics_main, "_fetch_json", fake_fetch)
    yield
    analytics_main.app.dependency_overrides.clear()


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["service"] == "analytics-service"


def test_summary_for_field_worker():
    _as_role("field_worker")
    resp = client.get("/api/v1/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_campaigns"] == 1
    assert data["total_beneficiaries"] == 2
    assert data["total_vaccinations"] == 1
    assert data["coverage_percentage"] == 1.0


def test_district_metrics_blocked_for_field_worker():
    _as_role("field_worker")
    resp = client.get("/api/v1/metrics/coverage")
    assert resp.status_code == 403


def test_district_metrics_for_admin():
    _as_role("admin")
    resp = client.get("/api/v1/metrics/coverage")
    assert resp.status_code == 200
    districts = resp.json()["districts"]
    assert len(districts) == 1
    assert districts[0]["district"] == "Mysuru"
    assert districts[0]["vaccinated_beneficiaries"] == 1