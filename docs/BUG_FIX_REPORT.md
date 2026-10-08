# Tier 1: Security and Correctness Findings

**Document status:** Implemented fixes and regression coverage recorded

**Audience:** Reviewers, maintainers, and QA engineers

**Scope:** Authentication, authorization, todo state changes, caching, and client state

## Executive Summary

The assessment identified thirteen issues with direct impact on data isolation,
credential validation, pagination correctness, or user-visible state. The highest
risk defects allowed a user to access another user's todo, allowed expired or
wrong-class JWTs to authenticate requests, and allowed one user's cached list to
be returned to another user.

All thirteen findings have an implementation or documented remediation in the
current worktree. Backend regression tests cover token rejection, ownership
boundaries, boolean toggles, partial updates, and create/update/delete cache
invalidation. Frontend lint, TypeScript compilation, and production bundling
also pass.

## Severity Definitions

| Severity | Definition | Required response |
|---|---|---|
| Critical | Confidentiality, authorization, or credential boundary can be bypassed | Block release until fixed and regression-tested |
| High | Significant security, consistency, or availability risk under normal use | Fix before release; add targeted test or operational control |
| Medium | Material behavior or maintainability issue with a bounded impact | Fix in the assessment scope or schedule immediately |
| Low | Correctness or maintainability issue with limited user impact | Fix when practical; prevent recurrence in review |

## Findings and Remediation

| ID | Location | Severity | Impact | Remediation | Verification |
|---|---|---|---|---|---|
| SEC-01 | `backend/app/core/security.py`, `verify_token` | Critical | Expired JWTs could remain usable if expiration verification was disabled. | Decode tokens with expiration verification enabled and return `None` for expired or malformed credentials. | `test_expired_access_token_is_rejected` |
| SEC-02 | `backend/app/api/v1/todos.py`, item endpoints | Critical | Item lookup was not scoped to the authenticated user, allowing cross-user read, update, or delete attempts. | Use `get_todo_by_id_for_user(db, todo_id, current_user.id)` for every item endpoint. | `test_user_cannot_access_other_users_todo` |
| SEC-03 | `backend/app/api/deps.py`, `get_current_user` | Critical | A valid refresh token could be replayed as an access token because token class was not checked. | Require the signed `type=access` claim before resolving the user. | `test_refresh_token_cannot_be_used_as_access_token` |
| SEC-04 | `backend/app/api/v1/auth.py`, `/refresh` | High | A refresh credential with a malformed or deleted subject could mint new credentials. | Parse the subject as UUID and verify that the user still exists. | Refresh validation path and protected endpoint tests |
| SEC-05 | `backend/app/api/v1/todos.py`, list cache | High | A global cache key could return one user's list to another user. | Scope keys by user, page, and size: `todos:user:{user_id}:page:{page}:size:{size}`. | User-isolated cache tests and cache key review |
| COR-01 | `backend/app/api/v1/todos.py`, update endpoint | High | A truthiness check ignored `completed=false`; full payload dumping could erase omitted fields. | Use `model_dump(exclude_unset=True)` and apply only fields present in the request. | `test_toggle_completed_false_persists`, `test_partial_todo_update_keeps_existing_description` |
| SEC-06 | `backend/app/api/v1/auth.py`, login | Medium | Different responses for unknown email and wrong password enabled user enumeration. | Authenticate through one service path and return the same `401 Invalid email or password` response. | Login failure manual case and auth tests |
| COR-02 | `backend/app/services/todo_service.py`, `get_todos` | Medium | Pagination without a deterministic tie-breaker could duplicate or skip rows between requests. | Order by `created_at DESC, id DESC`. | Query review and index alignment |
| COR-03 | `frontend/src/features/todos/api/todos.ts` | Medium | An excessive page size and incomplete query key caused stale or incorrectly shared client results. | Use bounded defaults and include all list parameters in the React Query key. | TypeScript build and query-key review |
| SEC-07 | `frontend/src/features/auth/api/auth.ts` | Medium | Logout left prior user data in React Query memory. | Remove tokens and clear the query client on both logout success and failure. | Manual logout case and client implementation review |
| SEC-08 | `backend/app/main.py`, CORS middleware | High | Wildcard origins combined with credentials allowed unsafe browser cross-origin behavior. | Read an explicit comma-separated origin allowlist from `CORS_ORIGINS`. | Compose/config review and CORS configuration check |
| COR-04 | `frontend/src/features/todos/components/TodoList.tsx` | Low | Array indexes as React keys could preserve the wrong item identity after list mutations. | Use the persisted todo UUID as the key. | Frontend lint and component review |
| SEC-09 | `backend/app/services/session_service.py`, refresh session flow | High | Rotated refresh credentials remained reusable and logout did not revoke server-side state. | Persist one-way token hashes, rotate under row lock, revoke replayed families, and revoke sessions on logout. | `test_refresh_rotates_token_and_rejects_replay`, logout revocation tests |

## Cache Invalidation Contract

Every mutation that changes a user's list invalidates all matching list variants:

```text
todos:user:{user_id}:*
```

The invalidation runs after the database transaction commits. The current
implementation uses Redis `SCAN` rather than `KEYS`, so invalidation does not
block Redis for the entire keyspace. Cache failures should be treated as an
operational alert; authorization is still enforced by the API on cache misses.

## Residual Risks and Follow-up Work

- Access tokens remain valid until their short expiry after logout; refresh-token
  rotation and server-side revocation are implemented. See
  [`SECURITY_HARDENING.md`](SECURITY_HARDENING.md) for the remaining threat-model
  considerations.
- Development Redis is intentionally unsecured for local use. Production compose
  requires a password; TLS and secret management belong to deployment controls.
- Registration normalizes email identity and the `f7a8b9c0d1e2` migration adds a
  database-level case-insensitive unique index; the service maps a race-condition
  violation to `409 Conflict`.
- Performance timings require a running PostgreSQL instance with the seeded
  dataset. The procedure and capture table are in
  [`DATABASE_PERFORMANCE.md`](DATABASE_PERFORMANCE.md).

## Verification Commands

```bash
cd backend
pytest tests/ -v
python -m black --check app tests
python -m flake8 app tests

cd ../frontend
npm run lint
npx tsc -b
npm run build
```
