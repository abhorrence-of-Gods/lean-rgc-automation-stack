# U'1 evidence milestone 2b phase 2a execution record (2026-07-11)

Status: READ-ONLY BUNDLE-RESERVATION V1.1 IDENTITY/TOKEN VERIFIER IMPLEMENTED
AND VERIFIED; NOT A CLAIM, WRITER, REMOTE AUTHENTICATOR, MANIFEST, REPORT,
CANONICAL-RUN, RERUN, LATER-STAGE, OR GPU LICENSE.

## Temporal and commit boundary

The governing forward-only amendment was committed and pushed as
`e9e031ef6b9632ac7eed18b2449a7ea9d3908324` before implementation began.
The final implementation/test head is
`7ff763194bed98533b16d066f01e297b3387a390` on
`origin/codex/uprime-odlrq-plan`.

Implementation commit `aca61337f0838ab6575ee06ed62065d6b518bda3`
added the verifier and matrix. Its first Linux CI run `29122513081` correctly
failed four path-mutation cases: those tests had hard-coded Windows separators,
so four replacements were no-ops on POSIX. Corrective commit
`7ff763194bed98533b16d066f01e297b3387a390` derived every mutation from the
separator actually present in the lexical path and asserted that every
candidate differs from the valid fixture. It did not weaken a verifier rule.
CI run `29122802051`, job `pytest` (`86461574638`), then completed successfully
for the final head.

The final delta from the preregistered head changes exactly five paths: the new
source, its noncollectable case-support module, the existing registered ledger
collector, the anchor set, and the anchor-membership test. No tracked or
registered reservation, persisted raw token, live claim, manifest, ledger,
report, registered-run artifact, or remote object was created; tests used only
ephemeral synthetic temporary fixtures.

## Implemented scope

`lean_rgc/evals/uprime_rpc_bundle_reservation.py` exposes exactly:

```text
StandaloneBundleReservationV11Attestation
StandaloneBundleReservationV11Error
inspect_standalone_bundle_reservation_v1_1
verify_standalone_bundle_reservation_v1_1
```

The two entry points:

- take one lexical path, with `verify_*` additionally requiring one exact
  lowercase-hex64 caller token;
- perform one read-only `os.open`, two bounded passes on the same descriptor,
  three same-handle metadata snapshots, one close, and one final no-follow path
  binding observation;
- require one compact canonical JSON object plus LF, with a 1 MiB inclusive
  file bound;
- validate all 13 public-receipt and 22 v1.1 reservation fields, the frozen
  license-ID formula, receipt digest, identity duplication, schemas, frozen
  expected frame-count and frame-manifest-digest fields, canonical sibling
  names, and lexical path suffix;
- distinguish structural inspection from ephemeral token verification and use
  `hmac.compare_digest` for the SHA-256 of the 64 token ASCII bytes;
- reject raw-token occurrence in verified reservation bytes or the lexical
  path and never return, persist, log, or interpolate a token; and
- raise one public error class with no partial result for every rejection.

The implementation imports only strict JSON/canonical-byte primitives from the
standalone ledger substrate. It has no writer, network, subprocess, Git, Lean,
production-litmus, phase-1 semantic, migration, fallback, or schema-detection
path. The legacy reservation v1.0 helpers remain untouched and behaviorally
default-denied before side effects.

## Output and authority interpretation

The immutable attestation has the exact 31 fields frozen by the amendment. It
binds the observed reservation bytes, byte count, digest, identity, anchor,
artifact basenames, receipt digest, and schema versions. Structural inspection
reports `reservation_token_verification=not_performed`; successful held-token
verification reports `verified_ascii_sha256`.

Both modes retain:

```text
origin_status = unknown_may_be_synthetic
remote_claim_authentication = not_performed
git_object_authentication = not_performed
claim_once_authentication = not_performed
manifest_binding = not_performed
ledger_binding = not_performed
report_binding = not_performed
privacy_scan = not_performed
archive_verification = not_performed
authority_scope = none
canonical_run_authority = false
licenses_execution = false
licenses_later_stage = false
```

An internally valid receipt projection is not evidence that a remote ref
exists or that `claim_once` occurred. Token equality is an in-process
capability check, not durable external authentication.

## Acceptance and adversarial review

`tests/uprime_rpc_bundle_reservation_cases.py` is imported exactly once by the
frozen collector `tests/test_uprime_rpc_ledger.py`. The final 267-case matrix
covers:

- independent golden bytes and digests, exact 31-field output, and negative
  authority;
- complete missing, wrong-container, bool-as-scalar, and extra-field matrices
  for the 13 receipt and 22 reservation fields;
- every identity/schema/manifest/artifact binding plus malformed same-type
  receipt fields after recomputing the receipt digest;
- correct, wrong, malformed, decoded-byte-confused, byte/path-exposed, and
  inspection-versus-verification token cases;
- canonical JSON/LF/UTF-8/numeric grammar, injected N-1/N/N+1 reader bounds,
  sparse max+1 rejection, process-ID signed-64 boundaries, and pathlike types;
- lexical suffix, basename, case, normalization, final-component identity,
  same-size mutation, metadata drift, disappearance, and replacement;
- exact successful I/O call counts and injected open, all fstat/seek/read
  stages, short observation, close, and final-stat failures;
- v1.0/raw-token/migration/fallback rejection, exact public signatures,
  forbidden-import and no-side-effect gates; and
- continued default denial of formal and legacy entry points.

Adversarial review forced repairs before the final head for:

- unimplementable absolute TOCTOU and secret-nonappearance wording in the
  amendment;
- ambiguous Windows lexical-path and symlink-prefix claims;
- a public `verify(path, None)` sentinel bug that had silently returned an
  inspection attestation;
- stale-digest tests that did not independently exercise receipt syntax;
- missing injected I/O failure/short-read and signed-64 boundary cases; and
- POSIX no-op path mutations in the first CI run.

Independent source, test-matrix, and cross-platform re-reviews approved the
final bounded scope with no remaining P0/P1 blocker.

## Verification evidence

Local verification used Windows `Microsoft Windows NT 10.0.26200.0` and
CPython `3.13.7`:

1. bytecode compilation of the source and support module succeeded;
2. the explicit phase-2a support matrix completed with 267 passed in 8.88
   seconds;
3. the exact frozen four-file M2b command completed with 627 passed, zero
   failures/errors/skips/xfails, in 250.58 seconds;
4. the default suite completed with 934 passed, 3 skipped, and 163 deselected
   in 496.40 seconds; and
5. staged diff and whitespace checks were clean.

Final CI run `29122802051` used Ubuntu 24.04 and CPython 3.11.15. It completed
with 933 passed, 4 skipped, and 163 deselected in 77.98 seconds. The
runtime-boundary and dead-candidate-ledger checks also passed. The Linux-only
difference is one additional environment-dependent skip; the final conclusion
is success.

## Decision and next gate

Phase 2a passes as a read-only engineering milestone. It licenses only the next
synthetic design/implementation step: Phase 2b attempt-manifest schema, local
hash chain, terminal grammar, fake-remote compare-and-swap publication, and
recovery simulation.

It does not license the reservation writer, worker, RPC integration, final
parsed-ledger verifier, report/bundle binding, real claim, network access,
registered-run mutation, M2c privacy/archive, canonical diagnostic, U'0.5,
U'2--U'5, publication, or remote GPU construction.
