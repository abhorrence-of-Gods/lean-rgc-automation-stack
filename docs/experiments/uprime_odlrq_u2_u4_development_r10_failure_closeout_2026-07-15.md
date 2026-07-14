# U-prime / ODLRQ U2--U4 R10 failure closeout

Date: 2026-07-15 (Asia/Tokyo)

Status: `U24_R10_DIRTY_B0_CONTROL_BLOCKED`

Scientific interpretation: `NON_MATHEMATICAL_DENYLIST_SUBSTRING_DOMAIN_FAILURE`

R10 is terminal at its first official dirty B0 invocation.  The registered
wrapper started the B0 child exactly once, but the invocation produced no
required `5 passed` result and emitted a complete control-plane traceback.
No rerun, control commit, candidate push, accepted fast-forward, or E2
continuation is licensed.

## 1. Authority and exact closeout topology

R10 began at the immutable R9 failure-closeout commit
`6fb521b50ee375a9f01fe464ed313aff5f02431e` (`F9`), with parent
`66a7ed676c6bd8045d6ce6ea6d5d2a5177355b55` and tree
`60b01892a2559219d92b9957eca9ad4a06e4eac2`.  F9 changes only
`docs/experiments/uprime_odlrq_u2_u4_development_r9_failure_closeout_2026-07-15.md`,
mode `100644`, blob `4cabbea1b4760b0914794313cd19252d852e021c`,
`6879` bytes, raw SHA-256
`D8E186C6B3D5F65669C40FE153D0216AC1451FEC16F3EF092D0F48AE5B28F6D6`.

F9's CI run `29359255679`, job `87174809137`, attempt `1`, was red with
exactly `1 failed, 2599 passed, 8 skipped, 161 deselected`.  As frozen in the
R10 amendment, its sole failure was inherited identity topology that could
not admit the F9 closeout child; it was not a scientific endpoint result.

The dirty invocation was governed by the exact R10 amendment:

```text
path   docs/experiments/uprime_odlrq_u2_u4_development_r10_minimal_control_reentry_amendment_2026-07-15.md
bytes  10299
SHA256 8A6DB02A8604F6D9F373907C85C7C8CCC5E48036F9F950443E0E943AA449A354
blob   b79d7b57158594bb64defbecfd57f534dbb80cf9
mode   100644
```

That amendment has correction budget zero and stops R10 on any static-scope,
process, stream, B0, or result-count failure.  This closeout is valid only as
the immediate sole-parent child of exact F9, changing exactly this one
mode-`100644` path:

```text
docs/experiments/uprime_odlrq_u2_u4_development_r10_failure_closeout_2026-07-15.md
```

It does not incorporate, commit, or repair the failed dirty exact-five state.

## 2. Exact dirty B0 inputs

The single official dirty B0 saw exactly these five worktree paths over F9:

| state | bytes | raw SHA-256 | Git blob | mode | path |
|---|---:|---|---|---|---|
| untracked | 116892 | `FCF4AD9FB80E88D96DFE8D8682D8FBE63E530C869636627F74AB6A931FD0484D` | `61aad0ff3240b4d17b191b4f0b36392971b5bddb` | `100644` | `docs/experiments/uprime_odlrq_u2_u4_development_r8_tracked_universe_reentry_amendment_2026-07-15.md` |
| untracked | 10299 | `8A6DB02A8604F6D9F373907C85C7C8CCC5E48036F9F950443E0E943AA449A354` | `b79d7b57158594bb64defbecfd57f534dbb80cf9` | `100644` | `docs/experiments/uprime_odlrq_u2_u4_development_r10_minimal_control_reentry_amendment_2026-07-15.md` |
| modified | 138960 | `3BCA0EEF77CEEE4B49C482C50B812BEF88929D733EC7621A6B9AF627E959C658` | `0f6e538d44d24471294f980477bb79c6deeed7d2` | `100644` | `tests/test_uprime_u2_u4_development.py` |
| modified | 102373 | `F604E8B5DE376AC3FB0AAAFDAF1CA3D35D09DE65CB7353598BF4B5A043218BB2` | `0748d35530fa495086243896c2da7fa1e100bacd` | `100644` | `tests/uprime_u24_guard.py` |
| modified | 170974 | `E8E0B6DCDAE1A4F8C11AC1A63BE6BB459875561B720A3B7BCB17FDED3EDB3D2A` | `e094aeba629f00e4f34717f18a74fc182ab55dea` | `100644` | `tools/run_uprime_u2_u4_development_tests.ps1` |

