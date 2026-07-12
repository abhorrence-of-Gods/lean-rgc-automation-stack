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
$TempPrefix = "lean-rgc-uprime-kp3-d4-history-"
$FrozenTests = @(
    "tests/test_odlrq_history_normal_form.py",
    "tests/test_odlrq_hankel_depth4.py"
)

function Write-RunnerError {
    param([Parameter(Mandatory = $true)][string] $Message)
    [Console]::Error.WriteLine("uprime-kp3-d4-history: {0}", $Message)
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
            "uprime-kp3-d4-history: captured {0} omitted after output cap",
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
    $expectedScript = [IO.Path]::GetFullPath((Join-Path $repoRoot "tools\run_uprime_kp3_d4_history_tests.ps1"))
    if (-not $scriptPath.Equals($expectedScript, [StringComparison]::OrdinalIgnoreCase)) {
        throw "runner path does not match the canonical repository location"
    }
    foreach ($marker in @(".git", "pyproject.toml", "lean_rgc", "tests")) {
        if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $marker))) {
            throw "repository marker is missing: $marker"
        }
    }

    $testsRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath (Join-Path $repoRoot "tests")).ProviderPath)
    $selectedTests = [Collections.Generic.List[string]]::new()
    foreach ($relativePath in $FrozenTests) {
        $candidate = [IO.Path]::GetFullPath((Join-Path $repoRoot $relativePath))
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            Write-RunnerError "a frozen KP3-D4 C1 test module is missing: $relativePath"
            $requestedExitCode = $ExitNoTests
            throw [OperationCanceledException]::new("fail-closed runner exit")
        }
        $resolvedTest = Resolve-RegularFile -LiteralPath $candidate -RequiredRoot $testsRoot
        if (-not $resolvedTest.Equals($candidate, [StringComparison]::OrdinalIgnoreCase)) {
            throw "frozen test path resolved unexpectedly: $relativePath"
        }
        $selectedTests.Add($relativePath.Replace("\", "/"))
    }
    if ($selectedTests.Count -ne 2) {
        throw "the runner must select exactly two frozen C1 test modules"
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
    $bootstrapPath = Join-Path $runTemp "forbid_external_access_and_run_pytest.py"
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


_startup_import_paths = tuple(sys.path)


def _deny_process(*_args, **_kwargs):
    raise RuntimeError("KP3-D4 C1 tests may not spawn subprocesses or exit the process")


def _deny_network(*_args, **_kwargs):
    raise RuntimeError("KP3-D4 C1 tests may not access the network")


def _deny_ffi(*_args, **_kwargs):
    raise RuntimeError("KP3-D4 C1 tests may not load or call native libraries")


def _deny_site_path(*_args, **_kwargs):
    raise RuntimeError("KP3-D4 C1 tests may not process site path files")


for _name in (
    "Popen", "run", "call", "check_call", "check_output",
    "getoutput", "getstatusoutput",
):
    if hasattr(subprocess, _name):
        setattr(subprocess, _name, _deny_process)

for _name in (
    "_exit", "execl", "execle", "execlp", "execlpe", "execv", "execve",
    "execvp", "execvpe", "startfile", "system", "popen", "spawnl",
    "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp",
    "spawnvpe", "posix_spawn", "posix_spawnp",
):
    if hasattr(os, _name):
        setattr(os, _name, _deny_process)
    if hasattr(nt, _name):
        setattr(nt, _name, _deny_process)

asyncio.create_subprocess_exec = _deny_process
asyncio.create_subprocess_shell = _deny_process
multiprocessing.process.BaseProcess.start = _deny_process

try:
    import _winapi
except ImportError:
    _winapi = None
if _winapi is not None:
    for _name in (
        "CreateFile", "CreateFileMapping", "CreateJunction", "CreateNamedPipe",
        "CreatePipe", "CreateProcess", "OpenFileMapping", "OpenProcess",
        "ReadFile", "ShellExecute", "WriteFile",
    ):
        if hasattr(_winapi, _name):
            setattr(_winapi, _name, _deny_process)


class _DeniedSocket:
    __slots__ = ()

    def __new__(cls, *_args, **_kwargs):
        _deny_network()

    accept = _deny_network
    bind = _deny_network
    connect = _deny_network
    connect_ex = _deny_network
    listen = _deny_network
    recv = _deny_network
    recvfrom = _deny_network
    recvfrom_into = _deny_network
    recv_into = _deny_network
    send = _deny_network
    sendall = _deny_network
    sendmsg = _deny_network
    sendto = _deny_network


socket.socket = _DeniedSocket
socket.SocketType = _DeniedSocket
_socket.socket = _DeniedSocket
for _module in (socket, _socket):
    for _name in (
        "create_connection", "create_server", "fromfd", "fromshare",
        "getaddrinfo", "gethostbyaddr", "gethostbyname", "gethostbyname_ex",
        "gethostname", "getnameinfo", "socketpair",
    ):
        if hasattr(_module, _name):
            setattr(_module, _name, _deny_network)


class _DeniedLoaderProxy:
    __slots__ = ()

    def __getattr__(self, _name):
        _deny_ffi()

    def LoadLibrary(self, *_args, **_kwargs):
        _deny_ffi()


for _name in (
    "CDLL", "PyDLL", "WinDLL", "OleDLL", "LibraryLoader", "CFUNCTYPE",
    "WINFUNCTYPE", "PYFUNCTYPE", "cast", "memmove", "memset", "string_at",
    "wstring_at", "_dlopen", "_CFuncPtr",
):
    if hasattr(ctypes, _name):
        setattr(ctypes, _name, _deny_ffi)
for _name in ("cdll", "pydll", "windll", "oledll", "pythonapi"):
    if hasattr(ctypes, _name):
        setattr(ctypes, _name, _DeniedLoaderProxy())
for _name in ("LoadLibrary", "call_cdeclfunction", "call_function", "CFuncPtr"):
    if hasattr(_ctypes, _name):
        setattr(_ctypes, _name, _deny_ffi)

site.addsitedir = _deny_site_path
site.addpackage = _deny_site_path

_receipt = os.environ.pop("UPRIME_KP3_D4_C1_EXIT_RECEIPT", None)
if not _receipt:
    raise RuntimeError("owned pytest exit receipt path is unavailable")
if os.environ.get("UPRIME_KP3_D4_C1_POLICY") != "forbid":
    raise RuntimeError("KP3-D4 C1 external-access policy is unavailable")

_repo_root = os.path.normcase(os.path.abspath(os.getcwd()))
_forbidden_lexical_roots = tuple(
    os.path.normcase(os.path.abspath(os.path.join(_repo_root, _relative)))
    for _relative in (
        os.path.join("docs", "experiments", "inputs"),
        os.path.join("docs", "external", "quarantine"),
        os.path.join("lean_rgc", "native_lean"),
    )
)
_forbidden_real_roots = tuple(
    os.path.normcase(os.path.realpath(_root)) for _root in _forbidden_lexical_roots
)
_forbidden_lexical_files = tuple(
    os.path.normcase(os.path.abspath(os.path.join(_repo_root, _relative)))
    for _relative in (
        os.path.join(
            "docs", "experiments", "artifacts", "uprime_u05_20260711",
            "u05_kill_probes.json",
        ),
        os.path.join("lean_rgc", "evals", "uprime_u05_kill_probes.py"),
        "llm_local.json",
        "pilot_tasks.json",
        "fake_lean_smoke.py",
        "smoke_tasks_local.jsonl",
    )
)
_forbidden_real_files = tuple(
    os.path.normcase(os.path.realpath(_path)) for _path in _forbidden_lexical_files
)
_quarantine_lexical_root = os.path.normcase(
    os.path.abspath(
        os.path.join(os.path.expanduser("~"), ".codex", "quarantine")
    )
)
_quarantine_decoy = os.path.join(
    _quarantine_lexical_root, "__uprime_kp3_d4_forbidden_decoy__"
)
_process_audit_events = frozenset(
    {
        "os.exec",
        "os.posix_spawn",
        "os.spawn",
        "os.system",
        "subprocess.Popen",
    }
)


def _audited_lexical_path(raw):
    if isinstance(raw, int):
        return None
    try:
        value = os.fsdecode(os.fspath(raw))
    except (TypeError, ValueError):
        return None
    if not os.path.isabs(value):
        value = os.path.join(_repo_root, value)
    return os.path.normcase(os.path.abspath(value))


def _path_is_within(path, roots):
    return any(path == root or path.startswith(root + os.sep) for root in roots)


def _deny_protected_path(raw):
    lexical = _audited_lexical_path(raw)
    if lexical is None:
        return
    if lexical.lower().endswith(".pth"):
        raise RuntimeError("KP3-D4 C1 tests may not process .pth files")
    if (
        _path_is_within(lexical, _forbidden_lexical_roots)
        or lexical in _forbidden_lexical_files
        or lexical == _quarantine_decoy
        or _path_is_within(lexical, (_quarantine_lexical_root,))
    ):
        raise RuntimeError(
            "KP3-D4 C1 tests may not access registered, native, U05, quarantine, or LLM inputs"
        )
    real = os.path.normcase(os.path.realpath(lexical))
    if _path_is_within(real, _forbidden_real_roots) or real in _forbidden_real_files:
        raise RuntimeError(
            "KP3-D4 C1 tests may not access a path resolving to protected input"
        )


def _deny_external_access(event, args):
    if event in _process_audit_events:
        _deny_process()
    if event.startswith("socket."):
        _deny_network()
    if event.startswith("ctypes."):
        _deny_ffi()
    if event in {"open", "os.chdir", "os.listdir", "os.scandir"} and args:
        _deny_protected_path(args[0])


sys.addaudithook(_deny_external_access)


def _append_unique_path(target, value):
    lexical = os.path.normcase(os.path.abspath(value))
    if lexical not in target:
        target.append(lexical)


_trusted_import_paths = []
_base_prefix = os.path.normcase(os.path.abspath(sys.base_prefix))
_append_unique_path(_trusted_import_paths, _repo_root)
for _path in _startup_import_paths:
    if not _path:
        continue
    _lexical = os.path.normcase(os.path.abspath(_path))
    if _lexical == _base_prefix or _lexical.startswith(_base_prefix + os.sep):
        _append_unique_path(_trusted_import_paths, _lexical)
# The selected interpreter installs pytest in its user purelib.  Add the
# directory only after the audit/process/network policy is live; importing
# ``site`` under ``-S`` never processes its .pth files.
for _scheme in ("nt", "nt_user"):
    for _kind in ("purelib", "platlib"):
        _candidate = sysconfig.get_path(_kind, _scheme)
        if _candidate and os.path.isdir(_candidate):
            _append_unique_path(_trusted_import_paths, _candidate)
sys.path[:] = _trusted_import_paths
if (
    not sys.flags.isolated
    or not sys.flags.no_site
    or not sys.flags.safe_path
    or any(not _path for _path in sys.path)
    or os.path.normcase(os.path.abspath(sys.path[0])) != _repo_root
):
    raise RuntimeError("isolated Python import policy was not established")


def _require_denial(label, callback):
    try:
        callback()
    except RuntimeError:
        return
    raise RuntimeError(f"KP3-D4 C1 policy self-check failed: {label}")


_require_denial("subprocess", lambda: subprocess.Popen([sys.executable, "-V"]))
_require_denial("os.exec", lambda: os.execv(sys.executable, [sys.executable, "-V"]))
_require_denial("os._exit", lambda: os._exit(0))
_require_denial("nt._exit", lambda: nt._exit(0))
_require_denial("socket constructor", lambda: socket.socket())
for _socket_method in ("accept", "bind", "listen", "send", "sendto"):
    _require_denial(
        f"socket.{_socket_method}",
        lambda _name=_socket_method: getattr(socket.socket, _name)(None),
    )
_require_denial("socket audit", lambda: sys.audit("socket.__new__", None))
_require_denial("ctypes.CDLL", lambda: ctypes.CDLL("kernel32.dll"))
_require_denial("ctypes LibraryLoader", lambda: ctypes.cdll.LoadLibrary("kernel32.dll"))
_require_denial("raw _ctypes loader", lambda: _ctypes.LoadLibrary("kernel32.dll"))
for _ctypes_event in ("ctypes.dlopen", "ctypes.dlsym", "ctypes.call_function"):
    _require_denial(
        _ctypes_event,
        lambda _event=_ctypes_event: sys.audit(_event, None),
    )
_require_denial(
    "registered input",
    lambda: open(
        os.path.join(
            _repo_root,
            "docs",
            "experiments",
            "inputs",
            "uprime_kp3_d4_fresh_tasks.json",
        ),
        "rb",
    ),
)
_require_denial(
    "native Lean",
    lambda: open(
        os.path.join(_repo_root, "lean_rgc", "native_lean", "RGCKernelRPC.lean"),
        "rb",
    ),
)
_require_denial(
    "old U05 artifact",
    lambda: open(
        os.path.join(
            _repo_root,
            "docs",
            "experiments",
            "artifacts",
            "uprime_u05_20260711",
            "u05_kill_probes.json",
        ),
        "rb",
    ),
)
_require_denial(
    "old U05 evaluator",
    lambda: open(
        os.path.join(
            _repo_root, "lean_rgc", "evals", "uprime_u05_kill_probes.py"
        ),
        "rb",
    ),
)
_require_denial("quarantine decoy", lambda: open(_quarantine_decoy, "rb"))
_require_denial(
    "LLM decoy", lambda: open(os.path.join(_repo_root, "llm_local.json"), "rb")
)
_require_denial(
    ".pth processing",
    lambda: open(
        os.path.join(sysconfig.get_path("purelib", "nt_user"), "forbidden.pth"),
        "rb",
    ),
)
_require_denial("network", lambda: socket.getaddrinfo("localhost", 0))

# Pytest imports colorama on Windows solely for an import-time console
# workaround.  A local inert module prevents that optional workaround from
# opening kernel32 through ctypes after the FFI boundary has been closed.
sys.modules["colorama"] = types.ModuleType("colorama")
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
    $env:UPRIME_KP3_D4_C1_POLICY = "forbid"
    $env:UPRIME_KP3_D4_C1_EXIT_RECEIPT = $exitReceiptPath

    $pythonArguments = [Collections.Generic.List[string]]::new()
    $pythonArguments.Add("-I")
    $pythonArguments.Add("-S")
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
            "uprime-kp3-d4-history: qualification elapsed={0:N3}s peak_working_set={1}" -f `
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
    Remove-Item Env:UPRIME_KP3_D4_C1_EXIT_RECEIPT -ErrorAction SilentlyContinue
    Remove-Item Env:UPRIME_KP3_D4_C1_POLICY -ErrorAction SilentlyContinue
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
