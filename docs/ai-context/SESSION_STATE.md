# SESSION STATE

**Repository:** `SR-TechSandbox/zero-dose-tracking-platform`  
**Current Phase:** Phase 2 — Backend Decomposition (Ready to Start)  
**Active Branch:** `main` (cut `feat/phase-2-backend-services` next)  
**Last Updated:** 2026-11-21

## Completed
- [x] **Phase 0:** Repo setup, `ARCHITECTURE_LOCK.md`, `SESSION_STATE.md`, `BRIEF.md`, `CODEOWNERS`
- [x] **Phase 1: Core Infrastructure**
  - PostgreSQL 18 with isolated databases (`campaign_db`, `tracking_db`, `keycloak_db`) and least-privilege roles (`infra/postgres/init-databases.sh`)
  - Keycloak 26.0 auto-imported `zero-dose-realm`, `admin` & `field_worker` roles, `zd-frontend` (PKCE) & `zd-cli-test` clients
  - Kong OSS 3.8 (DB-less) declarative routing, CORS, and local rate-limiting (`100 req/min`)
  - Nginx 1.27 Edge LB with TLS termination, `/healthz`, and reverse proxying to Kong & Keycloak
  - Docker Compose profiles (`core`, `auth`, `full`) with strict RAM caps & `Makefile`
  - Verified green via GitHub Actions CI (`.github/workflows/verify-phase1.yml`)
  - Repo hygiene verified via `git ls-files` (no secrets or local certs tracked)

## Pending (Phase 2 Build Queue)
- [ ] `docs/specs/PHASE_2_SPEC.md`
- [ ] `services/shared/` (Keycloak JWKS caching & RBAC FastAPI middleware)
- [ ] `services/campaign-service/` (FastAPI + SQLAlchemy + Alembic + pytest)
- [ ] `services/tracking-service/` (FastAPI + SQLAlchemy + Alembic + pytest)
- [ ] `services/analytics-service/` (FastAPI + Pandas + pytest)
- [ ] Wire all 3 services into `docker-compose.yml` (`full` profile) + Phase 2 CI workflow

## Known Constraints / Notes
- Local dev environment uses Windows Git Bash without Docker installed; **GitHub Actions CI** is the primary runtime/verification runner ($0 on public repo).
- `MSYS_NO_PATHCONV=1` is required in `infra/nginx/generate-certs.sh` for Git Bash compatibility.