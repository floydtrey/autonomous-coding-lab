from __future__ import annotations

import json
from pathlib import Path

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.operator_console import (
    OperatorConsoleBackend,
    RunJobRequest,
    protected_files_from_text,
)


FIXTURE_PLAN = Path(__file__).parent / "fixtures" / "two-task-job-plan.json"


class _Report:
    def __init__(self, value):
        self.value = value

    def to_dict(self):
        return self.value


class _FakeService:
    def __init__(self):
        self.run_calls = []
        self.status_calls = []
        self.stop_calls = []
        self.reconcile_calls = []

    def run_job(self, *args, **kwargs):
        self.run_calls.append((args, kwargs))
        return _Report({"job_id": args[0], "status": "complete", "tasks": []})

    def job_status(self, job_id):
        self.status_calls.append(job_id)
        return _Report({"job_id": job_id, "status": "ready", "tasks": []})

    def stop_job(self, job_id, *, controller_identity):
        self.stop_calls.append((job_id, controller_identity))
        return _Report({"job_id": job_id, "status": "ready", "tasks": []})

    def reconcile_job(self, job_id, *, controller_identity, artifact_root=None):
        self.reconcile_calls.append((job_id, controller_identity, artifact_root))
        return _Report({"job_id": job_id, "status": "ready", "tasks": []})


def _plan_copy(tmp_path: Path) -> Path:
    path = tmp_path / "plan.json"
    path.write_text(FIXTURE_PLAN.read_text(encoding="utf-8"), encoding="utf-8")
    return path.resolve()


def _request(tmp_path: Path, plan_file: Path, digest: str) -> RunJobRequest:
    target = (tmp_path / "target").resolve()
    workspaces = (tmp_path / "workspaces").resolve()
    artifacts = (tmp_path / "artifacts").resolve()
    protected = (tmp_path / "check.py").resolve()
    for path in (target, workspaces, artifacts):
        path.mkdir()
    protected.write_text("raise SystemExit(0)\n", encoding="utf-8")
    return RunJobRequest(
        plan_file=plan_file,
        approved_plan_digest=digest,
        job_id="JOB-CONSOLE",
        controller_identity="controller:operator",
        target_repository=target,
        workspace_root=workspaces,
        artifact_root=artifacts,
        provider_binding_id="binding:test",
        protected_files=(protected,),
        acknowledge_unsandboxed=True,
        candidate_archive_limit_bytes=0,
    )


def test_console_run_uses_exact_previewed_plan_and_existing_service_path(tmp_path):
    fake = _FakeService()
    backend = OperatorConsoleBackend(tmp_path.resolve(), service_factory=lambda root: fake)
    plan_file = _plan_copy(tmp_path)
    loaded = backend.load_plan(plan_file)

    result = backend.run_job(_request(tmp_path, plan_file, loaded.digest))

    assert result == {"job_id": "JOB-CONSOLE", "status": "complete", "tasks": []}
    assert len(fake.run_calls) == 1
    args, kwargs = fake.run_calls[0]
    assert args[0] == "JOB-CONSOLE"
    assert args[1].digest() == loaded.digest
    assert kwargs["approved_plan_digest"] == loaded.digest
    assert kwargs["controller_identity"] == "controller:operator"
    assert kwargs["provider_binding_id"] == "binding:test"
    assert kwargs["acknowledge_unsandboxed"] is True
    assert kwargs["candidate_archive_limit_bytes"] == 0


def test_console_rejects_plan_changed_after_preview_before_service_call(tmp_path):
    fake = _FakeService()
    backend = OperatorConsoleBackend(tmp_path.resolve(), service_factory=lambda root: fake)
    plan_file = _plan_copy(tmp_path)
    loaded = backend.load_plan(plan_file)

    value = json.loads(plan_file.read_text(encoding="utf-8"))
    value["objective"]["text"] = "Changed after operator preview."
    plan_file.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(LabValidationError) as error:
        backend.run_job(_request(tmp_path, plan_file, loaded.digest))

    assert error.value.code == "OPERATOR_CONSOLE_PLAN_CHANGED"
    assert fake.run_calls == []


def test_console_status_stop_and_reconcile_delegate_without_new_workflow_logic(tmp_path):
    fake = _FakeService()
    backend = OperatorConsoleBackend(tmp_path.resolve(), service_factory=lambda root: fake)
    artifact_root = (tmp_path / "artifacts").resolve()
    artifact_root.mkdir()

    assert backend.status("JOB-CONSOLE")["status"] == "ready"
    assert backend.stop("JOB-CONSOLE", controller_identity="controller:operator")["status"] == "ready"
    assert backend.reconcile(
        "JOB-CONSOLE",
        controller_identity="controller:operator",
        artifact_root=artifact_root,
    )["status"] == "ready"

    assert fake.status_calls == ["JOB-CONSOLE"]
    assert fake.stop_calls == [("JOB-CONSOLE", "controller:operator")]
    assert fake.reconcile_calls == [("JOB-CONSOLE", "controller:operator", artifact_root)]


def test_protected_file_text_requires_absolute_unique_paths(tmp_path):
    first = (tmp_path / "a.py").resolve()
    second = (tmp_path / "b.py").resolve()

    assert protected_files_from_text(f"{first}\n\n{second}\n") == (first, second)

    with pytest.raises(LabValidationError) as relative:
        protected_files_from_text("checks/test.py")
    assert relative.value.code == "OPERATOR_CONSOLE_INPUT_INVALID"

    with pytest.raises(LabValidationError) as duplicate:
        protected_files_from_text(f"{first}\n{first}\n")
    assert duplicate.value.code == "OPERATOR_CONSOLE_INPUT_INVALID"
