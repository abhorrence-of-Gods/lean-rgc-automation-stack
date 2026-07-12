# U-prime / ODLRQ KP3 depth-4 canonical-history feasibility amendment

Date: 2026-07-12 (Asia/Tokyo)

Status: **FROZEN ONLY WHEN THE EXACT FIVE-PATH AMENDMENT COMMIT IS COMMITTED,
PUSHED, AND HOSTED-CI GREEN.**

This is a new phase after the immutable lane-isolated recovery closeout.  It
does not extend M4--M6, reopen U05, or claim that a result on a new task family
continues the old U05 rank sequence.

## 1. Authority, parent, and the question actually being tested

The sole parent of the amendment commit is:

```text
5bb86a43fbd05731dd7e5db25394995139854805
```

The parent closeout blob is:

```text
docs/experiments/uprime_odlrq_lane_isolated_recovery_closeout_2026-07-12.md
5061650434a1fb5dde29ff1b6dd1e48fdb117182
```

The phase asks a bounded engineering and finite-model question:

> Can generation-time exact-state history aggregation remove the depth-four
> word-table bottleneck while preserving every raw occurrence, the frozen
> `ExactOccurrenceResponse`, and the raw-coordinate Hankel matrix on a newly
> registered public development family?

It does **not** ask whether the old U05 family has `r_4 = 10`.  That question is
not executable from the committed result.  The U05 artifact stores an outer
envelope and aggregate reports, not its in-memory state, transition, word, or
Hankel tables.  Worker states and live handles were released.  Reconstructing
the missing table would require a prohibited same-family RPC rerun.  Therefore:

```text
old U05 r_1,r_2,r_3 = 5,10,10
fresh-family r_1,r_2,r_3,r_4
```

are two separate sequences.  They are never concatenated, pooled, or described
as one plateau.

Here `fresh` means only new frozen IDs and bytes with zero old-artifact/table
read.  The tasks were hand-authored after U05 and are structurally related
development examples; they are not independent, unexposed, held out, or a
statistical sample.  Coincident response values are possible and are not
evidence of data reuse.  This is a D4 plumbing/mechanical-feasibility family,
not a nondegenerate compression, memory-only, or generalization stress test.

## 2. Historical CI adjudication retained

The immutable U05 result-publication commit
`cc91a4181a9f87ec10f11727ed787eb7149f955a` has red GitHub Actions run
`29166670576` (job `86580832840`).  The dated audit determined that the failure
was caused by the identity guard's shallow-history design omission, not by a
probe, prerequisite, artifact-integrity, or scientific-result failure.  The
exact scientific candidate at `3bb3408afc50a08307cff2c9b1906a299739dfb5`
had green run `29166073728` (job `86579287017`).  The red result-commit badge
must not be interpreted as a failed scientific execution.  The consumed look,
immutable result values, result commit, and rerun prohibition remain unchanged.

The recovery amendment's distinct red run `29178759991` (job `86612624356`)
was a post-closeout guard-lifecycle defect and was repaired by green successor
`40cb97a8...` before M4.  The new identity guard uses full Git history and raw
commit parents; it does not reintroduce either shallow-history failure mode.

## 3. External provenance and no-copy boundary

The design input is:

| source | SHA-256 | permitted use |
|---|---|---|
| `fiber_closure_generator_part2_jp.tex` | `FED9A116D04E56D41FC6A306B1C85CA85399B92375322ED45EED546E4FE126A7` | completed finite-support structural techniques and explicit warnings |
| `fiber_closure_generator_part2_experiments.zip` | `1FA90B92C0998FAEC941F658BA295B34790568924022A068EFC2CA03C69C95E2` | static algorithm-pattern inspection only |

The archive contains 337 entries and no traversal, absolute-path, or symlink
entry, but it contains no LICENSE, COPYING, NOTICE, or SPDX grant.  No source,
CSV, generated number, or binary from the archive is copied or executed.  The
Lean-side implementation is a no-copy independent reimplementation based on
the documented ideas; this is not a claim of legally isolated clean-room teams.

Provenance is tiered rather than flattened:

| status in the source | transferred item | treatment here |
|---|---|---|
| completed on declared finite supports | generation-time normal forms, tree-history elimination, first-order closure audit, ghost/memory warning | translated into exact finite Lean invariants and adversarial tests |
| completed only on a selected separator support | nonadditive gluing and one rank-one correction | warning and later measurement interface only; no universal rank-one claim |
| recommended construction order | exact quotient before positive majorant | retained as later U'2 order; no envelope is built here |
| listed as future performance work | packed exponents, exact/float two-layer engineering, interface parallelism | not cited as a completed NS implementation; packed words are deferred |

