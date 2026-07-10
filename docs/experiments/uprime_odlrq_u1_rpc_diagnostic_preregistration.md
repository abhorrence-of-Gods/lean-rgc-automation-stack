# U'1 live RPC diagnostic preregistration

Status: FROZEN BEFORE FIRST LIVE EXECUTION. The preregistration, harness,
synthetic unit tests, and tier entry must be committed and pushed together.
The executable rejects uncommitted anchor inputs and an anchor absent from its
configured upstream.

This protocol is licensed by the T0 result recorded in
`uprime_odlrq_t0_execution_2026-07-10.md`. It uses no benchmark task or model
proposal. All inputs are synthetic and development-public.

## Purpose and scope

Replace K0-R source-pattern smoke checks by a single-process Windows CPU
behavioral diagnostic of the current native Lean RPC. The diagnostic covers
parts of M0, M1, M2, and M4:

- task/action heartbeat inheritance, explicit-zero semantics, non-stickiness,
  enforcement, reset, and telemetry;
- episode-budget field presence and monotonic remaining value;
- explicit target metavariable routing;
- before/after transition delta and all-goal assignment sweeping;
- independent replay status;
- request-id echo;
- cache preservation of the Lean convention `0 = unlimited`.

It does not test M3 boundary/read provenance, full canonical signatures,
process-kill resynchronization, or the full F0--F3 frame contract. Even a clear
diagnostic cannot license K1--K4, U'2--U'5, or GPU work.

## Frozen worker and budget

- Platform: the registered Windows CPU workspace.
- Toolchain: `leanprover/lean4:v4.31.0`; any other `lean --version` is a
  harness error. The frozen `lean.exe` SHA-256 is
  `9B216DEB50D37C32C829D1EFAAA5BAFD5560417D382DF35A815489E31A31593F`;
  any other executable bytes are also a harness error.
- Worker source: `lean_rgc/native_lean/RGCKernelRPC.lean`.
- All anchor inputs must match their `HEAD` Git blobs. The worker executes a
  temporary byte copy of the committed worker blob, and HEAD/worktree blob
  identities are rechecked after shutdown.
- Runtime: one direct `lean --run` process with imports `Lean`.
- One JSONL request stream; no worker restart between probes.
- Per-request and total live RPC-stream deadline: 900 seconds. Preflight is
  outside that clock; forced cleanup or reader drain may use at most ten
  additional seconds. Any `--timeout-s` value other than exactly `900` is
  rejected before Lean starts.
- Task heartbeat option: `731` (Lean option units; internal cap `731000`).
- Episode heartbeat budget: `1000000` internal counter units.
- Successful constructor override: `123456` option units (internal cap
  `123456000`).
- Burn-action override: `200000` option units (internal cap `200000000`).
- Synthetic burn increment: `400000000` internal heartbeats.
- The burn probe is last except for its immediate reset check.

Lean's `maxHeartbeats` option is expressed in units of 1000 internal heartbeat
counter increments. Every registered field below names its unit explicitly;
option values and counter values must never be compared without conversion.
Per-action consumption is the counter difference around that action's
`CoreM.toIO` execution only. Prefix replay, serialization, and minimal-support
extraction are outside that measurement scope. File/bulk source-check lanes may
budget a larger command scope, so their consumption is not numerically
interchangeable with the kernel-RPC lane.

Default CI may run the harness's pure synthetic oracle tests. They do not start
Lean or construct live responses and therefore are not a live execution. The
canonical CLI below is the first live probe.

## Frozen request sequence

1. `load_project` with import `Lean`.
2. `init_state` for task `True ∧ True`, carrying task budget `731` and episode
   budget `1000000`.
3. Apply `constructor` with action override `123456`.
4. Read the two resulting mvar IDs. Apply `exact True.intro` to the tail using
   request-level `target_mvar_id`, with no action heartbeat override.
5. Apply `exact True.intro` to the remaining head goal using its explicit ID.
6. Initialize a second `True ∧ True` state with the same task/episode
   budgets. Apply `constructor` with explicit action budget `0` (unlimited),
   then apply `exact True.intro` to an explicit child goal with no override.
   The second action must return to task baseline `731`, not inherit `0`.
