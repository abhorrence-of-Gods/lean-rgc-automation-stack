# Lean-RGC v12 QGEN implementation notes

This revision implements the first system-side transition from a hand-written chart universe to a response-mined quotient universe.

## Added/updated modules

- `lean_rgc/qgen.py`
  - Computes a finite response cone projection.
  - Extracts coker residual coordinates as candidate defect atoms.
  - Scores audited contexts against the coker normal.
  - Emits candidate context actions, carrier-incidence patches, and failure-signature charts.
  - All outputs are explicitly marked as witness/chart-level objects, not canonical objects.

- `lean_rgc/coker_synthesis.py`
  - Added high-level `synthesize(...)` wrapper.
  - Added `synthesize_from_coker_files(...)` compatibility wrapper used by the CLI.
  - Writes:
    - `synthesized_actions.jsonl`
    - `synthesized_defect_atoms.jsonl`
    - `synthesized_defect_registry.json`
    - `carrier_incidence_patches.jsonl`
    - `coker_profiles.jsonl`
    - `response_archetypes.jsonl`
    - `synthesis_report.json`

- `lean_rgc/cli.py`
  - Added `qgen` command.
  - Existing `coker-synthesize` / `synthesize-from-coker` commands now import working synthesis wrappers.

- `tests/test_qgen.py`
  - Adds minimal tests for coker-driven generation artifacts.

## New commands

```bash
lean-rgc qgen \
  --responses responses.jsonl \
  --audits micro_audit.jsonl \
  --out qgen_out
```

```bash
lean-rgc coker-synthesize \
  --base-responses responses.jsonl \
  --out-actions synthesized_actions.jsonl \
  --out-profiles coker_profiles.jsonl \
  --out-archetypes response_archetypes.jsonl \
  --out-atoms synthesized_defect_registry.json \
  --out-summary synthesis_summary.json
```

```bash
lean-rgc synthesize-from-coker \
  --base-responses responses.jsonl \
  --audits micro_audit.jsonl \
  --actions actions.jsonl \
  --out-actions synthesized_actions.jsonl \
  --out-report synthesis_report.json
```

## Theoretical status

The generated artifacts implement:

```text
coker residual -> candidate defect atoms
coker normal   -> candidate proof contexts
carrier deltas -> carrier incidence patches
failure logs   -> failure chart candidates
```

These are not promoted to canonical status.  They still require micro-audit, carrier/audit/cost safety, and POMS promotion.

## Test status

`pytest -q` passes all included tests.
