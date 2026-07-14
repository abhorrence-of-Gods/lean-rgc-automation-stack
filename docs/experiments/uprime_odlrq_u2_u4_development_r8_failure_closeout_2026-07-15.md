# U-prime / ODLRQ U2--U4 R8 failure closeout

Date: 2026-07-15 (Asia/Tokyo)

Status: `U24_R8_B0_CONTROL_BLOCKED`

R8 bootstrap disposition: `UNLICENSED LOCAL COMMIT QUARANTINED / REMOTE-ABSENT AT 2026-07-15 02:38 JST / NOT ACCEPTED`

Scientific interpretation: `NON_MATHEMATICAL_B0_SYNTHETIC_ROW_SCHEMA_FAILURE`

R8 is terminal at its first official dirty B0 invocation.  That invocation
did not produce a qualifying success receipt; its synthetic-row failure source
is identified retrospectively from the later direct clean trace and the
byte-identical, unconditional common probe.  A later local commit and second
invocation were discipline violations; neither licenses R8.

## 1. Authority and exact failed bytes

This closeout follows the R7 failure closeout at commit
`a9113a0d9b834b744a05d7eaceab40153d32e2fe` (`F7`), tree
`84991dd1a1ed131976060a53f58348cbc0532061`, and the stopping rule in section
15 of
`uprime_odlrq_u2_u4_development_r8_tracked_universe_reentry_amendment_2026-07-15.md`.
That rule says that a dirty or clean official lane failure stops immediately,
permits at most one R8 failure closeout, and makes the bootstrap correction
available only to an otherwise qualifying locally green B8 whose repository
CI is red.

A closeout commit is valid only as the immediate sole-parent child of exact
F7, with exactly this one changed path at mode `100644`:

```text
docs/experiments/uprime_odlrq_u2_u4_development_r8_failure_closeout_2026-07-15.md
```

Any other parent, extra changed path, or mode is not an R8 closeout.

The exact four dirty paths presented to the first official B0 were later
captured without byte changes in the unlicensed local commit.  Their frozen
identities are:

| first-B0 state | bytes | raw SHA-256 | Git blob | committed mode | path |
|---|---:|---|---|---|---|
| untracked | 116892 | `FCF4AD9FB80E88D96DFE8D8682D8FBE63E530C869636627F74AB6A931FD0484D` | `61aad0ff3240b4d17b191b4f0b36392971b5bddb` | `100644` | `docs/experiments/uprime_odlrq_u2_u4_development_r8_tracked_universe_reentry_amendment_2026-07-15.md` |
| modified | 136453 | `560AE893CAB7D2AB0EF9C9482465634D58AB9B0B822F20C1940607255208700A` | `f142c39dd89d233a1a79099714b4fd04698b3223` | `100644` | `tests/test_uprime_u2_u4_development.py` |
| modified | 92161 | `606A8606446C7B80846ACC834822C1A68A3EB08841D3F49E7D8FB3B02918BBF3` | `988432367c7f9ba174ab9c326d64d413e6d64582` | `100644` | `tests/uprime_u24_guard.py` |
| modified | 168626 | `AFFB04D458821B2B95E4BF9BD8AE30B520774E4441E08FDD50DCB7E8CC06E5B2` | `289b88e5ad3104e03fd31c83cfbac285ccc248fc` | `100644` | `tools/run_uprime_u2_u4_development_tests.ps1` |

These identities preserve failed inputs.  They do not attest a B0 pass or
retroactively authorize the commit that contains them.

## 2. First failure and later violations

The registered dirty B0 was invoked once on the exact four-path state above.
The orchestration surface reported only `Script completed`; it did not expose
runner stdout or meaningful exit semantics, and no qualifying `5 passed`
result or success receipt was captured.  The root operator mistakenly read
that message as success and created this unlicensed local bootstrap commit:

```text
branch codex/uprime-u2-u4-development-r8-tracked-universe-bootstrap
commit 6616eb3fc3473dedd7e8f49e4a2d01cd98487fd4
parent a9113a0d9b834b744a05d7eaceab40153d32e2fe
tree   f40de0bb645205e20056b2e07a8c5cdb33112dc8
```

A purported clean B0 was then invoked on that byte-identical exact4.  This
second invocation directly exposed the following trace: local helper
`synthetic_row` supplied `tree_modes` but omitted `tree_blobs`, and
`_assert_e2_commit_prefix` called `_modes`, which required the missing key.

```text
source = synthetic_row(...)
_assert_e2_commit_prefix([source], accepted_b8_commit=b8)
  -> _modes(source)
  -> blobs = row["tree_blobs"]
KeyError: 'tree_blobs'
```

Static control-flow audit establishes that, after the registered dirty- or
clean-topology checks, both lanes unconditionally reach this one common
synthetic probe in the same identity bytes.  The clean trace therefore fixes
the dirty failure source retrospectively as the same missing `tree_blobs` row.
It is not a direct dirty traceback.  Inspection at that point also revealed
that the first B0 had not qualified.  Creating the commit and making the
second invocation both violated R8 section 15: the first nonqualifying B0 had
already stopped R8.  The second observation diagnoses the control defect but
is not a registered result and cannot repair the first failure.

The operator record contains no push command.  Independently, a remote audit
at 2026-07-15 02:38 JST found no exact bootstrap ref, found no exact commit SHA
(the commit API returned `422`), and found zero Actions runs.  These are
time-scoped audit facts, not an unbounded claim about all later remote state.

## 3. Zero scientific exposure and publication

According to the operator record and local/remote audit at 2026-07-15 02:38
JST, each of the following counts was zero at that audit point:

| event or capability | count |
|---|---:|
| operator-recorded push command through the audit point | 0 |
| remote exact B8 ref at the audit point | 0 |
| remote exact B8 SHA at the audit point (`commit` API returned `422`) | 0 |
| GitHub Actions run for the exact B8 ref/SHA at the audit point | 0 |
| R8 accepted-ref fast-forward through the audit point | 0 |
| E2 scientific source creation | 0 |
| E2 import, compile, collection, or scientific pytest endpoint | 0 |
| E2 source-freeze, result record, or scientific artifact | 0 |
| GPU/CUDA use | 0 |
| SSH or remote-CPU use | 0 |
| LLM/model-server/proposer use | 0 |
| protected K/KP execution | 0 |

The two local B0 observations were control-plane Python diagnostics only.
They provide no evidence for or against the finite-horizon envelope, exact
restriction replay, lifting-uniform safety, cocycle, return-memory, MaxEnt,
similarity, integrated certificate, or any other upper-stack scientific
claim.

## 4. Terminal disposition

The section 15 bootstrap correction is ineligible: there was no qualifying
locally green committed B8 followed by red repository CI.  R8 therefore has
no correction, rerun, amendment, or scientific continuation.  Only a
separately dated and preregistered R9 may continue.

The local branch and commit `6616eb3fc3473dedd7e8f49e4a2d01cd98487fd4`
must not be rewound, deleted, rebased, amended, force-pushed, or presented as
accepted history.  At the 2026-07-15 02:38 JST audit point the exact remote
ref/SHA was absent and the operator record contained no push command.  The
branch and commit remain locally quarantined as immutable evidence of the
discipline violation.  This closeout records the failure; it does not repair
the quarantined exact4.

For a possible R9 only, the narrow future fix is to add `tree_blobs` to the
`synthetic_row` fixture and to capture an explicit runner exit receipt so an
orchestration-level `Script completed` message cannot be mistaken for a lane
pass.  Neither fix is implemented in R8.
