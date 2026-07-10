# U'1 evidence milestone 2b: full parsed-semantic ledger preregistration

Status: FORWARD-ONLY EVIDENCE SUBSTRATE; NO CANONICAL RUN OR POSITIVE
RERUN IS LICENSED.

Git-freeze date: 2026-07-11 (Asia/Tokyo).

## 1. Claim boundary

M2b adds an append-only ledger that retains the complete parsed objects needed
to recompute U'1 object-level contracts. It is a **full parsed-semantic
request/response ledger**, not a wire transcript.

`Full` means every field of every accepted Python request object, every stdout
JSON object accepted as a response, and the raw observations of the local B4
cache probe are retained without compaction, redaction, or truncation. It does
not preserve or prove exact stdin/stdout octets, whitespace, key order, escape
spelling, line endings, duplicate-key spelling, invalid UTF-8 bytes,
blank/non-JSON/non-object stdout, or delivery of a request intent to Lean. The
header states:

```text
evidence_scope = parsed_json_objects_and_local_probe_not_raw_wire_octets
wire_exact = false
```

The ledger permits independent recomputation of all 11 object/local-probe
contracts from recorded raw values. X0 is mechanically reproduced from
harness-observed closure telemetry; the chain makes that telemetry immutable
after anchoring but does not independently observe the OS process or pipes.
A chain detects byte corruption, deletion, and reordering once its head/file
digest is externally anchored. It is not authentication against an owner who
rewrites and rehashes the entire bundle.

## 2. Frozen frame and local-probe manifests

The expected request/response labels, in order, are:

```text
load
primary_init
primary_split
primary_split_replay
primary_tail_close
primary_tail_close_replay
primary_head_close
primary_head_close_replay
zero_init
zero_split
zero_split_replay
zero_child_close
zero_child_close_replay
side_init
side_effect_close
side_effect_close_replay
burn_init
burn
reset_init
reset
reset_replay
status
shutdown
```

Frame indices are one-based. Request id `k` is
`uprime-<two-digit-k>-<label>`. The manifest digest is SHA-256 of the compact
canonical JSON label array without LF:

```text
03A58EA8661BAB7423D5B7CF86DF66F97134DCBAEC976744051310E437BC394E
```

Record 1 is a `local_probe` for B4. It retains, without `passed` or `checks`
booleans, the five payloads (`task_fallback`, `explicit_zero`,
`explicit_nonzero`, `omitted_default`, `explicit_default`), `key_kwargs`, all
five resolved values, both full cache keys and key-field objects, and the exact
Git blob identities of the code that produced them. The independent verifier
derives B4 from these raw observations and does not call production probe code.

The payloads use exactly the synthetic task `{task_id:"cache",
statement:"True", imports:["Lean"]}` and action tactic `trivial`:

```text
task_fallback      task max=731,    action max omitted
explicit_zero      task max=731,    action max=0
explicit_nonzero   task max=731,    action max=123456
omitted_default    task max omitted, action max omitted
explicit_default   task max=200000, action max omitted
```

`key_kwargs` has exactly `lean_version="uprime-cache-probe"`,
`workdir_fingerprint_value="uprime-cache-probe"`, `import_mode="preserve"`,
`trace_state=false`, and `lane="kernel_rpc"`. B4 independently checks resolved
strings `731`, `0`, `123456`, and omitted-default `200000`, equality of omitted
and explicit-default keys, and both key-field `max_heartbeats` values equal to
`"200000"`.

The nominal full sequence has 49 records: header, local probe, 23 request
intents, 23 parsed responses, and closure. Extra parsed response objects are
also retained, so a sequence-complete anomalous ledger may exceed 49 records
and must fail X0 or abort according to Section 9.

## 3. Strict canonical JSON and exact bounds

The canonicalizer id is `lean-rgc-strict-json-int-v1`. Its value algebra is
null, bool, signed 64-bit integer, UTF-8 string, array, and string-keyed object.
Floats, NaN/infinity, duplicate keys at any depth, invalid UTF-8, and
unencodable surrogates are rejected. Metadata objects have exact field sets.
Only the nested full RPC request/response objects and the observed
`omitted_fields`/`explicit_fields` objects may contain arbitrary keys within
this strict algebra; B4 payloads and key kwargs require deep equality to the
frozen inputs.

Canonical bytes use sorted keys, compact separators, `ensure_ascii=false`, and
no LF. Each JSONL record is exactly canonical bytes plus one LF; BOM, CRLF,
blank lines, trailing spaces, and bytes after closure are forbidden. UTC is
exactly `YYYY-MM-DDTHH:MM:SS.ffffffZ`. Monotonic clocks are nonnegative integer
nanoseconds from `time.monotonic_ns` and order only one process run.

All maxima are inclusive:

- ledger file: 134,217,728 bytes, including every LF;
- event line: 16,777,216 bytes, including LF;
- reserved closure line: 1,048,576 bytes, including LF;
- records: 1,024, including closure;
- report: 16,777,216 bytes; reservation: 1,048,576 bytes;
- nesting: 128 containers, where a root object/array has depth 1;
- members: 100,000 per individual object or array;
- decoded UTF-8 key or string: 8,388,608 bytes; and
- integer range: `[-2^63, 2^63-1]`, with bool never accepted as integer.

Before every non-closure append the writer requires
`current_bytes + event_line_bytes + 1,048,576 <= 134,217,728`, so a healthy
writer always retains closure capacity. It also requires
`current_record_count + 2 <= 1,024`, reserving one record slot for closure.
Closure must fit both its own line limit and the file limit. File and line
lengths are bounded before JSON allocation; depth/member/string checks
necessarily occur after bounded-line decoding. Primitive bound tests cover
limit-1, limit, and limit+1. Oversize is an error, never truncation.

## 4. Public claim receipt and bundle reservation

The positive path remains disabled. Its future public receipt projection has
schema `lean-rgc-uprime-u1-claim-receipt-public-v1.0` and exactly these fields:

```text
schema_version                 fixed string
candidate_commit               lowercase hex40 C
license_commit                 lowercase hex40 L
license_id                     lowercase hex64
remote_url                     fixed canonical HTTPS URL
remote_branch_ref              fixed full ref
remote_claim_ref               fixed tag ref derived from C
remote_claim_oid               lowercase hex40, equal to L
registry_blob_oid              lowercase hex40
registry_sha256                uppercase hex64
candidate_tree_oid             lowercase hex40
input_manifest_sha256          uppercase hex64
claimed_at_utc                 canonical UTC string
```

The fixed URL is
`https://github.com/abhorrence-of-Gods/lean-rgc-automation-stack.git`; the
branch is `refs/heads/codex/uprime-odlrq-plan`; the claim ref is
`refs/tags/uprime-u1-attempts/<deterministic license_id>`.

Its digest is uppercase SHA-256 of its canonical bytes without LF. Reservation,
header, report, and attempt manifest contain both this public object and its
digest; a digest alone is not accepted. Secrets are not part of the projection.

Bundle reservation schema is
`lean-rgc-uprime-rpc-bundle-reservation-v1.1`. For license anchor
`A=lowercase(L[0:12])`, canonical siblings are:

```text
runs/uprime_u1_rpc_20260710/rpc_diagnostic_A.json
runs/uprime_u1_rpc_20260710/rpc_diagnostic_A.responses.jsonl
runs/uprime_u1_rpc_20260710/rpc_diagnostic_A.json.reservation
```

The reservation has exactly these fields:

```text
schema_version                 fixed reservation schema
status                         LIVE_EVIDENCE_BUNDLE_RESERVED
anchor                         lowercase hex12 A
candidate_commit               lowercase hex40 C
license_commit                 lowercase hex40 L
license_id                     lowercase hex64
remote_claim_ref               fixed full tag ref
claim_receipt                  exact public receipt object
claim_receipt_sha256           uppercase hex64
registered_run_dir             runs/uprime_u1_rpc_20260710
report_artifact_name           canonical basename
ledger_artifact_name           canonical basename
reservation_artifact_name      canonical basename
report_schema_version          lean-rgc-uprime-rpc-diagnostic-v1.2
ledger_schema_version          lean-rgc-uprime-rpc-parsed-ledger-v1.0
record_schema_version          lean-rgc-uprime-rpc-parsed-ledger-record-v1.0
rpc_protocol_version           lean-rgc-jsonl-rpc-v2
expected_frame_count           integer 23
expected_frame_manifest_sha256 frozen uppercase digest
reservation_token_sha256       uppercase hex64
reserved_at_utc                canonical UTC string
process_id                     positive signed-64 integer
```

`registered_run_dir` uses forward slashes and no leading/trailing slash.
Artifact-name fields are ASCII basenames matching their frozen anchor pattern;
slashes, backslashes, `.`/`..`, alternate normalization, and absolute paths are
invalid. Every duplicated C/L/anchor/license/ref/receipt/schema/manifest value
must be exactly equal across receipt, reservation, header, report, and
manifest.

The private reservation token is 32 random bytes conveyed in memory as 64
lowercase hexadecimal ASCII characters. The stored digest is SHA-256 of those
64 ASCII bytes, not of decoded token bytes. The raw token never appears in any
file. Reservation verification requires the caller-held token.
Reservation bytes are one compact canonical object plus LF; its SHA-256 covers
that LF.

## 5. Record envelope and chain formula

