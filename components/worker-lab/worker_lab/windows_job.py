from __future__ import annotations

import ctypes
import hashlib
import os
import subprocess
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .errors import LabValidationError
from .canonical import canonical_digest
from .process_custody import (
    PROCESS_CUSTODY_SCHEMA,
    CustodyState,
    ProcessCustodyRecord,
    ProcessCustodyStore,
    transition_custody,
)


JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS = 1
HANDLE_FLAG_INHERIT = 0x00000001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
WINDOWS_JOB_BACKEND_ID = "windows-job-object:v1"
WINDOWS_PROCESS_IDENTITY_SCHEMA = "windows-process:v1"
WINDOWS_JOB_ABSENCE_SCHEMA = "worker-lab-windows-job-absence-evidence:v1"


class _FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_longlong),
        ("TotalKernelTime", ctypes.c_longlong),
        ("ThisPeriodTotalUserTime", ctypes.c_longlong),
        ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    ]


Now = Callable[[], str]


@dataclass(frozen=True)
class WorkspaceLaunchEvidence:
    workspace_path: Path
    workspace_path_digest: str
    observed_head: str
    status: str
    content_digest: str


WorkspaceInspector = Callable[[Path], WorkspaceLaunchEvidence]




def process_creation_time_for_pid(pid: int) -> int | None:
    if os.name != "nt":
        raise LabValidationError("INTEGRATION_RUNTIME_FORBIDDEN", "Windows process identity is required")
    kernel32 = _kernel32()
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        return _process_creation_time(handle, kernel32)
    finally:
        kernel32.CloseHandle(handle)


def windows_process_identity(pid: int, creation_time_100ns: int) -> str:
    """Encode a Windows process identity for the backend's opaque custody field."""
    if (
        isinstance(pid, bool)
        or not isinstance(pid, int)
        or pid <= 0
        or isinstance(creation_time_100ns, bool)
        or not isinstance(creation_time_100ns, int)
        or creation_time_100ns <= 0
    ):
        raise LabValidationError(
            "INTEGRATION_PROCESS_IDENTITY_INVALID", "Windows process identity is invalid",
        )
    return f"{WINDOWS_PROCESS_IDENTITY_SCHEMA}:{pid}:{creation_time_100ns}"


class WindowsJobCustodyBackend:
    """Interpret Custody V2 identities and absence evidence for Job Objects."""

    backend_id = WINDOWS_JOB_BACKEND_ID

    def __init__(self, process_probe: Callable[[int], int | None] | None = None) -> None:
        if process_probe is not None and not callable(process_probe):
            raise LabValidationError(
                "INTEGRATION_CUSTODY_BACKEND_INVALID", "Windows process probe is invalid",
            )
        self._process_probe = process_probe or process_creation_time_for_pid

    def controller_is_active(self, record: ProcessCustodyRecord) -> bool:
        self._require_backend(record)
        pid, creation_time = _parse_windows_process_identity(record.controller_identity)
        return self._process_probe(pid) == creation_time

    def absence_evidence_after_controller_exit(
        self, record: ProcessCustodyRecord,
    ) -> str | None:
        if self.controller_is_active(record):
            return None
        return self.absence_evidence_digest(
            record, basis="controller-exit-after-job-zero",
        )

    def absence_evidence_digest(
        self,
        record: ProcessCustodyRecord,
        *,
        basis: str,
    ) -> str:
        self._require_backend(record)
        if basis not in {"job-accounting-zero", "controller-exit-after-job-zero"}:
            raise LabValidationError(
                "INTEGRATION_CUSTODY_BACKEND_INVALID", "Windows absence basis is invalid",
            )
        if record.active_workload_count != 0:
            raise LabValidationError(
                "INTEGRATION_OUTCOME_UNCERTAIN", "Windows Job Object does not prove absence",
            )
        if record.worker_identity is not None:
            _parse_windows_process_identity(record.worker_identity)
        return canonical_digest({
            "schema_version": WINDOWS_JOB_ABSENCE_SCHEMA,
            "backend_id": self.backend_id,
            "invocation_digest": record.invocation_digest,
            "controller_identity": record.controller_identity,
            "worker_identity": record.worker_identity,
            "active_workload_count": record.active_workload_count,
            "basis": basis,
        })

    def _require_backend(self, record: ProcessCustodyRecord) -> None:
        if not isinstance(record, ProcessCustodyRecord) or record.backend_id != self.backend_id:
            raise LabValidationError(
                "INTEGRATION_CUSTODY_BACKEND_INVALID", "custody is not Windows Job Object evidence",
            )


def _parse_windows_process_identity(value: str) -> tuple[int, int]:
    try:
        schema, version, pid_text, creation_text = value.split(":")
        pid = int(pid_text)
        creation_time = int(creation_text)
    except (AttributeError, TypeError, ValueError) as exc:
        raise LabValidationError(
            "INTEGRATION_PROCESS_IDENTITY_INVALID", "Windows process identity is invalid",
        ) from exc
    if f"{schema}:{version}" != WINDOWS_PROCESS_IDENTITY_SCHEMA:
        raise LabValidationError(
            "INTEGRATION_PROCESS_IDENTITY_INVALID", "Windows process identity schema differs",
        )
    if windows_process_identity(pid, creation_time) != value:
        raise LabValidationError(
            "INTEGRATION_PROCESS_IDENTITY_INVALID", "Windows process identity is not canonical",
        )
    return pid, creation_time


