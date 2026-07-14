# U-prime / ODLRQ U2--U4 R4 failure closeout

Date: 2026-07-14 (Asia/Tokyo)

Status: `U24_E1_ENVELOPE_BLOCKED`

E1 stage disposition: `NOT_COMMITTED / NOT_PUSHED / NOT_EMITTED / NOT_ACCEPTED`

Subcause: `POWERSHELL_5_1_E1_TABLE_CARDINALITY_CONTROL_PREFLIGHT`

Scientific interpretation: `NON_MATHEMATICAL_CONTROL_PREFLIGHT_FAILURE`

Authority:
`docs/experiments/uprime_odlrq_u2_u4_development_r4_guard_canonicalization_reentry_amendment_2026-07-14.md`
at immutable R4 bootstrap commit
`fbc1259dc276265a8949aad86d9e15b87e4a6dff`.

R4 stops at the first official dirty E1 invocation.  This closeout records the
failure without converting it into an E1 result, using the R4 correction
quota, or changing any frozen E1 byte, test, wall, runner, guard, or endpoint.

## 1. Immutable R4 bootstrap

The R4 bootstrap is the sole-parent child

```text
fbc1259dc276265a8949aad86d9e15b87e4a6dff
parent 773a4bae0ed6c88fe855d92a69a211f8834c688c
tree   e17b8dd85e6ee4bf299c6dcfc491deb7119253c5
```

of the accepted R3 failure closeout.  It changed exactly the registered four
bootstrap paths and no E1 path:

```text
docs/experiments/uprime_odlrq_u2_u4_development_r4_guard_canonicalization_reentry_amendment_2026-07-14.md
tests/test_uprime_u2_u4_development.py
tests/uprime_u24_guard.py
tools/run_uprime_u2_u4_development_tests.ps1
```

The dirty four-path bootstrap passed its registered B0 runner with the
following success receipt fields:

| state | tests passed | wall ticks | peak Job memory bytes |
|---|---:|---:|---:|
| dirty bootstrap worktree | 5 | 62743169 | 55185408 |
| clean `fbc1259d...` commit | 5 | 63945131 | 55214080 |

Both receipts carried the B0 success disposition
`CPU_U24_IDENTITY_AND_RUNNER_GATE_VERIFIED`.  No bootstrap correction was
created.

The clean bootstrap commit then passed candidate CI run `29309634540`, job
`87010470961`, with exactly:

```text
2590 passed, 8 skipped, 161 deselected
```

The identical `fbc1259d...` SHA/tree was fast-forwarded to
`codex/uprime-odlrq-plan` and passed distinct accepted CI run `29310057446`,
job `87011718613`, again with exactly:

```text
2590 passed, 8 skipped, 161 deselected
```

Thus the R4 bootstrap and its control-plane repair were accepted before any
E1 execution.  The accepted line still contained no E1 source commit.

## 2. Exact preserved E1 import bytes

The dedicated R4 build worktree was based on the accepted bootstrap commit.
Its dirt was exactly the six registered E1 paths.  Before official execution,
independent read-only preflight confirmed every byte length, SHA-256 digest,
and Git blob below:

| bytes | SHA-256 | Git blob | path |
|---:|---|---|---|
| 153187 | `21030E4DD3C392D5EA2A9DEA1D5A8354F57AFE1301A59CFA6B0A2CDEE199EF16` | `1e1576ad1f51ebf667bc55d159048c0ae6587524` | `lean_rgc/odlrq/quotient_generator.py` |
| 87121 | `13C4F4D97AFFB363A1EC484BDDD870AF9FB88B0C0796D6728AC774DE941D5496` | `0618f603b86eba3c61c9fb2e15c4edaacce44a14` | `lean_rgc/odlrq/envelope.py` |
| 13341 | `F968B3BC4EB945811E88553F118856658CE45D476B94860B56D7F39DBE90D752` | `f97272d5de222fb555a78639d66eb89e77e63d86` | `lean_rgc/odlrq/__init__.py` |
| 59547 | `4D1FAF8C725BB2EA9FAD01E83A330C578B1ABE01840EAD263E98D174A84CA7C0` | `400f630e10ddbd98657fd1b142c6b202a8656c7d` | `tests/test_odlrq_quotient_generator.py` |
| 32675 | `90580302C24F99B8CAF1500EF013296E214D2206F6C936D781BAA8E8A64832D5` | `66f9be1a3c5455b822b229fc2024b9c58b768fff` | `tests/test_odlrq_envelope.py` |
| 8827 | `D955F797DFA2F4C0943F5F385F9301CED0A9D592BE19D459BF5EB2BEEB657854` | `8bb7810cc49b56aff3d7b18020dab475644911a2` | `tests/tier_manifest.json` |

