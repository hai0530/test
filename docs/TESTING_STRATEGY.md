# Testing Strategy

The test suite is organized by failure cost rather than by implementation file.
Security boundaries and data ownership are covered at the API boundary, while
browser tests verify that the most important user journeys remain usable.

## Test Pyramid

| Layer | Tooling | Purpose | Expected scope |
|---|---|---|---|
| Unit/service | `pytest`, isolated service tests | Token parsing, ownership predicates, filter normalization, bulk validation | Fast and broad |
| API integration | `pytest` + `httpx` + SQLite test database | Authentication, CRUD, cache invalidation, migrations/contracts | Every critical endpoint |
| Frontend static | ESLint, TypeScript, Vite | Type safety and predictable builds | Every pull request |
| Browser E2E | Playwright | Register/login, private data isolation, filters and mutations | Critical journeys |
| Operational | Compose config, healthchecks, migration checks, audit tools | Deployment safety and dependency risk | Every pull request/release |

## Required Regression Scenarios

- Expired, tampered, wrong-class, revoked, and replayed JWT credentials are rejected.
- User A cannot read, update, delete, tag, or bulk-update User B's records.
- `completed` can persist in both directions, and partial updates preserve omitted fields.
- Create, update, delete, tag mapping, and bulk mutations invalidate every affected cache variant.
- Case-insensitive duplicate tags are rejected without creating a second row.
- Bulk status updates are atomic when one requested record is unauthorized or invalid.
- Filter query keys include every parameter and do not leak data between users.
- Logout removes browser credentials and user-scoped client cache.

## Test Data Rules

- Use generated unique emails in E2E tests so parallel runs do not collide.
- Use separate browser contexts for cross-user isolation.
- Never commit real credentials, tokens, personal data, or raw production data.
- Keep seed data deterministic enough to reproduce benchmark and migration results.

## Local Verification

```bash
docker compose up --build -d
docker compose run --rm backend pytest tests/ -v
docker compose run --rm backend python -m black --check app tests
docker compose run --rm backend python -m flake8 app tests

cd frontend
npm ci
npm run lint
npx tsc -b
npm run build
npm run test:e2e
```

The CI workflow runs the same checks and stores Playwright traces/reports and
coverage as build artifacts. A failed security scan or migration check blocks a
release even when the application tests pass.
