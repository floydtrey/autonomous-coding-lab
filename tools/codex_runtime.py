from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence


AUDITED_CODEX_VERSION = "0.149.1"
AUDITED_WINDOWS_SANDBOX = "elevated"
ALLOWED_SANDBOX_MODES = frozenset({"read-only", "workspace-write"})
_API_KEY_NAMES = frozenset({"OPENAI_API_KEY", "CODEX_API_KEY"})
_CHATGPT_STATUS_RE = re.compile(r"logged in using chatgpt", re.IGNORECASE)


class CodexRuntimeError(RuntimeError):
    """A fail-closed Codex execution boundary failure."""

    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary


@dataclass(frozen=True)
class CodexRequest:
    prompt: str
    target_repo: Path
    framework_repo: Path
    sandbox: str
    model: str = "gpt-5.6-terra"
    reasoning_effort: str = "medium"
    timeout_seconds: int = 900
    output_last_message: Path | None = None


@dataclass(frozen=True)
class CodexExecution:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


RunProcess = Callable[..., subprocess.CompletedProcess[str]]


def sanitized_codex_environment(source: Mapping[str, str]) -> dict[str, str]:
    """Return a subprocess environment without GitHub credential-like values."""
    blocked_api_keys = sorted(
        name for name in source if name.upper() in _API_KEY_NAMES and source[name]
    )
    if blocked_api_keys:
        raise CodexRuntimeError(
            "API_KEY_AUTH_FORBIDDEN",
            "Codex execution refuses API-key authentication variables: "
            + ", ".join(blocked_api_keys),
        )

    return {
        name: value
        for name, value in source.items()
        if not _is_github_credential_name(name)
    }


def _is_github_credential_name(name: str) -> bool:
    upper = name.upper()
    return (
        upper.startswith("GITHUB_")
        or upper in {"GH_TOKEN", "GH_ENTERPRISE_TOKEN"}
        or upper.startswith("ACTIONS_ID_TOKEN_REQUEST_")
    )


def resolve_codex_executable(environment: Mapping[str, str]) -> str:
    path_value = next(
        (value for name, value in environment.items() if name.upper() == "PATH"),
        None,
    )
    resolved = shutil.which("codex", path=path_value)
    if resolved is None:
        raise CodexRuntimeError("CODEX_UNAVAILABLE", "could not resolve Codex from PATH")
    return resolved


def validate_request(request: CodexRequest) -> None:
    if not request.prompt.strip():
        raise CodexRuntimeError("PROMPT_INVALID", "Codex prompt must not be empty")
    if request.sandbox not in ALLOWED_SANDBOX_MODES:
        raise CodexRuntimeError(
            "SANDBOX_FORBIDDEN",
            "sandbox must be exactly read-only or workspace-write",
        )
    if not request.model.strip() or not request.reasoning_effort.strip():
        raise CodexRuntimeError("RUNTIME_CONFIG_INVALID", "model and reasoning effort are required")
    if request.timeout_seconds <= 0:
        raise CodexRuntimeError("RUNTIME_CONFIG_INVALID", "timeout_seconds must be positive")

    target = request.target_repo.resolve()
    framework = request.framework_repo.resolve()
    if target == framework:
        raise CodexRuntimeError(
            "TARGET_REPOSITORY_INVALID",
            "Codex must operate on a separate target repository, not the framework repository",
        )
    if not target.is_dir() or not (target / ".git").exists():
        raise CodexRuntimeError(
            "TARGET_REPOSITORY_INVALID",
            "Codex target must be an existing Git repository",
        )


def codex_command(request: CodexRequest, executable: str = "codex") -> tuple[str, ...]:
    validate_request(request)
    command = (
        executable,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--strict-config",
        "--config",
        f'windows.sandbox="{AUDITED_WINDOWS_SANDBOX}"',
        "--sandbox",
        request.sandbox,
        "--model",
        request.model,
        "--config",
        f'model_reasoning_effort="{request.reasoning_effort}"',
        "--cd",
        str(request.target_repo.resolve()),
        "-",
    )
    if request.output_last_message is not None:
        command = command[:-1] + ("--output-last-message", str(request.output_last_message), "-")
    return command


