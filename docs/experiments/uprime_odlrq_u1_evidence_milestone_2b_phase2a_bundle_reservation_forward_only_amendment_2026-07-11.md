# U'1 evidence milestone 2b phase 2a bundle-reservation forward-only amendment

Date: 2026-07-11

Status: PREREGISTERED READ-ONLY IDENTITY/CAPABILITY SLICE; NO CLAIM, WRITE,
PUBLICATION, WORKER, CANONICAL-RUN, RERUN, LATER-STAGE, OR GPU AUTHORITY.

## 1. Purpose and governing boundary

The parent M2b preregistration remains authoritative. Phase 1a implemented the
standalone chain substrate, phase 1b1 implemented exact-49 sequence semantics,
and phase 1b2 implemented independent recomputation of the eleven raw contract
predicates. Phase 2 still lacks public-receipt and reservation-file binding,
attempt visibility/recovery, durable RPC/ledger integration, report and bundle
binding, and the final verifier.

This amendment freezes the first Phase-2 implementation slice before code is
written. Phase 2a is a read-only, standalone verifier for the Section-4 public
claim-receipt projection, bundle-reservation v1.1 file, canonical bundle path,
and caller-held reservation token. It operates only on synthetic files under
test temporary directories. It authenticates no remote claim or Git object and
creates no reservation.

The final Phase-2 goal is not reduced. The remaining subphases are frozen in
Section 11 so this bounded slice cannot be relabeled as completion of M2b.

## 2. Forward-only replacement of the legacy helper family

The current production module contains historical helpers for
`lean-rgc-uprime-rpc-reservation-v1.0`. They store the raw token in the JSON
sidecar and include it in a temporary filename. They are incompatible with the
parent Section 4, which requires a v1.1 reservation containing only the digest
of the 64 ASCII token bytes.

Therefore:

- the v1.0 helpers remain unchanged and behind the existing behavioral
  default-deny gate;
- no phase-2a source may import or call `_reserve_output`,
  `_verify_reservation`, `_publish_reserved_json`, `main`, `run_diagnostic`,
  or any other production litmus helper;
- v1.0-to-v1.1 migration, fallback, schema autodetection, and compatibility
  acceptance are forbidden;
- a v1.0 object, its `LIVE_EXECUTION_RESERVED` status, a raw `token` field, or
  any unknown field is an exact-schema error; and
- existing historical sidecars are never rewritten, promoted, or used as a
  source of v1.1 bytes.

The new implementation paths are:

```text
lean_rgc/evals/uprime_rpc_bundle_reservation.py
tests/uprime_rpc_bundle_reservation_cases.py
```

The support filename remains outside pytest's default pattern. Its marked test
objects are imported exactly once by `tests/test_uprime_rpc_ledger.py`, so the
frozen four-file M2b command is unchanged. Both new paths and this amendment
must be in `ANCHOR_PATHS` before an implementation-result commit.

## 3. Public APIs and single-snapshot rule

The only public verification entry points are:

```python
inspect_standalone_bundle_reservation_v1_1(path)
verify_standalone_bundle_reservation_v1_1(path, token_hex)
```

The source defines one immutable result class,
`StandaloneBundleReservationV11Attestation`, and one public rejection class,
`StandaloneBundleReservationV11Error(ValueError)`. Both APIs accept
`str | os.PathLike[str]`; `verify_*` requires `token_hex` to have exact type
`str`. Every path, I/O, syntax, schema, binding, or token rejection raises the
single public error class and returns no partial object. Error messages never
interpolate the caller token. `__all__` contains exactly those two classes and
the two entry points.

`inspect_*` performs structural and internal-identity verification and reports
`reservation_token_verification=not_performed`. `verify_*` performs the same
verification and additionally proves that the caller-held token hashes to the
stored digest. A wrong or malformed token yields no attestation.

Neither API accepts a caller-supplied receipt, expected commit, expected
license, report, manifest, context object, authority flag, or precomputed
digest. Receipt and identity values are derived only from the reservation
snapshot. This prevents a caller from making a rewritten bundle self-confirm
by supplying matching external context.

Each call uses this exact observation protocol:

1. take the caller's lexical path without `resolve`, `normcase`, or case-folding;
2. open it once with `os.open(O_RDONLY | O_BINARY)` where `O_BINARY` exists;
3. require a regular file and capture
   `S0=(st_dev, st_ino, st_ctime_ns, st_size, st_mtime_ns)`;
