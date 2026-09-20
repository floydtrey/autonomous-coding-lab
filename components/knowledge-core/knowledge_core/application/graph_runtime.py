from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
import logging
import os
import threading
from uuid import UUID, uuid5

from knowledge_core.application.authorization import AuthorizationKernel
from knowledge_core.application.graph_readiness import (
    disabled_graph_readiness,
    inspect_source_neutral_graph_readiness,
)
from knowledge_core.application.source_neutral_graph import (
    DEFAULT_GRAPH_SYNC_MAX_SEGMENTS,
    MAX_GRAPH_SYNC_SEGMENTS,
    SourceNeutralGraphProjectionKnowledgeKernel,
)
from knowledge_core.application.unified_retrieval import UnifiedGraphSearchBinding
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.authority.retrieval import (
    RetrievalAuthorityDecision,
    RetrievalAuthorityOperation,
    RetrievalAuthorityRequest,
)
from knowledge_core.domain.authorization import KCOperation
from knowledge_core.domain.generations import DerivedKind
from knowledge_core.domain.projection_adapter import (
    ProjectionAdapter,
    ProjectionAdapterExecutionError,
)
from knowledge_core.domain.projection_evidence import (
    ProjectionDisposition,
    ProjectionValidationState,
)
from knowledge_core.domain.projection_validation import ProjectionValidationOutcome
from knowledge_core.domain.unified_retrieval import (
    GraphRetrievalEvidence,
    GraphRetrievalState,
)
from knowledge_core.storage.projection_models import ProjectionAttempt
from knowledge_core.storage.resource_models import ResourceVersion
from knowledge_core_providers.graphiti import (
    GraphitiLocalConfig,
    GraphitiProjectionValidator,
    _require_graphiti_version,
)


_LOG = logging.getLogger(__name__)
_DEFAULT_NAMESPACE = "kc:graphiti-source-neutral-v1"
_ATTEMPT_NAMESPACE = UUID("ba63ea9d-3dd3-5c0b-8e08-62f98c6d7081")
_VALIDATION_NAMESPACE = UUID("2b58eefe-5c0d-5288-8fca-a32fa58131e6")


def _env_bool(source: Mapping[str, str], name: str, default: bool) -> bool:
    raw = source.get(name)
    if raw is None:
        return default
    normalized = raw.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean value")


def _env_int(
    source: Mapping[str, str],
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw = source.get(name)
    try:
        value = default if raw is None else int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < minimum or value > maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return value


def _canonical_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _stable_uuid(namespace: UUID, payload: dict[str, object]) -> UUID:
    return uuid5(namespace, _canonical_digest(payload))


@dataclass(frozen=True)
class GraphRuntimeSettings:
    enabled: bool = False
    namespace_key: str = _DEFAULT_NAMESPACE
    max_segments: int = DEFAULT_GRAPH_SYNC_MAX_SEGMENTS
    max_attempts: int = 2
    provider: GraphitiLocalConfig = GraphitiLocalConfig()

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
    ) -> "GraphRuntimeSettings":
        source = os.environ if env is None else env
        enabled = _env_bool(
            source,
            "KNOWLEDGE_CORE_GRAPH_ENABLED",
            False,
        )
        namespace = source.get(
            "KNOWLEDGE_CORE_GRAPH_NAMESPACE",
            _DEFAULT_NAMESPACE,
        ).strip()
        if not namespace:
            raise RuntimeError("KNOWLEDGE_CORE_GRAPH_NAMESPACE must be non-blank")

        defaults = GraphitiLocalConfig()
        provider = GraphitiLocalConfig(
            falkor_host=source.get("FALKORDB_HOST", defaults.falkor_host).strip(),
            falkor_port=_env_int(
                source,
                "FALKORDB_PORT",
                defaults.falkor_port,
                minimum=1,
                maximum=65535,
            ),
            falkor_username=source.get("FALKORDB_USERNAME") or None,
            falkor_password=source.get("FALKORDB_PASSWORD") or None,
            ollama_base_url=source.get(
                "GRAPHITI_OLLAMA_BASE_URL",
                defaults.ollama_base_url,
            ).strip(),
            ollama_api_key=source.get(
                "GRAPHITI_OLLAMA_API_KEY",
                source.get("OLLAMA_API_KEY", defaults.ollama_api_key),
            ),
            llm_model=source.get(
                "GRAPHITI_LLM_MODEL",
                defaults.llm_model,
            ).strip(),
            llm_max_tokens=_env_int(
                source,
                "GRAPHITI_LLM_MAX_TOKENS",
                defaults.llm_max_tokens,
                minimum=1024,
                maximum=262144,
            ),
            temperature=float(
                source.get("GRAPHITI_TEMPERATURE", str(defaults.temperature))
            ),
            embed_model=source.get(
                "GRAPHITI_EMBED_MODEL",
                defaults.embed_model,
            ).strip(),
            embed_dim=_env_int(
                source,
                "GRAPHITI_EMBED_DIM",
                defaults.embed_dim,
                minimum=1,
                maximum=65536,
            ),
            structured_output_mode=defaults.structured_output_mode,
            reasoning_effort=defaults.reasoning_effort,
            projection_policy=defaults.projection_policy,
        )
        if not provider.falkor_host:
            raise RuntimeError("FALKORDB_HOST must be non-blank")
        if not provider.ollama_base_url:
            raise RuntimeError("GRAPHITI_OLLAMA_BASE_URL must be non-blank")
        if not provider.llm_model:
            raise RuntimeError("GRAPHITI_LLM_MODEL must be non-blank")
        if not provider.embed_model:
            raise RuntimeError("GRAPHITI_EMBED_MODEL must be non-blank")

        return cls(
            enabled=enabled,
            namespace_key=namespace,
            max_segments=_env_int(
                source,
                "KNOWLEDGE_CORE_GRAPH_MAX_SEGMENTS",
                DEFAULT_GRAPH_SYNC_MAX_SEGMENTS,
                minimum=1,
                maximum=MAX_GRAPH_SYNC_SEGMENTS,
            ),
            max_attempts=_env_int(
                source,
                "KNOWLEDGE_CORE_GRAPH_MAX_ATTEMPTS",
                2,
                minimum=1,
                maximum=4,
            ),
            provider=provider,
        )