The archive actually uses tuple exponents rather than a packed-integer
implementation.  Tuple action words are therefore the reference representation
in this phase.  A packed representation may be introduced only after byte-for-
byte equality with the tuple reference under a later amendment.

## 4. Frozen public development inputs

The amendment commits the task and action matrices before implementation or
native execution:

| input | file SHA-256 | canonical JSON SHA-256 |
|---|---|---|
| `docs/experiments/inputs/uprime_kp3_d4_fresh_tasks.json` | `C0B5428DCB7174CB96F469E38E229043AF47B9E9ECF684797FF45EE8AE4163A0` | `814BFBC235B6E464013637210E1C5382B0CED5AEB0C8D50C9C282E3236202D62` |
| `docs/experiments/inputs/uprime_kp3_d4_actions.json` | `FC9FB44E8E5D6929712CE15DC2D6F93FCCA74B81EE99C9EAF55D13B76A0CCF51` | `BE4AC0348631D0D7E3ABCA3DD22A05240E1D86B494B21FDBB47EF7FADA99FB1A` |

The canonical digest is over the complete wrapper object using strict UTF-8,
lexicographically sorted object keys, separators `(',', ':')`,
`ensure_ascii=False`, no NaN/Infinity, and **no trailing line feed**.  The
canonical payload-list digests are respectively
`402410B252C71EFFF250437D9715ECA7A39F433BE056DF5D1997D9EB2FDECB95`
and `8A203CD2C993ABECECEE860A071C75E4C81A5E9E1D87CA37F8E7CC5AEEC879DE`.

The task matrix contains five hand-authored, openly committed development
tasks.  It is neither held out nor a statistical evaluation sample.  The
action matrix contains twelve semantically ordered actions under new `d4a*`
IDs.  Reusing the previously audited action *shapes* reads or copies no old
task, state, response, or result bytes; coincident semantic values remain
possible.

The old task IDs are permanent deny sentinels:

```text
u05_identity
u05_pair
u05_split
u05_nested_split
u05_nat_zero
```

The fresh evaluator must reject these IDs before task initialization.  It must
also reject the U05 artifact path, old task-matrix digest, old evaluator module
as an input provider, every reserved task source, and every quarantine input.
The exact deny anchors are:

| forbidden authority | frozen value |
|---|---|
| old artifact path | `docs/experiments/artifacts/uprime_u05_20260711/u05_kill_probes.json` |
| old artifact SHA-256 / Git blob | `75BD0F4A742FD7F5DA221FD629DA58F080FD17CB0ACE9BFC8150153D8FDB55F8` / `33061cffae56abf4ed2a4fcdb9400eb2004e61c6` |
| old task / action matrix SHA-256 | `C86569C9C5A793C842BD3F4D7E5795A16C5B6C0B8F6E806F3D30D6A8B571E0E3` / `6EA21704F48153362504D4AC7F753C30B8EF6FBDFB0FD98B15A37E56120D393D` |
| old evaluator path / Git blob | `lean_rgc/evals/uprime_u05_kill_probes.py` / `d47f99f90ff4cfb1332fde3de90c734fd8e876ed` |

Positive input authority is exactly the two committed §4 paths with both their
file and canonical digests.  Every other task/action source is denied.  Tests
for quarantine denial use literal decoy paths and must not enumerate or open
the real `$HOME/.codex/quarantine` shelf.

## 5. Immutable substrate through this phase

The following parent blobs remain unchanged:

| path | Git blob |
|---|---|
| `lean_rgc/odlrq/contracts.py` | `eca7d55bc7c2a7a08fbdc75c3b589f1972cd258f` |
| `lean_rgc/odlrq/rule_algebra.py` | `1deff84c42168c65c5fa1ef953cd51f5b772502e` |
| `lean_rgc/odlrq/reachable_chart.py` | `67204f31f03d228362132e5892ecb7c2832434f1` |
| `lean_rgc/odlrq/hankel.py` | `c724d1a31257ba7f63f55a2af6ae8c4acbbda387` |
| `lean_rgc/lean/kernel_state_identity.py` | `f9924024609d1ffd2ad60fe296b8bb9173dcd40d` |
| `lean_rgc/lean/kernel_rpc_client.py` | `ef5d81bff4c6ab4d8110fe6671f5e5b5f8bc263a` |
| `lean_rgc/native_lean/RGCKernelRPC.lean` | `305509d9b89081a3d002734e09724b98e244a24c` |
| `tests/test_uprime_u05_identity.py` | `277f46ec0e4cecfe6ae3d119adb85c2b3a043182` |
| `tests/test_odlrq_lane_isolated_recovery_identity.py` | `27f103c258b004a3e45bc33b5234303c675b64c7` |

