# U'1 evidence milestone 2b phase 2b2a execution result

Date: 2026-07-11

Status: EXECUTION COMPLETE; THIS RESULT RECORD BECOMES GATE-BEARING ONLY AFTER
ITS OWN COMMIT, PUSH, AND GREEN CI. NEGATIVE AUTHORITY ONLY. NO ARTIFACT
OBSERVATION, CAS, WRITE, RECOVERY, WITNESS, CLAIM, REMOTE, WORKER, LEAN,
NETWORK, CANONICAL-RUN, RERUN, LATER-STAGE, OR GPU AUTHORITY.

## Registered boundary and commits

Phase 2b2a was frozen by
`uprime_odlrq_u1_evidence_milestone_2b_phase2b2a_seeded_local_inventory_amendment_2026-07-11.md`
at commit `41f9b1510cd872bf434dca88dbf42c7b397dbf7a`. Its Ubuntu preregistration
gate passed in CI run `29129809652` before implementation began.

The reviewed implementation was committed as
`c7df014a33539779dbdd706dc2483c079b6e64f2`. The exact committed Git blobs are:

| Role | Path | Git blob |
|---|---|---|
| frozen amendment | `docs/experiments/uprime_odlrq_u1_evidence_milestone_2b_phase2b2a_seeded_local_inventory_amendment_2026-07-11.md` | `15000677ca18e83dc9993c658d48b9f789490c6c` |
| source | `lean_rgc/evals/uprime_rpc_seed_inventory.py` | `baf849e562a32b7f4025f2e5b78f8c02848d9329` |
| noncollectable support | `tests/uprime_rpc_seed_inventory_cases.py` | `700eadcb6449d5927a847bed259d3a98b06cfd29` |
| external anchor/collector oracle | `tests/test_uprime_rerun_license.py` | `b637a2e0aa15f1accfe8df6f1727eb0a6c21a400` |
| collector | `tests/test_uprime_rpc_ledger.py` | `9b9525fc3eb8bd7c912f137ed00d8b9487066d8a` |
| anchor registry | `lean_rgc/evals/uprime_rpc_litmus.py` | `638dfb527f58b52f76d7bfe0efa263e529998dda` |

The default-deny rerun registry remained the exact 96-byte blob
`13ffca6de484effc66f0e628d2e46823277271c6`. The implementation created no
registered run, exposure marker, persistent or repository-tree local attempt
artifact, or result under `runs/`. Its only local attempt chains were
disposable pytest fixtures under temporary directories.

## Implemented surface

The implementation adds exactly two positional-only public functions, three
frozen/slotted records, and one public exception:

```text
parse_synthetic_claim_seed_v1_0(raw, /)
audit_synthetic_seed_local_inventory_v1_0(root, seed_raw, /)
```

The parser accepts only strict canonical caller-supplied seed bytes, rebuilds
each exact 13-field Phase-2b1 public receipt, and binds both the complete seed
file hash and its length-prefixed domain-separated identity hash. Those hashes
identify only bytes supplied in the call; they are not temporal commitments or
remote inventory authentication.

The audit evaluates `os.fspath(root)` once, retains that exact lexical text,
and compares the entire bounded local attempt namespace with the reparsed seed.
Only exact lowercase-hex64 child candidates are joined and no-follow statted.
Every safe bounded strict-UTF-8 noncandidate name is blocking unexpected
evidence and is never joined or statted. Unsafe names reject before any child
join/stat, while exact-hex nonclaim candidates become unexpected evidence only
after their no-follow stat. The present-base path uses
`D0 -> scan 1 -> sequential per-claim Phase-2b1 reduction -> scan 2 -> D1`;
the absent-base path uses two no-follow absence observations.

Every Phase-2b1 error and every aggregate resource overshoot aborts the whole
audit without a partial result. The returned records expose the exact
seed/local set relation, receipt relation, endpoint state, derived ID tuples,
nonvacuous aggregate booleans, and `empty_seed|matched_terminal|mismatched`
precedence. All authority and license fields are negative.

## Frozen resource accounting

Production bounds are unchanged from the amendment:

```text
seed receipts                         <= 16
valid local claim directories         <= 16
base entries                          <= 32
seed/local ID union                   <= 32
accepted event bytes                  <= 67,108,864
returned payload read-work upper bound = 268,435,457
scan-1 logical file admissions        <= 159,984
```

The read-work value is `2C + (2C + 1)` for `C=67,108,864`: a successful
accepted prefix plus the first terminal overshoot/failure call. Fail-fast
translation prevents that terminal cost from repeating. The admission value is
`16 * 9,999` and deliberately excludes scan-2 iterator occurrences and
low-level stat/read calls.