4. perform two bounded passes on the same descriptor, each from offset zero,
   retaining pass-one bytes and requiring equal byte count and SHA-256;
5. capture S1 after pass one and S2 after pass two and require S0=S1=S2;
6. close the descriptor exactly once; and
7. perform one `os.stat(path, follow_symlinks=False)` and require its
   `(st_dev, st_ino, st_size, st_mtime_ns)` binding to equal `bind(S0)`, where
   `bind(S)=(S.st_dev, S.st_ino, S.st_size, S.st_mtime_ns)`.

Any open/read/seek/stat/close failure, short or oversized observation,
same-handle drift, pass mismatch, disappearance, symlink/reparse mismatch, or
post-close path replacement observed at step 7 is rejected. Step 7 is the
attestation observation point; no claim is made about mutation after that
stat and before Python returns. The path is never reopened to validate a
field. The implementation may share only strict JSON/canonical-byte primitives
from the standalone ledger substrate; it must not import phase-1 semantics,
the contract oracle, the production litmus, subprocess, socket, HTTP, Git, or
Lean helpers.

## 4. Exact file and token encoding

The reservation file is exactly one compact canonical JSON object followed by
one LF. The LF is part of the reservation-file SHA-256. BOM, CRLF, leading or
trailing whitespace, missing LF, extra LF, multiple objects, duplicate keys,
noncanonical key order or spacing, floats, nonfinite values, surrogates,
booleans used as integers, and trailing bytes are rejected.

The maximum file size is 1,048,576 bytes including LF. The reader rejects an
oversize stat before allocating its payload and also enforces the limit while
reading. Its private bounded-reader size predicate is tested with an injected
small bound N at N-1, N, and N+1. The public API additionally rejects a sparse
1,048,577-byte file before payload allocation. No semantically valid 1 MiB
reservation fixture is required.

The caller-held token is exactly 64 lowercase ASCII hexadecimal characters and
therefore syntactically encodes 32 bytes. Phase 2a does not verify entropy,
random generation, or provenance. The stored uppercase digest is:

```text
uppercase_hex(SHA256(token_hex.encode("ascii")))
```

It is not the digest of decoded token bytes. `verify_*` rejects if the exact 64
token ASCII characters occur contiguously in the reservation bytes or in the
caller-supplied lexical path. `inspect_*`, which does not know a token, claims
only exact-schema absence of a raw `token` field. The module never writes,
logs, or interpolates the token into an attestation, attestation `repr`,
stdout/stderr, a log record, or an exception message. Caller-owned `repr` and
traceback-local capture are outside this guarantee. Phase 2a does not generate,
persist, escrow, or recover a token.

## 5. Exact receipt and reservation validation

The embedded receipt has exactly the 13 fields frozen in parent Section 4 and
schema `lean-rgc-uprime-u1-claim-receipt-public-v1.0`. The reservation has
exactly the 22 fields frozen there and schema
`lean-rgc-uprime-rpc-bundle-reservation-v1.1`.

The verifier checks all primitive types and syntax with booleans excluded from
integer fields. It checks, without caller input:

- lowercase-hex40 candidate and license commits and Git object IDs;
- lowercase-hex64 license ID equal to
  `lower_hex(SHA256(b"lean-rgc-uprime-u1-attempt-v1\0" +
  candidate_commit.encode("ascii")))`;
- uppercase-hex64 registry, input-manifest, receipt, frame-manifest, and token
  digests;
- the fixed remote URL and branch ref, exact claim ref
  `refs/tags/uprime-u1-attempts/<license_id>`, and equality of remote claim OID
  to the license commit;
- real UTC timestamps in exact `YYYY-MM-DDTHH:MM:SS.ffffffZ` form and positive
  signed-64 process ID;
- exact equality of every duplicated candidate/license/license-ID/ref value
  between receipt and reservation;
- `anchor=lowercase(license_commit[0:12])`;
- receipt digest as uppercase SHA-256 of compact canonical receipt bytes
  without LF;
- fixed run directory, report/ledger/record/RPC schemas, expected frame count
  23, and frozen frame-manifest digest
  `03A58EA8661BAB7423D5B7CF86DF66F97134DCBAEC976744051310E437BC394E`; and
- exact canonical sibling basenames derived from the anchor.

