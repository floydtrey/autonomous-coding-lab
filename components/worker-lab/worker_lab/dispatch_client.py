from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .canonical import canonical_json
from .controller_task_packet import parse_controller_task_packet
from .errors import LabValidationError
from .output_acceptance import OutputAcceptance
from .integration_v3 import (
    FRAMEWORK_DISPATCH_CONTRACT_V1,
    InvocationOperation,
    InvocationRecordV3,
    InvocationState,
)
from .provider_binding import (
    CODING_WORKER_SETTINGS_V1,
    ProviderBinding,
    ProviderBindingStore,
    RuntimeSettingsProfile,
    validate_current_provider_binding,
)


DISPATCH_REQUEST_SCHEMA = "worker-lab-provider-dispatch-request:v1"
DISPATCH_RESPONSE_SCHEMA = "worker-lab-provider-dispatch-response:v1"
WORKSPACE_WRITE_TASK_SCHEMA = "worker-lab-workspace-write-task:v2"
MAX_DISPATCH_REQUEST_BYTES = 262_144
MAX_DISPATCH_RESPONSE_BYTES = 131_072
MAX_PROMPT_BYTES = 32_768
_DIGEST_PREFIX = "sha256:"

DispatchRunner = Callable[[bytes], bytes]


@dataclass(frozen=True)
class WorkspaceWriteTask:
    schema_version: str
    task_digest: str
    objective: str
    acceptance_criteria: tuple[str, ...]
    consumer_profile: Mapping[str, Any]
    test_ids: tuple[str, ...]
    writable_paths: tuple[str, ...]
    output_acceptance: OutputAcceptance | None = None

    def to_dict(self) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "task_digest": self.task_digest,
            "objective": self.objective,
            "acceptance_criteria": list(self.acceptance_criteria),
            "consumer_profile": dict(self.consumer_profile),
            "test_ids": list(self.test_ids),
            "writable_paths": list(self.writable_paths),
        }
        if self.output_acceptance is not None:
            value["output_acceptance"] = self.output_acceptance.to_dict()
        return value

    @classmethod
    def from_mapping(
        cls,
        value: Any,
        *,
        invocation: InvocationRecordV3,
    ) -> "WorkspaceWriteTask":
        expected = {
            "schema_version",
            "task_digest",
            "objective",
            "acceptance_criteria",
            "consumer_profile",
            "test_ids",
            "writable_paths",
        }
        if invocation.output_acceptance is not None:
            expected.add("output_acceptance")
        if not isinstance(value, Mapping) or set(value) != expected:
            raise LabValidationError(
                "DISPATCH_TASK_FIELDS_INVALID",
                "workspace-write task fields are missing or unknown",
            )
        schema = "worker-lab-workspace-write-task:v3" if invocation.output_acceptance else WORKSPACE_WRITE_TASK_SCHEMA
        if value["schema_version"] != schema:
            raise LabValidationError(
                "DISPATCH_TASK_IDENTITY_INVALID",
                "workspace-write task schema is unsupported",
            )
        task_digest = _digest(value["task_digest"], "task digest")
        if task_digest != invocation.task_digest:
            raise LabValidationError(
                "DISPATCH_TASK_IDENTITY_INVALID",
                "workspace-write task differs from the sealed invocation task",
            )
        objective = _bounded_text(value["objective"], "objective", 16_384)
        criteria = _text_array(value["acceptance_criteria"], "acceptance criteria")
        profile = value["consumer_profile"]
        if not isinstance(profile, Mapping) or not profile:
            raise LabValidationError(
                "DISPATCH_TASK_FIELDS_INVALID",
                "workspace-write consumer profile must be an object",
            )
        try:
            canonical_json(dict(profile))
        except (TypeError, ValueError) as exc:
            raise LabValidationError(
                "DISPATCH_TASK_FIELDS_INVALID",
                "workspace-write consumer profile must be canonical JSON data",
            ) from exc
        test_ids = _text_array(value["test_ids"], "test ids", sorted_unique=True)
        writable_paths = _text_array(value["writable_paths"], "writable paths", sorted_unique=True)
        if test_ids != invocation.test_ids or writable_paths != invocation.writable_paths:
            raise LabValidationError(
                "DISPATCH_TASK_SCOPE_INVALID",
                "workspace-write task scope or tests differ from the sealed invocation",
            )
        output = OutputAcceptance.from_mapping(value["output_acceptance"]) if "output_acceptance" in value else None
        if output != invocation.output_acceptance:
            raise LabValidationError("DISPATCH_TASK_SCOPE_INVALID", "output contract differs from sealed invocation")
        return cls(
            schema,
            task_digest,
            objective,
            criteria,
            dict(profile),
            test_ids,
            writable_paths,
            output,
        )