The ledger schema is `lean-rgc-uprime-rpc-parsed-ledger-v1.0`; every record
uses `lean-rgc-uprime-rpc-parsed-ledger-record-v1.0`. The only record types are
`header`, `local_probe`, `request_intent`, `parsed_response`, and `closure`.
Every line has exactly:

```text
schema_version                 fixed record schema
record_index                   zero-based signed-64 integer
record_type                    one frozen type string
previous_record_sha256         uppercase hex64
body                           exact metadata object for that type
record_sha256                  uppercase hex64
```

Let `B` be canonical header-body bytes without LF. Let `C_i` be canonical bytes
without LF of the exact core object containing `schema_version`,
`record_index`, `record_type`, `previous_record_sha256`, and `body`.

```text
DS_G = utf8("lean-rgc-uprime-u1-parsed-ledger-genesis-v1") || NUL
DS_R = utf8("lean-rgc-uprime-u1-parsed-ledger-record-v1")  || NUL

G   = SHA256(DS_G || u64be(len(B))   || B)
H_i = SHA256(DS_R || u64be(len(C_i)) || C_i)
```

Record 0 stores `previous_record_sha256=uppercase_hex(G)`. Every later record
stores the prior `H`; `record_sha256=uppercase_hex(H_i)`. Thus changing the
schema, index, type, previous digest, or body changes the chain.

## 6. Exact body schemas

### Header (record 0)

The exact fields are:

```text
ledger_schema_version          fixed ledger schema
canonicalizer_id               lean-rgc-strict-json-int-v1
hash_algorithm                 SHA-256
evidence_scope                 frozen scope string from Section 1
wire_exact                     false
reservation                    exact reservation object
reservation_sha256             uppercase hash of exact reservation bytes
expected_frame_labels          exact ordered 23-string array
created_at_utc                 canonical UTC string
```

### Local probe (record 1 on the nominal path)

The exact fields are:

```text
probe_id                       B4_cache_budget_semantics
payloads                       object with exactly the five named payloads
key_kwargs                     full strict object
resolved                       object with exactly the five named raw values
omitted_key                    full string
omitted_fields                 full strict object
explicit_key                   full string
explicit_fields                full strict object
source_blobs                   exact four-key object described below
observed_at_utc                canonical UTC string
```

`payloads` is deeply equal to the five literal objects in Section 2.
`key_kwargs` has exactly the five listed fields and literal values. `resolved`
has exactly the five case-name keys, each with type string or null. The two key
strings are unrestricted strict strings; their field objects are open strict
objects because they are observations rather than inputs.

`source_blobs` has exactly the keys `lean_rgc/audit_result_cache.py`,
`lean_rgc/schemas.py`, `lean_rgc/core/ids.py`, and
`lean_rgc/evals/uprime_rpc_litmus.py`. Each value has exactly `git_blob_oid`
(lowercase hex40) and `head_blob_sha256` (uppercase hex64).
No derived pass/fail boolean is stored.

### Request intent

The exact fields are:

```text
frame_index                    integer 1..23
frame_label                    frozen label at that index
expected_request_id            frozen id for that index
request                        complete strict JSON object
intent_at_utc                  canonical UTC string
intent_monotonic_ns            nonnegative signed-64 integer
durability_marker              durable_send_intent_before_stdin_write
```

The record is appended, flushed, and fsynced before `stdin.write` and
`stdin.flush`. It proves durable send intent, not OS write or Lean delivery.

### Parsed response

The exact fields are:

```text
arrival_index                  positive signed-64 integer
association                    active_frame | duplicate_for_frame |
                               late_for_frame | unsolicited
frame_index                    integer 1..23 or null
frame_label                    frozen string or null
expected_request_id            frozen string or null
response                       complete strict JSON object
received_at_utc                canonical UTC string
received_monotonic_ns          nonnegative signed-64 integer
```

Only `unsolicited` has all three frame fields null. Other associations require
all three. The response object's echoed id is never rewritten and is not used
for association. An id mismatch on the active frame is delivered and makes R0
false. Duplicate, late, and unsolicited objects are durably recorded but never
delivered to a request or inserted into a later frame's response map.

### Closure

The exact top-level fields are:

```text
sequence_status                complete | aborted
primary_reason_code            frozen code or null
reason_codes                   sorted unique frozen-code array
closed_at_utc                  canonical UTC string
preclosure_record_sha256       uppercase hex64
local_probe_count              nonnegative integer
request_intent_count           nonnegative integer
parsed_response_count          nonnegative integer
expected_frame_count           integer 23
expected_frame_manifest_sha256 frozen uppercase digest
observed_request_frame_indices record-order integer array
observed_response_frame_indices record-order integer array
missing_request_frame_indices  ascending unique integer array
missing_response_frame_indices ascending unique integer array
duplicate_request_frame_indices ascending unique integer array
duplicate_response_frame_indices ascending unique integer array
unsolicited_response_count     nonnegative integer
late_response_count            nonnegative integer
response_id_mismatch_count     nonnegative integer
invalid_utf8_stdout_count      nonnegative integer
non_json_stdout_count          nonnegative integer
non_object_stdout_count        nonnegative integer
stderr_line_count              nonnegative integer
transport_overflow             bool
process_returncode             signed-64 integer or null
process_quiesced               bool
stdout_reader_quiesced         bool
stderr_reader_quiesced         bool
writer_healthy                 true
shutdown_transport             exact object below
```

