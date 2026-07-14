# U-prime / ODLRQ U2--U4 R11 failure closeout

Date: 2026-07-15 (Asia/Tokyo)

Status: `U24_R11_DIRTY_B0_CONTROL_BLOCKED`

Scientific interpretation: `NON_SCIENTIFIC_CONTROL_SELF_CHECK_AND_STREAM_BOUNDARY_FAILURE`

R11 is terminal at its first official dirty B0 invocation.  The registered
status calibration passed once, and the registered dirty B0 child was started
exactly once.  B0 did not produce the required five-test receipt.  Its sole
test traceback is an identity self-check failure before any E2 source,
scientific endpoint, protected K/KP probe, Lean RPC, GPU, SSH, or LLM action.
There is no rerun, correction, control commit, candidate push, accepted-ref
fast-forward, or E2 continuation in R11.

## 1. Immutable authority and closeout topology

R11 began at exact F10:

```text
commit 3fbfcee28e685c34d3015c796d86f51ec5436ecc
tree   adf47385f542adf034b61df9b2dc841ad067802a
parent 6fb521b50ee375a9f01fe464ed313aff5f02431e
```

F10 changes only
`docs/experiments/uprime_odlrq_u2_u4_development_r10_failure_closeout_2026-07-15.md`,
mode `100644`, blob `f9c6dfe97bff40794dd2d5b9c3663d88372ea3fc`,
`10038` bytes, raw SHA-256
`749CAC64D30FC4D308DB9DED7457573E0ECA5D5CDB42870D44AE22B6B9F257E7`.

F10 CI run `29362139242`, job `87184628715`, attempt `1`, was red with
exactly `1 failed, 2599 passed, 8 skipped, 161 deselected`.  The dated R11
amendment records that this was the inherited closeout-topology assertion at
identity line `1003 -> 648`, not a scientific endpoint result.  R11 did not
rerun or reinterpret it.

The dirty invocation was governed by this exact amendment:

```text
path   docs/experiments/uprime_odlrq_u2_u4_development_r11_minimal_control_reentry_amendment_2026-07-15.md
bytes  18802
SHA256 8F7FEBCA36EDF0AB1B86C18C2FD5C2056CA60E4468A684D885B1D3B7DAAB7BDF
blob   af3405dc1807fa4f43b6fd8b4b11d67ed984232e
mode   100644
```

That amendment freezes correction budget zero and stops R11 on any
calibration, source, topology, wrapper, stream, B0, count, or receipt failure.
This closeout is therefore the immediate sole-parent child of F10 and changes
only this registered mode-`100644` path:

```text
docs/experiments/uprime_odlrq_u2_u4_development_r11_failure_closeout_2026-07-15.md
```

The failed dirty exact-five is not committed, merged, rebased, reset,
cherry-picked, or admitted into this branch.

## 2. Exact dirty input and pre-execution audit

The one official dirty B0 saw exactly these five paths over F10:

| state | bytes | raw SHA-256 | Git blob | path |
|---|---:|---|---|---|
| untracked | 116892 | `FCF4AD9FB80E88D96DFE8D8682D8FBE63E530C869636627F74AB6A931FD0484D` | `61aad0ff3240b4d17b191b4f0b36392971b5bddb` | `docs/experiments/uprime_odlrq_u2_u4_development_r8_tracked_universe_reentry_amendment_2026-07-15.md` |
| untracked | 18802 | `8F7FEBCA36EDF0AB1B86C18C2FD5C2056CA60E4468A684D885B1D3B7DAAB7BDF` | `af3405dc1807fa4f43b6fd8b4b11d67ed984232e` | `docs/experiments/uprime_odlrq_u2_u4_development_r11_minimal_control_reentry_amendment_2026-07-15.md` |
| modified | 142545 | `CCCDB3D0B5616A5EA64EB4DE0DD0495E477C2DB2E3664D01210FD01C022C71E3` | `b6b4b06b11de5e463fb1192a58a2aa466c209185` | `tests/test_uprime_u2_u4_development.py` |
| modified | 108523 | `4AEDBED714BBFCDA6D6A21AB0C0ABE4482CBBD9222698EEFF78DDFDC9C64B1E6` | `56c6bd764a918f70f0396a1d215d464679a5e71d` | `tests/uprime_u24_guard.py` |
| modified | 171617 | `1DE3056622238E2D6BC0B29D23B6EB70B29EB19FD7472BFE891A1EAC7854A63E` | `1e81d5169fa018d32bcba27433f09c06045ff38d` | `tools/run_uprime_u2_u4_development_tests.ps1` |

