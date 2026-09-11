from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .runtime_selection import CODING_WORKER_V1


CANDIDATE_SCHEMA = "worker-lab-provider-candidate:v1"
QUALIFICATION_SCHEMA = "worker-lab-host-provider-qualification:v1"
QUALIFICATION_IDENTITY_SCHEMA = "worker-lab-host-provider-qualification-identity:v1"
PYDANTIC_AI_OLLAMA_CANDIDATE_ID = "pydantic-ai-ollama-files"
TOOL_SURFACE_ID = "acl-bounded-file-tools:v1"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
MINIMUM_CONTEXT_TOKENS = 32_768


@dataclass(frozen=True)
class ProviderCandidate:
    schema_version: str
    candidate_id: str
    candidate_version: int
    runtime_requirement_profile_id: str
    runtime_requirement_digest: str
    harness_project: str
    harness_distribution: str
    provider_kind: str
    transport_policy: str
    tool_surface_id: str
    allowed_effects: tuple[str, ...]
    forbidden_effects: tuple[str, ...]
    minimum_context_tokens: int
    required_model_capabilities: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["allowed_effects"] = list(self.allowed_effects)
        value["forbidden_effects"] = list(self.forbidden_effects)
        value["required_model_capabilities"] = list(self.required_model_capabilities)
        return value

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


PYDANTIC_AI_OLLAMA_V1 = ProviderCandidate(
    schema_version=CANDIDATE_SCHEMA,
    candidate_id=PYDANTIC_AI_OLLAMA_CANDIDATE_ID,
    candidate_version=1,
    runtime_requirement_profile_id=CODING_WORKER_V1.profile_id,
    runtime_requirement_digest=CODING_WORKER_V1.digest(),
    harness_project="pydantic/pydantic-ai",
    harness_distribution="pydantic-ai-slim",
    provider_kind="ollama",
    transport_policy="loopback-http-only",
    tool_surface_id=TOOL_SURFACE_ID,
    allowed_effects=("read-bounded-file", "write-bounded-file"),
    forbidden_effects=("approval", "git", "network", "process", "publication", "shell"),
    minimum_context_tokens=MINIMUM_CONTEXT_TOKENS,
    required_model_capabilities=("tools",),
)

PROTECTED_PROVIDER_CANDIDATES = (PYDANTIC_AI_OLLAMA_V1,)