class _KCGraphAuthority:
    def __init__(
        self,
        *,
        session_factory,
        principal_ref: UUID,
        active_scope_ref: UUID,
        namespace_key: str,
        graph_scope_key: str,
    ) -> None:
        self.session_factory = session_factory
        self.principal_ref = principal_ref
        self.active_scope_ref = active_scope_ref
        self.namespace_key = namespace_key
        self.graph_scope_key = graph_scope_key

    def evaluate_retrieval(
        self,
        request: RetrievalAuthorityRequest,
    ) -> RetrievalAuthorityDecision:
        allowed = (
            request.caller_principal_ref == str(self.principal_ref)
            and request.operation is RetrievalAuthorityOperation.SEARCH_GRAPH
            and request.namespace_key == self.namespace_key
            and request.scope_key == self.graph_scope_key
            and not request.include_superseded
        )
        reason = "graph-request-boundary-mismatch"
        if allowed:
            with self.session_factory() as session:
                decision = AuthorizationKernel(session).evaluate(
                    principal_ref=self.principal_ref,
                    operation=KCOperation.SEARCH,
                    scope_ref=self.active_scope_ref,
                )
                allowed = decision.allowed
                reason = (
                    "authenticated-principal-scope-search-authorized"
                    if allowed
                    else "active-scope-search-not-authorized"
                )
        return RetrievalAuthorityDecision(
            allowed=allowed,
            decision_ref=(
                f"kc-graph:{self.principal_ref}:{self.active_scope_ref}"
            ),
            reason_code=reason,
        )


