# U-prime / ODLRQ U2--U4 development-construction failure closeout

Date: 2026-07-13 (Asia/Tokyo)

Status: `U24_B0_IDENTITY_OR_RUNNER_BLOCKED`

Guard disposition: `NOT_EMITTED`

Fixture digest: `NOT_CREATED / NOT_APPLICABLE` (B0 constructs no
mathematical fixture)

Cause: `CI_SETUP_WORKTREE_DIRT / unregistered_path`
(`lean_rgc.egg-info/*`)

Authority:
`docs/experiments/uprime_odlrq_u2_u4_development_construction_bundle_amendment_2026-07-13.md`
at accepted A0 commit `14234e209229931c00615d4b171620ec6d1bbbf5`.

Parent: accepted A0 commit
`14234e209229931c00615d4b171620ec6d1bbbf5`.

The A0 candidate passed CI run `29220100153`, job `86723388478`.  The exact
A0 commit was then fast-forwarded to the accepted branch and passed distinct
accepted CI run `29220232702`, job `86723755880`.

## Rejected build lineage

The append-only build ref
`codex/uprime-u2-u4-development-build` preserves:

```text
3e6331a6b1bbcca3ca3acfea02daeb0c8de62406  initial B0 commit
7ca946ef6c23cf0855cd3942eecbe20663f70e21  sole bundle correction
```

The initial B0 commit had no GitHub Actions run and is not described as a red
CI run.  Its correction repaired only B0 identity infrastructure: cross-
checkout CRLF identity, terminal dirty-state rejection, and stale Python
bytecode isolation.  Three independent local audits approved the corrected
bytes, including an attack with an effective forged repository `.pyc`.

On the clean correction commit, the registered Windows command

```powershell
& .\tools\run_uprime_u2_u4_development_tests.ps1 -Lane B0
```

passed all five B0 contracts with disposition
`CPU_U24_IDENTITY_AND_RUNNER_GATE_VERIFIED`, elapsed
`102514063 / 10000000 = 10.2514063` seconds, peak job memory `53764096`
bytes, and zero captured output bytes.  The supporting 29-test local suite also
passed.  These local diagnostics do not substitute for candidate and accepted
CI.

## Candidate CI failure

The sole-correction candidate `7ca946ef6c23cf0855cd3942eecbe20663f70e21`
failed CI run `29223348434`, job `86732622987`, after a full-history exact-head
checkout.  Installation and both pre-test checks passed.  The test step ended
with:

```text
1 failed, 2580 passed, 8 skipped, 161 deselected
```

The failing test was
`test_u24_b0_anchor_contiguous_budget_and_terminal_topology`.  Before pytest,
the fixed CI command `python -m pip install -e ".[test]"` created these six
untracked paths in the checkout:

```text
lean_rgc.egg-info/PKG-INFO
lean_rgc.egg-info/SOURCES.txt
lean_rgc.egg-info/dependency_links.txt
lean_rgc.egg-info/entry_points.txt
lean_rgc.egg-info/requires.txt
lean_rgc.egg-info/top_level.txt
```

The full-status B0 identity assertion rejected those unregistered paths as
designed.  No denial guard emitted `U24_RESOURCE_OR_SCOPE_BLOCKED`.  The
observed terminal label is the B0 label
`U24_B0_IDENTITY_OR_RUNNER_BLOCKED`.

This is a deterministic CI/package-install integration omission.  It is not a
shallow-history incident: Actions checkout used `fetch-depth: 0`, and the
tested head was exact.  It is also not a scientific endpoint failure.  The
accepted branch remained at A0; B0 was never accepted.

## Frozen adjudication

The bundle-wide correction quota was consumed by `7ca946e...`.  The frozen
authority therefore prohibits another identity, runner, workflow,
`.gitignore`, status-filter, or allowlist repair, and it prohibits an E0 start
or a rerun under this authority.  The rejected build commits and the
correction's red CI remain on the build ref; neither commit is imported into
this failure-closeout line.

No artifact directory was created.  E0, E1, E2, ME0, S0, I0, EMIT, and
CLOSEOUT were not executed.  No K1--K4 or protected result was read.  No Lean
RPC, remote CPU, SSH, GPU, LLM, deployment, MaxEnt fit, global-similarity
certificate, or locality learner was run.

This closeout is evidence only that the frozen B0/CI integration was
insufficient.  It is not evidence that the upper mathematical program is
impossible, and claims no protected K1--K4 performance, same-family D4 rank,
production Lean locality, complete all-germ quotient, production hard
envelope, MaxEnt safety, global Lean similarity, learner improvement, solve
rate, deployment, remote/GPU work, or LLM benefit.  In particular, it makes no
claim for or against exact quotient coordinates, worst-case envelopes, MaxEnt
model selection, finite-approximation-stable global similarity, or Lean-oracle
locality learning.  Any repair or replacement construction bundle requires
new prior authority after this failure closeout is accepted.
