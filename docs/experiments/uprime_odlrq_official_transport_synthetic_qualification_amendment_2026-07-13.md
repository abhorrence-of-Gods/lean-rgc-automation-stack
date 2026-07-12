# U-prime / ODLRQ official-transport synthetic qualification amendment

Date: 2026-07-13 (Asia/Tokyo)

Status: **REGISTERED BEFORE ANY LIVE SYNTHETIC RPC EXECUTION**

Parent authority:
`249d2b1074b74f61c4f6eedcbabcab852ab5b317`, the accepted and green KP3-D4
closeout.  Its accepted CI was run `29213290583`, job `86704567410`, success.

This amendment is a narrow engineering response to the immutable E1 artifact
at
`docs/experiments/artifacts/uprime_kp3_d4_20260712/fresh_family_d4.json`.
That one-shot ended as `D4_EXECUTION_FAILED`: after durable `RUN_OPENED`, the
frozen `python -I -S` child attempted the normal `lean_rgc` package import path
and contemporaneous terminal output reported missing `numpy`.  The same
scientific endpoint is consumed and will not be rerun.

## 1. Registered question

The sole question is:

> Can a source-bound, standard-library-only Python leaf run under exact
> `-I -S -B`, complete a fixed public synthetic request sequence against the
> exact existing Lean RPC worker, and publish a strictly validated artifact
> through the Windows parent without importing `lean_rgc`, site packages, or
> any protected input?

This is not a KP3, rank, compression, quotient, envelope, MaxEnt, similarity,
learner, or proof-search experiment.  A green result qualifies only the new
stdlib leaf, the exact PowerShell-to-Python-to-Lean process graph, the existing
worker at its frozen blob, and the small publication boundary.

## 2. Immutable exclusions

The following paths are immutable and out of implementation scope:

```text
lean_rgc/evals/uprime_kp3_d4_canonical_history.py
tests/test_uprime_kp3_d4_canonical_history.py
tools/run_uprime_kp3_d4_native_tests.ps1
tools/run_uprime_kp3_d4_fresh_execution.ps1
docs/experiments/inputs/**
docs/experiments/artifacts/uprime_kp3_d4_20260712/**
lean_rgc/native_lean/RGCKernelRPC.lean
lean_rgc/lean/kernel_rpc_client.py
lean_rgc/__init__.py
```

The runner and its tests must reject access, import, or directory enumeration
of the registered KP3 inputs, the old U05 inputs/artifacts, quarantine roots,
SSH, GPU/CUDA, model/LLM configuration, and arbitrary user paths.  Reading the
frozen worker file and exact executable identities is allowed.  No scientific
task path is ever supplied.

## 3. Chosen architecture

The implementation is a new directly executed file:

```text
tools/uprime_official_transport_smoke.py
```

It is not a `lean_rgc` package module and does not add the repository root to
`sys.path`.  It may import only an explicit standard-library allowlist.  It
must not import or dynamically load `lean_rgc`, `importlib`, `runpy`, `site`,
`numpy`, or any third-party package.  It requires:

```text
sys.flags.isolated == 1
sys.flags.no_site == 1
sys.flags.ignore_environment == 1
sys.flags.safe_path == 1
__package__ in {None, ""}
loaded module names beginning with "lean_rgc" == []
```

An import fence rejects any later `lean_rgc` import request.  A Python-leaf
file-access fence rejects `lean_rgc/__init__.py`, every protected/excluded
root, and every path outside the exact leaf, worker, executable, and the one
freshly created parent-owned nonce run-temp subtree.  This audit hook does not
OS-sandbox the Lean child.  Instead the child receives no protected path or
capability, and the exact worker/fixture source contains no such access.  The
leaf directly implements the small strict JSONL subset needed by this fixture
instead of importing the frozen Python RPC client.  Therefore success does not
qualify that client, the C2 scientific adapter, or recursive Lean filesystem
confinement.

Namespace-package injection, `sys.modules` package stubs, lazy conversion of
the existing top-level package, ambient site-package access, and temporary
dependency installation are explicitly rejected designs.

## 4. Two-phase READY/ARM protocol

The live runner uses this order:

```text
exact Windows PowerShell 5.1 parent
  -> exact CPython 3.13.7: -I -S -B <verified leaf> --official-child
       -> built-in-only bootstrap blocks on the first stdin token
  -> parent assigns the exact Python process handle to the kill-on-close Job
  -> parent sends PROBE
       -> child completes stdlib imports and self-checks inside the Job
       -> import/file/process fences installed
       -> READY(nonce, pid, leaf/flags/sys.path digests,
                echoed parent Job-assignment receipt digest)
  -> parent strictly validates READY
  -> parent CreateNew-publishes and durably flushes a synthetic RUN_OPENED
  -> parent sends ARM with exact Lean/worker/temp capabilities
       -> child starts exact lean.exe --run exact-worker --imports Lean
       -> fixed synthetic JSONL sequence
       -> canonical nonce stage and receipt
  -> parent independently validates stage/receipt and child exit
  -> parent revalidates its exact RUN_OPENED bytes
  -> MoveFileExW(REPLACE_EXISTING | WRITE_THROUGH) replaces only that marker
```

