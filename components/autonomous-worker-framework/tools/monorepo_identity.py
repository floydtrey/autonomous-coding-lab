from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


SCHEMA_VERSION = "acl-framework-monorepo-identity-policy:v1"
POLICY_ID = "acl-framework-monorepo-identity:v1"
POLICY_PATH = "config/monorepo-identity.json"
FRAMEWORK_REPOSITORY_ID = "autonomous-worker-framework"
FRAMEWORK_PREFIX = "components/autonomous-worker-framework"
SOURCE_ADAPTER_PATH = "tools/worker_lab_adapter.py"
INTEGRATION_ADAPTER_PATH = f"{FRAMEWORK_PREFIX}/{SOURCE_ADAPTER_PATH}"
MAX_POLICY_BYTES = 16_384


class IdentityPolicyError(ValueError):
    """Raised when monorepo identity policy evidence is unsafe or stale."""


@dataclass(frozen=True)
class SourceProvenance:
    repository_id: str
    commit: str
    tree: str
    branch: str
    final_tag: str
    remote_state: str
    recovery_bundle_sha256: str
    adapter_blob: str
    adapter_sha256: str


@dataclass(frozen=True)
class IntegrationPolicy:
    import_commit: str
    canonical_component_prefix: str
    source_adapter_path: str
    adapter_integration_path: str
    component_scope: str
    shared_dependency_paths: tuple[str, ...]


@dataclass(frozen=True)
class FrameworkIdentityPolicy:
    schema_version: str
    policy_id: str
    activation_state: str
    execution_authority: str
    deferred_participants: tuple[str, ...]
    framework: SourceProvenance
    integration_policy: IntegrationPolicy


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for name, item in pairs:
        if name in value:
            raise IdentityPolicyError(f"duplicate identity policy field: {name}")
        value[name] = item
    return value