class KnowledgeGraphRuntime:
    """Normal-service Graphiti coordinator.

    Projection remains derived from the current canonical SR-2 generation. The
    first authorized scoped search after a generation change performs a bounded
    build/validation in a worker thread. Writes remain canonical/text-first and
    therefore do not wait on Graphiti.
    """

    def __init__(
        self,
        *,
        session_factory,
        artifact_store: LocalArtifactStore,
        adapter: ProjectionAdapter,
        namespace_key: str = _DEFAULT_NAMESPACE,
        max_segments: int = DEFAULT_GRAPH_SYNC_MAX_SEGMENTS,
        max_attempts: int = 2,
    ) -> None:
        self.session_factory = session_factory
        self.artifact_store = artifact_store
        self.adapter = adapter
        self.namespace_key = namespace_key.strip()
        self.max_segments = int(max_segments)
        self.max_attempts = int(max_attempts)
        self._sync_lock = threading.Lock()
        if not self.namespace_key:
            raise ValueError("graph namespace must be non-blank")
        if self.max_segments < 1 or self.max_segments > MAX_GRAPH_SYNC_SEGMENTS:
            raise ValueError(
                f"max_segments must be between 1 and {MAX_GRAPH_SYNC_SEGMENTS}"
            )
        if self.max_attempts < 1 or self.max_attempts > 4:
            raise ValueError("max_attempts must be between 1 and 4")

    @classmethod
    def from_env(
        cls,
        *,
        session_factory,
        artifact_store: LocalArtifactStore,
        env: Mapping[str, str] | None = None,
    ) -> "KnowledgeGraphRuntime | None":
        settings = GraphRuntimeSettings.from_env(env)
        if not settings.enabled:
            return None
        # Import the hardened provider only when graph service is explicitly
        # enabled, so ordinary KC installs do not require graphiti-core.
        from knowledge_core_providers.graphiti_hardened import (
            HardenedGraphitiProjectionAdapter,
        )

        # Explicit graph enablement is a deployment contract. Fail startup for a
        # missing/wrong Graphiti package instead of silently discovering it on the
        # first user query.
        _require_graphiti_version()

        return cls(
            session_factory=session_factory,
            artifact_store=artifact_store,
            adapter=HardenedGraphitiProjectionAdapter(settings.provider),
            namespace_key=settings.namespace_key,
            max_segments=settings.max_segments,
            max_attempts=settings.max_attempts,
        )

    @staticmethod
    def graph_scope_key(project_scope_ref: UUID) -> str:
        return f"kc-project:{project_scope_ref}"

    def _project_scope_for_request(
        self,
        *,
        principal_ref: UUID,
        active_scope_ref: UUID | None,
    ):
        if active_scope_ref is None:
            return None
        with self.session_factory() as session:
            authz = AuthorizationKernel(session)
            decision = authz.evaluate(
                principal_ref=principal_ref,
                operation=KCOperation.SEARCH,
                scope_ref=active_scope_ref,
            )
            if not decision.allowed:
                return None
            return authz.project_scope_for(active_scope_ref)

    def _projectable_version_refs(
        self,
        *,
        session,
        kernel: SourceNeutralGraphProjectionKnowledgeKernel,
        project_scope_ref: UUID,
    ) -> tuple[UUID, ...]:
        logical_refs = AuthorizationKernel(session).graph_projectable_resource_refs(
            scope_ref=project_scope_ref,
        )
        current = kernel.current_generation(derived_kind=DerivedKind.TEXT)
        if current is None or not logical_refs:
            return ()
        refs: list[UUID] = []
        for source in current.sources:
            version = session.get(ResourceVersion, source.source_ref)
            if version is not None and version.resource_ref_id in logical_refs:
                refs.append(version.ref_id)
        return tuple(dict.fromkeys(refs))

    def _attempt_id(
        self,
        *,
        plan,
        graph_scope_key: str,
        ordinal: int,
    ) -> UUID:
        descriptor = self.adapter.descriptor
        return _stable_uuid(
            _ATTEMPT_NAMESPACE,
            {
                "adapter_config_digest": descriptor.config_digest,
                "adapter_identity": descriptor.adapter_identity,
                "adapter_version": descriptor.adapter_version,
                "generation_id": str(plan.generation_id),
                "namespace_key": self.namespace_key,
                "ordinal": ordinal,
                "profile_digest": plan.profile_digest,
                "profile_id": plan.profile_id,
                "scope_key": graph_scope_key,
                "sources": [
                    [str(ref), revision]
                    for ref, revision in sorted(
                        plan.sources,
                        key=lambda item: str(item[0]),
                    )
                ],
            },
        )

    def _validation_id(
        self,
        *,
        attempt_id: UUID,
        validator: GraphitiProjectionValidator,
    ) -> UUID:
        return _stable_uuid(
            _VALIDATION_NAMESPACE,
            {
                "attempt_id": str(attempt_id),
                "config_digest": validator.config_digest,
                "ruleset_digest": validator.descriptor.ruleset_digest,
                "ruleset_id": validator.descriptor.ruleset_id,
                "validator_identity": validator.descriptor.validator_identity,
                "validator_version": validator.descriptor.validator_version,
            },
        )

    def _attempt_is_ready(
        self,
        *,
        kernel: SourceNeutralGraphProjectionKnowledgeKernel,
        attempt_id: UUID,
        expected_refs: tuple[UUID, ...],
    ) -> bool:
        attempt = kernel.read_projection_attempt(attempt_id)
        if (
            attempt.disposition is not ProjectionDisposition.SUCCEEDED
            or attempt.validation_state is not ProjectionValidationState.VALIDATED
        ):
            return False
        requirement = self.adapter.descriptor.validation_requirement
        if requirement is not None and not kernel.projection_satisfies_validation_requirement(
            attempt_id=attempt_id,
            requirement=requirement,
        ):
            return False
        return {source.source_ref for source in attempt.sources} == set(expected_refs)

    def _ready_attempt_ids_for_refs(
        self,
        *,
        kernel: SourceNeutralGraphProjectionKnowledgeKernel,
        refs: tuple[UUID, ...],
        project_scope_ref: UUID,
    ) -> frozenset[UUID]:
        if not refs:
            return frozenset()
        plan = kernel.build_sr2_projection_plan(resource_version_refs=refs)
        graph_scope_key = self.graph_scope_key(project_scope_ref)
        for ordinal in range(self.max_attempts):
            attempt_id = self._attempt_id(
                plan=plan,
                graph_scope_key=graph_scope_key,
                ordinal=ordinal,
            )
            if kernel.session.get(ProjectionAttempt, attempt_id) is None:
                continue
            if self._attempt_is_ready(
                kernel=kernel,
                attempt_id=attempt_id,
                expected_refs=refs,
            ):
                return frozenset((attempt_id,))
        return frozenset()

    def _ensure_ready_sync(
        self,
        *,
        project_scope_ref: UUID,
        probe_query: str,
    ) -> None:
        with self._sync_lock:
            with self.session_factory() as session:
                kernel = SourceNeutralGraphProjectionKnowledgeKernel(
                    session,
                    artifact_store=self.artifact_store,
                )
                refs = self._projectable_version_refs(
                    session=session,
                    kernel=kernel,
                    project_scope_ref=project_scope_ref,
                )
                if not refs:
                    return
                plan = kernel.build_sr2_projection_plan(
                    resource_version_refs=refs,
                )
                if len(plan.segments) > self.max_segments:
                    raise RuntimeError(
                        f"graph sync plan has {len(plan.segments)} segments, "
                        f"exceeding configured maximum {self.max_segments}"
                    )
                graph_scope_key = self.graph_scope_key(project_scope_ref)

                for ordinal in range(self.max_attempts):
                    attempt_id = self._attempt_id(
                        plan=plan,
                        graph_scope_key=graph_scope_key,
                        ordinal=ordinal,
                    )
                    existing = session.get(ProjectionAttempt, attempt_id)
                    if existing is not None:
                        if self._attempt_is_ready(
                            kernel=kernel,
                            attempt_id=attempt_id,
                            expected_refs=refs,
                        ):
                            return
                        if existing.disposition == ProjectionDisposition.PENDING.value:
                            # External side effects are ambiguous. Never create a
                            # competing retry automatically while a durable attempt
                            # is still pending.
                            return
                        if (
                            existing.disposition
                            == ProjectionDisposition.SUCCEEDED.value
                            and existing.validation_state
                            == ProjectionValidationState.UNVALIDATED.value
                        ):
                            execution_attempt_id = attempt_id
                        else:
                            continue
                    else:
                        try:
                            execution = asyncio.run(
                                kernel.sync_current_sr2_projection(
                                    attempt_id=attempt_id,
                                    namespace_key=self.namespace_key,
                                    scope_key=graph_scope_key,
                                    adapter=self.adapter,
                                    resource_version_refs=refs,
                                    max_segments=self.max_segments,
                                )
                            )
                        except ProjectionAdapterExecutionError:
                            continue
                        if (
                            execution.attempt.disposition
                            is not ProjectionDisposition.SUCCEEDED
                        ):
                            continue
                        execution_attempt_id = attempt_id

                    plan_for_attempt = kernel.projection_plan_for_attempt(
                        execution_attempt_id
                    )
                    bindings = kernel.read_projection_source_bindings(
                        execution_attempt_id
                    )
                    validator = GraphitiProjectionValidator(
                        adapter=self.adapter,
                        segments=plan_for_attempt.segments,
                        source_bindings=bindings,
                        namespace_key=self.namespace_key,
                        scope_key=graph_scope_key,
                        projection_profile_id=plan_for_attempt.profile_id,
                        probe_query=probe_query,
                    )
                    validation = kernel.validate_projection_attempt(
                        validation_id=self._validation_id(
                            attempt_id=execution_attempt_id,
                            validator=validator,
                        ),
                        attempt_id=execution_attempt_id,
                        validator=validator,
                        config_digest=validator.config_digest,
                    )
                    if (
                        validation.outcome
                        is ProjectionValidationOutcome.VALIDATED
                    ):
                        return

                raise RuntimeError(
                    "no validated Graphiti projection could be established "
                    "within the configured bounded attempts"
                )

    async def prepare_binding(
        self,
        *,
        principal_ref: UUID,
        active_scope_ref: UUID | None,
        query: str,
    ) -> UnifiedGraphSearchBinding | None:
        project_scope = self._project_scope_for_request(
            principal_ref=principal_ref,
            active_scope_ref=active_scope_ref,
        )
        if project_scope is None:
            return None

        try:
            await asyncio.to_thread(
                self._ensure_ready_sync,
                project_scope_ref=project_scope.scope_ref,
                probe_query=query,
            )
        except Exception as exc:
            # Graph is optional derived infrastructure. Canonical/lexical retrieval
            # must remain usable and provider exception detail is intentionally not
            # exposed through the consumer response.
            _LOG.warning(
                "KC Graphiti preparation unavailable (%s)",
                type(exc).__name__,
            )

        with self.session_factory() as session:
            authz = AuthorizationKernel(session)
            allowed_statement = authz.authorized_resource_refs_statement(
                principal_ref=principal_ref,
                operation=KCOperation.SEARCH,
                scope_ref=active_scope_ref,
            )
            authorized_refs = frozenset(
                session.scalars(allowed_statement).all()
            )
            kernel = SourceNeutralGraphProjectionKnowledgeKernel(
                session,
                artifact_store=self.artifact_store,
            )
            projectable_refs = self._projectable_version_refs(
                session=session,
                kernel=kernel,
                project_scope_ref=project_scope.scope_ref,
            )
            allowed_attempt_ids = self._ready_attempt_ids_for_refs(
                kernel=kernel,
                refs=projectable_refs,
                project_scope_ref=project_scope.scope_ref,
            )

        graph_scope_key = self.graph_scope_key(project_scope.scope_ref)
        return UnifiedGraphSearchBinding(
            adapter=self.adapter,
            authority_evaluator=_KCGraphAuthority(
                session_factory=self.session_factory,
                principal_ref=principal_ref,
                active_scope_ref=active_scope_ref,
                namespace_key=self.namespace_key,
                graph_scope_key=graph_scope_key,
            ),
            caller_principal_ref=str(principal_ref),
            namespace_key=self.namespace_key,
            scope_key=graph_scope_key,
            authorized_resource_refs=authorized_refs,
            authorization_principal_ref=principal_ref,
            authorization_scope_ref=active_scope_ref,
            allowed_attempt_ids=allowed_attempt_ids,
        )

    def readiness(
        self,
        *,
        principal_ref: UUID,
        active_scope_ref: UUID | None,
    ) -> GraphRetrievalEvidence:
        project_scope = self._project_scope_for_request(
            principal_ref=principal_ref,
            active_scope_ref=active_scope_ref,
        )
        if project_scope is None:
            return disabled_graph_readiness()

        with self.session_factory() as session:
            kernel = SourceNeutralGraphProjectionKnowledgeKernel(
                session,
                artifact_store=self.artifact_store,
            )
            graph_scope_key = self.graph_scope_key(project_scope.scope_ref)
            evidence = inspect_source_neutral_graph_readiness(
                kernel=kernel,
                adapter=self.adapter,
                namespace_key=self.namespace_key,
                scope_key=graph_scope_key,
            )
            expected_refs = self._projectable_version_refs(
                session=session,
                kernel=kernel,
                project_scope_ref=project_scope.scope_ref,
            )
            exact_ready = self._ready_attempt_ids_for_refs(
                kernel=kernel,
                refs=expected_refs,
                project_scope_ref=project_scope.scope_ref,
            )
            if exact_ready:
                return GraphRetrievalEvidence(
                    state=GraphRetrievalState.READY,
                    namespace_key=self.namespace_key,
                    scope_key=graph_scope_key,
                    generation_id=evidence.generation_id,
                    attempt_ids=tuple(exact_ready),
                )
            if evidence.state is GraphRetrievalState.READY:
                return GraphRetrievalEvidence(
                    state=GraphRetrievalState.STALE,
                    namespace_key=self.namespace_key,
                    scope_key=graph_scope_key,
                    generation_id=evidence.generation_id,
                    attempt_ids=evidence.attempt_ids,
                    reason_code="graph-projectable-source-set-changed",
                )
            return evidence
