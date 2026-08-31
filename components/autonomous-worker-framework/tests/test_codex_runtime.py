from pathlib import Path
from subprocess import CompletedProcess
import subprocess
import threading

import pytest

from tools.codex_runtime import (
    AUDITED_CODEX_VERSION,
    AUDITED_WINDOWS_SANDBOX,
    CodexRequest,
    CodexRuntimeError,
    codex_command,
    execute_codex_bounded,
    execute_codex,
    resolve_codex_executable,
    sanitized_codex_environment,
)


class _Stream:
    def __init__(self, chunks=(), exc=None, blocker=None):
        self.chunks = list(chunks)
        self.exc = exc
        self.blocker = blocker

    def read(self, _size):
        if self.chunks:
            return self.chunks.pop(0)
        if self.blocker is not None:
            self.blocker.wait()
            return b""
        if self.exc is not None:
            raise self.exc
        return b""


class _Stdin:
    def __init__(self):
        self.written = b""
        self.closed = False

    def write(self, value):
        self.written += value

    def close(self):
        self.closed = True


class _Process:
    def __init__(self, *, stdout=b"", stderr=b"", returncode=0, wait_error=None):
        self.stdin = _Stdin()
        self.stdout = stdout if isinstance(stdout, _Stream) else _Stream([stdout])
        self.stderr = stderr if isinstance(stderr, _Stream) else _Stream([stderr])
        self.returncode = returncode
        self.wait_error = wait_error
        self.terminated = False

    def wait(self, timeout=None):
        if self.wait_error:
            error, self.wait_error = self.wait_error, None
            raise error
        return self.returncode

    def terminate(self):
        self.terminated = True


def _bounded(request, process, **updates):
    values = {"environment": {"Path": "bin"}, "executable": "codex", "popen": lambda *_args, **_kwargs: process,
              "auth_checker": lambda **_kwargs: None}
    values.update(updates)
    return execute_codex_bounded(request, **values)


def _repos(tmp_path: Path) -> tuple[Path, Path]:
    framework = tmp_path / "framework"
    target = tmp_path / "consumer"
    framework.mkdir()
    target.mkdir()
    (framework / ".git").mkdir()
    (target / ".git").mkdir()
    return framework, target


def _request(tmp_path: Path, sandbox: str = "workspace-write") -> CodexRequest:
    framework, target = _repos(tmp_path)
    return CodexRequest(
        prompt="Change only autonomy_smoke/fixture_state.txt from A to B.",
        target_repo=target,
        framework_repo=framework,
        sandbox=sandbox,
    )


def test_api_key_variables_fail_closed_before_environment_sanitizing():
    with pytest.raises(CodexRuntimeError) as error:
        sanitized_codex_environment({"Path": "bin", "OPENAI_API_KEY": "secret"})

    assert error.value.code == "API_KEY_AUTH_FORBIDDEN"


def test_missing_codex_executable_fails_closed():
    with pytest.raises(CodexRuntimeError) as error:
        resolve_codex_executable({"PATH": ""})

    assert error.value.code == "CODEX_UNAVAILABLE"


@pytest.mark.parametrize("name", [
    "GITHUB_TOKEN",
    "GITHUB_ACTIONS",
    "GH_TOKEN",
    "GH_ENTERPRISE_TOKEN",
    "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
    "ACTIONS_ID_TOKEN_REQUEST_URL",
])
def test_github_credential_like_variables_are_removed(name):
    clean = sanitized_codex_environment({"Path": "bin", name: "secret"})

    assert clean == {"Path": "bin"}


@pytest.mark.parametrize("sandbox", ["read-only", "workspace-write"])
def test_command_uses_only_explicit_bounded_sandbox(tmp_path, sandbox):
    command = codex_command(_request(tmp_path, sandbox))

    assert command[command.index("--sandbox") + 1] == sandbox
    assert f'windows.sandbox="{AUDITED_WINDOWS_SANDBOX}"' in command
    assert "--ephemeral" in command
    assert "--ignore-user-config" in command
    assert "--strict-config" in command
    assert "--approve-for-me" not in command
    assert "danger-full-access" not in command
    assert "--dangerously-bypass-approvals-and-sandbox" not in command


@pytest.mark.parametrize("sandbox", ["danger-full-access", "full-access", "auto", ""])
def test_forbidden_or_implicit_sandbox_is_rejected(tmp_path, sandbox):
    with pytest.raises(CodexRuntimeError) as error:
        codex_command(_request(tmp_path, sandbox))

    assert error.value.code == "SANDBOX_FORBIDDEN"


def test_framework_repository_cannot_be_the_codex_target(tmp_path):
    repo = tmp_path / "framework"
    repo.mkdir()
    (repo / ".git").mkdir()

    with pytest.raises(CodexRuntimeError) as error:
        codex_command(CodexRequest("bounded task", repo, repo, "read-only"))

    assert error.value.code == "TARGET_REPOSITORY_INVALID"


