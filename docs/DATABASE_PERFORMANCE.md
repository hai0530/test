# Database Performance and Indexing Strategy

**Document status:** Index migration implemented; benchmark executed locally

**Workload:** User-scoped todo listing, deterministic pagination, status filtering, and counts

**Database:** PostgreSQL 16

## 1. Performance Objective

The primary list query filters by `user_id`, orders by `created_at DESC, id DESC`,
and returns a small page. The count query filters by the same owner. At one
million todos, a sequential scan and a separate sort can dominate latency even
when each user owns only a small fraction of the table.

The optimization target is to reduce rows scanned and avoid an explicit sort for
the common first-page query, while keeping index count and write overhead
reasonable.

## 2. Baseline Queries

Run the following before applying the index migration. Use the same database,
statistics state, `user_id`, and cache setting for the before and after runs.

```sql
SELECT id FROM users ORDER BY id LIMIT 1;
```

Replace `YOUR-UUID-HERE` with the selected value:

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, title, description, completed, user_id, created_at, updated_at
FROM todos
WHERE user_id = 'YOUR-UUID-HERE'
ORDER BY created_at DESC, id DESC
LIMIT 20 OFFSET 0;

EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT count(*)
FROM todos
WHERE user_id = 'YOUR-UUID-HERE';

EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, title, description, completed, user_id, created_at, updated_at
FROM todos
WHERE user_id = 'YOUR-UUID-HERE'
  AND completed = false
ORDER BY created_at DESC, id DESC
LIMIT 20 OFFSET 0;
```

Record `Execution Time`, `Planning Time`, scan type, rows removed by filter,
and shared buffer hits/reads. Run each query at least five times and report the
median execution time; the first run may include cold filesystem pages.

## 3. Applied Migration

Alembic revision:

```text
backend/alembic/versions/c4f8a1b2d3e4_add_todo_query_indexes.py
```

Apply it with:

```bash
docker compose exec backend alembic upgrade head
```

The migration adds:

| Index | Columns | Query supported | Rationale |
|---|---|---|---|
| `ix_todos_user_id` | `user_id` | Owner counts and simple owner filters | Smallest useful index for count narrowing |
| `ix_todos_user_id_created_at_id` | `user_id, created_at, id` | Ordered owner pagination | Matches the filter and deterministic sort; PostgreSQL can scan backward |
| `ix_todos_user_id_completed_created_at` | `user_id, completed, created_at` | Status-filtered owner lists | Moves both equality predicates into the index before the sort column |

The service query intentionally uses the same stable order:

```sql
ORDER BY created_at DESC, id DESC
```

This prevents page drift when multiple rows have the same timestamp.

## 4. Before/After Benchmark

Run `ANALYZE todos;` after seeding and after applying the migration, then repeat
the exact baseline queries. Enter measured PostgreSQL output below. Values must
come from `EXPLAIN ANALYZE`; do not use estimates or synthetic numbers.

Benchmark execution date: **2026-10-06**  
Environment: PostgreSQL 16.14 in Docker, local developer machine, warm container  
Dataset: **10,000 users**, **1,000,000 todos**  
Selected benchmark user: `e8560de6-8afb-4696-b62c-d14c702b7477` with 139 todos  
Method: five `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` runs per query; median
`Execution Time` is reported. The same user and SQL were used before and after
the migration.

| Query | Before indexes (median ms) | After indexes (median ms) | Improvement | Before plan | After plan |
|---|---:|---:|---:|---|---|
| Owner list, page 1, 20 rows | 32.777 | 0.151 | 217.1x | Parallel sequential scan + top-N sort | Backward index scan on `ix_todos_user_id_created_at_id` |
| Count by owner | 36.338 | 0.189 | 192.3x | Parallel sequential scan + aggregate | Index-only scan on `ix_todos_user_id` |
| Owner list, `completed=false` | 37.403 | 0.254 | 147.3x | Parallel sequential scan + sort | `ix_todos_user_id_completed_created_at` + incremental sort |

The baseline was collected after dropping only the three assessment indexes
from the disposable local database. The migration revision was then stamped
back to `a0790c76a129`, upgraded to `c4f8a1b2d3e4`, and the database was
analyzed before the after runs. These numbers demonstrate the local workload
improvement; they are not a production SLA because hardware, cache state, and
data distribution differ across deployments.

Measured index storage for the same 1,000,000-row `todos` table:

| Index | Size |
|---|---:|
| `ix_todos_user_id` | 7,258,112 bytes (7.1 MB) |
| `ix_todos_user_id_completed_created_at` | 49,758,208 bytes (47 MB) |
| `ix_todos_user_id_created_at_id` | 58,908,672 bytes (56 MB) |
| `todos_pkey` | 39,305,216 bytes (37 MB) |

The three assessment indexes add approximately 115 MB to this dataset, in
addition to the primary-key index.

## 5. Dataset and Reproduction Procedure

```bash
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec -e SEED_USERS=10000 -e SEED_TODOS=1000000 \
  backend python -m app.db.seed
docker compose exec postgres psql -U fabbi -d postgres
```

Inside `psql`, collect index sizes and refresh statistics:

```sql
ANALYZE todos;

SELECT indexrelname,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE relname = 'todos'
ORDER BY indexrelname;
```

Run the same queries before and after the migration using the same selected user.
Save output under the PR or attach it to the performance review; do not commit
large raw query logs to the repository.

## 6. Trade-offs

### Write cost

Each insert must update three additional B-tree indexes. Updates that change
`user_id`, `completed`, or `created_at` also maintain the relevant index entries.
This increases write CPU and WAL volume, but the workload is read-heavy and the
indexes directly support the primary user workflow.

### Storage

Index size depends on UUID and timestamp distribution, fill factor, and table
statistics. Measure actual sizes with `pg_relation_size`; do not assume a fixed
percentage of table size. The composite indexes intentionally duplicate some
`user_id` information to avoid a sort on hot list queries.

### Migration safety

The checked-in migration uses standard Alembic `create_index`, which is suitable
for development and a controlled maintenance window. For a large production
table, use `CREATE INDEX CONCURRENTLY` in a separate non-transactional migration
step, monitor lock/WAL impact, and verify the index with `pg_stat_progress_create_index`.
Do not run concurrent index creation inside Alembic's default transaction block.

### Pagination limits

Offset pagination still becomes more expensive for very deep pages because the
database must walk past skipped rows. A future release can use a cursor based on
`(created_at, id)` while preserving the same composite index.

## 7. Acceptance Criteria

- Migration upgrades and downgrades cleanly on a disposable database.
- The owner list query uses the composite ordering index after statistics refresh.
- The status-filtered query uses the status composite index or a defensible
  planner alternative documented in the benchmark evidence.
- Before/after timings use the same dataset and query parameters.
- The recorded local benchmark shows the measured execution plan and median
  timing for each core query.
- Index storage and write-latency trade-offs are reviewed before production rollout.
