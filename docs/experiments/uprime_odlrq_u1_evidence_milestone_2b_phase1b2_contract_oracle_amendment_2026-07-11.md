# U'1 evidence milestone 2b phase 1b2: independent contract-oracle amendment

Status: FROZEN BEFORE PHASE-1B2 IMPLEMENTATION; NO CANONICAL EXECUTION OR GPU
WORK IS LICENSED.

## 1. Purpose and timing

The M2b preregistration requires independent recomputation of all eleven U'1
contracts from the parsed ledger. Phase 1b1 showed that the exact 49-record
sequence is implementable, but adversarial specification review found several
places where mechanically copying the current production evaluator would make
the independent oracle either depend on data absent from the ledger or retain
missing-versus-null loopholes.

This amendment resolves only those oracle-interface questions before any
phase-1b2 implementation or result exists. No canonical post-repair diagnostic
has run, no positive rerun license exists, and no live result was inspected in
making these choices.

## 2. Frozen phase boundary

The phase-specific oracle id is
`lean-rgc-uprime-rpc-exact-49-contract-oracle-v0.1`. It is neither the final
M2b verifier id nor a report, verdict, bundle, origin, or publication verifier.
The exact `oracle_scope` value is
`standalone_exact_49_raw_contract_predicates_only`.

Its public path API accepts only a ledger path. It must load one same-handle
snapshot, independently enforce the phase-1b1 exact-49 semantic precondition,
then re-extract all requests, responses, the local probe, and closure from those
record bytes. It must not accept caller-supplied response maps, request IDs,
context, report rows, contract summaries, a phase-1b1 predicate scalar, or an
X0 scalar.

If chain, record, exact-body, request, frame, association, or state-machine
semantics are invalid, contract recomputation is `not_computed`: the oracle
raises a phase-scoped validation error and returns no eleven-value vector.
Within a valid captured response object, however, a missing, mistyped, or wrong
scientific telemetry field makes the affected frozen check false when that
absence does not already invalidate the exact dynamic-request precondition. It
is not a ledger error and must never be converted to true by default.

The exact public binding object contains only:

```text
oracle_schema_version
oracle_scope
origin_status
input_sha256
input_bytes
final_chain_head
record_count
contract_ids
contract_passes
contract_failure_ids
raw_all_contracts
reservation_token_verification
source_blob_authentication
remote_claim_authentication
bundle_binding
report_binding
attempt_manifest_binding
privacy_scan
archive_verification
authority_scope
canonical_run_authority
licenses_execution
licenses_later_stage
```

`contract_ids` is the fixed ordered registry below; `contract_passes` is its
same-length boolean array; failure IDs are the false entries in registry order;
`raw_all_contracts` is their conjunction. Diagnostic per-check rows are
implementation-private, nonbinding, and excluded from this public object.

The object may expose `raw_all_contracts=true` for fully synthetic bytes. It
must not emit `CLEAR`, `BLOCKED`, `verdict`, `finalized`, `verifier_passed`, or
a scientific disposition. Origin remains `unknown_may_be_synthetic`; all
authentication/binding stages are `not_performed`; authority is `none`;
canonical/execution/later-stage licenses are false.

## 3. Fixed contract registry and nonvacuity

The order is exactly:

```text
R0_request_id_echo
B0_task_budget_init
B1_action_budget_nonsticky
B2_budget_telemetry
B3_enforcement_reset
B4_cache_budget_semantics
D0_target_routing
D1_transition_delta
D2_all_goal_sweep
R1_independent_replay
E0_episode_budget
```

The oracle uses fixed label registries: 23 envelopes, five init responses,
eight action responses, seven non-burn delta/replay pairs, and episode groups
of sizes 3, 2, 1, 1, and 1. Every aggregation checks its exact registry before
calling `all`; dynamic or empty caller collections are forbidden. Integer
checks exclude booleans, and nested equality uses strict canonical JSON rather
than Python bool/int-coercing equality.

Except for the explicit clarifications in Sections 4 through 6, the raw
predicates and their cross-contract division remain those frozen by the U'1
amendments and current `evaluate_contracts`: B0 accepts integer or digit-string
`maxHeartbeats`; B4 does not add a new check on
`resolved.explicit_default`; D0 does not duplicate all D1 checks; D1 does not
duplicate all B0 checks; and B2 does not absorb B3's burn-exceeds-cap check.

## 4. D2 selector transport clarification

The current production D2 row checks the transient context string
`side_target_selector=refine_tuple_position_1`. That string is not present in
the M2b record schemas and therefore cannot be independently recomputed from a
ledger.

For this independent oracle only, the source-string check is replaced by its
recorded operational predicate:

1. the side-init response's raw ordered goal list has exactly two distinct,
   nonempty string `mvar_id` rows;
2. the side-effect apply request contains `target_mvar_id`; and
3. that target equals the second ordered side-init goal.

All remaining D2 checks stay frozen: the action succeeds, its delta is valid,
the after-goal list is empty, the independently derived assigned and closed
sets equal both initial side goals, and all eight action after-states are well
formed. The replacement proves the recorded selection behavior; it does not
claim to recover the unrecorded source variable name.

## 5. R1 presence-aware null clarification

The current evaluator uses `.get`, which treats a missing key like explicit
JSON null in two places. The independent oracle closes those evidence-presence
holes:

- every replay response must contain `target_mvar_id`; its value must strictly
  equal the primary apply request's target, using explicit null when that apply
  request has no target; and
- every replay certificate must contain `error`, whose value must be explicit
  null for the verified path.