The same preflight confirmed that `HEAD` and the local accepted ref were the
identical bootstrap commit, the control files were clean, the current dirty
state was a first E1 import rather than a correction, and the manifest and
runner selected the exact three E1 test modules with the frozen exact count
gate of 48 passed tests.

Static multi-agent review returned `APPROVE` with no open P0 or P1 blocker for
the four-path bootstrap, guard canonicalization and stable-operand repair,
identity/runner topology, exact E1 byte binding, prohibition of an E1
correction, manifest selection, and terminal topology.  These approvals were
pre-execution engineering evidence only.  They did not execute the official
E1 child and did not create an E1 certificate or result.

## 3. Official dirty E1 control-preflight failure

The exact registered dirty-worktree command was:

```powershell
& .\tools\run_uprime_u2_u4_development_tests.ps1 -Lane E1
```

It exited with code `1` and exactly reported:

```text
uprime-u2-u4-development: E1 frozen byte table cardinality changed
```

The failure occurred in the outer PowerShell control preflight, before the
guarded Python child was created.  Consequently:

- no E1 child process started;
- no pytest collection or E1 test ran;
- the frozen 48-test endpoint was not observed;
- no lane receipt was written; and
- no success disposition or artifact was emitted.

The root cause is a Windows PowerShell 5.1 representation mismatch in the new
exact-byte preflight.  `ConvertFrom-Json` returns the top-level six-element
JSON array as one `Object[]` pipeline item in this runtime.  Wrapping that
result again with `@(...)` produces a one-item outer array, so the preflight's
cardinality check observes `Count == 1` rather than six and fails closed.
The six JSON rows and all six E1 files remain byte-identical to their frozen
values; the error does not report a missing or altered E1 file.

This is therefore a control-preflight implementation defect, not an E1
mathematical, scientific, test, resource, or capability failure.  In
particular, R4 observed no failed fiber law, quotient law, exact rational
oracle, positive-majorant inequality, extension monotonicity check, tier
firewall, timeout, memory limit, output limit, protected read, or forbidden
capability.

## 4. Frozen adjudication and stop

The R4 amendment makes the exact E1 import non-correction-eligible and states
that an E1 failure or bootstrap specification error stops the epoch.  The
outer parser defect is in the frozen runner/control boundary, not in any of
the six E1 paths.  Repairing it would change a bootstrap control file after
the official E1 attempt and cannot be represented as an E1 correction.

R4 therefore terminates at:

```text
U24_E1_ENVELOPE_BLOCKED
subcause: POWERSHELL_5_1_E1_TABLE_CARDINALITY_CONTROL_PREFLIGHT
```

No R4 correction is licensed.  No E1 commit was created, staged, pushed, or
fast-forwarded.  E2, ME0, S0, I0, EMIT, and success CLOSEOUT were not run.
No protected K1--K4 endpoint was read.  No native Lean/RPC, remote CPU, SSH,
GPU/CUDA, model server, LLM proposer, knowledge distillation, deployment, or
external publication was used.

The failure supplies no evidence against the preserved exact E1 mathematics
or the upper-stack program.  It only shows that the R4 PowerShell 5.1
preflight encoded the frozen six-row table with the wrong container depth.

Continuation requires a separately dated and frozen R5 authority.  R5 must
re-anchor at this immutable R4 failure-closeout child of the accepted R4
bootstrap, repair and adversarially bind the PowerShell 5.1 array-shape
handling before execution, preserve the exact six E1 bytes and all
walls/tests/endpoints, pass distinct candidate and accepted bootstrap CI, and
only then make a fresh official dirty E1 attempt.  This R4 closeout does not
select an implementation beyond that requirement and does not license
outcome-dependent weakening.
