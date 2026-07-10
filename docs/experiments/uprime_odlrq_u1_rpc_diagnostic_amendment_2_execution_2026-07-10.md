# U'1 RPC diagnostic amendment 2 execution (2026-07-10)

Status: THIRD ANCHORED EXECUTION CLOSED AS `U1_DIAGNOSTIC_BLOCKED`.

## Anchor and command

Amendment 2 was committed as
`4ba370f543c82f4e8edef92b587645aec7674349`, pushed with upstream 0/0, and
passed CI run `29098472020` before execution.

```powershell
python -m lean_rgc.evals.uprime_rpc_litmus `
  --repo-root . `
  --anchor 4ba370f543c8 `
  --out runs/uprime_u1_rpc_20260710/rpc_diagnostic_4ba370f543c8.json `
  --timeout-s 900
```

The canonical output and reservation paths did not exist before this command.
The exact registered Windows Lean executable SHA-256 was rechecked immediately
before execution.

## Result

- verdict: `U1_DIAGNOSTIC_BLOCKED`;
- 23 registered requests and 23 responses;
- eleven evaluated contracts, all false;
- verdict-level transport gate `X0_shutdown_transport_clear=false`;
- elapsed harness time: `93.615763` seconds;
- `licenses_later_stage=false`.

The ignored raw artifact is 91,831 bytes with SHA-256
`7E6FE9DC6101CA02A06C9D3A18EFC5FFA4C129F1FB6170126FAEC041F590D80F`.
The reservation sidecar SHA-256 is
`E0B4B556AA143CB7541B5B12B6E70363C2BF4776F094DB4CCDF9EBB33052BC42`.
The sidecar contains the live reservation token and is not published. Its token
hash matches the hash committed by the raw report.

All response receipt hashes match their compact response summaries. The
pre-execution and post-execution anchor snapshots are identical. Status at
registered frame 22 reports `n_states=13`, `n_requests=22`, and `n_failures=2`;
shutdown is registered frame 23.

## Terminal transport disposition

Frame 23 returned `ok=true, shutdown=true`. Natural exit did not occur in the
five-second grace. The harness invoked terminate and then kill; bounded reap
succeeded with return code 1. Both reader threads joined, the stdout queue held
exactly one EOF and no residual response, and overflow, non-JSON stdout, and
stderr counts were zero. Total post-response finalization was
`7.0743966000154614` seconds, inside the fixed ten-second deadline.

Amendment 2 therefore correctly allowed the eleven contracts to be aggregated
instead of producing a third harness error. It also correctly denied CLEAR:
`natural_exit_within_grace`, `no_forced_reap`, and `returncode_zero` are false,
while every other X0 check is true.

## Contract failures by common cause

The twelve names in the top-level failure list are not twelve independent root
causes. The observed failures form five repair groups.

1. **Envelope (`R0`).** Every response lacks the request ID and
   `rpc_protocol_version`. The load/status/shutdown control flags themselves are
   present and correct.
2. **Budget substrate (`B0`--`B4`, `E0`).** Every initialized state stores the
   runtime default option `200000`, not task option `731`. Action overrides are
   stored persistently in their child states (`123456` and `0`) instead of
   returning descendants to the task baseline. All registered budget/episode
   telemetry is absent. The burn returns `failure`, not the required exposed
   `timeout`, although the reset action succeeds; without telemetry this does
   not prove that heartbeat enforcement itself is absent. Independently, the
   Python cache resolver maps an omitted default to the empty string rather
   than runtime default `200000`, so the omitted and explicit-default cache
   identities differ.
3. **Target routing and deltas (`D0`, `D1`, `D2`).** Tail-targeted actions do
   not close the named tail, constructor deltas omit newly assigned
   metavariables, close deltas include prior cumulative assignments, and the
   existential side-effect action fails. Other registered delta sets and state
   continuity checks pass. These facts cascade across all three contracts;
   they must not be counted as independent estimates of defect prevalence.
4. **Independent replay (`R1`).** All seven registered replay requests return
   `unknown cmd: replay_transition`; no replay certificate or independent
   reexecution evidence exists.
5. **Lifecycle (`X0`).** The completed response stream required forced process
   reap and therefore cannot qualify for CLEAR even if every scientific
   contract were later repaired.

## Decision and next repair order

U'1 remains blocked. U'0.5 kill probes, later U' stages, and GPU construction
remain barred. The diagnostic now provides a stable repair oracle, so repairs
must use new pushed anchors and retain this result unchanged.

The dependency-minimal repair order is:

1. preserve append-only full response frames for independent recomputation,
   then add request/protocol echo and fix the independent cache omitted-default
   identity;
2. fix task initialization and non-sticky action-option state semantics;
3. implement explicit target routing and all-goal sweep, then differential
   assignment accounting;
4. add heartbeat/episode telemetry and typed timeout classification before
   judging enforcement;
5. implement independent replay from an immutable before state;
6. isolate the slow natural shutdown with a separate Windows microprobe,
   without assuming that the 13 retained states are causal.

Each repair milestone must be committed and pushed with unit/fixture evidence.
The next canonical live artifact is reserved until those fixtures form a CLEAR
candidate, avoiding repeated result-aware one-shot runs. A later CLEAR still
would not by itself license GPU work or U'2--U'5.