@dataclass(frozen=True)
class HostProviderQualification:
    schema_version: str
    candidate_id: str
    candidate_version: int
    candidate_digest: str
    runtime_requirement_profile_id: str
    runtime_requirement_digest: str
    tool_surface_id: str
    host_platform: str
    host_architecture: str
    python_version: str
    python_executable: str
    python_sha256: str
    harness_distribution: str
    harness_version: str
    harness_tree_digest: str
    provider_kind: str
    provider_endpoint: str
    provider_executable: str
    provider_executable_sha256: str
    provider_cli_version: str
    provider_api_version: str
    model_name: str
    model_digest: str
    model_metadata_digest: str
    model_context_tokens: int
    model_capabilities: tuple[str, ...]
    execution_authority: str
    provider_runtime_qualified: bool
    execution_ready: bool

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["model_capabilities"] = list(self.model_capabilities)
        return value

    def digest(self) -> str:
        return canonical_digest({
            "schema_version": QUALIFICATION_IDENTITY_SCHEMA,
            "qualification": self.to_dict(),
        })

    @classmethod
    def from_mapping(
        cls,
        value: Any,
        *,
        candidate: ProviderCandidate = PYDANTIC_AI_OLLAMA_V1,
    ) -> "HostProviderQualification":
        if not isinstance(value, Mapping) or set(value) != set(cls.__dataclass_fields__):
            raise LabValidationError(
                "PROVIDER_QUALIFICATION_FIELDS_INVALID",
                "provider qualification fields are missing or unknown",
            )
        capabilities = _texts(value["model_capabilities"], "model capabilities")
        record = cls(
            _exact(value["schema_version"], QUALIFICATION_SCHEMA, "schema_version"),
            _text(value["candidate_id"], "candidate id"),
            _positive(value["candidate_version"], "candidate version"),
            _digest(value["candidate_digest"], "candidate digest"),
            _text(value["runtime_requirement_profile_id"], "runtime requirement profile"),
            _digest(value["runtime_requirement_digest"], "runtime requirement digest"),
            _text(value["tool_surface_id"], "tool surface"),
            _text(value["host_platform"], "host platform"),
            _text(value["host_architecture"], "host architecture"),
            _text(value["python_version"], "python version"),
            _absolute_path_text(value["python_executable"], "python executable"),
            _digest(value["python_sha256"], "python digest"),
            _text(value["harness_distribution"], "harness distribution"),
            _text(value["harness_version"], "harness version"),
            _digest(value["harness_tree_digest"], "harness tree digest"),
            _text(value["provider_kind"], "provider kind"),
            _loopback_endpoint(value["provider_endpoint"]),
            _absolute_path_text(value["provider_executable"], "provider executable"),
            _digest(value["provider_executable_sha256"], "provider executable digest"),
            _text(value["provider_cli_version"], "provider CLI version"),
            _text(value["provider_api_version"], "provider API version"),
            _text(value["model_name"], "model name"),
            _digest(value["model_digest"], "model digest"),
            _digest(value["model_metadata_digest"], "model metadata digest"),
            _positive(value["model_context_tokens"], "model context tokens"),
            capabilities,
            _exact(value["execution_authority"], "DISABLED", "execution_authority"),
            _true(value["provider_runtime_qualified"], "provider_runtime_qualified"),
            _false(value["execution_ready"], "execution_ready"),
        )
        _validate_qualification(record, candidate)
        return record


HttpJson = Callable[[str, str, Mapping[str, Any] | None, float], Mapping[str, Any]]
DistributionReader = Callable[[str], tuple[str, str]]
ExecutableResolver = Callable[[str], str | None]
VersionReader = Callable[[str], str]


def protected_provider_candidate(candidate_id: str) -> ProviderCandidate:
    for candidate in PROTECTED_PROVIDER_CANDIDATES:
        if candidate.candidate_id == candidate_id:
            return candidate
    raise LabValidationError(
        "PROVIDER_CANDIDATE_INVALID",
        "provider candidate is not protected by Worker Lab",
    )


