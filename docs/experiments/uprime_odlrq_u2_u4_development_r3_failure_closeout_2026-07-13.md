# U-prime / ODLRQ U2--U4 R3 failure closeout

Date: 2026-07-13 (Asia/Tokyo)

Terminal observation recorded: 2026-07-14 (Asia/Tokyo)

Status: `U24_E1_ENVELOPE_BLOCKED`

E1 stage disposition: `NOT_COMMITTED / NOT_EMITTED / NOT_ACCEPTED`

Cause: `FROZEN_E1_COLD_MARGIN_UNSATISFIED / fixed guarded-runner overhead
outside the E1 path authority`

Authority:
`docs/experiments/uprime_odlrq_u2_u4_development_r3_stage_local_reentry_amendment_2026-07-13.md`
at immutable R3 bootstrap commit
`4b0fa1ff2f701b1814a835d3b43f1251a92a3296`, inheriting A2 and sections
9, 13, and 14 of the original construction authority.

Parent: accepted E0 commit
`80b09bc8eaae63739d2078b3f206e2fd31386ebc`.

This one-file closeout remains a draft until it is committed as the sole-parent
child of `80b09bc...` on the registered failure ref
`codex/uprime-u2-u4-development-r3-failure-closeout`, passes candidate CI, is
fast-forwarded as the identical SHA/tree to the accepted branch, and passes a
distinct accepted CI.  A closeout-CI failure stops without repair or recursion.

## Accepted R3 predecessor

The R3 composite bootstrap commit `4b0fa1ff...` passed candidate CI run
`29293443408`.  The identical SHA/tree was fast-forwarded to the accepted
branch and passed distinct accepted CI run `29293633214`.

E0 then changed only its three registered paths and was committed as
`80b09bc...`.  That immutable commit passed candidate CI run `29294411968`,
job `86964703247`, with exactly:

```text
2590 passed, 8 skipped, 161 deselected in 172.76s
```

The identical SHA/tree was fast-forwarded to the accepted branch and passed
distinct accepted CI run `29294581465`, job `86965221964`, with exactly:

```text
2590 passed, 8 skipped, 161 deselected in 173.86s
```

The accepted line therefore contains a qualified exact finite quotient
coordinate generator and no E1 source.  This closeout neither relabels nor
weakens the accepted E0 result.

## Preserved uncommitted E1 implementation

After accepted E0, E1 was developed only in the dedicated uncommitted R3
build worktree on branch `codex/uprime-u2-u4-development-r3-build`, still at
parent `80b09bc...`.  Its dirt is restricted to the six frozen E1 paths:

| worktree status | bytes | SHA-256 | path |
|---|---:|---|---|
| modified | 153187 | `21030E4DD3C392D5EA2A9DEA1D5A8354F57AFE1301A59CFA6B0A2CDEE199EF16` | `lean_rgc/odlrq/quotient_generator.py` |
| untracked | 87121 | `13C4F4D97AFFB363A1EC484BDDD870AF9FB88B0C0796D6728AC774DE941D5496` | `lean_rgc/odlrq/envelope.py` |
| modified | 13341 | `F968B3BC4EB945811E88553F118856658CE45D476B94860B56D7F39DBE90D752` | `lean_rgc/odlrq/__init__.py` |
| modified | 59547 | `4D1FAF8C725BB2EA9FAD01E83A330C578B1ABE01840EAD263E98D174A84CA7C0` | `tests/test_odlrq_quotient_generator.py` |
| untracked | 32675 | `90580302C24F99B8CAF1500EF013296E214D2206F6C936D781BAA8E8A64832D5` | `tests/test_odlrq_envelope.py` |
| modified | 8827 | `D955F797DFA2F4C0943F5F385F9301CED0A9D592BE19D459BF5EB2BEEB657854` | `tests/tier_manifest.json` |

These exact bytes are preserved as diagnostic source material only.  They
implement the declared-synthetic finite-fiber weights and laws, weighted
compression and lifting, complete sparse transfer rectangle, exact positive
majorant and maximizer certificate, independent `Fraction` verification,
domain/completeness witnesses, and fiber-extension monotonicity checks.  They
were not staged, committed, pushed, imported into this failure line, emitted
as an artifact, or accepted as E1.

