from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor, found {text.count(old)}")
    write(path, text.replace(old, new, 1))


def replace_between(path: str, start: str, end: str, replacement: str) -> None:
    text = read(path)
    i = text.find(start)
    if i < 0:
        raise SystemExit(f"{path}: start anchor missing: {start!r}")
    j = text.find(end, i)
    if j < 0:
        raise SystemExit(f"{path}: end anchor missing: {end!r}")
    write(path, text[:i] + replacement + text[j:])


# ---------------------------------------------------------------------------
# Worker Lab: one protected runtime-settings definition shared by binding and
# controlled provider capability qualification.
# ---------------------------------------------------------------------------
write(
    "components/worker-lab/worker_lab/runtime_settings.py",
    '''from __future__ import annotations

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
''',
)


# ---------------------------------------------------------------------------
# Worker Lab: preserve HostProviderQualification V1 exactly as the historical
# metadata-only record, and add the current observation/capability split.
# ---------------------------------------------------------------------------
pq = "components/worker-lab/worker_lab/provider_qualification.py"
replace_once(
    pq,
    "from .runtime_selection import CODING_WORKER_V1\n",
    "from .runtime_selection import CODING_WORKER_V1, selected_runtime_requirement_v3\n"
    "from .runtime_settings import (\n"
    "    CODING_WORKER_SETTINGS_V1,\n"
    "    RuntimeSettingsProfile,\n"
    "    validate_runtime_settings,\n"
    ")\n",
)
replace_once(
    pq,
    'MINIMUM_CONTEXT_TOKENS = 32_768\n',
    'MINIMUM_CONTEXT_TOKENS = 32_768\n'
    'INSTALLATION_OBSERVATION_SCHEMA = "worker-lab-provider-installation-observation:v1"\n'
    'INSTALLATION_OBSERVATION_IDENTITY_SCHEMA = "worker-lab-provider-installation-observation-identity:v1"\n'
    'CAPABILITY_PROBE_REQUEST_SCHEMA = "worker-lab-provider-capability-probe-request:v1"\n'
    'CAPABILITY_PROBE_EVIDENCE_SCHEMA = "worker-lab-provider-capability-probe-evidence:v1"\n'
    'CAPABILITY_QUALIFICATION_SCHEMA = "worker-lab-provider-capability-qualification:v1"\n'
    'CAPABILITY_QUALIFICATION_IDENTITY_SCHEMA = "worker-lab-provider-capability-qualification-identity:v1"\n'
    'PROVIDER_ADAPTER_ID = "pydantic-ai-ollama-files:v1"\n'
    'TOOL_CAPABILITY_FIXTURE_ID = "acl-bounded-file-tool-probe:v1"\n'
    'CONTEXT_CAPABILITY_FIXTURE_ID = "acl-context-retention-probe:v1"\n'
    'TOOL_CAPABILITY_PATH = "qualification/input.txt"\n'
    'TOOL_CAPABILITY_RESULT_DIGEST = canonical_digest({"fixture": "bounded-file-tool-result:v1"})\n'
    'CONTEXT_CAPABILITY_CANARY_DIGEST = canonical_digest({"fixture": "context-retention-canary:v1"})\n',
)

