# U'1 evidence milestone 2b phase 2b1 local attempt-manifest amendment

Date: 2026-07-11

Status: PREREGISTERED READ-ONLY SYNTHETIC SCHEMA/CHAIN SLICE; NO WRITE, CLAIM,
REMOTE, CAS, RECOVERY ORACLE, ARTIFACT OBSERVATION, WORKER, SCIENTIFIC VERDICT,
CANONICAL-RUN, RERUN, LATER-STAGE, NETWORK, OR GPU AUTHORITY.

## 1. Purpose and adversarially reduced boundary

The parent M2b Sections 12--13 freeze attempt visibility and retention in
principle. The first Phase-2b draft combined local parsing, file staging,
fake-remote CAS, acknowledgement loss, causal recovery, epoch ownership, and a
future ordering capability. Independent adversarial review rejected that draft:
the public records were underdetermined, exclusive local final files made CAS
retry and pre-start recovery collide, recovery cause was caller-forgeable, and
epoch release and witness issuance were not uniquely specified.

This amendment therefore splits the work before implementation:

1. **Phase 2b1 (this amendment):** an exact, read-only parser, bounded local
   chain inspector, and terminal-chain verifier for synthetic pre-artifact
   attempt manifests;
2. **Phase 2b2 (future amendment):** content-addressed per-operation staging,
   immutable fake claim inventory, fake-remote CAS, acknowledgement loss,
   internal causal markers, exclusive recovery epochs, and synthetic witness
   issuance; and
3. **Phase 2c (future amendment):** reservation writer and preflight.

Phase 2b1 writes nothing and asserts no filesystem artifact absence. It checks
only that supplied event bytes encode the frozen all-absent profile. This
removes the CAS/retry, TOCTOU, cause-provenance, and epoch problems from the
current implementation surface without weakening the final M2b objective.

This amendment explicitly supersedes the parent Section-12 grammar only in one
respect: once a recovery event has appeared, a later `attempt_finished` is
invalid. That recovery-sticky rule implements the parent's no-resume
requirement. Every other parent requirement remains in force.

## 2. New paths, collection, anchors, and imports

The Phase-2b1 implementation paths are exactly:

```text
lean_rgc/evals/uprime_rpc_attempt_manifest.py
tests/uprime_rpc_attempt_manifest_cases.py
```

The support filename is outside pytest's default `test_*.py`/`*_test.py`
patterns. It defines an exact `__all__` containing only its `test_*` functions.
The anchored collector `tests/test_uprime_rpc_ledger.py` imports it once with:

```python
from uprime_rpc_attempt_manifest_cases import *  # noqa: F403
```

The frozen four-file M2b command remains unchanged. Before the Phase-2b1 result
commit, the amendment, source, and support path must all be members of
`ANCHOR_PATHS` and the anchor-membership test. `pytest --collect-only -q` must
show each support test exactly once in both the frozen four-file profile and
default repository collection; the support file itself must not be collected
as a second module.

The source import allowlist is Python standard-library modules `dataclasses`,
`datetime`, `hashlib`, `os`, `re`, and `stat`, plus only
`canonical_json_bytes` and `parse_canonical_json_bytes` from
`lean_rgc.evals.uprime_rpc_ledger`. It may not import Phase-1 semantics, the
contract oracle, bundle reservation module, production litmus, rerun registry,
subprocess, socket, HTTP, Git, Lean, worker, scanner/archive, registered-run,
or formal entrypoint code.

## 3. Exact public surface

All records below use `@dataclass(frozen=True, slots=True)` in the displayed
field order. Tuple annotations mean immutable tuples, never lists. The only
public exception is `AttemptManifestV10Error(ValueError)`.

`PublicClaimReceiptV10` has the exact 13 fields:

```python
schema_version: str
candidate_commit: str
license_commit: str
license_id: str
remote_url: str
remote_branch_ref: str
remote_claim_ref: str
remote_claim_oid: str
registry_blob_oid: str
registry_sha256: str
candidate_tree_oid: str
input_manifest_sha256: str
claimed_at_utc: str
```

