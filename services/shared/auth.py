import os
import time
from typing import Callable, Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import RSAAlgorithm
from pydantic import BaseModel

# JWKS_URL = os.getenv(
#     "JWKS_URL",
#     "http://zd-keycloak:8080/realms/zero-dose-realm/protocol/openid-connect/certs",
# )
JWKS_URL = os.getenv(
    "JWKS_URL",
    "http://zd-keycloak:8080/auth/realms/zero-dose-realm/protocol/openid-connect/certs",
)
JWT_ISSUER = os.getenv(
    "JWT_ISSUER",
    "https://localhost/auth/realms/zero-dose-realm",
)
JWKS_CACHE_TTL_SECONDS = int(os.getenv("JWKS_CACHE_TTL_SECONDS", "600"))

bearer_scheme = HTTPBearer(auto_error=False)


class UserContext(BaseModel):
    sub: str
    username: str
    email: Optional[str] = None
    roles: list[str] = []
    raw_token: str


class JWKSCache:
    """In-memory JWKS cache with TTL and auto-refresh on unknown key ID (kid)."""

    def __init__(self, jwks_url: str = JWKS_URL, ttl: int = JWKS_CACHE_TTL_SECONDS):
        self.jwks_url = jwks_url
        self.ttl = ttl
        self._keys: dict[str, dict] = {}
        self._expires_at: float = 0.0

    def _fetch_jwks(self) -> None:
        try:
            response = httpx.get(self.jwks_url, timeout=5.0)
            response.raise_for_status()
            jwks = response.json()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to fetch JWKS from identity provider: {exc}",
            ) from exc

        self._keys = {
            key["kid"]: key for key in jwks.get("keys", []) if "kid" in key
        }
        self._expires_at = time.monotonic() + self.ttl

    def get_signing_key(self, kid: str):
        now = time.monotonic()
        if not self._keys or now >= self._expires_at or kid not in self._keys:
            self._fetch_jwks()

        jwk_data = self._keys.get(kid)
        if not jwk_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unknown signing key (kid)",
            )
        return RSAAlgorithm.from_jwk(jwk_data)


jwks_cache = JWKSCache()


def verify_jwt(token: str) -> UserContext:
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token header missing key ID (kid)",
            )

        public_key = jwks_cache.get_signing_key(kid)
        payload = jwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            issuer=JWT_ISSUER,
            options={"verify_aud": False},
        )
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc

    roles = payload.get("realm_access", {}).get("roles", [])
    return UserContext(
        sub=payload.get("sub", ""),
        username=payload.get("preferred_username", ""),
        email=payload.get("email"),
        roles=roles,
        raw_token=token,
    )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> UserContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    return verify_jwt(credentials.credentials)


def require_roles(*allowed_roles: str) -> Callable[[UserContext], UserContext]:
    """FastAPI dependency enforcing Keycloak realm_access.roles."""

    def _role_checker(user: UserContext = Depends(get_current_user)) -> UserContext:
        if not any(role in user.roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return user

    return _role_checker