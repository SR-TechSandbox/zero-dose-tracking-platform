.PHONY: init up-core up-auth up-full down clean stats seed reset-demo verify-phase1

init:
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example"; fi
	@./infra/nginx/generate-certs.sh

up-core: init
	docker compose --profile core up -d

up-auth: init
	docker compose --profile auth up -d

up-full: init
	docker compose --profile full up -d

down:
	docker compose --profile full down

clean:
	docker compose --profile full down -v

stats:
	docker stats --no-stream

seed:
	docker exec zd-campaign-service python -m app.seed
	docker exec zd-tracking-service python -m app.seed

reset-demo:
	docker exec zd-postgres sh -c 'psql -U "$${POSTGRES_USER:-postgres}" -d campaign_db -c "TRUNCATE TABLE campaigns, rounds RESTART IDENTITY CASCADE;" && psql -U "$${POSTGRES_USER:-postgres}" -d tracking_db -c "TRUNCATE TABLE beneficiaries, vaccinations, encounters RESTART IDENTITY CASCADE;"'
	$(MAKE) seed

verify-phase1:
	@echo "1. Checking Nginx Edge LB (/healthz)..."
	@curl -sk https://localhost/healthz
	@echo "2. Checking Nginx -> Kong routing & rate-limit headers..."
	@curl -skI https://localhost/api/v1/campaigns | grep -iE "HTTP/|X-RateLimit"
	@echo "3. Checking Keycloak JWKS endpoint..."
	@curl -sk https://localhost/auth/realms/zero-dose-realm/protocol/openid-connect/certs | head -c 120 && echo "..."
	@echo "4. Minting Admin JWT from Keycloak..."
	@curl -sk -X POST https://localhost/auth/realms/zero-dose-realm/protocol/openid-connect/token \
		-H "Content-Type: application/x-www-form-urlencoded" \
		-d "client_id=zd-cli-test" \
		-d "username=admin" \
		-d "password=AdminPass123!" \
		-d "grant_type=password" | grep -q "access_token" && echo "JWT minted successfully!"