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
$ExitSyntheticExecution = 70
$ExitSyntheticImport = 71
$ExitSyntheticScope = 72
$ExitSyntheticRpc = 73
$ExitSyntheticResource = 74
$ExitSyntheticArtifact = 75
$ExitSyntheticMargin = 76

$CanonicalLiveRoot = "C:\Users\yusei\Desktop\lean_rgc_automation_stack_v47_goal_state_dynamics_transport_v2_recovery_live"
$ResultRef = "codex/uprime-official-transport-v2-precommit-recovery-result"
$ResultRelativePath = "docs/experiments/artifacts/uprime_official_transport_v2_20260713/synthetic_qualification.json"
$TempPrefix = "lean-rgc-uprime-official-transport-v2-"

$ExpectedPowerShellVersion = "5.1.26100.8655"
$ExpectedPowerShellSha256 = "0FF6F2C94BC7E2833A5F7E16DE1622E5DBA70396F31C7D5F56381870317E8C46"
$ExpectedPythonVersion = "3.13.7"
$ExpectedPythonSha256 = "D932E5E2F324D57F392E8FD063DCF6D0185BE8A664C57C6D24E7762ED02C28CA"
$ExpectedLeanVersion = "4.31.0"
$ExpectedLeanCommit = "68218e876d2a38b1985b8590fff244a83c321783"
$ExpectedLeanSha256 = "9B216DEB50D37C32C829D1EFAAA5BAFD5560417D382DF35A815489E31A31593F"
$ExpectedWorkerBlob = "305509d9b89081a3d002734e09724b98e244a24c"
$ExpectedWorkerSha256 = "741E19237C829BA5E76E895EDB20ECD26517804C5CEE4FF8C711946739AB3A14"

$ProbeSchema = "lean-rgc-uprime-official-transport-probe-v2.0"
$ReadySchema = "lean-rgc-uprime-official-transport-ready-v2.0"
$ArmSchema = "lean-rgc-uprime-official-transport-arm-v2.0"
$ArtifactSchema = "lean-rgc-uprime-official-transport-artifact-v2.0"
$ChildResultSchema = "lean-rgc-uprime-official-transport-child-result-v2.0"
$ReceiptSchema = "lean-rgc-uprime-official-transport-receipt-v2.0"
$TimingSchema = "lean-rgc-uprime-official-transport-timing-v2.0"
$TranscriptSchema = "lean-rgc-uprime-official-transport-transcript-v2.0"
$AttestationScope = "EXTERNAL_CI_ATTESTATION_UNVERIFIED_BY_RUNNER"

$WorkingSetLimitBytes = [uint64]1 * 1024 * 1024 * 1024
$StreamLimitBytes = [int64]1 * 1024 * 1024
$ResponseLimitBytes = [int64]4 * 1024 * 1024
$ArtifactLimitBytes = [int64]1 * 1024 * 1024
$ReceiptLimitBytes = [int64]1 * 1024 * 1024
$ProbeMaximumBytes = 192
$ReadyMaximumBytes = 8192

$I1Allowlist = @(
    "tools/uprime_official_transport_v2_smoke.py",
    "tools/run_uprime_official_transport_v2_smoke.ps1",
    "tools/run_uprime_official_transport_v2_tests.ps1",
    "tests/test_uprime_official_transport_v2_smoke.py",
    "tests/tier_manifest.json"
)

$RequestIds = @(
    "i1-v2-01-load",
    "i1-v2-02-status-initial",
    "i1-v2-03-init",
    "i1-v2-04-apply",
    "i1-v2-05-discard-child",
    "i1-v2-06-discard-source",
    "i1-v2-07-status-final",
    "i1-v2-08-shutdown"
)
$RequestClasses = @(
    "startup_load", "control", "control_initialization", "action",
    "control", "control", "control", "shutdown"
)

function New-SortedMap {
    return [Collections.Generic.SortedDictionary[string,object]]::new([StringComparer]::Ordinal)
}

function Write-RunnerError {
    param([Parameter(Mandatory = $true)][string] $Message)
    [Console]::Error.WriteLine("uprime-official-transport-v2: {0}", $Message)
}

function ConvertTo-CanonicalJson {
    param(
        [Parameter(Mandatory = $true)][object] $Value,
        [int] $Depth = 64
    )
    return ($Value | ConvertTo-Json -Compress -Depth $Depth)
}

function Get-Sha256Text {
    param([Parameter(Mandatory = $true)][string] $Text)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.UTF8Encoding]::new($false, $true).GetBytes($Text)
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "")
    }
    finally { $sha.Dispose() }
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
    $sha = [Security.Cryptography.SHA1]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($framed))).Replace("-", "").ToLowerInvariant() }
    finally { $sha.Dispose() }
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

