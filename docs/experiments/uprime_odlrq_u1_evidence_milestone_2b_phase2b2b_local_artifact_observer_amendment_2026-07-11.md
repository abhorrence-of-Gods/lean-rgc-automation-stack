# U'1 evidence milestone 2b phase 2b2b local artifact observer amendment

Date: 2026-07-11

Status: PREREGISTERED READ-ONLY SYNTHETIC LOCAL ARTIFACT-SET OBSERVER; NO
FORMAT VALIDATION, ATOMIC BUNDLE SNAPSHOT, CAS, WRITE, STAGING, MARKER,
RECOVERY, WITNESS, CLAIM, REMOTE, WORKER, LEAN, NETWORK, CANONICAL-RUN, RERUN,
LATER-STAGE, OR GPU AUTHORITY.

## 1. Purpose and exact boundary

Phase 2b2a completed a bounded comparison between one caller-supplied receipt
seed and the complete local attempt-manifest namespace. It intentionally did
not observe the reservation, parsed ledger, or report paths named by an
attempt. Its result commit `6c238b1c8b80cb989127d92247c2f1e969282245`
was committed, pushed, and passed CI run `29132623882`, satisfying the
Phase-2b2a stop rule.

Phase 2b2b adds only a generic local raw-byte/path observation substrate for
the three fixed artifact paths derived from one exact public claim receipt. It
answers, separately and sequentially for each path:

```text
present | absent | indeterminate
```

`present` means that one bounded real regular file survived one same-handle
two-pass byte observation and the frozen path/descriptor checks. `absent`
means only either that two direct no-follow observations of the exact artifact
path returned `FileNotFoundError`, or that two no-follow observations of its
exact shared parent returned `FileNotFoundError` and no child path was touched.
The two cases retain their distinct frozen reasons. Every other enumerated
filesystem, resource, type, or race outcome is `indeterminate`.

The observer does not parse the reservation, ledger, or report. Stable
malformed reservation bytes, a corrupt/torn ledger, arbitrary report bytes,
and an empty regular file are all physically `present`. No P/A/I vector is a
transition verdict, publication fact, or safety certificate.

## 2. New paths, collection, anchors, and dependency boundary

The Phase-2b2b implementation paths are exactly:

```text
lean_rgc/evals/uprime_rpc_local_artifact_observer.py
tests/uprime_rpc_local_artifact_observer_cases.py
```

The support filename remains outside pytest's default patterns. It has an
exact dynamic `__all__` containing only its
`test_uprime_local_artifact_observer_*` functions and is imported exactly once
by `tests/test_uprime_rpc_ledger.py`:

```python
from uprime_rpc_local_artifact_observer_cases import *  # noqa: F403
```

Before a result commit, this amendment, source, support, collector, and later
execution record must be in `ANCHOR_PATHS` and the independently collected
membership oracle. Frozen and default collection must each expose every new
node once and only once.

The source may import only Python standard-library `dataclasses`, `hashlib`,
`os`, `re`, and `stat`; exactly `AttemptManifestV10Error` and
`PublicClaimReceiptV10` from
`lean_rgc.evals.uprime_rpc_attempt_manifest`; and only
`canonical_json_bytes` from `lean_rgc.evals.uprime_rpc_ledger`.

It may not import any private Phase-2b1 name, production litmus, reservation
inspector/writer, ledger parser/writer, report code, scanner/archive, CAS,
marker, recovery, subprocess, Git, socket/HTTP, Lean, worker, registered-run,
formal entrypoint, or later-phase module.

## 3. Exact selector and canonical path derivation

The single public API takes a caller-owned root and one exact
`PublicClaimReceiptV10`. There is no public anchor, artifact, basename, path,
filter, pagination, expected digest, bound, token, or precomputed-state input.

