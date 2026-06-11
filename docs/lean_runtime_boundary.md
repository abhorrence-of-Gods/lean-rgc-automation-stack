# Lean Runtime Boundary

`lean_rgc.lean` is the stable package for Lean runtime APIs. Top-level modules
stay in place and remain import-compatible, but new runtime-facing code should
import from `lean_rgc.lean.*`.

## Canonical Package Map

| Canonical package path | Compatibility module |
| --- | --- |
| `lean_rgc.lean.server` | `lean_rgc.lean_server` |
| `lean_rgc.lean.executor` | `lean_rgc.executor` |
| `lean_rgc.lean.persistent_worker` | `lean_rgc.persistent_worker` |
| `lean_rgc.lean.native_worker` | `lean_rgc.native_worker` |
| `lean_rgc.lean.state_parser` | `lean_rgc.state_parser` |
| `lean_rgc.lean.kernel_state` | `lean_rgc.kernel_state` |
| `lean_rgc.lean.structured_state` | `lean_rgc.structured_state` |
| `lean_rgc.lean.goal_state_dynamics` | `lean_rgc.goal_state_dynamics` |
| `lean_rgc.lean.frontier` | `lean_rgc.frontier` |
| `lean_rgc.lean.worker_supervisor` | `lean_rgc.lean_worker_supervisor` |
| `lean_rgc.lean.bulk_executor` | `lean_rgc.bulk_executor` |

## v77 Rule

`lean_rgc.lean.*` is now the canonical import boundary. The modules are thin
re-export layers over the top-level compatibility modules, so object identity is
preserved for existing callers. CLI modules and the pipeline entrypoint should
use canonical imports for Lean runtime dependencies.

Do not delete or rename the top-level modules in v77. They remain supported
compatibility imports while downstream callers migrate.

## v78 Physical Move I

`lean_rgc.lean.state_parser` and `lean_rgc.lean.native_worker` now own their
implementations. The top-level modules `lean_rgc.state_parser` and
`lean_rgc.native_worker` are compatibility shims that re-export the canonical
objects.

The native worker source remains under `lean_rgc/native_lean/`. Both module
entrypoints are supported:

```bash
python -m lean_rgc.native_worker --print-command
python -m lean_rgc.lean.native_worker --print-command
```

`lean_server` continues to launch `lean_rgc.native_worker` for subprocess
compatibility in v78.

## v79 Physical Move II

`lean_rgc.lean.executor` and `lean_rgc.lean.bulk_executor` now own their
implementations. The top-level modules `lean_rgc.executor` and
`lean_rgc.bulk_executor` are compatibility shims that re-export canonical
objects.

Bulk executor private helper imports used by historical tests remain supported
through `lean_rgc.bulk_executor`, including `_render_bulk_file`,
`_errors_by_line`, and `_block_messages`.

## v80 Physical Move III

`lean_rgc.lean.structured_state`, `lean_rgc.lean.kernel_state`, and
`lean_rgc.lean.goal_state_dynamics` now own their implementations. The top-level
modules `lean_rgc.structured_state`, `lean_rgc.kernel_state`, and
`lean_rgc.goal_state_dynamics` are compatibility shims that re-export canonical
objects.

Runtime callers use canonical imports for state extraction. Historical tests and
external callers can continue using the top-level compatibility paths.

## v81 Physical Move IV

`lean_rgc.lean.frontier` and `lean_rgc.lean.worker_supervisor` now own their
implementations. The top-level modules `lean_rgc.frontier` and
`lean_rgc.lean_worker_supervisor` are compatibility shims that re-export
canonical objects.

Runtime-facing package exports, CLI modules, and pipeline entrypoints use
canonical imports for frontier construction and worker-supervised audit queues.
Historical tests and external callers can continue using the top-level
compatibility paths.

## v82 Physical Move V

`lean_rgc.lean.server`, `lean_rgc.lean.persistent_lean_worker`, and
`lean_rgc.lean.persistent_worker` now own their implementations. The top-level
modules `lean_rgc.lean_server`, `lean_rgc.persistent_lean_worker`, and
`lean_rgc.persistent_worker` are compatibility shims that re-export canonical
objects.

Persistent worker module entrypoints remain supported through both compatibility
and canonical paths:

```bash
python -m lean_rgc.persistent_lean_worker --backend dry_run
python -m lean_rgc.lean.persistent_lean_worker --backend dry_run
python -m lean_rgc.persistent_worker --dry-run
python -m lean_rgc.lean.persistent_worker --dry-run
```

`LeanServerAdapter(backend="persistent")` continues to launch
`lean_rgc.persistent_lean_worker` for subprocess compatibility in v82.

## Future Boundary Work

The runtime implementation files now sit behind the canonical package boundary.
Future phases should focus on compatibility hardening and inventory cleanup:

1. audit remaining top-level runtime shims as compatibility surfaces
2. decide whether `lean_rgc.persistent_lean_worker` should remain the subprocess
   command string permanently or gain a canonical command string after one more
   compatibility phase
3. defer deletion, physical test relocation, and `pipeline.py` splitting until
   import compatibility has stayed stable

Each phase should keep the v77-v82
identity tests passing.
