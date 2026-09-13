from __future__ import annotations

import ctypes
import hashlib
import os
import subprocess
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Callable

from .errors import LabValidationError
from .canonical import canonical_digest
from .integration_v3 import InvocationRecordV3
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


class WindowsJobAdapterRunner:
    """Run one fixed adapter command in a non-inheritable kill-on-close Job Object."""

    def __init__(
        self,
        store: ProcessCustodyStore,
        *,
        invocation: InvocationRecordV3,
        timeout_seconds: int,
        workspace_path: Path,
        stdout_limit: int = 131_072,
        stderr_limit: int = 16_384,
        now: Now | None = None,
        kernel32_factory: Callable[[], object] | None = None,
        process_launcher: Callable[..., subprocess.Popen[bytes]] | None = None,
        creation_time_reader: Callable[[object, object], int] | None = None,
        active_process_waiter: Callable[[object, object], int] | None = None,
        platform_name: str | None = None,
        reader_join_timeout: float = 10.0,
        workspace_inspector: WorkspaceInspector | None = None,
    ) -> None:
        if timeout_seconds <= 0 or stdout_limit <= 0 or stderr_limit <= 0:
            raise LabValidationError("INTEGRATION_RUNTIME_FORBIDDEN", "process limits must be positive")
        if not isinstance(invocation, InvocationRecordV3) or invocation.source_state is None:
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "a Git-backed V3 invocation is required")
        self.store = store
        self.invocation_id = invocation.invocation_id
        self.invocation_digest = invocation.identity_digest()
        self.timeout_seconds = timeout_seconds
        self.stdout_limit = stdout_limit
        self.stderr_limit = stderr_limit
        self.workspace_path = workspace_path
        self.workspace_path_digest = invocation.source_state.workspace_path_digest
        self.starting_commit = invocation.source_state.base_commit
        self.now = now or _utc_now
        self.kernel32_factory = kernel32_factory or _kernel32
        self.process_launcher = process_launcher or subprocess.Popen
        self.creation_time_reader = creation_time_reader or _process_creation_time
        self.active_process_waiter = active_process_waiter or _wait_for_zero_active
        self.platform_name = os.name if platform_name is None else platform_name
        self.reader_join_timeout = reader_join_timeout
        self.workspace_inspector = workspace_inspector or inspect_launch_workspace

    def __call__(self, command: tuple[str, ...], payload: bytes) -> bytes:
        if self.platform_name != "nt":
            raise LabValidationError("INTEGRATION_RUNTIME_FORBIDDEN", "Windows Job Objects are required")
        if not command or not all(isinstance(item, str) and item for item in command):
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter command is invalid")
        if not isinstance(payload, bytes) or not payload:
            raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter request is invalid")

        workspace = self.workspace_inspector(self.workspace_path)
        if (
            not isinstance(workspace, WorkspaceLaunchEvidence)
            or _path_key(workspace.workspace_path) != _path_key(self.workspace_path)
            or workspace.workspace_path_digest != self.workspace_path_digest
            or workspace.observed_head != self.starting_commit
            or workspace.status != ""
            or not _is_digest(workspace.content_digest)
        ):
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter workspace identity differs")

        kernel32 = self.kernel32_factory()
        controller_pid = os.getpid()
        controller_time = self.creation_time_reader(kernel32.GetCurrentProcess(), kernel32)
        backend = WindowsJobCustodyBackend()
        custody = ProcessCustodyRecord.from_mapping({
            "schema_version": PROCESS_CUSTODY_SCHEMA,
            "invocation_digest": self.invocation_digest,
            "invocation_id": self.invocation_id,
            "backend_id": backend.backend_id,
            "controller_identity": windows_process_identity(controller_pid, controller_time),
            "worker_identity": None,
            "workspace_content_digest": workspace.content_digest,
            "state": "PREPARED",
            "request_sent": False,
            "exit_code": None,
            "active_workload_count": None,
            "absence_evidence_digest": None,
            "absence_verified_at": None,
            "first_failure": None,
        })
        self.store.create(custody)

        try:
            job = _create_job(kernel32)
        except LabValidationError:
            uncertain = transition_custody(
                custody, CustodyState.UNCERTAIN, exit_code=None, active_workload_count=None,
                first_failure="INTEGRATION_CONTAINMENT_FAILED",
            )
            self.store.save_transition(uncertain, expected_digest=custody.digest())
            raise
        process: subprocess.Popen[bytes] | None = None
        stdout = bytearray()
        stderr = bytearray()
        overflow = threading.Event()
        overflow_name: list[str] = []
        termination_lock = threading.Lock()
        persisted = custody
        finalized = False

        def terminate_job() -> None:
            with termination_lock:
                if job:
                    kernel32.TerminateJobObject(job, 1)

        try:
            process = self.process_launcher(
                list(command), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                shell=False, close_fds=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                cwd=workspace.workspace_path,
            )
            if not kernel32.AssignProcessToJobObject(job, wintypes.HANDLE(int(process._handle))):
                process.terminate()
                process.wait(timeout=5)
                try:
                    active = self.active_process_waiter(job, kernel32)
                except LabValidationError:
                    active = None
                target = CustodyState.TERMINATED if active == 0 else CustodyState.UNCERTAIN
                failed = transition_custody(
                    custody, target, exit_code=process.returncode, active_workload_count=active,
                    first_failure="INTEGRATION_CONTAINMENT_FAILED",
                )
                self.store.save_transition(failed, expected_digest=custody.digest())
                if active == 0:
                    self._verify_absence(failed, backend)
                raise LabValidationError("INTEGRATION_CONTAINMENT_FAILED", "adapter job assignment failed")

            adapter_time = self.creation_time_reader(wintypes.HANDLE(int(process._handle)), kernel32)
            assigned = transition_custody(
                custody,
                CustodyState.ASSIGNED,
                worker_identity=windows_process_identity(process.pid, adapter_time),
            )
            self.store.save_transition(assigned, expected_digest=custody.digest())
            persisted = assigned

            assert process.stdout is not None and process.stderr is not None and process.stdin is not None
            reader_failure: list[tuple[str, BaseException]] = []
            failure_lock = threading.Lock()
            readers = [
                threading.Thread(
                    target=_drain_bounded,
                    args=(process.stdout, stdout, self.stdout_limit, "stdout", overflow, overflow_name, terminate_job, reader_failure, failure_lock),
                    daemon=True,
                ),
                threading.Thread(
                    target=_drain_bounded,
                    args=(process.stderr, stderr, self.stderr_limit, "stderr", overflow, overflow_name, terminate_job, reader_failure, failure_lock),
                    daemon=True,
                ),
            ]
            for reader in readers:
                reader.start()

            dispatching = transition_custody(assigned, CustodyState.DISPATCHING)
            self.store.save_transition(dispatching, expected_digest=assigned.digest())
            persisted = dispatching
            process.stdin.write(payload)
            process.stdin.close()

            timed_out = False
            try:
                process.wait(timeout=self.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                terminate_job()
                process.wait(timeout=10)
            for reader in readers:
                reader.join(timeout=self.reader_join_timeout)
            if any(reader.is_alive() for reader in readers):
                terminate_job()
                raise LabValidationError("INTEGRATION_OUTCOME_UNCERTAIN", "adapter output reader did not stop")

            active = self.active_process_waiter(job, kernel32)
            failure = None
            if timed_out:
                failure = "INTEGRATION_TIMEOUT"
            elif reader_failure:
                failure = "INTEGRATION_RESULT_INVALID"
            elif overflow.is_set():
                failure = f"INTEGRATION_{overflow_name[0].upper()}_LIMIT" if overflow_name else "INTEGRATION_RESULT_INVALID"
            elif process.returncode != 0:
                failure = "INTEGRATION_EXECUTION_FAILED"

            target = CustodyState.TERMINATED if failure else CustodyState.EXITED
            ended = transition_custody(
                dispatching, target, exit_code=process.returncode,
                active_workload_count=active, first_failure=failure,
            )
            self.store.save_transition(ended, expected_digest=dispatching.digest())
            persisted = ended
            if active != 0:
                raise LabValidationError("INTEGRATION_OUTCOME_UNCERTAIN", "adapter process tree remains active")
            self._verify_absence(ended, backend)
            finalized = True
            if failure:
                code = "INTEGRATION_RESULT_INVALID" if (overflow.is_set() or reader_failure) else failure
                raise LabValidationError(code, "contained adapter execution failed")
            return bytes(stdout)
        except BaseException:
            if process is not None and process.poll() is None:
                terminate_job()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
            if not finalized and persisted.state not in {
                CustodyState.ABSENCE_VERIFIED, CustodyState.EXITED, CustodyState.TERMINATED,
            }:
                try:
                    active = self.active_process_waiter(job, kernel32)
                except LabValidationError:
                    active = None
                target = CustodyState.TERMINATED if active == 0 else CustodyState.UNCERTAIN
                first_failure = (
                    "INTEGRATION_CONTAINMENT_FAILED"
                    if persisted.state is CustodyState.PREPARED
                    else "INTEGRATION_OUTCOME_UNCERTAIN"
                )
                try:
                    failed = transition_custody(
                        persisted, target, exit_code=(process.returncode if process is not None else None),
                        active_workload_count=active, first_failure=first_failure,
                    )
                    self.store.save_transition(failed, expected_digest=persisted.digest())
                    if active == 0:
                        self._verify_absence(failed, backend)
                except LabValidationError:
                    pass
            raise
        finally:
            if process is not None and process.poll() is None:
                terminate_job()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
            kernel32.CloseHandle(job)

    def _verify_absence(
        self,
        record: ProcessCustodyRecord,
        backend: "WindowsJobCustodyBackend",
    ) -> ProcessCustodyRecord:
        verified = transition_custody(
            record,
            CustodyState.ABSENCE_VERIFIED,
            active_workload_count=0,
            absence_evidence_digest=backend.absence_evidence_digest(
                record, basis="job-accounting-zero",
            ),
            absence_verified_at=self.now(),
        )
        self.store.save_transition(verified, expected_digest=record.digest())
        return verified




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


def _create_job(kernel32):
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise LabValidationError("INTEGRATION_CONTAINMENT_FAILED", "could not create Job Object")
    if not kernel32.SetHandleInformation(job, HANDLE_FLAG_INHERIT, 0):
        kernel32.CloseHandle(job)
        raise LabValidationError("INTEGRATION_CONTAINMENT_FAILED", "could not protect Job Object handle")
    limits = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(
        job,
        JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
        ctypes.byref(limits),
        ctypes.sizeof(limits),
    ):
        kernel32.CloseHandle(job)
        raise LabValidationError("INTEGRATION_CONTAINMENT_FAILED", "could not configure Job Object")
    return job




def _process_creation_time(handle, kernel32) -> int:
    created, exited, kernel, user = _FILETIME(), _FILETIME(), _FILETIME(), _FILETIME()
    if not kernel32.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user)):
        raise LabValidationError("INTEGRATION_PROCESS_IDENTITY_INVALID", "could not read process creation time")
    return (created.dwHighDateTime << 32) | created.dwLowDateTime