Missing and explicit null are therefore distinct evidence states. All other R1
requirements remain fixed: primary delta validity; response success;
before/after/action/target binding derived from raw requests; unchanged state
table; fresh independent reexecution with positive integer heartbeats; exact
before/expected/observed state and delta equality; and the frozen certificate
schema, method, status, and match fields.

## 6. B2 presence and strict-equality clarification

The zero-option B2 branch has another missing-versus-null ambiguity: `.get` on
`effective_max_heartbeats_counter` accepts an omitted key as though explicit
JSON null had been recorded. The independent oracle instead requires both the
top-level budget object and its mirrored
`audit.audit_flags.heartbeat_telemetry` object to contain all of these frozen
telemetry keys:

```text
effective_max_heartbeats_option
effective_max_heartbeats_counter
unlimited
source
consumed_heartbeats_counter
episode_max_heartbeats_counter
episode_remaining_heartbeats_counter
episode_source
measurement_scope
reset_scope
```

The two objects must be strictly equal. For `zero_split`, the counter key is
present with explicit null; absence makes B2 false. Top-level and audit
heartbeat scalars remain separately required by the existing predicate.

The current Python evaluator also compares some nested JSON values with Python
equality, under which `true == 1` and `false == 0`. The independent oracle uses
canonical strict-JSON equality for the budget mirror, predecessor kernel
objects, replay state objects, and replay delta objects. This is an explicit
evidence-integrity clarification, not an unlisted change: it preserves JSON
type distinctions already required by M2b and prevents bool/int substitution
from satisfying an equality predicate.

For B0/B1 option extraction, an integer remains valid and a string form is
accepted only when it matches ASCII `[0-9]+`; leading zeroes retain the current
numeric interpretation. Unicode `isdigit` forms, signs, empty strings, and
failed conversions make the affected predicate false and never raise. This
closes the current `str.isdigit()`/`int()` exception edge while retaining the
documented integer-or-digit-string behavior.

## 7. Independent derivation and provenance limits

The implementation may share only the strict ledger JSON/hash/chain-snapshot
substrate. It loads once and independently validates and extracts exact-49
semantics from that immutable snapshot. It must not import or call phase-1b1
semantic entry points, predicate scalars, the production contract evaluator,
disposition function, response summarizer, cache probe, or caller context. B4
is recomputed from the ledger's raw local probe. State views, structure checks,
deltas, budgets, episode accounting, targets, predecessor continuity, replay
specs, and control checks are all reconstructed from the 49 records.

For avoidance of doubt, this amendment supersedes the parent M2b Section 11
sharing sentence only to permit the bounded, nonsemantic chain-snapshot I/O
primitive needed for one-handle reading. It does not permit sharing phase-1b1
semantic validation or any production contract predicate.

State and metavariable provenance is chain-local. Global metavariable-name
uniqueness is not required because independent primary and zero trajectories
may legitimately reuse printed identifiers. Each action must instead bind its
request state to the response before ID, before-kernel ID, and exact predecessor
kernel object; the response after ID must bind its after-kernel object. Targets
must be selected from the relevant ordered predecessor goals.

Self-consistent, fully rehashed synthetic states can satisfy all raw predicates.
That demonstrates oracle reachability only. It authenticates neither Lean
execution nor the source of any response.

Phase 1b2 does not bind a final report. In the later report phase, the exact
ordered independent boolean vector and its input digest/head are authoritative.
Any production-evaluator vector is diagnostic only; a disagreement is recorded
and cannot yield a clear result. The final report schema for that disagreement
remains a phase-2 freeze obligation.

## 8. Finite phase-1b2 acceptance matrix

Before a phase-1b2 result commit, the frozen four-file M2b command must collect
the added cases through the anchored ledger test support and pass with zero
failures/errors/skips/xfails. Required cases include:

1. one rich exact-49 synthetic fixture with all eleven raw predicates true and
   every authority/license field negative;
2. the same result while the phase-1b1 semantic entry point and production
   evaluator, disposition, response-summary, and cache-probe helpers are
   raising sentinels;
3. an isolated, fully rehashed false case for every contract ID;
4. missing shutdown protocol affects R0 but remains computed evidence;
5. explicit-null versus missing R1 target and certificate-error pairs, plus an
   explicit-null versus missing zero-option budget-counter pair;
6. budget mirror, zero-option, cap, heartbeat type, episode-accounting, and burn
   boundary cases that expose the frozen cross-contract divisions;
7. cumulative/forged delta, assigned-open goal, predecessor transplant, target,
   replay action/state/delta/certificate, and chain-local name-reuse cases;
8. scientific response/B4 failures remain computed false, while torn chains,
   wrong count/order/index/association, and dynamic-request violations produce
   no contract vector;
9. forged caller report/context data is not accepted by any public API; and
10. deterministic output for fixtures built with different in-memory insertion
    orders but identically canonicalized bytes, plus strict rejection of raw
    noncanonical key order, bool-as-int substitutions, and non-ASCII/failed
    digit-string conversions;
11. exactly one chain snapshot/path open per evaluation, with retained-record
    same-size mutation and path-replacement rejection; and
12. the new oracle source and case-support paths are present in `ANCHOR_PATHS`
    and its membership test before any phase-1b2 result commit.

No case may start Lean, use a registered run path, contact a network or remote
claim, or access GPU infrastructure.

## 9. Stop rule

Passing phase 1b2 closes only independent raw-predicate recomputation for the
exact-49 complete sequence. Aborted/anomalous ledgers, bundle/receipt/token and
runtime-origin authentication, RPC writer/queue/quiescence integration, report
and attempt-manifest binding, privacy/archive controls, the final independent
verifier, and canonical execution remain later gates. U'0.5, U'2--U'5, and GPU
construction remain barred.