def dispatch_workspace_write(
    invocation: InvocationRecordV3,
    *,
    prompt: str,
    workspace_write: Mapping[str, Any] | WorkspaceWriteTask,
    binding_store: ProviderBindingStore,
    runner: DispatchRunner | None,
    settings: RuntimeSettingsProfile | None = None,
) -> bytes:
    """Dispatch one sealed V3 workspace-write request through an injected framework runner.

    The runner is an explicit transport seam only. It does not select a provider.
    Provider/model/settings identity is already fixed by the authorized Provider Binding.
    """
    _validate_invocation_for_dispatch(invocation)
    if not isinstance(binding_store, ProviderBindingStore):
        raise LabValidationError(
            "DISPATCH_BINDING_INVALID",
            "dispatch requires the durable Provider Binding store",
        )
    binding = binding_store.require(
        invocation.provider_binding_id,
        invocation.provider_binding_digest,
    )
    if settings is None:
        if binding.provider_adapter_id == "pi-local-files:v1":
            from .pi_binding import validate_pi_binding
            settings = RuntimeSettingsProfile(**validate_pi_binding(binding)["runtime_settings"])
        else:
            settings = CODING_WORKER_SETTINGS_V1
    _validate_binding_reference(invocation, binding, settings)
    task = (
        workspace_write
        if isinstance(workspace_write, WorkspaceWriteTask)
        else WorkspaceWriteTask.from_mapping(workspace_write, invocation=invocation)
    )
    if isinstance(workspace_write, WorkspaceWriteTask):
        task = WorkspaceWriteTask.from_mapping(task.to_dict(), invocation=invocation)
    _validate_prompt(invocation, prompt)
    if runner is None:
        raise LabValidationError(
            "DISPATCH_RUNNER_REQUIRED",
            "provider-neutral dispatch requires an explicitly injected framework runner",
        )

    payload = canonical_json(
        {
            "schema_version": DISPATCH_REQUEST_SCHEMA,
            "framework_contract_version": FRAMEWORK_DISPATCH_CONTRACT_V1,
            "invocation": invocation.to_dict(),
            "provider_binding": binding.to_dict(),
            "runtime_settings": settings.to_dict(),
            "prompt": prompt,
            "workspace_write": task.to_dict(),
        }
    ).encode("utf-8")
    if len(payload) > MAX_DISPATCH_REQUEST_BYTES:
        raise LabValidationError(
            "DISPATCH_REQUEST_OVERSIZED",
            "provider-neutral dispatch request exceeds its bounded size",
        )
    response = runner(payload)
    return _validate_response(response, invocation=invocation, binding=binding)


