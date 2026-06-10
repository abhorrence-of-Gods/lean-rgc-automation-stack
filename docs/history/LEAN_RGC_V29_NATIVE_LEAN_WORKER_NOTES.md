# Lean-RGC v29: Native Lean-side Kernel Worker MVP

v29 adds a packaged Lean-side JSONL worker and integrates it with the existing
`LeanServerAdapter` as `--server-backend native`.

## What changed

- Added packaged Lean worker source:
  - `lean_rgc/native_lean/RGCKernelWorker.lean`
- Added Python helper/installer:
  - `lean_rgc/native_worker.py`
- Added native backend mapping in `LeanServerAdapter`.
- Added package data so the `.lean` worker is included in source/wheel builds.
- Added tests for packaged worker source, command generation, and adapter backend mapping.

## Usage

Inspect the bundled worker without running Lean:

```bash
lean-rgc lean-native-worker --print-source
lean-rgc native-lean-worker --print-command --workdir . --lean-cmd "lake env lean"
```

Run server audit through native backend:

```bash
lean-rgc lean-server-audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/native_audit \
  --server-backend native \
  --import-mode core
```

The native backend installs `RGCKernelWorker.lean` into `WORKDIR/.lean_rgc` and
runs it via:

```bash
lake env lean --run WORKDIR/.lean_rgc/RGCKernelWorker.lean
```

## Status and limitations

This is a native Lean process speaking the JSONL worker protocol. It keeps a
state registry and returns kernel-state-shaped JSON consumable by the v28
structured-state normalizer.

It is still an MVP: the shipped Lean code is a protocol bridge and does not yet
expose full Lean internal tactic-state mutation, metavariable graphs, or true
Expr-local-context extraction. Those can replace the worker internals later
without changing the Python adapter contract.

All returned states are finite proof-state charts, not canonical proof states.
Promotion to canonical status still requires parent non-paid evidence, a dual
certificate, and least-repair verification.
