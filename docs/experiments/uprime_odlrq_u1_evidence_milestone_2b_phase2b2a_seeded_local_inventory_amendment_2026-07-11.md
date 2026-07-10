# U'1 evidence milestone 2b phase 2b2a seeded/local inventory amendment

Date: 2026-07-11

Status: PREREGISTERED READ-ONLY SYNTHETIC SEED/LOCAL-NAMESPACE AUDIT; NO WRITE,
ARTIFACT OBSERVATION, CAS, FAULT MARKER, RECOVERY EPOCH, WITNESS, CLAIM, REMOTE,
WORKER, LEAN, NETWORK, CANONICAL-RUN, RERUN, LATER-STAGE, OR GPU AUTHORITY.

## 1. Purpose and explicit decomposition amendment

Phase 2b1 implemented exact event/chain structure for one caller-selected
license directory. It deliberately cannot detect an omitted claim or an orphan
directory under another license ID. That limitation is a selective-evidence
surface: a caller can inspect only a favorable directory and never ask about
the rest.

The first Phase-2b design attempted to combine local staging, fake CAS,
acknowledgement loss, causal markers, recovery epochs, and witness issuance.
Independent adversarial review rejected that monolith as underdetermined. The
same review of the completed Phase-2b1 result found that the smallest material
next step is instead a read-only, all-entry comparison between one exact
synthetic seed and the entire local attempt-manifest namespace.

This amendment therefore supersedes only the Phase-2b1 Section-11 requirement
that every later Phase-2b2 obligation be frozen simultaneously before any
Phase-2b2 code. The obligations are not removed. They are reassigned to the
following ordered subphases, and each subphase requires its own reviewed,
committed, pushed, green amendment before its code begins:

1. **Phase 2b2a (this amendment):** exact caller-supplied seed parsing and
   complete local namespace/chain accounting, read-only;
2. **Phase 2b2b:** tri-state `present|absent|indeterminate` local artifact
   observation, with no claim of an atomic three-artifact snapshot;
3. **Phase 2b2c:** pure single-process in-memory fake CAS transition kernel,
   including exact acknowledged/conflict/ack-loss/confirmation/wrong-delta
   outcomes and hash formulas, with no filesystem or recovery;
4. **Phase 2b2d:** nonce-separated local staging plus normal fake publisher,
   with no crash or causal recovery claim;
5. **Phase 2b2e:** internal one-shot synthetic marker journal, publisher/
   recovery exclusion, epoch ownership/release/abandon/replay, and private
   same-instance single-use witness registry; and
6. **Phase 2b2f:** integrated synthetic manifest writer and recovery audit.

Artifact truth/TOCTOU, fake hashes/CAS, local staging collision avoidance,
marker causality, conflict-without-marker, epoch lifecycle, witness issuer,
ack-loss reconciliation, and out-of-band post-terminal facts remain mandatory
at their named gates. No later subphase may import an earlier structural result
as authority for a deferred property.

## 2. New paths, collection, anchors, and dependency boundary

The Phase-2b2a implementation paths are exactly:

```text
lean_rgc/evals/uprime_rpc_seed_inventory.py
tests/uprime_rpc_seed_inventory_cases.py
```

The support filename is outside pytest's default patterns. It has an exact
`__all__` containing only its `test_uprime_seed_inventory_*` functions and is
imported exactly once by `tests/test_uprime_rpc_ledger.py`:

```python
from uprime_rpc_seed_inventory_cases import *  # noqa: F403
```

Before a result commit, this amendment, source, support, collector, and later
execution record must be in `ANCHOR_PATHS` and the membership test. Frozen and
default collection must each expose every new node once and only once.

The source may import Python standard-library `dataclasses`, `hashlib`, `os`,
`re`, and `stat`; exactly these four public Phase-2b1 symbols from
`lean_rgc.evals.uprime_rpc_attempt_manifest`:

```text
AttemptManifestV10Error
PublicClaimReceiptV10
AttemptManifestChainInspectionV10
inspect_local_attempt_manifest_chain_v1_0
```

and only `canonical_json_bytes`/`parse_canonical_json_bytes` from the standalone
ledger. It may not import a Phase-2b1 private name, production litmus,
reservation module/writer, subprocess, Git, socket/HTTP, Lean, worker,
scanner/archive, registered-run, or formal entrypoint code.

## 3. Exact seed wire format and hash formulas

The seed schema is `lean-rgc-uprime-u1-synthetic-claim-seed-v1.0` and has
exactly three fields:

```text
schema_version
seed_scope = caller_supplied_synthetic_claims_only
claim_receipts = array of exact 13-field PublicClaimReceiptV10 mappings
```

Seed bytes are compact strict canonical JSON plus exactly one LF. The inclusive
maximum is 16,777,216 bytes. BOM, CRLF, missing/extra LF, noncanonical spacing
or key order, duplicate keys, invalid UTF-8, float/nonfinite/surrogate values,
trailing data, and bounds violations reject. `raw` has exact type `bytes`.

The array contains 0..16 receipts in strictly ascending ASCII `license_id`
order. Each receipt is reconstructed through the Phase-2b1 public value type
and fully revalidated. Duplicate license ID, duplicate remote claim ref,
unsorted order, unknown/missing receipt field, or a byte rewrite that does not
round-trip exactly rejects. Empty seed is syntactically valid but can never
produce a matched coverage result.

For exact seed file bytes `R`:

```text
seed_file_sha256 = UPPER_HEX(SHA256(R))
seed_identity_sha256 = UPPER_HEX(SHA256(
    b"lean-rgc-uprime-u1-synthetic-claim-seed-v1\0" ||
    uint64_be(len(R)) || R
))
```

The LF is included in both hashes. `uint64_be` rejects booleans, negatives,
and overflow. A seed timestamp, caller label, or parsed object is never used as
an identity input.

## 4. Exact public records and APIs

All records are `@dataclass(frozen=True, slots=True)` in the displayed order.
Tuple fields are immutable tuples. The single public exception is
`SyntheticSeedInventoryV10Error(ValueError)`.

`SyntheticClaimSeedV10` has exactly 16 fields:

```python
schema_version: str
seed_scope: str
origin_status: str
seed_file_sha256: str
seed_identity_sha256: str
seed_bytes: int
claim_receipts: tuple[PublicClaimReceiptV10, ...]
claim_count: int
inventory_completeness: str
omitted_claim_detectability: str
remote_inventory_observation: str
seed_temporal_commitment: str
authority_scope: str
licenses_execution: bool
licenses_publication: bool
licenses_later_stage: bool
```

`SyntheticLocalClaimAuditV10` has exactly 16 fields:

```python
license_id: str
seed_membership: bool
local_membership: bool
set_relation: str
receipt_relation: str
seed_receipt_sha256: str | None
local_receipt_sha256: str | None
chain_observation: str
event_count: int | None
last_event_index: int | None
last_event_sha256: str | None
terminal_event: bool | None
recorded_verdict: str | None
authority_scope: str
licenses_execution: bool
licenses_later_stage: bool
```

`SyntheticSeedLocalInventoryAuditV10` has exactly 43 fields:

```python
auditor_schema_version: str
auditor_scope: str
origin_status: str
base_directory_status: str
seed_file_sha256: str
seed_identity_sha256: str
seed_count: int
local_directory_count: int
union_claim_count: int
examined_claim_count: int
total_observed_event_bytes: int
read_work_upper_bound_bytes: int
event_file_admission_upper_bound: int
claim_audits: tuple[SyntheticLocalClaimAuditV10, ...]
unexpected_entry_names: tuple[str, ...]
unexpected_entry_count: int
seeded_missing_ids: tuple[str, ...]
local_orphan_ids: tuple[str, ...]
receipt_mismatch_ids: tuple[str, ...]
terminal_ids: tuple[str, ...]
nonterminal_ids: tuple[str, ...]
empty_chain_ids: tuple[str, ...]
coverage_status: str
set_equality: bool
all_seeded_local_present: bool
all_seeded_terminal: bool
all_seeded_receipts_match: bool
seed_origin: str
seed_binding: str
seed_temporal_commitment: str
remote_inventory_observation: str
real_claim_completeness: str
omitted_claim_detectability: str
coordinated_omission_detectability: str
root_scope: str
snapshot_scope: str
resource_status: str
authority_scope: str
canonical_run_authority: bool
licenses_execution: bool
licenses_publication: bool
licenses_recovery: bool
licenses_later_stage: bool
```

The only public functions are positional-only:

```python
parse_synthetic_claim_seed_v1_0(
    raw: bytes, /
) -> SyntheticClaimSeedV10

audit_synthetic_seed_local_inventory_v1_0(
    root: str | os.PathLike[str], seed_raw: bytes, /
) -> SyntheticSeedLocalInventoryAuditV10
```

`__all__` is this exact ordered Python list:

```python
[
    "SyntheticSeedInventoryV10Error",
    "SyntheticClaimSeedV10",
    "SyntheticLocalClaimAuditV10",
    "SyntheticSeedLocalInventoryAuditV10",
    "parse_synthetic_claim_seed_v1_0",
    "audit_synthetic_seed_local_inventory_v1_0",
]
```

Type/schema/seed/base-scan/I/O/resource errors raise the single public
exception and return no partial result. An `AttemptManifestV10Error` from a
`PublicClaimReceiptV10` constructor during seed parsing is wrapped in the new
public exception. Expected set mismatch and structurally valid
empty/nonterminal chains return typed negative audit results. Any Phase-2b1
per-claim rejection, including its I/O failures, is also wrapped in the new
public exception and aborts the entire audit; no later claim is inspected.

The audit API accepts raw seed bytes, never a caller-constructed
`SyntheticClaimSeedV10`. It reparses and revalidates the seed inside the call.

## 5. Seed output constants and non-authority

Every parsed seed fixes:

```text
schema_version = lean-rgc-uprime-u1-synthetic-claim-seed-v1.0
seed_scope = caller_supplied_synthetic_claims_only
origin_status = unknown_may_be_synthetic
inventory_completeness = not_authenticated_may_omit_claims
omitted_claim_detectability = none_outside_supplied_seed
remote_inventory_observation = not_performed
seed_temporal_commitment = not_authenticated
authority_scope = none
licenses_execution = false
licenses_publication = false
licenses_later_stage = false
```

The parser copies no caller container and retains only immutable receipt
records reconstructed from exact bytes. `seed_bytes=len(R)` including the final
LF, and `claim_count=len(claim_receipts)`. `seed_file_sha256` proves only
equality to bytes supplied in this call. Unless a later record binds that digest
to an earlier commit, it is not a temporal commitment. Even a committed seed
cannot prove that a real remote claim was not omitted.

## 6. Local base namespace and stable observation

`root` is a caller-owned, nonempty, lexically absolute synthetic sandbox
prefix. It is not resolved or normalized. The local base path is formed by
appending:

```text
docs/experiments/artifacts/uprime_u1_rpc_attempts
```

The source writes nothing and never creates the root or base. Prefix links are
outside the audit. A present final base directory and every child classified as
a local claim must be a real non-reparse directory under the Phase-2b1 POSIX-
symlink/Windows-reparse predicate.

The resource constants are:

```text
_MAX_SEED_BYTES = 16_777_216
_MAX_SEEDED_CLAIMS = 16
_MAX_LOCAL_CLAIM_DIRS = 16
_MAX_BASE_ENTRIES = 32
_MAX_UNEXPECTED_NAMES = 16
_MAX_UNEXPECTED_NAME_UTF8_BYTES = 4_096
_MAX_UNION_CLAIMS = 32
_MAX_TOTAL_ACCEPTED_EVENT_BYTES = 67_108_864
_MAX_TOTAL_EVENT_READ_WORK_BYTES = 268_435_457
_MAX_EVENT_FILE_ADMISSIONS = 159_984
```

