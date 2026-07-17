# U-prime / ODLRQ E2 Q1 qualification amendment

Date: 2026-07-17 (Asia/Tokyo)

Status: **DRAFT UNTIL THE STAGE-1 CORRECTION IS THE SECOND PARENT OF THIS
FIRST-PARENT DOCUMENT-ONLY SIDECAR CARRIER AND THE CARRIER IS PUSHED ONCE.**
After that freeze, this document licenses one Q1 Windows-CPU qualification.  It
does not reopen accepted E1, Q0, the four E2 endpoint meanings, any protected
endpoint, or any upper-stack claim.

## 1. Authority and disposition of Q0

This authority implements `FABLE-20260717-0005`, which carries the user's
explicit delegation: implementation, runner, CI, and governance mistakes are
ordinary repair conditions.  User escalation is reserved for a theoretical
refutation of the program or exhaustion of rational repairs.

Accepted E1 remains the remote ref `codex/uprime-odlrq-plan`; its current value
must be machine-equal to the immutable R6 build ref at every Q1 preflight.  The
human-readable historical value is `6fb35aa229fc60e2220cbb68c1e7fff2ce64f199`,
but no gate compares against a hand-transcribed hash.

Q0 authority `8a1688e72104873139238af6fe34d90c99d91ab1` and closeout
`0c5caa9459045d8a3dc87cca5b6e8689d82f8d4a` remain closed audit history.  Its
post-stop fixture-admission observation is not scientific evidence.  Q1
reproduced the defect in a development lane and does not reuse a Q0 attempt.

This carrier has exactly two ordered parents: the frozen repair-authority commit
is parent 1 and the exact Stage-1 correction is parent 2.  Relative to parent 1,
its tree adds only this document at mode `100644`; it is never merged into the
candidate or accepted line.  The old E2 runner remains present byte-identically
in the sidecar tree/history and is forbidden to invoke, edit, copy, or use as
evidence.  The separate correction tree does not contain it.

The correction is intentionally remotely reachable through the authority's
second-parent edge before the scientific look, but no remote branch or tag
points directly to it.  Authority CI checks out only the sidecar merge tree and
must have zero E2 module/node hits.

The freeze identity is exact:

```text
ref       codex/uprime-e2-qualification-authority-q1
subject   uprime: freeze E2 Q1 qualification
parent 1  fresh remote codex/uprime-e2-repair-authority-q1
parent 2  exact Stage-1 correction; no direct remote ref or tag
tree      parent-1 tree plus this one mode-100644 document only
push      one non-force creation; never amended, repointed, deleted, or forced
```

Its sole natural CI is an expected control red, not a scientific failure: exact
summary `1 failed, 2599 passed, 8 skipped, 161 deselected`, sole failure
`test_u24_b0_anchor_contiguous_budget_and_terminal_topology`, and zero E2
module/node hits.  The inline preflight machine-checks that shape, the exact
`CI` workflow (`.github/workflows/ci.yml`, workflow ID `292918982`), the authority
branch/SHA, and `run_attempt=1` before arming.  It applies the same check to the
repair authority's already-completed natural CI.  Its historical run is
`29544863956`, job `87774799508`; those numbers are audit notes, not gate operands.

Before push, the exact local sidecar merge tree was checked with the sole
topology node.  It produced that same single historical-carrier assertion and
no other failure (`1 failed in 32.36s`); `git ls-tree` also confirmed the E2
selection module is absent from the sidecar checkout tree.

## 2. Stage 1: non-scientific engineering repair

Stage 1 identified one complete fixture defect: E2 used eleven synthetic
state/action identifiers outside E1's frozen `unit_cpu_survivor_` admission
namespace.  The permitted correction is the bijective alpha-renaming

```text
u24_e2_source_* -> unit_cpu_survivor_u24_e2_source_*
u24_e2_target_* -> unit_cpu_survivor_u24_e2_target_*
```

in production fixture reconstruction and its independent test.  The same
correction may remove redundant repeated derivations, provided exact fresh-wire
validation, strict parsing, mutation detection, and all public schemas remain
unchanged.

The correction must preserve all four frozen endpoint meanings:

1. source/target coordinate identification and parent-envelope restriction;
2. retained/complement P/Q split and weighted norm orientation;
3. complete literal three-candidate universe before thresholding; and
4. binding certified-support selection with the same ranking and fallback.

It must also preserve endpoint ID, universe ID, coordinate order, all five
parent matrices, exact rational coefficients, laws, candidate IDs, threshold,
P1/P2 cocycles, return-memory horizon, dispositions, schemas, and the existing
ten pytest node names.  Old A0 constants remain provenance for those unchanged
endpoint meanings; this Q1 authority supersedes A0 only for fixture namespace
admissibility and the semantics-preserving serializer repair.

The Stage-1 correction identity is never parsed from a document literal.  It is
resolved only as the pushed qualification carrier's `^2^{commit}`.

The correction must be a single-parent direct child of the semantic B commit mechanically
resolved as parent 2 of remote `codex/uprime-e2-endpoint-runner-control`.  Its
diff against B is exactly these three paths:

```text
lean_rgc/odlrq/certificates.py
lean_rgc/odlrq/selection.py
tests/test_odlrq_selection.py
```

Its final diff against accepted E1 is exactly the original four-path E2
footprint, adding the unchanged manifest path:

```text
tests/tier_manifest.json
```

The manifest blob at B and the correction must be machine-equal.  No no-op
manifest edit is allowed.

Before freeze, the corrected tree passed the existing ten E2 nodes on Windows
CPU in `316.09s`, including strict JSON round-trip, unknown-field rejection,
noncanonical-rational rejection, returned-dict isolation, subclass rejection,
stale-authority rejection, preallocation bombs, and instance-serializer
override rejection.  These are development diagnostics and consume no Q1
scientific look.  The exact pre-freeze Windows-CPU evidence is:

```text
C:\Python313\python.exe -m pytest -q -p no:cacheprovider tests/test_odlrq_selection.py --durations=10
10 passed in 316.09s

C:\Python313\python.exe -m pytest -q -p no:cacheprovider tests/test_odlrq_behavioral_partition.py tests/test_odlrq_quotient_generator.py tests/test_odlrq_envelope.py
98 passed in 154.15s

C:\Python313\python.exe -m pytest -q -p no:cacheprovider --durations=20
2614 passed, 4 skipped, 161 deselected in 1129.57s
```

