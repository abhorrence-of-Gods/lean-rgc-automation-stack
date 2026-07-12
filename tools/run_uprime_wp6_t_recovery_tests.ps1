[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [object[]] $UnexpectedArguments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ExitUsage = 64
$ExitUnsafeEnvironment = 65
$ExitNoTest = 66
$ExitPythonUnavailable = 69
$ExitInternalError = 70
$ExitTimeout = 124
$ExitQualificationMargin = 125
$ExitWorkingSet = 137
$ExitOutputLimit = 138
$WallLimitSeconds = 30.0
$QualificationMarginSeconds = 10.0
$WorkingSetLimitBytes = [int64]2 * 1024 * 1024 * 1024
$OutputLimitBytes = [int64]64 * 1024 * 1024
$TempPrefix = "lean-rgc-uprime-wp6t-recovery-"
$FrozenTest = "tests/test_odlrq_quotient_generator.py"

function Write-RunnerError {
    param([Parameter(Mandatory = $true)][string] $Message)
    [Console]::Error.WriteLine("uprime-wp6t-recovery: {0}", $Message)
}

function Resolve-RegularFile {
    param(
        [Parameter(Mandatory = $true)][string] $LiteralPath,
        [Parameter(Mandatory = $true)][string] $RequiredRoot
    )

    $item = Get-Item -LiteralPath $LiteralPath -Force
    if ($item.PSIsContainer) {
        throw "expected a regular file: $LiteralPath"
    }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "reparse-point inputs are forbidden: $LiteralPath"
    }
    $resolved = [IO.Path]::GetFullPath($item.FullName)
    $rootPrefix = [IO.Path]::GetFullPath($RequiredRoot).TrimEnd("\", "/") + [IO.Path]::DirectorySeparatorChar
    if (-not $resolved.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "resolved file escaped its required root: $LiteralPath"
    }
    return $resolved
}

function Quote-NativeArgument {
    param([Parameter(Mandatory = $true)][string] $Value)

    if ($Value.IndexOf([char]0) -ge 0 -or $Value.Contains("`r") -or $Value.Contains("`n")) {
        throw "native argument contains a forbidden control character"
    }
    if ($Value.Contains('"')) {
        throw "native argument contains a quote"
    }
    if ($Value.EndsWith("\") -or $Value.EndsWith("/")) {
        throw "native argument may not end in a directory separator"
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

    if (-not (Test-Path -LiteralPath $LiteralPath -PathType Leaf)) {
        return
    }
    $item = Get-Item -LiteralPath $LiteralPath -Force
    if ($item.Length -ge $OutputLimitBytes) {
        [Console]::Error.WriteLine(
            "uprime-wp6t-recovery: captured {0} omitted after output cap",
            $Stream
        )
        return
    }
    $content = [IO.File]::ReadAllText($LiteralPath, [Text.Encoding]::UTF8)
    if ($content.Length -eq 0) {
        return
    }
    if ($Stream -eq "stdout") {
        [Console]::Out.Write($content)
    }
    else {
        [Console]::Error.Write($content)
    }
}

$unboundCount = if ($null -eq $MyInvocation.UnboundArguments) {
    0
}
else {
    @($MyInvocation.UnboundArguments).Count
}
$unexpectedCount = if ($null -eq $UnexpectedArguments) {
    0
}
else {
    @($UnexpectedArguments).Count
}
if ($PSBoundParameters.Count -ne 0 -or $unboundCount -ne 0 -or $unexpectedCount -ne 0) {
    Write-RunnerError "arguments are forbidden"
    exit $ExitUsage
}

if ($env:OS -ne "Windows_NT") {
    Write-RunnerError "this runner is restricted to Windows"
    exit $ExitUnsafeEnvironment
}

$runTemp = $null
$stdoutPath = $null
$stderrPath = $null
$exitReceiptPath = $null
$pythonProcess = $null
$pythonProcessHandle = $null
$capturedWritten = $false
$exitCode = $ExitInternalError
$requestedExitCode = $null
$processExitCode = $null
$receiptExitCode = $null

try {
    if ([string]::IsNullOrWhiteSpace($PSCommandPath)) {
        throw "script path is unavailable"
    }
    $scriptPath = Resolve-RegularFile -LiteralPath $PSCommandPath -RequiredRoot (Split-Path -Parent $PSCommandPath)
    $toolsPath = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Split-Path -Parent $scriptPath)).ProviderPath)
    if ([IO.Path]::GetFileName($toolsPath) -cne "tools") {
        throw "runner is not located in the repository tools directory"
    }

    $repoRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Join-Path $toolsPath "..")).ProviderPath)
    $expectedScript = [IO.Path]::GetFullPath((Join-Path $repoRoot "tools\run_uprime_wp6_t_recovery_tests.ps1"))
    if (-not $scriptPath.Equals($expectedScript, [StringComparison]::OrdinalIgnoreCase)) {
        throw "runner path does not match the canonical repository location"
    }
    foreach ($marker in @(".git", "pyproject.toml", "lean_rgc", "tests")) {
        if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $marker))) {
            throw "repository marker is missing: $marker"
        }
    }

    $testsRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Join-Path $repoRoot "tests")).ProviderPath)
    $testCandidate = [IO.Path]::GetFullPath((Join-Path $repoRoot $FrozenTest))
    if (-not (Test-Path -LiteralPath $testCandidate -PathType Leaf)) {
        Write-RunnerError "the one frozen WP6-T test module is missing"
        $requestedExitCode = $ExitNoTest
        throw [OperationCanceledException]::new("fail-closed runner exit")
    }
    $testPath = Resolve-RegularFile -LiteralPath $testCandidate -RequiredRoot $testsRoot
    if (-not $testPath.Equals($testCandidate, [StringComparison]::OrdinalIgnoreCase)) {
        throw "frozen test path resolved unexpectedly"
    }

    $pythonCommand = Get-Command python.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1
    if ($null -eq $pythonCommand -or [string]::IsNullOrWhiteSpace($pythonCommand.Source)) {
        Write-RunnerError "python.exe is unavailable"
        $requestedExitCode = $ExitPythonUnavailable
        throw [OperationCanceledException]::new("fail-closed runner exit")
    }
    $pythonPath = Resolve-RegularFile -LiteralPath $pythonCommand.Source -RequiredRoot (Split-Path -Parent $pythonCommand.Source)
    if ([IO.Path]::GetExtension($pythonPath) -ine ".exe") {
        throw "resolved Python command is not an executable"
    }

    $systemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd("\", "/")
    $runTemp = [IO.Path]::GetFullPath((Join-Path $systemTemp ($TempPrefix + [Guid]::NewGuid().ToString("N"))))
    $expectedTempParent = [IO.Path]::GetFullPath((Split-Path -Parent $runTemp)).TrimEnd("\", "/")
    if (-not $expectedTempParent.Equals($systemTemp, [StringComparison]::OrdinalIgnoreCase)) {
        throw "owned temporary directory escaped the system temp root"
    }
    if (-not ([IO.Path]::GetFileName($runTemp)).StartsWith($TempPrefix, [StringComparison]::Ordinal)) {
        throw "owned temporary directory has an invalid name"
    }
    if (Test-Path -LiteralPath $runTemp) {
        throw "owned temporary directory already exists"
    }
    [void][IO.Directory]::CreateDirectory($runTemp)

    $stdoutPath = Join-Path $runTemp "pytest.stdout.txt"
    $stderrPath = Join-Path $runTemp "pytest.stderr.txt"
    $pytestTemp = Join-Path $runTemp "pytest-tmp"
    $exitReceiptPath = Join-Path $runTemp "pytest.exit.txt"
    $bootstrapPath = Join-Path $runTemp "forbid_subprocess_and_run_pytest.py"
    $bootstrap = @'
import asyncio
import multiprocessing.process
import nt
import os
import subprocess
import sys


def _deny_subprocess(*_args, **_kwargs):
    raise RuntimeError("WP6-T semantic tests may not spawn subprocesses")


for _name in (
    "Popen", "run", "call", "check_call", "check_output",
    "getoutput", "getstatusoutput",
):
    if hasattr(subprocess, _name):
        setattr(subprocess, _name, _deny_subprocess)

for _name in (
    "_exit", "execl", "execle", "execlp", "execlpe", "execv", "execve",
    "execvp", "execvpe", "startfile", "system", "popen", "spawnl",
    "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp",
    "spawnvpe",
):
    if hasattr(os, _name):
        setattr(os, _name, _deny_subprocess)
    if hasattr(nt, _name):
        setattr(nt, _name, _deny_subprocess)

asyncio.create_subprocess_exec = _deny_subprocess
asyncio.create_subprocess_shell = _deny_subprocess
multiprocessing.process.BaseProcess.start = _deny_subprocess

_receipt = os.environ.pop("UPRIME_WP6T_EXIT_RECEIPT", None)
if not _receipt:
    raise RuntimeError("owned pytest exit receipt path is unavailable")
import pytest

_exit_code = int(pytest.main(sys.argv[1:]))
with open(_receipt, "x", encoding="ascii", newline="\n") as _handle:
    _handle.write(f"{_exit_code}\n")
raise SystemExit(_exit_code)
'@
    [IO.File]::WriteAllText($bootstrapPath, $bootstrap, [Text.UTF8Encoding]::new($false))

    $env:PYTHONDONTWRITEBYTECODE = "1"
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    $env:PYTHONPATH = ""
    $env:PYTEST_ADDOPTS = ""
    $env:PYTEST_PLUGINS = ""
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
    $env:UPRIME_WP6T_SUBPROCESS_POLICY = "forbid"
    $env:UPRIME_WP6T_EXIT_RECEIPT = $exitReceiptPath

    $pythonArguments = [Collections.Generic.List[string]]::new()
    $pythonArguments.Add($bootstrapPath)
    $pythonArguments.Add("-p")
    $pythonArguments.Add("no:cacheprovider")
    $pythonArguments.Add("--basetemp")
    $pythonArguments.Add($pytestTemp)
    $pythonArguments.Add("-q")
    $pythonArguments.Add($FrozenTest)
    $nativeArgumentLine = (($pythonArguments | ForEach-Object { Quote-NativeArgument -Value $_ }) -join " ")

    $pythonProcess = Start-Process `
        -FilePath $pythonPath `
        -ArgumentList $nativeArgumentLine `
        -WorkingDirectory $repoRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath `
        -PassThru
    # Force System.Diagnostics.Process to retain its native handle.  Without
    # this access Windows PowerShell can report a null ExitCode after a manual
    # WaitForExit even though HasExited is true.
    $pythonProcessHandle = $pythonProcess.Handle

    $stopwatch = [Diagnostics.Stopwatch]::StartNew()
    $peakWorkingSetBytes = [int64]0
    $capFailure = $null
    while (-not $pythonProcess.HasExited) {
        Start-Sleep -Milliseconds 25
        $pythonProcess.Refresh()
        $peakWorkingSetBytes = [Math]::Max($peakWorkingSetBytes, $pythonProcess.WorkingSet64)
        if ($pythonProcess.HasExited) {
            break
        }
        if ($peakWorkingSetBytes -ge $WorkingSetLimitBytes) {
            $capFailure = "working_set"
            break
        }
        if ((Get-CapturedBytes -Paths @($stdoutPath, $stderrPath)) -ge $OutputLimitBytes) {
            $capFailure = "output_limit"
            break
        }
        if ($stopwatch.Elapsed.TotalSeconds -ge $WallLimitSeconds) {
            $capFailure = "timeout"
            break
        }
    }

    if ($null -ne $capFailure -and -not $pythonProcess.HasExited) {
        $pythonProcess.Kill()
    }
    $pythonProcess.WaitForExit()
    $pythonProcess.Refresh()
    $peakWorkingSetBytes = [Math]::Max($peakWorkingSetBytes, $pythonProcess.PeakWorkingSet64)
    try {
        $nativeExitCode = $pythonProcess.ExitCode
        if ($null -eq $nativeExitCode) {
            throw "native Python exit code is unavailable"
        }
        $processExitCode = [int]$nativeExitCode
    }
    catch {
        throw "native Python exit code is unavailable after process completion"
    }
    $stopwatch.Stop()

    if ($null -eq $capFailure) {
        if ($stopwatch.Elapsed.TotalSeconds -ge $WallLimitSeconds) {
            $capFailure = "timeout"
        }
        elseif ($peakWorkingSetBytes -ge $WorkingSetLimitBytes) {
            $capFailure = "working_set"
        }
        elseif ((Get-CapturedBytes -Paths @($stdoutPath, $stderrPath)) -ge $OutputLimitBytes) {
            $capFailure = "output_limit"
        }
        elseif ($processExitCode -lt 0 -or $processExitCode -gt 255) {
            throw "native Python exit code is outside the process exit range"
        }
        elseif (-not (Test-Path -LiteralPath $exitReceiptPath -PathType Leaf)) {
            throw "owned pytest exit receipt is missing after process completion"
        }
        else {
            $receiptItem = Get-Item -LiteralPath $exitReceiptPath -Force
            if (($receiptItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "owned pytest exit receipt may not be a reparse point"
            }
            $receiptResolved = [IO.Path]::GetFullPath($receiptItem.FullName)
            $expectedReceipt = [IO.Path]::GetFullPath($exitReceiptPath)
            if (-not $receiptResolved.Equals($expectedReceipt, [StringComparison]::OrdinalIgnoreCase)) {
                throw "owned pytest exit receipt resolved unexpectedly"
            }
            $receiptText = [IO.File]::ReadAllText($receiptResolved, [Text.Encoding]::ASCII)
            if ($receiptText -notmatch '^(0|[1-9][0-9]{0,2})\r?\n$') {
                throw "owned pytest exit receipt is malformed"
            }
            $receiptExitCode = [int]$Matches[1]
            if ($receiptExitCode -gt 255) {
                throw "owned pytest exit receipt is outside the process exit range"
            }
            if ($receiptExitCode -ne $processExitCode) {
                throw "owned pytest exit receipt disagrees with the native process exit"
            }
        }
    }

    if ($capFailure -ne "output_limit") {
        Write-CapturedStream -LiteralPath $stdoutPath -Stream stdout
        Write-CapturedStream -LiteralPath $stderrPath -Stream stderr
    }
    $capturedWritten = $true

    if ($capFailure -eq "timeout") {
        Write-RunnerError "30-second hard wall exceeded; Python was terminated"
        $exitCode = $ExitTimeout
    }
    elseif ($capFailure -eq "working_set") {
        Write-RunnerError "2-GiB parent working-set limit reached; Python was terminated"
        $exitCode = $ExitWorkingSet
    }
    elseif ($capFailure -eq "output_limit") {
        Write-RunnerError "64-MiB captured-output limit reached; Python was terminated"
        $exitCode = $ExitOutputLimit
    }
    elseif ($processExitCode -ne 0) {
        $exitCode = $processExitCode
    }
    elseif ($stopwatch.Elapsed.TotalSeconds -gt $QualificationMarginSeconds) {
        Write-RunnerError (
            "10-second qualification margin exceeded ({0:N3} seconds); hard wall unchanged" -f `
                $stopwatch.Elapsed.TotalSeconds
        )
        $exitCode = $ExitQualificationMargin
    }
    else {
        $qualificationMessage = (
            "uprime-wp6t-recovery: qualification elapsed={0:N3}s peak_working_set={1}" -f `
            $stopwatch.Elapsed.TotalSeconds, $peakWorkingSetBytes
        )
        [Console]::Out.WriteLine($qualificationMessage)
        $exitCode = 0
    }
}
catch [OperationCanceledException] {
    if ($null -eq $requestedExitCode) {
        Write-RunnerError $_.Exception.Message
        $exitCode = $ExitInternalError
    }
    else {
        $exitCode = $requestedExitCode
    }
}
catch [System.Management.Automation.CommandNotFoundException] {
    Write-RunnerError "python.exe is unavailable"
    $exitCode = $ExitPythonUnavailable
}
catch {
    Write-RunnerError $_.Exception.Message
    $exitCode = $ExitInternalError
}
finally {
    Remove-Item Env:UPRIME_WP6T_EXIT_RECEIPT -ErrorAction SilentlyContinue
    if ($null -ne $pythonProcess -and -not $pythonProcess.HasExited) {
        try {
            $pythonProcess.Kill()
            $pythonProcess.WaitForExit()
        }
        catch {
            Write-RunnerError "failed to terminate the owned Python process"
        }
    }
    if (-not $capturedWritten) {
        if ($null -ne $stdoutPath) {
            Write-CapturedStream -LiteralPath $stdoutPath -Stream stdout
        }
        if ($null -ne $stderrPath) {
            Write-CapturedStream -LiteralPath $stderrPath -Stream stderr
        }
    }
    if ($null -ne $runTemp -and (Test-Path -LiteralPath $runTemp)) {
        try {
            $resolvedCleanup = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $runTemp).ProviderPath)
            $cleanupParent = [IO.Path]::GetFullPath((Split-Path -Parent $resolvedCleanup)).TrimEnd("\", "/")
            $systemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd("\", "/")
            $cleanupLeaf = [IO.Path]::GetFileName($resolvedCleanup)
            if (
                -not $cleanupParent.Equals($systemTemp, [StringComparison]::OrdinalIgnoreCase) -or
                -not $cleanupLeaf.StartsWith($TempPrefix, [StringComparison]::Ordinal)
            ) {
                throw "refusing to clean an unowned path: $resolvedCleanup"
            }
            Remove-Item -LiteralPath $resolvedCleanup -Recurse -Force
        }
        catch {
            Write-RunnerError $_.Exception.Message
            if ($exitCode -eq 0) {
                $exitCode = $ExitInternalError
            }
        }
    }
}

exit $exitCode