In particular, historical `reachable_chart.py`, `hankel.py`, and
`uprime_u05_kill_probes.py` are not edited to admit cutoff four.  New semantics
live in new modules and cannot alter the old U05 disposition.

## 6. Mathematical object to code contract

| theoretical object | code owner | frozen operational meaning | independent test/witness |
|---|---|---|---|
| finite total-domain coverage | `history_normal_form.FiniteTotalActionDomain` | every admitted OPEN representative has exactly one sealed/replayed row for each action; terminal outcomes are totalized; no censor or unresolved frontier | source-bound row coverage rederived from the complete representative domain |
| history normal form | `history_normal_form.HistoryGrammar` | `exact_state_merge` is exact for pure finite C1 systems and conditional on `CanonicalKStateMarkovContract` for native C2; behavioral `terminal_tail_absorb` keeps provenance outside the class; no action swap/deletion/observed alias | deterministic first-occurrence representative, idempotence, reconstruction, and mutation rejection |
| generation-time compression | `history_normal_form.CanonicalHistoryChart` | successors enter the depth layer already normalized; every incoming `(class, action)` contribution retains a hash-consed witness edge while class weights are derived, not trusted | generation-time versus batch reference equality on small fixtures |
| raw denominator | `CanonicalHistoryLayer.raw_multiplicity` | every class weight obeys local flow conservation; terminal absorption applies the same transition flow; layer totals are a secondary check | independent verifier recomputes every class weight from seed weights and edge incidence |
| native Markov scope | `CanonicalKStateMarkovContract` | explicit unproved substrate assumption: equal canonical identity plus full signature under one frame/transition semantics has path/live-handle-independent registered-action behavior | one-step duplicate-row comparisons are falsification only, never a congruence proof; every native result carries a conditional scope label |
| depth-three equivalence oracle | `RawNormalizedEqualityReport` | enumerate all 9,425 fresh-family words and compare `ExactOccurrenceResponse` field by field within the sealed representative domain | a separately coded raw transition walker; one mismatch is fatal relative to that domain |
| depth-four raw Hankel | `hankel_depth4.ExactRawCoordinateHankel` | retain 785 raw rows and 1,099 raw columns; canonical lookup evaluates `prefix ++ suffix`, while an independent walker reconstructs all coordinates from the same sealed representative domain | compare all 123,245 word coordinates and all 862,715 channel cells; bind the matrix digest and conditional scope to rank certificates |
| exact rank screen | `hankel_depth4.ExactRankCertificate` | for each `H_1` through `H_4`, an exact independent basis plus complete-row span verification when rank is at most 64, or 65 independent rows as a lower-bound witness | independent verifier redoes elimination from immutable raw coordinate keys and the verified matrix digest |
| conditioning | result field only | frozen `null` with censor `NOT_ATTEMPTED_IN_THIS_PHASE`; no official float computation occurs | any non-null official value is a schema failure |

The history grammar deliberately has no adjacent-swap rule in this first
phase.  Lean action words are noncommutative.  Sorting actions, `aa -> a`,
deleting an apparent no-op, or merging by seven-channel equality is forbidden.
An OPEN merge requires full exact state equality and full-signature comparison,
not merely equal debt or response.  A terminal behavioral class retains the
terminal kind; exact first-entry task/source/action/word provenance belongs to
the raw occurrence response and is never a class key.

`ExactOccurrenceResponse` is a frozen tagged record.  OPEN values contain the
outcome kind, state identity key, complete canonical state signature, exact
five-coordinate debt, and full occurrence-response signature.  Terminal values
contain the terminal kind and exact first-entry task, source identity, action,
and full word.  The seven Hankel channels are a named projection of this record,
not the complete response type.

Sealed state rows and occurrence provenance are different types.  A terminal
row stores only `TerminalTransitionKind` and replay evidence.
`TerminalOccurrence` is constructed when that row is applied to a raw query
word; cached representative provenance is never copied to another occurrence.

