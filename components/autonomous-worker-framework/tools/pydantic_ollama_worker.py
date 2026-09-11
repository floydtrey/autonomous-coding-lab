from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import tempfile
import urllib.parse
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

try:
    from tools.worker_runtime import PROVIDER_QUALIFIED, WorkerExecution, WorkerRequest
except ModuleNotFoundError:  # direct execution support
    from worker_runtime import PROVIDER_QUALIFIED, WorkerExecution, WorkerRequest  # type: ignore


CANDIDATE_ID = "pydantic-ai-ollama-files"
TOOL_SURFACE_ID = "acl-bounded-file-tools:v1"
HARNESS_DISTRIBUTION = "pydantic-ai-slim"
PROVIDER_KIND = "ollama"
RUNTIME_SETTINGS_SCHEMA = "worker-lab-runtime-settings:v1"
MAX_FILE_BYTES = 262_144
MAX_FINAL_MESSAGE_BYTES = 32_768
ABSENT_DIGEST = "absent"
_DIGEST_PREFIX = "sha256:"


class PydanticWorkerError(RuntimeError):
    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary


@dataclass(frozen=True)
class QualifiedRuntimeBinding:
    """Exact host-qualified runtime evidence consumed by the provider adapter.

    This record is evidence only. It never grants execution authority. The outer
    Worker Lab invocation and framework dispatch gates remain authoritative.
    """

    qualification_digest: str
    installation_observation_digest: str
    runtime_settings_profile_id: str
    runtime_settings_digest: str
    qualified_context_tokens: int
    candidate_id: str
    tool_surface_id: str
    harness_distribution: str
    harness_version: str
    harness_tree_digest: str
    provider_kind: str
    provider_endpoint: str
    provider_executable_sha256: str
    provider_cli_version: str
    provider_api_version: str
    model_name: str
    model_digest: str
    model_metadata_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        encoded = json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return _bytes_digest(encoded)


@dataclass(frozen=True)
class SealedRuntimeSettings:
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
        return _bytes_digest(_canonical_json(self.to_dict()).encode("utf-8"))

    @classmethod
    def from_mapping(cls, value: Any) -> "SealedRuntimeSettings":
        fields = set(cls.__dataclass_fields__)
        if not isinstance(value, dict) or set(value) != fields:
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_SETTINGS_INVALID",
                "runtime settings fields are missing or unknown",
            )
        if value.get("schema_version") != RUNTIME_SETTINGS_SCHEMA:
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_SETTINGS_INVALID",
                "runtime settings schema differs",
            )
        profile_id = value.get("profile_id")
        if not isinstance(profile_id, str) or not profile_id.strip() or profile_id != profile_id.strip():
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_SETTINGS_INVALID",
                "runtime settings profile is invalid",
            )
        positive = (
            "profile_version",
            "requested_context_tokens",
            "request_limit",
            "tool_calls_limit",
            "tool_timeout_seconds",
            "max_concurrency",
        )
        nonnegative = ("tool_retries", "output_retries")
        for name in positive:
            item = value.get(name)
            if isinstance(item, bool) or not isinstance(item, int) or item <= 0:
                raise PydanticWorkerError(
                    "PYDANTIC_WORKER_SETTINGS_INVALID",
                    f"{name} must be positive",
                )
        for name in nonnegative:
            item = value.get(name)
            if isinstance(item, bool) or not isinstance(item, int) or item < 0:
                raise PydanticWorkerError(
                    "PYDANTIC_WORKER_SETTINGS_INVALID",
                    f"{name} must be nonnegative",
                )
        return cls(**value)