The receipt input must have exact type `PublicClaimReceiptV10`. Before any
filesystem I/O, the implementation projects its exact 13 public fields,
constructs a new `PublicClaimReceiptV10`, and lets the public constructor fully
revalidate it. A subclass or an invalid object modified through bypass mutation
rejects through the one new public error. The immutable reconstructed value,
not the caller's object, is retained and returned.

The receipt digest is:

```text
claim_receipt_sha256 = UPPER_HEX(SHA256(canonical_json_bytes(M)))
```

where `M` is the exact 13-field receipt mapping and the canonical bytes contain
no LF. This authenticates only equality to the caller-supplied structural
receipt; it does not authenticate origin, claim-once status, or a remote ref.

Let `A = reconstructed_receipt.license_commit[:12]`. The fixed repository
relative paths, in observation order, are:

```text
runs/uprime_u1_rpc_20260710/rpc_diagnostic_<A>.json.reservation
runs/uprime_u1_rpc_20260710/rpc_diagnostic_<A>.responses.jsonl
runs/uprime_u1_rpc_20260710/rpc_diagnostic_<A>.json
```

The artifact kinds are exactly `reservation`, `ledger`, and `report` in that
order. Host paths are formed only by joining the retained root text with the
fixed ASCII components. Repository paths always use forward slashes.

`root` must have exact type `str` and be nonempty and lexically absolute.
Subclasses, `os.PathLike`, bytes, and every other type reject before invoking
`__fspath__` or any other caller callback. The exact input text is retained
byte-for-byte. The implementation never calls `os.fspath`, `resolve`, `abspath`,
`realpath`, `normcase`, Unicode normalization, or case-folding on it.

An arbitrary prefix before the exact `runs/uprime_u1_rpc_20260710` suffix is
permitted solely for synthetic tests. Ancestor links in that prefix remain out
of scope.

“Local” is not an authenticated backing-store property. An absolute string can
name a UNC path, mounted remote filesystem, device namespace, or a local path
whose ancestor redirects elsewhere; ordinary filesystem reads may then use
host-managed transport. The observer imports and calls no network API, but it
does not prove transport locality. The licensed profile supplies only a
test-created local `tmp_path`; UNC/device/mount access is not part of execution.

## 4. Exact public records and API

All records use `@dataclass(frozen=True, slots=True)` in the displayed order.
Tuple fields are immutable tuples. The only public exception is
`LocalArtifactObservationV10Error(ValueError)`.

`LocalArtifactObservationV10` has exactly 13 fields:

```python
artifact_kind: str
repository_path: str
observation_state: str
reason_codes: tuple[str, ...]
artifact_sha256: str | None
artifact_bytes: int | None
byte_limit: int
content_validation: str
authority_scope: str
licenses_execution: bool
licenses_publication: bool
licenses_recovery: bool
licenses_later_stage: bool
```

`LocalArtifactSetObservationV10` has exactly 50 fields:

```python
observer_schema_version: str
observer_scope: str
origin_status: str
selector_scope: str
claim_receipt: PublicClaimReceiptV10
claim_receipt_sha256: str
anchor: str
registered_run_dir: str
parent_namespace_state: str
parent_reason_codes: tuple[str, ...]
reservation: LocalArtifactObservationV10
ledger: LocalArtifactObservationV10
report: LocalArtifactObservationV10
state_vector: tuple[str, str, str]
present_count: int
absent_count: int
indeterminate_count: int
total_present_bytes: int
accepted_byte_upper_bound: int
read_work_upper_bound_bytes: int
read_call_upper_bound: int
peak_buffer_upper_bound_bytes: int
hash_algorithm: str
snapshot_scope: str
root_scope: str
selector_binding: str
basename_spelling_verification: str
hostile_concurrent_reparse_prevention: str
ancestor_link_containment: str
reservation_validation: str
ledger_validation: str
report_validation: str
cross_artifact_binding: str
manifest_binding: str
inventory_binding: str
anchor_uniqueness: str
artifact_claim_binding: str
durability_observation: str
cas_observation: str
publication_observation: str
recovery_observation: str
witness_observation: str
remote_claim_authentication: str
git_object_authentication: str
authority_scope: str
canonical_run_authority: bool
licenses_execution: bool
licenses_publication: bool
licenses_recovery: bool
licenses_later_stage: bool
```

