# U'1 evidence milestone 2b phase 2b2d nonce staging fake publisher amendment

Date: 2026-07-11

Status: PREREGISTERED NONCANONICAL LOCAL-STAGING / PURE FAKE-PUBLISHER SLICE;
NO REAL OR CANONICAL PUBLICATION, STORE, REMOTE CAS, CLEANUP, FSYNC, DURABILITY,
MARKER, RECOVERY, EPOCH, WITNESS, MANIFEST, EXECUTION, LEAN, NETWORK, WORKER,
CANONICAL-RUN, RERUN, LATER-STAGE, OR GPU AUTHORITY.

## 1. Purpose, prerequisite, and adversarially reduced boundary

The committed and pushed Phase-2b2c result at
`faf163882216c1fa9679ece8058d8f1b43994d10`, together with successful hosted
CI run `29140750358`, licenses Phase-2b2d preregistration only. It does not
license this phase's source or support code.

Phase 2b2d freezes the smallest bridge between the pure one-cell fake-CAS
kernel and local filesystem staging. A caller supplies one deterministic
collision nonce and one existing staging parent. The changed branch creates
one exclusive nonce-separated file, writes the exact proposal, reads the same
descriptor back, closes it, observes the retained path and parent at one
endpoint, and only then returns the Phase-2b2c normal acknowledged value
transition. Conflict and existing-identical branches perform no physical
filesystem operation.

The returned transition is still a pure, caller-threaded value. There is no
mutable or process-global fake store and no hidden application. “Fake
publisher” means only that the normal acknowledged Phase-2b2c transition is
withheld from the caller until the local staging endpoint succeeds. It does
not mean that a real remote ref, canonical artifact, local final name, claim,
receipt, reservation, or manifest has been published.

Three expansions considered during preregistration are deliberately rejected:

- an exclusive hard link or final filename would add a second local
  publication endpoint not required by the licensed boundary;
- `fsync` would add only a syscall-return observation while inviting an
  unsupported crash/durability interpretation; and
- unlinking the stage would introduce a destructive TOCTOU and a fallible
  post-stage cleanup endpoint.

Accordingly this phase performs no link, rename, replace, unlink, directory
creation, file or directory `fsync`, flush, cleanup, scan, retry loop, or
promotion. A successful changed call retains exactly one stage file at its
observation endpoint. A failed changed call may retain a partial or complete
stage. Later classification, cleanup, causality, exclusion, replay, and
reconciliation remain Phase-2b2e work.

The implementation may begin only on local Windows CPU after this amendment
is adversarially reviewed, committed, pushed, and green in CI. No SSH, GPU,
network service, Lean, worker, registered experiment, canonical diagnostic,
or repository/canonical artifact write is part of Phase 2b2d.

## 2. Exact paths, collection, anchors, and preregistration sentinel

The future implementation paths are exactly:

```text
lean_rgc/evals/uprime_rpc_local_staging_fake_publisher.py
tests/uprime_rpc_local_staging_fake_publisher_cases.py
```

The support filename is outside pytest's default patterns. At implementation
time it will expose only its `test_uprime_local_staging_fake_publisher_*`
functions and be imported exactly once by `tests/test_uprime_rpc_ledger.py`:

```python
from uprime_rpc_local_staging_fake_publisher_cases import *  # noqa: F403
```

This preregistration commit anchors only this amendment. It adds
`EVIDENCE_MILESTONE_2B_PHASE2B2D_AMENDMENT_PATH` to `ANCHOR_PATHS` and to the
independent membership test. It does not add future source, support, or result
paths.

An executable sentinel in `tests/test_uprime_rerun_license.py` requires both
future implementation files to be absent and the future collector import to
occur zero times. The sentinel may be replaced only by an implementation
commit whose parent contains this pushed amendment after its hosted CI is
green. At that later implementation commit, source/support path constants,
both anchor memberships, and exactly-once collection replace the absence
sentinel. The execution-record path is added only in a later result commit.

No package initializer or tier-manifest change is required in any of those
three commits. Git ancestry, push state, and hosted-CI conclusion remain
external governance observations; no local record or hash proves them.

## 3. Exact source imports and public surface

Apart from blank lines, the source starts with exactly these imports:

```python
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import re
import stat

from lean_rgc.evals.uprime_rpc_fake_cas_kernel import (
    InMemoryFakeCasStateV10,
    InMemoryFakeCasTransitionV10,
    InMemoryFakeCasV10Error,
    step_in_memory_fake_cas_v1_0,
)
```

The future import is mandatory. Raw `__annotations__` and
`dataclasses.Field.type` strings are frozen and tests separately resolve them
for semantic comparison.

No prior private symbol may be imported. In particular the module may not
import the attempt manifest, claim receipt, seed inventory, artifact observer,
reservation writer, rerun gate, ledger, canonical-JSON helpers, or litmus
runner. It may not import `pathlib`, `io`, `tempfile`, `shutil`, `secrets`,
`random`, UUIDs, time, clocks, subprocesses, sockets, HTTP, Git, async,
threads, multiprocessing, Lean, workers, scanners, archives, registered runs,
or formal entrypoints.

The exact ordered production `__all__` is:

```text
LocalStagingFakePublisherV10Error
LocalStagingFakePublishResultV10
stage_and_fake_publish_normal_v1_0
```

There is one public exception:

```python
class LocalStagingFakePublisherV10Error(ValueError): ...
```

All semantic, resource, frozen-constant, fake-CAS, path-derivation, metadata,
ordinary filesystem, collision, write, readback, binding, and close failures
are mapped to this exception. Missing, extra, or keyword-supplied
positional-only arguments remain Python `TypeError`. `BaseException`
subclasses are not caught. No failure returns a partial Result or candidate
Transition.

There is exactly one public function, with no defaults, variadic arguments,
or keyword acceptance:

```python
def stage_and_fake_publish_normal_v1_0(
    staging_parent: str,
    collision_nonce: str,
    state: InMemoryFakeCasStateV10,
    expected_state_version_sha256: str,
    proposed_payload: bytes,
    /,
) -> LocalStagingFakePublishResultV10: ...
```

There is no caller-selectable directive or alternate payload. The function
invokes Phase 2b2c only as:

```python
step_in_memory_fake_cas_v1_0(
    state,
    expected_state_version_sha256,
    proposed_payload,
    "apply_intended_acknowledge",
    None,
)
```

There is no receipt, claim, key, basename, operation/request identity, retry
policy, marker, epoch, witness, callback, authority flag, or final path
argument.

## 4. Exact input and lexical-path contract

Frozen constants and every structural input are validated before semantic
classification. Exact types are required; subclasses, `PathLike`, bytes paths,
bytearray, memoryview, bool-as-int, and callback-bearing coercions are rejected
without invoking them.

`staging_parent` must satisfy all of the following:

1. exact `str`, UTF-8 encodable without surrogate handling;
2. UTF-8 length in inclusive range 1 through 4,096 bytes;
3. no U+0000--U+001F control, U+007F, or embedded NUL;
4. `os.path.isabs(staging_parent)` returns exact `True`;
5. `os.path.normpath(staging_parent)` returns an exact string equal to the
   supplied text; and
6. on Windows, it does not begin with `\\` or `//`, thereby rejecting UNC and
   device-namespace spellings, and it matches `^[A-Za-z]:\\` so a rooted path
   always carries an explicit drive rather than depending on the current
   drive.

No `resolve`, `realpath`, `abspath`, case folding, separator rewriting, or
environment/cwd expansion is performed. The normalized lexical spelling is
retained verbatim. A POSIX mount or Windows drive can still be backed by a
remote, virtual, overlay, or adversarial filesystem; this phase neither
detects nor authenticates that property.

`collision_nonce` is an exact lowercase ASCII string matching
`[0-9a-f]{32}` and is decoded to exactly 16 bytes for commitment framing. It
is caller-selected. It is only a collision separator. It is not evidence of
entropy, freshness, uniqueness, secrecy, capability possession, request
identity, operation identity, epoch ownership, idempotence, or exactly-once
execution.

The exact basename is:

```text
uprime-rpc-fake-cas-stage-v1-<collision_nonce>.bin
```

It is 65 ASCII bytes. `stage_path` is the exact result of
`os.path.join(staging_parent, stage_basename)`. The join must return exact
`str`, must not equal the parent, and must encode to at most 4,162 UTF-8 bytes.
No free-form caller basename is accepted; the only caller-derived basename
component is the exact validated nonce.