function Quote-NativeArgument {
    param([Parameter(Mandatory = $true)][string] $Value)
    if ($Value.IndexOf([char]0) -ge 0 -or $Value.Contains("`r") -or
        $Value.Contains("`n") -or $Value.Contains('"') -or
        $Value.EndsWith("\") -or $Value.EndsWith("/")) {
        throw "unsafe native argument"
    }
    return '"' + $Value + '"'
}

function Write-DurableExclusiveUtf8 {
    param(
        [Parameter(Mandatory = $true)][string] $LiteralPath,
        [Parameter(Mandatory = $true)][string] $Text,
        [int64] $MaximumBytes = $ArtifactLimitBytes
    )
    $bytes = [Text.UTF8Encoding]::new($false, $true).GetBytes($Text)
    if ($bytes.LongLength -le 0 -or $bytes.LongLength -gt $MaximumBytes) {
        throw "owned output is empty or exceeds its byte cap"
    }
    $stream = [IO.FileStream]::new(
        $LiteralPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write,
        [IO.FileShare]::None, 4096, [IO.FileOptions]::WriteThrough
    )
    try { $stream.Write($bytes, 0, $bytes.Length); $stream.Flush($true) }
    finally { $stream.Dispose() }
}

function Flush-DurableFile {
    param([Parameter(Mandatory = $true)][string] $LiteralPath)
    $stream = [IO.FileStream]::new(
        $LiteralPath, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite,
        [IO.FileShare]::Read, 4096, [IO.FileOptions]::WriteThrough
    )
    try { $stream.Flush($true) }
    finally { $stream.Dispose() }
}

function Read-StrictUtf8File {
    param(
        [Parameter(Mandatory = $true)][string] $LiteralPath,
        [Parameter(Mandatory = $true)][int64] $MaximumBytes
    )
    $item = Get-Item -LiteralPath $LiteralPath -Force
    if ($item.PSIsContainer -or (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) -or
        $item.Length -le 0 -or $item.Length -gt $MaximumBytes) {
        throw "strict UTF-8 file is empty, reparse, or outside its byte cap"
    }
    $encoding = [Text.UTF8Encoding]::new($false, $true)
    $stream = [IO.FileStream]::new($LiteralPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $reader = [IO.StreamReader]::new($stream, $encoding, $false, 65536, $false)
    try { return $reader.ReadToEnd() }
    finally { $reader.Dispose(); $stream.Dispose() }
}

function Get-NowTicks { return [Diagnostics.Stopwatch]::GetTimestamp() }

function New-DeadlineTicks {
    param(
        [Parameter(Mandatory = $true)][int64] $StartTicks,
        [Parameter(Mandatory = $true)][int64] $WallSeconds
    )
    $frequency = [int64][Diagnostics.Stopwatch]::Frequency
    if ($WallSeconds -le 0 -or $WallSeconds -gt [int64]::MaxValue / $frequency) {
        throw "deadline multiplication overflow"
    }
    $wallTicks = [int64]($WallSeconds * $frequency)
    if ($StartTicks -lt 0 -or $StartTicks -gt [int64]::MaxValue - $wallTicks) {
        throw "deadline addition overflow"
    }
    return [int64]($StartTicks + $wallTicks)
}

function Get-RemainingMilliseconds {
    param([Parameter(Mandatory = $true)][int64[]] $Deadlines)
    $deadline = [int64]($Deadlines | Measure-Object -Minimum).Minimum
    $now = Get-NowTicks
    $remaining = [int64]($deadline - $now)
    if ($remaining -le 0) { return 0 }
    $frequency = [int64][Diagnostics.Stopwatch]::Frequency
    $milliseconds = [int64](($remaining * 1000 + $frequency - 1) / $frequency)
    if ($milliseconds -gt [int]::MaxValue) { return [int]::MaxValue }
    return [int][Math]::Max(1, $milliseconds)
}

function Assert-Deadline {
    param(
        [Parameter(Mandatory = $true)][int64] $DeadlineTicks,
        [Parameter(Mandatory = $true)][string] $Name
    )
    if ((Get-NowTicks) -gt $DeadlineTicks) { throw "$Name hard wall exceeded" }
}

function New-ParentTimingRecord {
    param(
        [Parameter(Mandatory = $true)][string] $ClockClass,
        [Parameter(Mandatory = $true)][int64] $StartTicks,
        [Parameter(Mandatory = $true)][int64] $EndTicks,
        [Parameter(Mandatory = $true)][int64] $HardWallSeconds,
        [Parameter(Mandatory = $true)][int64] $SuccessMarginSeconds
    )
    if ($StartTicks -lt 0 -or $EndTicks -lt $StartTicks) { throw "invalid parent timing order" }
    $frequency = [int64][Diagnostics.Stopwatch]::Frequency
    $hardTicks = [int64]($HardWallSeconds * $frequency)
    $marginTicks = [int64]($SuccessMarginSeconds * $frequency)
    $elapsed = [int64]($EndTicks - $StartTicks)
    $classification = if ($elapsed -gt $hardTicks) {
        "RESOURCE_BLOCKED"
    } elseif ($elapsed -gt $marginTicks) {
        "QUALIFICATION_MARGIN_BLOCKED"
    } else {
        "PASS"
    }
    $value = New-SortedMap
    $value["authority"] = "parent_stopwatch_ticks"
    $value["classification"] = $classification
    $value["clock_class"] = $ClockClass
    $value["elapsed_ticks"] = $elapsed
    $value["end_ticks"] = $EndTicks
    $value["hard_wall_ticks"] = $hardTicks
    $value["schema_version"] = $TimingSchema
    $value["start_ticks"] = $StartTicks
    $value["stopwatch_frequency"] = $frequency
    $value["success_margin_ticks"] = $marginTicks
    return $value
}

function New-BatchBlockResult {
    param([Parameter(Mandatory = $true)][int64] $BatchStartTicks)
    $now = Get-NowTicks
    $timing = New-ParentTimingRecord -ClockClass "batch_execution" -StartTicks $BatchStartTicks -EndTicks $now `
        -HardWallSeconds 1200 -SuccessMarginSeconds 400
    if ($timing["classification"] -ceq "PASS") { return $null }
    $blocked = New-SortedMap
    $blocked["child"] = $null
    $blocked["disposition"] = if ($timing["classification"] -ceq "RESOURCE_BLOCKED") {
        "SYNTHETIC_RESOURCE_BLOCKED"
    } else {
        "SYNTHETIC_QUALIFICATION_MARGIN_BLOCKED"
    }
    $blocked["failure_code"] = if ($timing["classification"] -ceq "RESOURCE_BLOCKED") {
        "BATCH_EXECUTION_HARD_WALL"
    } else {
        "BATCH_EXECUTION_MARGIN_BLOCKED"
    }
    $blocked["resource_evidence"] = $null
    if ($timing["classification"] -ceq "RESOURCE_BLOCKED") {
        $resource = New-SortedMap
        $resource["cap_name"] = "batch_execution"
        $resource["cap_value"] = [int64](1200 * [Diagnostics.Stopwatch]::Frequency)
        $resource["observed_value"] = [int64]$timing["elapsed_ticks"]
        $resource["stage"] = "parent_batch_gate"
        $blocked["resource_evidence"] = $resource
    }
    $blocked["role"] = "BATCH"
    $blocked["success"] = $false
    return $blocked
}

function Read-BoundedUtf8LineUntil {
    param(
        [Parameter(Mandatory = $true)][IO.Stream] $Stream,
        [Parameter(Mandatory = $true)][int] $MaximumBytes,
        [Parameter(Mandatory = $true)][int64[]] $Deadlines
    )
    $memory = [IO.MemoryStream]::new()
    $one = [byte[]]::new(1)
    try {
        while ($true) {
            $remaining = Get-RemainingMilliseconds -Deadlines $Deadlines
            if ($remaining -le 0) { throw "READY hard wall exceeded" }
            $task = $Stream.ReadAsync($one, 0, 1)
            if (-not $task.Wait($remaining)) { throw "READY hard wall exceeded" }
            if ($task.Result -ne 1) { throw "child stdout closed before READY" }
            if ($one[0] -eq 10) { break }
            if ($one[0] -eq 13) { throw "READY contains CR" }
            if ($memory.Length -ge $MaximumBytes) { throw "READY exceeds byte cap" }
            $memory.WriteByte($one[0])
        }
        if ($memory.Length -eq 0) { throw "READY is empty" }
        return [Text.UTF8Encoding]::new($false, $true).GetString($memory.ToArray())
    }
    finally { $memory.Dispose() }
}

function Write-ChildFrameUntil {
    param(
        [Parameter(Mandatory = $true)][IO.Stream] $Stream,
        [Parameter(Mandatory = $true)][string] $Text,
        [Parameter(Mandatory = $true)][int64[]] $Deadlines
    )
    $bytes = [Text.UTF8Encoding]::new($false, $true).GetBytes($Text)
    $write = $Stream.WriteAsync($bytes, 0, $bytes.Length)
    $remaining = Get-RemainingMilliseconds -Deadlines $Deadlines
    if ($remaining -le 0 -or -not $write.Wait($remaining)) { throw "child frame write exceeded absolute deadline" }
    $flush = $Stream.FlushAsync()
    $remaining = Get-RemainingMilliseconds -Deadlines $Deadlines
    if ($remaining -le 0 -or -not $flush.Wait($remaining)) { throw "child frame flush exceeded absolute deadline" }
}

function Assert-ExactCanonicalObject {
    param(
        [Parameter(Mandatory = $true)][object] $Value,
        [Parameter(Mandatory = $true)][string[]] $Fields,
        [Parameter(Mandatory = $true)][string] $Raw,
        [Parameter(Mandatory = $true)][string] $Where,
        [int] $Depth = 64
    )
    if ((@($Value.PSObject.Properties.Name) -join "`n") -cne ($Fields -join "`n")) {
        throw "$Where field set/order mismatch"
    }
    if ((ConvertTo-CanonicalJson -Value $Value -Depth $Depth) -cne $Raw) {
        throw "$Where is duplicate or noncanonical JSON"
    }
}

function Invoke-GitScalar {
    param(
        [Parameter(Mandatory = $true)][string] $Root,
        [Parameter(Mandatory = $true)][string[]] $Arguments
    )
    $output = @(& git -C $Root @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0 -or $output.Count -ne 1) { throw "git scalar query failed: $($Arguments -join ' ')" }
    return ([string]$output[0]).Trim()
}

function New-TimingPolicy {
    $policy = New-SortedMap
    foreach ($entry in @(
        @("action", "child_monotonic_ns", 15, 5),
        @("artifact_publication", "parent_stopwatch_ticks", 30, 10),
        @("batch_execution", "parent_stopwatch_ticks", 1200, 400),
        @("control", "child_monotonic_ns", 30, 10),
        @("control_initialization", "child_monotonic_ns", 30, 10),
        @("fixture_execution", "parent_stopwatch_ticks", 300, 100),
        @("python_ready", "parent_stopwatch_ticks", 15, 5),
        @("shutdown", "child_monotonic_ns", 10, 3),
        @("startup_load", "child_monotonic_ns", 120, 40),
        @("unit_whole", "parent_stopwatch_ticks", 30, 10)
    )) {
        $row = New-SortedMap
        $row["authority"] = [string]$entry[1]
        if ($entry[1] -ceq "child_monotonic_ns") {
            $row["hard_wall_ns"] = [int64]$entry[2] * 1000000000
            $row["success_margin_ns"] = [int64]$entry[3] * 1000000000
        }
        else {
            $row["hard_wall_seconds"] = [int]$entry[2]
            $row["success_margin_seconds"] = [int]$entry[3]
        }
        $policy[[string]$entry[0]] = $row
    }
    return $policy
}

function New-BatchMarkerJson {
    param(
        [Parameter(Mandatory = $true)][string] $RunNonce,
        [Parameter(Mandatory = $true)][string] $IdentityDigest,
        [Parameter(Mandatory = $true)][string] $EnvironmentDigest,
        [Parameter(Mandatory = $true)][string] $TimingPolicyDigest,
        [Parameter(Mandatory = $true)][string] $ParentCommit
    )
    $value = New-SortedMap
    $value["artifact_variant"] = "BATCH_OPENED"
    $value["canonical_execution_root"] = $CanonicalLiveRoot
    $value["environment_digest"] = $EnvironmentDigest
    $value["identity_digest"] = $IdentityDigest
    $value["parent_commit"] = $ParentCommit
    $value["result_ref"] = $ResultRef
    $value["run_nonce"] = $RunNonce
    $value["run_state"] = "BATCH_OPENED"
    $value["schema_version"] = $ArtifactSchema
    $value["timing_policy_digest"] = $TimingPolicyDigest
    return ConvertTo-CanonicalJson -Value $value
}

function New-RunMarkerJson {
    param(
        [Parameter(Mandatory = $true)][string] $RunNonce,
        [Parameter(Mandatory = $true)][string] $IdentityDigest,
        [Parameter(Mandatory = $true)][string] $EnvironmentDigest,
        [Parameter(Mandatory = $true)][string] $TimingPolicyDigest,
        [Parameter(Mandatory = $true)][string] $ParentCommit,
        [Parameter(Mandatory = $true)][object[]] $QualificationDigests,
        [Parameter(Mandatory = $true)][object[]] $FixtureSummaries
    )
    if ($QualificationDigests.Count -ne 5 -or $FixtureSummaries.Count -ne 5) {
        throw "RUN_OPENED requires exactly five qualification records"
    }
    $value = New-SortedMap
    $value["artifact_variant"] = "RUN_OPENED"
    $value["canonical_execution_root"] = $CanonicalLiveRoot
    $value["environment_digest"] = $EnvironmentDigest
    $value["fixture_summaries"] = $FixtureSummaries
    $value["identity_digest"] = $IdentityDigest
    $value["parent_commit"] = $ParentCommit
    $value["qualification_result_digests"] = $QualificationDigests
    $value["result_ref"] = $ResultRef
    $value["run_nonce"] = $RunNonce
    $value["run_state"] = "RUN_OPENED"
    $value["schema_version"] = $ArtifactSchema
    $value["timing_policy_digest"] = $TimingPolicyDigest
    return ConvertTo-CanonicalJson -Value $value
}

function New-FinalEnvelopeJson {
    param(
        [Parameter(Mandatory = $true)][string] $Variant,
        [Parameter(Mandatory = $true)][string] $ExecutionDisposition,
        [AllowNull()][object] $FailureCode,
        [Parameter(Mandatory = $true)][Collections.Generic.SortedDictionary[string,object]] $Identity,
        [Parameter(Mandatory = $true)][string] $EnvironmentDigest,
        [Parameter(Mandatory = $true)][string] $RunNonce,
        [Parameter(Mandatory = $true)][Collections.Generic.SortedDictionary[string,object]] $TimingPolicy,
        [Parameter(Mandatory = $true)][string] $TimingPolicyDigest,
        [Parameter(Mandatory = $true)][object[]] $QualificationDigests,
        [Parameter(Mandatory = $true)][object[]] $FixtureSummaries,
        [AllowNull()][object] $ArchivalChildResult,
        [Parameter(Mandatory = $true)][object] $BatchExecution,
        [Parameter(Mandatory = $true)][object[]] $ProcessGraph,
        [AllowNull()][object] $ResourceEvidence
    )
    if ($Variant -notin @("ORDINARY_RESULT_COMMITTED", "RESOURCE_RESULT_COMMITTED")) {
        throw "final envelope variant is not closed"
    }
    if ($Variant -ceq "RESOURCE_RESULT_COMMITTED" -and $null -eq $ResourceEvidence) {
        throw "resource envelope lacks resource evidence"
    }
    if ($Variant -ceq "ORDINARY_RESULT_COMMITTED" -and $null -ne $ResourceEvidence) {
        throw "ordinary envelope has resource evidence"
    }
    $value = New-SortedMap
    $value["archival_child_result"] = $ArchivalChildResult
    $value["artifact_variant"] = $Variant
    $value["batch_execution"] = $BatchExecution
    $value["environment_digest"] = $EnvironmentDigest
    $value["execution_disposition"] = $ExecutionDisposition
    $value["failure_code"] = $FailureCode
    $value["fixture_summaries"] = $FixtureSummaries
    $value["identity"] = $Identity
    $value["process_graph"] = $ProcessGraph
    $value["qualification_result_digests"] = $QualificationDigests
    if ($Variant -ceq "RESOURCE_RESULT_COMMITTED") { $value["resource_evidence"] = $ResourceEvidence }
    $value["run_nonce"] = $RunNonce
    $value["run_state"] = $Variant
    $value["schema_version"] = $ArtifactSchema
    $value["stopwatch_frequency"] = [int64][Diagnostics.Stopwatch]::Frequency
    $value["timing_policy"] = $TimingPolicy
    $value["timing_policy_digest"] = $TimingPolicyDigest
    return ConvertTo-CanonicalJson -Value $value
}

function Assert-HexDigest {
    param([AllowNull()][object] $Value, [Parameter(Mandatory = $true)][string] $Where)
    if ($Value -isnot [string] -or $Value -cnotmatch '^[0-9A-F]{64}$') { throw "$Where is not uppercase SHA-256" }
}

function Assert-ChildTimingFrames {
    param(
        [Parameter(Mandatory = $true)][object[]] $Frames,
        [Parameter(Mandatory = $true)][bool] $Success
    )
    if ($Frames.Count -gt 8) { throw "child timing frame count is outside the closed prefix" }
    if (-not $Success -and $Frames.Count -eq 0) { return }
    if ($Success -and $Frames.Count -ne 8) { throw "completed child lacks eight timing frames" }
    $frameFields = @(
        "classification", "clock_class", "completed", "elapsed_ns", "end_ns",
        "hard_wall_ns", "request_id", "schema_version", "sequence", "start_ns",
        "success_margin_ns"
    )
    $previousEnd = [int64]-1
    for ($index = 0; $index -lt $Frames.Count; $index++) {
        $frame = $Frames[$index]
        if ((@($frame.PSObject.Properties.Name) -join "`n") -cne ($frameFields -join "`n")) {
            throw "child timing frame field set/order mismatch"
        }
        if ($frame.schema_version -cne $TimingSchema -or $frame.sequence -ne ($index + 1) -or
            $frame.request_id -cne $RequestIds[$index] -or $frame.clock_class -cne $RequestClasses[$index]) {
            throw "child timing frame identity/order changed"
        }
        foreach ($name in @("start_ns", "end_ns", "elapsed_ns", "hard_wall_ns", "success_margin_ns")) {
            if (($frame.$name -isnot [int]) -and ($frame.$name -isnot [long])) { throw "child timing integer is not exact" }
        }
        if ($frame.start_ns -lt 0 -or $frame.start_ns -lt $previousEnd -or $frame.end_ns -lt $frame.start_ns -or
            $frame.elapsed_ns -ne ($frame.end_ns - $frame.start_ns)) { throw "child timing arithmetic failed" }
        $policyRow = $script:TimingPolicy[[string]$frame.clock_class]
        if ($frame.hard_wall_ns -ne $policyRow["hard_wall_ns"] -or
            $frame.success_margin_ns -ne $policyRow["success_margin_ns"]) { throw "child timing wall differs from policy" }
        if ($frame.completed -isnot [bool]) { throw "child timing completed is not bool" }
        $boundaryClass = if ($frame.elapsed_ns -gt $frame.hard_wall_ns) {
            "RESOURCE_BLOCKED"
        } elseif ($frame.elapsed_ns -gt $frame.success_margin_ns) {
            "QUALIFICATION_MARGIN_BLOCKED"
        } else {
            "PASS"
        }
        if ($frame.completed) {
            if ($frame.classification -cne $boundaryClass) { throw "child timing classification is inconsistent" }
        }
        elseif ($index -ne $Frames.Count - 1 -or
            $frame.classification -notin @("FAILED", "RESOURCE_BLOCKED", "QUALIFICATION_MARGIN_BLOCKED") -or
            ($boundaryClass -cne "PASS" -and $frame.classification -cne $boundaryClass)) {
            throw "terminal child timing classification is inconsistent"
        }
        if ($index -lt $Frames.Count - 1 -and (-not $frame.completed -or $frame.classification -cne "PASS")) {
            throw "child timing prefix contains a nonterminal failure"
        }
        $previousEnd = [int64]$frame.end_ns
    }
    if ($Success -and @($Frames | Where-Object { -not $_.completed -or $_.classification -cne "PASS" }).Count -ne 0) {
        throw "completed child contains a blocked timing frame"
    }
}

function Read-ValidatedChildResult {
    param(
        [Parameter(Mandatory = $true)][string] $ChildResultPath,
        [Parameter(Mandatory = $true)][string] $ChildReceiptPath,
        [Parameter(Mandatory = $true)][string] $Nonce,
        [Parameter(Mandatory = $true)][string] $Role,
        [Parameter(Mandatory = $true)][int] $Ordinal,
        [Parameter(Mandatory = $true)][string] $IdentityDigest,
        [Parameter(Mandatory = $true)][string] $EnvironmentDigest,
        [Parameter(Mandatory = $true)][string] $LeafSha256,
        [Parameter(Mandatory = $true)][string] $TimingPolicyJson,
        [Parameter(Mandatory = $true)][string] $TimingPolicyDigest
    )
    $raw = Read-StrictUtf8File -LiteralPath $ChildResultPath -MaximumBytes $ArtifactLimitBytes
    $receiptRaw = Read-StrictUtf8File -LiteralPath $ChildReceiptPath -MaximumBytes $ReceiptLimitBytes
    try { $value = $raw | ConvertFrom-Json; $receipt = $receiptRaw | ConvertFrom-Json }
    catch { throw "child result or receipt is not strict JSON" }

    $fields = @(
        "environment_digest", "failure_code", "fixture_role", "identity_digest", "leaf_sha256",
        "nonce", "payload", "process_ordinal", "resource_evidence", "run_state", "schema_version",
        "scientific_disposition", "timing_frames", "timing_policy", "timing_policy_digest", "transcript",
        "worker_blob", "worker_sha256"
    )
    Assert-ExactCanonicalObject -Value $value -Fields $fields -Raw $raw -Where "child result"
    if ($value.schema_version -cne $ChildResultSchema -or $value.nonce -cne $Nonce -or
        $value.fixture_role -cne $Role -or $value.process_ordinal -ne $Ordinal -or
        $value.run_state -cne "CHILD_RESULT_COMMITTED" -or $value.identity_digest -cne $IdentityDigest -or
        $value.environment_digest -cne $EnvironmentDigest -or $value.leaf_sha256 -cne $LeafSha256 -or
        $value.worker_blob -cne $ExpectedWorkerBlob -or $value.worker_sha256 -cne $ExpectedWorkerSha256 -or
        $value.timing_policy_digest -cne $TimingPolicyDigest -or
        (ConvertTo-CanonicalJson -Value $value.timing_policy) -cne $TimingPolicyJson) {
        throw "child result does not bind the frozen fixture"
    }

    $success = $value.scientific_disposition -ceq "SYNTHETIC_ARCHIVAL_EXECUTION_COMPLETED"
    Assert-ChildTimingFrames -Frames @($value.timing_frames) -Success $success
    if ($success) {
        if ($null -ne $value.failure_code -or $null -eq $value.payload -or $null -ne $value.resource_evidence) {
            throw "successful child contains failure evidence"
        }
        $payloadFields = @(
            "closed", "final_n_states", "init_response_digest", "n_primary_executions",
            "n_replay_executions", "natural_lean_exit_code", "ownership_zero", "request_count",
            "rpc_protocol_version", "shutdown_ack_digest", "transition_response_digest"
        )
        if ((@($value.payload.PSObject.Properties.Name) -join "`n") -cne ($payloadFields -join "`n")) {
            throw "child success payload field set/order changed"
        }
        if ($value.payload.closed -isnot [bool] -or -not $value.payload.closed -or
            $value.payload.final_n_states -ne 0 -or $value.payload.ownership_zero -isnot [bool] -or
            -not $value.payload.ownership_zero -or $value.payload.request_count -ne 8 -or
            $value.payload.natural_lean_exit_code -ne 0 -or $value.payload.n_primary_executions -ne 1 -or
            $value.payload.n_replay_executions -ne 1 -or
            $value.payload.rpc_protocol_version -cne "lean-rgc-jsonl-rpc-v2") {
            throw "child payload does not prove the synthetic fixture"
        }
        foreach ($name in @("init_response_digest", "shutdown_ack_digest", "transition_response_digest")) {
            Assert-HexDigest -Value $value.payload.$name -Where "child semantic response digest"
        }
    }
    else {
        $failureCodes = @{
            SYNTHETIC_BATCH_EXECUTION_FAILED = "BATCH_EXECUTION_FAILED"
            SYNTHETIC_QUALIFICATION_MARGIN_BLOCKED = "QUALIFICATION_MARGIN_BLOCKED"
            SYNTHETIC_EXECUTION_FAILED = "EXECUTION_FAILED"
            SYNTHETIC_IMPORT_BLOCKED = "IMPORT_BLOCKED"
            SYNTHETIC_SCOPE_VIOLATION = "SCOPE_VIOLATION"
            SYNTHETIC_RPC_BLOCKED = "RPC_BLOCKED"
            SYNTHETIC_ARTIFACT_BLOCKED = "ARTIFACT_BLOCKED"
            SYNTHETIC_RESOURCE_BLOCKED = "RESOURCE_BLOCKED"
        }
        if (-not $failureCodes.ContainsKey([string]$value.scientific_disposition) -or
            $value.failure_code -cne $failureCodes[[string]$value.scientific_disposition] -or
            $null -ne $value.payload -or $null -ne $value.transcript) {
            throw "failed child disposition/evidence is inconsistent"
        }
        if ($value.scientific_disposition -ceq "SYNTHETIC_RESOURCE_BLOCKED") {
            $resourceFields = @("cap_name", "cap_value", "observed_value", "stage")
            if ((@($value.resource_evidence.PSObject.Properties.Name) -join "`n") -cne ($resourceFields -join "`n") -or
                $value.resource_evidence.cap_name -isnot [string] -or
                (($value.resource_evidence.cap_value -isnot [int]) -and ($value.resource_evidence.cap_value -isnot [long])) -or
                (($value.resource_evidence.observed_value -isnot [int]) -and ($value.resource_evidence.observed_value -isnot [long])) -or
                $value.resource_evidence.stage -isnot [string] -or
                $value.resource_evidence.cap_value -lt 0 -or
                $value.resource_evidence.observed_value -lt $value.resource_evidence.cap_value) {
                throw "child resource evidence is malformed"
            }
        }
        elseif ($null -ne $value.resource_evidence) { throw "non-resource child has resource evidence" }
    }

    if ($success) {
        $transcriptFields = @(
            "ordered_request_digests", "ordered_response_digests", "ordered_transcript_digest",
            "request_ids", "schema_version"
        )
        if ((@($value.transcript.PSObject.Properties.Name) -join "`n") -cne ($transcriptFields -join "`n") -or
            $value.transcript.schema_version -cne $TranscriptSchema) { throw "child transcript schema changed" }
        Assert-HexDigest -Value $value.transcript.ordered_transcript_digest -Where "transcript digest"
        $transcriptIds = @($value.transcript.request_ids)
        if (($transcriptIds -join "`n") -cne ($RequestIds -join "`n")) { throw "completed transcript request IDs changed" }
        foreach ($digest in @($value.transcript.ordered_request_digests) + @($value.transcript.ordered_response_digests)) {
            Assert-HexDigest -Value $digest -Where "ordered transcript member digest"
        }
        if (@($value.transcript.ordered_request_digests).Count -ne 8 -or
            @($value.transcript.ordered_response_digests).Count -ne 8) { throw "completed transcript length changed" }
        $transcriptRows = [Collections.Generic.List[object]]::new()
        for ($index = 0; $index -lt 8; $index++) {
            $row = New-SortedMap
            $row["request_sha256"] = [string]$value.transcript.ordered_request_digests[$index]
            $row["response_sha256"] = [string]$value.transcript.ordered_response_digests[$index]
            $transcriptRows.Add($row)
        }
        if ((Get-Sha256Text -Text (ConvertTo-CanonicalJson -Value $transcriptRows.ToArray())) -cne
            $value.transcript.ordered_transcript_digest) { throw "ordered transcript digest mismatch" }
    }

    $receiptFields = @(
        "child_result_length", "child_result_sha256", "environment_digest", "fixture_role",
        "identity_digest", "leaf_sha256", "nonce", "process_ordinal", "receipt_kind",
        "schema_version", "timing_policy_digest", "worker_sha256"
    )
    Assert-ExactCanonicalObject -Value $receipt -Fields $receiptFields -Raw $receiptRaw -Where "child receipt" -Depth 16
    $rawLength = [Text.UTF8Encoding]::new($false, $true).GetByteCount($raw)
    $rawSha = Get-Sha256Text -Text $raw
    if ($receipt.schema_version -cne $ReceiptSchema -or $receipt.receipt_kind -cne "CHILD_RESULT" -or
        $receipt.nonce -cne $Nonce -or $receipt.fixture_role -cne $Role -or
        $receipt.process_ordinal -ne $Ordinal -or $receipt.child_result_length -ne $rawLength -or
        $receipt.child_result_sha256 -cne $rawSha -or $receipt.identity_digest -cne $IdentityDigest -or
        $receipt.environment_digest -cne $EnvironmentDigest -or $receipt.leaf_sha256 -cne $LeafSha256 -or
        $receipt.worker_sha256 -cne $ExpectedWorkerSha256 -or
        $receipt.timing_policy_digest -cne $TimingPolicyDigest) {
        throw "child receipt does not bind the child result"
    }
    $out = New-SortedMap
    $out["digest"] = $rawSha
    $out["raw"] = $raw
    $out["success"] = $success
    $out["value"] = $value
    return $out
}

$jobSource = @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
public static class UPrimeOfficialTransportV2Job {
  [StructLayout(LayoutKind.Sequential)] public struct BasicLimit {
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
    public BasicLimit BasicLimitInformation;
    public IO IoInfo;
    public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed;
  }
  [StructLayout(LayoutKind.Sequential)] public struct Accounting {
    public long TotalUserTime, TotalKernelTime, ThisPeriodTotalUserTime, ThisPeriodTotalKernelTime;
    public uint TotalPageFaultCount, TotalProcesses, ActiveProcesses, TotalTerminatedProcesses;
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
  public static ulong Peak(IntPtr h) {
    int size = Marshal.SizeOf(typeof(Extended)); IntPtr mem = Marshal.AllocHGlobal(size);
    try { uint used; if (!QueryInformationJobObject(h, 9, mem, (uint)size, out used)) throw new System.ComponentModel.Win32Exception();
      return ((Extended)Marshal.PtrToStructure(mem, typeof(Extended))).PeakJobMemoryUsed.ToUInt64();
    } finally { Marshal.FreeHGlobal(mem); }
  }
  public static uint Active(IntPtr h) {
    int size = Marshal.SizeOf(typeof(Accounting)); IntPtr mem = Marshal.AllocHGlobal(size);
    try { uint used; if (!QueryInformationJobObject(h, 1, mem, (uint)size, out used)) throw new System.ComponentModel.Win32Exception();
      return ((Accounting)Marshal.PtrToStructure(mem, typeof(Accounting))).ActiveProcesses;
    } finally { Marshal.FreeHGlobal(mem); }
  }
  public static Task<bool> StartAndAssignAsync(Process process, IntPtr job, CancellationToken token) {
    return Task.Run(() => {
      bool started = process.Start();
      if (!started) return false;
      if (token.IsCancellationRequested) { try { process.Kill(); } catch { } return false; }
      if (!AssignProcessToJobObject(job, process.Handle)) {
        try { process.Kill(); } catch { }
        throw new System.ComponentModel.Win32Exception();
      }
      if (token.IsCancellationRequested) { try { process.Kill(); } catch { } return false; }
      return true;
    }, token);
  }
  public static void ReplaceOwned(string source, string destination) {
    if (!MoveFileEx(source, destination, 0x1u | 0x8u)) throw new System.ComponentModel.Win32Exception();
  }
}
'@

function Invoke-V2Fixture {
    param(
        [Parameter(Mandatory = $true)][ValidateSet("QUALIFICATION", "ARCHIVAL")][string] $Role,
        [Parameter(Mandatory = $true)][ValidateRange(1, 6)][int] $Ordinal,
        [Parameter(Mandatory = $true)][int64] $BatchDeadlineTicks
    )
    $fixtureStart = Get-NowTicks
    $fixtureDeadline = New-DeadlineTicks -StartTicks $fixtureStart -WallSeconds 300
    $nonce = [Guid]::NewGuid().ToString("N")
    $runTemp = $null
    $process = $null
    $job = [IntPtr]::Zero
    $stdoutStream = $null
    $stderrStream = $null
    $stdoutTask = $null
    $stderrTask = $null
    $startCancellation = $null
    $readyTiming = $null
    $readyDeadline = $null
    $readyBytes = [int64]0
    $peak = [uint64]0
    try {
        if ((Get-Sha256 -LiteralPath $script:LeafPath) -cne $script:LeafSha256 -or
            (Get-Sha256 -LiteralPath $script:WorkerPath) -cne $ExpectedWorkerSha256 -or
            (Get-GitBlobOid -LiteralPath $script:WorkerPath) -cne $ExpectedWorkerBlob) {
            throw "per-fixture source identity recheck failed"
        }
        Assert-Deadline -DeadlineTicks $BatchDeadlineTicks -Name "batch_execution"
        Assert-Deadline -DeadlineTicks $fixtureDeadline -Name "fixture_execution"

        $systemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd("\", "/")
        $runTemp = [IO.Path]::GetFullPath((Join-Path $systemTemp ($TempPrefix + $nonce)))
        if (-not [IO.Path]::GetFullPath((Split-Path -Parent $runTemp)).TrimEnd("\", "/").Equals(
            $systemTemp, [StringComparison]::OrdinalIgnoreCase)) { throw "fixture temp escaped system temp" }
        [void][IO.Directory]::CreateDirectory($runTemp)
        $childResultPath = Join-Path $runTemp ("uprime_transport_v2_child_result.$nonce.json")
        $childReceiptPath = Join-Path $runTemp ("uprime_transport_v2_child_receipt.$nonce.json")
        $stdoutPath = Join-Path $runTemp "child.stdout"
        $stderrPath = Join-Path $runTemp "child.stderr"

        $childEnvironment = [Collections.Generic.SortedDictionary[string,object]]::new([StringComparer]::Ordinal)
        $childEnvironment["COMSPEC"] = [IO.Path]::GetFullPath($env:ComSpec)
        $childEnvironment["LANG"] = "C.UTF-8"
        $childEnvironment["LC_ALL"] = "C.UTF-8"
        $childEnvironment["PATH"] = ([IO.Path]::GetDirectoryName($script:LeanPath) + ";" + (Join-Path $script:SystemRoot "System32"))
        $childEnvironment["PYTHONDONTWRITEBYTECODE"] = "1"
        $childEnvironment["PYTHONIOENCODING"] = "utf-8"
        $childEnvironment["PYTHONUTF8"] = "1"
        $childEnvironment["SYSTEMROOT"] = $script:SystemRoot
        $childEnvironment["TEMP"] = $runTemp
        $childEnvironment["TMP"] = $runTemp
        $childEnvironment["WINDIR"] = $script:SystemRoot
        $environmentDigest = Get-Sha256Text -Text (ConvertTo-CanonicalJson -Value $childEnvironment)

        $startInfo = [Diagnostics.ProcessStartInfo]::new()
        $startInfo.FileName = $script:PythonPath
        $startInfo.Arguments = ((@("-I", "-S", "-B", $script:LeafPath, "--official-child") |
            ForEach-Object { Quote-NativeArgument -Value $_ }) -join " ")
        $startInfo.WorkingDirectory = $runTemp
        $startInfo.UseShellExecute = $false
        $startInfo.CreateNoWindow = $true
        $startInfo.RedirectStandardInput = $true
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $startInfo.EnvironmentVariables.Clear()
        foreach ($pair in $childEnvironment.GetEnumerator()) { $startInfo.EnvironmentVariables[$pair.Key] = [string]$pair.Value }

        $job = [UPrimeOfficialTransportV2Job]::Create($WorkingSetLimitBytes)
        $process = [Diagnostics.Process]::new()
        $process.StartInfo = $startInfo
        $readyStart = Get-NowTicks
        $readyDeadline = New-DeadlineTicks -StartTicks $readyStart -WallSeconds 15
        $startCancellation = [Threading.CancellationTokenSource]::new()
        $startTask = [UPrimeOfficialTransportV2Job]::StartAndAssignAsync($process, $job, $startCancellation.Token)
        $startRemaining = Get-RemainingMilliseconds -Deadlines @($readyDeadline, $fixtureDeadline, $BatchDeadlineTicks)
        if ($startRemaining -le 0 -or -not $startTask.Wait($startRemaining)) {
            $startCancellation.Cancel()
            throw "Python Start/Job assignment exceeded absolute deadline"
        }
        if (-not $startTask.GetAwaiter().GetResult()) { throw "failed to start and assign exact isolated Python child" }
        $stderrStream = [IO.FileStream]::new($stderrPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
        $stderrTask = $process.StandardError.BaseStream.CopyToAsync($stderrStream)
        $jobReceipt = New-SortedMap
        $jobReceipt["job_assigned"] = $true
        $jobReceipt["job_memory_limit_bytes"] = [int64]$WorkingSetLimitBytes
        $jobReceipt["kill_on_close"] = $true
        $jobReceipt["pid"] = [int]$process.Id
        $jobReceiptDigest = Get-Sha256Text -Text (ConvertTo-CanonicalJson -Value $jobReceipt)
        $probe = "$ProbeSchema|$nonce|$jobReceiptDigest`n"
        if ([Text.Encoding]::ASCII.GetByteCount($probe) -gt $ProbeMaximumBytes) { throw "PROBE exceeds cap" }
        Write-ChildFrameUntil -Stream $process.StandardInput.BaseStream -Text $probe `
            -Deadlines @($readyDeadline, $fixtureDeadline, $BatchDeadlineTicks)

        $readyLine = Read-BoundedUtf8LineUntil -Stream $process.StandardOutput.BaseStream -MaximumBytes $ReadyMaximumBytes `
            -Deadlines @($readyDeadline, $fixtureDeadline, $BatchDeadlineTicks)
        $readyBytes = [int64]([Text.UTF8Encoding]::new($false, $true).GetByteCount($readyLine) + 1)
        try { $ready = $readyLine | ConvertFrom-Json }
        catch { throw "READY is not JSON" }
        $readyFields = @(
            "import_fence_passed", "job_assignment_receipt_digest", "leaf_sha256",
            "loaded_lean_rgc_modules", "nonce", "pid", "python_flags_digest",
            "schema_version", "sys_path_digest"
        )
        Assert-ExactCanonicalObject -Value $ready -Fields $readyFields -Raw $readyLine -Where "READY" -Depth 16
        if ($ready.schema_version -cne $ReadySchema -or $ready.nonce -cne $nonce -or
            $ready.pid -ne $process.Id -or $ready.job_assignment_receipt_digest -cne $jobReceiptDigest -or
            $ready.leaf_sha256 -cne $script:LeafSha256 -or $ready.import_fence_passed -isnot [bool] -or
            -not $ready.import_fence_passed -or @($ready.loaded_lean_rgc_modules).Count -ne 0) {
            throw "READY does not bind the isolated child"
        }
        Assert-HexDigest -Value $ready.python_flags_digest -Where "Python flags digest"
        Assert-HexDigest -Value $ready.sys_path_digest -Where "sys.path digest"
        $readyEnd = Get-NowTicks
        $readyTiming = New-ParentTimingRecord -ClockClass "python_ready" -StartTicks $readyStart -EndTicks $readyEnd `
            -HardWallSeconds 15 -SuccessMarginSeconds 5
        if ($readyTiming["classification"] -cne "PASS") {
            throw "python_ready $($readyTiming['classification'])"
        }
        Assert-Deadline -DeadlineTicks $fixtureDeadline -Name "fixture_execution"
        Assert-Deadline -DeadlineTicks $BatchDeadlineTicks -Name "batch_execution"

        $stdoutStream = [IO.FileStream]::new($stdoutPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
        $stdoutTask = $process.StandardOutput.BaseStream.CopyToAsync($stdoutStream)

        $arm = New-SortedMap
        $arm["action_count"] = 1
        $arm["artifact_limit_bytes"] = $ArtifactLimitBytes
        $arm["child_receipt_path"] = [IO.Path]::GetFullPath($childReceiptPath)
        $arm["child_result_path"] = [IO.Path]::GetFullPath($childResultPath)
        $arm["environment_digest"] = $environmentDigest
        $arm["fixture_role"] = $Role
        $arm["identity"] = $script:Identity
        $arm["lean_executable"] = $script:LeanPath
        $arm["lean_sha256"] = $ExpectedLeanSha256
        $arm["max_open_states"] = 2
        $arm["nonce"] = $nonce
        $arm["process_ordinal"] = $Ordinal
        $arm["receipt_limit_bytes"] = $ReceiptLimitBytes
        $arm["repo_root"] = $script:RepoRoot
        $arm["request_count"] = 8
        $arm["response_limit_bytes"] = $ResponseLimitBytes
        $arm["run_temp"] = $runTemp
        $arm["schema_version"] = $ArmSchema
        $arm["stream_limit_bytes"] = $StreamLimitBytes
        $arm["task_count"] = 1
        $arm["timing_policy"] = $script:TimingPolicy
        $arm["timing_policy_digest"] = $script:TimingPolicyDigest
        $arm["worker_blob"] = $ExpectedWorkerBlob
        $arm["worker_path"] = $script:WorkerPath
        $arm["worker_sha256"] = $ExpectedWorkerSha256
        Write-ChildFrameUntil -Stream $process.StandardInput.BaseStream -Text ((ConvertTo-CanonicalJson -Value $arm) + "`n") `
            -Deadlines @($fixtureDeadline, $BatchDeadlineTicks)

        $capFailure = $null
        while (-not $process.HasExited) {
            $remaining = Get-RemainingMilliseconds -Deadlines @($fixtureDeadline, $BatchDeadlineTicks)
            if ($remaining -le 0) { $capFailure = "fixture_or_batch_wall"; break }
            if ((Get-Item -LiteralPath $stderrPath -Force).Length -gt $StreamLimitBytes -or
                ($readyBytes + (Get-Item -LiteralPath $stdoutPath -Force).Length) -gt $StreamLimitBytes) { $capFailure = "stream_limit"; break }
            try { $peak = [Math]::Max($peak, [UPrimeOfficialTransportV2Job]::Peak($job)) } catch { }
            if ($peak -gt $WorkingSetLimitBytes) { $capFailure = "job_working_set"; break }
            [void]$process.WaitForExit([Math]::Min(100, $remaining))
        }
        if ($null -ne $capFailure -and -not $process.HasExited) {
            [void][UPrimeOfficialTransportV2Job]::CloseHandle($job)
            $job = [IntPtr]::Zero
        }
        $remainingExit = Get-RemainingMilliseconds -Deadlines @($fixtureDeadline, $BatchDeadlineTicks)
        if (-not $process.HasExited -and ($remainingExit -le 0 -or -not $process.WaitForExit($remainingExit))) {
            throw "fixture process failed to exit within its absolute deadline"
        }
        if ($null -ne $stdoutTask) {
            $remaining = Get-RemainingMilliseconds -Deadlines @($fixtureDeadline, $BatchDeadlineTicks)
            if ($remaining -le 0 -or -not $stdoutTask.Wait($remaining)) { throw "stdout drain exceeded absolute deadline" }
        }
        if ($null -ne $stderrTask) {
            $remaining = Get-RemainingMilliseconds -Deadlines @($fixtureDeadline, $BatchDeadlineTicks)
            if ($remaining -le 0 -or -not $stderrTask.Wait($remaining)) { throw "stderr drain exceeded absolute deadline" }
        }
        if ($null -ne $stdoutStream) { $stdoutStream.Flush($true); $stdoutStream.Dispose(); $stdoutStream = $null }
        if ($null -ne $stderrStream) { $stderrStream.Flush($true); $stderrStream.Dispose(); $stderrStream = $null }
        if ($job -ne [IntPtr]::Zero) { $peak = [Math]::Max($peak, [UPrimeOfficialTransportV2Job]::Peak($job)) }
        if ($null -eq $capFailure -and
            ((Get-Item -LiteralPath $stderrPath -Force).Length -gt $StreamLimitBytes -or
             ($readyBytes + (Get-Item -LiteralPath $stdoutPath -Force).Length) -gt $StreamLimitBytes)) {
            $capFailure = "stream_limit"
        }

        if ($null -ne $capFailure) {
            $fixtureEnd = Get-NowTicks
            $fixtureTiming = New-ParentTimingRecord -ClockClass "fixture_execution" -StartTicks $fixtureStart -EndTicks $fixtureEnd `
                -HardWallSeconds 300 -SuccessMarginSeconds 100
            $resource = New-SortedMap
            if ($capFailure -ceq "job_working_set") {
                $resource["cap_name"] = "job_working_set_bytes"
                $resource["cap_value"] = [int64]$WorkingSetLimitBytes
                $resource["observed_value"] = [int64][Math]::Max([int64]$peak, [int64]$WorkingSetLimitBytes)
            }
            elseif ($capFailure -ceq "stream_limit") {
                $observedStream = [int64][Math]::Max(
                    (Get-Item -LiteralPath $stderrPath -Force).Length,
                    $readyBytes + (Get-Item -LiteralPath $stdoutPath -Force).Length
                )
                $resource["cap_name"] = "stream_bytes"
                $resource["cap_value"] = [int64]$StreamLimitBytes
                $resource["observed_value"] = $observedStream
            }
            else {
                $nowTicks = Get-NowTicks
                $expiredDeadline = if ($nowTicks -gt $BatchDeadlineTicks) { $BatchDeadlineTicks } else { $fixtureDeadline }
                $resource["cap_name"] = if ($expiredDeadline -eq $BatchDeadlineTicks) { "batch_absolute_deadline_ticks" } else { "fixture_absolute_deadline_ticks" }
                $resource["cap_value"] = [int64]$expiredDeadline
                $resource["observed_value"] = [int64][Math]::Max($nowTicks, $expiredDeadline + 1)
            }
            $resource["stage"] = "parent_fixture_monitor"
            $failure = New-SortedMap
            $failure["child"] = $null
            $failure["disposition"] = "SYNTHETIC_RESOURCE_BLOCKED"
            $failure["failure_code"] = "RESOURCE_BLOCKED"
            $failure["fixture_timing"] = $fixtureTiming
            $failure["process_ordinal"] = $Ordinal
            $failure["resource_evidence"] = $resource
            $failure["role"] = $Role
            $failure["success"] = $false
            return $failure
        }

        $child = Read-ValidatedChildResult -ChildResultPath $childResultPath -ChildReceiptPath $childReceiptPath `
            -Nonce $nonce -Role $Role -Ordinal $Ordinal -IdentityDigest $script:IdentityDigest `
            -EnvironmentDigest $environmentDigest -LeafSha256 $script:LeafSha256 `
            -TimingPolicyJson $script:TimingPolicyJson -TimingPolicyDigest $script:TimingPolicyDigest
        $expectedChildExit = switch ([string]$child["value"].scientific_disposition) {
            "SYNTHETIC_ARCHIVAL_EXECUTION_COMPLETED" { 0 }
            "SYNTHETIC_BATCH_EXECUTION_FAILED" { 69 }
            "SYNTHETIC_EXECUTION_FAILED" { 70 }
            "SYNTHETIC_IMPORT_BLOCKED" { 71 }
            "SYNTHETIC_SCOPE_VIOLATION" { 72 }
            "SYNTHETIC_RPC_BLOCKED" { 73 }
            "SYNTHETIC_RESOURCE_BLOCKED" { 74 }
            "SYNTHETIC_ARTIFACT_BLOCKED" { 75 }
            "SYNTHETIC_QUALIFICATION_MARGIN_BLOCKED" { 76 }
            default { -1 }
        }
        if ($process.ExitCode -ne $expectedChildExit) { throw "child exit code disagrees with its transient result" }
        $fixtureEnd = Get-NowTicks
        $fixtureTiming = New-ParentTimingRecord -ClockClass "fixture_execution" -StartTicks $fixtureStart -EndTicks $fixtureEnd `
            -HardWallSeconds 300 -SuccessMarginSeconds 100
        $active = if ($job -eq [IntPtr]::Zero) { 0 } else { [int][UPrimeOfficialTransportV2Job]::Active($job) }
        if ($active -ne 0) { throw "Job orphan-zero assertion failed" }

        $summary = New-SortedMap
        $summary["child_result_sha256"] = $child["digest"]
        $summary["child_timing_frames"] = @($child["value"].timing_frames)
        $summary["environment_digest"] = $environmentDigest
        $summary["fixture_execution"] = $fixtureTiming
        $summary["fixture_role"] = $Role
        $summary["job_orphan_zero"] = $true
        $summary["job_peak_memory_bytes"] = [int64]$peak
        $summary["process_ordinal"] = $Ordinal
        $summary["python_pid"] = [int]$process.Id
        $summary["python_ready"] = $readyTiming

        $node = New-SortedMap
        $node["child_result_sha256"] = $child["digest"]
        $node["fixture_role"] = $Role
        $node["job_assigned_before_probe"] = $true
        $node["job_orphan_zero"] = $true
        $node["process_ordinal"] = $Ordinal
        $node["python_pid"] = [int]$process.Id

        $disposition = [string]$child["value"].scientific_disposition
        $failureCode = $child["value"].failure_code
        $success = [bool]$child["success"]
        if ($fixtureTiming["classification"] -ceq "RESOURCE_BLOCKED") {
            $disposition = "SYNTHETIC_RESOURCE_BLOCKED"; $failureCode = "FIXTURE_EXECUTION_HARD_WALL"; $success = $false
            $parentResource = New-SortedMap
            $parentResource["cap_name"] = "fixture_execution_ticks"
            $parentResource["cap_value"] = [int64](300 * [Diagnostics.Stopwatch]::Frequency)
            $parentResource["observed_value"] = [int64]$fixtureTiming["elapsed_ticks"]
            $parentResource["stage"] = "parent_fixture_validation"
        }
        elseif ($fixtureTiming["classification"] -ceq "QUALIFICATION_MARGIN_BLOCKED") {
            $disposition = "SYNTHETIC_QUALIFICATION_MARGIN_BLOCKED"; $failureCode = "FIXTURE_EXECUTION_MARGIN_BLOCKED"; $success = $false
        }
        $out = New-SortedMap
        $out["child"] = $child["value"]
        $out["digest"] = $child["digest"]
        $out["disposition"] = $disposition
        $out["failure_code"] = $failureCode
        $out["fixture_timing"] = $fixtureTiming
        $out["process_node"] = $node
        $out["resource_evidence"] = if ($fixtureTiming["classification"] -ceq "RESOURCE_BLOCKED") {
            $parentResource
        } else {
            $child["value"].resource_evidence
        }
        $out["role"] = $Role
        $out["success"] = $success
        $out["summary"] = $summary
        return $out
    }
    catch {
        if ($null -ne $startCancellation) { try { $startCancellation.Cancel() } catch { } }
        if ($job -ne [IntPtr]::Zero) { try { [void][UPrimeOfficialTransportV2Job]::CloseHandle($job) } catch { }; $job = [IntPtr]::Zero }
        if ($null -ne $process) { try { if (-not $process.HasExited) { $process.Kill() } } catch { } }
        $fixtureEnd = Get-NowTicks
        $fixtureTiming = New-ParentTimingRecord -ClockClass "fixture_execution" -StartTicks $fixtureStart -EndTicks $fixtureEnd `
            -HardWallSeconds 300 -SuccessMarginSeconds 100
        $out = New-SortedMap
        $out["child"] = $null
        $out["disposition"] = if ($_.Exception.Message -match 'QUALIFICATION_MARGIN_BLOCKED') {
            "SYNTHETIC_QUALIFICATION_MARGIN_BLOCKED"
        } elseif ($_.Exception.Message -match 'wall|deadline') {
            "SYNTHETIC_RESOURCE_BLOCKED"
        } else {
            "SYNTHETIC_EXECUTION_FAILED"
        }
        $out["failure_code"] = if ($_.Exception.Message -match 'QUALIFICATION_MARGIN_BLOCKED') {
            "QUALIFICATION_MARGIN_BLOCKED"
        } elseif ($_.Exception.Message -match 'wall|deadline') {
            "RESOURCE_BLOCKED"
        } else {
            "EXECUTION_FAILED"
        }
        $out["fixture_timing"] = $fixtureTiming
        if ($out["disposition"] -ceq "SYNTHETIC_RESOURCE_BLOCKED") {
            $nowTicks = Get-NowTicks
            $activeDeadline = if ($null -ne $readyDeadline -and $nowTicks -gt $readyDeadline) {
                [int64]$readyDeadline
            } elseif ($nowTicks -gt $BatchDeadlineTicks) {
                [int64]$BatchDeadlineTicks
            } else {
                [int64]$fixtureDeadline
            }
            $resource = New-SortedMap
            $resource["cap_name"] = "active_absolute_deadline_ticks"
            $resource["cap_value"] = $activeDeadline
            $resource["observed_value"] = [int64][Math]::Max($nowTicks, $activeDeadline + 1)
            $resource["stage"] = "parent_fixture_exception"
            $out["resource_evidence"] = $resource
        }
        else { $out["resource_evidence"] = $null }
        $out["role"] = $Role
        $out["success"] = $false
        $out["failure_message"] = $_.Exception.Message
        return $out
    }
    finally {
        if ($null -ne $startCancellation) { try { $startCancellation.Dispose() } catch { } }
        if ($job -ne [IntPtr]::Zero) { try { [void][UPrimeOfficialTransportV2Job]::CloseHandle($job) } catch { } }
        if ($null -ne $stdoutStream) { try { $stdoutStream.Dispose() } catch { } }
        if ($null -ne $stderrStream) { try { $stderrStream.Dispose() } catch { } }
        if ($null -ne $runTemp -and (Test-Path -LiteralPath $runTemp)) {
            try {
                $resolved = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $runTemp).ProviderPath)
                $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd("\", "/")
                if (-not [IO.Path]::GetFullPath((Split-Path -Parent $resolved)).TrimEnd("\", "/").Equals(
                    $tempRoot, [StringComparison]::OrdinalIgnoreCase) -or
                    -not [IO.Path]::GetFileName($resolved).StartsWith($TempPrefix, [StringComparison]::Ordinal)) {
                    throw "refusing to clean an unowned fixture temp"
                }
                Remove-Item -LiteralPath $resolved -Recurse -Force
            }
            catch { Write-RunnerError $_.Exception.Message }
        }
    }
}

function Publish-ParentEnvelope {
    param(
        [Parameter(Mandatory = $true)][string] $EnvelopeJson,
        [Parameter(Mandatory = $true)][string] $ExpectedMarkerJson,
        [Parameter(Mandatory = $true)][string] $ResultPath,
        [Parameter(Mandatory = $true)][string] $StagePath,
        [Parameter(Mandatory = $true)][string] $ReceiptPath,
        [Parameter(Mandatory = $true)][string] $RunNonce,
        [Parameter(Mandatory = $true)][string] $IdentityDigest,
        [Parameter(Mandatory = $true)][string] $EnvironmentDigest,
        [Parameter(Mandatory = $true)][string] $TimingPolicyDigest,
        [Parameter(Mandatory = $true)][int64] $PublicationStartTicks,
        [Parameter(Mandatory = $true)][int64] $PublicationDeadlineTicks
    )
    if (Test-Path -LiteralPath $StagePath) { throw "parent publication stage exists" }
    if (Test-Path -LiteralPath $ReceiptPath) { throw "parent publication receipt exists" }
    Write-DurableExclusiveUtf8 -LiteralPath $StagePath -Text $EnvelopeJson -MaximumBytes $ArtifactLimitBytes
    Assert-Deadline -DeadlineTicks $PublicationDeadlineTicks -Name "artifact_publication"
    $stageLength = [Text.UTF8Encoding]::new($false, $true).GetByteCount($EnvelopeJson)
    $stageSha = Get-Sha256Text -Text $EnvelopeJson
    $envelope = $EnvelopeJson | ConvertFrom-Json
    $envelopeFields = @(
        "archival_child_result", "artifact_variant", "batch_execution", "environment_digest",
        "execution_disposition", "failure_code", "fixture_summaries", "identity", "process_graph",
        "qualification_result_digests"
    )
    if ($envelope.artifact_variant -ceq "RESOURCE_RESULT_COMMITTED") { $envelopeFields += "resource_evidence" }
    $envelopeFields += @(
        "run_nonce", "run_state", "schema_version", "stopwatch_frequency", "timing_policy",
        "timing_policy_digest"
    )
    Assert-ExactCanonicalObject -Value $envelope -Fields $envelopeFields -Raw $EnvelopeJson -Where "parent envelope"
    $receipt = New-SortedMap
    $receipt["artifact_length"] = $stageLength
    $receipt["artifact_sha256"] = $stageSha
    $receipt["artifact_variant"] = $envelope.artifact_variant
    $receipt["environment_digest"] = $EnvironmentDigest
    $receipt["identity_digest"] = $IdentityDigest
    $receipt["receipt_kind"] = "PARENT_PUBLICATION"
    $receipt["run_nonce"] = $RunNonce
    $receipt["schema_version"] = $ReceiptSchema
    $receipt["timing_policy_digest"] = $TimingPolicyDigest
    $receiptJson = ConvertTo-CanonicalJson -Value $receipt
    Write-DurableExclusiveUtf8 -LiteralPath $ReceiptPath -Text $receiptJson -MaximumBytes $ReceiptLimitBytes
    Assert-Deadline -DeadlineTicks $PublicationDeadlineTicks -Name "artifact_publication"
    if ((Read-StrictUtf8File -LiteralPath $StagePath -MaximumBytes $ArtifactLimitBytes) -cne $EnvelopeJson -or
        (Read-StrictUtf8File -LiteralPath $ReceiptPath -MaximumBytes $ReceiptLimitBytes) -cne $receiptJson -or
        (Get-Sha256 -LiteralPath $StagePath) -cne $stageSha) { throw "parent stage/receipt double-hash failed" }
    if ((Read-StrictUtf8File -LiteralPath $ResultPath -MaximumBytes $ArtifactLimitBytes) -cne $ExpectedMarkerJson) {
        throw "owned marker changed before final replacement"
    }
    [UPrimeOfficialTransportV2Job]::ReplaceOwned($StagePath, $ResultPath)
    Flush-DurableFile -LiteralPath $ResultPath
    if ((Read-StrictUtf8File -LiteralPath $ResultPath -MaximumBytes $ArtifactLimitBytes) -cne $EnvelopeJson) {
        throw "final artifact reread differs"
    }
    $publicationEnd = Get-NowTicks
    $timing = New-ParentTimingRecord -ClockClass "artifact_publication" -StartTicks $PublicationStartTicks -EndTicks $publicationEnd `
        -HardWallSeconds 30 -SuccessMarginSeconds 10
    if (Test-Path -LiteralPath $ReceiptPath) { Remove-Item -LiteralPath $ReceiptPath -Force }
    if ((Test-Path -LiteralPath $StagePath) -or (Test-Path -LiteralPath $ReceiptPath)) { throw "publication residue is nonzero" }
    $out = New-SortedMap
    $out["artifact_sha256"] = $stageSha
    $out["timing"] = $timing
    return $out
}

$unboundCount = if ($null -eq $MyInvocation.UnboundArguments) { 0 } else { @($MyInvocation.UnboundArguments).Count }
$unexpectedCount = if ($null -eq $UnexpectedArguments) { 0 } else { @($UnexpectedArguments).Count }
if ($PSBoundParameters.Count -ne 0 -or $unboundCount -ne 0 -or $unexpectedCount -ne 0) {
    Write-RunnerError "arguments are forbidden"
    exit $ExitUsage
}

$script:TimingPolicy = New-TimingPolicy
$script:TimingPolicyJson = ConvertTo-CanonicalJson -Value $script:TimingPolicy
$script:TimingPolicyDigest = Get-Sha256Text -Text $script:TimingPolicyJson
$script:Identity = $null
$script:IdentityDigest = $null
$script:RepoRoot = $null
$script:LeafPath = $null
$script:LeafSha256 = $null
$script:WorkerPath = $null
$script:PythonPath = $null
$script:LeanPath = $null
$script:SystemRoot = $null

$batchStart = Get-NowTicks
$batchDeadline = New-DeadlineTicks -StartTicks $batchStart -WallSeconds 1200
$mutex = $null
$mutexOwned = $false
$markerOwned = $false
$markerJson = $null
$resultPath = $null
$parentStagePath = $null
$parentReceiptPath = $null
$runNonce = $null
$publicationStart = $null
$publicationDeadline = $null
$publicationCompleted = $false
$exitCode = $ExitPreflight

try {
    if ($env:OS -cne "Windows_NT" -or -not [Environment]::Is64BitOperatingSystem -or
        -not [Environment]::Is64BitProcess -or
        [Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString() -cne "X64") {
        throw "official transport v2 requires 64-bit Windows x86-64"
    }
    if ($PSVersionTable.PSEdition -cne "Desktop" -or $PSVersionTable.PSVersion.ToString() -cne $ExpectedPowerShellVersion) {
        throw "Windows PowerShell identity changed"
    }
    if ($null -eq ("UPrimeOfficialTransportV2Job" -as [type])) { Add-Type -TypeDefinition $jobSource -Language CSharp }

    $powerShellPath = Resolve-RegularFile -LiteralPath (Join-Path $PSHOME "powershell.exe") -RequiredRoot $PSHOME
    if ((Get-Sha256 -LiteralPath $powerShellPath) -cne $ExpectedPowerShellSha256) { throw "PowerShell digest changed" }
    if ([string]::IsNullOrWhiteSpace($PSCommandPath)) { throw "script path is unavailable" }
    $scriptPath = Resolve-RegularFile -LiteralPath $PSCommandPath -RequiredRoot (Split-Path -Parent $PSCommandPath)
    $toolsPath = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Split-Path -Parent $scriptPath)).ProviderPath)
    $script:RepoRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Join-Path $toolsPath "..")).ProviderPath).TrimEnd("\", "/")
    if (-not $script:RepoRoot.Equals($CanonicalLiveRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "runner is outside the registered canonical live root"
    }
    $expectedScript = [IO.Path]::GetFullPath((Join-Path $script:RepoRoot "tools\run_uprime_official_transport_v2_smoke.ps1"))
    if (-not $scriptPath.Equals($expectedScript, [StringComparison]::OrdinalIgnoreCase)) { throw "runner path is not canonical" }
    foreach ($marker in @(".git", "pyproject.toml", "lean_rgc", "tests", "tools")) {
        if (-not (Test-Path -LiteralPath (Join-Path $script:RepoRoot $marker))) { throw "repository marker missing: $marker" }
    }

    foreach ($legacy in @([Environment]::GetEnvironmentVariables("Process").Keys | Where-Object { [string]$_ -like "UPRIME_OFFICIAL_TRANSPORT_Q1*" })) {
        throw "legacy Q1 control input is forbidden: $legacy"
    }
    $controlNames = @(
        "UPRIME_OFFICIAL_TRANSPORT_V2_I1_ACCEPTED_COMMIT",
        "UPRIME_OFFICIAL_TRANSPORT_V2_I1_ACCEPTED_TREE",
        "UPRIME_OFFICIAL_TRANSPORT_V2_I1_ACCEPTED_RUN_ID",
        "UPRIME_OFFICIAL_TRANSPORT_V2_I1_ACCEPTED_JOB_ID",
        "UPRIME_OFFICIAL_TRANSPORT_V2_I1_CANDIDATE_RUN_ID",
        "UPRIME_OFFICIAL_TRANSPORT_V2_I1_CANDIDATE_JOB_ID"
    )
    $control = [ordered]@{}
    foreach ($name in $controlNames) {
        $value = [Environment]::GetEnvironmentVariable($name, "Process")
        if ([string]::IsNullOrWhiteSpace($value)) { throw "missing external I1 attestation: $name" }
        if ($name.EndsWith("COMMIT") -or $name.EndsWith("TREE")) {
            if ($value -cnotmatch '^[0-9a-f]{40}$') { throw "malformed I1 hex attestation: $name" }
        }
        elseif ($value -cnotmatch '^[1-9][0-9]*$') { throw "malformed I1 numeric attestation: $name" }
        $control[$name] = $value
    }
    $expectedDigestJson = [Environment]::GetEnvironmentVariable(
        "UPRIME_OFFICIAL_TRANSPORT_V2_I1_EXPECTED_FILE_DIGESTS_JSON", "Process"
    )
    if ([string]::IsNullOrWhiteSpace($expectedDigestJson) -or $expectedDigestJson.Length -gt 4096) {
        throw "missing or oversized I1 digest attestation"
    }

    $acceptedCommit = [string]$control["UPRIME_OFFICIAL_TRANSPORT_V2_I1_ACCEPTED_COMMIT"]
    $acceptedTree = [string]$control["UPRIME_OFFICIAL_TRANSPORT_V2_I1_ACCEPTED_TREE"]
    $gitTopLevel = [IO.Path]::GetFullPath((Invoke-GitScalar -Root $script:RepoRoot -Arguments @("rev-parse", "--show-toplevel"))).TrimEnd("\", "/")
    if ((Invoke-GitScalar -Root $script:RepoRoot -Arguments @("rev-parse", "--abbrev-ref", "HEAD")) -cne $ResultRef -or
        (Invoke-GitScalar -Root $script:RepoRoot -Arguments @("rev-parse", "HEAD")) -cne $acceptedCommit -or
        (Invoke-GitScalar -Root $script:RepoRoot -Arguments @("rev-parse", "HEAD^{tree}")) -cne $acceptedTree -or
        -not $gitTopLevel.Equals($CanonicalLiveRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "canonical result worktree ref/parent/tree changed"
    }
    $status = @(& git -C $script:RepoRoot status --porcelain=v1 --untracked-files=all 2>&1)
    if ($LASTEXITCODE -ne 0 -or $status.Count -ne 0) { throw "canonical result worktree is not clean before BATCH_OPENED" }

    $script:PythonPath = Resolve-RegularFile -LiteralPath "C:\Python313\python.exe" -RequiredRoot "C:\Python313"
    if ((Get-Item -LiteralPath $script:PythonPath -Force).VersionInfo.FileVersion -cne $ExpectedPythonVersion -or
        (Get-Sha256 -LiteralPath $script:PythonPath) -cne $ExpectedPythonSha256) { throw "Python identity changed" }
    $leanRoot = [IO.Path]::GetFullPath((Join-Path $env:USERPROFILE ".elan\toolchains\leanprover--lean4---v4.31.0"))
    $script:LeanPath = Resolve-RegularFile -LiteralPath (Join-Path $leanRoot "bin\lean.exe") -RequiredRoot $leanRoot
    if ((Get-Sha256 -LiteralPath $script:LeanPath) -cne $ExpectedLeanSha256) { throw "Lean identity changed" }
    $script:WorkerPath = Resolve-RegularFile -LiteralPath (Join-Path $script:RepoRoot "lean_rgc\native_lean\RGCKernelRPC.lean") -RequiredRoot $script:RepoRoot
    if ((Get-GitBlobOid -LiteralPath $script:WorkerPath) -cne $ExpectedWorkerBlob -or
        (Get-Sha256 -LiteralPath $script:WorkerPath) -cne $ExpectedWorkerSha256) { throw "worker identity changed" }
    $script:LeafPath = Resolve-RegularFile -LiteralPath (Join-Path $script:RepoRoot "tools\uprime_official_transport_v2_smoke.py") -RequiredRoot $script:RepoRoot

    $actualDigests = New-SortedMap
    foreach ($relative in $I1Allowlist) {
        $path = Resolve-RegularFile -LiteralPath (Join-Path $script:RepoRoot $relative) -RequiredRoot $script:RepoRoot
        $actualDigests[$relative] = Get-Sha256 -LiteralPath $path
    }
    try { $expectedDigestValue = $expectedDigestJson | ConvertFrom-Json }
    catch { throw "I1 digest attestation is not JSON" }
    if ((@($expectedDigestValue.PSObject.Properties.Name) -join "`n") -cne (($I1Allowlist | Sort-Object) -join "`n")) {
        throw "I1 digest path set changed"
    }
    $expectedDigests = New-SortedMap
    foreach ($relative in $I1Allowlist) {
        $digest = $expectedDigestValue.PSObject.Properties[$relative].Value
        Assert-HexDigest -Value $digest -Where "I1 file digest"
        $expectedDigests[$relative] = $digest
    }
    if ((ConvertTo-CanonicalJson -Value $expectedDigests) -cne $expectedDigestJson -or
        (ConvertTo-CanonicalJson -Value $actualDigests) -cne $expectedDigestJson) {
        throw "accepted-tree I1 files differ from external digests"
    }
    $script:LeafSha256 = [string]$actualDigests["tools/uprime_official_transport_v2_smoke.py"]

    $script:Identity = New-SortedMap
    $script:Identity["accepted_commit"] = $acceptedCommit
    $script:Identity["accepted_job_id"] = $control["UPRIME_OFFICIAL_TRANSPORT_V2_I1_ACCEPTED_JOB_ID"]
    $script:Identity["accepted_run_id"] = $control["UPRIME_OFFICIAL_TRANSPORT_V2_I1_ACCEPTED_RUN_ID"]
    $script:Identity["accepted_tree"] = $acceptedTree
    $script:Identity["attestation_scope"] = $AttestationScope
    $script:Identity["candidate_job_id"] = $control["UPRIME_OFFICIAL_TRANSPORT_V2_I1_CANDIDATE_JOB_ID"]
    $script:Identity["candidate_run_id"] = $control["UPRIME_OFFICIAL_TRANSPORT_V2_I1_CANDIDATE_RUN_ID"]
    $script:Identity["i1_file_sha256"] = $actualDigests
    $script:Identity["lean_commit"] = $ExpectedLeanCommit
    $script:Identity["lean_sha256"] = $ExpectedLeanSha256
    $script:Identity["lean_version"] = $ExpectedLeanVersion
    $script:Identity["powershell_sha256"] = $ExpectedPowerShellSha256
    $script:Identity["powershell_version"] = $ExpectedPowerShellVersion
    $script:Identity["python_sha256"] = $ExpectedPythonSha256
    $script:Identity["python_version"] = $ExpectedPythonVersion
    $script:Identity["worker_blob"] = $ExpectedWorkerBlob
    $script:Identity["worker_sha256"] = $ExpectedWorkerSha256
    $identityJson = ConvertTo-CanonicalJson -Value $script:Identity
    $script:IdentityDigest = Get-Sha256Text -Text $identityJson
    $script:SystemRoot = [IO.Path]::GetFullPath($env:SystemRoot)
    $runEnvironment = New-SortedMap
    $runEnvironment["canonical_execution_root"] = $CanonicalLiveRoot
    $runEnvironment["result_ref"] = $ResultRef
    $runEnvironment["timing_policy_digest"] = $script:TimingPolicyDigest
    $runEnvironmentDigest = Get-Sha256Text -Text (ConvertTo-CanonicalJson -Value $runEnvironment)

    Assert-Deadline -DeadlineTicks $batchDeadline -Name "batch_execution"
    $artifactDirectory = [IO.Path]::GetFullPath((Join-Path $script:RepoRoot "docs\experiments\artifacts\uprime_official_transport_v2_20260713"))
    if (-not (Test-Path -LiteralPath $artifactDirectory)) { [void][IO.Directory]::CreateDirectory($artifactDirectory) }
    $artifactItem = Get-Item -LiteralPath $artifactDirectory -Force
    if (-not $artifactItem.PSIsContainer -or (($artifactItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
        throw "artifact directory is not an owned non-reparse directory"
    }
    $resultPath = [IO.Path]::GetFullPath((Join-Path $artifactDirectory "synthetic_qualification.json"))
    $runNonce = [Guid]::NewGuid().ToString("N")
    $parentStagePath = [IO.Path]::GetFullPath((Join-Path $artifactDirectory ("synthetic_qualification.json.stage." + $runNonce)))
    $parentReceiptPath = [IO.Path]::GetFullPath((Join-Path $artifactDirectory ("synthetic_qualification.json.receipt." + $runNonce)))
    $publicationResidue = @(Get-ChildItem -LiteralPath $artifactDirectory -Force | Where-Object {
        $_.Name -ceq "synthetic_qualification.json" -or
        $_.Name -like "synthetic_qualification.json.stage.*" -or
        $_.Name -like "synthetic_qualification.json.receipt.*"
    })
    if ($publicationResidue.Count -ne 0) {
        throw "fixed final/stage/receipt namespace is not absent"
    }

    $mutexName = "Local\LeanRGC-UPrimeOfficialTransportV2-" + (Get-Sha256Text -Text $resultPath.ToLowerInvariant())
    $mutex = [Threading.Mutex]::new($false, $mutexName)
    $mutexWait = Get-RemainingMilliseconds -Deadlines @($batchDeadline)
    if ($mutexWait -le 0) { throw "batch deadline expired before mutex" }
    try { $mutexOwned = $mutex.WaitOne($mutexWait, $false) }
    catch [Threading.AbandonedMutexException] { $mutexOwned = $true }
    if (-not $mutexOwned) { throw "mutex wait consumed the batch deadline" }
    Assert-Deadline -DeadlineTicks $batchDeadline -Name "batch_execution"
    $publicationResidue = @(Get-ChildItem -LiteralPath $artifactDirectory -Force | Where-Object {
        $_.Name -ceq "synthetic_qualification.json" -or
        $_.Name -like "synthetic_qualification.json.stage.*" -or
        $_.Name -like "synthetic_qualification.json.receipt.*"
    })
    if ($publicationResidue.Count -ne 0) {
        throw "final/stage/receipt appeared under mutex"
    }

    $markerJson = New-BatchMarkerJson -RunNonce $runNonce -IdentityDigest $script:IdentityDigest `
        -EnvironmentDigest $runEnvironmentDigest -TimingPolicyDigest $script:TimingPolicyDigest -ParentCommit $acceptedCommit
    Write-DurableExclusiveUtf8 -LiteralPath $resultPath -Text $markerJson
    if ((Read-StrictUtf8File -LiteralPath $resultPath -MaximumBytes $ArtifactLimitBytes) -cne $markerJson) {
        throw "BATCH_OPENED durable reread failed"
    }
    $markerOwned = $true
    Assert-Deadline -DeadlineTicks $batchDeadline -Name "batch_execution"

    $qualificationDigests = [Collections.Generic.List[object]]::new()
    $fixtureSummaries = [Collections.Generic.List[object]]::new()
    $processGraph = [Collections.Generic.List[object]]::new()
    $terminal = $null
    $archive = $null
    for ($ordinal = 1; $ordinal -le 5; $ordinal++) {
        $terminal = New-BatchBlockResult -BatchStartTicks $batchStart
        if ($null -ne $terminal) { break }
        $fixture = Invoke-V2Fixture -Role "QUALIFICATION" -Ordinal $ordinal -BatchDeadlineTicks $batchDeadline
        if ($fixture.ContainsKey("summary")) { $fixtureSummaries.Add($fixture["summary"]) }
        if ($fixture.ContainsKey("process_node")) { $processGraph.Add($fixture["process_node"]) }
        if (-not $fixture["success"]) { $terminal = $fixture; break }
        $qualificationDigests.Add($fixture["digest"])
    }

    if ($null -eq $terminal) {
        $terminal = New-BatchBlockResult -BatchStartTicks $batchStart
    }

    if ($null -eq $terminal -and $qualificationDigests.Count -eq 5) {
        $runMarkerJson = New-RunMarkerJson -RunNonce $runNonce -IdentityDigest $script:IdentityDigest `
            -EnvironmentDigest $runEnvironmentDigest -TimingPolicyDigest $script:TimingPolicyDigest -ParentCommit $acceptedCommit `
            -QualificationDigests $qualificationDigests.ToArray() -FixtureSummaries $fixtureSummaries.ToArray()
        Write-DurableExclusiveUtf8 -LiteralPath $parentStagePath -Text $runMarkerJson
        if ((Read-StrictUtf8File -LiteralPath $resultPath -MaximumBytes $ArtifactLimitBytes) -cne $markerJson) {
            throw "owned BATCH_OPENED changed before RUN_OPENED"
        }
        [UPrimeOfficialTransportV2Job]::ReplaceOwned($parentStagePath, $resultPath)
        Flush-DurableFile -LiteralPath $resultPath
        if ((Read-StrictUtf8File -LiteralPath $resultPath -MaximumBytes $ArtifactLimitBytes) -cne $runMarkerJson) {
            throw "RUN_OPENED durable reread failed"
        }
        $markerJson = $runMarkerJson
        $terminal = New-BatchBlockResult -BatchStartTicks $batchStart
        if ($null -eq $terminal) {
            $archive = Invoke-V2Fixture -Role "ARCHIVAL" -Ordinal 6 -BatchDeadlineTicks $batchDeadline
            if ($archive.ContainsKey("summary")) { $fixtureSummaries.Add($archive["summary"]) }
            if ($archive.ContainsKey("process_node")) { $processGraph.Add($archive["process_node"]) }
            if (-not $archive["success"]) { $terminal = $archive }
        }
    }

    $batchEnd = Get-NowTicks
    $batchTiming = New-ParentTimingRecord -ClockClass "batch_execution" -StartTicks $batchStart -EndTicks $batchEnd `
        -HardWallSeconds 1200 -SuccessMarginSeconds 400
    $disposition = if ($null -ne $terminal) { [string]$terminal["disposition"] } else { "SYNTHETIC_ARCHIVAL_EXECUTION_COMPLETED" }
    $failureCode = if ($null -ne $terminal) { $terminal["failure_code"] } else { $null }
    $resourceEvidence = if ($null -ne $terminal -and $terminal.ContainsKey("resource_evidence")) { $terminal["resource_evidence"] } else { $null }
    if ($batchTiming["classification"] -ceq "RESOURCE_BLOCKED") {
        $disposition = "SYNTHETIC_RESOURCE_BLOCKED"; $failureCode = "BATCH_EXECUTION_HARD_WALL"
        $resourceEvidence = New-SortedMap
        $resourceEvidence["cap_name"] = "batch_execution"
        $resourceEvidence["cap_value"] = [int64](1200 * [Diagnostics.Stopwatch]::Frequency)
        $resourceEvidence["observed_value"] = [int64]$batchTiming["elapsed_ticks"]
        $resourceEvidence["stage"] = "parent_batch"
    }
    elseif ($null -eq $terminal -and $batchTiming["classification"] -ceq "QUALIFICATION_MARGIN_BLOCKED") {
        $disposition = "SYNTHETIC_QUALIFICATION_MARGIN_BLOCKED"; $failureCode = "BATCH_EXECUTION_MARGIN_BLOCKED"
    }
    $variant = if ($disposition -ceq "SYNTHETIC_RESOURCE_BLOCKED") { "RESOURCE_RESULT_COMMITTED" } else { "ORDINARY_RESULT_COMMITTED" }
    $archivalChild = if ($null -ne $archive -and $archive.ContainsKey("child")) { $archive["child"] } else { $null }

    $publicationStart = Get-NowTicks
    $publicationDeadline = New-DeadlineTicks -StartTicks $publicationStart -WallSeconds 30
    $envelopeJson = New-FinalEnvelopeJson -Variant $variant -ExecutionDisposition $disposition -FailureCode $failureCode `
        -Identity $script:Identity -EnvironmentDigest $runEnvironmentDigest -RunNonce $runNonce `
        -TimingPolicy $script:TimingPolicy -TimingPolicyDigest $script:TimingPolicyDigest `
        -QualificationDigests $qualificationDigests.ToArray() -FixtureSummaries $fixtureSummaries.ToArray() `
        -ArchivalChildResult $archivalChild -BatchExecution $batchTiming -ProcessGraph $processGraph.ToArray() `
        -ResourceEvidence $resourceEvidence
    $publication = Publish-ParentEnvelope -EnvelopeJson $envelopeJson -ExpectedMarkerJson $markerJson `
        -ResultPath $resultPath -StagePath $parentStagePath -ReceiptPath $parentReceiptPath -RunNonce $runNonce `
        -IdentityDigest $script:IdentityDigest -EnvironmentDigest $runEnvironmentDigest -TimingPolicyDigest $script:TimingPolicyDigest `
        -PublicationStartTicks $publicationStart -PublicationDeadlineTicks $publicationDeadline
    $publicationCompleted = $true

    $publicationClass = [string]$publication["timing"]["classification"]
    $finalDisposition = if ($disposition -ceq "SYNTHETIC_ARCHIVAL_EXECUTION_COMPLETED") {
        if ($publicationClass -ceq "PASS") { "SYNTHETIC_OFFICIAL_TRANSPORT_V2_QUALIFIED" }
        elseif ($publicationClass -ceq "QUALIFICATION_MARGIN_BLOCKED") { "SYNTHETIC_QUALIFICATION_MARGIN_BLOCKED" }
        else { "SYNTHETIC_ARTIFACT_BLOCKED" }
    } else { $disposition }
    $closeout = New-SortedMap
    $closeout["artifact_publication"] = $publication["timing"]
    $closeout["artifact_sha256"] = $publication["artifact_sha256"]
    $closeout["execution_disposition"] = $disposition
    $closeout["final_disposition"] = $finalDisposition
    $closeout["result_ref"] = $ResultRef
    $closeout["run_nonce"] = $runNonce
    $closeout["schema_version"] = $TimingSchema
    [Console]::Out.WriteLine((ConvertTo-CanonicalJson -Value $closeout))

    $exitCode = switch ($finalDisposition) {
        "SYNTHETIC_OFFICIAL_TRANSPORT_V2_QUALIFIED" { 0 }
        "SYNTHETIC_QUALIFICATION_MARGIN_BLOCKED" { $ExitSyntheticMargin }
        "SYNTHETIC_IMPORT_BLOCKED" { $ExitSyntheticImport }
        "SYNTHETIC_SCOPE_VIOLATION" { $ExitSyntheticScope }
        "SYNTHETIC_RPC_BLOCKED" { $ExitSyntheticRpc }
        "SYNTHETIC_RESOURCE_BLOCKED" { $ExitSyntheticResource }
        "SYNTHETIC_ARTIFACT_BLOCKED" { $ExitSyntheticArtifact }
        default { $ExitSyntheticExecution }
    }
}
catch [System.Management.Automation.ItemNotFoundException] {
    Write-RunnerError "a frozen executable or source file is unavailable"
    $exitCode = if ($markerOwned -and $null -ne $publicationStart -and -not $publicationCompleted) {
        $ExitSyntheticArtifact
    } elseif ($markerOwned) {
        $ExitSyntheticExecution
    } else {
        $ExitPythonUnavailable
    }
}
catch {
    Write-RunnerError $_.Exception.Message
    $route = if ($markerOwned) { "R" } else { "F" }
    $failure = New-SortedMap
    $failure["additional_live_worker_diagnostics"] = 0
    $publicationFailed = $markerOwned -and $null -ne $publicationStart -and -not $publicationCompleted
    if ($publicationFailed) {
        $publicationFailureEnd = Get-NowTicks
        $failure["artifact_publication"] = New-ParentTimingRecord -ClockClass "artifact_publication" `
            -StartTicks $publicationStart -EndTicks $publicationFailureEnd -HardWallSeconds 30 -SuccessMarginSeconds 10
        $failure["final_disposition"] = "SYNTHETIC_ARTIFACT_BLOCKED"
    }
    $failure["marker_owned"] = $markerOwned
    $failure["route"] = $route
    if ($null -ne $runNonce) { $failure["run_nonce"] = $runNonce }
    [Console]::Error.WriteLine((ConvertTo-CanonicalJson -Value $failure))
    $exitCode = if ($publicationFailed) { $ExitSyntheticArtifact } elseif ($markerOwned) { $ExitSyntheticExecution } else { $ExitPreflight }
}
finally {
    foreach ($owned in @($parentStagePath, $parentReceiptPath)) {
        if ($null -ne $owned -and (Test-Path -LiteralPath $owned -PathType Leaf)) {
            try { Remove-Item -LiteralPath $owned -Force } catch { Write-RunnerError $_.Exception.Message }
        }
    }
    if ($mutexOwned -and $null -ne $mutex) { try { $mutex.ReleaseMutex() } catch { }; $mutexOwned = $false }
    if ($null -ne $mutex) { try { $mutex.Dispose() } catch { } }
}

exit $exitCode
