# Lean-RGC v21: Lean Server Adapter

v21 adds a persistent-worker shaped Lean execution adapter.  The goal is to
separate the RGC audit interface from the old one-file/one-process execution
chart while keeping every existing response / carrier / lineage artifact schema
stable.

## New module

```text
lean_rgc/lean_server.py
```

Main objects:

```python
LeanServerConfig
LeanServerAdapter
audit_with_lean_server
project_fingerprint
```

The adapter supports four backend modes:

- `dry_run`: deterministic CI / Colab-compatible pseudo-audit.
- `file` / `file_fallback`: uses the existing `LeanExecutor` behind the new
  persistent-worker API.
- `jsonl`: optional protocol hook for a future true Lean worker process.
- `auto`: chooses dry-run when `--dry-run` is set, otherwise JSONL if
  `--server-cmd` is provided, otherwise file fallback.

The JSONL protocol is intentionally minimal:

```json
{"cmd":"load_project", ...}
{"cmd":"apply_tactic", "task":{...}, "action":{...}, "state":{...}}
{"cmd":"shutdown"}
```

A real Lean worker can implement this later without changing downstream RGC
artifacts.

## New commands

```bash
lean-rgc lean-server-probe \
  --dry-run \
  --out runs/server_probe.json
```

```bash
lean-rgc server-audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/server_audit \
  --dry-run \
  --max-actions 8
```

Backward-compatible aliases / hooks are also supported:

```bash
lean-rgc lean-server-health ...
lean-rgc lean-server-apply ...
lean-rgc lean-server-audit ...
```

## Pipeline integration

`pipeline` and `iterate` now accept:

```bash
--audit-mode server
--server-cmd <jsonl-worker-command>
--server-backend auto|dry_run|file|file_fallback|jsonl
--server-no-fallback
```

Example:

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v21_server \
  --dry-run \
  --audit-mode server \
  --max-actions 8
```

Output includes:

```text
audit/server_summary.json
audit/micro_audit.jsonl
audit/responses.jsonl
audit/defects.jsonl
```

Each audit record receives:

```json
"audit_flags": {
  "lean_server_adapter": true,
  "server_session_id": "...",
  "server_backend": "dry_run|file_fallback|jsonl",
  "project_fingerprint": "..."
}
```

## Status

This is an adapter layer, not the final v22 structured Lean state extraction.
The returned structured state is explicitly marked as:

```text
structured_state_chart_only_v22_ast_pending
```

The important v21 achievement is that the rest of the RGC stack no longer has
to assume file-mode Lean execution.  A real persistent Lean worker can now be
plugged in behind the same audit API.
