[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("B0", "E0", "E1", "E2", "ME0", "S0", "I0", "EMIT", "CLOSEOUT")]
    [string] $Lane,
    [Parameter(ValueFromRemainingArguments = $true)]
    [object[]] $UnexpectedArguments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ExitUsage = 64
$ExitPreflight = 65
$ExitNoTests = 66
$ExitPythonUnavailable = 69
$ExitInternalError = 70
$ExitTimeout = 124
$ExitQualificationMargin = 125
$ExitMemory = 137
$ExitOutput = 138
$StopwatchFrequency = [int64][Diagnostics.Stopwatch]::Frequency
$MemoryLimitBytes = [uint64]2 * 1024 * 1024 * 1024
$OutputLimitBytes = [int64]64 * 1024 * 1024
$ExpectedPythonVersion = "3.13.7"
$ExpectedPythonSha256 = "D932E5E2F324D57F392E8FD063DCF6D0185BE8A664C57C6D24E7762ED02C28CA"
$ExpectedNumpyVersion = "2.3.3"
$ExpectedMultiarraySha256 = "3F8A35487C05180F4F6B6168165935C99FAE6F14264A443FB665C5CB07FA2725"
$ExpectedLinalgSha256 = "5B7F5ECB0970EE956E36608D4F1ED405C0B688691E99C05F5F314C2F053DBA10"
$ExpectedOpenBlasSha256 = "860D95B1C38E637CE4509F5FA24FBF2A98BA8696F9F3D28BF184BEE74AD9A325"
$RuntimeIdentitySha256 = "D6E6DEBCE5C150AE31BA0D04EAF6E59FD2D79FDC4C0D5272264574665C0242F4"
$ReceiptSchema = "u24-lane-receipt-v1"
$RuntimeManifestCanonical = @'
{"blas":"scipy-openblas-0.3.30-USE64BITINT-Haswell","linalg_path":"C:\\Users\\yusei\\AppData\\Roaming\\Python\\Python313\\site-packages\\numpy\\linalg\\_umath_linalg.cp313-win_amd64.pyd","linalg_sha256":"5B7F5ECB0970EE956E36608D4F1ED405C0B688691E99C05F5F314C2F053DBA10","multiarray_path":"C:\\Users\\yusei\\AppData\\Roaming\\Python\\Python313\\site-packages\\numpy\\_core\\_multiarray_umath.cp313-win_amd64.pyd","multiarray_sha256":"3F8A35487C05180F4F6B6168165935C99FAE6F14264A443FB665C5CB07FA2725","numpy_version":"2.3.3","openblas_path":"C:\\Users\\yusei\\AppData\\Roaming\\Python\\Python313\\site-packages\\numpy.libs\\libscipy_openblas64_-860d95b1c38e637ce4509f5fa24fbf2a.dll","openblas_sha256":"860D95B1C38E637CE4509F5FA24FBF2A98BA8696F9F3D28BF184BEE74AD9A325","python_path":"C:\\Python313\\python.exe","python_sha256":"D932E5E2F324D57F392E8FD063DCF6D0185BE8A664C57C6D24E7762ED02C28CA","python_version":"3.13.7","threads":{"MKL_NUM_THREADS":"1","NUMEXPR_NUM_THREADS":"1","OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1"}}
'@
$RuntimeManifestCanonical = $RuntimeManifestCanonical.TrimEnd("`r", "`n")

$Walls = @{
    B0 = 60; E0 = 90; E1 = 120; E2 = 180; ME0 = 180
    S0 = 300; I0 = 900; EMIT = 900; CLOSEOUT = 60
}
$Dispositions = @{
    B0 = "CPU_U24_IDENTITY_AND_RUNNER_GATE_VERIFIED"
    E0 = "CPU_SYNTHETIC_QUOTIENT_COORDINATE_GENERATOR_VERIFIED"
    E1 = "CPU_SYNTHETIC_FIBER_ENVELOPE_CORE_VERIFIED"
    E2 = "CPU_SYNTHETIC_FINITE_HORIZON_ENVELOPE_VERIFIED"
    ME0 = "CPU_SYNTHETIC_MAXENT_CORE_VERIFIED"
    S0 = "CPU_SYNTHETIC_TYPED_SIMILARITY_CORE_VERIFIED"
    I0 = "CPU_SYNTHETIC_U2_U4_CANDIDATE_CONSTRUCTED"
    EMIT = "CPU_SYNTHETIC_U2_U4_ARTIFACTS_EMITTED"
    CLOSEOUT = "CPU_SYNTHETIC_U2_U4_ARTIFACTS_REVALIDATED"
}
$LaneTests = @{
    B0 = @("tests/test_uprime_u2_u4_development.py")
    E0 = @("tests/test_odlrq_quotient_generator.py", "tests/test_uprime_u2_u4_development.py")
    E1 = @("tests/test_odlrq_quotient_generator.py", "tests/test_odlrq_envelope.py", "tests/test_uprime_u2_u4_development.py")
    E2 = @("tests/test_odlrq_quotient_generator.py", "tests/test_odlrq_envelope.py", "tests/test_odlrq_selection.py", "tests/test_uprime_u2_u4_development.py")
    ME0 = @("tests/test_odlrq_quotient_generator.py", "tests/test_odlrq_envelope.py", "tests/test_odlrq_selection.py", "tests/test_odlrq_maxent.py", "tests/test_uprime_u2_u4_development.py")
    S0 = @("tests/test_odlrq_quotient_generator.py", "tests/test_odlrq_envelope.py", "tests/test_odlrq_selection.py", "tests/test_odlrq_maxent.py", "tests/test_odlrq_similarity.py", "tests/test_uprime_u2_u4_development.py")
    I0 = @("tests/test_odlrq_quotient_generator.py", "tests/test_odlrq_envelope.py", "tests/test_odlrq_selection.py", "tests/test_odlrq_maxent.py", "tests/test_odlrq_similarity.py", "tests/test_uprime_u2_u4_development.py")
}
$LaneRequirements = @{
    E0 = @("lean_rgc/odlrq/quotient_generator.py", "odlrq_exact_quotient_coordinate_generator_v1")
    E1 = @("lean_rgc/odlrq/envelope.py", "class FiberEnvelope")
    E2 = @("lean_rgc/odlrq/selection.py", "class CertifiedSupportToken")
    ME0 = @("lean_rgc/odlrq/maxent.py", "INTERIOR_SOLVED")
    S0 = @("lean_rgc/odlrq/similarity.py", "class LocalTower")
    I0 = @("lean_rgc/evals/uprime_u2_u4_development.py", "u24_integrated_certificate_v1")
}

# U24_DENYLIST_BEGIN
$DenylistCanonicalJson = @'
["docs/experiments/inputs/","docs/experiments/artifacts/","runs/","lean_rgc/native_lean/RGCKernelRPC.lean","tools/uprime_official_transport_v2_smoke.py","tools/run_uprime_official_transport_v2_smoke.ps1","tools/run_uprime_official_transport_v2_tests.ps1","tests/test_uprime_official_transport_v2_smoke.py","C:/Users/yusei/Desktop/lean_rgc_automation_stack_v47_goal_state_dynamics/llm_local.json","C:/Users/yusei/Desktop/lean_rgc_automation_stack_v47_goal_state_dynamics/pilot_tasks.json","C:/Users/yusei/Desktop/lean_rgc_automation_stack_v47_goal_state_dynamics/fake_lean_smoke.py","C:/Users/yusei/Desktop/lean_rgc_automation_stack_v47_goal_state_dynamics/smoke_tasks_local.jsonl","C:/Users/yusei/.codex/quarantine/lean-rgc/uprime-deferred-2026-07-12/","C:/Users/yusei/Desktop/lean_rgc_automation_stack_v47_goal_state_dynamics_transport_v2_live/","C:/Users/yusei/Desktop/lean_rgc_automation_stack_v47_goal_state_dynamics_transport_v2_i1/","C:/Users/yusei/Desktop/lean_rgc_automation_stack_v47_goal_state_dynamics_transport_v2_recovery_live/","lean_rgc.egg-info/"]
'@
# U24_DENYLIST_END