Every enumeration streams at most its bound plus one before rejecting and
closing. It never materializes an unbounded iterator. Bounds are validated as
exact nonnegative integers with booleans rejected. Boundary tests use actual
in-memory bytes under injected small bounds; no sparse object or sparse-byte
surrogate is accepted, and no production-size accepted event fixture is
allocated.

`os.fspath(root)` is evaluated exactly once. It must return exact type `str`;
empty or lexically relative roots reject. The retained value is `root_text`,
and that exact string is used both to form the base and as the `root` argument
of every Phase-2b1 inspection. The implementation does not call `resolve`,
`abspath`, `normcase`, or case-folding. It appends the fixed base components
with `os.path.join`.

A scan-provided entry name is safe for bounded output only when it has exact
type `str`, is strict UTF-8 encodable in at most 4,096 bytes, is nonempty, is
not `.` or `..`, contains no U+0000, and contains neither slash nor backslash.
Any other name raises before any child-path join or entry stat. Only an exact
lowercase-hex64 safe name is a claim-path candidate and may be appended to the
base or statted. Every other safe name -- including a Windows device spelling,
an ADS-like colon spelling, or a trailing-dot/space spelling -- is retained as
unexpected evidence without any child-path join or entry stat.

If the base is absent, only `FileNotFoundError`/ENOENT means absent. The audit
performs a second no-follow observation after seed accounting and requires it
still absent; appearance between observations rejects. Other failures reject.

If present, the exact order is:

1. no-follow stat the base; require real/non-reparse directory and capture
   `D0=(dev, ino, mode, reparse, ctime_ns, mtime_ns)`;
2. stream scan 1 to at most `_MAX_BASE_ENTRIES+1` and close exactly once;
3. read and validate all bounded entry names before any child-path join or
   entry stat and reject duplicate names;
4. for each exact lowercase-hex64 candidate only, append that name to the base,
   perform exactly one full-path no-follow stat, and capture
   `E=(dev, ino, mode, reparse, ctime_ns, size, mtime_ns)`; classify it as
   `local_claim` only when `E` proves a real non-reparse directory and as
   `unexpected_claim_candidate` otherwise; classify every noncandidate safe
   name as `unexpected_name` without joining or statting it;
5. ASCII-sort valid claim IDs, UTF-8-byte-sort unexpected names, and require
   valid local claims <=16 and unexpected names <=16;
6. inspect every ID in the sorted union of seed IDs and valid local IDs; each
   local member is observed through
   `inspect_local_attempt_manifest_chain_v1_0(root_text, license_id)`;
7. stream scan 2 with the same rules and require exact sorted
   `(name,classification,E_or_null)` tuples as scan 1, where classification is
   exactly `local_claim`, `unexpected_claim_candidate`, or `unexpected_name`,
   and `E_or_null` is null exactly for `unexpected_name`;
8. no-follow stat the base again; require real/non-reparse and exact `D0=D1`.

Every numeric component of `D` and candidate-only `E` must be exact type `int`,
with booleans rejected. `reparse` is an exact `bool` derived by the Phase-2b1
POSIX-symlink/Windows-reparse predicate. Each scan observes each claim
candidate's metadata tuple once; no `DirEntry.stat` fallback or second stat of
the same candidate in one scan is permitted.

Step 8 is the base-namespace observation point. A per-claim chain observation
occurs earlier at the observation point defined by Phase 2b1. The audit is
therefore sequential and never claims all chains were terminal at one atomic
instant. No claim covers mutation after the relevant observation point.

A safe noncandidate name is retained in `unexpected_entry_names` without a
join/stat. An exact hex64 candidate that is a non-directory, symlink, or
reparse entry is also retained there after its no-follow stat. Both block
`matched_terminal`. Unsafe names and candidate stat/scan/identity failures
raise instead of being encoded as absence. Initial and final base
non-directory/symlink/reparse states also raise.

