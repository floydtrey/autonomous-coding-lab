"""Small operator-facing facade for the existing M09 controller path.

This module does not create authority or infer plans.  It turns an explicit
operator selection into the same WorkerLabApplicationService calls used by the
CLI and keeps the exact previewed plan digest bound to launch.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Callable

from .application_service import WorkerLabApplicationService
from .errors import LabValidationError
from .job_plan import JobPlan


@dataclass(frozen=True)
class LoadedPlan:
    path: Path
    plan: JobPlan
    digest: str

    @property
    def job_id(self) -> str:
        return self.plan.plan_id

    @property
    def objective(self) -> str:
        return self.plan.objective.text


@dataclass(frozen=True)
class RunJobRequest:
    plan_file: Path
    approved_plan_digest: str
    job_id: str | None
    controller_identity: str
    target_repository: Path
    workspace_root: Path
    artifact_root: Path
    provider_binding_id: str
    protected_files: tuple[Path, ...]
    acknowledge_unsandboxed: bool
    review_required: bool = False
    validation_timeout_seconds: int = 30
    validation_output_limit_bytes: int = 1048576
    validation_cleanup_timeout_seconds: int = 5
    candidate_archive_limit_bytes: int | None = None


class OperatorConsoleBackend:
    """Thin GUI-facing wrapper over the existing application-service boundary."""

    def __init__(
        self,
        data_root: Path,
        *,
        service_factory: Callable[[Path], WorkerLabApplicationService] = WorkerLabApplicationService,
    ) -> None:
        if not isinstance(data_root, Path):
            raise LabValidationError("OPERATOR_CONSOLE_INPUT_INVALID", "data root must be a path")
        self.data_root = data_root.expanduser().resolve()
        self._service_factory = service_factory

    def load_plan(self, plan_file: Path) -> LoadedPlan:
        path = _path(plan_file, "plan file")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LabValidationError(
                "OPERATOR_CONSOLE_PLAN_INVALID",
                f"cannot read job plan: {exc}",
            ) from exc
        plan = JobPlan.from_mapping(value)
        return LoadedPlan(path=path, plan=plan, digest=plan.digest())

    def run_job(self, request: RunJobRequest) -> dict:
        if not isinstance(request, RunJobRequest):
            raise LabValidationError("OPERATOR_CONSOLE_INPUT_INVALID", "run request is invalid")
        loaded = self.load_plan(request.plan_file)
        if loaded.digest != request.approved_plan_digest:
            raise LabValidationError(
                "OPERATOR_CONSOLE_PLAN_CHANGED",
                "job plan changed after it was previewed; reload and approve the current plan",
            )
        if not request.protected_files:
            raise LabValidationError(
                "OPERATOR_CONSOLE_INPUT_INVALID",
                "at least one protected validation input is required",
            )
        report = self._service().run_job(
            request.job_id or loaded.job_id,
            loaded.plan,
            approved_plan_digest=loaded.digest,
            controller_identity=_text(request.controller_identity, "controller identity"),
            target_repository=_path(request.target_repository, "target repository"),
            workspace_root=_path(request.workspace_root, "workspace root"),
            artifact_root=_path(request.artifact_root, "artifact root"),
            provider_binding_id=_text(request.provider_binding_id, "provider binding ID"),
            protected_files=tuple(_path(path, "protected file") for path in request.protected_files),
            acknowledge_unsandboxed=request.acknowledge_unsandboxed,
            review_required=request.review_required,
            validation_timeout_seconds=request.validation_timeout_seconds,
            validation_output_limit_bytes=request.validation_output_limit_bytes,
            validation_cleanup_timeout_seconds=request.validation_cleanup_timeout_seconds,
            candidate_archive_limit_bytes=request.candidate_archive_limit_bytes,
        )
        return report.to_dict()

    def status(self, job_id: str) -> dict:
        return self._service().job_status(_text(job_id, "job ID")).to_dict()

    def stop(self, job_id: str, *, controller_identity: str) -> dict:
        return self._service().stop_job(
            _text(job_id, "job ID"),
            controller_identity=_text(controller_identity, "controller identity"),
        ).to_dict()

    def reconcile(
        self,
        job_id: str,
        *,
        controller_identity: str,
        artifact_root: Path | None = None,
    ) -> dict:
        root = None if artifact_root is None else _path(artifact_root, "artifact root")
        return self._service().reconcile_job(
            _text(job_id, "job ID"),
            controller_identity=_text(controller_identity, "controller identity"),
            artifact_root=root,
        ).to_dict()

    def _service(self) -> WorkerLabApplicationService:
        return self._service_factory(self.data_root)


def protected_files_from_text(value: str) -> tuple[Path, ...]:
    """Parse one absolute protected file path per nonblank line."""
    if not isinstance(value, str):
        raise LabValidationError("OPERATOR_CONSOLE_INPUT_INVALID", "protected files must be text")
    raw = tuple(line.strip() for line in value.splitlines() if line.strip())
    if not raw:
        return ()
    if any(not Path(item).expanduser().is_absolute() for item in raw):
        raise LabValidationError(
            "OPERATOR_CONSOLE_INPUT_INVALID",
            "protected files must use absolute paths",
        )
    paths = tuple(Path(item).expanduser().resolve() for item in raw)
    if len(paths) != len(set(paths)):
        raise LabValidationError("OPERATOR_CONSOLE_INPUT_INVALID", "protected files contain duplicates")
    return paths


def _path(value: Path, label: str) -> Path:
    if not isinstance(value, Path):
        raise LabValidationError("OPERATOR_CONSOLE_INPUT_INVALID", f"{label} must be a path")
    path = value.expanduser().resolve()
    if not path.is_absolute():
        raise LabValidationError("OPERATOR_CONSOLE_INPUT_INVALID", f"{label} must be absolute")
    return path


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise LabValidationError("OPERATOR_CONSOLE_INPUT_INVALID", f"{label} must be trimmed nonblank text")
    return value