The Windows/Linux difference in pass/skip partition is an inherited platform
split; both totals are 2618 selected tests and the Windows run has zero failure.
Candidate/accepted Linux CI remains frozen at `2610 passed, 8 skipped, 161
deselected`.  `git diff --check`, ten-node collect-only, eleven-ID bijection,
three-path correction/four-path final footprint, unchanged manifest blob, and
repair-authority three-way constant checks also passed before this freeze.

## 3. Machine-derived preflight

Every commit, tree, parent, ref-containment, and blob comparison resolves both
sides inside the same preflight process.  Human-readable hashes elsewhere in
this document are history, never gate operands.  Section 9 contains the complete
inline PowerShell block; there is no external script, omitted helper, caller-
supplied node, or placeholder.  Native Git nonzero status, malformed output, or
non-singleton required ref output fails closed before the scientific marker.

The block fresh-resolves remote heads with checked `git ls-remote --heads`,
fetches the same objects, checks ordered parent counts, first-parent sidecar
tree, second-parent candidate, path sets, modes, manifest equality, clean tree,
and the allowed single indirect remote containment.  It also performs the
repair-authority three-way constant comparison, strict JSON diagnostic
canonicalization and digest emission, exact collection-only check, interpreter
identity check, marker creation, and the sole inherited-console pytest launch.

## 4. Attempts, arming, and proportional wall

Q1 distinguishes two counters:

```text
control_attempt_ordinal  1..3
scientific_look_consumed 0 or 1
```

There are at most three control attempts total.  Attempt 1 is the first actual
invocation of the frozen block after its pushed authority CI is complete; merely
reading or syntax-checking the document is not an invocation.  The inline JSON
helper's exclusive creation of `control_records/u24_e2_q1/attempt-1-opened.json`
is the first durable counter record.  Success of the underlying
`os.open(...O_EXCL...)` consumes ordinal 1 even if write, flush, reread, or later
preflight fails.  An invoked block that fails before that exclusive open also
conservatively consumes ordinal 1 and requires a result record with
`control_record_sha256=ABSENT`; it may not be silently relaunched.  Any such
failure before the scientific marker consumes no scientific look, but it
requires a dated `attempt-1-result.md` in the same directory before any retry.

Attempts 2 and 3, if rationally required, each require a separate frozen
two-parent control-correction carrier on a new ref.  Parent 1 is the preceding
Q1 authority carrier, parent 2 is the identical correction commit, and its tree
is the parent-1 tree plus one dated mode-`100644` control-correction document.
The original authority ref is never moved.  Each fresh block differs only in the
diagnosed control repair, ordinal, exact authority/containment set, and record
filename.  Across both corrections the budget is at most two commits and two new
paths; no candidate change, new process primitive, custom runner, or silent retry
is allowed.  After ordinal 3, the disposition is reported to Fable with
remaining rational remedies.

Every pre-marker failure after the control-record exclusive open requires a
create-new dated result record before a retry.  That record binds the opened
record's canonical SHA, authority commit, candidate commit if it was resolved,
failure stage and message, unchanged scientific identities, and
`scientific_look_consumed=false`.  The opened record is immutable and is never
overwritten with a retrospective diagnosis.

The scientific look is consumed at exclusive durable creation of this marker,
outside every Git worktree:

```text
C:\Users\yusei\Desktop\codex_claude_bridge\attempt_markers\
u24_e2_q1__<machine-resolved-Q1-authority-commit>.json
```

The marker is canonical UTF-8 JSON plus LF with exactly: schema version,
machine-resolved authority commit/document blob, accepted E1 commit, semantic
base commit, candidate commit/tree, control-attempt ordinal, ten-node-list SHA,
exact command SHA, preflight-diagnostic SHA, control-record SHA, creation time,
and `run_state=RUN_OPENED`.  It is opened with
Python `os.open(O_WRONLY|O_CREAT|O_EXCL, 0o600)`, written once, flushed and
`os.fsync`ed, closed, reopened, parsed with duplicate-key rejection, and required
to reproduce the exact canonical bytes.  A pre-existing marker blocks arming.
The scientific look is consumed at successful exclusive `os.open(...O_EXCL...)`,
not at child launch; any later write/flush/reread ambiguity is therefore consumed
and terminal.  The marker also binds the preflight diagnostic SHA and control-
record SHA.

The only scientific child is the standard installed interpreter with inherited
console, no output redirection, parser, receipt, P/Invoke, Job Object, suspended
process, or custom runner:

```text
C:\Python313\python.exe -m pytest -q -p no:cacheprovider <the frozen ten nodes>
```

The frozen named set of Python, pytest, coverage, import, and warning control
variables is removed using the exact ordered list bound into the command digest.
The block then sets only `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`,
`PYTHONDONTWRITEBYTECODE=1`, and `PYTHONHASHSEED=0`.  The required user-site
installation remains enabled, so the preflight checks exact pytest/NumPy versions
and import paths and confirms that `lean_rgc` resolves inside the candidate root.
Interpreter SHA, Python 3.13.7, pytest 9.0.3, and NumPy 2.3.3 are checked before
the first JSON helper invocation and again by the late pre-marker barrier.
Mutable Windows host state outside those checks remains an explicit host-trust
boundary; Q1 does not claim a hermetic or byte-attested runtime image.

The Stage-1 cold ten-node time is `316.09s`.  The Q1 wall is therefore
`1,200,000ms` from successful `Start-Process`, greater than 3x the measured
lane time.  The inline control uses only normal `Start-Process`, retained
process handle, `WaitForExit(1200000)`, and direct `Kill()` on timeout.  This is
not the historical E2 runner and makes no claim about Job Objects or P/Invoke.
After a timeout, kill and cleanup receive only a bounded additional 10-second
wait.  Kill failure or failure to exit in that cleanup window returns terminal
control status 125 after consumption; it never extends the scientific wall with
an unbounded wait.

After the marker exists, pass, test failure, timeout, launch failure, crash,
capture loss, or operator interruption is terminal for Q1.  There is no second
scientific launch and no Actions rerun.

## 5. Exact nodes and success rule

The ten full node IDs, in order, are:

```text
tests/test_odlrq_selection.py::test_e2_square_parent_coordinate_identification_rederives_complete_typed_basis
tests/test_odlrq_selection.py::test_e2_restriction_replays_full_parent_terminal_zeros_and_restricted_weights
tests/test_odlrq_selection.py::test_e2_lifting_uniform_safety_is_law_independent_and_cancellation_free
tests/test_odlrq_selection.py::test_e2_p1_p2_cocycles_match_products_weighted_norms_and_limited_derivations
tests/test_odlrq_selection.py::test_e2_return_memory_split_stationary_semantics_and_finite_sum_are_exact
tests/test_odlrq_selection.py::test_e2_orientation_basis_weight_split_and_transport_mutations_fail_closed
tests/test_odlrq_selection.py::test_e2_caps_horizon_work_and_preallocation_bombs_fail_before_authority
tests/test_odlrq_selection.py::test_e2_fixed_candidate_universe_prevents_prefilter_omission_and_accepts_boundary
tests/test_odlrq_selection.py::test_e2_gate_is_coverage_complete_nonempty_reachable_and_top_ranking_binding
tests/test_odlrq_selection.py::test_e2_strict_roundtrip_invalidation_tier_firewall_and_nominal_fallback
```

