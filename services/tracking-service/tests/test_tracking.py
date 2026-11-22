import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from services.shared.auth import UserContext, get_current_user  # noqa: E402

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        sub="w-1", username="worker", roles=["field_worker"], raw_token="fake"
    )
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["service"] == "tracking-service"


def test_register_beneficiary_and_log_vaccination():
    b_resp = client.post(
        "/api/v1/beneficiaries",
        json={
            "campaign_id": "camp-001",
            "full_name": "Aarav Kumar",
            "age_months": 14,
            "district": "Bengaluru Urban",
        },
    )
    assert b_resp.status_code == 201
    beneficiary_id = b_resp.json()["id"]

    v_resp = client.post(
        "/api/v1/vaccinations",
        json={
            "beneficiary_id": beneficiary_id,
            "vaccine_name": "DTP1",
            "dose_number": 1,
        },
    )
    assert v_resp.status_code == 201
    assert v_resp.json()["vaccine_name"] == "DTP1"

    list_b = client.get("/api/v1/beneficiaries?district=Bengaluru%20Urban")
    assert list_b.status_code == 200
    assert len(list_b.json()) == 1

    list_v = client.get(f"/api/v1/vaccinations?beneficiary_id={beneficiary_id}")
    assert list_v.status_code == 200
    assert len(list_v.json()) == 1


def test_vaccination_for_unknown_beneficiary_returns_404():
    resp = client.post(
        "/api/v1/vaccinations",
        json={
            "beneficiary_id": "non-existent-id",
            "vaccine_name": "OPV1",
            "dose_number": 1,
        },
    )
    assert resp.status_code == 404