# U-prime / ODLRQ U2--U4 R2 failure closeout

Date: 2026-07-13 (Asia/Tokyo)

Status: `U24_E0_GENERATOR_BLOCKED`

E0 stage disposition: `NOT_COMMITTED / NOT_EMITTED / NOT_ACCEPTED`

Cause: `FROZEN_E0_COLD_MARGIN_UNSATISFIED / pre-existing wall-design failure`

Authority:
`docs/experiments/uprime_odlrq_u2_u4_development_r2_exact_admission_integration_amendment_2026-07-13.md`
at immutable A2 commit `7c05c494ce79e84ffeb0d0c912ca3ba5f141f402`,
as activated by the one-time topology bootstrap at commits
`3970b4f505b842a76573329aaa526a1af08da7c4` and
`de8d7e6e3f0cb41b514de25f6b3867bde49033f0`.

Parent: accepted corrected T0 commit
`de8d7e6e3f0cb41b514de25f6b3867bde49033f0`.

This one-file closeout remains a draft until it is committed as the sole-parent
child of `de8d7e6...`, passes candidate CI, is fast-forwarded as the identical
SHA/tree to the accepted branch, and passes a distinct accepted CI.  A
closeout-CI failure stops without repair or recursion.

## Accepted control-plane predecessor

The immutable A2 candidate at `7c05c49...` had red CI run `29228439065`, job
`86747336553`, with exactly:

```text
1 failed, 2580 passed, 8 skipped, 161 deselected
```

The dated T0 authority records that failure as
`CONTROL_TERMINAL_EPOCH_NOT_REOPENABLE`: the old classifier could not place an
A2 child after the accepted R1 failure terminal.  It was not an E0 admission,
generator, theory, or scientific failure.  The red commit and run remain
immutable.

T0 commit `3970b4f...` reopened only that exact epoch.  Its clean B0 diagnostic
then exposed a committed-state self-reference mismatch.  The sole shared R2
correction `de8d7e6...` changed only the registered identity core and guard.
An investigator-observed clean Windows B0 console run passed all five
contracts with disposition
`CPU_U24_IDENTITY_AND_RUNNER_GATE_VERIFIED`, elapsed `10.4876373` seconds, and
peak job memory `54153216` bytes.  Candidate CI run `29244989629`, job
`86799628732`, passed exactly:

```text
2581 passed, 8 skipped, 161 deselected in 179.26s
```

The exact same commit/tree was fast-forwarded to the accepted branch and
passed distinct accepted CI run `29245245989`, job `86800447682`, exactly:

```text
2581 passed, 8 skipped, 161 deselected in 179.37s
```

T0 therefore remains a valid accepted control-plane predecessor.  This
closeout neither relabels nor weakens it.

## Precommit E0 implementation result

After T0 acceptance, E0 was developed only in the dedicated uncommitted build
worktree.  Its dirt is restricted to the three frozen E0 paths:

```text
lean_rgc/odlrq/quotient_generator.py
lean_rgc/odlrq/__init__.py
tests/test_odlrq_quotient_generator.py
```

The intended bytes implement the fresh admission/reverification chain, exact
`P_action - I` quotient-coordinate rows, strict source sealing and wire
roundtrip, signed-64 and rational caps, total-work preflight, tier rejection,
and all four frozen fixture oracles.  The focused E0 test file passed
`30 passed in 5.85s`; `git diff --check` was clean.  The uncommitted file
digests are preserved as diagnostic identities only:

```text
B9E05757BEAD3D0F26182FA93BB7863D737604529D2DDB46F41291E78575DA9C  lean_rgc/odlrq/quotient_generator.py
BEF1F682E388B3361914C31C4ABEB70F7DB34DB3E8DE2711AA22478F7EC157D7  lean_rgc/odlrq/__init__.py
5ACD68F936BE63AEE946714404AF8CFC65DA3B979DEDC0CF694329D7E46C5E99  tests/test_odlrq_quotient_generator.py
```

The four freshly derived full-wire generator digests were:

```text
g0-self     48678C4629701BAD64C0BC3C4D2B98FE03EC0B5DC1130FEC6C265F9BF5298C2D
g0-move     B3147DA5E7DF6D6C23D311FD5AB8C243DEB54A9EAD5B4206F874047C9204439D
g0-diamond  62887FAFD6E613D5DA73D80C5A6A5E8B89A199FCCFDA416FF84D40F0DC3452A6
g0-members  6DA7F7F95E68462B36C11745E7E5A6035345B3BBCDA31F1E14D6CDDD505F08DF
```