Local Q1 success is exit zero and exact `10 passed`, with no failure, error,
skip, xfail, deselection, extra collection, or warning-based substitution.
Exit zero is necessary but not sufficient: the operator must observe the exact
single inherited-console `10 passed` summary.  Missing or ambiguous console
output is capture loss and terminal; it cannot license candidate publication.

Only local success licenses one non-force creation of
`codex/uprime-e2-qualification-candidate-q1` at the exact correction commit.
Its one natural push CI must be green with exact summary
`2610 passed, 8 skipped, 161 deselected`.  Only that licenses a fast-forward of
`codex/uprime-odlrq-plan` from machine-resolved E1 through B to the same
correction commit.  The accepted push must produce a distinct natural green CI
at the identical SHA and counts.  No workflow dispatch or Actions rerun is
allowed.  Any **candidate or accepted** CI failure is engineering evidence
terminating Q1, not a mathematical refutation.  The authority-side CI is the
separately specified expected topology-only red and is a pre-marker control
gate rather than a candidate/accepted outcome.

## 6. Closeout and stopping rule

One document-only Q1 closeout may be committed on a separate sidecar ref whose
parent is the final Q1 authority head.  It records all actual control attempts,
marker identity, local outcome, and candidate/accepted run IDs that exist.  It
is never merged into accepted science.

User escalation occurs only if the Stage-1 diagnosis yields a mathematical
contradiction in envelope/quotient semantics, or if no rational repair remains.
Three pre-arm control failures require a reasoned report to Fable; they do not
by themselves establish either escalation condition.

## 7. Historical red-CI clarification

**Recorded 2026-07-17; events of 2026-07-16:** immutable U05 result commit
`cc91a4181a9f87ec10f11727ed787eb7149f955a` has red Actions run `29166670576`,
job `86580832840`, because the guard omitted shallow-history handling.  Audit
authority `628d3cc64af2531da3a527bad335d9e5158294a7` adjudicated that cause.  The
exact scientific candidate `3bb3408afc50a08307cff2c9b1906a299739dfb5` had
green candidate run `29166073728`, job `86579287017`.  The red result badge is a
control/guard design defect and must not be read as a scientific U05 failure.

## 8. Forbidden and deferred work

Accepted E1, old authorities, Q0 closeout, consumed artifacts, and protected
endpoints remain immutable.  This authority licenses no K1-K4 read, reserved
data, GPU, SSH, LLM, MaxEnt/ME0, similarity/S0, integration/I0, locality learner,
or upper-stack claim.  Those phases resume only after E2 acceptance under fresh
authority.  LLM remains outside the loop until the exact theoretical generator
and finite downstream pipeline have been independently accepted.

## 9. Frozen Q1 attempt-1 inline control block

This is the complete attempt-1 block.  It is invoked once from an ordinary
Windows PowerShell 5.1 console.  It reads no caller-supplied parameter and uses
no external runner or serializer file.

```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$CandidateRoot = "C:\Users\yusei\Desktop\lean_rgc_automation_stack_v47_goal_state_dynamics_e2_engineering_repair"
$Python = "C:\Python313\python.exe"
$ExpectedPythonSha256 = "D932E5E2F324D57F392E8FD063DCF6D0185BE8A664C57C6D24E7762ED02C28CA"
$GitHubRepository = "abhorrence-of-Gods/lean-rgc-automation-stack"
$ExpectedOriginUrl = "https://github.com/abhorrence-of-Gods/lean-rgc-automation-stack.git"
$ExpectedWorkflowId = 292918982
$ExpectedWorkflowPath = ".github/workflows/ci.yml"
$RepairRefName = "codex/uprime-e2-repair-authority-q1"
$AuthorityRefName = "codex/uprime-e2-qualification-authority-q1"
$AcceptedRefName = "codex/uprime-odlrq-plan"
$AcceptedAnchorRefName = "codex/uprime-u2-u4-development-r6-build"
$CarrierRefName = "codex/uprime-e2-endpoint-runner-control"
$CandidateRefName = "codex/uprime-e2-qualification-candidate-q1"
$CloseoutRefName = "codex/uprime-e2-qualification-closeout-q1"
$RepairDocumentPath = "docs/experiments/uprime_odlrq_e2_q1_fixture_repair_authority_2026-07-17.md"
$AuthorityDocumentPath = "docs/experiments/uprime_odlrq_e2_qualification_q1_amendment_2026-07-17.md"
$RepairSubject = "uprime: authorize E2 Q1 fixture repair"
$AuthoritySubject = "uprime: freeze E2 Q1 qualification"
$CandidateSubject = "uprime: repair E2 fixture namespace and serialization"
$ControlAttemptOrdinal = 1
$WallMilliseconds = 1200000
$RemovedEnvironmentNames = @(
  "PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTHONPATH", "PYTHONHOME",
  "PYTHONNOUSERSITE", "PYTHONUSERBASE", "PYTHONWARNINGS", "PYTHONOPTIMIZE",
  "PYTHONINSPECT", "PYTHONBREAKPOINT", "PYTHONSAFEPATH", "PYTHONUTF8",
  "PYTHONIOENCODING", "PYTHONSTARTUP", "PYTHONCASEOK", "PYTHONPYCACHEPREFIX",
  "PYTHONMALLOC", "PYTHONTRACEMALLOC", "PYTHONPROFILEIMPORTTIME",
  "PYTHONDEVMODE", "PYTHONFAULTHANDLER", "PYTHONWARNDEFAULTENCODING",
  "PYTHONINTMAXSTRDIGITS", "PYTHONNODEBUGRANGES", "COVERAGE_PROCESS_START",
  "COVERAGE_FILE", "COVERAGE_RCFILE", "COV_CORE_SOURCE", "COV_CORE_CONFIG",
  "COV_CORE_DATAFILE"
)

$Nodes = @(
  "tests/test_odlrq_selection.py::test_e2_square_parent_coordinate_identification_rederives_complete_typed_basis",
  "tests/test_odlrq_selection.py::test_e2_restriction_replays_full_parent_terminal_zeros_and_restricted_weights",
  "tests/test_odlrq_selection.py::test_e2_lifting_uniform_safety_is_law_independent_and_cancellation_free",
  "tests/test_odlrq_selection.py::test_e2_p1_p2_cocycles_match_products_weighted_norms_and_limited_derivations",
  "tests/test_odlrq_selection.py::test_e2_return_memory_split_stationary_semantics_and_finite_sum_are_exact",
  "tests/test_odlrq_selection.py::test_e2_orientation_basis_weight_split_and_transport_mutations_fail_closed",
  "tests/test_odlrq_selection.py::test_e2_caps_horizon_work_and_preallocation_bombs_fail_before_authority",
  "tests/test_odlrq_selection.py::test_e2_fixed_candidate_universe_prevents_prefilter_omission_and_accepts_boundary",
  "tests/test_odlrq_selection.py::test_e2_gate_is_coverage_complete_nonempty_reachable_and_top_ranking_binding",
  "tests/test_odlrq_selection.py::test_e2_strict_roundtrip_invalidation_tier_firewall_and_nominal_fallback"
)

function Invoke-GitLines {
  param(
    [Parameter(Mandatory = $true)][string[]] $Arguments,
    [int] $ExpectedCount = -1
  )
  $lines = @(& git @Arguments 2>&1 | ForEach-Object { [string]$_ })
  $code = $LASTEXITCODE
  if ($code -ne 0) {
    throw "git failed ($code): git $($Arguments -join ' ') :: $($lines -join ' | ')"
  }
  if ($ExpectedCount -ge 0 -and $lines.Count -ne $ExpectedCount) {
    throw "git output count mismatch for git $($Arguments -join ' '): $($lines.Count)"
  }
  return $lines
}

function Resolve-OneGitObject {
  param([Parameter(Mandatory = $true)][string[]] $Arguments)
  $lines = @(Invoke-GitLines -Arguments $Arguments -ExpectedCount 1)
  $value = [string]$lines[0]
  if ($value -notmatch '^[0-9a-f]{40}$') {
    throw "git object is not one lowercase 40-hex value: $value"
  }
  return $value
}

function Get-FreshRemoteHead {
  param([Parameter(Mandatory = $true)][string] $BranchName)
  $fullRef = "refs/heads/$BranchName"
  $lines = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "ls-remote", "--heads", "origin", $fullRef) -ExpectedCount 1)
  $columns = $lines[0] -split "`t"
  if ($columns.Count -ne 2 -or $columns[1] -cne $fullRef -or $columns[0] -notmatch '^[0-9a-f]{40}$') {
    throw "malformed remote-head row for $BranchName"
  }
  return [string]$columns[0]
}

