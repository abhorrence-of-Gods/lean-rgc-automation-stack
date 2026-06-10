# Lean-RGC v0.4 notes

This release is a pre-production cleanup for real Lean pilot runs.

## Main fixes

1. `lean-rgc pipeline` now accepts real Lean execution arguments:
   - `--lean-cmd`
   - `--workdir`
   - `--timeout-s`
   - `--cache-dir`
   - `--trace-state`
   - `--import-mode preserve|auto|core|mathlib`
   - `--resume`
   - `--flush-every`

2. Pipeline now runs the full minimal sequence in both dry-run and real Lean mode:
   - batch audit
   - response model
   - response quotient
   - carrier generator / carrier coker
   - transition generation
   - gamma audit
   - report

3. `init-lake --no-mathlib` now writes a more robust Lake project:
   - sanitized Lean identifier package name
   - root module `<Name>.lean`
   - submodule `<Name>/Basic.lean`
   - Mathlib-free examples in no-Mathlib mode

4. Task import handling is now explicit:
   - `--import-mode core` removes Mathlib imports from tasks
   - `--import-mode mathlib` ensures Mathlib import
   - `--import-mode auto` detects Mathlib from Lake project when possible

5. `batch-audit` supports pilot-scale stability flags:
   - `--resume`
   - `--flush-every N`
   - periodic JSONL flush of audit/response/defect artifacts

6. Packaging is fixed with explicit setuptools package discovery.

## Recommended core Lean real-mode run

```bash
lean-rgc init-lake --out /workspace/lean/projects/lean_rgc_core --no-mathlib
cd /workspace/lean/projects/lean_rgc_core
lake build

cd /workspace/lean-rgc/src/lean_rgc_stack
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/tactic_templates.jsonl \
  --out /workspace/lean-rgc/runs/core_pipeline \
  --lean-cmd "lake env lean" \
  --workdir /workspace/lean/projects/lean_rgc_core \
  --import-mode core \
  --jobs 4 \
  --cache-dir /workspace/lean-rgc/cache/core \
  --resume \
  --flush-every 25
```

## Mathlib mode

Use a Mathlib Lake project and either preserve task imports or force Mathlib:

```bash
lean-rgc init-lake --out /workspace/lean/projects/lean_rgc_mathlib
cd /workspace/lean/projects/lean_rgc_mathlib
lake update
lake build

lean-rgc pipeline \
  --tasks tasks_mathlib.jsonl \
  --actions tactics_mathlib.jsonl \
  --out runs/mathlib_pipeline \
  --lean-cmd "lake env lean" \
  --workdir /workspace/lean/projects/lean_rgc_mathlib \
  --import-mode mathlib \
  --jobs 4 \
  --cache-dir runs/cache \
  --resume
```

## Status

This is still file-mode Lean execution.  It is suitable for 1k--10k micro-audit pilots with cache/resume.  Larger experiments still need a persistent Lean worker/server and structured proof-state extraction.
