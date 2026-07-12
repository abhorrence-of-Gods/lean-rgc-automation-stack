[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [object[]] $UnexpectedArguments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ExitUsage = 64
$ExitUnsafeEnvironment = 65
$ExitNoTests = 66
$ExitPythonUnavailable = 69
$ExitInternalError = 70
$ExitTimeout = 124
$ExitWorkingSet = 137
$ExitOutputLimit = 138
$WallLimitSeconds = 300.0
$WorkingSetLimitBytes = [int64]2 * 1024 * 1024 * 1024
$OutputLimitBytes = [int64]64 * 1024 * 1024
$TempPrefix = "lean-rgc-uprime-cpu-survivor-"

function Write-RunnerError {
    param([Parameter(Mandatory = $true)][string] $Message)

    [Console]::Error.WriteLine("uprime-cpu-survivor: {0}", $Message)
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
    # Every argument used here is a file path, module flag, or fixed token and
    # none ends in a directory separator. Quoting every token avoids the
    # Start-Process string-array joining ambiguity on Windows PowerShell 5.1.
    if ($Value.EndsWith("\") -or $Value.EndsWith("/")) {
        throw "native argument may not end in a directory separator"
    }
    return '"' + $Value + '"'
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
            "uprime-cpu-survivor: captured {0} omitted after output cap",
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
$pythonProcess = $null
$capturedWritten = $false
$exitCode = $ExitInternalError
$requestedExitCode = $null

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
    $expectedScript = [IO.Path]::GetFullPath((Join-Path $repoRoot "tools\run_uprime_cpu_survivor_tests.ps1"))
    if (-not $scriptPath.Equals($expectedScript, [StringComparison]::OrdinalIgnoreCase)) {
        throw "runner path does not match the canonical repository location"
    }
    foreach ($marker in @(".git", "pyproject.toml", "lean_rgc", "tests")) {
        if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $marker))) {
            throw "repository marker is missing: $marker"
        }
    }
    $testsRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Join-Path $repoRoot "tests")).ProviderPath)

    $frozenTests = @(
        "tests/test_odlrq_behavioral_partition.py",
        "tests/test_odlrq_quotient_generator.py",
        "tests/test_odlrq_hankel_predictive.py",
        "tests/test_odlrq_componentwise_window.py"
    )
    $selectedTests = [Collections.Generic.List[string]]::new()
    foreach ($relativePath in $frozenTests) {
        $candidate = [IO.Path]::GetFullPath((Join-Path $repoRoot $relativePath))
        if (-not (Test-Path -LiteralPath $candidate)) {
            continue
        }
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            throw "frozen test path exists but is not a file: $relativePath"
        }
        $resolvedTest = Resolve-RegularFile -LiteralPath $candidate -RequiredRoot $testsRoot
        $expectedTest = [IO.Path]::GetFullPath((Join-Path $repoRoot $relativePath))
        if (-not $resolvedTest.Equals($expectedTest, [StringComparison]::OrdinalIgnoreCase)) {
            throw "frozen test path resolved unexpectedly: $relativePath"
        }
        $selectedTests.Add($relativePath.Replace("\", "/"))
    }
    if ($selectedTests.Count -lt 1) {
        Write-RunnerError "none of the four frozen CPU-survivor test modules exists"
        $requestedExitCode = $ExitNoTests
        throw [OperationCanceledException]::new("fail-closed runner exit")
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
    $bootstrapPath = Join-Path $runTemp "forbid_subprocess_and_run_pytest.py"
    $bootstrap = @'
import asyncio
import multiprocessing.process
import os
import subprocess
import sys


def _deny_subprocess(*_args, **_kwargs):
    raise RuntimeError("CPU-survivor semantic tests may not spawn subprocesses")


for _name in (
    "Popen",
    "run",
    "call",
    "check_call",
    "check_output",
    "getoutput",
    "getstatusoutput",
):
    if hasattr(subprocess, _name):
        setattr(subprocess, _name, _deny_subprocess)

for _name in (
    "system",
    "popen",
    "spawnl",
    "spawnle",
    "spawnlp",
    "spawnlpe",
    "spawnv",
    "spawnve",
    "spawnvp",
    "spawnvpe",
):
    if hasattr(os, _name):
        setattr(os, _name, _deny_subprocess)

asyncio.create_subprocess_exec = _deny_subprocess
asyncio.create_subprocess_shell = _deny_subprocess
multiprocessing.process.BaseProcess.start = _deny_subprocess

import pytest

raise SystemExit(pytest.main(sys.argv[1:]))
'@
    [IO.File]::WriteAllText($bootstrapPath, $bootstrap, [Text.UTF8Encoding]::new($false))

    $env:PYTHONDONTWRITEBYTECODE = "1"
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    $env:PYTHONPATH = ""
    $env:PYTEST_ADDOPTS = ""
    $env:PYTEST_PLUGINS = ""
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
    $env:UPRIME_CPU_SURVIVOR_SUBPROCESS_POLICY = "forbid"

    $pythonArguments = [Collections.Generic.List[string]]::new()
    $pythonArguments.Add($bootstrapPath)
    $pythonArguments.Add("-p")
    $pythonArguments.Add("no:cacheprovider")
    $pythonArguments.Add("--basetemp")
    $pythonArguments.Add($pytestTemp)
    $pythonArguments.Add("-q")
    foreach ($relativePath in $selectedTests) {
        $pythonArguments.Add($relativePath)
    }
    $nativeArgumentLine = (($pythonArguments | ForEach-Object { Quote-NativeArgument -Value $_ }) -join " ")

    $pythonProcess = Start-Process `
        -FilePath $pythonPath `
        -ArgumentList $nativeArgumentLine `
        -WorkingDirectory $repoRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath `
        -PassThru

    $stopwatch = [Diagnostics.Stopwatch]::StartNew()
    $capFailure = $null
    while (-not $pythonProcess.HasExited) {
        Start-Sleep -Milliseconds 50
        $pythonProcess.Refresh()
        if ($pythonProcess.HasExited) {
            break
        }
        if ($pythonProcess.WorkingSet64 -ge $WorkingSetLimitBytes) {
            $capFailure = "working_set"
            break
        }
        $capturedBytes = [int64]0
        foreach ($capturePath in @($stdoutPath, $stderrPath)) {
            if (Test-Path -LiteralPath $capturePath -PathType Leaf) {
                $capturedBytes += (Get-Item -LiteralPath $capturePath -Force).Length
            }
        }
        if ($capturedBytes -ge $OutputLimitBytes) {
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

    if ($null -eq $capFailure) {
        $capturedBytes = [int64]0
        foreach ($capturePath in @($stdoutPath, $stderrPath)) {
            if (Test-Path -LiteralPath $capturePath -PathType Leaf) {
                $capturedBytes += (Get-Item -LiteralPath $capturePath -Force).Length
            }
        }
        if ($capturedBytes -ge $OutputLimitBytes) {
            $capFailure = "output_limit"
        }
    }

    if ($capFailure -ne "output_limit") {
        Write-CapturedStream -LiteralPath $stdoutPath -Stream stdout
        Write-CapturedStream -LiteralPath $stderrPath -Stream stderr
    }
    $capturedWritten = $true

    if ($capFailure -eq "timeout") {
        Write-RunnerError "300-second wall limit exceeded; Python was terminated"
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
    else {
        $exitCode = $pythonProcess.ExitCode
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
