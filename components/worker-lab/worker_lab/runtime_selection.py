from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .canonical import canonical_digest
from .errors import LabValidationError


RUNTIME_REQUIREMENT_SCHEMA_V2 = "worker-lab-runtime-requirement:v2"


@dataclass(frozen=True)
class RuntimeRequirementV2:
    """Provider-neutral protected capability requirement for Invocation V3."""

    schema_version: str
    requirement_id: str
    requirement_version: int
    capability: str
    profile_id: str
    timeout_seconds: int
    provider_binding_required: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


CODING_WORKER_V2 = RuntimeRequirementV2(
    schema_version=RUNTIME_REQUIREMENT_SCHEMA_V2,
    requirement_id="coding-worker",
    requirement_version=2,
    capability="bounded-code-task",
    profile_id="coding-worker:v2",
    timeout_seconds=900,
    provider_binding_required=True,
)

PROTECTED_RUNTIME_REQUIREMENTS_V3 = (CODING_WORKER_V2,)


def selected_runtime_requirement_v3() -> RuntimeRequirementV2:
    return CODING_WORKER_V2


def resolve_runtime_identity(profile_id: Any, requirement_digest: Any) -> RuntimeRequirementV2:
    for requirement in PROTECTED_RUNTIME_REQUIREMENTS_V3:
        if profile_id == requirement.profile_id and requirement_digest == requirement.digest():
            return requirement
    raise LabValidationError(
        "INTEGRATION_RUNTIME_INVALID",
        "runtime identity does not resolve to a protected Worker Lab V3 requirement",
    )