new_types = r'''
@dataclass(frozen=True)
class ProviderInstallationObservation:
    """Exact installed bytes/metadata only; this is not capability qualification."""

    schema_version: str
    candidate_id: str
    candidate_version: int
    candidate_digest: str
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

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["model_capabilities"] = list(self.model_capabilities)
        return value

    def digest(self) -> str:
        return canonical_digest({
            "schema_version": INSTALLATION_OBSERVATION_IDENTITY_SCHEMA,
            "observation": self.to_dict(),
        })

    @classmethod
    def from_mapping(
        cls,
        value: Any,
        *,
        candidate: ProviderCandidate = PYDANTIC_AI_OLLAMA_V1,
    ) -> "ProviderInstallationObservation":
        if not isinstance(value, Mapping) or set(value) != set(cls.__dataclass_fields__):
            raise LabValidationError(
                "PROVIDER_INSTALLATION_FIELDS_INVALID",
                "provider installation observation fields are missing or unknown",
            )
        record = cls(
            _exact(value["schema_version"], INSTALLATION_OBSERVATION_SCHEMA, "schema_version"),
            _text(value["candidate_id"], "candidate id"),
            _positive(value["candidate_version"], "candidate version"),
            _digest(value["candidate_digest"], "candidate digest"),
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
            _texts(value["model_capabilities"], "model capabilities"),
            _exact(value["execution_authority"], "DISABLED", "execution_authority"),
        )
        _validate_installation_observation(record, candidate)
        return record


@dataclass(frozen=True)
class CapabilityProbeRequest:
    schema_version: str
    installation_observation_digest: str
    candidate_id: str
    candidate_digest: str
    runtime_requirement_profile_id: str
    runtime_requirement_digest: str
    provider_adapter_id: str
    tool_surface_id: str
    model_name: str
    model_digest: str
    runtime_settings_profile_id: str
    runtime_settings_digest: str
    requested_context_tokens: int
    tool_fixture_id: str
    tool_fixture_path: str
    tool_fixture_result_digest: str
    context_fixture_id: str
    context_canary_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True)
class CapabilityProbeEvidence:
    schema_version: str
    request_digest: str
    tool_fixture_id: str
    tool_call_name: str
    tool_call_path: str
    tool_result_digest: str
    tool_result_consumed: bool
    tool_evidence_digest: str
    context_fixture_id: str
    context_target_tokens: int
    context_prompt_tokens: int
    context_canary_digest: str
    context_canary_observed: bool
    context_evidence_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderCapabilityQualification:
    """Controlled capability evidence for one exact observed provider configuration."""

    schema_version: str
    qualification_version: int
    installation_observation_digest: str
    candidate_id: str
    candidate_version: int
    candidate_digest: str
    runtime_requirement_profile_id: str
    runtime_requirement_digest: str
    provider_adapter_id: str
    tool_surface_id: str
    provider_kind: str
    model_name: str
    model_digest: str
    model_metadata_digest: str
    runtime_settings_profile_id: str
    runtime_settings_digest: str
    requested_context_tokens: int
    effective_context_tokens: int
    tool_fixture_id: str
    tool_evidence_digest: str
    context_fixture_id: str
    context_evidence_digest: str
    execution_authority: str
    capability_qualified: bool
    execution_ready: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        return canonical_digest({
            "schema_version": CAPABILITY_QUALIFICATION_IDENTITY_SCHEMA,
            "qualification": self.to_dict(),
        })

    @classmethod
    def from_mapping(
        cls,
        value: Any,
        *,
        settings: RuntimeSettingsProfile = CODING_WORKER_SETTINGS_V1,
    ) -> "ProviderCapabilityQualification":
        if not isinstance(value, Mapping) or set(value) != set(cls.__dataclass_fields__):
            raise LabValidationError(
                "PROVIDER_CAPABILITY_FIELDS_INVALID",
                "provider capability qualification fields are missing or unknown",
            )
        record = cls(
            _exact(value["schema_version"], CAPABILITY_QUALIFICATION_SCHEMA, "schema_version"),
            _positive(value["qualification_version"], "qualification version"),
            _digest(value["installation_observation_digest"], "installation observation digest"),
            _text(value["candidate_id"], "candidate id"),
            _positive(value["candidate_version"], "candidate version"),
            _digest(value["candidate_digest"], "candidate digest"),
            _text(value["runtime_requirement_profile_id"], "runtime requirement profile"),
            _digest(value["runtime_requirement_digest"], "runtime requirement digest"),
            _exact(value["provider_adapter_id"], PROVIDER_ADAPTER_ID, "provider adapter"),
            _text(value["tool_surface_id"], "tool surface"),
            _text(value["provider_kind"], "provider kind"),
            _text(value["model_name"], "model name"),
            _digest(value["model_digest"], "model digest"),
            _digest(value["model_metadata_digest"], "model metadata digest"),
            _text(value["runtime_settings_profile_id"], "runtime settings profile"),
            _digest(value["runtime_settings_digest"], "runtime settings digest"),
            _positive(value["requested_context_tokens"], "requested context tokens"),
            _positive(value["effective_context_tokens"], "effective context tokens"),
            _exact(value["tool_fixture_id"], TOOL_CAPABILITY_FIXTURE_ID, "tool fixture"),
            _digest(value["tool_evidence_digest"], "tool evidence digest"),
            _exact(value["context_fixture_id"], CONTEXT_CAPABILITY_FIXTURE_ID, "context fixture"),
            _digest(value["context_evidence_digest"], "context evidence digest"),
            _exact(value["execution_authority"], "DISABLED", "execution_authority"),
            _true(value["capability_qualified"], "capability_qualified"),
            _false(value["execution_ready"], "execution_ready"),
        )
        _validate_capability_qualification(record, settings=settings)
        return record


CapabilityProbeRunner = Callable[[CapabilityProbeRequest], CapabilityProbeEvidence]


'''
replace_once(
    pq,
    "@dataclass(frozen=True)\nclass HostProviderQualification:",
    new_types + "@dataclass(frozen=True)\nclass HostProviderQualification:",
)

