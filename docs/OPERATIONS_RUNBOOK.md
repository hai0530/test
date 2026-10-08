# Operations Runbook

This runbook covers the supported local and production-like operating
procedures for the Fabbi Todo API. It deliberately keeps deployment simple:
Docker Compose runs the API, frontend, PostgreSQL, and Redis as one stack.
For a production platform, map the same checks and rollback steps to the
platform's service manager.

## Service Contract

| Endpoint | Purpose | Healthy response |
|---|---|---|
| `GET /health` | Backward-compatible liveness probe | `200 {"status":"healthy"}` |
| `GET /health/live` | Process liveness probe | `200 {"status":"alive"}` |
| `GET /health/ready` | PostgreSQL and Redis readiness probe | `200` with both checks `ok` |

Readiness returns HTTP `503` while either dependency is unavailable. It does
not expose connection strings or exception details. Configure load balancers
to route traffic only after `/health/ready` succeeds; configure orchestrators
to restart a container only from the liveness probe.

## Environment and Secrets

1. Copy `.env.example` to an environment-specific `.env` outside source
   control.
2. Set a randomly generated `JWT_SECRET`, `POSTGRES_PASSWORD`, and
   `REDIS_PASSWORD` before using the production compose file.
3. Set `CORS_ORIGINS` to the exact browser origins that should call the API.
4. Set `VITE_API_URL` to a URL reachable by the browser. It is embedded into
   the frontend image during the build.

The development compose file intentionally exposes PostgreSQL and Redis for
local tooling. Use `docker-compose.prod.yml` in shared environments; it
requires explicit secrets and enables Redis authentication. Never put secrets
in a Dockerfile, image label, committed `.env`, or command pasted into an
issue.

## Start, Stop, and Smoke Test

```bash
docker compose up --build -d
docker compose ps
curl --fail http://localhost:8000/health/ready
```

For a production-like start:

```bash
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml ps
curl --fail http://localhost:8000/health/ready
```

Stop the stack without deleting its database volume:

```bash
docker compose down
```

Use `docker compose down --volumes` only when intentionally discarding local
data, such as in a disposable CI environment.

## Logs and Request Tracing

Application HTTP records are JSON lines containing the request method, path,
status code, duration, and a correlation ID. Every response includes the same
ID in `X-Request-ID`.

```bash
docker compose logs --follow backend
curl -H 'X-Request-ID: incident-2026-01' http://localhost:8000/health/live
```

Use the response header and the `request_id` JSON field to correlate a client
report with backend logs. Tokens, passwords, request bodies, and query string
values are intentionally excluded from request logs.

## Database Migrations

The backend image applies `alembic upgrade head` before starting Uvicorn.
For a controlled rollout, run the migration as a separate release step and
verify the revision before serving traffic:

```bash
docker compose run --rm backend alembic upgrade head
docker compose exec backend alembic current
```

Before a large production migration:

- take and verify a PostgreSQL backup;
- review the generated SQL and expected lock duration;
- use a concurrent index strategy where supported;
- monitor database locks and API readiness during the rollout.

Never downgrade automatically during an incident. First roll back the
application image, confirm that no newer code depends on the migration, and
only then perform a reviewed downgrade or forward-fix migration.

## Backup and Restore Checklist

The named `postgres_data` volume is not a backup. Schedule database backups
outside Docker and test restores regularly. A local logical backup example:

```bash
docker compose exec -T postgres pg_dump -U fabbi -d postgres > backup.sql
cat backup.sql | docker compose exec -T postgres psql -U fabbi -d postgres
```

Use encrypted, access-controlled storage for real backups. Do not commit dump
files or include user data in test artifacts.

## Incident Triage

1. Check `docker compose ps` and `/health/live` to distinguish a process issue
   from a dependency issue.
2. Check `/health/ready` and service logs for PostgreSQL or Redis failures.
3. Search backend logs by `X-Request-ID` when investigating one request.
4. Confirm database connectivity and free disk before restarting services.
5. Roll back the application image if a release caused the regression; retain
   logs and migration revision information for the incident record.

Redis is a cache, so a restart can remove cached todo lists without data loss.
PostgreSQL restarts require backup and recovery procedures if the data volume
is damaged.

## Release Quality Gates

The GitHub Actions workflow in `.github/workflows/ci.yml` runs:

- backend pytest, coverage reporting, Black, Flake8, and `pip-audit`;
- frontend lint, TypeScript/Vite build, and `npm audit`;
- Alembic migration application against PostgreSQL 16;
- development and production Compose validation plus image builds;
- Playwright journeys against the built Docker stack.

Merge only when all required jobs are green. The same commands are available
locally in [`PR_DESCRIPTION.md`](PR_DESCRIPTION.md) and the root
[`GUIDE.md`](../GUIDE.md).