## Adversarial review and oracle repairs

The preregistration was rejected until it fixed the two-pass read-work proof,
complete per-claim truth table, exact `D`/`E` metadata, public error translation,
one-shot `root_text`, and a Windows-safe rule that never joins an arbitrary
unexpected name. Three independent rereads then approved the frozen amendment.

The first implementation matrix passed 190 nodes but was rejected as an oracle,
even though the source itself had no identified semantic violation. Required
repairs added both proper-subset directions, true multi-event sums, exact record
annotations, production/no-exposure sentinels, candidate stat ordering,
complete missing/end-point mappings, lexical-root preservation, and every
`D`/`E` component and exact-integer probe.

A second review rejected vacuous max+1 and fail-fast tests plus a bypassable
read-only AST check. The final matrix therefore uses exact-hex candidates with
zero join/stat sentinels at max+1, forbids inspection before local/union bound
rejection, preserves a real non-null `attempt_finished` endpoint, crosses
terminal/receipt aggregate booleans, freezes the five allowed OS seams, and
checks the collector import from an independently collected test. Three final
review lenses approved the exact source/support blobs with no remaining
implementation-determining blocker.

## Local Windows verification

Local verification used Microsoft Windows 11 Home `10.0.26200` build `26200`
and CPython `3.13.7` at exact implementation commit
`c7df014a33539779dbdd706dc2483c079b6e64f2`:

1. bytecode compilation and staged whitespace checks succeeded;
2. the explicit Phase-2b2a support matrix completed with **222 passed** in
   3.70 seconds;
3. the frozen collector selected the same 222 nodes exactly once and completed
   with **222 passed, 930 deselected** in 4.35 seconds;
4. the anchor/license profile completed with **21 passed** in 1.82 seconds;
5. the exact frozen four-file M2b command completed with **1220 passed**, zero
   failures/errors/skips/xfails, in 676.16 seconds; and
6. the default repository suite completed with **1527 passed, 3 skipped, 163
   deselected** in 440.79 seconds.

The exact frozen four-file command was:

```text
python -m pytest -q tests/test_uprime_rpc_ledger.py tests/test_uprime_rpc_litmus.py tests/test_uprime_rerun_license.py tests/test_v74_test_tier_manifest.py
```

All Phase-2b2a filesystem fixtures were small and local to pytest temporary
directories. The Phase-2b2a source, support, and frozen profile invoked no SSH,
GPU, Lean worker, registered experiment, or canonical diagnostic. The broader
default repository suite could execute pre-existing Lean worker tests when the
local optional toolchain was available; those tests were not a Phase-2b2a
experiment and grant it no worker or Lean authority.

## Ubuntu CI verification

CI run `29132252576`, job `86489666017`, executed the exact implementation
commit. It used GitHub Actions runner `2.335.1`, Ubuntu 24.04 image
`20260705.232.1`, and CPython `3.11.15`.

- runtime boundary: `12 modules, 230 files`;
- dead candidate ledger: `8 modules`;
- default suite: **1526 passed, 4 skipped, 163 deselected in 80.83 seconds**;
- job conclusion: **success** in 1 minute 34 seconds.

CI reported four skips versus three in the local Windows suite. This record
makes no causal inference from that aggregate environment-dependent skip
accounting. The sole GitHub Actions job annotation was the hosted-actions Node
20 deprecation; the raw setup log also contained Node `punycode` deprecation
warnings. Neither changed the Python result.

## Exact conclusion and remaining limits

Phase 2b2a closes the Phase-2b1 selective-directory hole for one bounded local
root: a caller cannot request only one favorable license directory, and a local
orphan or safe unexpected entry blocks `matched_terminal`.

It does **not** prove that the caller-supplied seed is complete, detect a claim
omitted from both seed and local root, authenticate a real remote claim, or
provide a simultaneous atomic snapshot of all chains. Prefix links remain
outside scope. `matched_terminal` means only sequential structural agreement
between the exact supplied seed and the complete bounded local namespace.

Only commit and push of this result record plus its anchor wiring, followed by
green CI for that result commit, completes Phase 2b2a and licenses Phase 2b2b
preregistration for the tri-state `present|absent|indeterminate` local artifact
observer. Until all three conditions hold, even Phase 2b2b preregistration
remains barred. Phase 2b2b implementation, fake CAS, staging, marker/recovery,
witness issuance, real claim/publication, network/SSH, Lean, worker execution,
GPU construction, Phase 2c, canonical diagnostic, M2c, U'0.5, and U'2--U'5
remain barred in either case.
