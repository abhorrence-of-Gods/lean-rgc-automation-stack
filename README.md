# Lean-RGC Automation Stack

Lean-RGC is a Lean automation research stack that is being hardened into a
production-style runtime for repeatable audit, response completion, repair
generation, CRG hardening, concept geometry, and POMS promotion workflows.

The v75 production contract freeze keeps the research history intact while
making the durable runtime assets explicit:

- stable schema metadata on JSONL records
- a SQLite run database for metadata, lineage, and indexes
- artifact identity with run ids, parent ids, schema versions, and hashes
- replayable audit and hardening traces
- curated test tiers for default CI, e2e, and legacy history

## Install

```bash
python -m pip install -e .
```

The package exposes the main CLI as:

```bash
lean-rgc --help
```

## Quickstart

Run a dry Lean audit and build the local production run database:

```bash
lean-rgc audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/dry_audit \
  --dry-run

lean-rgc data build --run-dir runs/dry_audit --db runs/dry_audit/runs.db
lean-rgc data check --db runs/dry_audit/runs.db --json
lean-rgc data summarize --db runs/dry_audit/runs.db
lean-rgc data lineage --db runs/dry_audit/runs.db
```

General invariant-check form:

```bash
lean-rgc data check --db runs.db --json
```

For an end-to-end dry production pipeline:

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/dry_pipeline \
  --dry-run \
  --max-actions 2 \
  --run-db
```

Run the stable smoke benchmark:

```bash
lean-rgc benchmark smoke --out runs/benchmark_smoke --dry-run --run-db
```

## Production Spine

The current package layout separates runtime contracts from command wiring:

```text
lean_rgc/
  core/        stable metadata contract, ids, and JSONL I/O
  data/        SQLite run DB, artifact metadata, importers, invariants
  cli/         argparse command registry and domain command groups
  dost/        response completion and DOST runtime pieces
  experiment/  experiment orchestration helpers
  lean/        Lean runtime boundary modules
```

The legacy top-level `lean_rgc.cli_*.py` modules are compatibility shims. New
CLI work should live under `lean_rgc/cli/`.

## Main Commands

```text
lean-rgc audit ...          dry-run or Lean-backed micro audit
lean-rgc benchmark smoke    stable smoke benchmark plus optional run DB check
lean-rgc pipeline ...       audit -> DOST/CRG/POMS style pipeline entrypoint
lean-rgc data build ...     build the SQLite run DB from run artifacts
lean-rgc data check ...     validate run DB production invariants
lean-rgc data query ...     query run DB tables
lean-rgc data lineage ...   summarize typed lineage edges
lean-rgc crg-* ...          CRG registry, problem, optimizer, and hardening commands
lean-rgc dost-* ...         DOST response completion and report commands
lean-rgc poms-* ...         POMS status and promotion commands
```

Deprecated root commands are retained during migration and emit replacement
warnings where a namespaced command exists.

## Testing

The default production CI contract is:

```bash
python -m pytest -q
```

Useful local targets:

```bash
python -m pytest -m "unit or integration or golden" -q
python -m pytest -m e2e -q
python -m pytest -m "legacy or slow" --collect-only -q
```

Test tiers are assigned in `tests/tier_manifest.json`. Historical vXX tests are
preserved as `legacy` and excluded from default CI.

## Documentation

- `docs/architecture.md`: runtime architecture and package boundaries
- `docs/data_model.md`: run DB, artifact metadata, lineage, and schema contract
- `docs/cli.md`: current CLI shape and migration policy
- `docs/testing.md`: test tier contract
- `docs/migration_status.md`: v75 production freeze status
- `docs/history/`: version notes preserved from the research phase