These are validating public records, not unchecked passive containers. Each
class has `__post_init__` and every normal constructor call must either produce
a value satisfying all applicable invariants below or raise the one public
exception. Private builders must use those constructors and may not use
`object.__new__`, bypass mutation, or an unvalidated factory.

The row validator requires exact field types; the exact kind/path-suffix/anchor
shape and kind-specific byte limit from Sections 3 and 5; exactly one of the
Section-8 present/absent/indeterminate digest, byte, and reason combinations;
the fixed content/authority strings; and exact-false license booleans. The set
validator requires exact field types and exact row-record types; reconstructs
and revalidates its receipt; recomputes its receipt digest and anchor; requires
the three exact derived paths and artifact order; enforces every parent/child
state relation, vector, count, present-byte sum, resource constant, and negative
suffix in Sections 5, 6, 8, and 9; and rejects every true license boolean. A
stable-present parent permits every child P/A/I vector but requires only the
local present, direct-child absence, or artifact-indeterminate reason domains;
no parent reason is allowed in a child. A stable-absent parent requires three
parent-derived absent rows. An indeterminate parent requires three cleared
indeterminate rows with its same singleton parent reason. `dataclasses.replace`
therefore revalidates; forged inconsistent public records cannot be constructed
normally.

The only public function is positional-only:

```python
observe_local_rpc_artifact_set_v1_0(
    root: str,
    claim_receipt: PublicClaimReceiptV10,
    /,
) -> LocalArtifactSetObservationV10
```

`__all__` is this exact ordered Python list:

```python
[
    "LocalArtifactObservationV10Error",
    "LocalArtifactObservationV10",
    "LocalArtifactSetObservationV10",
    "observe_local_rpc_artifact_set_v1_0",
]
```

Invalid caller inputs, invalid frozen constants, path-construction failures,
and internal invariant failures raise the one public exception and return no
partial result. Enumerated filesystem, resource, and race outcomes return a
complete three-row typed result; they do not raise or omit a later row.

## 5. Frozen resources and exact work proof

The production constants are:

```text
_MAX_RESERVATION_BYTES = 1_048_576
_MAX_LEDGER_BYTES = 134_217_728
_MAX_REPORT_BYTES = 16_777_216
_READ_CHUNK_BYTES = 65_536
_MAX_TOTAL_ACCEPTED_BYTES = 152_043_520
_MAX_RETURNED_PAYLOAD_WORK_BYTES = 304_087_043
_MAX_READ_CALLS = 4_646
_MAX_PEAK_BUFFER_BYTES = 65_536
```

Every constant is validated before receipt/root/filesystem processing as exact
type `int`; booleans reject. Per-artifact limits and aggregate accepted/work
bounds must be nonnegative. `_READ_CHUNK_BYTES` must be positive. Derived
constants must equal their formulas or the call rejects before I/O.

The accepted raw-byte upper bound is:

```text
1,048,576 + 134,217,728 + 16,777,216 = 152,043,520
```

Every present candidate is read twice. Each artifact can additionally return
at most one nonempty byte at the second EOF probe before becoming
`indeterminate`. Because observation continues after an indeterminate row, the
absolute returned-payload upper bound is:

```text
2 * 152,043,520 + 3 = 304,087,043 bytes
```

Zero-byte EOF returns, stat metadata, and receipt bytes are outside that
payload counter. With exact requested-length reads of at most 65,536 bytes and
one EOF probe per pass, the read-call upper bound is:

```text
2 * (16 + 2,048 + 256 + 3) = 4,646 calls
```

