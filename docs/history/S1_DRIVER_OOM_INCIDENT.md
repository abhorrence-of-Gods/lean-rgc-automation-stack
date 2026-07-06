# Incident note: S1 stepwise-replay driver OOM (registered fix 2026-07-06)

## What happened

The first S1 stepwise corpus build (commit 77630fe era) ran the whole
script inventory through ONE `LeanServerAdapter` process. The pod-side
run died by OOM before completing. No incident record was committed at
the time (flagged by the 2026-07-06 adversarial review); this note is
the retroactive record required by the S'1 prereg rider.

## Root cause (in-code evidence)

- `lean_rgc/native_lean/RGCKernelRPC.lean`: the worker's `states`
  HashMap retains every KState — each pinning a full `Environment` —
  and the op table has no erase/evict/drop-state operation.
- `register_task` re-runs `importModules` per task with no environment
  reuse across tasks.
- The Python driver (`lean_rgc/evals/stepwise_replay.py`) drove the
  entire corpus through a single worker process with no restarts, so
  retained state grew monotonically with scripts processed.

## Fix (S'1 rider: driver-level, no Lean-side rework)

`replay_scripts` now recycles the worker every `recycle_every` scripts
(default 40; CLI `--recycle-every`). Chains never span scripts, so
recycling at script boundaries is behavior-preserving; the summary
reports `worker_recycles`. Bounded-memory acceptance test:
`tests/test_v101_stepwise_recycle.py` (same transitions, ceil(n/k)
worker instances).

## Residual risk

Within one 40-script chunk the worker still accumulates state; if a
chunk OOMs in practice, lower `--recycle-every` (a per-script recycle
is supported and tested). A protocol-level KState eviction op remains
the clean long-term fix and is explicitly out of S'1 scope.
