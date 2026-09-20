from __future__ import annotations

from dataclasses import dataclass

from knowledge_core.application.consumer_read import ConsumerReadKnowledgeKernel
from knowledge_core.application.source_neutral_graph import (
    SourceNeutralGraphProjectionKnowledgeKernel,
)
from knowledge_core.authority.retrieval import RetrievalAuthorityEvaluator
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.projection_adapter import (
    ProjectionAdapter,
    TrustedProjectionSearchSnapshot,
)
from knowledge_core.domain.source_neutral_projection import (
    GovernedProjectionSourceSegment,
)
from knowledge_core.domain.unified_retrieval import (
    GraphRetrievalEvidence,
    GraphRetrievalHit,
    GraphRetrievalState,
    GraphSourceCorrelation,
    UnifiedRetrievalSearchSnapshot,
    UnifiedRetrievalWarning,
    UnifiedRetrievalWarningCode,
)


@dataclass(frozen=True)
class UnifiedGraphSearchBinding:
    """Explicit host binding for optional trusted graph augmentation.

    Supplying this binding does not synchronize/build a graph. It only permits the
    coordinator to query the existing validated graph-retrieval kernel. The adapter
    and Authority seam are injected by the trusted host rather than discovered or
    started by KC.
    """

    adapter: ProjectionAdapter
    authority_evaluator: RetrievalAuthorityEvaluator | None
    caller_principal_ref: str
    namespace_key: str
    scope_key: str

    def __post_init__(self) -> None:
        for name in ("caller_principal_ref", "namespace_key", "scope_key"):
            if not str(getattr(self, name)).strip():
                raise KnowledgeInvariantError(
                    f"unified graph search binding {name} must not be blank"
                )


