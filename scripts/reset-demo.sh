#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

REPO_DIR="${HOME}/zero-dose-tracking-platform"
LOG_FILE="${HOME}/demo-reset.log"

cd "$REPO_DIR"

echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Starting demo data reset..." | tee -a "$LOG_FILE"

# Truncate only application tables in tracking_db and campaign_db (leaves keycloak_db & alembic_version untouched)
for db in tracking_db campaign_db; do
  echo "Truncating tables in ${db}..." | tee -a "$LOG_FILE"
  docker exec -i zd-postgres sh -c "psql -U \"\$POSTGRES_USER\" -d \"${db}\" -v ON_ERROR_STOP=1" <<'SQL' >> "$LOG_FILE" 2>&1
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename <> 'alembic_version'
    )
    LOOP
        EXECUTE format('TRUNCATE TABLE public.%I RESTART IDENTITY CASCADE;', r.tablename);
    END LOOP;
END $$;
SQL
done

# Ensure migrations are up to date and re-seed clean demo data
docker exec zd-campaign-service alembic upgrade head >> "$LOG_FILE" 2>&1
docker exec zd-campaign-service python -m app.seed >> "$LOG_FILE" 2>&1

docker exec zd-tracking-service alembic upgrade head >> "$LOG_FILE" 2>&1
docker exec zd-tracking-service python -m app.seed >> "$LOG_FILE" 2>&1

echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Demo data reset complete." | tee -a "$LOG_FILE"