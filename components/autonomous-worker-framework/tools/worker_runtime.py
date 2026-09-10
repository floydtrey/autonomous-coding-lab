from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkerRequest:
    """Provider-neutral execution request consumed by the code-task harness.

    The model/reasoning defaults preserve the accepted Codex compatibility path.
    They are compatibility defaults, not portable installation authority; a future
    provider-qualified runtime may interpret or replace them behind the executor
    boundary without changing code-task scope or validation authority.
    """

    prompt: str
    target_repo: Path
    framework_repo: Path
    sandbox: str
    model: str = "gpt-5.6-terra"
    reasoning_effort: str = "medium"
    timeout_seconds: int = 900
    output_last_message: Path | None = None


@dataclass(frozen=True)
class WorkerExecution:
    """Provider-neutral bounded execution result used by the harness."""

    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
