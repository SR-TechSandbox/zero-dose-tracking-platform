# Zero-Dose Tracking Platform

## Overview
A multi-service platform for tracking zero-dose children, multi-round field encounters, sequential vaccination doses, and round-to-round immunization transitions across campaign rounds.

## Architecture
* **Edge & Auth:** Nginx (TLS termination), Kong API Gateway, Keycloak (`zero-dose-realm`, OIDC with `admin` and `field_worker` roles)
* **Services:** `campaign-service`, `tracking-service`, `analytics-service` (FastAPI)
* **Frontend:** React + TypeScript SPA served via Nginx
* **Data:** PostgreSQL 18 (`zd-postgres`)
* **Hosting:** Docker Compose (`--profile full`) on Oracle Cloud VM, exposed via Cloudflare Quick Tunnel (`*.trycloudflare.com`)

## Key Capabilities & Fixes Included
* **Multi-Round Field Encounter Logging (`POST /api/v1/encounters`)**:
  * Supports logging field visits from the **Field Tracking** tab with `device_id` (`"web-field-ui"` from the web UI).
  * Maps visit outcomes to `vaccinated_since_last` and `vaccinated_elsewhere`:
    * `Vaccinated (Campaign)`
    * `Vaccinated Elsewhere (External)`
    * `Not Vaccinated (Still Zero-Dose / Correction)`
    * `Child Unavailable / Not Home (No Status Change)`
* **Sequential Dose Progression (`POST /api/v1/vaccinations`)**:
  * Enforces strict `1 → 2 → 3` dose ordering per beneficiary and vaccine.
  * Returns `409 Conflict` on out-of-order doses or attempts beyond Dose 3, with UI controls locking completed doses and stepping to the next valid dose.
* **Round Transitions & Timeline Replay (`analytics-service`)**:
  * Replays child encounters chronologically across rounds (`R1 → R2 → R3`) to compute transitions, remaining zero-dose counts, per-round status, and audit trails.
  * Uses natural numeric child ID ordering (`C001`, `C002`, …, `C015`, `C060`) across round transitions, child selectors, and timeline replay.
  * Defensively normalizes round IDs and argument ordering in `compute_round_transitions` and `replay_child_timeline`.

## Display Name Configuration
To update the platform display name across the UI, login screen, and documentation, edit these locations:

| Location | File | Line / Field to Update |
| :--- | :--- | :--- |
| **Browser Tab Title** | `frontend/index.html` | `<title>Zero-Dose Tracking Platform</title>` |
| **App Topbar Header** | `frontend/src/App.tsx` | `<h1>Zero-Dose Tracking Platform</h1>` |
| **Keycloak Login Screen** | `infra/keycloak/realm-export.json` | `"displayName": "Zero-Dose Tracking Platform"` |
| **Repo / Freeze Docs** | `README.md` & `FREEZE.md` | `# Zero-Dose Tracking Platform` |

To update the live Keycloak realm display name without re-importing the realm:

```bash
docker exec zd-keycloak /opt/keycloak/bin/kcadm.sh update realms/zero-dose-realm \
  -s 'displayName=Zero-Dose Tracking Platform'
```

## Oracle VM Deployment Runbook

### 1. Pull Updates & Rebuild (Preserving `docker-compose.demo.yml`)
```bash
cd ~/zero-dose-tracking-platform
cp docker-compose.demo.yml /tmp/docker-compose.demo.yml.bak
git fetch origin
git reset --hard origin/main
cp /tmp/docker-compose.demo.yml.bak docker-compose.demo.yml
docker compose -f docker-compose.yml -f docker-compose.demo.yml --profile full up -d --build
```

### 2. Restart Cloudflare Quick Tunnel & Update Keycloak Redirect URIs
Whenever `cloudflared` restarts and generates a new `*.trycloudflare.com` URL, run these commands on the Oracle VM:

```bash
# 1. Restart Quick Tunnel and capture the new URL
pkill -f cloudflared || true
nohup cloudflared tunnel --url https://127.0.0.1:443 --no-tls-verify > ~/cloudflared.log 2>&1 &
sleep 4
NEW_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' ~/cloudflared.log | head -n 1)
echo "New Tunnel URL: $NEW_URL"

# 2. Authenticate kcadm.sh (replace <KEYCLOAK_ADMIN_PASSWORD> with your .env value)
docker exec zd-keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080/auth --realm master \
  --user kc_admin --password '<KEYCLOAK_ADMIN_PASSWORD>'

# 3. Update zd-frontend valid redirect URIs and web origins in Keycloak
CLIENT_UUID=$(docker exec zd-keycloak /opt/keycloak/bin/kcadm.sh get clients \
  -r zero-dose-realm -q clientId=zd-frontend --fields id --format csv --noquotes | tr -d '\r')

docker exec zd-keycloak /opt/keycloak/bin/kcadm.sh update "clients/$CLIENT_UUID" \
  -r zero-dose-realm \
  -s "redirectUris=[\"${NEW_URL}/*\",\"https://127.0.0.1/*\",\"http://localhost:5173/*\"]" \
  -s "webOrigins=[\"${NEW_URL}\",\"https://127.0.0.1\",\"http://localhost:5173\"]"
```

## Resilience & Crash Recovery
* Docker Compose container restart policies (`unless-stopped` / `on-failure`) automatically restart crashed service containers.
* Brief `502`/`503` windows can still occur during container restarts or under sustained overload without memory caps, rate limiting, or a managed `cloudflared` systemd unit.
* Check active restart policies on the VM:

```bash
docker inspect -f '{{.Name}}: RestartPolicy={{.HostConfig.RestartPolicy.Name}} MaxRetry={{.HostConfig.RestartPolicy.MaximumRetryCount}}' \
  zd-analytics-service zd-tracking-service zd-campaign-service zd-frontend zd-kong zd-nginx zd-keycloak zd-postgres
```

## Automated 6-Hour Demo Reset
The demo database is reset every 6 hours using `scripts/reset-demo.sh` so test entries are cleared and the seeded 60-child, 3-round dataset is restored without restarting Keycloak or the Cloudflare tunnel.

Enable and schedule the reset job on the Oracle VM:

```bash
chmod +x ~/zero-dose-tracking-platform/scripts/reset-demo.sh
~/zero-dose-tracking-platform/scripts/reset-demo.sh

(crontab -l 2>/dev/null | grep -v 'reset-demo.sh'; echo '0 */6 * * * /home/ubuntu/zero-dose-tracking-platform/scripts/reset-demo.sh') | crontab -
crontab -l
```