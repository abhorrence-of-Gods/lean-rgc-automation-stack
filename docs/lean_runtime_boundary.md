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

## Future Physical Move Order

When the canonical package has stayed stable for another phase, move
implementation files behind the package boundary in this order:

1. low-dependency helpers: `state_parser`, `native_worker`
2. executor surfaces: `executor`, `bulk_executor`
3. state extraction: `structured_state`, `kernel_state`, `goal_state_dynamics`
4. orchestration: `server`, `persistent_worker`, `worker_supervisor`, `frontier`

Each move should leave a top-level compatibility shim and keep the v77 identity
tests passing.