function Assert-FreshRemoteHeadAbsent {
  param([Parameter(Mandatory = $true)][string] $BranchName)
  $fullRef = "refs/heads/$BranchName"
  $null = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "ls-remote", "--heads", "origin", $fullRef) -ExpectedCount 0)
}

function Assert-ExactList {
  param(
    [Parameter(Mandatory = $true)][object[]] $Observed,
    [Parameter(Mandatory = $true)][object[]] $Expected,
    [Parameter(Mandatory = $true)][string] $Label
  )
  $observedText = [string]::Join("`n", @($Observed | ForEach-Object { [string]$_ }))
  $expectedText = [string]::Join("`n", @($Expected | ForEach-Object { [string]$_ }))
  if ($Observed.Count -ne $Expected.Count -or $observedText -cne $expectedText) {
    throw "$Label mismatch :: observed=[$observedText] expected=[$expectedText]"
  }
}

function Assert-Mode100644 {
  param(
    [Parameter(Mandatory = $true)][string] $Commit,
    [Parameter(Mandatory = $true)][string] $Path
  )
  $rows = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "ls-tree", $Commit, "--", $Path) -ExpectedCount 1)
  $row = [string]$rows[0]
  $parts = $row -split '\s+', 4
  if ($parts.Count -ne 4 -or $parts[0] -cne "100644" -or $parts[1] -cne "blob" -or $parts[2] -notmatch '^[0-9a-f]{40}$' -or $parts[3] -cne $Path) {
    throw "mode/blob/path mismatch for $Path"
  }
}

function Assert-NoReparseAncestry {
  param([Parameter(Mandatory = $true)][string] $Path)
  $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
  while ($null -ne $item) {
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
      throw "reparse point is forbidden in evidence path ancestry: $($item.FullName)"
    }
    $item = $item.Parent
  }
}

function Get-ExactPackageIdentity {
  $PackageIdentityCode = @'
import pathlib
import numpy
import pytest
import lean_rgc
print(pytest.__version__ + "|" + numpy.__version__)
print(pathlib.Path(pytest.__file__).resolve())
print(pathlib.Path(numpy.__file__).resolve())
print(pathlib.Path(lean_rgc.__file__).resolve())
'@
  $identity = @($PackageIdentityCode | & $Python - 2>&1 | ForEach-Object { [string]$_ })
  $identityExitCode = $LASTEXITCODE
  if ($identityExitCode -ne 0) {
    throw "package identity query failed ($identityExitCode): $($identity -join ' | ')"
  }
  $expectedIdentity = @(
    "9.0.3|2.3.3",
    "C:\Users\yusei\AppData\Roaming\Python\Python313\site-packages\pytest\__init__.py",
    "C:\Users\yusei\AppData\Roaming\Python\Python313\site-packages\numpy\__init__.py",
    (Join-Path $CandidateRoot "lean_rgc\__init__.py")
  )
  Assert-ExactList -Observed $identity -Expected $expectedIdentity -Label "pytest/NumPy/candidate import identity"
  return [string]::Join("|", $identity)
}