Native merging relies on the frozen `CanonicalKStateMarkovContract`: for one
frame, totalization, transition semantics, and action grammar, equal canonical
identity plus equal full signature is assumed to make every registered action
path/live-handle independent.  This phase does not prove that assumption.  Its
prior evidence is the strict U'0/U'1 identity construction, independent replay,
and the published zero response-mismatch diagnostic; those are not promoted to
a theorem.

For up to 128 distinct incoming duplicate OPEN occurrences, C2 retains the
live handle long enough to compare its complete immediate twelve-action row
with the representative under independent replay.  This is a bounded
one-step falsification audit.  It can reject an immediate hidden-handle
dependency but cannot certify or exclude delayed dependence.  Child handles
are released after comparison.  Native E1 exactness is therefore always
labelled `CONDITIONAL_KSTATE_MARKOV`; C1 hand-built finite-domain exactness is
unconditional.  No result is called an arbitrary-depth closure theorem.

Behavioral class weights satisfy, for every layer and class `v`,

```text
m[d+1,v] = sum(m[d,u] for every registered (u,a) contribution targeting v).
```

The independent verifier recomputes this equation from seed weights and edge
incidence.  Terminal behavior is aggregated only by kind.  When a raw word is
queried, a separate transition walker constructs its `TerminalOccurrence` from
that word's own first terminal prefix.  It also streams all 113,105
depth-at-most-four raw words to compare the complete behavioral-class histogram
and every occurrence provenance record without retaining a raw word table.

This is the Lean translation of “generate on the normal form” without importing
commutative monomial semantics.  It is also ghost-safe: an action with no
immediate registered response change remains in the alphabet and may alter a
later continuation.

## 7. Frozen dimensions, caps, and preflight order

With five tasks and twelve actions:

```text
raw words through depth 3 = 5 * (1 + 12 + 12^2 + 12^3) = 9,425
raw words through depth 4 = 5 * (1 + 12 + 12^2 + 12^3 + 12^4) = 113,105
D4 rows                    = 5 * (1 + 12 + 12^2) = 785
D4 columns                 = 7 * (1 + 12 + 12^2) = 1,099
D4 raw cells               = 785 * 1,099 = 862,715
```

All input-only structural arithmetic is checked signed-64 arithmetic before
task initialization, word generation, transition execution, cache allocation,
or Hankel materialization.  Source-dependent byte bounds are checked after the
finite domain is sealed but before canonical-layer, raw-coordinate, rank, or
final-report materialization.  The document does not pretend that unknown
native signature lengths can be bounded before they are read.

| resource | frozen cap |
|---|---:|
| raw equality depth | 3 |
| canonical construction depth | 4 |
| raw depth-three occurrences | 15,000 |
| raw depth-four occurrences | 150,000 |
| unique OPEN states total | 1,024 |
| state/action transition rows | 12,288 |
| unique-row primary attempts | 12,288 |
| unique-row independent replay attempts | 12,288 |
| duplicate incoming OPEN occurrences retained for one-step falsification | 128 |
| duplicate-row action comparisons / primary / replay | 1,536 each |
| canonical task-history classes | 50,000 |
| generation contribution edges | 300,000 |
| raw D4 Hankel cells | 1,000,000 |
| exact rank | 64; row 65 becomes a lower-bound stop witness |
| exact integer/rational numerator or denominator | 8,192 bits |
| one canonical state/response signature | 64 KiB UTF-8 |
| all canonical state/response signatures | 8 MiB UTF-8 |
| canonical report bytes | 64 MiB |
| process working set | 2 GiB |
| captured runner output | 64 MiB |

The observed NS compression numbers and any fresh-family compression observed
during this phase never waive a cap.  If the uncompressed dimension preflight
does not fit, the corresponding construction does not start.

The canonical artifact schema contains the source/environment binding, finite
domain, transition kinds, duplicate-row falsification digests, layer classes,
contribution edges, per-class multiplicities, raw-coordinate/matrix digests,
four exact rank certificates, and a required null conditioning field with
`NOT_ATTEMPTED_IN_THIS_PHASE`.  It does not serialize dense rational
reconstruction coefficients.  Variable records use only these compact indexed
canonical-JSON arrays:

```text
transition = [source_idx, action_idx, kind_code, target_idx_or_null,
              replay_digest_idx]
duplicate  = [left_occurrence_digest_idx, right_occurrence_digest_idx,
              compared_row_digest_idx]
class      = [depth, task_idx, kind_code, state_idx_or_null, multiplicity]
contribution = [source_class_idx, action_idx, target_class_idx, witness_idx]
```

