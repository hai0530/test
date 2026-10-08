# Manual Test Plan: Authentication, Authorization, and Todo Workflows

**Document status:** Ready for execution

**Owner:** QA / Engineering

**Risk focus:** Account isolation, credential handling, state persistence, and cache consistency

## 1. Objective

This plan verifies the user-facing workflows and security boundaries changed in
the assessment, including the optional tags, filters, and bulk-actions slice.
It complements the automated backend and Playwright suites with repeatable
exploratory checks, explicit evidence fields, and release gates.

## 2. Scope

### In scope

- Registration, login, logout, current-user lookup, refresh rotation, replay
  rejection, and token rejection.
- Todo create, read, update, delete, pagination, and completion state changes.
- Cross-user read, update, and delete isolation.
- Partial update behavior and Redis list-cache invalidation.
- Tag creation, rename, deletion, attachment, and filtering.
- Atomic bulk completion updates and mixed-ownership rejection.
- Service cold start and healthcheck behavior.

### Out of scope

- Todo sharing, which is specified separately in
  [`TODO_SHARING_SPEC.md`](TODO_SHARING_SPEC.md) and is not implemented in this
  release.
- Load testing beyond the database benchmark procedure in
  [`DATABASE_PERFORMANCE.md`](DATABASE_PERFORMANCE.md).
- Browser compatibility outside the supported Chromium-based Playwright run.

## 3. Test Environment

| Item | Value |
|---|---|
| Backend | `http://localhost:8000` |
| Frontend | `http://localhost:3000` |
| API documentation | `http://localhost:8000/docs` |
| Services | PostgreSQL and Redis via `docker compose up --build` |
| Demo account | `demo@test.com` / `Demo@123` |
| Fresh accounts | Create User A and User B through the register flow |

