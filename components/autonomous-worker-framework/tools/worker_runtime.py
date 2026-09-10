from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROVIDER_QUALIFIED = "provider-qualified"


@dataclass(frozen=True)
class WorkerRequest:
    """Provider-neutral execution request consumed by the code-task harness.

    Model and reasoning values describe a protected capability requirement, not
    a provider executable or model name. A host-qualified provider adapter must
    resolve them before execution without changing task scope or validation authority.
    """

    prompt: str
    target_repo: Path
    framework_repo: Path
    sandbox: str
    model: str = PROVIDER_QUALIFIED
    reasoning_effort: str = PROVIDER_QUALIFIED
    timeout_seconds: int = 900
    output_last_message: Path | None = None


@dataclass(frozen=True)
class WorkerExecution:
    """Provider-neutral bounded execution result used by the harness."""

    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