`shutdown_transport` has exactly the current X0 raw-input fields, with durations
converted to integer nanoseconds:

```text
stream_complete, shutdown_ack_ok                         bool
shutdown_response_sha256                                 uppercase hex64 or null
post_response_timeout_ns                                 10000000000
natural_exit_grace_ns                                    5000000000
forced_reap_budget_ns                                    4000000000
reader_drain_reserve_ns                                  1000000000
exit_mode                                                null | natural |
                                                         natural_after_grace |
                                                         forced_terminate |
                                                         forced_kill
graceful_exit                                            bool or null
termination_signal_attempted, kill_signal_attempted      bool
forced_reap                                              bool
forced_reap_succeeded                                    bool or null
reader_threads_drained                                   bool
stdout_eof_count, residual_response_count                nonnegative integer
residual_frame_kinds                                     strict string array
terminal_eof_exact, transport_finalized                  bool
post_response_elapsed_ns                                 nonnegative integer or null
```

`non_json_stdout_count` is the aggregate of invalid-UTF-8, JSON-decode, and
non-object stdout lines; the invalid-UTF-8 and non-object fields are disjoint
subcounts. A classified duplicate, late, or unsolicited parsed object increments
`residual_response_count`, adds its association to `residual_frame_kinds`, and
forces `terminal_eof_exact=false` even though it is quarantined outside the
consumer queue. With no anomaly, terminal EOF exact means one EOF, zero residual
responses, and residual kinds exactly `["eof"]`.

The 12 X0 predicates, in frozen order, are exactly:

```text
stream_complete              == true
shutdown_ack_ok              == true
shutdown_response_sha256     == canonical SHA-256 of recorded shutdown response
graceful_exit                == true AND exit_mode == "natural"
forced_reap                  == false
process_returncode           == 0
reader_threads_drained       == true
terminal_eof_exact           == true
transport_overflow           == false
non_json_stdout_count        == 0
post_response_elapsed_ns     is nonnull and 0 <= value <= 10000000000,
                             with post_response_timeout_ns == 10000000000
transport_finalized          == true
```

The strict verifier also requires `shutdown_ack_ok` to equal the predicate
`response.ok is true AND response.shutdown is true AND response.error is null`.
The gate passes iff all 12 predicates are true. These are computations over
recorded harness observations, not independent pipe/process measurements.

The closure reason registry is:

```text
CLEANUP_ERROR
EOF_BEFORE_EXPECTED_RESPONSE
INVALID_UTF8_STDOUT
NON_JSON_STDOUT
NON_OBJECT_STDOUT
OTHER_HARNESS_ERROR
PROCESS_EXIT_BEFORE_REQUEST
READER_ERROR
REQUEST_TIMEOUT
REQUEST_VALIDATION_ERROR
REQUEST_WRITE_ERROR
RESPONSE_DUPLICATE
RESPONSE_LATE
RESPONSE_UNSOLICITED
SHUTDOWN_FINALIZATION_ERROR
STDIN_UNAVAILABLE
TRANSPORT_OVERFLOW
WORKER_START_ERROR
WORKER_TIMEOUT
```

`reason_codes` is lexicographically sorted and
`primary_reason_code=min(reason_codes)`; both are therefore independently
verifiable. A complete sequence may retain transport reason codes observed
after all expected pairs.
An aborted sequence has at least one reason. Writer/durability failures cannot
produce a closure and use the attempt-manifest codes in Section 12.
A structurally valid closure requires `process_quiesced`, both reader-quiesced
fields, and `writer_healthy` all true. `sequence_status=complete` additionally
requires one local probe, exactly one request and one `active_frame` response
for every ordered frame, and no missing/duplicate request index; only the
post-frame-23 response anomalies described below may add records.

## 7. Record state machine and delivery binding

After header, the healthy nominal state is `NEED_LOCAL_PROBE`, then `IDLE(1)`.
Legal nominal transitions are:

```text
header -> local_probe -> IDLE(1)
IDLE(k) -> request_intent(k) -> WAITING(k)
WAITING(k) -> parsed_response(active_frame,k) -> RESPONDED(k)
RESPONDED(k) -> request_intent(k+1)   for k < 23
RESPONDED(23) -> DONE -> closure(complete)
```