7. Initialize `∃ n : Nat, n = 0` with prefix `refine ⟨?_, ?_⟩`. Target the
   equality goal with `rfl`; the side-effect assignment of the witness goal
   must be reported and swept from the open-goal list.
8. Initialize a separate `True` state with the same task/episode budgets.
9. Apply
   `run_tac do IO.addHeartbeats 400000000; Lean.Core.checkMaxHeartbeats
   "uprime-litmus"` with action budget `200000`.
10. Initialize another `True` state in the same worker and apply `trivial` with
   action budget `200000` to test per-action reset.
11. Request worker status and shutdown.

Immediately after each of the seven expected-success/partial actions
(`primary_split`, both primary closes, `zero_split`, `zero_child_close`,
`side_effect_close`, and `reset`), the harness sends a distinct
`replay_transition` request naming the original before state, expected after
state, exact action, and target. The replay command must reexecute from the
immutable before state without inserting another persistent child. Thus the
full stream contains 23 request/response frames; the deliberate burn is not
replayed. Each replay response reports equal state-table counts before/after,
and final status must report exactly 13 persistent states (five init states plus
eight primary action results), proving replay did not insert a child. It also
reports `reexecution_performed = true`, a positive
`reexecution_heartbeats_counter`, and
`reexecution_scope = fresh_from_immutable_before_state`. The status request is
frame 22 and must report `n_requests = 22`; shutdown is frame 23.

All requests carry distinct IDs. The worker must echo the same ID and exact
protocol identifier `lean-rgc-jsonl-rpc-v2`; sequential transport alone is not
accepted as M4 evidence.

## Independent state/delta oracle

For every successful/partial transition, derive from serialized before/after
kernel states:

```text
before_goals = set(before.goals[*].mvar_id)
after_goals = set(after.goals[*].mvar_id)
before_assigned = set(before.metavars[assigned=true].mvar_id)
after_assigned = set(after.metavars[assigned=true].mvar_id)
before_mvars = set(before.metavars[*].mvar_id)
after_mvars = set(after.metavars[*].mvar_id)

expected_assigned = after_assigned - before_assigned
expected_closed = before_goals intersect expected_assigned
expected_new_goals = after_goals - before_goals
expected_new_mvars = after_mvars - before_mvars
```

The reported four sets must match exactly, and
`after_goals intersect after_assigned` must be empty. Lists are compared as
sets; no missing/extra item or duplicate is tolerated.

## Frozen contracts

`R0_request_id_echo`: every response echoes its request ID and carries
`rpc_protocol_version = lean-rgc-jsonl-rpc-v2`. Load, status, and shutdown
control responses must also report their expected successful flags.

`B0_task_budget_init`: initial state option `maxHeartbeats` is exactly `731`.

`B1_action_budget_nonsticky`: the first constructor executes with effective
option `123456`, but the child state's stored task/default option remains `731`;
the next action without override resolves to `731` from the task. In the second
chain, explicit `0` means unlimited for that action only, and its descendant
without an override again resolves to task option `731`.

`B2_budget_telemetry`: every action reports the same object at top-level
`budget` and `audit.audit_flags.heartbeat_telemetry`, containing
`effective_max_heartbeats_option`,
`effective_max_heartbeats_counter`, `unlimited`, `source`,
`consumed_heartbeats_counter`, `episode_max_heartbeats_counter`,
`episode_remaining_heartbeats_counter`, `episode_source`, `measurement_scope`, and
`reset_scope`. A nonzero effective counter cap is exactly 1000 times its option
value; option `0` is marked unlimited and has no finite counter cap. Top-level
`heartbeats` and `audit.heartbeats` both equal
`consumed_heartbeats_counter`. Episode remaining is monotonically
non-increasing within each initialized task chain. The fixed values are
`episode_source = task`, `measurement_scope = action_corem_toio_counter`, and
`reset_scope = per_corem_toio_call`. Effective option/source pairs are frozen
per action: constructor `123456/action`; ordinary unoverridden closes
`731/task`; zero constructor `0/action`; burn and reset `200000/action`. Every
finite expected-success/partial action must report consumed counter less than
or equal to its effective counter cap; only the deliberate burn must exceed it.