Task/action strings, signatures, and unique 64-hex-character digests are stored
once in bounded dictionaries charged to `total_signature_utf8_bytes` or fixed
metadata, never repeated in an edge.  Tests construct every index/count at its
maximum frozen value and require canonical encoded lengths of at most 256,
256, 256, and 64 bytes respectively.  For each
`H_k`, the certificate stores raw coordinate digests, basis row indices, pivot
columns, and the elimination-transcript digest; the independent verifier
recomputes independence and every-row span exactly from the matrix.

Before allocating those arrays, the source-bound conservative byte estimate is

```text
R_upper = 1 MiB
        + total_signature_utf8_bytes
        + 256 * transition_rows
        + 256 * duplicate_row_checks
        + 256 * canonical_classes
        +  64 * contribution_edges
        + 2 MiB for four rank certificates, digests, and fixed metadata.
```

Every multiplier is an inclusive canonical-JSON upper allowance, not an
observed average.  With the frozen individual caps, `R_upper < 64 MiB` is
required before layer/report construction.  Exact arithmetic also enforces the
8,192-bit coefficient cap during streaming elimination.  The final canonical
byte length is checked again before atomic publication.

## 8. Work packages and exact allowlists

### 8.1 A0: amendment and full-history identity guard

The amendment commit changes exactly:

```text
docs/experiments/uprime_odlrq_kp3_d4_canonical_history_amendment_2026-07-12.md
docs/experiments/inputs/uprime_kp3_d4_fresh_tasks.json
docs/experiments/inputs/uprime_kp3_d4_actions.json
tests/test_odlrq_kp3_d4_identity.py
tests/tier_manifest.json
```

It appends only `test_odlrq_kp3_d4_identity.py: ["unit"]` to the manifest.
The guard uses `git --no-replace-objects`, raw commit parents, full-history
ancestor checks, immutable predecessor blobs, exact per-commit allowlists, and
a self-sealing amendment identity blob.  A0 must be pushed and green before C1.

### 8.2 C1: pure canonical-history and raw-D4 core

C1 changes only:

```text
lean_rgc/odlrq/__init__.py
lean_rgc/odlrq/history_normal_form.py
lean_rgc/odlrq/hankel_depth4.py
tests/test_odlrq_history_normal_form.py
tests/test_odlrq_hankel_depth4.py
tools/run_uprime_kp3_d4_history_tests.ps1
tests/tier_manifest.json
```

The manifest appends exactly the two new test rows as `unit`.  The argumentless
Windows runner selects exactly those two modules, has a 30-second hard wall,
requires elapsed at most 10 seconds, and enforces the 2 GiB/64 MiB caps.  It
uses only hand-built `unit_kp3d4_*` finite systems and performs no native Lean
call or input-file read.

### 8.3 C2: fresh-family native adapter and fixed execution runner

C2 changes only:

```text
lean_rgc/evals/uprime_kp3_d4_canonical_history.py
tests/test_uprime_kp3_d4_canonical_history.py
tools/run_uprime_kp3_d4_native_tests.ps1
tools/run_uprime_kp3_d4_fresh_execution.ps1
tests/tier_manifest.json
```

The manifest appends only the native-adapter unit test.  The unit runner has a
30-second wall and 10-second qualification margin and uses a fake strict RPC
transport.  The fixed execution runner accepts no task path, action path,
output path, budget, retry, or selector argument.  It reads only the two
registered input files, launches local Windows CPU Lean, and has:

```text
whole-run wall     3,600 seconds
per action wall       30 seconds
working set            2 GiB
captured output        64 MiB
```

The frozen native identity checked before the durable run-open marker is:

| component | required identity |
|---|---|
| OS/runtime | Windows x86-64; platform record stored verbatim in the result |
| PowerShell parent | Windows PowerShell `5.1.26100.8655`, executable SHA-256 `0FF6F2C94BC7E2833A5F7E16DE1622E5DBA70396F31C7D5F56381870317E8C46` |
| Python | CPython `3.13.7`, executable SHA-256 `D932E5E2F324D57F392E8FD063DCF6D0185BE8A664C57C6D24E7762ED02C28CA` |
| Lean | `4.31.0`, commit `68218e876d2a38b1985b8590fff244a83c321783`, x86_64-w64-windows-gnu Release |
| executed Lean binary | SHA-256 `9B216DEB50D37C32C829D1EFAAA5BAFD5560417D382DF35A815489E31A31593F` |
| native worker source | `lean_rgc/native_lean/RGCKernelRPC.lean` blob `305509d9b89081a3d002734e09724b98e244a24c` |
| Python RPC client | `lean_rgc/lean/kernel_rpc_client.py` blob `ef5d81bff4c6ab4d8110fe6671f5e5b5f8bc263a` |
| implementation | the unique accepted hosted-CI-green C2 commit and tree derived by the identity guard |

