# Inventory Classification

This is the human-reviewed disposition ledger for v84. It complements generated
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

## v84 Dead Candidate Investigation Targets

The current generated import inventory marks these modules as `dead_candidate`:

- `lean_rgc.acceptance_report`
- `lean_rgc.active_scheduler`
- `lean_rgc.audit_scheduler`
- `lean_rgc.defect_promotion`
- `lean_rgc.response_learner`
- `lean_rgc.response_quotient_registry`
- `lean_rgc.state_ir`
- `lean_rgc.trajectory_runner`

Disposition for v84: keep all eight in place. They are investigation targets,
not deletion targets. Per-module review notes live in
`docs/inventory/dead_candidates.md`, and the ledger is checked by
`scripts/check_dead_candidate_ledger.py`.

## v84 Legacy Modules

- `lean_rgc.coker`
- `lean_rgc.coker_synthesis`
- `lean_rgc.iteration`
- `lean_rgc.iteration_report`
- `lean_rgc.iterative`
- `lean_rgc.stage_coker`

Disposition for v84: keep compatibility intact.

## v84 Runtime Boundary Disposition

The `lean_rgc.lean.*` package paths are the canonical Lean runtime boundary.
`lean_rgc.lean.state_parser`, `lean_rgc.lean.native_worker`,
`lean_rgc.lean.executor`, `lean_rgc.lean.bulk_executor`,
`lean_rgc.lean.structured_state`, `lean_rgc.lean.kernel_state`, and
`lean_rgc.lean.goal_state_dynamics`, `lean_rgc.lean.frontier`, and
`lean_rgc.lean.worker_supervisor`, `lean_rgc.lean.server`,
`lean_rgc.lean.persistent_lean_worker`, and `lean_rgc.lean.persistent_worker`
now own their implementations. Their top-level modules remain compatibility
imports and must not be deleted in this phase.

`lean_rgc.lean_server`, `lean_rgc.persistent_lean_worker`, and
`lean_rgc.persistent_worker` are compatibility surfaces. The server still uses
`lean_rgc.persistent_lean_worker` as its persistent subprocess module string in
v84.

Runtime boundary enforcement is checked by `scripts/check_runtime_boundary.py`
and default CI. A passing check means compatibility shims are thin, canonical
exports preserve identity, and runtime-facing code does not import top-level
runtime shims directly.

## v84 Ledger Enforcement

Generated inventory remains the source of reachability truth. The human ledger
does not hide `dead_candidate` classification; it records review status,
provisional disposition, and the explicit deletion block for each candidate.

`scripts/check_dead_candidate_ledger.py` checks that every generated
`dead_candidate` has a ledger entry, no stale ledger entries remain, and every
entry states `not approved for deletion`. Compile/import status is observation
only; a broken candidate must be recorded as a risk rather than silently
ignored.