function Get-ExactKnownTopologyRed {
  param(
    [Parameter(Mandatory = $true)][string] $Commit,
    [Parameter(Mandatory = $true)][string] $BranchName,
    [Parameter(Mandatory = $true)][string] $Label
  )
  $listJson = @(& gh run list --repo $GitHubRepository --commit $Commit --event push --workflow ci.yml --limit 10 --json databaseId,headBranch,headSha,event,status,conclusion,workflowName 2>&1 | ForEach-Object { [string]$_ })
  if ($LASTEXITCODE -ne 0) {
    throw "$Label CI query failed: $($listJson -join ' | ')"
  }
  $runs = @(([string]::Join("`n", $listJson) | ConvertFrom-Json) | Where-Object {
    $_.headSha -ceq $Commit -and $_.headBranch -ceq $BranchName
  })
  if ($runs.Count -ne 1 -or $runs[0].event -cne "push" -or
      $runs[0].status -cne "completed" -or $runs[0].conclusion -cne "failure" -or
      $runs[0].workflowName -cne "CI") {
    throw "$Label CI identity/status mismatch"
  }
  $runId = [string]$runs[0].databaseId
  if ($runId -notmatch '^[1-9][0-9]*$') {
    throw "$Label CI run ID is malformed"
  }
  $apiJson = @(& gh api ("repos/" + $GitHubRepository + "/actions/runs/" + $runId) 2>&1 | ForEach-Object { [string]$_ })
  if ($LASTEXITCODE -ne 0) {
    throw "$Label CI API query failed: $($apiJson -join ' | ')"
  }
  $apiRun = [string]::Join("`n", $apiJson) | ConvertFrom-Json
  if ([string]$apiRun.id -cne $runId -or [int64]$apiRun.run_attempt -ne 1 -or
      [int64]$apiRun.workflow_id -ne $ExpectedWorkflowId -or
      $apiRun.name -cne "CI" -or $apiRun.path -cne $ExpectedWorkflowPath -or
      $apiRun.head_branch -cne $BranchName -or $apiRun.head_sha -cne $Commit -or
      $apiRun.event -cne "push" -or $apiRun.status -cne "completed" -or
      $apiRun.conclusion -cne "failure") {
    throw "$Label CI API identity/attempt/workflow mismatch"
  }
  $logLines = @(& gh run view $runId --repo $GitHubRepository --attempt 1 --log 2>&1 | ForEach-Object { [string]$_ })
  if ($LASTEXITCODE -ne 0) {
    throw "$Label CI log query failed: $($logLines -join ' | ')"
  }
  $logText = [string]::Join("`n", $logLines)
  $summary = "1 failed, 2599 passed, 8 skipped, 161 deselected"
  $failureNode = "test_u24_b0_anchor_contiguous_budget_and_terminal_topology"
  $failureLine = "FAILED tests/test_uprime_u2_u4_development.py::" + $failureNode
  if ([regex]::Matches($logText, [regex]::Escape($summary)).Count -ne 1 -or
      [regex]::Matches($logText, [regex]::Escape($failureNode)).Count -ne 2 -or
      [regex]::Matches($logText, [regex]::Escape($failureLine)).Count -ne 1 -or
      $logText -match 'test_odlrq_selection\.py' -or $logText -match '::test_e2_') {
    throw "$Label CI is not the exact known topology-only red with zero E2 hits"
  }
  return $runId
}

$JsonHelperCode = @'
import base64
import hashlib
import json
import os
import sys

def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result

