# Lean Runtime Boundary

`lean_rgc.lean` is the stable facade for Lean runtime APIs. In v76, top-level
modules stay in place and remain import-compatible. Future physical moves should
preserve the facade first, then update internal imports once tests cover the new
paths.

## Current Facade Map

| Future package path | Current module |
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

## v76 Rule

Do not move these modules yet. Add facade coverage and command smoke tests first.