Focused Windows CPU diagnostics on the final bytes passed:

```text
quotient-generator selection: 34 passed in 3.29s
exact E1 selection:            48 passed in 23.92s
exact E1 outer stopwatch:      25.285s
```

The final blocker-only multi-agent adversarial pass found no open P0 or P1
correctness, authority, tier, completeness, or test-contract defect.  Those
observations show that the bytes are suitable material for a future fresh
qualification attempt; they are not an official E1 result and do not create
the registered envelope token.

## Official E1 qualification failure

The registered dirty-worktree command was exercised during uncommitted E1
engineering on the intended six E1 paths:

```powershell
& .\tools\run_uprime_u2_u4_development_tests.ps1 -Lane E1
```

Multiple engineering invocations returned `125`; the final quiet invocation
is the terminal R3 observation.  The lane has a fixed 120-second hard wall and
the inherited three-times cold-margin rule, so a qualifying parent stopwatch
must be at most 40 seconds.  By the runner's branch order, reaching the margin
failure proves only that the child exited zero, no hard resource failure was
set, and the parent stopwatch was greater than 40 and at most 120 seconds.
External process polling placed the final observation at roughly 60 seconds,
but that estimate is non-authoritative and is not an elapsed-time receipt.  The
parent exited `125` with exactly:

```text
three-times cold-margin requirement failed
```

No qualifying E1 receipt was emitted.  The registered success disposition
`CPU_SYNTHETIC_FIBER_ENVELOPE_CORE_VERIFIED` was not reached.  There was no
test assertion failure, false weighted round-trip, false majorant inequality,
decreasing extension witness, tier crossing, hard timeout, memory cap, output
cap, protected read, or forbidden capability use.

The paired timings isolate the engineering boundary.  The direct exact
48-test selection has more than threefold margin under the 120-second wall,
but the official child installs the frozen denial guard before it starts the
cold pytest selection.  That fixed guarded-bootstrap cost is included in the
parent qualification stopwatch.  The runner and guard are outside all six E1
source/test paths, while the E1 test selection, 120-second wall, and
three-times rule are frozen by the inherited authority.  Altering the guard,
runner, wall, selection, or qualification rule would expand the registered E1
path and contract rather than repair the mathematical implementation.

## Frozen adjudication

R3 requires dirty qualification before an E1 commit and stops on an
ineligible failure, a specification/path expansion, or work that would need a
second authority change.  It does not license raising the wall, deleting
tests, bypassing the guard, changing the stopwatch boundary, adding a runner,
committing an unqualified E1 stage, or continuing to E2.  The failure is
therefore closed at the registered terminal label
`U24_E1_ENVELOPE_BLOCKED`.

No official E1 exists under R3.  No E1 artifact directory or envelope token
was created.  E2, ME0, S0, I0, EMIT, and success CLOSEOUT were not executed.
No protected K1--K4 result was read.  No native Lean/RPC, official transport,
remote CPU, SSH, GPU/CUDA, model server, LLM, deployment, MaxEnt fit,
global-similarity certificate, or locality learner was run.

The terminal is an implementation-harness qualification failure, not a
mathematical or scientific failure.  In particular, the direct diagnostics
do not prove the E1 theorem, but the frozen margin failure supplies no evidence
against exact quotient coordinates, the weighted fiber majorant, extension
monotonicity, worst-case stabilization, MaxEnt model selection inside a hard
support, finite-approximation-stable global similarity, or Lean-oracle
locality learning.

The six diagnostic files and their byte identities must remain preserved.
Only a future, separately frozen harness amendment may continue.  Such an
authority must re-enter from accepted E0, explicitly account for the fixed
pre-pytest guard cost while retaining a genuine cold resource margin, freeze
its runner/guard/path boundary before execution, and independently requalify
the preserved mathematical bytes.  This closeout neither selects that repair
nor licenses outcome-dependent weakening.
