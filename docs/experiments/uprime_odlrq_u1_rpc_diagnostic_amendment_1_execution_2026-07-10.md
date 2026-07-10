# U'1 RPC diagnostic amendment 1 execution (2026-07-10)

Status: SECOND ANCHORED EXECUTION CLOSED AS HARNESS_ERROR.

## Anchor and command

Selector amendment 1 was committed as
`fc6b69ea14fb2d7820a190aea22df9409f59b666`, pushed with upstream 0/0, and
passed CI run `29096213184` before execution.

```powershell
python -m lean_rgc.evals.uprime_rpc_litmus `
  --repo-root . `
  --anchor fc6b69ea14fb `
  --out runs/uprime_u1_rpc_20260710/rpc_diagnostic_fc6b69ea14fb.json `
  --timeout-s 900
```

## Result

- verdict: `HARNESS_ERROR`;
- error: `TimeoutError: U'1 RPC worker did not exit after shutdown`;
- elapsed harness time: `117.120953` seconds;
- all 23 registered responses, including status and `shutdown:true`, were
  received and compactly preserved;
- `licenses_later_stage=false`.

The ignored raw artifact SHA-256 is
`054FE61EEEB10493037530ACBF70197729C756E42EAACC4FB9C3FDF5D0341A88`.
The durable reservation sidecar SHA-256 is
`45ED3A7F40791B8FF3E701D7054B9E4ACF14BBB72D3F29E7025AC5934BD148AF`.

## Diagnosis

Amendment 1 worked: frame 14 passed, the side-effect action and its replay
request ran, and the stream reached burn, reset, status, and shutdown. The
worker returned a successful shutdown response and status reported 13
persistent states, but the Lean process did not finish post-response teardown
inside the harness's original ten-second wait. The artifact does not establish
that the retained states caused the delay. The harness then terminated the
process and, by its stricter-than-contract operational rule, discarded contract
aggregation in favor of `HARNESS_ERROR`.

This is not evidence that any U'1 contract passed. The artifact visibly retains
known blocking observations (for example absent request/protocol echo, null
budget telemetry, unknown replay commands, and pending primary replay), but the
eleven-contract evaluator was not reached.

## Disposition

The raw/public artifact and reservation are immutable. A second amendment must
separate a valid `shutdown:true` protocol response from slow process teardown.
Because process-kill resynchronization was explicitly outside the original
scientific scope, bounded post-response reap may be recorded as transport
telemetry rather than suppressing the contract verdict. That change must be
committed and pushed under a new anchor before another live run.

GPU construction and all later U' stages remain barred.
