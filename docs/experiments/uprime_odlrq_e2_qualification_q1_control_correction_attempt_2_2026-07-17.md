# U-prime / ODLRQ E2 Q1 control correction: attempt 2

Date: 2026-07-17 (Asia/Tokyo)

Status: **DRAFT UNTIL THIS DOCUMENT IS THE SOLE FIRST-PARENT TREE ADDITION OF
`codex/uprime-e2-qualification-authority-q1-a2`, WITH THE UNCHANGED STAGE-1
CORRECTION AS ORDERED PARENT 2, AND THAT REF IS CREATED BY ONE NON-FORCE PUSH.**
After freeze it licenses control attempt 2 only.

## 1. Prior attempt and unchanged scientific object

Control attempt 1 was invoked under authority
`4643ccc502efe8cc6cee44b6bd035d487348f8f1` after its natural CI run
`29547190425` produced the exact expected topology-only red with zero E2 hits.
It stopped before `attempt-1-opened.json`, before the scientific marker, and
before any E2 node.  Its immutable result is
`C:\Users\yusei\Desktop\codex_claude_bridge\control_records\u24_e2_q1\attempt-1-result.md`
with SHA256
`566EEF4B8A879FD49EA8FAFD4A79B187D1C9E05754112BA2883104584C303E3F`.
Therefore control ordinal 1 is consumed and the scientific look is not.

The Stage-1 candidate remains exactly
`7a8b28872439dd61d40174c2500c5990790002be`.  No candidate byte, endpoint
meaning, node list, wall, environment, process primitive, protected endpoint,
accepted ref, or success rule changes in attempt 2.

## 2. Diagnosis and sole behavioral correction

Windows PowerShell 5.1 promoted the expected native Git stderr from the
bridge-root non-worktree probe to a terminating `NativeCommandError` because
global `$ErrorActionPreference` was `Stop`.  This occurred before the code could
adjudicate Git exit 128.  It is a control-flow defect, not scientific evidence.

The only behavioral correction is to save `$ErrorActionPreference`, set it to
`Continue` for that one expected-nonzero Git invocation, capture stderr and
`$LASTEXITCODE`, restore `Stop` in `finally`, and require both exact exit 128 and
the exact non-repository diagnostic.  The other textual differences below are
the mechanically required ordinal-2 record name, fresh authority topology,
prior-result binding, and two-authority containment set.

## 3. Frozen authority topology and CI

```text
ref       codex/uprime-e2-qualification-authority-q1-a2
subject   uprime: correct E2 Q1 qualification control attempt 2
parent 1  remote codex/uprime-e2-qualification-authority-q1
parent 2  identical Stage-1 correction resolved from parent 1's parent 2
tree      parent-1 tree plus this one mode-100644 document only
push      one non-force creation; never amended, repointed, deleted, or forced
```

The new sidecar's sole natural CI must again be the exact known control red:
`1 failed, 2599 passed, 8 skipped, 161 deselected`, sole topology failure,
`run_attempt=1`, exact workflow ID `292918982`, and zero E2 hits.  Attempt 2 may
be invoked only after the inline block machine-checks repair, prior-authority,
and current-authority natural CI identities.

## 4. Attempt-2 arming and stopping rule

Invocation of the frozen block consumes control ordinal 2 even if it fails
before its durable record.  Successful exclusive creation of
`attempt-2-opened.json` is its durable counter.  Successful exclusive creation
of `u24_e2_q1__<attempt-2-authority>.json` consumes the single scientific look.
The block requires the entire frozen `u24_e2_q1__*.json` marker namespace to be
empty both during initial attempt-state validation and immediately before the
exclusive open; an attempt-1 or other Q1 marker therefore blocks attempt 2.
After that marker, every outcome is terminal and no second scientific launch is
allowed.  A pre-marker failure permits at most the already-frozen attempt-3
mechanism; it cannot change the candidate or process primitive.