The runner uses a minimal allowlisted environment, records its canonical
content digest, clears proxy/model/CUDA variables, disables network use, and
denies SSH, GPU, LLM, arbitrary subprocess, and shell execution at runtime.
The official process graph permits only the frozen PowerShell parent, the exact
Python executable, and the exact Lean binary at the frozen v4.31.0 toolchain
path with the registered worker invocation.  It does not spawn `elan.exe` for
resolution.  Unit runners permit no child process at all.

The adapter expands every unique OPEN representative through all actions to a
fixed point.  It additionally retains at most 128 distinct incoming duplicate
OPEN occurrences for the bounded one-step falsification audit described in
§6.  An immediate hidden-live-handle-dependent fake must be rejected; a delayed
fake demonstrates why the native result remains conditionally scoped rather
than falsely passing a congruence theorem.  A depth-four frontier discard is
not a total representative domain.  The 12,288-row and 30-second limits are
independent fail-closed resource envelopes; their simultaneous worst case is
not promised to fit the 3,600-second wall.

### 8.4 E1-R and E1-C: artifact, then consolidated closeout

After C1 and C2 are each committed, pushed, and hosted-CI green, exactly one
official fixed execution is made in a clean dedicated worktree on the frozen
result candidate ref `codex/uprime-kp3-d4-result`.  Before the first native task
initialization, the parent exclusively creates the final artifact path with a
canonical `RUN_OPENED` marker, flushes it, and calls the Windows durable-file
primitive.  Any existing marker or result permanently denies another run.
Success or an ordinary captured failure atomically replaces that marker.  A
process or OS crash may leave `RUN_OPENED`; that is a final incomplete
execution, not a retry license.

The marker is itself a complete parseable artifact variant.  Before opening it
already binds schema version, C2 commit/tree, C2 CI, both input digests, all
native identities, and `run_state="RUN_OPENED"`; it sets
`scientific_disposition="D4_EXECUTION_FAILED"`, the failure reason to
`process_or_os_terminated_after_open`, and matrix/rank/conditioning fields to
explicit null.  A recovered process commits that marker unchanged.  Every
ordinary success/failure replacement is atomically installed and durably
flushed before the runner reports completion.

E1-R changes only:

```text
docs/experiments/artifacts/uprime_kp3_d4_20260712/fresh_family_d4.json
```

The artifact binds C2 commit/tree and CI, native identities, input digests,
run-open state, exact scientific disposition, matrix/rank certificates, and
the required null conditioning field.  E1-R has one immutable commit and no
repair.  If candidate CI is red, the accepted line is unchanged.  If candidate
CI is green, E1-R fast-forwards the accepted line and a distinct accepted-line
CI runs.  A red accepted-line CI does not change or rerun the scientific
artifact; E1-R remains the accepted immutable head and the closeout adjudicates
the green candidate run and red accepted control-plane run separately.

Only after E1-R CI adjudication does E1-C add exactly:

```text
docs/experiments/uprime_odlrq_kp3_d4_canonical_history_closeout_2026-07-12.md
```

The closeout records every result branch/commit/run/job and distinguishes a
scientific disposition from CI control-plane status.  It is the final commit
of this phase.  There is no pre-open or post-open control-plane repair license,
no silent retry, and no receipt/CAS/ledger/publisher hierarchy.

E1-C uses fixed ref `codex/uprime-kp3-d4-closeout` and one commit with no
repair.  If E1-R candidate and accepted CI are green, E1-C's sole parent is the
accepted E1-R commit.  If E1-R candidate CI is green but accepted CI is red,
E1-C's sole parent is also the accepted immutable E1-R commit and records both
runs without a scientific rerun.  If E1-R candidate CI is red, E1-C's sole
parent is the unchanged accepted C2 commit and its document references the
immutable result ref/hash/run without importing the artifact.  In every case E1-C must have
green candidate CI before fast-forward and green accepted CI afterward.  A red
E1-C candidate leaves the accepted line unchanged and stops the phase.

