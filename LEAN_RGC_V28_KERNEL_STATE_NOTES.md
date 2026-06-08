# Lean-RGC v28: Kernel-backed Structured State Extraction

v28 adds the kernel-state normalization layer requested after the v27 persistent worker.

## What changed

- `lean_rgc/structured_state.py` now accepts Lean-kernel/proof-state JSON payloads and normalizes them into the stable `StructuredProofState` schema.
- The schema version is now `lean-rgc-structured-state-v28.0`.
- Kernel payloads use the protocol schema `lean-rgc-kernel-state-v28.0`.
- `PersistentLeanWorker` now exposes a `kernel_state` JSONL command and returns kernel-shaped state payloads from `apply_tactic` / `structured_state`.
- `LeanServerAdapter` prefers `kernel_state` side-channel payloads over text-derived extraction.
- `structured-state-extract` accepts `--kernel-jsonl` in addition to `--tasks` and `--audits`.

## Status

This is a kernel-backed protocol/normalization layer.  In the in-tree dry-run/file worker, the returned payload is a kernel-shaped compatibility payload derived from the persistent state registry.  A native Lean RPC worker can now return real kernel JSON with the same fields, and Python will normalize it without changing downstream RGC artifacts.

The resulting state remains a finite proof-state chart, not a canonical observable.

## Kernel payload shape

Minimal payload:

```json
{
  "schema_version": "lean-rgc-kernel-state-v28.0",
  "task_id": "t",
  "state_id": "s",
  "goals": [
    {
      "mvar_id": "?m.1",
      "target": {"text": "n = n", "kind": "app", "head": "Eq"},
      "local_deps": ["fvar_n"]
    }
  ],
  "local_context": {
    "nodes": [
      {"fvar_id": "fvar_n", "user_name": "n", "type": {"text": "Nat", "head": "Nat"}}
    ]
  },
  "metavars": [{"mvar_id": "?m.1", "type_text": "n = n"}],
  "typeclasses": []
}
```

## CLI

Normalize kernel JSONL:

```bash
lean-rgc structured-state-extract \
  --kernel-jsonl kernel_states.jsonl \
  --out structured_states.jsonl \
  --summary-out structured_state_summary.json
```

Persistent worker kernel state:

```jsonl
{"cmd":"init_state","task":{"task_id":"t","statement":"True","imports":["Init"]}}
{"cmd":"kernel_state","state_id":"..."}
{"cmd":"structured_state","state_id":"..."}
```

## Next step

A native Lean-side RPC worker should implement the same JSONL commands with real `Expr`, `LocalDecl`, metavariable, and typeclass obligation data.
