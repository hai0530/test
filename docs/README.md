# Assessment Documentation

This directory contains the reviewable engineering deliverables for the
assessment. Each document has a single responsibility so reviewers can inspect
security, QA, product design, and performance decisions independently.

| Document | Purpose | When to use |
|---|---|---|
| [`BUG_FIX_REPORT.md`](BUG_FIX_REPORT.md) | Findings, severity, remediation, verification, and residual risks | Code review and PR preparation |
| [`SECURITY_HARDENING.md`](SECURITY_HARDENING.md) | Refresh-token rotation, revocation, replay detection, and residual risks | Authentication and threat-model review |
| [`MANUAL_TEST_PLAN.md`](MANUAL_TEST_PLAN.md) | Manual scenarios, evidence fields, release gates, and defect reporting | QA execution against a running stack |
| [`TODO_SHARING_SPEC.md`](TODO_SHARING_SPEC.md) | Proposed product, data, API, authorization, cache, and rollout design | Requirement and architecture review |
| [`DATABASE_PERFORMANCE.md`](DATABASE_PERFORMANCE.md) | Index rationale, EXPLAIN procedure, benchmark capture, and migration trade-offs | Database review and production rollout |
| [`PR_DESCRIPTION.md`](PR_DESCRIPTION.md) | PR-ready summary, verification, rollout, rollback, and AI disclosure | Final submission |
| [`OPERATIONS_RUNBOOK.md`](OPERATIONS_RUNBOOK.md) | Health probes, secrets, deployment, migration, backup, incident, and CI procedures | Local and production-like operations |
| [`TODO_TAGS_BULK.md`](TODO_TAGS_BULK.md) | Optional Tier 4 tags, filtering, bulk actions, cache, and authorization contract | Extension feature review |

## Recommended Review Order

1. Read the bug report for security and correctness context.
2. Run the automated checks listed in the bug report.
3. Execute the manual test plan against `docker compose up --build`.
4. Review the sharing specification before implementation.
5. Run the database benchmark only with a reproducible PostgreSQL dataset.

## Evidence Policy

- Report measured results, not estimates.
- Redact tokens, passwords, and personal data from screenshots and logs.
- Keep large EXPLAIN outputs attached to the PR or an external artifact rather
  than committing them to this repository.
- Update each document's status when a test, design decision, or benchmark is completed.
