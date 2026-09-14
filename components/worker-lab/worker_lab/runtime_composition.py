from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Callable, Protocol

from .canonical import canonical_json
from .errors import LabValidationError
from .integration_v3 import InvocationRecordV3
from .operator_control import inspect_source_identity
from .process_custody import ProcessCustodyStore
from .provider_binding import (
    ProviderBinding,
    ProviderBindingStore,
    validate_binding_qualification,
)
from .provider_qualification import (
    ProviderCapabilityQualification,
    ProviderInstallationObservation,
    inspect_distribution,
)
from .provider_records import (
    ProviderCapabilityQualificationStore,
    ProviderInstallationObservationStore,
)
from .runtime_selection import resolve_runtime_identity
from .windows_job import WindowsJobAdapterRunner


PROVIDER_RUNTIME_ENVELOPE_SCHEMA = "acl-provider-runtime-envelope:v1"
FRAMEWORK_ADAPTER_RELATIVE_PATH = "tools/dispatch_adapter.py"


class ContainedAdapterRunner(Protocol):
    def __call__(self, command: tuple[str, ...], payload: bytes) -> bytes: ...


ContainedRunnerFactory = Callable[..., ContainedAdapterRunner]
RuntimeIdentityVerifier = Callable[[ProviderInstallationObservation], None]
Clock = Callable[[], str]


def compose_pydantic_ollama_workspace_runner(
    state_root: Path,
    framework_root: Path,
    *,
    binding_id: str,
    binding_digest: str,
    now: Clock,
    contained_runner_factory: ContainedRunnerFactory = WindowsJobAdapterRunner,
    runtime_identity_verifier: RuntimeIdentityVerifier | None = None,
):
    """Bind one qualified provider chain to one contained V3 dispatch runner.

    Construction is explicit and immutable. There is no provider registry, model
    selection, or fallback. The returned runner accepts only the configured
    Provider Binding and rechecks source/runtime evidence immediately before launch.
    """
    state = _real_directory(state_root, "state root")
    framework = _protected_framework_root(framework_root)
    if not callable(now) or not callable(contained_runner_factory):
        raise LabValidationError("RUNTIME_COMPOSITION_INVALID", "runner construction inputs are invalid")
    verifier = runtime_identity_verifier or _verify_observed_runtime
    if not callable(verifier):
        raise LabValidationError("RUNTIME_COMPOSITION_INVALID", "runtime identity verifier is invalid")

    binding = ProviderBindingStore(state).require(binding_id, binding_digest)
    qualification = ProviderCapabilityQualificationStore(state).read(
        binding.host_provider_qualification_digest
    )
    validate_binding_qualification(binding, qualification)
    observation = ProviderInstallationObservationStore(state).read(
        qualification.installation_observation_digest
    )
    _validate_observation_chain(observation, qualification, binding)
    requirement = resolve_runtime_identity(
        binding.runtime_requirement_profile_id,
        binding.runtime_requirement_digest,
    )

    def run(
        payload: bytes,
        invocation: InvocationRecordV3,
        workspace_path: Path,
        custody_store: ProcessCustodyStore,
    ) -> bytes:
        if not isinstance(invocation, InvocationRecordV3):
            raise LabValidationError("RUNTIME_COMPOSITION_INVALID", "V3 invocation is required")
        if (
            invocation.provider_binding_id != binding.binding_id
            or invocation.provider_binding_digest != binding.digest()
        ):
            raise LabValidationError(
                "RUNTIME_COMPOSITION_BINDING_MISMATCH",
                "invocation differs from the explicitly composed Provider Binding",
            )
        if not isinstance(custody_store, ProcessCustodyStore) or _path_key(
            custody_store.records.root
        ) != _path_key(state):
            raise LabValidationError(
                "RUNTIME_COMPOSITION_CUSTODY_MISMATCH",
                "dispatch custody store differs from the composed state root",
            )
        _, source = inspect_source_identity()
        if invocation.framework_source_digest != source.component_digests.get(
            "autonomous-worker-framework"
        ):
            raise LabValidationError(
                "RUNTIME_COMPOSITION_SOURCE_MISMATCH",
                "invocation framework source differs from current protected bytes",
            )
        verifier(observation)
        dispatch_request = _canonical_dispatch_object(payload)
        envelope = canonical_json({
            "schema_version": PROVIDER_RUNTIME_ENVELOPE_SCHEMA,
            "dispatch_request": dispatch_request,
            "installation_observation": observation.to_dict(),
            "capability_qualification": qualification.to_dict(),
        }).encode("utf-8")
        command = (
            observation.python_executable,
            "-I",
            "-B",
            str(framework / FRAMEWORK_ADAPTER_RELATIVE_PATH),
            "execute-pydantic-ollama",
            "--workspace-root",
            str(workspace_path),
            "--framework-root",
            str(framework),
        )
        contained = contained_runner_factory(
            custody_store,
            invocation=invocation,
            timeout_seconds=requirement.timeout_seconds,
            workspace_path=workspace_path,
            now=now,
        )
        if not callable(contained):
            raise LabValidationError(
                "RUNTIME_COMPOSITION_INVALID",
                "contained runner factory did not return a runner",
            )
        return contained(command, envelope)

    return run