These are synthetic-development diagnostics, not an accepted E0 stage,
published artifact, protected endpoint, or production Lean result.  No E0
commit or push was created, and the worktree remains preserved without being
imported into this closeout line.

The final read-only adversarial review found no production authority, cap, or
tier bypass, but it did find a separate precommit test-completeness blocker.
The construction authority requires kill tests for omission, alteration,
unknown values, and attempted promotion of both mandatory scope fields in
every public wire.  The uncommitted E0 suite asserts the positive scope values
but does not attack those fields at generator, row, and term level.  It also
lacks explicit negative and `2^63` index/count attacks, the source-type-before-
attribute trap, and an independently recomputed source-seal precursor.  Direct
read-only attacks confirmed that the production parsers reject the tested
scope, signed-64, and source-type violations; this is a frozen test-contract
gap, not an observed production-wire bypass.  These omissions would have
blocked an E0 commit even if the cold margin had passed, and they were not
repaired after the independently terminal wall-design result.

## Frozen cold-margin blocker

The registered Windows command was run on the intended dirty E0 bytes:

```powershell
& .\tools\run_uprime_u2_u4_development_tests.ps1 -Lane E0
```

Its semantic child completed all 35 selected tests successfully within the
60-second hard wall.  The parent nevertheless exited `125` with
`three-times cold-margin requirement failed`; an external observation of one
run measured `44.862` seconds from ARM to child receipt.  The runner suppresses
a qualifying receipt when the margin fails.  There was no test assertion,
hard timeout, memory-cap, output-cap, protected-read, or capability failure.

A read-only baseline probe then isolated the wall design from the new E0
implementation.  A disposable detached worktree at accepted `de8d7e6...`
added only the E0 schema marker as an explicitly nonqualifying diagnostic and
ran the unchanged official E0 lane.  The same runner again completed its child
inside 60 seconds but rejected the `wall >= 3 * isolated measured lane time`
condition, showing elapsed time greater than 20 seconds on that accepted-base
observation before any E0 implementation was present.  The identical
inherited 24 quotient-generator
tests plus five identity tests passed directly as `29 passed in 22.76s`, with
an outer stopwatch of `23.976884s`.

The disposable probe was removed after absolute-path, Git-toplevel, HEAD, and
dirt verification.  It made no commit or push, did not change the active E0
worktree, and did not touch the investigator-owned `docs/external/` dirt.

This paired observation supports the adjudication of a pre-existing frozen
runner/test-selection wall-design defect, rather than a regression caused by
the exact quotient-coordinate implementation.

## Frozen adjudication

A2 requires every stage to pass deterministic dirty-worktree qualification
before commit.  It also freezes the E0 wall at 60 seconds and requires the wall
to be at least three times isolated measured lane time.  Its anti-fractal rule
explicitly prohibits repairing a wall-design failure with a second runner.
The only correction was already consumed by corrected T0 and, independently,
no correction may change a wall, runner contract, cap, allowlist, or endpoint.

It would therefore be unregistered to raise the wall, delete inherited tests,
weaken the three-times rule, add another runner, commit a knowingly
unqualified E0 stage, or continue to E1.  R2 closes at the registered terminal
label `U24_E0_GENERATOR_BLOCKED`.

No E0 artifact directory was created.  E1, E2, ME0, S0, I0, EMIT, and
CLOSEOUT were not executed.  No protected K1--K4 result was read.  No native
Lean/RPC, official transport, remote CPU, SSH, GPU/CUDA, model server, LLM,
deployment, MaxEnt fit, global-similarity certificate, or locality learner was
run.

A future, separately frozen authority may reuse the preserved E0 bytes only
after it corrects or replaces the pre-existing E0 lane selection/calibration
contract and closes the recorded test gaps without using a protected outcome.
One narrow candidate repair is to give E0 a genuinely stage-local selection
whose accepted-base cold time fits a preregistered wall with at least
threefold margin; that decision is not licensed or made by this closeout.

This closeout is evidence only that the frozen R2 E0 qualification failed on
its observed accepted-baseline run under the registered stopping rule.  It is
not evidence that the E0 implementation, exact quotient coordinates,
worst-case envelopes, MaxEnt
model selection, finite-approximation-stable global similarity, or
Lean-oracle locality learning is impossible.  It claims no protected K1--K4
performance, same-family D4 rank, production Lean locality, complete all-germ
quotient, production hard envelope, MaxEnt safety, global Lean similarity,
learner improvement, solve rate, deployment, remote/GPU benefit, or LLM
benefit.
