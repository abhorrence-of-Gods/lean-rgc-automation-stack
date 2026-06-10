# Inventory Classification

This is the human-reviewed disposition ledger for v76. It complements generated
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

## v76 Dead Candidate Investigation Targets

The current generated import inventory marks these modules as `dead_candidate`:

- `lean_rgc.acceptance_report`
- `lean_rgc.active_scheduler`
- `lean_rgc.audit_scheduler`
- `lean_rgc.defect_promotion`
- `lean_rgc.response_learner`
- `lean_rgc.response_quotient_registry`
- `lean_rgc.state_ir`
- `lean_rgc.trajectory_runner`

Disposition for v76: keep all eight in place. They are investigation targets,
not deletion targets.

## v76 Legacy Modules

- `lean_rgc.coker`
- `lean_rgc.coker_synthesis`
- `lean_rgc.iteration`
- `lean_rgc.iteration_report`
- `lean_rgc.iterative`
- `lean_rgc.stage_coker`

Disposition for v76: keep compatibility intact.