def inspect_launch_workspace(path: Path) -> WorkspaceLaunchEvidence:
    """Independently seal the exact clean Git workspace used as adapter cwd."""
    if not isinstance(path, Path) or not path.is_absolute() or not path.exists():
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter workspace path is unavailable")
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink() or getattr(os.lstat(current), "st_file_attributes", 0) & 0x400:
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter workspace path is substituted")
    resolved = absolute.resolve(strict=True)
    if _path_key(resolved) != _path_key(absolute) or not resolved.is_dir():
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter workspace path is not canonical")
    git_dir = resolved / ".git"
    if not git_dir.is_dir() or git_dir.is_symlink() or getattr(os.lstat(git_dir), "st_file_attributes", 0) & 0x400:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter workspace is not a real Git repository")
    top = Path(_workspace_git(resolved, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if _path_key(top) != _path_key(resolved):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter workspace Git root differs")
    head = _workspace_git(resolved, "rev-parse", "HEAD")
    if _workspace_git(resolved, "rev-parse", "--abbrev-ref", "HEAD") != "HEAD":
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter workspace is not detached")
    status = _workspace_git(resolved, "status", "--porcelain=v1", "--untracked-files=all")
    if _workspace_git(resolved, "remote"):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter workspace retains a remote")
    if os.path.lexists(git_dir / "objects" / "info" / "alternates"):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter workspace shares a Git object store")
    from .workspace import canonical_path_digest

    return WorkspaceLaunchEvidence(
        resolved, canonical_path_digest(resolved), head, status, workspace_content_digest(resolved),
    )


def workspace_content_digest(path: Path) -> str:
    """Digest every regular working-tree byte, excluding separately checked Git metadata."""
    if not isinstance(path, Path) or not path.is_absolute():
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "workspace content path is invalid")
    root = path.resolve(strict=True)
    entries: list[dict[str, object]] = []
    for item in sorted(root.rglob("*"), key=lambda candidate: candidate.relative_to(root).as_posix()):
        relative = item.relative_to(root)
        if relative.parts and relative.parts[0] == ".git":
            continue
        if item.is_symlink() or getattr(os.lstat(item), "st_file_attributes", 0) & 0x400:
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "workspace contains a substituted path")
        if item.is_dir():
            continue
        if not item.is_file():
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "workspace contains an unsupported entry")
        entries.append(_content_entry(item, relative.as_posix()))
    config = root / ".git" / "config"
    if not config.is_file() or config.is_symlink() or getattr(os.lstat(config), "st_file_attributes", 0) & 0x400:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "workspace Git configuration is unavailable")
    entries.append(_content_entry(config, ".git/config"))
    return canonical_digest({"schema_version": "worker-lab-workspace-content:v1", "files": entries})


def _content_entry(path: Path, relative_path: str) -> dict[str, object]:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65_536), b""):
                digest.update(chunk)
    except OSError as exc:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "workspace content cannot be read") from exc
    return {"path": relative_path, "size": path.stat().st_size, "digest": "sha256:" + digest.hexdigest()}


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 71 and value.startswith("sha256:") and all(
        item in "0123456789abcdef" for item in value[7:]
    )


def _workspace_git(root: Path, *arguments: str) -> str:
    environment = {
        "PATH": os.environ.get("PATH", ""), "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
    }
    try:
        process = subprocess.run(
            ["git", "-c", f"core.hooksPath={os.devnull}", "-c", "credential.helper=", *arguments],
            cwd=root, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter workspace Git check failed") from exc
    if process.returncode != 0:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter workspace Git check failed")
    return process.stdout.strip()


def _path_key(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


def _kernel32():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
    kernel32.SetHandleInformation.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
    kernel32.QueryInformationJobObject.restype = wintypes.BOOL
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE, ctypes.POINTER(_FILETIME), ctypes.POINTER(_FILETIME), ctypes.POINTER(_FILETIME), ctypes.POINTER(_FILETIME)]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32




def _process_creation_time(handle, kernel32) -> int:
    created, exited, kernel, user = _FILETIME(), _FILETIME(), _FILETIME(), _FILETIME()
    if not kernel32.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user)):
        raise LabValidationError("INTEGRATION_PROCESS_IDENTITY_INVALID", "could not read process creation time")
    return (created.dwHighDateTime << 32) | created.dwLowDateTime


class _STARTUPINFOW(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
        *[(name, wintypes.DWORD) for name in ("dwX", "dwY", "dwXSize", "dwYSize",
          "dwXCountChars", "dwYCountChars", "dwFillAttribute", "dwFlags")],
        ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p), ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]


class _STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [("StartupInfo", _STARTUPINFOW), ("lpAttributeList", ctypes.c_void_p)]


