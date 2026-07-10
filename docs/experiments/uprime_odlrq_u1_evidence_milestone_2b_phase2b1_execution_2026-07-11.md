# U'1 evidence milestone 2b phase 2b1 execution record (2026-07-11)

Status: READ-ONLY SYNTHETIC PRE-ARTIFACT ATTEMPT-MANIFEST PARSER/CHAIN
VERIFIER IMPLEMENTED AND VERIFIED; NOT A WRITER, CLAIM, REMOTE, CAS, RECOVERY
ORACLE, ARTIFACT OBSERVATION, INVENTORY AUDIT, WORKER, SCIENTIFIC VERDICT,
CANONICAL-RUN, RERUN, NETWORK, LATER-STAGE, OR GPU LICENSE.

## Temporal and commit boundary

The reduced Phase-2b1 amendment was committed and pushed as
`e1811bf1dab459e834c2c025ffe29806c337d107` before implementation. Independent
review had rejected the earlier combined Phase-2b design because local final
files conflicted with CAS retry/pre-start recovery, caller-supplied recovery
cause was forgeable, epoch release was unspecified, and most public records
were not field-frozen. The committed amendment therefore limited Phase 2b1 to
read-only schema and local-chain verification and preserved CAS/recovery as a
separate Phase-2b2 preregistration obligation.

The first uncommitted Windows prototype then exposed an impossible cross-API
metadata equality: path `stat` and descriptor `fstat` reported different
`st_ctime_ns` values for the same file. Before a source commit, the portability
correction was independently reviewed, committed, pushed as
`02e22114e8f6bdedde0e65caf783591c47760e42`, and passed CI run `29125770050`.
It keeps exact path-family and descriptor-family snapshots while restricting
only their cross-family projection to `(dev, ino, size, mtime_ns)`.

The final implementation/test head is
`ede1888fa56546423e311dadb68e86a18fcd5216` on
`origin/codex/uprime-odlrq-plan`. Implementation CI run `29127350954`, job
`pytest` (`86475653104`), completed successfully. No Phase-2b1 source or result
was committed before the amendment and portability-correction gates passed.

The implementation delta is exactly the new read-only source, its
non-default-discoverable support module, one import in the frozen collector,
two anchor constants/members, and the anchor-membership test. This execution
record is the only later result path. The default-deny rerun registry stayed at
its committed 96 bytes and no exposure marker or file under `runs/` was created
or modified.

## Implemented scope

`lean_rgc/evals/uprime_rpc_attempt_manifest.py` exposes exactly:

```text
AttemptManifestV10Error
PublicClaimReceiptV10
AttemptManifestEventV10
AttemptManifestEventFileV10
AttemptManifestChainInspectionV10
AttemptManifestChainAttestationV10
encode_attempt_manifest_event_v1_0
parse_attempt_manifest_event_file_v1_0
inspect_local_attempt_manifest_chain_v1_0
verify_local_attempt_manifest_terminal_chain_v1_0
```

The implementation provides:

- exact frozen/slotted 13-field receipt, 29-field event, 4-field event-file,
  16-field inspection, and 33-field terminal-attestation records;
- compact strict canonical JSON projection with tuple-to-array conversion,
  exactly one LF, a 1,048,576-byte inclusive event bound, LF-free receipt
  digest, and LF-included event digest;
- the frozen C/L/license/ref formula, exact repository path and four-digit
  1..9999 index, contiguous prior-digest chain, nondecreasing real six-digit-Z
  event time, and recovery-sticky terminal grammar;
- the all-absent pre-artifact wire profile and exact 41-code parent registry,
  with `SCANNER_ERROR`, `PRIVACY_DENIED`, `ARCHIVE_ERROR`, and
  `PUBLICATION_ERROR` excluded and three recovery-only codes structurally
  confined without claiming causal provenance;
- a caller-selected, read-only local directory snapshot with streaming
  `max_count+1` enumeration, 64 MiB aggregate bound, two directory scans,
  exact `D0=D1`, exact `S0=S1`, second-scan names/path tuples equal to their
  first-scan values, exact `F0=F1=F2`, and portable
  `B(S0)=B(F0)`/`B(S1)=B(F2)` for `B=(dev, ino, size, mtime_ns)`; each opened
  event file receives two descriptor passes, EOF probes, and exactly one close,
  and the step-8 `D1` stat is the observation point with no later-mutation
  claim; and
- terminal structural attestation with a fully negative authority suffix.

The source imports only the two strict canonical JSON primitives from the
standalone ledger substrate plus the frozen standard-library allowlist. It has
no write, subprocess, Git, network, Lean, worker, registered-run,
reservation-writer, scanner/archive, production-litmus, or formal-entrypoint
path.

## Output and authority interpretation

Inspection is limited to one caller-selected license directory. A missing or
empty selected directory returns `missing`; invalid bytes, namespace, chain,
or I/O raise the one public error and return no partial result. The inspector
does not enumerate a remote inventory and cannot detect an omitted claim or an
orphan directory under another license.

The terminal attestation retains:

```text
origin_status = unknown_may_be_synthetic
verifier_scope = local_preartifact_chain_structure_only
preartifact_profile = true
artifact_observation = not_performed
remote_claim_authentication = not_performed
git_object_authentication = not_performed
real_remote_publication = not_performed
claim_once_authentication = not_performed
reservation_token_verification = not_performed
artifact_binding = not_performed
verifier_binding = not_performed
scanner_binding = not_performed
privacy_scan = not_performed
archive_verification = not_performed
authority_scope = none
canonical_run_authority = false
licenses_execution = false
licenses_later_stage = false
```

A fully self-consistent whole-chain rewrite remains structurally acceptable
and keeps every origin/authentication field negative. A parsed `POWER_LOSS`
code is syntax, not evidence that power loss occurred. An all-false artifact
profile is an encoded value, not a filesystem observation.

## Acceptance and adversarial review

`tests/uprime_rpc_attempt_manifest_cases.py` is imported exactly once through
`tests/test_uprime_rpc_ledger.py`. The final 370-case matrix covers:

- independently constructed receipt/event fixtures using the shared strict
  canonical primitive, literal expected sizes/SHA-256 vectors, LF-confusion
  kills, exact public fields, annotations, frozen/slots behavior, and ordered
  list `__all__`;
- complete missing/wrong-type/bool matrices for all 13 receipt and 29 event
  fields, exact extra-key rejection, same-type semantic failures, and encode
  revalidation after deliberate frozen-object bypass;
- fully rebound receipt mutations that recompute dependent license/ref/OID,
  repeated event copies, digest, and path, preventing stale-copy self-blessing;
- all grammar edges including equal timestamps, invalid starts, recovery
  stickiness, multiple nonterminal recovery steps, terminal-only failure-code
  projection, gaps, terminal tails, and index exhaustion classification;
- exact 41-code membership, order, forbidden/recovery-only contexts, all seven
  nonempty artifact-existence subsets, and every null/status profile field;
- canonical JSON/UTF-8/LF/numeric failures, N-1/N/N+1 byte and count bounds,
  sparse public max+1, streaming max+1 stop/close/no-stat/no-open, and aggregate
  rejection;
- absolute/case/slash/backslash/empty/dot/dot-dot/extra/Unicode/index/license
  path mutations, sorting independent of directory enumeration order, and
  selected-directory isolation;
- every directory/entry stat, scan, open, seek, fstat, read, EOF probe, close,
  and post-close stage; path replacement/disappearance, second-scan mutation,
  mode/ctime drift, nonregular/symlink/reparse sentinels, and all four portable
  binding components on both sides; and
- exact import/AST/read-only restrictions, production raising sentinels,
  collection uniqueness, no-file-creation behavior, and the literal/SHA/Git
  blob/HEAD binding of the unchanged default-deny rerun registry.

Adversarial review forced the Phase-2b split, the Windows stat-binding
correction, streaming rather than unbounded directory materialization, exact
public type/return surfaces, self-consistent rewrite disclosure, terminal-code
non-union tests, dependent mutation repair, exhaustive I/O calls, and explicit
selected-directory noncoverage. Three independent final re-reviews approved
the source and matrix with no remaining implementation-determining blocker.

## Verification evidence

Local verification used Windows 11 Home 10.0.26200 build 26200 and CPython
3.13.7 at exact head `ede1888fa56546423e311dadb68e86a18fcd5216`:

1. bytecode compilation and staged whitespace checks succeeded;
2. the explicit support matrix completed with 370 passed in 4.48 seconds;
3. the frozen collector selected exactly 370 unique Phase-2b1 nodes and
   completed with 370 passed, 560 deselected in 4.02 seconds;
4. the exact frozen four-file M2b command completed with 997 passed, zero
   failures/errors/skips/xfails, in 192.26 seconds; and
5. the default repository suite completed with 1304 passed, 3 skipped, and 163
   deselected in 379.89 seconds.

Final CI run `29127350954` used Ubuntu 24.04 image release
`20260705.232` and CPython 3.11.15. It completed with 1303 passed, 4 skipped,
and 163 deselected in 75.62 seconds. Runtime-boundary and
dead-candidate-ledger checks also passed. The one-skip platform difference is
consistent with prior repository runs; the CI conclusion is success.

The default-deny registry bytes are exactly 96 bytes, SHA-256
`ADBE0AB6FBE3F455E03120F2074543F15C1D75D1F7B52E1BD628A91ADB33B31B`,
and Git blob `13ffca6de484effc66f0e628d2e46823277271c6`; working-tree and HEAD blobs
matched during the matrix.

## Decision and next gate

Commit and push of this reviewed execution record, with the cited green
Windows and Ubuntu gates, complete Phase 2b1 as a read-only local engineering
milestone and license only Phase-2b2 preregistration.

It does not license Phase-2b2 implementation before a separate amendment is
reviewed, committed, pushed, and green. It does not license a manifest writer,
claim, fake or real CAS, recovery oracle, causal failure marker, artifact
observation, inventory-completeness claim, reservation creation, worker/RPC
execution, real remote/network use, canonical diagnostic, Phase 2c, U'0.5,
U'2--U'5, publication, or remote GPU construction. Contact with the GPU host
remains barred.
