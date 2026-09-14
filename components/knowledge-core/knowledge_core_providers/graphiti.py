from __future__ import annotations

import asyncio
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
import logging
from typing import Any

from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.projection_adapter import (
    ProjectionAdapterDescriptor,
    ProjectionAdapterReceipt,
    ProjectionAdapterRequest,
    ProjectionLifecycleEdge,
    ProjectionLifecycleInventory,
    ProjectionProviderSourceBinding,
    ProjectionSearchHit,
    ProjectionSourceSegment,
)
from knowledge_core.domain.projection_evidence import ProjectionDisposition
from knowledge_core.domain.projection_validation import (
    ProjectionCheckOutcome,
    ProjectionValidationCheck,
    ProjectionValidationOutcome,
    ProjectionValidationReport,
    ProjectionValidationRequirement,
    ProjectionValidatorDescriptor,
)


_EXPECTED_GRAPHITI_VERSION = "0.30.2"
_ADAPTER_VERSION = "1"
_GOVERNED_DOCUMENT_POLICY = "governed-document-v1"
_INTEGRITY_WARNING_FRAGMENTS = (
    "Target entity not found in nodes for edge relation",
    "Source entity not found in nodes for edge relation",
)
_VALIDATION_RULESET = {
    "id": "kc-graphiti-governed-document-v2",
    "checks": [
        "attempt-contract",
        "source-binding-contract",
        "projection-integrity-warnings",
        "source-episodes-present",
        "governed-lifecycle-inventory",
        "namespace-search-isolation",
        "search-source-attribution",
    ],
}
_VALIDATION_RULESET_DIGEST = "sha256:" + sha256(
    json.dumps(_VALIDATION_RULESET, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
_VALIDATION_REQUIREMENT = ProjectionValidationRequirement(
    validator_identity="kc-graphiti-live-validator",
    validator_version="2",
    ruleset_id=_VALIDATION_RULESET["id"],
    ruleset_digest=_VALIDATION_RULESET_DIGEST,
)


def _canonical_digest(payload: dict[str, object]) -> str:
    return "sha256:" + sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def graphiti_partition_key(
    *,
    namespace_key: str,
    scope_key: str,
    projection_profile_id: str,
) -> str:
    namespace_key = namespace_key.strip()
    scope_key = scope_key.strip()
    projection_profile_id = projection_profile_id.strip()
    if not namespace_key or not scope_key or not projection_profile_id:
        raise KnowledgeInvariantError(
            "Graphiti partition identity requires namespace, scope, and projection profile"
        )
    digest = sha256(
        f"{namespace_key}\x00{scope_key}\x00{projection_profile_id}".encode("utf-8")
    ).hexdigest()
    return f"kc_{digest[:28]}"


@dataclass(frozen=True)
class GraphitiLocalConfig:
    falkor_host: str = "localhost"
    falkor_port: int = 6379
    falkor_username: str | None = None
    falkor_password: str | None = None
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_api_key: str = "ollama"
    llm_model: str = "graphiti-qwen35-9b-32k"
    llm_max_tokens: int = 12288
    temperature: float = 0.0
    embed_model: str = "nomic-embed-text:latest"
    embed_dim: int = 768
    structured_output_mode: str = "json_schema"
    reasoning_effort: str = "none"
    projection_policy: str = _GOVERNED_DOCUMENT_POLICY

    def behavioral_digest(self) -> str:
        # Secrets are intentionally absent. This digest binds behavior-bearing
        # provider/runtime choices, not credentials.
        return _canonical_digest(
            {
                "adapter_identity": "kc-graphiti-falkordb-ollama",
                "adapter_version": _ADAPTER_VERSION,
                "embed_dim": self.embed_dim,
                "embed_model": self.embed_model,
                "falkor_host": self.falkor_host,
                "falkor_port": self.falkor_port,
                "graphiti_core": _EXPECTED_GRAPHITI_VERSION,
                "llm_max_tokens": self.llm_max_tokens,
                "llm_model": self.llm_model,
                "ollama_base_url": self.ollama_base_url,
                "projection_policy": self.projection_policy,
                "reasoning_effort": self.reasoning_effort,
                "structured_output_mode": self.structured_output_mode,
                "temperature": self.temperature,
            }
        )


class _WarningCapture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(f"{record.name}: {record.getMessage()}")


def _require_graphiti_version() -> None:
    try:
        installed = version("graphiti-core")
    except PackageNotFoundError as exc:
        raise RuntimeError(
            "Graphiti integration is not installed; install Knowledge Core with the graphiti extra"
        ) from exc
    if installed != _EXPECTED_GRAPHITI_VERSION:
        raise RuntimeError(
            f"Graphiti live qualification requires graphiti-core {_EXPECTED_GRAPHITI_VERSION}; found {installed}"
        )


def _reasoning_disabled_client(llm_config, *, max_tokens: int, structured_output_mode: str):
    # Keep the tested local behavior inside the KC adapter instead of patching
    # upstream Graphiti. graphiti-core itself remains unmodified.
    import openai
    from graphiti_core.llm_client.config import DEFAULT_MAX_TOKENS, ModelSize
    from graphiti_core.llm_client.errors import EmptyResponseError, RateLimitError
    from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
    from graphiti_core.prompts.models import Message
    from pydantic import BaseModel

    class ReasoningDisabledOpenAIGenericClient(OpenAIGenericClient):
        async def _generate_response(
            self,
            messages: list[Message],
            response_model: type[BaseModel] | None = None,
            max_tokens: int = DEFAULT_MAX_TOKENS,
            model_size: ModelSize = ModelSize.medium,
        ) -> dict[str, Any]:
            openai_messages = []
            for message in messages:
                message.content = self._clean_input(message.content)
                if message.role == "user":
                    openai_messages.append({"role": "user", "content": message.content})
                elif message.role == "system":
                    openai_messages.append({"role": "system", "content": message.content})
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=openai_messages,
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                    response_format=self._build_response_format(response_model),
                    reasoning_effort="none",
                )
                result = response.choices[0].message.content or ""
                if not result:
                    raise EmptyResponseError("LLM returned an empty response")
                return json.loads(self._strip_code_fences(result))
            except openai.RateLimitError as exc:
                raise RateLimitError from exc

    return ReasoningDisabledOpenAIGenericClient(
        config=llm_config,
        max_tokens=max_tokens,
        structured_output_mode=structured_output_mode,
    )


def _normalize_governed_edge_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _governed_edge_identity(edge: Any) -> tuple[str, str, str, str, str]:
    return (
        str(edge.group_id),
        str(edge.source_node_uuid),
        str(edge.target_node_uuid),
        _normalize_governed_edge_text(str(edge.name)),
        _normalize_governed_edge_text(str(edge.fact)),
    )


async def _resolve_governed_document_edges(
    *,
    clients: Any,
    extracted_edges: list[Any],
    episode: Any,
    get_between_nodes: Any | None = None,
    embed_edges: Any | None = None,
) -> tuple[list[Any], list[Any], list[Any]]:
    """Resolve document edges without semantic dedupe or lifecycle decisions."""
    if get_between_nodes is None or embed_edges is None:
        from graphiti_core.edges import EntityEdge, create_entity_edge_embeddings

        get_between_nodes = get_between_nodes or EntityEdge.get_between_nodes
        embed_edges = embed_edges or create_entity_edge_embeddings

    deduplicated: dict[tuple[str, str, str, str, str], Any] = {}
    for edge in extracted_edges:
        # Model-extracted dates can describe source content, but they cannot retire
        # governed document facts or make a newly projected fact arrive retired.
        edge.invalid_at = None
        edge.expired_at = None
        edge.episodes = sorted(set(edge.episodes).union({str(episode.uuid)}))
        identity = _governed_edge_identity(edge)
        retained = deduplicated.get(identity)
        if retained is None:
            deduplicated[identity] = edge
        else:
            retained.episodes = sorted(set(retained.episodes).union(edge.episodes))

    candidate_edges = list(deduplicated.values())
    existing_by_edge = await asyncio.gather(
        *(
            get_between_nodes(
                clients.driver,
                edge.source_node_uuid,
                edge.target_node_uuid,
            )
            for edge in candidate_edges
        )
    )

    resolved_edges: list[Any] = []
    new_edges: list[Any] = []
    for edge, existing_edges in zip(candidate_edges, existing_by_edge, strict=True):
        identity = _governed_edge_identity(edge)
        exact_active_matches = sorted(
            (
                existing
                for existing in existing_edges
                if _governed_edge_identity(existing) == identity
                and existing.invalid_at is None
                and existing.expired_at is None
            ),
            key=lambda existing: str(existing.uuid),
        )
        if exact_active_matches:
            resolved = exact_active_matches[0]
            resolved.episodes = sorted(
                set(edge.episodes).union(
                    episode_id
                    for match in exact_active_matches
                    for episode_id in match.episodes
                )
            )
            resolved_edges.append(resolved)
        else:
            resolved_edges.append(edge)
            new_edges.append(edge)

    await embed_edges(clients.embedder, resolved_edges)
    # The ordinary Graphiti path returns model-selected invalidated edges in the
    # second position. Governed documents never authorize such mutations.
    return resolved_edges, [], new_edges


def _governed_document_graphiti_type(graphiti_type: type[Any]) -> type[Any]:
    class GovernedDocumentGraphiti(graphiti_type):
        async def _extract_and_resolve_edges(
            self,
            episode,
            extracted_nodes,
            previous_episodes,
            edge_type_map,
            group_id,
            edge_types,
            nodes,
            uuid_map,
            custom_extraction_instructions=None,
            clients=None,
        ):
            from graphiti_core.utils.bulk_utils import resolve_edge_pointers
            from graphiti_core.utils.maintenance.edge_operations import extract_edges

            clients = clients or self.clients
            episodes = episode if isinstance(episode, list) else [episode]
            extracted_edges = await extract_edges(
                clients,
                episode,
                extracted_nodes,
                previous_episodes,
                edge_type_map,
                group_id,
                edge_types,
                custom_extraction_instructions,
            )
            edges = resolve_edge_pointers(extracted_edges, uuid_map)
            return await _resolve_governed_document_edges(
                clients=clients,
                extracted_edges=edges,
                episode=episodes[0],
            )

    GovernedDocumentGraphiti.__name__ = "GovernedDocumentGraphiti"
    return GovernedDocumentGraphiti


async def _await_graphiti_driver_initialization(graphiti) -> None:
    task = getattr(graphiti.driver, "_init_task", None)
    if task is not None:
        await task
    else:
        await graphiti.build_indices_and_constraints()


class GraphitiProjectionAdapter:
    """Real Graphiti 0.30.2 / FalkorDB / Ollama adapter for governed SR-2 segments."""

    def __init__(self, config: GraphitiLocalConfig | None = None):
        self.config = config or GraphitiLocalConfig()
        if self.config.projection_policy != _GOVERNED_DOCUMENT_POLICY:
            raise KnowledgeInvariantError(
                "unsupported Graphiti projection policy: "
                f"{self.config.projection_policy!r}; expected {_GOVERNED_DOCUMENT_POLICY!r}"
            )
        if self.config.reasoning_effort != "none":
            raise KnowledgeInvariantError(
                "the qualified local Graphiti profile requires reasoning_effort='none'"
            )
        if self.config.structured_output_mode != "json_schema":
            raise KnowledgeInvariantError(
                "the qualified local Graphiti profile requires json_schema structured output"
            )

    @property
    def descriptor(self) -> ProjectionAdapterDescriptor:
        return ProjectionAdapterDescriptor(
            backend_identity="graphiti-falkordb",
            backend_version=_EXPECTED_GRAPHITI_VERSION,
            adapter_identity="kc-graphiti-falkordb-ollama",
            adapter_version=_ADAPTER_VERSION,
            config_digest=self.config.behavioral_digest(),
            validation_requirement=_VALIDATION_REQUIREMENT,
        )

    def partition_key(
        self,
        *,
        namespace_key: str,
        scope_key: str,
        projection_profile_id: str,
    ) -> str:
        return graphiti_partition_key(
            namespace_key=namespace_key,
            scope_key=scope_key,
            projection_profile_id=projection_profile_id,
        )

    def _build_graphiti(self, *, partition_key: str):
        _require_graphiti_version()
        from graphiti_core import Graphiti
        from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
        from graphiti_core.driver.falkordb_driver import FalkorDriver
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
        from graphiti_core.llm_client.config import LLMConfig

        Graphiti = _governed_document_graphiti_type(Graphiti)

        llm_config = LLMConfig(
            api_key=self.config.ollama_api_key,
            model=self.config.llm_model,
            small_model=self.config.llm_model,
            base_url=self.config.ollama_base_url,
            temperature=self.config.temperature,
            max_tokens=self.config.llm_max_tokens,
        )
        llm_client = _reasoning_disabled_client(
            llm_config,
            max_tokens=self.config.llm_max_tokens,
            structured_output_mode=self.config.structured_output_mode,
        )
        embedder = OpenAIEmbedder(
            config=OpenAIEmbedderConfig(
                api_key=self.config.ollama_api_key,
                base_url=self.config.ollama_base_url,
                embedding_model=self.config.embed_model,
                embedding_dim=self.config.embed_dim,
            )
        )
        reranker = OpenAIRerankerClient(config=llm_config, client=llm_client.client)
        driver = FalkorDriver(
            host=self.config.falkor_host,
            port=self.config.falkor_port,
            username=self.config.falkor_username,
            password=self.config.falkor_password,
            database=partition_key,
        )
        return Graphiti(
            graph_driver=driver,
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=reranker,
        )

    async def project(self, request: ProjectionAdapterRequest) -> ProjectionAdapterReceipt:
        from graphiti_core.nodes import EpisodeType

        if request.attempt.profile_id is None:
            raise KnowledgeInvariantError("Graphiti projection requires a projection profile identity")
        partition = self.partition_key(
            namespace_key=request.attempt.namespace_key,
            scope_key=request.attempt.scope_key,
            projection_profile_id=request.attempt.profile_id,
        )
        graphiti = self._build_graphiti(partition_key=partition)
        capture = _WarningCapture()
        graphiti_logger = logging.getLogger("graphiti_core")
        graphiti_logger.addHandler(capture)
        episode_count = 0
        node_count = 0
        edge_count = 0
        bindings: list[ProjectionProviderSourceBinding] = []
        try:
            await _await_graphiti_driver_initialization(graphiti)
            for segment in request.segments:
                # Graphiti 0.30.2 treats add_episode(uuid=...) as lookup/update of an
                # existing episode. Let Graphiti mint its provider ID, then persist
                # the returned ID as KC operational correlation evidence.
                result = await graphiti.add_episode(
                    name=f"kc:{segment.segment_key}",
                    episode_body=segment.body,
                    source=EpisodeType.text,
                    source_description="Knowledge Core governed SR-2 canonical segment",
                    reference_time=segment.reference_time,
                    group_id=partition,
                )
                provider_source_id = str(result.episode.uuid).strip()
                if not provider_source_id:
                    raise KnowledgeInvariantError("Graphiti returned an empty episode UUID")
                bindings.append(
                    ProjectionProviderSourceBinding(
                        resource_version_ref=segment.resource_version_ref,
                        source_revision_id=segment.source_revision_id,
                        segment_key=segment.segment_key,
                        source_slice_sha256=segment.source_slice_sha256,
                        provider_partition_key=partition,
                        provider_source_id=provider_source_id,
                    )
                )
                episode_count += 1
                node_count += len(result.nodes)
                edge_count += len(result.edges)
        finally:
            graphiti_logger.removeHandler(capture)
            await graphiti.close()

        warnings = tuple(capture.messages)
        integrity_warnings = tuple(
            warning
            for warning in warnings
            if any(fragment in warning for fragment in _INTEGRITY_WARNING_FRAGMENTS)
        )
        disposition = (
            ProjectionDisposition.INCOMPLETE
            if integrity_warnings
            else ProjectionDisposition.SUCCEEDED
        )
        return ProjectionAdapterReceipt(
            disposition=disposition,
            warnings=warnings,
            errors=(),
            episode_count=episode_count,
            node_count=node_count,
            edge_count=edge_count,
            source_bindings=tuple(bindings),
        )

    async def search(
        self,
        *,
        query: str,
        namespace_key: str,
        scope_key: str,
        projection_profile_id: str,
        limit: int,
    ) -> tuple[ProjectionSearchHit, ...]:
        partition = self.partition_key(
            namespace_key=namespace_key,
            scope_key=scope_key,
            projection_profile_id=projection_profile_id,
        )
        graphiti = self._build_graphiti(partition_key=partition)
        try:
            await _await_graphiti_driver_initialization(graphiti)
            results = await graphiti.search(
                query,
                group_ids=[partition],
                num_results=limit,
            )
            return tuple(
                ProjectionSearchHit(
                    provider_hit_id=edge.uuid,
                    partition_key=edge.group_id,
                    fact=edge.fact,
                    source_correlation_keys=tuple(edge.episodes or ()),
                    valid_at=edge.valid_at,
                    invalid_at=edge.invalid_at,
                )
                for edge in results
            )
        finally:
            await graphiti.close()

    async def existing_source_keys(
        self,
        *,
        source_keys: tuple[str, ...],
        namespace_key: str,
        scope_key: str,
        projection_profile_id: str,
    ) -> frozenset[str]:
        if not source_keys:
            return frozenset()
        from graphiti_core.nodes import EpisodicNode

        partition = self.partition_key(
            namespace_key=namespace_key,
            scope_key=scope_key,
            projection_profile_id=projection_profile_id,
        )
        graphiti = self._build_graphiti(partition_key=partition)
        try:
            await _await_graphiti_driver_initialization(graphiti)
            episodes = await EpisodicNode.get_by_uuids(graphiti.driver, list(source_keys))
            return frozenset(str(episode.uuid) for episode in episodes)
        finally:
            await graphiti.close()

    async def lifecycle_inventory(
        self,
        *,
        namespace_key: str,
        scope_key: str,
        projection_profile_id: str,
    ) -> ProjectionLifecycleInventory:
        from graphiti_core.edges import EntityEdge
        from graphiti_core.errors import GroupsEdgesNotFoundError

        partition = self.partition_key(
            namespace_key=namespace_key,
            scope_key=scope_key,
            projection_profile_id=projection_profile_id,
        )
        graphiti = self._build_graphiti(partition_key=partition)
        try:
            await _await_graphiti_driver_initialization(graphiti)
            try:
                edges = await EntityEdge.get_by_group_ids(
                    graphiti.driver,
                    [partition],
                )
            except GroupsEdgesNotFoundError:
                edges = []
            inventory_edges = tuple(
                sorted(
                    (
                        ProjectionLifecycleEdge(
                            provider_edge_id=str(edge.uuid),
                            partition_key=str(edge.group_id),
                            source_correlation_keys=tuple(
                                sorted(str(source_id) for source_id in (edge.episodes or ()))
                            ),
                            invalid_at=edge.invalid_at,
                            expired_at=edge.expired_at,
                        )
                        for edge in edges
                    ),
                    key=lambda edge: edge.provider_edge_id,
                )
            )
            return ProjectionLifecycleInventory(
                partition_key=partition,
                complete=True,
                edges=inventory_edges,
            )
        except Exception as exc:
            return ProjectionLifecycleInventory(
                partition_key=partition,
                complete=False,
                edges=(),
                error=f"{type(exc).__name__}: {exc}",
            )
        finally:
            await graphiti.close()


class GraphitiProjectionValidator:
    """Deterministic validator backed by live Graphiti/FalkorDB observations."""

    def __init__(
        self,
        *,
        adapter: GraphitiProjectionAdapter,
        segments: tuple[ProjectionSourceSegment, ...],
        source_bindings: tuple[ProjectionProviderSourceBinding, ...],
        namespace_key: str,
        scope_key: str,
        projection_profile_id: str,
        probe_query: str,
    ):
        self.adapter = adapter
        self.segments = segments
        self.source_bindings = source_bindings
        self.namespace_key = namespace_key.strip()
        self.scope_key = scope_key.strip()
        self.projection_profile_id = projection_profile_id.strip()
        self.probe_query = probe_query.strip()
        if (
            not self.namespace_key
            or not self.scope_key
            or not self.projection_profile_id
            or not self.probe_query
        ):
            raise KnowledgeInvariantError(
                "Graphiti validation requires namespace, scope, projection profile, and probe query"
            )

    @property
    def descriptor(self) -> ProjectionValidatorDescriptor:
        return ProjectionValidatorDescriptor(
            validator_identity=_VALIDATION_REQUIREMENT.validator_identity,
            validator_version=_VALIDATION_REQUIREMENT.validator_version,
            ruleset_id=_VALIDATION_REQUIREMENT.ruleset_id,
            ruleset_digest=_VALIDATION_REQUIREMENT.ruleset_digest,
        )

    @property
    def config_digest(self) -> str:
        bindings = sorted(
            (
                {
                    "resource_version_ref": str(binding.resource_version_ref),
                    "source_revision_id": binding.source_revision_id,
                    "segment_key": binding.segment_key,
                    "source_slice_sha256": binding.source_slice_sha256,
                    "provider_partition_key": binding.provider_partition_key,
                    "provider_source_id": binding.provider_source_id,
                }
                for binding in self.source_bindings
            ),
            key=lambda item: (
                item["resource_version_ref"],
                item["segment_key"],
                item["provider_source_id"],
            ),
        )
        return _canonical_digest(
            {
                "adapter_config_digest": self.adapter.descriptor.config_digest,
                "bindings": bindings,
                "namespace_key": self.namespace_key,
                "probe_query": self.probe_query,
                "projection_profile_id": self.projection_profile_id,
                "scope_key": self.scope_key,
            }
        )

    def validate(self, attempt) -> ProjectionValidationReport:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._validate_async(attempt))
        raise RuntimeError(
            "GraphitiProjectionValidator.validate must run outside an active asyncio event loop"
        )

    async def _validate_async(self, attempt) -> ProjectionValidationReport:
        checks: list[ProjectionValidationCheck] = []
        descriptor = self.adapter.descriptor
        expected_partition = self.adapter.partition_key(
            namespace_key=self.namespace_key,
            scope_key=self.scope_key,
            projection_profile_id=self.projection_profile_id,
        )
        contract_ok = (
            attempt.backend_identity == descriptor.backend_identity
            and attempt.backend_version == descriptor.backend_version
            and attempt.config_digest == descriptor.config_digest
            and attempt.namespace_key == self.namespace_key
            and attempt.scope_key == self.scope_key
            and attempt.profile_id == self.projection_profile_id
        )
        checks.append(
            ProjectionValidationCheck(
                check_code="attempt-contract",
                outcome=(
                    ProjectionCheckOutcome.PASSED
                    if contract_ok
                    else ProjectionCheckOutcome.FAILED
                ),
                evidence={
                    "backend_identity": attempt.backend_identity,
                    "backend_version": attempt.backend_version,
                    "config_digest": attempt.config_digest,
                    "namespace_key": attempt.namespace_key,
                    "scope_key": attempt.scope_key,
                    "projection_profile_id": attempt.profile_id,
                },
            )
        )

        expected_segments = {
            (
                segment.resource_version_ref,
                segment.source_revision_id,
                segment.segment_key,
                segment.source_slice_sha256,
            )
            for segment in self.segments
        }
        binding_segments = {
            (
                binding.resource_version_ref,
                binding.source_revision_id,
                binding.segment_key,
                binding.source_slice_sha256,
            )
            for binding in self.source_bindings
        }
        provider_ids = [binding.provider_source_id for binding in self.source_bindings]
        wrong_binding_partitions = sorted(
            binding.provider_source_id
            for binding in self.source_bindings
            if binding.provider_partition_key != expected_partition
        )
        binding_contract_ok = (
            bool(expected_segments)
            and len(self.source_bindings) == len(expected_segments)
            and binding_segments == expected_segments
            and len(set(provider_ids)) == len(provider_ids)
            and all(provider_id.strip() for provider_id in provider_ids)
            and not wrong_binding_partitions
        )
        checks.append(
            ProjectionValidationCheck(
                check_code="source-binding-contract",
                outcome=(
                    ProjectionCheckOutcome.PASSED
                    if binding_contract_ok
                    else ProjectionCheckOutcome.FAILED
                ),
                evidence={
                    "expected_segment_count": len(expected_segments),
                    "binding_count": len(self.source_bindings),
                    "unique_provider_source_count": len(set(provider_ids)),
                    "wrong_partition_provider_source_ids": wrong_binding_partitions,
                },
            )
        )

        integrity_warnings = [
            warning
            for warning in attempt.warnings
            if any(fragment in warning for fragment in _INTEGRITY_WARNING_FRAGMENTS)
        ]
        checks.append(
            ProjectionValidationCheck(
                check_code="projection-integrity-warnings",
                outcome=(
                    ProjectionCheckOutcome.PASSED
                    if not integrity_warnings
                    else ProjectionCheckOutcome.FAILED
                ),
                evidence={"warnings": integrity_warnings},
            )
        )

        observed_keys = await self.adapter.existing_source_keys(
            source_keys=tuple(provider_ids),
            namespace_key=self.namespace_key,
            scope_key=self.scope_key,
            projection_profile_id=self.projection_profile_id,
        )
        missing_keys = sorted(set(provider_ids) - set(observed_keys))
        checks.append(
            ProjectionValidationCheck(
                check_code="source-episodes-present",
                outcome=(
                    ProjectionCheckOutcome.PASSED
                    if binding_contract_ok and not missing_keys
                    else ProjectionCheckOutcome.FAILED
                ),
                evidence={
                    "expected_count": len(provider_ids),
                    "observed_count": len(observed_keys),
                    "missing_provider_source_ids": missing_keys,
                },
            )
        )

        lifecycle_inventory = await self.adapter.lifecycle_inventory(
            namespace_key=self.namespace_key,
            scope_key=self.scope_key,
            projection_profile_id=self.projection_profile_id,
        )
        inventory_payload = [
            {
                "provider_edge_id": edge.provider_edge_id,
                "partition_key": edge.partition_key,
                "source_correlation_keys": list(edge.source_correlation_keys),
                "invalid_at": edge.invalid_at.isoformat() if edge.invalid_at else None,
                "expired_at": edge.expired_at.isoformat() if edge.expired_at else None,
            }
            for edge in lifecycle_inventory.edges
        ]
        inventory_digest = _canonical_digest({"edges": inventory_payload})
        lifecycle_outcome = (
            ProjectionCheckOutcome.PASSED
            if lifecycle_inventory.complete
            else ProjectionCheckOutcome.INDETERMINATE
        )
        retired_edge_ids = sorted(
            edge.provider_edge_id
            for edge in lifecycle_inventory.edges
            if edge.invalid_at is not None or edge.expired_at is not None
        )
        wrong_partition_edge_ids = sorted(
            edge.provider_edge_id
            for edge in lifecycle_inventory.edges
            if edge.partition_key != expected_partition
        )
        missing_attribution_edge_ids = sorted(
            edge.provider_edge_id
            for edge in lifecycle_inventory.edges
            if not edge.source_correlation_keys
        )
        multi_source_edge_ids = sorted(
            edge.provider_edge_id
            for edge in lifecycle_inventory.edges
            if len(edge.source_correlation_keys) > 1
        )
        provider_id_set = set(provider_ids)
        unknown_source_edge_ids = sorted(
            edge.provider_edge_id
            for edge in lifecycle_inventory.edges
            if any(
                source_id not in provider_id_set
                for source_id in edge.source_correlation_keys
            )
        )
        if lifecycle_inventory.complete and (
            lifecycle_inventory.partition_key != expected_partition
            or retired_edge_ids
            or wrong_partition_edge_ids
            or missing_attribution_edge_ids
            or unknown_source_edge_ids
        ):
            lifecycle_outcome = ProjectionCheckOutcome.FAILED
        checks.append(
            ProjectionValidationCheck(
                check_code="governed-lifecycle-inventory",
                outcome=lifecycle_outcome,
                evidence={
                    "complete": lifecycle_inventory.complete,
                    "error": lifecycle_inventory.error,
                    "expected_partition": expected_partition,
                    "observed_partition": lifecycle_inventory.partition_key,
                    "edge_count": len(lifecycle_inventory.edges),
                    "source_contribution_count": sum(
                        len(edge.source_correlation_keys)
                        for edge in lifecycle_inventory.edges
                    ),
                    "inventory_digest": inventory_digest,
                    "retired_edge_ids": retired_edge_ids,
                    "wrong_partition_edge_ids": wrong_partition_edge_ids,
                    "missing_attribution_edge_ids": missing_attribution_edge_ids,
                    "multi_source_edge_ids": multi_source_edge_ids,
                    "unknown_source_edge_ids": unknown_source_edge_ids,
                },
                detail=(
                    "Governed document validation requires a complete edge inventory with "
                    "zero provider-controlled retirement and exact current source attribution."
                ),
            )
        )

        probe_hits = await self.adapter.search(
            query=self.probe_query,
            namespace_key=self.namespace_key,
            scope_key=self.scope_key,
            projection_profile_id=self.projection_profile_id,
            limit=10,
        )
        wrong_partition = [
            hit.provider_hit_id for hit in probe_hits if hit.partition_key != expected_partition
        ]

        # Search a fresh sibling Falkor graph without writing a synthetic sentinel.
        # Any returned hit proves partition leakage because nothing was projected there.
        isolation_scope = f"{self.scope_key}:kc-isolation:{attempt.attempt_id}"
        isolation_hits = await self.adapter.search(
            query=self.probe_query,
            namespace_key=self.namespace_key,
            scope_key=isolation_scope,
            projection_profile_id=self.projection_profile_id,
            limit=10,
        )
        checks.append(
            ProjectionValidationCheck(
                check_code="namespace-search-isolation",
                outcome=(
                    ProjectionCheckOutcome.PASSED
                    if not wrong_partition and not isolation_hits
                    else ProjectionCheckOutcome.FAILED
                ),
                evidence={
                    "expected_partition": expected_partition,
                    "wrong_partition_hit_ids": wrong_partition,
                    "isolated_scope_result_count": len(isolation_hits),
                    "isolated_scope_partition": self.adapter.partition_key(
                        namespace_key=self.namespace_key,
                        scope_key=isolation_scope,
                        projection_profile_id=self.projection_profile_id,
                    ),
                },
            )
        )

        missing_attribution = [
            hit.provider_hit_id for hit in probe_hits if not hit.source_correlation_keys
        ]
        checks.append(
            ProjectionValidationCheck(
                check_code="search-source-attribution",
                outcome=(
                    ProjectionCheckOutcome.PASSED
                    if not missing_attribution
                    else ProjectionCheckOutcome.FAILED
                ),
                evidence={
                    "probe_result_count": len(probe_hits),
                    "missing_attribution_hit_ids": missing_attribution,
                    "attributed_hit_ids": [
                        hit.provider_hit_id
                        for hit in probe_hits
                        if hit.source_correlation_keys
                    ],
                },
                detail=(
                    "Zero probe hits are safe but do not prove retrieval usefulness; "
                    "the host qualification separately requires at least one trusted result."
                ),
            )
        )

        if any(
            check.outcome is ProjectionCheckOutcome.INDETERMINATE for check in checks
        ):
            outcome = ProjectionValidationOutcome.QUARANTINED
            return ProjectionValidationReport(outcome=outcome, checks=tuple(checks))

        failed_codes = {
            check.check_code
            for check in checks
            if check.outcome is ProjectionCheckOutcome.FAILED
        }
        if not failed_codes:
            outcome = ProjectionValidationOutcome.VALIDATED
        elif failed_codes.intersection(
            {
                "attempt-contract",
                "source-binding-contract",
                "governed-lifecycle-inventory",
                "namespace-search-isolation",
            }
        ):
            outcome = ProjectionValidationOutcome.REJECTED
        else:
            outcome = ProjectionValidationOutcome.INCOMPLETE
        return ProjectionValidationReport(outcome=outcome, checks=tuple(checks))