def check_chatgpt_auth(
    *,
    environment: Mapping[str, str],
    executable: str = "codex",
    run_process: RunProcess = subprocess.run,
) -> None:
    clean_env = sanitized_codex_environment(environment)
    try:
        version = run_process(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=clean_env,
        )
    except OSError as exc:
        raise CodexRuntimeError("CODEX_UNAVAILABLE", f"could not start Codex: {exc}") from exc
    expected = f"codex-cli {AUDITED_CODEX_VERSION}"
    if version.returncode != 0 or expected not in version.stdout.strip():
        observed = (version.stdout or version.stderr or "no version output").strip()
        raise CodexRuntimeError(
            "CODEX_VERSION_INVALID",
            f"expected {expected!r}; observed {observed!r}",
        )

    status = run_process(
        [executable, "login", "status"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=clean_env,
    )
    combined = "\n".join((status.stdout, status.stderr))
    if status.returncode != 0 or not _CHATGPT_STATUS_RE.search(combined):
        raise CodexRuntimeError(
            "CHATGPT_AUTH_REQUIRED",
            "Codex must be logged in with ChatGPT-managed authentication",
        )


def execute_codex(
    request: CodexRequest,
    *,
    environment: Mapping[str, str] | None = None,
    executable: str | None = None,
    run_process: RunProcess = subprocess.run,
) -> CodexExecution:
    source_env = os.environ if environment is None else environment
    clean_env = sanitized_codex_environment(source_env)
    resolved_executable = executable or resolve_codex_executable(clean_env)
    command = codex_command(request, resolved_executable)
    check_chatgpt_auth(
        environment=clean_env,
        executable=resolved_executable,
        run_process=run_process,
    )
    try:
        process = run_process(
            list(command),
            input=request.prompt,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=clean_env,
            timeout=request.timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise CodexRuntimeError(
            "CODEX_TIMEOUT",
            f"Codex exceeded the {request.timeout_seconds}-second execution limit",
        ) from exc
    except OSError as exc:
        raise CodexRuntimeError("CODEX_UNAVAILABLE", f"could not start Codex: {exc}") from exc

    result = CodexExecution(
        command=command,
        returncode=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
    )
    if process.returncode != 0:
        detail = (process.stderr or process.stdout or "Codex failed without output").strip()
        raise CodexRuntimeError("CODEX_EXECUTION_FAILED", detail)
    return result


def execute_codex_bounded(
    request: CodexRequest,
    *,
    environment: Mapping[str, str] | None = None,
    executable: str | None = None,
    stdout_limit: int = 65_536,
    stderr_limit: int = 16_384,
    reader_join_timeout: float = 10.0,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
    auth_checker: Callable[..., None] = check_chatgpt_auth,
) -> CodexExecution:
    """Execute Codex with streaming byte caps; outer callers retain process-tree custody."""
    if stdout_limit <= 0 or stderr_limit <= 0 or reader_join_timeout <= 0:
        raise CodexRuntimeError("RUNTIME_CONFIG_INVALID", "output limits must be positive")
    source_env = os.environ if environment is None else environment
    clean_env = sanitized_codex_environment(source_env)
    resolved_executable = executable or resolve_codex_executable(clean_env)
    command = codex_command(request, resolved_executable)
    auth_checker(environment=clean_env, executable=resolved_executable)
    try:
        process = popen(
            list(command), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=False, close_fds=True, env=clean_env,
        )
    except OSError as exc:
        raise CodexRuntimeError("CODEX_UNAVAILABLE", f"could not start Codex: {exc}") from exc
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
    stdout = bytearray()
    stderr = bytearray()
    overflow = threading.Event()
    reader_failure: list[tuple[str, BaseException]] = []
    failure_lock = threading.Lock()

    def drain(stream, target: bytearray, limit: int, name: str) -> None:
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    return
                remaining = limit - len(target)
                if remaining > 0:
                    target.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    overflow.set()
                    process.terminate()
        except Exception as exc:
            # Bytes captured before a read failure are never trustworthy; treat
            # the failure itself as authoritative instead of returning them.
            with failure_lock:
                if not reader_failure:
                    reader_failure.append((name, exc))
            process.terminate()

    readers = [
        threading.Thread(target=drain, args=(process.stdout, stdout, stdout_limit, "stdout"), daemon=True),
        threading.Thread(target=drain, args=(process.stderr, stderr, stderr_limit, "stderr"), daemon=True),
    ]
    for reader in readers:
        reader.start()
    try:
        process.stdin.write(request.prompt.encode("utf-8"))
        process.stdin.close()
        process.wait(timeout=request.timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        process.terminate()
        process.wait(timeout=10)
        raise CodexRuntimeError("CODEX_TIMEOUT", f"Codex exceeded the {request.timeout_seconds}-second execution limit") from exc
    finally:
        for reader in readers:
            reader.join(timeout=reader_join_timeout)
    if any(reader.is_alive() for reader in readers):
        process.terminate()
        raise CodexRuntimeError("CODEX_EXECUTION_FAILED", "Codex output readers did not stop")
    if reader_failure:
        raise CodexRuntimeError("CODEX_OUTPUT_INVALID", f"Codex {reader_failure[0][0]} could not be captured")
    if overflow.is_set():
        raise CodexRuntimeError("CODEX_OUTPUT_LIMIT", "Codex output exceeded the bounded capture limit")
    try:
        stdout_text = bytes(stdout).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CodexRuntimeError("CODEX_OUTPUT_INVALID", "Codex stdout is not UTF-8") from exc
    stderr_text = bytes(stderr).decode("utf-8", errors="replace")
    result = CodexExecution(command, process.returncode, stdout_text, stderr_text)
    if process.returncode != 0:
        raise CodexRuntimeError("CODEX_EXECUTION_FAILED", "Codex returned nonzero")
    return result