All forbidden/deferred work and the local/candidate/accepted success gates from
the attempt-1 authority remain in force, including the requirement that exit
zero alone is insufficient and the inherited console must show exact `10 passed`.

## 5. Frozen attempt-2 inline control block

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
$PriorAuthorityRefName = "codex/uprime-e2-qualification-authority-q1"
$AuthorityRefName = "codex/uprime-e2-qualification-authority-q1-a2"
$AcceptedRefName = "codex/uprime-odlrq-plan"
$AcceptedAnchorRefName = "codex/uprime-u2-u4-development-r6-build"
$CarrierRefName = "codex/uprime-e2-endpoint-runner-control"
$CandidateRefName = "codex/uprime-e2-qualification-candidate-q1"
$CloseoutRefName = "codex/uprime-e2-qualification-closeout-q1"
$RepairDocumentPath = "docs/experiments/uprime_odlrq_e2_q1_fixture_repair_authority_2026-07-17.md"
$PriorAuthorityDocumentPath = "docs/experiments/uprime_odlrq_e2_qualification_q1_amendment_2026-07-17.md"
$AuthorityDocumentPath = "docs/experiments/uprime_odlrq_e2_qualification_q1_control_correction_attempt_2_2026-07-17.md"
$ExpectedAttempt1ResultSha256 = "566EEF4B8A879FD49EA8FAFD4A79B187D1C9E05754112BA2883104584C303E3F"
$RepairSubject = "uprime: authorize E2 Q1 fixture repair"
$PriorAuthoritySubject = "uprime: freeze E2 Q1 qualification"
$AuthoritySubject = "uprime: correct E2 Q1 qualification control attempt 2"
$CandidateSubject = "uprime: repair E2 fixture namespace and serialization"
$ControlAttemptOrdinal = 2
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
$priorAuthorityCommit = Get-FreshRemoteHead -BranchName $PriorAuthorityRefName
$BridgeRoot = "C:\Users\yusei\Desktop\codex_claude_bridge"
if (-not (Test-Path -LiteralPath $BridgeRoot -PathType Container)) {
  throw "bridge root is absent or not a directory"
}
Assert-NoReparseAncestry -Path $BridgeRoot
$savedErrorActionPreference = $ErrorActionPreference
try {
  $ErrorActionPreference = "Continue"
  $bridgeGitProbe = @(& git -C $BridgeRoot rev-parse --show-toplevel 2>&1 | ForEach-Object { [string]$_ })
  $bridgeGitExitCode = $LASTEXITCODE
} finally {
  $ErrorActionPreference = $savedErrorActionPreference
}
if ($bridgeGitExitCode -ne 128) {
  throw "bridge non-worktree probe returned unexpected exit $bridgeGitExitCode : $($bridgeGitProbe -join ' | ')"
}
Assert-ExactList -Observed $bridgeGitProbe -Expected @(
  "fatal: not a git repository (or any of the parent directories): .git"
) -Label "bridge non-worktree diagnostic"
$ControlRoot = Join-Path $BridgeRoot "control_records\u24_e2_q1"
$null = [IO.Directory]::CreateDirectory($ControlRoot)
Assert-NoReparseAncestry -Path $ControlRoot
$AttemptRoot = Join-Path $BridgeRoot "attempt_markers"
$null = [IO.Directory]::CreateDirectory($AttemptRoot)
Assert-NoReparseAncestry -Path $AttemptRoot
$existingQ1ScientificMarkers = @(Get-ChildItem -LiteralPath $AttemptRoot -Filter "u24_e2_q1__*.json" -File)
if ($existingQ1ScientificMarkers.Count -ne 0) {
  throw "attempt 2 requires zero prior Q1 scientific markers"
}
$existingControlRecords = @(Get-ChildItem -LiteralPath $ControlRoot -Filter "attempt-*-opened.json" -File)
if ($existingControlRecords.Count -ne 0) {
  throw "attempt-2 block requires zero prior opened control records"
}
$existingResultRecords = @(Get-ChildItem -LiteralPath $ControlRoot -Filter "attempt-*-result.md" -File)
Assert-ExactList -Observed @($existingResultRecords | ForEach-Object { $_.Name }) -Expected @(
  "attempt-1-result.md"
) -Label "prior control-result record set"
$attempt1ResultPath = Join-Path $ControlRoot "attempt-1-result.md"
$attempt1ResultItem = Get-Item -LiteralPath $attempt1ResultPath -Force -ErrorAction Stop
if (($attempt1ResultItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
  throw "attempt-1 result record is a reparse point"
}
$attempt1ResultSha = (Get-FileHash -LiteralPath $attempt1ResultPath -Algorithm SHA256).Hash
if ($attempt1ResultSha -cne $ExpectedAttempt1ResultSha256) {
  throw "attempt-1 result record SHA mismatch"
}
$attempt1ResultText = [IO.File]::ReadAllText($attempt1ResultPath, [Text.Encoding]::UTF8).Replace("`r`n", "`n")
$attempt1AuthorityMatches = [regex]::Matches(
  $attempt1ResultText,
  '(?m)^- qualification authority commit: `([0-9a-f]{40})`$'
)
$attempt1CandidateMatches = [regex]::Matches(
  $attempt1ResultText,
  '(?m)^- unchanged candidate commit: `([0-9a-f]{40})`$'
)
if ($attempt1AuthorityMatches.Count -ne 1 -or
    $attempt1AuthorityMatches[0].Groups[1].Value -cne $priorAuthorityCommit -or
    $attempt1CandidateMatches.Count -ne 1 -or
    [regex]::Matches($attempt1ResultText, '(?m)^- control record SHA256: `ABSENT`$').Count -ne 1 -or
    [regex]::Matches($attempt1ResultText, '(?m)^- scientific marker SHA256: `ABSENT`$').Count -ne 1 -or
    [regex]::Matches($attempt1ResultText, '(?m)^- scientific look consumed: `false`$').Count -ne 1) {
  throw "attempt-1 result authority/candidate/no-look fields mismatch"
}
$attempt1CandidateCommit = [string]$attempt1CandidateMatches[0].Groups[1].Value
$controlRecordPath = Join-Path $ControlRoot "attempt-2-opened.json"
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
  @($PriorAuthorityRefName, $priorAuthorityCommit),
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
if ($authorityParents.Count -ne 3 -or $authorityParents[0] -cne $authorityCommit -or $authorityParents[1] -cne $priorAuthorityCommit) {
  throw "Q1 attempt-2 authority ordered-parent topology mismatch"
}
$candidateCommit = [string]$authorityParents[2]
if ($candidateCommit -cne $attempt1CandidateCommit) {
  throw "attempt-2 candidate differs from SHA-bound attempt-1 result"
}
$priorAuthorityParentLines = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "rev-list", "--parents", "-n", "1", $priorAuthorityCommit) -ExpectedCount 1)
$priorAuthorityParents = ([string]$priorAuthorityParentLines[0]) -split ' '
if ($priorAuthorityParents.Count -ne 3 -or
    $priorAuthorityParents[0] -cne $priorAuthorityCommit -or
    $priorAuthorityParents[1] -cne $repairCommit -or
    $priorAuthorityParents[2] -cne $candidateCommit) {
  throw "attempt-1 authority ordered-parent/candidate chain mismatch"
}
$candidateTree = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ($candidateCommit + "^{tree}"))
$authorityTree = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ($authorityCommit + "^{tree}"))
$repairTree = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ($repairCommit + "^{tree}"))
$authorityBlob = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ($authorityCommit + ":" + $AuthorityDocumentPath))
$priorAuthorityBlob = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ($priorAuthorityCommit + ":" + $PriorAuthorityDocumentPath))
$repairBlob = Resolve-OneGitObject -Arguments @("-C", $CandidateRoot, "rev-parse", ($repairCommit + ":" + $RepairDocumentPath))
Assert-ExactList -Observed @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "log", "-1", "--format=%s", $authorityCommit) -ExpectedCount 1) -Expected @($AuthoritySubject) -Label "authority subject"
Assert-ExactList -Observed @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "log", "-1", "--format=%s", $priorAuthorityCommit) -ExpectedCount 1) -Expected @($PriorAuthoritySubject) -Label "prior authority subject"
Assert-ExactList -Observed @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "log", "-1", "--format=%s", $repairCommit) -ExpectedCount 1) -Expected @($RepairSubject) -Label "repair-authority subject"
Assert-Mode100644 -Commit $priorAuthorityCommit -Path $PriorAuthorityDocumentPath
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