function Write-RunnerError {
    param([Parameter(Mandatory = $true)][string] $Message)
    [Console]::Error.WriteLine("uprime-u2-u4-development: {0}", $Message)
}

function Resolve-RegularFile {
    param(
        [Parameter(Mandatory = $true)][string] $LiteralPath,
        [Parameter(Mandatory = $true)][string] $RequiredRoot
    )
    $item = Get-Item -LiteralPath $LiteralPath -Force
    if ($item.PSIsContainer -or (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
        throw "expected a non-reparse regular file: $LiteralPath"
    }
    $resolved = [IO.Path]::GetFullPath($item.FullName)
    $root = [IO.Path]::GetFullPath($RequiredRoot).TrimEnd("\", "/")
    if (-not ($resolved.Equals($root, [StringComparison]::OrdinalIgnoreCase) -or
              $resolved.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase))) {
        throw "resolved file escaped required root: $LiteralPath"
    }
    return $resolved
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string] $LiteralPath)
    return (Get-FileHash -LiteralPath $LiteralPath -Algorithm SHA256).Hash.ToUpperInvariant()
}

function Get-Sha256Text {
    param([Parameter(Mandatory = $true)][string] $Text)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.UTF8Encoding]::new($false).GetBytes($Text)
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "").ToUpperInvariant()
    }
    finally { $sha.Dispose() }
}

