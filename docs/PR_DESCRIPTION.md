# Pull Request Handoff

Use this document as the PR description body. Attach the final commit SHA and
repository link before opening the PR. Detailed Tier 1 findings are in
[`BUG_FIX_REPORT.md`](BUG_FIX_REPORT.md).

## Summary

This change hardens authentication and todo ownership, adds regression coverage,
improves cache isolation and invalidation, documents the todo-sharing design,
adds the optional tags/filtering/bulk-actions vertical slice, and adds
Docker/indexing improvements required by the assessment.

## Change Areas

### Security and correctness

- Reject expired, tampered, and wrong-class JWT credentials.
- Rotate refresh tokens once, persist only token hashes, revoke sessions on
  logout, and revoke a token family when a rotated credential is replayed.
- Scope todo reads and mutations to the authenticated owner.
- Add user-owned tags with case-insensitive uniqueness, ownership-safe mapping,
  filtered pagination, and atomic bulk status updates.
- Return a generic login failure for unknown users and bad passwords.
- Restrict CORS to configured browser origins.
- Scope Redis list keys by user and pagination parameters.
- Include every todo filter in Redis keys and invalidate all affected user keys
  after todo, tag, mapping, and bulk mutations.

The reviewable finding table, with location, severity, impact, remediation, and
verification for each issue, is maintained in
[`BUG_FIX_REPORT.md`](BUG_FIX_REPORT.md).

### Testing

- Backend tests cover auth rejection, refresh rotation/replay, session
  revocation, ownership, partial updates, completion toggles, and
  create/update/delete cache invalidation.
- Playwright covers the full browser journey, cross-user isolation, and the
  Tier 4 tags/filter/bulk flow.
- Manual execution matrix is in [`MANUAL_TEST_PLAN.md`](MANUAL_TEST_PLAN.md).
- Tier 4 API/UI behavior and test coverage are documented in
  [`TODO_TAGS_BULK.md`](TODO_TAGS_BULK.md).
- `npm audit --omit=dev` reports zero known vulnerabilities after the lockfile
  refresh.

### Infrastructure and data

- PostgreSQL and Redis healthchecks gate backend startup.
- Production compose requires explicit secrets and protects Redis with a password.
- Multi-stage images and Docker ignore files reduce build context and runtime size.
- Alembic adds owner/order/status indexes; benchmark procedure is in
  [`DATABASE_PERFORMANCE.md`](DATABASE_PERFORMANCE.md).
- `/health/live` and `/health/ready` separate process liveness from PostgreSQL/
  Redis readiness; Docker healthchecks use the dependency-aware probe.
- Request IDs are echoed in `X-Request-ID` and emitted in structured JSON HTTP
  logs for incident correlation.
- GitHub Actions runs backend/frontend quality gates, dependency audits,
  migration application, Docker builds, and Playwright against the compose stack.

## Verification

Run from the repository root:

```bash
cd backend
pytest tests/ -v
python -m black --check app tests
python -m flake8 app tests

cd ../frontend
npm run lint
npx tsc -b
npm run build
npm run test:e2e
```

Record the date, commit SHA, environment, and result for each command. The E2E
suite requires the backend and frontend stack to be running.

Current local verification:

- Backend: 33 tests passed (including refresh rotation, replay detection,
  server-side session revocation, tag ownership, filtering, cache isolation,
  and atomic bulk updates).
- Coverage: 65.96% with the CI gate set to 60%.
- `pip-audit -r requirements.txt`: no known vulnerabilities found.
- Black and Flake8: passed.
- ESLint and TypeScript: passed.
- Vite production build: passed.
- Playwright E2E: 3 tests passed (journey, cross-user isolation, and Tier 4
  tags/filter/bulk flow).
- Docker Compose development and production configurations: valid.
- Health probes: `/health/live` and dependency-aware `/health/ready` are covered
  by backend tests; production-like Docker healthchecks target readiness.
- PostgreSQL benchmark: executed on PostgreSQL 16.14 with 10,000 users and
  1,000,000 todos; median timings and plans are recorded in
  [`DATABASE_PERFORMANCE.md`](DATABASE_PERFORMANCE.md).

## Security and Data Review

- No access token, password, or personal data is committed.
- Cache keys contain the authenticated user identifier.
- Unauthorized item lookups return a non-disclosing `404`/`403` response.
- Production secrets are supplied through environment configuration, not image layers.
- Refresh-session details and residual risks are documented in
  [`SECURITY_HARDENING.md`](SECURITY_HARDENING.md).

## Deployment and Rollback

1. Apply the Alembic migration during a maintenance window or use a concurrent
   index migration strategy for large production tables.
2. Deploy the backend and frontend together because query/cache contracts changed.
3. Verify `/health/live`, `/health/ready`, service healthchecks, login, and an
   owner todo smoke test.
4. Roll back application images first if needed; only downgrade the migration
   after confirming no newer code depends on the indexes.

## Known Limitations

- Development Redis is intentionally open; production compose requires a password,
  while TLS remains an infrastructure responsibility.
- Benchmark timings are environment-specific evidence, not a production SLA;
  rerun them after major hardware, PostgreSQL, or data-distribution changes.

## AI Disclosure

AI assistance was used for code review, test design, documentation drafting, and
implementation support. All generated changes were reviewed locally, formatted,
and validated with the commands listed above. The final owner remains responsible
for security review, deployment decisions, and test evidence.