Before invocation, independent static reviews confirmed the F9 ancestry, the
exact-five status, canonical60, absent20, the amendment wires, Python ASTs,
both embedded Python programs, Windows PowerShell 5.1 parsing, and the
non-circular mutual hash closure:

```text
canonical tracked paths  count 60 / bytes 4201
canonical SHA256         8632556B9A03C061885A2A61E2553DE0BF1434EC78D98B6B5D9F638D08BB5645
designated absent paths  20, all absent at exact F9
identity core            B3A275B6955974129C731A343B68CC5E29B34CCB7FB98E3D0840A782E2E78496
guard core               CEA55B7465D1BE94827E7289C2220603FB112DAD850C72B3198BFBEDE61F5D4C
normalized runner        E8E0B6DCDAE1A4F8C11AC1A63BE6BB459875561B720A3B7BCB17FDED3EDB3D2A
64-digit zero bindings   0
```

Those byte and topology facts do not override the official B0 failure.

## 3. First official invocation and complete capture

The frozen wrapper started one hidden, noninteractive Windows PowerShell 5.1
child with the registered runner and `-Lane B0`, redirected both streams into
a fresh repository-external directory, waited for completion, and printed the
following complete receipt.  No second child was started.

```text
CHILD_EXIT=0
TAG=u24-r10-b0-113c4c5e18f34d6d8781f7c77e989b5d
CAPTURE_DIR=C:\Users\yusei\AppData\Local\Temp\u24-r10-b0-113c4c5e18f34d6d8781f7c77e989b5d
STDOUT_BYTES=0
STDOUT_SHA256=E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855
STDOUT_BASE64=
STDERR_BYTES=1200
STDERR_SHA256=B6A9FD9B1C74E765DEF0F664C7747AD79D1AAF2EE356019122F187BAD6456CFE
STDERR_BASE64=VHJhY2ViYWNrIChtb3N0IHJlY2VudCBjYWxsIGxhc3QpOg0KICBGaWxlICJDOlxVc2Vyc1x5dXNlaVxBcHBEYXRhXExvY2FsXFRlbXBcbGVhbi1yZ2MtdTI0LWQzZjlkMzk1NTg3NzQzMmM5ZTRlODVhYmYxMDIwM2ExXGJvb3RzdHJhcC5weSIsIGxpbmUgMTA0MSwgaW4gPG1vZHVsZT4NCiAgICBpZiBmdW5jdGlvbigpIGlzIG5vdCBOb25lOg0KICAgICAgIH5+fn5+fn5+Xl4NCiAgRmlsZSAiQzpcVXNlcnNceXVzZWlcRGVza3RvcFxsZWFuX3JnY19hdXRvbWF0aW9uX3N0YWNrX3Y0N19nb2FsX3N0YXRlX2R5bmFtaWNzX3UyX3U0X3IxMF9ib290c3RyYXBcdGVzdHNcdGVzdF91cHJpbWVfdTJfdTRfZGV2ZWxvcG1lbnQucHkiLCBsaW5lIDIyNDgsIGluIHRlc3RfdTI0X2RlbnlsaXN0X3N0YXRpY19zY2FuX2FuZF9leGFjdF9ydW5uZXJfY29weQ0KICAgIHUyNF9ndWFyZC5zdGF0aWNfc2Nhbl91bmlvbl9zb3VyY2VzKFJFUE9fUk9PVCkNCiAgICB+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fl5eXl5eXl5eXl5eDQogIEZpbGUgIkM6XFVzZXJzXHl1c2VpXERlc2t0b3BcbGVhbl9yZ2NfYXV0b21hdGlvbl9zdGFja192NDdfZ29hbF9zdGF0ZV9keW5hbWljc191Ml91NF9yMTBfYm9vdHN0cmFwXHRlc3RzXHVwcmltZV91MjRfZ3VhcmQucHkiLCBsaW5lIDIyNTMsIGluIHN0YXRpY19zY2FuX3VuaW9uX3NvdXJjZXMNCiAgICBfYmxvY2tlZCgicnVubmVyIHJlcGVhdHMgYSBmb3JiaWRkZW4gbGl0ZXJhbCBvdXRzaWRlIGl0cyBkZW55bGlzdCIpDQogICAgfn5+fn5+fn5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXg0KICBGaWxlICJDOlxVc2Vyc1x5dXNlaVxEZXNrdG9wXGxlYW5fcmdjX2F1dG9tYXRpb25fc3RhY2tfdjQ3X2dvYWxfc3RhdGVfZHluYW1pY3NfdTJfdTRfcjEwX2Jvb3RzdHJhcFx0ZXN0c1x1cHJpbWVfdTI0X2d1YXJkLnB5IiwgbGluZSAzOTUsIGluIF9ibG9ja2VkDQogICAgcmFpc2UgVTI0UmVzb3VyY2VPclNjb3BlQmxvY2tlZChmIntERU5JQUxfRElTUE9TSVRJT059OiB7bWVzc2FnZX0iKQ0KdXByaW1lX3UyNF9ndWFyZC5VMjRSZXNvdXJjZU9yU2NvcGVCbG9ja2VkOiBVMjRfUkVTT1VSQ0VfT1JfU0NPUEVfQkxPQ0tFRDogcnVubmVyIHJlcGVhdHMgYSBmb3JiaWRkZW4gbGl0ZXJhbCBvdXRzaWRlIGl0cyBkZW55bGlzdA0K
```

