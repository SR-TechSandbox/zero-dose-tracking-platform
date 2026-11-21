import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from services.shared.auth import JWT_ISSUER, UserContext, jwks_cache, require_roles

# Generate an ephemeral RSA keypair for unit testing
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()
_TEST_KID = "test-kid-1"

app = FastAPI()


@app.get("/admin-only")
def admin_route(user: UserContext = Depends(require_roles("admin"))):
    return {"username": user.username, "roles": user.roles}


@app.get("/shared-route")
def shared_route(user: UserContext = Depends(require_roles("admin", "field_worker"))):
    return {"username": user.username}


client = TestClient(app)


def _mint_token(roles: list[str], exp_offset: int = 300, issuer: str = JWT_ISSUER) -> str:
    payload = {
        "sub": "user-123",
        "preferred_username": "test.user",
        "email": "test@zerodose.local",
        "iss": issuer,
        "exp": int(time.time()) + exp_offset,
        "realm_access": {"roles": roles},
    }
    return jwt.encode(
        payload,
        _private_key,
        algorithm="RS256",
        headers={"kid": _TEST_KID},
    )


@pytest.fixture(autouse=True)
def mock_jwks(monkeypatch):
    monkeypatch.setattr(jwks_cache, "get_signing_key", lambda kid: _public_key)


def test_missing_token_returns_401():
    resp = client.get("/admin-only")
    assert resp.status_code == 401


def test_expired_token_returns_401():
    token = _mint_token(roles=["admin"], exp_offset=-10)
    resp = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_wrong_issuer_returns_401():
    token = _mint_token(roles=["admin"], issuer="https://evil.example/realms/fake")
    resp = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_field_worker_blocked_from_admin_route_403():
    token = _mint_token(roles=["field_worker"])
    resp = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_admin_allowed_on_admin_route_200():
    token = _mint_token(roles=["admin"])
    resp = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "test.user"


def test_field_worker_allowed_on_shared_route_200():
    token = _mint_token(roles=["field_worker"])
    resp = client.get("/shared-route", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200