class BoundedFileTools:
    """Exact-file UTF-8 read/write surface owned by ACL, not by the model provider."""

    def __init__(
        self,
        root: Path,
        *,
        readable_paths: tuple[str, ...],
        writable_paths: tuple[str, ...],
    ) -> None:
        self.root = _real_directory(root, "target repository")
        self.readable_paths = _scope(readable_paths, "readable paths")
        self.writable_paths = _scope(writable_paths, "writable paths")
        if not self.writable_paths or not set(self.writable_paths).issubset(self.readable_paths):
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_SCOPE_INVALID",
                "writable paths must be a non-empty subset of readable paths",
            )

    def read_file(self, path: str) -> str:
        """Read one exact authorized UTF-8 file and return its content plus SHA-256."""
        relative = _relative_path(path)
        if relative not in self.readable_paths:
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_SCOPE_DENIED",
                "read path is outside the sealed file scope",
            )
        target = self._existing_file(relative, writable=False)
        content = target.read_bytes()
        if len(content) > MAX_FILE_BYTES or b"\x00" in content:
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_FILE_INVALID",
                "authorized file is binary, unsafe, or oversized",
            )
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_FILE_INVALID",
                "authorized file is not UTF-8",
            ) from exc
        return _canonical_json(
            {
                "path": relative,
                "sha256": _bytes_digest(content),
                "content": text,
            }
        )

    def write_file(self, path: str, content: str, expected_sha256: str) -> str:
        """Atomically write one exact authorized UTF-8 file after a stale-write check."""
        relative = _relative_path(path)
        if relative not in self.writable_paths:
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_SCOPE_DENIED",
                "write path is outside the sealed writable scope",
            )
        if not isinstance(content, str) or "\x00" in content:
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_FILE_INVALID",
                "write content must be UTF-8 text without NUL bytes",
            )
        try:
            encoded = content.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_FILE_INVALID",
                "write content must be UTF-8 text",
            ) from exc
        if len(encoded) > MAX_FILE_BYTES:
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_FILE_INVALID",
                "write content exceeds the bounded file limit",
            )
        expected = _expected_digest(expected_sha256)
        target = self._candidate_file(relative)
        if target.exists():
            target = self._existing_file(relative, writable=True)
            current = _bytes_digest(target.read_bytes())
            if expected == ABSENT_DIGEST or current != expected:
                raise PydanticWorkerError(
                    "PYDANTIC_WORKER_STALE_WRITE",
                    "write precondition differs from the current file",
                )
        elif expected != ABSENT_DIGEST:
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_STALE_WRITE",
                "write expected an existing file that is absent",
            )

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".acl-worker-",
            suffix=".tmp",
            dir=target.parent,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        return _canonical_json(
            {
                "path": relative,
                "sha256": _bytes_digest(encoded),
                "bytes": len(encoded),
            }
        )

    def _candidate_file(self, relative: str) -> Path:
        parts = PurePosixPath(relative).parts
        current = self.root
        for part in parts[:-1]:
            current = current / part
            if not current.exists() or not current.is_dir() or _is_linklike(current):
                raise PydanticWorkerError(
                    "PYDANTIC_WORKER_SCOPE_DENIED",
                    "authorized path traverses an unavailable or substituted directory",
                )
        target = current / parts[-1]
        if _is_linklike(target):
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_SCOPE_DENIED",
                "authorized path resolves through a link or reparse point",
            )
        return target

    def _existing_file(self, relative: str, *, writable: bool) -> Path:
        target = self._candidate_file(relative)
        if not target.exists() or not target.is_file():
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_FILE_INVALID",
                "authorized path is not an existing regular file",
            )
        if writable:
            try:
                links = os.stat(target, follow_symlinks=False).st_nlink
            except OSError as exc:
                raise PydanticWorkerError(
                    "PYDANTIC_WORKER_FILE_INVALID",
                    "authorized file metadata is unavailable",
                ) from exc
            if links != 1:
                raise PydanticWorkerError(
                    "PYDANTIC_WORKER_SCOPE_DENIED",
                    "writable file has multiple hard links",
                )
        return target


AgentRunner = Callable[[WorkerRequest, QualifiedRuntimeBinding, SealedRuntimeSettings, BoundedFileTools], str]