## 9. Commit and candidate-branch topology

```text
5bb86a4 closeout
  -> A0 on codex/uprime-kp3-d4-a0, one commit, candidate CI green,
       accepted fast-forward and accepted CI green
  -> C1 on codex/uprime-kp3-d4-c1
       (one semantic commit + at most one same-work-package repair)
       -> accepted fast-forward only after candidate CI green
       -> accepted CI green before C2
  -> C2 on codex/uprime-kp3-d4-c2
       (one semantic commit + at most one same-work-package repair)
       -> accepted fast-forward only after candidate CI green
       -> accepted CI green before E1-R
  -> E1-R on codex/uprime-kp3-d4-result, one immutable artifact commit
       -> candidate green / accepted green: E1-C parent E1-R
       -> candidate green / accepted red: E1-C parent E1-R; both runs adjudicated
       -> candidate red: accepted stays C2; E1-C parent C2, result ref cited only
  -> E1-C on codex/uprime-kp3-d4-closeout, one closeout-only commit,
       candidate green -> accepted FF/green, last in this phase
```

These five candidate refs are fixed and are never force-pushed, deleted, or
restarted.  Every CI run is retained for the closeout.  C1/C2 have at most two
commits on their one ref; a second red commit stops that work package.  A red
candidate never enters the accepted line.  Unused repair quota is not
transferable.  The first semantic commit makes exactly the registered manifest
append; a repair commit leaves the manifest byte-identical.  The A0 identity
guard self-seals by locating the unique A0 addition and requiring every
descendant to retain `_tree_blob(A0, identity_path)`; it does not embed its own
future blob hash.  Deterministic unit tests are covered by this amendment and
do not receive per-test preregistration documents.  E1-C is the only later
experiment document.

## 10. Required adversarial tests

At minimum the implementation must include:

1. strict UTF-8, duplicate-key, unknown-field, subclass, bool-as-int, signed-64,
   mutation, and source-authority rejection;
2. normalizer termination, determinism, idempotence, reconstruction, witness
   mutation, and input/task/action permutation invariance;
3. a noncommuting `a;b` versus `b;a` fixture that would be corrupted by sorting;
4. a one-step response no-op whose later continuation differs, proving ghost
   actions are retained;
5. same identity key with different full signature, debt, or response rejected;
6. two task/word histories merging to one OPEN state and then taking one closing
   row produce distinct correct `TerminalOccurrence` provenance records;
7. every class satisfies local flow conservation, its independently streamed
   raw histogram count, and the secondary layer-total check;
8. generation-time aggregation equal to an independent batch reference on
   small systems;
9. all 9,425 fresh-family depth-at-most-3 `ExactOccurrenceResponse` records
   equal to canonical lookup field by field;
10. every one of the 123,245 D4 raw word coordinates and all 862,715 channel
    cells equal to an independent transition-walking raw oracle;
11. separate `H_1`--`H_4` basis-independence and complete-span verification,
    plus a rank-65 lower-bound fixture bound to row/pivot coordinates and
    matrix digest;
12. cap failure before oracle, word, cache, matrix, or report materialization;
13. cold/warm cache and `PYTHONHASHSEED` independence;
14. old U05 IDs, artifact, old task digest, quarantine, SSH, GPU, network, and
    LLM access denied before task initialization;
15. unit runners reject arguments, all child subprocesses, `exec`, `os._exit`,
    and `nt._exit`; the official runner admits only the frozen
    PowerShell-to-Python-to-Lean process graph and rejects every other child;
16. an immediate hidden-live-handle-dependent fake makes the one-step audit
    fail, while a delayed fake proves that the result schema cannot emit an
    unconditional native-exactness label;
17. the official conditioning value is exactly null with
    `NOT_ATTEMPTED_IN_THIS_PHASE`; a non-null value is rejected.

Rank equality alone never validates normalization.  Absence of a sampled
counterexample never admits a rewrite.  The independent raw oracle must not
call the canonical producer being tested.

## 11. Dispositions and stopping rules

C1 has one success disposition:

```text
CANONICAL_HISTORY_CORE_VERIFIED
```

E1 records exactly one of:

```text
D4_FRESH_FAMILY_COMPLETED_CONDITIONAL_KSTATE_MARKOV
D4_FRESH_FAMILY_RANK_ABOVE_CAP_CONDITIONAL_KSTATE_MARKOV
D4_NORMALIZATION_UNSOUND
D4_DOMAIN_INCOMPLETE
D4_RESOURCE_BLOCKED
D4_EXECUTION_FAILED
```

