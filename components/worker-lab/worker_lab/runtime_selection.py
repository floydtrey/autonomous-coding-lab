from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .canonical import canonical_digest
from .errors import LabValidationError


RUNTIME_REQUIREMENT_SCHEMA = "worker-lab-runtime-requirement:v1"
PROVIDER_QUALIFIED = "provider-qualified"
HOST_QUALIFIED_ONLY = "host-qualified-only"


@dataclass(frozen=True)
class RuntimeRequirement:
    """Protected Worker Lab capability requirement, never a provider selection."""

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

# Historical records remain parseable during the migration. This requirement is
# not selected for new invocations and does not grant provider or execution authority.
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


PROTECTED_RUNTIME_REQUIREMENTS = (CODING_WORKER_V1, LEGACY_TERRA_V1)


def selected_runtime_requirement() -> RuntimeRequirement:
    """Return the only requirement selected for newly prepared invocations."""
    return CODING_WORKER_V1


def resolve_runtime_requirement(
    profile_id: Any,
    model: Any,
    reasoning_effort: Any,
    timeout_seconds: Any,
) -> RuntimeRequirement:
    """Resolve only an exact protected requirement; arbitrary provider fields fail closed."""
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
        "runtime fields do not resolve to a protected Worker Lab requirement",
    )
