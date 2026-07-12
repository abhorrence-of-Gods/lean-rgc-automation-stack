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
$ExitQualificationMargin = 125
$ExitWorkingSet = 137
$ExitOutputLimit = 138
$WallLimitSeconds = 30.0
$QualificationMarginSeconds = 10.0
$WorkingSetLimitBytes = [int64]2 * 1024 * 1024 * 1024
$OutputLimitBytes = [int64]64 * 1024 * 1024
$TempPrefix = "lean-rgc-uprime-kp3-d4-native-tests-"
$FrozenTest = "tests/test_uprime_kp3_d4_canonical_history.py"

function Write-RunnerError {
    param([Parameter(Mandatory = $true)][string] $Message)
    [Console]::Error.WriteLine("uprime-kp3-d4-native-tests: {0}", $Message)
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
    $prefix = $root + [IO.Path]::DirectorySeparatorChar
    if (-not ($resolved.Equals($root, [StringComparison]::OrdinalIgnoreCase) -or
              $resolved.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase))) {
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

$unboundCount = if ($null -eq $MyInvocation.UnboundArguments) { 0 } else { @($MyInvocation.UnboundArguments).Count }
$unexpectedCount = if ($null -eq $UnexpectedArguments) { 0 } else { @($UnexpectedArguments).Count }
if ($PSBoundParameters.Count -ne 0 -or $unboundCount -ne 0 -or $unexpectedCount -ne 0) {
    Write-RunnerError "arguments are forbidden"
    exit $ExitUsage
}
if ($env:OS -ne "Windows_NT") {
    Write-RunnerError "this runner is restricted to Windows"
    exit $ExitUnsafeEnvironment
}

$runTemp = $null
$pythonProcess = $null
$pythonProcessHandle = $null
$stdoutPath = $null
$stderrPath = $null
$exitCode = $ExitInternalError
$savedEnvironment = @{}
try {
    if ([string]::IsNullOrWhiteSpace($PSCommandPath)) { throw "script path is unavailable" }
    $scriptPath = Resolve-RegularFile -LiteralPath $PSCommandPath -RequiredRoot (Split-Path -Parent $PSCommandPath)
    $toolsPath = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Split-Path -Parent $scriptPath)).ProviderPath)
    $repoRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Join-Path $toolsPath "..")).ProviderPath)
    $expectedScript = [IO.Path]::GetFullPath((Join-Path $repoRoot "tools\run_uprime_kp3_d4_native_tests.ps1"))
    if (-not $scriptPath.Equals($expectedScript, [StringComparison]::OrdinalIgnoreCase)) {
        throw "runner path does not match the canonical repository location"
    }
    foreach ($marker in @(".git", "pyproject.toml", "lean_rgc", "tests")) {
        if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $marker))) { throw "repository marker is missing: $marker" }
    }
    $testsRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Join-Path $repoRoot "tests")).ProviderPath)
    $testPath = [IO.Path]::GetFullPath((Join-Path $repoRoot $FrozenTest))
    if (-not (Test-Path -LiteralPath $testPath -PathType Leaf)) {
        Write-RunnerError "the frozen C2 test module is missing"
        exit $ExitNoTests
    }
    [void](Resolve-RegularFile -LiteralPath $testPath -RequiredRoot $testsRoot)

    $pythonCommand = Get-Command python.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1
    $pythonPath = Resolve-RegularFile -LiteralPath $pythonCommand.Source -RequiredRoot (Split-Path -Parent $pythonCommand.Source)
    if ([IO.Path]::GetExtension($pythonPath) -ine ".exe") { throw "resolved Python is not an executable" }

    $systemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd("\", "/")
    $runTemp = [IO.Path]::GetFullPath((Join-Path $systemTemp ($TempPrefix + [Guid]::NewGuid().ToString("N"))))
    if (-not ([IO.Path]::GetFullPath((Split-Path -Parent $runTemp)).TrimEnd("\", "/")).Equals($systemTemp, [StringComparison]::OrdinalIgnoreCase)) {
        throw "owned temporary directory escaped the system temp root"
    }
    [void][IO.Directory]::CreateDirectory($runTemp)
    $stdoutPath = Join-Path $runTemp "pytest.stdout.txt"
    $stderrPath = Join-Path $runTemp "pytest.stderr.txt"
    $receiptPath = Join-Path $runTemp "pytest.exit.txt"
    $bootstrapPath = Join-Path $runTemp "isolated_native_adapter_tests.py"
    $pytestTemp = Join-Path $runTemp "pytest-tmp"
    $bootstrap = @'
import asyncio
import ctypes
import _ctypes
import _socket
import multiprocessing.process
import nt
import os
import site
import socket
import subprocess
import sys
import sysconfig
import types

_startup_paths = tuple(sys.path)

def _deny_process(*_args, **_kwargs):
    raise RuntimeError("KP3-D4 C2 unit tests may not spawn child processes")

def _deny_network(*_args, **_kwargs):
    raise RuntimeError("KP3-D4 C2 unit tests may not access the network")

def _deny_ffi(*_args, **_kwargs):
    raise RuntimeError("KP3-D4 C2 unit tests may not use FFI")

for _name in ("Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput"):
    if hasattr(subprocess, _name): setattr(subprocess, _name, _deny_process)
for _module in (os, nt):
    for _name in ("_exit", "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe", "startfile", "system", "popen", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe", "posix_spawn", "posix_spawnp"):
        if hasattr(_module, _name): setattr(_module, _name, _deny_process)
asyncio.create_subprocess_exec = _deny_process
asyncio.create_subprocess_shell = _deny_process
multiprocessing.process.BaseProcess.start = _deny_process
try:
    import _winapi
except ImportError:
    _winapi = None
if _winapi is not None:
    for _name in ("CreateProcess", "ShellExecute"):
        if hasattr(_winapi, _name): setattr(_winapi, _name, _deny_process)

class _DeniedSocket:
    def __new__(cls, *_args, **_kwargs): _deny_network()
socket.socket = _DeniedSocket
socket.SocketType = _DeniedSocket
_socket.socket = _DeniedSocket
for _module in (socket, _socket):
    for _name in ("create_connection", "create_server", "fromfd", "fromshare", "getaddrinfo", "gethostbyaddr", "gethostbyname", "gethostbyname_ex", "gethostname", "getnameinfo", "socketpair"):
        if hasattr(_module, _name): setattr(_module, _name, _deny_network)

class _DeniedLoader:
    def __getattr__(self, _name): _deny_ffi()
    def LoadLibrary(self, *_args, **_kwargs): _deny_ffi()
for _name in ("CDLL", "PyDLL", "WinDLL", "OleDLL", "LibraryLoader", "CFUNCTYPE", "WINFUNCTYPE", "PYFUNCTYPE", "cast", "_dlopen", "_CFuncPtr"):
    if hasattr(ctypes, _name): setattr(ctypes, _name, _deny_ffi)
for _name in ("cdll", "pydll", "windll", "oledll", "pythonapi"):
    if hasattr(ctypes, _name): setattr(ctypes, _name, _DeniedLoader())
for _name in ("LoadLibrary", "call_cdeclfunction", "call_function", "CFuncPtr"):
    if hasattr(_ctypes, _name): setattr(_ctypes, _name, _deny_ffi)
site.addsitedir = _deny_ffi
site.addpackage = _deny_ffi

_receipt = os.environ.pop("UPRIME_KP3_D4_C2_TEST_RECEIPT", None)
if not _receipt or os.environ.get("UPRIME_KP3_D4_C2_TEST_POLICY") != "forbid":
    raise RuntimeError("C2 unit-test policy is unavailable")
_repo = os.path.normcase(os.path.abspath(os.getcwd()))
_forbidden_roots = tuple(os.path.normcase(os.path.abspath(os.path.join(_repo, p))) for p in (
    os.path.join("docs", "experiments", "inputs"),
    os.path.join("docs", "experiments", "artifacts", "uprime_kp3_d4_20260712"),
    os.path.join("docs", "experiments", "artifacts", "uprime_u05_20260711"),
    os.path.join("docs", "external", "quarantine"),
    os.path.join("lean_rgc", "native_lean"),
))
_forbidden_files = tuple(os.path.normcase(os.path.abspath(os.path.join(_repo, p))) for p in (
    os.path.join("lean_rgc", "evals", "uprime_u05_kill_probes.py"),
    "llm_local.json", "pilot_tasks.json", "fake_lean_smoke.py", "smoke_tasks_local.jsonl",
))
_home_quarantine = os.path.normcase(os.path.abspath(os.path.join(os.path.expanduser("~"), ".codex", "quarantine")))
_forbidden_real_roots = tuple(os.path.normcase(os.path.realpath(p)) for p in _forbidden_roots + (_home_quarantine,))
_forbidden_real_files = tuple(os.path.normcase(os.path.realpath(p)) for p in _forbidden_files)

def _lexical(raw):
    if isinstance(raw, int): return None
    try: value = os.fsdecode(os.fspath(raw))
    except (TypeError, ValueError): return None
    if not os.path.isabs(value): value = os.path.join(_repo, value)
    return os.path.normcase(os.path.abspath(value))

def _within(path, roots):
    return any(path == root or path.startswith(root + os.sep) for root in roots)

def _audit(event, args):
    if event in {"os.exec", "os.posix_spawn", "os.spawn", "os.system", "subprocess.Popen"}: _deny_process()
    if event.startswith("socket."): _deny_network()
    if event.startswith("ctypes."): _deny_ffi()
    if event in {"open", "os.chdir", "os.listdir", "os.scandir"} and args:
        path = _lexical(args[0])
        if path is not None and (_within(path, _forbidden_roots + (_home_quarantine,)) or path in _forbidden_files or path.lower().endswith(".pth")):
            raise RuntimeError("C2 unit tests may not read protected inputs, native worker, result, U05, quarantine, or LLM files")
        if path is not None:
            real = os.path.normcase(os.path.realpath(path))
            if _within(real, _forbidden_real_roots) or real in _forbidden_real_files:
                raise RuntimeError("C2 unit tests may not access a path resolving to protected data")
sys.addaudithook(_audit)

_trusted = []
def _add(path):
    value = os.path.normcase(os.path.abspath(path))
    if value not in _trusted: _trusted.append(value)
_add(_repo)
_base = os.path.normcase(os.path.abspath(sys.base_prefix))
for _path in _startup_paths:
    if _path:
        _value = os.path.normcase(os.path.abspath(_path))
        if _value == _base or _value.startswith(_base + os.sep): _add(_value)
for _scheme in ("nt", "nt_user"):
    for _kind in ("purelib", "platlib"):
        _path = sysconfig.get_path(_kind, _scheme)
        if _path and os.path.isdir(_path): _add(_path)
sys.path[:] = _trusted
if not sys.flags.isolated or not sys.flags.no_site or not sys.flags.safe_path or os.path.normcase(os.path.abspath(sys.path[0])) != _repo:
    raise RuntimeError("isolated Python policy was not established")

def _must_deny(label, callback):
    try: callback()
    except RuntimeError: return
    raise RuntimeError("C2 unit policy self-check failed: " + label)
_must_deny("process", lambda: subprocess.Popen([sys.executable, "-V"]))
_must_deny("network", lambda: socket.socket())
_must_deny("ffi", lambda: ctypes.CDLL("kernel32.dll"))
_must_deny("fresh input", lambda: open(os.path.join(_repo, "docs", "experiments", "inputs", "uprime_kp3_d4_fresh_tasks.json"), "rb"))
_must_deny("native worker", lambda: open(os.path.join(_repo, "lean_rgc", "native_lean", "RGCKernelRPC.lean"), "rb"))
_must_deny("result", lambda: open(os.path.join(_repo, "docs", "experiments", "artifacts", "uprime_kp3_d4_20260712", "fresh_family_d4.json"), "rb"))
sys.modules["colorama"] = types.ModuleType("colorama")
import pytest
_code = int(pytest.main(sys.argv[1:]))
with open(_receipt, "x", encoding="ascii", newline="\n") as _handle:
    _handle.write(f"{_code}\n")
raise SystemExit(_code)
'@
    [IO.File]::WriteAllText($bootstrapPath, $bootstrap, [Text.UTF8Encoding]::new($false))

    $runnerEnvironment = [ordered]@{
        PYTHONDONTWRITEBYTECODE = "1"
        PYTHONIOENCODING = "utf-8"
        PYTHONUTF8 = "1"
        PYTHONPATH = ""
        PYTEST_ADDOPTS = ""
        PYTEST_PLUGINS = ""
        PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
        UPRIME_KP3_D4_C2_TEST_POLICY = "forbid"
        UPRIME_KP3_D4_C2_TEST_RECEIPT = $receiptPath
    }
    foreach ($pair in $runnerEnvironment.GetEnumerator()) {
        $savedEnvironment[$pair.Key] = [Environment]::GetEnvironmentVariable($pair.Key, "Process")
        [Environment]::SetEnvironmentVariable($pair.Key, $pair.Value, "Process")
    }
    $arguments = @("-I", "-S", $bootstrapPath, "-p", "no:cacheprovider", "--basetemp", $pytestTemp, "-q", $FrozenTest)
    $nativeArgumentLine = (($arguments | ForEach-Object { Quote-NativeArgument -Value $_ }) -join " ")
    $pythonProcess = Start-Process -FilePath $pythonPath -ArgumentList $nativeArgumentLine -WorkingDirectory $repoRoot -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru
    $pythonProcessHandle = $pythonProcess.Handle
    $stopwatch = [Diagnostics.Stopwatch]::StartNew()
    $peakWorkingSet = [int64]0
    $failure = $null
    while (-not $pythonProcess.HasExited) {
        Start-Sleep -Milliseconds 25
        $pythonProcess.Refresh()
        $peakWorkingSet = [Math]::Max($peakWorkingSet, $pythonProcess.WorkingSet64)
        if ($peakWorkingSet -ge $WorkingSetLimitBytes) { $failure = "working_set"; break }
        if ((Get-CapturedBytes -Paths @($stdoutPath, $stderrPath)) -ge $OutputLimitBytes) { $failure = "output"; break }
        if ($stopwatch.Elapsed.TotalSeconds -ge $WallLimitSeconds) { $failure = "timeout"; break }
    }
    if ($null -ne $failure -and -not $pythonProcess.HasExited) { $pythonProcess.Kill() }
    $pythonProcess.WaitForExit()
    $pythonProcess.Refresh()
    $stopwatch.Stop()
    $peakWorkingSet = [Math]::Max($peakWorkingSet, $pythonProcess.PeakWorkingSet64)
    $processExit = [int]$pythonProcess.ExitCode
    if ($null -eq $failure -and $stopwatch.Elapsed.TotalSeconds -ge $WallLimitSeconds) { $failure = "timeout" }
    if ($null -eq $failure -and $peakWorkingSet -ge $WorkingSetLimitBytes) { $failure = "working_set" }
    if ($null -eq $failure -and (Get-CapturedBytes -Paths @($stdoutPath, $stderrPath)) -ge $OutputLimitBytes) { $failure = "output" }
    if ($null -eq $failure) {
        if (-not (Test-Path -LiteralPath $receiptPath -PathType Leaf)) { throw "owned pytest exit receipt is missing" }
        $receipt = [IO.File]::ReadAllText($receiptPath, [Text.Encoding]::ASCII)
        if ($receipt -notmatch '^(0|[1-9][0-9]{0,2})\r?\n$') { throw "owned pytest exit receipt is malformed" }
        $receiptExit = [int]$Matches[1]
        if ($receiptExit -ne $processExit) { throw "owned pytest exit receipt disagrees with process exit ($receiptExit != $processExit)" }
    }
    if ($failure -ne "output") {
        Write-CapturedStream -LiteralPath $stdoutPath -Stream stdout
        Write-CapturedStream -LiteralPath $stderrPath -Stream stderr
    }
    if ($failure -eq "timeout") { Write-RunnerError "30-second hard wall exceeded"; $exitCode = $ExitTimeout }
    elseif ($failure -eq "working_set") { Write-RunnerError "2-GiB working-set limit reached"; $exitCode = $ExitWorkingSet }
    elseif ($failure -eq "output") { Write-RunnerError "64-MiB output limit reached"; $exitCode = $ExitOutputLimit }
    elseif ($processExit -ne 0) { $exitCode = $processExit }
    elseif ($stopwatch.Elapsed.TotalSeconds -gt $QualificationMarginSeconds) {
        Write-RunnerError ("10-second qualification margin exceeded ({0:N3}s)" -f $stopwatch.Elapsed.TotalSeconds)
        $exitCode = $ExitQualificationMargin
    }
    else {
        $qualificationMessage = (
            "uprime-kp3-d4-native-tests: qualification elapsed={0:N3}s peak_working_set={1}" -f `
                $stopwatch.Elapsed.TotalSeconds, $peakWorkingSet
        )
        [Console]::Out.WriteLine($qualificationMessage)
        $exitCode = 0
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
    foreach ($pair in $savedEnvironment.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($pair.Key, $pair.Value, "Process")
    }
    if ($null -ne $pythonProcess -and -not $pythonProcess.HasExited) {
        try { $pythonProcess.Kill(); $pythonProcess.WaitForExit() } catch { }
    }
    if ($null -ne $runTemp -and (Test-Path -LiteralPath $runTemp)) {
        try {
            $resolved = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $runTemp).ProviderPath)
            $parent = [IO.Path]::GetFullPath((Split-Path -Parent $resolved)).TrimEnd("\", "/")
            $systemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd("\", "/")
            if (-not $parent.Equals($systemTemp, [StringComparison]::OrdinalIgnoreCase) -or -not [IO.Path]::GetFileName($resolved).StartsWith($TempPrefix, [StringComparison]::Ordinal)) {
                throw "refusing to clean an unowned path"
            }
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
        catch { Write-RunnerError $_.Exception.Message; if ($exitCode -eq 0) { $exitCode = $ExitInternalError } }
    }
}
exit $exitCode