def inspect_host_provider(
    *,
    model: str,
    repository_root: Path,
    candidate: ProviderCandidate = PYDANTIC_AI_OLLAMA_V1,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    executable_name: str = "ollama",
    timeout_seconds: float = 10.0,
    distribution_reader: DistributionReader | None = None,
    executable_resolver: ExecutableResolver | None = None,
    version_reader: VersionReader | None = None,
    http_json: HttpJson | None = None,
) -> HostProviderQualification:
    """Inspect an installed provider without sending a completion/chat request.

    Qualification is intentionally observation-only. It may inspect package bytes,
    provider version metadata and model metadata, but it never starts a provider,
    loads a model, sends /api/chat, or changes execution authority.
    """
    if candidate != protected_provider_candidate(candidate.candidate_id):
        raise LabValidationError(
            "PROVIDER_CANDIDATE_INVALID",
            "provider candidate differs from the protected declaration",
        )
    model = _text(model, "model name")
    repository_root = _real_directory(repository_root, "repository root")
    execution_authority = _portable_execution_authority(repository_root)
    if execution_authority != "DISABLED":
        raise LabValidationError(
            "PROVIDER_QUALIFICATION_AUTHORITY_INVALID",
            "provider qualification requires execution authority to remain disabled",
        )
    endpoint = _loopback_endpoint(base_url)

    distribution_reader = distribution_reader or inspect_distribution
    harness_version, harness_tree_digest = distribution_reader(candidate.harness_distribution)
    harness_version = _text(harness_version, "harness version")
    harness_tree_digest = _digest(harness_tree_digest, "harness tree digest")

    resolver = executable_resolver or shutil.which
    resolved = resolver(executable_name)
    if not resolved:
        raise LabValidationError(
            "PROVIDER_RUNTIME_UNAVAILABLE",
            "provider executable is unavailable",
        )
    executable = _real_file(Path(resolved), "provider executable")
    provider_executable_sha256 = _bytes_digest(executable.read_bytes())
    provider_cli_version = (version_reader or _provider_cli_version)(str(executable))

    request_json = http_json or _http_json
    version_payload = request_json("GET", endpoint + "/api/version", None, timeout_seconds)
    provider_api_version = _text(version_payload.get("version"), "provider API version")

    tags_payload = request_json("GET", endpoint + "/api/tags", None, timeout_seconds)
    model_digest = _model_digest_from_tags(tags_payload, model)

    show_payload = request_json("POST", endpoint + "/api/show", {"model": model}, timeout_seconds)
    capabilities = _model_capabilities(show_payload)
    context_tokens = _model_context_tokens(show_payload)
    metadata_digest = canonical_digest(show_payload)

    missing = set(candidate.required_model_capabilities) - set(capabilities)
    if missing:
        raise LabValidationError(
            "PROVIDER_MODEL_CAPABILITY_INVALID",
            "model metadata lacks a required capability",
        )
    if context_tokens < candidate.minimum_context_tokens:
        raise LabValidationError(
            "PROVIDER_MODEL_CONTEXT_INVALID",
            "model context is below the protected minimum",
        )

    python_path = _real_file(Path(sys.executable), "Python executable")
    record = HostProviderQualification(
        schema_version=QUALIFICATION_SCHEMA,
        candidate_id=candidate.candidate_id,
        candidate_version=candidate.candidate_version,
        candidate_digest=candidate.digest(),
        runtime_requirement_profile_id=candidate.runtime_requirement_profile_id,
        runtime_requirement_digest=candidate.runtime_requirement_digest,
        tool_surface_id=candidate.tool_surface_id,
        host_platform=platform.system(),
        host_architecture=platform.machine(),
        python_version=platform.python_version(),
        python_executable=str(python_path),
        python_sha256=_bytes_digest(python_path.read_bytes()),
        harness_distribution=candidate.harness_distribution,
        harness_version=harness_version,
        harness_tree_digest=harness_tree_digest,
        provider_kind=candidate.provider_kind,
        provider_endpoint=endpoint,
        provider_executable=str(executable),
        provider_executable_sha256=provider_executable_sha256,
        provider_cli_version=_text(provider_cli_version, "provider CLI version"),
        provider_api_version=provider_api_version,
        model_name=model,
        model_digest=model_digest,
        model_metadata_digest=metadata_digest,
        model_context_tokens=context_tokens,
        model_capabilities=capabilities,
        execution_authority="DISABLED",
        provider_runtime_qualified=True,
        execution_ready=False,
    )
    _validate_qualification(record, candidate)
    return record


def inspect_distribution(distribution_name: str) -> tuple[str, str]:
    """Return exact installed Pydantic AI distribution version and Python-tree digest."""
    try:
        distribution = importlib.metadata.distribution(distribution_name)
    except importlib.metadata.PackageNotFoundError as exc:
        raise LabValidationError(
            "PROVIDER_HARNESS_UNAVAILABLE",
            "qualified harness distribution is not installed",
        ) from exc
    version = _text(distribution.version, "harness version")
    entries: list[dict[str, str]] = []
    for item in distribution.files or ():
        pure = PurePosixPath(str(item).replace("\\", "/"))
        if not pure.parts or pure.parts[0] != "pydantic_ai" or pure.suffix != ".py":
            continue
        if "__pycache__" in pure.parts:
            continue
        path = _real_file(Path(distribution.locate_file(item)), "harness package file")
        entries.append({"path": pure.as_posix(), "sha256": _bytes_digest(path.read_bytes())})
    entries.sort(key=lambda item: item["path"])
    if not entries or len({item["path"] for item in entries}) != len(entries):
        raise LabValidationError(
            "PROVIDER_HARNESS_IDENTITY_INVALID",
            "harness Python production tree is empty or ambiguous",
        )
    return version, canonical_digest(entries)