Before valid PROBE, the leaf may use only built-in `sys` I/O and must remain
blocked.  Before valid ARM, Python cannot spawn Lean or any other subprocess
and has no result/stage path.  After ARM, further imports and arbitrary
subprocess calls are denied.  The only permitted child is the exact frozen Lean
executable with the exact worker argv.  `elan`, a shell, command strings, and
`shell=True` are forbidden.

The parent holds an exclusive named mutex derived from the fixed final path.
Before starting Python it requires the final artifact, stage, and receipt to be
absent.  An existing final destination is a permanent preflight failure.  In
the single owning invocation, replacement is allowed only after byte-for-byte
and digest revalidation of the exact marker written by that invocation.  An OS
or parent crash after marker creation therefore leaves a valid synthetic
`RUN_OPENED`; a captured ordinary or resource outcome replaces it.  A captured
pre-marker preflight failure publishes one canonical ordinary
`SYNTHETIC_ARTIFACT_BLOCKED` artifact to the previously absent final path.  The
archival invocation is not rerun after any disposition.

The durable marker is synthetic publication evidence, not a scientific look.
The phase performs one archival live run only after Q1 candidate and accepted
CI are green.

## 5. Frozen public synthetic fixture

The fixture is embedded as exact constants in the leaf and repeated here as
the registration authority:

```text
task_id         synthetic_isolated_identity_v1
imports         ["Lean"]
statement       ∀ (p : Prop), p → p
prefix          intro p\nintro h
max_heartbeats  20000

action_id       synthetic_exact_h
tactic          exact h
target_selector first
max_heartbeats  20000
```

The request order is exact:

```text
1 load_project
2 status                 require loaded, n_states == 0
3 init_state             require OPEN and one owned source
4 apply_tactic           require CLOSED and replay_status == verified
5 discard_state          discard the returned retained CLOSED child
6 discard_state          discard the original owned source
7 status                 require n_states == 0, primary == replay == 1
8 shutdown               require ack and natural Lean exit 0
```

Every request is canonical compact UTF-8 JSON followed by one LF.  Every
response is bounded before parsing.  The JSON envelope and each response's
top-level field set are exact.  The state summary, replay and replay-certificate
alias, target binding, and status-counter witness objects also have exact field
sets.  The leaf requires strict UTF-8, no duplicate top-level/selected-witness
keys, exact request ID and protocol version, expected ownership, verified
replay, CLOSED `kernel_state_after.status`, empty goals, and the fixed status
counters.  It stores the canonical digest of the complete response.  Recursive
qualification of every nested kernel/audit mirror is explicitly not claimed.
Raw task and traceback text are never stored in the artifact.

## 6. Artifact sum type

One parser is the semantic authority:

```text
parse_artifact_sum(raw) -> RunOpened | OrdinaryResult | ResourceResult
```

Every variant has an explicit `artifact_variant`, exact `run_state`, exact
field set, identity block, and canonical byte representation.  Q1's first
semantic commit is the exact READY, PROBE, ARM, receipt, identity-block, union,
ordinary-failure, resource-evidence, and payload schema authority.  All schemas
must be closed before any live execution and remain byte-identical in a Q1
repair commit.

| artifact variant | run state | allowed disposition | payload |
|---|---|---|---|
| `RUN_OPENED` | `RUN_OPENED` | `SYNTHETIC_EXECUTION_FAILED` | null |
| `ORDINARY` | `ORDINARY_RESULT_COMMITTED` | success or fixed ordinary failure | exact result object |
| `RESOURCE` | `ORDINARY_RESULT_COMMITTED` | `SYNTHETIC_RESOURCE_BLOCKED` | null plus fixed resource evidence |

Cross-variant combinations are invalid.  Common parsing rejects BOM, floats,
NaN/Infinity, duplicate/unknown/missing keys, noncanonical JSON, trailing
bytes, and over-cap input before full read.  The closed Q1 success payload must
contain the following evidence:

```text
import_fence_passed
loaded_lean_rgc_modules == []
job_assignment_receipt_digest
python_flags_digest
sys_path_digest
leaf_sha256
worker_blob and worker_sha256
process_graph_digest
rpc_protocol_version
request_count == 8
init_response_digest
transition_response_digest
closed == true
shutdown_ack_digest
natural_lean_exit_code == 0
ordered_transcript_digest
```