new_functions = r'''
def inspect_provider_installation(
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
) -> ProviderInstallationObservation:
    """Observe exact installation/model metadata without claiming runtime capability."""
    if candidate != protected_provider_candidate(candidate.candidate_id):
        raise LabValidationError(
            "PROVIDER_CANDIDATE_INVALID",
            "provider candidate differs from the protected declaration",
        )
    model = _text(model, "model name")
    repository_root = _real_directory(repository_root, "repository root")
    if _portable_execution_authority(repository_root) != "DISABLED":
        raise LabValidationError(
            "PROVIDER_QUALIFICATION_AUTHORITY_INVALID",
            "provider installation observation requires execution authority to remain disabled",
        )
    endpoint = _loopback_endpoint(base_url)
    distribution_reader = distribution_reader or inspect_distribution
    harness_version, harness_tree_digest = distribution_reader(candidate.harness_distribution)
    harness_version = _text(harness_version, "harness version")
    harness_tree_digest = _digest(harness_tree_digest, "harness tree digest")

    resolver = executable_resolver or shutil.which
    resolved = resolver(executable_name)
    if not resolved:
        raise LabValidationError("PROVIDER_RUNTIME_UNAVAILABLE", "provider executable is unavailable")
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

    python_path = _real_file(Path(sys.executable), "Python executable")
    record = ProviderInstallationObservation(
        schema_version=INSTALLATION_OBSERVATION_SCHEMA,
        candidate_id=candidate.candidate_id,
        candidate_version=candidate.candidate_version,
        candidate_digest=candidate.digest(),
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
    )
    _validate_installation_observation(record, candidate)
    return record


def qualify_provider_capabilities(
    observation: ProviderInstallationObservation,
    *,
    probe_runner: CapabilityProbeRunner | None,
    settings: RuntimeSettingsProfile = CODING_WORKER_SETTINGS_V1,
) -> ProviderCapabilityQualification:
    """Run one explicitly injected controlled probe and seal independently checked evidence.

    There is intentionally no default probe runner. Calling this function cannot launch
    a provider/model unless a separately authorized caller injects a runner that does so.
    """
    if not isinstance(observation, ProviderInstallationObservation):
        raise LabValidationError(
            "PROVIDER_INSTALLATION_INVALID",
            "controlled qualification requires an installation observation",
        )
    observation = ProviderInstallationObservation.from_mapping(observation.to_dict())
    validate_runtime_settings(settings)
    if probe_runner is None or not callable(probe_runner):
        raise LabValidationError(
            "PROVIDER_CAPABILITY_PROBE_REQUIRED",
            "controlled provider capability qualification requires an explicit probe runner",
        )
    candidate = protected_provider_candidate(observation.candidate_id)
    missing = set(candidate.required_model_capabilities) - set(observation.model_capabilities)
    if missing or observation.model_context_tokens < settings.requested_context_tokens:
        raise LabValidationError(
            "PROVIDER_CAPABILITY_PRECONDITION_INVALID",
            "installation metadata does not satisfy controlled qualification preconditions",
        )
    requirement = selected_runtime_requirement_v3()
    request = CapabilityProbeRequest(
        schema_version=CAPABILITY_PROBE_REQUEST_SCHEMA,
        installation_observation_digest=observation.digest(),
        candidate_id=candidate.candidate_id,
        candidate_digest=candidate.digest(),
        runtime_requirement_profile_id=requirement.profile_id,
        runtime_requirement_digest=requirement.digest(),
        provider_adapter_id=PROVIDER_ADAPTER_ID,
        tool_surface_id=candidate.tool_surface_id,
        model_name=observation.model_name,
        model_digest=observation.model_digest,
        runtime_settings_profile_id=settings.profile_id,
        runtime_settings_digest=settings.digest(),
        requested_context_tokens=settings.requested_context_tokens,
        tool_fixture_id=TOOL_CAPABILITY_FIXTURE_ID,
        tool_fixture_path=TOOL_CAPABILITY_PATH,
        tool_fixture_result_digest=TOOL_CAPABILITY_RESULT_DIGEST,
        context_fixture_id=CONTEXT_CAPABILITY_FIXTURE_ID,
        context_canary_digest=CONTEXT_CAPABILITY_CANARY_DIGEST,
    )
    evidence = probe_runner(request)
    _validate_capability_probe_evidence(evidence, request)
    record = ProviderCapabilityQualification(
        schema_version=CAPABILITY_QUALIFICATION_SCHEMA,
        qualification_version=1,
        installation_observation_digest=observation.digest(),
        candidate_id=candidate.candidate_id,
        candidate_version=candidate.candidate_version,
        candidate_digest=candidate.digest(),
        runtime_requirement_profile_id=requirement.profile_id,
        runtime_requirement_digest=requirement.digest(),
        provider_adapter_id=PROVIDER_ADAPTER_ID,
        tool_surface_id=candidate.tool_surface_id,
        provider_kind=candidate.provider_kind,
        model_name=observation.model_name,
        model_digest=observation.model_digest,
        model_metadata_digest=observation.model_metadata_digest,
        runtime_settings_profile_id=settings.profile_id,
        runtime_settings_digest=settings.digest(),
        requested_context_tokens=settings.requested_context_tokens,
        effective_context_tokens=evidence.context_prompt_tokens,
        tool_fixture_id=TOOL_CAPABILITY_FIXTURE_ID,
        tool_evidence_digest=evidence.tool_evidence_digest,
        context_fixture_id=CONTEXT_CAPABILITY_FIXTURE_ID,
        context_evidence_digest=evidence.context_evidence_digest,
        execution_authority="DISABLED",
        capability_qualified=True,
        execution_ready=False,
    )
    _validate_capability_qualification(record, settings=settings)
    return record


def _validate_installation_observation(
    record: ProviderInstallationObservation,
    candidate: ProviderCandidate,
) -> None:
    expected = (
        record.candidate_id == candidate.candidate_id,
        record.candidate_version == candidate.candidate_version,
        record.candidate_digest == candidate.digest(),
        record.tool_surface_id == candidate.tool_surface_id,
        record.harness_distribution == candidate.harness_distribution,
        record.provider_kind == candidate.provider_kind,
        record.execution_authority == "DISABLED",
    )
    if not all(expected):
        raise LabValidationError(
            "PROVIDER_INSTALLATION_INVALID",
            "provider installation observation differs from the protected candidate",
        )


def _validate_capability_probe_evidence(
    evidence: CapabilityProbeEvidence,
    request: CapabilityProbeRequest,
) -> None:
    if not isinstance(evidence, CapabilityProbeEvidence):
        raise LabValidationError(
            "PROVIDER_CAPABILITY_EVIDENCE_INVALID",
            "controlled capability probe returned invalid evidence",
        )
    for value, name in (
        (evidence.request_digest, "probe request digest"),
        (evidence.tool_result_digest, "tool result digest"),
        (evidence.tool_evidence_digest, "tool evidence digest"),
        (evidence.context_canary_digest, "context canary digest"),
        (evidence.context_evidence_digest, "context evidence digest"),
    ):
        _digest(value, name)
    if (
        evidence.schema_version != CAPABILITY_PROBE_EVIDENCE_SCHEMA
        or evidence.request_digest != request.digest()
        or evidence.tool_fixture_id != TOOL_CAPABILITY_FIXTURE_ID
        or evidence.tool_call_name != "read_file"
        or evidence.tool_call_path != TOOL_CAPABILITY_PATH
        or evidence.tool_result_digest != TOOL_CAPABILITY_RESULT_DIGEST
        or evidence.tool_result_consumed is not True
        or evidence.context_fixture_id != CONTEXT_CAPABILITY_FIXTURE_ID
        or evidence.context_target_tokens != request.requested_context_tokens
        or isinstance(evidence.context_prompt_tokens, bool)
        or not isinstance(evidence.context_prompt_tokens, int)
        or evidence.context_prompt_tokens < request.requested_context_tokens
        or evidence.context_canary_digest != CONTEXT_CAPABILITY_CANARY_DIGEST
        or evidence.context_canary_observed is not True
    ):
        raise LabValidationError(
            "PROVIDER_CAPABILITY_EVIDENCE_INVALID",
            "controlled capability evidence does not prove the sealed tool/context contract",
        )


def _validate_capability_qualification(
    record: ProviderCapabilityQualification,
    *,
    settings: RuntimeSettingsProfile = CODING_WORKER_SETTINGS_V1,
) -> None:
    validate_runtime_settings(settings)
    candidate = protected_provider_candidate(record.candidate_id)
    requirement = selected_runtime_requirement_v3()
    if (
        record.qualification_version != 1
        or record.candidate_version != candidate.candidate_version
        or record.candidate_digest != candidate.digest()
        or record.runtime_requirement_profile_id != requirement.profile_id
        or record.runtime_requirement_digest != requirement.digest()
        or record.provider_adapter_id != PROVIDER_ADAPTER_ID
        or record.tool_surface_id != candidate.tool_surface_id
        or record.provider_kind != candidate.provider_kind
        or record.runtime_settings_profile_id != settings.profile_id
        or record.runtime_settings_digest != settings.digest()
        or record.requested_context_tokens != settings.requested_context_tokens
        or record.effective_context_tokens < settings.requested_context_tokens
        or record.tool_fixture_id != TOOL_CAPABILITY_FIXTURE_ID
        or record.context_fixture_id != CONTEXT_CAPABILITY_FIXTURE_ID
        or record.execution_authority != "DISABLED"
        or record.capability_qualified is not True
        or record.execution_ready is not False
    ):
        raise LabValidationError(
            "PROVIDER_CAPABILITY_QUALIFICATION_INVALID",
            "provider capability qualification differs from the protected current runtime contract",
        )


'''
replace_once(pq, "def inspect_host_provider(\n", new_functions + "def inspect_host_provider(\n")


