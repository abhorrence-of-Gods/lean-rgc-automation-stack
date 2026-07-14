# U-prime / ODLRQ U2--U4 R5 failure closeout

Date: 2026-07-14 (Asia/Tokyo)

Status: `U24_B0_IDENTITY_OR_RUNNER_BLOCKED`

R5 bootstrap disposition: `NOT_COMMITTED / NOT_PUSHED / NOT_ACCEPTED`

Subcause: `GLOBAL_E1_IO_LITERAL_COUNT_COLLIDES_WITH_MANIFEST_VALIDATION`

Scientific interpretation: `NON_MATHEMATICAL_STATIC_SCOPE_ASSERTION_FAILURE`

Authority:
`docs/experiments/uprime_odlrq_u2_u4_development_r5_powershell51_decode_reentry_amendment_2026-07-14.md`
at the exact uncommitted R5 four-path bootstrap bytes recorded below.

R5 stops after its sole registered dirty B0 invocation.  This document
preserves the failed bootstrap without editing it, consuming a correction,
creating an E1 import, or converting a static identity failure into a
scientific result.

## 1. Immutable R5 anchor

The R5 worktree remained at the accepted R4 failure-closeout anchor:

```text
anchor b57ac55e823bc90a7d86f8b593249b70feeadaf1
parent fbc1259dc276265a8949aad86d9e15b87e4a6dff
tree   3fbb08d6e3d496460e97ca60b83c7667ec518480
```

At the anchor, the sole changed path is the accepted R4 failure closeout:

```text
docs/experiments/uprime_odlrq_u2_u4_development_r4_failure_closeout_2026-07-14.md
```

Its frozen Git blob is
`fc1f409d2150fcfd199383d6d881549ee81984e7`.

The failed R5 worktree is
`codex/uprime-u2-u4-development-r5-decode-bootstrap`.  Its `HEAD` did not move
from `b57ac55e...`; no R5 bootstrap commit or tree exists.

## 2. Exact failed four-path bootstrap bytes

The failed worktree dirt was exactly the four registered bootstrap paths and
no E1 source path:

| status | raw bytes | raw SHA-256 | Git filtered blob | path |
|---|---:|---|---|---|
| untracked | 18061 | `0AFF640B22FF4E7F3AE23EF488D826D5672902B0F5DEDB9823DF126C5DE7DA5D` | `a15d3e339d634f7dfe36e5c8b7a7595d39a2dbde` | `docs/experiments/uprime_odlrq_u2_u4_development_r5_powershell51_decode_reentry_amendment_2026-07-14.md` |
| modified | 93070 | `ED89E1DBCD87CB8B1822CF13BE7D8ED8B92E36C4EE317D55E5234AEDCB6CB19C` | `52ea6408d8f0e14d77278cb07dce845e1d6db3a9` | `tests/test_uprime_u2_u4_development.py` |
| modified | 58698 | `83A670F069D46D97F803A756214CE18275DA100F72F389368ED3090BDF6D4C06` | `7799d0eb274db7653fbee097c5d53fc13f57836e` | `tests/uprime_u24_guard.py` |
| modified | 68228 | `6F0B0CC574C2615FBD146D77570DE883445855B1AB797CE55240B23ABDAFC195` | `4db9708071f94cd6c492794ba2f1cc0a49871425` | `tools/run_uprime_u2_u4_development_tests.ps1` |

For the runner, line-ending identities are deliberately distinguished:

```text
raw working-tree bytes:       68228
raw SHA-256:                  6F0B0CC574C2615FBD146D77570DE883445855B1AB797CE55240B23ABDAFC195
raw --no-filters Git blob:    deffdb187b33738dfa6c1c97c370e5764117983f
normalized-LF SHA-256:        8631AE7436C6A1DDE1E28774C0CEE34581B7E2ED90313268F214217054E1E59C
filtered Git blob:            4db9708071f94cd6c492794ba2f1cc0a49871425
```

The filtered blob is the registered Git identity; the raw no-filter blob is
recorded only to prevent future readers from confusing CRLF working-tree
bytes with the repository-filtered object.  The other three files have no
filtered/no-filter divergence.

The R5 amendment is reproduced byte-for-byte in the R6 evidence worktree with
exactly 18061 bytes, raw SHA-256
`0AFF640B22FF4E7F3AE23EF488D826D5672902B0F5DEDB9823DF126C5DE7DA5D`,
and Git blob `a15d3e339d634f7dfe36e5c8b7a7595d39a2dbde`.

