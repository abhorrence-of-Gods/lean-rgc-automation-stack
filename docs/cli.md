# CLI

The active entrypoint is:

```toml
lean-rgc = "lean_rgc.cli:main"
```

The root parser lives in `lean_rgc/cli/main.py` and registers domain command
groups:

```text
audit
lean
experiment
dost
pipeline
crg
poms
data
```

## Data Commands

```bash
lean-rgc data build --run-dir runs/dry_audit --db runs/dry_audit/runs.db
lean-rgc data check --db runs/dry_audit/runs.db --json
lean-rgc data summarize --db runs/dry_audit/runs.db
lean-rgc data query --db runs/dry_audit/runs.db --sql "SELECT COUNT(*) AS n FROM responses"
lean-rgc data lineage --db runs/dry_audit/runs.db
```

## Migration Policy

Deprecated root commands such as `run-db-build`, `run-db-query`,
`audit-db-build`, and `repair-db-build` remain available during this freeze and
print replacement warnings. New command work should use namespaced commands
under `lean-rgc data`, `lean-rgc crg`, `lean-rgc dost`, or the existing domain
groups.

The top-level `lean_rgc.cli_*.py` modules are compatibility shims. Do not add new
handler logic to those files.