The verifier does not claim that the receipt was fetched from the remote, that
the remote ref exists, that any Git OID resolves, that the registry or input
manifest bytes were inspected, or that `claim_once` occurred.

`inspect_*` requires the stored token digest to have valid uppercase-hex64
syntax but does not compare a caller capability. `verify_*` compares the
stored and computed token digests with `hmac.compare_digest`.

## 6. On-disk path binding

Let `raw_path=os.fspath(path)`, which must have exact type `str`. Without
`resolve`, normalization, or case-folding, split the delivered lexical string
on both `/` and `\` while preserving visible dot components. Any visible `.` or
`..` component is rejected. A caller-created path object that already discarded
such syntax is judged only on the representation it supplies.

Split while preserving empty components. The final three components must be
case-sensitively equal to:

```text
runs/uprime_u1_rpc_20260710/rpc_diagnostic_<anchor>.json.reservation
```

The basename is the final component, and exactly one `/` or `\` separator
occurs at each of the two suffix boundaries. No empty component is allowed from
the lexical `runs` component through the basename. Leading empty components in
an arbitrary drive/UNC-style prefix remain outside bundle identity.

The last component must equal `reservation_artifact_name`. The two sibling
basenames must be exactly:

```text
rpc_diagnostic_<anchor>.json
rpc_diagnostic_<anchor>.responses.jsonl
```

Artifact fields are ASCII basenames. Empty names, slash or backslash, absolute
paths, dot components, alternate case or Unicode normalization, drive or UNC
syntax, and anchor mismatch are rejected. Drive/UNC rejection applies to the
artifact-field strings, not to the arbitrary caller-owned temporary prefix.
That prefix before the exact `runs/uprime_u1_rpc_20260710` suffix is outside
the bundle identity and is allowed solely so synthetic tests never touch the
registered repository directory. Descriptor identity plus the final no-follow
stat rejects a final-component symlink or reparse-point path entry. No claim is
made about a symlink or junction in the arbitrary prefix.

Phase 2a does not check sibling existence or disk free space and performs no
exclusive create. Those belong to the later writer/preflight subphase after
attempt-manifest ordering is implemented.

## 7. Exact attestation surface and negative authority

Both APIs return the same frozen 31-field immutable attestation:

```text
verifier_schema_version
verifier_scope
origin_status
input_sha256
input_bytes
reservation_sha256
reservation_artifact_name
report_artifact_name
ledger_artifact_name
registered_run_dir
candidate_commit
license_commit
license_id
anchor
remote_claim_ref
claim_receipt_sha256
receipt_schema_version
reservation_schema_version
reservation_token_verification
remote_claim_authentication
git_object_authentication
claim_once_authentication
manifest_binding
ledger_binding
report_binding
privacy_scan
archive_verification
authority_scope
canonical_run_authority
licenses_execution
licenses_later_stage
```

Frozen values are:

```text
verifier_schema_version = lean-rgc-uprime-rpc-bundle-reservation-token-verifier-v0.1
verifier_scope = standalone_bundle_reservation_receipt_token_only
origin_status = unknown_may_be_synthetic
reservation_token_verification = not_performed | verified_ascii_sha256
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

`input_sha256` and `reservation_sha256` both bind the exact file bytes including
LF and are therefore equal in v0.1. No field named `verified`, `verdict`,
`CLEAR`, `BLOCKED`, `finalized`, `claim_valid`, or `verifier_passed` is exposed.
Token binding is an in-process capability check, not durable external evidence.

## 8. Token loss and recovery interpretation

The raw token is memory-only, so power loss may make later capability
reverification impossible. This is not repaired by persisting the secret.

Recovery uses structural `inspect_*` and records only actual existence,
digest, and byte facts. It must report token verification as `not_performed`.
Only a still-running caller that possesses the token may obtain
`verified_ascii_sha256` through `verify_*`. Neither status authenticates the
remote claim or licenses execution. If a later design requires long-term token
escrow, it needs a separate preregistration and cannot silently weaken the
no-secret-on-disk rule.

## 9. Finite phase-2a acceptance matrix

Before a phase-2a result commit, the frozen four-file M2b command must collect
the new cases through the anchored ledger collector and pass with zero
failures, errors, skips, or xfails. Required cases include:

1. frozen golden v1.1 bytes, file digest, receipt digest, ASCII-token digest,
   exact 31-field inspection/verification outputs, and negative authority;
