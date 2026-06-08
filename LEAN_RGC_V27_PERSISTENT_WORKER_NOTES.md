# Lean-RGC v27: Persistent Lean Worker Protocol

v27 adds a stateful proof-state worker layer.

## What is implemented

- Persistent JSONL worker command:

```bash
lean-rgc persistent-worker --backend dry_run
```

- Compatibility command:

```bash
lean-rgc lean-persistent-worker --dry-run
```

- Probe:

```bash
lean-rgc lean-persistent-probe --dry-run --out probe.json
```

- `LeanServerAdapter(backend="persistent")` now starts a persistent JSONL worker.
- The worker keeps server-side state ids.
- The worker supports:
  - `load_project`
  - `register_task` / `init_state`
  - `apply_tactic`
  - `get_state`
  - `list_states`
  - `branch_state`
  - `rollback_state`
  - `structured_state`
  - `shutdown`
- Branch/rollback metadata is returned and audit records include persistent state flags.

## Current backend status

The current in-tree worker is stateful at the RGC layer.  It stores proof prefixes and replays them through either:

- deterministic dry-run backend, or
- existing file-backed Lean executor.

This is not yet a kernel-resident Lean RPC implementation.  The protocol is designed so that a future Lean-side worker can replace the backend while preserving the Python/RGC API and artifact schema.

## Canonical status

Persistent worker states are still proof-state charts, not canonical proof observables.  They are marked as chart/witness artifacts until the usual parent-nonpaid / dual-certificate / least-repair promotion conditions are met.
