from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = "acl-monorepo-identity-policy:v2"
POLICY_ID = "acl-monorepo-identity:v2"
POLICY_PATH = "config/monorepo-identity.json"
FRAMEWORK_REPOSITORY_ID = "autonomous-worker-framework"
FRAMEWORK_PREFIX = "components/autonomous-worker-framework"
SOURCE_ADAPTER_PATH = "tools/worker_lab_adapter.py"
INTEGRATION_ADAPTER_PATH = f"{FRAMEWORK_PREFIX}/{SOURCE_ADAPTER_PATH}"
WORKER_LAB_REPOSITORY_ID = "worker-lab"
WORKER_LAB_PREFIX = "components/worker-lab"
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
class WorkerSourceProvenance:
    repository_id: str
    commit: str
    tree: str
    branch: str
    final_tag: str
    remote_state: str
    recovery_bundle_sha256: str


@dataclass(frozen=True)
class WorkerIntegrationPolicy:
    import_commit: str
    canonical_component_prefix: str
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
    worker_lab: WorkerSourceProvenance
    worker_integration_policy: WorkerIntegrationPolicy


@dataclass(frozen=True)
class FrameworkIntegrationIdentity:
    schema_version: str
    monorepo_commit: str
    monorepo_tree: str
    source_commit: str
    source_tree: str
    import_commit: str
    component_prefix: str
    component_tree: str
    adapter_path: str
    adapter_blob: str
    adapter_digest: str
    policy_path: str
    policy_blob: str
    policy_digest: str
    dependency_set_version: str


GitRunner = Callable[[Path, tuple[str, ...]], bytes]


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
            "worker_lab",
            "worker_integration_policy",
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
        raise IdentityPolicyError("Worker Lab must remain operationally deferred")

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
        raise IdentityPolicyError("framework dependency closure is unsupported")

    worker = _strict_object(
        top["worker_lab"],
        {
            "repository_id",
            "commit",
            "tree",
            "branch",
            "final_tag",
            "remote_state",
            "recovery_bundle_sha256",
        },
        "Worker Lab provenance",
    )
    worker_provenance = WorkerSourceProvenance(
        repository_id=_text(worker["repository_id"], "Worker Lab repository ID"),
        commit=_sha1(worker["commit"], "Worker Lab source commit"),
        tree=_sha1(worker["tree"], "Worker Lab source tree"),
        branch=_text(worker["branch"], "Worker Lab source branch"),
        final_tag=_text(worker["final_tag"], "Worker Lab final tag"),
        remote_state=_text(worker["remote_state"], "Worker Lab remote state"),
        recovery_bundle_sha256=_sha256(
            worker["recovery_bundle_sha256"], "Worker Lab recovery bundle"
        ),
    )
    if worker_provenance.repository_id != WORKER_LAB_REPOSITORY_ID:
        raise IdentityPolicyError("Worker Lab repository ID is substituted")
    if worker_provenance.branch != "main":
        raise IdentityPolicyError("Worker Lab branch is substituted")
    if worker_provenance.final_tag != "v0.2.0-phase2":
        raise IdentityPolicyError("Worker Lab final tag is substituted")
    if worker_provenance.remote_state != "private-remote-local-ahead:10":
        raise IdentityPolicyError("Worker Lab remote state is unsupported")

    worker_integration = _strict_object(
        top["worker_integration_policy"],
        {
            "import_commit",
            "canonical_component_prefix",
            "component_scope",
            "shared_dependency_paths",
        },
        "Worker Lab integration policy",
    )
    worker_prefix = _relative_path(
        worker_integration["canonical_component_prefix"],
        "Worker Lab component prefix",
    )
    worker_shared_paths = tuple(
        _relative_path(path, "Worker Lab shared dependency path")
        for path in _string_list(
            worker_integration["shared_dependency_paths"],
            "Worker Lab shared dependency paths",
        )
    )
    worker_policy = WorkerIntegrationPolicy(
        import_commit=_sha1(
            worker_integration["import_commit"], "Worker Lab import commit"
        ),
        canonical_component_prefix=worker_prefix,
        component_scope=_text(
            worker_integration["component_scope"], "Worker Lab component scope"
        ),
        shared_dependency_paths=worker_shared_paths,
    )
    if worker_policy.canonical_component_prefix != WORKER_LAB_PREFIX:
        raise IdentityPolicyError("Worker Lab component prefix is substituted")
    if worker_policy.component_scope != "whole-component:v1":
        raise IdentityPolicyError("Worker Lab component scope is unsupported")
    if worker_policy.shared_dependency_paths != (FRAMEWORK_PREFIX, POLICY_PATH):
        raise IdentityPolicyError("Worker Lab dependency closure is unsupported")

    return FrameworkIdentityPolicy(
        schema_version=top["schema_version"],
        policy_id=top["policy_id"],
        activation_state=top["activation_state"],
        execution_authority=top["execution_authority"],
        deferred_participants=deferred,
        framework=provenance,
        integration_policy=policy,
        worker_lab=worker_provenance,
        worker_integration_policy=worker_policy,
    )


