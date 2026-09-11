import ctypes
import os
import subprocess
import sys
import threading

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.process_custody import CustodyState, ProcessCustodyStore, transition_custody
from worker_lab.windows_job import (
    _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION,
    WindowsJobAdapterRunner,
    WorkspaceLaunchEvidence,
    inspect_launch_workspace,
)
from tests.test_integration import record


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows Job Object contract")
DIGEST = "sha256:" + "a" * 64


def runner(tmp_path, **updates):
    values = {
        "invocation": record(),
        "timeout_seconds": 5, "now": lambda: "2026-08-28T00:00:01Z",
        "workspace_path": tmp_path,
        "workspace_inspector": lambda path: WorkspaceLaunchEvidence(path, DIGEST, "a" * 40, "", DIGEST),
    }
    values.update(updates)
    store = updates.pop("store", None) or ProcessCustodyStore(tmp_path / "state")
    values.pop("store", None)
    return WindowsJobAdapterRunner(store, **values), store


def test_workspace_identity_failure_prevents_custody_and_launch(tmp_path):
    launched = []
    item, store = runner(
        tmp_path,
        workspace_inspector=lambda path: WorkspaceLaunchEvidence(path, DIGEST, "b" * 40, "", DIGEST),
        process_launcher=lambda *args, **kwargs: launched.append((args, kwargs)),
    )
    with pytest.raises(LabValidationError) as error:
        item((sys.executable, "-c", "pass"), b"request")
    assert error.value.code == "INTEGRATION_IDENTITY_INVALID"
    assert not launched
    with pytest.raises(LabValidationError) as missing:
        store.read("INVOCATION-001")
    assert missing.value.code == "STORAGE_RECORD_MISSING"