def execute_pydantic_ollama(
    request: WorkerRequest,
    binding: QualifiedRuntimeBinding,
    runtime_settings: Mapping[str, Any] | SealedRuntimeSettings,
    *,
    runner: AgentRunner | None = None,
) -> WorkerExecution:
    """Execute one provider-qualified request through only ACL-owned file tools."""
    _validate_request(request)
    settings = (
        runtime_settings
        if isinstance(runtime_settings, SealedRuntimeSettings)
        else SealedRuntimeSettings.from_mapping(dict(runtime_settings))
    )
    _validate_binding(binding, settings)
    tools = BoundedFileTools(
        request.target_repo,
        readable_paths=request.readable_paths,
        writable_paths=request.writable_paths,
    )
    output = (runner or _run_pydantic_agent)(request, binding, settings, tools)
    if not isinstance(output, str) or not output.strip() or "\x00" in output:
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_RESULT_INVALID",
            "provider final message is empty or invalid",
        )
    encoded = output.encode("utf-8")
    if len(encoded) > MAX_FINAL_MESSAGE_BYTES:
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_RESULT_INVALID",
            "provider final message exceeds the bounded output limit",
        )
    return WorkerExecution(
        (
            "pydantic-ai",
            binding.harness_version,
            "ollama",
            binding.provider_api_version,
            binding.model_name,
        ),
        0,
        output,
        "",
    )


def _run_pydantic_agent(
    request: WorkerRequest,
    binding: QualifiedRuntimeBinding,
    settings: SealedRuntimeSettings,
    tools: BoundedFileTools,
) -> str:
    """Production Pydantic AI path. Imports are intentionally lazy for deterministic tests."""
    try:
        from pydantic_ai import Agent, UsageLimits
        from pydantic_ai.models.ollama import OllamaModel
        from pydantic_ai.providers.ollama import OllamaProvider
    except ImportError as exc:
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_HARNESS_UNAVAILABLE",
            "qualified Pydantic AI harness is unavailable",
        ) from exc

    installed_version = importlib.metadata.version(HARNESS_DISTRIBUTION)
    if installed_version != binding.harness_version:
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_HARNESS_IDENTITY_INVALID",
            "installed Pydantic AI version differs from qualification",
        )

    base_url = binding.provider_endpoint.rstrip("/") + "/v1"
    model = OllamaModel(
        binding.model_name,
        provider=OllamaProvider(base_url=base_url),
    )
    agent = Agent(
        model,
        instructions=(
            "You are a bounded coding worker. You have exactly two ACL-owned tools: "
            "read_file and write_file. You have no shell, Git, network, process, approval, "
            "publication, directory-listing, or arbitrary filesystem authority. Read only "
            "the exact paths made available to you. Before every write, read the target and "
            "pass the returned SHA-256 as expected_sha256. Make only the requested bounded "
            "change, then return a concise summary."
        ),
        tools=(tools.read_file, tools.write_file),
        retries={"tools": settings.tool_retries, "output": settings.output_retries},
        tool_timeout=settings.tool_timeout_seconds,
        max_concurrency=settings.max_concurrency,
    )
    try:
        result = agent.run_sync(
            request.prompt,
            usage_limits=UsageLimits(
                request_limit=settings.request_limit,
                tool_calls_limit=settings.tool_calls_limit,
            ),
        )
    except Exception as exc:
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_EXECUTION_FAILED",
            "Pydantic AI worker run did not complete",
        ) from exc
    if not isinstance(result.output, str):
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_RESULT_INVALID",
            "Pydantic AI final output is not text",
        )
    return result.output


def _validate_request(request: WorkerRequest) -> None:
    if not isinstance(request, WorkerRequest):
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_REQUEST_INVALID",
            "worker request type is invalid",
        )
    if (
        request.sandbox != "workspace-write"
        or request.model != PROVIDER_QUALIFIED
        or request.reasoning_effort != PROVIDER_QUALIFIED
        or not isinstance(request.prompt, str)
        or not request.prompt.strip()
        or request.timeout_seconds <= 0
    ):
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_REQUEST_INVALID",
            "worker request differs from the provider-neutral workspace-write contract",
        )
    readable = _scope(request.readable_paths, "readable paths")
    writable = _scope(request.writable_paths, "writable paths")
    if not writable or not set(writable).issubset(readable):
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_SCOPE_INVALID",
            "worker request file scope is invalid",
        )