mode, path, payload_b64 = sys.argv[1:4]
payload_bytes = base64.b64decode(payload_b64, validate=True)
payload = json.loads(payload_bytes.decode("utf-8"), object_pairs_hook=reject_duplicates)
canonical = (json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
roundtrip = json.loads(canonical.decode("utf-8"), object_pairs_hook=reject_duplicates)
if roundtrip != payload:
    raise RuntimeError("strict JSON round-trip mismatch")
if mode == "create":
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb", closefd=True) as handle:
        handle.write(canonical)
        handle.flush()
        os.fsync(handle.fileno())
    with open(path, "rb") as handle:
        observed = handle.read()
    reparsed = json.loads(observed.decode("utf-8"), object_pairs_hook=reject_duplicates)
    recanonical = (json.dumps(reparsed, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    if observed != canonical or recanonical != canonical:
        raise RuntimeError("durable canonical JSON reread mismatch")
elif mode != "check":
    raise RuntimeError("unknown JSON helper mode")
print(hashlib.sha256(canonical).hexdigest().upper())
'@

function Invoke-StrictJson {
  param(
    [Parameter(Mandatory = $true)][ValidateSet("check", "create")][string] $Mode,
    [Parameter(Mandatory = $true)][string] $Path,
    [Parameter(Mandatory = $true)] $Payload
  )
  $json = ConvertTo-Json -InputObject $Payload -Depth 12 -Compress
  $payloadBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
  $lines = @($JsonHelperCode | & $Python - $Mode $Path $payloadBase64 2>&1 | ForEach-Object { [string]$_ })
  $code = $LASTEXITCODE
  if ($code -ne 0 -or $lines.Count -ne 1 -or $lines[0] -notmatch '^[0-9A-F]{64}$') {
    throw "strict JSON helper failed ($code): $($lines -join ' | ')"
  }
  return [string]$lines[0]
}

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
  throw "frozen Python executable is absent"
}
if (-not (Test-Path -LiteralPath $CandidateRoot -PathType Container)) {
  throw "frozen CandidateRoot is absent or not a directory"
}
$resolvedCandidateRoot = (Resolve-Path -LiteralPath $CandidateRoot -ErrorAction Stop).Path
$rootLines = @(Invoke-GitLines -Arguments @("-C", $resolvedCandidateRoot, "rev-parse", "--show-toplevel") -ExpectedCount 1)
$gitCandidateRoot = [IO.Path]::GetFullPath(([string]$rootLines[0]).Replace("/", "\"))
$resolvedCandidateRoot = [IO.Path]::GetFullPath($resolvedCandidateRoot)
if (-not [string]::Equals($gitCandidateRoot, $resolvedCandidateRoot, [StringComparison]::OrdinalIgnoreCase)) {
  throw "CandidateRoot is not the exact Git worktree root"
}
$CandidateRoot = $resolvedCandidateRoot
Set-Location -LiteralPath $CandidateRoot
$originUrl = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "remote", "get-url", "origin") -ExpectedCount 1)
Assert-ExactList -Observed $originUrl -Expected @($ExpectedOriginUrl) -Label "origin URL"

foreach ($name in $RemovedEnvironmentNames) {
  Remove-Item -LiteralPath ("Env:" + $name) -ErrorAction SilentlyContinue
}
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONHASHSEED = "0"

$pythonSha = (Get-FileHash -LiteralPath $Python -Algorithm SHA256).Hash
if ($pythonSha -cne $ExpectedPythonSha256) {
  throw "Python executable SHA mismatch"
}
$pythonVersion = @(& $Python --version 2>&1 | ForEach-Object { [string]$_ })
$pythonVersionCode = $LASTEXITCODE
if ($pythonVersionCode -ne 0) {
  throw "Python version query failed ($pythonVersionCode): $($pythonVersion -join ' | ')"
}
Assert-ExactList -Observed $pythonVersion -Expected @("Python 3.13.7") -Label "Python version"
$packageIdentity = Get-ExactPackageIdentity

$null = Invoke-StrictJson -Mode "check" -Path "-" -Payload ([ordered]@{
  schema_version = "u24-e2-q1-json-self-test-v1"
  exact = $true
})

$authorityCommit = Get-FreshRemoteHead -BranchName $AuthorityRefName
$BridgeRoot = "C:\Users\yusei\Desktop\codex_claude_bridge"
if (-not (Test-Path -LiteralPath $BridgeRoot -PathType Container)) {
  throw "bridge root is absent or not a directory"
}
Assert-NoReparseAncestry -Path $BridgeRoot
$bridgeGitProbe = @(& git -C $BridgeRoot rev-parse --show-toplevel 2>&1 | ForEach-Object { [string]$_ })
if ($LASTEXITCODE -eq 0) {
  throw "bridge root is inside a Git worktree: $($bridgeGitProbe -join ' | ')"
}
$ControlRoot = Join-Path $BridgeRoot "control_records\u24_e2_q1"
$null = [IO.Directory]::CreateDirectory($ControlRoot)
Assert-NoReparseAncestry -Path $ControlRoot
$existingControlRecords = @(Get-ChildItem -LiteralPath $ControlRoot -Filter "attempt-*-opened.json" -File)
if ($existingControlRecords.Count -ne 0) {
  throw "attempt-1 block requires zero prior Q1 control-attempt records"
}
$controlRecordPath = Join-Path $ControlRoot "attempt-1-opened.json"
$controlRecordSha = Invoke-StrictJson -Mode "create" -Path $controlRecordPath -Payload ([ordered]@{
  schema_version = "u24-e2-q1-control-attempt-v1"
  control_attempt_ordinal = $ControlAttemptOrdinal
  authority_ref = $AuthorityRefName
  authority_commit = $authorityCommit
  opened_at_utc = [DateTime]::UtcNow.ToString("o")
  scientific_look_consumed = $false
  state = "CONTROL_OPENED"
})

$repairCommit = Get-FreshRemoteHead -BranchName $RepairRefName
$acceptedCommit = Get-FreshRemoteHead -BranchName $AcceptedRefName
$acceptedAnchorCommit = Get-FreshRemoteHead -BranchName $AcceptedAnchorRefName
$carrierCommit = Get-FreshRemoteHead -BranchName $CarrierRefName
Assert-FreshRemoteHeadAbsent -BranchName $CandidateRefName
Assert-FreshRemoteHeadAbsent -BranchName $CloseoutRefName
if ($acceptedCommit -cne $acceptedAnchorCommit) {
  throw "accepted E1 and immutable R6 anchor differ"
}

$fetchLines = @(& git -C $CandidateRoot fetch --prune --prune-tags --tags origin '+refs/heads/*:refs/remotes/origin/*' 2>&1 | ForEach-Object { [string]$_ })
if ($LASTEXITCODE -ne 0) {
  throw "fresh origin fetch failed: $($fetchLines -join ' | ')"
}
foreach ($binding in @(
  @($AuthorityRefName, $authorityCommit),
  @($RepairRefName, $repairCommit),
  @($AcceptedRefName, $acceptedCommit),
  @($AcceptedAnchorRefName, $acceptedAnchorCommit),
  @($CarrierRefName, $carrierCommit)
)) {
  $localValue = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ("refs/remotes/origin/" + $binding[0] + "^{commit}"))
  if ($localValue -cne $binding[1]) {
    throw "fetched remote-tracking object differs for $($binding[0])"
  }
}

$authorityParentLines = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "rev-list", "--parents", "-n", "1", $authorityCommit) -ExpectedCount 1)
$authorityParents = ([string]$authorityParentLines[0]) -split ' '
if ($authorityParents.Count -ne 3 -or $authorityParents[0] -cne $authorityCommit -or $authorityParents[1] -cne $repairCommit) {
  throw "Q1 authority ordered-parent topology mismatch"
}
$candidateCommit = [string]$authorityParents[2]
$candidateTree = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ($candidateCommit + "^{tree}"))
$authorityTree = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ($authorityCommit + "^{tree}"))
$repairTree = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ($repairCommit + "^{tree}"))
$authorityBlob = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ($authorityCommit + ":" + $AuthorityDocumentPath))
$repairBlob = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ($repairCommit + ":" + $RepairDocumentPath))
Assert-ExactList -Observed @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "log", "-1", "--format=%s", $authorityCommit) -ExpectedCount 1) -Expected @($AuthoritySubject) -Label "authority subject"
Assert-ExactList -Observed @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "log", "-1", "--format=%s", $repairCommit) -ExpectedCount 1) -Expected @($RepairSubject) -Label "repair-authority subject"
Assert-ExactList -Observed @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "log", "-1", "--format=%s", $candidateCommit) -ExpectedCount 1) -Expected @($CandidateSubject) -Label "candidate subject"

$repairParentLines = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "rev-list", "--parents", "-n", "1", $repairCommit) -ExpectedCount 1)
$repairParents = ([string]$repairParentLines[0]) -split ' '
if ($repairParents.Count -ne 2 -or $repairParents[0] -cne $repairCommit) {
  throw "repair-authority parent topology mismatch"
}
$repairBase = [string]$repairParents[1]
$repairAuthorityPaths = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "diff", "--name-only", $repairBase, $repairCommit))
Assert-ExactList -Observed $repairAuthorityPaths -Expected @($RepairDocumentPath) -Label "repair-authority path set"
$repairAuthorityStatus = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "diff", "--name-status", $repairBase, $repairCommit))
Assert-ExactList -Observed $repairAuthorityStatus -Expected @("A`t$RepairDocumentPath") -Label "repair-authority status"
Assert-Mode100644 -Commit $repairCommit -Path $RepairDocumentPath

$authorityFirstParentPaths = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "diff", "--name-only", $repairCommit, $authorityCommit))
Assert-ExactList -Observed $authorityFirstParentPaths -Expected @($AuthorityDocumentPath) -Label "authority first-parent path set"
$authorityFirstParentStatus = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "diff", "--name-status", $repairCommit, $authorityCommit))
Assert-ExactList -Observed $authorityFirstParentStatus -Expected @("A`t$AuthorityDocumentPath") -Label "authority first-parent status"
Assert-Mode100644 -Commit $authorityCommit -Path $AuthorityDocumentPath