All are mode `100644`.  Three independent read-only adversarial audits plus
one actual union static scan were green before execution.  They verified:

```text
canonical tracked paths  count 63 / bytes 4465
canonical SHA256         E6405214C7180F56C661562C2A85B9AD48AA164E09658BA8CFFB5BB67FEADC97
designated absent paths  22, all absent at exact F10
identity core            AEF4D58CFC0D54C9E422403EBEC8C57615CA996BE951E6FF31F151DB0A02EFBD
guard core               70FC9C4CCD88140A0D31859DE825174A1198FF3FC0219E70970D346EA56D7C9F
normalized runner        1DE3056622238E2D6BC0B29D23B6EB70B29EB19FD7472BFE891A1EAC7854A63E
Python AST               green
PowerShell 5.1 parse     green
union static scan        green
```

Repair A also verified that only the exact `Read-Run` and `Read-Jobs`
network-route lines were carved before the unchanged all-row filesystem
denylist scan.  Those green facts attest the frozen bytes; they do not
override the official B0 failure below.

## 3. One status calibration

The repository-independent calibration ran once and exited zero with:

```text
CALIBRATION_MATRIX=4/4
CALIBRATION_CHILD_EXIT=37
CALIBRATION_TAG=u24-r11-status-calibration-e0edabf8f7ab43b4aac54029016bb8c6
CALIBRATION_DIR=C:\Users\yusei\AppData\Local\Temp\u24-r11-status-calibration-e0edabf8f7ab43b4aac54029016bb8c6
CALIBRATION_STDOUT_SHA256=E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855
CALIBRATION_STDERR_SHA256=0E687C820483E6FF93027D65E1EE3306168B368070ED1139DBCFEB161B2669F0
```

The status-37 child had zero stdout bytes and exactly the frozen 13-byte ASCII
stderr `R11_STATUS_37`.  Windows PowerShell also serialized a first-use module
progress record as host CLIXML outside those child capture files.  It did not
alter the calibrated child exit or hashes, and no calibration rerun occurred.

## 4. First official dirty B0 capture

The exact frozen wrapper started one hidden Windows PowerShell 5.1 child with
`-Lane B0` and created:

```text
TAG=u24-r11-b0-800b5fbcf42b428c9a5e02840536295f
CAPTURE_DIR=C:\Users\yusei\AppData\Local\Temp\u24-r11-b0-800b5fbcf42b428c9a5e02840536295f
```

The outer host returned only its CLIXML prefix and no required
`CHILD_EXIT`, `WRAPPER_EXIT`, or `CAPTURE_DISPOSITION` lines.  Polling the
already-created capture is explicitly not a rerun.  The first post-return
poll saw both files at zero bytes.  The same stderr file then reached its
stable final 531-byte state at `2026-07-14T20:08:54.6609480Z`; stdout remained
zero bytes at `2026-07-14T20:08:14.5826066Z`.

Final strict byte authorities are:

```text
STDOUT_BYTES=0
STDOUT_SHA256=E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855
STDOUT_BASE64=
STDERR_BYTES=531
STDERR_SHA256=7DCE317729748D4390B70E8CDD6F27B55B7527EA23F6FB94F78D10FBB970CE04
STDERR_BASE64=VHJhY2ViYWNrIChtb3N0IHJlY2VudCBjYWxsIGxhc3QpOg0KICBGaWxlICJDOlxVc2Vyc1x5dXNlaVxBcHBEYXRhXExvY2FsXFRlbXBcbGVhbi1yZ2MtdTI0LWFjOGJlMGY5NDI4YTRhMWU5M2YzZGRhYTBmOWQxZjYzXGJvb3RzdHJhcC5weSIsIGxpbmUgMTA0MSwgaW4gPG1vZHVsZT4NCiAgICBpZiBmdW5jdGlvbigpIGlzIG5vdCBOb25lOg0KICAgICAgIH5+fn5+fn5+Xl4NCiAgRmlsZSAiQzpcVXNlcnNceXVzZWlcRGVza3RvcFxsZWFuX3JnY19hdXRvbWF0aW9uX3N0YWNrX3Y0N19nb2FsX3N0YXRlX2R5bmFtaWNzX3UyX3U0X3IxMV9ib290c3RyYXBcdGVzdHNcdGVzdF91cHJpbWVfdTJfdTRfZGV2ZWxvcG1lbnQucHkiLCBsaW5lIDI1ODksIGluIHRlc3RfdTI0X2RlbnlsaXN0X3N0YXRpY19zY2FuX2FuZF9leGFjdF9ydW5uZXJfY29weQ0KICAgIGFzc2VydCBydW5uZXIuY291bnQoZnJvemVuX2xpdGVyYWwpID49IDENCiAgICAgICAgICAgXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eDQpBc3NlcnRpb25FcnJvcg0K
```

The Base64 has length `708` and round-trips exactly to the recorded bytes and
SHA-256.  Decoded stderr terminates at:

```text
bootstrap.py:1041
  -> test_u24_denylist_static_scan_and_exact_runner_copy:2589
assert runner.count(frozen_literal) >= 1
AssertionError
```

There is no B0 receipt and no `5 passed, 0 skipped, 0 xfailed, 0 deselected`
result.  Empty stdout alone violates the frozen receipt contract; the final
traceback independently violates the stderr and test-count contracts.  Raw
process status cannot override either failure.

## 5. Root cause and audit miss

The first missing `frozen_literal` is the full contiguous F10 changed path:

```text
docs/experiments/uprime_odlrq_u2_u4_development_r10_failure_closeout_2026-07-15.md
```

The runner intentionally constructs that path as adjacent Python source
literals, so its raw PowerShell source contains no contiguous full-path
substring.  The same stale raw-source assertion would also reject the full R6
amendment, R5 amendment, R5 failure-closeout, and reconstruction-failure
paths; their raw runner-source counts are also zero.  The check therefore
confuses semantic literal construction with contiguous host-source spelling.
It is a control self-check representation defect, not a filesystem access,
protected-data read, or result about quotient/envelope mathematics.

The pre-execution audits checked exact route carving, denylist authority,
topology, source parsing, and mutual hashes.  They did not evaluate every item
of the later identity `runner.count(frozen_literal)` loop against the final
raw runner text.  R10 stopped earlier in the same test, so this later stale
assertion had never been reached.

The capture also shows that the status-37 calibration was too small to
establish prompt drain of a larger redirected stream: after the outer host
returned, the same stderr file changed from zero to 531 bytes.  R11 does not
attribute that observation to a specific undocumented component.  It records
the runner-to-OS-to-host stream boundary as uncalibrated for this workload.
Either the missing receipt or the traceback is sufficient to stop R11, so no
causal choice between these two control failures is needed.

## 6. Zero scientific exposure and terminal disposition

At the R11 stop point all of these counts remain zero:

| event or capability | count |
|---|---:|
| R11 control commits | 0 |
| R11 candidate pushes or CI runs | 0 |
| accepted-ref fast-forwards or accepted CI runs | 0 |
| E2 scientific source creation, import, compilation, collection, or execution | 0 |
| E2 source-freeze/result documents or scientific artifacts | 0 |
| ME0, S0, or I0 execution | 0 |
| native Lean/RPC execution | 0 |
| protected K/KP execution | 0 |
| GPU/CUDA use | 0 |
| SSH or remote-CPU use | 0 |
| LLM/model-server/proposer use | 0 |

The dirty R11 worktree remains local quarantine evidence over F10.  It must
not enter accepted ancestry or be presented as a successful control result.
The invalid R8 commit `6616eb3fc3473dedd7e8f49e4a2d01cd98487fd4`
and dirty R9/R10 states remain separately quarantined.  R11 has no correction
or rerun.  Any continuation requires a new, separately dated and frozen epoch.
