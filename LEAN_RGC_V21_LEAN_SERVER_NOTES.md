# Lean-RGC v21: Lean Server Adapter

v21 introduces a persistent-worker shaped Lean server adapter.

## Status

This is an adapter contract and runnable bridge, not yet a true Lean kernel/LSP persistent elaborator.

Implemented backends:

- `dry_run`: deterministic CI/Colab backend.
- `file_fallback`: one long-lived Python adapter using the existing file-based Lean executor.
- `jsonl`: protocol wrapper for a future external Lean worker process. If unavailable, it can fall back to file mode.

The goal is to make downstream RGC stages depend on a server-shaped interface now, so a true persistent Lean worker can replace the backend without changing audit artifacts.

## New commands

### Probe server health

```bash
lean-rgc lean-server-probe \
  --dry-run \
  --workdir . \
  --out server_probe.json
```

### Audit through the adapter

```bash
lean-rgc lean-server-audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/server_audit \
  --dry-run \
  --import-mode core
```

Outputs:

- `micro_audit.jsonl`
- `responses.jsonl`
- `defects.jsonl`
- `structured_states.jsonl`
- `server_summary.json`
- `summary.json`

### Pipeline server audit mode

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/server_pipeline \
  --dry-run \
  --audit-mode server \
  --import-mode core
```

## JSONL external worker protocol

The adapter can call an external JSONL server using `--server-cmd`.

Requests:

```json
{"cmd":"load_project","workdir":"...","lean_cmd":"lake env lean"}
```

```json
{"cmd":"apply_tactic","task":{...},"action":{...},"state":{...}}
```

Responses should include either:

```json
{"ok":true,"record":{...AuditRecord...}}
```

or

```json
{"ok":true,"audit":{...AuditRecord...}}
```

## Theory status

The server adapter is a system substrate for quotient-safe audit. It does not make text/state charts canonical. Structured state rows are still charts until v22 replaces text parsing with Lean AST / local-context extraction.
