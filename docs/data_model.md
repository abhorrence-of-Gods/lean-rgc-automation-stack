# Data Model

The production-local store is SQLite. The database is an index and lineage
ledger over run artifacts; it is not the raw artifact store.

## Contract Metadata

Production JSONL records should carry:

```text
schema_version
run_id
parent_ids
payload_json
```

The canonical metadata contract lives in `lean_rgc.core`:

```python
from lean_rgc.core import SCHEMA_CONTRACT_VERSION, PRODUCTION_METADATA_FIELDS
```

`lean_rgc.schemas` keeps backward-compatible exports for existing modules.

## Run DB

`lean-rgc data build` creates a run DB with these high-value table groups:

- run and artifact identity: `runs`, `artifacts`, `schema_migrations`
- audit and response rows: `tasks`, `actions`, `responses`, `audit_events`
- repair and hardening: `repair_faces`, `crg_problems`,
  `relaxed_candidates`, `hardening_attempts`, `hard_candidates`
- concept and promotion: `concept_points`, `concept_search_rows`,
  `poms_evidence`, `poms_promotion_decisions`
- replay and operations: `audit_jobs`, `timeout_events`, `worker_events`,
  `action_quarantine`, `audit_result_cache_index`
- lineage: `lineage_edges`

## Invariants

Use:

```bash
lean-rgc data check --db runs.db --json
```

The check fails with a nonzero exit code if required tables are missing or if
canonical identity fields are absent from artifacts, records, or lineage edges.

## Artifact Policy

Large raw outputs stay as files under a run directory or external object store.
The run DB stores metadata, hashes, indexes, summaries, and lineage references.
Postgres and object-store backends are intentionally outside the v75 freeze.