The next request record is proof that the requester consumed and cleared the
prior active frame. Echo-id mismatch does not change this transition.

From `IDLE`, a parsed object is `unsolicited`; from `WAITING` after cancellation
the logical state becomes `CANCELLED(k)` and a later object is
`late_for_frame`; from `RESPONDED` before clear it is
`duplicate_for_frame`. Classification is strictly by observation state, never
by echoed id: an old object first observed during `WAITING(k+1)` is
indistinguishable from the current active response, is recorded/delivered as
`active_frame,k+1`, and can only be exposed by its untouched content and R0 or
other contract mismatch. The implementation must not claim to quarantine that
cross-frame case.

Classified duplicate, late, and unsolicited objects are recorded and
quarantined. Before frame 23 completion they permit only quiescence plus an
aborted closure. At frame 23, a duplicate observed in `RESPONDED(23)` or an
unsolicited object observed in `DONE` is not delivered; because all expected
pairs already exist, closure may remain `complete`, carries the corresponding
reason code, and must make X0 false. Unsolicited null frame indices are omitted
from `observed_response_frame_indices`; all nonnull response indices remain in
record order. Unique duplicate indices appear ascending in
`duplicate_response_frame_indices`; late responses contribute to their observed
index and `late_response_count`. `_request_lock` forbids duplicate request records, so
`duplicate_request_frame_indices` must always be empty and any ledger containing
one is invalid. Closure is terminal. Header-only or header-plus-prefix closure
is legal only with `sequence_status=aborted`. A missing/torn closure is never
finalized.

Every queued response carries the active frame index, label, expected id,
ledger record index, and ledger record hash. `request()` verifies all five
before returning the response. No bare response object is consumable.

## 8. Lock order and fsync order

The requester holds `_request_lock` for one in-flight frame. It installs the
frame under `_active_lock`, releases that lock, appends/fsyncs the request under
the writer lock, then writes stdin. The reader snapshots and marks the active
frame under `_active_lock`, releases it, appends/fsyncs the response under the
writer lock, then queues the bound item. The requester clears active state only
after a matched delivery or recorded failure.

The reader never takes `_request_lock`. No holder of the writer lock takes
`_active_lock` or `_request_lock`; active and writer locks are never held
together. Closure takes only the writer lock after the requester has ended and
both readers are joined.

A writer validation failure before any bytes are written leaves it healthy and
may lead to an aborted closure. Any open, write, short-write, flush, fsync, or
closure-durability failure permanently poisons it: no further append, no
closure, no canonical report. A healthy closure is appended/flushed/fsynced,
then the file is closed exactly once. Append, second closure, reopen-for-append,
resume, repair, or truncate is forbidden.

## 9. Quiescence and verdict preservation

Normal shutdown keeps the existing 10-second post-response budget: 5 seconds
natural-exit grace, 4 seconds forced-reap budget, and 1 second reader reserve.
For an earlier error, `quiesce_for_evidence` starts one 10-second monotonic
deadline at the first abort request: close stdin; wait at most 2.5 seconds after
terminate; if alive, wait at most 4 seconds after kill; give both reader joins
all remaining time. Later calls are idempotent and cannot extend the deadline.

Closure is written only after process and both readers are proven stopped and
no append callback can run. A reader that cannot join leaves an unclosed ledger
and no canonical report.

`sequence_status` measures expected object coverage, not scientific or
transport success. Forced terminate/kill, nonzero return code, non-graceful
exit, or other X0 telemetry does not by itself change a 23/23 sequence from
`complete`. Therefore the Amendment-2 verdict rule is preserved:

- complete sequence, no cleanup/harness exception: independently derive the 11
  contracts and mechanically reproduce X0 from captured telemetry; all true
  gives `U1_DIAGNOSTIC_CLEAR`, otherwise `U1_DIAGNOSTIC_BLOCKED`;
- active-frame echo-id mismatch: complete, R0 false, therefore BLOCKED;
- forced reap after the recorded shutdown response: complete, X0 false,
  therefore BLOCKED rather than HARNESS;
- timeout, parse/type error, duplicate/late/unsolicited response before frame
  completion, worker error, or stdin failure: closed aborted prefix and
  `HARNESS_ERROR` if writer and quiescence remain healthy;
- cleanup/reader exception, even after 23 pairs: `HARNESS_ERROR`; and
- writer poison, closure failure, unquiesced reader, or power loss: no canonical
  report; only immutable partial evidence and mandatory attempt manifests.

An aborted prefix never claims recomputation of missing contracts.

## 10. Bundle order, races, and disk preflight