## 3. Sole official dirty B0 observation

R5 made exactly one official dirty invocation:

```powershell
& .\tools\run_uprime_u2_u4_development_tests.ps1 -Lane B0
```

The invocation exited `1` after an observed wall time of `18.3005356s`.  It
emitted no lane receipt.  The terminal traceback reached
`tests/test_uprime_u2_u4_development.py` line 1586 and failed:

```text
assert runner.count(e1_io_literal) == 1
AssertionError
```

The failing identity loop registered these exact literals:

```text
foreach ($entry in $e1Frozen)
Resolve-RegularFile -LiteralPath (Join-Path $repoRoot $relative)
Get-Item -LiteralPath $candidate -Force
Get-Sha256 -LiteralPath $candidate
hash-object $relative
```

Four of the five literals occurred exactly once in the runner.  The
`Resolve-RegularFile -LiteralPath (Join-Path $repoRoot $relative)` literal
occurred twice:

```text
runner line 222: Lane E1 exact frozen-byte preflight
runner line 291: inherited tier-manifest lane-test-path validation
```

The assertion at identity line 1586 counted the literal over the complete
runner text and required a global count of one before it separately checked
the E1 lexical block.  It therefore rejected the legitimate inherited
tier-manifest lane-test-path validation occurrence even though the new exact
frozen-byte preflight occurrence itself remained inside Lane E1.

## 4. Diagnosis and scientific boundary

The registered Windows PowerShell 5.1 process successfully executed the R5
two-stage decode and unconditional six-element cardinality check.  Otherwise
the outer runner would have stopped before child creation with the R4
cardinality message.  Instead, the B0 child was created and reached the
identity test at line 1586.  R5 therefore supplies positive engineering
evidence for the narrow PowerShell 5.1 decode repair.

The terminal defect is the static assertion's scope model.  It treated a
textual literal used by two separately governed blocks as if the literal were
globally unique.  The tier-manifest lane-test-path occurrence was inherited
and is not an E1 file read, module import, pytest collection, or scientific
endpoint.  During B0, its `$relative` value is
`tests/test_uprime_u2_u4_development.py`, the identity test path, not an E1
path.  The R5 amendment's explicit control-plane/tier-manifest
lane-test-path scope boundary was not violated; the source assertion failed
to represent it.

No E1 file was imported into the R5 bootstrap.  No E1 child, E1 pytest
selection, exact 48-test endpoint, receipt, fiber-envelope result, or
scientific certificate was created.  The failure observed no false quotient
law, fiber law, rational oracle, positive-majorant inequality, extension
monotonicity condition, tier firewall, resource limit, or capability check.

The R5 result is therefore a B0 identity/runner failure, not a mathematical
or scientific E1 failure.  It supplies no evidence for or against the
upper-stack envelope, MaxEnt, global-similarity, or Lean-oracle-locality
hypotheses.

## 5. Frozen adjudication and stop

The R5 stopping rules require dirty B0 to pass before a bootstrap commit and
forbid repairing a failed registered outcome in place.  R5 therefore stops at

```text
U24_B0_IDENTITY_OR_RUNNER_BLOCKED
subcause: GLOBAL_E1_IO_LITERAL_COUNT_COLLIDES_WITH_MANIFEST_VALIDATION
```

The failed R5 worktree remains byte-for-byte unchanged at the four identities
in section 2.  No correction was made.  There was no clean B0, bootstrap
commit, staging, push, candidate CI, accepted fast-forward, accepted CI, new
ref, or accepted-ref movement.  No E1 import, E1 commit, artifact emission,
or success closeout occurred.

No protected K1--K4 result, native Lean/Lake/RPC, SSH, remote CPU, GPU/CUDA,
model server, LLM proposer, knowledge distillation, deployment, MaxEnt fit,
global-similarity construction, or locality learner was used.

Only a separately dated R6 authority may continue.  R6 may re-register a
scope-aware static assertion that distinguishes the one Lane E1 exact
preflight occurrence from the inherited tier-manifest lane-test-path
validation occurrence while preserving the R5 two-stage decode, all four
failed R5 source identities, the scientific E1 bytes, and every
wall/test/endpoint.  This R5 closeout does not license an in-place repair, a
global literal deletion, a tier-manifest lane-test-path validation change, or
any mathematical or scientific modification.
