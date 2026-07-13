# U-prime / ODLRQ official-transport v2 precommit recovery amendment

Date: 2026-07-13 (Asia/Tokyo)

Status: **REGISTERED BEFORE RECOVERY SOURCE CREATION OR EXECUTION**

Sole parent authority: accepted failure closeout
`b6abf5eddf7702239ff2fd65b1d33f8b5c58bcd4`.  Its candidate CI is run
`29217386354`, job `86715802509`, success; its accepted CI is run
`29217531656`, job `86716215010`, success.

## 1. Narrow registered question

The closed v2 phase reached 29 passing fake/fault tests but its official G2
wrapper exited `1` while formatting the final success message.  No I1 commit,
push, candidate CI, live root, `BATCH_OPENED`, official/live fixture
`--official-child` Python process, or Lean process was created.  The immutable record is
`docs/experiments/uprime_odlrq_official_transport_v2_failure_closeout_2026-07-13.md`.

This recovery asks only:

> Does the exact stopped five-path source, under new Git/runtime authority and
> with the one registered format-expression repair, pass its fake gate and CI,
> so that the already-frozen v2 5+1 live attempt may be executed once?

This is not a new transport design and does not reopen Q0, Q1, or v2 I1.  All
clock, schema, fixture, cap, marker, failure, and nonclaim rules in
`uprime_odlrq_official_transport_v2_amendment_2026-07-13.md` remain binding.

## 2. Frozen source provenance and allowed delta

The old uncommitted worktree remains forensic-only.  Recovery reapplication
must begin from these exact staged Git blobs:

| path | frozen staged blob |
|---|---|
| `tools/uprime_official_transport_v2_smoke.py` | `3eb21461a552cfb36e944bf1aeded6fb6bd45fce` |
| `tools/run_uprime_official_transport_v2_smoke.ps1` | `a5e6e630409b0a13d63fc8b72f41af9241e12761` |
| `tools/run_uprime_official_transport_v2_tests.ps1` | `e8ae564175e9a1f125f20ead40a959275a9ab9db` |
| `tests/test_uprime_official_transport_v2_smoke.py` | `e134ff8d04926cec9b4be1be16392e790fe5aeaf` |
| `tests/tier_manifest.json` | `88eb765c7c0eb484825e39b956860621db71bc84` |

Before applying the delta, each reconstructed path must reproduce its listed
blob.  Exactly four semantic text changes are allowed:

1. In the unit runner, replace the failing summary expression by the fully
   parenthesized form:

   ```powershell
   [Console]::Out.WriteLine((
       "uprime-official-transport-v2-tests: qualification ticks={0} frequency={1} peak_job_memory={2}" -f `
           $elapsedTicks, $StopwatchFrequency, $peak
   ))
   ```

2. In the live parent set the canonical root to exactly
   `C:\Users\yusei\Desktop\lean_rgc_automation_stack_v47_goal_state_dynamics_transport_v2_recovery_live`.
3. In the live parent set the result ref to exactly
   `codex/uprime-official-transport-v2-precommit-recovery-result`.
4. Update only the corresponding frozen root/ref literals in the unit test.

Line endings may be normalized by Git.  No other code, schema, policy, field,
fixture, wall, margin, process count, disposition, test expectation, manifest
entry, or path may change.  The existing `...V2_I1_...` environment names are
retained as schema-level names and refer to the accepted recovery
implementation; there is no fallback to the old stopped ref.

After the registered delta and LF normalization, the recovered files must have
exactly these identities before H3:

| path | bytes | recovered Git blob | recovered SHA-256 |
|---|---:|---|---|
| `tools/uprime_official_transport_v2_smoke.py` | 70,885 | `3eb21461a552cfb36e944bf1aeded6fb6bd45fce` | `14983F9796F0BD68ACD69D89112537774A3280693E48BF1D6D401E0224373BEC` |
| `tools/run_uprime_official_transport_v2_smoke.ps1` | 83,501 | `760744928e76f6583046ddedb6414682fc568ee5` | `C8F9C2BA0E3E4A72E79DECE37DBEB6696185E55C076396D082CB0B8687BF220E` |
| `tools/run_uprime_official_transport_v2_tests.ps1` | 21,284 | `ba4feed97d82441ead0564e71810a7f3320e035b` | `5D554F4BEF3475282DD0D0070BA061495C8DAF553255D2FBFA6AB99E366CABDF` |
| `tests/test_uprime_official_transport_v2_smoke.py` | 29,989 | `37a772fdee36a48aabe55afe08586d3174ca265d` | `1CFF4BE183F0C7E7ABCD296906FE4465B6504F62555FD20F0721C2D5CA272FEA` |
| `tests/tier_manifest.json` | 8,725 | `88eb765c7c0eb484825e39b956860621db71bc84` | `359AD8EAE47E1EBB365A532514FE769AF27598572A846769081275AE5FB90C2D` |

These values were derived without source creation by applying the four byte
replacements in memory to the frozen base blobs and hashing Git's exact
`blob <length>\0<bytes>` framing.  H2 must reproduce all five values.

## 3. Fixed refs and quotas

### Recovery A0

Fixed ref `codex/uprime-official-transport-v2-precommit-recovery-a0`; one
commit, no repair, adding only this document.

### Recovery I2

Fixed ref `codex/uprime-official-transport-v2-precommit-recovery-i2`; exactly
one source commit, no repair, on the same five paths in Section 2.  The source
commit is permitted only after the official fake/fault gate exits `0` once.
`I2` means the second implementation attempt after the stopped v2 I1; it is
unrelated to the retained schema-level `...V2_I1_...` environment spelling.

### Recovery R

Fixed ref `codex/uprime-official-transport-v2-precommit-recovery-result`;
exactly one result commit, no repair, adding only:

```text
docs/experiments/artifacts/uprime_official_transport_v2_20260713/synthetic_qualification.json
docs/experiments/uprime_odlrq_official_transport_v2_recovery_closeout_2026-07-13.md
```

The canonical live worktree is exactly:

```text
C:\Users\yusei\Desktop\lean_rgc_automation_stack_v47_goal_state_dynamics_transport_v2_recovery_live
```

### Recovery F

Fixed ref `codex/uprime-official-transport-v2-precommit-recovery-failure-closeout`;
one commit, no repair, adding only
`docs/experiments/uprime_odlrq_official_transport_v2_recovery_failure_closeout_2026-07-13.md`.

## 4. Gates and stopping

```text
H0  recovery A0 candidate CI green
H1  accepted fast-forward; accepted CI green
H2  reconstruct exact five blobs; apply only Section 2 delta
H3  one official fake/fault runner invocation exits 0; no Lean capability
H4  recovery I2 commit/push; candidate CI green
H5  accepted fast-forward; accepted CI green
H6  create the one canonical recovery result worktree
H7  one live-runner invocation: five qualification + one archival at most
H8  R candidate/accepted CI green, or immutable R/F failure closeout
```

The H3 command is exactly:

```powershell
& .\tools\run_uprime_official_transport_v2_tests.ps1
```

If H3 is red, recovery I2 remains uncommitted and F is
`RECOVERY_PRECOMMIT_FAKE_GATE`.  If I2 candidate or accepted CI is red, no live
runner executes.  Once a verifiably owned `BATCH_OPENED` exists, every outcome
follows R and no real worker is rerun.  Before it exists, failure follows F.
The number of post-failure live-worker diagnostics is always zero.

All refs are never force-pushed, deleted, or restarted.  Candidate and accepted
CI are required at every listed Git gate.  The work budget is four active hours
or one calendar day.  No extra ledger, publisher, identity guard, recovery
framework, test-specific amendment, or repair commit may be introduced.

The closed failure stages and parents are:

| failure stage | F parent and mandatory action |
|---|---|
| `RECOVERY_A0_CANDIDATE_RED` | accepted `b6abf5eddf7702239ff2fd65b1d33f8b5c58bcd4`; do not accept A0 |
| `RECOVERY_A0_ACCEPTED_RED` | accepted recovery A0; no source creation |
| `RECOVERY_SOURCE_RECONSTRUCTION_MISMATCH` | accepted recovery A0; do not run H3 |
| `RECOVERY_PRECOMMIT_FAKE_GATE` | accepted recovery A0; source remains uncommitted |
| `RECOVERY_I2_CANDIDATE_RED` | accepted recovery A0; no repair or live runner |
| `RECOVERY_I2_ACCEPTED_RED` | accepted immutable I2; no live runner |
| `RECOVERY_LIVE_PREFLIGHT_BEFORE_BATCH_OPENED` | accepted I2; no artifact |
| `RECOVERY_RESULT_CANDIDATE_RED` | accepted remains I2; cite R ref/hash/run without importing its artifact |
| `RECOVERY_RESULT_ACCEPTED_RED` | accepted immutable R; record red control plane without rerun |

If an owned `BATCH_OPENED` exists, the live artifact and one-shot outcome always
remain immutable in R; they are never regenerated or migrated.  An R candidate
or accepted CI red additionally opens the registered administrative F closeout
with the parent specified in the table, but F never imports the R artifact and
never reruns a worker.  If either F candidate or accepted CI is red, retain that
immutable F ref/run and create no repair, replacement ref, or recursive
closeout.

## 5. Evidence and nonclaims

Development-only direct pytest, AST parsing, and extracted C# compilation may
be used before H3, but they cannot turn a red official wrapper green.  H3 is
fake/fault-only: its PATH contains no Lean and pytest poisons `Popen`.  The real
Windows Job/orphan-zero assertion remains integrated into the fixed live 5+1
processes and never creates a seventh worker.

Success qualifies only the public synthetic stdlib transport boundary already
defined by v2.  It does not qualify C2/KP3, D4 rank or compression, exact
quotient, worst-case envelope, MaxEnt, global similarity, locality learning,
solve rate, GPU, or deployment.  SSH, remote CPU, GPU/CUDA, model servers, LLM
proposal, and LLM distillation remain forbidden in this recovery.

After a successful closeout, the retained scientific order is unchanged:

```text
new registered D4 family
  -> exact behavioral quotient
  -> quotient-coordinate generator
  -> positive finite-horizon worst-case envelope
  -> MaxEnt nominal law inside the envelope
  -> typed predictive/positive global similarity
  -> nominal Lean-oracle locality CEGAR
```