function Quote-NativeArgument {
    param([Parameter(Mandatory = $true)][string] $Value)
    if ($Value.IndexOf([char]0) -ge 0 -or $Value.Contains("`r") -or
        $Value.Contains("`n") -or $Value.Contains('"') -or
        $Value.EndsWith("\") -or $Value.EndsWith("/")) {
        throw "unsafe native argument"
    }
    return '"' + $Value + '"'
}

function Get-CapturedBytes {
    param([string[]] $Paths)
    $total = [int64]0
    foreach ($path in $Paths) {
        if ($null -ne $path -and (Test-Path -LiteralPath $path -PathType Leaf)) {
            $total += (Get-Item -LiteralPath $path -Force).Length
        }
    }
    return $total
}

$unboundCount = if ($null -eq $MyInvocation.UnboundArguments) { 0 } else { @($MyInvocation.UnboundArguments).Count }
$unexpectedCount = if ($null -eq $UnexpectedArguments) { 0 } else { @($UnexpectedArguments).Count }
if ($PSBoundParameters.Count -ne 1 -or $unboundCount -ne 0 -or $unexpectedCount -ne 0) {
    Write-RunnerError "exactly one -Lane selector is required"
    exit $ExitUsage
}
if ($env:OS -ne "Windows_NT" -or -not [Environment]::Is64BitProcess) {
    Write-RunnerError "64-bit Windows is required"
    exit $ExitPreflight
}
$isSemanticLane = $Lane -notin @("EMIT", "CLOSEOUT")

$runTemp = $null
$systemTemp = $null
$pythonProcess = $null
$job = [IntPtr]::Zero
$stdoutStream = $null
$stderrStream = $null
$stdoutTask = $null
$stderrTask = $null
$exitCode = $ExitInternalError

try {
    if ([string]::IsNullOrWhiteSpace($PSCommandPath)) { throw "script path unavailable" }
    $scriptPath = Resolve-RegularFile -LiteralPath $PSCommandPath -RequiredRoot (Split-Path -Parent $PSCommandPath)
    $toolsRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Split-Path -Parent $scriptPath)).ProviderPath)
    $repoRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Join-Path $toolsRoot "..")).ProviderPath)
    $expectedScript = [IO.Path]::GetFullPath((Join-Path $repoRoot "tools\run_uprime_u2_u4_development_tests.ps1"))
    if (-not $scriptPath.Equals($expectedScript, [StringComparison]::OrdinalIgnoreCase)) { throw "runner path changed" }
    foreach ($marker in @(".git", "pyproject.toml", "lean_rgc", "tests")) {
        if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $marker))) { throw "repository marker missing: $marker" }
    }
    $headCommit = (& git -C $repoRoot --no-replace-objects rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $headCommit -cnotmatch '^[0-9a-f]{40}$') { throw "commit identity unavailable" }
    if ($Lane -in @("EMIT", "CLOSEOUT")) {
        $acceptedCommit = (& git -C $repoRoot --no-replace-objects rev-parse refs/heads/codex/uprime-odlrq-plan).Trim()
        if ($LASTEXITCODE -ne 0 -or $acceptedCommit -cne $headCommit) {
            throw "EMIT/CLOSEOUT requires the exact accepted I0 head"
        }
    }
    $emitReceiptRaw = (& git -C $repoRoot --no-replace-objects rev-parse --git-path u24_u2_u4_emit_receipt.json).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($emitReceiptRaw)) { throw "EMIT receipt path unavailable" }
    $emitReceiptPath = if ([IO.Path]::IsPathRooted($emitReceiptRaw)) {
        [IO.Path]::GetFullPath($emitReceiptRaw)
    } else { [IO.Path]::GetFullPath((Join-Path $repoRoot $emitReceiptRaw)) }
    $expectedEmitMapJson = "{}"
    if ($Lane -eq "EMIT" -and (Test-Path -LiteralPath $emitReceiptPath)) {
        throw "EMIT control receipt already exists; repeat emission is forbidden"
    }
    if ($Lane -eq "CLOSEOUT") {
        if (-not (Test-Path -LiteralPath $emitReceiptPath -PathType Leaf)) { throw "EMIT control receipt is missing" }
        $emitReceipt = [IO.File]::ReadAllText($emitReceiptPath, [Text.UTF8Encoding]::new($false, $true)) | ConvertFrom-Json
        if ($emitReceipt.schema_version -cne "u24-emit-control-receipt-v1" -or
            $emitReceipt.source_commit -cne $headCommit) { throw "EMIT control receipt source identity changed" }
        $emitNames = @($emitReceipt.artifact_sha256.PSObject.Properties.Name | Sort-Object)
        if ($emitNames.Count -ne 7) { throw "EMIT control receipt artifact map is incomplete" }
        foreach ($name in $emitNames) {
            if ([string]$emitReceipt.artifact_sha256.$name -cnotmatch '^[0-9A-F]{64}$') {
                throw "EMIT control receipt digest is malformed"
            }
        }
        $expectedEmitMapJson = ($emitReceipt.artifact_sha256 | ConvertTo-Json -Compress)
    }

    $pythonPath = Resolve-RegularFile -LiteralPath "C:\Python313\python.exe" -RequiredRoot "C:\Python313"
    if ((Get-Item -LiteralPath $pythonPath -Force).VersionInfo.FileVersion -cne $ExpectedPythonVersion -or
        (Get-Sha256 -LiteralPath $pythonPath) -cne $ExpectedPythonSha256) { throw "Python identity changed" }
    $userSite = "C:\Users\yusei\AppData\Roaming\Python\Python313\site-packages"
    $multiarrayPath = Resolve-RegularFile -LiteralPath (Join-Path $userSite "numpy\_core\_multiarray_umath.cp313-win_amd64.pyd") -RequiredRoot $userSite
    $linalgPath = Resolve-RegularFile -LiteralPath (Join-Path $userSite "numpy\linalg\_umath_linalg.cp313-win_amd64.pyd") -RequiredRoot $userSite
    $openBlasPath = Resolve-RegularFile -LiteralPath (Join-Path $userSite "numpy.libs\libscipy_openblas64_-860d95b1c38e637ce4509f5fa24fbf2a.dll") -RequiredRoot $userSite
    if ((Get-Sha256 $multiarrayPath) -cne $ExpectedMultiarraySha256 -or
        (Get-Sha256 $linalgPath) -cne $ExpectedLinalgSha256 -or
        (Get-Sha256 $openBlasPath) -cne $ExpectedOpenBlasSha256) { throw "NumPy native identity changed" }
    if ((Get-Sha256Text $RuntimeManifestCanonical) -cne $RuntimeIdentitySha256) {
        throw "canonical runtime manifest identity changed"
    }

    [object[]]$tests = @(if ($isSemanticLane) { $LaneTests[$Lane] } else { })
    if ($isSemanticLane -and $tests.Count -eq 0) { throw "lane has no registered tests" }
    if ($LaneRequirements.ContainsKey($Lane)) {
        $requirement = @($LaneRequirements[$Lane])
        $requiredPath = Resolve-RegularFile -LiteralPath (Join-Path $repoRoot $requirement[0]) -RequiredRoot $repoRoot
        $requiredText = [IO.File]::ReadAllText($requiredPath, [Text.UTF8Encoding]::new($false, $true))
        if (-not $requiredText.Contains($requirement[1])) {
            throw "requested lane has not reached its frozen source marker"
        }
    }
    if ($isSemanticLane) {
        $manifestPath = Resolve-RegularFile -LiteralPath (Join-Path $repoRoot "tests\tier_manifest.json") -RequiredRoot $repoRoot
        $manifest = [IO.File]::ReadAllText($manifestPath, [Text.UTF8Encoding]::new($false, $true)) | ConvertFrom-Json
        foreach ($relative in $tests) {
            $candidate = Resolve-RegularFile -LiteralPath (Join-Path $repoRoot $relative) -RequiredRoot $repoRoot
            $name = [IO.Path]::GetFileName($candidate)
            $property = $manifest.PSObject.Properties[$name]
            if ($null -eq $property -or @($property.Value).Count -ne 1 -or @($property.Value)[0] -cne "unit") {
                throw "tier manifest is not exact unit for $name"
            }
        }
    }

    $systemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd("\", "/")
    $runTemp = [IO.Path]::GetFullPath((Join-Path $systemTemp ("lean-rgc-u24-" + [Guid]::NewGuid().ToString("N"))))
    $runParent = [IO.Path]::GetFullPath((Split-Path -Parent $runTemp)).TrimEnd("\", "/")
    if (-not $runParent.Equals($systemTemp, [StringComparison]::OrdinalIgnoreCase)) { throw "temporary root escaped" }
    [void][IO.Directory]::CreateDirectory($runTemp)
    $stdoutPath = Join-Path $runTemp "child.stdout"
    $stderrPath = Join-Path $runTemp "child.stderr"
    $childReceiptPath = Join-Path $runTemp "child.receipt.json"
    $armPath = Join-Path $runTemp "child.arm"
    $controlPath = Join-Path $runTemp "control.py"
    $bootstrapPath = Join-Path $runTemp "bootstrap.py"

$control = @'
import importlib.util
import os
import pathlib
import sys

repo = pathlib.Path(os.environ["UPRIME_U24_REPO"])
tests = repo / "tests"
sys.path[:] = [*sys.path, os.environ["UPRIME_U24_USER_SITE"], str(tests)]
spec = importlib.util.spec_from_file_location("uprime_u24_guard", tests / "uprime_u24_guard.py")
if spec is None or spec.loader is None:
    raise RuntimeError("guard control spec unavailable")
guard = importlib.util.module_from_spec(spec)
sys.modules["uprime_u24_guard"] = guard
spec.loader.exec_module(guard)
artifact_root = 'docs/experiments/' + 'artifacts/uprime_u2_u4_development_20260713'
tracked = (
    '.github/workflows/ci.yml',
    *(artifact_root + '/' + name for name in (
        'envelope_core.json', 'global_measure.json', 'integrated_certificate.json',
        'level_transport.json', 'local_tower.json', 'maxent_fixture.json',
        'similarity_certificate.json',
    )),
    'docs/experiments/uprime_odlrq_kp3_d4_canonical_history_closeout_2026-07-12.md',
    'docs/experiments/uprime_odlrq_lane_isolated_recovery_closeout_2026-07-12.md',
    'docs/experiments/uprime_odlrq_official_transport_v2_recovery_failure_closeout_2026-07-13.md',
    'docs/experiments/uprime_odlrq_u2_u4_development_construction_bundle_amendment_2026-07-13.md',
    'docs/experiments/uprime_odlrq_u2_u4_development_failure_closeout_2026-07-13.md',
    'docs/experiments/uprime_odlrq_u2_u4_development_reconstruction_amendment_2026-07-13.md',
    'docs/experiments/uprime_odlrq_u2_u4_development_reconstruction_closeout_2026-07-13.md',
    'docs/experiments/uprime_odlrq_u2_u4_development_reconstruction_failure_closeout_2026-07-13.md',
    'docs/experiments/uprime_odlrq_u2_u4_development_r2_exact_admission_integration_amendment_2026-07-13.md',
    'docs/experiments/uprime_odlrq_u2_u4_development_r2_failure_closeout_2026-07-13.md',
    'docs/experiments/uprime_odlrq_u2_u4_development_r2_topology_bootstrap_amendment_2026-07-13.md',
    'docs/experiments/uprime_odlrq_u2_u4_development_r3_closeout_2026-07-13.md',
    'docs/experiments/uprime_odlrq_u2_u4_development_r3_failure_closeout_2026-07-13.md',
    'docs/experiments/uprime_odlrq_u2_u4_development_r3_stage_local_reentry_amendment_2026-07-13.md',
    'docs/experiments/uprime_odlrq_upper_stack_implementation_plan_and_u05_amendment_2026-07-11.md',
    'lean_rgc/evals/uprime_u2_u4_development.py', 'lean_rgc/odlrq/__init__.py',
    'lean_rgc/odlrq/certificates.py', 'lean_rgc/odlrq/contracts.py',
    'lean_rgc/odlrq/envelope.py', 'lean_rgc/odlrq/maxent.py',
    'lean_rgc/odlrq/quotient_generator.py', 'lean_rgc/odlrq/selection.py',
    'lean_rgc/odlrq/similarity.py', 'tests/test_odlrq_envelope.py',
    'tests/test_odlrq_maxent.py', 'tests/test_odlrq_quotient_generator.py',
    'tests/test_odlrq_selection.py', 'tests/test_odlrq_similarity.py',
    'tests/test_uprime_u2_u4_development.py', 'tests/tier_manifest.json',
    'tests/uprime_u24_guard.py', 'tools/run_uprime_u2_u4_development_tests.ps1',
)
absent = (
    'docs/experiments/uprime_odlrq_u2_u4_development_r3_closeout_2026-07-13.md',
    'docs/experiments/uprime_odlrq_u2_u4_development_r3_failure_closeout_2026-07-13.md',
    'docs/experiments/uprime_odlrq_u2_u4_development_r3_stage_local_reentry_amendment_2026-07-13.md',
    'lean_rgc/evals/uprime_u2_u4_development.py', 'lean_rgc/odlrq/certificates.py',
    'lean_rgc/odlrq/envelope.py', 'lean_rgc/odlrq/maxent.py',
    'lean_rgc/odlrq/selection.py', 'lean_rgc/odlrq/similarity.py',
    'tests/test_odlrq_envelope.py', 'tests/test_odlrq_maxent.py',
    'tests/test_odlrq_selection.py', 'tests/test_odlrq_similarity.py',
)
value = guard.load_control_plane_attestation(
    repo,
    a0_commit='cbc7377c588e024d17438beb83e444c515ff0172',
    identity_path='tests/test_uprime_u2_u4_development.py',
    tracked_paths=tracked,
    absent_at_a0=absent,
)
lane = os.environ["UPRIME_U24_CONTROL_LANE"]
allowed_dirty = set(guard.UNION_SOURCE_PATHS)
if lane == "B0":
    allowed_dirty.add(
        'docs/experiments/uprime_odlrq_u2_u4_development_r3_stage_local_reentry_amendment_2026-07-13.md'
    )
if lane in {"EMIT", "CLOSEOUT"}:
    allowed_dirty.update(guard.CLOSEOUT_ARTIFACTS)
stage_dirty = guard.governed_status_paths(
    value["status_paths"], value["ci_setup_paths"]
)
if any(path not in allowed_dirty for path in stage_dirty):
    raise RuntimeError("unregistered dirty path exists before semantic import")
semantic_markers = {
    "E0": "lean_rgc/odlrq/quotient_generator.py",
    "E1": "lean_rgc/odlrq/envelope.py",
    "E2": "lean_rgc/odlrq/selection.py",
    "ME0": "lean_rgc/odlrq/maxent.py",
    "S0": "lean_rgc/odlrq/similarity.py",
    "I0": "lean_rgc/evals/uprime_u2_u4_development.py",
}
semantic_order = tuple(semantic_markers)
semantic_allowlists = {
    "E0": {
        "lean_rgc/odlrq/quotient_generator.py",
        "lean_rgc/odlrq/__init__.py",
        "tests/test_odlrq_quotient_generator.py",
    },
    "E1": {
        "lean_rgc/odlrq/quotient_generator.py",
        "lean_rgc/odlrq/envelope.py",
        "lean_rgc/odlrq/__init__.py",
        "tests/test_odlrq_quotient_generator.py",
        "tests/test_odlrq_envelope.py",
        "tests/tier_manifest.json",
    },
    "E2": {
        "lean_rgc/odlrq/envelope.py",
        "lean_rgc/odlrq/selection.py",
        "lean_rgc/odlrq/certificates.py",
        "lean_rgc/odlrq/__init__.py",
        "tests/test_odlrq_envelope.py",
        "tests/test_odlrq_selection.py",
        "tests/tier_manifest.json",
    },
    "ME0": {
        "lean_rgc/odlrq/maxent.py",
        "lean_rgc/odlrq/__init__.py",
        "tests/test_odlrq_maxent.py",
        "tests/tier_manifest.json",
    },
    "S0": {
        "lean_rgc/odlrq/similarity.py",
        "lean_rgc/odlrq/__init__.py",
        "tests/test_odlrq_similarity.py",
        "tests/tier_manifest.json",
    },
    "I0": {
        "lean_rgc/odlrq/certificates.py",
        "lean_rgc/odlrq/__init__.py",
        "lean_rgc/evals/uprime_u2_u4_development.py",
        "tests/test_uprime_u2_u4_development.py",
        "tests/tier_manifest.json",
    },
}
bootstrap_correction_sets = {
    frozenset({"tests/uprime_u24_guard.py"}),
    frozenset({
        "tests/test_uprime_u2_u4_development.py",
        "tests/uprime_u24_guard.py",
    }),
    frozenset({
        "tests/uprime_u24_guard.py",
        "tools/run_uprime_u2_u4_development_tests.ps1",
    }),
    frozenset({
        "tests/test_uprime_u2_u4_development.py",
        "tests/uprime_u24_guard.py",
        "tools/run_uprime_u2_u4_development_tests.ps1",
    }),
}
if lane in semantic_markers:
    accepted_result = guard._git(
        repo,
        "rev-parse",
        "refs/heads/codex/uprime-odlrq-plan",
        check=False,
    )
    if accepted_result.returncode != 0:
        raise RuntimeError("semantic lane requires the local accepted branch")
    accepted = accepted_result.stdout.decode("ascii").strip()
    revisions = value.get("revisions")
    if type(revisions) is not list or not revisions:
        raise RuntimeError("semantic accepted-ref topology is malformed")
    head_row = revisions[-1]
    if type(head_row) is not dict or head_row.get("commit") != value.get("head"):
        raise RuntimeError("semantic accepted-ref head is malformed")
    head_parents = head_row.get("parents")
    head_changed = head_row.get("changed_paths")
    if (
        type(head_parents) is not list
        or not all(type(item) is str for item in head_parents)
        or type(head_changed) is not list
        or not all(type(item) is str for item in head_changed)
    ):
        raise RuntimeError("semantic accepted-ref row is malformed")
    marker = semantic_markers[lane]
    dirty_set = set(stage_dirty)
    if stage_dirty:
        if marker in head_changed:
            current_is_correction = True
            if len(head_parents) != 1:
                raise RuntimeError("semantic correction parent is malformed")
            expected_accepted = head_parents[0]
        else:
            current_is_correction = False
            expected_accepted = value["head"]
        if (
            not dirty_set <= semantic_allowlists[lane]
            or (not current_is_correction and marker not in dirty_set)
        ):
            raise RuntimeError("dirty semantic lane does not match its frozen stage")
    else:
        if len(revisions) < 2 or len(head_parents) != 1:
            raise RuntimeError("clean semantic stage parent is malformed")
        parent_row = revisions[-2]
        if type(parent_row) is not dict or parent_row.get("commit") != head_parents[0]:
            raise RuntimeError("clean semantic parent row is malformed")
        parent_parents = parent_row.get("parents")
        parent_changed = parent_row.get("changed_paths")
        if (
            type(parent_parents) is not list
            or not all(type(item) is str for item in parent_parents)
            or type(parent_changed) is not list
            or not all(type(item) is str for item in parent_changed)
        ):
            raise RuntimeError("clean semantic parent data is malformed")
        if marker in parent_changed:
            current_is_correction = True
            if len(parent_parents) != 1:
                raise RuntimeError("clean semantic correction ancestry is malformed")
            expected_accepted = parent_parents[0]
        else:
            current_is_correction = False
            if marker not in head_changed:
                raise RuntimeError("clean semantic stage marker is missing")
            expected_accepted = head_parents[0]
        if not head_changed or not set(head_changed) <= semantic_allowlists[lane]:
            raise RuntimeError("clean semantic lane exceeds its frozen stage")
    if accepted != expected_accepted:
        raise RuntimeError("semantic lane requires accepted branch activation")
    accepted_positions = [
        index for index, row in enumerate(revisions)
        if type(row) is dict and row.get("commit") == accepted
    ]
    if len(accepted_positions) != 1 or accepted_positions[0] < 1:
        raise RuntimeError("accepted branch is outside the registered R3 epoch")
    accepted_history = list(revisions[2:accepted_positions[0] + 1])
    correction_used = False
    if accepted_history:
        first_changed = accepted_history[0].get("changed_paths")
        if (
            type(first_changed) is list
            and frozenset(first_changed) in bootstrap_correction_sets
        ):
            accepted_history.pop(0)
            correction_used = True
    completed = []
    last_stage = None
    for row in accepted_history:
        if type(row) is not dict:
            raise RuntimeError("accepted semantic history row is malformed")
        changed_value = row.get("changed_paths")
        if (
            type(changed_value) is not list
            or not changed_value
            or not all(type(item) is str for item in changed_value)
            or len(changed_value) != len(set(changed_value))
        ):
            raise RuntimeError("accepted semantic history paths are malformed")
        changed = set(changed_value)
        candidate = (
            semantic_order[len(completed)]
            if len(completed) < len(semantic_order)
            else None
        )
        if (
            candidate is not None
            and changed <= semantic_allowlists[candidate]
            and semantic_markers[candidate] in changed
        ):
            completed.append(candidate)
            last_stage = candidate
            continue
        if (
            last_stage is None
            or correction_used
            or not changed <= semantic_allowlists[last_stage]
        ):
            raise RuntimeError("accepted branch skips or mutates a semantic stage")
        correction_used = True
    expected_prefix = list(semantic_order[:semantic_order.index(lane)])
    if completed != expected_prefix:
        raise RuntimeError("accepted branch has not completed the prior semantic stages")
    if current_is_correction and correction_used:
        raise RuntimeError("the shared R3 correction budget is already spent")
print(guard.encode_control_plane_attestation(value))
'@
    [IO.File]::WriteAllText($controlPath, $control, [Text.UTF8Encoding]::new($false))
    $savedRepo = $env:UPRIME_U24_REPO
    $savedSite = $env:UPRIME_U24_USER_SITE
    $controlPycachePrefix = Join-Path $runTemp "control-pycache"
    if (Test-Path -LiteralPath $controlPycachePrefix) { throw "control pycache prefix is not empty" }
    try {
        $env:UPRIME_U24_REPO = $repoRoot
        $env:UPRIME_U24_USER_SITE = $userSite
        $env:UPRIME_U24_CONTROL_LANE = $Lane
        $controlEncoded = (& $pythonPath -I -S -X "pycache_prefix=$controlPycachePrefix" $controlPath)
        if ($LASTEXITCODE -ne 0) { throw "control-plane attestation failed" }
    }
    finally {
        $env:UPRIME_U24_REPO = $savedRepo
        $env:UPRIME_U24_USER_SITE = $savedSite
        Remove-Item Env:UPRIME_U24_CONTROL_LANE -ErrorAction SilentlyContinue
    }
    if ($controlEncoded -is [array]) { $controlEncoded = $controlEncoded -join "" }
    if ($controlEncoded -cnotmatch '^z1:[A-Za-z0-9+/=]+$' -or $controlEncoded.Length -ge 24000) {
        throw "control-plane attestation is malformed or oversized"
    }

    $bootstrap = @'
import ast
import importlib.util
import json
import os
import pathlib
import sys
import time
import types

arm = os.environ.pop("UPRIME_U24_ARM")
while True:
    try:
        with open(arm, "rb") as handle:
            if handle.read() != b"ARM\n":
                raise RuntimeError("arm malformed")
        break
    except FileNotFoundError:
        time.sleep(0.005)

repo = pathlib.Path(os.environ.pop("UPRIME_U24_REPO"))
user_site = os.environ.pop("UPRIME_U24_USER_SITE")
sys.path[:] = [*sys.path, str(repo), str(repo / "tests"), user_site]
sys.modules["colorama"] = types.ModuleType("colorama")
guard_path = repo / "tests" / "uprime_u24_guard.py"
spec = importlib.util.spec_from_file_location("uprime_u24_guard", guard_path)
if spec is None or spec.loader is None:
    raise RuntimeError("guard spec unavailable")
guard = importlib.util.module_from_spec(spec)
sys.modules["uprime_u24_guard"] = guard
spec.loader.exec_module(guard)
guard.verify_runner_denylist(os.environ.pop("UPRIME_U24_DENYLIST").encode("ascii"))

import numpy as np
import numpy.linalg._umath_linalg as ul
np.linalg.svd(np.eye(1, dtype=np.float64), compute_uv=False)
if np.__version__ != os.environ.pop("UPRIME_U24_NUMPY_VERSION"):
    raise RuntimeError("NumPy version changed")
if pathlib.Path(np._core._multiarray_umath.__file__).resolve() != pathlib.Path(os.environ.pop("UPRIME_U24_MULTIARRAY")).resolve():
    raise RuntimeError("NumPy multiarray load path changed")
if pathlib.Path(ul.__file__).resolve() != pathlib.Path(os.environ.pop("UPRIME_U24_LINALG")).resolve():
    raise RuntimeError("NumPy linalg load path changed")
import ctypes
openblas = pathlib.Path(os.environ.pop("UPRIME_U24_OPENBLAS")).resolve()
source_commit = os.environ.pop("UPRIME_U24_SOURCE_COMMIT")
expected_emit_map = json.loads(os.environ.pop("UPRIME_U24_EXPECTED_EMIT_MAP"))
get_module = ctypes.windll.kernel32.GetModuleHandleW
get_module.argtypes = [ctypes.c_wchar_p]
get_module.restype = ctypes.c_void_p
if not get_module(str(openblas)):
    raise RuntimeError("registered OpenBLAS binary is not the loaded backend")

lane = os.environ.pop("UPRIME_U24_LANE")
mode = {
    "EMIT": guard.GuardMode.EMIT,
    "CLOSEOUT": guard.GuardMode.CLOSEOUT,
}.get(lane, guard.GuardMode.SEMANTIC)
policy = guard.GuardPolicy(mode, repo)
guard.install_guard(policy)
encoded_control = os.environ.pop("UPRIME_U24_CONTROL")
os.environ[guard.CONTROL_ATTESTATION_ENV] = encoded_control
receipt = os.environ.pop("UPRIME_U24_CHILD_RECEIPT")

if lane in {"EMIT", "CLOSEOUT"}:
    control = guard.load_control_plane_attestation(
        repo,
        a0_commit="cbc7377c588e024d17438beb83e444c515ff0172",
        identity_path="tests/test_uprime_u2_u4_development.py",
        tracked_paths=(),
        absent_at_a0=(),
    )
    if control["head"] != source_commit:
        raise RuntimeError("publication CONTROL head differs from source commit")
    interval = control["first_parent_after_a0"]
    revisions = {row["commit"]: row for row in control["revisions"]}
    previous = "cbc7377c588e024d17438beb83e444c515ff0172"
    for commit in interval:
        row = revisions[commit]
        if row["parents"] != [previous]:
            raise RuntimeError("publication CONTROL is not a sole-parent chain")
        previous = commit
    if not interval or interval[-1] != source_commit:
        raise RuntimeError("publication CONTROL does not terminate at source commit")
    last_changed = set(revisions[source_commit]["changed_paths"])
    if "lean_rgc/evals/uprime_u2_u4_development.py" not in last_changed:
        raise RuntimeError("publication CONTROL has not reached I0")
    status = set(guard.governed_status_paths(
        control["status_paths"], control["ci_setup_paths"]
    ))
    expected_status = set() if lane == "EMIT" else set(guard.CLOSEOUT_ARTIFACTS)
    if status != expected_status:
        raise RuntimeError("publication CONTROL worktree status is not exact")

if lane == "EMIT":
    from lean_rgc.evals.uprime_u2_u4_development import emit_registered_artifacts
    artifact_sha256 = emit_registered_artifacts(repo_root=repo, source_commit=source_commit)
    expected = set(guard.CLOSEOUT_ARTIFACTS)
    if type(artifact_sha256) is not dict or set(artifact_sha256) != expected:
        raise RuntimeError("emitter returned the wrong artifact digest map")
    if any(type(value) is not str or len(value) != 64 or value.upper() != value for value in artifact_sha256.values()):
        raise RuntimeError("emitter returned a malformed artifact digest")
    payload = {"artifact_sha256": dict(sorted(artifact_sha256.items())), "tests_passed": 1}
    with open(receipt, "x", encoding="ascii", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n")
    raise SystemExit(0)

if lane == "CLOSEOUT":
    import hashlib
    common = [
        "schema_version", "evidence_scope", "source_commit", "observation_frame_id",
        "reachable_domain_id", "response_vocabulary_id", "transition_semantics_id",
        "domain_scope", "runtime_identity_sha256", "operator_tier", "operator_sha256",
        "coverage", "censors", "disposition", "payload",
    ]
    schemas = {
        "envelope_core.json": ("u24_envelope_core_v1", ["generator", "source_weights", "target_weights", "fiber_law", "transfer_layer", "completeness_witness", "inclusion_witness", "envelope", "verification_report"]),
        "maxent_fixture.json": ("u24_maxent_fixture_v1", ["support_token", "reference_law", "orbit_law", "statistics", "target", "kl_radius", "status", "probabilities", "residuals", "verification_report"]),
        "local_tower.json": ("u24_local_tower_v1", ["levels", "restrictions", "cauchy_majorant", "verification_report"]),
        "global_measure.json": ("u24_global_measure_v1", ["measures", "predictive_metric", "predictive_upper_bound", "positive_representation_distance", "safety_majorant", "verification_report"]),
        "level_transport.json": ("u24_level_transport_v1", ["radius_morphism", "word_depth_morphism", "granularity_morphism", "composition", "verification_report"]),
        "similarity_certificate.json": ("u24_similarity_certificate_v1", ["coverage", "target_residuals", "l_plus_token", "remainder_certificate", "verification_report"]),
        "integrated_certificate.json": ("u24_integrated_certificate_v1", ["candidate_manifest", "stages", "initial_residual", "hard_bound", "nominal_addendum", "total_bound", "coverage", "disposition", "verification_report"]),
    }
    observed = {}
    source_commits = set()
    for relative in guard.CLOSEOUT_ARTIFACTS:
        raw = (repo / relative).read_bytes()
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"closeout artifact is not strict UTF-8 JSON: {relative}") from exc
        name = pathlib.PurePosixPath(relative).name
        schema, payload_keys = schemas[name]
        if type(value) is not dict or list(value) != common:
            raise RuntimeError(f"closeout common artifact fields changed: {relative}")
        if value["schema_version"] != schema or type(value["payload"]) is not dict or list(value["payload"]) != payload_keys:
            raise RuntimeError(f"closeout artifact schema/payload fields changed: {relative}")
        if value["evidence_scope"] != "synthetic_development" or value["domain_scope"] != "declared_finite_totalized_snapshot_only":
            raise RuntimeError(f"closeout artifact scope promotion: {relative}")
        if value["runtime_identity_sha256"] != "D6E6DEBCE5C150AE31BA0D04EAF6E59FD2D79FDC4C0D5272264574665C0242F4":
            raise RuntimeError(f"closeout runtime identity changed: {relative}")
        if type(value["source_commit"]) is not str or value["source_commit"] != source_commit:
            raise RuntimeError(f"closeout source commit is malformed: {relative}")
        if type(value["operator_sha256"]) is not str or not __import__("re").fullmatch(r"[0-9A-F]{64}", value["operator_sha256"]):
            raise RuntimeError(f"closeout operator digest is malformed: {relative}")
        if json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("ascii") != raw:
            raise RuntimeError(f"closeout artifact is not canonical JSON: {relative}")
        source_commits.add(value["source_commit"])
        observed[relative] = hashlib.sha256(raw).hexdigest().upper()
    if len(observed) != 7 or any(len(value) != 64 for value in observed.values()):
        raise RuntimeError("closeout artifact validation is incomplete")
    if len(source_commits) != 1:
        raise RuntimeError("closeout artifacts do not share one source commit")
    if observed != expected_emit_map:
        raise RuntimeError("closeout artifact bytes differ from the official EMIT receipt")
    payload = {"artifact_sha256": None, "tests_passed": 1}
    with open(receipt, "x", encoding="ascii", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n")
    raise SystemExit(0)

os.environ[guard.PREINSTALLED_GUARD_ENV] = "1"

safe_type = type
safe_compile = compile
safe_ast_parse = ast.parse
safe_module_type = types.ModuleType
safe_module_getattribute = types.ModuleType.__getattribute__
safe_function_type = types.FunctionType
safe_function_getattribute = types.FunctionType.__getattribute__
safe_code_type = types.CodeType
safe_path_type = pathlib.Path
safe_path_resolve = pathlib.Path.resolve
e0_names = (
    "test_e0_exact_coordinate_generator_matches_frozen_independent_oracle",
    "test_e0_roundtrip_permutation_cancellation_and_terminal_rows",
    "test_e0_wire_and_source_attacks_fail_closed",
    "test_e0_capability_types_and_later_tiers_are_rejected",
    "test_e0_public_surface_has_no_later_tier_tokens",
    "test_read_only_bundle_cache_is_quarantined_from_mutation_tests",
    "test_e0_scope_fields_fail_closed_at_every_wire_layer",
    "test_e0_signed64_preflight_rejects_before_authority",
    "test_e0_source_type_is_checked_before_attribute_access",
)
e0_source_path = None
e0_source_resolved = None
e0_node_by_name = {}
e0_expected_codes = {}
e0_monkeypatch_type = None
if lane == "E0":
    import pytest as e0_pytest

    e0_monkeypatch_type = e0_pytest.MonkeyPatch
    e0_source_path = repo / "tests" / "test_odlrq_quotient_generator.py"
    e0_source_resolved = safe_path_resolve(e0_source_path)
    e0_source = e0_source_path.read_text(encoding="utf-8")
    e0_tree = safe_ast_parse(e0_source, filename=str(e0_source_path))
    e0_nodes = [
        node
        for node in e0_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in e0_names
    ]
    if (
        len(e0_nodes) != len(e0_names)
        or {node.name for node in e0_nodes} != set(e0_names)
        or any(
            isinstance(node, ast.AsyncFunctionDef) or node.decorator_list
            for node in e0_nodes
        )
    ):
        raise RuntimeError("E0 direct-call functions must be unique undecorated definitions")
    e0_node_by_name = {node.name: node for node in e0_nodes}
    e0_compiled = safe_compile(
        e0_source,
        str(e0_source_path),
        "exec",
        dont_inherit=True,
    )
    e0_expected_codes = {
        code.co_name: code
        for code in e0_compiled.co_consts
        if safe_type(code) is safe_code_type and code.co_name in e0_names
    }
    if set(e0_expected_codes) != set(e0_names):
        raise RuntimeError("E0 source code-object set changed")

if lane in {"B0", "E0"}:
    identity_path = repo / "tests" / "test_uprime_u2_u4_development.py"
    identity_spec = importlib.util.spec_from_file_location("u24_b0_identity", identity_path)
    if identity_spec is None or identity_spec.loader is None:
        raise RuntimeError("B0/E0 identity spec unavailable")
    identity = importlib.util.module_from_spec(identity_spec)
    identity_spec.loader.exec_module(identity)
    if safe_type(identity) is not safe_module_type:
        raise RuntimeError("B0/E0 identity module type changed")
    identity_dict = safe_module_getattribute(identity, "__dict__")
    if (
        "pytestmark" in identity_dict
        or "pytest_plugins" in identity_dict
        or identity_dict.get("__test__", True) is not True
    ):
        raise RuntimeError("B0/E0 identity module is marked, hidden, or plugin-modified")
    identity_names = (
        "test_u24_a0_anchor_authorities_and_nonexistence_are_frozen",
        "test_u24_b0_anchor_contiguous_budget_and_terminal_topology",
        "test_u24_denylist_static_scan_and_exact_runner_copy",
        "test_u24_autouse_guard_blocks_paths_process_network_and_dynamic_import",
        "test_u24_four_tier_public_wires_do_not_trust_tier_booleans",
    )
    discovered = tuple(
        sorted(name for name in identity_dict if name.startswith("test_u24_"))
    )
    if discovered != tuple(sorted(identity_names)):
        raise RuntimeError("B0/E0 identity function set changed")
    for name in identity_names:
        function = identity_dict.get(name)
        function_dict = (
            safe_function_getattribute(function, "__dict__")
            if safe_type(function) is safe_function_type
            else {}
        )
        function_code = (
            safe_function_getattribute(function, "__code__")
            if safe_type(function) is safe_function_type
            else None
        )
        if (
            safe_type(function) is not safe_function_type
            or function.__module__ != identity.__name__
            or function.__name__ != name
            or function.__qualname__ != name
            or "pytestmark" in function_dict
            or "__signature__" in function_dict
            or function_dict.get("__test__", True) is not True
            or function_dict.get("__wrapped__") is not None
            or function_code.co_argcount != 0
            or function_code.co_posonlyargcount != 0
            or function_code.co_kwonlyargcount != 0
            or function_code.co_flags & 0x2AC
            or safe_function_getattribute(function, "__defaults__") is not None
            or safe_function_getattribute(function, "__kwdefaults__") is not None
        ):
            raise RuntimeError(
                "B0/E0 identity functions must be undecorated zero-argument functions"
            )
        if function() is not None:
            raise RuntimeError("B0/E0 identity function returned a value")
    if lane == "B0":
        payload = {"artifact_sha256": None, "tests_passed": len(identity_names)}
        with open(receipt, "x", encoding="ascii", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n")
        raise SystemExit(0)

if lane == "E0":
    quotient = sys.modules.get("test_odlrq_quotient_generator")
    if safe_type(quotient) is not safe_module_type:
        raise RuntimeError("E0 quotient-generator test module was not imported by identity")
    quotient_dict = safe_module_getattribute(quotient, "__dict__")
    if (
        "pytestmark" in quotient_dict
        or "pytest_plugins" in quotient_dict
        or quotient_dict.get("__test__", True) is not True
    ):
        raise RuntimeError("E0 test module is marked, hidden, or plugin-modified")
    discovered_e0 = tuple(
        sorted(
            name
            for name in quotient_dict
            if name.startswith("test_e0_")
            or name == e0_names[5]
        )
    )
    if discovered_e0 != tuple(sorted(e0_names)):
        raise RuntimeError("E0 direct-call function set changed")

    passed = len(identity_names)
    for name in e0_names:
        function = quotient_dict.get(name)
        function_dict = (
            safe_function_getattribute(function, "__dict__")
            if safe_type(function) is safe_function_type
            else {}
        )
        function_code = (
            safe_function_getattribute(function, "__code__")
            if safe_type(function) is safe_function_type
            else None
        )
        if (
            safe_type(function) is not safe_function_type
            or function.__module__ != quotient.__name__
            or function.__name__ != name
            or function.__qualname__ != name
            or "pytestmark" in function_dict
            or "__signature__" in function_dict
            or function_dict.get("__test__", True) is not True
            or function_dict.get("__wrapped__") is not None
        ):
            raise RuntimeError("E0 direct-call function is marked, wrapped, or replaced")
        node = e0_node_by_name[name]
        if (
            function_code.co_name != name
            or function_code.co_firstlineno != node.lineno
            or safe_path_resolve(safe_path_type(function_code.co_filename))
            != e0_source_resolved
            or function_code != e0_expected_codes[name]
            or function.__globals__ is not quotient_dict
            or function.__closure__ is not None
        ):
            raise RuntimeError("E0 runtime function is not its frozen source definition")
        if (
            function_code.co_posonlyargcount != 0
            or function_code.co_kwonlyargcount != 0
            or function_code.co_flags & 0x2AC
            or function_code.co_argcount not in (0, 1)
            or (
                function_code.co_argcount == 1
                and function_code.co_varnames[0] != "monkeypatch"
            )
            or safe_function_getattribute(function, "__defaults__") is not None
            or safe_function_getattribute(function, "__kwdefaults__") is not None
        ):
            raise RuntimeError("E0 direct-call function parameterization changed")
        if function_code.co_argcount == 1:
            monkeypatch = e0_monkeypatch_type()
            try:
                result = function(monkeypatch)
            finally:
                monkeypatch.undo()
        else:
            result = function()
        if result is not None:
            raise RuntimeError("E0 direct-call function returned a value")
        passed += 1
    if passed != 14:
        raise RuntimeError("E0 direct-call receipt count changed")
    payload = {"artifact_sha256": None, "tests_passed": 14}
    with open(receipt, "x", encoding="ascii", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n")
    raise SystemExit(0)

class Audit:
    def __init__(self):
        self.passed = 0
        self.skipped = 0
        self.xfailed = 0
        self.deselected = 0
    def pytest_runtest_logreport(self, report):
        if getattr(report, "wasxfail", None) is not None:
            self.xfailed += 1
        elif report.skipped:
            self.skipped += 1
        elif report.when == "call" and report.passed:
            self.passed += 1
    def pytest_collectreport(self, report):
        if report.skipped:
            self.skipped += 1
    def pytest_deselected(self, items):
        self.deselected += len(items)

import pytest
audit = Audit()
tests = json.loads(os.environ.pop("UPRIME_U24_TESTS"))
code = int(pytest.main([
    "-q", "-p", "no:cacheprovider",
    "--ignore=" + "tests/test_uprime_" + "official_transport_v2_smoke.py",
    *tests,
], plugins=[audit]))
if code == 0 and (audit.passed <= 0 or audit.skipped or audit.xfailed or audit.deselected):
    code = 66
payload = {"artifact_sha256": None, "tests_passed": audit.passed}
with open(receipt, "x", encoding="ascii", newline="\n") as handle:
    handle.write(json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n")
raise SystemExit(code)
'@
    [IO.File]::WriteAllText($bootstrapPath, $bootstrap, [Text.UTF8Encoding]::new($false))

    $jobSource = @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
public static class U24Job {
  [StructLayout(LayoutKind.Sequential)] public struct Basic { public long PerProcessUserTimeLimit, PerJobUserTimeLimit; public uint LimitFlags; public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize; public uint ActiveProcessLimit; public IntPtr Affinity; public uint PriorityClass, SchedulingClass; }
  [StructLayout(LayoutKind.Sequential)] public struct IO { public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount, ReadTransferCount, WriteTransferCount, OtherTransferCount; }
  [StructLayout(LayoutKind.Sequential)] public struct Extended { public Basic BasicLimitInformation; public IO IoInfo; public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed; }
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern IntPtr CreateJobObject(IntPtr a, string n);
  [DllImport("kernel32.dll", SetLastError=true)] static extern bool SetInformationJobObject(IntPtr h, int c, IntPtr p, uint l);
  [DllImport("kernel32.dll", SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr h, int c, IntPtr p, uint l, out uint used);
  [DllImport("kernel32.dll", SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr h, IntPtr p);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern bool TerminateJobObject(IntPtr h, uint code);
  [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);
  public static IntPtr Create(ulong bytes) { IntPtr h=CreateJobObject(IntPtr.Zero,null); if(h==IntPtr.Zero) throw new System.ComponentModel.Win32Exception(); Extended x=new Extended(); x.BasicLimitInformation.LimitFlags=0x8u|0x100u|0x200u|0x2000u; x.BasicLimitInformation.ActiveProcessLimit=1; x.ProcessMemoryLimit=(UIntPtr)bytes; x.JobMemoryLimit=(UIntPtr)bytes; int s=Marshal.SizeOf(typeof(Extended)); IntPtr m=Marshal.AllocHGlobal(s); try { Marshal.StructureToPtr(x,m,false); if(!SetInformationJobObject(h,9,m,(uint)s)) throw new System.ComponentModel.Win32Exception(); return h; } catch { CloseHandle(h); throw; } finally { Marshal.FreeHGlobal(m); } }
  public static bool StartAssigned(Process p, IntPtr j, int ms) { Task<bool> t=Task.Run(()=>{ if(!p.Start()) return false; if(!AssignProcessToJobObject(j,p.Handle)){try{p.Kill();}catch{} throw new System.ComponentModel.Win32Exception();} return true;}); if(!t.Wait(ms)){t.ContinueWith(_=>{try{if(!p.HasExited)p.Kill();}catch{}},TaskScheduler.Default);return false;} return t.GetAwaiter().GetResult(); }
  public static ulong Peak(IntPtr h) { int s=Marshal.SizeOf(typeof(Extended)); IntPtr m=Marshal.AllocHGlobal(s); try { uint used; if(!QueryInformationJobObject(h,9,m,(uint)s,out used)) throw new System.ComponentModel.Win32Exception(); return ((Extended)Marshal.PtrToStructure(m,typeof(Extended))).PeakJobMemoryUsed.ToUInt64(); } finally { Marshal.FreeHGlobal(m); } }
}
'@
    if ($null -eq ("U24Job" -as [type])) { Add-Type -TypeDefinition $jobSource -Language CSharp }
    $job = [U24Job]::Create($MemoryLimitBytes)

    $childPycachePrefix = Join-Path $runTemp "child-pycache"
    if (Test-Path -LiteralPath $childPycachePrefix) { throw "child pycache prefix is not empty" }
    $arguments = @("-I", "-S", "-X", "pycache_prefix=$childPycachePrefix", $bootstrapPath)
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $pythonPath
    $startInfo.Arguments = (($arguments | ForEach-Object { Quote-NativeArgument $_ }) -join " ")
    $startInfo.WorkingDirectory = $repoRoot
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.EnvironmentVariables.Clear()
    $environment = [ordered]@{
        COMSPEC = [IO.Path]::GetFullPath($env:ComSpec); LANG = "C.UTF-8"; LC_ALL = "C.UTF-8"
        PATH = ([IO.Path]::GetDirectoryName($pythonPath) + ";" + (Join-Path $env:SystemRoot "System32"))
        PYTHONDONTWRITEBYTECODE = "1"; PYTHONIOENCODING = "utf-8"; PYTHONUTF8 = "1"
        PYTEST_ADDOPTS = ""; PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"; PYTEST_PLUGINS = ""
        SYSTEMROOT = [IO.Path]::GetFullPath($env:SystemRoot); TEMP = $runTemp; TMP = $runTemp
        USERPROFILE = [IO.Path]::GetFullPath($env:USERPROFILE); WINDIR = [IO.Path]::GetFullPath($env:SystemRoot)
        OMP_NUM_THREADS = "1"; OPENBLAS_NUM_THREADS = "1"; MKL_NUM_THREADS = "1"; NUMEXPR_NUM_THREADS = "1"
        UPRIME_U24_ARM = $armPath; UPRIME_U24_REPO = $repoRoot; UPRIME_U24_USER_SITE = $userSite
        UPRIME_U24_LANE = $Lane
        UPRIME_U24_DENYLIST = $DenylistCanonicalJson; UPRIME_U24_CONTROL = $controlEncoded
        UPRIME_U24_CHILD_RECEIPT = $childReceiptPath
        UPRIME_U24_TESTS = (ConvertTo-Json -InputObject @($tests) -Compress)
        UPRIME_U24_NUMPY_VERSION = $ExpectedNumpyVersion
        UPRIME_U24_MULTIARRAY = $multiarrayPath; UPRIME_U24_LINALG = $linalgPath
        UPRIME_U24_OPENBLAS = $openBlasPath
        UPRIME_U24_SOURCE_COMMIT = $headCommit
        UPRIME_U24_EXPECTED_EMIT_MAP = $expectedEmitMapJson
        UPRIME_U24_RUNTIME_IDENTITY_SHA256 = $RuntimeIdentitySha256
    }
    foreach ($pair in $environment.GetEnumerator()) { $startInfo.EnvironmentVariables[$pair.Key] = [string]$pair.Value }

    $pythonProcess = [Diagnostics.Process]::new(); $pythonProcess.StartInfo = $startInfo
    $wallSeconds = [int64]$Walls[$Lane]
    $wallTicks = [int64]($wallSeconds * $StopwatchFrequency)
    $qualificationTicks = [int64]($wallTicks / 3)
    $stopwatch = [Diagnostics.Stopwatch]::StartNew()
    if (-not [U24Job]::StartAssigned($pythonProcess, $job, [int]($wallSeconds * 1000))) { throw "failed to start Job-assigned child" }
    $stdoutStream = [IO.FileStream]::new($stdoutPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    $stderrStream = [IO.FileStream]::new($stderrPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    $stdoutTask = $pythonProcess.StandardOutput.BaseStream.CopyToAsync($stdoutStream)
    $stderrTask = $pythonProcess.StandardError.BaseStream.CopyToAsync($stderrStream)
    [IO.File]::WriteAllText($armPath, "ARM`n", [Text.Encoding]::ASCII)
    $failure = $null; $peak = [uint64]0
    while (-not $pythonProcess.HasExited) {
        Start-Sleep -Milliseconds 20
        if ((Get-CapturedBytes @($stdoutPath, $stderrPath)) -ge $OutputLimitBytes) { $failure = "output"; break }
        if ($stopwatch.ElapsedTicks -gt $wallTicks) { $failure = "timeout"; break }
    }
    if ($null -ne $failure -and -not $pythonProcess.HasExited) {
        [void][U24Job]::TerminateJobObject($job, 1)
    }
    if (-not $pythonProcess.HasExited) { [void]$pythonProcess.WaitForExit(2000) }
    if ($null -ne $stdoutTask) { try { [void]$stdoutTask.GetAwaiter().GetResult() } catch { } }
    if ($null -ne $stderrTask) { try { [void]$stderrTask.GetAwaiter().GetResult() } catch { } }
    $stdoutStream.Flush($true); $stdoutStream.Dispose(); $stdoutStream = $null
    $stderrStream.Flush($true); $stderrStream.Dispose(); $stderrStream = $null
    $stopwatch.Stop()
    if ($job -ne [IntPtr]::Zero) { try { $peak = [Math]::Max($peak, [U24Job]::Peak($job)) } catch { } }
    $elapsedTicks = [int64]$stopwatch.ElapsedTicks
    $captured = Get-CapturedBytes @($stdoutPath, $stderrPath)
    $processExit = if ($pythonProcess.HasExited) { [int]$pythonProcess.ExitCode } else { $ExitTimeout }
    if ($null -eq $failure -and $peak -ge $MemoryLimitBytes) { $failure = "memory" }
    if ($null -eq $failure -and $captured -ge $OutputLimitBytes) { $failure = "output" }
    if ($null -eq $failure -and $elapsedTicks -gt $wallTicks) { $failure = "timeout" }

    if ($failure -eq "timeout") { Write-RunnerError "hard wall exceeded"; $exitCode = $ExitTimeout }
    elseif ($failure -eq "memory") { Write-RunnerError "2-GiB Job memory cap reached"; $exitCode = $ExitMemory }
    elseif ($failure -eq "output") { Write-RunnerError "64-MiB output cap reached"; $exitCode = $ExitOutput }
    elseif ($processExit -ne 0) {
        if (Test-Path $stderrPath) { [Console]::Error.Write([IO.File]::ReadAllText($stderrPath)) }
        if (Test-Path $stdoutPath) { [Console]::Error.Write([IO.File]::ReadAllText($stdoutPath)) }
        $exitCode = if ($processExit -eq $ExitNoTests) { $ExitNoTests } else { $processExit }
    }
    elseif ($elapsedTicks -gt $qualificationTicks) {
        Write-RunnerError "three-times cold-margin requirement failed"
        $exitCode = $ExitQualificationMargin
    }
    else {
        if (-not (Test-Path -LiteralPath $childReceiptPath -PathType Leaf)) { throw "child receipt missing" }
        $child = [IO.File]::ReadAllText($childReceiptPath, [Text.UTF8Encoding]::new($false, $true)) | ConvertFrom-Json
        if ($child.tests_passed -isnot [int] -and $child.tests_passed -isnot [long]) { throw "test count malformed" }
        if ([int64]$child.tests_passed -le 0) { throw "child receipt semantics malformed" }
        $artifactReceipt = $null
        if ($Lane -eq "EMIT") {
            if ($null -eq $child.artifact_sha256) { throw "EMIT artifact digest map is missing" }
            $names = @($child.artifact_sha256.PSObject.Properties.Name | Sort-Object)
            if ($names.Count -ne 7) { throw "EMIT artifact digest map has the wrong cardinality" }
            $artifactReceipt = [Collections.Generic.SortedDictionary[string,string]]::new([StringComparer]::Ordinal)
            foreach ($name in $names) {
                $value = [string]$child.artifact_sha256.$name
                if ($value -cnotmatch '^[0-9A-F]{64}$') { throw "EMIT artifact digest is malformed" }
                $artifactReceipt[$name] = $value
            }
            $controlReceipt = [ordered]@{
                schema_version = "u24-emit-control-receipt-v1"
                source_commit = $headCommit
                artifact_sha256 = $artifactReceipt
            }
            $controlBytes = [Text.UTF8Encoding]::new($false).GetBytes(
                ($controlReceipt | ConvertTo-Json -Compress -Depth 8)
            )
            $controlStream = [IO.FileStream]::new(
                $emitReceiptPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write,
                [IO.FileShare]::None, 4096, [IO.FileOptions]::WriteThrough
            )
            try { $controlStream.Write($controlBytes, 0, $controlBytes.Length); $controlStream.Flush($true) }
            finally { $controlStream.Dispose() }
        }
        elseif ($null -ne $child.artifact_sha256) { throw "non-EMIT artifact digest must be null" }
        $commit = $headCommit
        $receipt = [ordered]@{
            schema_version = $ReceiptSchema; lane = $Lane; commit = $commit
            tests_passed = [int64]$child.tests_passed; wall_ticks = $elapsedTicks
            clock_frequency = $StopwatchFrequency; peak_job_memory_bytes = [uint64]$peak
            output_bytes = [int64]$captured; artifact_sha256 = $artifactReceipt
            disposition = $Dispositions[$Lane]
        }
        [Console]::Out.WriteLine(($receipt | ConvertTo-Json -Compress -Depth 8))
        $exitCode = 0
    }
}
catch [System.Management.Automation.CommandNotFoundException] {
    Write-RunnerError $_.Exception.Message; $exitCode = $ExitPythonUnavailable
}
catch {
    Write-RunnerError $_.Exception.Message; $exitCode = $ExitInternalError
}
finally {
    if ($null -ne $stdoutStream) { try { $stdoutStream.Dispose() } catch { } }
    if ($null -ne $stderrStream) { try { $stderrStream.Dispose() } catch { } }
    if ($job -ne [IntPtr]::Zero) {
        if ($null -ne $pythonProcess -and -not $pythonProcess.HasExited) {
            try { [void][U24Job]::TerminateJobObject($job, 1) } catch { }
        }
        try { [void][U24Job]::CloseHandle($job) } catch { }
    }
    if ($null -ne $pythonProcess) { try { $pythonProcess.Dispose() } catch { } }
    if ($null -ne $runTemp -and $null -ne $systemTemp -and (Test-Path -LiteralPath $runTemp)) {
        $resolvedTemp = [IO.Path]::GetFullPath($runTemp)
        $expectedPrefix = $systemTemp + [IO.Path]::DirectorySeparatorChar + "lean-rgc-u24-"
        if ($resolvedTemp.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $resolvedTemp -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}
exit $exitCode