The parent must already exist when the changed branch reaches physical I/O.
The function never creates it. Conflict and existing-identical calls validate
the lexical parent and nonce but do not stat the parent, derive filesystem
metadata, open a path, draw randomness, or create a stage.

## 5. Exact public Result record

`LocalStagingFakePublishResultV10` uses
`@dataclass(frozen=True, slots=True)` and has exactly these 63 fields in this
order:

```text
result_schema_version: str
result_scope: str
origin_status: str
staging_parent: str
collision_nonce: str
stage_basename: str
stage_path: str
cas_transition: InMemoryFakeCasTransitionV10
outcome: str
reason_codes: tuple[str, ...]
cas_gate_status: str
parent_observation_status: str
stage_status: str
stage_payload_bytes: int | None
stage_payload_sha256: str | None
write_call_count: int
read_call_count: int
operation_sha256: str
payload_byte_limit: int
staging_parent_utf8_byte_limit: int
stage_path_utf8_byte_limit: int
collision_nonce_chars: int
io_chunk_bytes: int
write_call_upper_bound: int
read_call_upper_bound: int
filesystem_payload_work_upper_bound_bytes: int
peak_transient_buffer_upper_bound_bytes: int
retained_payload_copy_upper_bound_bytes: int
stage_file_create_upper_bound: int
retained_stage_byte_upper_bound: int
operation_hash_preimage_upper_bound_bytes: int
hash_preimage_construction: str
result_provenance: str
collision_nonce_scope: str
staging_parent_authority: str
path_derivation_scope: str
ancestor_reparse_check_scope: str
backing_store_scope: str
hostile_concurrent_reparse_prevention: str
stage_exclusivity_scope: str
stage_readback_scope: str
stage_retention_scope: str
durability_scope: str
cleanup_scope: str
publisher_scope: str
state_linearity: str
concurrency_scope: str
idempotence_scope: str
exactly_once_scope: str
payload_confidentiality: str
attempt_completeness: str
marker_scope: str
recovery_scope: str
epoch_scope: str
witness_scope: str
manifest_scope: str
remote_publication: str
authority_scope: str
canonical_remote_authority: bool
licenses_execution: bool
licenses_publication: bool
licenses_recovery: bool
licenses_later_stage: bool
```

The fixed leading and resource fields are exactly:

```text
result_schema_version = lean-rgc-uprime-u1-local-staging-fake-publish-result-v1.0
result_scope = one_call_changed_branch_nonce_stage_before_pure_normal_fake_cas_return
origin_status = unknown_may_be_synthetic
payload_byte_limit = 1048576
staging_parent_utf8_byte_limit = 4096
stage_path_utf8_byte_limit = 4162
collision_nonce_chars = 32
io_chunk_bytes = 65536
write_call_upper_bound = 1048576
read_call_upper_bound = 17
filesystem_payload_work_upper_bound_bytes = 2097152
peak_transient_buffer_upper_bound_bytes = 65536
retained_payload_copy_upper_bound_bytes = 0
stage_file_create_upper_bound = 1
retained_stage_byte_upper_bound = 1048576
operation_hash_preimage_upper_bound_bytes = 1052813
hash_preimage_construction = payload_streamed_no_full_preimage_materialization
```

The exact negative suffix is:

```text
result_provenance = unauthenticated_forgeable_value_object_not_io_attestation
collision_nonce_scope = caller_supplied_collision_separator_not_identity_or_entropy_evidence
staging_parent_authority = caller_supplied_write_location_not_authenticated_namespace
path_derivation_scope = lexical_native_join_no_resolution_or_canonical_binding
ancestor_reparse_check_scope = not_performed_only_final_parent_entry_observed
backing_store_scope = unauthenticated_may_be_remote_virtual_or_overlay
hostile_concurrent_reparse_prevention = not_provided
stage_exclusivity_scope = changed_branch_one_native_path_exclusive_create_only
stage_readback_scope = changed_branch_same_descriptor_exact_bytes_at_one_observation_interval
stage_retention_scope = any_created_stage_retained_no_post_return_lifetime_claim
durability_scope = fsync_not_called_crash_and_power_loss_not_observed
cleanup_scope = not_performed_any_created_stage_may_remain_after_success_or_error
publisher_scope = pure_fake_cas_value_return_changed_branch_stage_gated_not_real_publication
state_linearity = caller_threaded_not_enforced
concurrency_scope = no_exclusion_or_cross_process_atomicity
idempotence_scope = not_provided_distinct_nonce_is_explicit_new_attempt
exactly_once_scope = not_provided
payload_confidentiality = not_provided_any_staged_bytes_written_to_caller_location
attempt_completeness = successful_returns_only_errors_unjournaled
marker_scope = not_created_or_observed
recovery_scope = not_performed
epoch_scope = none
witness_scope = none
manifest_scope = not_read_or_written
remote_publication = not_performed
authority_scope = none
canonical_remote_authority = false
licenses_execution = false
licenses_publication = false
licenses_recovery = false
licenses_later_stage = false
```