def require_source_provenance(
    policy: FrameworkIdentityPolicy, expected: SourceProvenance
) -> None:
    if policy.framework != expected:
        raise IdentityPolicyError("framework source provenance is stale or substituted")


def require_worker_source_provenance(
    policy: FrameworkIdentityPolicy, expected: WorkerSourceProvenance
) -> None:
    if policy.worker_lab != expected:
        raise IdentityPolicyError("Worker Lab source provenance is stale or substituted")


def identity_policy_digest(raw: bytes | str) -> str:
    parse_identity_policy(raw)
    encoded = raw.encode("utf-8") if isinstance(raw, str) else raw
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _git(repository_root: Path, args: tuple[str, ...]) -> bytes:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    process = subprocess.run(
        ["git", "-c", f"safe.directory={repository_root}", *args],
        cwd=repository_root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    if process.returncode != 0:
        raise IdentityPolicyError("monorepo Git identity check failed")
    return process.stdout


def _git_bytes(run_git: GitRunner, root: Path, *args: str) -> bytes:
    try:
        raw = run_git(root, tuple(args))
    except OSError as exc:
        raise IdentityPolicyError("monorepo Git identity check failed") from exc
    if not isinstance(raw, bytes):
        raise IdentityPolicyError("monorepo Git identity output is invalid")
    return raw


def _git_line(
    run_git: GitRunner,
    root: Path,
    *args: str,
    allow_spaces: bool = False,
) -> str:
    try:
        decoded = _git_bytes(run_git, root, *args).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IdentityPolicyError("monorepo Git identity output is invalid") from exc
    lines = decoded.splitlines()
    if len(lines) != 1 or not lines[0]:
        raise IdentityPolicyError("monorepo Git identity output is invalid")
    value = lines[0]
    if not allow_spaces and any(character.isspace() for character in value):
        raise IdentityPolicyError("monorepo Git identity output is invalid")
    return value


def _git_sha1(run_git: GitRunner, root: Path, *args: str) -> str:
    return _sha1(_git_line(run_git, root, *args), "monorepo Git object")


def _is_link_or_junction(path: Path) -> bool:
    try:
        junction_check = getattr(path, "is_junction", None)
        return path.is_symlink() or bool(junction_check and junction_check())
    except OSError as exc:
        raise IdentityPolicyError("identity path metadata is unreadable") from exc


def _require_plain_path(repository_root: Path, target: Path, name: str) -> None:
    try:
        relative = target.relative_to(repository_root)
    except ValueError as exc:
        raise IdentityPolicyError(f"{name} escapes the monorepo root") from exc
    current = repository_root
    if _is_link_or_junction(current):
        raise IdentityPolicyError(f"{name} uses a linked or reparse path")
    for part in relative.parts:
        current /= part
        if _is_link_or_junction(current):
            raise IdentityPolicyError(f"{name} uses a linked or reparse path")
    try:
        if not target.exists():
            raise IdentityPolicyError(f"{name} does not exist")
    except OSError as exc:
        raise IdentityPolicyError(f"{name} is unreadable") from exc


def _read_bytes(path: Path, name: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise IdentityPolicyError(f"{name} is unreadable") from exc


def _integration_identity_payload(
    identity: FrameworkIntegrationIdentity,
) -> dict[str, str]:
    return {
        "adapter_blob": identity.adapter_blob,
        "adapter_digest": identity.adapter_digest,
        "adapter_path": identity.adapter_path,
        "component_prefix": identity.component_prefix,
        "component_tree": identity.component_tree,
        "dependency_set_version": identity.dependency_set_version,
        "import_commit": identity.import_commit,
        "monorepo_commit": identity.monorepo_commit,
        "monorepo_tree": identity.monorepo_tree,
        "policy_blob": identity.policy_blob,
        "policy_digest": identity.policy_digest,
        "policy_path": identity.policy_path,
        "schema_version": identity.schema_version,
        "source_commit": identity.source_commit,
        "source_tree": identity.source_tree,
    }


def integration_identity_digest(identity: FrameworkIntegrationIdentity) -> str:
    encoded = json.dumps(
        _integration_identity_payload(identity),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def verify_framework_integration(
    policy: FrameworkIdentityPolicy,
    *,
    expected_monorepo_commit: str,
    component_root: Path,
    git_runner: GitRunner | None = None,
) -> FrameworkIntegrationIdentity:
    expected_head = _sha1(expected_monorepo_commit, "expected monorepo commit")
    run_git = git_runner or _git
    component_path = Path(os.path.abspath(component_root))
    prefix_parts = PurePosixPath(
        policy.integration_policy.canonical_component_prefix
    ).parts
    repository_root = component_path
    for _ in prefix_parts:
        repository_root = repository_root.parent
    expected_component = repository_root.joinpath(*prefix_parts)
    if os.path.normcase(str(component_path)) != os.path.normcase(
        str(expected_component)
    ):
        raise IdentityPolicyError("framework component root is substituted")

    _require_plain_path(repository_root, repository_root, "monorepo root")
    _require_plain_path(repository_root, component_path, "framework component root")
    adapter_path = repository_root.joinpath(
        *PurePosixPath(policy.integration_policy.adapter_integration_path).parts
    )
    policy_path = repository_root.joinpath(*PurePosixPath(POLICY_PATH).parts)
    _require_plain_path(repository_root, adapter_path, "framework adapter")
    _require_plain_path(repository_root, policy_path, "identity policy")

    reported_root = Path(
        _git_line(
            run_git,
            repository_root,
            "rev-parse",
            "--show-toplevel",
            allow_spaces=True,
        )
    )
    try:
        if reported_root.resolve(strict=True) != repository_root.resolve(strict=True):
            raise IdentityPolicyError("Git reported a substituted monorepo root")
    except OSError as exc:
        raise IdentityPolicyError("monorepo root is unreadable") from exc

    head = _git_sha1(run_git, repository_root, "rev-parse", "HEAD")
    if head != expected_head:
        raise IdentityPolicyError("monorepo commit is stale or substituted")
    monorepo_tree = _git_sha1(
        run_git, repository_root, "rev-parse", "HEAD^{tree}"
    )

    source = policy.framework
    source_tree = _git_sha1(
        run_git,
        repository_root,
        "rev-parse",
        f"{source.commit}^{{tree}}",
    )
    if source_tree != source.tree:
        raise IdentityPolicyError("framework source tree is stale or substituted")
    source_adapter_blob = _git_sha1(
        run_git,
        repository_root,
        "rev-parse",
        f"{source.commit}:{policy.integration_policy.source_adapter_path}",
    )
    if source_adapter_blob != source.adapter_blob:
        raise IdentityPolicyError("framework source adapter blob is substituted")
    source_adapter_bytes = _git_bytes(
        run_git,
        repository_root,
        "show",
        f"{source.commit}:{policy.integration_policy.source_adapter_path}",
    )
    if hashlib.sha256(source_adapter_bytes).hexdigest() != source.adapter_sha256:
        raise IdentityPolicyError("framework source adapter digest is substituted")

    import_component_tree = _git_sha1(
        run_git,
        repository_root,
        "rev-parse",
        (
            f"{policy.integration_policy.import_commit}:"
            f"{policy.integration_policy.canonical_component_prefix}"
        ),
    )
    if import_component_tree != source.tree:
        raise IdentityPolicyError("framework import subtree differs from provenance")
    import_adapter_blob = _git_sha1(
        run_git,
        repository_root,
        "rev-parse",
        (
            f"{policy.integration_policy.import_commit}:"
            f"{policy.integration_policy.adapter_integration_path}"
        ),
    )
    if import_adapter_blob != source.adapter_blob:
        raise IdentityPolicyError("framework imported adapter differs from provenance")

    component_tree = _git_sha1(
        run_git,
        repository_root,
        "rev-parse",
        f"HEAD:{policy.integration_policy.canonical_component_prefix}",
    )
    adapter_blob = _git_sha1(
        run_git,
        repository_root,
        "rev-parse",
        f"HEAD:{policy.integration_policy.adapter_integration_path}",
    )
    committed_adapter = _git_bytes(
        run_git,
        repository_root,
        "show",
        f"HEAD:{policy.integration_policy.adapter_integration_path}",
    )
    worktree_adapter = _read_bytes(adapter_path, "framework adapter")
    if committed_adapter != worktree_adapter:
        raise IdentityPolicyError("framework adapter worktree differs from HEAD")
    adapter_digest = "sha256:" + hashlib.sha256(worktree_adapter).hexdigest()

    policy_blob = _git_sha1(
        run_git, repository_root, "rev-parse", f"HEAD:{POLICY_PATH}"
    )
    committed_policy = _git_bytes(
        run_git, repository_root, "show", f"HEAD:{POLICY_PATH}"
    )
    worktree_policy = _read_bytes(policy_path, "identity policy")
    if committed_policy != worktree_policy:
        raise IdentityPolicyError("identity policy worktree differs from HEAD")
    parsed_worktree_policy = parse_identity_policy(worktree_policy)
    if parsed_worktree_policy != policy:
        raise IdentityPolicyError("identity policy input differs from the worktree")
    policy_digest = identity_policy_digest(worktree_policy)

    closure = (
        policy.integration_policy.canonical_component_prefix,
        *policy.integration_policy.shared_dependency_paths,
    )
    status = _git_bytes(
        run_git,
        repository_root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--",
        *closure,
    )
    if status:
        raise IdentityPolicyError("framework invocation dependency set is dirty")
    final_head = _git_sha1(run_git, repository_root, "rev-parse", "HEAD")
    if final_head != head:
        raise IdentityPolicyError("monorepo commit changed during identity verification")

    return FrameworkIntegrationIdentity(
        schema_version="acl-framework-monorepo-integration-identity:v1",
        monorepo_commit=head,
        monorepo_tree=monorepo_tree,
        source_commit=source.commit,
        source_tree=source.tree,
        import_commit=policy.integration_policy.import_commit,
        component_prefix=policy.integration_policy.canonical_component_prefix,
        component_tree=component_tree,
        adapter_path=policy.integration_policy.adapter_integration_path,
        adapter_blob=adapter_blob,
        adapter_digest=adapter_digest,
        policy_path=POLICY_PATH,
        policy_blob=policy_blob,
        policy_digest=policy_digest,
        dependency_set_version=policy.integration_policy.component_scope,
    )