`D4_FRESH_FAMILY_COMPLETED_CONDITIONAL_KSTATE_MARKOV` reports `r_1..r_4`, raw
dimensions, exact certificate kind, the fixed null conditioning field,
raw-weighted class counts, and coverage.  It is not a pass/fail assertion that
rank must plateau.  Rank growth is recorded, not tuned away.  A rank above 64
is a contract-relative exact lower-bound witness, not a memory failure.

The phase stops immediately if:

- an old U05 task, artifact payload, reserved task, or quarantine input would
  have to be opened;
- a same-family U05 rerun, second protected look, or modification of a frozen
  historical module is required;
- the finite domain is not total and closed under all actions;
- a censor, replay mismatch, identity collision, incomplete full signature,
  unresolved frontier, or unverified transition remains;
- one raw/canonical depth-three cell, outcome, or provenance field differs;
- one independently streamed D4 coordinate/cell or class histogram differs;
- local flow, multiplicity, idempotence, reconstruction, one-step duplicate-row
  falsification audit, permutation, or certificate verification fails;
- any frozen construction, RSS, wall, output, or report cap is exceeded;
- depth-four raw words are materialized first and normalized afterward;
- outcome-dependent task/action/cap/rewrite changes are proposed;
- SSH, GPU, LLM, a new evidence ledger/CAS, or external coordination is needed.

Weak or zero compression is reported continuously and creates no categorical
post-look label.  If a frozen class/contribution cap is exceeded, the result is
`D4_RESOURCE_BLOCKED`; no cap is relaxed.  The official phase performs no float
conditioning after exact sealing; its conditioning field is fixed null.

## 12. Interpretation and program decision

This fresh family can answer whether the pure finite C1 implementation is
sound and whether a native raw D4 Hankel is computationally feasible relative
to the explicitly assumed canonical-KState Markov contract.  It neither proves
that contract nor answers the unavailable same-U05-family `r_4` question.

- If normalization is unsound or the finite domain cannot close, the canonical
  history path stops before any upper-stack dependency uses it.
- If exact rank exceeds 64, the large predictive/MaxEnt/similarity investment
  is deferred pending a separately registered scaling response; the lower-bound
  witness is retained.
- If D4 completes with rank at most 64, the bounded predictor remains a
  conditional engineering candidate on this fresh family.  Plateau or growth
  is reported as family-specific, contract-relative evidence, not a universal
  decision.
- No outcome in this phase creates a hard envelope or safety certificate.

## 13. Upper-stack sequence retained after this phase

The already reviewed upper theory is not re-litigated.  Its implementation
sequence remains:

```text
verified exact finite domain
  -> generation-time canonical history
  -> exact behavioral quotient
  -> quotient-coordinate generator
  -> positive finite-horizon worst-case majorant
  -> MaxEnt nominal law constrained inside that majorant
  -> predictive and positive global similarities with typed transports
```

`U'1.5-L0` is a separate nominal proposal/query track.  It retains ghost
actions, uses exact Lean counterexamples only to force splits, and measures any
separator correction rank instead of assuming rank one.  It does not construct
hard merges or upper bounds.  The hard U'2 track proceeds independently from
verified exact quotient coordinates; exact cancellation removes duplicate
representations before the positive majorant, but signed cancellation is never
a safety proof.  MaxEnt remains model selection, not the source of safety.

Only after a serial CPU reference is green may separate amendments consider
separator-aware parallelization, finite-quotient Poisson continuousization,
and nominal-only gradientization, in that order.  GPU work is reserved for a
later learned representation/acquisition model, never exact partition or hard
certificate construction.  LLM proposal or distillation remains last, after
the theory-driven generator and upper pipeline independently work, with a new
model/runtime/contamination amendment.

## 14. Mandatory nonclaims

This amendment licenses no old-U05 rerun or same-family depth-four claim,
protected K1--K4 result, production task result, complete all-germ quotient,
hard fiber envelope, MaxEnt fit, global-similarity certificate, locality-learner
improvement, solve-rate claim, deployment, SSH/GPU work, or LLM use.  It does
not transfer NS numerical compression, separator rank, physical coefficients,
or completion labels as Lean evidence.  A verified result is exact only for
its declared finite total development domain and raw response vocabulary.
