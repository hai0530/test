# Todo Tags, Filtering, and Bulk Actions

This document describes the optional Tier 4 vertical slice implemented in the
application. The feature is intentionally user-scoped: a tag, mapping, and
todo can only be read or mutated by its owner.

## Data Model

- `tags`: UUID primary key, owner UUID, 50-character name, optional color, and
  timezone-aware creation/update timestamps.
- `todo_tags`: composite primary key `(todo_id, tag_id)` with cascading foreign
  keys to `todos` and `tags`.
- A PostgreSQL functional unique index on `(user_id, lower(name))` prevents
  duplicate tag names regardless of casing.

The Alembic revision `e6f7a8b9c0d1` follows the authentication-session
migration and adds owner, relation, and filtering indexes.

## API Contract

| Method | Endpoint | Behavior |
|---|---|---|
| `GET` | `/api/v1/tags` | List the current user's tags, case-insensitively ordered |
| `POST` | `/api/v1/tags` | Create a tag; duplicate names return `409` |
| `PATCH` | `/api/v1/tags/{tag_id}` | Rename or recolor an owned tag |
| `DELETE` | `/api/v1/tags/{tag_id}` | Delete a tag and its mappings |
| `GET` | `/api/v1/todos` | Filter by `status`, `tag_id`, `keyword`, `date_from`, `date_to`; paginate with `page` and `page_size` |
| `POST` | `/api/v1/todos/{todo_id}/tags` | Attach an owned tag to an owned todo |
| `DELETE` | `/api/v1/todos/{todo_id}/tags/{tag_id}` | Detach an owned mapping |
| `PATCH` | `/api/v1/todos/bulk-status` | Atomically update up to 1,000 owned todos |

Bulk requests containing a todo owned by another user fail as a whole with
`404`; no subset is committed. Duplicate mappings return `409`. Invalid date
ranges return `422`.

## Cache and Query Semantics

Todo-list cache keys include user ID, page, page size, status, tag, keyword,
and date bounds. Create/update/delete, tag mapping changes, tag mutations, and
bulk updates invalidate every todo-list key for the affected user. Todo pages
are ordered by `created_at DESC, id DESC` for stable pagination.

## Frontend Behavior

The dashboard provides a React Query-backed filter bar, tag CRUD manager,
per-todo tag chips, attach/detach controls, selection across the current page,
and complete/active bulk actions. Query keys contain all filter parameters;
mutations invalidate `todos` and `tags` data. Tag forms use `react-hook-form`
and Zod validation, and logout clears the user-scoped query cache.

## Verification

Backend tests cover case-insensitive uniqueness, cross-user tag access, tag
filtering and attach/detach, atomic mixed-ownership bulk rejection, and
filter-specific cache invalidation. Playwright also covers tag creation
validation, tag filtering, and bulk completion persistence. Frontend static
verification uses ESLint, TypeScript, and the production Vite build.
