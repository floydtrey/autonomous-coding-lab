from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence


AUDITED_CODEX_VERSION = "0.149.1"
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
    return (
        executable,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--sandbox",
        request.sandbox,
        "--ask-for-approval",
        "never",
        "--model",
        request.model,
        "--config",
        f'model_reasoning_effort="{request.reasoning_effort}"',
        "--cd",
        str(request.target_repo.resolve()),
        "-",
    )


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
    executable: str = "codex",
    run_process: RunProcess = subprocess.run,
) -> CodexExecution:
    source_env = os.environ if environment is None else environment
    clean_env = sanitized_codex_environment(source_env)
    command = codex_command(request, executable)
    check_chatgpt_auth(
        environment=clean_env,
        executable=executable,
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

