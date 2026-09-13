import ctypes
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_integration_v3 import invocation, qualification
from worker_lab.errors import LabValidationError
from worker_lab.process_custody import CustodyState, ProcessCustodyStore
from worker_lab.provider_binding import create_provider_binding
from worker_lab.windows_job import (
    _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION,
    WindowsJobAdapterRunner,
    WorkspaceLaunchEvidence,
    inspect_launch_workspace,
)


DIGEST = "sha256:" + "a" * 64


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def test_launch_workspace_inspector_seals_exact_clean_git_root(tmp_path):
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    (workspace / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(workspace, "init")
    _git(workspace, "config", "core.autocrlf", "false")
    _git(workspace, "config", "user.email", "fixture@example.com")
    _git(workspace, "config", "user.name", "Fixture")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-m", "fixture")
    _git(workspace, "checkout", "--detach")
    evidence = inspect_launch_workspace(workspace)
    assert evidence.workspace_path == workspace
    assert evidence.observed_head == _git(workspace, "rev-parse", "HEAD")
    assert evidence.status == ""
    assert evidence.content_digest.startswith("sha256:")


class FakeKernel32:
    def __init__(self, *, create_ok=True, assign_ok=True, active_count=0):
        self.create_ok = create_ok
        self.assign_ok = assign_ok
        self.active_count = active_count
        self.terminated = False

    def GetCurrentProcess(self):
        return object()

    def CreateJobObjectW(self, *_):
        return 1 if self.create_ok else 0

    def SetHandleInformation(self, *_):
        return 1

    def SetInformationJobObject(self, *_):
        return 1

    def AssignProcessToJobObject(self, *_):
        return 1 if self.assign_ok else 0

    def TerminateJobObject(self, *_):
        self.terminated = True
        return 1

    def QueryInformationJobObject(self, job, info_class, buffer, size, _):
        ctypes.cast(
            buffer,
            ctypes.POINTER(_JOBOBJECT_BASIC_ACCOUNTING_INFORMATION),
        ).contents.ActiveProcesses = self.active_count
        return 1

    def CloseHandle(self, *_):
        return 1


class FakeStream:
    def __init__(self, chunks=()):
        self.chunks = list(chunks)

    def read(self, size):
        return self.chunks.pop(0) if self.chunks else b""


class FakeStdin:
    def __init__(self):
        self.written = []
        self.closed = False

    def write(self, value):
        self.written.append(value)

    def close(self):
        self.closed = True


class FakeProcess:
    def __init__(self, *, stdout=b"{}", returncode=0):
        self.stdout = FakeStream((stdout,))
        self.stderr = FakeStream()
        self.stdin = FakeStdin()
        self.pid = 42
        self._handle = 4242
        self.returncode = returncode
        self.terminated = False

    def wait(self, timeout=None):
        return self.returncode

    def terminate(self):
        self.terminated = True

    def poll(self):
        return self.returncode


def _runner(tmp_path, *, kernel=None, process=None, **updates):
    binding = create_provider_binding("BINDING-WINDOWS-0001", qualification())
    record = invocation(
        binding,
        state="DISPATCHING",
        authorized_by="controller-1",
        authorized_at="2026-09-11T02:00:00Z",
        source_state={
            "schema_version": "worker-lab-git-workspace-source-state:v1",
            "backend_id": "git-workspace:v1",
            "base_commit": "a" * 40,
            "workspace_receipt_digest": DIGEST,
            "workspace_root_digest": DIGEST,
            "workspace_path_digest": DIGEST,
        },
    )
    store = ProcessCustodyStore(tmp_path / "state")
    values = {
        "invocation": record,
        "timeout_seconds": 5,
        "workspace_path": tmp_path,
        "now": lambda: "2026-09-11T02:00:01Z",
        "platform_name": "nt",
        "kernel32_factory": lambda: kernel or FakeKernel32(),
        "process_launcher": lambda *args, **kwargs: process or FakeProcess(),
        "creation_time_reader": lambda *_: 1,
        "active_process_waiter": lambda *_: (kernel or FakeKernel32()).active_count,
        "workspace_inspector": lambda path: WorkspaceLaunchEvidence(
            path, DIGEST, "a" * 40, "", DIGEST
        ),
    }
    values.update(updates)
    return WindowsJobAdapterRunner(store, **values), store


def test_job_runner_persists_assignment_dispatch_and_absence(tmp_path):
    process = FakeProcess(stdout=b'{"ok":true}')
    runner, store = _runner(tmp_path, process=process)
    assert runner(("fixed-adapter",), b"request") == b'{"ok":true}'
    assert process.stdin.written == [b"request"]
    custody = store.read("INVOCATION-001")
    assert custody.state is CustodyState.ABSENCE_VERIFIED
    assert custody.request_sent is True
    assert custody.active_workload_count == 0


def test_job_creation_failure_never_launches_or_fabricates_absence(tmp_path):
    launched = False

    def launch(*_, **__):
        nonlocal launched
        launched = True
        raise AssertionError("must not launch")

    runner, store = _runner(
        tmp_path,
        kernel=FakeKernel32(create_ok=False),
        process_launcher=launch,
    )
    with pytest.raises(LabValidationError) as error:
        runner(("fixed-adapter",), b"request")
    assert error.value.code == "INTEGRATION_CONTAINMENT_FAILED"
    assert launched is False
    custody = store.read("INVOCATION-001")
    assert custody.state is CustodyState.UNCERTAIN
    assert custody.request_sent is False
    assert custody.active_workload_count is None


def test_job_assignment_failure_terminates_before_request(tmp_path):
    kernel = FakeKernel32(assign_ok=False)
    process = FakeProcess()
    runner, store = _runner(tmp_path, kernel=kernel, process=process)
    with pytest.raises(LabValidationError) as error:
        runner(("fixed-adapter",), b"request")
    assert error.value.code == "INTEGRATION_CONTAINMENT_FAILED"
    assert process.stdin.written == []
    assert process.terminated is True
    assert store.read("INVOCATION-001").state is CustodyState.ABSENCE_VERIFIED


def test_job_runner_refuses_success_while_workload_remains_active(tmp_path):
    kernel = FakeKernel32(active_count=1)
    runner, store = _runner(tmp_path, kernel=kernel)
    with pytest.raises(LabValidationError) as error:
        runner(("fixed-adapter",), b"request")
    assert error.value.code == "INTEGRATION_OUTCOME_UNCERTAIN"
    custody = store.read("INVOCATION-001")
    assert custody.state is CustodyState.EXITED
    assert custody.active_workload_count == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object integration")
def test_real_windows_job_contains_short_python_adapter(tmp_path):
    binding = create_provider_binding("BINDING-WINDOWS-REAL", qualification())
    record = invocation(
        binding,
        state="DISPATCHING",
        authorized_by="controller-1",
        authorized_at="2026-09-11T02:00:00Z",
        source_state={
            "schema_version": "worker-lab-git-workspace-source-state:v1",
            "backend_id": "git-workspace:v1",
            "base_commit": "a" * 40,
            "workspace_receipt_digest": DIGEST,
            "workspace_root_digest": DIGEST,
            "workspace_path_digest": DIGEST,
        },
    )
    store = ProcessCustodyStore(tmp_path / "state")
    runner = WindowsJobAdapterRunner(
        store,
        invocation=record,
        timeout_seconds=5,
        workspace_path=tmp_path,
        workspace_inspector=lambda path: WorkspaceLaunchEvidence(
            path, DIGEST, "a" * 40, "", DIGEST
        ),
    )
    response = runner(
        (
            sys.executable,
            "-I",
            "-B",
            "-c",
            "import sys; data=sys.stdin.buffer.read(); sys.stdout.buffer.write(data)",
        ),
        b'{"contained":true}',
    )
    assert response == b'{"contained":true}'
    assert store.read("INVOCATION-001").state is CustodyState.ABSENCE_VERIFIED