$authorityFirstParentPaths = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "diff", "--name-only", $priorAuthorityCommit, $authorityCommit))
Assert-ExactList -Observed $authorityFirstParentPaths -Expected @($AuthorityDocumentPath) -Label "authority first-parent path set"
$authorityFirstParentStatus = @(Invoke-GitLines -Arguments @("-C", $CandidateRoot, "diff", "--name-status", $priorAuthorityCommit, $authorityCommit))
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
  "refs/remotes/origin/codex/uprime-e2-qualification-authority-q1",
  "refs/remotes/origin/codex/uprime-e2-qualification-authority-q1-a2"
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
$priorAuthorityRunId = Get-ExactKnownTopologyRed -Commit $priorAuthorityCommit -BranchName $PriorAuthorityRefName -Label "attempt-1 qualification authority"
$authorityRunId = Get-ExactKnownTopologyRed -Commit $authorityCommit -BranchName $AuthorityRefName -Label "attempt-2 qualification authority"

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
  prior_authority_commit = $priorAuthorityCommit
  prior_authority_document_blob = $priorAuthorityBlob
  attempt_1_result_sha256 = $attempt1ResultSha
  repair_authority_commit = $repairCommit
  accepted_e1_commit = $acceptedCommit
  semantic_base_commit = $semanticBase
  candidate_commit = $candidateCommit
  candidate_tree = $candidateTree
  node_list_sha256 = $nodeListSha
  command_sha256 = $commandSha
  authority_ci_run_id = $authorityRunId
  prior_authority_ci_run_id = $priorAuthorityRunId
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
  @($PriorAuthorityRefName, $priorAuthorityCommit),
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
  "refs/remotes/origin/codex/uprime-e2-qualification-authority-q1",
  "refs/remotes/origin/codex/uprime-e2-qualification-authority-q1-a2"
) -Label "final pre-marker remote containment"
Write-Output ("U24_E2_Q1_PREFLIGHT_DIAGNOSTIC_SHA256=" + $diagnosticSha)

$finalExistingQ1ScientificMarkers = @(Get-ChildItem -LiteralPath $AttemptRoot -Filter "u24_e2_q1__*.json" -File)
if ($finalExistingQ1ScientificMarkers.Count -ne 0) {
  throw "a Q1 scientific marker appeared before attempt-2 arming"
}
$attemptMarkerPath = Join-Path $AttemptRoot ("u24_e2_q1__" + $authorityCommit + ".json")
if (Test-Path -LiteralPath $attemptMarkerPath) {
  throw "Q1 scientific attempt marker already exists"
}
$attemptMarkerSha = Invoke-StrictJson -Mode "create" -Path $attemptMarkerPath -Payload ([ordered]@{
  schema_version = "u24-e2-q1-scientific-attempt-v1"
  authority_commit = $authorityCommit
  authority_document_blob = $authorityBlob
  prior_authority_commit = $priorAuthorityCommit
  attempt_1_result_sha256 = $attempt1ResultSha
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