The two capture files are strict byte authorities.  Their UTC last-write
timestamps are `2026-07-14T19:22:53.6955065Z` for stdout and
`2026-07-14T19:23:17.5170881Z` for stderr.  The stderr Base64 above is length
1600 and round-trips exactly to the recorded 1200 bytes and SHA-256.

Decoded stderr terminates as follows:

```text
bootstrap.py:1041
  -> test_u24_denylist_static_scan_and_exact_runner_copy:2248
  -> u24_guard.static_scan_union_sources:2253
  -> _blocked:395
U24ResourceOrScopeBlocked: U24_RESOURCE_OR_SCOPE_BLOCKED:
runner repeats a forbidden literal outside its denylist
```

The wrapper explicitly reported `CHILD_EXIT=0`, while stdout was empty and
stderr contained the unhandled traceback.  The zero status is therefore not
success evidence; it is an additional process-status propagation
inconsistency.  Independently, unexpected stderr and the absence of exactly
`5 passed, 0 skipped, 0 xfailed, 0 deselected` violate the frozen outcome
contract and are sufficient to stop R10.

## 4. Root cause and audit miss

The sole denylist row that appears outside the runner's marked denylist is the
filesystem prefix `runs/`.  It occurs exactly twice, only inside these GitHub
Actions API routes:

```text
/repos/$CandidateRepository/actions/runs/$RunId
/repos/$CandidateRepository/actions/runs/$RunId/jobs?filter=all&per_page=100&page=1
```

The guard compares every filesystem denylist row to the entire remaining raw
runner source with untyped substring membership.  It therefore treats the
network-route component `runs/` as the protected filesystem prefix `runs/`
and fails closed.  No `runs/` filesystem access and no protected-data read
occurred.  This is a string-domain separation defect in the control layer,
not evidence about quotient dynamics, envelopes, MaxEnt, similarity, or the
Lean-oracle locality learner.

R9 stopped at an earlier identity raw-literal defect, so this later check had
not been reached.  The R10 pre-execution reviews verified parsing, topology,
literal authority, and mutual hashes, but did not independently emulate the
complete denylist-row by outside-runner substring product.  The hashes
correctly attested frozen bytes; they did not establish that this raw
substring predicate would accept them.

A future, separately frozen epoch may domain-separate filesystem paths from
API routes or replace substring membership with a typed, segment-aware
predicate.  R10 makes neither repair.

## 5. Zero scientific exposure and terminal disposition

At the R10 stop point the following counts remain zero:

| event or capability | count |
|---|---:|
| R10 control commits | 0 |
| R10 candidate pushes or CI runs | 0 |
| accepted-ref fast-forwards or accepted CI runs | 0 |
| E2 scientific source creation, import, compilation, collection, or execution | 0 |
| E2 source-freeze/result documents or scientific artifacts | 0 |
| ME0, S0, or I0 execution | 0 |
| native Lean or RPC execution | 0 |
| GPU/CUDA use | 0 |
| SSH or remote-CPU use | 0 |
| LLM/model-server/proposer use | 0 |
| protected K/KP execution | 0 |

The dirty R10 bootstrap worktree and its exact five bytes remain local
evidence over F9.  They must not be committed, amended, reset, rebased,
pushed, merged, cherry-picked, or presented as accepted history.  The invalid
R8 bootstrap `6616eb3fc3473dedd7e8f49e4a2d01cd98487fd4` and dirty R9 state remain
separately quarantined and are not ancestors of this closeout.  R10 has no
correction or rerun.  Any continuation requires a separately dated and frozen
epoch.
