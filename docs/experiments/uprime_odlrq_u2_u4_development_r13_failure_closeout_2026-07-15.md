# U-prime / ODLRQ U2--U4 R13 failure closeout

Date: 2026-07-15 (Asia/Tokyo)

Status: **R13 FAILED CLOSED DURING ITS SOLE EXPLICIT-HANDLE CALIBRATION; NO B0 OR SCIENTIFIC EXECUTION**

R13 stopped during its one licensed calibration, before the calibration could
adjudicate explicit descendant stderr inheritance.  This closeout preserves
the failure without importing the dirty R13 control state into Git history
and, as required by the R13 amendment, licenses no fourth control repair.

## 1. Immutable starting point and licensed dirty state

R13 began from exact F12:

```text
commit 259ed6c497990047c3a1ff37eabfaeff604ab636  (F12)
tree   5107442e6de7814d0fa6bc8ba85038044ede20d2
parent 14b1043d4a2df007d40b0390f4f162d14b3be1aa
```

The final uncommitted R13 state contained exactly the registered five paths:
the exact R8 amendment, the R13 amendment, identity, guard, and runner.  The
R13 amendment's exact authority was:

```text
bytes  12617
SHA256 4ED4B524F928930B00712CA76A3F69975621585CDB8C103BA538B94975F132B2
blob   0bf9b1fb485a413a27a7e2e5fcf6cd0ce0bce026
```

Static review closed the mutual hash authorities before execution:

```text
identity core     B5D1A9134EF12296AC52BFE850754479B582E9856794FB9049D3DBA0C97628A2
guard core        34E6B4AFC8D9D53B370A8D02A1E6FAEF45D2453026BBE75A8A59E3B7EBD5F2C2
normalized runner 026AF91967BC5A4DBF9965DF4954A6CEF996D1F5F2472E87AB840CEAFD52765A
```

The sole calibration used the frozen repository-external wrapper and
independent supervisor:

```text
wrapper path   C:\Users\yusei\AppData\Local\Temp\u24-r13-explicit-handle-wrapper-20260715.ps1
wrapper bytes  26224
wrapper SHA256 A6C7DB07B68961312BF9BAC02A7AE9DB34A0C697537A41AD9C420C8D7A26AB97

supervisor path   C:\Users\yusei\AppData\Local\Temp\u24-r13-independent-supervisor-20260715.ps1
supervisor bytes  10020
supervisor SHA256 7DA24661C504A409F472B90B103BA78E741B6EC2E9033120957398FA43D98A13
```

These external files are execution evidence, not repository helpers or
scientific source.

## 2. Sole execution outcome

The independent supervisor started the wrapper exactly once.  The wrapper
and supervisor both exited `197`.  The supervisor reported
`wall_ticks = 571718175` at `clock_frequency = 10000000`, or `57.1718175`
seconds.  Its exact raw capture directory is:

```text
C:\Users\yusei\AppData\Local\Temp\u24-r13-calibration-supervisor-20260715-4c2e9b7a
```

The outer captures are:

```text
stdout bytes  0
stdout SHA256 E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855

stderr bytes  280
stderr SHA256 2881677167E0AB54DCAA7DF20271ED6359F69A1639DE068C57143C16D84712F3
stderr Base64 UjEzX0VYVEVSTkFMX0NBUFRVUkVfRkFJTFVSRToiMSIgjMKCzIj4kJSC8I53kuiCtYLEICJSZWFkQWxsQnl0ZXMiIILwjMSC0Y9vgrWShoLJl+GKT4KqlK2QtoK1gtyCtYK9OiAilcqCzIN2g42DWoNYgsWOZ5dwgrOC6oLEgqKC6YK9gt+BQYN2g42DWoNYgs2DdINAg0ODiyAnQzpcVXNlcnNceXVzZWlcQXBwRGF0YVxMb2NhbFxUZW1wXHUyNC1yMTMtY2FsaWJyYXRpb24tZDkyNTUwNDA5OWE2NGU5ZThjMWE0MTZkMzg0NDRmNWRcc3Rkb3V0LmJpbicggsmDQYNOg1qDWILFgquC3IK5gvGBQiINCg==

supervisor.release bytes  28
supervisor.release SHA256 A0C0FF00B750A49BD2C801D533C76BE128B902B0B88DDB97849EC7E984D341C8
```

The stderr bytes are CP932.  Decoded with the frozen Windows default code
page, their exact message is:

```text
R13_EXTERNAL_CAPTURE_FAILURE:"1" 個の引数を指定して "ReadAllBytes" を呼び出し中に例外が発生しました: "別のプロセスで使用されているため、プロセスはファイル 'C:\Users\yusei\AppData\Local\Temp\u24-r13-calibration-d925504099a64e9e8c1a416d38444f5d\stdout.bin' にアクセスできません。"
```

The inner capture directory is:

```text
C:\Users\yusei\AppData\Local\Temp\u24-r13-calibration-d925504099a64e9e8c1a416d38444f5d
```

Its stable evidence is:

```text
stdout bytes  113
stdout SHA256 9EECC988DA858CCC2175A20E49976CA77F8A0C6FEF2CDB4A6A9D3F9F7804798B
stdout ASCII  {"child_started":true,"schema_version":"u24-r13-explicit-handle-calibration-v1","stderr_handle_inheritable":true}

stderr bytes  0
stderr SHA256 E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855

descendant.pid bytes  7
descendant.pid SHA256 CACCDAB0F372CBC13FA0CD29F908D7A21FAFDE3DC5C48B4969C998A1B1D9C9CF
descendant.pid ASCII 30652\n

release.gate      absent
```

PID `30652` was not alive after the failed wrapper's cleanup.  That
post-cleanup fact is not evidence that the required pre-gate liveness check
passed.  The wrapper emitted no success summary.

## 3. Diagnosis and adjudication boundary

One terminal defect is confirmed directly: the wrapper called
`ReadAllBytes` on `stdout.bin` while its own write-side `FileStream` still
held an incompatible share mode.  Windows therefore raised the recorded
sharing violation before the wrapper could validate the receipt, establish
pre-gate descendant liveness, create `release.gate`, or observe the delayed
stderr marker and common EOF.

A second defect is a strong mechanical inference, not a directly traced
handle event.  The root launched its descendant with `close_fds=False`.
That admits every inheritable handle, not only the deliberately inheritable
stderr handle, so the descendant could retain the root's redirected stdout
pipe as an otherwise unused handle.  The evidence matches that mechanism:

- inner `stdout.bin` was created at `2026-07-14T21:33:50.1418008Z` but its
  final write timestamp was `2026-07-14T21:34:46.1916921Z`;
- `release.gate` was never created, while the descendant's frozen ungated
  timeout was 55 seconds; and
- the supervisor completed after `57.1718175` seconds.

Thus the inferred stdout-handle retention prevented stdout EOF until the
ungated descendant timed out; the wrapper then reached the terminal
`ReadAllBytes` sharing violation.  The timestamp evidence does not by itself
prove a pipe-handle graph, so this point remains explicitly labelled an
inference.

Most importantly, R13 did **not** adjudicate its intended question.  Empty
captured stderr, a root receipt saying the handle was inheritable, and a PID
receipt do not establish that the descendant retained stderr across root
exit.  The required gate was absent, the delayed marker was never written,
and the required EOF ordering checks were never reached.  No claim of either
success or failure for explicit descendant stderr inheritance is licensed.

Neither defect concerns the R8 E2 finite quotient, positive envelope,
certificate, binding selector, MaxEnt, global similarity, Lean-oracle
learner, or any protected K/KP endpoint.

## 4. Execution budgets and absent work

The execution ledger for R13 is exact:

```text
explicit-handle calibration 1
dirty B0                   0
clean B0                   0
control commit             0
push                       0
candidate CI               0
accepted CI                0
E2                         0
ME0                        0
S0                         0
I0                         0
GPU / SSH / LLM            0
```

There is no scientific endpoint, candidate, accepted control state, or CI
result to interpret.  The dirty exact-five state remains local quarantine
evidence only and must not be committed, merged, cherry-picked, rebased, or
pushed.

## 5. Frozen disposition

R13 is `FAILED_CLOSED_EXTERNAL_CAPTURE_CALIBRATION`.  The sole calibration
is consumed and must not be rerun.  Dirty B0 was not started, and no later
phase is partially credited.

The R13 amendment explicitly freezes: "There is no rerun, correction,
second calibration, same-SHA replacement, partial success, or fourth control
repair."  Accordingly, this closeout does not license R14, another wrapper
change, another control epoch, or an alternate control path.  It also does
not license E2, ME0, S0, I0, GPU/SSH work, LLM work, or protected K/KP
execution, because the accepted-green prerequisite was not reached.

This document is the single registered R13 failure action.  It records a
control-infrastructure failure and no scientific result.
