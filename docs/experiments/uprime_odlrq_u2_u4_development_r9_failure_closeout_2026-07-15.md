# U-prime / ODLRQ U2--U4 R9 failure closeout

Date: 2026-07-15 (Asia/Tokyo)

Status: `U24_R9_DIRTY_B0_CONTROL_BLOCKED`

Scientific interpretation: `NON_MATHEMATICAL_RAW_SOURCE_LITERAL_CONTRACT_FAILURE`

R9 is terminal at its first official dirty B0 invocation.  The invocation ran
the B0 child once, captured an unhandled control-plane traceback, and did not
produce the required `5 passed` result.  No rerun, control commit, candidate
push, accepted fast-forward, or E2 continuation is licensed.

## 1. Authority and exact closeout topology

R9 began at the immutable R8 failure-closeout commit
`66a7ed676c6bd8045d6ce6ea6d5d2a5177355b55` (`F8`), with parent
`a9113a0d9b834b744a05d7eaceab40153d32e2fe` and tree
`480f8826ee70ba2c12cd79ed9d7bf8895446b48a`.  Its authority is the dirty R9
amendment
`uprime_odlrq_u2_u4_development_r9_minimal_control_reentry_amendment_2026-07-15.md`,
whose section 5 stops R9 on any dirty-lane, process-outcome, identity, or scope
failure and permits only one failure closeout.

This closeout is valid only as the immediate sole-parent child of exact F8,
changing exactly this one mode-`100644` path:

```text
docs/experiments/uprime_odlrq_u2_u4_development_r9_failure_closeout_2026-07-15.md
```

It does not incorporate, commit, or repair the failed dirty exact-five state.

## 2. Exact dirty B0 inputs

The single official dirty B0 saw exactly these five worktree paths over F8:

| state | bytes | raw SHA-256 | Git blob | mode | path |
|---|---:|---|---|---|---|
| untracked | 116892 | `FCF4AD9FB80E88D96DFE8D8682D8FBE63E530C869636627F74AB6A931FD0484D` | `61aad0ff3240b4d17b191b4f0b36392971b5bddb` | `100644` | `docs/experiments/uprime_odlrq_u2_u4_development_r8_tracked_universe_reentry_amendment_2026-07-15.md` |
| untracked | 7585 | `8BFF52D7A70B1F1ABE17177405A8A2A89C7E787E99C800E5D01EE9BB8A3BA8B7` | `f28423f14e0741825a370e4bdb064e77039eff6b` | `100644` | `docs/experiments/uprime_odlrq_u2_u4_development_r9_minimal_control_reentry_amendment_2026-07-15.md` |
| modified | 138134 | `C9B5375376FD32E869C671ACE378562CD91D925FE4B19F5A54371617063B4357` | `9968578504c707a5b7d05dd440c825294959e788` | `100644` | `tests/test_uprime_u2_u4_development.py` |
| modified | 96400 | `14314C43A7E637B9616C625A5568620C4FAFFCAD2E7AEC56873935439007F83C` | `3702c6af1e6cef55e86072577318d3f67f25c713` | `100644` | `tests/uprime_u24_guard.py` |
| modified | 170371 | `92A28B1EE76E63B31C3067C8715BECF0952A332D2AA0BDC03473BA689D4D6528` | `7846ed06a014787581c98449f20805bc489f0b6d` | `100644` | `tools/run_uprime_u2_u4_development_tests.ps1` |

Before invocation, static checks confirmed canonical57, absent18, F8 ancestry,
the exact-five status, the R8 scientific-amendment wire binding, Python ASTs,
PowerShell parsing, and the non-circular mutual hash closure:

```text
identity core  333E4813427F333C886D8CC5A91E0391B13D144DD01816594F67E1B87878AFF7
guard core     C7BBB34EA96CFF37C1938122B6DEB27D68C443CC84FD41D39030EB373193C1F7
runner         92A28B1EE76E63B31C3067C8715BECF0952A332D2AA0BDC03473BA689D4D6528
```

