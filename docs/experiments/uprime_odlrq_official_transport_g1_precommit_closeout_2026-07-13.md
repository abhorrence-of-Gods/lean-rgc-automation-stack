# U-prime / ODLRQ official-transport G1 pre-commit closeout

Date: 2026-07-13 (Asia/Tokyo)

Status: **CLOSED — G1 BLOCKED BY FROZEN CAPS BEFORE Q1 COMMIT**

Controlling registration:
`docs/experiments/uprime_odlrq_official_transport_synthetic_qualification_amendment_2026-07-13.md`.

This is a one-file administrative failure record.  Its sole parent is the
accepted Q0 freeze commit `2165d7ee1a522726421fefe03455561b133fbecf`.
It is not a Q0 repair, Q1 semantic commit, Q2 artifact, new preregistration, or
license for another execution.

## 1. Administrative disposition

The final gate status is:

```text
G1_BLOCKED_BY_FROZEN_CAPS
```

This is a pre-Q1 engineering gate disposition, not one of the archival artifact
dispositions in the controlling amendment.  Q1 was not committed, pushed, or
admitted to candidate CI.  Q2 was not started.  No archival live runner,
synthetic `RUN_OPENED`, stage, receipt, result artifact, or scientific endpoint
was executed.

## 2. Q0 authority and CI

Q0 was correctly frozen before the failed integration attempt:

| role | commit/run | job | conclusion |
|---|---|---|---|
| Q0 commit | `2165d7ee1a522726421fefe03455561b133fbecf` | n/a | one amendment document only |
| Q0 candidate CI | run `29213822870` | `86705983190` | success |
| Q0 accepted CI | run `29213936876` | `86706281061` | success |

The accepted branch and remote both pointed to the exact Q0 commit before G1
work began.  The frozen amendment specified a 15-second hard wall for every RPC
frame, a 10-second fixed unit-runner qualification gate, and no permission to
relax either cap after observation.

## 3. Implemented but uncommitted forensic state

The local fixed Q1 worktree contains uncommitted drafts only on the registered
five-path allowlist:

```text
tools/uprime_official_transport_smoke.py
tools/run_uprime_official_transport_smoke.ps1
tools/run_uprime_official_transport_tests.ps1
tests/test_uprime_official_transport_smoke.py
tests/tier_manifest.json
```

Those drafts are not accepted source and are not incorporated by this closeout.
They remain in the fixed local Q1 worktree solely as forensic engineering
material.  The dated operator/session record states that the Q1 ref was not
pushed, restarted, deleted, or force-updated.

## 4. Observed gate evidence

The following is dated operator/session engineering evidence; no immutable Q2
artifact was created.

- The direct fake/fault Python suite reported `26 passed, 1 skipped` in about
  0.56 seconds.  The explicit skip is the real-worker lane.
- The fixed Windows unit runner enabled that real-worker lane and reported
  `26 passed, 1 failed`.
- The failure occurred on the first `load_project` request to the exact worker,
  before any synthetic task initialization or action.
- An independent exact-argv diagnostic used the frozen
  `lean.exe --run RGCKernelRPC.lean --imports Lean` process and one canonical
  `load_project` request.  At 15.052 seconds it had produced zero stdout bytes
  and zero stderr bytes and was killed at the frozen 15-second frame wall.
- PowerShell parser checks were clean, the embedded Job Object C# compiled,
  invalid runner arguments returned 64, and no evidence indicated an
  environment-path or schema mismatch before the timeout.

The first-frame timeout is therefore a genuine frozen-cap infeasibility for
this design.  It is not converted into success by the 26 fake/fault passes.
The fixed unit runner also cannot meet its 10-second qualification gate when a
single required real-worker frame already exceeds 15 seconds.

## 5. Stop-rule adjudication

Q0 section 7 permits pre-archival unprotected calibration only to tighten caps
or show infeasibility; it forbids cap relaxation.  Section 11 requires immediate
stop when a frozen cap is exceeded.  Accordingly:

- the 15-second wall was not raised;
- the 10-second qualification gate was not changed;
- no Q1 commit or repair commit was made;
- no candidate/accepted Q1 CI was requested;
- no archival runner or Q2 publication was attempted;
- no synthetic artifact was fabricated from unaccepted code.

After the first frozen-cap failure, follow-up unprotected diagnostic
invocations were performed before the stop order, including repeated live-lane
execution and the exact-argv probe above.  None passed, reached task
initialization, changed a cap, or opened an archival run.  These diagnostics
strengthened the infeasibility diagnosis but exceeded Q0's literal immediate-
stop rule.  This deviation is not a license for another diagnostic or a
warm-cache acceptance rule.

The controlling amendment specified Q2 only after accepted Q1 and omitted an
explicit closeout branch for a pre-Q1 G1 failure.  This one-file administrative
record is the minimum honest exception: it documents the stop-rule result
without pretending that Q1 or Q2 existed.  It adds no artifact, ledger, CAS,
publisher, receipt registry, recovery coordinator, or new identity guard.

## 6. Exposure and resource accounting

- Work used local Windows CPU only.
- Network use was limited to Git push and read-only hosted-CI inspection.
- The public embedded synthetic fixture was not initialized because
  `load_project` never returned.
- No registered KP3/U05 task input, E1 artifact payload, quarantine file, or
  production task was read as execution data.
- No same-family KP3 endpoint or protected scientific response was rerun.
- No SSH session, remote CPU, GPU, CUDA, model server, LLM proposer, or LLM
  distillation was used.
- The frozen worker and executable were opened only for the registered
  synthetic transport qualification.

These negative-use statements are operator/session governance attestations,
not fields in an archival artifact.

## 7. Program consequence

This result does not test the mathematical upper-stack hypotheses.  It provides
no rank, compression, plateau, quotient, generator, envelope, MaxEnt,
similarity, learner, solve-rate, or deployment evidence.  It also does not
refute the standalone stdlib leaf architecture: the process did not become
ready to answer the first control frame within the chosen wall.

The immediate gate consequence is nevertheless strict.  A new scientific task
family cannot be registered on this transport.  The upper stack remains behind
the exact-domain/rank gate, GPU remains unlicensed, and LLM proposal or
distillation remains last.

## 8. Only permissible continuation

Any continuation must be a separate, dated amendment.  If this closeout's
candidate and accepted CI are green, its only parent is the accepted closeout.
If closeout candidate CI is red, accepted Q0 may remain the parent only if the
new amendment explicitly cites the immutable closeout ref, hash, and red run.
It must not modify Q0/Q1 in place or reuse Q1's repair quota.  Before
implementation it must:

1. distinguish worker startup/load-project latency from post-load per-action
   RPC latency rather than applying one frame wall to both;
2. freeze a startup/control wall and a separate action wall with an explicit
   calibration rule and hard overall cap;
3. retain exact `-I -S -B`, Job-before-PROBE, READY-before-marker/ARM, the
   stdlib-only leaf, public synthetic fixture, and all protected-input denials;
4. retain the real-worker lane as a mandatory gate rather than substituting
   fake-only success;
5. keep the five-path/maximum-two-commit/anti-ledger budget or make any change
   explicit before execution;
6. state a pre-Q1 failure closeout branch so this topology omission does not
   recur.

No additional measurement or implementation is licensed by this document.

## 9. Mandatory nonclaims

This closeout does not call Q1 implemented, the synthetic transport qualified,
the exact worker defective, the 15.052-second censored latency a complete
startup measurement, or a larger future cap justified.  It does not reopen E1,
license the C2 client/adapter, or advance exact quotient, worst-case envelope,
MaxEnt, global similarity, locality learning, GPU, or LLM work.  The only claim
is that Q0's own G1 gate could not pass under its frozen caps.  The cap was not
relaxed and archival execution was stopped, with the post-failure diagnostic
overrun disclosed above.