All strings and flags are first-class validated fields. A detached Result does
not depend on prose to disclose its scope.

## 6. Exact outcome table and precedence

There are exactly three successful-return outcomes in tag order:

```text
01 cas_conflict_no_stage
02 cas_existing_identical_no_stage
03 staged_intended_fake_publish_acknowledged
```

Their complete dynamic cells are:

| outcome | reason code | Phase-2b2c outcome | CAS gate | parent observation | stage status | stage bytes/hash | write/read calls |
|---|---|---|---|---|---|---|---|
| `cas_conflict_no_stage` | `expected_state_version_mismatch` | `conflict_no_change` | `conflict` | `not_attempted` | `not_attempted` | `None` / `None` | 0 / 0 |
| `cas_existing_identical_no_stage` | `exact_payload_already_current` | `existing_identical_no_change` | `existing_identical` | `not_attempted` | `not_attempted` | `None` / `None` | 0 / 0 |
| `staged_intended_fake_publish_acknowledged` | `exact_stage_retained_before_exposing_synthetic_acknowledged_transition` | `intended_applied_acknowledged` | `intended_acknowledged` | `stable_at_endpoint` | `retained_stable_at_endpoint` | exact proposal count / raw SHA-256 | bounded actual counts |

`reason_codes` is an exact one-element tuple. No I/O error, collision,
acknowledgement loss, wrong delta, cleanup state, or recovery state is a fourth
Result outcome.

The exact public-function precedence is:

1. validate every frozen constant and derived resource formula;
2. validate exact scalar types, parent/nonce grammar, and lexical path
   derivation;
3. invoke the exact fixed normal Phase-2b2c step, mapping its public error;
4. for conflict or existing-identical, construct and return the no-stage
   Result without any physical filesystem call;
5. only for `intended_applied_acknowledged`, execute the Section-7 staging
   protocol; and
6. only after that endpoint, construct and return the changed Result.

This means stale expected version plus malformed parent/nonce is a local input
error rather than conflict. Structurally invalid State, expected hash, or
proposal raises before any physical I/O. A maximum-generation exact-identical
proposal remains a no-stage return; a maximum-generation changed proposal is a
public error with no stage.

The Phase-2b2c Transition is a candidate pure value while staging runs. It is
not returned on any staging failure. Because the kernel has no mutable store,
discarding that candidate does not roll back or hide a global mutation.

## 7. Exact changed-branch filesystem protocol

Production uses private direct seams for exactly these native operations:

```text
os.path.isabs
os.path.normpath
os.path.join
os.stat
os.open
os.fstat
os.write
os.lseek
os.read
os.close
```

Tests may monkeypatch those private seams only. There is no public dependency
injection or fault directive.

### 7.1 Parent observation

The first physical operation is:

```python
os.stat(staging_parent, follow_symlinks=False)
```

The exact initial parent snapshot is:

```text
D0 = (st_dev, st_ino, st_mode, reparse)
```

Every numeric component must be exact nonnegative `int`, with bool rejected.
The frozen `FILE_ATTRIBUTE_REPARSE_POINT` mask is exact integer `0x400`.
Absent `st_file_attributes` contributes exact zero; when the attribute is
present it must be exact nonnegative `int`, with bool rejected. `reparse` is
exactly `stat.S_ISLNK(st_mode) or bool(st_file_attributes & 0x400)`. The parent
must be a real non-reparse directory. Missing, inaccessible, malformed,
non-directory, symlink, or reparse parents raise the public error before open.

No ancestor component is walked or opened. This is a final-parent-entry
observation, not containment against hostile ancestor replacement.

### 7.2 Exclusive create and initial descriptor

