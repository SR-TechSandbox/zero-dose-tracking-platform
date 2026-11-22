#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${HOME}/zero-dose-tracking-platform"
LOG_FILE="${HOME}/demo-reset.log"

cd "$REPO_DIR"

echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Starting demo data reset..." | tee -a "$LOG_FILE"

# Truncate only application tables (leaves Keycloak tables untouched)
docker exec -i zd-postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' <<'SQL' >> "$LOG_FILE" 2>&1
DO $$
DECLARE
    tbl text;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'encounters',
        'vaccinations',
        'beneficiaries',
        'rounds',
        'campaigns'
    ]
    LOOP
        IF to_regclass('public.' || tbl) IS NOT NULL THEN
            EXECUTE format('TRUNCATE TABLE public.%I RESTART IDENTITY CASCADE;', tbl);
        END IF;
    END LOOP;
END $$;
SQL

# Ensure migrations are up to date and re-seed clean demo data
docker exec zd-campaign-service alembic upgrade head >> "$LOG_FILE" 2>&1
docker exec zd-campaign-service python -m app.seed >> "$LOG_FILE" 2>&1

docker exec zd-tracking-service alembic upgrade head >> "$LOG_FILE" 2>&1
docker exec zd-tracking-service python -m app.seed >> "$LOG_FILE" 2>&1

echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Demo data reset complete." | tee -a "$LOG_FILE"