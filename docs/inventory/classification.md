# Inventory Classification

This is the human-reviewed disposition ledger for v81. It complements generated
inventory JSON files and does not authorize deletion by itself.

## Classes

- `core`: production runtime or stable contract surface.
- `experimental`: useful research implementation that is not yet production
  runtime.
- `legacy`: compatibility or historical code that remains supported for now.
- `archive_candidate`: code or artifacts that should move to docs/archive or a
  legacy package after another review.
- `dead_candidate`: no current import reachability in generated inventory;
  investigate before moving or deleting.

## v81 Dead Candidate Investigation Targets

The current generated import inventory marks these modules as `dead_candidate`:

- `lean_rgc.acceptance_report`
- `lean_rgc.active_scheduler`
- `lean_rgc.audit_scheduler`
- `lean_rgc.defect_promotion`
- `lean_rgc.response_learner`
- `lean_rgc.response_quotient_registry`
- `lean_rgc.state_ir`
- `lean_rgc.trajectory_runner`

Disposition for v81: keep all eight in place. They are investigation targets,
not deletion targets.

## v81 Legacy Modules

- `lean_rgc.coker`
- `lean_rgc.coker_synthesis`
- `lean_rgc.iteration`
- `lean_rgc.iteration_report`
- `lean_rgc.iterative`
- `lean_rgc.stage_coker`

Disposition for v81: keep compatibility intact.

## v81 Runtime Boundary Disposition

The `lean_rgc.lean.*` package paths are the canonical Lean runtime boundary.
`lean_rgc.lean.state_parser`, `lean_rgc.lean.native_worker`,
`lean_rgc.lean.executor`, `lean_rgc.lean.bulk_executor`,
`lean_rgc.lean.structured_state`, `lean_rgc.lean.kernel_state`, and
`lean_rgc.lean.goal_state_dynamics`, `lean_rgc.lean.frontier`, and
`lean_rgc.lean.worker_supervisor` now own their implementations. Their top-level
modules remain compatibility imports and must not be deleted in this phase.

`lean_rgc.lean.server` and `lean_rgc.lean.persistent_worker` remain facades for
v81. The `lean_rgc.persistent_lean_worker` implementation remains top-level
until the next orchestration phase.
