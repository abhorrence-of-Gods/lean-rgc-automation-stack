[CmdletBinding(PositionalBinding = $false)]
param(
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
$ExitWorkingSet = 137
$ExitOutputLimit = 138
$WallLimitSeconds = [int64]30
$QualificationMarginSeconds = [int64]10
$StopwatchFrequency = [int64][Diagnostics.Stopwatch]::Frequency
$WallLimitTicks = [int64]($StopwatchFrequency * $WallLimitSeconds)
$QualificationMarginTicks = [int64]($StopwatchFrequency * $QualificationMarginSeconds)
$WorkingSetLimitBytes = [uint64]1 * 1024 * 1024 * 1024
$OutputLimitBytes = [int64]16 * 1024 * 1024
$ExpectedPythonVersion = "3.13.7"
$ExpectedPythonSha256 = "D932E5E2F324D57F392E8FD063DCF6D0185BE8A664C57C6D24E7762ED02C28CA"
$FrozenTest = "tests/test_uprime_official_transport_v2_smoke.py"
$TempPrefix = "lean-rgc-uprime-official-transport-v2-tests-"

function Write-RunnerError {
    param([Parameter(Mandatory = $true)][string] $Message)
    [Console]::Error.WriteLine("uprime-official-transport-v2-tests: {0}", $Message)
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
    $text = [IO.File]::ReadAllText($LiteralPath, [Text.UTF8Encoding]::new($false, $true))
    if ($Stream -eq "stdout") { [Console]::Out.Write($text) }
    else { [Console]::Error.Write($text) }
}

$unboundCount = if ($null -eq $MyInvocation.UnboundArguments) { 0 } else { @($MyInvocation.UnboundArguments).Count }
$unexpectedCount = if ($null -eq $UnexpectedArguments) { 0 } else { @($UnexpectedArguments).Count }
if ($PSBoundParameters.Count -ne 0 -or $unboundCount -ne 0 -or $unexpectedCount -ne 0) {
    Write-RunnerError "arguments are forbidden"
    exit $ExitUsage
}
if ($env:OS -ne "Windows_NT" -or -not [Environment]::Is64BitProcess) {
    Write-RunnerError "this runner requires 64-bit Windows"
    exit $ExitPreflight
}

$runTemp = $null
$pythonProcess = $null
$job = [IntPtr]::Zero
$stdoutStream = $null
$stderrStream = $null
$stdoutCopyTask = $null
$stderrCopyTask = $null
$exitCode = $ExitInternalError

try {
    if ([string]::IsNullOrWhiteSpace($PSCommandPath)) { throw "script path is unavailable" }
    $scriptPath = Resolve-RegularFile -LiteralPath $PSCommandPath -RequiredRoot (Split-Path -Parent $PSCommandPath)
    $toolsPath = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Split-Path -Parent $scriptPath)).ProviderPath)
    $repoRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Join-Path $toolsPath "..")).ProviderPath)
    $expectedScript = [IO.Path]::GetFullPath((Join-Path $repoRoot "tools\run_uprime_official_transport_v2_tests.ps1"))
    if (-not $scriptPath.Equals($expectedScript, [StringComparison]::OrdinalIgnoreCase)) {
        throw "runner path does not match its canonical repository location"
    }
    foreach ($marker in @(".git", "pyproject.toml", "lean_rgc", "tests")) {
        if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $marker))) { throw "repository marker is missing: $marker" }
    }
    $testsRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Join-Path $repoRoot "tests")).ProviderPath)
    $testPath = Resolve-RegularFile -LiteralPath (Join-Path $repoRoot $FrozenTest) -RequiredRoot $testsRoot
    if (-not (Test-Path -LiteralPath $testPath -PathType Leaf)) { throw "frozen transport test module is missing" }

    $pythonPath = Resolve-RegularFile -LiteralPath "C:\Python313\python.exe" -RequiredRoot "C:\Python313"
    $pythonVersion = (Get-Item -LiteralPath $pythonPath -Force).VersionInfo.FileVersion
    if ($pythonVersion -cne $ExpectedPythonVersion -or (Get-Sha256 -LiteralPath $pythonPath) -cne $ExpectedPythonSha256) {
        throw "Python identity changed"
    }
    $userSite = [IO.Path]::GetFullPath((Join-Path $env:APPDATA "Python\Python313\site-packages"))
    if (-not (Test-Path -LiteralPath $userSite -PathType Container)) { throw "frozen pytest user-site is unavailable" }

    $systemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd("\", "/")
    $runTemp = [IO.Path]::GetFullPath((Join-Path $systemTemp ($TempPrefix + [Guid]::NewGuid().ToString("N"))))
    if (-not ([IO.Path]::GetFullPath((Split-Path -Parent $runTemp)).TrimEnd("\", "/")).Equals($systemTemp, [StringComparison]::OrdinalIgnoreCase)) {
        throw "owned temporary directory escaped the system temp root"
    }
    [void][IO.Directory]::CreateDirectory($runTemp)
    $stdoutPath = Join-Path $runTemp "pytest.stdout.txt"
    $stderrPath = Join-Path $runTemp "pytest.stderr.txt"
    $receiptPath = Join-Path $runTemp "pytest.exit.txt"
    $bootstrapPath = Join-Path $runTemp "isolated_transport_tests.py"
    $armPath = Join-Path $runTemp "pytest.arm"
    $pytestTemp = Join-Path $runTemp "pytest-tmp"

    $bootstrap = @'
import os
import sys
import sysconfig
import time
import types

_startup_paths = tuple(sys.path)

_arm = os.path.abspath(os.environ.pop("UPRIME_OFFICIAL_TRANSPORT_V2_TEST_ARM"))
while True:
    try:
        with open(_arm, "rb") as _handle:
            if _handle.read(16) != b"ARM\n":
                raise RuntimeError("unit-test arm is malformed")
        break
    except FileNotFoundError:
        # The sole registered unit_whole deadline is enforced by the parent
        # integer Stopwatch.  This loop is only the pre-ARM capability gate.
        time.sleep(0.01)

_repo = os.path.normcase(os.path.abspath(os.getcwd()))
_user_site = os.path.normcase(os.path.abspath(os.environ.pop("UPRIME_OFFICIAL_TRANSPORT_V2_TEST_USER_SITE")))
_trusted = [_repo]
_base = os.path.normcase(os.path.abspath(sys.base_prefix))
for _path in _startup_paths:
    if _path:
        _value = os.path.normcase(os.path.abspath(_path))
        if (_value == _base or _value.startswith(_base + os.sep)) and _value not in _trusted:
            _trusted.append(_value)
for _kind in ("stdlib", "platstdlib", "purelib", "platlib"):
    _path = sysconfig.get_path(_kind)
    if _path:
        _value = os.path.normcase(os.path.abspath(_path))
        if _value not in _trusted:
            _trusted.append(_value)
for _scheme in ("nt", "nt_user"):
    for _kind in ("purelib", "platlib"):
        _path = sysconfig.get_path(_kind, _scheme)
        if _path:
            _value = os.path.normcase(os.path.abspath(_path))
            if _value not in _trusted:
                _trusted.append(_value)
if _user_site in _trusted:
    _trusted.remove(_user_site)
_trusted.append(_user_site)
sys.path[:] = _trusted
sys.modules["colorama"] = types.ModuleType("colorama")
if not sys.flags.isolated or not sys.flags.no_site or not sys.flags.safe_path:
    raise RuntimeError("unit-test Python is not isolated")
import pytest

_receipt = os.environ.pop("UPRIME_OFFICIAL_TRANSPORT_V2_TEST_RECEIPT")
_code = int(pytest.main(sys.argv[1:]))
with open(_receipt, "x", encoding="ascii", newline="\n") as _handle:
    _handle.write(f"{_code}\n")
raise SystemExit(_code)
'@
    [IO.File]::WriteAllText($bootstrapPath, $bootstrap, [Text.UTF8Encoding]::new($false))

    $jobSource = @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
public static class UPrimeOfficialTransportV2TestJob {
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
  [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);
  public static bool StartAssigned(Process process, IntPtr job, int timeoutMilliseconds) {
    if (timeoutMilliseconds <= 0) return false;
    Task<bool> task = Task.Run(() => {
      if (!process.Start()) return false;
      if (!AssignProcessToJobObject(job, process.Handle)) {
        try { process.Kill(); } catch { }
        throw new System.ComponentModel.Win32Exception();
      }
      return true;
    });
    if (!task.Wait(timeoutMilliseconds)) {
      task.ContinueWith(_ => { try { if (!process.HasExited) process.Kill(); } catch { } }, TaskScheduler.Default);
      return false;
    }
    return task.GetAwaiter().GetResult();
  }
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
    int size = Marshal.SizeOf(typeof(Extended));
    IntPtr mem = Marshal.AllocHGlobal(size);
    try {
      uint used;
      if (!QueryInformationJobObject(h, 9, mem, (uint)size, out used)) throw new System.ComponentModel.Win32Exception();
      Extended x = (Extended)Marshal.PtrToStructure(mem, typeof(Extended));
      return x.PeakJobMemoryUsed.ToUInt64();
    } finally { Marshal.FreeHGlobal(mem); }
  }
}
'@
    if ($null -eq ("UPrimeOfficialTransportV2TestJob" -as [type])) {
        Add-Type -TypeDefinition $jobSource -Language CSharp
    }
    $job = [UPrimeOfficialTransportV2TestJob]::Create($WorkingSetLimitBytes)

    $arguments = @("-I", "-S", $bootstrapPath, "-p", "no:cacheprovider", "--basetemp", $pytestTemp, "-q", $FrozenTest)
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $pythonPath
    $startInfo.Arguments = (($arguments | ForEach-Object { Quote-NativeArgument -Value $_ }) -join " ")
    $startInfo.WorkingDirectory = $repoRoot
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.EnvironmentVariables.Clear()
    $environment = [ordered]@{
        COMSPEC = [IO.Path]::GetFullPath($env:ComSpec)
        LANG = "C.UTF-8"
        LC_ALL = "C.UTF-8"
        PATH = ([IO.Path]::GetDirectoryName($pythonPath) + ";" + (Join-Path $env:SystemRoot "System32"))
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONIOENCODING = "utf-8"
        PYTHONUTF8 = "1"
        PYTEST_ADDOPTS = ""
        PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
        PYTEST_PLUGINS = ""
        SYSTEMROOT = [IO.Path]::GetFullPath($env:SystemRoot)
        TEMP = $runTemp
        TMP = $runTemp
        UPRIME_OFFICIAL_TRANSPORT_V2_TEST_ARM = $armPath
        UPRIME_OFFICIAL_TRANSPORT_V2_TEST_RECEIPT = $receiptPath
        UPRIME_OFFICIAL_TRANSPORT_V2_TEST_USER_SITE = $userSite
        USERPROFILE = [IO.Path]::GetFullPath($env:USERPROFILE)
        WINDIR = [IO.Path]::GetFullPath($env:SystemRoot)
    }
    foreach ($pair in $environment.GetEnumerator()) { $startInfo.EnvironmentVariables[$pair.Key] = $pair.Value }

    $pythonProcess = [Diagnostics.Process]::new()
    $pythonProcess.StartInfo = $startInfo
    $stopwatch = [Diagnostics.Stopwatch]::StartNew()
    $startRemainingTicks = [Math]::Max([int64]0, $WallLimitTicks - [int64]$stopwatch.ElapsedTicks)
    $startMilliseconds = [int](($startRemainingTicks * 1000 + $StopwatchFrequency - 1) / $StopwatchFrequency)
    if (-not [UPrimeOfficialTransportV2TestJob]::StartAssigned($pythonProcess, $job, $startMilliseconds)) {
        throw "failed to start and Job-assign exact unit-test Python within unit_whole"
    }
    if ([int64]$stopwatch.ElapsedTicks -gt $WallLimitTicks) { throw "30-second hard wall exceeded during Process.Start" }
    $stdoutStream = [IO.FileStream]::new($stdoutPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    $stderrStream = [IO.FileStream]::new($stderrPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    $stdoutCopyTask = $pythonProcess.StandardOutput.BaseStream.CopyToAsync($stdoutStream)
    $stderrCopyTask = $pythonProcess.StandardError.BaseStream.CopyToAsync($stderrStream)
    $armBytes = [Text.Encoding]::ASCII.GetBytes("ARM`n")
    $armFile = [IO.FileStream]::new($armPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None, 4096, [IO.FileOptions]::WriteThrough)
    try { $armFile.Write($armBytes, 0, $armBytes.Length); $armFile.Flush($true) }
    finally { $armFile.Dispose() }

    $failure = $null
    $peak = [uint64]0
    while (-not $pythonProcess.HasExited) {
        Start-Sleep -Milliseconds 25
        if ((Get-CapturedBytes -Paths @($stdoutPath, $stderrPath)) -ge $OutputLimitBytes) { $failure = "output"; break }
        if ([int64]$stopwatch.ElapsedTicks -gt $WallLimitTicks) { $failure = "timeout"; break }
        try { $peak = [Math]::Max($peak, [UPrimeOfficialTransportV2TestJob]::Peak($job)) } catch { }
    }
    if ($null -ne $failure -and -not $pythonProcess.HasExited) {
        [void][UPrimeOfficialTransportV2TestJob]::CloseHandle($job)
        $job = [IntPtr]::Zero
    }
    if (-not $pythonProcess.HasExited) {
        $remainingTicks = [Math]::Max([int64]0, $WallLimitTicks - [int64]$stopwatch.ElapsedTicks)
        $remainingMilliseconds = [int][Math]::Min([int64][int]::MaxValue, [int64](($remainingTicks * 1000) / $StopwatchFrequency))
        if ($remainingMilliseconds -gt 0) { [void]$pythonProcess.WaitForExit($remainingMilliseconds) }
    }
    while ($null -eq $failure -and
           (($null -ne $stdoutCopyTask -and -not $stdoutCopyTask.IsCompleted) -or
            ($null -ne $stderrCopyTask -and -not $stderrCopyTask.IsCompleted))) {
        if ([int64]$stopwatch.ElapsedTicks -gt $WallLimitTicks) { $failure = "timeout"; break }
        Start-Sleep -Milliseconds 1
    }
    if ($null -eq $failure -and $null -ne $stdoutCopyTask) { [void]$stdoutCopyTask.GetAwaiter().GetResult() }
    if ($null -eq $failure -and $null -ne $stderrCopyTask) { [void]$stderrCopyTask.GetAwaiter().GetResult() }
    $stdoutStream.Flush($true); $stdoutStream.Dispose(); $stdoutStream = $null
    $stderrStream.Flush($true); $stderrStream.Dispose(); $stderrStream = $null
    $stopwatch.Stop()
    if ($job -ne [IntPtr]::Zero) { try { $peak = [Math]::Max($peak, [UPrimeOfficialTransportV2TestJob]::Peak($job)) } catch { } }
    $processExit = if ($pythonProcess.HasExited) { [int]$pythonProcess.ExitCode } else { $ExitTimeout }
    $elapsedTicks = [int64]$stopwatch.ElapsedTicks
    if ($null -eq $failure -and $elapsedTicks -gt $WallLimitTicks) { $failure = "timeout" }
    if ($null -eq $failure -and -not (Test-Path -LiteralPath $receiptPath -PathType Leaf) -and
        ($peak -ge $WorkingSetLimitBytes -or $processExit -in @(-1073741801, -1073741523))) { $failure = "working_set" }
    if ($null -eq $failure -and $peak -ge $WorkingSetLimitBytes) { $failure = "working_set" }
    if ($null -eq $failure -and (Get-CapturedBytes -Paths @($stdoutPath, $stderrPath)) -ge $OutputLimitBytes) { $failure = "output" }

    if ($failure -ne "output") {
        Write-CapturedStream -LiteralPath $stdoutPath -Stream stdout
        Write-CapturedStream -LiteralPath $stderrPath -Stream stderr
    }
    if ($null -eq $failure) {
        if (-not (Test-Path -LiteralPath $receiptPath -PathType Leaf)) { throw "owned pytest exit receipt is missing" }
        $receipt = [IO.File]::ReadAllText($receiptPath, [Text.Encoding]::ASCII)
        if ($receipt -notmatch '^(0|[1-9][0-9]{0,2})\r?\n$') { throw "owned pytest exit receipt is malformed" }
        if ([int]$Matches[1] -ne $processExit) { throw "owned pytest exit receipt disagrees with process exit" }
    }
    if ($failure -eq "timeout") { Write-RunnerError "30-second hard wall exceeded"; $exitCode = $ExitTimeout }
    elseif ($failure -eq "working_set") { Write-RunnerError "1-GiB Job working-set limit reached"; $exitCode = $ExitWorkingSet }
    elseif ($failure -eq "output") { Write-RunnerError "16-MiB captured-output limit reached"; $exitCode = $ExitOutputLimit }
    elseif ($processExit -ne 0) { $exitCode = $processExit }
    elseif ($elapsedTicks -gt $QualificationMarginTicks) {
        Write-RunnerError ("10-second qualification margin exceeded (ticks={0}, frequency={1})" -f $elapsedTicks, $StopwatchFrequency)
        $exitCode = $ExitQualificationMargin
    }
    else {
        [Console]::Out.WriteLine((
            "uprime-official-transport-v2-tests: qualification ticks={0} frequency={1} peak_job_memory={2}" -f `
                $elapsedTicks, $StopwatchFrequency, $peak
        ))
        $exitCode = 0
    }
}
catch [System.Management.Automation.ItemNotFoundException] {
    Write-RunnerError "Python or the frozen test module is unavailable"
    $exitCode = $ExitPythonUnavailable
}
catch {
    Write-RunnerError $_.Exception.Message
    $exitCode = $ExitInternalError
}
finally {
    if ($job -ne [IntPtr]::Zero) { try { [void][UPrimeOfficialTransportV2TestJob]::CloseHandle($job) } catch { }; $job = [IntPtr]::Zero }
    if ($null -ne $pythonProcess -and -not $pythonProcess.HasExited) { try { $pythonProcess.Kill() } catch { } }
    if ($null -ne $stdoutStream) { try { $stdoutStream.Dispose() } catch { } }
    if ($null -ne $stderrStream) { try { $stderrStream.Dispose() } catch { } }
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