The open flags are exactly:

```text
O_CREAT | O_EXCL | O_RDWR
+ O_BINARY when exposed
+ O_NOINHERIT when exposed
+ O_CLOEXEC when exposed
+ O_NOFOLLOW when exposed
```

The mode argument is exactly `0o600`. `O_TRUNC`, `O_APPEND`, `O_WRONLY`, and
every other flag are absent. `FileExistsError` means only that the supplied
collision path is occupied. The existing entry is not statted, opened, read,
linked, renamed, or deleted; the call raises the public error. There is no
same-call nonce retry. An explicit retry is a new call with a different
caller-selected nonce.

A successful `os.open` return must be exact nonnegative `int`. An invalid
return is not treated as a descriptor and is not closed. The initial `fstat`
must describe a real regular non-reparse file of size zero. Its exact
descriptor snapshot is:

```text
F0 = (st_dev, st_ino, st_mode, st_ctime_ns, st_size, st_mtime_ns)
```

Every component is exact `int`, bool rejected. No existing file content is
accepted as an idempotent success.

### 7.3 Write and readback

The proposal is written from a `memoryview` in chunks of at most 65,536 bytes.
Positive partial writes are completed. Each `os.write` return must be an exact
integer in inclusive range 1 through the requested remaining slice. Zero,
negative, bool, over-report, exception, or more than 1,048,576 calls fails.
The empty payload makes zero write calls.

After the final write, `F1 = fstat(fd)` must be a regular non-reparse file with
the same `(dev, ino, file-kind)` as `F0` and exact size equal to the proposal.
Expected write-induced size/time changes are not compared to `F0`.

`os.lseek(fd, 0, os.SEEK_SET)` must return exact integer zero. Readback requests
exactly `min(65,536, remaining)` bytes per data call. Each data return must be
exact `bytes` of exactly the requested length. Short, empty-before-complete,
overlong, non-bytes, or exceptional returns fail. Every chunk is compared
directly to the corresponding proposal `memoryview` and fed incrementally to
SHA-256. Digest equality alone is insufficient. After the expected length,
one `os.read(fd, 1)` EOF probe must return exact `b""`; growth fails.

Thus read calls are exactly `ceil(payload_bytes / 65,536) + 1`, in inclusive
range 1 through 17. `F2 = fstat(fd)` after readback must equal `F1` exactly.
The incremental readback SHA must equal the raw proposal SHA.

No `fsync`, flush, mmap, buffering wrapper, full-file read, encoding, JSON,
hex, Base64, or proportional container is permitted.

### 7.4 Close and retained endpoint

`os.close(fd)` is called exactly once and must return exact `None`. On a prior
post-create failure, close is attempted exactly once before the public error is
raised. A close failure is reported, but no unlink is attempted and descriptor
closure is not claimed.

Only after successful close, the stage path is observed with no-follow stat.
The exact path snapshot is:

```text
P = (st_dev, st_ino, st_mode, reparse, st_ctime_ns, st_size, st_mtime_ns)
```

It must be a real non-reparse regular file. Its cross-close, cross-family
binding `(dev, ino, size)` must equal the corresponding binding from `F2`.
`mtime_ns` is deliberately excluded from that comparison: on Windows a
writer's last-write time need not be finalized until the last writing handle
closes. Full `F1 = F2` remains required inside the open-descriptor family. The
parent is then observed once more with no-follow stat; `D1` must equal `D0`
exactly. The endpoint is the completion of those two observations.

The stage is retained. There is no subsequent filesystem action in a
successful call. The Result says only that the path and parent matched at this
endpoint. Another actor can mutate, remove, replace, link, or expose the file
immediately afterward.

### 7.5 Failure residue

Any failure after exclusive create returns no Result and no Transition. The
stage is never deleted by this phase. It may contain zero bytes, a prefix, the
complete payload, or bytes concurrently altered by another actor. The path
may also have been replaced. This phase does not call such residue owned,
orphaned, recoverable, causal, durable, private, or safe to remove.

Using a distinct nonce prevents one occupied path from being the only name
available to an explicit retry; it does not guarantee that the new name is
free. A pre-start file with the same supplied nonce collides fail-closed and is
not inspected. Enumeration and adjudication are deferred.

## 8. Operation commitment and frozen goldens

The operation commitment domain is exact bytes:

```python
D_OPERATION = (
    b"lean-rgc-uprime-u1-local-staging-fake-publisher-operation-v1\0"
)
```

Its length is exactly 61 bytes. Define `U32` and `U64` as unsigned big-endian
four- and eight-byte integers. Let `P` be the exact UTF-8 parent bytes, `N` the
16 decoded nonce bytes, `T` the 32 raw bytes of
`cas_transition.transition_sha256`, and `X` the exact staged payload or absent.
The preimage is:

```text
D_OPERATION
|| U32(len(P)) || P
|| N
|| T
|| outcome_tag_u8
|| parent_observation_tag_u8
|| stage_status_tag_u8
|| optional_stage_tag_u8
|| [ U64(len(X)) || X ]
|| U64(write_call_count)
|| U64(read_call_count)
```

Tags use the Section-6 orders; parent observation is `01 not_attempted`, `02
stable_at_endpoint`; stage status is `01 not_attempted`, `02
retained_stable_at_endpoint`; optional stage is `00 absent`, `01 present`.

The proposal is streamed raw when present. A proposal digest is not substituted
for byte identity. No full preimage is concatenated. The inclusive maximum is:

```text
61 + 4 + 4096 + 16 + 32 + 1 + 1 + 1 + 1
+ 8 + 1048576 + 8 + 8 = 1052813 bytes
```

Use the Phase-2b2c definitions `A = 0x11 * 32` and `B = 0x22 * 32`, with A at
generation one. The exact independent goldens are:

| case | parent | nonce | fake Transition | write/read | preimage bytes | OPERATION |
|---|---|---|---|---|---:|---|
| conflict | `C:\uprime-stage` | `00` repeated 16 | `60D25236487695725CF5C6AAE03B8BD5426085D3B6A89DB8527843E79E3C4F3F` | 0 / 0 | 148 | `94AEB8A5436ECFB6F92636FF5F1F3FE54F017B97DBC2BFEA2D4B8CAFFEDAD29B` |
| identical A | `/tmp/uprime-stage` | `11` repeated 16 | `E3293691B197ED371747C098EF462850846705282FBD449BAD8D321FD6E742BC` | 0 / 0 | 150 | `4034FA2EB322E027EBAD97F1403E2FA834FFAF1A1AB2A67190FA52BFCCCF71A1` |
| staged A-to-B | `C:\uprime-stage` | `22` repeated 16 | `029C6ECD6148EDC6736727E780DE474C7D760B63E650EA22744800547208C44C` | 1 / 2 | 188 | `1977C339326297C3FA8A13F85236DF22643DA662D5CDF9619513A05B40AF49D1` |
| absent-to-empty staged | `/tmp/uprime-stage` | `33` repeated 16 | `194FC9297D81669BDE36952C414D47F013FD0DBF4A51DA175B2649447DEE1AAF` | 0 / 1 | 158 | `29BA2F61DB81D4030988BEAEBF123B1031C5C06B60E2C3EC92ECBCDB311E366F` |

The Windows strings above contain one native backslash after `C:` and their
exact parent UTF-8 hex is
`433A5C757072696D652D7374616765`. Goldens test framing directly and do not
claim that a
Windows lexical path is valid on a POSIX host or conversely.

## 9. Resource and computation contract

The payload limit is inherited exactly from Phase 2b2c: 1,048,576 bytes.
Per changed call:

- at most one stage path is created;
- at most 1,048,576 bytes are retained in that stage at a successful endpoint;
- payload filesystem work is at most 1,048,576 written plus 1,048,576 read;
- write calls are at most 1,048,576 under one-byte positive progress;
- read calls are at most 17 including the EOF probe;
- the largest caller-independent live payload buffer is one 65,536-byte read
  result; and
- no additional proportional payload copy is retained in Python memory.

The `memoryview`, hash object and its internal buffer, fixed framing, metadata
tuples, regex match, scalar counters, exception objects, and OS buffers are not
counted as retained payload copies. The existing Phase-2b2c Transition retains
its already frozen payload references and advertises its own general bound;
this wrapper does not weaken or relabel it.

There is no cumulative bound across calls because files are retained and no
registry tracks them. That absence is intentional and first-class: callers
must use test-owned disposable parents during Phase-2b2d verification.

