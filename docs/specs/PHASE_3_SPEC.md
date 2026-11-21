# PHASE 3 SPEC — Frontend SPA & Keycloak PKCE Integration

**Status:** Active  
**Target Branch:** `feature/phase-3-frontend-spa`  
**Depends On:** Phase 2 Backend Decomposition (Green)

---

## 1. Objective
Build a lightweight **React + Vite + TypeScript** Single Page Application (SPA) served behind the Nginx Edge LB (`https://localhost/`), authenticated via **Keycloak OIDC Authorization Code Flow with PKCE** (`zd-frontend` client), and enforcing role-based UI views (`admin` vs `field_worker`).

---

## 2. Container & Networking Boundaries
- **Build:** Multi-stage Docker build (`node:22-alpine` → `nginx:1.27-alpine`).
- **Container Name:** `zd-frontend`
- **Network:** `edge-net` only (no direct access to `app-net` or `data-net`; all API traffic routes through `https://localhost/api/v1/...`).
- **RAM Cap:** `64m`
- **Nginx Edge Routing:** Replace the Phase 1 placeholder `location /` in `infra/nginx/nginx.conf` with a reverse proxy to `http://zd-frontend:80`.

---

## 3. Authentication & Role-Based UI
- Uses official **`keycloak-js`** against `https://localhost/auth` (realm: `zero-dose-realm`, client: `zd-frontend`, PKCE `S256`).
- Automatically refreshes tokens before expiry and attaches `Authorization: Bearer <token>` to all `/api/v1/*` requests.
- **Role-Aware Views:**
  - **Dashboard (All roles):** Live KPI cards from `GET /api/v1/analytics/summary`.
  - **District Coverage Table (`admin` only):** Calls `GET /api/v1/metrics/coverage`.
  - **Campaigns (`admin` create/update, `field_worker` read-only):** Calls `/api/v1/campaigns`.
  - **Field Tracking (All roles):** Register zero-dose beneficiaries (`POST /api/v1/beneficiaries`) and log vaccination doses (`POST /api/v1/vaccinations`).

---

## 4. Phase 3 Verification Gate (GitHub Actions CI)
Phase 3 is complete when `.github/workflows/verify-phase3.yml` passes:
1. **Frontend Build & Typecheck:** `npm ci && npm run build` passes cleanly with zero TypeScript errors.
2. **Full 8-Container Stack Boot:** `docker compose --profile full up -d --build` boots all 8 containers healthy under RAM limits.
3. **Edge SPA Serving:** `curl -sk https://localhost/` returns `200 OK` with the compiled React `index.html` (`<div id="root">`).
4. **Phase 2 E2E Regression:** All API RBAC and functional checks continue to pass.