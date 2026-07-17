# U-prime / ODLRQ E2 Q1 qualification closeout

Date: 2026-07-17 (Asia/Tokyo)

Status: **COMPLETE — E2 ACCEPTED.**

This is a document-only sidecar closeout.  Its parent is final Q1 authority
`9f7a6616ea57f10b12c5d9d9250cc1ccc50b6107`; it is never merged into accepted
science.  Accepted E2 is the separate exact candidate commit
`7a8b28872439dd61d40174c2500c5990790002be`.

## 1. Verdict

The exact finite-fiber E2 endpoint passed its single licensed Windows-CPU local
qualification and two distinct natural Linux CI gates.  Remote
`codex/uprime-odlrq-plan` now fast-forwards to the exact same SHA as
`codex/uprime-e2-qualification-candidate-q1`:

```text
7a8b28872439dd61d40174c2500c5990790002be
```

The Q0/Q1 failures preceding this result were implementation and control-plane
defects.  They do not refute the quotient, exact envelope, lifting-uniform safety,
or the upper theoretical program.  No protected K1-K4 endpoint, reserved task
data, GPU, SSH, or LLM was used.

## 2. Candidate identity and repair footprint

The accepted candidate is a single-parent direct child of semantic B
`6998f2f9ec430881df50e6790ef9a8f13b1b7857`.  Its correction diff is exactly:

```text
lean_rgc/odlrq/certificates.py
lean_rgc/odlrq/selection.py
tests/test_odlrq_selection.py
```

Its final diff against accepted E1 adds only the unchanged pre-existing manifest
path `tests/tier_manifest.json`.  The manifest blob is identical at B and the
accepted candidate.  The repair bijectively moved all eleven E2 synthetic state
IDs into the frozen `unit_cpu_survivor_` admission namespace and replaced
redundant reconstruction/serialization work while preserving strict fresh-wire
validation, public schemas, all four endpoint meanings, and all ten node IDs.

Pre-freeze development evidence on the exact accepted tree was:

```text
10 passed in 316.09s
98 passed in 154.15s
2614 passed, 4 skipped, 161 deselected in 1129.57s
```

## 3. Control-attempt ledger

### Attempt 1

- authority: `4643ccc502efe8cc6cee44b6bd035d487348f8f1`
- authority CI: run `29547190425`, job `87781939106`
- disposition: `CONTROL_FAILED_PRE_MARKER_REPAIRABLE`
- control record: absent
- scientific marker: absent
- scientific look consumed: false
- immutable result:
  `C:\Users\yusei\Desktop\codex_claude_bridge\control_records\u24_e2_q1\attempt-1-result.md`
- result SHA256:
  `566EEF4B8A879FD49EA8FAFD4A79B187D1C9E05754112BA2883104584C303E3F`

The cause was Windows PowerShell 5.1 promoting expected native Git stderr to a
terminating error under global `$ErrorActionPreference=Stop` before exit-128
adjudication.  No E2 node ran.  Attempt 2 changed only this scoped control
behavior plus mechanically required retry identities.

### Attempt 2

- authority: `9f7a6616ea57f10b12c5d9d9250cc1ccc50b6107`
- authority CI: run `29548028682`, job `87784451452`
- control record SHA256:
  `7220F44F8354CC0EB37EBB7933A50EBD54C3870011480B1EDC5487B0DC09ED03`
- preflight diagnostic SHA256:
  `147A9C621500295E750F86BB7FDBAEFE2A8B179EC619DD9163F27DABDC610A17`
- scientific marker SHA256:
  `7ACCD1ACA725393A12876AD827CE71A3AAA5C735916437E1D39EFF9DA7A774D8`
- node-list SHA256:
  `E08F9708288738867A7A86A4E2C1BD453D84813419453E7B46BB77CB581E6540`
- command SHA256:
  `37DDE2DDA67A8995EA5CDBD59B5DB936AF5B17DB7E34DD14D6D3B88175A7206D`
- scientific look consumed: true
- scientific relaunch permitted: false
- immutable result:
  `C:\Users\yusei\Desktop\codex_claude_bridge\control_records\u24_e2_q1\attempt-2-result.md`
- result SHA256:
  `F68B310C0B6113CB1826F5BBF2133CCAD3B45C5A9BAB0A1B05FDE05249C9C1B3`

The sole inherited-console scientific outcome was exactly:

```text
..........                                                               [100%]
10 passed in 271.36s (0:04:31)
```

Exit code was zero, with no failure, error, skip, xfail, deselection, extra
collection, timeout, capture loss, or second launch.

## 4. Natural CI ledger

All runs used workflow `CI`, path `.github/workflows/ci.yml`, workflow ID
`292918982`, event `push`, and `run_attempt=1`.  No run was rerun or dispatched.

| Role | Ref | Run / job | SHA | Outcome |
|---|---|---|---|---|
| attempt-1 authority | `codex/uprime-e2-qualification-authority-q1` | `29547190425` / `87781939106` | `4643ccc...` | expected topology-only red; E2 hits 0 |
| attempt-2 authority | `codex/uprime-e2-qualification-authority-q1-a2` | `29548028682` / `87784451452` | `9f7a661...` | expected topology-only red; E2 hits 0 |
| candidate | `codex/uprime-e2-qualification-candidate-q1` | `29548427172` / `87785632743` | `7a8b288...` | green; `2610 passed, 8 skipped, 161 deselected` |
| accepted | `codex/uprime-odlrq-plan` | `29548712422` / `87786490144` | `7a8b288...` | distinct green; same exact count |

The two red authority badges are caused solely by the historical first-parent
topology guard rejecting intentional sidecar merge carriers.  They are control
artifacts, not scientific failures.  This is the same class of badge-interpretation
risk recorded in the dated U05 clarification: U05 result CI was red because of
the shallow-history guard defect, while candidate CI `29166073728` was green.

The closeout ref itself inherits the same historical sidecar topology and its
natural CI is therefore expected to have the same sole topology failure and zero
E2 hits.  A red closeout badge must not be read as reversing E2 acceptance.

## 5. Governance disposition and next license

FABLE-20260717-0005 and the user's delegated policy were followed: ordinary
implementation/runner/CI/governance defects were repaired without pausing for
user approval; user escalation remained reserved for theoretical refutation or
exhaustion of rational remedies.  Neither escalation condition occurred.

E2 acceptance closes the prior upper-stack license gate.  Work may now resume on
the registered implementation plan, with the already-requested priority:

1. finish this document-only closeout and preserve its CI classification;
2. resume the adversarially reviewed mathematics-to-code work packages;
3. advance the minimal kill-probe measurement substrate before broad upper-stack
   construction;
4. build exact quotient coordinates before positive worst-case envelope, then
   MaxEnt model selection and finite-approximation-stable global similarity;
5. keep the Lean-oracle locality learner/CEGAR path registered after its exact
   substrate is accepted; and
6. keep LLM knowledge distillation outside the loop until the theoretical
   generator and finite downstream pipeline are independently validated.

The main dirty user checkout and quarantined/user-owned untracked files were not
modified by Q1.