The PowerShell parent parses and independently checks the selected variant,
nonce receipt, repeated file hash, process disposition, and fixed identities
before atomic publication.

## 7. Frozen identities and caps

Q1 freezes the same local runtime identities already verified by C2:

| component | exact identity |
|---|---|
| Windows PowerShell | `5.1.26100.8655`, SHA-256 `0FF6F2C94BC7E2833A5F7E16DE1622E5DBA70396F31C7D5F56381870317E8C46` |
| CPython | `3.13.7`, SHA-256 `D932E5E2F324D57F392E8FD063DCF6D0185BE8A664C57C6D24E7762ED02C28CA` |
| Lean | `4.31.0`, commit `68218e876d2a38b1985b8590fff244a83c321783`, executable SHA-256 `9B216DEB50D37C32C829D1EFAAA5BAFD5560417D382DF35A815489E31A31593F` |
| worker | Git blob `305509d9b89081a3d002734e09724b98e244a24c`; SHA-256 `741E19237C829BA5E76E895EDB20ECD26517804C5CEE4FF8C711946739AB3A14` |

The parent receives accepted commit/tree, candidate/accepted run/job, and an
external ordinal canonical SHA-256 map for the exact Q1 allowlist.  It compares
those values with a clean dedicated accepted-tree checkout before starting the
child.  Expected digests are not minted from a dirty execution worktree and
are recorded with scope `EXTERNAL_CI_ATTESTATION_UNVERIFIED_BY_RUNNER`.

The hard live caps are:

```text
whole wall                 120 seconds
per RPC frame               15 seconds
natural shutdown exit       10 seconds
Job working set              1 GiB
stdout                       1 MiB
stderr                       1 MiB
single RPC response          4 MiB
artifact/stage/receipt       1 MiB each
task/action count             1 / 1
request count                 exactly 8
open states                   at most 2
```

Before the archival run, unprotected calibration may only tighten these caps
or show that the amendment is infeasible; it may not relax them.  Resource-path
tests use fault injection rather than changing production caps.

## 8. Commit topology and exact allowlists

Q0 is this one-file freeze commit on fixed ref:

```text
codex/uprime-official-transport-q0
docs/experiments/uprime_odlrq_official_transport_synthetic_qualification_amendment_2026-07-13.md
```

Q0 has exactly one commit and no repair commit.

Q1 is one semantic commit plus at most one same-work-package repair on fixed
ref `codex/uprime-official-transport-q1`.  Its first commit changes exactly:

```text
tools/uprime_official_transport_smoke.py
tools/run_uprime_official_transport_smoke.ps1
tools/run_uprime_official_transport_tests.ps1
tests/test_uprime_official_transport_smoke.py
tests/tier_manifest.json
```

The manifest appends exactly `test_uprime_official_transport_smoke.py` as
`unit`.  A repair leaves the manifest byte-identical.  Q1 candidate CI must be
green before accepted fast-forward, and accepted CI must be green before the
archival live run.

Q2 uses fixed ref `codex/uprime-official-transport-result`, one immutable commit
and no repair.  It adds exactly:

```text
docs/experiments/artifacts/uprime_official_transport_20260713/synthetic_qualification.json
docs/experiments/uprime_odlrq_official_transport_synthetic_closeout_2026-07-13.md
```

The result and closeout are deliberately bundled because the input is public,
synthetic, and non-scientific.  If the live run fails, its durable
`RUN_OPENED`, ordinary, or resource artifact and closeout are still committed
without Q1 repair or rerun.  Q2 candidate green precedes accepted fast-forward
and a distinct accepted CI.  If Q2 candidate CI is red, the accepted line
remains at Q1 while the Q2 ref/result/closeout stay immutable and the phase
stops.  If Q2 candidate is green but accepted CI is red, the accepted head
remains the immutable Q2 commit, the control-plane-red state is recorded, and
the phase stops without execution rerun or Q2 repair.

All three refs are fixed, never force-pushed, deleted, or restarted.  No new
identity guard is created: exact diff inspection, immutable Git commit/tree,
the external allowlist digest, and candidate/accepted hosted CI are the frozen
authority for this non-scientific phase.

## 9. Required tests

At minimum Q1 must test:

1. exact `-I -S -B` flags and no `lean_rgc` modules at READY and exit;
2. static AST rejection of `lean_rgc`, `importlib`, `runpy`, `site`, third-party
   import, repository `sys.path` insertion, shell, and arbitrary subprocess;