`AttemptManifestEventV10` has the exact 29 fields:

```python
schema_version: str
event_type: str
event_index: int
created_at_utc: str
license_id: str
candidate_commit: str
license_commit: str
remote_claim_ref: str
claim_receipt: PublicClaimReceiptV10
claim_receipt_sha256: str
prior_event_sha256: str | None
reservation_exists: bool
ledger_exists: bool
report_exists: bool
reservation_sha256: str | None
reservation_bytes: int | None
ledger_sha256: str | None
ledger_bytes: int | None
report_sha256: str | None
report_bytes: int | None
ledger_inspection_status: str
ledger_sequence_status: str | None
verifier_status: str
scanner_status: str
scanner_rule_ids: tuple[str, ...]
verdict: str | None
failure_codes: tuple[str, ...]
full_ledger_published: bool
terminal_event: bool
```

`AttemptManifestEventFileV10` has exactly:

```python
repository_path: str
event_sha256: str
event_bytes: bytes
event: AttemptManifestEventV10
```

`AttemptManifestChainInspectionV10` has exactly:

```python
inspector_schema_version: str
inspector_scope: str
origin_status: str
license_id: str
chain_state: str
event_files: tuple[AttemptManifestEventFileV10, ...]
event_count: int
first_event_sha256: str | None
last_event_index: int | None
last_event_sha256: str | None
last_event_type: str | None
terminal_event: bool
recorded_verdict: str | None
next_event_index: int | None
claim_receipt: PublicClaimReceiptV10 | None
claim_receipt_sha256: str | None
```

`AttemptManifestChainAttestationV10` has exactly 33 fields:

```python
verifier_schema_version: str
verifier_scope: str
origin_status: str
license_id: str
candidate_commit: str
license_commit: str
remote_claim_ref: str
claim_receipt_sha256: str
event_count: int
first_event_sha256: str
last_event_index: int
last_event_sha256: str
chain_state: str
terminal_event: bool
last_event_type: str
recorded_verdict: str | None
failure_codes: tuple[str, ...]
preartifact_profile: bool
artifact_observation: str
remote_claim_authentication: str
git_object_authentication: str
real_remote_publication: str
claim_once_authentication: str
reservation_token_verification: str
artifact_binding: str
verifier_binding: str
scanner_binding: str
privacy_scan: str
archive_verification: str
authority_scope: str
canonical_run_authority: bool
licenses_execution: bool
licenses_later_stage: bool
```

The only public functions, with positional-only arguments and exact returns,
are:

```python
encode_attempt_manifest_event_v1_0(
    event: AttemptManifestEventV10, /
) -> bytes

parse_attempt_manifest_event_file_v1_0(
    repository_path: str, raw: bytes, /
) -> AttemptManifestEventFileV10

inspect_local_attempt_manifest_chain_v1_0(
    root: str | os.PathLike[str], license_id: str, /
) -> AttemptManifestChainInspectionV10

verify_local_attempt_manifest_terminal_chain_v1_0(
    root: str | os.PathLike[str], license_id: str, /
) -> AttemptManifestChainAttestationV10
```

`__all__` is exactly the exception, the five records, and the four functions.
Every type, encoding, path, I/O, schema, chain, grammar, or terminality
rejection raises `AttemptManifestV10Error` and returns no partial object.
There are no conflict, blocked, retry, or no-op result statuses in Phase 2b1.
The receipt and event constructors perform their complete field/type/domain
validation immediately; `encode_*` repeats validation rather than trusting a
caller-constructed object. The other four records are constructed only after
the same internal validators have succeeded. Direct construction of an output
record is not evidence of inspection and carries no authority.

## 4. Receipt validation and exact identity

Receipt schema is
`lean-rgc-uprime-u1-claim-receipt-public-v1.0`. The fixed remote URL is
`https://github.com/abhorrence-of-Gods/lean-rgc-automation-stack.git`, the fixed
branch is `refs/heads/codex/uprime-odlrq-plan`, and the claim ref is
`refs/tags/uprime-u1-attempts/<license_id>`.

The validator requires exact field types and:

- lowercase hexadecimal C/L and all Git OIDs of length 40;
- lowercase hexadecimal license ID of length 64 equal to
  `lower_hex(SHA256(b"lean-rgc-uprime-u1-attempt-v1\0" +
  C.encode("ascii")))`;
- `remote_claim_oid == L` and the exact URL, branch, and derived claim ref;
- uppercase hexadecimal registry/input-manifest digests of length 64; and
- real UTC timestamps in exact `YYYY-MM-DDTHH:MM:SS.ffffffZ` form.

Receipt canonical bytes are the compact strict canonical JSON mapping in the
displayed 13-field schema, without LF. `claim_receipt_sha256` is uppercase
SHA-256 of those bytes. The event repeats C/L/license/ref exactly; all copies
must agree. This is internal identity validation only. No remote ref or Git
object is contacted or authenticated.

## 5. Exact event encoding, path, and bounds

Manifest schema is `lean-rgc-uprime-u1-attempt-manifest-v1.0`. Exact event
bytes are:

```text
canonical_json_bytes(exact_29_field_mapping) + b"\n"
```

The strict algebra, depth/member/string limits, duplicate-key rejection, and
integer rules are those of `lean-rgc-strict-json-int-v1`. Integer fields are
signed-64 and booleans are never integers. Event bytes have exactly one LF and
an inclusive maximum of 1,048,576 bytes. BOM, CRLF, missing/extra LF,
noncanonical spacing or key order, duplicate keys at any depth, invalid UTF-8,
floats/nonfinite values, surrogates, trailing objects, and oversize inputs are
rejected. `raw` must have exact type `bytes`; `repository_path` exact type
`str`.

The repository path is exactly:

```text
docs/experiments/artifacts/uprime_u1_rpc_attempts/<license_id>/<NNNN>.json
```

`event_index` is an integer in 1..9999. `NNNN` is exactly four ASCII digits
with zero padding. Slash is the only repository separator. Alternate case,
Unicode digits, `0000`, unpadded/five-digit indices, backslash, absolute, empty,
`.`/`..`, extra components, and license/index mismatch are rejected.

`event_sha256` is uppercase SHA-256 of exact event bytes including LF. Parsing
must decode through the strict parser, construct the exact records, re-encode,
and require byte equality. It never accepts a semantically equivalent rewrite.
The exact 29-field wire projection recursively emits the displayed 13-field
receipt mapping and converts `scanner_rule_ids` and `failure_codes` from tuples
to JSON arrays without reordering. Parsing performs the inverse list-to-tuple
conversion before record construction. Dataclass objects and Python tuples are
never passed directly to the strict JSON primitive.

## 6. Frozen pre-artifact profile and failure registry

Every event accepted in Phase 2b1 has exactly:

```text
reservation_exists = ledger_exists = report_exists = false
reservation_sha256 = reservation_bytes = null
ledger_sha256 = ledger_bytes = null
report_sha256 = report_bytes = null
ledger_inspection_status = absent
ledger_sequence_status = null
verifier_status = not_run
scanner_status = not_run
scanner_rule_ids = []
full_ledger_published = false
```

This is a wire-profile assertion, not an observation of sibling files. The
seven nonempty subsets of `{reservation, ledger, report}` are rejected; the
all-absent subset is the only eligible profile. Unknown/unavailable artifact
truth cannot be represented by this slice and must not be encoded as false.

`failure_codes` is an ASCII-lexically sorted unique tuple drawn only from the
parent union below:

```text
ARCHIVE_ERROR
CLAIM_STARTED_MANIFEST_ERROR
CLEANUP_ERROR
EOF_BEFORE_EXPECTED_RESPONSE
FINAL_MANIFEST_ERROR
INVALID_UTF8_STDOUT
LEDGER_APPEND_ERROR
LEDGER_CLOSURE_ERROR
LEDGER_FSYNC_ERROR
LEDGER_OPEN_ERROR
LEDGER_VERIFY_ERROR
NON_JSON_STDOUT
NON_OBJECT_STDOUT
OTHER_ATTEMPT_ERROR
OTHER_HARNESS_ERROR
POWER_LOSS
PRIVACY_DENIED
PROCESS_EXIT_BEFORE_REQUEST
PUBLICATION_ERROR
READER_ERROR
READER_NOT_QUIESCED
REPORT_FSYNC_ERROR
REPORT_HARDLINK_ERROR
REPORT_REVALIDATION_ERROR
REPORT_TEMP_CREATE_ERROR
REPORT_WRITE_ERROR
REQUEST_TIMEOUT
REQUEST_VALIDATION_ERROR
REQUEST_WRITE_ERROR
RESERVATION_CREATE_ERROR
RESERVATION_FSYNC_ERROR
RESERVATION_WRITE_ERROR
RESPONSE_DUPLICATE
RESPONSE_LATE
RESPONSE_UNSOLICITED
SCANNER_ERROR
SHUTDOWN_FINALIZATION_ERROR
STDIN_UNAVAILABLE
TRANSPORT_OVERFLOW
WORKER_START_ERROR
WORKER_TIMEOUT
```

Because scanner and artifact publication are `not_run`/false in this profile,
`SCANNER_ERROR`, `PRIVACY_DENIED`, `ARCHIVE_ERROR`, and `PUBLICATION_ERROR` are
rejected. `CLAIM_STARTED_MANIFEST_ERROR`, `FINAL_MANIFEST_ERROR`, and
`POWER_LOSS` occur only on recovery events. Phase 2b1 checks these structural
contexts but does not authenticate causal provenance; in particular, a parsed
`POWER_LOSS` string is not evidence that power loss occurred. Phase 2b2 must
bind any such code to a non-caller-supplied internal marker.

## 7. Exact chain grammar and states

The Phase-2b1 state machine is:

```text
START -> claim_started(nonterminal) -> ACTIVE
START -> recovery(terminal) -> TERMINAL
ACTIVE -> attempt_finished(terminal) -> TERMINAL
ACTIVE -> recovery(nonterminal) -> RECOVERY_ONLY
ACTIVE -> recovery(terminal) -> TERMINAL
RECOVERY_ONLY -> recovery(nonterminal)* -> recovery(terminal) -> TERMINAL
```

Once `RECOVERY_ONLY` is entered, `attempt_finished` is forbidden. No event
follows a terminal event. A chain is contiguous from index 1; prior digest is
null exactly at index 1 and otherwise equals the immediately preceding exact
event-file digest. Every event repeats the first receipt and identity exactly.

`claim_started` is exactly index 1, nonterminal, null verdict, and empty failure
codes. A recovery has a nonempty structurally valid failure-code tuple and null
verdict; it may be nonterminal or terminal. A raw `attempt_finished` is terminal,
occurs directly after `claim_started` before recovery, has verdict
`HARNESS_ERROR`, and has nonempty failure codes excluding the three
recovery-only codes. `U1_DIAGNOSTIC_CLEAR` and `U1_DIAGNOSTIC_BLOCKED` are
impossible in the pre-artifact profile and rejected.

Every event `created_at_utc` is a real instant in exact
`YYYY-MM-DDTHH:MM:SS.ffffffZ` form. Equality is allowed. Because all values are
fixed-width UTC, chain order is ASCII order after individual real-date
validation; invalid calendar dates and backwards time reject.

Event timestamps are nondecreasing in chain order. Local verification has no
external expected receipt or anchored digest. It therefore rejects a mid-chain
receipt/identity drift and any fully rehashed rewrite that breaks a frozen
identity or grammar relation, but a self-consistent whole-chain rewrite that
also changes its path and all derived hashes remains structurally valid. The
negative origin/authentication fields are mandatory precisely because this
read-only slice cannot distinguish that rewrite from an originally published
chain.

A nonterminal event at index 9999 is validly encoded but produces
`chain_state=valid_nonterminal_index_exhausted` and `next_event_index=null`; it
cannot pass the terminal verifier. Other inspection states are `missing`,
`valid_nonterminal`, and `valid_terminal`.