Those static facts do not override the official B0 failure.

## 3. First official failure and capture facts

The wrapper started exactly one hidden, noninteractive Windows PowerShell child
with the frozen runner and `-Lane B0`, redirected its stdout and stderr to
unique repository-external files, and waited for completion.  The recovered
capture is:

```text
tag           u24-r9-dirty-b0-8fd69e6fcb274de7be0102d610f1c1c9
stdout bytes  0
stdout SHA256 E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855
stderr bytes  1278
stderr SHA256 1B2F23CD6982C5E15F6199EAA7F42EE98A20C3AE3437EA874A03C9F662804D2B
stdout UTC    2026-07-14T18:41:09.8729761Z
stderr UTC    2026-07-14T18:41:33.3452872Z
```

Stderr contains this terminal control trace:

```text
test_u24_denylist_static_scan_and_exact_runner_copy
  -> u24_guard.static_scan_union_sources(REPO_ROOT)
  -> _blocked("identity test lost a frozen B0 invariant: " + required)
U24ResourceOrScopeBlocked: U24_RESOURCE_OR_SCOPE_BLOCKED:
identity test lost a frozen B0 invariant:
docs/experiments/uprime_odlrq_u2_u4_development_r9_minimal_control_reentry_amendment_2026-07-15.md
```

The child therefore did not reach a B0 pytest summary.  After the child had
completed, the outer reporting wrapper itself attempted the unavailable
Windows-PowerShell-5.1 method `System.Convert.ToHexString` while formatting the
already captured digests.  It exited before printing the stored child exit
property.  The child exit code is consequently not an admissible recorded
fact.  This secondary reporting defect independently violates the explicit
outcome rule, but it does not obscure the primary B0 failure: complete stderr
contains an unhandled B0 traceback and stdout contains no `5 passed` result.
No second child was started.

## 4. Root cause and audit miss

The R9 identity defines `BOOTSTRAP_DOCUMENT_PATH` from adjacent split string
literals.  At Python runtime their value is the correct full R9 amendment
path.  The guard's static union scan, however, requires the full path as one
contiguous substring of the raw identity source.  That full substring is not
present across the split literal boundary, so the scanner fails closed.

The pre-execution multi-agent reviews checked runtime/AST equality, topology,
literal counts in the runner, and mutual hashes, but did not emulate this
raw-source substring loop against every required value.  Their green static
verdicts were therefore incomplete.  This is a control-test coverage defect,
not evidence about quotient dynamics, envelopes, MaxEnt, similarity, or the
Lean-oracle locality learner.

A future epoch may choose one narrow repair: place the registered path as a
contiguous identity-source literal or replace the raw substring condition with
an exact AST constant-value check.  R9 makes neither change.

## 5. Zero scientific exposure and terminal disposition

At the R9 stop point the following counts remain zero:

| event or capability | count |
|---|---:|
| R9 control commits | 0 |
| R9 candidate pushes or CI runs | 0 |
| accepted-ref fast-forwards or accepted CI runs | 0 |
| E2 scientific source creation, import, compilation, collection, or execution | 0 |
| E2 source-freeze/result documents or scientific artifacts | 0 |
| ME0, S0, or I0 execution | 0 |
| GPU/CUDA use | 0 |
| SSH or remote-CPU use | 0 |
| LLM/model-server/proposer use | 0 |
| protected K/KP execution | 0 |

The dirty R9 bootstrap worktree and its five exact bytes remain local evidence
over F8.  They must not be committed, amended, reset, rebased, pushed, merged,
cherry-picked, or presented as accepted history.  The invalid R8 bootstrap
`6616eb3fc3473dedd7e8f49e4a2d01cd98487fd4` remains separately quarantined and
is not an ancestor of this closeout.  R9 has no correction or rerun.  Any
continuation requires a separately dated and frozen epoch.