## 7. Per-claim accounting

The union is sorted by ASCII license ID and every union element produces
exactly one `SyntheticLocalClaimAuditV10`.

`set_relation` is exactly one of:

```text
seed_and_local
seeded_missing_local
local_orphan
```

`chain_observation` is exactly one of:

```text
not_present
missing
valid_nonterminal
valid_nonterminal_index_exhausted
valid_terminal
```

`receipt_relation` is exactly one of:

```text
exact_match
seed_only
local_only
mismatch
not_observed
```

Seed receipt SHA is
`UPPER_HEX(SHA256(canonical_json_bytes(M)))`, where `M` is the exact 13-field
receipt mapping named in Section 3 and the canonical bytes contain no LF.
Local receipt SHA is copied only from a successful nonempty Phase-2b1
inspection. Exact dataclass equality, not digest equality alone, determines
`exact_match`.

The complete per-claim mapping is:

| Seed/local state | set_relation | receipt_relation | receipt SHA fields | chain/endpoints |
|---|---|---|---|---|
| seed only | `seeded_missing_local` | `seed_only` | seed set, local null | `not_present`; count/index/hash/terminal/verdict null |
| local only, Phase-2b1 `missing` | `local_orphan` | `not_observed` | both null | `missing`; count 0, index/hash null, terminal false, verdict null |
| local only, nonempty valid | `local_orphan` | `local_only` | seed null, local set | exact Phase-2b1 chain/endpoints |
| seed and local, Phase-2b1 `missing` | `seed_and_local` | `not_observed` | seed set, local null | `missing`; count 0, index/hash null, terminal false, verdict null |
| seed and local, nonempty exact receipt | `seed_and_local` | `exact_match` | both set and equal | exact Phase-2b1 chain/endpoints |
| seed and local, nonempty different receipt | `seed_and_local` | `mismatch` | both set | exact Phase-2b1 chain/endpoints |

Every per-claim record fixes `authority_scope=none`,
`licenses_execution=false`, and `licenses_later_stage=false`. A Phase-2b1
`AttemptManifestV10Error` is wrapped as `SyntheticSeedInventoryV10Error`; no
per-claim record, error message, or partial aggregate is returned.

For each successful Phase-2b1 inspection, the audit sums exact retained
`event_bytes` lengths. If the total exceeds 67,108,864 it rejects. Because one
Phase-2b1 call can consume two complete 67,108,864-byte passes and return one
extra byte at the second EOF probe before rejection, the successful-prefix plus
one terminal overshoot/failure call is bounded by 268,435,457 returned payload
bytes. The audit aborts on that first error or budget excess, so the failure
cannot repeat across claims. At most `16*9,999=159,984` event filenames pass
the Phase-2b1 scan-1 count, exact event-name, and path-metadata gates and become
eligible for descriptor payload observation. Each such logical file is one
admission. `event_file_admission_upper_bound` means only that unit; it excludes
scan-2 iterator occurrences and all stat/read calls. EOF calls returning zero,
directory metadata, and seed bytes are outside the payload-byte counter but
have separate call/count/seed bounds. The output reports the accepted total,
fixed read-work bound, and fixed event-file admission bound.

Phase-2b1 inspection results are reduced to the 16-field record and discarded
one at a time; `event_files` from multiple claims are never retained together.

All ID tuples and `claim_audits` are ASCII sorted and unique. Their exact
derivations are:

```text
seeded_missing_ids     = IDs with set_relation=seeded_missing_local
local_orphan_ids       = IDs with set_relation=local_orphan
receipt_mismatch_ids   = IDs with receipt_relation=mismatch
terminal_ids           = IDs with chain_observation=valid_terminal
nonterminal_ids        = IDs with chain_observation in
                         {valid_nonterminal,
                          valid_nonterminal_index_exhausted}
empty_chain_ids        = local-member IDs with chain_observation=missing
```

