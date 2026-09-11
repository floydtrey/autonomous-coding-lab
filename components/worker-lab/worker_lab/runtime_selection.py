from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .canonical import canonical_digest
from .errors import LabValidationError


RUNTIME_REQUIREMENT_SCHEMA = "worker-lab-runtime-requirement:v1"
RUNTIME_REQUIREMENT_SCHEMA_V2 = "worker-lab-runtime-requirement:v2"
PROVIDER_QUALIFIED = "provider-qualified"
HOST_QUALIFIED_ONLY = "host-qualified-only"


@dataclass(frozen=True)
class RuntimeRequirement:
    """Historical Invocation/Result V2 capability requirement.

    This contract is retained byte-for-byte for legacy parsing until the V2
    application path is migrated. Fake provider-neutral model/reasoning
    sentinels must not be copied into Invocation V3.
    """

    schema_version: str
    requirement_id: str
    requirement_version: int
    capability: str
    profile_id: str
    model_selector: str
    reasoning_selector: str
    timeout_seconds: int
    provider_selection: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def invocation_fields(self) -> dict[str, str | int]:
        return {
            "runtime_profile_id": self.profile_id,
            "model": self.model_selector,
            "reasoning_effort": self.reasoning_selector,
            "timeout_seconds": self.timeout_seconds,
        }


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


CODING_WORKER_V1 = RuntimeRequirement(
    schema_version=RUNTIME_REQUIREMENT_SCHEMA,
    requirement_id="coding-worker",
    requirement_version=1,
    capability="bounded-code-task",
    profile_id="coding-worker:v1",
    model_selector=PROVIDER_QUALIFIED,
    reasoning_selector=PROVIDER_QUALIFIED,
    timeout_seconds=900,
    provider_selection=HOST_QUALIFIED_ONLY,
)

LEGACY_TERRA_V1 = RuntimeRequirement(
    schema_version=RUNTIME_REQUIREMENT_SCHEMA,
    requirement_id="legacy-terra-codex",
    requirement_version=1,
    capability="legacy-codex-worker",
    profile_id="terra-medium:v1",
    model_selector="gpt-5.6-terra",
    reasoning_selector="medium",
    timeout_seconds=900,
    provider_selection="legacy-pinned-provider",
)

CODING_WORKER_V2 = RuntimeRequirementV2(
    schema_version=RUNTIME_REQUIREMENT_SCHEMA_V2,
    requirement_id="coding-worker",
    requirement_version=2,
    capability="bounded-code-task",
    profile_id="coding-worker:v2",
    timeout_seconds=900,
    provider_binding_required=True,
)

PROTECTED_RUNTIME_REQUIREMENTS = (CODING_WORKER_V1, LEGACY_TERRA_V1)
PROTECTED_RUNTIME_REQUIREMENTS_V3 = (CODING_WORKER_V2,)


def selected_runtime_requirement() -> RuntimeRequirement:
    """Return the protected requirement used by the still-live V2 application seam."""
    return CODING_WORKER_V1


def selected_runtime_requirement_v3() -> RuntimeRequirementV2:
    """Return the provider-neutral requirement used for newly prepared V3 records."""
    return CODING_WORKER_V2


def resolve_runtime_profile(profile_id: Any) -> RuntimeRequirement:
    """Resolve a V2 profile name only when it belongs to the protected legacy set."""
    for requirement in PROTECTED_RUNTIME_REQUIREMENTS:
        if profile_id == requirement.profile_id:
            return requirement
    raise LabValidationError(
        "INTEGRATION_RUNTIME_INVALID",
        "runtime profile does not identify a protected Worker Lab V2 requirement",
    )


def resolve_runtime_requirement(
    profile_id: Any,
    model: Any,
    reasoning_effort: Any,
    timeout_seconds: Any,
) -> RuntimeRequirement:
    """Resolve only an exact V2 protected requirement."""
    observed = (profile_id, model, reasoning_effort, timeout_seconds)
    for requirement in PROTECTED_RUNTIME_REQUIREMENTS:
        expected = (
            requirement.profile_id,
            requirement.model_selector,
            requirement.reasoning_selector,
            requirement.timeout_seconds,
        )
        if observed == expected:
            return requirement
    raise LabValidationError(
        "INTEGRATION_RUNTIME_INVALID",
        "runtime fields do not resolve to a protected Worker Lab V2 requirement",
    )


def resolve_runtime_identity(profile_id: Any, requirement_digest: Any) -> RuntimeRequirementV2:
    """Resolve only an exact provider-neutral V3 requirement identity."""
    for requirement in PROTECTED_RUNTIME_REQUIREMENTS_V3:
        if profile_id == requirement.profile_id and requirement_digest == requirement.digest():
            return requirement
    raise LabValidationError(
        "INTEGRATION_RUNTIME_INVALID",
        "runtime identity does not resolve to a protected Worker Lab V3 requirement",
    )
