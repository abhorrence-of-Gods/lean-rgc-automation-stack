# U'0.5 / U'1.5 one-look execution result

Date: 2026-07-11 UTC / 2026-07-12 JST

Status: **EXECUTION COMPLETE; `runner_complete`; `U05_COMPLETE`; ONE LOOK
CONSUMED.** U05-KP1, U05-KP2, and U05-KP3 all reached their preregistered
development-survivor dispositions. This result licenses only the drafting of
the separate CPU-survivor implementation-bundle amendment named in the frozen
plan. It does **not** license K1--K4, WP4--WP12 implementation, U'2--U'5 claims,
GPU work, reserved-data access, a canonical RPC rerun, MaxEnt, an envelope, or
similarity construction.

## 1. Frozen lineage and scheduling

The governing plan/amendment is
`docs/experiments/uprime_odlrq_upper_stack_implementation_plan_and_u05_amendment_2026-07-11.md`,
introduced at commit `0da9ff3de91819778761fb087e85e6f83e4c9ea4` with Git blob
`2b2355f49aef149c1a7b5493951fa10e4a254235`. The final execution candidate is
`3bb3408afc50a08307cff2c9b1906a299739dfb5`. The contiguous single-parent
implementation interval after the plan contains exactly the permitted four
commits:

| order | commit | parent | role |
|---:|---|---|---|
| 1 | `a78150ee403d28f78be75c44fe95d69e19a745a9` | `0da9ff3de91819778761fb087e85e6f83e4c9ea4` | strict U05 substrate |
| 2 | `8f19a0070e1df8bbeb209da14ad396b2d75e3ba7` | `a78150ee403d28f78be75c44fe95d69e19a745a9` | strict RPC lifecycle |
| 3 | `491b3c9424e98eaf5ae2dd719b05c22119473506` | `8f19a0070e1df8bbeb209da14ad396b2d75e3ba7` | one-look runner and sealed-row apparatus |
| 4 | `3bb3408afc50a08307cff2c9b1906a299739dfb5` | `491b3c9424e98eaf5ae2dd719b05c22119473506` | canonical empty-registry preflight repair |

The exact candidate was pushed before execution. GitHub Actions workflow `CI`,
push run `29166073728`, job `86579287017`, completed with conclusion `success`
at that head. Its workflow blob is
`bdeae23336653ce30b33aaad080c250435982089`.

An earlier launch at candidate `491b3c9424e98eaf5ae2dd719b05c22119473506`
stopped during pre-receipt preflight because the U05 runner checked an obsolete
empty-registry field name. Independent inspection found no receipt, matrix-open
marker, raw output, or artifact; only the one-byte process-lock file existed.
Consequently that launch did not open the matrix and did not consume the look.
The exact canonical registry repair was the fourth and final implementation
commit, was independently reviewed, pushed, and made green before the attempt
reported here.

The accepted run used a new disposable detached worktree. Before launch it had
exact candidate/upstream equality, Git branch name `HEAD`, zero status rows,
the frozen plan blob, four implementation commits, and no receipt, raw output,
marker, or artifact.

## 2. Command and execution boundary

The frozen Windows CPU command shape was executed with the bundled Python
recorded in the attempt receipt, `PYTHONNOUSERSITE=1`, and
`UPRIME_U05_EXECUTE=1`:

```text
python -m lean_rgc.evals.uprime_u05_kill_probes
  --repo-root .
  --anchor 3bb3408afc50a08307cff2c9b1906a299739dfb5
  --upstream refs/remotes/origin/codex/uprime-odlrq-plan
  --ci-workflow .github/workflows/ci.yml
  --ci-job pytest
  --accepted-ci-conclusion success
  --attempt-receipt runs/uprime_u05_20260711/attempt_receipt_3bb3408afc50.json
  --raw-output runs/uprime_u05_20260711/runner_raw_3bb3408afc50.json
  --artifact docs/experiments/artifacts/uprime_u05_20260711/u05_kill_probes.json
```

The outer process alone performed the read-only GitHub control-plane query.
The isolated measurement child and its Lean workers received no endpoint or
credential and ran inside a kill-on-close Windows Job Object. Tasks used fresh
workers sequentially. A concrete state/action row was executed and replayed
once; later cross-task occurrences used only exact, zero-attempt, handle-free
sealed-row derivations. No GPU, SSH, LLM proposer, protected benchmark,
reserved split, canonical RPC rerun, or external experimental data was used.

## 3. Byte-exact evidence

The tracked artifact is the byte-exact canonical outer envelope. The ignored
receipt, marker, and raw child output are preserved inside it as base64 with
their exact lengths and SHA-256 values.

