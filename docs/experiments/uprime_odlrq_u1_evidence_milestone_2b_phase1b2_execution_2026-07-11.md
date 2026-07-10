# U'1 evidence milestone 2b phase 1b2 execution record (2026-07-11)

Status: INDEPENDENT EXACT-49 RAW-CONTRACT ORACLE IMPLEMENTED AND VERIFIED;
SYNTHETIC REACHABILITY ONLY, NOT RUNTIME-ORIGIN AUTHENTICATION, NOT THE FINAL
PARSED-LEDGER VERIFIER, NOT A SCIENTIFIC VERDICT, AND NOT A CANONICAL, RERUN,
OR GPU LICENSE.

## Temporal and commit boundary

The phase-1b2 implementation was committed and pushed as
`e04fed42685c8bdbd324b65b165f4bbe87cc02e9` on
`origin/codex/uprime-odlrq-plan` before this execution record was written.
GitHub Actions CI run `29118116900`, job `pytest` (`86446456785`), completed
successfully for that exact head SHA.

The governing documents remain:

- `docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_parsed_ledger_preregistration.md`;
- `docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_phase1b2_contract_oracle_amendment_2026-07-11.md`;
- the phase-1a standalone-chain execution record; and
- the phase-1b1 exact-49 semantic execution record.

This record reports the preregistered phase-1b2 engineering slice. It does not
amend an endpoint, activate the default-deny rerun registry, create a registered
attempt, or authenticate a Lean process. The implementation commit changes
exactly six paths: the new oracle, its noncollectable case-support module, the
rich exact-49 fixture support, the registered collector, the anchor set, and
the anchor-membership test.

## Implemented phase-1b2 scope

The phase-specific oracle identity is
`lean-rgc-uprime-rpc-exact-49-contract-oracle-v0.1`, with scope
`standalone_exact_49_raw_contract_predicates_only`. Its public API accepts one
ledger path and loads one same-handle immutable chain snapshot. It shares only
the strict JSON/hash/chain-snapshot substrate with phase 1a. It does not import
or call the phase-1b1 semantic verifier, the production contract evaluator,
the production disposition or response summarizer, or the cache-probe helper.

From the retained canonical record bytes, the oracle independently:

- revalidates the frozen exact 49-record schema, order, dynamic request state
  machine, closure relations, and raw B4 local probe;
- reconstructs the fixed eleven-contract vector in the preregistered order
  `R0, B0, B1, B2, B3, B4, D0, D1, D2, R1, E0`;
- uses strict canonical-JSON equality so integer zero/one cannot be replaced by
  booleans at budget, predecessor, replay-state, or replay-delta boundaries;
- requires all ten B2 telemetry keys on both the budget and audit-mirror
  surfaces, including an explicit null counter for the zero option;
- derives the D2 operational selector from the second ordered side-init goal,
  without reconstructing the unrecorded production-only selector variable;
- cross-binds every R1 replay to the primary raw request, primary response,
  exact predecessor/after kernels, action, target, delta, and presence-aware
  replay-certificate fields;
- accepts ASCII digit strings only for option parsing, returns affected
  contracts false for malformed scientific telemetry, and returns no vector
  for chain or exact-state-machine failure; and
- fixes every registry cardinality before aggregation, so an empty or dynamic
  caller collection cannot satisfy a contract vacuously.

The result has exactly the 23 public fields frozen by the amendment. It reports
the actual snapshot input digest, byte count, final chain head, ordered boolean
vector, and ordered failure IDs. Its origin remains
`unknown_may_be_synthetic`; all reservation-token, source-blob, remote-claim,
bundle, report, attempt-manifest, privacy, and archive checks are
`not_performed`; `authority_scope=none`; and all execution, canonical-run, and
later-stage license booleans are false.

## Synthetic reachability and production-reference boundary

The rich fixture is a fully rehashed, internally consistent synthetic ledger.
It demonstrates that all eleven independent raw predicates are reachable. It
does not demonstrate that Lean emitted the bytes.

