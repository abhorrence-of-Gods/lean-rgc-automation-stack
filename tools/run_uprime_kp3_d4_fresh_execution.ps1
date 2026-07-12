[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [object[]] $UnexpectedArguments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ExitUsage = 64
$ExitPreflight = 65
$ExitPythonUnavailable = 69
$ExitInternalError = 70
$ExitTimeout = 124
$ExitWorkingSet = 137
$ExitOutputLimit = 138
$WholeRunWallSeconds = 3600.0
$PerActionWallSeconds = 30.0
$WorkingSetLimitBytes = [uint64]2 * 1024 * 1024 * 1024
$OutputLimitBytes = [int64]64 * 1024 * 1024
$RowLimit = 12288
$TempPrefix = "lean-rgc-uprime-kp3-d4-official-"

$ExpectedPowerShellVersion = "5.1.26100.8655"
$ExpectedPowerShellSha256 = "0FF6F2C94BC7E2833A5F7E16DE1622E5DBA70396F31C7D5F56381870317E8C46"
$ExpectedPythonVersion = "3.13.7"
$ExpectedPythonSha256 = "D932E5E2F324D57F392E8FD063DCF6D0185BE8A664C57C6D24E7762ED02C28CA"
$ExpectedLeanVersion = "4.31.0"
$ExpectedLeanCommit = "68218e876d2a38b1985b8590fff244a83c321783"
$ExpectedLeanSha256 = "9B216DEB50D37C32C829D1EFAAA5BAFD5560417D382DF35A815489E31A31593F"
$ExpectedWorkerBlob = "305509d9b89081a3d002734e09724b98e244a24c"
$ExpectedClientBlob = "ef5d81bff4c6ab4d8110fe6671f5e5b5f8bc263a"
$ExpectedTaskSha256 = "C0B5428DCB7174CB96F469E38E229043AF47B9E9ECF684797FF45EE8AE4163A0"
$ExpectedTaskCanonicalSha256 = "814BFBC235B6E464013637210E1C5382B0CED5AEB0C8D50C9C282E3236202D62"
$ExpectedActionSha256 = "FC9FB44E8E5D6929712CE15DC2D6F93FCCA74B81EE99C9EAF55D13B76A0CCF51"
$ExpectedActionCanonicalSha256 = "BE4AC0348631D0D7E3ABCA3DD22A05240E1D86B494B21FDBB47EF7FADA99FB1A"
$ArtifactSchema = "lean-rgc-uprime-kp3-d4-fresh-family-v1.0"
$ReceiptSchema = "lean-rgc-uprime-kp3-d4-stage-receipt-v1.0"
$ControlAttestationScope = "EXTERNAL_CI_ATTESTATION_UNVERIFIED_BY_RUNNER"
$OfficialArtifactFields = @(
    "action_input_canonical_sha256", "action_input_sha256",
    "c2_accepted_job_id", "c2_accepted_run_id", "c2_allowlist_file_sha256",
    "c2_candidate_job_id", "c2_candidate_run_id", "c2_commit",
    "c2_control_attestation_scope", "c2_file_digest_match", "c2_tree", "conditioning",
    "conditioning_censor", "environment_digest", "failure_reason",
    "lean_binary_sha256", "lean_commit", "lean_version", "matrix",
    "native_worker_blob", "platform_record", "powershell_executable_sha256",
    "python_executable_sha256", "rank", "rpc_client_blob", "run_state",
    "schema_version", "scientific_disposition", "task_input_canonical_sha256",
    "task_input_sha256"
)

function Write-RunnerError {
    param([Parameter(Mandatory = $true)][string] $Message)
    [Console]::Error.WriteLine("uprime-kp3-d4-fresh-execution: {0}", $Message)
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
        throw "resolved file escaped its required root: $LiteralPath"
    }
    return $resolved
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string] $LiteralPath)
    return (Get-FileHash -LiteralPath $LiteralPath -Algorithm SHA256).Hash.ToUpperInvariant()
}

function Get-GitBlobOid {
    param([Parameter(Mandatory = $true)][string] $LiteralPath)
    $raw = [IO.File]::ReadAllBytes($LiteralPath)
    $prefix = [Text.Encoding]::ASCII.GetBytes("blob $($raw.LongLength)`0")
    $framed = [byte[]]::new($prefix.Length + $raw.Length)
    [Array]::Copy($prefix, 0, $framed, 0, $prefix.Length)
    [Array]::Copy($raw, 0, $framed, $prefix.Length, $raw.Length)
    $sha1 = [Security.Cryptography.SHA1]::Create()
    try { return ([BitConverter]::ToString($sha1.ComputeHash($framed))).Replace("-", "").ToLowerInvariant() }
    finally { $sha1.Dispose() }
}