def test_launch_workspace_inspector_seals_exact_clean_git_root(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("fixture\n", encoding="utf-8")
    (workspace / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    for command in (
        ["git", "init"], ["git", "config", "core.autocrlf", "false"],
            ["git", "config", "user.email", "fixture@example.com"],
            ["git", "config", "user.name", "Fixture"], ["git", "add", "."],
            ["git", "commit", "-m", "fixture"],
            ["git", "checkout", "--detach"],
        ):
        subprocess.run(command, cwd=workspace, check=True, capture_output=True)
    evidence = inspect_launch_workspace(workspace)
    assert evidence.workspace_path == workspace.resolve()
    assert evidence.observed_head == subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=workspace, check=True, capture_output=True, text=True,
    ).stdout.strip()
    assert evidence.status == ""
    (workspace / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    ignored = inspect_launch_workspace(workspace)
    assert ignored.status == ""
    assert ignored.content_digest != evidence.content_digest
    subprocess.run(["git", "config", "user.name", "Changed"], cwd=workspace, check=True, capture_output=True)
    assert inspect_launch_workspace(workspace).content_digest != ignored.content_digest
    (workspace / "unexpected.txt").write_text("dirty\n", encoding="utf-8")
    assert inspect_launch_workspace(workspace).status


class FakeKernel32:
    """Deterministic native seam standing in for the real kernel32 Job Object API."""

    def __init__(
        self, *, create_ok=True, assign_ok=True, active_count=0, query_ok=True,
    ):
        self.create_ok = create_ok
        self.assign_ok = assign_ok
        self.active_count = active_count
        self.query_ok = query_ok
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
        if not self.query_ok:
            return 0
        ctypes.cast(buffer, ctypes.POINTER(_JOBOBJECT_BASIC_ACCOUNTING_INFORMATION)).contents.ActiveProcesses = self.active_count
        return 1

    def CloseHandle(self, *_):
        return 1


class FakeStream:
    """A binary stream that can emit bytes then optionally fail or block forever."""

    def __init__(self, chunks=(), exc=None, block=None):
        self._chunks = list(chunks)
        self._exc = exc
        self._block = block

    def read(self, size):
        if self._chunks:
            return self._chunks.pop(0)
        if self._block is not None:
            self._block.wait()
            return b""
        if self._exc is not None:
            raise self._exc
        return b""


class FakeStdin:
    def __init__(self, exc=None):
        self.exc = exc
        self.written = []
        self.closed = False

    def write(self, data):
        if self.exc is not None:
            raise self.exc
        self.written.append(data)

    def close(self):
        self.closed = True


class FakeProcess:
    """A minimal stand-in for subprocess.Popen used to drive deterministic tests."""

    def __init__(
        self, *, stdout=None, stderr=None, stdin=None, pid=42, handle=4242,
        wait_exc=None, returncode=0,
    ):
        self.stdout = stdout or FakeStream()
        self.stderr = stderr or FakeStream()
        self.stdin = stdin or FakeStdin()
        self.pid = pid
        self._handle = handle
        self.returncode = returncode
        self._wait_exc = wait_exc
        self._terminated = False

    def wait(self, timeout=None):
        if self._wait_exc is not None:
            exc, self._wait_exc = self._wait_exc, None
            raise exc

    def terminate(self):
        self._terminated = True

    def poll(self):
        return self.returncode if self._terminated else None


class FailingCustodyStore:
    """Wraps a real store and fails once for a chosen target custody state."""

    def __init__(self, inner, *, fail_on_states=()):
        self.inner = inner
        self.fail_on_states = set(fail_on_states)
        self.saved_states: list[str] = []

    def create(self, record):
        self.inner.create(record)

    def read(self, invocation_id):
        return self.inner.read(invocation_id)

    def save_transition(self, updated, *, expected_digest):
        state = str(updated.state)
        if state in self.fail_on_states:
            self.fail_on_states.discard(state)
            raise LabValidationError("STORAGE_WRITE_FAILED", f"simulated persistence failure for {state}")
        self.saved_states.append(state)
        self.inner.save_transition(updated, expected_digest=expected_digest)


def test_job_runner_assigns_before_request_and_proves_normal_absence(tmp_path):
    item, store = runner(tmp_path)
    command = (sys.executable, "-I", "-B", "-c",
               "import subprocess,sys; sys.stdin.buffer.read(); "
               "child=subprocess.Popen([sys.executable,'-I','-B','-c','pass']); child.wait(); "
               "sys.stdout.buffer.write(b'{}')")
    assert item(command, b"request") == b"{}"
    custody = store.read("INVOCATION-001")
    assert custody.state is CustodyState.ABSENCE_VERIFIED
    assert custody.request_sent and custody.active_workload_count == 0


def test_job_runner_terminates_tree_on_stream_overflow(tmp_path):
    item, store = runner(tmp_path, stdout_limit=64)
    command = (sys.executable, "-I", "-B", "-c",
               "import sys,time; sys.stdin.buffer.read(); sys.stdout.buffer.write(b'x'*4096); sys.stdout.flush(); time.sleep(30)")
    with pytest.raises(LabValidationError) as error:
        item(command, b"request")
    assert error.value.code == "INTEGRATION_RESULT_INVALID"
    assert store.read("INVOCATION-001").active_workload_count == 0


def test_job_runner_terminates_inert_child_tree_on_timeout(tmp_path):
    item, store = runner(tmp_path, timeout_seconds=1)
    child = "import time; time.sleep(30)"
    parent = ("import subprocess,sys,time; sys.stdin.buffer.read(); "
              f"subprocess.Popen([sys.executable,'-I','-B','-c',{child!r}]); time.sleep(30)")
    with pytest.raises(LabValidationError) as error:
        item((sys.executable, "-I", "-B", "-c", parent), b"request")
    assert error.value.code == "CODEX_TIMEOUT"
    custody = store.read("INVOCATION-001")
    assert custody.state is CustodyState.ABSENCE_VERIFIED
    assert custody.active_workload_count == 0


def test_job_creation_failure_prevents_launch_and_never_fabricates_absence(tmp_path):
    class FailedJobCreate:
        def GetCurrentProcess(self):
            return object()

        def CreateJobObjectW(self, *_):
            return 0

    launched = False

    def launch(*_, **__):
        nonlocal launched
        launched = True
        raise AssertionError("adapter must not launch when Job Object creation fails")

    item, store = runner(
        tmp_path, platform_name="nt", kernel32_factory=lambda: FailedJobCreate(),
        process_launcher=launch, creation_time_reader=lambda *_: 1,
    )
    with pytest.raises(LabValidationError) as error:
        item(("inert-adapter",), b"request")
    assert error.value.code == "INTEGRATION_CONTAINMENT_FAILED"
    custody = store.read("INVOCATION-001")
    assert not launched
    assert custody.state is CustodyState.UNCERTAIN
    assert not custody.request_sent
    assert custody.active_workload_count is None


def test_adapter_launch_failure_is_non_dispatching_uncertainty(tmp_path):
    item, store = runner(
        tmp_path, platform_name="nt", kernel32_factory=lambda: FakeKernel32(active_count=0),
        process_launcher=lambda *_, **__: (_ for _ in ()).throw(OSError("inert launch failure")),
        creation_time_reader=lambda *_: 1,
    )
    with pytest.raises(OSError):
        item(("inert-adapter",), b"request")
    custody = store.read("INVOCATION-001")
    assert custody.state is CustodyState.ABSENCE_VERIFIED
    assert not custody.request_sent
    assert custody.active_workload_count == 0
    assert custody.first_failure == "INTEGRATION_CONTAINMENT_FAILED"


def test_assignment_failure_terminates_before_request_with_independent_zero(tmp_path):
    stdin = FakeStdin()
    process = FakeProcess(stdin=stdin)
    item, store = runner(
        tmp_path, platform_name="nt", kernel32_factory=lambda: FakeKernel32(assign_ok=False, active_count=0),
        process_launcher=lambda *_, **__: process, creation_time_reader=lambda *_: 1,
    )
    with pytest.raises(LabValidationError) as error:
        item(("inert-adapter",), b"request")
    assert error.value.code == "INTEGRATION_CONTAINMENT_FAILED"
    assert not stdin.written
    custody = store.read("INVOCATION-001")
    assert custody.state is CustodyState.ABSENCE_VERIFIED
    assert custody.active_workload_count == 0
    assert process._terminated


def test_assignment_failure_with_failed_query_leaves_uncertain(tmp_path):
    process = FakeProcess()
    item, store = runner(
        tmp_path, platform_name="nt",
        kernel32_factory=lambda: FakeKernel32(assign_ok=False, query_ok=False),
        process_launcher=lambda *_, **__: process, creation_time_reader=lambda *_: 1,
    )
    with pytest.raises(LabValidationError):
        item(("inert-adapter",), b"request")
    custody = store.read("INVOCATION-001")
    assert custody.state is CustodyState.UNCERTAIN
    assert custody.active_workload_count is None


def test_adapter_creation_time_capture_failure_terminates_and_preserves_failure(tmp_path):
    stdin = FakeStdin()
    process = FakeProcess(stdin=stdin)
    kernel = FakeKernel32(active_count=0)
    calls = {"count": 0}

    def creation_time_reader(*_):
        calls["count"] += 1
        if calls["count"] == 1:
            return 1
        raise LabValidationError("INTEGRATION_PROCESS_IDENTITY_INVALID", "simulated capture failure")

    item, store = runner(
        tmp_path, platform_name="nt", kernel32_factory=lambda: kernel,
        process_launcher=lambda *_, **__: process, creation_time_reader=creation_time_reader,
    )
    with pytest.raises(LabValidationError):
        item(("inert-adapter",), b"request")
    assert not stdin.written
    custody = store.read("INVOCATION-001")
    assert custody.state is CustodyState.ABSENCE_VERIFIED
    assert custody.active_workload_count == 0
    assert custody.first_failure == "INTEGRATION_CONTAINMENT_FAILED"
    assert kernel.terminated


def test_assigned_persistence_failure_preserves_first_failure(tmp_path):
    stdin = FakeStdin()
    process = FakeProcess(stdin=stdin)
    real_store = ProcessCustodyStore(tmp_path / "state")
    failing = FailingCustodyStore(real_store, fail_on_states={"ASSIGNED"})
    item, _ = runner(
        tmp_path, store=failing, platform_name="nt", kernel32_factory=lambda: FakeKernel32(active_count=0),
        process_launcher=lambda *_, **__: process, creation_time_reader=lambda *_: 1,
    )
    with pytest.raises(LabValidationError) as error:
        item(("inert-adapter",), b"request")
    assert error.value.code == "STORAGE_WRITE_FAILED"
    assert not stdin.written
    custody = real_store.read("INVOCATION-001")
    assert custody.state is CustodyState.ABSENCE_VERIFIED
    assert custody.active_workload_count == 0
    assert custody.first_failure == "INTEGRATION_CONTAINMENT_FAILED"


def test_dispatching_persistence_failure_preserves_first_failure_and_never_dispatches(tmp_path):
    stdin = FakeStdin()
    process = FakeProcess(stdin=stdin)
    real_store = ProcessCustodyStore(tmp_path / "state")
    failing = FailingCustodyStore(real_store, fail_on_states={"DISPATCHING"})
    item, _ = runner(
        tmp_path, store=failing, platform_name="nt", kernel32_factory=lambda: FakeKernel32(active_count=0),
        process_launcher=lambda *_, **__: process, creation_time_reader=lambda *_: 1,
    )
    with pytest.raises(LabValidationError) as error:
        item(("inert-adapter",), b"request")
    assert error.value.code == "STORAGE_WRITE_FAILED"
    assert not stdin.written
    custody = real_store.read("INVOCATION-001")
    # Request was never sent, so custody cannot claim verified absence; it must
    # remain the weaker TERMINATED evidence instead of a fabricated success shape.
    assert custody.state is CustodyState.TERMINATED
    assert custody.active_workload_count == 0
    assert custody.first_failure == "INTEGRATION_OUTCOME_UNCERTAIN"
    assert failing.saved_states == ["ASSIGNED", "TERMINATED"]


def test_standard_input_write_failure_ends_in_verified_absence(tmp_path):
    stdin = FakeStdin(exc=OSError("broken pipe"))
    process = FakeProcess(stdin=stdin)
    item, store = runner(
        tmp_path, platform_name="nt", kernel32_factory=lambda: FakeKernel32(active_count=0),
        process_launcher=lambda *_, **__: process, creation_time_reader=lambda *_: 1,
    )
    with pytest.raises(OSError):
        item(("inert-adapter",), b"request")
    custody = store.read("INVOCATION-001")
    assert custody.state is CustodyState.ABSENCE_VERIFIED
    assert custody.active_workload_count == 0
    assert custody.first_failure == "INTEGRATION_OUTCOME_UNCERTAIN"


def test_simulated_interruption_terminates_and_verifies_absence(tmp_path):
    process = FakeProcess(wait_exc=KeyboardInterrupt())
    kernel = FakeKernel32(active_count=0)
    item, store = runner(
        tmp_path, platform_name="nt", kernel32_factory=lambda: kernel,
        process_launcher=lambda *_, **__: process, creation_time_reader=lambda *_: 1,
    )
    with pytest.raises(KeyboardInterrupt):
        item(("inert-adapter",), b"request")
    custody = store.read("INVOCATION-001")
    assert custody.state is CustodyState.ABSENCE_VERIFIED
    assert custody.active_workload_count == 0
    assert kernel.terminated


def test_reader_exception_is_authoritative_and_never_returns_partial_success(tmp_path):
    stdout = FakeStream(chunks=[b'{"partial": true}'], exc=OSError("stdout read failure"))
    process = FakeProcess(stdout=stdout, stderr=FakeStream())
    kernel = FakeKernel32(active_count=0)
    item, store = runner(
        tmp_path, platform_name="nt", kernel32_factory=lambda: kernel,
        process_launcher=lambda *_, **__: process, creation_time_reader=lambda *_: 1,
    )
    with pytest.raises(LabValidationError) as error:
        item(("inert-adapter",), b"request")
    assert error.value.code == "INTEGRATION_RESULT_INVALID"
    custody = store.read("INVOCATION-001")
    assert custody.state is CustodyState.ABSENCE_VERIFIED
    assert custody.active_workload_count == 0
    assert custody.first_failure == "INTEGRATION_RESULT_INVALID"
    assert kernel.terminated


def test_stderr_reader_exception_is_also_authoritative(tmp_path):
    stderr = FakeStream(exc=OSError("stderr read failure"))
    process = FakeProcess(stdout=FakeStream(chunks=[b"{}"]), stderr=stderr)
    item, store = runner(
        tmp_path, platform_name="nt", kernel32_factory=lambda: FakeKernel32(active_count=0),
        process_launcher=lambda *_, **__: process, creation_time_reader=lambda *_: 1,
    )
    with pytest.raises(LabValidationError) as error:
        item(("inert-adapter",), b"request")
    assert error.value.code == "INTEGRATION_RESULT_INVALID"


def test_reader_that_never_exits_is_uncertain_not_success(tmp_path):
    block = threading.Event()
    process = FakeProcess(stdout=FakeStream(block=block), stderr=FakeStream())
    item, store = runner(
        tmp_path, platform_name="nt", kernel32_factory=lambda: FakeKernel32(active_count=0),
        process_launcher=lambda *_, **__: process, creation_time_reader=lambda *_: 1,
        reader_join_timeout=0.05,
    )
    with pytest.raises(LabValidationError) as error:
        item(("inert-adapter",), b"request")
    assert error.value.code == "INTEGRATION_OUTCOME_UNCERTAIN"
    block.set()


def test_active_process_query_failure_after_exit_leaves_uncertain(tmp_path):
    process = FakeProcess(stdout=FakeStream(chunks=[b"{}"]), stderr=FakeStream())
    item, store = runner(
        tmp_path, platform_name="nt", kernel32_factory=lambda: FakeKernel32(query_ok=False),
        process_launcher=lambda *_, **__: process, creation_time_reader=lambda *_: 1,
    )
    with pytest.raises(LabValidationError):
        item(("inert-adapter",), b"request")
    custody = store.read("INVOCATION-001")
    assert custody.state is CustodyState.UNCERTAIN
    assert custody.active_workload_count is None


def test_nonzero_active_count_after_exit_never_becomes_verified(tmp_path):
    process = FakeProcess(stdout=FakeStream(chunks=[b"{}"]), stderr=FakeStream())
    item, store = runner(
        tmp_path, platform_name="nt", kernel32_factory=lambda: FakeKernel32(active_count=1),
        process_launcher=lambda *_, **__: process, creation_time_reader=lambda *_: 1,
    )
    with pytest.raises(LabValidationError) as error:
        item(("inert-adapter",), b"request")
    assert error.value.code == "INTEGRATION_OUTCOME_UNCERTAIN"
    custody = store.read("INVOCATION-001")
    assert custody.state is CustodyState.EXITED
    assert custody.active_workload_count == 1


def test_terminal_persistence_failure_never_fabricates_verified_absence(tmp_path):
    process = FakeProcess(stdout=FakeStream(chunks=[b"{}"]), stderr=FakeStream())
    real_store = ProcessCustodyStore(tmp_path / "state")
    failing = FailingCustodyStore(real_store, fail_on_states={"ABSENCE_VERIFIED"})
    item, _ = runner(
        tmp_path, store=failing, platform_name="nt", kernel32_factory=lambda: FakeKernel32(active_count=0),
        process_launcher=lambda *_, **__: process, creation_time_reader=lambda *_: 1,
    )
    with pytest.raises(LabValidationError) as error:
        item(("inert-adapter",), b"request")
    assert error.value.code == "STORAGE_WRITE_FAILED"
    custody = real_store.read("INVOCATION-001")
    assert custody.state is CustodyState.EXITED
    assert custody.active_workload_count == 0
