# U'1 evidence milestone 2b phase 1a execution record (2026-07-11)

Status: STANDALONE CHAIN-STRUCTURE CORE IMPLEMENTED AND VERIFIED; NOT A PARSED
LEDGER VERIFIER, NOT CANONICAL EVIDENCE, AND NOT A RERUN OR GPU LICENSE.

## Temporal anchor

The implementation and its registered tests were committed and pushed as
`77dfbe1372ec0de26e7d2cab0c2596ab8b3f19c1` on
`origin/codex/uprime-odlrq-plan` before this result record was written. GitHub
Actions CI run `29105834665`, job `pytest`, completed successfully for that exact
head SHA.

That implementation commit changes exactly the ledger source, its tests, the
litmus anchor list, the rerun-license anchor-membership test, and the test-tier
manifest. No claim receipt, reservation, registered run artifact, remote
attempt, or positive registry entry was created.

The frozen governing preregistration is
`docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_parsed_ledger_preregistration.md`,
committed earlier as `70041ed276433be9fe436b3e79d8861f0f957b5c`. The phase 1a
implementation is deliberately narrower than the final verifier specified
there. This record reports engineering evidence only and does not amend any
scientific endpoint or activation rule.

## Implemented scope

The new `lean_rgc/evals/uprime_rpc_ledger.py` supplies a strict, standalone
hash-chain substrate:

- integer-only canonical JSON parsing and serialization with duplicate-key,
  non-finite number, surrogate, BOM, unknown representation, size, depth, and
  member-count rejection;
- the preregistered domain-separated genesis and record-core hash formulas;
- an append-only writer using exclusive creation, one owner for the file
  descriptor, one raw write per record, pre/post offset and stat checks, flush
  and `fsync`, and poison-on-I/O-drift behavior;
- bounded two-pass binary inspection from one open handle, with same-handle
  mutation checks and post-close path rebinding checks;
- explicit partial classifications for unclosed, torn, corrupt, and structurally
  closed chains; and
- a standalone structural attestation that keeps every bundle, remote receipt,
  contract, manifest, privacy, archive, finalization, canonical-run, later-stage,
  and GPU authority field false or absent by construction.

The exposed phase identifiers and API names are intentionally chain-scoped.
They do not use the final parsed-ledger verifier identifier frozen by the
preregistration. Their exact identities are
`lean-rgc-uprime-rpc-chain-structure-verifier-v0.1` and
`lean-rgc-uprime-rpc-chain-prefix-inspector-v0.1`. Structural attestations fix
`attestation_scope=standalone_chain_structure_only`,
`origin_status=unknown_may_be_synthetic`, `authority_scope=none`, and all three
license/authority booleans to false. Prefix inspection is never finalized,
including when its structural status is `closed_chain`.

## Verification evidence

The implementation was exercised locally on Windows
`Microsoft Windows NT 10.0.26200.0` with CPython `3.13.7`:

1. `python -m py_compile lean_rgc/evals/uprime_rpc_ledger.py
   tests/test_uprime_rpc_ledger.py` succeeded;
2. the registered four-file profile
   (`test_uprime_rpc_ledger.py`, `test_uprime_rpc_litmus.py`,
   `test_uprime_rerun_license.py`, and `test_v74_test_tier_manifest.py`)
   completed with 130 passed, zero failed, zero skipped, and zero xfailed;
3. the default Windows CPU suite completed with 437 passed, 3 skipped, and 163
   deselected in 185.62 seconds; and
4. the pushed implementation commit passed CI run `29105834665`.

The standalone ledger suite contained 63 passing tests after the final repairs.
The CI `pytest` job ran on Ubuntu 24.04 with CPython 3.11.15 and completed with
436 passed, 4 skipped, and 163 deselected in 31.64 seconds; its runtime-boundary
and dead-candidate-ledger checks also passed.

Three independent adversarial reviews attacked governance naming and authority,
test coverage, and I/O/path bypasses. Their final disposition was approval with
no P0/P1 commit blocker. The review forced two final repairs before the recorded
full-suite run: factory `fstat` failure can no longer double-close the transferred
descriptor, and a path swapped while the scan handle closes is rejected by a
post-close binding check. Targeted regression tests cover both cases.

## Explicitly unimplemented

Phase 1a does **not** implement or verify:

- the exact nominal 49-record body schemas, order, or state machine;
- reservation, attempt, or claim-once receipt authenticity;
- the exact request/response and local-probe semantic relations;
- bundle membership, quiescence, worker/process provenance, contract verdicts,
  report construction, privacy scanning, archival publication, or an
  independent verifier executable; or
- any positive rerun-license path.

Consequently, even a `closed_chain` result proves only that the supplied bytes
form the standalone structural chain accepted by this phase-specific parser.
It cannot be relabeled as a complete M2b ledger, candidate evidence, a
scientific result, or a canonical diagnostic.

## Decision and next gate

Phase 1a passes as a local engineering milestone. Phase 1b may now implement the
frozen 49-record semantic validator and its negative-test matrix without
starting Lean or consuming a canonical attempt. Phase 2 remains responsible for
bundle/receipt/RPC/quiescence integration and an independently invocable final
verifier.

The tracked rerun registry remains `default_allow=false` with no licenses.
Canonical U'1 execution, U'0.5 kill probes, U'2--U'5, remote GPU construction,
and any publication claim remain barred.