def _strict_object(value: object, fields: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise IdentityPolicyError(f"{name} fields are invalid")
    return value


def _text(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
    ):
        raise IdentityPolicyError(f"{name} is invalid")
    return value


def _sha1(value: object, name: str) -> str:
    text = _text(value, name)
    if len(text) != 40 or any(
        character not in "0123456789abcdef" for character in text
    ):
        raise IdentityPolicyError(f"{name} is not a canonical SHA-1 identity")
    return text


def _sha256(value: object, name: str) -> str:
    text = _text(value, name)
    if len(text) != 64 or any(
        character not in "0123456789abcdef" for character in text
    ):
        raise IdentityPolicyError(f"{name} is not a canonical SHA-256 identity")
    return text


def _relative_path(value: object, name: str) -> str:
    text = _text(value, name)
    candidate = PurePosixPath(text)
    if (
        "\\" in text
        or candidate.is_absolute()
        or ".." in candidate.parts
        or candidate.as_posix() != text
        or text == "."
        or ":" in candidate.parts[0]
    ):
        raise IdentityPolicyError(f"{name} is not a canonical repository path")
    return text


def _string_list(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise IdentityPolicyError(f"{name} must be a nonempty list")
    items = tuple(_text(item, name) for item in value)
    if list(items) != sorted(set(items)):
        raise IdentityPolicyError(f"{name} must be sorted and unique")
    return items


def canonical_policy_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"


def parse_identity_policy(raw: bytes | str) -> FrameworkIdentityPolicy:
    if isinstance(raw, str):
        try:
            encoded = raw.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise IdentityPolicyError("identity policy is not UTF-8") from exc
    elif isinstance(raw, bytes):
        encoded = raw
    else:
        raise IdentityPolicyError("identity policy must be bytes or text")
    if not encoded or len(encoded) > MAX_POLICY_BYTES or b"\x00" in encoded:
        raise IdentityPolicyError("identity policy is empty, unsafe, or oversized")
    try:
        value = json.loads(
            encoded.decode("utf-8"),
            object_pairs_hook=_unique_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IdentityPolicyError("identity policy must be UTF-8 JSON") from exc
    try:
        canonical = canonical_policy_json(value).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise IdentityPolicyError("identity policy is not canonical JSON") from exc
    if canonical != encoded:
        raise IdentityPolicyError("identity policy is not canonical JSON")

    top = _strict_object(
        value,
        {
            "schema_version",
            "policy_id",
            "activation_state",
            "execution_authority",
            "deferred_participants",
            "framework",
            "integration_policy",
        },
        "identity policy",
    )
    if top["schema_version"] != SCHEMA_VERSION or top["policy_id"] != POLICY_ID:
        raise IdentityPolicyError("identity policy schema or ID is unsupported")
    if top["activation_state"] != "FRAMEWORK_ONLY":
        raise IdentityPolicyError("identity policy is not framework-only")
    if top["execution_authority"] != "DISABLED":
        raise IdentityPolicyError("identity policy cannot grant execution authority")
    deferred = _string_list(top["deferred_participants"], "deferred participants")
    if deferred != ("worker-lab",):
        raise IdentityPolicyError("Worker Lab must remain deferred during M2")

    source = _strict_object(
        top["framework"],
        {
            "repository_id",
            "commit",
            "tree",
            "branch",
            "final_tag",
            "remote_state",
            "recovery_bundle_sha256",
            "adapter_blob",
            "adapter_sha256",
        },
        "framework provenance",
    )
    provenance = SourceProvenance(
        repository_id=_text(source["repository_id"], "framework repository ID"),
        commit=_sha1(source["commit"], "framework source commit"),
        tree=_sha1(source["tree"], "framework source tree"),
        branch=_text(source["branch"], "framework source branch"),
        final_tag=_text(source["final_tag"], "framework final tag"),
        remote_state=_text(source["remote_state"], "framework remote state"),
        recovery_bundle_sha256=_sha256(
            source["recovery_bundle_sha256"], "framework recovery bundle"
        ),
        adapter_blob=_sha1(source["adapter_blob"], "source adapter blob"),
        adapter_sha256=_sha256(source["adapter_sha256"], "source adapter digest"),
    )
    if provenance.repository_id != FRAMEWORK_REPOSITORY_ID:
        raise IdentityPolicyError("framework repository ID is substituted")
    if provenance.remote_state != "local-only":
        raise IdentityPolicyError("framework remote state is unsupported")

    integration = _strict_object(
        top["integration_policy"],
        {
            "import_commit",
            "canonical_component_prefix",
            "source_adapter_path",
            "adapter_integration_path",
            "component_scope",
            "shared_dependency_paths",
        },
        "framework integration policy",
    )
    component_prefix = _relative_path(
        integration["canonical_component_prefix"], "framework component prefix"
    )
    source_adapter_path = _relative_path(
        integration["source_adapter_path"], "source adapter path"
    )
    adapter_integration_path = _relative_path(
        integration["adapter_integration_path"], "integration adapter path"
    )
    shared_paths = tuple(
        _relative_path(path, "shared dependency path")
        for path in _string_list(
            integration["shared_dependency_paths"], "shared dependency paths"
        )
    )
    policy = IntegrationPolicy(
        import_commit=_sha1(integration["import_commit"], "framework import commit"),
        canonical_component_prefix=component_prefix,
        source_adapter_path=source_adapter_path,
        adapter_integration_path=adapter_integration_path,
        component_scope=_text(integration["component_scope"], "component scope"),
        shared_dependency_paths=shared_paths,
    )
    if policy.canonical_component_prefix != FRAMEWORK_PREFIX:
        raise IdentityPolicyError("framework component prefix is substituted")
    if policy.source_adapter_path != SOURCE_ADAPTER_PATH:
        raise IdentityPolicyError("source adapter path is substituted")
    if policy.adapter_integration_path != INTEGRATION_ADAPTER_PATH:
        raise IdentityPolicyError("integration adapter path is substituted")
    if policy.component_scope != "whole-component:v1":
        raise IdentityPolicyError("framework component scope is unsupported")
    if policy.shared_dependency_paths != (POLICY_PATH,):
        raise IdentityPolicyError("M2 shared dependency closure is unsupported")

    return FrameworkIdentityPolicy(
        schema_version=top["schema_version"],
        policy_id=top["policy_id"],
        activation_state=top["activation_state"],
        execution_authority=top["execution_authority"],
        deferred_participants=deferred,
        framework=provenance,
        integration_policy=policy,
    )


def require_source_provenance(
    policy: FrameworkIdentityPolicy, expected: SourceProvenance
) -> None:
    if policy.framework != expected:
        raise IdentityPolicyError("framework source provenance is stale or substituted")


def identity_policy_digest(raw: bytes | str) -> str:
    parse_identity_policy(raw)
    encoded = raw.encode("utf-8") if isinstance(raw, str) else raw
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