For `missing`, the exact inspection suffix is: empty `event_files`, count zero,
all first/last/type/verdict/receipt fields null, `terminal_event=false`, and
`next_event_index=1`. For a nonempty valid chain, receipt fields come from its
first event; `next_event_index` is current index plus one only for
`valid_nonterminal`. Invalid bytes, namespace, identity, hash, or grammar raise
instead of producing an `invalid` inspection object.

All inspections fix:

```text
inspector_schema_version = lean-rgc-uprime-u1-local-attempt-chain-inspector-v0.1
inspector_scope = local_preartifact_chain_structure_only
origin_status = unknown_may_be_synthetic
```

The remaining inspection mapping is exact: `license_id` is the validated input;
`event_files` is numeric-index order and `event_count=len(event_files)`; first
and last digests are the corresponding tuple endpoints; last index, type,
terminal flag, and recorded verdict are the last event's exact values; receipt
and receipt digest are the first event's exact values; and `next_event_index`
follows the state rule above. No field is a chain union or caller override.

## 8. Bounded local read protocol

`root` is a caller-owned synthetic sandbox prefix. `os.fspath(root)` must have
exact type `str`, be nonempty, and be lexically absolute. Without resolving or
normalizing the prefix, the inspector
appends the repository components from Section 5 using host separators. It
opens no registered repository path by itself. Prefix symlinks/junctions are
outside the attestation; the final license directory and event entries must
not be symlinks or reparse points.

The exact reparse predicate is `stat.S_ISLNK(st_mode)` or, when both the result
field and platform constant exist,
`bool(st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)`. The final
directory must satisfy `stat.S_ISDIR`; every event entry must satisfy
`stat.S_ISREG`.

A missing final license directory or an empty valid directory yields the
`missing` state. Only ENOENT/`FileNotFoundError` means missing. Permission,
identity, stat, scan, read, seek, or close failure raises. If the directory
exists, inspection performs this exact bounded snapshot:

1. no-follow stat the final license directory, require a real non-reparse
   directory, and capture
   `D0=(st_dev, st_ino, st_mode, reparse_bit, st_ctime_ns, st_mtime_ns)`;
2. `os.scandir` once, require at most 9,999 entries, exact ASCII filenames,
   only regular files, no subdirectories/symlinks/reparse points, and sort
   names by ASCII;
3. capture a no-follow metadata tuple
   `S0=(st_dev, st_ino, st_mode, reparse_bit, st_ctime_ns, st_size,
   st_mtime_ns)` for every entry;
4. require each size in 1..1,048,576 and aggregate size at most 67,108,864
   bytes before payload retention;
5. open each file once read-only/binary, capture descriptor metadata, perform
   two bounded passes from offset zero on that descriptor, retain pass-one
   bytes, and require `bind(S0)=bind(F0)=bind(F1)=bind(F2)`, equal counts, and
   equal SHA-256 values, where each `F` is an `os.fstat` before/pass-one/
   pass-two tuple and `bind` drops only the path-only reparse bit;
6. close each descriptor exactly once and require a no-follow post-close path
   stat `S1` with exact `S0=S1`;
7. `os.scandir` the directory a second time and require the same sorted names
   and exact `S0` tuples, repeating regular/non-reparse checks; and
8. no-follow stat the final license directory again, require exact `D0`
   equality plus real-directory/non-reparse checks, then parse and validate
   retained files in numeric order.

`O_BINARY` is added where available. A zero read before the declared size,
growth beyond the bound, same-size retained-byte mutation between passes,
directory mutation, replacement, disappearance, or final link/reparse entry is
rejected. The step-8 directory stat is the observation point. No claim covers
mutation after it and before Python returns, nor a change hidden by all frozen
metadata and equal two-pass digests.

Each pass loops over and accepts positive partial reads until the declared size
is reached. Zero bytes before that point is early EOF and rejects. After the
declared size, the pass performs exactly one one-byte read and requires EOF;
nonempty output is growth and rejects. Each pass uses an absolute seek to zero.
After successful open, close is attempted exactly once on every exit; a close
failure rejects even when another read/seek/stat failure is already pending.

