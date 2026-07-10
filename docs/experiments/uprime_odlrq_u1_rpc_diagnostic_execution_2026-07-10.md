# U'1 native RPC diagnostic execution record (2026-07-10)

Status: FIRST ANCHORED EXECUTION CLOSED AS HARNESS_ERROR.

## Temporal anchor

The preregistration, harness, pure oracle tests, tier entry, and stateful-RPC
cache exclusion were committed as
`eb38b4b9c0cb2711c88bb9bea8f2e5646d851925` and pushed to
`origin/codex/uprime-odlrq-plan` before execution. The branch was 0 ahead / 0
behind its upstream. CI run `29095539730` completed successfully before the live
probe.

No live Lean process was started by the preregistration tests. Three independent
static review passes reported no remaining release blocker before the anchor was
committed.

## Canonical Windows CPU execution

```powershell
python -m lean_rgc.evals.uprime_rpc_litmus `
  --repo-root . `
  --anchor eb38b4b9c0cb `
  --out runs/uprime_u1_rpc_20260710/rpc_diagnostic_eb38b4b9c0cb.json `
  --timeout-s 900
```

The canonical output was reserved before Lean launch, then atomically
published. Result:

- verdict: `HARNESS_ERROR`;
- failure: `RuntimeError: side-effect fixture did not expose witness and
  equality goals`;
- elapsed live-harness time: `71.116913` seconds;
- last completed response: `side_init` (frame 14 of the frozen 23-frame
  stream);
- `licenses_later_stage=false`.

The ignored raw artifact SHA-256 is
`B6636510C6D47CB370FBDFFFAB81BEB4D417915A6DD6CF67E8F95DBF5B13C5B1`.
The durable reservation sidecar SHA-256 is
`E3639542834D87C3674AFC7AC05347CA96FE791C42F6224872A412470AAF8612`.

## Failure diagnosis

The worker successfully initialized the registered existential fixture. Its
compact saved state view contains exactly two open goals, so prefix replay did
not fail. The harness nevertheless required the serialized goal rows to expose
exactly one `relation == "="` marker before selecting the target. That selector
returned a non-singleton result and raised before the side-effect action, burn,
reset, status, shutdown, or contract aggregation ran.

Therefore this artifact is not evidence for either `U1_DIAGNOSTIC_CLEAR` or
`U1_DIAGNOSTIC_BLOCKED`. It is an implementation defect in the preregistered
fixture selector. The already-visible null request IDs, null heartbeat
telemetry, pending/unknown replay responses, and sticky state options remain
diagnostic observations only; the eleven-contract verdict was never computed.

## Disposition

The raw artifact and reservation remain immutable. They will not be overwritten
or relabeled. A selector amendment must be committed and pushed under a new
anchor before a second canonical live execution. The deterministic Lean tactic
`refine ⟨?_, ?_⟩` produces witness then proof goals, so the amendment may freeze
the second returned goal as the equality target while retaining the existing
two-goal cardinality check.

GPU construction, K1--K4, and U'2--U'5 remain barred.