def test_auth_failure_stops_before_codex_execution(tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[-1] == "--version":
            return CompletedProcess(command, 0, f"codex-cli {AUDITED_CODEX_VERSION}\n", "")
        return CompletedProcess(command, 1, "", "Not logged in")

    with pytest.raises(CodexRuntimeError) as error:
        execute_codex(
            _request(tmp_path),
            environment={"Path": "bin"},
            executable="codex",
            run_process=fake_run,
        )

    assert error.value.code == "CHATGPT_AUTH_REQUIRED"
    assert len(calls) == 2


def test_execution_receives_sanitized_environment_and_prompt_on_stdin(tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if command[-1] == "--version":
            return CompletedProcess(command, 0, f"codex-cli {AUDITED_CODEX_VERSION}\n", "")
        if command[-2:] == ["login", "status"]:
            return CompletedProcess(command, 0, "Logged in using ChatGPT\n", "")
        return CompletedProcess(command, 0, "candidate produced\n", "")

    request = _request(tmp_path)
    result = execute_codex(
        request,
        environment={"Path": "bin", "GITHUB_TOKEN": "secret"},
        executable="codex",
        run_process=fake_run,
    )

    assert result.returncode == 0
    assert len(calls) == 3
    command, kwargs = calls[-1]
    assert command[-1] == "-"
    assert kwargs["input"] == request.prompt
    assert kwargs["env"] == {"Path": "bin"}


def test_codex_failure_is_classified_at_execution_boundary(tmp_path):
    def fake_run(command, **kwargs):
        if command[-1] == "--version":
            return CompletedProcess(command, 0, f"codex-cli {AUDITED_CODEX_VERSION}\n", "")
        if command[-2:] == ["login", "status"]:
            return CompletedProcess(command, 0, "Logged in using ChatGPT\n", "")
        return CompletedProcess(command, 7, "", "sandbox denied write")

    with pytest.raises(CodexRuntimeError) as error:
        execute_codex(
            _request(tmp_path),
            environment={"Path": "bin"},
            executable="codex",
            run_process=fake_run,
        )

    assert error.value.code == "CODEX_EXECUTION_FAILED"
    assert "sandbox denied write" in error.value.summary


def test_bounded_execution_caps_output_and_preserves_prompt_input(tmp_path):
    request = _request(tmp_path, "read-only")
    process = _Process(stdout=b"x" * 8)
    result = _bounded(request, process, stdout_limit=8, stderr_limit=8)
    assert result.stdout == "x" * 8
    assert process.stdin.written == request.prompt.encode()
    assert process.stdin.closed

    overflow = _Process(stdout=b"x" * 9)
    with pytest.raises(CodexRuntimeError) as error:
        _bounded(request, overflow, stdout_limit=8, stderr_limit=8)
    assert error.value.code == "CODEX_OUTPUT_LIMIT"
    assert overflow.terminated


@pytest.mark.parametrize("stdout", [b"\xff", b"valid-prefix"])
def test_bounded_execution_rejects_invalid_or_incompletely_captured_stdout(tmp_path, stdout):
    request = _request(tmp_path, "read-only")
    if stdout == b"\xff":
        process = _Process(stdout=stdout)
    else:
        process = _Process(stdout=_Stream([stdout], exc=OSError("read failed")))
    with pytest.raises(CodexRuntimeError) as error:
        _bounded(request, process)
    assert error.value.code == "CODEX_OUTPUT_INVALID"
    if stdout == b"valid-prefix":
        assert process.terminated


def test_bounded_execution_rejects_stderr_reader_failure_timeout_and_nonzero_exit(tmp_path):
    request = _request(tmp_path, "read-only")
    stderr_failure = _Process(stdout=b"ok", stderr=_Stream(exc=OSError("stderr failed")))
    with pytest.raises(CodexRuntimeError) as error:
        _bounded(request, stderr_failure)
    assert error.value.code == "CODEX_OUTPUT_INVALID"
    assert stderr_failure.terminated

    timeout = _Process(wait_error=subprocess.TimeoutExpired(["codex"], 1))
    with pytest.raises(CodexRuntimeError) as error:
        _bounded(request, timeout)
    assert error.value.code == "CODEX_TIMEOUT"
    assert timeout.terminated

    nonzero = _Process(returncode=7, stderr=b"bounded failure")
    with pytest.raises(CodexRuntimeError) as error:
        _bounded(request, nonzero)
    assert error.value.code == "CODEX_EXECUTION_FAILED"


def test_bounded_execution_rejects_reader_that_does_not_stop(tmp_path):
    request = _request(tmp_path, "read-only")
    unblock = threading.Event()
    process = _Process(stdout=_Stream(blocker=unblock))
    try:
        with pytest.raises(CodexRuntimeError) as error:
            _bounded(request, process, reader_join_timeout=0.01)
        assert error.value.code == "CODEX_EXECUTION_FAILED"
        assert process.terminated
    finally:
        unblock.set()