Before the remote claim, read-only preflight checks canonical paths, absence of
all three final bundle members and known temp names, anchor/topology, and at
least 235,929,600 free bytes in the target filesystem. This threshold is 128
MiB ledger + two 16 MiB report copies + 1 MiB reservation + 64 MiB margin.
Preflight is advisory; exclusive create remains race authority.

The only positive order is:

1. read-only preflight;
2. one remote `claim_once` returning the public receipt;
3. publish the `claim_started` event on the separate manifest branch;
4. exclusive-create canonical reservation, write/flush/fsync, close;
5. exclusive-create ledger with one OS append-only handle;
6. write/flush/fsync header;
7. start any platform/Lean preflight and then the worker;
8. append evidence, quiesce, closure-fsync, close, and strict verify;
9. construct report, write/fsync temp, reverify receipt/reservation/ledger/report;
10. exclusive hard-link report; and
11. publish the final attempt-manifest event.

The one writer handle is passed through the runner and never reopened for
append. It is opened with `O_CREAT|O_EXCL|O_WRONLY|O_APPEND` and `O_BINARY` when
available; Python `x+b` alone is not accepted as append authority. Before every
write, the tracked byte count must equal the OS file position and observed EOF.
Any exclusive-create race or failure after step 2 consumes the remote
attempt. Pre-run reservation/receipt bind identity and header, not future
ledger content. Only the post-run report digest and externally committed result
manifest anchor final ledger bytes/head against a fully recomputed rewrite.

## 11. Verifiers and report binding

Finalized verifier id is
`lean-rgc-uprime-rpc-parsed-ledger-verifier-v1.0`; partial inspector id is
`lean-rgc-uprime-rpc-parsed-ledger-inspector-v1.0`. Both stream bounded lines.
The finalized verifier requires a valid closure and rejects noncanonical bytes,
bounds, exact-field/type violations, index or chain errors, illegal state
transitions, wrong frame/probe/count/head, second closure, and trailing bytes.
It rejects non-rehashed tamper. The bundle verifier rejects a fully rehashed
rewrite only relative to an already anchored report/manifest file digest.

The read-only inspector returns maximal verified complete-line offset/head,
state/pending frame, and `unclosed`, `torn`, or `corrupt`; corruption before a
final incomplete line is never called torn. It never edits, truncates, resumes,
or promotes evidence.

Report schema is `lean-rgc-uprime-rpc-diagnostic-v1.2`. Its exact
`evidence_ledger` object is:

```text
path, schema_version, evidence_scope                    fixed strings
sha256, genesis_sha256, header_record_sha256,
closure_record_sha256, final_chain_head                 uppercase hex64
bytes, record_count, local_probe_count,
request_intent_count, parsed_response_count,
closure_record_index                                   signed-64 integers
sequence_status                                         complete | aborted
expected_frame_manifest_sha256                          frozen digest
claim_receipt                                            exact public object
claim_receipt_sha256, reservation_sha256                 uppercase hex64
verifier_schema_version                                  fixed verifier id
verifier_passed                                          true
```

`path` is the exact forward-slash repository-relative ledger path from Section
4; `schema_version` and `evidence_scope` equal the header values.

The report is built only after strict verification. Immediately before report
hard-link, all bindings and ledger bytes are reverified. Compact summaries and
request maps must match full ledger objects.
Exact report bytes remain the repository format: UTF-8 JSON with sorted keys,
two-space indentation, `ensure_ascii=false`, `allow_nan=false`, and one final
LF.

The independent contract verifier may share only strict JSON and hash
primitives. It must not import or call `evaluate_contracts`,
`diagnostic_disposition`, `_response_summary`, `cache_budget_probe`, or any
production contract predicate. A test replaces those production functions
with raising sentinels while independent recomputation still succeeds. X0 is
explicitly reported as a predicate over captured closure telemetry, not an
independent OS observation.

## 12. Mandatory attempt visibility, retention, and privacy dependency

The attempt-manifest schema, local writer, verifier, terminality rules, and
recovery simulation are M2b governance work. M2b tests use a fake remote and do
not contact the network. The privacy scanner and encrypted archive are the M2c
dependency.

Selective full-ledger publication cannot hide an attempt. Every remote claim
must publish an append-only `claim_started` event on fixed branch
`refs/heads/uprime-u1-attempt-manifests` before Lean starts. If that publication
fails, the claim is consumed and no worker starts. A final/recovery event is
mandatory after CLEAR, BLOCKED, HARNESS, privacy hit/error, torn evidence,
disk failure, or power loss discovery.

Manifest schema `lean-rgc-uprime-u1-attempt-manifest-v1.0` has exactly:

```text
schema_version                 fixed manifest schema
event_type                     claim_started | attempt_finished | recovery
event_index                    positive integer, starting at 1
created_at_utc                 canonical UTC string
license_id                     lowercase hex64
candidate_commit               lowercase hex40
license_commit                 lowercase hex40
remote_claim_ref               fixed full tag ref
claim_receipt                  exact public receipt object
claim_receipt_sha256           uppercase hex64
prior_event_sha256             null only at index 1, else uppercase hex64
reservation_exists             bool
ledger_exists                  bool
report_exists                  bool
reservation_sha256             uppercase hex64 or null
reservation_bytes              nonnegative integer or null
ledger_sha256                  uppercase hex64 or null
ledger_bytes                   nonnegative integer or null
report_sha256                  uppercase hex64 or null
report_bytes                   nonnegative integer or null
ledger_inspection_status       absent | unclosed | torn | corrupt | finalized
ledger_sequence_status         null | complete | aborted
verifier_status                not_run | passed | failed | unavailable
scanner_status                 not_run | clear | hit | error | unavailable
scanner_rule_ids               sorted unique string array, never matched text
verdict                        null | U1_DIAGNOSTIC_CLEAR |
                               U1_DIAGNOSTIC_BLOCKED | HARNESS_ERROR
failure_codes                  sorted unique frozen string array
full_ledger_published          bool
terminal_event                 bool
```

Each event is compact canonical JSON plus LF at the path pattern
`docs/experiments/artifacts/uprime_u1_rpc_attempts/<license_id>/NNNN.json` on
the fixed manifest branch, where `NNNN` is the four-digit event index. Event
SHA is SHA-256 of exact file bytes including LF and forms the
`prior_event_sha256` chain. The separate branch must be pushed successfully;
changing it does not move execution HEAD `L`.
Attempt-only failure codes additionally include `LEDGER_OPEN_ERROR`,
`LEDGER_APPEND_ERROR`, `LEDGER_FSYNC_ERROR`, `LEDGER_CLOSURE_ERROR`,
`LEDGER_VERIFY_ERROR`, `RESERVATION_CREATE_ERROR`, `RESERVATION_WRITE_ERROR`,
`RESERVATION_FSYNC_ERROR`, `CLAIM_STARTED_MANIFEST_ERROR`,
`REPORT_TEMP_CREATE_ERROR`, `REPORT_WRITE_ERROR`, `REPORT_FSYNC_ERROR`,
`REPORT_REVALIDATION_ERROR`, `REPORT_HARDLINK_ERROR`, `FINAL_MANIFEST_ERROR`,
`READER_NOT_QUIESCED`, `POWER_LOSS`, `SCANNER_ERROR`, `ARCHIVE_ERROR`,
`PUBLICATION_ERROR`, `PRIVACY_DENIED`, and `OTHER_ATTEMPT_ERROR`.
`failure_codes` is drawn only from the union of that list and the closure
registry in Section 6.
At normal `claim_started`, all three existence flags are false, their hash/byte fields
are null, `event_index=1`, `prior_event_sha256=null`, and
`terminal_event=false`; verifier/scanner are `not_run`, verdict is null, failure
codes are empty, and `full_ledger_published=false`. A final
`attempt_finished` has `terminal_event=true`.
A recovery event may be nonterminal or terminal but must continue the chain.
If power fails after the claim ref is created but before `claim_started`, the
remote-ref recovery scanner publishes a terminal `recovery` as event 1 with
null prior hash before any later experiment or claim; it may not start the
worker for that consumed attempt.

The only event grammar is normal
`claim_started(index=1) -> recovery* -> exactly one terminal
(attempt_finished|recovery)`, or the pre-start terminal recovery exception just
described. No event follows a terminal event. Before any later canonical worker
or remote claim, a remote scan must show exactly one valid terminal chain for
every prior U'1 claim ref; otherwise only recovery work is permitted.

For a finalized ledger/report with `scanner_status=clear`, a terminal event is
valid only after byte-identical tracked publication of both artifacts and must
set `full_ledger_published=true`. A publication failure keeps the scientific
verdict, sets `PUBLICATION_ERROR` and false, and requires recovery before later
claims. Scanner `hit|error|unavailable`, archive failure, or nonfinalized
evidence requires false and the corresponding code; none licenses a rerun.

Raw reservation, ledger, and report bytes are copied byte-identically to an
encrypted content-addressed off-workstation archive before local cleanup and
retained for at least 365 days after claim or until external review closes,
whichever is later. Archive provider, encryption/key custody, upload verifier,
recovery drill, privacy rule corpus, no-allowlist policy, scanner schema, and
scan/mutation race protocol must be frozen in a separate M2c preregistration
and implemented before any positive claim. M2b core does not claim that M2c is
already satisfied. Privacy outcome never changes the scientific verdict and
never licenses a cleaner rerun.

## 13. Finite acceptance profile

M2b core tests are restricted to:

```text
tests/test_uprime_rpc_ledger.py
tests/test_uprime_rpc_litmus.py
tests/test_uprime_rerun_license.py
tests/test_v74_test_tier_manifest.py
```

The registered Windows command is the following single command line:

```text
python -m pytest -q tests/test_uprime_rpc_ledger.py tests/test_uprime_rpc_litmus.py tests/test_uprime_rerun_license.py tests/test_v74_test_tier_manifest.py
```

It runs on Windows 11 build 26200, CPython 3.13.7, with zero failures, errors,
skips, or xfails, and is recorded in a commit-bound execution document. The
same commit must pass repository CI on CPython 3.11/Ubuntu. Positive activation
additionally requires the pinned Windows CI/profile already mandated by M2a.

The exact synthetic matrix is:

1. canonical golden header/probe/one-pair/aborted-closure fixture no larger
   than 32,768 bytes; freeze its bytes/digests in the test and inspect every cut
   offset `0..len(fixture)-1`: offset zero or a complete-line boundary is
   `unclosed`, a cut inside the now-final line is `torn`; corrupting an earlier
   complete line while later bytes remain is `corrupt`, never torn;
2. nominal synthetic 23-frame fixture: exactly 49 records, independent 11
   contract recomputation equals report; forced-reap variant is complete and
   X0-BLOCKED; complete frame-23 duplicate and DONE-state unsolicited variants
   are quarantined and X0-BLOCKED;
3. duplicate nested/top keys, BOM, CRLF, spacing/key order, invalid UTF-8,
   float/NaN/infinity, surrogate, missing/extra fields, bool-as-int;
4. every numeric bound at limit-1/limit/limit+1 using primitive validators;
   sparse max-file+1 and bounded-line tests avoid allocating a valid 128 MiB
   ledger;
5. body/schema/previous/hash bit flip, insertion, deletion, duplication,
   reorder, cross-bundle transplant, wrong counts/head, second closure, and
   trailing bytes;
6. full-chain recomputation after semantic tamper: standalone ledger verifies
   only if state remains valid, while the original anchored report/manifest
   digest rejects the replacement;
7. event spies prove request fsync before stdin and response fsync before queue;
   response queue binding rejects wrong frame/hash and quarantines duplicate,
   late, and unsolicited objects;
8. open/write/short-write/flush/fsync and closure-fsync injection; writer poison
   yields no closure/report, whereas stdin failure with healthy writer yields
   an aborted closure;
9. normal shutdown, forced reap, timeout at each of 23 frames, EOF pending,
   invalid/non-object response, crossing-frame delayed object, overflow, reader
   exception, and reader refusal to join; the crossing-frame object is delivered
   as current `active_frame` and exposes R0/contract failure rather than being
   mislabeled duplicate; no write occurs after closure;
10. the seven nonempty subsets of pre-existing
    `{reservation, ledger, report}` all reject; a two-contender barrier gives
    exactly one reservation winner;
11. crash injection immediately after each of these 14 boundaries: claim,
    claim-started manifest push, reservation fsync, ledger create, header fsync,
    request fsync, response fsync, quiescence, closure fsync, ledger close,
    ledger verify, report-temp fsync, final reverify, report hard-link;
12. one claim call and identical receipt at every boundary; current bootstrap
    still reaches no reservation, ledger, worker, or network;
13. independent verifier succeeds while all forbidden production evaluators
    are raising sentinels; and
14. new M2b positive-path tests use only temp paths/fake processes/synthetic
    local JSONL and never invoke formal `main`/`run_diagnostic`, Lean,
    registered run paths, network, or GPU; existing default-denial tests may
    call formal entrypoints only to prove they stop before side effects.

Every crash case runs the same recovery oracle: the unique remote claim remains
consumed; only files/records durably completed at or before the named boundary
exist and nothing from a later boundary exists; no worker remains, restarts, or
resumes the ledger; the inspector status matches those bytes; and a recovery
event (event 1 for pre-start crash, otherwise the next event) records exact
existence/hash/byte facts and closes one valid terminal manifest chain. Recovery
does not promote a temp file or rerun Lean.

The targeted profile and default test collection must contain every new test;
tier registration is `unit`. A zero-skip targeted Windows result and green CI
are both necessary, neither sufficient for a positive claim.

## 14. Stop rule

M2b implementation may proceed synthetically on Windows CPU after this document
is committed and pushed. No canonical rerun is licensed until M2b writer,
verifiers, bundle/queue/quiescence integration, independent recomputation, all
failure tests and attempt-manifest writer/recovery simulation, M2a claim
receipt, M2c privacy scanner plus encrypted archive/retention, pinned Windows
evidence, CI, and adversarial review are complete.

This milestone does not license U'0.5, later U' stages, GPU construction, or
contact with the GPU host.
