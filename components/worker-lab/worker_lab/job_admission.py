"""Admission-only bridge from approved job plans to existing Worker Lab contracts.

No curriculum/exercise is created. Legacy V3 field names carry a deterministic
job-task identity; the definition digest covers the full plan and authority bundle.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .job_plan import JobPlan, identity, invalid, obj, positive
from .models import EXERCISE_SCHEMA, ExerciseRecord
from .operator_control import validate_controller_identity
from .policy import ContextManifest, PolicyRecord, RoleRecord, validate_authority
from .storage import AtomicRecordStore
from .test_catalog import ChangeFacts, TestCatalog

PROFILE_SCHEMA = "worker-lab-job-authority:v1"
TASK_SCHEMA = "worker-lab-job-task:v1"
INPUT_TASK_SCHEMA = "worker-lab-job-task:v2"
ATTEMPT_PREFIX = "JOBTASK-"


@dataclass(frozen=True)
class JobAuthorityProfile:
    # Canonical text holds a deeply immutable copy of the protected definitions.
    canonical: str

    @classmethod
    def from_mapping(cls, value):
        d = obj(value, {"schema_version", "profile_id", "version", "target_id", "policy", "role",
                        "context", "catalog", "writable_paths", "protected_paths", "test_profile_ids",
                        "required_capabilities", "temporary_denied_capabilities"}, "job authority profile")
        if d["schema_version"] != PROFILE_SCHEMA:
            invalid("unsupported authority profile schema")
        identity(d["profile_id"], "profile_id")
        positive(d["version"], "profile version")
        from .job_plan import Objective
        Objective.from_mapping({"objective_id": "profile-target", "text": "Protected target", "target_id": d["target_id"]})
        policy = PolicyRecord.from_mapping(d["policy"])
        role = RoleRecord.from_mapping(d["role"])
        ContextManifest.from_mapping(d["context"])
        TestCatalog.from_mapping(d["catalog"])
        validate_authority(policy, role, required_capabilities=tuple(d["required_capabilities"]),
                           temporary_denied_capabilities=tuple(d["temporary_denied_capabilities"]))
        profile = cls(canonical_json(d))
        # Reuse the bounded scope/reference parser; this value is never persisted
        # as an exercise or registered in a curriculum.
        profile.bounded_record("job-profile-validation", 1, "job-profile", "Validate profile", ("Profile scope",))
        for path in d["writable_paths"]:
            if any(char in path for char in "*?[]"):
                invalid("job writable paths must name exact files")
        return profile

    def to_dict(self):
        return json.loads(self.canonical)

    def digest(self):
        return canonical_digest(self.to_dict())

    def authorities(self):
        d = self.to_dict()
        return (PolicyRecord.from_mapping(d["policy"]), RoleRecord.from_mapping(d["role"]),
                ContextManifest.from_mapping(d["context"]), TestCatalog.from_mapping(d["catalog"]))

    def bounded_record(self, task_id, revision, job_id, objective, criteria):
        d = self.to_dict()
        policy, role, context, catalog = self.authorities()
        return ExerciseRecord.from_mapping({
            "schema_version": EXERCISE_SCHEMA, "exercise_id": task_id, "exercise_version": revision,
            "curriculum_id": job_id, "objective": objective,
            "template_repository": context.repository, "template_commit": context.starting_commit,
            "policy_id": policy.policy_id, "policy_version": policy.policy_version,
            "role_id": role.role_id, "role_version": role.role_version, "sandbox_mode": "workspace-write",
            "context_manifest_id": context.manifest_id, "context_manifest_version": context.manifest_version,
            "evaluator_catalog_version": catalog.catalog_version,
            **{key: d[key] for key in ("writable_paths", "protected_paths", "test_profile_ids",
                                      "required_capabilities", "temporary_denied_capabilities")},
            "acceptance_criteria": list(criteria), "prohibited_shortcuts": [],
            "expected_failure_behavior": ["Stop on any failed identity, authority, scope, test, or evidence boundary."],
        })


@dataclass(frozen=True)
class JobTaskDefinition:
    plan: JobPlan
    task_id: str
    profile: JobAuthorityProfile
    approved_by: str
    approved_plan_digest: str
    input_binding: object | None = None

    @classmethod
    def from_mapping(cls, value):
        fields = {"schema_version", "plan", "task_id", "profile", "approved_by", "approved_plan_digest"}
        if isinstance(value, dict) and value.get('schema_version') == INPUT_TASK_SCHEMA:
            fields.add('input_binding')
        d = obj(value, fields, "job task")
        if d["schema_version"] not in (TASK_SCHEMA, INPUT_TASK_SCHEMA):
            invalid("unsupported job task schema")
        from .job_input import JobInput
        record = cls(JobPlan.from_mapping(d["plan"]), identity(d["task_id"], "task_id"),
                     JobAuthorityProfile.from_mapping(d["profile"]), validate_controller_identity(d["approved_by"]),
                     d["approved_plan_digest"], JobInput.from_mapping(d['input_binding']) if 'input_binding' in d else None)
        record.validate()
        return record

    def validate(self):
        if self.approved_plan_digest != self.plan.digest():
            invalid("approval must name the exact immutable plan digest", "JOB_PLAN_APPROVAL_MISMATCH")
        task = self.plan.task(self.task_id)
        p = self.profile.to_dict()
        if (task.authority_ref.profile_id, task.authority_ref.version, task.authority_ref.digest) != (
                p["profile_id"], p["version"], self.profile.digest()):
            invalid("task authority reference differs from the protected profile", "JOB_TASK_AUTHORITY_MISMATCH")
        if self.plan.objective.target_id != p["target_id"]:
            invalid("plan target differs from protected profile", "JOB_TASK_TARGET_MISMATCH")
        if self.input_binding is not None:
            self.input_binding.validate_scope(profile=self.profile,plan_digest=self.plan.digest(),
                task_id=self.task_id,controller_identity=self.approved_by)
        _, role, context, catalog = self.profile.authorities()
        bounded = self.bounded_record()
        profiles = {item.profile_id for item in catalog.profiles}
        if not set(bounded.test_profile_ids) <= profiles:
            invalid("task names missing protected test profiles")
        selected = catalog.select(ChangeFacts(bounded.writable_paths), profile_ids=bounded.test_profile_ids)
        required_tests = {test for criterion in task.acceptance_criteria for test in criterion.test_ids}
        if not required_tests <= set(selected.test_ids):
            invalid("criterion tests are absent from the protected selected test plan", "JOB_TASK_TEST_MISMATCH")
        if task.required_outputs.allowed_writable_paths != tuple(sorted(bounded.writable_paths)):
            invalid("output contract writable permission differs from protected profile", "JOB_TASK_OUTPUT_MISMATCH")
        if not set(role.required_outputs) <= set(task.required_outputs.required_evidence):
            invalid("task omits role-required outputs", "JOB_TASK_OUTPUT_MISMATCH")
        # Context files provide exact reads; writable paths are checked against
        # the real source filesystem at admission, never treated as directories.
        if any(any(char in item.path for char in "*?[]") for item in context.files):
            invalid("job context must name exact files")

    def bounded_record(self):
        task = self.plan.task(self.task_id)
        key = canonical_digest({"plan_id": self.plan.plan_id, "revision": self.plan.revision,
                                "task_id": self.task_id}).split(":")[1][:56]
        job_key = canonical_digest({"plan_id": self.plan.plan_id}).split(":")[1][:56]
        profile = self.profile
        if self.input_binding is not None:
            value = self.profile.to_dict()
            value['context'] = self.input_binding.context().to_dict()
            # Parsing still validates the unchanged bounded grants. The original
            # profile remains embedded and checked against its plan authority ref.
            profile = JobAuthorityProfile.from_mapping(value)
        return profile.bounded_record("job-" + key, self.plan.revision, "job-" + job_key,
            task.description, tuple(canonical_json({"criterion_id": c.criterion_id,
                "description": c.description, "test_ids": c.test_ids}) for c in task.acceptance_criteria))

    def __getattr__(self, name):
        # Only the explicitly existing bounded-definition fields cross the bridge.
        if name in ExerciseRecord.__dataclass_fields__ and name != "schema_version":
            return getattr(self.bounded_record(), name)
        raise AttributeError(name)

    def to_dict(self):
        value = {"schema_version": TASK_SCHEMA, "plan": self.plan.to_dict(), "task_id": self.task_id,
                "profile": self.profile.to_dict(), "approved_by": self.approved_by,
                "approved_plan_digest": self.approved_plan_digest}
        if self.input_binding is not None:
            value.update(schema_version=INPUT_TASK_SCHEMA,input_binding=self.input_binding.to_dict())
        return value

    def authorities(self):
        policy, role, context, catalog = self.profile.authorities()
        if self.input_binding is not None:
            context = self.input_binding.context()
        return policy, role, context, catalog

    def verify_input(self, data_root, *, source_repository=None):
        if self.input_binding is not None:
            from .job_input import verify_job_input
            verify_job_input(data_root,binding=self.input_binding,profile=self.profile,
                plan_digest=self.plan.digest(),task_id=self.task_id,controller_identity=self.approved_by,
                source_repository=source_repository)

    def digest(self):
        return canonical_digest(self.to_dict())


def load_task_authorities(data_root: Path, attempt):
    """Explicit job namespace; a missing job record never falls back to an exercise."""
    if attempt.attempt_id.startswith(ATTEMPT_PREFIX):
        definition = AtomicRecordStore(data_root / "state").read(
            f"job-tasks/{attempt.attempt_id}.json", JobTaskDefinition.from_mapping)
        definition.verify_input(data_root)
        return (definition, *definition.authorities())
    definitions = AtomicRecordStore(data_root / "curricula")
    exercise = definitions.read(f"exercises/{attempt.exercise_id}/v{attempt.exercise_version}.json", ExerciseRecord.from_mapping)
    return (exercise,
            definitions.read(f"policies/{attempt.policy_id}/v{attempt.policy_version}.json", PolicyRecord.from_mapping),
            definitions.read(f"roles/{attempt.role_id}/v{attempt.role_version}.json", RoleRecord.from_mapping),
            definitions.read(f"contexts/{exercise.context_manifest_id}/v{exercise.context_manifest_version}.json", ContextManifest.from_mapping),
            definitions.read(f"catalogs/{attempt.evaluator_catalog_version}.json", TestCatalog.from_mapping))
