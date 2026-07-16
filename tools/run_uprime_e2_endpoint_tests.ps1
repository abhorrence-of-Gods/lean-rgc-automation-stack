[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [object[]] $UnexpectedArguments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# This is the sole fresh-authority E2 endpoint runner.  Its immutable carrier
# tree contains no E2 source: the source is materialized from the second parent
# only after every content-addressed topology and runtime check below passes.
$ExitUsage = 64
$ExitRunnerBlocked = 70
$ExitTimeout = 124
$ExitQualificationMargin = 125
$ExitMemory = 137
$ExitOutput = 138

$Lane = "U24_E2_ENDPOINT"
$EndpointId = "u24_e2_declared_square_endpoint_v1"
$RunnerRelativePath = "tools/run_uprime_e2_endpoint_tests.ps1"
$SemanticPaths = @(
    "lean_rgc/odlrq/certificates.py",
    "lean_rgc/odlrq/selection.py",
    "tests/test_odlrq_selection.py",
    "tests/tier_manifest.json"
)
$AuthorityDocumentPath = "docs/experiments/uprime_odlrq_e2_endpoint_semantics_authority_amendment_2026-07-16.md"

$AuthorityCommit = "28c5a29000dddadcaf3e9ad9dd5534554dd67f32"
$AuthorityTree = "1a71fc6ff774dd0bcf7e4ab551bd737a7a9dab14"
$AuthorityDocumentBlob = "139a5992a38269974068858ef00f47f43ef5fca4"
$AuthorityCiRunId = "29484928269"
$AuthorityCiJobId = "87577038652"
$AcceptedE1Commit = "6fb35aa229fc60e2220cbb68c1e7fff2ce64f199"
$AcceptedE1Tree = "b3fc7f21b6420e718eb954be0c1b5affca65d263"
$SemanticCommit = "6998f2f9ec430881df50e6790ef9a8f13b1b7857"
$SemanticTree = "3512b6bc2e7e357544f87f2e7e05e8868b26d658"
$SemanticBlobs = [ordered]@{
    "lean_rgc/odlrq/certificates.py" = "8d995768e93da62829035a1ff187a74e3ea8a378"
    "lean_rgc/odlrq/selection.py" = "b856555271bdea8eb9f9f05e41b4aa52cab9c95d"
    "tests/test_odlrq_selection.py" = "e22223008cab410dd99f953806ce18d38db854f6"
    "tests/tier_manifest.json" = "c649f7f3d74b8a08ea880e250fc8583a21eef790"
}
$ImmutableE1Blobs = [ordered]@{
    "lean_rgc/odlrq/quotient_generator.py" = "1e1576ad1f51ebf667bc55d159048c0ae6587524"
    "lean_rgc/odlrq/envelope.py" = "0618f603b86eba3c61c9fb2e15c4edaacce44a14"
    "lean_rgc/odlrq/__init__.py" = "f97272d5de222fb555a78639d66eb89e77e63d86"
    "tests/tier_manifest.json" = "8bb7810cc49b56aff3d7b18020dab475644911a2"
}

$AuthorityRef = "refs/heads/codex/uprime-e2-endpoint-authority-a0"
$RunnerRef = "refs/heads/codex/uprime-e2-endpoint-runner-control"
$BuildRef = "refs/heads/codex/uprime-e2-endpoint-build"
$SuccessCloseoutRef = "refs/heads/codex/uprime-e2-endpoint-closeout"
$FailureCloseoutRef = "refs/heads/codex/uprime-e2-endpoint-failure-closeout"
$AcceptedRef = "refs/heads/codex/uprime-odlrq-plan"
$ExpectedRemoteUrl = "https://github.com/abhorrence-of-Gods/lean-rgc-automation-stack.git"
$RunnerSubject = "uprime: freeze exact E2 endpoint runner"

$PythonPath = "C:\Python313\python.exe"
$PythonVersion = "3.13.7"
$PythonSha256 = "D932E5E2F324D57F392E8FD063DCF6D0185BE8A664C57C6D24E7762ED02C28CA"
$PowerShellPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
$PowerShellVersion = "5.1.26100.8655"
$PowerShellFileVersion = "10.0.26100.8457"
$PowerShellSha256 = "0FF6F2C94BC7E2833A5F7E16DE1622E5DBA70396F31C7D5F56381870317E8C46"
$GitPath = "C:\Program Files\Git\cmd\git.exe"
$GitVersion = "git version 2.54.0.windows.1"
$GitSha256 = "81EF35AE005CA9318018D18E3327578CE939FB99FEAAD6B2D7C8AB15F3DE8DB5"
$RuntimeSourceRoot = "C:\Users\yusei\AppData\Roaming\Python\Python313\site-packages"
$PytestInitSha256 = "7BE7A1E2218DC59A19D1AD131E4ABE21172A295087EFC72898938248782E8766"
$RuntimeAggregateRowCount = 1424
$RuntimeAggregateByteLength = 277439
$RuntimeAggregateSha256 = "A4BC026C0D68CF9E016157F2E9E161292374FEDBCB21F85ACE44E708EB009751"
$RuntimeCopyFileCount = 1419
$RuntimeDistributions = [ordered]@{
    "colorama" = [ordered]@{ version = "0.4.6"; directory = "colorama-0.4.6.dist-info"; rows = 18 }
    "iniconfig" = [ordered]@{ version = "2.3.0"; directory = "iniconfig-2.3.0.dist-info"; rows = 11 }
    "numpy" = [ordered]@{ version = "2.3.3"; directory = "numpy-2.3.3.dist-info"; rows = 924 }
    "packaging" = [ordered]@{ version = "25.0"; directory = "packaging-25.0.dist-info"; rows = 24 }
    "pluggy" = [ordered]@{ version = "1.6.0"; directory = "pluggy-1.6.0.dist-info"; rows = 15 }
    "pygments" = [ordered]@{ version = "2.19.2"; directory = "pygments-2.19.2.dist-info"; rows = 346 }
    "pytest" = [ordered]@{ version = "9.0.3"; directory = "pytest-9.0.3.dist-info"; rows = 86 }
}
$EscapingRecordRows = @(
    "../Scripts/py.test.exe",
    "../Scripts/pytest.exe",
    "../Scripts/pygmentize.exe",
    "../Scripts/f2py.exe",
    "../Scripts/numpy-config.exe"
)

$ExpectedTestNames = @(
    "test_e2_square_parent_coordinate_identification_rederives_complete_typed_basis",
    "test_e2_restriction_replays_full_parent_terminal_zeros_and_restricted_weights",
    "test_e2_lifting_uniform_safety_is_law_independent_and_cancellation_free",
    "test_e2_p1_p2_cocycles_match_products_weighted_norms_and_limited_derivations",
    "test_e2_return_memory_split_stationary_semantics_and_finite_sum_are_exact",
    "test_e2_orientation_basis_weight_split_and_transport_mutations_fail_closed",
    "test_e2_caps_horizon_work_and_preallocation_bombs_fail_before_authority",
    "test_e2_fixed_candidate_universe_prevents_prefilter_omission_and_accepts_boundary",
    "test_e2_gate_is_coverage_complete_nonempty_reachable_and_top_ranking_binding",
    "test_e2_strict_roundtrip_invalidation_tier_firewall_and_nominal_fallback"
)
$ExpectedNodeIds = @($ExpectedTestNames | ForEach-Object { "tests/test_odlrq_selection.py::$_" })

$WallSeconds = 180
$QualificationSeconds = 60
$MemoryLimitBytes = [uint64]2147483648
$OutputLimitBytes = [int64]67108864
$ControlOutputLimitBytes = [int64]1048576
$ReceiptLimitBytes = [int64]1048576
$PollMilliseconds = 25
$ControlLocalWallSeconds = 15
$ControlRemoteWallSeconds = 30
$ControlAggregateWallSeconds = 120
$ControlMaxInvocations = 32
$StopwatchFrequency = [int64][Diagnostics.Stopwatch]::Frequency
$WallTicks = [int64]($WallSeconds * $StopwatchFrequency)
$QualificationTicks = [int64]($QualificationSeconds * $StopwatchFrequency)

$ChildReceiptSchema = "u24-e2-child-receipt-v1"
$OuterReportSchema = "u24-e2-outer-execution-report-v1"
$PreRunManifestSchema = "u24-e2-pre-run-manifest-v1"
$AttemptSchema = "u24-e2-attempt-consumed-v1"

function Write-RunnerError {
    param([Parameter(Mandatory = $true)][string] $Message)
    [Console]::Error.WriteLine("uprime-e2-endpoint: {0}", $Message)
}

function Throw-SourceFreezeMismatch {
    param([Parameter(Mandatory = $true)][string] $Message)
    $exception = [IO.InvalidDataException]::new($Message)
    $exception.Data["u24_e2_failure_disposition"] = "U24_E2_SOURCE_FREEZE_BLOCKED"
    throw $exception
}

function Get-Sha256Bytes {
    param([Parameter(Mandatory = $true)][byte[]] $Bytes)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace("-", "")
    }
    finally { $sha.Dispose() }
}

function Get-Sha256File {
    param([Parameter(Mandatory = $true)][string] $LiteralPath)
    $stream = [IO.File]::Open($LiteralPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace("-", "") }
    finally { $sha.Dispose(); $stream.Dispose() }
}

function ConvertTo-JsonStringLiteral {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string] $Value)
    $builder = [Text.StringBuilder]::new()
    [void]$builder.Append('"')
    foreach ($character in $Value.ToCharArray()) {
        $code = [int][char]$character
        switch ($code) {
            8 { [void]$builder.Append('\b'); continue }
            9 { [void]$builder.Append('\t'); continue }
            10 { [void]$builder.Append('\n'); continue }
            12 { [void]$builder.Append('\f'); continue }
            13 { [void]$builder.Append('\r'); continue }
            34 { [void]$builder.Append('\"'); continue }
            92 { [void]$builder.Append('\\'); continue }
        }
        if ($code -lt 32 -or $code -gt 126) {
            [void]$builder.Append(('\u{0:x4}' -f $code))
        }
        else { [void]$builder.Append($character) }
    }
    [void]$builder.Append('"')
    return $builder.ToString()
}

function ConvertTo-E2CanonicalJson {
    param([Parameter(Mandatory = $false)] $Value)
    if ($null -eq $Value) { return "null" }
    if ($Value -is [string]) { return ConvertTo-JsonStringLiteral -Value $Value }
    if ($Value -is [bool]) { if ($Value) { return "true" } else { return "false" } }
    if (
        $Value -is [byte] -or $Value -is [sbyte] -or $Value -is [int16] -or
        $Value -is [uint16] -or $Value -is [int32] -or $Value -is [uint32] -or
        $Value -is [int64] -or $Value -is [uint64]
    ) { return ([Convert]::ToString($Value, [Globalization.CultureInfo]::InvariantCulture)) }
    if ($Value -is [Collections.IDictionary]) {
        $parts = [Collections.Generic.List[string]]::new()
        $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach ($keyObject in $Value.Keys) {
            if ($keyObject -isnot [string]) { throw "canonical JSON object key is not a string" }
            $key = [string]$keyObject
            if (-not $seen.Add($key)) { throw "duplicate canonical JSON key: $key" }
            $parts.Add((ConvertTo-JsonStringLiteral -Value $key) + ":" + (ConvertTo-E2CanonicalJson -Value $Value[$key]))
        }
        return "{" + ($parts -join ",") + "}"
    }
    if ($Value -is [Management.Automation.PSCustomObject]) {
        $ordered = [ordered]@{}
        foreach ($property in $Value.PSObject.Properties) { $ordered[$property.Name] = $property.Value }
        return ConvertTo-E2CanonicalJson -Value $ordered
    }
    if ($Value -is [Collections.IEnumerable]) {
        $parts = [Collections.Generic.List[string]]::new()
        foreach ($item in $Value) { $parts.Add((ConvertTo-E2CanonicalJson -Value $item)) }
        return "[" + ($parts -join ",") + "]"
    }
    throw "unsupported canonical JSON type: $($Value.GetType().FullName)"
}

function Get-CanonicalPayload {
    param([Parameter(Mandatory = $true)] $Value)
    $json = ConvertTo-E2CanonicalJson -Value $Value
    $bytes = [Text.Encoding]::ASCII.GetBytes($json)
    return [pscustomobject][ordered]@{
        text = $json
        bytes = $bytes
        byte_length = [int64]$bytes.Length
        sha256 = Get-Sha256Bytes -Bytes $bytes
    }
}