The only mutable test seams are module-private constants
`_MAX_EVENT_BYTES=1_048_576`, `_MAX_EVENT_COUNT=9_999`, and
`_MAX_CHAIN_BYTES=67_108_864`, plus private helpers
`_read_bounded_pass(fd, expected_size)` and
`_classify_chain_suffix(event_index, terminal_event)`. Production validation
checks the literal event-index domain 1..9999 independently of the injected
resource bounds. Full inspection calls both helpers. Tests may monkeypatch the
three constants and module-local OS call bindings; no public caller can supply
a bound or alternate reader.

The inspector examines only the selected seeded license directory. It does not
enumerate a remote claim inventory and cannot detect an omitted claim or an
orphan directory under another license ID. That selective-coverage problem is
reserved for Phase 2b2 and may not be hidden by the function name or result.

## 9. Terminal attestation and negative authority

`verify_local_attempt_manifest_terminal_chain_v1_0` independently performs
the Section-8 inspection and rejects any state other than `valid_terminal`.
Its fixed values are:

```text
verifier_schema_version = lean-rgc-uprime-u1-local-attempt-chain-verifier-v0.1
verifier_scope = local_preartifact_chain_structure_only
origin_status = unknown_may_be_synthetic
chain_state = valid_terminal
terminal_event = true
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

The remaining fields are derived from the validated chain. No output field is
named bare `verified`, `published`, `durable`, `CLEAR`, or `claim_valid`.
The exact mapping is the terminal inspection mapping from Section 7:
candidate/license commits and remote ref come from the first receipt; first and
last fields come from the corresponding event-file endpoints; recorded verdict
and `failure_codes` are the terminal event's exact values. `failure_codes` is
not a union over earlier recovery events.

## 10. Finite Phase-2b1 acceptance matrix

Before a result commit, the frozen four-file profile must collect all new tests
and pass with zero failures, errors, skips, or xfails. The exact finite families
are:

1. golden claim-start/nonterminal, direct attempt-finished terminal,
   claim-start plus terminal recovery, nonterminal recovery plus terminal
   recovery, and pre-start terminal recovery fixtures;
2. one missing, one wrong primitive type, and bool-as-int mutation where
   applicable for each of 29 event fields and 13 nested receipt fields; one
   extra key at the event-object level and one at the nested receipt-object
   level; exact ordered
   4/16/33-field output surfaces, frozen tuples, and frozen/slots records;
   exact inspector/verifier constants and every first/last/terminal mapping;
3. BOM, CRLF, missing/extra LF, spacing/key-order rewrite, duplicate top/nested
   keys, invalid UTF-8, float/NaN/infinity, surrogate, trailing object,
   injected reader bound N-1/N/N+1, and sparse public max+1 pre-read rejection;
4. LF-included event hash versus LF-free receipt hash, lowercase/wrong digest,
   prior mismatch, fully rehashed identity/grammar tamper, receipt/C/L/ref
   mid-chain drift, raw cross-license transplant, and path/directory/index
   mismatch; plus one fully self-consistent whole-chain rewrite that remains
   structurally accepted while every origin/authentication field stays
   negative;
   same-type invalid event/receipt UTC values including invalid month and
   backwards chain time, malformed or wrong-case/length Git OIDs and SHA
   fields, and wrong URL/branch/ref with all dependent canonical bytes and
   receipt digests recomputed;
5. `0000`, unpadded, Unicode digit, `10000`, alternate case, backslash,
   absolute/dot/empty/extra path, gap, reorder, unexpected entry,
   nonterminal index 9999, and terminal-plus-tail;
6. every edge of the six-line state machine plus claim-start index/verdict/code,
   recovery stickiness, terminality, verdict, failure-code membership/order/
   duplicate/context, and CLEAR/BLOCKED rejection;
7. the all-absent profile accepted and each of the seven nonempty artifact
   existence subsets rejected, with every associated hash/byte/status nullity
   changed individually;
8. missing/empty directory, two-pass success, short/zero/oversize read,
   metadata drift, same-size mutation, path replacement/disappearance,
   directory entry or final-directory identity mutation, permission/stat/seek/
   close failure, symlink/reparse sentinels, count 10,000, and aggregate-bound
   rejection; the fixed injected call table covers both directory scans and
   directory stats, every entry stat, open, both seeks, every descriptor stat,
   each pass read, close, and post-close path stat; positive partial reads
   succeed while early EOF and the extra-byte probe fail;
9. exact terminal attestation and all negative-authority constants, plus proof
   that local inspection does not authenticate POWER_LOSS, artifact absence,
   remote inventory completeness, or origin; and
10. exact signatures/`__all__`/import AST, production raising sentinels,
    collector node-ID uniqueness, and byte-identical default-deny registry.

The mechanically protected registry path is
`docs/experiments/uprime_odlrq_u1_rerun_license_registry.json`; its bytes must
not change. Phase-2b1 actions create or modify no exposure marker and no file
under `runs/`. The complete allowed Phase-2b1 delta is limited to this
amendment, the source/support/collector, litmus anchor, anchor-membership test,
and the later Phase-2b1 execution record; the result record must enumerate the
actual subset.

Boundary tests assert all three production defaults, then use injected small
private resource bounds and deterministic in-memory reader/stat doubles. The
literal index-9999 parser boundary and
`_classify_chain_suffix(9999, False)` are tested separately from a reduced
resource-count inspection; tests do not allocate a valid 64 MiB tree or
9,999-event chain. There are no sleeps, threads, races, writes, or fault-oracle schedules in
Phase 2b1. All real files are test-created under `tmp_path`. Tests contact no
network, Git remote, Lean, registered experiment path, worker, or GPU.

## 11. Phase-2b2 obligations preserved, not silently deferred

Before any Phase-2b2 code, a separate amendment must uniquely freeze:

- exact public records, constructors, typed returns, bounds, and fake hash
  byte formulas;
- per-operation content-addressed or nonce-separated staging so an exclusive
  local file cannot block explicit retry or collide with pre-start recovery;
- immutable seeded claim inventory and an explicit statement that omissions
  are unauthenticated without a real remote inventory;
- fake CAS outcomes for acknowledged apply, conflict, acknowledgement loss,
  confirmation failure, existing-identical bytes, and wrong delta;
- a non-caller-supplied, one-shot internal fault-marker journal and exact
  failure-code mapping; ordinary stale-token conflict must create no marker;
- publisher/recovery mutual exclusion, epoch owner/nonce, release, abandonment,
  replay, terminal no-op, retry, and permanent-block transitions;
- same-instance private witness issuer identity, issuance registry, and
  single-use validation; `init=False` or a dataclass type alone is insufficient;
- exact artifact paths and two-observation no-follow semantics, explicitly
  bounded against filesystem TOCTOU; and
- recovery/audit result labels that cannot be relabeled as real publication,
  durability, power loss, claim completeness, or execution authority.

No Phase-2b1 result may be used as evidence that these obligations are met.

## 12. Stop rule

Passing Phase 2b1 proves only exact pre-artifact event-byte parsing, internal
receipt/path/hash identity, bounded local chain structure, the recovery-sticky
grammar, and a terminal structural attestation over one caller-selected
synthetic directory.

It does not prove artifact absence, causal failure, power loss, claim inventory
coverage, a real claim/ref/object, Git branch publication, CAS, local or remote
durability, a recovery epoch, a worker ordering capability, reservation token,
ledger/report/verifier/scanner/archive binding, scientific verdict, or origin.

Commit and push of this amendment license only the exact local Windows-CPU
Phase-2b1 implementation. A later committed Phase-2b1 result with the frozen
zero-skip Windows profile and green Ubuntu CI licenses only Phase-2b2
preregistration. It does not license Phase-2b2 implementation before that
separate amendment is committed and pushed. Reservation creation, worker/RPC execution,
real claim/network use, canonical diagnostic, U'0.5, U'2--U'5, publication,
remote GPU construction, and contact with the GPU host remain barred. The
rerun registry stays byte-identical with `default_allow=false` and no licenses;
no exposure-class record is changed.