# ---------------------------------------------------------------------------
# Worker Lab Provider Binding: only controlled capability qualification may bind.
# ---------------------------------------------------------------------------
pb = "components/worker-lab/worker_lab/provider_binding.py"
replace_once(
    pb,
    "from .provider_qualification import HostProviderQualification, protected_provider_candidate\n",
    "from .provider_qualification import (\n"
    "    PROVIDER_ADAPTER_ID,\n"
    "    ProviderCapabilityQualification,\n"
    "    protected_provider_candidate,\n"
    ")\n"
    "from .runtime_settings import (\n"
    "    CODING_WORKER_SETTINGS_V1,\n"
    "    RUNTIME_SETTINGS_SCHEMA,\n"
    "    RuntimeSettingsProfile,\n"
    "    validate_runtime_settings,\n"
    ")\n",
)
text = read(pb)
start = text.index('RUNTIME_SETTINGS_SCHEMA = "worker-lab-runtime-settings:v1"\n')
end = text.index('@dataclass(frozen=True)\nclass ProviderBinding:', start)
replacement = '_BINDING_ID_RE = re.compile(r"^[A-Z][A-Z0-9-]{7,95}$")\n_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")\n\n\n'
write(pb, text[:start] + replacement + text[end:])

new_create = r'''def create_provider_binding(
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
        or qualification.execution_authority != "DISABLED"
        or qualification.capability_qualified is not True
        or qualification.execution_ready is not False
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


'''
replace_between(pb, "def create_provider_binding(\n", "def validate_current_provider_binding(\n", new_create)

new_validate_qualification = r'''def validate_binding_qualification(
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


'''
replace_between(pb, "def validate_binding_qualification(\n", "class ProviderBindingStore:", new_validate_qualification)
replace_between(
    pb,
    "def _validate_settings(settings: RuntimeSettingsProfile) -> None:\n",
    "def _binding_id(value: Any) -> str:\n",
    "def _validate_settings(settings: RuntimeSettingsProfile) -> None:\n    validate_runtime_settings(settings)\n\n\n",
)


