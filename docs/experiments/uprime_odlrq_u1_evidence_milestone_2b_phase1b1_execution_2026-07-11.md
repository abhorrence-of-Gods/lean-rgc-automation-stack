# U'1 evidence milestone 2b phase 1b1 execution record (2026-07-11)

Status: EXACT-49 SYNTHETIC SCHEMA/STATE VALIDATION IMPLEMENTED AND VERIFIED;
NOT THE FINAL PARSED-LEDGER VERIFIER, NOT ORIGIN AUTHENTICATION, NOT A
SCIENTIFIC VERDICT, AND NOT A CANONICAL OR GPU LICENSE.

## Temporal and commit boundary

The phase-1b1 implementation was committed and pushed as
`329c48e5b2e314e99f0fb9b49fc06a465707e3e6` on
`origin/codex/uprime-odlrq-plan` before this result record was written. GitHub
Actions CI run `29109082490`, job `pytest`, completed successfully for that
exact head SHA.

The governing M2b preregistration remains
`docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_parsed_ledger_preregistration.md`.
The preceding phase-1a result is anchored by
`docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_phase1a_execution_2026-07-11.md`.
This record reports a narrower engineering slice and does not amend either
document or activate the default-deny rerun registry.

The implementation commit changes exactly six paths: the chain substrate, a
new exact-49 semantic module, the litmus anchor set, the anchor-membership test,
the registered ledger test module, and its noncollectable semantic case-support
module. It creates no reservation, claim receipt, registered run artifact,
remote attempt, report, manifest, or positive license entry.

## Implemented phase-1b1 scope

The phase-specific verifier identity is
`lean-rgc-uprime-rpc-exact-49-sequence-semantics-v0.1`. It is deliberately not
the preregistered final `parsed-ledger-verifier-v1.0` identity.

The implementation validates:

- a structurally closed ledger snapshot whose canonical record bytes are
  retained from the same open handle and two-pass digest used for chain
  attestation, with post-close path binding;
- exactly 49 records in the frozen order: header, local probe, 23 alternating
  durable request intents and active-frame parsed responses, then closure;
- exact header, nested public-receipt, reservation, B4 local-probe, request,
  response, shutdown-transport, and closure field sets;
- receipt/reservation digest and internal identity relations, while explicitly
  leaving token, Git-object, remote, and runtime-origin authentication
  unperformed;
- each operational request object against the frozen sequence, including
  dynamic state, replay, goal, and target values independently derived from
  prior recorded responses using the producer's actual fallback and filtering
  rules;
- strict JSON typed equality, so booleans cannot impersonate integer zero or
  one;
- record-derived counts, index arrays, preclosure head, ID-mismatch count,
  timestamps, monotonic ordering, lifecycle relations, and reason/counter
  relations; and
- the frozen B4 raw predicate and ordered X0 raw predicates without computing
  the other contracts or a scientific disposition.

Scientifically adverse observations remain valid evidence. Tested examples
include response-ID and protocol mismatch, every B4 conjunct failing, bad
shutdown acknowledgement, missing/incorrect X0 telemetry, natural exit after
grace, forced terminate/kill, failed forced reap, bad acknowledgement plus
forced reap, nonzero return code, invalid/non-object/non-JSON stdout, transport
overflow, and post-pair harness reason codes. They produce false raw predicates
or retained reason codes; they are not relabeled as ledger corruption.

The returned attestation states
`semantic_scope=standalone_exact_49_sequence_semantics_only`,
`origin_status=unknown_may_be_synthetic`,
`scientific_disposition=not_computed`, and `authority_scope=none`. Reservation
token, source-blob, remote claim, bundle, report, attempt-manifest, privacy, and
archive checks are `not_performed`; all execution/canonical/later-stage license
booleans are false.

## Frozen-profile support-module interpretation

M2b Section 13 freezes a four-file pytest command and requires every new test
to occur in that profile. The exact command remains unchanged. The large
synthetic matrix resides in
`tests/uprime_rpc_ledger_semantics_cases.py`, whose name is not
default-discoverable by pytest. `tests/test_uprime_rpc_ledger.py` imports its
marked test objects;
pytest collection reports every case under the registered
`tests/test_uprime_rpc_ledger.py` path, exactly once. The support path is itself
an anchored transitive test input. It is not a fifth collected test module or a
change to the frozen command, and the registered test path remains tier
`unit`.

This interpretation was explicitly included in the final governance review.
Because phase 1b1 grants no positive authority, any later stricter reading must
be resolved before final M2b activation rather than by relabeling this result.

## Verification evidence

Local verification used Windows `Microsoft Windows NT 10.0.26200.0` and
CPython `3.13.7`:

1. bytecode compilation of the changed Python modules and tests succeeded;
2. `tests/test_uprime_rpc_ledger.py`, including every imported exact-49 case,
   completed with 171 passed;
3. the exact frozen four-file M2b command completed with 238 passed, zero
   failures/errors/skips/xfails, in 90.16 seconds;
4. the default Windows suite completed with 545 passed, 3 skipped, and 163
   deselected in 266.79 seconds; and
5. `git diff --check` was clean for the implementation scope.

CI run `29109082490` used Ubuntu 24.04 and CPython 3.11.15. It completed with
544 passed, 4 skipped, and 163 deselected in 46.25 seconds; the runtime-boundary
and dead-candidate-ledger checks also passed.

## Adversarial review disposition

Independent specification, implementation, test-coverage, and governance
lenses repeatedly attacked the slice. Their counterexamples forced repairs for:

- bool/int equality coercion in deep JSON comparisons;
- over-rejection of valid `stream_complete=false`, nullable telemetry, and
  other X0-failing evidence;
- request derivation that initially failed to mirror `after_state_id` fallback
  and producer goal-row filtering;
- X0 predicate-name drift from the frozen registry;
- invisible post-pair reason codes in the returned attestation;
- lifecycle races with successful/failed forced reap and no exit mode;
- missing receipt/reservation cross-binding, same-handle snapshot,
  path-replacement, same-size mutation, 48/50-record, time-order, B4-conjunct,
  and failure-preservation tests; and
- ambiguity between the frozen collected test files and the anchored support
  module described above.

After the repairs, both final code and governance re-reviews approved the
current scope with no P0/P1 commit blocker.

## Explicit exclusions and next gate

Phase 1b1 does not validate aborted prefixes, extra parsed responses,
duplicate/late/unsolicited association claims, or their unrecorded
cancellation/clear transitions. It does not independently recompute all eleven
scientific contracts, authenticate any origin or public claim, verify a caller
token, bind a report/attempt manifest/archive, integrate the RPC queue and
quiescence writer, or provide the final independent verifier executable.

Those items remain phase 1b2/phase 2 work. The rerun registry remains strict
default-deny. Canonical U'1 execution, U'0.5 probes, U'2--U'5, remote GPU
construction, and publication claims remain barred.
