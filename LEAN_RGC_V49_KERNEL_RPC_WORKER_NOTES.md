# Lean-RGC v49: In-Memory Lean Kernel RPC Worker

v49 adds a native Lean JSONL worker for the strict kernel-state design.

Implemented:

- `lean_rgc/native_lean/RGCKernelRPC.lean`
- process-local opaque `state_id`s backed by real Lean `Core.State`,
  `Meta.State`, `Term.State`, and open `MVarId`s
- `init_state`, `apply_tactic`, `kernel_state`, `branch_state`,
  `rollback_state`, `list_states`, `status`, and `shutdown`
- direct tactic transition via `Lean.Elab.runTactic`
- strict `lean-rgc-kernel-state-v1` payloads with:
  - Expr DAG nodes/edges/roots
  - LocalContextGraph nodes and dependency edges
  - Metavariable graph nodes with assignment/dependency readouts
  - typeclass-obligation readouts for class-headed metavariables
  - raw and normalized hashes
  - before/after transition deltas and replay certificate stubs
- Python launcher support with `--exec-mode kernel_rpc`

The worker source is small and is copied into `.lean_rgc/RGCKernelRPC.lean`
when installed.  Lean itself is installed by elan outside the repository, so the
repository does not vendor Lean or Mathlib.

Current limits:

- replay certificates are emitted but replay source verification is still
  `pending`
- arbitrary command/section/open-declaration prefixes are not reconstructed as
  a full frontend namespace context
- Lean exposes stable class-headed metavariables, but not a public stable
  internal typeclass search tree; the worker returns obligation nodes instead
  of a full synthesizer trace graph