function Get-Sha256Text {
    param([Parameter(Mandatory = $true)][string] $Text)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $raw = [Text.UTF8Encoding]::new($false).GetBytes($Text)
        return ([BitConverter]::ToString($sha.ComputeHash($raw))).Replace("-", "").ToUpperInvariant()
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

function Write-CapturedStream {
    param(
        [Parameter(Mandatory = $true)][string] $LiteralPath,
        [Parameter(Mandatory = $true)][ValidateSet("stdout", "stderr")][string] $Stream
    )
    if (-not (Test-Path -LiteralPath $LiteralPath -PathType Leaf)) { return }
    if ((Get-Item -LiteralPath $LiteralPath -Force).Length -ge $OutputLimitBytes) { return }
    $text = [IO.File]::ReadAllText($LiteralPath, [Text.Encoding]::UTF8)
    if ($Stream -eq "stdout") { [Console]::Out.Write($text) }
    else { [Console]::Error.Write($text) }
}

function Write-DurableExclusiveUtf8 {
    param(
        [Parameter(Mandatory = $true)][string] $LiteralPath,
        [Parameter(Mandatory = $true)][string] $Text
    )
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes($Text)
    $stream = [IO.FileStream]::new(
        $LiteralPath,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write,
        [IO.FileShare]::None,
        4096,
        [IO.FileOptions]::WriteThrough
    )
    try {
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    }
    finally { $stream.Dispose() }
}

function Flush-DurableFile {
    param([Parameter(Mandatory = $true)][string] $LiteralPath)
    $stream = [IO.FileStream]::new(
        $LiteralPath,
        [IO.FileMode]::Open,
        [IO.FileAccess]::ReadWrite,
        [IO.FileShare]::Read,
        4096,
        [IO.FileOptions]::WriteThrough
    )
    try { $stream.Flush($true) }
    finally { $stream.Dispose() }
}

function Read-StrictUtf8File {
    param(
        [Parameter(Mandatory = $true)][string] $LiteralPath,
        [Parameter(Mandatory = $true)][int64] $MaximumBytes,
        [switch] $ReturnText
    )
    $item = Get-Item -LiteralPath $LiteralPath -Force
    if ($item.PSIsContainer -or (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) -or
        $item.Length -le 0 -or $item.Length -ge $MaximumBytes) {
        throw "strict UTF-8 file is empty, reparse, or outside its byte cap: $LiteralPath"
    }
    $encoding = [Text.UTF8Encoding]::new($false, $true)
    $stream = [IO.FileStream]::new($LiteralPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $reader = [IO.StreamReader]::new($stream, $encoding, $false, 65536, $false)
    try {
        if ($ReturnText) { return $reader.ReadToEnd() }
        $buffer = [char[]]::new(65536)
        while ($reader.ReadBlock($buffer, 0, $buffer.Length) -gt 0) { }
        return $null
    }
    finally { $reader.Dispose(); $stream.Dispose() }
}

function Install-ParentResourceArtifact {
    param(
        [Parameter(Mandatory = $true)][Collections.Generic.SortedDictionary[string,object]] $Marker,
        [Parameter(Mandatory = $true)][string] $FailureReason,
        [Parameter(Mandatory = $true)][string] $FailureStagePath,
        [Parameter(Mandatory = $true)][string] $FinalPath
    )
    $value = [Collections.Generic.SortedDictionary[string,object]]::new([StringComparer]::Ordinal)
    foreach ($pair in $Marker.GetEnumerator()) { $value[$pair.Key] = $pair.Value }
    $value["failure_reason"] = $FailureReason
    $value["run_state"] = "ORDINARY_RESULT_COMMITTED"
    $value["scientific_disposition"] = "D4_RESOURCE_BLOCKED"
    $json = ($value | ConvertTo-Json -Compress -Depth 12)
    Write-DurableExclusiveUtf8 -LiteralPath $FailureStagePath -Text $json
    [UPrimeKP3D4Job]::DurableReplace($FailureStagePath, $FinalPath)
    Flush-DurableFile -LiteralPath $FinalPath
}

$unboundCount = if ($null -eq $MyInvocation.UnboundArguments) { 0 } else { @($MyInvocation.UnboundArguments).Count }
$unexpectedCount = if ($null -eq $UnexpectedArguments) { 0 } else { @($UnexpectedArguments).Count }
if ($PSBoundParameters.Count -ne 0 -or $unboundCount -ne 0 -or $unexpectedCount -ne 0) {
    Write-RunnerError "arguments are forbidden"
    exit $ExitUsage
}

$runTemp = $null
$pythonProcess = $null
$job = [IntPtr]::Zero
$stdoutPath = $null
$stderrPath = $null
$stdoutStream = $null
$stderrStream = $null
$stdoutCopyTask = $null
$stderrCopyTask = $null
$stagePath = $null
$receiptPath = $null
$failureStagePath = $null
$markerOpened = $false
$resultInstalled = $false
$exitCode = $ExitInternalError

try {
    if ($env:OS -ne "Windows_NT" -or -not [Environment]::Is64BitOperatingSystem -or
        -not [Environment]::Is64BitProcess -or
        [Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString() -cne "X64") {
        throw "official execution requires a 64-bit Windows x86-64 parent"
    }
    if ($PSVersionTable.PSEdition -cne "Desktop" -or $PSVersionTable.PSVersion.ToString() -cne $ExpectedPowerShellVersion) {
        throw "Windows PowerShell parent version is not frozen identity"
    }
    $powerShellPath = [IO.Path]::GetFullPath((Join-Path $PSHOME "powershell.exe"))
    if ((Get-Sha256 -LiteralPath $powerShellPath) -cne $ExpectedPowerShellSha256) {
        throw "Windows PowerShell executable digest changed"
    }
    if ([string]::IsNullOrWhiteSpace($PSCommandPath)) { throw "script path is unavailable" }
    $scriptPath = Resolve-RegularFile -LiteralPath $PSCommandPath -RequiredRoot (Split-Path -Parent $PSCommandPath)
    $toolsPath = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Split-Path -Parent $scriptPath)).ProviderPath)
    $repoRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Join-Path $toolsPath "..")).ProviderPath)
    $expectedScript = [IO.Path]::GetFullPath((Join-Path $repoRoot "tools\run_uprime_kp3_d4_fresh_execution.ps1"))
    if (-not $scriptPath.Equals($expectedScript, [StringComparison]::OrdinalIgnoreCase)) {
        throw "runner path does not match its canonical repository location"
    }
    foreach ($marker in @(".git", "pyproject.toml", "lean_rgc", "tests")) {
        if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $marker))) { throw "repository marker is missing: $marker" }
    }

    $controlNames = @(
        "UPRIME_KP3_D4_C2_COMMIT", "UPRIME_KP3_D4_C2_TREE",
        "UPRIME_KP3_D4_C2_CANDIDATE_RUN_ID", "UPRIME_KP3_D4_C2_CANDIDATE_JOB_ID",
        "UPRIME_KP3_D4_C2_ACCEPTED_RUN_ID", "UPRIME_KP3_D4_C2_ACCEPTED_JOB_ID"
    )
    $control = [ordered]@{}
    foreach ($name in $controlNames) {
        $value = [Environment]::GetEnvironmentVariable($name, "Process")
        if ([string]::IsNullOrWhiteSpace($value)) { throw "missing fixed control-plane attestation: $name" }
        if ($name.EndsWith("COMMIT") -or $name.EndsWith("TREE")) {
            if ($value -cnotmatch '^[0-9a-f]{40}$') { throw "malformed fixed control-plane hex attestation: $name" }
        }
        elseif ($value -cnotmatch '^[1-9][0-9]*$') { throw "malformed fixed control-plane numeric attestation: $name" }
        $control[$name] = $value
    }
    $expectedC2FileDigestsJson = [Environment]::GetEnvironmentVariable(
        "UPRIME_KP3_D4_C2_EXPECTED_FILE_DIGESTS_JSON", "Process"
    )
    if ([string]::IsNullOrWhiteSpace($expectedC2FileDigestsJson) -or
        $expectedC2FileDigestsJson.Length -ge 4096) {
        throw "missing or oversized external C2 file-digest attestation"
    }

    $pythonPath = [IO.Path]::GetFullPath("C:\Python313\python.exe")
    $pythonPath = Resolve-RegularFile -LiteralPath $pythonPath -RequiredRoot "C:\Python313"
    $pythonVersionInfo = (Get-Item -LiteralPath $pythonPath -Force).VersionInfo
    if ($pythonVersionInfo.FileVersion -cne $ExpectedPythonVersion -or
        (Get-Sha256 -LiteralPath $pythonPath) -cne $ExpectedPythonSha256) {
        throw "Python identity changed"
    }
    $leanRoot = [IO.Path]::GetFullPath((Join-Path $env:USERPROFILE ".elan\toolchains\leanprover--lean4---v4.31.0"))
    $leanPath = Resolve-RegularFile -LiteralPath (Join-Path $leanRoot "bin\lean.exe") -RequiredRoot $leanRoot
    if ((Get-Sha256 -LiteralPath $leanPath) -cne $ExpectedLeanSha256) { throw "Lean executable digest changed" }
    $workerPath = Resolve-RegularFile -LiteralPath (Join-Path $repoRoot "lean_rgc\native_lean\RGCKernelRPC.lean") -RequiredRoot $repoRoot
    $clientPath = Resolve-RegularFile -LiteralPath (Join-Path $repoRoot "lean_rgc\lean\kernel_rpc_client.py") -RequiredRoot $repoRoot
    if ((Get-GitBlobOid -LiteralPath $workerPath) -cne $ExpectedWorkerBlob) { throw "native worker blob changed" }
    if ((Get-GitBlobOid -LiteralPath $clientPath) -cne $ExpectedClientBlob) { throw "RPC client blob changed" }

    $inputRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Join-Path $repoRoot "docs\experiments\inputs")).ProviderPath)
    $taskPath = Resolve-RegularFile -LiteralPath (Join-Path $inputRoot "uprime_kp3_d4_fresh_tasks.json") -RequiredRoot $inputRoot
    $actionPath = Resolve-RegularFile -LiteralPath (Join-Path $inputRoot "uprime_kp3_d4_actions.json") -RequiredRoot $inputRoot
    if ((Get-Sha256 -LiteralPath $taskPath) -cne $ExpectedTaskSha256) { throw "registered task input digest changed" }
    if ((Get-Sha256 -LiteralPath $actionPath) -cne $ExpectedActionSha256) { throw "registered action input digest changed" }

    $c2Allowlist = @(
        "lean_rgc/evals/uprime_kp3_d4_canonical_history.py",
        "tests/test_uprime_kp3_d4_canonical_history.py",
        "tools/run_uprime_kp3_d4_native_tests.ps1",
        "tools/run_uprime_kp3_d4_fresh_execution.ps1",
        "tests/tier_manifest.json"
    )
    $c2FileDigests = [Collections.Generic.SortedDictionary[string,object]]::new([StringComparer]::Ordinal)
    foreach ($relative in $c2Allowlist) {
        $candidate = Resolve-RegularFile -LiteralPath (Join-Path $repoRoot $relative) -RequiredRoot $repoRoot
        $c2FileDigests[$relative] = Get-Sha256 -LiteralPath $candidate
    }
    if ($c2FileDigests.Count -ne 5) { throw "C2 allowlist identity must contain exactly five files" }
    $c2FileDigestsJson = ($c2FileDigests | ConvertTo-Json -Compress)
    try { $expectedC2FileDigests = $expectedC2FileDigestsJson | ConvertFrom-Json }
    catch { throw "external C2 file-digest attestation is not strict parseable JSON" }
    $expectedDigestNames = @($expectedC2FileDigests.PSObject.Properties.Name | Sort-Object)
    if (($expectedDigestNames -join "`n") -cne (($c2Allowlist | Sort-Object) -join "`n")) {
        throw "external C2 file-digest attestation has the wrong path set"
    }
    $expectedDigestCanonical = [Collections.Generic.SortedDictionary[string,object]]::new([StringComparer]::Ordinal)
    foreach ($relative in $c2Allowlist) {
        $digest = $expectedC2FileDigests.$relative
        if ($digest -isnot [string] -or $digest -cnotmatch '^[0-9A-F]{64}$') {
            throw "external C2 file-digest attestation contains a malformed digest"
        }
        $expectedDigestCanonical[$relative] = $digest
    }
    if (($expectedDigestCanonical | ConvertTo-Json -Compress) -cne $expectedC2FileDigestsJson) {
        throw "external C2 file-digest attestation is duplicate or noncanonical"
    }
    if ($expectedC2FileDigestsJson -cne $c2FileDigestsJson) {
        throw "external accepted-tree C2 file digests differ from working files"
    }
    $fixedIdentity = [Collections.Generic.SortedDictionary[string,string]]::new([StringComparer]::Ordinal)
    $fixedIdentity["action_input_canonical_sha256"] = $ExpectedActionCanonicalSha256
    $fixedIdentity["action_input_sha256"] = $ExpectedActionSha256
    $fixedIdentity["lean_binary_sha256"] = $ExpectedLeanSha256
    $fixedIdentity["lean_commit"] = $ExpectedLeanCommit
    $fixedIdentity["lean_version"] = $ExpectedLeanVersion
    $fixedIdentity["native_worker_blob"] = $ExpectedWorkerBlob
    $fixedIdentity["powershell_executable_sha256"] = $ExpectedPowerShellSha256
    $fixedIdentity["python_executable_sha256"] = $ExpectedPythonSha256
    $fixedIdentity["rpc_client_blob"] = $ExpectedClientBlob
    $fixedIdentity["task_input_canonical_sha256"] = $ExpectedTaskCanonicalSha256
    $fixedIdentity["task_input_sha256"] = $ExpectedTaskSha256
    $fixedIdentityDigest = Get-Sha256Text -Text ($fixedIdentity | ConvertTo-Json -Compress)

    $artifactDirectory = [IO.Path]::GetFullPath((Join-Path $repoRoot "docs\experiments\artifacts\uprime_kp3_d4_20260712"))
    if (-not (Test-Path -LiteralPath $artifactDirectory)) { [void][IO.Directory]::CreateDirectory($artifactDirectory) }
    $artifactDirectory = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $artifactDirectory).ProviderPath)
    $resultPath = [IO.Path]::GetFullPath((Join-Path $artifactDirectory "fresh_family_d4.json"))
    $stageNonce = [Guid]::NewGuid().ToString("N")
    $stagePath = [IO.Path]::GetFullPath((Join-Path $artifactDirectory ("fresh_family_d4.json.stage." + $stageNonce)))
    $receiptPath = [IO.Path]::GetFullPath((Join-Path $artifactDirectory ("fresh_family_d4.json.receipt." + $stageNonce)))
    $failureStagePath = [IO.Path]::GetFullPath((Join-Path $artifactDirectory ("fresh_family_d4.json.parent-resource." + $stageNonce)))
    if (Test-Path -LiteralPath $resultPath) { throw "RUN_OPENED marker or result already exists; official rerun is permanently denied" }
    foreach ($ownedPath in @($stagePath, $receiptPath, $failureStagePath)) {
        if (Test-Path -LiteralPath $ownedPath) { throw "unpredictable parent-owned output path already exists" }
    }

    $systemRoot = [IO.Path]::GetFullPath($env:SystemRoot)
    $comspec = [IO.Path]::GetFullPath($env:ComSpec)
    $systemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd("\", "/")
    $runTemp = [IO.Path]::GetFullPath((Join-Path $systemTemp ($TempPrefix + [Guid]::NewGuid().ToString("N"))))
    if (-not ([IO.Path]::GetFullPath((Split-Path -Parent $runTemp)).TrimEnd("\", "/")).Equals($systemTemp, [StringComparison]::OrdinalIgnoreCase)) {
        throw "owned temporary directory escaped the system temp root"
    }
    [void][IO.Directory]::CreateDirectory($runTemp)
    $stdoutPath = Join-Path $runTemp "official.stdout.txt"
    $stderrPath = Join-Path $runTemp "official.stderr.txt"
    $bootstrapPath = Join-Path $runTemp "official_child.py"
    $armPath = Join-Path $runTemp "official.arm"

    $platformRecord = "Windows_NT|X64|64-bit|PowerShell-$ExpectedPowerShellVersion"
    $markerValue = [ordered]@{
        action_input_canonical_sha256 = $ExpectedActionCanonicalSha256
        action_input_sha256 = $ExpectedActionSha256
        c2_accepted_job_id = $control["UPRIME_KP3_D4_C2_ACCEPTED_JOB_ID"]
        c2_accepted_run_id = $control["UPRIME_KP3_D4_C2_ACCEPTED_RUN_ID"]
        c2_allowlist_file_sha256 = $c2FileDigests
        c2_candidate_job_id = $control["UPRIME_KP3_D4_C2_CANDIDATE_JOB_ID"]
        c2_candidate_run_id = $control["UPRIME_KP3_D4_C2_CANDIDATE_RUN_ID"]
        c2_commit = $control["UPRIME_KP3_D4_C2_COMMIT"]
        c2_control_attestation_scope = $ControlAttestationScope
        c2_file_digest_match = $true
        c2_tree = $control["UPRIME_KP3_D4_C2_TREE"]
        conditioning = $null
        conditioning_censor = "NOT_ATTEMPTED_IN_THIS_PHASE"
        failure_reason = "process_or_os_terminated_after_open"
        lean_binary_sha256 = $ExpectedLeanSha256
        lean_commit = $ExpectedLeanCommit
        lean_version = $ExpectedLeanVersion
        matrix = $null
        native_worker_blob = $ExpectedWorkerBlob
        platform_record = $platformRecord
        powershell_executable_sha256 = $ExpectedPowerShellSha256
        python_executable_sha256 = $ExpectedPythonSha256
        rank = $null
        rpc_client_blob = $ExpectedClientBlob
        run_state = "RUN_OPENED"
        schema_version = $ArtifactSchema
        scientific_disposition = "D4_EXECUTION_FAILED"
        task_input_canonical_sha256 = $ExpectedTaskCanonicalSha256
        task_input_sha256 = $ExpectedTaskSha256
    }

    $childEnvironment = [Collections.Generic.SortedDictionary[string,string]]::new([StringComparer]::Ordinal)
    $childEnvironment["COMSPEC"] = $comspec
    $childEnvironment["LANG"] = "C.UTF-8"
    $childEnvironment["LC_ALL"] = "C.UTF-8"
    $childEnvironment["PATH"] = ([IO.Path]::GetDirectoryName($leanPath) + ";" + (Join-Path $systemRoot "System32"))
    $childEnvironment["PYTHONDONTWRITEBYTECODE"] = "1"
    $childEnvironment["PYTHONIOENCODING"] = "utf-8"
    $childEnvironment["PYTHONPATH"] = ""
    $childEnvironment["PYTHONUTF8"] = "1"
    $childEnvironment["SYSTEMROOT"] = $systemRoot
    $childEnvironment["TEMP"] = $runTemp
    $childEnvironment["TMP"] = $runTemp
    $childEnvironment["UPRIME_KP3_D4_ACTIONS_PATH"] = $actionPath
    $childEnvironment["UPRIME_KP3_D4_ACTION_CANONICAL_SHA256"] = $ExpectedActionCanonicalSha256
    $childEnvironment["UPRIME_KP3_D4_ARM_PATH"] = $armPath
    $childEnvironment["UPRIME_KP3_D4_C2_ACCEPTED_JOB_ID"] = $control["UPRIME_KP3_D4_C2_ACCEPTED_JOB_ID"]
    $childEnvironment["UPRIME_KP3_D4_C2_ACCEPTED_RUN_ID"] = $control["UPRIME_KP3_D4_C2_ACCEPTED_RUN_ID"]
    $childEnvironment["UPRIME_KP3_D4_C2_CONTROL_SCOPE"] = $ControlAttestationScope
    $childEnvironment["UPRIME_KP3_D4_C2_EXPECTED_FILE_DIGESTS_JSON"] = $expectedC2FileDigestsJson
    $childEnvironment["UPRIME_KP3_D4_C2_FILE_DIGEST_MATCH"] = "true"
    $childEnvironment["UPRIME_KP3_D4_C2_FILE_DIGESTS_JSON"] = $c2FileDigestsJson
    $childEnvironment["UPRIME_KP3_D4_C2_CANDIDATE_JOB_ID"] = $control["UPRIME_KP3_D4_C2_CANDIDATE_JOB_ID"]
    $childEnvironment["UPRIME_KP3_D4_C2_CANDIDATE_RUN_ID"] = $control["UPRIME_KP3_D4_C2_CANDIDATE_RUN_ID"]
    $childEnvironment["UPRIME_KP3_D4_C2_COMMIT"] = $control["UPRIME_KP3_D4_C2_COMMIT"]
    $childEnvironment["UPRIME_KP3_D4_C2_TREE"] = $control["UPRIME_KP3_D4_C2_TREE"]
    $childEnvironment["UPRIME_KP3_D4_FINAL_PATH"] = $resultPath
    $childEnvironment["UPRIME_KP3_D4_FIXED_IDENTITY_DIGEST"] = $fixedIdentityDigest
    $childEnvironment["UPRIME_KP3_D4_LEAN_EXE"] = $leanPath
    $childEnvironment["UPRIME_KP3_D4_NATIVE_WORKER"] = $workerPath
    $childEnvironment["UPRIME_KP3_D4_OFFICIAL_CHILD"] = "1"
    $childEnvironment["UPRIME_KP3_D4_OUTPUT_STAGE"] = $stagePath
    $childEnvironment["UPRIME_KP3_D4_OUTPUT_RECEIPT"] = $receiptPath
    $childEnvironment["UPRIME_KP3_D4_PER_ACTION_WALL_SECONDS"] = "30"
    $childEnvironment["UPRIME_KP3_D4_PLATFORM_RECORD"] = $platformRecord
    $childEnvironment["UPRIME_KP3_D4_QUARANTINE_ROOT"] = [IO.Path]::GetFullPath((Join-Path $env:USERPROFILE ".codex\quarantine"))
    $childEnvironment["UPRIME_KP3_D4_REPO_ROOT"] = $repoRoot
    $childEnvironment["UPRIME_KP3_D4_ROW_LIMIT"] = "12288"
    $childEnvironment["UPRIME_KP3_D4_SCHEMA_VERSION"] = $ArtifactSchema
    $childEnvironment["UPRIME_KP3_D4_STAGE_NONCE"] = $stageNonce
    $childEnvironment["UPRIME_KP3_D4_TASKS_PATH"] = $taskPath
    $childEnvironment["UPRIME_KP3_D4_TASK_CANONICAL_SHA256"] = $ExpectedTaskCanonicalSha256
    $childEnvironment["UPRIME_KP3_D4_WHOLE_WALL_SECONDS"] = "3600"
    $childEnvironment["WINDIR"] = $systemRoot
    $environmentCanonical = ($childEnvironment | ConvertTo-Json -Compress)
    $environmentDigest = Get-Sha256Text -Text $environmentCanonical
    $childEnvironment["UPRIME_KP3_D4_ENVIRONMENT_DIGEST"] = $environmentDigest
    $markerValue["environment_digest"] = $environmentDigest
    $markerSorted = [Collections.Generic.SortedDictionary[string,object]]::new([StringComparer]::Ordinal)
    foreach ($pair in $markerValue.GetEnumerator()) { $markerSorted[$pair.Key] = $pair.Value }
    $markerJson = ($markerSorted | ConvertTo-Json -Compress -Depth 8)

    $bootstrap = @'
import _ctypes
import asyncio
import ctypes
import json
import multiprocessing.process
import nt
import os
import re
import socket
import subprocess
import sys
import threading
import time
import types

if sys.argv != [sys.argv[0], "--official-child"]:
    raise RuntimeError("official child accepts exactly one internal token")
if not sys.flags.isolated or not sys.flags.no_site or not sys.flags.safe_path:
    raise RuntimeError("official child is not isolated")

_digest = os.environ.get("UPRIME_KP3_D4_ENVIRONMENT_DIGEST")
if not _digest or re.fullmatch(r"[0-9A-F]{64}", _digest) is None:
    raise RuntimeError("minimal environment digest is missing")
_base_environment = dict(os.environ)
del _base_environment["UPRIME_KP3_D4_ENVIRONMENT_DIGEST"]
_canonical = json.dumps(_base_environment, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
import hashlib
if hashlib.sha256(_canonical).hexdigest().upper() != _digest:
    raise RuntimeError("minimal environment digest mismatch")

for _name in os.environ:
    _upper = _name.upper()
    if any(_token in _upper for _token in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "CUDA", "NVIDIA", "MODEL", "OPENAI", "ANTHROPIC", "SSH")):
        raise RuntimeError("forbidden proxy/model/GPU/LLM/SSH environment survived")

_repo = os.path.normcase(os.path.abspath(os.environ["UPRIME_KP3_D4_REPO_ROOT"]))
_lean = os.path.normcase(os.path.abspath(os.environ["UPRIME_KP3_D4_LEAN_EXE"]))
_worker = os.path.normcase(os.path.abspath(os.environ["UPRIME_KP3_D4_NATIVE_WORKER"]))
_tasks = os.path.normcase(os.path.abspath(os.environ["UPRIME_KP3_D4_TASKS_PATH"]))
_actions = os.path.normcase(os.path.abspath(os.environ["UPRIME_KP3_D4_ACTIONS_PATH"]))
_stage = os.path.normcase(os.path.abspath(os.environ["UPRIME_KP3_D4_OUTPUT_STAGE"]))
_receipt = os.path.normcase(os.path.abspath(os.environ["UPRIME_KP3_D4_OUTPUT_RECEIPT"]))
_final = os.path.normcase(os.path.abspath(os.environ["UPRIME_KP3_D4_FINAL_PATH"]))
sys.path[:] = [_repo] + [p for p in sys.path if p and os.path.normcase(os.path.abspath(p)).startswith(os.path.normcase(os.path.abspath(sys.base_prefix)) + os.sep)]

def _deny_process(*_args, **_kwargs):
    raise RuntimeError("arbitrary child process and shell execution are forbidden")
def _deny_network(*_args, **_kwargs):
    raise RuntimeError("network access is forbidden")
def _deny_ffi(*_args, **_kwargs):
    raise RuntimeError("arbitrary FFI is forbidden")

def _install_exact_lean_process_broker():
    # Closure-private authority: no raw launcher or mutable permit is installed
    # in __main__.  This narrows trivial introspection bypasses; it is not an OS
    # sandbox claim (the Windows Job Object remains the resource boundary).
    raw_popen = subprocess.Popen
    permit = [None]
    required_env = {
        "COMSPEC", "LANG", "LC_ALL", "PATH", "SYSTEMROOT", "TEMP", "TMP", "WINDIR"
    }
    try:
        import _winapi as winapi
    except ImportError:
        winapi = None
    raw_create_process = None if winapi is None else winapi.CreateProcess

    def validate_exact_lean_call(args, kwargs):
        if isinstance(args, (str, bytes)) or type(args) not in (list, tuple):
            _deny_process()
        argv = tuple(args)
        normalized = tuple(
            os.path.normcase(os.path.abspath(value)) if index in (0, 2) else value
            for index, value in enumerate(argv)
        )
        if (
            len(argv) < 5
            or normalized[0] != _lean
            or argv[1] != "--run"
            or normalized[2] != _worker
            or argv[3] != "--imports"
        ):
            _deny_process()
        if any(
            type(value) is not str
            or re.fullmatch(r"[A-Za-z][A-Za-z0-9_.]*", value) is None
            for value in argv[4:]
        ):
            _deny_process()
        if kwargs.get("shell", False) or kwargs.get("executable") not in (None, _lean):
            _deny_process()
        if os.path.normcase(os.path.abspath(kwargs.get("cwd", _repo))) != _repo:
            _deny_process()
        env = kwargs.get("env")
        if type(env) is not dict or set(env) != required_env:
            _deny_process()

    def guarded_create_process(*args, **kwargs):
        if permit[0] != threading.get_ident() or raw_create_process is None:
            _deny_process()
        return raw_create_process(*args, **kwargs)

    def guarded_popen(args, *pos, **kwargs):
        validate_exact_lean_call(args, kwargs)
        if permit[0] is not None:
            _deny_process()
        permit[0] = threading.get_ident()
        try:
            return raw_popen(args, *pos, **kwargs)
        finally:
            permit[0] = None

    def process_audit(event, _args):
        if event == "subprocess.Popen":
            if permit[0] != threading.get_ident():
                _deny_process()
        elif event in {"os.exec", "os.posix_spawn", "os.spawn", "os.system"}:
            _deny_process()

    # EXACT_LEAN_BROKER_STRUCTURAL_SELF_CHECK: validate without spawning.
    validate_exact_lean_call(
        [_lean, "--run", _worker, "--imports", "Lean"],
        {"cwd": _repo, "env": {name: "unit" for name in required_env}},
    )
    if winapi is not None:
        winapi.CreateProcess = guarded_create_process
        if hasattr(winapi, "ShellExecute"):
            winapi.ShellExecute = _deny_process
    subprocess.Popen = guarded_popen
    sys.addaudithook(process_audit)

    def require_direct_denial(label, callback):
        try:
            callback()
        except RuntimeError:
            return
        raise RuntimeError("process broker self-check failed: " + label)

    if winapi is not None:
        require_direct_denial("_winapi.CreateProcess", lambda: winapi.CreateProcess())
        if hasattr(winapi, "ShellExecute"):
            require_direct_denial("_winapi.ShellExecute", lambda: winapi.ShellExecute())

_install_exact_lean_process_broker()
del _install_exact_lean_process_broker
_main_module = sys.modules["__main__"]
for _forbidden_launcher_name in (
    "_real_popen", "_real_create_process", "_lean_launch_gate",
    "raw_popen", "raw_create_process", "permit", "winapi",
):
    if hasattr(_main_module, _forbidden_launcher_name):
        raise RuntimeError("raw process launcher or mutable permit leaked into __main__")
del _main_module, _forbidden_launcher_name
for _name in ("run", "call", "check_call", "check_output", "getoutput", "getstatusoutput"):
    if hasattr(subprocess, _name): setattr(subprocess, _name, _deny_process)
for _module in (os, nt):
    for _name in ("execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe", "startfile", "system", "popen", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe", "posix_spawn", "posix_spawnp"):
        if hasattr(_module, _name): setattr(_module, _name, _deny_process)
asyncio.create_subprocess_exec = _deny_process
asyncio.create_subprocess_shell = _deny_process
multiprocessing.process.BaseProcess.start = _deny_process

class _DeniedSocket:
    def __new__(cls, *_args, **_kwargs): _deny_network()
socket.socket = _DeniedSocket
socket.SocketType = _DeniedSocket
for _name in ("create_connection", "create_server", "fromfd", "fromshare", "getaddrinfo", "gethostbyaddr", "gethostbyname", "gethostbyname_ex", "gethostname", "getnameinfo", "socketpair"):
    if hasattr(socket, _name): setattr(socket, _name, _deny_network)

class _DeniedLoader:
    def __getattr__(self, _name): _deny_ffi()
    def LoadLibrary(self, *_args, **_kwargs): _deny_ffi()
for _name in ("CDLL", "PyDLL", "WinDLL", "OleDLL", "LibraryLoader", "CFUNCTYPE", "WINFUNCTYPE", "PYFUNCTYPE", "cast", "_dlopen", "_CFuncPtr"):
    if hasattr(ctypes, _name): setattr(ctypes, _name, _deny_ffi)
for _name in ("cdll", "pydll", "windll", "oledll", "pythonapi"):
    if hasattr(ctypes, _name): setattr(ctypes, _name, _DeniedLoader())
for _name in ("LoadLibrary", "call_cdeclfunction", "call_function", "CFuncPtr"):
    if hasattr(_ctypes, _name): setattr(_ctypes, _name, _deny_ffi)

_input_root = os.path.dirname(_tasks)
_result_root = os.path.dirname(_final)
_forbidden_roots = (
    os.path.normcase(os.path.abspath(os.path.join(_repo, "docs", "experiments", "artifacts", "uprime_u05_20260711"))),
    os.path.normcase(os.path.abspath(os.path.join(_repo, "docs", "external", "quarantine"))),
    os.path.normcase(os.path.abspath(os.environ["UPRIME_KP3_D4_QUARANTINE_ROOT"])),
)
_forbidden_files = tuple(os.path.normcase(os.path.abspath(os.path.join(_repo, p))) for p in (
    os.path.join("lean_rgc", "evals", "uprime_u05_kill_probes.py"),
    "llm_local.json", "pilot_tasks.json", "fake_lean_smoke.py", "smoke_tasks_local.jsonl",
))
_forbidden_real_roots = tuple(os.path.normcase(os.path.realpath(path)) for path in _forbidden_roots)
_forbidden_real_files = tuple(os.path.normcase(os.path.realpath(path)) for path in _forbidden_files)
_input_real_root = os.path.normcase(os.path.realpath(_input_root))
_allowed_input_reals = {os.path.normcase(os.path.realpath(_tasks)), os.path.normcase(os.path.realpath(_actions))}
def _within(path, root): return path == root or path.startswith(root + os.sep)
def _audit(event, args):
    if event.startswith("socket."): _deny_network()
    if event.startswith("ctypes."): _deny_ffi()
    if event in {"open", "os.listdir", "os.scandir", "os.chdir"} and args:
        raw = args[0]
        if isinstance(raw, int): return
        try: path = os.path.normcase(os.path.abspath(os.fsdecode(os.fspath(raw))))
        except (TypeError, ValueError): return
        if _within(path, _input_root) and path not in (_tasks, _actions):
            raise RuntimeError("only the two registered scientific input files may be read")
        if path in _forbidden_files or any(_within(path, root) for root in _forbidden_roots):
            raise RuntimeError("U05, quarantine, and LLM files are forbidden")
        if _within(path, _result_root) and path not in (_stage, _receipt, _final):
            raise RuntimeError("unregistered result path is forbidden")
        real = os.path.normcase(os.path.realpath(path))
        if _within(real, _input_real_root) and real not in _allowed_input_reals:
            raise RuntimeError("realpath alias reached an unregistered scientific input")
        if real in _forbidden_real_files or any(_within(real, root) for root in _forbidden_real_roots):
            raise RuntimeError("realpath alias reached U05, quarantine, or LLM data")
sys.addaudithook(_audit)

# The parent creates this durable arm only after this exact Python process is
# inside the 2-GiB kill-on-close Job Object and RUN_OPENED is durable.  Until
# then even an import-time regression cannot launch Lean through the guarded
# transport because official_child_main is not entered.
_arm = os.path.normcase(os.path.abspath(os.environ["UPRIME_KP3_D4_ARM_PATH"]))
_arm_deadline = time.monotonic() + 120.0
while True:
    try:
        with open(_arm, "rb") as _handle:
            _arm_payload = _handle.read(16)
        if _arm_payload != b"ARM\n":
            raise RuntimeError("official child arm is malformed")
        break
    except FileNotFoundError:
        if time.monotonic() >= _arm_deadline:
            raise RuntimeError("official child was not armed")
        time.sleep(0.01)

from lean_rgc.evals.uprime_kp3_d4_canonical_history import official_child_main
_exit = official_child_main()
if type(_exit) is not int or not 0 <= _exit <= 255:
    raise RuntimeError("official_child_main returned an invalid exit code")
raise SystemExit(_exit)
'@
    [IO.File]::WriteAllText($bootstrapPath, $bootstrap, [Text.UTF8Encoding]::new($false))

    $jobSource = @'
using System;
using System.Runtime.InteropServices;
public static class UPrimeKP3D4Job {
  [StructLayout(LayoutKind.Sequential)] public struct Basic {
    public long PerProcessUserTimeLimit, PerJobUserTimeLimit;
    public uint LimitFlags;
    public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize;
    public uint ActiveProcessLimit;
    public IntPtr Affinity;
    public uint PriorityClass, SchedulingClass;
  }
  [StructLayout(LayoutKind.Sequential)] public struct IO {
    public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount;
    public ulong ReadTransferCount, WriteTransferCount, OtherTransferCount;
  }
  [StructLayout(LayoutKind.Sequential)] public struct Extended {
    public Basic BasicLimitInformation;
    public IO IoInfo;
    public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed;
  }
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr CreateJobObject(IntPtr a, string n);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern bool SetInformationJobObject(IntPtr h, int c, IntPtr p, uint l);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern bool QueryInformationJobObject(IntPtr h, int c, IntPtr p, uint l, out uint used);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern bool AssignProcessToJobObject(IntPtr h, IntPtr p);
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool MoveFileEx(string source, string destination, uint flags);
  [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);
  public static IntPtr Create(ulong bytes) {
    IntPtr h = CreateJobObject(IntPtr.Zero, null);
    if (h == IntPtr.Zero) throw new System.ComponentModel.Win32Exception();
    Extended x = new Extended();
    x.BasicLimitInformation.LimitFlags = 0x100u | 0x200u | 0x2000u;
    x.ProcessMemoryLimit = (UIntPtr)bytes;
    x.JobMemoryLimit = (UIntPtr)bytes;
    int size = Marshal.SizeOf(typeof(Extended));
    IntPtr mem = Marshal.AllocHGlobal(size);
    try {
      Marshal.StructureToPtr(x, mem, false);
      if (!SetInformationJobObject(h, 9, mem, (uint)size)) throw new System.ComponentModel.Win32Exception();
      return h;
    } catch { CloseHandle(h); throw; } finally { Marshal.FreeHGlobal(mem); }
  }
  public static ulong PeakJobMemory(IntPtr h) {
    int size = Marshal.SizeOf(typeof(Extended));
    IntPtr mem = Marshal.AllocHGlobal(size);
    try {
      uint used;
      if (!QueryInformationJobObject(h, 9, mem, (uint)size, out used)) throw new System.ComponentModel.Win32Exception();
      Extended x = (Extended)Marshal.PtrToStructure(mem, typeof(Extended));
      return x.PeakJobMemoryUsed.ToUInt64();
    } finally { Marshal.FreeHGlobal(mem); }
  }
  public static void DurableReplace(string source, string destination) {
    const uint ReplaceExisting = 0x1u;
    const uint WriteThrough = 0x8u;
    if (!MoveFileEx(source, destination, ReplaceExisting | WriteThrough)) throw new System.ComponentModel.Win32Exception();
  }
}
'@
    Add-Type -TypeDefinition $jobSource -Language CSharp
    $job = [UPrimeKP3D4Job]::Create($WorkingSetLimitBytes)

    # The durable parseable marker is the one-shot arm.  All identity, input,
    # environment, bootstrap, and resource-governor preflight is complete.
    # Nothing below may delete it or grant a retry after host termination.
    Write-DurableExclusiveUtf8 -LiteralPath $resultPath -Text $markerJson
    $markerOpened = $true

    # Construct a child-only environment; never mutate or inherit the parent
    # process environment, which may contain proxy, model, CUDA, or secrets.
    $arguments = @("-I", "-S", $bootstrapPath, "--official-child")
    $nativeArgumentLine = (($arguments | ForEach-Object { Quote-NativeArgument -Value $_ }) -join " ")
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $pythonPath
    $startInfo.Arguments = $nativeArgumentLine
    $startInfo.WorkingDirectory = $repoRoot
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.EnvironmentVariables.Clear()
    foreach ($pair in $childEnvironment.GetEnumerator()) { $startInfo.EnvironmentVariables[$pair.Key] = $pair.Value }
    $pythonProcess = [Diagnostics.Process]::new()
    $pythonProcess.StartInfo = $startInfo
    if (-not $pythonProcess.Start()) { throw "failed to start the exact official Python child" }
    $pythonProcessHandle = $pythonProcess.Handle
    $stdoutStream = [IO.FileStream]::new($stdoutPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read, 4096, [IO.FileOptions]::SequentialScan)
    $stderrStream = [IO.FileStream]::new($stderrPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read, 4096, [IO.FileOptions]::SequentialScan)
    $stdoutCopyTask = $pythonProcess.StandardOutput.BaseStream.CopyToAsync($stdoutStream)
    $stderrCopyTask = $pythonProcess.StandardError.BaseStream.CopyToAsync($stderrStream)
    if (-not [UPrimeKP3D4Job]::AssignProcessToJobObject($job, $pythonProcess.Handle)) {
        throw "failed to assign the official Python/Lean process tree to the 2-GiB job"
    }
    Write-DurableExclusiveUtf8 -LiteralPath $armPath -Text "ARM`n"
    $stopwatch = [Diagnostics.Stopwatch]::StartNew()
    $peakWorkingSet = [int64]0
    $peakJobMemory = [uint64]0
    $capFailure = $null
    while (-not $pythonProcess.HasExited) {
        Start-Sleep -Milliseconds 50
        $pythonProcess.Refresh()
        $peakWorkingSet = [Math]::Max($peakWorkingSet, $pythonProcess.WorkingSet64)
        if ((Get-CapturedBytes -Paths @($stdoutPath, $stderrPath)) -ge $OutputLimitBytes) { $capFailure = "output"; break }
        if ($stopwatch.Elapsed.TotalSeconds -ge $WholeRunWallSeconds) { $capFailure = "timeout"; break }
    }
    if ($job -ne [IntPtr]::Zero) {
        try { $peakJobMemory = [UPrimeKP3D4Job]::PeakJobMemory($job) } catch { }
    }
    if ($null -ne $capFailure -and -not $pythonProcess.HasExited) { [void][UPrimeKP3D4Job]::CloseHandle($job); $job = [IntPtr]::Zero }
    $pythonProcess.WaitForExit()
    $pythonProcess.Refresh()
    if ($null -ne $stdoutCopyTask) { $stdoutCopyTask.GetAwaiter().GetResult() }
    if ($null -ne $stderrCopyTask) { $stderrCopyTask.GetAwaiter().GetResult() }
    if ($null -ne $stdoutStream) { $stdoutStream.Flush($true); $stdoutStream.Dispose(); $stdoutStream = $null }
    if ($null -ne $stderrStream) { $stderrStream.Flush($true); $stderrStream.Dispose(); $stderrStream = $null }
    $stopwatch.Stop()
    $peakWorkingSet = [Math]::Max($peakWorkingSet, $pythonProcess.PeakWorkingSet64)
    $processExit = [int]$pythonProcess.ExitCode
    if ($job -ne [IntPtr]::Zero) {
        try { $peakJobMemory = [Math]::Max($peakJobMemory, [UPrimeKP3D4Job]::PeakJobMemory($job)) } catch { }
    }
    if ($null -eq $capFailure -and $stopwatch.Elapsed.TotalSeconds -ge $WholeRunWallSeconds) { $capFailure = "timeout" }
    if ($null -eq $capFailure -and (Get-CapturedBytes -Paths @($stdoutPath, $stderrPath)) -ge $OutputLimitBytes) { $capFailure = "output" }
    if ($null -eq $capFailure -and -not (Test-Path -LiteralPath $receiptPath -PathType Leaf) -and
        ($peakJobMemory -ge $WorkingSetLimitBytes -or $processExit -in @(-1073741801, -1073741523))) {
        $capFailure = "working_set"
    }
    if ($capFailure -ne "output") {
        Write-CapturedStream -LiteralPath $stdoutPath -Stream stdout
        Write-CapturedStream -LiteralPath $stderrPath -Stream stderr
    }
    if ($null -ne $capFailure) {
        if ($capFailure -eq "timeout") {
            $resourceReason = "parent_whole_run_wall_limit"
            Write-RunnerError "3,600-second whole-run hard wall reached"
            $exitCode = $ExitTimeout
        }
        elseif ($capFailure -eq "working_set") {
            $resourceReason = "parent_job_memory_limit"
            Write-RunnerError "2-GiB process/job memory limit reached"
            $exitCode = $ExitWorkingSet
        }
        else {
            $resourceReason = "parent_captured_output_limit"
            Write-RunnerError "64-MiB captured-output limit reached"
            $exitCode = $ExitOutputLimit
        }
        Install-ParentResourceArtifact -Marker $markerSorted -FailureReason $resourceReason -FailureStagePath $failureStagePath -FinalPath $resultPath
        $resultInstalled = $true
    }
    elseif ((Test-Path -LiteralPath $stagePath -PathType Leaf) -and (Test-Path -LiteralPath $receiptPath -PathType Leaf)) {
        $stageItem = Get-Item -LiteralPath $stagePath -Force
        if (($stageItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
            $stageItem.Length -le 0 -or $stageItem.Length -ge $OutputLimitBytes) {
            throw "official child stage is empty, reparse, or outside the 64-MiB cap"
        }
        [void](Read-StrictUtf8File -LiteralPath $stagePath -MaximumBytes $OutputLimitBytes)
        $receiptRaw = Read-StrictUtf8File -LiteralPath $receiptPath -MaximumBytes 16384 -ReturnText
        $receiptValue = $receiptRaw | ConvertFrom-Json
        $receiptFields = @(
            "artifact_canonical", "artifact_length", "artifact_sha256",
            "artifact_top_level_fields", "c2_allowlist_file_sha256", "c2_commit",
            "c2_control_attestation_scope", "c2_file_digest_match", "c2_tree", "child_exit_code",
            "conditioning_censor", "conditioning_is_null", "environment_digest",
            "fixed_identity_digest", "run_state", "schema_version",
            "scientific_disposition", "stage_nonce"
        )
        $actualReceiptFields = @($receiptValue.PSObject.Properties.Name | Sort-Object)
        if (($actualReceiptFields -join "`n") -cne (($receiptFields | Sort-Object) -join "`n")) {
            throw "official child receipt field mismatch"
        }
        $canonicalReceipt = [Collections.Generic.SortedDictionary[string,object]]::new([StringComparer]::Ordinal)
        foreach ($name in $receiptFields) { $canonicalReceipt[$name] = $receiptValue.$name }
        if (($canonicalReceipt | ConvertTo-Json -Compress -Depth 8) -cne $receiptRaw) {
            throw "official child receipt is duplicate, noncanonical, or changed after parse"
        }
        $receiptTopFields = @($receiptValue.artifact_top_level_fields)
        $receiptFileDigestsJson = ($receiptValue.c2_allowlist_file_sha256 | ConvertTo-Json -Compress)
        $completedDispositions = @(
            "D4_FRESH_FAMILY_COMPLETED_CONDITIONAL_KSTATE_MARKOV",
            "D4_FRESH_FAMILY_RANK_ABOVE_CAP_CONDITIONAL_KSTATE_MARKOV"
        )
        $failureDispositions = @(
            "D4_NORMALIZATION_UNSOUND", "D4_DOMAIN_INCOMPLETE",
            "D4_RESOURCE_BLOCKED", "D4_EXECUTION_FAILED"
        )
        if ($receiptValue.schema_version -cne $ReceiptSchema -or
            (($receiptValue.artifact_length -isnot [int]) -and ($receiptValue.artifact_length -isnot [long])) -or
            (($receiptValue.child_exit_code -isnot [int]) -and ($receiptValue.child_exit_code -isnot [long])) -or
            $receiptValue.artifact_top_level_fields -isnot [Array] -or
            @($receiptTopFields | Where-Object { $_ -isnot [string] }).Count -ne 0 -or
            $receiptValue.stage_nonce -cne $stageNonce -or
            $receiptValue.artifact_canonical -isnot [bool] -or $receiptValue.artifact_canonical -ne $true -or
            $receiptValue.conditioning_is_null -isnot [bool] -or $receiptValue.conditioning_is_null -ne $true -or
            $receiptValue.conditioning_censor -cne "NOT_ATTEMPTED_IN_THIS_PHASE" -or
            $receiptValue.run_state -cne "ORDINARY_RESULT_COMMITTED" -or
            $receiptValue.c2_commit -cne $control["UPRIME_KP3_D4_C2_COMMIT"] -or
            $receiptValue.c2_tree -cne $control["UPRIME_KP3_D4_C2_TREE"] -or
            $receiptValue.c2_control_attestation_scope -cne $ControlAttestationScope -or
            $receiptValue.c2_file_digest_match -isnot [bool] -or
            $receiptValue.c2_file_digest_match -ne $true -or
            $receiptValue.environment_digest -cne $environmentDigest -or
            $receiptValue.fixed_identity_digest -cne $fixedIdentityDigest -or
            $receiptFileDigestsJson -cne $c2FileDigestsJson -or
            ($receiptTopFields -join "`n") -cne ($OfficialArtifactFields -join "`n") -or
            $receiptValue.artifact_length -ne $stageItem.Length -or
            $receiptValue.artifact_sha256 -cne (Get-Sha256 -LiteralPath $stagePath) -or
            $receiptValue.child_exit_code -ne $processExit) {
            throw "official child receipt does not bind the exact fixed stage"
        }
        $disposition = [string]$receiptValue.scientific_disposition
        if (($completedDispositions -contains $disposition -and $processExit -ne 0) -or
            ($failureDispositions -contains $disposition -and $processExit -ne 1) -or
            (-not ($completedDispositions -contains $disposition) -and -not ($failureDispositions -contains $disposition))) {
            throw "official child disposition and exit code are incoherent"
        }
        $stageItem.Refresh()
        if ($stageItem.Length -ne $receiptValue.artifact_length -or
            (Get-Sha256 -LiteralPath $stagePath) -cne $receiptValue.artifact_sha256) {
            throw "official child stage changed immediately before durable replacement"
        }
        [UPrimeKP3D4Job]::DurableReplace($stagePath, $resultPath)
        Flush-DurableFile -LiteralPath $resultPath
        $resultInstalled = $true
        $exitCode = $processExit
    }
    else {
        Write-RunnerError "official child produced no complete nonce stage/receipt pair; RUN_OPENED remains final"
        $exitCode = if ($processExit -eq 0) { $ExitInternalError } else { $processExit }
    }
}
catch {
    Write-RunnerError $_.Exception.Message
    $exitCode = if ($markerOpened) { $ExitInternalError } else { $ExitPreflight }
}
finally {
    if ($job -ne [IntPtr]::Zero) { try { [void][UPrimeKP3D4Job]::CloseHandle($job) } catch { }; $job = [IntPtr]::Zero }
    if ($null -ne $pythonProcess -and -not $pythonProcess.HasExited) {
        try { $pythonProcess.Kill(); $pythonProcess.WaitForExit() } catch { }
    }
    if ($null -ne $stdoutStream) { try { $stdoutStream.Dispose() } catch { }; $stdoutStream = $null }
    if ($null -ne $stderrStream) { try { $stderrStream.Dispose() } catch { }; $stderrStream = $null }
    foreach ($ownedOutput in @($stagePath, $receiptPath, $failureStagePath)) {
        if ($null -ne $ownedOutput -and (Test-Path -LiteralPath $ownedOutput -PathType Leaf)) {
            try { Remove-Item -LiteralPath $ownedOutput -Force } catch { }
        }
    }
    if ($null -ne $runTemp -and (Test-Path -LiteralPath $runTemp)) {
        try {
            $resolved = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $runTemp).ProviderPath)
            $systemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd("\", "/")
            if (-not [IO.Path]::GetFullPath((Split-Path -Parent $resolved)).TrimEnd("\", "/").Equals($systemTemp, [StringComparison]::OrdinalIgnoreCase) -or
                -not [IO.Path]::GetFileName($resolved).StartsWith($TempPrefix, [StringComparison]::Ordinal)) {
                throw "refusing to clean an unowned path"
            }
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
        catch { Write-RunnerError $_.Exception.Message; if ($exitCode -eq 0) { $exitCode = $ExitInternalError } }
    }
}

exit $exitCode