# ---------------------------------------------------------------------------
# Shared deterministic test fixtures for the new qualification identity.
# ---------------------------------------------------------------------------
write(
    "components/worker-lab/tests/provider_capability_fixture.py",
    '''from __future__ import annotations

import sys
from pathlib import Path

from worker_lab.provider_qualification import (
    CAPABILITY_QUALIFICATION_SCHEMA,
    INSTALLATION_OBSERVATION_SCHEMA,
    CONTEXT_CAPABILITY_FIXTURE_ID,
    PROVIDER_ADAPTER_ID,
    TOOL_CAPABILITY_FIXTURE_ID,
    PYDANTIC_AI_OLLAMA_V1,
    ProviderCapabilityQualification,
    ProviderInstallationObservation,
)
from worker_lab.runtime_selection import selected_runtime_requirement_v3
from worker_lab.runtime_settings import CODING_WORKER_SETTINGS_V1


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
DIGEST_D = "sha256:" + "d" * 64
DIGEST_E = "sha256:" + "e" * 64


def installation_observation(
    *,
    model_name: str = "qwen2.5-coder:7b",
    model_digest: str = DIGEST_B,
    model_metadata_digest: str = DIGEST_C,
    model_context_tokens: int = 65_536,
    model_capabilities: tuple[str, ...] = ("completion", "tools"),
    harness_tree_digest: str = DIGEST_D,
) -> ProviderInstallationObservation:
    candidate = PYDANTIC_AI_OLLAMA_V1
    executable = str(Path(sys.executable).resolve())
    return ProviderInstallationObservation.from_mapping({
        "schema_version": INSTALLATION_OBSERVATION_SCHEMA,
        "candidate_id": candidate.candidate_id,
        "candidate_version": candidate.candidate_version,
        "candidate_digest": candidate.digest(),
        "tool_surface_id": candidate.tool_surface_id,
        "host_platform": "fixture-os",
        "host_architecture": "fixture-arch",
        "python_version": "3.12.0",
        "python_executable": executable,
        "python_sha256": DIGEST_A,
        "harness_distribution": candidate.harness_distribution,
        "harness_version": "1.2.3",
        "harness_tree_digest": harness_tree_digest,
        "provider_kind": candidate.provider_kind,
        "provider_endpoint": "http://127.0.0.1:11434",
        "provider_executable": executable,
        "provider_executable_sha256": DIGEST_A,
        "provider_cli_version": "fixture-provider",
        "provider_api_version": "fixture-api",
        "model_name": model_name,
        "model_digest": model_digest,
        "model_metadata_digest": model_metadata_digest,
        "model_context_tokens": model_context_tokens,
        "model_capabilities": list(model_capabilities),
        "execution_authority": "DISABLED",
    })


def capability_qualification(
    *,
    model_name: str = "qwen2.5-coder:7b",
    model_digest: str = DIGEST_B,
    model_metadata_digest: str = DIGEST_C,
    installation_observation_digest: str | None = None,
    effective_context_tokens: int = 65_536,
    tool_evidence_digest: str = DIGEST_D,
    context_evidence_digest: str = DIGEST_E,
) -> ProviderCapabilityQualification:
    candidate = PYDANTIC_AI_OLLAMA_V1
    requirement = selected_runtime_requirement_v3()
    settings = CODING_WORKER_SETTINGS_V1
    observation_digest = installation_observation_digest or installation_observation(
        model_name=model_name,
        model_digest=model_digest,
        model_metadata_digest=model_metadata_digest,
    ).digest()
    return ProviderCapabilityQualification.from_mapping({
        "schema_version": CAPABILITY_QUALIFICATION_SCHEMA,
        "qualification_version": 1,
        "installation_observation_digest": observation_digest,
        "candidate_id": candidate.candidate_id,
        "candidate_version": candidate.candidate_version,
        "candidate_digest": candidate.digest(),
        "runtime_requirement_profile_id": requirement.profile_id,
        "runtime_requirement_digest": requirement.digest(),
        "provider_adapter_id": PROVIDER_ADAPTER_ID,
        "tool_surface_id": candidate.tool_surface_id,
        "provider_kind": candidate.provider_kind,
        "model_name": model_name,
        "model_digest": model_digest,
        "model_metadata_digest": model_metadata_digest,
        "runtime_settings_profile_id": settings.profile_id,
        "runtime_settings_digest": settings.digest(),
        "requested_context_tokens": settings.requested_context_tokens,
        "effective_context_tokens": effective_context_tokens,
        "tool_fixture_id": TOOL_CAPABILITY_FIXTURE_ID,
        "tool_evidence_digest": tool_evidence_digest,
        "context_fixture_id": CONTEXT_CAPABILITY_FIXTURE_ID,
        "context_evidence_digest": context_evidence_digest,
        "execution_authority": "DISABLED",
        "capability_qualified": True,
        "execution_ready": False,
    })
''',
)

# Replace the repeated legacy qualification fixture bodies while keeping test call sites stable.
tpb = "components/worker-lab/tests/test_provider_binding.py"
replace_between(
    tpb,
    "def qualification(*, model_digest: str = DIGEST_A, harness_tree_digest: str = DIGEST_C):\n",
    "\n\ndef test_binding_seals_v3_requirement_exact_qualification_and_settings():",
    '''def qualification(*, model_digest: str = DIGEST_A, harness_tree_digest: str = DIGEST_C):
    from tests.provider_capability_fixture import capability_qualification

    return capability_qualification(
        model_digest=model_digest,
        installation_observation_digest=harness_tree_digest,
    )
''',
)
text = read(tpb)
text += '''

def test_metadata_only_installation_observation_cannot_create_binding():
    from tests.provider_capability_fixture import installation_observation

    with pytest.raises(LabValidationError) as error:
        create_provider_binding("BINDING-0002", installation_observation())
    assert error.value.code == "PROVIDER_BINDING_QUALIFICATION_INVALID"
'''
write(tpb, text)

for path, next_anchor, model_name in (
    ("components/worker-lab/tests/test_integration_v3.py", "def invocation(", "qwen2.5-coder:7b"),
    ("components/worker-lab/tests/test_dispatch_client.py", "def packet(", "fixture-model"),
):
    replacement = f'''def qualification():
    from tests.provider_capability_fixture import capability_qualification

    return capability_qualification(model_name="{model_name}")


'''
    replace_between(path, "def qualification():\n", next_anchor, replacement)


