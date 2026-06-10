# v75 Migration Status

## Completed

- The former monolithic CLI has been replaced by the `lean_rgc.cli` package.
- `lean_rgc.core` contains stable metadata helpers and production record
  dataclasses.
- `lean_rgc.data` builds the SQLite run DB, imports artifact metadata,
  materializes canonical tables, and records typed lineage edges.
- `lean_rgc.dost` has been split into runtime, transcript, feature, selection,
  autoplan, compile, and report modules.
- Test tiers are assigned through `tests/tier_manifest.json`; default pytest
  excludes `legacy` and `slow`.

## Frozen For v75

- SQLite is the production-local metadata store.
- Raw JSONL and Lean outputs remain file artifacts.
- Legacy CLI shims stay supported.
- Historical vXX tests and notes are preserved.

## Deferred

- Physical relocation of tests into `tests/legacy/`, `tests/integration/`, and
  related folders.
- Postgres, S3, GCS, MinIO, or graph database backends.
- Deleting dead modules.
- Removing legacy CLI shims.

## Next Candidates

- Use the inventory scripts to decide which modules become core,
  experimental, legacy, archive, or dead candidates.
- Move top-level Lean runtime adapters into `lean_rgc.lean` after compatibility
  tests are in place.
- Add a small curated smoke benchmark corpus as a stable artifact.

