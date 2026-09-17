from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .canonical import canonical_digest
from .errors import LabValidationError
from .provider_qualification import (
    PROVIDER_ADAPTER_ID,
    ProviderCapabilityQualification,
    protected_provider_candidate,
)
from .runtime_settings import (
    CODING_WORKER_SETTINGS_V1,
    RUNTIME_SETTINGS_SCHEMA,
    RuntimeSettingsProfile,
    validate_runtime_settings,
)
from .runtime_selection import (
    resolve_runtime_identity,
    selected_runtime_requirement_v3,
)
from .storage import AtomicRecordStore


PROVIDER_BINDING_SCHEMA = "worker-lab-provider-binding:v1"
PROVIDER_BINDING_IDENTITY_SCHEMA = "worker-lab-provider-binding-identity:v1"
_BINDING_ID_RE = re.compile(r"^[A-Z][A-Z0-9-]{7,95}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProviderBinding:
    """Immutable authorization-time binding of one exact qualified provider configuration."""

    schema_version: str
    binding_id: str
    binding_version: int
    runtime_requirement_profile_id: str
    runtime_requirement_digest: str
    host_provider_qualification_digest: str
    qualification_candidate_id: str
    qualification_candidate_version: int
    qualification_candidate_digest: str
    provider_adapter_id: str
    tool_surface_id: str
    provider_kind: str
    model_name: str
    model_digest: str
    model_metadata_digest: str
    runtime_settings_profile_id: str
    runtime_settings_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        return canonical_digest({
            "schema_version": PROVIDER_BINDING_IDENTITY_SCHEMA,
            "binding": self.to_dict(),
        })

    @classmethod
    def from_mapping(cls, value: Any) -> "ProviderBinding":
        if not isinstance(value, Mapping) or set(value) != set(cls.__dataclass_fields__):
            raise LabValidationError(
                "PROVIDER_BINDING_FIELDS_INVALID",
                "provider binding fields are missing or unknown",
            )
        record = cls(
            _exact(value["schema_version"], PROVIDER_BINDING_SCHEMA, "schema_version"),
            _binding_id(value["binding_id"]),
            _positive(value["binding_version"], "binding version"),
            _text(value["runtime_requirement_profile_id"], "runtime requirement profile"),
            _digest(value["runtime_requirement_digest"], "runtime requirement digest"),
            _digest(value["host_provider_qualification_digest"], "host qualification digest"),
            _text(value["qualification_candidate_id"], "qualification candidate id"),
            _positive(value["qualification_candidate_version"], "qualification candidate version"),
            _digest(value["qualification_candidate_digest"], "qualification candidate digest"),
            _text(value["provider_adapter_id"], "provider adapter"),
            _text(value["tool_surface_id"], "tool surface"),
            _text(value["provider_kind"], "provider kind"),
            _text(value["model_name"], "model name"),
            _digest(value["model_digest"], "model digest"),
            _digest(value["model_metadata_digest"], "model metadata digest"),
            _text(value["runtime_settings_profile_id"], "runtime settings profile"),
            _digest(value["runtime_settings_digest"], "runtime settings digest"),
        )
        validate_current_provider_binding(record)
        return record


def create_provider_binding(
    binding_id: str,
    qualification: ProviderCapabilityQualification,
    *,
    settings: RuntimeSettingsProfile = CODING_WORKER_SETTINGS_V1,
) -> ProviderBinding:
    """Seal one exact controlled capability qualification into V3 authorization identity."""
    if not isinstance(qualification, ProviderCapabilityQualification):
        raise LabValidationError(
            "PROVIDER_BINDING_QUALIFICATION_INVALID",
            "provider binding requires controlled capability qualification evidence",
        )
    qualification = ProviderCapabilityQualification.from_mapping(
        qualification.to_dict(),
        settings=settings,
    )
    qualification_candidate = protected_provider_candidate(qualification.candidate_id)
    requirement = selected_runtime_requirement_v3()
    _validate_settings(settings)
    if (
        qualification.candidate_version != qualification_candidate.candidate_version
        or qualification.candidate_digest != qualification_candidate.digest()
        or qualification.runtime_requirement_profile_id != requirement.profile_id
        or qualification.runtime_requirement_digest != requirement.digest()
        or qualification.provider_adapter_id != PROVIDER_ADAPTER_ID
        or qualification.tool_surface_id != qualification_candidate.tool_surface_id
        or qualification.provider_kind != qualification_candidate.provider_kind
        or qualification.runtime_settings_profile_id != settings.profile_id
        or qualification.runtime_settings_digest != settings.digest()
        or qualification.requested_context_tokens != settings.requested_context_tokens
        or qualification.effective_context_tokens < settings.requested_context_tokens
        or qualification.capability_qualified is not True
    ):
        raise LabValidationError(
            "PROVIDER_BINDING_QUALIFICATION_INVALID",
            "controlled capability qualification does not match the protected runtime contract",
        )
    record = ProviderBinding(
        schema_version=PROVIDER_BINDING_SCHEMA,
        binding_id=_binding_id(binding_id),
        binding_version=1,
        runtime_requirement_profile_id=requirement.profile_id,
        runtime_requirement_digest=requirement.digest(),
        host_provider_qualification_digest=qualification.digest(),
        qualification_candidate_id=qualification_candidate.candidate_id,
        qualification_candidate_version=qualification_candidate.candidate_version,
        qualification_candidate_digest=qualification_candidate.digest(),
        provider_adapter_id=PROVIDER_ADAPTER_ID,
        tool_surface_id=qualification_candidate.tool_surface_id,
        provider_kind=qualification_candidate.provider_kind,
        model_name=qualification.model_name,
        model_digest=qualification.model_digest,
        model_metadata_digest=qualification.model_metadata_digest,
        runtime_settings_profile_id=settings.profile_id,
        runtime_settings_digest=settings.digest(),
    )
    validate_current_provider_binding(record, settings=settings)
    return record


def validate_current_provider_binding(
    binding: ProviderBinding,
    *,
    settings: RuntimeSettingsProfile | None = None,
) -> ProviderBinding:
    if not isinstance(binding, ProviderBinding):
        raise LabValidationError("PROVIDER_BINDING_INVALID", "provider binding type is invalid")
    if binding.provider_adapter_id == "pi-local-files:v1":
        from .pi_binding import validate_pi_binding
        validate_pi_binding(binding, settings)
        return binding
    settings = CODING_WORKER_SETTINGS_V1 if settings is None else settings
    requirement = resolve_runtime_identity(
        binding.runtime_requirement_profile_id,
        binding.runtime_requirement_digest,
    )
    qualification_candidate = protected_provider_candidate(binding.qualification_candidate_id)
    _validate_settings(settings)
    if (
        requirement != selected_runtime_requirement_v3()
        or binding.binding_version != 1
        or binding.qualification_candidate_version != qualification_candidate.candidate_version
        or binding.qualification_candidate_digest != qualification_candidate.digest()
        or binding.provider_adapter_id != PROVIDER_ADAPTER_ID
        or binding.tool_surface_id != qualification_candidate.tool_surface_id
        or binding.provider_kind != qualification_candidate.provider_kind
        or binding.runtime_settings_profile_id != settings.profile_id
        or binding.runtime_settings_digest != settings.digest()
    ):
        raise LabValidationError(
            "PROVIDER_BINDING_STALE",
            "provider binding differs from the current protected runtime declaration",
        )
    return binding


def validate_binding_qualification(
    binding: ProviderBinding,
    qualification: ProviderCapabilityQualification,
    *,
    settings: RuntimeSettingsProfile = CODING_WORKER_SETTINGS_V1,
) -> None:
    """Reject model, observed installation, probe, or runtime-settings substitution."""
    validate_current_provider_binding(binding, settings=settings)
    if not isinstance(qualification, ProviderCapabilityQualification):
        raise LabValidationError(
            "PROVIDER_BINDING_QUALIFICATION_MISMATCH",
            "provider binding does not match controlled capability qualification evidence",
        )
    qualification = ProviderCapabilityQualification.from_mapping(
        qualification.to_dict(),
        settings=settings,
    )
    if (
        binding.host_provider_qualification_digest != qualification.digest()
        or binding.qualification_candidate_id != qualification.candidate_id
        or binding.qualification_candidate_version != qualification.candidate_version
        or binding.qualification_candidate_digest != qualification.candidate_digest
        or binding.provider_adapter_id != qualification.provider_adapter_id
        or binding.tool_surface_id != qualification.tool_surface_id
        or binding.provider_kind != qualification.provider_kind
        or binding.model_name != qualification.model_name
        or binding.model_digest != qualification.model_digest
        or binding.model_metadata_digest != qualification.model_metadata_digest
        or binding.runtime_settings_profile_id != qualification.runtime_settings_profile_id
        or binding.runtime_settings_digest != qualification.runtime_settings_digest
    ):
        raise LabValidationError(
            "PROVIDER_BINDING_QUALIFICATION_MISMATCH",
            "provider binding does not match controlled capability qualification evidence",
        )


class ProviderBindingStore:
    """Content-checked durable binding store used before task authorization."""

    def __init__(self, state_root: Path) -> None:
        self.records = AtomicRecordStore(state_root)

    def create(self, binding: ProviderBinding) -> None:
        validate_current_provider_binding(binding)
        path = self._path(binding.binding_id)
        try:
            self.records.read(path, ProviderBinding.from_mapping)
        except LabValidationError as exc:
            if exc.code != "STORAGE_RECORD_MISSING":
                raise
        else:
            raise LabValidationError(
                "PROVIDER_BINDING_EXISTS",
                "provider binding identity already exists",
            )
        self.records.write(path, binding)

    def read(self, binding_id: str) -> ProviderBinding:
        binding = self.records.read(self._path(binding_id), ProviderBinding.from_mapping)
        return validate_current_provider_binding(binding)

    def require(self, binding_id: str, expected_digest: str) -> ProviderBinding:
        binding = self.read(binding_id)
        if binding.digest() != _digest(expected_digest, "provider binding digest"):
            raise LabValidationError(
                "PROVIDER_BINDING_MISMATCH",
                "provider binding digest differs from the authorized reference",
            )
        return binding

    @staticmethod
    def _path(binding_id: str) -> str:
        return f"provider-bindings/{_binding_id(binding_id)}.json"


def _validate_settings(settings: RuntimeSettingsProfile) -> None:
    validate_runtime_settings(settings)


def _binding_id(value: Any) -> str:
    text = _text(value, "binding id")
    if not _BINDING_ID_RE.fullmatch(text):
        raise LabValidationError("PROVIDER_BINDING_FIELD_INVALID", "binding id is invalid")
    return text


def _digest(value: Any, name: str) -> str:
    text = _text(value, name)
    if not _DIGEST_RE.fullmatch(text):
        raise LabValidationError("PROVIDER_BINDING_FIELD_INVALID", f"{name} is invalid")
    return text


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or "\x00" in value:
        raise LabValidationError("PROVIDER_BINDING_FIELD_INVALID", f"{name} is invalid")
    return value


def _positive(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LabValidationError("PROVIDER_BINDING_FIELD_INVALID", f"{name} must be positive")
    return value


def _exact(value: Any, expected: str, name: str) -> str:
    text = _text(value, name)
    if text != expected:
        raise LabValidationError("PROVIDER_BINDING_FIELD_INVALID", f"{name} is unsupported")
    return text