### Environment setup

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend python -m app.db.seed
docker compose ps
```

The backend healthcheck must be `healthy` before UI testing begins. Use the
demo account for smoke checks and fresh accounts for isolation checks so that
existing seed data does not affect expected counts.

## 4. Priority and Severity

| Priority | Meaning |
|---|---|
| P0 | Blocks authentication, data isolation, or release validation |
| P1 | Major workflow or data consistency failure with no practical workaround |
| P2 | Important regression with a limited workaround |
| P3 | Minor usability or documentation defect |

| Severity | Meaning |
|---|---|
| Critical | Unauthorized access, data disclosure, or credential bypass |
| Major | Data loss, incorrect persisted state, or blocked primary workflow |
| Minor | Non-blocking behavior or recoverable presentation issue |

## 5. Test Case Matrix

The **Actual / Evidence** column is intentionally blank for execution. Record
the observed response, screenshot, request ID, or database value and mark the
case `PASS` or `FAIL` after execution.

| ID | Area | Scenario | Preconditions and steps | Expected result | Priority / severity | Actual / evidence |
|---|---|---|---|---|---|---|
| AUTH-01 | Authentication | Register a new account | Open `/register`; submit a new valid email and password. | API returns `201`; tokens are stored; user reaches the dashboard. | P0 / Critical | |
| AUTH-02 | Authentication | Login with valid credentials | Use an existing account on `/login`. | API returns `200`; dashboard loads; `/auth/me` resolves the same user. | P0 / Critical | |
| AUTH-03 | Authentication | Login failure does not enumerate users | Try a wrong password for an existing email, then a nonexistent email. | Both attempts return `401` with the same generic message. | P1 / Major | |
| AUTH-04 | Authentication | Expired access token | Call `GET /api/v1/auth/me` with an expired access token. | Request returns `401`; no user data is returned. | P0 / Critical | |
| AUTH-05 | Authentication | Tampered access token | Change one character in a valid access token and call `/auth/me`. | Request returns `401`. | P0 / Critical | |
| AUTH-06 | Authentication | Refresh token class separation | Send a refresh token in the `Authorization: Bearer` header to `/auth/me`. | Request returns `401`; refresh credentials cannot act as access credentials. | P0 / Critical | |
| AUTH-07 | Authentication | Logout clears client state | Login; create or load a todo; click Logout; use browser back and refresh. | Redirects to login; tokens and cached user data are gone; private todo is not visible. | P1 / Major | |
| AUTH-08 | Authentication | Refresh rotates one-time credential | Capture a refresh request; call `/auth/refresh` twice with the original token. | First call returns new credentials; second returns `401`; the replacement is also revoked after replay detection. | P0 / Critical | |
| AUTH-09 | Authentication | Logout revokes refresh session | Login; send the current refresh token to `/auth/logout`; attempt `/auth/refresh` with it. | Logout returns `200`; refresh returns `401`. | P0 / Critical | |
| TODO-01 | Todo | Create and reload | Login; create a todo with title and description; reload the page. | Todo appears once and both fields persist. | P1 / Major | |
| TODO-02 | Todo | Toggle completion both ways | Create an incomplete todo; check it; uncheck it; reload. | State persists as `true`, then persists as `false`. | P1 / Major | |
| TODO-03 | Todo | Partial title update | Create a todo with a description; edit title only. | Title changes; existing description remains unchanged. | P1 / Major | |
| TODO-04 | Todo | Delete todo | Create a todo; delete it; reload. | API returns `204`; item is absent from the list and direct lookup. | P1 / Major | |
| TAG-01 | Tags | Create and rename a tag | Create a tag; rename it; reload the dashboard. | The tag appears once with the new name and remains owned by the current user. | P1 / Major | |
| TAG-02 | Tags | Case-insensitive duplicate prevention | Create `Work`; attempt to create ` work `. | The second request returns `409`; only one tag is present. | P1 / Major | |
| TAG-03 | Tags | Attach, filter, and detach | Create a tag and todo; attach the tag; select it in the filter; detach it. | The filtered list contains the todo while attached and excludes it after detaching. | P1 / Major | |
| BULK-01 | Bulk actions | Complete and reactivate selected todos | Select multiple owned todos; mark them complete; then mark them active. | Each selected todo persists `true`, then `false`, after reload. | P1 / Major | |
| BULK-02 | Bulk actions | Reject mixed ownership atomically | Submit one owned todo and one other user's todo in one bulk request. | API returns `404`; none of the current user's todos change. | P0 / Critical | |
| AUTHZ-01 | Authorization | User B cannot read User A's todo | User A creates a todo; User B calls `GET /todos/{id}`. | Response is `404` or `403`; no fields are disclosed. | P0 / Critical | |
| AUTHZ-02 | Authorization | User B cannot update User A's todo | User B sends `PUT /todos/{id}` with a changed title. | Response is `404` or `403`; User A's title is unchanged. | P0 / Critical | |
| AUTHZ-03 | Authorization | User B cannot delete User A's todo | User B sends `DELETE /todos/{id}`. | Response is `404` or `403`; User A's todo remains present. | P0 / Critical | |
| CACHE-01 | Caching | Cache is user-scoped | User A and User B each create different todos; request both lists. | Each user receives only their own items, including on a cache hit. | P0 / Critical | |
| CACHE-02 | Caching | Create invalidates list cache | Request an empty list; create a todo; request the same list again. | New item appears without waiting for TTL expiration. | P1 / Major | |
| CACHE-03 | Caching | Update and delete invalidate cache | Populate the list cache; update a title; repeat for delete. | Changed or removed state is visible immediately. | P1 / Major | |
| INFRA-01 | Infrastructure | Cold start | Stop services; run `docker compose up --build`. | PostgreSQL and Redis become healthy before backend; backend healthcheck passes; frontend starts afterward. | P1 / Major | |

## 6. Defect Reporting

For every failed case, record:

1. Test case ID and environment commit.
2. Exact request or UI steps, including account identity and todo ID.
3. Expected result versus actual result.
4. Response status, response body, browser console, and relevant logs.
5. Reproducibility and proposed priority/severity.

Do not include real passwords, access tokens, or personal data in screenshots or
issue reports. Redact authorization headers before attaching logs.

## 7. Entry and Exit Criteria

### Entry criteria

- Compose services are running and healthy.
- Database migrations completed successfully.
- A clean User A and User B account are available.
- Automated backend and frontend static checks have passed.

### Exit criteria

- All P0 and P1 cases pass.
- No Critical or Major defect remains without an owner and documented mitigation.
- Evidence is attached for each failed or skipped case.
- Automated suites are run after the final manual fix.

## 8. Automated Coverage Cross-Reference

| Area | Command | Coverage |
|---|---|---|
| Backend | `cd backend && pytest tests/ -v` | Auth, ownership, partial update, toggle, and cache mutation paths |
| Frontend static checks | `cd frontend && npm run lint && npx tsc -b` | Type and lint regressions |
| Frontend E2E | `cd frontend && npm run test:e2e` | Full journey and cross-user browser isolation |

## 9. Known Limitations

- Access tokens remain valid until their short expiry after logout; refresh-token
  revocation and replay detection are covered in
  [`SECURITY_HARDENING.md`](SECURITY_HARDENING.md).
- Development Redis is open by design; production compose requires a password.
- E2E tests require the backend and frontend services to be running before the suite starts.