| evidence | bytes | SHA-256 | Git blob |
|---|---:|---|---|
| attempt receipt | 109,988 | `E3225BE4AB7E3BE5E482B119352DD0A8F08891E6D7E9336859FB35FF2DF9D0BB` | `1b82d2b9b076933e8c777a7abe8be975448efeae` |
| matrix-open marker | 519 | `DB63010837D3A341991FE4F7044FD028CEAC514947A6C754DFC09CEAD9F5B059` | `d9606d29f388727d45b5a88b80a15a6392cda957` |
| raw child result | 9,208 | `704E05D66AB57633F015486C4C9E4718493A8A3529F3877693DD56B7CB79E6E9` | `f391cec0fff60fa8c69249899e236502b5afaabe` |
| tracked outer envelope | 160,974 | `75BD0F4A742FD7F5DA221FD629DA58F080FD17CB0ACE9BFC8150153D8FDB55F8` | `33061cffae56abf4ed2a4fcdb9400eb2004e61c6` |

The attempt ID is
`3BDF3E7D14B7B1884D4120F2CAD1FAEE2B5DF838253C05792994E249FC14C494`.
The marker was created at `2026-07-11T20:00:36.613534+00:00`; the envelope was
published at `2026-07-11T20:03:46.455908+00:00`.

The envelope reports:

```text
schema                  lean-rgc-uprime-u05-attempt-envelope-v1.0
envelope_kind           runner_complete
look_consumed           true
matrix_open_marker_valid true
raw_child_schema_valid  true
raw_child_status        U05_COMPLETE
process exit_code       0
stdout/stderr bytes     0 / 0
```

## 4. Frozen identity and environment

The raw task/action digests match the plan:

```text
task matrix   C86569C9C5A793C842BD3F4D7E5795A16C5B6C0B8F6E806F3D30D6A8B571E0E3
action matrix 6EA21704F48153362504D4AC7F753C30B8EF6FBDFB0FD98B15A37E56120D393D
```

The executed Lean identity was
`Lean (version 4.31.0, x86_64-w64-windows-gnu, commit
68218e876d2a38b1985b8590fff244a83c321783, Release)`. The principal environment
commitments are:

| field | value |
|---|---|
| Lean executable SHA-256 | `9B216DEB50D37C32C829D1EFAAA5BAFD5560417D382DF35A815489E31A31593F` |
| compiler runtime manifest | `DE92894E759ABA6B81CF86180CF0A4231EAC9B75E466A023D69F70F9A30DE000` |
| compiler build | `AD65105E495222445BF8CEA89E7FE8FBDB96CD196F33F0C86386A9E1751E0C91` |
| Lean dependency import, 12,114 files | `C9D291AD9146D7237BB83850284FA82BB66375AB651DF7AA42E38FE9A9163450` |
| strict worker source | `741E19237C829BA5E76E895EDB20ECD26517804C5CEE4FF8C711946739AB3A14` |
| environment content | `BEAD6DFC8F060A7F4E7D5F34696FB65BC9F286368EB9B2C8B09F57B2DF922C8B` |
| Python executable | `3C6A206B7D93CCA823934A83732220DCFFD413FD1036D9FB82EEBB64599CF7F3` |
| Python runtime, 12,372 files | `B7E987F771A92EBB22F4B917793B42A85EAF896EA2C42DCFB9AD9F1E88CA246D` |
| tracked `lean_rgc` source, 245 files | `0CCCC1DB6D6A00B3390CFFB989197FA0955FDC5DB878603E79F6038486CA9001` |

The rerun registry remained canonical, `default_allow=false`, with zero
licenses and Git blob `13ffca6de484effc66f0e628d2e46823277271c6`.

## 5. Prerequisites and costs

Every preregistered completion prerequisite was true:

- matrix literal digests verified;
- strict RPC schema verified;
- independent replay verified for every concrete row;
- prefix-closed chart complete;
- transition censor count zero;
- cache bypass and heartbeat caps verified;
- worker cleanup verified; and
- fresh worker per task verified.

The run used 5 tasks, 12 actions, and all 9,425 frozen word occurrences. It
produced 13 unique states and 156 sealed transition rows. Of those rows, 70
were concrete primary/replay executions and 86 were syntactic sinks. The 7
prefix executions give 147 total Lean tactic executions. Peak worker-owned
state count was 4; chart releases were 27 and final frontier discards 1. The
matrix phase elapsed time was 182.734 seconds. Every worker ended with zero
states and zero process-abort releases.

## 6. U05-KP1: exact-partition scale probe

Disposition: **`U05_KP1_SCALE_READY`**.

| cutoff | open occurrences | exact identities | exact compression | observation classes | observation compression | first closed / sink | derived closed / sink |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 6 | 3 | 2.0x | 3 | 2.0x | 10 / 44 | 0 / 0 |
| 2 | 28 | 8 | 3.5x | 7 | 4.0x | 10 / 94 | 120 / 528 |
| 3 | 44 | 8 | 5.5x | 7 | 44/7 = 6.2857x | 74 / 278 | 1,560 / 7,464 |