The implementation streams each pass directly into SHA-256 and retains no raw
artifact. The loop must keep exactly one local for the current `bytes` payload,
use it only for the byte count and synchronous `hash.update`, and execute
`del chunk` before issuing the next read or either EOF probe. The probe payload
is likewise deleted before any later read. No payload may enter a container,
closure, exception payload, result, mock call history, or other retained
reference. Under this frozen observer-owned-live-payload definition, its public
peak payload buffer bound is one 65,536-byte chunk; allocator slack and the
SHA-256 object's fixed internal state are not raw payload buffers. Tests use
actual small bytes under injected small limits; no sparse surrogate or
production-size fixture is accepted.

The payload-work and live-buffer proofs use the documented `os.read(fd, n)`
contract that a successful call returns at most `n` bytes. Deterministic tests
also inject overlong returns to prove fail-closed classification, but bytes
returned by such a contract-violating test double are not claimed to satisfy a
production OS resource bound.

## 6. Parent namespace observation and deliberate non-enumeration

The shared parent is the exact derived host directory corresponding to:

```text
runs/uprime_u1_rpc_20260710
```

The observer never calls `scandir`, lists sibling anchors, or validates
unrelated entry names. Full directory enumeration would add unrelated-entry
DoS, name-bound, and false completeness surfaces to this per-receipt slice.

The initial no-follow parent observation captures:

```text
D0 = (dev, ino, mode, reparse)
```

Every numeric component is exact `int`, with booleans rejected. `reparse` is
an exact `bool` derived from POSIX symlink mode plus the Windows
`FILE_ATTRIBUTE_REPARSE_POINT` bit.

If the parent is initially absent, only `FileNotFoundError` means absent. A
second immediate no-follow parent observation must also produce
`FileNotFoundError`. Stable parent absence returns three `absent` rows with
reason `stable_parent_absence` and performs zero child join/stat/open calls.
Appearance, another error, malformed metadata, non-directory, symlink, or
reparse makes the parent and all three rows `indeterminate`.

If the parent is initially a real non-reparse directory, all three child
observations run. A final no-follow observation must produce the exact same
`D1=D0`. Parent disappearance, error, unsafe type, or identity/type drift
downgrades all three rows to `indeterminate`, clears every digest/byte field,
and replaces each row's reason tuple with the parent failure reason.

`parent_namespace_state` is exactly `present`, `absent`, or `indeterminate`.
Its reason tuple is always a singleton. Stable present uses
`(stable_parent_directory,)`; stable absence uses
`(stable_parent_absence,)`; indeterminate uses exactly one of the nine
`parent_*` reasons frozen in Section 8. A parent-level downgrade replaces, not
appends to, every per-row reason tuple so a returned aggregate cannot retain a
seemingly present child under an unstable parent.

Directory ctime and mtime are deliberately absent from `D`: the directory is
shared by other anchors, whose unrelated updates must not invalidate this
per-receipt observation. The observer proves no parent-directory immutability.

Direct path lookup on a case-insensitive host may resolve an alternate on-disk
case or trailing-dot/space alias. Because there is no directory enumeration,
the output fixes `basename_spelling_verification=not_performed`. A later Git or
publication layer must verify exact tracked spelling if it needs that property.

## 7. Exact per-artifact observation protocol

For each derived path, in fixed reservation -> ledger -> report order:

1. perform a full-path no-follow stat;
2. if it raises `FileNotFoundError`, perform one immediate second no-follow
   stat on the same exact path;
3. otherwise require a real non-reparse regular file and size within that
   kind's inclusive bound;
4. open read-only using `O_RDONLY`, plus `O_BINARY` and `O_NOFOLLOW` whenever
   the host exposes those flags; no create, write, append, or truncate flag is
   permitted; require the return to be an exact nonnegative `int`, with booleans
   rejected, before treating the descriptor as opened;
5. capture descriptor metadata `F0`, require a regular file, and require
   `B(S0)=B(F0)`;
