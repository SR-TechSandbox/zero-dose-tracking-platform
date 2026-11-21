# ARCHITECTURE LOCK — Zero-Dose Tracking Campaign

**Repo:** `https://github.com/SR-TechSandbox/zero-dose-tracking-campaign`  
**Rules:** AI-Only engineering (specs, code, verification) | Open-Source & Open Standards First | **$0/month cost**  
**Workflow:** Monorepo, service-by-service, file-by-file. Do NOT alter the locked stack or ADRs below.

## Locked Tech Stack
- **Edge Load Balancer:** Nginx (`nginx:1.27-alpine`) — TLS termination (self-signed locally), static SPA serving, reverse proxy `/api/*` -> Kong.
- **API Gateway:** Kong Gateway OSS (`kong:3.8` in **DB-less mode**, `KONG_DATABASE=off`) — declarative `kong.yml` in Git, L7 routing, rate limiting, CORS. *(Tuned: `KONG_NGINX_WORKER_PROCESSES=1`, `KONG_MEM_CACHE_SIZE=64m`)*
- **IAM (AuthN/AuthZ):** Keycloak (`quay.io/keycloak/keycloak:26.0`) — OAuth 2.0 / OIDC (PKCE for SPA), JWT issuance, realm `zero-dose-realm`, roles: `admin`, `field_worker`.
- **Token Validation Pattern (ADR-002):** Kong OSS handles routing/rate-limits/CORS; FastAPI services validate Keycloak JWTs locally via a shared Python JWKS caching middleware (avoids paid Kong Enterprise OIDC plugin).
- **Backend Microservices:** Python 3.12 (`python:3.12-slim`) + FastAPI + SQLAlchemy + Alembic + `pytest`:
  1. `campaign-service` (port `8001`): Campaigns CRUD (`campaign_db`).
  2. `tracking-service` (port `8002`): Beneficiaries, zero-dose logic, vaccination logs (`tracking_db`). Co-located to avoid distributed Sagas (ADR-004).
  3. `analytics-service` (port `8003`): `/metrics`, `/analytics`, CSV/Excel exports (Pandas).
- **Frontend:** React + Vite (`node:20-alpine` build -> `nginx:1.27-alpine` serve), OIDC PKCE client.
- **Database:** Single PostgreSQL 18 container (`postgres:18-alpine`) hosting isolated DBs: `campaign_db`, `tracking_db`, `keycloak_db` (ADR-003).
- **Phase 5 (Deferred):** Apache Kafka (KRaft mode, no ZooKeeper), Prometheus, Grafana.

## Zero-Cost & Resource Constraints
- **Compose Profiles:** `core` (~650 MB), `auth` (~1.35 GB), `full` (~1.75 GB), `scale` (~2.6 GB).
- **Mandatory Memory Caps:** Keycloak `512m` (`-Xms256m -Xmx512m`), Kong `256m`, Postgres `256m`, each FastAPI service `192m`, Nginx `64m`.
- **Testing:** Local open-source runtime (Podman/Colima/Docker) for inner loop; public GitHub Actions (`ci-e2e.yml`) for free full-stack E2E.

## Monorepo Layout
- `docs/ai-context/` (`ARCHITECTURE_LOCK.md`, `SESSION_STATE.md`)
- `docs/specs/` (Phase specifications)
- `infra/` (`nginx/`, `kong/`, `keycloak/`, `postgres/`)
- `services/` (`shared/`, `campaign-service/`, `tracking-service/`, `analytics-service/`)
- `frontend/`
- Root: `docker-compose.yml`, `.env.example`, `Makefile`, `README.md`