`B3_enforcement_reset`: the burn action returns `timeout`; the immediately
following simple action in the same process returns `success`, proving that the
action heartbeat baseline was reset. The burn response must be `ok`, its audit
must also say `timeout`, consumed counter must exceed the finite `200000000`
cap, its semantic state/normalized hash must be unchanged, and its delta must
be empty and independently valid.

`B4_cache_budget_semantics`: the Python cache resolver returns task `731` when
the action field is absent, returns `0` when action value is zero, and returns
the explicit nonzero override otherwise. When both fields are absent it returns
the runtime default `200000`, making omitted and explicit-default cache keys
identical.

`D0_target_routing`: after tail-targeted `exact True.intro`, the original head
remains open and the target tail is assigned/removed. The separate zero-budget
chain must satisfy the same explicit-tail invariant.

`D1_transition_delta`: every expected-success/partial action in the frozen
sequence (all actions except the deliberate burn timeout) succeeds and matches
the independent four-set delta oracle. Each response's before-state ID must
equal the exact state ID sent in that request; init summary IDs must equal their
kernel-state IDs. Each full before-kernel object must exactly equal the prior
init state or predecessor action's after-kernel object.

`D2_all_goal_sweep`: no serialized open goal is assigned after any transition.
In the existential side-effect probe, both the targeted equality and witness
goals are newly assigned/closed and the after-goal set is empty.

`R1_independent_replay`: every registered `replay_transition` response binds
the original before-state ID, expected after-state ID, action ID, and target. It
returns the original before/expected kernel states and delta plus a freshly
reexecuted observed kernel state and delta. The harness requires exact
three-way equality between primary, expected, and observed objects. The
response also carries a `lean-rgc-kernel-replay-certificate-v1` certificate
with `verification_method = same_before_state_independent_reexecution`, status
`verified`, `state_match = true`, `delta_match = true`, and null error. A
certificate embedded only in the primary response, `pending`, or a bare
self-asserted status is a failure. The harness records canonical sorted-key JSON
SHA-256 values; the Lean worker need not implement SHA-256.

`E0_episode_budget`: the registered episode limit/source/remaining fields are
present. Within each initialized task chain, remaining starts at the registered
limit and after each action equals
`max(0, prior_remaining - consumed_heartbeats_counter)`, hence is monotone.
This diagnostic does not prescribe the later policy for allocating episode
budget across branches.

## Frozen verdict

All eleven contracts must be true for `U1_DIAGNOSTIC_CLEAR`. Any false/missing
contract yields `U1_DIAGNOSTIC_BLOCKED`. A worker launch/protocol exception
yields `HARNESS_ERROR` and is preserved, not silently converted into a contract
failure. Every verdict keeps `licenses_later_stage=false`.

The expected current result is blocked; this expectation is not part of the
decision rule. Repair must preserve the first artifact and use a new anchored
revision.

The diagnostic itself bypasses all caches. B4 tests only budget-value identity;
it does not license the legacy audit cache for stateful target actions.
`lean_rgc.lean.worker_supervisor.audit_cache_eligibility` hard-disables cache
lookup and store for the `kernel_rpc` lane until the key includes
protocol/transition semantics, full before-frame identity, and
`target_mvar_id`.

## Anchored command

After pushing the anchor, substitute its 12-character prefix:

```powershell
python -m lean_rgc.evals.uprime_rpc_litmus `
  --repo-root . `
  --anchor <ANCHOR12> `
  --out runs/uprime_u1_rpc_20260710/rpc_diagnostic_<ANCHOR12>.json `
  --timeout-s 900
```

Before Lean starts, a sibling `<output>.reservation` path is exclusively
created as a durable `LIVE_EXECUTION_RESERVED` JSON record. The output path
must be exactly
`<repo>/runs/uprime_u1_rpc_20260710/rpc_diagnostic_<ANCHOR12>.json`; alternative
directories or names are rejected. The completed JSON is serialized to an
exclusive same-directory temporary file, flushed, and atomically hard-linked to
the previously nonexistent final path (there is no overwrite operation). The
matching reservation is reverified immediately before publication and remains
as evidence. A crash leaves only the reservation and does not license a rerun.
A tracked publication-safe derivative and raw/public hash manifest are
committed after execution.