# Add current observation/controlled-probe tests while retaining historical V1 tests.
tpq = "components/worker-lab/tests/test_provider_qualification.py"
replace_once(
    tpq,
    "from worker_lab.runtime_selection import CODING_WORKER_V1\n",
    "from worker_lab.runtime_selection import CODING_WORKER_V1\n"
    "from tests.provider_capability_fixture import installation_observation\n"
    "from worker_lab.provider_qualification import (\n"
    "    CAPABILITY_PROBE_EVIDENCE_SCHEMA,\n"
    "    CONTEXT_CAPABILITY_CANARY_DIGEST,\n"
    "    CONTEXT_CAPABILITY_FIXTURE_ID,\n"
    "    TOOL_CAPABILITY_FIXTURE_ID,\n"
    "    TOOL_CAPABILITY_PATH,\n"
    "    TOOL_CAPABILITY_RESULT_DIGEST,\n"
    "    CapabilityProbeEvidence,\n"
    "    ProviderCapabilityQualification,\n"
    "    inspect_provider_installation,\n"
    "    qualify_provider_capabilities,\n"
    ")\n",
)
text = read(tpq)
text += r'''


def _passing_probe(request, *, prompt_tokens=None):
    return CapabilityProbeEvidence(
        schema_version=CAPABILITY_PROBE_EVIDENCE_SCHEMA,
        request_digest=request.digest(),
        tool_fixture_id=TOOL_CAPABILITY_FIXTURE_ID,
        tool_call_name="read_file",
        tool_call_path=TOOL_CAPABILITY_PATH,
        tool_result_digest=TOOL_CAPABILITY_RESULT_DIGEST,
        tool_result_consumed=True,
        tool_evidence_digest=DIGEST_A,
        context_fixture_id=CONTEXT_CAPABILITY_FIXTURE_ID,
        context_target_tokens=request.requested_context_tokens,
        context_prompt_tokens=prompt_tokens or request.requested_context_tokens,
        context_canary_digest=CONTEXT_CAPABILITY_CANARY_DIGEST,
        context_canary_observed=True,
        context_evidence_digest=DIGEST_B,
    )


def test_installation_observation_records_metadata_without_claiming_capability(tmp_path):
    root = _repository(tmp_path)
    executable = _executable(tmp_path)
    calls, http_json = _metadata_reader(context=8_192, capabilities=("completion",))
    observation = inspect_provider_installation(
        model="qwen2.5-coder:7b",
        repository_root=root,
        executable_resolver=lambda _: str(executable),
        version_reader=lambda _: "ollama version 0.33.3",
        distribution_reader=lambda _: ("2.40.0", DIGEST_A),
        http_json=http_json,
    )
    assert observation.model_context_tokens == 8_192
    assert observation.model_capabilities == ("completion",)
    assert not hasattr(observation, "capability_qualified")
    assert not hasattr(observation, "provider_runtime_qualified")
    assert all(not url.endswith("/api/chat") for _, url, _, _ in calls)


def test_controlled_capability_qualification_requires_explicit_probe_runner():
    with pytest.raises(LabValidationError) as error:
        qualify_provider_capabilities(installation_observation(), probe_runner=None)
    assert error.value.code == "PROVIDER_CAPABILITY_PROBE_REQUIRED"


def test_controlled_probe_seals_tool_and_context_evidence():
    observed = installation_observation()
    requests = []

    def runner(request):
        requests.append(request)
        return _passing_probe(request)

    qualified = qualify_provider_capabilities(observed, probe_runner=runner)
    assert len(requests) == 1
    assert qualified.installation_observation_digest == observed.digest()
    assert qualified.capability_qualified is True
    assert qualified.execution_ready is False
    assert qualified.requested_context_tokens == 32_768
    assert qualified.effective_context_tokens == 32_768
    assert ProviderCapabilityQualification.from_mapping(qualified.to_dict()) == qualified


def test_metadata_labels_are_preconditions_not_capability_proof():
    called = False

    def runner(request):
        nonlocal called
        called = True
        return _passing_probe(request)

    with pytest.raises(LabValidationError) as error:
        qualify_provider_capabilities(
            installation_observation(model_capabilities=("completion",)),
            probe_runner=runner,
        )
    assert error.value.code == "PROVIDER_CAPABILITY_PRECONDITION_INVALID"
    assert called is False


def test_controlled_probe_rejects_unproven_context_or_tool_behavior():
    observed = installation_observation()

    def short_context(request):
        return _passing_probe(request, prompt_tokens=request.requested_context_tokens - 1)

    with pytest.raises(LabValidationError) as error:
        qualify_provider_capabilities(observed, probe_runner=short_context)
    assert error.value.code == "PROVIDER_CAPABILITY_EVIDENCE_INVALID"

    def wrong_tool(request):
        evidence = _passing_probe(request)
        return CapabilityProbeEvidence(**{**evidence.to_dict(), "tool_call_name": "run_shell"})

    with pytest.raises(LabValidationError) as error:
        qualify_provider_capabilities(observed, probe_runner=wrong_tool)
    assert error.value.code == "PROVIDER_CAPABILITY_EVIDENCE_INVALID"
'''
write(tpq, text)


# ---------------------------------------------------------------------------
# Framework: pass exact validated settings through the bound executor seam.
# ---------------------------------------------------------------------------
da = "components/autonomous-worker-framework/tools/dispatch_adapter.py"
replace_once(
    da,
    "ProviderExecutor = Callable[[WorkerRequest], WorkerExecution]\n",
    "ProviderExecutor = Callable[[WorkerRequest, Mapping[str, Any]], WorkerExecution]\n",
)
replace_once(
    da,
    "            execution = provider_executor.execute(request)\n",
    "            execution = provider_executor.execute(request, parsed.runtime_settings)\n",
)

tda = "components/autonomous-worker-framework/tests/test_dispatch_adapter.py"
replace_once(
    tda,
    "    def execute(worker_request):\n        seen.append(worker_request)\n",
    "    def execute(worker_request, runtime_settings):\n        assert runtime_settings[\"request_limit\"] == 12\n        assert runtime_settings[\"requested_context_tokens\"] == 32768\n        seen.append(worker_request)\n",
)
replace_once(tda, "    def fake(_):\n", "    def fake(_, __):\n")
replace_once(tda, "    def fake(_):\n", "    def fake(_, __):\n")
replace_once(
    tda,
    "    def failed(worker_request):\n",
    "    def failed(worker_request, runtime_settings):\n        assert runtime_settings[\"tool_calls_limit\"] == 24\n",
)