class UnifiedRetrievalCoordinator:
    """Task 6C lexical-first coordinator for the accepted Task 6B contract.

    Lexical retrieval is the mandatory trusted baseline. Graph evidence is optional
    augmentation and can only come from the existing source-neutral trusted graph
    kernel. Graph-side absence, denial, corruption or provider failure degrades to a
    bounded graph state without converting a lexical success into failure.

    This class does not expose an HTTP route, synchronize Graphiti, start providers,
    launch models, mutate graph state or alter the accepted lexical ranking path.
    """

    def __init__(
        self,
        *,
        lexical_kernel: ConsumerReadKnowledgeKernel,
        graph_kernel: SourceNeutralGraphProjectionKnowledgeKernel,
        graph_binding: UnifiedGraphSearchBinding | None = None,
    ) -> None:
        self.lexical_kernel = lexical_kernel
        self.graph_kernel = graph_kernel
        self.graph_binding = graph_binding

    @staticmethod
    def _warning(
        *,
        code: UnifiedRetrievalWarningCode,
        message: str,
    ) -> tuple[UnifiedRetrievalWarning, ...]:
        return (UnifiedRetrievalWarning(code=code, message=message),)

    @classmethod
    def _degraded(
        cls,
        *,
        lexical,
        state: GraphRetrievalState,
        reason_code: str,
        warning_code: UnifiedRetrievalWarningCode,
        warning_message: str,
    ) -> UnifiedRetrievalSearchSnapshot:
        return UnifiedRetrievalSearchSnapshot(
            lexical=lexical,
            graph=GraphRetrievalEvidence(
                state=state,
                reason_code=reason_code,
            ),
            warnings=cls._warning(
                code=warning_code,
                message=warning_message,
            ),
        )

    @staticmethod
    def _source_correlation(
        source: GovernedProjectionSourceSegment,
    ) -> GraphSourceCorrelation:
        return GraphSourceCorrelation(
            resource_version_ref=source.resource_version_ref,
            source_revision_id=source.source_revision_id,
            segment_key=source.segment_key,
            segment_ordinal=source.segment_ordinal,
            source_slice_sha256=source.source_slice_sha256,
            source_line_start=source.source_line_start,
            source_line_end=source.source_line_end,
            source_identity_digest=source.source_identity_digest,
            source_kind=source.source_kind,
            origin_scope=source.origin_scope,
            collection_key=source.collection_key,
            item_key=source.item_key,
            project_keys=source.project_keys,
            governed_source_observation_id=source.governed_source_observation_id,
            governed_observation_digest=source.governed_observation_digest,
            governed_decision_id=source.governed_decision_id,
            governed_decision_digest=source.governed_decision_digest,
            governing_snapshot_digest=source.governing_snapshot_digest,
            governed_projection_digest=source.governed_projection_digest,
            reference_time=source.reference_time,
            reference_time_policy=source.reference_time_policy,
            source_repository_key=source.source_repository_key,
            source_document_key=source.source_document_key,
            source_path=source.source_path,
            source_version=source.source_version,
        )

    @classmethod
    def _ready_graph_evidence(
        cls,
        snapshot: TrustedProjectionSearchSnapshot,
    ) -> GraphRetrievalEvidence:
        if snapshot.generation_id is None or not snapshot.attempt_ids:
            raise KnowledgeInvariantError(
                "trusted graph snapshot is not a ready validated build"
            )

        results: list[GraphRetrievalHit] = []
        for hit in snapshot.results:
            sources: list[GraphSourceCorrelation] = []
            for source in hit.sources:
                if not isinstance(source, GovernedProjectionSourceSegment):
                    raise KnowledgeInvariantError(
                        "trusted source-neutral graph hit lost generic KC correlation"
                    )
                sources.append(cls._source_correlation(source))
            results.append(
                GraphRetrievalHit(
                    provider_hit_id=hit.provider_hit_id,
                    fact=hit.fact,
                    valid_at=hit.valid_at,
                    invalid_at=hit.invalid_at,
                    sources=tuple(sources),
                )
            )

        return GraphRetrievalEvidence(
            state=GraphRetrievalState.READY,
            namespace_key=snapshot.namespace_key,
            scope_key=snapshot.scope_key,
            generation_id=snapshot.generation_id,
            attempt_ids=snapshot.attempt_ids,
            results=tuple(results),
        )

    async def search(
        self,
        *,
        query: str,
        limit: int = 10,
        include_superseded: bool = False,
        authorized_resource_refs_statement=None,
    ) -> UnifiedRetrievalSearchSnapshot:
        # Lexical retrieval is deliberately first and outside every graph-degradation
        # handler. If canonical/text trust fails, unified search fails exactly as the
        # accepted lexical path does; graph data can never mask that failure.
        lexical = self.lexical_kernel.search_text(
            query=query,
            limit=limit,
            include_superseded=include_superseded,
            authorized_resource_refs_statement=authorized_resource_refs_statement,
        )

        binding = self.graph_binding
        if binding is None:
            return self._degraded(
                lexical=lexical,
                state=GraphRetrievalState.DISABLED,
                reason_code="graph-augmentation-not-configured",
                warning_code=UnifiedRetrievalWarningCode.GRAPH_DISABLED,
                warning_message=(
                    "Validated graph augmentation is not configured; lexical evidence remains valid."
                ),
            )

        # The accepted graph path is current-only. Do not mix historical lexical
        # retrieval with current graph evidence or silently reinterpret the request.
        if include_superseded:
            return self._degraded(
                lexical=lexical,
                state=GraphRetrievalState.DISABLED,
                reason_code="graph-augmentation-current-only",
                warning_code=UnifiedRetrievalWarningCode.GRAPH_DISABLED,
                warning_message=(
                    "Graph augmentation is current-only and is disabled for historical lexical retrieval."
                ),
            )

        if lexical.generation_id is None:
            return self._degraded(
                lexical=lexical,
                state=GraphRetrievalState.NO_BUILD,
                reason_code="no-current-text-generation",
                warning_code=UnifiedRetrievalWarningCode.GRAPH_NO_BUILD,
                warning_message=(
                    "No current text generation exists, so no compatible graph evidence can be served."
                ),
            )

        try:
            graph_snapshot = await self.graph_kernel.search_validated_projection(
                adapter=binding.adapter,
                authority_evaluator=binding.authority_evaluator,
                caller_principal_ref=binding.caller_principal_ref,
                namespace_key=binding.namespace_key,
                scope_key=binding.scope_key,
                query=lexical.query,
                limit=limit,
            )

            if graph_snapshot.generation_id != lexical.generation_id:
                return self._degraded(
                    lexical=lexical,
                    state=GraphRetrievalState.STALE,
                    reason_code="text-generation-changed-before-graph-correlation",
                    warning_code=UnifiedRetrievalWarningCode.GRAPH_STALE,
                    warning_message=(
                        "Graph evidence does not match the lexical text generation; lexical evidence remains valid."
                    ),
                )

            if not graph_snapshot.attempt_ids:
                # The trusted-search kernel intentionally returns no attempt IDs when
                # no current compatible *validated* build is available. That does not
                # prove that no stale/pending/unvalidated physical build exists, so do
                # not overstate the public state as ``no_build``. Task 6F may inspect
                # durable attempt evidence later to distinguish those states.
                return self._degraded(
                    lexical=lexical,
                    state=GraphRetrievalState.UNAVAILABLE,
                    reason_code="no-compatible-validated-graph-build",
                    warning_code=UnifiedRetrievalWarningCode.GRAPH_UNAVAILABLE,
                    warning_message=(
                        "No compatible validated graph evidence is available; lexical evidence remains valid."
                    ),
                )

            graph = self._ready_graph_evidence(graph_snapshot)
            return UnifiedRetrievalSearchSnapshot(
                lexical=lexical,
                graph=graph,
            )
        except Exception:
            # The public Task 6B contract is deliberately nondisclosing for graph
            # Authority/provider/integrity failures. Do not leak raw exception text
            # or convert graph-side failure into lexical failure.
            return self._degraded(
                lexical=lexical,
                state=GraphRetrievalState.UNAVAILABLE,
                reason_code="graph-evidence-unavailable",
                warning_code=UnifiedRetrievalWarningCode.GRAPH_UNAVAILABLE,
                warning_message=(
                    "Validated graph evidence is unavailable; lexical evidence remains valid."
                ),
            )
