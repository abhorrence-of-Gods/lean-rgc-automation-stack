# Lean-RGC v30: Native Source-Check Execution Path

v30 strengthens the native Lean-side JSONL worker from a protocol/state-registry
scaffold into a source-check execution backend.

## What changed

The packaged Lean worker `lean_rgc/native_lean/RGCKernelWorker.lean` now supports
an `exec_mode`:

- `source_check` (default): render the current task/state/action into a temporary
  Lean theorem source and ask the project Lean executable to check it.  The worker
  returns status, stdout/stderr, messages, proof source hash/path, and a
  kernel-shaped payload.
- `heuristic`: retain the v29 lightweight chart behavior for CI/debugging.

This remains an MVP: it is Lean-side and project-aware, but not yet a true
in-memory `MVarId` tactic-state RPC.  It is designed so a later worker can replace
`source_check` with genuine elaborator/tactic-state mutation behind the same
JSONL protocol.

## CLI

```bash
lean-rgc lean-native-worker --print-command --exec-mode source_check
```

```bash
lean-rgc lean-server-audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/native_source_check \
  --server-backend native \
  --native-exec-mode source_check
```

Use heuristic mode when Lean is unavailable or when you only need protocol tests:

```bash
lean-rgc lean-server-audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/native_heuristic \
  --server-backend native \
  --native-exec-mode heuristic
```

## Audit metadata

Native source-check records include audit flags such as:

```json
{
  "native_lean_worker": true,
  "backend": "native_lean_jsonl_worker_v30",
  "native_exec_mode": "source_check",
  "elaboration_checked": true,
  "execution_backend": "native_lean_source_check_v30",
  "proof_source_sha": "...",
  "proof_source_path": "...",
  "return_code": 0,
  "kernel_state_schema": "lean-rgc-kernel-state-v28.0"
}
```

## Status

This is still a finite proof-state chart, not a canonical quotient.  Canonical
promotion still requires parent non-paid evidence, a dual certificate, and least
repair.