6. seek to offset zero, stream exactly the declared size into SHA-256 with
   exact requested-length reads, then perform one one-byte EOF probe;
7. capture `F1` and require `F1=F0`;
8. repeat the exact streaming pass and EOF probe;
9. capture `F2`, require `F2=F0`, and require equal byte counts and digests;
10. close the descriptor exactly once, without retry; and
11. only after a fully successful descriptor observation and successful close,
    perform the final full-path no-follow stat and require `S1=S0`.

The metadata families are:

```text
S = (dev, ino, mode, reparse, ctime_ns, size, mtime_ns)   # no-follow path
F = (dev, ino, mode,          ctime_ns, size, mtime_ns)   # descriptor
B = (dev, ino, size, mtime_ns)                            # cross-family
```

The exact rules are `S0=S1`, `F0=F1=F2`, and the single cross-family comparison
`B(S0)=B(F0)` immediately after open. Repeating `B` after an already accepted
family equality would be algebraically unreachable as a distinct failure and
is deliberately forbidden. Path and descriptor ctime or mode are never
compared across families; this preserves the Phase-2b1 Windows ctime
correction. No metadata is coerced with `int()` and no float-nanosecond fallback
exists.

Each non-EOF read must return exact type `bytes` with exactly the requested
length. A short or zero return before the declared size is `early_eof`; a
larger return is `read_error`. The one-byte probe must return exact `bytes`;
length zero means EOF, length one means `growth`, and length greater than one is
`read_error`. Every returned payload is deleted under the lifetime rule in
Section 5 before another read. This forbids unbounded retry loops and
overlapping observer-owned raw-payload buffers.

Each seek-to-zero call must return exact integer zero, with booleans rejected;
an exception or any other return is `seek_error`. A malformed open return is
`open_error` and is not closed. Once an exact nonnegative descriptor has been
accepted, its one close call must return `None`; an exception or any other
return is `close_error`.

If any failure occurs after open, the descriptor is still closed exactly once.
`close_error` is the sole reason when no earlier reason exists and is appended
as the second reason when a prior reason is pending. A close failure never
restores a present result and is never retried. If two passes and descriptor
checks succeed but the digests differ, the row is `content_drift`.

## 8. Tri-state invariants and exact reason domain

`observation_state` is exactly `present`, `absent`, or `indeterminate`.

For `present`:

```text
reason_codes = (stable_bounded_regular_file,)
artifact_sha256 = uppercase SHA-256 of exact raw bytes
artifact_bytes = exact 0..byte_limit
```

For direct-path `absent`:

```text
reason_codes = (absent_at_both_points,)
artifact_sha256 = artifact_bytes = null
```

Stable parent absence instead uses `(stable_parent_absence,)`. An absent row is
never produced from `PermissionError`, `ENOTDIR`, generic `OSError`, unsafe
type, resource excess, or malformed metadata.

For `indeterminate`, digest and byte fields are always null. Its primary reason
is exactly one of:

```text
parent_initial_stat_error
parent_absence_recheck_error
parent_absence_changed
parent_metadata_invalid
parent_reparse_entry
parent_nondirectory
parent_final_stat_error
parent_final_entry_invalid
parent_drift
initial_stat_error
absence_recheck_error
absence_changed
metadata_invalid
reparse_entry
nonregular_entry
size_limit
open_error
fstat_error
path_descriptor_mismatch
seek_error
read_error
early_eof
growth
descriptor_drift
content_drift
final_stat_error
final_entry_invalid
path_drift
close_error
```

The reason tuple has length one except when a pending post-open reason is
followed by a close failure, in which case the exact tuple is
`(primary_reason, close_error)`. It is ordered, unique, and never exposes host
paths, exception text, errno text, or Python exception class names.

The primary mapping is exact. Protocol stages are attempted in Section-7 order;
within one stage, the applicable rows below are evaluated from top to bottom
and the first match is primary. In particular, exact metadata validation
precedes reparse/type/size classification, and reparse precedes ordinary kind
classification:

| Observation stage/outcome | Primary reason |
|---|---|
| initial parent stat, non-`FileNotFoundError` failure | `parent_initial_stat_error` |
| second parent-absence stat, non-`FileNotFoundError` failure | `parent_absence_recheck_error` |
| second parent-absence stat returns any object | `parent_absence_changed` |
| initial parent metadata has a missing/non-exact numeric component | `parent_metadata_invalid` |
| initial parent is symlink/reparse | `parent_reparse_entry` |
| initial parent is not a directory | `parent_nondirectory` |
| final parent stat has any failure, including disappearance | `parent_final_stat_error` |
| final parent metadata is malformed, reparse, or non-directory | `parent_final_entry_invalid` |
| final valid parent `D1 != D0` | `parent_drift` |
| initial artifact stat, non-`FileNotFoundError` failure | `initial_stat_error` |
| second artifact-absence stat, non-`FileNotFoundError` failure | `absence_recheck_error` |
| second artifact-absence stat returns any object | `absence_changed` |
| initial artifact path metadata has a missing/non-exact numeric component | `metadata_invalid` |
| initial artifact path is symlink/reparse | `reparse_entry` |
| initial artifact path is not regular | `nonregular_entry` |
| initial artifact size is outside `0..byte_limit` | `size_limit` |
| descriptor open fails | `open_error` |
| any fstat fails, has malformed metadata, or is nonregular | `fstat_error` |
| initial `B(S0)=B(F0)` comparison fails | `path_descriptor_mismatch` |
| either seek-to-zero fails | `seek_error` |
| a read raises, returns a non-bytes value, or returns more than requested | `read_error` |
| a pre-EOF read returns fewer bytes than requested | `early_eof` |
| an EOF probe returns one byte | `growth` |
| `F1 != F0` or `F2 != F0` | `descriptor_drift` |
| completed passes have different byte counts or SHA-256 digests | `content_drift` |
| close fails with no earlier pending reason | `close_error` |
| final artifact stat has any failure, including disappearance | `final_stat_error` |
| final artifact metadata is malformed, reparse, or nonregular | `final_entry_invalid` |
| final valid `S1 != S0` | `path_drift` |

For `F1` and `F2`, any family inequality against `F0` is
`descriptor_drift`. At the final path stage, `S1!=S0` is `path_drift`. No later
`B` comparison or unreachable secondary binding reason exists. A close failure
never masks an earlier primary; it is appended as specified above. Parent-level
failure after all child observations replaces every row with the exact parent
primary and therefore has no trailing child `close_error`.

`content_validation=not_performed`, `authority_scope=none`, and every license
flag is false in every row, including `present`.

## 9. Aggregate derivation and exact negative suffix

The aggregate returns exactly the three named rows and:

```text
state_vector = (
    reservation.observation_state,
    ledger.observation_state,
    report.observation_state,
)
```

All 27 ordered vectors are valid outputs. Counts are exact occurrences in that
tuple; `total_present_bytes` is the sum of byte fields from present rows only.
There is deliberately no `bundle_status`, `complete`, `verified`,
`all_present`, `mixed`, `CLEAR`, `published`, `durable`, or causal-consistency
field.

Every returned set record fixes:

```text
observer_schema_version = lean-rgc-uprime-u1-local-artifact-set-observer-v0.1
observer_scope = three_receipt_derived_local_paths_raw_bytes_only
origin_status = unknown_may_be_synthetic
selector_scope = one_caller_supplied_public_receipt
registered_run_dir = runs/uprime_u1_rpc_20260710
accepted_byte_upper_bound = 152043520
read_work_upper_bound_bytes = 304087043
read_call_upper_bound = 4646
peak_buffer_upper_bound_bytes = 65536
hash_algorithm = SHA-256
snapshot_scope = sequential_per_artifact_not_atomic_bundle
root_scope = one_caller_supplied_unauthenticated_prefix
selector_binding = caller_supplied_receipt_to_paths_only
basename_spelling_verification = not_performed
hostile_concurrent_reparse_prevention = not_provided
ancestor_link_containment = not_authenticated
reservation_validation = not_performed
ledger_validation = not_performed
report_validation = not_performed
cross_artifact_binding = not_performed
manifest_binding = not_performed
inventory_binding = not_performed
anchor_uniqueness = not_performed
artifact_claim_binding = not_performed
durability_observation = not_performed
cas_observation = not_performed
publication_observation = not_performed
recovery_observation = not_performed
witness_observation = not_performed
remote_claim_authentication = not_performed
git_object_authentication = not_performed
authority_scope = none
canonical_run_authority = false
licenses_execution = false
licenses_publication = false
licenses_recovery = false
licenses_later_stage = false
```

Receipt input does not prevent a free 48-bit anchor selector. A caller can build
a structurally valid but unauthenticated receipt whose arbitrary lowercase
`license_commit` starts with any chosen 12-hex anchor, then probe that favorable
local slice. Two different receipts can also share the same 12-hex anchor. This
phase does not enumerate receipts, authenticate their origin, constrain the
selection process, or reject cross-receipt anchor collisions. Those facts are
why `inventory_binding`, `anchor_uniqueness`, and `artifact_claim_binding`
remain `not_performed` and why no result is a performance sample.

## 10. Explicit TOCTOU and security nonclaims

The row-local evidence endpoint is state- and path-dependent. A `present` row
ends at its successful post-close `S1` stat. A direct `absent` row ends at the
second `FileNotFoundError` for that artifact. An `indeterminate` row ends at its
last attempted local observation or close; it asserts no later path fact unless
that later stat was actually reached. Stable parent-derived absence ends at the
second parent `FileNotFoundError` and asserts no child-path observation. If the
final parent check downgrades the aggregate, the reported parent endpoint is
that final parent attempt, all child evidence fields are cleared, and no child
path fact is extended to that time.

The three child intervals are sequential and non-atomic; the parent interval is
separate. Mutation of reservation after its row-local endpoint while
ledger/report are observed is outside the reservation row, even when the final
parent `D1=D0`. No fact covers mutation after return.

On POSIX, `O_NOFOLLOW` is used when exposed. On Windows, ordinary `os.open`
does not provide a Win32 `OPEN_REPARSE_POINT`/no-follow handle. A hostile actor
can replace the final component with a reparse point between initial stat and
open; the later binding/final checks can downgrade the row but the process may
already have read bytes from the substituted target. Therefore:

```text
hostile_concurrent_reparse_prevention = not_provided
```

This observer is a mutation detector for bounded synthetic tests, not a
non-dereference sandbox or hostile-concurrency security boundary. A true
Windows prevention design requires a separately frozen native handle API and
is outside Phase 2b2b.

No row proves fsync, durability, immutability, privacy, format validity,
reservation-token possession, ledger closure, report schema, inter-artifact
agreement, attempt-manifest agreement, remote publication, or recoverability.

## 11. Finite Phase-2b2b acceptance matrix

Before a result commit, the explicit support, frozen four-file M2b profile, and
default collection must pass with zero failures/errors. The frozen profile has
zero skips/xfails. Required finite families are:

1. independent literal receipt mapping/digest, derived anchor and three paths,
   13/50-field records, exact annotations, frozen/slots tuples, exact
   positional-only signature, ordered `__all__`, every negative suffix, and a
   finite invalid-constructor family covering every row/set field and every
   cross-field branch of both `__post_init__` validators;
2. exact receipt reconstruction; wrong/subclass/invalid/bypass-mutated receipt,
   duplicate or inconsistent identity fields, root exact-type/empty/relative/
   subclass/bytes failures, hostile `PathLike` rejection with zero `__fspath__`
   calls, retained lexical dot-dot/case text, freely chosen receipt-anchor
   prefixes, and all bound failures before I/O;