$carrierParentLines = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "rev-list", "--parents", "-n", "1", $carrierCommit) -ExpectedCount 1)
$carrierParents = ([string]$carrierParentLines[0]) -split ' '
if ($carrierParents.Count -ne 3 -or $carrierParents[0] -cne $carrierCommit) {
  throw "historical carrier parent topology mismatch"
}
$semanticBase = [string]$carrierParents[2]
$semanticParentLines = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "rev-list", "--parents", "-n", "1", $semanticBase) -ExpectedCount 1)
$semanticParents = ([string]$semanticParentLines[0]) -split ' '
if ($semanticParents.Count -ne 2 -or $semanticParents[0] -cne $semanticBase -or $semanticParents[1] -cne $acceptedCommit) {
  throw "semantic B is not a single-parent direct child of accepted E1"
}
$candidateParentLines = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "rev-list", "--parents", "-n", "1", $candidateCommit) -ExpectedCount 1)
$candidateParents = ([string]$candidateParentLines[0]) -split ' '
if ($candidateParents.Count -ne 2 -or $candidateParents[0] -cne $candidateCommit -or $candidateParents[1] -cne $semanticBase) {
  throw "correction is not a single-parent direct child of semantic B"
}

$candidateHead = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", "HEAD^{commit}")
if ($candidateHead -cne $candidateCommit) {
  throw "candidate worktree HEAD differs from authority parent 2"
}
$candidateStatus = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "status", "--porcelain=v1", "--untracked-files=all"))
if ($candidateStatus.Count -ne 0) {
  throw "candidate worktree is dirty"
}

$correctionPaths = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "diff", "--name-only", $semanticBase, $candidateCommit))
Assert-ExactList -Observed $correctionPaths -Expected @(
  "lean_rgc/odlrq/certificates.py",
  "lean_rgc/odlrq/selection.py",
  "tests/test_odlrq_selection.py"
) -Label "correction path set"
$finalE2Paths = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "diff", "--name-only", $acceptedCommit, $candidateCommit))
Assert-ExactList -Observed $finalE2Paths -Expected @(
  "lean_rgc/odlrq/certificates.py",
  "lean_rgc/odlrq/selection.py",
  "tests/test_odlrq_selection.py",
  "tests/tier_manifest.json"
) -Label "final E2 path set"
foreach ($path in $finalE2Paths) {
  Assert-Mode100644 -Commit $candidateCommit -Path $path
}
$baseManifestBlob = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ($semanticBase + ":tests/tier_manifest.json"))
$candidateManifestBlob = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ($candidateCommit + ":tests/tier_manifest.json"))
if ($baseManifestBlob -cne $candidateManifestBlob) {
  throw "tier manifest blob changed in the correction"
}

$candidateRemoteContainment = @(Invoke-GitLines -Arguments @(
  "-C", $CandidateRoot, "for-each-ref", "--format=%(refname)", "--contains", $candidateCommit,
  "refs/remotes/origin", "refs/tags"
))
Assert-ExactList -Observed $candidateRemoteContainment -Expected @(
  "refs/remotes/origin/codex/uprime-e2-qualification-authority-q1"
) -Label "pre-look remote containment"

$AuthorityCheckCode = @'
import ast
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
names = (
    "E2_Q1_REPAIR_AUTHORITY_COMMIT_SHA",
    "E2_Q1_REPAIR_AUTHORITY_TREE_SHA",
    "E2_Q1_REPAIR_AUTHORITY_DOCUMENT_PATH",
    "E2_Q1_REPAIR_AUTHORITY_DOCUMENT_BLOB_SHA",
)
expected = dict(zip(names, sys.argv[2:6]))
for relative in ("lean_rgc/odlrq/certificates.py", "tests/test_odlrq_selection.py"):
    parsed = ast.parse((root / relative).read_text(encoding="utf-8"))
    observed = {}
    for node in parsed.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in names:
            if node.targets[0].id in observed:
                raise RuntimeError(relative + " duplicate repair-authority constant: " + node.targets[0].id)
            observed[node.targets[0].id] = ast.literal_eval(node.value)
    if observed != expected:
        raise RuntimeError(relative + " repair-authority constants mismatch")
print("Q1_REPAIR_AUTHORITY_CONSTANTS_MACHINE_MATCH")
'@
$authorityCheck = @($AuthorityCheckCode | & $Python - $CandidateRoot $repairCommit $repairTree $RepairDocumentPath $repairBlob 2>&1 | ForEach-Object { [string]$_ })
if ($LASTEXITCODE -ne 0 -or $authorityCheck.Count -ne 1 -or $authorityCheck[0] -cne "Q1_REPAIR_AUTHORITY_CONSTANTS_MACHINE_MATCH") {
  throw "repair-authority constant check failed: $($authorityCheck -join ' | ')"
}

$repairAuthorityRunId = Get-ExactKnownTopologyRed -Commit $repairCommit -BranchName $RepairRefName -Label "repair authority"
$authorityRunId = Get-ExactKnownTopologyRed -Commit $authorityCommit -BranchName $AuthorityRefName -Label "qualification authority"

$collectArguments = @("-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider") + $Nodes
$collectionLines = @(& $Python @collectArguments 2>&1 | ForEach-Object { [string]$_ })
if ($LASTEXITCODE -ne 0) {
  throw "exact collection-only preflight failed: $($collectionLines -join ' | ')"
}
$collectionNonblank = @($collectionLines | Where-Object { $_.Trim().Length -ne 0 })
if ($collectionNonblank.Count -ne 11 -or $collectionNonblank[10] -notmatch '^10 tests collected in [0-9]+(?:\.[0-9]+)?s$') {
  throw "collection-only output contains an unexpected line or summary: $($collectionLines -join ' | ')"
}
$collectedNodes = @($collectionNonblank[0..9])
Assert-ExactList -Observed $collectedNodes -Expected $Nodes -Label "collected E2 nodes"
$postCollectionStatus = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "status", "--porcelain=v1", "--untracked-files=all"))
if ($postCollectionStatus.Count -ne 0) {
  throw "collection-only preflight dirtied the candidate worktree"
}