def _validate_invocation_for_dispatch(invocation: InvocationRecordV3) -> None:
    if not isinstance(invocation, InvocationRecordV3):
        raise LabValidationError("DISPATCH_INVOCATION_INVALID", "dispatch invocation type is invalid")
    if (
        invocation.operation is not InvocationOperation.WORKSPACE_WRITE_CODE_TASK
        or invocation.sandbox_mode != "workspace-write"
        or invocation.framework_contract_version != FRAMEWORK_DISPATCH_CONTRACT_V1
    ):
        raise LabValidationError(
            "DISPATCH_OPERATION_INVALID",
            "dispatch supports only the current V3 workspace-write contract",
        )
    if invocation.state is not InvocationState.DISPATCHING:
        raise LabValidationError(
            "DISPATCH_AUTHORIZATION_INVALID",
            "dispatch requires an already-authorized DISPATCHING invocation",
        )
    if invocation.authorized_by is None or invocation.authorized_at is None:
        raise LabValidationError(
            "DISPATCH_AUTHORIZATION_INVALID",
            "dispatch invocation is missing authorization custody",
        )
    if invocation.result_digest is not None:
        raise LabValidationError(
            "DISPATCH_AUTHORIZATION_INVALID",
            "dispatch cannot run an invocation that already has a result",
        )


def _validate_binding_reference(
    invocation: InvocationRecordV3,
    binding: ProviderBinding,
    settings: RuntimeSettingsProfile,
) -> None:
    validate_current_provider_binding(binding, settings=settings)
    if (
        binding.binding_id != invocation.provider_binding_id
        or binding.digest() != invocation.provider_binding_digest
        or binding.runtime_requirement_profile_id != invocation.runtime_requirement_profile_id
        or binding.runtime_requirement_digest != invocation.runtime_requirement_digest
        or binding.runtime_settings_profile_id != settings.profile_id
        or binding.runtime_settings_digest != settings.digest()
    ):
        raise LabValidationError(
            "DISPATCH_BINDING_MISMATCH",
            "dispatch Provider Binding differs from the authorized invocation",
        )


def _validate_prompt(invocation: InvocationRecordV3, prompt: str) -> None:
    if not isinstance(prompt, str) or not prompt or "\x00" in prompt:
        raise LabValidationError("DISPATCH_PROMPT_INVALID", "dispatch prompt must be non-empty UTF-8 text")
    try:
        encoded = prompt.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise LabValidationError("DISPATCH_PROMPT_INVALID", "dispatch prompt is not UTF-8") from exc
    if len(encoded) > MAX_PROMPT_BYTES:
        raise LabValidationError("DISPATCH_PROMPT_INVALID", "dispatch prompt exceeds its bounded size")
    digest = _bytes_digest(encoded)
    if digest != invocation.prompt_digest:
        raise LabValidationError(
            "DISPATCH_IDENTITY_INVALID",
            "dispatch prompt differs from the sealed invocation",
        )
    packet = parse_controller_task_packet(prompt)
    if (
        packet.digest() != invocation.controller_task_packet_digest
        or packet.digest() != invocation.prompt_digest
        or packet.attempt_id != invocation.attempt_id
        or packet.exercise_id != invocation.exercise_id
        or packet.exercise_version != invocation.exercise_version
        or invocation.source_state is None
        or packet.starting_commit != invocation.source_state.base_commit
        or packet.controller_identity != invocation.authorized_by
    ):
        raise LabValidationError(
            "DISPATCH_IDENTITY_INVALID",
            "Controller Task Packet differs from the sealed invocation",
        )


