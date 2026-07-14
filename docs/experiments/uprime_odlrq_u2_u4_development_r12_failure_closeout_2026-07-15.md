# U-prime / ODLRQ U2--U4 R12 failure closeout

Date: 2026-07-15 (Asia/Tokyo)

Status: **R12 FAILED CLOSED DURING THE SOLE STREAM-DRAIN CALIBRATION; DIRTY B0 NOT STARTED**

R12 stopped before a dirty B0 invocation, control commit, E2 source freeze, or
scientific endpoint.  This closeout preserves the failure without importing
the dirty R12 control state into Git history.

## 1. Immutable starting point and licensed attempt

R12 began from exact F11:

```text
commit 14b1043d4a2df007d40b0390f4f162d14b3be1aa
tree   e0e126faa02fd82c6086e8dbea0dacdf47b27b27
parent 3fbfcee28e685c34d3015c796d86f51ec5436ecc
```

The local dirty state contained exactly the registered five paths: the exact
R8 amendment, the R12 amendment, identity, guard, and runner.  Two independent
read-only audits passed Canonical66, Absent24, F11 topology through accepted
E1, the amendment byte authorities, Repair A attacks, and the final mutual
hash closure:

```text
identity core     7F250958E6968A9C8E10123DF70844872854EDCCB38B26D228D404B17EE482F6
guard core        0DA2FA6A90AC44410E07C8C860671D8697480E56A4C2876A4356F82198980AE5
normalized runner 662DB79ACBDDFD18072FF16D83A5A7154361040453C9B511A92615B46BA19CEC
workflow          7879CC590945366A356DDEAE2B38480E5434048BFBCEC7E37848D443EA528D3B
```

The one licensed delayed-descendant calibration and dirty B0 were placed in a
single repository-external PowerShell 5.1 wrapper under an independent
180-second supervisor.  The wrapper implemented a 90-second root deadline, a
common 60-second post-root deadline for both `CopyToAsync` tasks, and the
64-MiB aggregate cap during both phases.  Its exact external bytes were:

```text
path   C:\Users\yusei\AppData\Local\Temp\u24-r12-pipe-wrapper-20260715-0f76e9c3.ps1
bytes  13157
SHA256 68F4D036DE2E3A3ABC32E94BEB81D729F2C9AA04CEDBDA7F65982753D4CEE1A0
UTF-8 LF, no BOM
```

This external file is diagnostic evidence, not a repository helper or source
authority.

## 2. Sole execution outcome

The supervisor started the external wrapper exactly once.  It terminated in
about four seconds with wrapper status `197`.  The exact supervisor evidence
is:

```text
capture C:\Users\yusei\AppData\Local\Temp\u24-r12-supervisor-20260715-4d02c761
stdout bytes 0
stdout SHA256 E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855
stderr bytes 97
stderr SHA256 98C7F4B88CE9B4F9B564F39407529ACA3145D87C79249EF3E65752F8B4B30C09
stderr Base64 UjEyX0VYVEVSTkFMX1BJUEVfRkFJTFVSRTqI+JCUgqqL84LMlHqX8YLFgqCC6YK9gt+BQYNwg4mDgYFbg16BWyAnQnl0ZXMnIILJg2+DQ4OTg2iCxYKrgtyCuYLxgUINCg==
```

The stderr bytes are Windows PowerShell 5.1's active code page, not UTF-8.
Decoded with the system default encoding, the exact message is:

```text
R12_EXTERNAL_PIPE_FAILURE:引数が空の配列であるため、パラメーター 'Bytes' にバインドできません。
```

That message means the strict `[byte[]] Bytes` parameter rejected an empty
array while the wrapper was computing a capture digest.  The wrapper did not
emit a success summary.

The already completed calibration captures are stable files:

```text
capture C:\Users\yusei\AppData\Local\Temp\u24-r12-cal-20260715-8c33e2b2

stdout bytes 24
stdout SHA256 F96D9E0D3AF91F4389FC5F2C09B5EDBA0F3C1D667AAB68D5898F16F054584D12
stdout Base64 UjEyX1BJUEVfRU9GX0NBTElCUkFUSU9O
stdout ASCII R12_PIPE_EOF_CALIBRATION

stderr bytes 0
stderr SHA256 E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855
stderr Base64 <empty>
```

The capture function reached successful EOF on both copy tasks, closed the
sinks, and read these bytes before the empty-array hash binding failed.  Thus
the empty stderr is not a shallow file-stability observation.

The registered dirty-B0 capture directory
`C:\Users\yusei\AppData\Local\Temp\u24-r12-b0-20260715-5ab8e9dc`
does not exist.  Therefore dirty B0 was not started.  There is no B0 receipt,
runner result, control commit, push, or CI event to interpret.

## 3. Diagnosis

Two distinct wrapper defects are confirmed.

1. `Get-R12Sha256Bytes` did not admit the valid empty byte array.  Empty
   stderr is required on an admissible B0, so this parameter binding would
   reject every successful B0 even if the calibration marker existed.
2. The synthetic root used `.NET Process.Start()` with an unredirected
   descendant and assumed the root's redirected standard-error handle would
   be inherited again.  The root receipt was captured, but the delayed
   descendant marker was absent and EOF completed with zero stderr bytes.
   That inheritance assumption is false for this launch path on the frozen
   Windows/PowerShell 5.1 runtime.

The first defect surfaced the terminal exception; the stable empty stderr
also independently falsifies the second assumption.  Neither defect concerns
Repair A, B0 tests, the finite quotient, the envelope, MaxEnt, similarity, or
the Lean-oracle learner.

## 4. Frozen disposition

R12 is `FAILED_CLOSED_EXTERNAL_DRAIN_CALIBRATION`.  It makes no scientific
claim and consumes no dirty-B0 or E2 execution budget.  The R12 dirty state is
retained only in its local quarantine worktree and must not be committed,
merged, cherry-picked, rebased, or pushed.

Any continuation requires a new epoch anchored at this closeout.  Its repair
scope must be limited to:

- allowing an empty byte array in the external digest function; and
- replacing implicit descendant inheritance with an explicitly inheritable
  Windows standard-error handle (for example, a Python/Win32 launch that sets
  the handle inheritable and uses `close_fds=False`), followed by one new
  delayed-descendant calibration.

No file-size quiescence window may return.  A new epoch must still require a
common bounded EOF deadline for both copy tasks, one independent host wall,
and no dirty B0 unless its new calibration passes.  It may not add repository
helpers, tests, schemas, ledgers, sidecars, scientific source, GPU/SSH work,
LLM work, K/KP execution, or another control topic.  If the new calibration
passes, the next action remains one dirty B0; if accepted-green control is
eventually reached, the immediate scientific action remains the exact
seven-path R8 E2 source freeze.