3. stable parent absent/present, absence appearance and error, every exact `D`
   component invalid/bool, non-directory/symlink/Windows-reparse sentinels,
   parent disappearance/replacement/type drift, `D1!=D0`, zero child work on
   absent/unsafe parent, and proof that `scandir` is never reached;
4. all 27 P/A/I vectors in exact artifact order, all count/byte derivations,
   every determinate subset, no rejected causal combination, and AST proof that
   no aggregate status/all-present boolean exists;
5. per kind: stable empty, malformed, and arbitrary bytes remain present;
   known literal raw digest; actual small N-1/N/N+1 bytes under injected limits;
   kind-specific bound selection; no raw-byte retention or sparse surrogate;
6. direct absence twice; first/second stat permission and generic I/O errors;
   appearance between absence observations; regular/directory/symlink/reparse;
   size limit; exact `follow_symlinks=false`; and no absent result from any
   non-`FileNotFoundError` path;
7. open flags contain no create/write/append/truncate and include each of
   `O_BINARY` and `O_NOFOLLOW` when exposed; exact fd/seek/close return types and values; every
   open/fstat/lseek/read/EOF-probe/close/final-stat failure;
   exact two passes, one probe per pass, exact-length reads, early EOF, growth,
   wrong read type, no retry, payload `del` before each subsequent read/probe,
   no payload retention, and close-error ordering;
8. every `S`/`F` exact-int component and bool rejection; `S0/S1` and `F0/F1/F2`
   component drift; every initial `B(S0)/B(F0)` component mismatch; replacement before open, between
   passes, after pass two, and before final stat; path/fd ctime inequality
   accepted when family-local invariants hold; same-size content drift;
9. exact production formulas for 152,043,520 accepted bytes, 304,087,043
   returned payload bytes, 4,646 read calls, and 65,536 observer-owned live
   payload buffer under the frozen lifetime definition;
   continue to later artifacts after every per-row indeterminate; no partial
   result or early favorable-vector return;
10. mutate an earlier artifact after its final stat while later rows are
    observed and prove the output retains the mandatory sequential/non-atomic,
    no-post-return, no-durability, and no-cross-binding labels;
11. raise if any existing reservation verifier, ledger parser, report/litmus,
    scanner, writer, CAS, marker, recovery, Git, network, Lean, worker, or
    registered-run capability is reached; freeze exact imports and OS seams;
    reject builtin `open`, writes, mkdir, link/rename/unlink, fsync, subprocess,
    socket/HTTP, async, threads, sleeps, retries, and path resolution;
12. no repository-tree or `runs/` metadata delta; unchanged literal/SHA/Git
    blob default-deny registry; support/collector uniqueness; source/support/
    amendment/result anchors; Windows zero-skip profile and Ubuntu CI.

All filesystem fixtures are test-created under `tmp_path`. Windows reparse,
hostile alias, permission, replacement, and metadata cases use deterministic
injected observations rather than touching device names, ADS, real junctions,
or protected files. No registered path, network, SSH, Lean, worker, or GPU
action is part of the Phase-2b2b profile.

## 12. Stop rule

Commit, push, and green CI of this reviewed amendment license only the exact
read-only synthetic Phase-2b2b implementation on local Windows CPU. Before
that gate, no Phase-2b2b source or support code may begin.

A later committed and pushed execution record with the frozen zero-skip
Windows profile and green Ubuntu CI licenses only Phase 2b2c preregistration
for the pure single-process in-memory fake CAS kernel.

Phase 2b2c implementation, local staging, artifact writing, marker/recovery,
witness issuance, real claim/publication, network/SSH, Lean, worker execution,
GPU construction, Phase 2c, canonical diagnostic, M2c, U'0.5, and U'2--U'5
remain barred.
