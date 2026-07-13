# U-prime / ODLRQ official transport v2 recovery failure closeout

Date: 2026-07-13 (Asia/Tokyo)

Status: `RECOVERY_LIVE_PREFLIGHT_BEFORE_BATCH_OPENED`

Authority: `docs/experiments/uprime_odlrq_official_transport_v2_precommit_recovery_amendment_2026-07-13.md`
at accepted commit `5d06bad78bf93e5d0cee12c0e823de06e89575a9`.

Parent: accepted recovery I2 commit
`40d5f5a0d91fabf75c0f3ccd74c86590b6a79538`.

## Frozen gate evidence

The recovery I2 source candidate passed CI run `29218232565`, job
`86718206075`.  It was fast-forwarded to the accepted branch and passed
accepted CI run `29218391074`, job `86718636384`.

H6 then created the sole canonical live worktree at
`C:\Users\yusei\Desktop\lean_rgc_automation_stack_v47_goal_state_dynamics_transport_v2_recovery_live`
on ref `codex/uprime-official-transport-v2-precommit-recovery-result`, with
parent `40d5f5a0d91fabf75c0f3ccd74c86590b6a79538` and tree
`aeae562961affe7f528489ee7f252871e2b3c397`.

H7 invoked the official live runner exactly once under the frozen Windows
PowerShell executable.  It exited `65` before `BATCH_OPENED` with:

```text
uprime-official-transport-v2: accepted-tree I1 files differ from external digests
{"additional_live_worker_diagnostics":0,"marker_owned":false,"route":"F"}
```

The runner therefore owned no marker, launched no Lean worker, and published
no result artifact.  The result ref has no result commit and was not pushed.
No second runner invocation, post-failure live-worker diagnostic, digest
repair, artifact migration, or replacement ref is permitted or performed.

## Verdict and scope

The recovery closes as
`RECOVERY_LIVE_PREFLIGHT_BEFORE_BATCH_OPENED`.  This is a transport preflight
failure, not evidence for or against C2/KP3, D4 rank or compression, exact
quotient, worst-case envelope, MaxEnt, global similarity, locality learning,
solve rate, GPU execution, deployment, or LLM proposal/distillation.

Any later attempt to explain or repair the external-digest attestation boundary
requires new prior authority.  This closeout records the immutable one-shot
outcome only and creates no such authority.
