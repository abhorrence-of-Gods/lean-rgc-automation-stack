# Dead Candidate Disposition Ledger

This is the v84 human-reviewed ledger for modules that generated import
inventory currently classifies as `dead_candidate`.

`dead_candidate` means no current generated import reachability, not approval to
delete. Every entry below is a review target and is not approved for deletion.

## lean_rgc.acceptance_report

- Reachability evidence: `docs/inventory/imports.json` marks this module as
  `dead_candidate`; `imported_by` is empty.
- Compile/import observation: ok.
- Inferred role: carrier acceptance summary helper for JSONL reports.
- Provisional disposition: `archive_candidate`.
- Next action: compare against current carrier and registry acceptance reports
  before deciding whether to archive or fold the helper into a supported report.
- Deletion status: not approved for deletion.
- Risk: importable helper with no current import reachability.

## lean_rgc.active_scheduler

- Reachability evidence: `docs/inventory/imports.json` marks this module as
  `dead_candidate`; `imported_by` is empty.
- Compile/import observation: ok.
- Inferred role: historical active audit scheduler with weighting and budget
  helpers.
- Provisional disposition: `legacy_review`.
- Next action: compare against `lean_rgc.audit_scheduler` and current scheduling
  entrypoints before deciding whether this is a duplicate, a legacy API, or a
  recoverable scheduler.
- Deletion status: not approved for deletion.
- Risk: importable scheduler logic with no current import reachability.

## lean_rgc.audit_scheduler

- Reachability evidence: `docs/inventory/imports.json` marks this module as
  `dead_candidate`; `imported_by` is empty.
- Compile/import observation: ok.
- Inferred role: audit candidate scheduler with history and CSV output support.
- Provisional disposition: `experimental_review`.
- Next action: decide whether scheduler functionality should become part of a
  supported experiment package or remain historical.
- Deletion status: not approved for deletion.
- Risk: importable scheduling surface with no current import reachability.

## lean_rgc.defect_promotion

- Reachability evidence: `docs/inventory/imports.json` marks this module as
  `dead_candidate`; `imported_by` is empty.
- Compile/import observation: ok.
- Inferred role: defect registry promotion helper predating the current POMS
  promotion service boundary.
- Provisional disposition: `experimental_review`.
- Next action: compare promotion scoring and output shape against current POMS
  promotion records before archive or revival.
- Deletion status: not approved for deletion.
- Risk: importable promotion helper with no current import reachability.

## lean_rgc.response_learner

- Reachability evidence: `docs/inventory/imports.json` marks this module as
  `dead_candidate`; `imported_by` is empty.
- Compile/import observation: ok.
- Inferred role: historical hashed/ridge response learner.
- Provisional disposition: `legacy_review`.
- Next action: compare against current response model and learner assets before
  deciding whether the old learner remains useful as a regression fixture.
- Deletion status: not approved for deletion.
- Risk: importable learner implementation with no current import reachability.

## lean_rgc.response_quotient_registry

- Reachability evidence: `docs/inventory/imports.json` marks this module as
  `dead_candidate`; `imported_by` is empty.
- Compile/import observation: ok.
- Inferred role: compatibility wrapper for v33 response quotient registry names;
  canonical functionality lives in `lean_rgc.response_quotient`.
- Provisional disposition: `legacy_compatibility`.
- Next action: keep compatibility until a dedicated deprecation phase records
  external import expectations.
- Deletion status: not approved for deletion.
- Risk: compatibility wrapper has no current in-repo import reachability but may
  still be an external import path.

## lean_rgc.state_ir

- Reachability evidence: `docs/inventory/imports.json` marks this module as
  `dead_candidate`; `imported_by` is empty.
- Compile/import observation: ok.
- Inferred role: historical text-chart proof-state IR parser predating the
  canonical Lean state extraction package.
- Provisional disposition: `archive_candidate`.
- Next action: compare against `lean_rgc.proof_ir` and
  `lean_rgc.lean.structured_state` before archiving.
- Deletion status: not approved for deletion.
- Risk: importable historical parser with no current import reachability.

## lean_rgc.trajectory_runner

- Reachability evidence: `docs/inventory/imports.json` marks this module as
  `dead_candidate`; `imported_by` is empty.
- Compile/import observation: ok.
- Inferred role: historical file-mode tactic trajectory runner.
- Provisional disposition: `legacy_review`.
- Next action: compare against current trajectory and pipeline flows before
  deciding whether to keep as a compatibility surface, archive, or revive with
  tests.
- Deletion status: not approved for deletion.
- Risk: importable runner implementation with no current import reachability.