class _PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
               ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]


class OwnedWindowsProcess:
    """Create suspended, atomically in a kill-on-close job; never launch then assign.

    Windows 10+ JOB_LIST closes the process-creation/assignment crash window.
    The parent exclusively owns the non-inheritable job handle. File handles are
    the only inherited handles; all descendants remain in the same lifetime job.
    This manages lifetime, not filesystem/network/account-permission isolation.
    """

    def __init__(self, argv, *, cwd: Path, environment: dict[str, str], stdin, stdout, stderr):
        if os.name != "nt":
            raise LabValidationError("INTEGRATION_RUNTIME_FORBIDDEN", "Windows Job Objects required")
        import msvcrt
        self.kernel = kernel = _kernel32()
        self.job = self.process = self.thread = None
        kernel.InitializeProcThreadAttributeList.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)]
        kernel.UpdateProcThreadAttribute.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]
        kernel.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
        kernel.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wintypes.BOOL,
            wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(_STARTUPINFOEXW), ctypes.POINTER(_PROCESS_INFORMATION)]
        kernel.ResumeThread.argtypes = [wintypes.HANDLE]
        kernel.ResumeThread.restype = wintypes.DWORD
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        handles = [msvcrt.get_osfhandle(f.fileno()) for f in (stdin, stdout, stderr)]
        attributes = None
        attributes_initialized = False
        try:
            self.job = kernel.CreateJobObjectW(None, None)
            self._require(self.job)
            self._require(kernel.SetHandleInformation(self.job, HANDLE_FLAG_INHERIT, 0))
            limits = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            self._require(kernel.SetInformationJobObject(self.job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
                ctypes.byref(limits), ctypes.sizeof(limits)))
            size = ctypes.c_size_t()
            kernel.InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(size))
            attributes = ctypes.create_string_buffer(size.value)
            self._require(kernel.InitializeProcThreadAttributeList(attributes, 2, 0, ctypes.byref(size)))
            attributes_initialized = True
            inherited = (wintypes.HANDLE * 3)(*handles)
            jobs = (wintypes.HANDLE * 1)(self.job)
            for handle in handles:
                self._require(kernel.SetHandleInformation(handle, HANDLE_FLAG_INHERIT, HANDLE_FLAG_INHERIT))
            self._require(kernel.UpdateProcThreadAttribute(attributes, 0, 0x00020002, inherited, ctypes.sizeof(inherited), None, None))
            self._require(kernel.UpdateProcThreadAttribute(attributes, 0, 0x0002000D, jobs, ctypes.sizeof(jobs), None, None))
            startup = _STARTUPINFOEXW()
            startup.StartupInfo.cb = ctypes.sizeof(startup)
            startup.StartupInfo.dwFlags = 0x100  # STARTF_USESTDHANDLES
            startup.StartupInfo.hStdInput, startup.StartupInfo.hStdOutput, startup.StartupInfo.hStdError = handles
            startup.lpAttributeList = ctypes.addressof(attributes)
            info = _PROCESS_INFORMATION()
            command = ctypes.create_unicode_buffer(subprocess.list2cmdline(list(argv)))
            env = ctypes.create_unicode_buffer("\0".join(f"{k}={v}" for k, v in sorted(environment.items(), key=lambda item: item[0].upper())) + "\0\0")
            # CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT | EXTENDED_STARTUPINFO_PRESENT | CREATE_NO_WINDOW
            self._require(kernel.CreateProcessW(str(argv[0]), command, None, None, True, 0x08080404,
                env, str(cwd), ctypes.byref(startup), ctypes.byref(info)))
            self.process, self.thread, self.pid = info.hProcess, info.hThread, info.dwProcessId
            self.identity = windows_process_identity(self.pid, _process_creation_time(self.process, kernel))
        except BaseException:
            self.close()
            raise
        finally:
            for handle in handles:
                kernel.SetHandleInformation(handle, HANDLE_FLAG_INHERIT, 0)
            if attributes_initialized:
                kernel.DeleteProcThreadAttributeList(attributes)

    @staticmethod
    def _require(ok):
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())

    def resume(self):
        if self.kernel.ResumeThread(self.thread) == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())

    def poll(self):
        state = self.kernel.WaitForSingleObject(self.process, 0)
        if state == 258:
            return None
        self._require(state == 0)
        code = wintypes.DWORD()
        self._require(self.kernel.GetExitCodeProcess(self.process, ctypes.byref(code)))
        return code.value

    def active_count(self):
        info = _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
        self._require(self.kernel.QueryInformationJobObject(self.job, JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS,
            ctypes.byref(info), ctypes.sizeof(info), None))
        return info.ActiveProcesses

    def terminate(self):
        self._require(self.kernel.TerminateJobObject(self.job, 1))

    def close(self):
        # Closing the job also covers construction/recording exceptions and crashes.
        for field in ("job", "thread", "process"):
            handle = getattr(self, field, None)
            if handle:
                self.kernel.CloseHandle(handle)
                setattr(self, field, None)