def _validate_binding(
    binding: QualifiedRuntimeBinding,
    settings: SealedRuntimeSettings,
) -> None:
    if not isinstance(binding, QualifiedRuntimeBinding):
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_BINDING_INVALID",
            "provider binding type is invalid",
        )
    for value, name in (
        (binding.qualification_digest, "qualification digest"),
        (binding.installation_observation_digest, "installation observation digest"),
        (binding.runtime_settings_digest, "runtime settings digest"),
        (binding.harness_tree_digest, "harness tree digest"),
        (binding.provider_executable_sha256, "provider executable digest"),
        (binding.model_digest, "model digest"),
        (binding.model_metadata_digest, "model metadata digest"),
    ):
        _digest(value, name)
    if (
        binding.candidate_id != CANDIDATE_ID
        or binding.tool_surface_id != TOOL_SURFACE_ID
        or binding.harness_distribution != HARNESS_DISTRIBUTION
        or binding.provider_kind != PROVIDER_KIND
        or binding.runtime_settings_profile_id != settings.profile_id
        or binding.runtime_settings_digest != settings.digest()
        or isinstance(binding.qualified_context_tokens, bool)
        or not isinstance(binding.qualified_context_tokens, int)
        or binding.qualified_context_tokens < settings.requested_context_tokens
    ):
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_BINDING_INVALID",
            "provider binding differs from the protected adapter candidate",
        )
    for value in (
        binding.harness_version,
        binding.provider_cli_version,
        binding.provider_api_version,
        binding.model_name,
    ):
        if not isinstance(value, str) or not value.strip() or value != value.strip() or "\x00" in value:
            raise PydanticWorkerError(
                "PYDANTIC_WORKER_BINDING_INVALID",
                "provider binding text field is invalid",
            )
    _loopback_endpoint(binding.provider_endpoint)


def _scope(values: tuple[str, ...], name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values:
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_SCOPE_INVALID",
            f"{name} must be a non-empty tuple",
        )
    normalized = tuple(_relative_path(value) for value in values)
    if normalized != tuple(sorted(set(normalized))):
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_SCOPE_INVALID",
            f"{name} must be sorted and unique",
        )
    return normalized


def _relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\\" in value:
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_SCOPE_INVALID",
            "file path is invalid",
        )
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or value.startswith("/")
        or ".." in candidate.parts
        or candidate.as_posix() != value
        or value == "."
        or any(":" in part for part in candidate.parts)
        or candidate.parts[0] == ".git"
    ):
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_SCOPE_INVALID",
            "file path is outside the bounded file policy",
        )
    return value


def _real_directory(path: Path, name: str) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_SCOPE_INVALID",
            f"{name} must be an absolute path",
        )
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_SCOPE_INVALID",
            f"{name} is unavailable",
        ) from exc
    if not resolved.is_dir() or _is_linklike(path) or os.path.normcase(str(resolved)) != os.path.normcase(str(path)):
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_SCOPE_INVALID",
            f"{name} must be a real directory",
        )
    return resolved


def _is_linklike(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_SCOPE_INVALID",
            "file identity is unavailable",
        ) from exc
    return bool(attributes & 0x400)


def _loopback_endpoint(value: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_BINDING_INVALID",
            "provider endpoint is invalid",
        )
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.port is None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_BINDING_INVALID",
            "provider endpoint must be loopback HTTP with an explicit port",
        )
    return value.rstrip("/")


def _expected_digest(value: str) -> str:
    if value == ABSENT_DIGEST:
        return value
    return _digest(value, "expected SHA-256")


def _digest(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 71
        or not value.startswith(_DIGEST_PREFIX)
        or any(character not in "0123456789abcdef" for character in value[7:])
    ):
        raise PydanticWorkerError(
            "PYDANTIC_WORKER_BINDING_INVALID",
            f"{name} is invalid",
        )
    return value


def _bytes_digest(value: bytes) -> str:
    return _DIGEST_PREFIX + hashlib.sha256(value).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
