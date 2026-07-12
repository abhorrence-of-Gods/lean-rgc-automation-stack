# U-prime / ODLRQ lane-isolated recovery control-plane successor

Date: 2026-07-12 (Asia/Tokyo)

Status: **FROZEN ONLY WHEN THIS EXACT THREE-PATH SUCCESSOR IS COMMITTED,
PUSHED, AND HOSTED-CI GREEN.**

This document is a bounded control-plane successor to the immutable recovery
plan commit

```text
2712060ff5b0223aa581dd611363dba517520048
```

It changes no M4--M6 semantics, allowlist, resource budget, endpoint, external
theory interpretation, or scientific disposition.  It supersedes only the
activation clause requiring `2712060` itself to be green: M4 authority begins
only after this exact child is green.

## 1. Hosted-CI adjudication

Hosted GitHub Actions run `29178759991`, job `86612624356`, at exact head
`2712060ff5b0223aa581dd611363dba517520048` reported:

```text
2396 passed
7 skipped
161 deselected
1 failed
```

The sole failure was
`test_first_implementation_commit_freezes_exact_plan_anchor_topology` in
`tests/test_uprime_u05_identity.py`.  Full-history checkout correctly exposed
the historical CPU-survivor branch of that guard.  The guard first found and
validated the unique old closeout, including its exact parent, changed paths,
document blob, ancestry, and frozen implementation interval.  It then
incorrectly continued into the old phase's next-milestone dirty-worktree check.

The preceding workflow step `python -m pip install -e ".[test]"` had created
six ordinary untracked editable-install files under `lean_rgc.egg-info/`:

```text
PKG-INFO
SOURCES.txt
dependency_links.txt
entry_points.txt
requires.txt
top_level.txt
```

The closed-phase guard rejected those files as if the old CPU bundle were still
awaiting another semantic milestone.  This is a post-closeout guard-lifecycle
defect exposed by the newly correct full-history checkout.  It is not an
NS-transfer, M3, M4/M5/M6 semantic, resource, scientific-result, or endpoint
failure.  No recovery semantic lane had begun.

The earlier U05 result adjudication is also unchanged: its result commit has a
red control-plane badge, while scientific candidate CI `29166073728` was green.
Neither red badge is evidence of a failed scientific endpoint.

## 2. Exact repair

The successor changes exactly:

```text
docs/experiments/uprime_odlrq_lane_isolated_recovery_control_plane_repair_2026-07-12.md
tests/test_uprime_u05_identity.py
tests/test_odlrq_lane_isolated_recovery_identity.py
```

The old guard retains every result, plan, amendment, closeout, commit, blob,
ancestry, and implementation-interval check.  Its only logic change is:

```text
if the registered CPU closeout has not been found:
    retain the original dirty-worktree precommit checks
else:
    do not apply a next-milestone dirty allowlist to later-phase build products
```

There is no global `egg-info` exclusion.  Before the exact old closeout, the
dirty-worktree policy is unchanged and remains fail-closed.

The recovery identity guard:

1. proves that `2712060` is the original exact four-path child and retains the
   original old-guard blob;
2. requires this control successor to be its sole-parent exact three-path
   child;
3. freezes this document and the repaired old-guard blob;
4. derives the repaired recovery-guard blob from this successor and freezes it
   for the accepted recovery interval; and
5. starts the M4--M6 semantic commit/order/quota accounting after this successor,
   so the repair consumes no semantic lane commit.

The immutable recovery-plan document blob remains
`955872dacb1ebfe6328a178797b68479ebc55069`.  Its workflow and manifest blobs,
M3 blobs, old closeout, U05 result package, lane runners, budgets, and all
scientific source files are unchanged.

## 3. Success gate and stopping rule

Before M4 begins, all of the following are required:

- local old/new identity and tier-manifest tests are green;
- the exact three-path diff and single-parent topology are green;
- the original four-path plan and scientific predecessor blobs match;
- hosted CI on this successor is green.

If the successor is not green, M4 remains unlicensed.  There is no retry of a
protected execution, no result reinterpretation, and no lane qualification in
this repair.

## 4. Mandatory nonclaims

This successor qualifies no M4, M5, or M6 lane; changes no NS-derived design
claim, cap, threshold, fixture, or evidence tier; reopens no U05/protected input;
and grants no canonical-history depth-four, U'1.5 learner, U'2--U'4,
Amendment-A execution, SSH/GPU, LLM, deployment, or evaluation authority.

Three independent reviewers approved this exact repair shape after inspecting
the hosted log and both guards.  Their approval is limited to the three-path
control-plane successor described here.