# ---------------------------------------------------------------------------
# Pydantic/Ollama adapter: consume sealed settings; context is qualification-
# checked rather than pretending OpenAI-compatible Ollama can set num_ctx/request.
# ---------------------------------------------------------------------------
pow_path = "components/autonomous-worker-framework/tools/pydantic_ollama_worker.py"
replace_once(
    pow_path,
    'PROVIDER_KIND = "ollama"\n',
    'PROVIDER_KIND = "ollama"\nRUNTIME_SETTINGS_SCHEMA = "worker-lab-runtime-settings:v1"\n',
)
replace_once(
    pow_path,
    "    qualification_digest: str\n    candidate_id: str\n",
    "    qualification_digest: str\n"
    "    installation_observation_digest: str\n"
    "    runtime_settings_profile_id: str\n"
    "    runtime_settings_digest: str\n"
    "    qualified_context_tokens: int\n"
    "    candidate_id: str\n",
)
replace_once(
    pow_path,
    "    def to_dict(self) -> dict[str, str]:\n        return asdict(self)\n",
    "    def to_dict(self) -> dict[str, Any]:\n        return asdict(self)\n",
)
settings_type = r'''

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
'''
replace_once(
    pow_path,
    "\n\nclass BoundedFileTools:\n",
    settings_type + "\n\nclass BoundedFileTools:\n",
)
replace_once(
    pow_path,
    "AgentRunner = Callable[[WorkerRequest, QualifiedRuntimeBinding, BoundedFileTools], str]\n",
    "AgentRunner = Callable[[WorkerRequest, QualifiedRuntimeBinding, SealedRuntimeSettings, BoundedFileTools], str]\n",
)
replace_once(
    pow_path,
    "def execute_pydantic_ollama(\n    request: WorkerRequest,\n    binding: QualifiedRuntimeBinding,\n    *,\n",
    "def execute_pydantic_ollama(\n"
    "    request: WorkerRequest,\n"
    "    binding: QualifiedRuntimeBinding,\n"
    "    runtime_settings: Mapping[str, Any] | SealedRuntimeSettings,\n"
    "    *,\n",
)
# Mapping is needed at runtime; update typing import.
replace_once(
    pow_path,
    "from typing import Any, Callable\n",
    "from typing import Any, Callable, Mapping\n",
)
replace_once(
    pow_path,
    "    _validate_request(request)\n    _validate_binding(binding)\n",
    "    _validate_request(request)\n"
    "    settings = (\n"
    "        runtime_settings\n"
    "        if isinstance(runtime_settings, SealedRuntimeSettings)\n"
    "        else SealedRuntimeSettings.from_mapping(dict(runtime_settings))\n"
    "    )\n"
    "    _validate_binding(binding, settings)\n",
)
replace_once(
    pow_path,
    "    output = (runner or _run_pydantic_agent)(request, binding, tools)\n",
    "    output = (runner or _run_pydantic_agent)(request, binding, settings, tools)\n",
)
replace_once(
    pow_path,
    "def _run_pydantic_agent(\n    request: WorkerRequest,\n    binding: QualifiedRuntimeBinding,\n    tools: BoundedFileTools,\n",
    "def _run_pydantic_agent(\n"
    "    request: WorkerRequest,\n"
    "    binding: QualifiedRuntimeBinding,\n"
    "    settings: SealedRuntimeSettings,\n"
    "    tools: BoundedFileTools,\n",
)
replace_once(
    pow_path,
    '        retries={"tools": 2, "output": 1},\n        tool_timeout=30,\n        max_concurrency=1,\n',
    '        retries={"tools": settings.tool_retries, "output": settings.output_retries},\n'
    '        tool_timeout=settings.tool_timeout_seconds,\n'
    '        max_concurrency=settings.max_concurrency,\n',
)
replace_once(
    pow_path,
    "            usage_limits=UsageLimits(request_limit=12, tool_calls_limit=24),\n",
    "            usage_limits=UsageLimits(\n"
    "                request_limit=settings.request_limit,\n"
    "                tool_calls_limit=settings.tool_calls_limit,\n"
    "            ),\n",
)
replace_once(
    pow_path,
    "def _validate_binding(binding: QualifiedRuntimeBinding) -> None:\n",
    "def _validate_binding(\n    binding: QualifiedRuntimeBinding,\n    settings: SealedRuntimeSettings,\n) -> None:\n",
)
replace_once(
    pow_path,
    "        (binding.qualification_digest, \"qualification digest\"),\n",
    "        (binding.qualification_digest, \"qualification digest\"),\n"
    "        (binding.installation_observation_digest, \"installation observation digest\"),\n"
    "        (binding.runtime_settings_digest, \"runtime settings digest\"),\n",
)
replace_once(
    pow_path,
    "        or binding.provider_kind != PROVIDER_KIND\n    ):\n",
    "        or binding.provider_kind != PROVIDER_KIND\n"
    "        or binding.runtime_settings_profile_id != settings.profile_id\n"
    "        or binding.runtime_settings_digest != settings.digest()\n"
    "        or isinstance(binding.qualified_context_tokens, bool)\n"
    "        or not isinstance(binding.qualified_context_tokens, int)\n"
    "        or binding.qualified_context_tokens < settings.requested_context_tokens\n"
    "    ):\n",
)

