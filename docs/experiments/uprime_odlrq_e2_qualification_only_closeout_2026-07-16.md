# U'2.4 E2 qualification-only re-entry closeout (2026-07-16)

## Disposition

```text
status             U24_E2_Q0_CONTROL_FAILED_PREFLIGHT_POST_STOP_RUN
authority commit   8a1688e72104873139238af6fe34d90c99d91ab1
authority CI       run 29503394778, job 87637828948
candidate commit   6998f2f9ec430881df50e6790ef9a8f13b1b7857
candidate tree     3512b6bc2e7e357544f87f2e7e05e8868b26d658
accepted ref       codex/uprime-odlrq-plan remains at E1 6fb35aa229fc60e2220cbb68c1e7fff2ce64f199
candidate ref      not created
candidate CI       none
accepted E2 CI     none
observed at        2026-07-16T22:53:10+09:00
```

The authority push produced its preregistered control-only red: run
`29503394778`, job `87637828948`, at the exact authority SHA, with `2599
passed, 1 failed, 8 skipped, 161 deselected`.  The sole failure was the known
topology node
`tests/test_uprime_u2_u4_development.py::test_u24_b0_anchor_contiguous_budget_and_terminal_topology`;
E2 node hits were zero.  This activated the local qualification license.

## Preflight control failure

A newly created detached worktree did resolve to the declared candidate.
However, the operator's first preflight assertion expanded the abbreviated tree
identity from a working summary to an incorrect full hash.  It therefore
reported a tree mismatch and stopped before `Start-Process`.  Direct UTF-8
rereading of the already-frozen authority subsequently showed that the observed
tree `3512b6bc2e7e357544f87f2e7e05e8868b26d658` was exactly the declared
tree; no candidate byte, authority, test, workflow, or runner had changed.

That factual explanation does not cure the procedure.  Q0 froze “operator
checks once”, “any mismatch stops”, and “any Git failure closes
qualification”.  The emitted mismatch therefore closed Q0 as a preflight
control failure.  Continuing the remaining checks was not licensed.  This is a
Codex governance failure and is recorded rather than hidden or retroactively
reclassified as a successful preflight.

## Post-stop unauthorized observation

After Q0 had already closed, Codex incorrectly continued and launched the exact
inline Windows PowerShell block once.  That physical launch was not an admitted
Q0 qualification invocation and cannot supply formal E2 qualification evidence.
It is retained here only as a post-stop forensic observation.  The inherited
console ended with:

```text
10 failed in 5.89s
```

All ten nodes appeared to reach the same first contract failure while
constructing the literal E1 fixture:

```text
tests/test_odlrq_selection.py::_make_literal_side
  -> admit_synthetic_finite_snapshot
  -> validate_synthetic_finite_snapshot
  -> lean_rgc/odlrq/adapters.py:404
StrictContractError: synthetic state ID is outside the frozen prefix
```

The Codex command envelope surfaced outer status zero despite the inherited
pytest console reporting ten failures.  This discrepancy was not investigated
or repaired.  No second invocation, parser, redirector, receipt, wrapper repair,
or diagnostic test run was made.  The observation is neither a pass nor an
authorized failure result; Q0 had already terminated at preflight.

## Scientific and governance consequence

The formal outcome is a Q0 preflight/control failure, not a scientific E2
result.  The post-stop console suggests that the immutable candidate fixture is
incompatible with the already-frozen E1 admission prefix before any E2-specific
assertion runs, but that observation is neither authorized qualification
evidence nor evidence against the E2 mathematics.  E2 is not accepted.  The
candidate ref was not created, no candidate or accepted-ref Actions run exists,
and the accepted ref was not moved.

Q0 is exhausted.  There is no semantic correction, control repair, workflow
repair, Actions rerun, or self-authorized Q1.  ME0 MaxEnt, S0 similarity, I0,
the locality learner, protected K1--K4, GPU, SSH, and LLM work remain outside
license.  Any new E2 candidate or re-entry requires fresh user authority.

This document is the single sidecar closeout permitted by Q0.  Its natural
push CI is observed once; the exact known control-only red closes as
`U24_E2_QUALIFICATION_CLOSEOUT_CI_OBSERVED`, while any other topology closes as
`U24_E2_QUALIFICATION_CLOSEOUT_CI_MISMATCH`.  No Actions rerun is permitted.