3. deliberate `lean_rgc` import and excluded-path open fail before Lean spawn;
4. READY nonce/PID/source/flags/sys.path mutation rejection;
5. Job assignment before PROBE, READY before marker/ARM, and no pre-ARM child;
6. exact worker process/argv only after ARM;
7. exact real worker load/status/init/apply/two-discards/status/shutdown sequence;
8. CLOSED, verified replay, ownership zero, shutdown ack, and natural exit 0;
9. request/response byte caps, timeouts, canonical JSONL, and ID/order binding;
10. worker/leaf/binary/allowlist digest mutation rejection before child start;
11. all three artifact variants and every invalid variant/state/disposition
    cross-combination;
12. duplicate/unknown/missing/float/noncanonical/trailing-byte rejection;
13. per-frame timeout, output overflow, memory cap, orphan cleanup, and at
    least one real Windows Job-containment/orphan-zero test distinct from
    branch-only fault injection;
14. child exit after ARM before stage leaves the exact synthetic RUN_OPENED;
15. crash at stage-before-receipt and receipt-before-replace is fail-closed;
16. stage hash double-read mismatch rejection;
17. success leaves no stage, receipt, temp, or live process;
18. runner arguments, ambient proxy/CUDA/model variables, and unapproved child
    processes are rejected;
19. unit runner obeys a 30-second wall, 10-second qualification gate, 1 GiB
    working-set cap, and 16 MiB captured-output cap;
20. the success schema and closeout cannot claim that C2, KP3, rank, quotient,
    upper stack, GPU, or LLM has been qualified.

## 10. Gates and dispositions

The sequential gates are:

```text
G0 Q0 candidate and accepted CI green
G1 Q1 unit/fault suite and fixed unit runner green
G2 Q1 candidate and accepted CI green
G3 clean accepted-tree identities and external allowlist digest exact
G4 one local Windows-CPU archival live run
G5 Q2 candidate and accepted CI green
```

The only archival dispositions are:

```text
SYNTHETIC_OFFICIAL_TRANSPORT_QUALIFIED
SYNTHETIC_EXECUTION_FAILED
SYNTHETIC_IMPORT_BLOCKED
SYNTHETIC_SCOPE_VIOLATION
SYNTHETIC_RPC_BLOCKED
SYNTHETIC_RESOURCE_BLOCKED
SYNTHETIC_ARTIFACT_BLOCKED
```

Any disposition closes the phase.  Only
`SYNTHETIC_OFFICIAL_TRANSPORT_QUALIFIED` permits drafting a separate work
package to port a future scientific adapter to this leaf boundary.  It does
not itself permit a scientific task execution.

## 11. Stopping rules and anti-fractal budget

Stop immediately if:

- a protected/registered scientific input, old result payload, quarantine, or
  same-family KP3 endpoint would have to be read or executed;
- one immutable path in section 2 would have to change;
- `numpy`, a third-party package, `lean_rgc` import, `-I/-S` relaxation,
  namespace injection, or ambient site package is required;
- READY occurs after ARM, Lean can spawn before ARM/Job assignment, or an
  unapproved process/network/SSH/GPU/LLM capability is needed;
- one RPC, replay, ownership, shutdown, artifact, receipt, atomic replace, or
  identity check fails;
- one frozen cap is exceeded or Q1's repair commit is red;
- the archival live run fails.  Record its disposition and close; do not repair
  Q1 or rerun the archival execution in this phase.

No EvidenceLedger, CAS, publisher abstraction, receipt registry, nonce
coordinator, reusable recovery framework, or per-unit preregistration document
may be added.  Stage/receipt remain two temporary files internal to the one
runner.  The work budget is 12 active implementation hours or two calendar
days, whichever comes first.  The definition of done is G0--G5 only.

## 12. Mandatory nonclaims and retained upper-stack order

This phase claims no repair or rerun of E1, no C2 client/adapter qualification,
no native canonical-KState contract, no D4 rank/compression/plateau, no exact
production quotient, no worst-case envelope, no MaxEnt law, no global
similarity, no locality-learner gain, no solve rate, and no deployment.  It
uses local Windows CPU only.  SSH, remote CPU, GPU, and LLM remain unlicensed.

The theoretical implementation order remains unchanged and gated:

```text
verified exact finite domain
  -> generation-time canonical history
  -> exact behavioral quotient
  -> quotient-coordinate generator
  -> positive finite-horizon worst-case majorant
  -> MaxEnt nominal law inside that majorant
  -> predictive and positive global similarities with typed transports
```

The separate locality learner remains nominal and counterexample-driven.  It
retains ghost actions, uses Lean counterexamples only to force splits, measures
separator correction rank, and supplies neither a hard merge nor a safety
bound.  LLM proposal/distillation remains last, after the theory-driven
generator and upper pipeline independently qualify under a new contamination
registration.
