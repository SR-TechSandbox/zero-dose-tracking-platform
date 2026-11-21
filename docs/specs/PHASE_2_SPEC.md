# PHASE 2 SPEC — Backend Decomposition (FastAPI Microservices)

**Status:** Active  
**Target Branch:** `feat/phase-2-backend-services`  
**Depends On:** Phase 1 Core Infrastructure (Green)

---

## 1. Objective
Decompose the monolithic prototype into three independently deployable **FastAPI** microservices behind Kong OSS, sharing a lightweight Keycloak JWKS/RBAC module while enforcing strict **database-per-service isolation** and **192 MB RAM caps** per container.

---

## 2. Architecture & Service Boundaries

| Service | Port | Network(s) | Database | RAM Cap | Primary Responsibility |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `campaign-service` | `8001` | `app-net`, `data-net` | `campaign_db` | `192m` | Manage vaccination campaigns, districts, and targets |
| `tracking-service` | `8002` | `app-net`, `data-net` | `tracking_db` | `192m` | Register zero-dose beneficiaries and log vaccinations |
| `analytics-service` | `8003` | `app-net` | None (Stateless) | `192m` | Aggregate coverage KPIs via internal HTTP calls to Campaign & Tracking services |

**Strict Isolation Rules:**
- No cross-database SQL queries or foreign keys. `tracking_db` stores `campaign_id` as a logical reference (UUID/string).
- `analytics-service` has **no database credentials** and does not attach to `data-net`. It forwards the caller's `Authorization: Bearer <token>` header to `campaign-service` and `tracking-service` over `app-net`.
- All containers run on `python:3.12-slim` as a non-root user with a single `uvicorn` worker to stay comfortably under `192m`.

---

## 3. Shared Auth & RBAC Module (`services/shared/`)
Every service validates Keycloak JWTs locally using cached public keys (no per-request round-trip to Keycloak):
- **JWKS Caching:** Fetches keys from `JWKS_URL` (`http://zd-keycloak:8080/realms/zero-dose-realm/protocol/openid-connect/certs`) and caches them in memory (TTL: 10 minutes, auto-refresh on unknown `kid`).
- **Validation:** Verifies RS256 signature, `exp`, and `iss` (`JWT_ISSUER`).
- **RBAC Dependency:** `require_roles("admin")` or `require_roles("admin", "field_worker")` inspects `realm_access.roles` inside the JWT payload.
  - Missing/invalid token → `401 Unauthorized`
  - Valid token, insufficient role → `403 Forbidden`

---

## 4. API Contracts & RBAC Matrix

### A. `campaign-service` (`/api/v1/campaigns`)
| Method | Endpoint | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/healthz` | Public | Liveness & DB connectivity check |
| `GET` | `/api/v1/campaigns` | `admin`, `field_worker` | List all campaigns |
| `POST` | `/api/v1/campaigns` | `admin` | Create a new campaign |
| `GET` | `/api/v1/campaigns/{id}` | `admin`, `field_worker` | Fetch campaign details |
| `PATCH` | `/api/v1/campaigns/{id}` | `admin` | Update campaign status/target |

### B. `tracking-service` (`/api/v1/beneficiaries`, `/api/v1/vaccinations`)
| Method | Endpoint | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/healthz` | Public | Liveness & DB connectivity check |
| `GET` | `/api/v1/beneficiaries` | `admin`, `field_worker` | List beneficiaries (filterable by `campaign_id`, `district`) |
| `POST` | `/api/v1/beneficiaries` | `admin`, `field_worker` | Register a zero-dose beneficiary |
| `GET` | `/api/v1/vaccinations` | `admin`, `field_worker` | List vaccination records |
| `POST` | `/api/v1/vaccinations` | `admin`, `field_worker` | Log a vaccination dose for a beneficiary |

### C. `analytics-service` (`/api/v1/analytics`, `/api/v1/metrics`)
| Method | Endpoint | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/healthz` | Public | Liveness check |
| `GET` | `/api/v1/analytics/summary` | `admin`, `field_worker` | Total campaigns, beneficiaries, doses given, and coverage % |
| `GET` | `/api/v1/metrics/coverage` | `admin` | District-level zero-dose coverage breakdown |

---

## 5. Database Migrations
- `campaign-service` and `tracking-service` each manage their own schema via **Alembic** (`alembic upgrade head` runs automatically in the container entrypoint before `uvicorn` starts).

---

## 6. Phase 2 Verification Gate (GitHub Actions CI)
Phase 2 is complete when `.github/workflows/verify-phase2.yml` passes all checks:
1. **Unit Tests:** `pytest` passes for `shared`, `campaign-service`, `tracking-service`, and `analytics-service`.
2. **Full Stack Boot:** `docker compose --profile full up -d --build` boots all 7 containers healthy under RAM limits.
3. **E2E Security & Functional Flow (via `https://localhost/api/v1/...`):**
   - Unauthenticated `GET /api/v1/campaigns` → `401`
   - `field_worker` `POST /api/v1/campaigns` → `403`
   - `admin` `POST /api/v1/campaigns` → `201`
   - `field_worker` `POST /api/v1/beneficiaries` → `201`
   - `field_worker` `POST /api/v1/vaccinations` → `201`
   - `admin` `GET /api/v1/analytics/summary` → `200` (returns `campaigns >= 1`, `beneficiaries >= 1`, `vaccinations >= 1`)