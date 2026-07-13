# U-prime / ODLRQ official-transport v2 administrative failure closeout

Date: 2026-07-13 (Asia/Tokyo)

Status: **FINAL — `I1_PRECOMMIT_FAKE_GATE`**

## 1. Controlling authority

The sole parent is accepted A0 commit
`3a6dd9dcc45df6b66f8a0afb317efc45f2d1ae5a`.  Its candidate GitHub Actions
run `29215892198`, job `86711600027`, and its accepted run `29216022723`, job
`86711962107`, both concluded `success`.

The controlling amendment is
`docs/experiments/uprime_odlrq_official_transport_v2_amendment_2026-07-13.md`.
Section 11 requires an I1 precommit fake/fault red outcome to remain
uncommitted, create F from accepted A0, and perform no live-worker execution.

## 2. Registered gate outcome

At approximately 2026-07-13 10:22 Asia/Tokyo, the one official G2 precommit
command was run in the uncommitted I1 worktree:

```powershell
& .\tools\run_uprime_official_transport_v2_tests.ps1
```

Its exact visible output was:

```text
.............................                                            [100%]
29 passed in 0.39s
uprime-official-transport-v2-tests: Error formatting a string: Index (zero based) must be greater than or equal to zero and less than the size of the argument list..
```

The process exited nonzero (`1`).  The registered disposition is therefore:

```text
failure_stage = I1_PRECOMMIT_FAKE_GATE
I1 commit count = 0
I1 push count = 0
I1 candidate CI count = 0
live-runner invocation count = 0
real Python child count = 0
Lean worker count = 0
post-failure live-worker diagnostic count = 0
```

The 29 fake/fault tests themselves passed.  This does not turn the wrapper gate
green: the official runner failed after pytest while emitting its qualification
summary, so G2 is red as a whole.

## 3. Audited cause without repair

Read-only inspection localized the failure to the success-reporting expression
in the uncommitted `tools/run_uprime_official_transport_v2_tests.ps1` draft:

```powershell
[Console]::Out.WriteLine(
    "uprime-official-transport-v2-tests: qualification ticks={0} frequency={1} peak_job_memory={2}" -f `
        $elapsedTicks, $StopwatchFrequency, $peak
)
```

Windows PowerShell binds this form so that the format operation does not receive
the intended three-element argument array.  Parenthesizing the complete `-f`
expression would be the obvious engineering repair, but no such repair was
applied and the gate was not rerun.  This diagnosis is administrative evidence,
not a green result or a license to alter I1 in place.

The failure is not a transport-science result: no Lean process started, no
public synthetic RPC request was sent, no KP3 endpoint or protected input was
read, and no envelope/MaxEnt/similarity/locality quantity was measured.

## 4. Uncommitted forensic source state

The stopped worktree is retained at:

```text
C:\Users\yusei\Desktop\lean_rgc_automation_stack_v47_goal_state_dynamics_transport_v2_i1
branch: codex/uprime-official-transport-v2-i1
HEAD:   3a6dd9dcc45df6b66f8a0afb317efc45f2d1ae5a
```

Its five staged paths are not Git-history authority and must not be imported as
an accepted result.  Their stopped byte identities are recorded only for
forensics:

| path | worktree bytes | worktree SHA-256 | staged Git blob |
|---|---:|---|---|
| `tools/uprime_official_transport_v2_smoke.py` | 70,885 | `14983F9796F0BD68ACD69D89112537774A3280693E48BF1D6D401E0224373BEC` | `3eb21461a552cfb36e944bf1aeded6fb6bd45fce` |
| `tools/run_uprime_official_transport_v2_smoke.ps1` | 83,473 | `0803950D237E584B04B0A607CF6FA459920BB669B4A96B4E4C1AD11634C307B1` | `a5e6e630409b0a13d63fc8b72f41af9241e12761` |
| `tools/run_uprime_official_transport_v2_tests.ps1` | 21,282 | `AB58D372CEC49719B6DAC3D4A2264ED8074AA592387331966622A2C38F2D069C` | `e8ae564175e9a1f125f20ead40a959275a9ab9db` |
| `tests/test_uprime_official_transport_v2_smoke.py` | 29,961 | `14E11757192585AFB4B4F583BA5B59F1D991A1F08D1017FCF751863FACF81003` | `e134ff8d04926cec9b4be1be16392e790fe5aeaf` |
| `tests/tier_manifest.json` | 8,725 | `359AD8EAE47E1EBB365A532514FE769AF27598572A846769081275AE5FB90C2D` | `88eb765c7c0eb484825e39b956860621db71bc84` |

Before the official gate, development-only fake checks reported 29 passing
tests, both PowerShell files parsed with zero AST errors, and both embedded C#
fragments compiled when extracted without invoking either runner.  Those checks
explain why the residual formatting edge was missed; they do not supersede the
red official wrapper.

## 5. No-attempt proof and stopping rule

The registered canonical live root

```text
C:\Users\yusei\Desktop\lean_rgc_automation_stack_v47_goal_state_dynamics_transport_v2_live
```

was absent after the failure.  Consequently no `BATCH_OPENED`, `RUN_OPENED`,
child result, artifact, or closeout result exists, and the R branch was never
entered.  No SSH, remote CPU, GPU/CUDA, model server, LLM proposal, or LLM
distillation was used.

The stopped I1 ref must not be committed, pushed, repaired, force-pushed,
deleted, or restarted.  Any future correction requires a new dated amendment,
new filenames or otherwise explicitly separated source authority, new fixed
refs/quotas, and accepted CI before another precommit gate.  This F closeout
does not itself license that future phase.