`seed_count`, `local_directory_count`, `union_claim_count`,
`unexpected_entry_count`, and `examined_claim_count` are respectively the
exact lengths of the seed tuple, valid-local-ID tuple, ID-set union,
unexpected-name tuple, and `claim_audits`. In every returned audit,
`examined_claim_count == union_claim_count`. The three aggregate booleans are
derived exactly as:

```text
all_seeded_local_present = seed_count > 0 and seeded_missing_ids is empty
all_seeded_terminal = seed_count > 0 and every seeded ID is in terminal_ids
all_seeded_receipts_match =
    seed_count > 0 and every seeded ID has receipt_relation=exact_match
```

## 8. Aggregate status and exact negative suffix

`coverage_status` precedence is:

1. `empty_seed` only when seed, valid local set, and unexpected-name set are all
   empty;
2. `matched_terminal` only when the seed is nonempty, there are no unexpected
   entries, seed/local ID sets are equal, every seeded receipt exactly matches,
   and every seeded chain is `valid_terminal`; and
3. `mismatched` otherwise, including an empty seed with any local or unexpected
   evidence.

`matched_terminal` means only that every caller-seeded claim was observed as a
terminal structurally valid local chain at its own sequential Phase-2b1
observation. It is not called `complete`, `verified`, `CLEAR`, or remote claim
coverage.

Every returned aggregate fixes:

```text
auditor_schema_version = lean-rgc-uprime-u1-seed-local-inventory-auditor-v0.1
auditor_scope = caller_seed_vs_entire_local_attempt_namespace
origin_status = unknown_may_be_synthetic
seed_origin = caller_supplied_synthetic_bytes
seed_binding = exact_bytes_within_call
seed_temporal_commitment = not_authenticated
remote_inventory_observation = not_performed
real_claim_completeness = not_authenticated
omitted_claim_detectability = local_orphans_only_none_if_absent_from_both
coordinated_omission_detectability = none
root_scope = one_caller_supplied_synthetic_root
snapshot_scope = sequential_per_claim_observations_not_atomic_inventory
resource_status = within_frozen_bounds
authority_scope = none
canonical_run_authority = false
licenses_execution = false
licenses_publication = false
licenses_recovery = false
licenses_later_stage = false
```

`base_directory_status` is `absent` or `present`. `set_equality` compares only
the exact seed/local valid-ID sets; unexpected names are separately blocking.
The aggregate `seed_file_sha256`, `seed_identity_sha256`, and `seed_count` are
copied from the seed reparsed inside this audit call, never from a caller-
constructed record or separate argument.
`all_seeded_local_present`, `all_seeded_terminal`, and
`all_seeded_receipts_match` are false for an empty seed to prevent vacuous
truth. All status booleans are derived, never caller inputs.

## 9. Coordinated omission and selective-evidence kill

The API has no selected license/filter/pagination/early-success parameter. It
must account for the entire seed and entire bounded local base in one call.
This prevents selecting only a favorable seeded claim or silently ignoring a
local orphan.

It cannot detect coordinated omission from both the seed and local root. The
acceptance matrix contains two synthetic universes where the supplied seed and
root are byte-identical over claim A but an external fixture additionally
knows claim B. Both calls necessarily return the same result, and the result
must expose `coordinated_omission_detectability=none` and
`real_claim_completeness=not_authenticated`. No solve-rate, coverage,
exposure, or claim-completeness statistic may be derived from this audit.

## 10. Finite Phase-2b2a acceptance matrix

Before a result commit, the support, frozen four-file profile, and default
collection must pass with zero failures/errors; the frozen profile has zero
skips/xfails. Required finite families are:

1. independent literal seed bytes, standard/domain-separated hashes, exact
   16/16/43-field records, annotations, frozen/slots tuples, ordered `__all__`,
   and all negative authority constants;
