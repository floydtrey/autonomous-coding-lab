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
    ProjectionValidatorDescriptor,
)


_EXPECTED_GRAPHITI_VERSION = "0.30.2"
_ADAPTER_VERSION = "1"
_INTEGRITY_WARNING_FRAGMENTS = (
    "Target entity not found in nodes for edge relation",
    "Source entity not found in nodes for edge relation",
)
_VALIDATION_RULESET = {
    "id": "kc-graphiti-live-v1",
    "checks": [
        "attempt-contract",
        "source-binding-contract",
        "projection-integrity-warnings",
        "source-episodes-present",
        "namespace-search-isolation",
        "search-source-attribution",
    ],
}
_VALIDATION_RULESET_DIGEST = "sha256:" + sha256(
    json.dumps(_VALIDATION_RULESET, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()


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
    embed_model: str = "nomic-embed-text:latest"
    embed_dim: int = 768
    structured_output_mode: str = "json_schema"
    reasoning_effort: str = "none"

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
                "reasoning_effort": self.reasoning_effort,
                "structured_output_mode": self.structured_output_mode,
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

        llm_config = LLMConfig(
            api_key=self.config.ollama_api_key,
            model=self.config.llm_model,
            small_model=self.config.llm_model,
            base_url=self.config.ollama_base_url,
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
            validator_identity="kc-graphiti-live-validator",
            validator_version="1",
            ruleset_id=_VALIDATION_RULESET["id"],
            ruleset_digest=_VALIDATION_RULESET_DIGEST,
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

        failed_codes = {
            check.check_code
            for check in checks
            if check.outcome is ProjectionCheckOutcome.FAILED
        }
        if not failed_codes:
            outcome = ProjectionValidationOutcome.VALIDATED
        elif failed_codes.intersection(
            {"attempt-contract", "source-binding-contract", "namespace-search-isolation"}
        ):
            outcome = ProjectionValidationOutcome.REJECTED
        else:
            outcome = ProjectionValidationOutcome.INCOMPLETE
        return ProjectionValidationReport(outcome=outcome, checks=tuple(checks))