def _validate_response(
    raw: bytes,
    *,
    invocation: InvocationRecordV3,
    binding: ProviderBinding,
) -> bytes:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_DISPATCH_RESPONSE_BYTES:
        raise LabValidationError(
            "DISPATCH_RESPONSE_INVALID",
            "framework dispatch response is empty, oversized, or not bytes",
        )
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
        canonical = canonical_json(value).encode("utf-8")
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        raise LabValidationError(
            "DISPATCH_RESPONSE_INVALID",
            "framework dispatch response must be canonical UTF-8 JSON",
        ) from exc
    expected_fields = {
        "schema_version",
        "invocation_digest",
        "provider_binding_digest",
        "provider_adapter_id",
        "framework_task_digest",
        "context_digest",
        "candidate_digest",
        "changed_paths",
        "validation_stages",
        "worker_output_digest",
    }
    if not isinstance(value, Mapping) or set(value) != expected_fields or canonical != raw:
        raise LabValidationError(
            "DISPATCH_RESPONSE_INVALID",
            "framework dispatch response fields or canonical bytes are invalid",
        )
    if value["schema_version"] != DISPATCH_RESPONSE_SCHEMA:
        raise LabValidationError("DISPATCH_RESPONSE_INVALID", "framework dispatch response schema differs")
    if (
        value["invocation_digest"] != invocation.identity_digest()
        or value["provider_binding_digest"] != binding.digest()
        or value["provider_adapter_id"] != binding.provider_adapter_id
        or not isinstance(value["changed_paths"], list)
        or any(not isinstance(p, str) for p in value["changed_paths"])
        or value["changed_paths"] != sorted(set(value["changed_paths"]))
        or not set(value["changed_paths"]) <= set(invocation.writable_paths)
    ):
        raise LabValidationError(
            "DISPATCH_IDENTITY_INVALID",
            "framework dispatch response differs from the sealed invocation or binding",
        )
    for name in (
        "framework_task_digest",
        "context_digest",
        "candidate_digest",
        "worker_output_digest",
    ):
        _digest(value[name], name)
    stages = value["validation_stages"]
    if not isinstance(stages, list) or len(stages) != len(invocation.test_ids):
        raise LabValidationError(
            "DISPATCH_RESPONSE_INVALID",
            "framework validation stages do not cover the sealed test plan",
        )
    observed_ids: list[str] = []
    for stage in stages:
        if not isinstance(stage, Mapping) or set(stage) != {"test_id", "outcome"}:
            raise LabValidationError(
                "DISPATCH_RESPONSE_INVALID",
                "framework validation stage fields are invalid",
            )
        test_id = _text(stage["test_id"], "validation test id")
        if stage["outcome"] != "pass":
            raise LabValidationError(
                "DISPATCH_RESPONSE_INVALID",
                "successful dispatch response contains a failed validation stage",
            )
        observed_ids.append(test_id)
    if tuple(observed_ids) != invocation.test_ids:
        raise LabValidationError(
            "DISPATCH_IDENTITY_INVALID",
            "framework validation stages differ from the sealed test plan",
        )
    return raw


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for name, item in pairs:
        if name in value:
            raise ValueError("duplicate JSON object key")
        value[name] = item
    return value


def _bytes_digest(value: bytes) -> str:
    return _DIGEST_PREFIX + hashlib.sha256(value).hexdigest()


def _digest(value: Any, name: str) -> str:
    text = _text(value, name)
    if len(text) != 71 or not text.startswith(_DIGEST_PREFIX):
        raise LabValidationError("DISPATCH_RESPONSE_INVALID", f"{name} is invalid")
    if any(character not in "0123456789abcdef" for character in text[7:]):
        raise LabValidationError("DISPATCH_RESPONSE_INVALID", f"{name} is invalid")
    return text


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        raise LabValidationError("DISPATCH_TASK_FIELDS_INVALID", f"{name} is invalid")
    return value


def _bounded_text(value: Any, name: str, limit: int) -> str:
    text = _text(value, name)
    try:
        encoded = text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise LabValidationError("DISPATCH_TASK_FIELDS_INVALID", f"{name} is not UTF-8") from exc
    if len(encoded) > limit:
        raise LabValidationError("DISPATCH_TASK_FIELDS_INVALID", f"{name} exceeds its bounded size")
    return text


def _text_array(
    value: Any,
    name: str,
    *,
    sorted_unique: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise LabValidationError("DISPATCH_TASK_FIELDS_INVALID", f"{name} must be a non-empty array")
    items = tuple(_text(item, name) for item in value)
    if len(items) != len(set(items)):
        raise LabValidationError("DISPATCH_TASK_FIELDS_INVALID", f"{name} must be unique")
    if sorted_unique and items != tuple(sorted(items)):
        raise LabValidationError("DISPATCH_TASK_FIELDS_INVALID", f"{name} must be sorted and unique")
    return items