def _validate_qualification(record: HostProviderQualification, candidate: ProviderCandidate) -> None:
    expected = (
        record.candidate_id == candidate.candidate_id,
        record.candidate_version == candidate.candidate_version,
        record.candidate_digest == candidate.digest(),
        record.runtime_requirement_profile_id == candidate.runtime_requirement_profile_id,
        record.runtime_requirement_digest == candidate.runtime_requirement_digest,
        record.tool_surface_id == candidate.tool_surface_id,
        record.harness_distribution == candidate.harness_distribution,
        record.provider_kind == candidate.provider_kind,
        record.execution_authority == "DISABLED",
        record.provider_runtime_qualified is True,
        record.execution_ready is False,
        record.model_context_tokens >= candidate.minimum_context_tokens,
        set(candidate.required_model_capabilities).issubset(record.model_capabilities),
    )
    if not all(expected):
        raise LabValidationError(
            "PROVIDER_QUALIFICATION_INVALID",
            "provider qualification differs from the protected candidate or authority boundary",
        )


def _portable_execution_authority(repository_root: Path) -> str:
    path = repository_root / "config" / "portable-installation-manifest.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        authority = value["activation_policy"]["execution_authority"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise LabValidationError(
            "PROVIDER_QUALIFICATION_AUTHORITY_INVALID",
            "portable execution authority is unavailable",
        ) from exc
    return _text(authority, "execution authority")


def _provider_cli_version(executable: str) -> str:
    try:
        process = subprocess.run(
            [executable, "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LabValidationError(
            "PROVIDER_RUNTIME_UNAVAILABLE",
            "provider version command did not complete",
        ) from exc
    output = (process.stdout or process.stderr).strip()
    if process.returncode != 0 or not output:
        raise LabValidationError(
            "PROVIDER_RUNTIME_UNAVAILABLE",
            "provider version command failed",
        )
    return output


def _http_json(
    method: str,
    url: str,
    payload: Mapping[str, Any] | None,
    timeout_seconds: float,
) -> Mapping[str, Any]:
    body = None if payload is None else canonical_json(dict(payload)).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read(2_000_001)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LabValidationError(
            "PROVIDER_RUNTIME_UNAVAILABLE",
            "provider metadata endpoint is unavailable",
        ) from exc
    if len(raw) > 2_000_000:
        raise LabValidationError(
            "PROVIDER_RUNTIME_INVALID",
            "provider metadata response is oversized",
        )
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LabValidationError(
            "PROVIDER_RUNTIME_INVALID",
            "provider metadata response is invalid",
        ) from exc
    if not isinstance(value, Mapping):
        raise LabValidationError(
            "PROVIDER_RUNTIME_INVALID",
            "provider metadata response must be an object",
        )
    return value


def _model_digest_from_tags(payload: Mapping[str, Any], model: str) -> str:
    models = payload.get("models")
    if not isinstance(models, list):
        raise LabValidationError("PROVIDER_MODEL_INVALID", "provider model inventory is invalid")
    matches: list[str] = []
    for item in models:
        if not isinstance(item, Mapping):
            continue
        name = item.get("model") or item.get("name")
        if name == model:
            matches.append(_digest(item.get("digest"), "model digest"))
    if len(matches) != 1:
        raise LabValidationError(
            "PROVIDER_MODEL_INVALID",
            "qualified model name must resolve to exactly one immutable digest",
        )
    return matches[0]


def _model_capabilities(payload: Mapping[str, Any]) -> tuple[str, ...]:
    value = payload.get("capabilities")
    if not isinstance(value, list):
        raise LabValidationError(
            "PROVIDER_MODEL_CAPABILITY_INVALID",
            "provider model capabilities are unavailable",
        )
    return _texts(value, "model capabilities")


def _model_context_tokens(payload: Mapping[str, Any]) -> int:
    values: list[int] = []

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                if isinstance(key, str) and key.endswith(".context_length"):
                    if isinstance(item, int) and not isinstance(item, bool) and item > 0:
                        values.append(item)
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload.get("model_info", payload))
    if not values:
        raise LabValidationError(
            "PROVIDER_MODEL_CONTEXT_INVALID",
            "provider model metadata does not expose context length",
        )
    return max(values)


