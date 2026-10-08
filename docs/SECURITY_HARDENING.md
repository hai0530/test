# Authentication Security Hardening

**Status:** Implemented and covered by backend regression tests

This document describes the refresh-token lifecycle implemented in the
assessment codebase. Access tokens remain short-lived JWTs for inexpensive API
authorization; refresh tokens are now one-time credentials backed by a
server-side session record.

## Security Goals

- Reject expired, malformed, tampered, and wrong-class JWTs.
- Prevent a rotated refresh token from being used twice.
- Detect refresh-token reuse and revoke the complete credential family.
- Allow logout to revoke the current device session immediately.
- Avoid persisting raw refresh credentials or logging bearer tokens.
- Normalize email identity and enforce database-level case-insensitive uniqueness.
- Keep concurrent browser requests from issuing competing refresh operations.

## Token Classes

| Credential | Lifetime | Claims | Server state |
|---|---:|---|---|
| Access token | 30 minutes by default | `sub`, `type=access`, `jti`, `exp` | None; signature and expiry are verified on every request |
| Refresh token | 7 days by default | `sub`, `type=refresh`, `jti`, `family_id`, `exp` | One `auth_sessions` row per issued token |

The token durations are configurable through `ACCESS_TOKEN_EXPIRE_MINUTES` and
`REFRESH_TOKEN_EXPIRE_DAYS`. The JWT signing secret must be a long, randomly
generated deployment secret and must never be committed or placed in an image
layer.

## Server-Side Session Model

`auth_sessions` stores the minimum state needed to rotate and revoke a refresh
credential:

| Field | Purpose |
|---|---|
| `user_id` | Owner; foreign key with `ON DELETE CASCADE` |
| `family_id` | Groups the original login token and all of its replacements |
| `jti` | Unique JWT ID used for indexed lookup |
| `token_hash` | SHA-256 digest of the raw token; the raw token is never stored |
| `issued_at`, `expires_at` | Session lifetime and cleanup metadata |
| `revoked_at`, `revoke_reason` | One-way revocation state and audit reason |
| `replaced_by_jti` | Links a rotated member to its successor |

The migration is `d5e6f7a8b9c0_add_auth_sessions.py`. Indexes on `(user_id,
revoked_at)`, `family_id`, and unique `jti` keep refresh and revocation lookups
bounded as the session table grows.

## Token Lifecycle

1. **Register or login.** The API creates an access token and a refresh token,
   generates a new `family_id`, hashes the refresh token, and flushes an active
   `auth_sessions` row before returning the pair.
2. **Refresh.** The API verifies the JWT signature, expiry, token class, UUID
   subject, and JTI. It locks the session row with `SELECT ... FOR UPDATE`,
   compares the stored hash, marks the old row as `rotated`, and creates the
   next member in the same family. The old token is invalid from that point
   onward.
3. **Replay detection.** A validly signed token whose row is already revoked is
   a reuse signal. The API revokes every still-active row in that family and
   returns a generic `401 Invalid refresh token`. This protects the legitimate
   replacement when an old token was copied by an attacker.
4. **Logout.** The frontend sends the current refresh token to `/auth/logout`.
   The matching session is revoked with reason `logout`. A legacy no-body
   logout remains supported and revokes all active sessions for the user.
5. **Expiry.** JWT expiry is checked before the database lookup. Expired rows
   can be removed by a scheduled retention job after the maximum refresh
   lifetime plus the operational audit-retention period.

## API Behavior

### `POST /api/v1/auth/refresh`

Request:

```json
{ "refresh_token": "<opaque-to-the-client-signed-jwt>" }
```

Success returns the normal `TokenResponse` with a different refresh token. The
previous refresh token must never be retried after a successful response.

Invalid, expired, unknown, cross-user, hash-mismatched, or revoked credentials
return `401`. The response does not disclose whether a JTI, user, or session
exists.

### `POST /api/v1/auth/logout`

The preferred request includes the refresh token:

```json
{ "refresh_token": "<current-refresh-token>" }
```

The access token still authenticates the caller. The endpoint is idempotent for
the client and returns `200` with `Successfully logged out`. A request without
a body revokes all active sessions for the authenticated user for backwards
compatibility.

## Client Concurrency

The Axios response interceptor retries a single failed request after a `401`
only when a refresh token exists. A module-level promise makes concurrent
requests share one refresh call; all queued requests use the replacement access
token. The refresh request itself uses the base Axios client to avoid loops;
login and registration explicitly opt out because their `401` responses are
normal validation failures. Logout may refresh an expired access token so the
server can still revoke the session. When refresh fails, access and refresh
tokens are removed, the React Query cache is cleared, and the browser returns
to `/login`.

## Threat Model and Controls

| Threat | Control |
|---|---|
| Stolen old refresh token | One-time rotation plus family-wide reuse revocation |
| Forged or modified JWT | Algorithm allowlist and signature verification |
| Expired credential | Required `exp` verification and session expiry check |
| Refresh token used as access token | `type=access` requirement in `get_current_user` |
| Database credential leak | Only SHA-256 token digests are persisted |
| Cross-user refresh/logout | Session owner must match authenticated subject |
| Double refresh race | Row lock around the current session in PostgreSQL |
| Browser cache leakage after logout | React Query cache is cleared on success and error |
| Token disclosure in diagnostics | Do not log `Authorization`, request bodies, or raw tokens |

## Verification

Focused backend coverage is in `backend/tests/test_auth.py`:

- `test_refresh_rotates_token_and_rejects_replay`
- `test_logout_revokes_the_supplied_refresh_session`
- `test_logout_without_body_revokes_all_user_sessions`
- `test_refresh_token_is_persisted_only_as_a_hash`
- Existing expired, tampered, and wrong-class token tests

Run the suite with:

```bash
cd backend
pytest tests/test_auth.py -v
```

## Residual Risks and Follow-Up

- Access tokens already issued remain valid until their short expiry even after
  logout. Use a short access lifetime or add an access-token denylist if
  immediate access revocation is a hard product requirement.
- The browser currently stores tokens in `localStorage`; a future deployment
  should evaluate HttpOnly, Secure, SameSite refresh cookies with CSRF defenses
  against the application's XSS and threat model.
- HS256 key rotation requires a key-version claim and a staged verification
  keyring. Rotation of `JWT_SECRET` alone invalidates all active JWTs.
- Add a scheduled job to purge expired/revoked session rows after the chosen
  audit-retention period and alert on abnormal reuse-detection rates.
- Production deployments should terminate TLS at the edge and keep the API,
  database, and Redis on private network paths.