Runtime is linear in input validation/hash work plus bytes written/read. No
retry, sleep, timeout, clock, randomness, hidden state, memo, map, history,
deduplication table, directory enumeration, or recursive traversal is allowed.

## 10. Constructor revalidation and record non-attestation

The Result's normal public constructor validates exact field types, constants,
nullable cells, one-element reason tuple, outcome table, path derivation,
resource arithmetic, and operation commitment. It requires exact
`InMemoryFakeCasTransitionV10`, rederives the fixed normal transition through
the public Phase-2b2c step, and compares every transition field. Imported
fake-CAS errors are mapped to the local public exception.

Validation is acyclic: a private derivation helper may call the Phase-2b2c
public step, but neither public Phase-2b2d function calls itself and the
Phase-2b2c module does not import this module. The production function uses the
same private scalar derivation and then the normal Result constructor.

`dataclasses.replace`, normal construction, subclasses, and bypass-mutated
Transition/State inputs must not forge inconsistent fields. Exact integers
reject bool; exact bytes reject bytearray/memoryview; hashes are uppercase
hex64; nullable fields obey the outcome table.

Crucially, Result construction and validation perform no physical filesystem
operation. A caller can construct a value-consistent staged Result and
recompute its hash without ever creating a file. The record is therefore not
an attestation, witness, capability, or proof that I/O occurred. Revalidation
after return does not restat the retained path and makes no current-existence
claim.

## 11. Threat model and explicit nonclaims

This slice observes only one caller-selected final parent entry and one stage
path over a finite interval. Python's portable `os.open` surface does not
provide a hostile-race containment proof for Windows reparse points or all
ancestor substitutions. Stat/open/stat comparisons fail closed for observed
drift but do not make the path secure against a concurrent adversary.

The module provides no:

- authenticated local namespace, local-disk fact, parent ownership, ancestor
  containment, permission guarantee, confidentiality, secure deletion, or
  post-return file lifetime;
- `fsync`, flush, directory-entry persistence, crash/power-loss durability, or
  recovery fact;
- final/published local name, hard link, rename, promotion, canonical artifact,
  claim, reservation, receipt, ledger, report, or manifest;
- mutable fake store, key namespace, global CAS linearity, concurrency
  exclusion, request identity, retry protocol, idempotence, or exactly-once;
- acknowledgement-loss injection, causal marker, conflict-without-marker
  distinction, orphan attribution, epoch, release/abandon/replay, terminal
  no-op, witness issuance/consumption, or recovery audit;
- remote CAS, remote ref, real publication, network, SSH, Git, Lean, worker,
  registered run, canonical diagnostic, execution, model-quality, safety, GPU,
  or later-stage authority.

An untrusted caller chooses the parent, nonce, State, expected version and raw
payload. Passing real or secret bytes causes those bytes to be written to that
location. “Synthetic” is a model label, not a type-enforced data provenance or
confidentiality policy.

## 12. Finite Phase-2b2d acceptance matrix

Before a result commit, the explicit support, frozen four-file M2b profile,
and default collection must pass with zero failures/errors. The frozen profile
has zero skips/xfails. Required finite families are:

1. exact module imports, ordered production/support `__all__`, one exception,
   one 63-field frozen/slotted record, one positional-only function, raw and
   resolved annotations, prereg/source/support/result anchors, collector
   uniqueness, and prereg-tree future-file absence/zero import;
2. exact parent and nonce type/grammar boundaries, UTF-8 N-1/N/N+1 lengths,
   surrogates/control/NUL, relative/dot/dot-dot/trailing-normalization, Windows
   UNC/device/current-drive-rooted forms, explicit drive qualification,
   hostile PathLike/coercion objects, deterministic 65-byte basename and
   native lexical join without resolve/realpath/abspath/casefold;
3. exact reconstruction and structural-invalid cross precedence for State,
   expected hash, proposal and every frozen constant; bool/subclass/bytearray/
   memoryview rejection; N-1/N/N+1 payload bounds; maximum-generation stale,
   identical and changed cases; no physical I/O before valid changed gating;
4. all three outcome rows and every field; the four payload cases—empty, A, B,
   and maximum payload; conflict/existing-identical under a nonexistent
   physical parent with every physical operation seam forbidden while lexical
   `isabs`/`normpath`/`join` seams remain expected; changed branch with the
   fixed directive only and no alternate semantics;