2. complete missing, extra, wrong-type, and bool-as-int matrices for all 13
   receipt and 22 reservation fields;
3. every candidate/license/anchor/license-ID/ref/schema/manifest/artifact-name
   cross-binding changed individually in fully canonical synthetic bytes;
4. correct token, wrong token, uppercase/short/long/nonhex/non-ASCII token,
   decoded-bytes-digest confusion, token-equals-file-field and token-in-prefix
   rejection, and assurance that module-controlled bytes, results, attestation
   repr, logs, stdout/stderr, and errors never expose the raw token;
5. BOM, CRLF, missing/extra LF, whitespace/key order, duplicate key, multiple
   object, float/nonfinite/surrogate, trailing-byte, injected N-1/N/N+1 reader
   bound, and sparse public max+1 preallocation-rejection cases;
6. exact temporary-prefix path success; visible traversal/dot, suffix slash or
   backslash, artifact-field absolute/drive/UNC, normalization, case, basename,
   anchor, final-component symlink/reparse identity, and on-disk filename
   failures; the final-component link cases use injected descriptor/no-follow
   identities rather than privilege-dependent real Windows symlinks;
7. one-open enforcement, same-size retained-byte mutation, metadata drift,
   path disappearance, and path replacement;
8. v1.0 schema/status, raw-token field, legacy shape, migration, fallback, and
   schema-autodetection rejection;
9. caller attempts to supply receipt, expected commits, report, manifest,
   authority, or precomputed digest rejected by the public signatures;
10. import/AST and raising-sentinel checks proving no production/phase-1,
    network, subprocess, Git, Lean, registered-path, write, claim, publication,
    or secret-persistence path; and
11. existing formal `main`, `run_diagnostic`, and legacy reservation/publication
    helpers remain behaviorally default-denied before side effects.

The matrix also includes the inspect/verify differential: a structurally valid
reservation with a changed but syntactically valid stored token digest is
accepted by `inspect_*` with `not_performed` and rejected by `verify_*` for the
held token; a malformed stored digest is rejected by both APIs. Every rejection
raises `StandaloneBundleReservationV11Error` and returns no partial object.

All fixtures live under `tmp_path`. Tests may construct synthetic canonical
bytes but may not invoke Lean, a network, a remote claim, the repository's
registered run path, or GPU infrastructure.

## 10. Phase-2a stop rule

Passing Phase 2a proves only internal consistency of one supplied v1.1
reservation projection and, when requested, equality of one caller-held token
to its stored ASCII digest. It does not prove claim uniqueness, remote state,
attempt visibility, ledger/report existence, or origin.

Phase 2a does not license a reservation writer, worker startup, canonical
diagnostic, rerun, U'0.5, U'2--U'5, publication, remote GPU construction, or
contact with the GPU host.

## 11. Remaining Phase-2 decomposition

The remaining parent scope is preserved in this order:

1. **Phase 2b — attempt-manifest core:** exact local schema, hash chain,
   terminal grammar, fake-remote compare-and-swap publisher, and recovery
   simulation. No network or worker.
2. **Phase 2c — reservation writer and preflight:** all seven pre-existing
   sibling subsets, two-contender exclusive create, free-space/topology checks,
   fsync failure injection, and a capability proving `claim_started` was
   durably published before reservation creation.
3. **Phase 2d — durable RPC evidence integration:** append receipts carrying
   record index/hash, active-frame state/lock, fsync-before-stdin and
   fsync-before-queue, quarantine, abort-prefix closure, idempotent bounded
   quiescence, and fake-process failure matrix.
4. **Phase 2e — final inspector/verifier and report binding:** finalized and
   partial v1.0 identities, report v1.2 evidence-ledger object, independent X0
   and contract vector, anchored bundle binding, and fully rehashed rewrite
   rejection. The production-versus-independent disagreement schema must be
   frozen in an amendment before code.
5. **Phase 2f — synthetic coordinator and crash recovery:** fake claim,
   receipt propagation, all 14 durability boundaries, unique consumed attempt,
   report hard-link, final/recovery manifest, and no restart/resume.
6. **Activation dependencies:** real M2a `claim_once`, M2c privacy scanner and
   encrypted archive/retention, pinned Windows evidence, CI, and adversarial
   review. Only a later explicit activation commit may connect formal
   entrypoints or contact a remote.

Until every required parent gate is complete, the rerun registry remains
strict default-deny and all canonical/network/GPU work remains barred.
