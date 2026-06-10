# Lean-RGC v48: Kernel Goal-State Server Schema

v48 introduces the strict `lean-rgc-kernel-state-v1` payload and an in-process
`KernelGoalStateServer` facade.

It provides:

- strict top-level kernel-state fields: `state_id`, `env_fingerprint`,
  `state_hash_raw`, `state_hash_norm`, `status`, `proof_prefix_hash`
- `ExprGraph`, `LocalContextGraph`, `MetavariableGraph`, and `TypeclassGraph`
  payloads with raw and normalized hashes
- quotient-safe normalization for local names, fvar ids, mvar ids, and binder
  names in text-backed payloads
- persistent branch/rollback state ids through the server facade
- `apply_tactic` transition records carrying before/after kernel states,
  state delta, structural response, replay certificate, and safety checks
- CLI support:

```bash
lean-rgc kernel-state-normalize --kernel-jsonl kernel_states.jsonl --out strict_kernel_states.jsonl
lean-rgc kernel-state-probe --task-json task.json --action-json action.json --backend dry_run --out probe.json
```

The packaged Lean worker now emits the v1 envelope.  In the current source-check
worker, native `Expr` / `LocalDecl` / `MVar` extraction is still partial and is
reported through `object_coverage`.  A future TacticM/MVarId-resident Lean worker
can fill the same v1 schema without changing RGC-side response dynamics.
