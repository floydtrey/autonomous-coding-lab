from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .canonical import canonical_digest
from .errors import LabValidationError


RUNTIME_SETTINGS_SCHEMA = "worker-lab-runtime-settings:v1"


@dataclass(frozen=True)
class RuntimeSettingsProfile:
    schema_version: str
    profile_id: str
    profile_version: int
    requested_context_tokens: int
    request_limit: int
    tool_calls_limit: int
    tool_timeout_seconds: int
    tool_retries: int
    output_retries: int
    max_concurrency: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


CODING_WORKER_SETTINGS_V1 = RuntimeSettingsProfile(
    schema_version=RUNTIME_SETTINGS_SCHEMA,
    profile_id="bounded-code-worker-settings:v1",
    profile_version=1,
    requested_context_tokens=32_768,
    request_limit=12,
    tool_calls_limit=24,
    tool_timeout_seconds=30,
    tool_retries=2,
    output_retries=1,
    max_concurrency=1,
)


def validate_runtime_settings(settings: RuntimeSettingsProfile) -> RuntimeSettingsProfile:
    if not isinstance(settings, RuntimeSettingsProfile) or settings != CODING_WORKER_SETTINGS_V1:
        raise LabValidationError(
            "PROVIDER_BINDING_SETTINGS_INVALID",
            "runtime settings are not the protected current profile",
        )
    if (
        settings.schema_version != RUNTIME_SETTINGS_SCHEMA
        or settings.profile_version != 1
        or settings.requested_context_tokens <= 0
        or settings.request_limit <= 0
        or settings.tool_calls_limit <= 0
        or settings.tool_timeout_seconds <= 0
        or settings.tool_retries < 0
        or settings.output_retries < 0
        or settings.max_concurrency <= 0
    ):
        raise LabValidationError(
            "PROVIDER_BINDING_SETTINGS_INVALID",
            "runtime settings profile is invalid",
        )
    return settings
