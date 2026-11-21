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
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _as_role(role: str):
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        sub="u-1", username=f"{role}.user", roles=[role], raw_token="fake"
    )


client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_field_worker_cannot_create_campaign():
    _as_role("field_worker")
    resp = client.post(
        "/api/v1/campaigns",
        json={"name": "Polio Drive", "district": "Bengaluru Urban", "target_beneficiaries": 500},
    )
    assert resp.status_code == 403


def test_admin_crud_and_field_worker_read():
    _as_role("admin")
    create_resp = client.post(
        "/api/v1/campaigns",
        json={"name": "Mission Indradhanush", "district": "Mysuru", "target_beneficiaries": 1200},
    )
    assert create_resp.status_code == 201
    campaign_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/v1/campaigns/{campaign_id}",
        json={"status": "completed", "target_beneficiaries": 1500},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "completed"

    _as_role("field_worker")
    list_resp = client.get("/api/v1/campaigns")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1