# Framework adapter tests: make the sealed settings and qualification explicit.
tpow = "components/autonomous-worker-framework/tests/test_pydantic_ollama_worker.py"
replace_once(
    tpow,
    "import hashlib\nimport json\n",
    "import hashlib\nimport importlib.metadata\nimport json\nimport sys\nfrom types import ModuleType, SimpleNamespace\n",
)
replace_once(
    tpow,
    "    QualifiedRuntimeBinding,\n    execute_pydantic_ollama,\n",
    "    QualifiedRuntimeBinding,\n    SealedRuntimeSettings,\n    execute_pydantic_ollama,\n",
)
replace_once(
    tpow,
    "def _binding() -> QualifiedRuntimeBinding:\n    fixed = \"sha256:\" + (\"a\" * 64)\n    return QualifiedRuntimeBinding(\n        qualification_digest=fixed,\n",
    "def _settings() -> SealedRuntimeSettings:\n"
    "    return SealedRuntimeSettings.from_mapping({\n"
    "        \"schema_version\": \"worker-lab-runtime-settings:v1\",\n"
    "        \"profile_id\": \"bounded-code-worker-settings:v1\",\n"
    "        \"profile_version\": 1,\n"
    "        \"requested_context_tokens\": 32768,\n"
    "        \"request_limit\": 12,\n"
    "        \"tool_calls_limit\": 24,\n"
    "        \"tool_timeout_seconds\": 30,\n"
    "        \"tool_retries\": 2,\n"
    "        \"output_retries\": 1,\n"
    "        \"max_concurrency\": 1,\n"
    "    })\n\n\n"
    "def _binding() -> QualifiedRuntimeBinding:\n"
    "    fixed = \"sha256:\" + (\"a\" * 64)\n"
    "    settings = _settings()\n"
    "    return QualifiedRuntimeBinding(\n"
    "        qualification_digest=fixed,\n"
    "        installation_observation_digest=fixed,\n"
    "        runtime_settings_profile_id=settings.profile_id,\n"
    "        runtime_settings_digest=settings.digest(),\n"
    "        qualified_context_tokens=32768,\n",
)
replace_once(
    tpow,
    "    def runner(req, binding, tools):\n",
    "    def runner(req, binding, settings, tools):\n"
    "        assert settings == _settings()\n",
)
replace_once(
    tpow,
    "    execution = execute_pydantic_ollama(request, _binding(), runner=runner)\n",
    "    execution = execute_pydantic_ollama(request, _binding(), _settings(), runner=runner)\n",
)
replace_once(
    tpow,
    "        execute_pydantic_ollama(request, invalid, runner=lambda *_: \"never\")\n",
    "        execute_pydantic_ollama(request, invalid, _settings(), runner=lambda *_: \"never\")\n",
)
replace_once(
    tpow,
    "        execute_pydantic_ollama(request, invalid_surface, runner=lambda *_: \"never\")\n",
    "        execute_pydantic_ollama(request, invalid_surface, _settings(), runner=lambda *_: \"never\")\n",
)
text = read(tpow)
text += r'''


def test_adapter_rejects_runtime_settings_or_context_not_sealed_by_qualification(tmp_path: Path):
    root = tmp_path.resolve()
    (root / "target.py").write_text("VALUE = 1\n", encoding="utf-8")
    request = WorkerRequest(
        prompt="Change the file.",
        target_repo=root,
        framework_repo=tmp_path / "framework",
        sandbox="workspace-write",
        readable_paths=("target.py",),
        writable_paths=("target.py",),
    )
    settings = _settings()
    changed = SealedRuntimeSettings(**{**settings.to_dict(), "request_limit": 13})
    with pytest.raises(PydanticWorkerError) as mismatch:
        execute_pydantic_ollama(request, _binding(), changed, runner=lambda *_: "never")
    assert mismatch.value.code == "PYDANTIC_WORKER_BINDING_INVALID"

    too_small = QualifiedRuntimeBinding(**{**_binding().to_dict(), "qualified_context_tokens": 8192})
    with pytest.raises(PydanticWorkerError) as context:
        execute_pydantic_ollama(request, too_small, settings, runner=lambda *_: "never")
    assert context.value.code == "PYDANTIC_WORKER_BINDING_INVALID"


def test_production_pydantic_path_uses_exact_sealed_limits_without_real_provider(monkeypatch, tmp_path: Path):
    root = tmp_path.resolve()
    (root / "target.py").write_text("VALUE = 1\n", encoding="utf-8")
    request = WorkerRequest(
        prompt="Inspect the file and summarize.",
        target_repo=root,
        framework_repo=tmp_path / "framework",
        sandbox="workspace-write",
        readable_paths=("target.py",),
        writable_paths=("target.py",),
    )
    observed = {}

    class FakeUsageLimits:
        def __init__(self, *, request_limit, tool_calls_limit):
            observed["usage_limits"] = (request_limit, tool_calls_limit)

    class FakeAgent:
        def __init__(self, model, *, instructions, tools, retries, tool_timeout, max_concurrency):
            observed["agent"] = (retries, tool_timeout, max_concurrency, len(tools))

        def run_sync(self, prompt, *, usage_limits):
            observed["prompt"] = prompt
            return SimpleNamespace(output="fixture output")

    class FakeOllamaModel:
        def __init__(self, name, *, provider):
            observed["model"] = name

    class FakeOllamaProvider:
        def __init__(self, *, base_url):
            observed["base_url"] = base_url

    pydantic_ai = ModuleType("pydantic_ai")
    pydantic_ai.Agent = FakeAgent
    pydantic_ai.UsageLimits = FakeUsageLimits
    models = ModuleType("pydantic_ai.models")
    models_ollama = ModuleType("pydantic_ai.models.ollama")
    models_ollama.OllamaModel = FakeOllamaModel
    providers = ModuleType("pydantic_ai.providers")
    providers_ollama = ModuleType("pydantic_ai.providers.ollama")
    providers_ollama.OllamaProvider = FakeOllamaProvider
    monkeypatch.setitem(sys.modules, "pydantic_ai", pydantic_ai)
    monkeypatch.setitem(sys.modules, "pydantic_ai.models", models)
    monkeypatch.setitem(sys.modules, "pydantic_ai.models.ollama", models_ollama)
    monkeypatch.setitem(sys.modules, "pydantic_ai.providers", providers)
    monkeypatch.setitem(sys.modules, "pydantic_ai.providers.ollama", providers_ollama)
    monkeypatch.setattr(importlib.metadata, "version", lambda _: _binding().harness_version)

    execution = execute_pydantic_ollama(request, _binding(), _settings())
    assert execution.stdout == "fixture output"
    assert observed["usage_limits"] == (12, 24)
    assert observed["agent"] == ({"tools": 2, "output": 1}, 30, 1, 2)
    assert observed["base_url"] == "http://127.0.0.1:11434/v1"
'''
write(tpow, text)

print("Task 6 source/test candidate materialized")