function Get-GitBlobOid {
    param([Parameter(Mandatory = $true)][string] $LiteralPath)
    $file = [IO.File]::Open($LiteralPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $sha1 = [Security.Cryptography.SHA1]::Create()
    try {
        $prefix = [Text.Encoding]::ASCII.GetBytes("blob $($file.Length)`0")
        [void]$sha1.TransformBlock($prefix, 0, $prefix.Length, $null, 0)
        $buffer = [byte[]]::new(65536)
        while (($read = $file.Read($buffer, 0, $buffer.Length)) -gt 0) {
            [void]$sha1.TransformBlock($buffer, 0, $read, $null, 0)
        }
        [void]$sha1.TransformFinalBlock([byte[]]::new(0), 0, 0)
        return ([BitConverter]::ToString($sha1.Hash)).Replace("-", "").ToLowerInvariant()
    }
    finally { $sha1.Dispose(); $file.Dispose() }
}

function Assert-Sha256File {
    param(
        [Parameter(Mandatory = $true)][string] $LiteralPath,
        [Parameter(Mandatory = $true)][string] $Expected,
        [Parameter(Mandatory = $true)][string] $Label
    )
    $actual = Get-Sha256File -LiteralPath $LiteralPath
    if ($actual -cne $Expected) { throw "$Label SHA-256 drift: $actual" }
}

function Assert-NonReparsePath {
    param(
        [Parameter(Mandatory = $true)][string] $LiteralPath,
        [switch] $AllowMissingLeaf
    )
    $full = [IO.Path]::GetFullPath($LiteralPath)
    $root = [IO.Path]::GetPathRoot($full)
    $relative = $full.Substring($root.Length)
    $cursor = $root.TrimEnd('\')
    foreach ($part in $relative.Split([char[]]@('\'), [StringSplitOptions]::RemoveEmptyEntries)) {
        $cursor = Join-Path $cursor $part
        if (-not (Test-Path -LiteralPath $cursor)) {
            if ($AllowMissingLeaf) { return }
            throw "required path component is missing: $cursor"
        }
        $item = Get-Item -LiteralPath $cursor -Force
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "reparse path component is forbidden: $cursor"
        }
    }
}

function New-OwnedDirectory {
    param(
        [Parameter(Mandatory = $true)][string] $LiteralPath,
        [Parameter(Mandatory = $true)][string] $RequiredParent
    )
    $full = [IO.Path]::GetFullPath($LiteralPath)
    $parent = [IO.Path]::GetFullPath((Split-Path -Parent $full)).TrimEnd('\')
    if (-not $parent.Equals([IO.Path]::GetFullPath($RequiredParent).TrimEnd('\'), [StringComparison]::OrdinalIgnoreCase)) {
        throw "owned directory escaped its required parent"
    }
    if (Test-Path -LiteralPath $full) { throw "owned directory already exists: $full" }
    [void][IO.Directory]::CreateDirectory($full)
    Assert-NonReparsePath -LiteralPath $full
    return $full
}

function Test-SafeRelativePath {
    param([Parameter(Mandatory = $true)][string] $RelativePath)
    if ([string]::IsNullOrWhiteSpace($RelativePath)) { return $false }
    if ($RelativePath.Contains('\') -or $RelativePath.StartsWith('/') -or $RelativePath.Contains(':')) { return $false }
    $parts = $RelativePath.Split('/')
    foreach ($part in $parts) {
        if ($part.Length -eq 0 -or $part -eq '.' -or $part -eq '..') { return $false }
        if ($part.EndsWith('.') -or $part.EndsWith(' ')) { return $false }
        if ($part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$') { return $false }
    }
    return $true
}

$unboundCount = if ($null -eq $MyInvocation.UnboundArguments) { 0 } else { @($MyInvocation.UnboundArguments).Count }
$unexpectedCount = if ($null -eq $UnexpectedArguments) { 0 } else { @($UnexpectedArguments).Count }
if ($PSBoundParameters.Count -ne 0 -or $unboundCount -ne 0 -or $unexpectedCount -ne 0) {
    Write-RunnerError "arguments are forbidden"
    exit $ExitUsage
}

$NativeSource = @'
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Win32.SafeHandles;

public sealed class U24E2PumpState {
    public readonly long Limit;
    public long Retained;
    public long StdoutDropped;
    public long StderrDropped;
    public int Exceeded;
    public string Error;
    public U24E2PumpState(long limit) { Limit = limit; }
    public bool Reserve(int count, bool stderr) {
        while (true) {
            long oldValue = Interlocked.Read(ref Retained);
            if (oldValue > Limit - count) {
                if (stderr) Interlocked.Add(ref StderrDropped, count);
                else Interlocked.Add(ref StdoutDropped, count);
                Interlocked.Exchange(ref Exceeded, 1);
                return false;
            }
            if (Interlocked.CompareExchange(ref Retained, oldValue + count, oldValue) == oldValue) return true;
        }
    }
}

public sealed class U24E2NativeSession : IDisposable {
    internal IntPtr ProcessHandle;
    internal IntPtr ThreadHandle;
    internal IntPtr JobHandle;
    internal IntPtr CompletionPort;
    internal FileStream StdoutRead;
    internal FileStream StderrRead;
    internal Task StdoutTask;
    internal Task StderrTask;
    internal string StdoutPath;
    internal string StderrPath;
    internal U24E2PumpState Pump;
    internal readonly List<uint> JobMessages = new List<uint>();
    internal bool Resumed;
    internal bool PipeEscape;
    internal bool WritersClosed;
    internal bool CleanupComplete;
    internal uint ProcessId;

    public bool OutputExceeded { get { return Volatile.Read(ref Pump.Exceeded) != 0; } }
    public long StdoutDropped { get { return Interlocked.Read(ref Pump.StdoutDropped); } }
    public long StderrDropped { get { return Interlocked.Read(ref Pump.StderrDropped); } }
    public bool ControlPipeEscape { get { return PipeEscape; } }
    public bool CaptureWritersClosed { get { return WritersClosed; } }
    public uint Id { get { return ProcessId; } }

    internal void StartPumps() {
        StdoutTask = Task.Run(delegate { U24E2Native.PumpPipe(StdoutRead, StdoutPath, Pump, false); });
        StderrTask = Task.Run(delegate { U24E2Native.PumpPipe(StderrRead, StderrPath, Pump, true); });
    }
    public void Resume() {
        if (Resumed) throw new InvalidOperationException("process was already resumed");
        uint previous = U24E2Native.ResumeThreadNative(ThreadHandle);
        if (previous == 0xffffffffu) {
            Exception primary = new Win32Exception(Marshal.GetLastWin32Error(), "ResumeThread failed");
            List<Exception> cleanup = new List<Exception>();
            U24E2Native.TryCleanup(cleanup, delegate { U24E2Native.TerminateAndWaitProcess(ProcessHandle, 70u, 2000u); });
            U24E2Native.CloseHandleCollect(ref ThreadHandle, cleanup);
            throw U24E2Native.CombineFailure(primary, cleanup);
        }
        if (!U24E2Native.CloseHandleNative(ThreadHandle)) {
            Exception primary = new Win32Exception(Marshal.GetLastWin32Error(), "resumed thread handle close failed");
            List<Exception> cleanup = new List<Exception>();
            U24E2Native.TryCleanup(cleanup, delegate { U24E2Native.TerminateAndWaitProcess(ProcessHandle, 70u, 2000u); });
            U24E2Native.CloseHandleCollect(ref ThreadHandle, cleanup);
            throw U24E2Native.CombineFailure(primary, cleanup);
        }
        ThreadHandle = IntPtr.Zero;
        Resumed = true;
    }
    public bool Wait(int milliseconds) {
        uint result = U24E2Native.WaitForSingleObjectNative(ProcessHandle, (uint)milliseconds);
        if (result == 0u) return true;
        if (result == 0x102u) return false;
        throw new Win32Exception(Marshal.GetLastWin32Error());
    }
    public void Terminate(uint code) {
        if (JobHandle != IntPtr.Zero && !U24E2Native.TerminateJobObjectNative(JobHandle, code)) {
            throw new Win32Exception(Marshal.GetLastWin32Error());
        }
    }
    public int ExitCode() {
        uint value;
        if (!U24E2Native.GetExitCodeProcessNative(ProcessHandle, out value)) throw new Win32Exception(Marshal.GetLastWin32Error());
        return unchecked((int)value);
    }
    public ulong PeakJobMemory() { return U24E2Native.QueryPeakJobMemory(JobHandle); }
    public uint[] DrainJobMessages() {
        if (CompletionPort == IntPtr.Zero) return new uint[0];
        List<uint> newlyDrained = new List<uint>();
        while (true) {
            uint message;
            UIntPtr key;
            IntPtr overlapped;
            bool ok = U24E2Native.GetQueuedCompletionStatusNative(CompletionPort, out message, out key, out overlapped, 0u);
            if (!ok) {
                int error = Marshal.GetLastWin32Error();
                if (error == 258) break;
                throw new Win32Exception(error);
            }
            JobMessages.Add(message);
            newlyDrained.Add(message);
        }
        return newlyDrained.ToArray();
    }
    public bool FinishPumps(int eofMilliseconds) {
        Task[] tasks = new Task[] { StdoutTask, StderrTask };
        bool finished = Task.WaitAll(tasks, eofMilliseconds);
        WritersClosed = finished;
        if (!finished) {
            PipeEscape = true;
            try { StdoutRead.Dispose(); } catch { }
            try { StderrRead.Dispose(); } catch { }
            try { WritersClosed = Task.WaitAll(tasks, 500); } catch { WritersClosed = false; }
        }
        else {
            StdoutRead.Dispose();
            StderrRead.Dispose();
        }
        if (!String.IsNullOrEmpty(Pump.Error)) throw new IOException(Pump.Error);
        return !PipeEscape;
    }
    public byte[] ReadStdout() { return File.ReadAllBytes(StdoutPath); }
    public byte[] ReadStderr() { return File.ReadAllBytes(StderrPath); }
    public void CloseJob() {
        List<Exception> errors = new List<Exception>();
        if (JobHandle != IntPtr.Zero) {
            U24E2Native.CloseHandleCollect(ref JobHandle, errors);
        }
        if (CompletionPort != IntPtr.Zero) {
            U24E2Native.CloseHandleCollect(ref CompletionPort, errors);
        }
        if (errors.Count != 0) throw U24E2Native.CleanupFailure(errors);
    }
    public void Dispose() {
        List<Exception> errors = new List<Exception>();
        if (ThreadHandle != IntPtr.Zero && ProcessHandle != IntPtr.Zero) {
            U24E2Native.TryCleanup(errors, delegate { U24E2Native.TerminateAndWaitProcess(ProcessHandle, 70u, 2000u); });
        }
        U24E2Native.CloseHandleCollect(ref ThreadHandle, errors);
        U24E2Native.CloseHandleCollect(ref ProcessHandle, errors);
        U24E2Native.TryCleanup(errors, delegate { CloseJob(); });
        U24E2Native.TryCleanup(errors, delegate { if (StdoutRead != null) StdoutRead.Dispose(); });
        U24E2Native.TryCleanup(errors, delegate { if (StderrRead != null) StderrRead.Dispose(); });
        CleanupComplete = errors.Count == 0;
        if (errors.Count != 0) throw U24E2Native.CleanupFailure(errors);
    }
}

public sealed class U24E2ManagedSession : IDisposable {
    internal Process Process;
    internal IntPtr JobHandle;
    internal IntPtr CompletionPort;
    internal Task StdoutTask;
    internal Task StderrTask;
    internal string StdoutPath;
    internal string StderrPath;
    internal U24E2PumpState Pump;
    internal readonly List<uint> JobMessages = new List<uint>();
    internal bool PipeEscape;
    internal bool WritersClosed;

    public bool OutputExceeded { get { return Volatile.Read(ref Pump.Exceeded) != 0; } }
    public long StdoutDropped { get { return Interlocked.Read(ref Pump.StdoutDropped); } }
    public long StderrDropped { get { return Interlocked.Read(ref Pump.StderrDropped); } }
    public int ExitCode { get { return Process.ExitCode; } }
    public bool CaptureWritersClosed { get { return WritersClosed; } }
    public bool Wait(int milliseconds) { return Process.WaitForExit(milliseconds); }
    public void Terminate(uint code) {
        if (JobHandle != IntPtr.Zero && !U24E2Native.TerminateJobObjectNative(JobHandle, code)) throw new Win32Exception(Marshal.GetLastWin32Error());
    }
    public ulong PeakJobMemory() { return U24E2Native.QueryPeakJobMemory(JobHandle); }
    public uint[] DrainJobMessages() {
        if (CompletionPort == IntPtr.Zero) return new uint[0];
        List<uint> newlyDrained = new List<uint>();
        while (true) {
            uint message; UIntPtr key; IntPtr overlapped;
            bool ok = U24E2Native.GetQueuedCompletionStatusNative(CompletionPort, out message, out key, out overlapped, 0u);
            if (!ok) { int error = Marshal.GetLastWin32Error(); if (error == 258) break; throw new Win32Exception(error); }
            JobMessages.Add(message); newlyDrained.Add(message);
        }
        return newlyDrained.ToArray();
    }
    public bool FinishPumps(int milliseconds) {
        Task[] tasks = new Task[] { StdoutTask, StderrTask };
        bool complete = Task.WaitAll(tasks, milliseconds);
        WritersClosed = complete;
        if (!complete) {
            PipeEscape = true;
            try { Process.StandardOutput.BaseStream.Dispose(); } catch { }
            try { Process.StandardError.BaseStream.Dispose(); } catch { }
            try { WritersClosed = Task.WaitAll(tasks, 500); } catch { WritersClosed = false; }
        }
        if (!String.IsNullOrEmpty(Pump.Error)) throw new IOException(Pump.Error);
        return !PipeEscape;
    }
    public byte[] ReadStdout() { return File.ReadAllBytes(StdoutPath); }
    public byte[] ReadStderr() { return File.ReadAllBytes(StderrPath); }
    public void CloseJob() {
        List<Exception> errors = new List<Exception>();
        if (JobHandle != IntPtr.Zero) {
            U24E2Native.CloseHandleCollect(ref JobHandle, errors);
        }
        if (CompletionPort != IntPtr.Zero) {
            U24E2Native.CloseHandleCollect(ref CompletionPort, errors);
        }
        if (errors.Count != 0) throw U24E2Native.CleanupFailure(errors);
    }
    public void Dispose() {
        List<Exception> errors = new List<Exception>();
        U24E2Native.TryCleanup(errors, delegate { CloseJob(); });
        U24E2Native.TryCleanup(errors, delegate { if (Process != null) Process.Dispose(); });
        if (errors.Count != 0) throw U24E2Native.CleanupFailure(errors);
    }
}

public static class U24E2Native {
    const uint CREATE_SUSPENDED = 0x00000004u;
    const uint CREATE_NO_WINDOW = 0x08000000u;
    const uint CREATE_UNICODE_ENVIRONMENT = 0x00000400u;
    const uint STARTF_USESTDHANDLES = 0x00000100u;
    const uint HANDLE_FLAG_INHERIT = 0x00000001u;
    const uint GENERIC_READ = 0x80000000u;
    const uint GENERIC_WRITE = 0x40000000u;
    const uint FILE_SHARE_READ = 0x00000001u;
    const uint FILE_SHARE_WRITE = 0x00000002u;
    const uint OPEN_EXISTING = 3u;
    const uint JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008u;
    const uint JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100u;
    const uint JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200u;
    const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000u;
    const uint WAIT_OBJECT_0 = 0u;
    const uint WAIT_TIMEOUT = 0x00000102u;

    [StructLayout(LayoutKind.Sequential)] struct SECURITY_ATTRIBUTES { public int nLength; public IntPtr lpSecurityDescriptor; public int bInheritHandle; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct STARTUPINFO {
        public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize;
        public int dwXCountChars; public int dwYCountChars; public int dwFillAttribute;
        public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError;
    }
    [StructLayout(LayoutKind.Sequential)] struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public uint dwProcessId; public uint dwThreadId; }
    [StructLayout(LayoutKind.Sequential)] struct IO_COUNTERS { public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount, ReadTransferCount, WriteTransferCount, OtherTransferCount; }
    [StructLayout(LayoutKind.Sequential)] struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
        public long PerProcessUserTimeLimit; public long PerJobUserTimeLimit; public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize; public UIntPtr MaximumWorkingSetSize;
        public uint ActiveProcessLimit; public UIntPtr Affinity; public uint PriorityClass; public uint SchedulingClass;
    }
    [StructLayout(LayoutKind.Sequential)] struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation; public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit; public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed; public UIntPtr PeakJobMemoryUsed;
    }
    [StructLayout(LayoutKind.Sequential)] struct JOBOBJECT_ASSOCIATE_COMPLETION_PORT { public IntPtr CompletionKey; public IntPtr CompletionPort; }

    [DllImport("kernel32.dll", SetLastError=true)] static extern bool CreatePipe(out IntPtr read, out IntPtr write, ref SECURITY_ATTRIBUTES attributes, int size);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool SetHandleInformation(IntPtr handle, uint mask, uint flags);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr CreateFile(string name, uint access, uint share, ref SECURITY_ATTRIBUTES attributes, uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool CreateProcess(string application, StringBuilder command, IntPtr pa, IntPtr ta, bool inherit, uint flags, IntPtr environment, string cwd, ref STARTUPINFO startup, out PROCESS_INFORMATION info);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr attributes, string name);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool SetInformationJobObject(IntPtr job, int infoClass, IntPtr info, uint length);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr job, int infoClass, IntPtr info, uint length, out uint returned);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool TerminateJobObjectNative(IntPtr job, uint code);
    [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool TerminateProcessNative(IntPtr process, uint code);
    [DllImport("kernel32.dll", SetLastError=true)] internal static extern uint ResumeThreadNative(IntPtr thread);
    [DllImport("kernel32.dll", SetLastError=true)] internal static extern uint WaitForSingleObjectNative(IntPtr handle, uint milliseconds);
    [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool GetExitCodeProcessNative(IntPtr process, out uint code);
    [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool CloseHandleNative(IntPtr handle);
    [DllImport("kernel32.dll", SetLastError=true)] static extern IntPtr CreateIoCompletionPort(IntPtr file, IntPtr existing, UIntPtr key, uint threads);
    [DllImport("kernel32.dll", SetLastError=true)] internal static extern bool GetQueuedCompletionStatusNative(IntPtr port, out uint bytes, out UIntPtr key, out IntPtr overlapped, uint milliseconds);

    static string Quote(string value) {
        if (value.IndexOf('\0') >= 0 || value.IndexOf('\r') >= 0 || value.IndexOf('\n') >= 0) throw new ArgumentException("argument control character");
        StringBuilder b = new StringBuilder(); b.Append('"'); int slashes = 0;
        foreach (char c in value) {
            if (c == '\\') { slashes++; continue; }
            if (c == '"') { b.Append('\\', slashes * 2 + 1); b.Append('"'); slashes = 0; continue; }
            if (slashes != 0) { b.Append('\\', slashes); slashes = 0; }
            b.Append(c);
        }
        if (slashes != 0) b.Append('\\', slashes * 2);
        b.Append('"'); return b.ToString();
    }
    public static string BuildArgumentLine(string[] arguments) {
        StringBuilder result = new StringBuilder();
        foreach (string argument in arguments) { if (result.Length != 0) result.Append(' '); result.Append(Quote(argument)); }
        return result.ToString();
    }
    internal static void TryCleanup(List<Exception> errors, Action action) {
        try { action(); } catch (Exception ex) { errors.Add(ex); }
    }
    internal static Exception CleanupFailure(List<Exception> errors) {
        if (errors.Count == 1) return errors[0];
        return new AggregateException("multiple native cleanup operations failed", errors.ToArray());
    }
    internal static Exception CombineFailure(Exception primary, List<Exception> cleanup) {
        if (cleanup.Count == 0) return primary;
        List<Exception> all = new List<Exception>(); all.Add(primary); all.AddRange(cleanup);
        return new AggregateException("primary native operation and containment cleanup failed", all.ToArray());
    }
    internal static void TerminateAndWaitProcess(IntPtr process, uint code, uint milliseconds) {
        if (process == IntPtr.Zero) return;
        uint initial = WaitForSingleObjectNative(process, 0u);
        if (initial == WAIT_OBJECT_0) return;
        if (initial != WAIT_TIMEOUT) throw new Win32Exception(Marshal.GetLastWin32Error(), "initial process wait failed");
        if (!TerminateProcessNative(process, code)) {
            int terminateError = Marshal.GetLastWin32Error();
            if (WaitForSingleObjectNative(process, 0u) != WAIT_OBJECT_0) {
                throw new Win32Exception(terminateError, "TerminateProcess failed before bounded wait");
            }
            return;
        }
        uint waited = WaitForSingleObjectNative(process, milliseconds);
        if (waited == WAIT_OBJECT_0) return;
        if (waited == WAIT_TIMEOUT) throw new TimeoutException("terminated process missed bounded wait");
        throw new Win32Exception(Marshal.GetLastWin32Error(), "terminated process wait failed");
    }
    internal static void CloseHandleCollect(ref IntPtr handle, List<Exception> errors) {
        if (handle == IntPtr.Zero || handle == new IntPtr(-1)) { handle = IntPtr.Zero; return; }
        if (CloseHandleNative(handle)) handle = IntPtr.Zero;
        else errors.Add(new Win32Exception(Marshal.GetLastWin32Error(), "native handle close failed"));
    }
    static void CloseRequired(ref IntPtr handle) {
        if (handle == IntPtr.Zero || handle == new IntPtr(-1)) { handle = IntPtr.Zero; return; }
        if (!CloseHandleNative(handle)) throw new Win32Exception(Marshal.GetLastWin32Error());
        handle = IntPtr.Zero;
    }
    static IntPtr EnvironmentBlock(IDictionary<string,string> environment) {
        List<string> keys = new List<string>(environment.Keys); keys.Sort(StringComparer.OrdinalIgnoreCase);
        StringBuilder b = new StringBuilder();
        foreach (string key in keys) {
            if (key.IndexOf('=') >= 0 || key.IndexOf('\0') >= 0 || environment[key].IndexOf('\0') >= 0) throw new ArgumentException("invalid environment");
            b.Append(key).Append('=').Append(environment[key]).Append('\0');
        }
        b.Append('\0'); byte[] bytes = Encoding.Unicode.GetBytes(b.ToString());
        IntPtr pointer = Marshal.AllocHGlobal(bytes.Length); Marshal.Copy(bytes, 0, pointer, bytes.Length); return pointer;
    }
    static IntPtr MakeJob(bool scientific, ulong memory, bool completion, out IntPtr port) {
        port = IntPtr.Zero; IntPtr job = CreateJobObject(IntPtr.Zero, null);
        if (job == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
        try {
            JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
            limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            if (scientific) {
                limits.BasicLimitInformation.LimitFlags |= JOB_OBJECT_LIMIT_ACTIVE_PROCESS | JOB_OBJECT_LIMIT_PROCESS_MEMORY | JOB_OBJECT_LIMIT_JOB_MEMORY;
                limits.BasicLimitInformation.ActiveProcessLimit = 1u;
                limits.ProcessMemoryLimit = new UIntPtr(memory); limits.JobMemoryLimit = new UIntPtr(memory);
            }
            int size = Marshal.SizeOf(typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION)); IntPtr p = Marshal.AllocHGlobal(size);
            try { Marshal.StructureToPtr(limits, p, false); if (!SetInformationJobObject(job, 9, p, (uint)size)) throw new Win32Exception(Marshal.GetLastWin32Error()); }
            finally { Marshal.FreeHGlobal(p); }
            if (completion) {
                port = CreateIoCompletionPort(new IntPtr(-1), IntPtr.Zero, UIntPtr.Zero, 1u);
                if (port == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
                JOBOBJECT_ASSOCIATE_COMPLETION_PORT association = new JOBOBJECT_ASSOCIATE_COMPLETION_PORT();
                association.CompletionKey = job; association.CompletionPort = port;
                int asize = Marshal.SizeOf(typeof(JOBOBJECT_ASSOCIATE_COMPLETION_PORT)); IntPtr ap = Marshal.AllocHGlobal(asize);
                try { Marshal.StructureToPtr(association, ap, false); if (!SetInformationJobObject(job, 7, ap, (uint)asize)) throw new Win32Exception(Marshal.GetLastWin32Error()); }
                finally { Marshal.FreeHGlobal(ap); }
            }
            return job;
        } catch { if (port != IntPtr.Zero) CloseHandleNative(port); CloseHandleNative(job); throw; }
    }
    public static U24E2ManagedSession AttachManagedProcess(Process process, string stdoutPath, string stderrPath, long outputLimit, ulong memory) {
        if (process == null) throw new ArgumentNullException("process");
        IntPtr port; IntPtr job = MakeJob(true, memory, true, out port);
        IntPtr processHandle = process.Handle;
        if (!AssignProcessToJobObject(job, processHandle)) {
            Exception primary = new Win32Exception(Marshal.GetLastWin32Error(), "scientific AssignProcessToJobObject failed");
            List<Exception> cleanup = new List<Exception>();
            TryCleanup(cleanup, delegate { TerminateAndWaitProcess(processHandle, 70u, 2000u); });
            CloseHandleCollect(ref port, cleanup); CloseHandleCollect(ref job, cleanup);
            throw CombineFailure(primary, cleanup);
        }
        U24E2ManagedSession session = null;
        try {
            session = new U24E2ManagedSession();
            session.Process = process; session.JobHandle = job; session.CompletionPort = port;
            session.StdoutPath = stdoutPath; session.StderrPath = stderrPath; session.Pump = new U24E2PumpState(outputLimit);
            session.StdoutTask = Task.Run(delegate { PumpPipe(process.StandardOutput.BaseStream, stdoutPath, session.Pump, false); });
            session.StderrTask = Task.Run(delegate { PumpPipe(process.StandardError.BaseStream, stderrPath, session.Pump, true); });
            job = IntPtr.Zero; port = IntPtr.Zero;
            return session;
        } catch (Exception primary) {
            List<Exception> cleanup = new List<Exception>();
            TryCleanup(cleanup, delegate { TerminateAndWaitProcess(processHandle, 70u, 2000u); });
            if (session != null) {
                TryCleanup(cleanup, delegate { session.Dispose(); });
                job = IntPtr.Zero; port = IntPtr.Zero;
            }
            CloseHandleCollect(ref port, cleanup); CloseHandleCollect(ref job, cleanup);
            throw CombineFailure(primary, cleanup);
        }
    }
    public static U24E2NativeSession StartSuspended(string executable, string[] arguments, string cwd, IDictionary<string,string> environment, string stdoutPath, string stderrPath, long outputLimit, bool scientific, ulong memory, bool completion) {
        SECURITY_ATTRIBUTES sa = new SECURITY_ATTRIBUTES(); sa.nLength = Marshal.SizeOf(typeof(SECURITY_ATTRIBUTES)); sa.bInheritHandle = 1;
        IntPtr outRead = IntPtr.Zero, outWrite = IntPtr.Zero, errRead = IntPtr.Zero, errWrite = IntPtr.Zero, nullInput = IntPtr.Zero, env = IntPtr.Zero, port = IntPtr.Zero;
        IntPtr job = IntPtr.Zero; PROCESS_INFORMATION pi = new PROCESS_INFORMATION(); U24E2NativeSession session = null;
        try {
            if (!CreatePipe(out outRead, out outWrite, ref sa, 0) || !CreatePipe(out errRead, out errWrite, ref sa, 0)) throw new Win32Exception(Marshal.GetLastWin32Error());
            if (!SetHandleInformation(outRead, HANDLE_FLAG_INHERIT, 0u) || !SetHandleInformation(errRead, HANDLE_FLAG_INHERIT, 0u)) throw new Win32Exception(Marshal.GetLastWin32Error());
            nullInput = CreateFile("NUL", GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, ref sa, OPEN_EXISTING, 0u, IntPtr.Zero);
            if (nullInput == new IntPtr(-1)) throw new Win32Exception(Marshal.GetLastWin32Error());
            job = MakeJob(scientific, memory, completion, out port);
            StringBuilder command = new StringBuilder(Quote(executable)); foreach (string argument in arguments) command.Append(' ').Append(Quote(argument));
            env = EnvironmentBlock(environment);
            STARTUPINFO startup = new STARTUPINFO(); startup.cb = Marshal.SizeOf(typeof(STARTUPINFO)); startup.dwFlags = (int)STARTF_USESTDHANDLES;
            startup.hStdInput = nullInput; startup.hStdOutput = outWrite; startup.hStdError = errWrite;
            if (!CreateProcess(executable, command, IntPtr.Zero, IntPtr.Zero, true, CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT, env, cwd, ref startup, out pi)) throw new Win32Exception(Marshal.GetLastWin32Error());
            if (!AssignProcessToJobObject(job, pi.hProcess)) {
                throw new Win32Exception(Marshal.GetLastWin32Error(), "control AssignProcessToJobObject failed");
            }
            CloseRequired(ref outWrite); CloseRequired(ref errWrite); CloseRequired(ref nullInput);
            session = new U24E2NativeSession(); session.ProcessHandle = pi.hProcess; session.ThreadHandle = pi.hThread; session.ProcessId = pi.dwProcessId;
            pi.hProcess = IntPtr.Zero; pi.hThread = IntPtr.Zero;
            session.JobHandle = job; session.CompletionPort = port; job = IntPtr.Zero; port = IntPtr.Zero;
            SafeFileHandle stdoutSafe = new SafeFileHandle(outRead, true); outRead = IntPtr.Zero;
            try { session.StdoutRead = new FileStream(stdoutSafe, FileAccess.Read, 16384, false); } catch { stdoutSafe.Dispose(); throw; }
            SafeFileHandle stderrSafe = new SafeFileHandle(errRead, true); errRead = IntPtr.Zero;
            try { session.StderrRead = new FileStream(stderrSafe, FileAccess.Read, 16384, false); } catch { stderrSafe.Dispose(); throw; }
            session.StdoutPath = stdoutPath; session.StderrPath = stderrPath; session.Pump = new U24E2PumpState(outputLimit); session.StartPumps(); return session;
        } catch (Exception primary) {
            List<Exception> cleanup = new List<Exception>();
            if (session != null) {
                TryCleanup(cleanup, delegate { session.Dispose(); });
            }
            else if (pi.hProcess != IntPtr.Zero) {
                TryCleanup(cleanup, delegate { TerminateAndWaitProcess(pi.hProcess, 70u, 2000u); });
            }
            CloseHandleCollect(ref outRead, cleanup); CloseHandleCollect(ref outWrite, cleanup);
            CloseHandleCollect(ref errRead, cleanup); CloseHandleCollect(ref errWrite, cleanup);
            CloseHandleCollect(ref nullInput, cleanup);
            CloseHandleCollect(ref pi.hThread, cleanup); CloseHandleCollect(ref pi.hProcess, cleanup);
            CloseHandleCollect(ref port, cleanup); CloseHandleCollect(ref job, cleanup);
            throw CombineFailure(primary, cleanup);
        } finally {
            if (env != IntPtr.Zero) Marshal.FreeHGlobal(env);
        }
    }
    internal static void PumpPipe(Stream input, string outputPath, U24E2PumpState state, bool stderr) {
        try {
            using (FileStream output = new FileStream(outputPath, FileMode.CreateNew, FileAccess.Write, FileShare.Read, 16384, FileOptions.SequentialScan)) {
                byte[] buffer = new byte[16384]; int read;
                while ((read = input.Read(buffer, 0, buffer.Length)) > 0) {
                    if (state.Reserve(read, stderr)) output.Write(buffer, 0, read);
                }
                output.Flush(true);
            }
        } catch (Exception ex) { state.Error = ex.GetType().FullName + ": " + ex.Message; }
    }
    internal static ulong QueryPeakJobMemory(IntPtr job) {
        int size = Marshal.SizeOf(typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION)); IntPtr p = Marshal.AllocHGlobal(size);
        try { uint returned; if (!QueryInformationJobObject(job, 9, p, (uint)size, out returned)) throw new Win32Exception(Marshal.GetLastWin32Error());
            JOBOBJECT_EXTENDED_LIMIT_INFORMATION value = (JOBOBJECT_EXTENDED_LIMIT_INFORMATION)Marshal.PtrToStructure(p, typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION)); return value.PeakJobMemoryUsed.ToUInt64();
        } finally { Marshal.FreeHGlobal(p); }
    }
}
'@

$NativeSourceSha256 = "D89735D8B7D753E01B83610DECE3E9261419A33616BDFB3A6CDAC46132EFBF0D"
$NativeSourceByteLength = 29678
$NativeAssemblySha256 = "7054B94C29BC080537E5BF43864E244A4C2A07FC2DA2BA456DAF6A3DC732AD00"
$NativeAssemblyByteLength = 19456
$NativeAssemblyFullName = "U24E2Native, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null"
$NativeAssemblyMvid = "d41e64bd-b699-453a-ae8f-957d359bd9f4"
$NativeAssemblySurface = @(
    'TYPE|U24E2ManagedSession|System.Object|1048833',
    'MEMBER|U24E2ManagedSession|Constructor|Void .ctor()',
    'MEMBER|U24E2ManagedSession|Method|Boolean FinishPumps(Int32)',
    'MEMBER|U24E2ManagedSession|Method|Boolean Wait(Int32)',
    'MEMBER|U24E2ManagedSession|Method|Boolean get_CaptureWritersClosed()',
    'MEMBER|U24E2ManagedSession|Method|Boolean get_OutputExceeded()',
    'MEMBER|U24E2ManagedSession|Method|Byte[] ReadStderr()',
    'MEMBER|U24E2ManagedSession|Method|Byte[] ReadStdout()',
    'MEMBER|U24E2ManagedSession|Method|Int32 get_ExitCode()',
    'MEMBER|U24E2ManagedSession|Method|Int64 get_StderrDropped()',
    'MEMBER|U24E2ManagedSession|Method|Int64 get_StdoutDropped()',
    'MEMBER|U24E2ManagedSession|Method|UInt32[] DrainJobMessages()',
    'MEMBER|U24E2ManagedSession|Method|UInt64 PeakJobMemory()',
    'MEMBER|U24E2ManagedSession|Method|Void CloseJob()',
    'MEMBER|U24E2ManagedSession|Method|Void Dispose()',
    'MEMBER|U24E2ManagedSession|Method|Void Terminate(UInt32)',
    'MEMBER|U24E2ManagedSession|Property|Boolean CaptureWritersClosed',
    'MEMBER|U24E2ManagedSession|Property|Boolean OutputExceeded',
    'MEMBER|U24E2ManagedSession|Property|Int32 ExitCode',
    'MEMBER|U24E2ManagedSession|Property|Int64 StderrDropped',
    'MEMBER|U24E2ManagedSession|Property|Int64 StdoutDropped',
    'TYPE|U24E2Native|System.Object|1048961',
    'MEMBER|U24E2Native|Method|System.String BuildArgumentLine(System.String[])',
    'MEMBER|U24E2Native|Method|U24E2ManagedSession AttachManagedProcess(System.Diagnostics.Process, System.String, System.String, Int64, UInt64)',
    'MEMBER|U24E2Native|Method|U24E2NativeSession StartSuspended(System.String, System.String[], System.String, System.Collections.Generic.IDictionary`2[System.String,System.String], System.String, System.String, Int64, Boolean, UInt64, Boolean)',
    'TYPE|U24E2NativeSession|System.Object|1048833',
    'MEMBER|U24E2NativeSession|Constructor|Void .ctor()',
    'MEMBER|U24E2NativeSession|Method|Boolean FinishPumps(Int32)',
    'MEMBER|U24E2NativeSession|Method|Boolean Wait(Int32)',
    'MEMBER|U24E2NativeSession|Method|Boolean get_CaptureWritersClosed()',
    'MEMBER|U24E2NativeSession|Method|Boolean get_ControlPipeEscape()',
    'MEMBER|U24E2NativeSession|Method|Boolean get_OutputExceeded()',
    'MEMBER|U24E2NativeSession|Method|Byte[] ReadStderr()',
    'MEMBER|U24E2NativeSession|Method|Byte[] ReadStdout()',
    'MEMBER|U24E2NativeSession|Method|Int32 ExitCode()',
    'MEMBER|U24E2NativeSession|Method|Int64 get_StderrDropped()',
    'MEMBER|U24E2NativeSession|Method|Int64 get_StdoutDropped()',
    'MEMBER|U24E2NativeSession|Method|UInt32 get_Id()',
    'MEMBER|U24E2NativeSession|Method|UInt32[] DrainJobMessages()',
    'MEMBER|U24E2NativeSession|Method|UInt64 PeakJobMemory()',
    'MEMBER|U24E2NativeSession|Method|Void CloseJob()',
    'MEMBER|U24E2NativeSession|Method|Void Dispose()',
    'MEMBER|U24E2NativeSession|Method|Void Resume()',
    'MEMBER|U24E2NativeSession|Method|Void Terminate(UInt32)',
    'MEMBER|U24E2NativeSession|Property|Boolean CaptureWritersClosed',
    'MEMBER|U24E2NativeSession|Property|Boolean ControlPipeEscape',
    'MEMBER|U24E2NativeSession|Property|Boolean OutputExceeded',
    'MEMBER|U24E2NativeSession|Property|Int64 StderrDropped',
    'MEMBER|U24E2NativeSession|Property|Int64 StdoutDropped',
    'MEMBER|U24E2NativeSession|Property|UInt32 Id',
    'TYPE|U24E2PumpState|System.Object|1048833',
    'MEMBER|U24E2PumpState|Constructor|Void .ctor(Int64)',
    'MEMBER|U24E2PumpState|Field|Int32 Exceeded',
    'MEMBER|U24E2PumpState|Field|Int64 Limit',
    'MEMBER|U24E2PumpState|Field|Int64 Retained',
    'MEMBER|U24E2PumpState|Field|Int64 StderrDropped',
    'MEMBER|U24E2PumpState|Field|Int64 StdoutDropped',
    'MEMBER|U24E2PumpState|Field|System.String Error',
    'MEMBER|U24E2PumpState|Method|Boolean Reserve(Int32, Boolean)'
)
$NativeAssemblyBase64 = @'
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
EAB8AAAADQBIAE0ACwEQAJAAAAANAEwATQALARAAnAAAAA0AUgBNAAsBEAC+AAAADQBbAE0ACwEQAOMAAAANAGEATQADARAAFxAAAAUAYwBNAAMBEADoEAAA
BQBoAFMAJgA0AQoABgA6AQoABgBDAQoABgBRAQoABgBfAQ0ABgBoARAAAwB8AR4AAwCKAR4AAwCXAR4AAwChAR4AAwDFASEAAwDQASEAAwD3ASUAAwACAiUA
AwANAhAAAwAYAhAAAwAjAikAIwBKAi0AAwBWAjQAAwBeAjQAAwBpAjQAAwB3AjQAAwCHAjcAAwDGA3IAAwCXAR4AAwChAR4AAwD3ASUAAwACAiUAAwANAhAA
AwAYAhAAAwAjAikAIwBKAi0AAwBeAjQAAwBpAjQAUYDbAzcAUYDsAzcAUYD9AzcAUYAYBDcAUYAtBDcAUYBBBDcAUYBOBDcAUYBcBDcAUYBsBDcAUYB9BDcA
UYCLBDcAUYCrBDcAUYDLBDcAUYDnBDcAUYAKBTcAUYAYBTcABgCLBw0ABgCTBx4ABgCoBw0ABgC3Bw0ABgC6BxAABgDFBxAABgDPBxAABgDXBw0ABgDbBw0A
BgDfBw0ABgDnBw0ABgDvBw0ABgD9Bw0ABgALCA0ABgAbCA0ABgAjCMwBBgAvCMwBBgA7CB4ABgBHCB4ABgBRCB4ABgBcCB4ABgBmCB4ABgBvCB4ABgB3CDcA
BgCDCDcABgCOCM8BBgChCM8BBgC1CM8BBgDJCM8BBgDbCM8BBgDuCM8BBgABCQoABgAZCQoABgAtCTcABgA4CdIBBgBOCdIBBgBkCTcABgB3CdIBBgCACTcA
BgCOCTcABgCeCdUBBgC0CdkBBgC7CdIBBgDOCdIBBgDdCdIBBgDzCdIBBgAFCh4ABgChAR4ABgAqEB4ABgA4EKUDBgAiC3IABgCsCxAABgC3CxAABgD8ENAD
BgA4ENQDUCAAAAAAhhhuARMAAQBgIAAAAACGAHQBGAACAMkgAAAAAIYIkQI6AAQA4SAAAAAAhgikAj4ABADzIAAAAACGCLYCPgAEAAUhAAAAAIYIyAI6AAQA
DSEAAAAAhgjeAjoABAAVIQAAAACGCPcCQgAEAFEhAAAAAIMA/gJGAAQArCEAAAAAhgAJA0YABACQIgAAAACGABADSgAEAMMiAAAAAIYAFQNPAAUA8CIAAAAA
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
bgEVAtEArQ19AgwAug1UADkAzgNUADkA/A1KADkAFQ6XAtkAKA6cAjkANw6XAuEAcgNGAOkAbgEVAsEAjw6hAvEAbgEVAkEAbgFGAEEAqQ6mAsEAsA6sAkEA
qQ6xAsEAug5UAAkAxQ64AkEAug5UAEEAqQ7FAlEAzg5GAAwAcAxNAgwA1Q7ZAgwAdw1TAvkAbgHfAgwA/w7nAgkBbgEVArEAbgHdARwAJw//AiQAbgHnAhkB
Pw8PAyQAYQ8VAyQAcQ8gAywAfw8xAxwA1Q42AywAiw86ABEAcgNGADEBnQ89AzEBqQ9DA6EAsg9JA6EAvw9OAzkBbgFrA0EB4w9wA6EA9Q95A6EA/A+AA6EA
CxCOAzkBUQ3SAVEBbgEVAjkA3RCpA0EAbgEVAlkBbgHYAyEAbgHeA2kBcgNGACEAbgEVBGEAjhEnBGEAawwvBCEAlBE3BEkAmhE8BEEBohG4AkkArxG4AsEA
uxFCBKEAwhFTBDkB0RFYAJEBbgFkBAkAjAB6AAkAkAB/AAkAlACEAAkAmACJAAkAnACOAAkAoACTAAkApACYAAkAqACOAAkArACdAAkAsACiAAkAtACnAAkA
uACJAAkAvACsAAkAwACxAAkAxAC2AAkAyAC7AC4AEwBrBC4AGwB0BKMBUwCOAMMBUwCOAMACUwCOAOACUwCOAAADUwCOACADUwCOAEADUwCOAGADUwCOAIAD
UwCOAKADUwCOAKAFUwCOAMAFUwCOAP4BKwJDAlkCcwKDAowCvALLAtQC8gJXA5gDrQPqA0kEWwQDAAEABAAHAAAAegNmAAAAQwFqAAAAUQFqAAAAiQNmAAAA
mwNmAAAAsANuAAAAegNmAAAAQwFqAAAAUQFqAAAAHwN2AAAAmwNmAAIAAwADAAIABAAFAAIABQAHAAIABgAJAAIABwALAAIACAANAAIAHgAPAAIAHwARAAIA
IAATAAIAIQAVAAIAIgAXAIIOJAJHAvgCCQMqA0ABXwAlBQEAQAFhADAFAQBEAWMARQUBAEQBZQBqBQEARAFnAHgFAQBAAWkAiAUBAEABawCgBQEAQAFtALoF
AQBAAW8A0wUBAEABcQDsBQEAQAFzAAMGAQBAAXUAFgYBAEABdwAwBgEAQAF5AEkGAQBAAXsAWwYBAEABfQByBgEABIAAAAAAAAAAAAAAAAAAAAAAUAAAAAQA
AAAAAAAAAAAAAAEABwEAAAAABAAAAAAAAAAAAAAAAQAQAQAAAAAGAAUABwAFAAgABQAJAAUACgAFAAsABQAMAAUADQAFAA4ABQCPAIkDjwCTAwAAADxNb2R1
bGU+AFUyNEUyTmF0aXZlLmRsbABVMjRFMlB1bXBTdGF0ZQBVMjRFMk5hdGl2ZVNlc3Npb24AVTI0RTJNYW5hZ2VkU2Vzc2lvbgBVMjRFMk5hdGl2ZQBTRUNV
UklUWV9BVFRSSUJVVEVTAFNUQVJUVVBJTkZPAFBST0NFU1NfSU5GT1JNQVRJT04ASU9fQ09VTlRFUlMASk9CT0JKRUNUX0JBU0lDX0xJTUlUX0lORk9STUFU
SU9OAEpPQk9CSkVDVF9FWFRFTkRFRF9MSU1JVF9JTkZPUk1BVElPTgBKT0JPQkpFQ1RfQVNTT0NJQVRFX0NPTVBMRVRJT05fUE9SVABtc2NvcmxpYgBTeXN0
ZW0AT2JqZWN0AElEaXNwb3NhYmxlAFZhbHVlVHlwZQBMaW1pdABSZXRhaW5lZABTdGRvdXREcm9wcGVkAFN0ZGVyckRyb3BwZWQARXhjZWVkZWQARXJyb3IA
LmN0b3IAUmVzZXJ2ZQBQcm9jZXNzSGFuZGxlAFRocmVhZEhhbmRsZQBKb2JIYW5kbGUAQ29tcGxldGlvblBvcnQAU3lzdGVtLklPAEZpbGVTdHJlYW0AU3Rk
b3V0UmVhZABTdGRlcnJSZWFkAFN5c3RlbS5UaHJlYWRpbmcuVGFza3MAVGFzawBTdGRvdXRUYXNrAFN0ZGVyclRhc2sAU3Rkb3V0UGF0aABTdGRlcnJQYXRo
AFB1bXAAU3lzdGVtLkNvbGxlY3Rpb25zLkdlbmVyaWMATGlzdGAxAEpvYk1lc3NhZ2VzAFJlc3VtZWQAUGlwZUVzY2FwZQBXcml0ZXJzQ2xvc2VkAENsZWFu
dXBDb21wbGV0ZQBQcm9jZXNzSWQAZ2V0X091dHB1dEV4Y2VlZGVkAGdldF9TdGRvdXREcm9wcGVkAGdldF9TdGRlcnJEcm9wcGVkAGdldF9Db250cm9sUGlw
ZUVzY2FwZQBnZXRfQ2FwdHVyZVdyaXRlcnNDbG9zZWQAZ2V0X0lkAFN0YXJ0UHVtcHMAUmVzdW1lAFdhaXQAVGVybWluYXRlAEV4aXRDb2RlAFBlYWtKb2JN
ZW1vcnkARHJhaW5Kb2JNZXNzYWdlcwBGaW5pc2hQdW1wcwBSZWFkU3Rkb3V0AFJlYWRTdGRlcnIAQ2xvc2VKb2IARGlzcG9zZQBPdXRwdXRFeGNlZWRlZABD
b250cm9sUGlwZUVzY2FwZQBDYXB0dXJlV3JpdGVyc0Nsb3NlZABJZABTeXN0ZW0uRGlhZ25vc3RpY3MAUHJvY2VzcwBnZXRfRXhpdENvZGUAQ1JFQVRFX1NV
U1BFTkRFRABDUkVBVEVfTk9fV0lORE9XAENSRUFURV9VTklDT0RFX0VOVklST05NRU5UAFNUQVJURl9VU0VTVERIQU5ETEVTAEhBTkRMRV9GTEFHX0lOSEVS
SVQAR0VORVJJQ19SRUFEAEdFTkVSSUNfV1JJVEUARklMRV9TSEFSRV9SRUFEAEZJTEVfU0hBUkVfV1JJVEUAT1BFTl9FWElTVElORwBKT0JfT0JKRUNUX0xJ
TUlUX0FDVElWRV9QUk9DRVNTAEpPQl9PQkpFQ1RfTElNSVRfUFJPQ0VTU19NRU1PUlkASk9CX09CSkVDVF9MSU1JVF9KT0JfTUVNT1JZAEpPQl9PQkpFQ1Rf
TElNSVRfS0lMTF9PTl9KT0JfQ0xPU0UAV0FJVF9PQkpFQ1RfMABXQUlUX1RJTUVPVVQAQ3JlYXRlUGlwZQBTZXRIYW5kbGVJbmZvcm1hdGlvbgBDcmVhdGVG
aWxlAFN5c3RlbS5UZXh0AFN0cmluZ0J1aWxkZXIAQ3JlYXRlUHJvY2VzcwBDcmVhdGVKb2JPYmplY3QAU2V0SW5mb3JtYXRpb25Kb2JPYmplY3QAUXVlcnlJ
bmZvcm1hdGlvbkpvYk9iamVjdABBc3NpZ25Qcm9jZXNzVG9Kb2JPYmplY3QAVGVybWluYXRlSm9iT2JqZWN0TmF0aXZlAFRlcm1pbmF0ZVByb2Nlc3NOYXRp
dmUAUmVzdW1lVGhyZWFkTmF0aXZlAFdhaXRGb3JTaW5nbGVPYmplY3ROYXRpdmUAR2V0RXhpdENvZGVQcm9jZXNzTmF0aXZlAENsb3NlSGFuZGxlTmF0aXZl
AENyZWF0ZUlvQ29tcGxldGlvblBvcnQAR2V0UXVldWVkQ29tcGxldGlvblN0YXR1c05hdGl2ZQBRdW90ZQBCdWlsZEFyZ3VtZW50TGluZQBFeGNlcHRpb24A
QWN0aW9uAFRyeUNsZWFudXAAQ2xlYW51cEZhaWx1cmUAQ29tYmluZUZhaWx1cmUAVGVybWluYXRlQW5kV2FpdFByb2Nlc3MAQ2xvc2VIYW5kbGVDb2xsZWN0
AENsb3NlUmVxdWlyZWQASURpY3Rpb25hcnlgMgBFbnZpcm9ubWVudEJsb2NrAE1ha2VKb2IAQXR0YWNoTWFuYWdlZFByb2Nlc3MAU3RhcnRTdXNwZW5kZWQA
U3RyZWFtAFB1bXBQaXBlAFF1ZXJ5UGVha0pvYk1lbW9yeQBuTGVuZ3RoAGxwU2VjdXJpdHlEZXNjcmlwdG9yAGJJbmhlcml0SGFuZGxlAGNiAGxwUmVzZXJ2
ZWQAbHBEZXNrdG9wAGxwVGl0bGUAZHdYAGR3WQBkd1hTaXplAGR3WVNpemUAZHdYQ291bnRDaGFycwBkd1lDb3VudENoYXJzAGR3RmlsbEF0dHJpYnV0ZQBk
d0ZsYWdzAHdTaG93V2luZG93AGNiUmVzZXJ2ZWQyAGxwUmVzZXJ2ZWQyAGhTdGRJbnB1dABoU3RkT3V0cHV0AGhTdGRFcnJvcgBoUHJvY2VzcwBoVGhyZWFk
AGR3UHJvY2Vzc0lkAGR3VGhyZWFkSWQAUmVhZE9wZXJhdGlvbkNvdW50AFdyaXRlT3BlcmF0aW9uQ291bnQAT3RoZXJPcGVyYXRpb25Db3VudABSZWFkVHJh
bnNmZXJDb3VudABXcml0ZVRyYW5zZmVyQ291bnQAT3RoZXJUcmFuc2ZlckNvdW50AFBlclByb2Nlc3NVc2VyVGltZUxpbWl0AFBlckpvYlVzZXJUaW1lTGlt
aXQATGltaXRGbGFncwBNaW5pbXVtV29ya2luZ1NldFNpemUATWF4aW11bVdvcmtpbmdTZXRTaXplAEFjdGl2ZVByb2Nlc3NMaW1pdABBZmZpbml0eQBQcmlv
cml0eUNsYXNzAFNjaGVkdWxpbmdDbGFzcwBCYXNpY0xpbWl0SW5mb3JtYXRpb24ASW9JbmZvAFByb2Nlc3NNZW1vcnlMaW1pdABKb2JNZW1vcnlMaW1pdABQ
ZWFrUHJvY2Vzc01lbW9yeVVzZWQAUGVha0pvYk1lbW9yeVVzZWQAQ29tcGxldGlvbktleQBsaW1pdABjb3VudABzdGRlcnIAbWlsbGlzZWNvbmRzAGNvZGUA
ZW9mTWlsbGlzZWNvbmRzAHJlYWQAU3lzdGVtLlJ1bnRpbWUuSW50ZXJvcFNlcnZpY2VzAE91dEF0dHJpYnV0ZQB3cml0ZQBhdHRyaWJ1dGVzAHNpemUAaGFu
ZGxlAG1hc2sAZmxhZ3MAbmFtZQBhY2Nlc3MAc2hhcmUAY3JlYXRpb24AdGVtcGxhdGUAYXBwbGljYXRpb24AY29tbWFuZABwYQB0YQBpbmhlcml0AGVudmly
b25tZW50AGN3ZABzdGFydHVwAGluZm8Aam9iAGluZm9DbGFzcwBsZW5ndGgAcmV0dXJuZWQAcHJvY2VzcwB0aHJlYWQAZmlsZQBleGlzdGluZwBrZXkAdGhy
ZWFkcwBwb3J0AGJ5dGVzAG92ZXJsYXBwZWQAdmFsdWUAYXJndW1lbnRzAGVycm9ycwBhY3Rpb24AcHJpbWFyeQBjbGVhbnVwAHNjaWVudGlmaWMAbWVtb3J5
AGNvbXBsZXRpb24Ac3Rkb3V0UGF0aABzdGRlcnJQYXRoAG91dHB1dExpbWl0AGV4ZWN1dGFibGUAaW5wdXQAb3V0cHV0UGF0aABzdGF0ZQBTeXN0ZW0uUnVu
dGltZS5Db21waWxlclNlcnZpY2VzAENvbXBpbGF0aW9uUmVsYXhhdGlvbnNBdHRyaWJ1dGUAUnVudGltZUNvbXBhdGliaWxpdHlBdHRyaWJ1dGUAU3lzdGVt
LlRocmVhZGluZwBJbnRlcmxvY2tlZABSZWFkAEFkZABFeGNoYW5nZQBDb21wYXJlRXhjaGFuZ2UAVm9sYXRpbGUAPFN0YXJ0UHVtcHM+Yl9fMAA8U3RhcnRQ
dW1wcz5iX18xAENvbXBpbGVyR2VuZXJhdGVkQXR0cmlidXRlAFJ1bgA8UmVzdW1lPmJfXzIAPFJlc3VtZT5iX18zAEludmFsaWRPcGVyYXRpb25FeGNlcHRp
b24ATWFyc2hhbABHZXRMYXN0V2luMzJFcnJvcgBTeXN0ZW0uQ29tcG9uZW50TW9kZWwAV2luMzJFeGNlcHRpb24ASW50UHRyAFplcm8Ab3BfSW5lcXVhbGl0
eQBvcF9FcXVhbGl0eQBVSW50MzIAVG9BcnJheQBXYWl0QWxsAFN0cmluZwBJc051bGxPckVtcHR5AElPRXhjZXB0aW9uAEZpbGUAUmVhZEFsbEJ5dGVzAGdl
dF9Db3VudAA8RGlzcG9zZT5iX182ADxEaXNwb3NlPmJfXzcAPERpc3Bvc2U+Yl9fOAA8RGlzcG9zZT5iX185AFdhaXRGb3JFeGl0AFN0cmVhbVJlYWRlcgBn
ZXRfU3RhbmRhcmRPdXRwdXQAZ2V0X0Jhc2VTdHJlYW0AZ2V0X1N0YW5kYXJkRXJyb3IAPERpc3Bvc2U+Yl9fMAA8RGlzcG9zZT5iX18xAENvbXBvbmVudABE
bGxJbXBvcnRBdHRyaWJ1dGUAa2VybmVsMzIuZGxsAEluZGV4T2YAQXJndW1lbnRFeGNlcHRpb24AQXBwZW5kAGdldF9DaGFycwBnZXRfTGVuZ3RoAFRvU3Ry
aW5nAEludm9rZQBnZXRfSXRlbQBBZ2dyZWdhdGVFeGNlcHRpb24ASUVudW1lcmFibGVgMQBBZGRSYW5nZQBUaW1lb3V0RXhjZXB0aW9uAElDb2xsZWN0aW9u
YDEAZ2V0X0tleXMAU3RyaW5nQ29tcGFyZXIAZ2V0X09yZGluYWxJZ25vcmVDYXNlAElDb21wYXJlcmAxAFNvcnQARW51bWVyYXRvcgBHZXRFbnVtZXJhdG9y
AGdldF9DdXJyZW50AE1vdmVOZXh0AEVuY29kaW5nAGdldF9Vbmljb2RlAEdldEJ5dGVzAEFsbG9jSEdsb2JhbABDb3B5AFVJbnRQdHIAVHlwZQBSdW50aW1l
VHlwZUhhbmRsZQBHZXRUeXBlRnJvbUhhbmRsZQBTaXplT2YAU3RydWN0dXJlVG9QdHIARnJlZUhHbG9iYWwAPD5jX19EaXNwbGF5Q2xhc3NhAHByb2Nlc3NI
YW5kbGUAc2Vzc2lvbgA8QXR0YWNoTWFuYWdlZFByb2Nlc3M+Yl9fMAA8QXR0YWNoTWFuYWdlZFByb2Nlc3M+Yl9fMQA8QXR0YWNoTWFuYWdlZFByb2Nlc3M+
Yl9fMgA8QXR0YWNoTWFuYWdlZFByb2Nlc3M+Yl9fMwA8QXR0YWNoTWFuYWdlZFByb2Nlc3M+Yl9fNABBcmd1bWVudE51bGxFeGNlcHRpb24AZ2V0X0hhbmRs
ZQA8PmNfX0Rpc3BsYXlDbGFzczEwAHBpADxTdGFydFN1c3BlbmRlZD5iX19jADxTdGFydFN1c3BlbmRlZD5iX19kAE1pY3Jvc29mdC5XaW4zMi5TYWZlSGFu
ZGxlcwBTYWZlRmlsZUhhbmRsZQBGaWxlQWNjZXNzAFNhZmVIYW5kbGUARmlsZU1vZGUARmlsZVNoYXJlAEZpbGVPcHRpb25zAEJ5dGUAV3JpdGUARmx1c2gA
R2V0VHlwZQBnZXRfRnVsbE5hbWUAZ2V0X01lc3NhZ2UAQ29uY2F0AFB0clRvU3RydWN0dXJlAFRvVUludDY0AFN0cnVjdExheW91dEF0dHJpYnV0ZQBMYXlv
dXRLaW5kAAAAN3AAcgBvAGMAZQBzAHMAIAB3AGEAcwAgAGEAbAByAGUAYQBkAHkAIAByAGUAcwB1AG0AZQBkAAAnUgBlAHMAdQBtAGUAVABoAHIAZQBhAGQA
IABmAGEAaQBsAGUAZAAARXIAZQBzAHUAbQBlAGQAIAB0AGgAcgBlAGEAZAAgAGgAYQBuAGQAbABlACAAYwBsAG8AcwBlACAAZgBhAGkAbABlAGQAADVhAHIA
ZwB1AG0AZQBuAHQAIABjAG8AbgB0AHIAbwBsACAAYwBoAGEAcgBhAGMAdABlAHIAAFNtAHUAbAB0AGkAcABsAGUAIABuAGEAdABpAHYAZQAgAGMAbABlAGEA
bgB1AHAAIABvAHAAZQByAGEAdABpAG8AbgBzACAAZgBhAGkAbABlAGQAAG9wAHIAaQBtAGEAcgB5ACAAbgBhAHQAaQB2AGUAIABvAHAAZQByAGEAdABpAG8A
bgAgAGEAbgBkACAAYwBvAG4AdABhAGkAbgBtAGUAbgB0ACAAYwBsAGUAYQBuAHUAcAAgAGYAYQBpAGwAZQBkAAA3aQBuAGkAdABpAGEAbAAgAHAAcgBvAGMA
ZQBzAHMAIAB3AGEAaQB0ACAAZgBhAGkAbABlAGQAAFdUAGUAcgBtAGkAbgBhAHQAZQBQAHIAbwBjAGUAcwBzACAAZgBhAGkAbABlAGQAIABiAGUAZgBvAHIA
ZQAgAGIAbwB1AG4AZABlAGQAIAB3AGEAaQB0AABNdABlAHIAbQBpAG4AYQB0AGUAZAAgAHAAcgBvAGMAZQBzAHMAIABtAGkAcwBzAGUAZAAgAGIAbwB1AG4A
ZABlAGQAIAB3AGEAaQB0AAA9dABlAHIAbQBpAG4AYQB0AGUAZAAgAHAAcgBvAGMAZQBzAHMAIAB3AGEAaQB0ACAAZgBhAGkAbABlAGQAADVuAGEAdABpAHYA
ZQAgAGgAYQBuAGQAbABlACAAYwBsAG8AcwBlACAAZgBhAGkAbABlAGQAACdpAG4AdgBhAGwAaQBkACAAZQBuAHYAaQByAG8AbgBtAGUAbgB0AAAPcAByAG8A
YwBlAHMAcwAAVXMAYwBpAGUAbgB0AGkAZgBpAGMAIABBAHMAcwBpAGcAbgBQAHIAbwBjAGUAcwBzAFQAbwBKAG8AYgBPAGIAagBlAGMAdAAgAGYAYQBpAGwA
ZQBkAAAHTgBVAEwAAE9jAG8AbgB0AHIAbwBsACAAQQBzAHMAaQBnAG4AUAByAG8AYwBlAHMAcwBUAG8ASgBvAGIATwBiAGoAZQBjAHQAIABmAGEAaQBsAGUA
ZAAABToAIAAAAL1kHtSZtjpFro+VfTWb2fQACLd6XFYZNOCJAgYKAgYIAgYOBCABAQoFIAICCAICBhgDBhIRAwYSFQMGEggGBhUSGQEJAgYCAgYJAyAAAgMg
AAoDIAAJAyAAAQQgAQIIBCABAQkDIAAIAyAACwQgAB0JBCAAHQUDKAACAygACgMoAAkDBhIdAygACAQEAAAABAAAAAgEAAQAAAQAAQAABAEAAAAEAAAAgAQA
AABABAIAAAAEAwAAAAQIAAAABAACAAAEACAAAAQAAAAABAIBAAALAAQCEBgQGBARGAgGAAMCGAkJDAAHGA4JCRARGAkJGBIACgIOEiEYGAIJGA4QERwQESAF
AAIYGA4HAAQCGAgYCQkABQIYCBgJEAkFAAICGBgFAAICGAkEAAEJGAUAAgkYCQYAAgIYEAkEAAECGAcABBgYGBkJCwAFAhgQCRAZEBgJBAABDg4FAAEOHQ4L
AAIBFRIZARIlEikKAAESJRUSGQESJQwAAhIlEiUVEhkBEiUGAAMBGAkJCwACARAYFRIZARIlBQABARAYCQABGBUSLQIODggABBgCCwIQGAoABRIQEh0ODgoL
FAAKEgwOHQ4OFRItAg4ODg4KAgsCCQAEARIxDhIIAgQAAQsYAgYGAgYLAgYZAwYRKAMGESQEIAEBCAUAAQoQCgYAAgoQCgoGAAIIEAgIBwADChAKCgoDBwEK
BQABCBAIBSACARwYBgABEhUSKQQgAQEOAwAACAUgAgEIDgYVEhkBEiUXBwcJEiUVEhkBEiUSJRUSGQESJRIpEikDBwEJBRUSGQEJBSABARMABSAAHRMADAcG
FRIZAQkJGRgCCAcAAgIdEhUIBAABAg4JBwMdEhUCHRIVBQABHQUOCAcBFRIZARIlCgcCFRIZARIlEikEIAASbQQgABIxBCABCAMFIAESIQMEIAEDCAYgAhIh
AwgDIAAOCAcFEiEIAw4IBSABEiEOCAcEEiEOHQ4IBAcBEiUFIAETAAgHIAIBDh0SJQogAQEVEoCBARMABQcDCQgJBhUSLQIODgkgABUSgIkBEwAFFRIZAQ4F
AAASgI0KIAEBFRKAkQETAAkgABURgJUBEwAGFRGAlQEOBCAAEwAGIAETARMABQAAEoCZBSABHQUOBAABGAgIAAQBHQUIGAgTBwYVEhkBDhIhDh0FGBURgJUB
DgQgAQELCAABEoChEYClBgABCBKAoQgQAQMBHgAYAgQKAREsBAABARgECgERMAwHCBgRLAgYETAIGBgDBhIQAyAAGCIHDRgYEiUVEhkBEiUSJRUSGQESJRIp
EikSKRIpEikSNBIQAwYRIAMGEgwFIAIBGAILIAQBEoCtEYCxCAIqBxYRGBgYGBgYGBgYEiEOERwSgK0SgK0SJRUSGQESJRIpEikSOBIMHQ4IESAGAQ4RgLkR
gLERgL0IEYDBByADAR0FCAgHIAMIHQUICAQgAQECBSAAEoChBgADDg4ODgkHBBIRHQUIEiUHAAIcGBKAoQgHBQgYCREsCwYgAQERgM0IAQAIAAAAAAAeAQAB
AFQCFldyYXBOb25FeGNlcHRpb25UaHJvd3MBACxjAAAAAAAAAAAAAE5jAAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAYwAAAAAAAAAAAAAAAAAAAAAAAAAA
X0NvckRsbE1haW4AbXNjb3JlZS5kbGwAAAAAAP8lACAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAQAAAAGAAAgAAAAAAAAAAAAAAAAAAAAQABAAAAMAAAgAAAAAAAAAAAAAAAAAAAAQAAAAAASAAAAFiAAABUAgAA
AAAAAAAAAABUAjQAAABWAFMAXwBWAEUAUgBTAEkATwBOAF8ASQBOAEYATwAAAAAAvQTv/gAAAQAAAAAAAAAAAAAAAAAAAAAAPwAAAAAAAAAEAAAAAgAAAAAA
AAAAAAAAAAAAAEQAAAABAFYAYQByAEYAaQBsAGUASQBuAGYAbwAAAAAAJAAEAAAAVAByAGEAbgBzAGwAYQB0AGkAbwBuAAAAAAAAALAEtAEAAAEAUwB0AHIA
aQBuAGcARgBpAGwAZQBJAG4AZgBvAAAAkAEAAAEAMAAwADAAMAAwADQAYgAwAAAALAACAAEARgBpAGwAZQBEAGUAcwBjAHIAaQBwAHQAaQBvAG4AAAAAACAA
AAAwAAgAAQBGAGkAbABlAFYAZQByAHMAaQBvAG4AAAAAADAALgAwAC4AMAAuADAAAABAABAAAQBJAG4AdABlAHIAbgBhAGwATgBhAG0AZQAAAFUAMgA0AEUA
MgBOAGEAdABpAHYAZQAuAGQAbABsAAAAKAACAAEATABlAGcAYQBsAEMAbwBwAHkAcgBpAGcAaAB0AAAAIAAAAEgAEAABAE8AcgBpAGcAaQBuAGEAbABGAGkA
bABlAG4AYQBtAGUAAABVADIANABFADIATgBhAHQAaQB2AGUALgBkAGwAbAAAADQACAABAFAAcgBvAGQAdQBjAHQAVgBlAHIAcwBpAG8AbgAAADAALgAwAC4A
MAAuADAAAAA4AAgAAQBBAHMAcwBlAG0AYgBsAHkAIABWAGUAcgBzAGkAbwBuAAAAMAAuADAALgAwAC4AMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAYAAADAAAAGAzAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAA==
'@

# NativeSource is retained above as the auditable source.  The helper was built
# once with frozen Windows PowerShell 5.1/.NET Framework and is loaded only from
# these content-addressed bytes; the endpoint runner never invokes a compiler.
function Initialize-NativeHelper {
    $nativeSourceBytes = [Text.UTF8Encoding]::new($false).GetBytes($NativeSource)
    if ($nativeSourceBytes.Length -ne $NativeSourceByteLength -or (Get-Sha256Bytes -Bytes $nativeSourceBytes) -cne $NativeSourceSha256) {
        throw "embedded native helper source identity mismatch"
    }
    try { $nativeAssemblyBytes = [Convert]::FromBase64String($NativeAssemblyBase64) }
    catch { throw "embedded native helper assembly base64 is invalid" }
    if ($nativeAssemblyBytes.Length -ne $NativeAssemblyByteLength -or (Get-Sha256Bytes -Bytes $nativeAssemblyBytes) -cne $NativeAssemblySha256) {
        throw "embedded native helper assembly identity mismatch"
    }
    $assembly = [Reflection.Assembly]::Load($nativeAssemblyBytes)
    if ($assembly.FullName -cne $NativeAssemblyFullName) { throw "embedded native helper full name mismatch" }
    if ($assembly.ManifestModule.ModuleVersionId.ToString("D") -cne $NativeAssemblyMvid) {
        throw "embedded native helper MVID mismatch"
    }
    $nativeSurfaceFlags = [Reflection.BindingFlags]"Public,Instance,Static,DeclaredOnly"
    [string[]]$nativeTypeNames = @($assembly.GetExportedTypes() | ForEach-Object { $_.FullName })
    [Array]::Sort($nativeTypeNames, [StringComparer]::Ordinal)
    $observedNativeSurface = [Collections.Generic.List[string]]::new()
    foreach ($nativeTypeName in $nativeTypeNames) {
        $nativeType = $assembly.GetType($nativeTypeName, $true, $false)
        $nativeBaseName = if ($null -eq $nativeType.BaseType) { "" } else { $nativeType.BaseType.FullName }
        $observedNativeSurface.Add(("TYPE|{0}|{1}|{2}" -f $nativeType.FullName, $nativeBaseName, [int]$nativeType.Attributes))
        [string[]]$nativeMemberRows = @($nativeType.GetMembers($nativeSurfaceFlags) | ForEach-Object {
            "MEMBER|{0}|{1}|{2}" -f $nativeType.FullName, $_.MemberType, $_.ToString()
        })
        [Array]::Sort($nativeMemberRows, [StringComparer]::Ordinal)
        foreach ($nativeMemberRow in $nativeMemberRows) { $observedNativeSurface.Add($nativeMemberRow) }
    }
    if ($observedNativeSurface.Count -ne $NativeAssemblySurface.Count) { throw "embedded native helper exported surface count mismatch" }
    for ($nativeSurfaceIndex = 0; $nativeSurfaceIndex -lt $NativeAssemblySurface.Count; $nativeSurfaceIndex++) {
        if ($observedNativeSurface[$nativeSurfaceIndex] -cne $NativeAssemblySurface[$nativeSurfaceIndex]) {
            throw "embedded native helper exported surface mismatch"
        }
    }
    return $assembly
}

$script:GitInvocationCount = 0
$script:GitAggregateTicks = [int64]0
$script:ControlPipeEscapeObserved = $false

function New-GitEnvironment {
    $environment = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::OrdinalIgnoreCase)
    $environment["SystemRoot"] = $env:SystemRoot
    $environment["WINDIR"] = $env:WINDIR
    $environment["ComSpec"] = $env:ComSpec
    $environment["TEMP"] = [IO.Path]::GetTempPath().TrimEnd('\')
    $environment["TMP"] = [IO.Path]::GetTempPath().TrimEnd('\')
    $environment["USERPROFILE"] = $env:USERPROFILE
    $environment["HOME"] = $env:USERPROFILE
    $environment["APPDATA"] = $env:APPDATA
    $environment["LOCALAPPDATA"] = $env:LOCALAPPDATA
    $environment["PROGRAMDATA"] = $env:PROGRAMDATA
    $environment["PATH"] = "C:\Program Files\Git\cmd;C:\Program Files\Git\mingw64\bin;C:\Windows\System32;C:\Windows"
    $environment["PATHEXT"] = ".COM;.EXE;.BAT;.CMD"
    $environment["GIT_TERMINAL_PROMPT"] = "0"
    $environment["GCM_INTERACTIVE"] = "Never"
    $environment["GIT_CONFIG_NOSYSTEM"] = "1"
    $environment["GIT_CONFIG_GLOBAL"] = "NUL"
    $environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    $environment["GIT_GRAFT_FILE"] = "NUL"
    $environment["GIT_NO_LAZY_FETCH"] = "1"
    $environment["GIT_OPTIONAL_LOCKS"] = "0"
    $environment["GIT_CEILING_DIRECTORIES"] = [IO.Path]::GetTempPath().TrimEnd('\')
    return $environment
}

function Invoke-BoundedGit {
    param(
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [Parameter(Mandatory = $true)][string] $RepositoryRoot,
        [int] $WallSeconds = $ControlLocalWallSeconds,
        [Parameter(Mandatory = $true)][string] $ScratchRoot
    )
    $script:GitInvocationCount++
    if ($script:GitInvocationCount -gt $ControlMaxInvocations) { throw "Git invocation cap exceeded" }
    if ($WallSeconds -notin @($ControlLocalWallSeconds, $ControlRemoteWallSeconds)) { throw "unregistered Git wall" }
    $aggregateLimitTicks = [int64]($ControlAggregateWallSeconds * $StopwatchFrequency)
    $aggregateRemainingTicks = $aggregateLimitTicks - $script:GitAggregateTicks
    if ($aggregateRemainingTicks -le 0) { throw "aggregate Git wall was exhausted before invocation" }
    $callLimitTicks = [Math]::Min([int64]($WallSeconds * $StopwatchFrequency), $aggregateRemainingTicks)

    $callRoot = Join-Path $ScratchRoot ("git-{0:D2}" -f $script:GitInvocationCount)
    $callRoot = New-OwnedDirectory -LiteralPath $callRoot -RequiredParent $ScratchRoot
    $stdoutPath = Join-Path $callRoot "stdout.bin"
    $stderrPath = Join-Path $callRoot "stderr.bin"
    $allArguments = [Collections.Generic.List[string]]::new()
    $allArguments.Add("-c")
    $allArguments.Add("credential.interactive=never")
    foreach ($argument in $Arguments) { $allArguments.Add([string]$argument) }
    $session = $null
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $timedOut = $false
    $outputExceeded = $false
    try {
        Assert-NonReparsePath -LiteralPath $callRoot
        if (Test-Path -LiteralPath $stdoutPath) { throw "bounded Git stdout path pre-existed" }
        if (Test-Path -LiteralPath $stderrPath) { throw "bounded Git stderr path pre-existed" }
        $session = [U24E2Native]::StartSuspended(
            $GitPath,
            $allArguments.ToArray(),
            $RepositoryRoot,
            (New-GitEnvironment),
            $stdoutPath,
            $stderrPath,
            $ControlOutputLimitBytes,
            $false,
            [uint64]0,
            $false
        )
        $session.Resume()
        while (-not $session.Wait($PollMilliseconds)) {
            if ($session.OutputExceeded) {
                $outputExceeded = $true
                $session.Terminate([uint32]$ExitOutput)
                break
            }
            if ($timer.ElapsedTicks -ge $callLimitTicks) {
                $timedOut = $true
                $session.Terminate([uint32]$ExitTimeout)
                break
            }
        }
        if (-not $session.Wait(2000)) {
            $session.Terminate([uint32]$ExitRunnerBlocked)
            if (-not $session.Wait(2000)) { throw "bounded Git process did not terminate" }
        }
        if ($timer.ElapsedTicks -ge $callLimitTicks) { $timedOut = $true }
        $nativeExit = $session.ExitCode()
        $gitPumpsComplete = $false
        try { $gitPumpsComplete = [bool]$session.FinishPumps(2000) }
        finally {
            try {
                if ([bool]$session.ControlPipeEscape) { $script:ControlPipeEscapeObserved = $true }
            }
            catch { }
        }
        if (-not $gitPumpsComplete) { throw "bounded Git control pipe escaped EOF deadline" }
        Assert-NonReparsePath -LiteralPath $callRoot
        Assert-NonReparsePath -LiteralPath $stdoutPath
        Assert-NonReparsePath -LiteralPath $stderrPath
        $stdout = $session.ReadStdout()
        $stderr = $session.ReadStderr()
        if ($session.StdoutDropped -ne 0 -or $session.StderrDropped -ne 0) { $outputExceeded = $true }
        $session.CloseJob()
        if ($timedOut) { throw "bounded Git call exceeded $WallSeconds seconds" }
        if ($outputExceeded) { throw "bounded Git call exceeded combined output cap" }
        if ($nativeExit -ne 0) {
            $stderrText = [Text.UTF8Encoding]::new($false, $true).GetString($stderr)
            throw "bounded Git call failed with exit $nativeExit`: $stderrText"
        }
        if ($script:GitAggregateTicks + [int64]$timer.ElapsedTicks -gt $aggregateLimitTicks) {
            throw "aggregate Git wall exceeded 120 seconds"
        }
        return [pscustomobject][ordered]@{
            stdout = $stdout
            stderr = $stderr
            exit_code = $nativeExit
            elapsed_ticks = [int64]$timer.ElapsedTicks
        }
    }
    finally {
        $timer.Stop()
        $script:GitAggregateTicks += [int64]$timer.ElapsedTicks
        if ($script:GitAggregateTicks -gt $aggregateLimitTicks) {
            if ($null -ne $session) { try { $session.Terminate([uint32]$ExitTimeout) } catch { } }
        }
        if ($null -ne $session) {
            try {
                if ([bool]$session.ControlPipeEscape) { $script:ControlPipeEscapeObserved = $true }
            }
            catch { }
            $session.Dispose()
        }
    }
}

function Convert-GitUtf8 {
    param([Parameter(Mandatory = $true)][byte[]] $Bytes)
    return [Text.UTF8Encoding]::new($false, $true).GetString($Bytes)
}

function Parse-CommitObject {
    param([Parameter(Mandatory = $true)][string] $Text)
    $normalized = $Text.Replace("`r`n", "`n")
    $split = $normalized.IndexOf("`n`n", [StringComparison]::Ordinal)
    if ($split -lt 0) { throw "malformed Git commit object" }
    $headers = $normalized.Substring(0, $split).Split("`n")
    $message = $normalized.Substring($split + 2).TrimEnd("`n")
    $tree = $null
    $parents = [Collections.Generic.List[string]]::new()
    foreach ($line in $headers) {
        if ($line.StartsWith("tree ", [StringComparison]::Ordinal)) { $tree = $line.Substring(5) }
        elseif ($line.StartsWith("parent ", [StringComparison]::Ordinal)) { $parents.Add($line.Substring(7)) }
    }
    if ($tree -notmatch '^[0-9a-f]{40}$') { throw "commit tree is malformed" }
    foreach ($parent in $parents) { if ($parent -notmatch '^[0-9a-f]{40}$') { throw "commit parent is malformed" } }
    return [pscustomobject][ordered]@{ tree = $tree; parents = $parents.ToArray(); message = $message }
}

function Parse-LsTree {
    param(
        [Parameter(Mandatory = $true)][byte[]] $Bytes,
        [switch] $WithSize
    )
    $text = Convert-GitUtf8 -Bytes $Bytes
    $rows = [Collections.Generic.List[object]]::new()
    foreach ($record in $text.Split([char]0, [StringSplitOptions]::RemoveEmptyEntries)) {
        if ($WithSize) {
            if ($record -notmatch '^(?<mode>[0-9]{6}) (?<type>blob) (?<oid>[0-9a-f]{40}) +(?<size>[0-9]+)\t(?<path>.+)$') {
                throw "malformed sized ls-tree record"
            }
            $size = [int64]$Matches.size
        }
        else {
            if ($record -notmatch '^(?<mode>[0-9]{6}) (?<type>blob) (?<oid>[0-9a-f]{40})\t(?<path>.+)$') {
                throw "malformed ls-tree record"
            }
            $size = $null
        }
        $mode = $Matches.mode
        $type = $Matches.type
        $oid = $Matches.oid
        $path = $Matches.path
        if (-not (Test-SafeRelativePath -RelativePath $path)) { throw "unsafe Git tree path: $path" }
        $rows.Add([pscustomobject][ordered]@{
            mode = $mode
            type = $type
            oid = $oid
            size = $size
            path = $path
        })
    }
    return $rows.ToArray()
}

function Parse-DiffTree {
    param([Parameter(Mandatory = $true)][byte[]] $Bytes)
    $text = Convert-GitUtf8 -Bytes $Bytes
    $rows = [Collections.Generic.List[object]]::new()
    $records = @($text.Split([char]0, [StringSplitOptions]::RemoveEmptyEntries))
    if (($records.Count % 2) -ne 0) { throw "name-status -z did not contain status/path pairs" }
    for ($index = 0; $index -lt $records.Count; $index += 2) {
        $status = $records[$index]
        $path = $records[$index + 1]
        if ($status -notin @("A", "M")) { throw "unexpected diff-tree status: $status" }
        if (-not (Test-SafeRelativePath -RelativePath $path)) { throw "unsafe diff-tree path" }
        $rows.Add([pscustomobject][ordered]@{ status = $status; path = $path })
    }
    return $rows.ToArray()
}

function Get-Sha256Digest {
    param([Parameter(Mandatory = $true)][string] $LiteralPath)
    $stream = [IO.File]::Open($LiteralPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return $sha.ComputeHash($stream) }
    finally { $sha.Dispose(); $stream.Dispose() }
}

function ConvertTo-UrlSafeBase64 {
    param([Parameter(Mandatory = $true)][byte[]] $Bytes)
    return ([Convert]::ToBase64String($Bytes)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function Get-RuntimeInventory {
    Assert-NonReparsePath -LiteralPath $RuntimeSourceRoot
    $rows = [Collections.Generic.List[object]]::new()
    $copies = [Collections.Generic.List[object]]::new()
    $casePaths = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $seenEscapes = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($distribution in $RuntimeDistributions.Keys) {
        $spec = $RuntimeDistributions[$distribution]
        $distInfo = Join-Path $RuntimeSourceRoot $spec.directory
        Assert-NonReparsePath -LiteralPath $distInfo
        $recordPath = Join-Path $distInfo "RECORD"
        if (-not (Test-Path -LiteralPath $recordPath -PathType Leaf)) { throw "runtime RECORD is missing: $distribution" }
        $recordLines = [IO.File]::ReadAllLines($recordPath, [Text.Encoding]::UTF8)
        $distributionCount = 0
        foreach ($line in $recordLines) {
            if ([string]::IsNullOrEmpty($line)) { throw "blank runtime RECORD row" }
            if ($line.Contains('"')) { throw "quoted runtime RECORD rows are outside the frozen baseline" }
            $fields = $line.Split([char[]]@(','), 3)
            if ($fields.Length -ne 3) { throw "malformed runtime RECORD row" }
            $relative = $fields[0].Replace('\', '/')
            if ($relative -match '(^|/)__pycache__(/|$)' -or $relative.EndsWith('.pyc', [StringComparison]::OrdinalIgnoreCase)) { continue }
            $isEscape = $relative.StartsWith("../", [StringComparison]::Ordinal)
            if ($isEscape) {
                if ($EscapingRecordRows -cnotcontains $relative) { throw "unregistered escaping RECORD row: $relative" }
                if (-not $seenEscapes.Add($relative)) { throw "duplicate escaping RECORD row: $relative" }
            }
            elseif (-not (Test-SafeRelativePath -RelativePath $relative)) { throw "unsafe runtime RECORD path: $relative" }

            $source = [IO.Path]::GetFullPath((Join-Path $RuntimeSourceRoot $relative.Replace('/', '\')))
            if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
                if (Test-Path -LiteralPath $source -PathType Container) { continue }
                throw "RECORD-listed runtime file is missing: $relative"
            }
            Assert-NonReparsePath -LiteralPath $source
            $item = Get-Item -LiteralPath $source -Force
            if ($item.PSIsContainer) { continue }
            $isRecord = $relative.Equals(($spec.directory + "/RECORD"), [StringComparison]::Ordinal)
            if (-not $isRecord -and [string]::IsNullOrEmpty($fields[1])) { throw "non-RECORD admitted file lacks a hash: $relative" }
            if (-not $isRecord -and $fields[1] -notmatch '^sha256=(?<value>[A-Za-z0-9_-]+)$') { throw "runtime RECORD hash algorithm is not sha256" }
            $digestBytes = Get-Sha256Digest -LiteralPath $source
            $digest = ([BitConverter]::ToString($digestBytes)).Replace("-", "")
            if (-not $isRecord -and (ConvertTo-UrlSafeBase64 -Bytes $digestBytes) -cne $Matches.value) {
                throw "runtime RECORD digest mismatch: $relative"
            }
            if (-not $isRecord) {
                if ($fields[2] -notmatch '^(0|[1-9][0-9]*)$' -or [int64]$fields[2] -ne [int64]$item.Length) {
                    throw "runtime RECORD size mismatch: $relative"
                }
            }
            if (-not $casePaths.Add($relative)) { throw "case-folded runtime path collision: $relative" }
            $row = [pscustomobject][ordered]@{
                distribution = [string]$distribution
                version = [string]$spec.version
                relative_posix_path = $relative
                byte_count = [int64]$item.Length
                sha256 = $digest
            }
            $rows.Add($row)
            if (-not $isEscape) {
                $copies.Add([pscustomobject][ordered]@{
                    source = $source
                    relative_posix_path = $relative
                    byte_count = [int64]$item.Length
                    sha256 = $digest
                })
            }
            $distributionCount++
        }
        if ($distributionCount -ne [int]$spec.rows) { throw "runtime admitted-row count drift for $distribution`: $distributionCount" }
    }
    foreach ($escape in $EscapingRecordRows) {
        if (-not $seenEscapes.Contains($escape)) { throw "required escaping runtime row is missing: $escape" }
    }
    if ($rows.Count -ne $RuntimeAggregateRowCount) { throw "runtime aggregate row count drift: $($rows.Count)" }
    if ($copies.Count -ne $RuntimeCopyFileCount) { throw "runtime copy target count drift: $($copies.Count)" }
    $rowArray = $rows.ToArray()
    [Array]::Sort($rowArray, [Collections.Generic.Comparer[object]]::Create([Comparison[object]]{
        param($left, $right)
        $c = [StringComparer]::Ordinal.Compare($left.distribution, $right.distribution)
        if ($c -eq 0) { $c = [StringComparer]::Ordinal.Compare($left.version, $right.version) }
        if ($c -eq 0) { $c = [StringComparer]::Ordinal.Compare($left.relative_posix_path, $right.relative_posix_path) }
        return $c
    }))
    $payload = Get-CanonicalPayload -Value $rowArray
    if ($payload.byte_length -ne $RuntimeAggregateByteLength -or $payload.sha256 -cne $RuntimeAggregateSha256) {
        throw "listed-runtime aggregate drift: rows=$($rows.Count) bytes=$($payload.byte_length) sha=$($payload.sha256)"
    }
    $pytestInit = Join-Path $RuntimeSourceRoot "pytest\__init__.py"
    Assert-Sha256File -LiteralPath $pytestInit -Expected $PytestInitSha256 -Label "pytest/__init__.py"
    return [pscustomobject][ordered]@{
        rows = $rowArray
        copies = $copies.ToArray()
        aggregate_byte_length = [int64]$payload.byte_length
        aggregate_sha256 = $payload.sha256
    }
}

function Copy-PrivateRuntime {
    param(
        [Parameter(Mandatory = $true)] $Inventory,
        [Parameter(Mandatory = $true)][string] $DestinationRoot
    )
    $caseDestinations = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($copy in $Inventory.copies) {
        $relative = [string]$copy.relative_posix_path
        if (-not (Test-SafeRelativePath -RelativePath $relative)) { throw "unsafe private runtime destination" }
        if (-not $caseDestinations.Add($relative)) { throw "private runtime destination collision" }
        $destination = [IO.Path]::GetFullPath((Join-Path $DestinationRoot $relative.Replace('/', '\')))
        $prefix = [IO.Path]::GetFullPath($DestinationRoot).TrimEnd('\') + '\'
        if (-not $destination.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw "private runtime destination escaped" }
        $parent = Split-Path -Parent $destination
        [void][IO.Directory]::CreateDirectory($parent)
        Assert-NonReparsePath -LiteralPath $parent
        $input = [IO.File]::Open($copy.source, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
        $output = [IO.File]::Open($destination, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try { $input.CopyTo($output, 65536); $output.Flush($true) }
        finally { $output.Dispose(); $input.Dispose() }
        if ((Get-Sha256File -LiteralPath $destination) -cne $copy.sha256) { throw "private runtime copy digest mismatch: $relative" }
    }
}

function Get-ExpectedArchiveTree {
    param(
        [Parameter(Mandatory = $true)][string] $RepositoryRoot,
        [Parameter(Mandatory = $true)][string] $ScratchRoot
    )
    $arguments = @("ls-tree", "-r", "-l", "-z", $SemanticCommit, "--", "lean_rgc", "tests/test_odlrq_selection.py", "tests/tier_manifest.json")
    $result = Invoke-BoundedGit -Arguments $arguments -RepositoryRoot $RepositoryRoot -ScratchRoot $ScratchRoot
    $rows = Parse-LsTree -Bytes $result.stdout -WithSize
    if ($rows.Count -eq 0) { throw "semantic archive tree is empty" }
    $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($row in $rows) {
        if ($row.mode -notin @("100644", "100755")) { throw "unsupported semantic archive mode: $($row.mode)" }
        if (-not $seen.Add($row.path)) { throw "semantic archive case-folded collision" }
    }
    return $rows
}

function Materialize-SemanticArchive {
    param(
        [Parameter(Mandatory = $true)][string] $RepositoryRoot,
        [Parameter(Mandatory = $true)][string] $ScratchRoot,
        [Parameter(Mandatory = $true)][string] $ZipPath,
        [Parameter(Mandatory = $true)][string] $DestinationRoot
    )
    $expectedRows = Get-ExpectedArchiveTree -RepositoryRoot $RepositoryRoot -ScratchRoot $ScratchRoot
    $expected = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    $expectedDirectories = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($row in $expectedRows) {
        $expected.Add($row.path, $row)
        $parts = $row.path.Split('/')
        for ($index = 1; $index -lt $parts.Length; $index++) {
            [void]$expectedDirectories.Add((($parts[0..($index - 1)]) -join '/') + '/')
        }
    }
    if (Test-Path -LiteralPath $ZipPath) { throw "owned semantic archive already exists" }
    $archive = Invoke-BoundedGit -Arguments @(
        "archive", "--format=zip", "--output=$ZipPath", $SemanticCommit, "--",
        "lean_rgc", "tests/test_odlrq_selection.py", "tests/tier_manifest.json"
    ) -RepositoryRoot $RepositoryRoot -ScratchRoot $ScratchRoot
    if ($archive.stdout.Length -ne 0) { throw "git archive emitted unexpected stdout" }
    if (-not (Test-Path -LiteralPath $ZipPath -PathType Leaf)) { throw "semantic archive was not created" }
    Assert-NonReparsePath -LiteralPath $ZipPath

    [void][Reflection.Assembly]::Load("System.IO.Compression, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089")
    $zipStream = [IO.File]::Open($ZipPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $zip = [IO.Compression.ZipArchive]::new($zipStream, [IO.Compression.ZipArchiveMode]::Read, $false)
    try {
        $entries = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
        $caseEntries = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        $seenDirectories = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach ($entry in $zip.Entries) {
            $name = $entry.FullName
            $isDirectory = $name.EndsWith('/', [StringComparison]::Ordinal)
            $probe = if ($isDirectory) { $name.Substring(0, $name.Length - 1) } else { $name }
            if (-not (Test-SafeRelativePath -RelativePath $probe)) { throw "unsafe semantic archive entry: $name" }
            if (-not $caseEntries.Add($name)) { throw "semantic archive case-folded duplicate: $name" }
            if ($isDirectory) {
                if (-not $expectedDirectories.Contains($name) -or $entry.Length -ne 0) { throw "unexpected semantic archive directory: $name" }
                if ([int64]$entry.ExternalAttributes -ne 16) { throw "semantic archive Windows directory attributes mismatch: $name ($($entry.ExternalAttributes))" }
                if (-not $seenDirectories.Add($name)) { throw "duplicate semantic archive directory: $name" }
                continue
            }
            if (-not $expected.ContainsKey($name)) { throw "unexpected semantic archive file: $name" }
            $row = $expected[$name]
            if ([int64]$entry.Length -ne [int64]$row.size) { throw "semantic archive entry size mismatch: $name" }
            if ([int64]$entry.ExternalAttributes -ne 0) { throw "semantic archive Windows file attributes mismatch: $name ($($entry.ExternalAttributes))" }
            $entries.Add($name, $entry)
        }
        if ($entries.Count -ne $expected.Count) { throw "semantic archive file set is incomplete" }
        if ($seenDirectories.Count -ne $expectedDirectories.Count) { throw "semantic archive directory set is incomplete" }
        foreach ($directory in $expectedDirectories) {
            if (-not $seenDirectories.Contains($directory)) { throw "semantic archive is missing directory: $directory" }
        }
        foreach ($path in $expected.Keys) {
            if (-not $entries.ContainsKey($path)) { throw "semantic archive is missing: $path" }
        }
        foreach ($path in $expected.Keys) {
            $destination = [IO.Path]::GetFullPath((Join-Path $DestinationRoot $path.Replace('/', '\')))
            $prefix = [IO.Path]::GetFullPath($DestinationRoot).TrimEnd('\') + '\'
            if (-not $destination.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw "semantic extraction escaped" }
            $parent = Split-Path -Parent $destination
            [void][IO.Directory]::CreateDirectory($parent)
            Assert-NonReparsePath -LiteralPath $parent
            $input = $entries[$path].Open()
            $output = [IO.File]::Open($destination, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
            try { $input.CopyTo($output, 65536); $output.Flush($true) }
            finally { $output.Dispose(); $input.Dispose() }
            if ((Get-Item -LiteralPath $destination -Force).Length -ne [int64]$expected[$path].size) { throw "materialized source length mismatch" }
            if ((Get-GitBlobOid -LiteralPath $destination) -cne $expected[$path].oid) { throw "materialized source Git blob mismatch: $path" }
        }
    }
    finally { $zip.Dispose(); $zipStream.Dispose() }
    return [pscustomobject][ordered]@{
        archive_sha256 = Get-Sha256File -LiteralPath $ZipPath
        rows = $expectedRows
    }
}

function Assert-ManifestDelta {
    param(
        [Parameter(Mandatory = $true)][byte[]] $ParentBytes,
        [Parameter(Mandatory = $true)][string] $SemanticManifestPath
    )
    $parentText = Convert-GitUtf8 -Bytes $ParentBytes
    $semanticText = [IO.File]::ReadAllText($SemanticManifestPath, [Text.UTF8Encoding]::new($false, $true))
    $keyPattern = '(?m)^  "(?<key>[^"\\]+)"\s*:'
    $parentKeyMatches = [Text.RegularExpressions.Regex]::Matches($parentText, $keyPattern)
    $semanticKeyMatches = [Text.RegularExpressions.Regex]::Matches($semanticText, $keyPattern)
    $parentKeySet = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($match in $parentKeyMatches) { if (-not $parentKeySet.Add($match.Groups["key"].Value)) { throw "parent manifest has a duplicate mapping" } }
    $semanticKeySet = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($match in $semanticKeyMatches) { if (-not $semanticKeySet.Add($match.Groups["key"].Value)) { throw "semantic manifest has a duplicate mapping" } }
    $parent = $parentText | ConvertFrom-Json
    $semantic = $semanticText | ConvertFrom-Json
    $parentNames = @($parent.PSObject.Properties.Name)
    $semanticNames = @($semantic.PSObject.Properties.Name)
    if ($parentKeyMatches.Count -ne $parentNames.Count -or $semanticKeyMatches.Count -ne $semanticNames.Count) { throw "manifest object shape is not the frozen flat mapping" }
    if (($semanticNames | Where-Object { $_ -eq "test_odlrq_selection.py" }).Count -ne 1) { throw "semantic manifest E2 row is missing or duplicated" }
    if ($semanticNames.Count -ne $parentNames.Count + 1) { throw "semantic manifest changed more than one mapping" }
    $semanticExistingOrder = @($semanticNames | Where-Object { $_ -cne "test_odlrq_selection.py" })
    if (-not (Test-ExactStringArray -Left $semanticExistingOrder -Right $parentNames)) { throw "semantic manifest reordered an existing mapping" }
    foreach ($name in $parentNames) {
        if ($semanticNames -cnotcontains $name) { throw "semantic manifest dropped mapping: $name" }
        $left = @($parent.PSObject.Properties[$name].Value)
        $right = @($semantic.PSObject.Properties[$name].Value)
        if ($left.Count -ne $right.Count) { throw "semantic manifest changed array length: $name" }
        for ($index = 0; $index -lt $left.Count; $index++) {
            if ([string]$left[$index] -cne [string]$right[$index]) { throw "semantic manifest changed mapping: $name" }
        }
    }
    $newValue = @($semantic.PSObject.Properties["test_odlrq_selection.py"].Value)
    if ($newValue.Count -ne 1 -or [string]$newValue[0] -cne "unit") { throw "semantic manifest E2 mapping is not exactly ['unit']" }
}

function Open-HeldFiles {
    param([Parameter(Mandatory = $true)][string[]] $Roots)
    $handles = [Collections.Generic.List[IO.FileStream]]::new()
    $identities = [Collections.Generic.List[object]]::new()
    try {
        foreach ($root in $Roots) {
            Assert-NonReparsePath -LiteralPath $root
            $rootPrefix = [IO.Path]::GetFullPath($root).TrimEnd('\') + '\'
            foreach ($file in Get-ChildItem -LiteralPath $root -File -Recurse | Sort-Object FullName) {
                $resolvedFile = [IO.Path]::GetFullPath($file.FullName)
                if (-not $resolvedFile.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw "held file escaped its private root" }
                Assert-NonReparsePath -LiteralPath $resolvedFile
                if (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "held file is a reparse point" }
                $stream = [IO.File]::Open($resolvedFile, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
                $handles.Add($stream)
                $sha = [Security.Cryptography.SHA256]::Create()
                try { $digest = ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace("-", "") }
                finally { $sha.Dispose() }
                $stream.Position = 0
                $sha1 = [Security.Cryptography.SHA1]::Create()
                try {
                    $prefix = [Text.Encoding]::ASCII.GetBytes("blob $($stream.Length)`0")
                    [void]$sha1.TransformBlock($prefix, 0, $prefix.Length, $null, 0)
                    $buffer = [byte[]]::new(65536)
                    while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) { [void]$sha1.TransformBlock($buffer, 0, $read, $null, 0) }
                    [void]$sha1.TransformFinalBlock([byte[]]::new(0), 0, 0)
                    $gitBlob = ([BitConverter]::ToString($sha1.Hash)).Replace("-", "").ToLowerInvariant()
                }
                finally { $sha1.Dispose() }
                $stream.Position = 0
                $identities.Add([pscustomobject][ordered]@{ path = $resolvedFile; byte_count = [int64]$stream.Length; sha256 = $digest; git_blob = $gitBlob })
            }
        }
        return [pscustomobject][ordered]@{ handles = $handles; identities = $identities.ToArray() }
    }
    catch {
        foreach ($handle in $handles) { $handle.Dispose() }
        throw
    }
}

function Get-E2BootstrapSource {
    return @'
import ast
import hashlib
import json
import ntpath
import sys
import time

AUTHORITY_COMMIT = "28c5a29000dddadcaf3e9ad9dd5534554dd67f32"
AUTHORITY_TREE = "1a71fc6ff774dd0bcf7e4ab551bd737a7a9dab14"
AUTHORITY_DOCUMENT_BLOB = "139a5992a38269974068858ef00f47f43ef5fca4"
SOURCE_COMMIT = "6998f2f9ec430881df50e6790ef9a8f13b1b7857"
SOURCE_TREE = "3512b6bc2e7e357544f87f2e7e05e8868b26d658"
CERTIFICATES_BLOB = "8d995768e93da62829035a1ff187a74e3ea8a378"
SELECTION_BLOB = "b856555271bdea8eb9f9f05e41b4aa52cab9c95d"
TEST_BLOB = "e22223008cab410dd99f953806ce18d38db854f6"
RECEIPT_SCHEMA = "u24-e2-child-receipt-v1"
LANE = "U24_E2_ENDPOINT"
EXPECTED_NAMES = [
    "test_e2_square_parent_coordinate_identification_rederives_complete_typed_basis",
    "test_e2_restriction_replays_full_parent_terminal_zeros_and_restricted_weights",
    "test_e2_lifting_uniform_safety_is_law_independent_and_cancellation_free",
    "test_e2_p1_p2_cocycles_match_products_weighted_norms_and_limited_derivations",
    "test_e2_return_memory_split_stationary_semantics_and_finite_sum_are_exact",
    "test_e2_orientation_basis_weight_split_and_transport_mutations_fail_closed",
    "test_e2_caps_horizon_work_and_preallocation_bombs_fail_before_authority",
    "test_e2_fixed_candidate_universe_prevents_prefilter_omission_and_accepts_boundary",
    "test_e2_gate_is_coverage_complete_nonempty_reachable_and_top_ranking_binding",
    "test_e2_strict_roundtrip_invalidation_tier_firewall_and_nominal_fallback",
]
EXPECTED_NODES = [f"tests/test_odlrq_selection.py::{name}" for name in EXPECTED_NAMES]
FORBIDDEN_IMPORT_ROOTS = {
    "aiohttp", "asyncio", "builtins", "cffi", "ctypes", "ftplib", "glob",
    "http", "importlib", "io", "multiprocessing", "numpy", "os", "pathlib",
    "requests", "shutil", "socket", "ssl", "subprocess", "sys", "tempfile",
    "urllib",
}

FORBIDDEN_CALL_NAMES = {"open", "eval", "exec", "compile", "__import__"}


class E2ExternalActionDenied(RuntimeError):
    pass


def _deny_external(*_args, **_kwargs):
    raise E2ExternalActionDenied("U24_E2_EXTERNAL_ACTION_DENIED")


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _parse_internal(arguments):
    names = [
        "--arm", "--receipt", "--source-root", "--runtime-root",
        "--manifest-sha", "--marker-sha", "--runner-commit", "--runner-tree",
    ]
    if len(arguments) != len(names) * 2:
        raise RuntimeError("wrong internal bootstrap arity")
    values = {}
    for index, name in enumerate(names):
        if arguments[index * 2] != name:
            raise RuntimeError("wrong internal bootstrap argument order")
        value = arguments[index * 2 + 1]
        if not value or "\x00" in value or "\r" in value or "\n" in value:
            raise RuntimeError("malformed internal bootstrap value")
        values[name] = value
    return values


def _wait_for_arm(path):
    deadline = time.monotonic() + 30.0
    while True:
        try:
            with open(path, "rb") as handle:
                value = handle.read(5)
            if value != b"ARM\n":
                raise RuntimeError("arm bytes are not exact")
            return
        except (FileNotFoundError, PermissionError):
            if time.monotonic() >= deadline:
                raise RuntimeError("arm wait expired")
            time.sleep(0.01)


def _install_denials():
    import asyncio
    import multiprocessing
    import multiprocessing.process
    import socket
    import subprocess

    for name in (
        "Popen", "run", "call", "check_call", "check_output", "getoutput",
        "getstatusoutput",
    ):
        if hasattr(subprocess, name):
            setattr(subprocess, name, _deny_external)
    for name in (
        "system", "popen", "startfile", "execl", "execle", "execlp", "execlpe",
        "execv", "execve", "execvp", "execvpe", "spawnl", "spawnle", "spawnlp",
        "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe",
    ):
        if hasattr(os, name):
            setattr(os, name, _deny_external)
    for name in (
        "create_subprocess_exec", "create_subprocess_shell", "open_connection",
        "open_unix_connection", "start_server", "start_unix_server",
    ):
        if hasattr(asyncio, name):
            setattr(asyncio, name, _deny_external)
    multiprocessing.Process.start = _deny_external
    multiprocessing.process.BaseProcess.start = _deny_external
    socket.socket = _deny_external
    socket.create_connection = _deny_external
    if hasattr(socket, "socketpair"):
        socket.socketpair = _deny_external
    if hasattr(socket, "create_server"):
        socket.create_server = _deny_external

    blocked_events = {
        "subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn",
        "socket.connect", "socket.connect_ex", "socket.bind", "socket.listen",
    }

    def audit(event, _args):
        if event in blocked_events:
            raise E2ExternalActionDenied("U24_E2_AUDIT_DENIED:" + event)

    sys.addaudithook(audit)
    spawn_pass = False
    network_pass = False
    try:
        subprocess.Popen(["u24-e2-denial-probe"])
    except E2ExternalActionDenied as error:
        spawn_pass = str(error) == "U24_E2_EXTERNAL_ACTION_DENIED"
    try:
        socket.create_connection(("127.0.0.1", 9))
    except E2ExternalActionDenied as error:
        network_pass = str(error) == "U24_E2_EXTERNAL_ACTION_DENIED"
    if not spawn_pass or not network_pass:
        raise RuntimeError("bootstrap denial probe failed")
    return spawn_pass, network_pass


def _audit_e2_ast(source_root):
    paths = [
        "lean_rgc/odlrq/certificates.py",
        "lean_rgc/odlrq/selection.py",
        "tests/test_odlrq_selection.py",
    ]
    for relative in paths:
        absolute = os.path.join(source_root, *relative.split("/"))
        with open(absolute, "r", encoding="utf-8", newline="") as handle:
            text = handle.read()
        tree = ast.parse(text, filename=relative, mode="exec")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".", 1)[0] in FORBIDDEN_IMPORT_ROOTS:
                        raise RuntimeError("forbidden direct E2 import: " + alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".", 1)[0] in FORBIDDEN_IMPORT_ROOTS:
                    raise RuntimeError("forbidden direct E2 from-import: " + node.module)
            elif isinstance(node, ast.Call):
                called = None
                if isinstance(node.func, ast.Name):
                    called = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    called = node.func.attr
                if called in FORBIDDEN_CALL_NAMES:
                    raise RuntimeError("forbidden direct E2 call: " + called)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value
                lowered = value.lower()
                if ntpath.isabs(value) or any(token in lowered for token in (
                    "\\downloads\\", "/downloads/", "\\.codex\\", "\\.claude\\",
                    "pilot_tasks.json", "llm_local.json", "minif2f",
                )):
                    raise RuntimeError("protected or absolute path literal in E2 source")


class EndpointPlugin:
    def __init__(self):
        self.collected = []
        self.reports = []
        self.deselected = []

    def pytest_collection_finish(self, session):
        self.collected = [item.nodeid for item in session.items]

    def pytest_deselected(self, items):
        self.deselected.extend(item.nodeid for item in items)

    def pytest_runtest_logreport(self, report):
        self.reports.append({
            "node_id": report.nodeid,
            "when": report.when,
            "outcome": report.outcome,
            "was_xfail": bool(getattr(report, "wasxfail", False)),
        })


def _summaries(plugin):
    passed = []
    failed = []
    skipped = []
    xfailed = []
    integrity = len(plugin.collected) == len(set(plugin.collected))
    collection_position = {node_id: index for index, node_id in enumerate(plugin.collected)}
    previous_node_position = -1
    previous_stage_position = -1
    stage_positions = {"setup": 0, "call": 1, "teardown": 2}
    seen_reports = set()
    for row in plugin.reports:
        node_id = row["node_id"]
        stage = row["when"]
        if node_id not in collection_position or stage not in stage_positions:
            integrity = False
            continue
        node_position = collection_position[node_id]
        stage_position = stage_positions[stage]
        key = (node_id, stage)
        if key in seen_reports:
            integrity = False
        seen_reports.add(key)
        if node_position < previous_node_position:
            integrity = False
        if node_position == previous_node_position and stage_position <= previous_stage_position:
            integrity = False
        if node_position != previous_node_position:
            previous_stage_position = -1
        previous_node_position = node_position
        previous_stage_position = stage_position
    for node_id in plugin.collected:
        rows = [row for row in plugin.reports if row["node_id"] == node_id]
        if len(rows) != 3 or [row["when"] for row in rows] != ["setup", "call", "teardown"]:
            integrity = False
        if any(row["was_xfail"] for row in rows):
            xfailed.append(node_id)
        if any(row["outcome"] == "failed" for row in rows):
            failed.append(node_id)
        if any(row["outcome"] == "skipped" for row in rows):
            skipped.append(node_id)
        by_stage = {row["when"]: row for row in rows}
        if (
            set(by_stage) == {"setup", "call", "teardown"}
            and all(by_stage[stage]["outcome"] == "passed" for stage in ("setup", "call", "teardown"))
            and not any(by_stage[stage]["was_xfail"] for stage in by_stage)
        ):
            passed.append(node_id)
    return passed, failed, skipped, xfailed, integrity


def _test_disposition(
    tests_passed, pytest_exit, collected, passed, failed, skipped, xfailed, deselected,
    report_integrity, receipt_path_hidden, spawn_denial_probe_pass,
    network_denial_probe_pass,
):
    if tests_passed:
        return "U24_E2_ENDPOINT_SOURCE_FROZEN"
    single_failure_is_clean = (
        pytest_exit == 1
        and collected == EXPECTED_NODES
        and len(failed) == 1
        and failed[0] in EXPECTED_NODES
        and passed == [node for node in EXPECTED_NODES if node != failed[0]]
        and skipped == []
        and xfailed == []
        and deselected == []
        and report_integrity
        and receipt_path_hidden
        and spawn_denial_probe_pass
        and network_denial_probe_pass
    )
    if not single_failure_is_clean:
        return "U24_E2_RUNNER_BLOCKED"
    index = EXPECTED_NODES.index(failed[0]) + 1
    if index in {1, 6, 8, 10}:
        return "U24_E2_TYPE_OR_WIRE_BLOCKED"
    if index in {2, 3, 4, 5}:
        return "U24_E2_ENVELOPE_BLOCKED"
    if index == 7:
        return "U24_E2_RESOURCE_OR_SCOPE_BLOCKED"
    if index == 9:
        return "U24_E2_GATE_NONBINDING"
    return "U24_E2_RUNNER_BLOCKED"


def _exclusive_receipt(path, payload):
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    if len(encoded) > 1048576:
        raise RuntimeError("child receipt exceeds cap")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)


def main():
    expected_prearm_path = [
        r"C:\Python313\python313.zip",
        r"C:\Python313\DLLs",
        r"C:\Python313\Lib",
    ]
    if list(sys.path) != expected_prearm_path:
        raise RuntimeError("isolated pre-arm sys.path drift")
    if not (
        sys.flags.isolated == 1
        and sys.flags.no_site == 1
        and sys.flags.no_user_site == 1
        and sys.flags.dont_write_bytecode == 1
        and sys.flags.utf8_mode == 1
        and getattr(sys.flags, "safe_path", 0) == 1
    ):
        raise RuntimeError("isolated Python flags drift")
    if any(name in sys.modules for name in ("site", "sitecustomize", "usercustomize", "pytest", "numpy")):
        raise RuntimeError("third-party or site import occurred before arm")
    values = _parse_internal(sys.argv[1:])
    arm_path = values["--arm"]
    receipt_path = values["--receipt"]
    source_root = values["--source-root"]
    runtime_root = values["--runtime-root"]
    manifest_sha = values["--manifest-sha"]
    marker_sha = values["--marker-sha"]
    runner_commit = values["--runner-commit"]
    runner_tree = values["--runner-tree"]
    sys.argv[:] = ["u24-e2-bootstrap"]
    sys.orig_argv[:] = ["python.exe", "-I", "-S", "-B", "-X", "utf8", "u24-e2-bootstrap"]
    _wait_for_arm(arm_path)
    global os
    import os
    spawn_pass, network_pass = _install_denials()
    sys.path[:] = [source_root, runtime_root] + expected_prearm_path
    _audit_e2_ast(source_root)
    receipt_path_hidden = (
        all(receipt_path not in value for value in sys.argv)
        and all(receipt_path not in value for value in sys.orig_argv)
        and all(receipt_path not in value for value in os.environ.values())
    )
    if not receipt_path_hidden:
        raise RuntimeError("receipt path was not hidden")

    import pytest
    import numpy
    if pytest.__version__ != "9.0.3" or numpy.__version__ != "2.3.3":
        raise RuntimeError("private runtime version drift")
    if not ntpath.abspath(pytest.__file__).lower().startswith(ntpath.abspath(runtime_root).lower() + "\\"):
        raise RuntimeError("pytest escaped private runtime")
    if not ntpath.abspath(numpy.__file__).lower().startswith(ntpath.abspath(runtime_root).lower() + "\\"):
        raise RuntimeError("numpy escaped private runtime")
    if _sha256(pytest.__file__) != "7BE7A1E2218DC59A19D1AD131E4ABE21172A295087EFC72898938248782E8766":
        raise RuntimeError("private pytest init drift")

    certificates_path = os.path.join(source_root, "lean_rgc", "odlrq", "certificates.py")
    selection_path = os.path.join(source_root, "lean_rgc", "odlrq", "selection.py")
    test_path = os.path.join(source_root, "tests", "test_odlrq_selection.py")
    plugin = EndpointPlugin()
    # Frozen pytest 9.0.3 treats an explicit unsupported .json config suffix as
    # an empty config; the held/verified tier manifest therefore suppresses
    # ancestor config discovery without adding an unbound runner-created file.
    code = int(pytest.main([
        "-p", "no:cacheprovider", "-c", "tests/tier_manifest.json",
        "--rootdir=.", "--confcutdir=.", "--noconftest",
        "--basetemp", ".pytest-tmp", "-q",
        "tests/test_odlrq_selection.py",
    ], plugins=[plugin]))
    passed, failed, skipped, xfailed, report_integrity = _summaries(plugin)
    tests_passed = (
        code == 0
        and plugin.collected == EXPECTED_NODES
        and passed == EXPECTED_NODES
        and failed == []
        and skipped == []
        and xfailed == []
        and plugin.deselected == []
        and report_integrity
    )
    payload = {
        "schema_version": RECEIPT_SCHEMA,
        "lane": LANE,
        "authority_commit": AUTHORITY_COMMIT,
        "authority_tree": AUTHORITY_TREE,
        "authority_document_blob": AUTHORITY_DOCUMENT_BLOB,
        "source_commit": SOURCE_COMMIT,
        "source_tree": SOURCE_TREE,
        "runner_commit": runner_commit,
        "runner_tree": runner_tree,
        "pre_run_manifest_sha256": manifest_sha,
        "attempt_marker_sha256": marker_sha,
        "expected_node_ids": EXPECTED_NODES,
        "collected_node_ids": plugin.collected,
        "node_reports": plugin.reports,
        "passed_node_ids": passed,
        "failed_node_ids": failed,
        "skipped_node_ids": skipped,
        "xfailed_node_ids": xfailed,
        "deselected_count": len(plugin.deselected),
        "tests_passed": tests_passed,
        "receipt_path_hidden": receipt_path_hidden,
        "spawn_denial_probe_pass": spawn_pass,
        "network_denial_probe_pass": network_pass,
        "pytest_exit_code": code,
        "test_module_materialized_sha256": _sha256(test_path),
        "test_module_git_blob": TEST_BLOB,
        "certificates_materialized_sha256": _sha256(certificates_path),
        "certificates_git_blob": CERTIFICATES_BLOB,
        "selection_materialized_sha256": _sha256(selection_path),
        "selection_git_blob": SELECTION_BLOB,
        "disposition": _test_disposition(
            tests_passed, code, plugin.collected, passed, failed, skipped, xfailed,
            plugin.deselected, report_integrity, receipt_path_hidden, spawn_pass,
            network_pass,
        ),
    }
    _exclusive_receipt(receipt_path, payload)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
'@
}
function Test-ExactPropertyOrder {
    param(
        [Parameter(Mandatory = $true)] $Object,
        [Parameter(Mandatory = $true)][string[]] $Expected
    )
    $actual = @($Object.PSObject.Properties.Name)
    if ($actual.Count -ne $Expected.Count) { return $false }
    for ($index = 0; $index -lt $Expected.Count; $index++) {
        if ($actual[$index] -cne $Expected[$index]) { return $false }
    }
    return $true
}

function Test-ExactStringArray {
    param(
        [Parameter(Mandatory = $true)] $Left,
        [Parameter(Mandatory = $true)] $Right
    )
    $leftArray = @($Left)
    $rightArray = @($Right)
    if ($leftArray.Count -ne $rightArray.Count) { return $false }
    for ($index = 0; $index -lt $leftArray.Count; $index++) {
        if (
            $leftArray[$index] -isnot [string] -or
            $rightArray[$index] -isnot [string] -or
            $leftArray[$index] -cne $rightArray[$index]
        ) { return $false }
    }
    return $true
}

function Test-ExactJsonInteger {
    param([AllowNull()] $Value)
    return $null -ne $Value -and ($Value.GetType() -eq [int] -or $Value.GetType() -eq [long])
}

function Read-E2ChildReceipt {
    param(
        [Parameter(Mandatory = $true)][string] $ReceiptPath,
        [Parameter(Mandatory = $true)][string] $RunnerCommit,
        [Parameter(Mandatory = $true)][string] $RunnerTree,
        [Parameter(Mandatory = $true)][string] $ManifestSha,
        [Parameter(Mandatory = $true)][string] $MarkerSha,
        [Parameter(Mandatory = $true)] $MaterializedPairs
    )
    $result = [ordered]@{
        status = "ABSENT"
        payload = $null
        parse_error = "FILE_ABSENT"
        byte_length = $null
        sha256 = $null
        pytest_exit = $null
    }
    $receiptFullPath = [IO.Path]::GetFullPath($ReceiptPath)
    $receiptParent = [IO.Path]::GetFullPath((Split-Path -Parent $receiptFullPath))
    $receiptLeaf = [IO.Path]::GetFileName($receiptFullPath)
    if ([string]::IsNullOrEmpty($receiptLeaf)) { throw "child receipt path has no leaf" }
    Assert-NonReparsePath -LiteralPath $receiptParent
    $matchingReceiptEntries = [Collections.Generic.List[string]]::new()
    foreach ($entry in [IO.Directory]::EnumerateFileSystemEntries($receiptParent)) {
        if ([IO.Path]::GetFileName($entry).Equals($receiptLeaf, [StringComparison]::OrdinalIgnoreCase)) {
            $matchingReceiptEntries.Add([IO.Path]::GetFullPath($entry))
        }
    }
    if ($matchingReceiptEntries.Count -eq 0) { return [pscustomobject]$result }
    if ($matchingReceiptEntries.Count -ne 1) { throw "child receipt path is case-colliding" }
    $observedReceiptPath = $matchingReceiptEntries[0]
    if (-not [IO.Path]::GetFileName($observedReceiptPath).Equals($receiptLeaf, [StringComparison]::Ordinal)) {
        throw "child receipt leaf casing drift"
    }
    $receiptAttributes = [IO.File]::GetAttributes($observedReceiptPath)
    if (
        ($receiptAttributes -band [IO.FileAttributes]::Directory) -ne 0 -or
        ($receiptAttributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
    ) { throw "child receipt path is not a regular non-reparse file" }
    Assert-NonReparsePath -LiteralPath $observedReceiptPath
    $receiptStream = [IO.File]::Open($observedReceiptPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        $result.byte_length = [int64]$receiptStream.Length
        if ($receiptStream.Length -gt $ReceiptLimitBytes) {
            $result.status = "INVALID"; $result.parse_error = "SIZE_CAP_EXCEEDED"; return [pscustomobject]$result
        }
        $bytes = [byte[]]::new([int]$receiptStream.Length)
        $offset = 0
        while ($offset -lt $bytes.Length) {
            $count = $receiptStream.Read($bytes, $offset, $bytes.Length - $offset)
            if ($count -le 0) { throw "bounded child receipt ended early" }
            $offset += $count
        }
        if ($receiptStream.ReadByte() -ne -1) { throw "bounded child receipt grew during held read" }
    }
    finally { $receiptStream.Dispose() }
    $result.sha256 = Get-Sha256Bytes -Bytes $bytes
    foreach ($byte in $bytes) {
        if ($byte -gt 127) { $result.status = "INVALID"; $result.parse_error = "NON_ASCII"; return [pscustomobject]$result }
    }
    $text = [Text.Encoding]::ASCII.GetString($bytes)
    try { $payload = $text | ConvertFrom-Json }
    catch {
        $result.status = "INVALID"
        $result.parse_error = if ($text.Length -eq 0 -or -not $text.EndsWith("}", [StringComparison]::Ordinal)) { "TRUNCATED" } else { "NONCANONICAL" }
        return [pscustomobject]$result
    }
    if ($null -eq $payload -or $payload -isnot [Management.Automation.PSCustomObject]) {
        $result.status = "INVALID"; $result.parse_error = "WRONG_KEYS"; return [pscustomobject]$result
    }
    try {
    $keys = @(
        "schema_version", "lane", "authority_commit", "authority_tree",
        "authority_document_blob", "source_commit", "source_tree",
        "runner_commit", "runner_tree", "pre_run_manifest_sha256",
        "attempt_marker_sha256", "expected_node_ids", "collected_node_ids",
        "node_reports", "passed_node_ids", "failed_node_ids", "skipped_node_ids",
        "xfailed_node_ids", "deselected_count", "tests_passed",
        "receipt_path_hidden", "spawn_denial_probe_pass", "network_denial_probe_pass",
        "pytest_exit_code", "test_module_materialized_sha256", "test_module_git_blob",
        "certificates_materialized_sha256", "certificates_git_blob",
        "selection_materialized_sha256", "selection_git_blob", "disposition"
    )
    if (-not (Test-ExactPropertyOrder -Object $payload -Expected $keys)) {
        $result.status = "INVALID"; $result.parse_error = "WRONG_KEYS"; return [pscustomobject]$result
    }
    if ([string]$payload.schema_version -cne $ChildReceiptSchema) {
        $result.status = "INVALID"; $result.parse_error = "WRONG_SCHEMA"; return [pscustomobject]$result
    }
    try { $canonical = Get-CanonicalPayload -Value $payload }
    catch { $result.status = "INVALID"; $result.parse_error = "NONCANONICAL"; return [pscustomobject]$result }
    if ($canonical.byte_length -ne $bytes.Length -or [Convert]::ToBase64String($canonical.bytes) -cne [Convert]::ToBase64String($bytes)) {
        $result.status = "INVALID"; $result.parse_error = "NONCANONICAL"; return [pscustomobject]$result
    }
    $scalarStringKeys = @(
        "schema_version", "lane", "authority_commit", "authority_tree", "authority_document_blob",
        "source_commit", "source_tree", "runner_commit", "runner_tree", "pre_run_manifest_sha256",
        "attempt_marker_sha256", "test_module_materialized_sha256", "test_module_git_blob",
        "certificates_materialized_sha256", "certificates_git_blob", "selection_materialized_sha256",
        "selection_git_blob", "disposition"
    )
    foreach ($key in $scalarStringKeys) {
        if ($payload.PSObject.Properties[$key].Value -isnot [string]) {
            $result.status = "INVALID"; $result.parse_error = "IDENTITY_MISMATCH"; return [pscustomobject]$result
        }
    }
    foreach ($arrayKey in @(
        "expected_node_ids", "collected_node_ids", "node_reports", "passed_node_ids",
        "failed_node_ids", "skipped_node_ids", "xfailed_node_ids"
    )) {
        if ($payload.PSObject.Properties[$arrayKey].Value -isnot [Array]) {
            $result.status = "INVALID"; $result.parse_error = "IDENTITY_MISMATCH"; return [pscustomobject]$result
        }
    }
    $identityMatches = (
        [string]$payload.lane -ceq $Lane -and
        [string]$payload.authority_commit -ceq $AuthorityCommit -and
        [string]$payload.authority_tree -ceq $AuthorityTree -and
        [string]$payload.authority_document_blob -ceq $AuthorityDocumentBlob -and
        [string]$payload.source_commit -ceq $SemanticCommit -and
        [string]$payload.source_tree -ceq $SemanticTree -and
        [string]$payload.runner_commit -ceq $RunnerCommit -and
        [string]$payload.runner_tree -ceq $RunnerTree -and
        [string]$payload.pre_run_manifest_sha256 -ceq $ManifestSha -and
        [string]$payload.attempt_marker_sha256 -ceq $MarkerSha -and
        [string]$payload.test_module_materialized_sha256 -ceq $MaterializedPairs["tests/test_odlrq_selection.py"].raw_sha256 -and
        [string]$payload.test_module_git_blob -ceq $SemanticBlobs["tests/test_odlrq_selection.py"] -and
        [string]$payload.certificates_materialized_sha256 -ceq $MaterializedPairs["lean_rgc/odlrq/certificates.py"].raw_sha256 -and
        [string]$payload.certificates_git_blob -ceq $SemanticBlobs["lean_rgc/odlrq/certificates.py"] -and
        [string]$payload.selection_materialized_sha256 -ceq $MaterializedPairs["lean_rgc/odlrq/selection.py"].raw_sha256 -and
        [string]$payload.selection_git_blob -ceq $SemanticBlobs["lean_rgc/odlrq/selection.py"]
    )
    if (-not $identityMatches) {
        $result.status = "INVALID"; $result.parse_error = "IDENTITY_MISMATCH"; return [pscustomobject]$result
    }
    $expectedNodes = @($payload.expected_node_ids)
    if ($expectedNodes.Count -ne $ExpectedNodeIds.Count) {
        $result.status = "INVALID"; $result.parse_error = "IDENTITY_MISMATCH"; return [pscustomobject]$result
    }
    for ($index = 0; $index -lt $ExpectedNodeIds.Count; $index++) {
        if ($expectedNodes[$index] -isnot [string] -or $expectedNodes[$index] -cne $ExpectedNodeIds[$index]) {
            $result.status = "INVALID"; $result.parse_error = "IDENTITY_MISMATCH"; return [pscustomobject]$result
        }
    }
    $collectedNodes = @($payload.collected_node_ids)
    $collectionPositions = [Collections.Generic.Dictionary[string,int]]::new([StringComparer]::Ordinal)
    for ($index = 0; $index -lt $collectedNodes.Count; $index++) {
        if ($collectedNodes[$index] -isnot [string]) {
            $result.status = "INVALID"; $result.parse_error = "IDENTITY_MISMATCH"; return [pscustomobject]$result
        }
        $node = $collectedNodes[$index]
        if ($collectionPositions.ContainsKey($node)) {
            $result.status = "INVALID"; $result.parse_error = "IDENTITY_MISMATCH"; return [pscustomobject]$result
        }
        $collectionPositions.Add($node, $index)
    }
    $reportKeys = @("node_id", "when", "outcome", "was_xfail")
    $stagePositions = [Collections.Generic.Dictionary[string,int]]::new([StringComparer]::Ordinal)
    $stagePositions.Add("setup", 0); $stagePositions.Add("call", 1); $stagePositions.Add("teardown", 2)
    $seenReports = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $previousNodePosition = -1
    $previousStagePosition = -1
    foreach ($row in @($payload.node_reports)) {
        if ($row -isnot [Management.Automation.PSCustomObject] -or -not (Test-ExactPropertyOrder -Object $row -Expected $reportKeys)) {
            $result.status = "INVALID"; $result.parse_error = "WRONG_KEYS"; return [pscustomobject]$result
        }
        if (
            $row.node_id -isnot [string] -or $row.when -isnot [string] -or $row.outcome -isnot [string] -or
            -not $collectionPositions.ContainsKey($row.node_id) -or
            $row.when -cnotin @("setup", "call", "teardown") -or
            $row.outcome -cnotin @("passed", "failed", "skipped") -or
            $row.was_xfail -isnot [bool]
        ) {
            $result.status = "INVALID"; $result.parse_error = "IDENTITY_MISMATCH"; return [pscustomobject]$result
        }
        $nodePosition = $collectionPositions[[string]$row.node_id]
        $stagePosition = $stagePositions[[string]$row.when]
        $reportKey = [string]$row.node_id + "`0" + [string]$row.when
        if (
            -not $seenReports.Add($reportKey) -or
            $nodePosition -lt $previousNodePosition -or
            ($nodePosition -eq $previousNodePosition -and $stagePosition -le $previousStagePosition)
        ) {
            $result.status = "INVALID"; $result.parse_error = "IDENTITY_MISMATCH"; return [pscustomobject]$result
        }
        if ($nodePosition -ne $previousNodePosition) { $previousStagePosition = -1 }
        $previousNodePosition = $nodePosition
        $previousStagePosition = $stagePosition
    }
    if (
        $payload.tests_passed -isnot [bool] -or
        $payload.receipt_path_hidden -isnot [bool] -or
        $payload.spawn_denial_probe_pass -isnot [bool] -or
        $payload.network_denial_probe_pass -isnot [bool] -or
        -not (Test-ExactJsonInteger -Value $payload.deselected_count) -or
        -not (Test-ExactJsonInteger -Value $payload.pytest_exit_code) -or
        [int64]$payload.deselected_count -lt 0 -or
        [int64]$payload.pytest_exit_code -lt 0 -or [int64]$payload.pytest_exit_code -gt 255
    ) {
        $result.status = "INVALID"; $result.parse_error = "IDENTITY_MISMATCH"; return [pscustomobject]$result
    }
    $derivedPassed = [Collections.Generic.List[string]]::new()
    $derivedFailed = [Collections.Generic.List[string]]::new()
    $derivedSkipped = [Collections.Generic.List[string]]::new()
    $derivedXfailed = [Collections.Generic.List[string]]::new()
    $reportIntegrity = $true
    foreach ($node in $collectedNodes) {
        $rows = @($payload.node_reports | Where-Object { [string]$_.node_id -ceq [string]$node })
        if (
            $rows.Count -ne 3 -or [string]$rows[0].when -cne "setup" -or
            [string]$rows[1].when -cne "call" -or [string]$rows[2].when -cne "teardown"
        ) { $reportIntegrity = $false }
        if (@($rows | Where-Object { [string]$_.outcome -ceq "failed" }).Count -gt 0) { $derivedFailed.Add([string]$node) }
        if (@($rows | Where-Object { [string]$_.outcome -ceq "skipped" }).Count -gt 0) { $derivedSkipped.Add([string]$node) }
        if (@($rows | Where-Object { [bool]$_.was_xfail }).Count -gt 0) { $derivedXfailed.Add([string]$node) }
        if (
            $rows.Count -eq 3 -and
            [string]$rows[0].when -ceq "setup" -and [string]$rows[1].when -ceq "call" -and [string]$rows[2].when -ceq "teardown" -and
            @($rows | Where-Object { [string]$_.outcome -cne "passed" -or [bool]$_.was_xfail }).Count -eq 0
        ) { $derivedPassed.Add([string]$node) }
    }
    if (
        -not (Test-ExactStringArray -Left @($payload.passed_node_ids) -Right $derivedPassed.ToArray()) -or
        -not (Test-ExactStringArray -Left @($payload.failed_node_ids) -Right $derivedFailed.ToArray()) -or
        -not (Test-ExactStringArray -Left @($payload.skipped_node_ids) -Right $derivedSkipped.ToArray()) -or
        -not (Test-ExactStringArray -Left @($payload.xfailed_node_ids) -Right $derivedXfailed.ToArray())
    ) {
        $result.status = "INVALID"; $result.parse_error = "IDENTITY_MISMATCH"; return [pscustomobject]$result
    }
    $computedPass = (
        [int]$payload.pytest_exit_code -eq 0 -and
        (Test-ExactStringArray -Left $collectedNodes -Right $ExpectedNodeIds) -and
        (Test-ExactStringArray -Left $derivedPassed.ToArray() -Right $ExpectedNodeIds) -and
        $derivedFailed.Count -eq 0 -and $derivedSkipped.Count -eq 0 -and $derivedXfailed.Count -eq 0 -and
        [int64]$payload.deselected_count -eq 0 -and [bool]$payload.receipt_path_hidden -and
        [bool]$payload.spawn_denial_probe_pass -and [bool]$payload.network_denial_probe_pass
    )
    if ([bool]$payload.tests_passed -ne [bool]$computedPass) {
        $result.status = "INVALID"; $result.parse_error = "IDENTITY_MISMATCH"; return [pscustomobject]$result
    }
    $expectedChildDisposition = "U24_E2_RUNNER_BLOCKED"
    $singleFailureIsClean = $false
    if ($computedPass) { $expectedChildDisposition = "U24_E2_ENDPOINT_SOURCE_FROZEN" }
    elseif ($derivedFailed.Count -eq 1 -and [string]$derivedFailed[0] -in $ExpectedNodeIds) {
        $expectedOtherPassed = @($ExpectedNodeIds | Where-Object { $_ -cne [string]$derivedFailed[0] })
        $singleFailureIsClean = (
            (Test-ExactStringArray -Left $collectedNodes -Right $ExpectedNodeIds) -and
            (Test-ExactStringArray -Left $derivedPassed.ToArray() -Right $expectedOtherPassed) -and
            $derivedSkipped.Count -eq 0 -and $derivedXfailed.Count -eq 0 -and
            [int64]$payload.deselected_count -eq 0 -and [int]$payload.pytest_exit_code -eq 1 -and
            $reportIntegrity -and [bool]$payload.receipt_path_hidden -and
            [bool]$payload.spawn_denial_probe_pass -and [bool]$payload.network_denial_probe_pass
        )
    }
    if (-not $computedPass -and $singleFailureIsClean) {
        $failedIndex = [Array]::IndexOf([string[]]$ExpectedNodeIds, [string]$derivedFailed[0]) + 1
        if ($failedIndex -in @(1, 6, 8, 10)) { $expectedChildDisposition = "U24_E2_TYPE_OR_WIRE_BLOCKED" }
        elseif ($failedIndex -in @(2, 3, 4, 5)) { $expectedChildDisposition = "U24_E2_ENVELOPE_BLOCKED" }
        elseif ($failedIndex -eq 7) { $expectedChildDisposition = "U24_E2_RESOURCE_OR_SCOPE_BLOCKED" }
        elseif ($failedIndex -eq 9) { $expectedChildDisposition = "U24_E2_GATE_NONBINDING" }
    }
    if ([string]$payload.disposition -cne $expectedChildDisposition) {
        $result.status = "INVALID"; $result.parse_error = "IDENTITY_MISMATCH"; return [pscustomobject]$result
    }
    $result.status = "VALID"
    $result.payload = $payload
    $result.parse_error = $null
    $result.pytest_exit = [int]$payload.pytest_exit_code
    return [pscustomobject]$result
    }
    catch {
        $result.status = "INVALID"
        $result.payload = $null
        $result.parse_error = "IDENTITY_MISMATCH"
        $result.pytest_exit = $null
        return [pscustomobject]$result
    }
}

function Get-E2TestDisposition {
    param([Parameter(Mandatory = $true)] $Receipt)
    if ($Receipt.status -cne "VALID") { return "U24_E2_RUNNER_BLOCKED" }
    $payload = $Receipt.payload
    $collected = @($payload.collected_node_ids)
    $passed = @($payload.passed_node_ids)
    $failed = @($payload.failed_node_ids)
    $skipped = @($payload.skipped_node_ids)
    $xfailed = @($payload.xfailed_node_ids)
    $exactCollection = $collected.Count -eq $ExpectedNodeIds.Count
    if ($exactCollection) {
        for ($index = 0; $index -lt $ExpectedNodeIds.Count; $index++) {
            if ([string]$collected[$index] -cne $ExpectedNodeIds[$index]) { $exactCollection = $false; break }
        }
    }
    $exactPassed = $passed.Count -eq $ExpectedNodeIds.Count
    if ($exactPassed) {
        for ($index = 0; $index -lt $ExpectedNodeIds.Count; $index++) {
            if ([string]$passed[$index] -cne $ExpectedNodeIds[$index]) { $exactPassed = $false; break }
        }
    }
    if (
        [bool]$payload.tests_passed -and $exactCollection -and $exactPassed -and
        $failed.Count -eq 0 -and $skipped.Count -eq 0 -and $xfailed.Count -eq 0 -and
        [int64]$payload.deselected_count -eq 0 -and [int]$payload.pytest_exit_code -eq 0 -and
        [bool]$payload.receipt_path_hidden -and [bool]$payload.spawn_denial_probe_pass -and
        [bool]$payload.network_denial_probe_pass
    ) { return "U24_E2_ENDPOINT_LOCAL_QUALIFIED" }
    if (
        -not $exactCollection -or $failed.Count -ne 1 -or [string]$failed[0] -notin $ExpectedNodeIds -or
        $skipped.Count -ne 0 -or $xfailed.Count -ne 0 -or [int64]$payload.deselected_count -ne 0 -or
        [int]$payload.pytest_exit_code -ne 1 -or -not [bool]$payload.receipt_path_hidden -or
        -not [bool]$payload.spawn_denial_probe_pass -or -not [bool]$payload.network_denial_probe_pass
    ) { return "U24_E2_RUNNER_BLOCKED" }
    $expectedOtherPassed = @($ExpectedNodeIds | Where-Object { $_ -cne [string]$failed[0] })
    if (-not (Test-ExactStringArray -Left $passed -Right $expectedOtherPassed)) { return "U24_E2_RUNNER_BLOCKED" }
    $index = [Array]::IndexOf([string[]]$ExpectedNodeIds, [string]$failed[0]) + 1
    if ($index -in @(1, 6, 8, 10)) { return "U24_E2_TYPE_OR_WIRE_BLOCKED" }
    if ($index -in @(2, 3, 4, 5)) { return "U24_E2_ENVELOPE_BLOCKED" }
    if ($index -eq 7) { return "U24_E2_RESOURCE_OR_SCOPE_BLOCKED" }
    if ($index -eq 9) { return "U24_E2_GATE_NONBINDING" }
    return "U24_E2_RUNNER_BLOCKED"
}

function Write-ExclusiveCanonicalFile {
    param(
        [Parameter(Mandatory = $true)][string] $LiteralPath,
        [Parameter(Mandatory = $true)] $Payload
    )
    $canonical = Get-CanonicalPayload -Value $Payload
    $stream = [IO.File]::Open($LiteralPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $stream.Write($canonical.bytes, 0, $canonical.bytes.Length); $stream.Flush($true) }
    finally { $stream.Dispose() }
    $reopened = [IO.File]::ReadAllBytes($LiteralPath)
    if ($reopened.Length -ne $canonical.byte_length -or (Get-Sha256Bytes -Bytes $reopened) -cne $canonical.sha256) {
        throw "exclusive canonical file failed durable revalidation"
    }
    return $canonical
}

function Write-CanonicalConsoleRecord {
    param(
        [Parameter(Mandatory = $true)][string] $Label,
        [Parameter(Mandatory = $true)] $Canonical
    )
    $recordText = "{0}_JSON={1}`n{0}_BYTE_LENGTH={2}`n{0}_SHA256={3}`n" -f @(
        $Label, $Canonical.text, $Canonical.byte_length, $Canonical.sha256
    )
    $recordBytes = [Text.Encoding]::ASCII.GetBytes($recordText)
    [Console]::Out.Flush()
    $standardOutput = [Console]::OpenStandardOutput()
    $standardOutput.Write($recordBytes, 0, $recordBytes.Length)
    $standardOutput.Flush()
}

function Write-E2ChildCaptures {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]] $StdoutBytes,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][byte[]] $StderrBytes,
        [Parameter(Mandatory = $true)][ref] $StdoutEmitted,
        [Parameter(Mandatory = $true)][ref] $StderrEmitted
    )
    $failures = [Collections.Generic.List[Exception]]::new()
    if (-not [bool]$StdoutEmitted.Value) {
        try {
            if ($StdoutBytes.Length -ne 0) {
                [Console]::Out.Flush()
                $stream = [Console]::OpenStandardOutput()
                $prefix = [Text.Encoding]::ASCII.GetBytes("U24_E2_CHILD_STDOUT_BEGIN`n")
                $suffix = [Text.Encoding]::ASCII.GetBytes("`nU24_E2_CHILD_STDOUT_END`n")
                $stream.Write($prefix, 0, $prefix.Length)
                $stream.Write($StdoutBytes, 0, $StdoutBytes.Length)
                $stream.Write($suffix, 0, $suffix.Length)
                $stream.Flush()
            }
            $StdoutEmitted.Value = $true
        }
        catch { $failures.Add($_.Exception) }
    }
    if (-not [bool]$StderrEmitted.Value) {
        try {
            if ($StderrBytes.Length -ne 0) {
                [Console]::Error.Flush()
                $stream = [Console]::OpenStandardError()
                $prefix = [Text.Encoding]::ASCII.GetBytes("U24_E2_CHILD_STDERR_BEGIN`n")
                $suffix = [Text.Encoding]::ASCII.GetBytes("`nU24_E2_CHILD_STDERR_END`n")
                $stream.Write($prefix, 0, $prefix.Length)
                $stream.Write($StderrBytes, 0, $StderrBytes.Length)
                $stream.Write($suffix, 0, $suffix.Length)
                $stream.Flush()
            }
            $StderrEmitted.Value = $true
        }
        catch { $failures.Add($_.Exception) }
    }
    if ($failures.Count -ne 0) {
        throw [AggregateException]::new("one or more child capture console emissions failed", $failures.ToArray())
    }
}

function Test-EphemeralCanonicalPayload {
    param(
        [Parameter(Mandatory = $true)][string] $LiteralPath,
        [Parameter(Mandatory = $true)] $Payload
    )
    $canonical = Get-CanonicalPayload -Value $Payload
    if (Test-Path -LiteralPath $LiteralPath) { throw "ephemeral canonical validation path pre-existed" }
    $options = [IO.FileOptions]([int][IO.FileOptions]::WriteThrough -bor [int][IO.FileOptions]::DeleteOnClose)
    $stream = $null
    $validationFailure = $null
    try {
        $stream = [IO.FileStream]::new(
            $LiteralPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite,
            [IO.FileShare]::None, 4096, $options
        )
        $stream.Write($canonical.bytes, 0, $canonical.bytes.Length)
        $stream.Flush($true)
        [void]$stream.Seek(0, [IO.SeekOrigin]::Begin)
        $reopened = [byte[]]::new([int]$canonical.byte_length)
        $offset = 0
        while ($offset -lt $reopened.Length) {
            $count = $stream.Read($reopened, $offset, $reopened.Length - $offset)
            if ($count -le 0) { throw "ephemeral canonical validation ended early" }
            $offset += $count
        }
        if ($stream.ReadByte() -ne -1) { throw "ephemeral canonical validation grew during held read" }
        if ((Get-Sha256Bytes -Bytes $reopened) -cne $canonical.sha256) {
            throw "ephemeral canonical validation digest mismatch"
        }
    }
    catch { $validationFailure = $_.Exception }
    finally {
        if ($null -ne $stream) {
            try { $stream.Dispose() }
            catch { if ($null -eq $validationFailure) { $validationFailure = $_.Exception } }
        }
    }
    if (Test-Path -LiteralPath $LiteralPath) { throw "ephemeral canonical validation path survived DeleteOnClose" }
    if ($null -ne $validationFailure) { throw $validationFailure }
    return $canonical
}

function Open-HeldExecutableIdentity {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string] $LiteralPath,
        [Parameter(Mandatory = $true)][string] $ExpectedSha256
    )
    $fullPath = [IO.Path]::GetFullPath($LiteralPath)
    Assert-NonReparsePath -LiteralPath $fullPath
    $stream = $null
    try {
        $stream = [IO.File]::Open($fullPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $observed = ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace("-", "") }
        finally { $sha.Dispose() }
        $stream.Position = 0
        if ($observed -cne $ExpectedSha256) { throw "$Name held executable SHA-256 drift: $observed" }
        return [pscustomobject][ordered]@{
            name = $Name
            path = $fullPath
            stream = $stream
            held_from_hash = $true
            closed = $false
            close_adjudicated = $false
        }
    }
    catch {
        if ($null -ne $stream) { try { $stream.Dispose() } catch { } }
        throw
    }
}

function Close-And-AdjudicateHeldExecutableIdentity {
    param([Parameter(Mandatory = $true)] $Identity)
    if (-not [bool]$Identity.held_from_hash) {
        throw "$($Identity.name) executable identity was not held continuously from hashing"
    }
    if ([bool]$Identity.closed) {
        if ($null -ne $Identity.stream -or -not [bool]$Identity.close_adjudicated) {
            throw "$($Identity.name) executable identity has inconsistent closed state"
        }
        return
    }
    if ($null -eq $Identity.stream) {
        throw "$($Identity.name) held executable stream is unavailable"
    }
    $safeHandle = $Identity.stream.SafeFileHandle
    $Identity.stream.Dispose()
    if (-not $safeHandle.IsClosed) {
        throw "$($Identity.name) held executable handle did not close"
    }
    $Identity.stream = $null
    $Identity.closed = $true
    $Identity.close_adjudicated = $true
}

$exitCode = $ExitRunnerBlocked
$runRoot = $null
$systemTemp = $null
$attemptMarkerPath = $null
$attemptMarkerCreated = $false
$attemptMarkerConsumed = $false
$preRunCanonical = $null
$runnerCommitObserved = $null
$runnerTreeObserved = $null
$scientificProcess = $null
$scientificSession = $null
$held = $null
$bootstrapHandle = $null
$childStarted = $false
$outerReportEmitted = $false
$existingMarkerEvidence = $null
$preserveInvalidEvidence = $false
$outerPath = $null
$outerCanonical = $null
$outerPayload = $null
$failureOuterCreated = $false
$stdoutCaptureEmitted = $false
$stderrCaptureEmitted = $false
$attemptMarkerWriteStarted = $false
$attemptMarkerAbsenceAdjudicated = $false
$attemptCanonical = $null
$materializedPairs = $null
$runnerRawSha256 = $null
$runnerBlobObserved = $null
$privateSourceRoot = $null
$privateRuntimeRoot = $null
$bootstrapPath = $null
$armPath = $null
$receiptPath = $null
$clock = $null
$elapsedTicks = $null
$wallExpired = $false
$outputObserved = $false
$jobMessages = $null
$jobFinalStateObserved = $false
$nativeExit = $null
$peakJobMemory = $null
$pumpsComplete = $false
$captureWritersClosed = $false
$stdoutBytes = $null
$stderrBytes = $null
$stdoutDropped = $null
$stderrDropped = $null
$memoryObserved = $false
$activeProcessViolation = $false
$receipt = $null
$receiptReadAttempted = $false
$receiptReadControlFailure = $false
$cleanupComplete = $false
$nativeAssembly = $null
$powerShellExecutableIdentity = $null
$gitExecutableIdentity = $null
$pythonExecutableIdentity = $null
$gitExecutableHeldThroughLastUse = $false

try {
    $nativeAssembly = Initialize-NativeHelper
    if ($env:OS -cne "Windows_NT" -or -not [Environment]::Is64BitProcess) { throw "runner requires x64 Windows" }
    if ($PSVersionTable.PSEdition -cne "Desktop" -or $PSVersionTable.PSVersion.ToString() -cne $PowerShellVersion) {
        throw "parent PowerShell version drift: $($PSVersionTable.PSVersion)"
    }
    $hostExecutable = [Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
    if (-not [IO.Path]::GetFullPath($hostExecutable).Equals($PowerShellPath, [StringComparison]::OrdinalIgnoreCase)) {
        throw "parent PowerShell executable drift"
    }
    $powerShellExecutableIdentity = Open-HeldExecutableIdentity -Name "PowerShell" -LiteralPath $PowerShellPath -ExpectedSha256 $PowerShellSha256
    $gitExecutableIdentity = Open-HeldExecutableIdentity -Name "Git" -LiteralPath $GitPath -ExpectedSha256 $GitSha256
    $pythonExecutableIdentity = Open-HeldExecutableIdentity -Name "Python" -LiteralPath $PythonPath -ExpectedSha256 $PythonSha256
    $hostVersion = [Diagnostics.FileVersionInfo]::GetVersionInfo($PowerShellPath).FileVersion.Split(' ')[0]
    if ($hostVersion -cne $PowerShellFileVersion) { throw "parent PowerShell file version drift: $hostVersion" }
    if ([Diagnostics.FileVersionInfo]::GetVersionInfo($PythonPath).FileVersion -cne $PythonVersion) {
        throw "Python file version drift"
    }

    if ([string]::IsNullOrWhiteSpace($PSCommandPath)) { throw "runner script path is unavailable" }
    $scriptPath = [IO.Path]::GetFullPath($PSCommandPath)
    Assert-NonReparsePath -LiteralPath $scriptPath
    $toolsRoot = [IO.Path]::GetFullPath((Split-Path -Parent $scriptPath))
    if ([IO.Path]::GetFileName($toolsRoot) -cne "tools") { throw "runner is outside the repository tools directory" }
    $repositoryRoot = [IO.Path]::GetFullPath((Split-Path -Parent $toolsRoot))
    $expectedScriptPath = [IO.Path]::GetFullPath((Join-Path $repositoryRoot $RunnerRelativePath.Replace('/', '\')))
    if (-not $scriptPath.Equals($expectedScriptPath, [StringComparison]::OrdinalIgnoreCase)) { throw "runner checkout path drift" }
    foreach ($marker in @(".git", "pyproject.toml", "lean_rgc", "tests")) {
        if (-not (Test-Path -LiteralPath (Join-Path $repositoryRoot $marker))) { throw "repository marker is missing: $marker" }
    }
    foreach ($semanticPath in @(
        "lean_rgc/odlrq/certificates.py", "lean_rgc/odlrq/selection.py", "tests/test_odlrq_selection.py"
    )) {
        if (Test-Path -LiteralPath (Join-Path $repositoryRoot $semanticPath.Replace('/', '\'))) {
            Throw-SourceFreezeMismatch "semantic source is present in the runner-control checkout: $semanticPath"
        }
    }

    $systemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
    Assert-NonReparsePath -LiteralPath $systemTemp
    $runRoot = New-OwnedDirectory -LiteralPath (Join-Path $systemTemp ("lean-rgc-u24-e2-" + [Guid]::NewGuid().ToString("N"))) -RequiredParent $systemTemp
    $gitScratch = New-OwnedDirectory -LiteralPath (Join-Path $runRoot "git-control") -RequiredParent $runRoot
    $privateSourceRoot = New-OwnedDirectory -LiteralPath (Join-Path $runRoot "source") -RequiredParent $runRoot
    $privateRuntimeRoot = New-OwnedDirectory -LiteralPath (Join-Path $runRoot "runtime") -RequiredParent $runRoot
    $archivePath = Join-Path $runRoot "semantic-source.zip"
    $bootstrapPath = Join-Path $runRoot "u24_e2_bootstrap.py"
    $armPath = Join-Path $runRoot "python.arm"
    $receiptPath = Join-Path $runRoot "child-receipt.json"
    $stdoutPath = Join-Path $runRoot "child.stdout.bin"
    $stderrPath = Join-Path $runRoot "child.stderr.bin"

    $gitVersionResult = Invoke-BoundedGit -Arguments @("--version") -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch
    if ((Convert-GitUtf8 -Bytes $gitVersionResult.stdout).TrimEnd("`r", "`n") -cne $GitVersion) { throw "Git version output drift" }
    $replaceRefResult = Invoke-BoundedGit -Arguments @("for-each-ref", "--format=%(refname)%00%(objectname)", "refs/replace") -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch
    if ($replaceRefResult.stdout.Length -ne 0) { throw "local replacement refs are forbidden" }
    $localConfigKeysResult = Invoke-BoundedGit -Arguments @("config", "--local", "--name-only", "--get-regexp", ".*") -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch
    $localConfigKeyText = (Convert-GitUtf8 -Bytes $localConfigKeysResult.stdout).Replace("`r`n", "`n").TrimEnd("`n")
    foreach ($configKey in $localConfigKeyText.Split("`n")) {
        if ($configKey -match '^(?:extensions\.partialclone|remote\..+\.(?:promisor|partialclonefilter)|url\..+\.(?:insteadof|pushinsteadof))$') {
            throw "partial-clone/promisor/URL-rewrite configuration is forbidden: $configKey"
        }
    }
    $headResult = Invoke-BoundedGit -Arguments @("rev-parse", "--verify", "HEAD^{commit}") -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch
    $runnerCommitObserved = (Convert-GitUtf8 -Bytes $headResult.stdout).TrimEnd("`r", "`n")
    if ($runnerCommitObserved -notmatch '^[0-9a-f]{40}$') { Throw-SourceFreezeMismatch "runner-control HEAD is malformed" }

    $runnerObject = Parse-CommitObject -Text (Convert-GitUtf8 -Bytes (Invoke-BoundedGit -Arguments @("cat-file", "-p", $runnerCommitObserved) -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch).stdout)
    $authorityObject = Parse-CommitObject -Text (Convert-GitUtf8 -Bytes (Invoke-BoundedGit -Arguments @("cat-file", "-p", $AuthorityCommit) -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch).stdout)
    $semanticObject = Parse-CommitObject -Text (Convert-GitUtf8 -Bytes (Invoke-BoundedGit -Arguments @("cat-file", "-p", $SemanticCommit) -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch).stdout)
    $e1Object = Parse-CommitObject -Text (Convert-GitUtf8 -Bytes (Invoke-BoundedGit -Arguments @("cat-file", "-p", $AcceptedE1Commit) -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch).stdout)
    $runnerTreeObserved = $runnerObject.tree
    if ($runnerObject.parents.Count -ne 2 -or $runnerObject.parents[0] -cne $AuthorityCommit -or $runnerObject.parents[1] -cne $SemanticCommit) {
        Throw-SourceFreezeMismatch "runner-control carrier ordered parents are not [authority,semantic]"
    }
    if ($runnerObject.message -cne $RunnerSubject) { Throw-SourceFreezeMismatch "runner-control subject drift" }
    if ($authorityObject.tree -cne $AuthorityTree -or $authorityObject.parents.Count -ne 1 -or $authorityObject.parents[0] -cne $AcceptedE1Commit) {
        Throw-SourceFreezeMismatch "authority commit topology drift"
    }
    if ($semanticObject.tree -cne $SemanticTree -or $semanticObject.parents.Count -ne 1 -or $semanticObject.parents[0] -cne $AcceptedE1Commit -or $semanticObject.message -cne "uprime: qualify exact E2 endpoint") {
        Throw-SourceFreezeMismatch "semantic source commit topology drift"
    }
    if ($e1Object.tree -cne $AcceptedE1Tree) { Throw-SourceFreezeMismatch "accepted E1 tree drift" }

    $statusResult = Invoke-BoundedGit -Arguments @("status", "--porcelain=v1", "-z", "--untracked-files=all") -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch
    if ($statusResult.stdout.Length -ne 0) { Throw-SourceFreezeMismatch "runner-control worktree or index is not clean" }
    $runnerDiff = Parse-DiffTree -Bytes (Invoke-BoundedGit -Arguments @(
        "diff-tree", "--no-commit-id", "--name-status", "--no-renames", "-r", "-z", $AuthorityCommit, $runnerCommitObserved
    ) -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch).stdout
    if ($runnerDiff.Count -ne 1 -or $runnerDiff[0].status -cne "A" -or $runnerDiff[0].path -cne $RunnerRelativePath) {
        Throw-SourceFreezeMismatch "runner-control tree is not authority plus only the runner"
    }
    $semanticDiff = Parse-DiffTree -Bytes (Invoke-BoundedGit -Arguments @(
        "diff-tree", "--no-commit-id", "--name-status", "--no-renames", "-r", "-z", $AcceptedE1Commit, $SemanticCommit
    ) -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch).stdout
    $expectedSemanticStatuses = [ordered]@{
        "lean_rgc/odlrq/certificates.py" = "A"
        "lean_rgc/odlrq/selection.py" = "A"
        "tests/test_odlrq_selection.py" = "A"
        "tests/tier_manifest.json" = "M"
    }
    if ($semanticDiff.Count -ne 4) { Throw-SourceFreezeMismatch "semantic source diff path count drift" }
    foreach ($row in $semanticDiff) {
        if (-not $expectedSemanticStatuses.Contains($row.path) -or $expectedSemanticStatuses[$row.path] -cne $row.status) {
            Throw-SourceFreezeMismatch "semantic source diff drift: $($row.path)"
        }
    }

    $headTreeRows = Parse-LsTree -Bytes (Invoke-BoundedGit -Arguments @(
        "ls-tree", "-z", $runnerCommitObserved, "--", $RunnerRelativePath, $AuthorityDocumentPath,
        "lean_rgc/odlrq/certificates.py", "lean_rgc/odlrq/selection.py",
        "tests/test_odlrq_selection.py", "tests/tier_manifest.json"
    ) -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch).stdout
    $headTreeMap = @{}
    foreach ($row in $headTreeRows) { $headTreeMap[$row.path] = $row }
    if ($headTreeMap.Count -ne 3) { Throw-SourceFreezeMismatch "runner-control checked-out special path set drift" }
    if ($headTreeMap[$RunnerRelativePath].mode -cne "100644") { Throw-SourceFreezeMismatch "runner Git mode drift" }
    if ($headTreeMap[$AuthorityDocumentPath].oid -cne $AuthorityDocumentBlob -or $headTreeMap[$AuthorityDocumentPath].mode -cne "100644") {
        Throw-SourceFreezeMismatch "authority document blob drift in carrier"
    }
    if ($headTreeMap["tests/tier_manifest.json"].oid -cne $ImmutableE1Blobs["tests/tier_manifest.json"]) {
        Throw-SourceFreezeMismatch "runner-control tier manifest is not accepted E1"
    }
    foreach ($absent in $SemanticPaths[0..2]) { if ($headTreeMap.ContainsKey($absent)) { Throw-SourceFreezeMismatch "semantic path is present in runner tree" } }

    $semanticTreeRows = Parse-LsTree -Bytes (Invoke-BoundedGit -Arguments (@("ls-tree", "-z", $SemanticCommit, "--") + $SemanticPaths) -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch).stdout
    if ($semanticTreeRows.Count -ne 4) { Throw-SourceFreezeMismatch "semantic tree four-path lookup incomplete" }
    foreach ($row in $semanticTreeRows) {
        if ($row.mode -cne "100644" -or -not $SemanticBlobs.Contains($row.path) -or $SemanticBlobs[$row.path] -cne $row.oid) {
            Throw-SourceFreezeMismatch "semantic tree mode/blob drift: $($row.path)"
        }
    }
    $e1TreeRows = Parse-LsTree -Bytes (Invoke-BoundedGit -Arguments (@("ls-tree", "-z", $AcceptedE1Commit, "--") + @($ImmutableE1Blobs.Keys)) -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch).stdout
    if ($e1TreeRows.Count -ne $ImmutableE1Blobs.Count) { Throw-SourceFreezeMismatch "immutable E1 blob lookup incomplete" }
    foreach ($row in $e1TreeRows) {
        if ($row.mode -cne "100644" -or $ImmutableE1Blobs[$row.path] -cne $row.oid) { Throw-SourceFreezeMismatch "immutable E1 blob drift: $($row.path)" }
    }

    $runnerBlobResult = Invoke-BoundedGit -Arguments @("hash-object", "--path=$RunnerRelativePath", "--", $RunnerRelativePath) -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch
    $runnerBlobObserved = (Convert-GitUtf8 -Bytes $runnerBlobResult.stdout).TrimEnd("`r", "`n")
    if ($runnerBlobObserved -notmatch '^[0-9a-f]{40}$' -or $headTreeMap[$RunnerRelativePath].oid -cne $runnerBlobObserved) {
        Throw-SourceFreezeMismatch "runner checkout filtered Git blob mismatch"
    }
    $runnerRawSha256 = Get-Sha256File -LiteralPath $scriptPath

    $remoteUrlResult = Invoke-BoundedGit -Arguments @("remote", "get-url", "--all", "origin") -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch
    $remoteUrlText = (Convert-GitUtf8 -Bytes $remoteUrlResult.stdout).Replace("`r`n", "`n").TrimEnd("`n")
    [string[]]$remoteUrls = if ([string]::IsNullOrEmpty($remoteUrlText)) { @() } else { $remoteUrlText.Split("`n") }
    if ($remoteUrls.Count -ne 1 -or $remoteUrls[0] -cne $ExpectedRemoteUrl) { throw "origin fetch URL is not the frozen public repository" }
    $remotePushUrlResult = Invoke-BoundedGit -Arguments @("remote", "get-url", "--push", "--all", "origin") -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch
    $remotePushUrlText = (Convert-GitUtf8 -Bytes $remotePushUrlResult.stdout).Replace("`r`n", "`n").TrimEnd("`n")
    [string[]]$remotePushUrls = if ([string]::IsNullOrEmpty($remotePushUrlText)) { @() } else { $remotePushUrlText.Split("`n") }
    if ($remotePushUrls.Count -ne 1 -or $remotePushUrls[0] -cne $ExpectedRemoteUrl) { throw "origin push URL is not the frozen public repository" }
    $remoteResult = Invoke-BoundedGit -Arguments @("ls-remote", "--heads", "--tags", $ExpectedRemoteUrl) -RepositoryRoot $runRoot -ScratchRoot $gitScratch -WallSeconds $ControlRemoteWallSeconds
    $remoteText = (Convert-GitUtf8 -Bytes $remoteResult.stdout).Replace("`r`n", "`n").TrimEnd("`n")
    if ([string]::IsNullOrEmpty($remoteText)) { throw "remote heads/tags census is empty" }
    [string[]]$censusLines = $remoteText.Split("`n")
    [Array]::Sort($censusLines, [StringComparer]::Ordinal)
    $remoteMap = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::Ordinal)
    foreach ($line in $censusLines) {
        if ($line -notmatch '^(?<sha>[0-9a-f]{40})\t(?<ref>refs/(?:heads|tags)/[\x21-\x7e]+(?:\^\{\})?)$') { throw "malformed or non-ASCII remote census row" }
        if ($remoteMap.ContainsKey($Matches.ref)) { throw "duplicate remote census ref" }
        $remoteMap.Add($Matches.ref, $Matches.sha)
        if ($Matches.sha -ceq $SemanticCommit) { throw "semantic commit is directly advertised by a head/tag tip" }
    }
    if (-not $remoteMap.ContainsKey($AuthorityRef) -or $remoteMap[$AuthorityRef] -cne $AuthorityCommit) { throw "authority remote ref drift" }
    if (-not $remoteMap.ContainsKey($RunnerRef) -or $remoteMap[$RunnerRef] -cne $runnerCommitObserved) { throw "runner-control remote ref drift" }
    if (-not $remoteMap.ContainsKey($AcceptedRef) -or $remoteMap[$AcceptedRef] -cne $AcceptedE1Commit) { throw "accepted remote ref drift" }
    foreach ($absentRef in @($BuildRef, $SuccessCloseoutRef, $FailureCloseoutRef)) {
        if ($remoteMap.ContainsKey($absentRef)) { throw "future publication ref already exists: $absentRef" }
    }
    $censusPayloadText = $censusLines -join "`n"
    if (@($censusPayloadText.ToCharArray() | Where-Object { [int][char]$_ -gt 127 }).Count -ne 0) { throw "remote census is not canonical ASCII" }
    $censusPayloadBytes = [Text.Encoding]::ASCII.GetBytes($censusPayloadText)
    $censusSha256 = Get-Sha256Bytes -Bytes $censusPayloadBytes

    $parentManifestResult = Invoke-BoundedGit -Arguments @("show", "$AcceptedE1Commit`:tests/tier_manifest.json") -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch
    if ((Get-Sha256Bytes -Bytes $parentManifestResult.stdout).Length -ne 64) { throw "parent manifest capture failed" }

    $runtimeInventory = Get-RuntimeInventory
    Copy-PrivateRuntime -Inventory $runtimeInventory -DestinationRoot $privateRuntimeRoot
    $archiveEvidence = Materialize-SemanticArchive -RepositoryRoot $repositoryRoot -ScratchRoot $gitScratch -ZipPath $archivePath -DestinationRoot $privateSourceRoot
    $gitExecutableHeldThroughLastUse = $true
    Close-And-AdjudicateHeldExecutableIdentity -Identity $gitExecutableIdentity
    Assert-ManifestDelta -ParentBytes $parentManifestResult.stdout -SemanticManifestPath (Join-Path $privateSourceRoot "tests\tier_manifest.json")

    $materializedPairs = [ordered]@{}
    foreach ($path in $SemanticPaths) {
        $materializedPath = Join-Path $privateSourceRoot $path.Replace('/', '\')
        $blob = Get-GitBlobOid -LiteralPath $materializedPath
        if ($blob -cne $SemanticBlobs[$path]) { throw "materialized semantic blob mismatch: $path" }
        $materializedPairs[$path] = [ordered]@{
            raw_sha256 = Get-Sha256File -LiteralPath $materializedPath
            git_blob = $blob
        }
    }
    foreach ($boundPath in @("lean_rgc/odlrq/certificates.py", "tests/test_odlrq_selection.py")) {
        $boundText = [IO.File]::ReadAllText((Join-Path $privateSourceRoot $boundPath.Replace('/', '\')), [Text.Encoding]::UTF8)
        foreach ($literal in @($AuthorityCommit, $AuthorityTree, $AuthorityDocumentPath, $AuthorityDocumentBlob)) {
            if (-not $boundText.Contains($literal)) { throw "materialized $boundPath lacks authority literal $literal" }
        }
    }

    $bootstrapSource = Get-E2BootstrapSource
    [IO.File]::WriteAllText($bootstrapPath, $bootstrapSource, [Text.UTF8Encoding]::new($false))
    $bootstrapSha256 = Get-Sha256File -LiteralPath $bootstrapPath
    $held = Open-HeldFiles -Roots @($privateSourceRoot, $privateRuntimeRoot)
    if ($held.identities.Count -ne $archiveEvidence.rows.Count + $RuntimeCopyFileCount) { throw "held private file set count drift" }
    $heldIdentityMap = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($identity in $held.identities) {
        if ($heldIdentityMap.ContainsKey($identity.path)) { throw "duplicate held private path" }
        $heldIdentityMap.Add($identity.path, $identity)
    }
    foreach ($row in $archiveEvidence.rows) {
        $heldPath = [IO.Path]::GetFullPath((Join-Path $privateSourceRoot $row.path.Replace('/', '\')))
        if (
            -not $heldIdentityMap.ContainsKey($heldPath) -or
            $heldIdentityMap[$heldPath].byte_count -ne [int64]$row.size -or
            $heldIdentityMap[$heldPath].git_blob -cne $row.oid
        ) { throw "held source file set/blob drift: $($row.path)" }
    }
    foreach ($path in $SemanticPaths) {
        $heldPath = [IO.Path]::GetFullPath((Join-Path $privateSourceRoot $path.Replace('/', '\')))
        if (-not $heldIdentityMap.ContainsKey($heldPath) -or $heldIdentityMap[$heldPath].sha256 -cne $materializedPairs[$path].raw_sha256) {
            throw "held semantic bytes disagree with pre-hold identity: $path"
        }
    }
    foreach ($copy in $runtimeInventory.copies) {
        $heldPath = [IO.Path]::GetFullPath((Join-Path $privateRuntimeRoot $copy.relative_posix_path.Replace('/', '\')))
        if (-not $heldIdentityMap.ContainsKey($heldPath) -or $heldIdentityMap[$heldPath].sha256 -cne $copy.sha256) {
            throw "held runtime bytes disagree with RECORD identity: $($copy.relative_posix_path)"
        }
    }
    $bootstrapHandle = [IO.File]::Open($bootstrapPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    if ((Get-Sha256File -LiteralPath $bootstrapPath) -cne $bootstrapSha256) { throw "bootstrap changed before held execution" }

    $runtimeIdentityRows = [Collections.Generic.List[object]]::new()
    foreach ($distribution in $RuntimeDistributions.Keys) {
        $runtimeIdentityRows.Add([ordered]@{
            distribution = $distribution
            version = $RuntimeDistributions[$distribution].version
            admitted_rows = [int]$RuntimeDistributions[$distribution].rows
        })
    }
    $preRunManifest = [ordered]@{
        schema_version = $PreRunManifestSchema
        lane = $Lane
        endpoint_id = $EndpointId
        authority_commit = $AuthorityCommit
        authority_tree = $AuthorityTree
        authority_document_path = $AuthorityDocumentPath
        authority_document_blob = $AuthorityDocumentBlob
        authority_ci_run_id = $AuthorityCiRunId
        authority_ci_job_id = $AuthorityCiJobId
        source_commit = $SemanticCommit
        source_tree = $SemanticTree
        source_parent = $AcceptedE1Commit
        source_diff = @($semanticDiff | ForEach-Object { [ordered]@{ status = $_.status; path = $_.path } })
        source_blobs = $SemanticBlobs
        runner_commit = $runnerCommitObserved
        runner_tree = $runnerTreeObserved
        runner_parents = @($runnerObject.parents)
        runner_subject = $RunnerSubject
        runner_diff = @([ordered]@{ status = "A"; path = $RunnerRelativePath })
        runner_checkout_raw_sha256 = $runnerRawSha256
        runner_git_blob = $runnerBlobObserved
        authority_ref = [ordered]@{ name = $AuthorityRef; tip = $AuthorityCommit }
        runner_ref = [ordered]@{ name = $RunnerRef; tip = $runnerCommitObserved }
        accepted_ref = [ordered]@{ name = $AcceptedRef; tip = $AcceptedE1Commit }
        absent_refs = @($BuildRef, $SuccessCloseoutRef, $FailureCloseoutRef)
        remote_census_payload = $censusPayloadText
        remote_census_byte_length = [int64]$censusPayloadBytes.Length
        remote_census_sha256 = $censusSha256
        remote_fetch_url = $remoteUrls[0]
        remote_push_url = $remotePushUrls[0]
        remote_fetch_get_url_byte_length = [int64]$remoteUrlResult.stdout.Length
        remote_fetch_get_url_sha256 = Get-Sha256Bytes -Bytes $remoteUrlResult.stdout
        remote_push_get_url_byte_length = [int64]$remotePushUrlResult.stdout.Length
        remote_push_get_url_sha256 = Get-Sha256Bytes -Bytes $remotePushUrlResult.stdout
        remote_semantic_tip_absent = $true
        clean_status = $true
        clean_status_byte_length = [int64]0
        clean_status_sha256 = Get-Sha256Bytes -Bytes ([byte[]]::new(0))
        materialized_pairs = $materializedPairs
        immutable_e1_blobs = $ImmutableE1Blobs
        semantic_archive_sha256 = $archiveEvidence.archive_sha256
        runtime_source_root = $RuntimeSourceRoot
        runtime_aggregate_row_count = [int]$RuntimeAggregateRowCount
        runtime_aggregate_byte_length = [int64]$RuntimeAggregateByteLength
        runtime_aggregate_sha256 = $RuntimeAggregateSha256
        runtime_copy_file_count = [int]$RuntimeCopyFileCount
        runtime_distributions = $runtimeIdentityRows.ToArray()
        runtime_inventory_rows = @($runtimeInventory.rows)
        native_helper = [ordered]@{
            source_sha256 = $NativeSourceSha256
            source_byte_length = [int64]$NativeSourceByteLength
            assembly_sha256 = $NativeAssemblySha256
            assembly_byte_length = [int64]$NativeAssemblyByteLength
            assembly_full_name = $NativeAssemblyFullName
            assembly_mvid = $NativeAssemblyMvid
            exported_surface = @($NativeAssemblySurface)
        }
        named_executable_holds = [ordered]@{
            powershell = [ordered]@{
                path = $powerShellExecutableIdentity.path
                held_from_hash = [bool]$powerShellExecutableIdentity.held_from_hash
                open_at_pre_run_manifest = [bool](-not $powerShellExecutableIdentity.closed)
            }
            git = [ordered]@{
                path = $gitExecutableIdentity.path
                held_from_hash = [bool]$gitExecutableIdentity.held_from_hash
                held_through_last_invocation = [bool]$gitExecutableHeldThroughLastUse
                closed_and_adjudicated_before_marker = [bool]($gitExecutableIdentity.closed -and $gitExecutableIdentity.close_adjudicated)
            }
            python = [ordered]@{
                path = $pythonExecutableIdentity.path
                held_from_hash = [bool]$pythonExecutableIdentity.held_from_hash
                open_at_pre_run_manifest = [bool](-not $pythonExecutableIdentity.closed)
            }
        }
        python = [ordered]@{ version = $PythonVersion; executable_sha256 = $PythonSha256; architecture = "x86-64" }
        powershell = [ordered]@{ version = $PowerShellVersion; file_version = $PowerShellFileVersion; executable_sha256 = $PowerShellSha256; architecture = "x86-64" }
        git = [ordered]@{ version = $GitVersion; executable_sha256 = $GitSha256; invocation_count = [int]$script:GitInvocationCount; aggregate_elapsed_ticks = [int64]$script:GitAggregateTicks }
        git_raw_object_policy = [ordered]@{
            config_nosystem = $true
            config_global = "NUL"
            no_replace_objects = $true
            graft_file = "NUL"
            no_lazy_fetch = $true
            optional_locks = $false
            temp_ceiling_directory = $true
            remote_query_uses_owned_nonrepository_working_directory = $true
            replace_ref_census_byte_length = [int64]$replaceRefResult.stdout.Length
            replace_ref_census_sha256 = Get-Sha256Bytes -Bytes $replaceRefResult.stdout
            local_config_key_census_byte_length = [int64]$localConfigKeysResult.stdout.Length
            local_config_key_census_sha256 = Get-Sha256Bytes -Bytes $localConfigKeysResult.stdout
        }
        pytest = [ordered]@{ version = "9.0.3"; init_sha256 = $PytestInitSha256 }
        bootstrap_sha256 = $bootstrapSha256
        expected_node_ids = $ExpectedNodeIds
        wall_ticks = $WallTicks
        qualification_ticks = $QualificationTicks
        clock_frequency = $StopwatchFrequency
        process_memory_limit_bytes = $MemoryLimitBytes
        job_memory_limit_bytes = $MemoryLimitBytes
        output_limit_bytes = $OutputLimitBytes
        active_process_limit = 1
        poll_milliseconds = $PollMilliseconds
    }
    $preRunCanonical = Get-CanonicalPayload -Value $preRunManifest
    Write-CanonicalConsoleRecord -Label "U24_E2_PRE_RUN_MANIFEST" -Canonical $preRunCanonical
    [Console]::Out.Flush()

    $localAppData = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
    if ([string]::IsNullOrWhiteSpace($localAppData)) { throw "LocalAppData path is unavailable" }
    Assert-NonReparsePath -LiteralPath $localAppData
    $latchRoot = Join-Path $localAppData "lean-rgc-automation"
    if (-not (Test-Path -LiteralPath $latchRoot)) { [void][IO.Directory]::CreateDirectory($latchRoot) }
    Assert-NonReparsePath -LiteralPath $latchRoot
    $attemptsRoot = Join-Path $latchRoot "uprime-e2-attempts"
    if (-not (Test-Path -LiteralPath $attemptsRoot)) { [void][IO.Directory]::CreateDirectory($attemptsRoot) }
    Assert-NonReparsePath -LiteralPath $attemptsRoot
    $attemptRoot = Join-Path $attemptsRoot "$AuthorityCommit-$SemanticCommit-$runnerCommitObserved"
    if (-not (Test-Path -LiteralPath $attemptRoot)) { [void][IO.Directory]::CreateDirectory($attemptRoot) }
    Assert-NonReparsePath -LiteralPath $attemptRoot
    $attemptMarkerPath = Join-Path $attemptRoot "attempt-consumed.json"
    if (Test-Path -LiteralPath $attemptMarkerPath) {
        $existingItem = Get-Item -LiteralPath $attemptMarkerPath -Force
        if ($existingItem.PSIsContainer -or ($existingItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "pre-existing attempt marker is not a regular non-reparse file" }
        if ($existingItem.Length -gt $ReceiptLimitBytes) { throw "pre-existing attempt marker exceeds evidence cap" }
        $existingMarkerEvidence = [ordered]@{
            path = $attemptMarkerPath
            byte_length = [int64]$existingItem.Length
            sha256 = Get-Sha256File -LiteralPath $attemptMarkerPath
        }
        throw "one-shot attempt marker already exists"
    }
    $attemptPayload = [ordered]@{
        schema_version = $AttemptSchema
        endpoint = $EndpointId
        authority_commit = $AuthorityCommit
        authority_tree = $AuthorityTree
        semantic_commit = $SemanticCommit
        semantic_tree = $SemanticTree
        runner_commit = $runnerCommitObserved
        runner_tree = $runnerTreeObserved
        pre_run_manifest_sha256 = $preRunCanonical.sha256
        attempt_consumed_before_child = $true
        created_at = [DateTime]::UtcNow.ToString("o", [Globalization.CultureInfo]::InvariantCulture)
    }
    $attemptMarkerWriteStarted = $true
    $attemptCanonical = Write-ExclusiveCanonicalFile -LiteralPath $attemptMarkerPath -Payload $attemptPayload
    $attemptMarkerCreated = $true
    $attemptMarkerConsumed = $true

    $pythonArguments = @(
        "-I", "-S", "-B", "-X", "utf8", $bootstrapPath,
        "--arm", $armPath,
        "--receipt", $receiptPath,
        "--source-root", $privateSourceRoot,
        "--runtime-root", $privateRuntimeRoot,
        "--manifest-sha", $preRunCanonical.sha256,
        "--marker-sha", $attemptCanonical.sha256,
        "--runner-commit", $runnerCommitObserved,
        "--runner-tree", $runnerTreeObserved
    )
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $PythonPath
    $startInfo.Arguments = [U24E2Native]::BuildArgumentLine([string[]]$pythonArguments)
    $startInfo.WorkingDirectory = $privateSourceRoot
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.RedirectStandardInput = $false
    $startInfo.EnvironmentVariables.Clear()
    $startInfo.EnvironmentVariables["SystemRoot"] = $env:SystemRoot
    $startInfo.EnvironmentVariables["WINDIR"] = $env:WINDIR
    $startInfo.EnvironmentVariables["ComSpec"] = $env:ComSpec
    $startInfo.EnvironmentVariables["TEMP"] = $systemTemp
    $startInfo.EnvironmentVariables["TMP"] = $systemTemp
    $startInfo.EnvironmentVariables["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    $scientificProcess = [Diagnostics.Process]::new()
    $scientificProcess.StartInfo = $startInfo
    $clock = [Diagnostics.Stopwatch]::StartNew()
    if (-not $scientificProcess.Start()) { throw "Python process creation returned false" }
    $childStarted = $true
    $scientificSession = [U24E2Native]::AttachManagedProcess($scientificProcess, $stdoutPath, $stderrPath, $OutputLimitBytes, $MemoryLimitBytes)
    if (Test-Path -LiteralPath $armPath) { throw "arm path existed before assignment" }
    $armBytes = [Text.Encoding]::ASCII.GetBytes("ARM`n")
    $armStream = [IO.File]::Open($armPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $armStream.Write($armBytes, 0, $armBytes.Length); $armStream.Flush($true) }
    finally { $armStream.Dispose() }
    if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($armPath)) -cne [Convert]::ToBase64String($armBytes)) { throw "arm bytes failed revalidation" }

    $wallExpired = $false
    $outputObserved = $false
    $jobMessages = [Collections.Generic.List[uint32]]::new()
    while (-not $scientificSession.Wait($PollMilliseconds)) {
        foreach ($message in $scientificSession.DrainJobMessages()) { $jobMessages.Add([uint32]$message) }
        if ($scientificSession.OutputExceeded) {
            $outputObserved = $true
            $scientificSession.Terminate([uint32]$ExitOutput)
            break
        }
        if ($clock.ElapsedTicks -ge $WallTicks) {
            $wallExpired = $true
            $scientificSession.Terminate([uint32]$ExitTimeout)
            break
        }
    }
    if (-not $scientificSession.Wait(2000)) {
        $scientificSession.Terminate([uint32]$ExitRunnerBlocked)
        if (-not $scientificSession.Wait(2000)) { throw "owned Python process did not terminate" }
    }
    $clock.Stop()
    $elapsedTicks = [int64]$clock.ElapsedTicks
    if ($elapsedTicks -ge $WallTicks) { $wallExpired = $true }
    foreach ($message in $scientificSession.DrainJobMessages()) { $jobMessages.Add([uint32]$message) }
    for ($completionPoll = 0; $completionPoll -lt 80 -and @($jobMessages | Where-Object { $_ -eq 4 }).Count -eq 0; $completionPoll++) {
        Start-Sleep -Milliseconds $PollMilliseconds
        foreach ($message in $scientificSession.DrainJobMessages()) { $jobMessages.Add([uint32]$message) }
    }
    $jobFinalStateObserved = @($jobMessages | Where-Object { $_ -eq 4 }).Count -gt 0
    $nativeExit = [int]$scientificSession.ExitCode
    $peakJobMemory = [uint64]$scientificSession.PeakJobMemory()
    $pumpsComplete = [bool]$scientificSession.FinishPumps(2000)
    $captureWritersClosed = [bool]$scientificSession.CaptureWritersClosed
    if (-not $captureWritersClosed) {
        throw "capture writers did not close after owned pipe disposal"
    }
    $stdoutBytes = $scientificSession.ReadStdout()
    $stderrBytes = $scientificSession.ReadStderr()
    $stdoutDropped = [int64]$scientificSession.StdoutDropped
    $stderrDropped = [int64]$scientificSession.StderrDropped
    if ($stdoutDropped -ne 0 -or $stderrDropped -ne 0 -or $scientificSession.OutputExceeded) { $outputObserved = $true }
    $memoryObserved = @($jobMessages | Where-Object { $_ -in @(9, 10) }).Count -gt 0
    $activeProcessViolation = @($jobMessages | Where-Object { $_ -eq 3 }).Count -gt 0
    $scientificSession.CloseJob()
    foreach ($handle in $held.handles) { $handle.Dispose() }
    $held = $null
    $bootstrapHandle.Dispose()
    $bootstrapHandle = $null
    $scientificSession.Dispose()
    $scientificSession = $null
    $scientificProcess = $null
    Close-And-AdjudicateHeldExecutableIdentity -Identity $pythonExecutableIdentity
    Close-And-AdjudicateHeldExecutableIdentity -Identity $powerShellExecutableIdentity

    $receiptReadAttempted = $true
    try {
        $receipt = Read-E2ChildReceipt -ReceiptPath $receiptPath -RunnerCommit $runnerCommitObserved -RunnerTree $runnerTreeObserved -ManifestSha $preRunCanonical.sha256 -MarkerSha $attemptCanonical.sha256 -MaterializedPairs $materializedPairs
    }
    catch {
        $receiptReadControlFailure = $true
        throw
    }
    $testDisposition = Get-E2TestDisposition -Receipt $receipt
    $captureText = [Text.Encoding]::UTF8.GetString($stdoutBytes) + [Text.Encoding]::UTF8.GetString($stderrBytes)
    $disposition = $testDisposition
    $exitCode = if ($nativeExit -ge 0 -and $nativeExit -le 255) { $nativeExit } else { $ExitRunnerBlocked }
    if ($activeProcessViolation) { $disposition = "U24_E2_RUNNER_BLOCKED"; $exitCode = $ExitRunnerBlocked }
    elseif ($wallExpired) { $disposition = "U24_E2_RESOURCE_OR_SCOPE_BLOCKED"; $exitCode = $ExitTimeout }
    elseif ($outputObserved) { $disposition = "U24_E2_RESOURCE_OR_SCOPE_BLOCKED"; $exitCode = $ExitOutput }
    elseif ($memoryObserved) { $disposition = "U24_E2_RESOURCE_OR_SCOPE_BLOCKED"; $exitCode = $ExitMemory }
    elseif (-not $pumpsComplete -or -not $jobFinalStateObserved) { $disposition = "U24_E2_RUNNER_BLOCKED"; $exitCode = $ExitRunnerBlocked }
    elseif ($nativeExit -ne 0 -and $captureText.Contains("MemoryError")) { $disposition = "U24_E2_RESOURCE_OR_SCOPE_BLOCKED" }
    elseif ($receipt.status -cne "VALID") { $disposition = "U24_E2_RUNNER_BLOCKED"; $exitCode = $ExitRunnerBlocked }
    elseif ($nativeExit -ne [int]$receipt.pytest_exit) { $disposition = "U24_E2_RUNNER_BLOCKED"; $exitCode = $ExitRunnerBlocked }
    else {
        if ($testDisposition -ceq "U24_E2_ENDPOINT_LOCAL_QUALIFIED") {
            if ($elapsedTicks -gt $QualificationTicks -or [int64](3 * $elapsedTicks) -gt $WallTicks) {
                $disposition = "U24_E2_RESOURCE_OR_SCOPE_BLOCKED"
                $exitCode = $ExitQualificationMargin
            }
            else { $exitCode = 0 }
        }
    }
    if ($disposition -cne "U24_E2_ENDPOINT_LOCAL_QUALIFIED" -and $exitCode -eq 0) {
        $exitCode = $ExitRunnerBlocked
    }
    if (-not $pumpsComplete -or -not $captureWritersClosed -or -not $jobFinalStateObserved) {
        throw "exact outer report withheld because Job-final-state/pump-EOF prerequisites were not established"
    }
    Write-E2ChildCaptures -StdoutBytes $stdoutBytes -StderrBytes $stderrBytes -StdoutEmitted ([ref]$stdoutCaptureEmitted) -StderrEmitted ([ref]$stderrCaptureEmitted)

    $cleanupComplete = $true
    if ($receipt.status -cne "VALID") {
        $preserveInvalidEvidence = $true
        $cleanupComplete = $false
        [Console]::Error.WriteLine("U24_E2_NONVALID_RECEIPT_EVIDENCE_ROOT={0}", $runRoot)
    }
    else { try {
        $resolvedRunRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $runRoot).ProviderPath)
        if (-not [IO.Path]::GetFullPath((Split-Path -Parent $resolvedRunRoot)).TrimEnd('\').Equals($systemTemp, [StringComparison]::OrdinalIgnoreCase)) {
            throw "refusing cleanup outside frozen system temp"
        }
        if (-not [IO.Path]::GetFileName($resolvedRunRoot).StartsWith("lean-rgc-u24-e2-", [StringComparison]::Ordinal)) {
            throw "refusing cleanup of unowned leaf"
        }
        Remove-Item -LiteralPath $resolvedRunRoot -Recurse -Force
        $runRoot = $null
    }
    catch {
        $preserveInvalidEvidence = $true
        $cleanupComplete = $false
        $disposition = "U24_E2_RUNNER_BLOCKED"
        $exitCode = $ExitRunnerBlocked
        Write-RunnerError ("owned temporary cleanup failed; preserving run root: " + $_.Exception.Message)
    }
    }

    $outerPayload = [ordered]@{
        schema_version = $OuterReportSchema
        lane = $Lane
        authority_commit = $AuthorityCommit
        authority_tree = $AuthorityTree
        authority_document_blob = $AuthorityDocumentBlob
        source_commit = $SemanticCommit
        source_tree = $SemanticTree
        runner_commit = $runnerCommitObserved
        runner_tree = $runnerTreeObserved
        pre_run_manifest_sha256 = $preRunCanonical.sha256
        attempt_marker_sha256 = $attemptCanonical.sha256
        child_receipt_status = $receipt.status
        child_receipt_payload = $receipt.payload
        child_receipt_parse_error = $receipt.parse_error
        child_receipt_byte_length = $receipt.byte_length
        child_receipt_sha256 = $receipt.sha256
        native_process_exit = $nativeExit
        child_pytest_exit = $receipt.pytest_exit
        elapsed_ticks = $elapsedTicks
        clock_frequency = $StopwatchFrequency
        peak_job_memory_bytes = $peakJobMemory
        stdout_retained_bytes = [int64]$stdoutBytes.Length
        stderr_retained_bytes = [int64]$stderrBytes.Length
        stdout_dropped_bytes = $stdoutDropped
        stderr_dropped_bytes = $stderrDropped
        wall_expired = [bool]$wallExpired
        memory_limit_observed = [bool]$memoryObserved
        output_limit_observed = [bool]$outputObserved
        test_module_materialized_sha256 = $materializedPairs["tests/test_odlrq_selection.py"].raw_sha256
        test_module_git_blob = $SemanticBlobs["tests/test_odlrq_selection.py"]
        runner_checkout_raw_sha256 = $runnerRawSha256
        runner_git_blob = $runnerBlobObserved
        certificates_materialized_sha256 = $materializedPairs["lean_rgc/odlrq/certificates.py"].raw_sha256
        certificates_git_blob = $SemanticBlobs["lean_rgc/odlrq/certificates.py"]
        selection_materialized_sha256 = $materializedPairs["lean_rgc/odlrq/selection.py"].raw_sha256
        selection_git_blob = $SemanticBlobs["lean_rgc/odlrq/selection.py"]
        tier_manifest_materialized_sha256 = $materializedPairs["tests/tier_manifest.json"].raw_sha256
        tier_manifest_git_blob = $SemanticBlobs["tests/tier_manifest.json"]
        cleanup_complete = [bool]$cleanupComplete
        disposition = $disposition
    }
    $ephemeralOuterPath = Join-Path $systemTemp ("lean-rgc-u24-e2-ephemeral-outer-" + [Guid]::NewGuid().ToString("N") + ".json")
    $outerCanonical = Test-EphemeralCanonicalPayload -LiteralPath $ephemeralOuterPath -Payload $outerPayload
    Write-CanonicalConsoleRecord -Label "U24_E2_OUTER_EXECUTION_REPORT" -Canonical $outerCanonical
    $outerReportEmitted = $true
}
catch {
    $failureRecord = $_
    $diagnosticDisposition = "U24_E2_RUNNER_BLOCKED"
    try {
        $taggedDisposition = $failureRecord.Exception.Data["u24_e2_failure_disposition"]
        if ($taggedDisposition -is [string] -and $taggedDisposition -ceq "U24_E2_SOURCE_FREEZE_BLOCKED") {
            $diagnosticDisposition = $taggedDisposition
        }
    }
    catch { }
    $exitCode = $ExitRunnerBlocked
    $recoveryErrors = [Collections.Generic.List[string]]::new()

    if ($attemptMarkerWriteStarted -and -not $attemptMarkerConsumed) {
        if ($null -eq $attemptMarkerPath) {
            $recoveryErrors.Add("attempt-marker latch adjudication is ambiguous because its path is unavailable")
        }
        else {
            try {
                $markerFullPath = [IO.Path]::GetFullPath($attemptMarkerPath)
                $markerParent = [IO.Path]::GetDirectoryName($markerFullPath)
                $markerLeaf = [IO.Path]::GetFileName($markerFullPath)
                Assert-NonReparsePath -LiteralPath $markerParent
                $matchingMarkerEntries = @(
                    [IO.Directory]::EnumerateFileSystemEntries($markerParent) | Where-Object {
                        [IO.Path]::GetFileName($_).Equals($markerLeaf, [StringComparison]::OrdinalIgnoreCase)
                    }
                )
                if ($matchingMarkerEntries.Count -eq 0) {
                    $attemptMarkerAbsenceAdjudicated = $true
                }
                elseif ($matchingMarkerEntries.Count -ne 1) {
                    throw "multiple case-insensitive attempt-marker entries were observed"
                }
                else {
                    $observedMarkerPath = [IO.Path]::GetFullPath($matchingMarkerEntries[0])
                    $observedMarkerLeaf = [IO.Path]::GetFileName($observedMarkerPath)
                    if (-not $observedMarkerLeaf.Equals($markerLeaf, [StringComparison]::Ordinal)) {
                        throw "attempt-marker leaf casing is not exact"
                    }
                    $observedMarkerAttributes = [IO.File]::GetAttributes($observedMarkerPath)
                    if (($observedMarkerAttributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                        throw "attempt marker is a reparse point"
                    }
                    if (
                        ($observedMarkerAttributes -band [IO.FileAttributes]::Directory) -ne 0 -or
                        -not (Test-Path -LiteralPath $observedMarkerPath -PathType Leaf)
                    ) {
                        throw "attempt marker is not a regular leaf"
                    }
                    $attemptMarkerConsumed = $true
                }
            }
            catch { $recoveryErrors.Add("attempt-marker latch adjudication is ambiguous: " + $_.Exception.Message) }
        }
    }
    $markerStateAmbiguous = [bool](
        $attemptMarkerWriteStarted -and -not $attemptMarkerConsumed -and -not $attemptMarkerAbsenceAdjudicated
    )
    $markerEvidenceMustBePreserved = [bool]($attemptMarkerConsumed -or $markerStateAmbiguous)
    if ($markerEvidenceMustBePreserved) {
        if ($null -ne $runRoot) {
            $preserveInvalidEvidence = $true
            $cleanupComplete = $false
        }
    }
    if ($null -eq $jobMessages) { $jobMessages = [Collections.Generic.List[uint32]]::new() }

    if ($null -ne $scientificSession) {
        $sessionExited = $false
        if ($childStarted) {
            try { $scientificSession.Terminate([uint32]$ExitRunnerBlocked) }
            catch { $recoveryErrors.Add("owned Job termination failed: " + $_.Exception.Message) }
            try { $sessionExited = [bool]$scientificSession.Wait(2000) }
            catch { $recoveryErrors.Add("owned process wait failed: " + $_.Exception.Message) }
            if (-not $sessionExited) {
                try { $scientificSession.Terminate([uint32]$ExitRunnerBlocked) }
                catch { $recoveryErrors.Add("second owned Job termination failed: " + $_.Exception.Message) }
                try { $sessionExited = [bool]$scientificSession.Wait(2000) }
                catch { $recoveryErrors.Add("second owned process wait failed: " + $_.Exception.Message) }
            }
        }
        try { foreach ($message in $scientificSession.DrainJobMessages()) { $jobMessages.Add([uint32]$message) } }
        catch { $recoveryErrors.Add("Job message drain failed: " + $_.Exception.Message) }
        if ($sessionExited) {
            for ($completionPoll = 0; $completionPoll -lt 80 -and @($jobMessages | Where-Object { $_ -eq 4 }).Count -eq 0; $completionPoll++) {
                Start-Sleep -Milliseconds $PollMilliseconds
                try { foreach ($message in $scientificSession.DrainJobMessages()) { $jobMessages.Add([uint32]$message) } }
                catch { $recoveryErrors.Add("Job final-state drain failed: " + $_.Exception.Message); break }
            }
            try { $nativeExit = [int]$scientificSession.ExitCode }
            catch { $recoveryErrors.Add("native exit-code recovery failed: " + $_.Exception.Message) }
        }
        try { $peakJobMemory = [uint64]$scientificSession.PeakJobMemory() }
        catch { $recoveryErrors.Add("peak Job memory recovery failed: " + $_.Exception.Message) }
        try { $pumpsComplete = [bool]$scientificSession.FinishPumps(2000) }
        catch { $pumpsComplete = $false; $recoveryErrors.Add("capture pump finalization failed: " + $_.Exception.Message) }
        try { $captureWritersClosed = [bool]$scientificSession.CaptureWritersClosed }
        catch { $captureWritersClosed = $false; $recoveryErrors.Add("capture-writer close adjudication failed: " + $_.Exception.Message) }
        try { $stdoutDropped = [int64]$scientificSession.StdoutDropped }
        catch { $recoveryErrors.Add("stdout drop telemetry failed: " + $_.Exception.Message) }
        try { $stderrDropped = [int64]$scientificSession.StderrDropped }
        catch { $recoveryErrors.Add("stderr drop telemetry failed: " + $_.Exception.Message) }
        try { if ($scientificSession.OutputExceeded) { $outputObserved = $true } }
        catch { $recoveryErrors.Add("output-limit telemetry failed: " + $_.Exception.Message) }
        if ($captureWritersClosed) {
            try {
                $stdoutBytes = $scientificSession.ReadStdout()
                $stderrBytes = $scientificSession.ReadStderr()
            }
            catch {
                $stdoutBytes = $null
                $stderrBytes = $null
                $recoveryErrors.Add("closed capture read failed: " + $_.Exception.Message)
            }
        }
        try { $scientificSession.CloseJob() }
        catch { $recoveryErrors.Add("owned Job close failed: " + $_.Exception.Message) }
        try { $scientificSession.Dispose() }
        catch { $recoveryErrors.Add("scientific session disposal failed: " + $_.Exception.Message) }
        $scientificSession = $null
        $scientificProcess = $null
    }
    elseif ($null -ne $scientificProcess) {
        try {
            if ($childStarted -and -not $scientificProcess.HasExited) {
                $scientificProcess.Kill()
                [void]$scientificProcess.WaitForExit(2000)
            }
            if ($childStarted -and $scientificProcess.HasExited) { $nativeExit = [int]$scientificProcess.ExitCode }
        }
        catch { $recoveryErrors.Add("unattached scientific process recovery failed: " + $_.Exception.Message) }
        try { $scientificProcess.Dispose() }
        catch { $recoveryErrors.Add("unattached scientific process disposal failed: " + $_.Exception.Message) }
        $scientificProcess = $null
    }
    if ($null -ne $clock) {
        try {
            if ($clock.IsRunning) { $clock.Stop() }
            $elapsedTicks = [int64]$clock.ElapsedTicks
        }
        catch { $recoveryErrors.Add("monotonic clock recovery failed: " + $_.Exception.Message) }
    }
    if ($null -ne $elapsedTicks -and $elapsedTicks -ge $WallTicks) { $wallExpired = $true }
    $jobFinalStateObserved = @($jobMessages | Where-Object { $_ -eq 4 }).Count -gt 0
    $memoryObserved = @($jobMessages | Where-Object { $_ -in @(9, 10) }).Count -gt 0
    $activeProcessViolation = @($jobMessages | Where-Object { $_ -eq 3 }).Count -gt 0
    if (($null -ne $stdoutDropped -and $stdoutDropped -ne 0) -or ($null -ne $stderrDropped -and $stderrDropped -ne 0)) {
        $outputObserved = $true
    }

    if ($null -ne $held) {
        foreach ($handle in $held.handles) {
            try { $handle.Dispose() }
            catch { $recoveryErrors.Add("held source/runtime handle close failed: " + $_.Exception.Message) }
        }
        $held = $null
    }
    if ($null -ne $bootstrapHandle) {
        try { $bootstrapHandle.Dispose() }
        catch { $recoveryErrors.Add("bootstrap handle close failed: " + $_.Exception.Message) }
        $bootstrapHandle = $null
    }
    foreach ($identity in @($gitExecutableIdentity, $powerShellExecutableIdentity)) {
        if ($null -ne $identity -and -not [bool]$identity.closed) {
            try { Close-And-AdjudicateHeldExecutableIdentity -Identity $identity }
            catch { $recoveryErrors.Add("named executable hold close failed: " + $_.Exception.Message) }
        }
    }
    if ($null -ne $pythonExecutableIdentity -and -not [bool]$pythonExecutableIdentity.closed) {
        if (-not $childStarted -or $null -ne $nativeExit) {
            try { Close-And-AdjudicateHeldExecutableIdentity -Identity $pythonExecutableIdentity }
            catch { $recoveryErrors.Add("Python executable hold close failed: " + $_.Exception.Message) }
        }
        else {
            $recoveryErrors.Add("Python executable hold retained because child exit was not established")
        }
    }

    $finalStatePrerequisites = [bool](
        $childStarted -and $null -ne $nativeExit -and $jobFinalStateObserved -and
        $pumpsComplete -and $captureWritersClosed -and
        $null -ne $stdoutBytes -and $null -ne $stderrBytes
    )
    if ($finalStatePrerequisites) {
        try {
            Write-E2ChildCaptures -StdoutBytes $stdoutBytes -StderrBytes $stderrBytes -StdoutEmitted ([ref]$stdoutCaptureEmitted) -StderrEmitted ([ref]$stderrCaptureEmitted)
        }
        catch { $recoveryErrors.Add("child capture console emission failed: " + $_.Exception.Message) }
    }
    else { $recoveryErrors.Add("frozen final-state/EOF prerequisites were not established") }

    $attemptMarkerSha = if ($null -eq $attemptCanonical) { $null } else { $attemptCanonical.sha256 }
    if ($null -eq $attemptMarkerSha -and $attemptMarkerConsumed -and $null -ne $attemptMarkerPath) {
        try {
            if (Test-Path -LiteralPath $attemptMarkerPath -PathType Leaf) {
                $markerItem = Get-Item -LiteralPath $attemptMarkerPath -Force
                if (($markerItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "attempt marker became a reparse point" }
                if ($markerItem.Length -gt $ReceiptLimitBytes) { throw "attempt marker exceeds evidence cap" }
                $attemptMarkerSha = Get-Sha256File -LiteralPath $attemptMarkerPath
            }
        }
        catch { $recoveryErrors.Add("attempt-marker identity recovery failed: " + $_.Exception.Message) }
    }
    $materializedIdentitiesComplete = $null -ne $materializedPairs
    if ($materializedIdentitiesComplete) {
        foreach ($path in $SemanticPaths) {
            if (-not $materializedPairs.Contains($path) -or $null -eq $materializedPairs[$path].raw_sha256) {
                $materializedIdentitiesComplete = $false
                break
            }
        }
    }
    $receiptIdentityPrerequisites = [bool](
        $null -ne $receiptPath -and $null -ne $runnerCommitObserved -and $null -ne $runnerTreeObserved -and
        $null -ne $preRunCanonical -and $null -ne $attemptMarkerSha -and $materializedIdentitiesComplete
    )
    if ($null -eq $receipt) {
        if ($receiptReadControlFailure) {
            $recoveryErrors.Add("child receipt control failure forbids fallback reinterpretation")
        }
        elseif ($receiptIdentityPrerequisites) {
            $receiptReadAttempted = $true
            try {
                $receipt = Read-E2ChildReceipt -ReceiptPath $receiptPath -RunnerCommit $runnerCommitObserved -RunnerTree $runnerTreeObserved -ManifestSha $preRunCanonical.sha256 -MarkerSha $attemptMarkerSha -MaterializedPairs $materializedPairs
            }
            catch {
                $receiptReadControlFailure = $true
                $recoveryErrors.Add("exact child receipt adjudication failed: " + $_.Exception.Message)
            }
        }
        else { $recoveryErrors.Add("frozen child receipt identities are unavailable") }
    }

    $blockedOuterPrerequisites = [bool](
        $attemptMarkerConsumed -and $finalStatePrerequisites -and $receiptIdentityPrerequisites -and
        -not $receiptReadControlFailure -and $null -ne $receipt -and $null -ne $systemTemp
    )
    if ($blockedOuterPrerequisites) {
        $blockedOuterPayload = [ordered]@{
            schema_version = $OuterReportSchema
            lane = $Lane
            authority_commit = $AuthorityCommit
            authority_tree = $AuthorityTree
            authority_document_blob = $AuthorityDocumentBlob
            source_commit = $SemanticCommit
            source_tree = $SemanticTree
            runner_commit = $runnerCommitObserved
            runner_tree = $runnerTreeObserved
            pre_run_manifest_sha256 = $preRunCanonical.sha256
            attempt_marker_sha256 = $attemptMarkerSha
            child_receipt_status = $receipt.status
            child_receipt_payload = $receipt.payload
            child_receipt_parse_error = $receipt.parse_error
            child_receipt_byte_length = $receipt.byte_length
            child_receipt_sha256 = $receipt.sha256
            native_process_exit = $nativeExit
            child_pytest_exit = $receipt.pytest_exit
            elapsed_ticks = $elapsedTicks
            clock_frequency = $StopwatchFrequency
            peak_job_memory_bytes = $peakJobMemory
            stdout_retained_bytes = [int64]$stdoutBytes.Length
            stderr_retained_bytes = [int64]$stderrBytes.Length
            stdout_dropped_bytes = $stdoutDropped
            stderr_dropped_bytes = $stderrDropped
            wall_expired = [bool]$wallExpired
            memory_limit_observed = [bool]$memoryObserved
            output_limit_observed = [bool]$outputObserved
            test_module_materialized_sha256 = $materializedPairs["tests/test_odlrq_selection.py"].raw_sha256
            test_module_git_blob = $SemanticBlobs["tests/test_odlrq_selection.py"]
            runner_checkout_raw_sha256 = $runnerRawSha256
            runner_git_blob = $runnerBlobObserved
            certificates_materialized_sha256 = $materializedPairs["lean_rgc/odlrq/certificates.py"].raw_sha256
            certificates_git_blob = $SemanticBlobs["lean_rgc/odlrq/certificates.py"]
            selection_materialized_sha256 = $materializedPairs["lean_rgc/odlrq/selection.py"].raw_sha256
            selection_git_blob = $SemanticBlobs["lean_rgc/odlrq/selection.py"]
            tier_manifest_materialized_sha256 = $materializedPairs["tests/tier_manifest.json"].raw_sha256
            tier_manifest_git_blob = $SemanticBlobs["tests/tier_manifest.json"]
            cleanup_complete = [bool]$cleanupComplete
            disposition = "U24_E2_RUNNER_BLOCKED"
        }
        $outerPath = Join-Path $systemTemp ("lean-rgc-u24-e2-outer-failure-" + [Guid]::NewGuid().ToString("N") + ".json")
        try {
            $outerCanonical = Write-ExclusiveCanonicalFile -LiteralPath $outerPath -Payload $blockedOuterPayload
            $failureOuterCreated = $true
        }
        catch { $recoveryErrors.Add("blocked outer report creation failed: " + $_.Exception.Message) }
        if ($failureOuterCreated) {
            try {
                Write-CanonicalConsoleRecord -Label "U24_E2_OUTER_EXECUTION_REPORT" -Canonical $outerCanonical
                $outerReportEmitted = $true
            }
            catch { $recoveryErrors.Add("blocked outer console emission failed: " + $_.Exception.Message) }
        }
    }

    if (-not $outerReportEmitted) {
        $outerArtifactPresent = $false
        $outerArtifactByteLength = $null
        $outerArtifactSha256 = $null
        if ($null -ne $outerPath) {
            try {
                $outerArtifactPresent = Test-Path -LiteralPath $outerPath -PathType Leaf
                if ($outerArtifactPresent) {
                    $outerArtifactItem = Get-Item -LiteralPath $outerPath -Force
                    if (($outerArtifactItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) {
                        $outerArtifactByteLength = [int64]$outerArtifactItem.Length
                        $outerArtifactSha256 = Get-Sha256File -LiteralPath $outerPath
                    }
                }
            }
            catch { $recoveryErrors.Add("blocked outer artifact adjudication failed: " + $_.Exception.Message) }
        }
        $attemptMarkerPresent = if ($attemptMarkerConsumed -or $null -ne $existingMarkerEvidence) { $true } elseif ($attemptMarkerAbsenceAdjudicated) { $false } else { $null }
        $runRootPresent = $false
        if ($markerEvidenceMustBePreserved -and $null -ne $runRoot) {
            try { $runRootPresent = Test-Path -LiteralPath $runRoot -PathType Container }
            catch { $recoveryErrors.Add("diagnostic run-root check failed: " + $_.Exception.Message) }
        }
        $diagnosticErrorMessage = $failureRecord.Exception.Message
        if ($recoveryErrors.Count -ne 0) {
            $diagnosticErrorMessage += " | recovery: " + [string]::Join(" | ", @($recoveryErrors.ToArray()))
        }
        $diagnostic = [ordered]@{
            schema_version = "u24-e2-runner-diagnostic-v1"
            lane = $Lane
            authority_commit = $AuthorityCommit
            source_commit = $SemanticCommit
            runner_commit = $runnerCommitObserved
            runner_tree = $runnerTreeObserved
            pre_run_manifest_sha256 = if ($null -eq $preRunCanonical) { $null } else { $preRunCanonical.sha256 }
            attempt_marker_present = $attemptMarkerPresent
            child_started = [bool]$childStarted
            run_root_preserved = [bool]$runRootPresent
            run_root = if ($markerEvidenceMustBePreserved) { $runRoot } else { $null }
            attempt_marker_path = if ($markerEvidenceMustBePreserved) { $attemptMarkerPath } else { $null }
            outer_report_preserved = [bool]$outerArtifactPresent
            outer_report_path = if ($outerArtifactPresent) { $outerPath } else { $null }
            outer_report_byte_length = $outerArtifactByteLength
            outer_report_sha256 = $outerArtifactSha256
            existing_marker_evidence = $existingMarkerEvidence
            control_pipe_escape = [bool]$script:ControlPipeEscapeObserved
            error_type = $failureRecord.Exception.GetType().FullName
            error_message = $diagnosticErrorMessage
            disposition = $diagnosticDisposition
        }
        try {
            $diagnosticCanonical = Get-CanonicalPayload -Value $diagnostic
            Write-CanonicalConsoleRecord -Label "U24_E2_RUNNER_DIAGNOSTIC" -Canonical $diagnosticCanonical
        }
        catch { Write-RunnerError "failed to emit bounded runner diagnostic" }
    }
}
finally {
    if (
        -not $outerReportEmitted -and -not $attemptMarkerConsumed -and
        (-not $attemptMarkerWriteStarted -or $attemptMarkerAbsenceAdjudicated)
    ) {
        if ($null -ne $scientificSession) {
            try { $scientificSession.Terminate([uint32]$ExitRunnerBlocked) } catch { }
            try { [void]$scientificSession.Wait(2000) } catch { }
            try { $scientificSession.Dispose() } catch { }
        }
        elseif ($null -ne $scientificProcess) {
            try { if (-not $scientificProcess.HasExited) { $scientificProcess.Kill(); [void]$scientificProcess.WaitForExit(2000) } } catch { }
            try { $scientificProcess.Dispose() } catch { }
        }
        if ($null -ne $held) { foreach ($handle in $held.handles) { try { $handle.Dispose() } catch { } } }
        if ($null -ne $bootstrapHandle) { try { $bootstrapHandle.Dispose() } catch { } }
        foreach ($identity in @($gitExecutableIdentity, $pythonExecutableIdentity, $powerShellExecutableIdentity)) {
            if ($null -ne $identity -and -not [bool]$identity.closed) {
                try { Close-And-AdjudicateHeldExecutableIdentity -Identity $identity } catch { }
            }
        }
        if (-not $attemptMarkerConsumed -and $null -ne $runRoot) {
            try {
                if (Test-Path -LiteralPath $runRoot -PathType Container) {
                    $resolved = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $runRoot).ProviderPath)
                    if (
                        $null -ne $systemTemp -and
                        [IO.Path]::GetFullPath((Split-Path -Parent $resolved)).TrimEnd('\').Equals($systemTemp, [StringComparison]::OrdinalIgnoreCase) -and
                        [IO.Path]::GetFileName($resolved).StartsWith("lean-rgc-u24-e2-", [StringComparison]::Ordinal)
                    ) { Remove-Item -LiteralPath $resolved -Recurse -Force }
                }
            }
            catch { }
        }
    }
}

exit $exitCode