2. seed BOM/CRLF/LF/spacing/order/duplicate/UTF-8/float/surrogate/trailing
   failures, top/receipt missing-extra-wrong-bool fields, exact-type raw,
   N-1/N/N+1 byte/claim bounds using actual bytes and injected small byte
   limits, sorted order, duplicate license/ref, wrapped receipt-constructor
   errors, and empty seed;
3. input mutation after parse cannot change the immutable seed; the audit
   reparses raw and rejects a caller-constructed or bypass-mutated seed object;
   a stateful `PathLike` is evaluated once and all base/inspection paths use
   the retained `root_text`;
4. absent-at-both-points and empty base, appearance between absence checks,
   exact present D0/D1 and two-scan success, initial/final base non-directory,
   symlink, and reparse rejection, reversed enumeration, second-scan
   insertion/deletion/replacement/metadata drift, final base drift, and every
   base stat/scan/close/candidate-entry-stat failure;
5. valid lowercase-hex64 child directory; exact-hex64 regular-file/symlink/
   reparse/non-directory candidates statted and retained as unexpected; safe
   alternate case, Unicode lookalike, short/long name, Windows device, ADS-like
   colon, trailing-dot/space, and nonhex file/directory spellings retained as
   unexpected with zero child join/stat; injected empty/dot/dotdot/separator/
   U+0000/non-UTF-8/duplicate names rejected before child join/stat; exact
   UTF-8-byte ordering, unexpected-name UTF-8 bound, total entry/local/
   unexpected N-1/N/N+1, and streaming max+1 no-further-stat proof;
6. seed/local exact match, seeded missing, local orphan, receipt mismatch with
   a separately valid local chain, Phase-2b1 `missing`, nonterminal, index
   exhausted through an injected module-local public
   `AttemptManifestChainInspectionV10` result, terminal, corrupt, and injected
   Phase-2b1 I/O rejection; corrupt/I/O cases raise the one public error and
   return no per-claim or aggregate result;
7. every two-set combination including empty/empty, nonempty/equal, disjoint,
   proper seed subset, and proper local subset; sorted exact per-claim records,
   count/list equality, endpoint/null mappings, and status precedence;
8. per-claim byte-sum N-1/N/N+1 using injected small bounds, successful-prefix
   plus one terminal failing/overshoot call bounded by exactly
   268,435,457 returned payload bytes at production constants, Phase-2b1
   scan-1 logical file admissions bounded by 159,984 (explicitly not generic
   scan/stat observations), abort before any later claim, and no partial result
   on resource rejection;
9. favorable-claim selection impossible by signature, orphan cannot be hidden,
   and the coordinated-omission pair produces indistinguishable scoped output
   with mandatory incompleteness labels;
10. exact imports/signatures/AST, no writes or directory creation, production
    raising sentinels, collector uniqueness, source/support/amendment anchors,
    literal/SHA/Git-blob default-deny registry, no exposure marker, and no
    `runs/` delta.

All filesystem fixtures are test-created under `tmp_path`. There are no
threads, sleeps, races, subprocesses, Git calls in the source, network, Lean,
worker, registered experiment path, or GPU action.

## 11. Stop rule

Commit and push of this reviewed amendment license only the exact read-only
Phase-2b2a implementation on local Windows CPU. A later committed result with
the frozen zero-skip Windows profile and green Ubuntu CI licenses only
Phase-2b2b preregistration.

Even `matched_terminal` proves neither seed completeness nor simultaneous
terminality. Phase 2b2a does not observe artifact existence, create an event,
write a manifest, stage bytes, execute fake or real CAS, inject a fault,
authenticate power loss, issue a witness, acquire a recovery epoch, recover an
attempt, authenticate a claim/ref/Git object, license a worker or rerun, contact
a network/SSH host, or construct on GPU. Phase 2b2b--2b2f implementation,
Phase 2c, canonical diagnostic, M2c, U'0.5, and U'2--U'5 remain barred.