def _active_process_count(job, kernel32) -> int:
    info = _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
    if not kernel32.QueryInformationJobObject(
        job,
        JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
        None,
    ):
        raise LabValidationError("INTEGRATION_CONTAINMENT_FAILED", "could not query Job Object")
    return int(info.ActiveProcesses)


def _wait_for_zero_active(job, kernel32, timeout: float = 5.0) -> int:
    deadline = time.monotonic() + timeout
    while True:
        active = _active_process_count(job, kernel32)
        if active == 0 or time.monotonic() >= deadline:
            return active
        time.sleep(0.01)


def _drain_bounded(
    stream: BinaryIO,
    target: bytearray,
    limit: int,
    name: str,
    overflow: threading.Event,
    overflow_name: list[str],
    terminate: Callable[[], None],
    failure: list[tuple[str, BaseException]],
    failure_lock: threading.Lock,
) -> None:
    try:
        while True:
            chunk = stream.read(4096)
            if not chunk:
                return
            remaining = limit - len(target)
            if remaining > 0:
                target.extend(chunk[:remaining])
            if len(chunk) > remaining:
                if not overflow.is_set():
                    overflow_name.append(name)
                    overflow.set()
                    terminate()
    except Exception as exc:
        with failure_lock:
            if not failure:
                failure.append((name, exc))
        terminate()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")