The fixture also exercises the legacy production evaluator as a compatibility
reachability check. That check now exposes its two non-ledger inputs explicitly:
the recorded B4 local probe and the unrecorded legacy selector name. The latter
is injected only at that compatibility boundary. Replay expectations are
derived from primary requests and responses, not from replay requests. Because
the fixture builder and production evaluator share the production delta helper,
that compatibility test is labeled reachability-only and is not cited as
independent delta evidence. The new oracle uses neither injected input.

## Frozen acceptance matrix and adversarial review

`tests/uprime_rpc_contract_oracle_cases.py` is noncollectable by filename and
is imported by the frozen registered collector
`tests/test_uprime_rpc_ledger.py`. The source and support paths are members of
`ANCHOR_PATHS`; the existing four-file M2b command therefore collects every
case exactly once without adding a fifth registered test file.

The final support matrix contains 121 passing cases. It includes:

- an all-eleven-true synthetic vector with an exact negative-authority public
  surface, plus sentinels proving independence from phase 1b1 and production;
- a fully rehashed isolated-false case for each of the eleven contract IDs;
- missing-versus-explicit-null, mirror, zero-option, cap, heartbeat-type,
  episode-accounting, and burn-boundary cases;
- cumulative/forged delta, assigned-open goal, predecessor transplant, target,
  replay action/state/delta/certificate, and chain-local name-reuse attacks;
- response/B4 computed-false cases and chain, count, order, index, association,
  dynamic-request, raw-key-order, bool/int, and digit-conversion no-vector or
  false cases at their frozen boundary;
- deterministic canonical output, actual input digest/size/head binding,
  deterministic failure order, and rejection of forged caller side channels;
  and
- same-size mutation, path replacement, exactly-one snapshot, complete import
  allowlisting, direct-I/O alias tainting, and bounded loader-capability tests.

Independent adversarial passes found and forced repairs for:

- a hidden injection of the unrecorded production selector in a helper that
  had claimed record-only reconstruction;
- replay expectations derived from replay inputs rather than primary inputs;
- an initially incomplete six-of-eleven isolated-false matrix;
- non-discriminating strict-equality tests and Python's `0 == False` /
  `1 == True` aliases across four evidence surfaces;
- relative and dynamic imports, imported and transitive `open` aliases,
  reflective path reads, and direct-I/O bypasses;
- snapshot-loader aliases, list/tuple/lambda indirection, loop/helper/nested
  execution, and guarded alias re-entry that could open a path more than once;
  and
- weak input-binding, public-surface, zero-option, integer-option, and B4
  cross-contract tests.

The final source, fixture, test-matrix, and governance re-reviews all approved
the bounded phase-1b2 scope with no remaining P0/P1 commit blocker.

## Verification evidence

Local verification used Windows `Microsoft Windows NT 10.0.26200.0` and
CPython `3.13.7`:

1. bytecode compilation of the new oracle and both support modules succeeded;
2. the explicit phase-1b2 support module completed with 121 passed;
3. the exact frozen four-file M2b command completed with 360 passed, zero
   failures/errors/skips/xfails, in 192.40 seconds;
4. the default Windows suite completed with 667 passed, 3 skipped, and 163
   deselected in 379.81 seconds; and
5. staged diff and whitespace checks were clean for the six-path
   implementation scope.

CI run `29118116900` used Ubuntu 24.04 and CPython 3.11.15. It completed with
666 passed, 4 skipped, and 163 deselected in 80.27 seconds. Its runtime-boundary
and dead-candidate-ledger checks also passed. The Linux-only difference is one
additional environment-dependent skip; the CI conclusion is success.

## Decision and next gate

Phase 1b2 passes as an implementation and adversarial-test milestone for
independent exact-49 raw-contract recomputation. This is not a result from a
canonical diagnostic. An all-true synthetic vector is not `CLEAR`, not a final
verifier pass, and not evidence of runtime origin.

Phase 2 remains responsible for bundle/receipt/token and runtime-origin
authentication, RPC writer/queue/quiescence integration, anomalous or aborted
ledger handling, report and attempt-manifest binding, privacy/archive controls,
production-versus-independent disagreement recording, and the final
independently invocable verifier.

The rerun registry remains strict default-deny with no positive license.
Canonical U'1 execution, U'0.5 probes, U'2--U'5, remote GPU construction, and
publication claims remain barred.
