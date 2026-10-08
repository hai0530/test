# Application Architecture

**Status:** Implemented baseline with optional feature modules

**Scope:** Authentication, owned todos, tags and filtered/bulk todo workflows

## 1. Design Principles

- Keep HTTP handlers thin; validation belongs in Pydantic/Zod schemas and business rules belong in services.
- Scope every read, mutation, cache key, and query key by the authenticated user.
- Treat PostgreSQL as the source of truth and Redis as a disposable read cache.
- Prefer additive migrations and explicit rollback notes over implicit schema changes.
- Keep feature code close to its domain: authentication, todos, and tags have separate modules.

## 2. Request Flow

```text
Browser
  |
  | Bearer access token + query parameters
  v
FastAPI router
  |
  +--> authentication dependency --> verified User
  |
  +--> Pydantic request validation
  |
  +--> domain service --> SQLAlchemy async session --> PostgreSQL
  |                                  |
  |                                  +--> commit/rollback
  |
  +--> user-scoped Redis cache invalidation or read-through
  v
JSON response
```

The router never accepts a caller-supplied owner ID. The authenticated user is
the authority for ownership checks. A missing or unauthorized todo is returned
as a non-disclosing `404`.

## 3. Backend Boundaries

| Layer | Responsibility |
|---|---|
| `app/api` | HTTP routes, dependencies, status codes, response mapping |
| `app/schemas` | Request and response validation |
| `app/services` | Ownership rules, transactions, query composition |
| `app/models` | SQLAlchemy persistence model and relationships |
| `app/core` | Settings, JWT verification, Redis client, cross-cutting concerns |
| `app/db` | Engine/session lifecycle, migrations, deterministic seed data |

Todo list queries use deterministic `created_at DESC, id DESC` ordering. Query
parameters are bounded before reaching the database, and cache keys include the
user plus every list/filter parameter.

## 4. Frontend Boundaries

```text
pages -> feature components -> feature API hooks -> Axios client
                                      |
                                      +--> TanStack Query cache
```

Feature hooks own query keys, mutations, optimistic updates, and invalidation.
Reusable UI primitives remain under `components/ui`. Authentication state is
cleared from both browser storage and the Query cache during logout.

## 5. Consistency Rules

1. Write the database mutation inside the request transaction.
2. Invalidate all affected user-scoped list variants after the mutation commits.
3. Never use a cached response to bypass authorization.
4. Bulk operations validate all IDs and ownership before committing any update.
5. Redis failure must not turn an authorization decision into a cache decision.

## 6. Operational Dependencies

- PostgreSQL stores users, todos, tags, and todo-tag mappings.
- Redis stores short-lived list responses and rate/session state where configured.
- Docker Compose healthchecks gate backend startup on PostgreSQL and Redis readiness.
- Alembic migrations are applied before the backend process starts in containerized environments.

## 7. Deliberate Non-Goals

The current release does not introduce microservices, a message broker, public
share links, realtime collaboration, or a second persistence store. Those would
increase operational cost without improving the assessment's core correctness
and security evidence.