All three response-mismatch fractions were exactly zero. At cutoff 3 there
were 8 nontrivial exact identity classes spanning `u05_pair`, `u05_split`, and
`u05_nested_split`. This establishes useful exact compression on the frozen
fragment and satisfies the preregistered scale-readiness endpoint. It does not
establish coverage outside the five tasks, twelve actions, or depth-three
task-seeded universe.

## 7. U05-KP2: componentwise-window probe

Disposition: **`U05_KP2_EVENTUAL_WINDOW`**.

There were 74 successful trajectories, 20 eligible open steps, and 36 eligible
open blocks. Contractive blocks were 32/36: 16/20 at length one and 16/16 at
length two. The one-step noncontractive fraction was exactly `1/5`; the first
two debt coordinates each increased on `1/5` of eligible steps, while the
remaining three never increased. The longest noncontractive run was 1.

Thus the frozen fragment contains a componentwise eventual window while also
recording that one-step contraction is not universal. This is a predictive
fragment result, not a Lyapunov certificate, an episode-uniform bound, or a
license to advertise a hard envelope.

## 8. U05-KP3: response-Hankel probe

Disposition: **`U05_KP3_PLATEAU_AT_D3`**.

| cutoff | rows | suffixes | columns | cells | exact rank | increment | inverse condition ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5 | 13 | 91 | 455 | 5 | 5 | 0.0539740 |
| 2 | 65 | 13 | 91 | 5,915 | 10 | 5 | 0.0408444 |
| 3 | 65 | 157 | 1,099 | 71,435 | 10 | 0 | 0.0524665 |

The exact rational rank plateaued from cutoff 2 to cutoff 3 while the matrix
grew materially, and the preregistered numeric conditioning floor was met.
This makes a bounded Hankel predictive model a candidate on the frozen family.
It does not prove rank stabilization at larger depth or on another task/action
family.

## 9. Capability decision and nonclaims

The complete raw result sets the following three independent candidates and
their `may_draft` fields to true:

```text
candidate_exact_partition        true  (scale_ready=true)
candidate_componentwise_window   true
candidate_hankel_predictive_model true
```

The following remain false and pending later witnesses:

```text
candidate_finite_horizon_envelope false  pending_later_certified_upper_witness
candidate_maxent_nominal          false  pending_later_hard_envelope
candidate_predictive_similarity   false  pending_later_predictive_residual_endpoint
candidate_positive_similarity     false  pending_later_hard_positive_majorant
```

Every authority field in the raw result is false:

```text
licenses_k1_k4                    false
licenses_u2_u5_claims             false
licenses_wp4_wp12_implementation  false
licenses_gpu                      false
licenses_canonical_rpc_rerun      false
licenses_reserved_data_read       false
```

Accordingly, the result rejects neither the upper-stack program nor its three
measured substrate hypotheses, but it also does not freeze the upper theory or
authorize its construction. The only next action permitted by this result is
to draft, commit, push, and make green a separate CPU-survivor
implementation-bundle amendment. That amendment may select the exact
partition, componentwise-window, and Hankel branches; it must still register
the certified finite-horizon upper witness before envelope code, the hard
envelope before MaxEnt, the predictive-residual endpoint before predictive
similarity, and a hard positive majorant before positive similarity. GPU and
protected K-series execution remain behind the later Amendment A.

## 10. Verification and result-commit guard

Before the candidate was frozen, local verification reported 2,343 passed, 3
skipped, and 161 deselected tests; the native Windows RPC worker suite reported
4 passed. Three independent final reviews approved sequential/merge semantics,
raw/manifest validation, and one-look governance. Candidate CI run
`29166073728`, job `86579287017`, concluded successfully.

The result commit has candidate `3bb3408afc50a08307cff2c9b1906a299739dfb5`
as its sole parent and changes exactly these four paths:

```text
docs/experiments/uprime_odlrq_u05_execution_2026-07-11.md
docs/experiments/artifacts/uprime_u05_20260711/u05_kill_probes.json
lean_rgc/evals/uprime_rpc_litmus.py
tests/test_uprime_rerun_license.py
```

The test guard discovers the result commit from the added execution document,
requires that sole parent and exact diff, verifies regular Git blobs, freezes
the artifact SHA-256/Git blob and canonical result fields, requires both result
paths to appear exactly once in `ANCHOR_PATHS`, and confirms that the rerun
registry remains empty. The result commit's own ID and the self-referential
source/test/document blobs cannot be embedded in their own content; they are
reported after commit and are required as anchors by the next amendment.