$pytestArguments = @("-m", "pytest", "-q", "-p", "no:cacheprovider") + $Nodes
foreach ($argument in $pytestArguments) {
  if ($argument -match '[\s"]') {
    throw "frozen Start-Process argument contains whitespace or quote: $argument"
  }
}
$nodeListSha = Invoke-StrictJson -Mode "check" -Path "-" -Payload $Nodes
$commandDescriptor = [ordered]@{
  executable_path = $Python
  executable_sha256 = $pythonSha
  argv = $pytestArguments
  working_directory = $CandidateRoot
  wall_milliseconds = $WallMilliseconds
  removed_environment_names = $RemovedEnvironmentNames
  package_identity = $packageIdentity
  environment_overrides = [ordered]@{
    PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
    PYTHONDONTWRITEBYTECODE = "1"
    PYTHONHASHSEED = "0"
  }
}
$commandSha = Invoke-StrictJson -Mode "check" -Path "-" -Payload $commandDescriptor
$diagnosticSha = Invoke-StrictJson -Mode "check" -Path "-" -Payload ([ordered]@{
  schema_version = "u24-e2-q1-preflight-diagnostic-v1"
  control_attempt_ordinal = $ControlAttemptOrdinal
  authority_commit = $authorityCommit
  authority_tree = $authorityTree
  authority_document_blob = $authorityBlob
  repair_authority_commit = $repairCommit
  accepted_e1_commit = $acceptedCommit
  semantic_base_commit = $semanticBase
  candidate_commit = $candidateCommit
  candidate_tree = $candidateTree
  node_list_sha256 = $nodeListSha
  command_sha256 = $commandSha
  authority_ci_run_id = $authorityRunId
  repair_authority_ci_run_id = $repairAuthorityRunId
  control_record_sha256 = $controlRecordSha
  scientific_look_consumed = $false
  disposition = "PREFLIGHT_GREEN_READY_TO_ARM"
})
$finalOriginUrl = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "remote", "get-url", "origin") -ExpectedCount 1)
Assert-ExactList -Observed $finalOriginUrl -Expected @($ExpectedOriginUrl) -Label "final origin URL"
$finalPythonSha = (Get-FileHash -LiteralPath $Python -Algorithm SHA256).Hash
if ($finalPythonSha -cne $pythonSha) {
  throw "Python executable identity drifted before marker creation"
}
$finalPythonVersion = @(& $Python --version 2>&1 | ForEach-Object { [string]$_ })
$finalPythonVersionCode = $LASTEXITCODE
if ($finalPythonVersionCode -ne 0) {
  throw "final Python version query failed ($finalPythonVersionCode): $($finalPythonVersion -join ' | ')"
}
Assert-ExactList -Observed $finalPythonVersion -Expected @("Python 3.13.7") -Label "final Python version"
$finalPackageIdentity = Get-ExactPackageIdentity
if ($finalPackageIdentity -cne $packageIdentity) {
  throw "package/import identity drifted before marker creation"
}
$finalFetchLines = @(& git -C $CandidateRoot fetch --prune --prune-tags --tags origin '+refs/heads/*:refs/remotes/origin/*' 2>&1 | ForEach-Object { [string]$_ })
if ($LASTEXITCODE -ne 0) {
  throw "final pre-marker origin fetch failed: $($finalFetchLines -join ' | ')"
}
foreach ($binding in @(
  @($AuthorityRefName, $authorityCommit),
  @($RepairRefName, $repairCommit),
  @($AcceptedRefName, $acceptedCommit),
  @($AcceptedAnchorRefName, $acceptedAnchorCommit),
  @($CarrierRefName, $carrierCommit)
)) {
  $freshValue = Get-FreshRemoteHead -BranchName ([string]$binding[0])
  if ($freshValue -cne [string]$binding[1]) {
    throw "remote head drifted before marker creation: $($binding[0])"
  }
  $trackedValue = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ("refs/remotes/origin/" + $binding[0] + "^{commit}"))
  if ($trackedValue -cne [string]$binding[1]) {
    throw "final fetched remote-tracking object differs for $($binding[0])"
  }
}
Assert-FreshRemoteHeadAbsent -BranchName $CandidateRefName
Assert-FreshRemoteHeadAbsent -BranchName $CloseoutRefName
$finalCandidateHead = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", "HEAD^{commit}")
if ($finalCandidateHead -cne $candidateCommit) {
  throw "candidate worktree HEAD drifted before marker creation"
}
$finalCandidateStatus = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "status", "--porcelain=v1", "--untracked-files=all"))
if ($finalCandidateStatus.Count -ne 0) {
  throw "candidate worktree became dirty before marker creation"
}
$finalCandidateRemoteContainment = @(Invoke-GitLines -Arguments @(
  "-C", $CandidateRoot, "for-each-ref", "--format=%(refname)", "--contains", $candidateCommit,
  "refs/remotes/origin", "refs/tags"
))
Assert-ExactList -Observed $finalCandidateRemoteContainment -Expected @(
  "refs/remotes/origin/codex/uprime-e2-qualification-authority-q1"
) -Label "final pre-marker remote containment"
Write-Output ("U24_E2_Q1_PREFLIGHT_DIAGNOSTIC_SHA256=" + $diagnosticSha)

$AttemptRoot = Join-Path $BridgeRoot "attempt_markers"
$null = [IO.Directory]::CreateDirectory($AttemptRoot)
Assert-NoReparseAncestry -Path $AttemptRoot
$attemptMarkerPath = Join-Path $AttemptRoot ("u24_e2_q1__" + $authorityCommit + ".json")
if (Test-Path -LiteralPath $attemptMarkerPath) {
  throw "Q1 scientific attempt marker already exists"
}
$attemptMarkerSha = Invoke-StrictJson -Mode "create" -Path $attemptMarkerPath -Payload ([ordered]@{
  schema_version = "u24-e2-q1-scientific-attempt-v1"
  authority_commit = $authorityCommit
  authority_document_blob = $authorityBlob
  accepted_e1_commit = $acceptedCommit
  semantic_base_commit = $semanticBase
  candidate_commit = $candidateCommit
  candidate_tree = $candidateTree
  control_attempt_ordinal = $ControlAttemptOrdinal
  node_list_sha256 = $nodeListSha
  command_sha256 = $commandSha
  preflight_diagnostic_sha256 = $diagnosticSha
  control_record_sha256 = $controlRecordSha
  created_at_utc = [DateTime]::UtcNow.ToString("o")
  run_state = "RUN_OPENED"
})
Write-Output ("U24_E2_Q1_ATTEMPT_MARKER_SHA256=" + $attemptMarkerSha)

$process = Start-Process -FilePath $Python -ArgumentList $pytestArguments `
  -WorkingDirectory $CandidateRoot -NoNewWindow -PassThru
$null = $process.Handle
if (-not $process.WaitForExit($WallMilliseconds)) {
  try {
    if (-not $process.HasExited) {
      $process.Kill()
    }
  } catch {
    if (-not $process.HasExited) {
      [Console]::Error.WriteLine("timed-out child kill failed after scientific consumption: " + $_.Exception.Message)
      exit 125
    }
  }
  if (-not $process.WaitForExit(10000)) {
    [Console]::Error.WriteLine("timed-out child did not exit during bounded cleanup after scientific consumption")
    exit 125
  }
  exit 124
}
$childExitCode = $process.ExitCode
if ($null -eq $childExitCode) {
  [Console]::Error.WriteLine("completed child exposed no exit code after scientific consumption")
  exit 125
}
exit [int]$childExitCode
```
