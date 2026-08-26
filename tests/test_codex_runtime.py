from pathlib import Path
from subprocess import CompletedProcess

import pytest

from tools.codex_runtime import (
    AUDITED_CODEX_VERSION,
    AUDITED_WINDOWS_SANDBOX,
    CodexRequest,
    CodexRuntimeError,
    codex_command,
    execute_codex,
    resolve_codex_executable,
    sanitized_codex_environment,
)


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