def _validate_observation_chain(
    observation: ProviderInstallationObservation,
    qualification: ProviderCapabilityQualification,
    binding: ProviderBinding,
) -> None:
    shared = (
        "candidate_id", "candidate_version", "candidate_digest", "tool_surface_id",
        "provider_kind", "model_name", "model_digest", "model_metadata_digest",
    )
    if (
        qualification.installation_observation_digest != observation.digest()
        or any(getattr(observation, name) != getattr(qualification, name) for name in shared)
        or binding.host_provider_qualification_digest != qualification.digest()
    ):
        raise LabValidationError(
            "RUNTIME_COMPOSITION_QUALIFICATION_MISMATCH",
            "provider observation, qualification, and binding do not form one identity chain",
        )


def _verify_observed_runtime(observation: ProviderInstallationObservation) -> None:
    python = _real_file(Path(observation.python_executable), "observed Python executable")
    provider = _real_file(Path(observation.provider_executable), "observed provider executable")
    if (
        _path_key(python) != _path_key(Path(sys.executable).resolve())
        or _bytes_digest(python.read_bytes()) != observation.python_sha256
        or _bytes_digest(provider.read_bytes()) != observation.provider_executable_sha256
    ):
        raise LabValidationError(
            "RUNTIME_COMPOSITION_HOST_MISMATCH",
            "current executable bytes differ from the qualified installation observation",
        )
    version, tree_digest = inspect_distribution(observation.harness_distribution)
    if version != observation.harness_version or tree_digest != observation.harness_tree_digest:
        raise LabValidationError(
            "RUNTIME_COMPOSITION_HOST_MISMATCH",
            "current harness bytes differ from the qualified installation observation",
        )


def _protected_framework_root(value: Path) -> Path:
    framework = _real_directory(value, "framework root")
    checkout = Path(__file__).resolve().parents[3]
    expected = (checkout / "components" / "autonomous-worker-framework").resolve(strict=True)
    if _path_key(framework) != _path_key(expected):
        raise LabValidationError(
            "RUNTIME_COMPOSITION_SOURCE_MISMATCH",
            "framework root differs from the protected portable source component",
        )
    adapter = _real_file(framework / FRAMEWORK_ADAPTER_RELATIVE_PATH, "framework adapter")
    del adapter
    inspect_source_identity()
    return framework


def _canonical_dispatch_object(payload: bytes):
    if not isinstance(payload, bytes) or not payload:
        raise LabValidationError("RUNTIME_COMPOSITION_REQUEST_INVALID", "dispatch request is invalid")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LabValidationError(
            "RUNTIME_COMPOSITION_REQUEST_INVALID",
            "dispatch request is not UTF-8 JSON",
        ) from exc
    if not isinstance(value, dict) or canonical_json(value).encode("utf-8") != payload:
        raise LabValidationError(
            "RUNTIME_COMPOSITION_REQUEST_INVALID",
            "dispatch request is not a canonical object",
        )
    return value


def _real_directory(value: Path, name: str) -> Path:
    if not isinstance(value, Path) or not value.is_absolute():
        raise LabValidationError("RUNTIME_COMPOSITION_INVALID", f"{name} must be absolute")
    try:
        resolved = value.resolve(strict=True)
    except OSError as exc:
        raise LabValidationError("RUNTIME_COMPOSITION_INVALID", f"{name} is unavailable") from exc
    if not resolved.is_dir() or _is_linklike(value) or _path_key(resolved) != _path_key(value):
        raise LabValidationError("RUNTIME_COMPOSITION_INVALID", f"{name} is indirect or invalid")
    return resolved


def _real_file(value: Path, name: str) -> Path:
    if not value.is_absolute():
        raise LabValidationError("RUNTIME_COMPOSITION_HOST_MISMATCH", f"{name} must be absolute")
    try:
        resolved = value.resolve(strict=True)
    except OSError as exc:
        raise LabValidationError("RUNTIME_COMPOSITION_HOST_MISMATCH", f"{name} is unavailable") from exc
    if not resolved.is_file() or _is_linklike(value) or _path_key(resolved) != _path_key(value):
        raise LabValidationError("RUNTIME_COMPOSITION_HOST_MISMATCH", f"{name} is indirect or invalid")
    return resolved


def _is_linklike(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        return bool(getattr(os.lstat(path), "st_file_attributes", 0) & 0x400)
    except OSError as exc:
        raise LabValidationError("RUNTIME_COMPOSITION_INVALID", "path identity is unavailable") from exc


def _path_key(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


def _bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()