def _loopback_endpoint(value: Any) -> str:
    text = _text(value, "provider endpoint").rstrip("/")
    parsed = urllib.parse.urlparse(text)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or parsed.port is None
    ):
        raise LabValidationError(
            "PROVIDER_ENDPOINT_INVALID",
            "provider endpoint must be loopback HTTP with an explicit port",
        )
    return text


def _real_directory(path: Path, name: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise LabValidationError("PROVIDER_PATH_INVALID", f"{name} is unavailable") from exc
    if not resolved.is_dir() or _is_reparse(resolved):
        raise LabValidationError("PROVIDER_PATH_INVALID", f"{name} must be a real directory")
    return resolved


def _real_file(path: Path, name: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise LabValidationError("PROVIDER_PATH_INVALID", f"{name} is unavailable") from exc
    if not resolved.is_file() or _is_reparse(resolved):
        raise LabValidationError("PROVIDER_PATH_INVALID", f"{name} must be a real file")
    return resolved


def _is_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    return bool(getattr(os.lstat(path), "st_file_attributes", 0) & 0x400)


def _bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _digest(value: Any, name: str) -> str:
    text = _text(value, name)
    if len(text) != 71 or not text.startswith("sha256:"):
        raise LabValidationError("PROVIDER_IDENTITY_INVALID", f"{name} is invalid")
    if any(character not in "0123456789abcdef" for character in text[7:]):
        raise LabValidationError("PROVIDER_IDENTITY_INVALID", f"{name} is invalid")
    return text


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or "\x00" in value:
        raise LabValidationError("PROVIDER_FIELD_INVALID", f"{name} is invalid")
    return value


def _texts(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise LabValidationError("PROVIDER_FIELD_INVALID", f"{name} must be an array")
    items = tuple(_text(item, name) for item in value)
    if not items or items != tuple(sorted(set(items))):
        raise LabValidationError("PROVIDER_FIELD_INVALID", f"{name} must be sorted and unique")
    return items


def _positive(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LabValidationError("PROVIDER_FIELD_INVALID", f"{name} must be positive")
    return value


def _true(value: Any, name: str) -> bool:
    if value is not True:
        raise LabValidationError("PROVIDER_FIELD_INVALID", f"{name} must be true")
    return True


def _false(value: Any, name: str) -> bool:
    if value is not False:
        raise LabValidationError("PROVIDER_FIELD_INVALID", f"{name} must be false")
    return False


def _exact(value: Any, expected: str, name: str) -> str:
    text = _text(value, name)
    if text != expected:
        raise LabValidationError("PROVIDER_FIELD_INVALID", f"{name} is unsupported")
    return text


def _absolute_path_text(value: Any, name: str) -> str:
    text = _text(value, name)
    if not Path(text).is_absolute():
        raise LabValidationError("PROVIDER_PATH_INVALID", f"{name} must be absolute")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect one protected ACL host provider without running a model"
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default=DEFAULT_OLLAMA_BASE_URL)
    parser.add_argument("--ollama-executable", default="ollama")
    args = parser.parse_args(argv)
    repository_root = Path(__file__).resolve().parents[3]
    try:
        report = inspect_host_provider(
            model=args.model,
            repository_root=repository_root,
            base_url=args.base_url,
            executable_name=args.ollama_executable,
        )
    except LabValidationError as exc:
        print(f"ERROR {exc.code}: {exc}", file=sys.stderr)
        return 1
    print(canonical_json({**report.to_dict(), "qualification_digest": report.digest()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