5. parent missing/error/malformed/non-directory/symlink/Windows-reparse and
   every D component bool/drift; absent, malformed, negative, and bool
   `st_file_attributes`; exact two no-follow parent observations on success;
   no ancestor walk or enumeration;
6. exact open flags/mode, O_EXCL collision with zero inspection/deletion/retry,
   open error/invalid descriptor, F0 regular/non-reparse/zero, every metadata
   error/type/bool including descriptor/path `st_file_attributes`, and at most
   one create;
7. empty, one byte, chunk-1/chunk/chunk+1 and maximum real writes/readbacks;
   positive partial writes complete; zero/negative/bool/over-report/error and
   call-bound failures; exact seek return; short/early-EOF/nonbytes/overlong/
   growth/read-error/raw-mismatch/digest-only-mutant rejection;
8. F0/F1 identity and size, exact F1=F2 stability, close exactly once on
   success or post-create error, close return/error behavior, post-close path
   regular/reparse `(dev, ino, size)` binding, Windows close-finalized mtime
   acceptance, final parent equality, and endpoint ordering before Result
   exposure;
9. every post-create failure leaves existing/staged bytes non-destructively
   untouched by this module; no unlink or cleanup; same nonce collides on the
   next call, distinct nonce can succeed; no result/Transition is exposed on
   failure and no hidden State changes;
10. exact OPERATION domain, tags, nullable/raw framing, preimage lengths,
    maxima and four goldens; mutation/omission of parent, nonce, transition,
    outcome, stage payload or counts changes or invalidates the commitment;
    raw payload rather than digest-only identity;
11. normal construction and `dataclasses.replace` reject every forged field;
    bypass-mutated State/Transition reject; constructor/validator performs no
    stat/open/read/write/close and records remain forgeable non-attestations;
12. exact resource arithmetic, invalid constants rejected before fake-CAS or
    I/O, streamed hashing, memoryview writes, no full preimage/file/payload
    copy, exact read buffer peak, and linear runtime;
13. AST/runtime sentinels forbid package-private imports, receipt/claim/final
    paths, mkdir/link/rename/replace/unlink/fsync/flush, retry/random/time,
    directory enumeration, hidden maps/history, marker/recovery/epoch/witness,
    network/Git/Lean/worker/scanner/writer/registered-run capability; and
14. all real filesystem fixtures are test-created under `tmp_path`; tests
    remove their disposable parent only through pytest lifecycle, not through
    production code; no repository-tree, `runs/`, exposure-marker, rerun
    registry, or registered-task delta; unchanged default-deny registry;
    Windows zero-skip frozen profile and green Ubuntu CI.

Independent adversarial review must also kill these explicit mutants:

- caller nonce ignored, truncated, case-folded, randomized, PID/time-derived,
  or omitted from the basename/commitment;
- `O_EXCL`, no-follow observation, raw readback, EOF probe, F1/F2/path/parent
  binding, or close omitted/reordered;
- digest equality substituted for raw chunk equality;
- conflict or identical branches touching the physical parent;
- failure exposing the candidate after State or Transition;
- existing collision opened/read/deleted or silently retried;
- short write treated as terminal success, short read silently accepted, or
  zero write looped forever;
- success stage deleted, renamed, linked, promoted, or relabeled durable;
- hidden store/registry/history, manifest/receipt binding, recovery marker,
  epoch/witness, or real/canonical publication added.

## 13. Stop rule

Commit, push, and green CI of this reviewed amendment license only the exact
Phase-2b2d source, support matrix, collector import, and source/support anchor
wiring on local Windows CPU. Until that gate is green, both implementation
paths must remain absent.

A later implementation commit must be committed, pushed, and green in hosted
CI. A separate execution record must then freeze the exact Windows zero-skip
profile, implementation blobs, review disposition, and Ubuntu CI evidence; its
commit must also be pushed and green. Only all of those conditions complete
Phase 2b2d and license Phase-2b2e preregistration.

Phase-2b2e implementation, Phase 2b2f, Phase 2c reservation/preflight,
registered runs, canonical diagnostic, M2c, U'0.5, U'2--U'5, SSH/network,
Lean, workers, GPU construction, real/canonical publication, cleanup,
marker/recovery, epoch/witness issuance, and integrated manifest writing remain
barred in either case.
