from __future__ import annotations

from sqlalchemy import select

from knowledge_core.application.section_generation import (
    SR2_SEGMENT_MODEL_IDENTITY,
    SR2_SEGMENT_MODEL_VERSION,
)
from knowledge_core.application.source_neutral_graph import (
    SourceNeutralGraphProjectionKnowledgeKernel,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind
from knowledge_core.domain.projection_adapter import ProjectionAdapter
from knowledge_core.domain.projection_evidence import (
    ProjectionDisposition,
    ProjectionValidationState,
)
from knowledge_core.domain.unified_retrieval import (
    GraphRetrievalEvidence,
    GraphRetrievalState,
)
from knowledge_core.storage.projection_models import ProjectionAttempt


_GRAPH_PROJECTION_KIND = "semantic_relationship_graph"
_GRAPH_TARGET_KIND = "sr2_segment_relationship_graph"


def _bounded_attempt_ids(rows: list[ProjectionAttempt]) -> tuple:
    """Expose one representative durable attempt, not unbounded history."""

    if not rows:
        return ()
    return (rows[0].attempt_id,)


def disabled_graph_readiness() -> GraphRetrievalEvidence:
    return GraphRetrievalEvidence(
        state=GraphRetrievalState.DISABLED,
        reason_code="graph-augmentation-not-configured",
    )


def unavailable_graph_readiness(*, namespace_key: str, scope_key: str) -> GraphRetrievalEvidence:
    return GraphRetrievalEvidence(
        state=GraphRetrievalState.UNAVAILABLE,
        namespace_key=namespace_key,
        scope_key=scope_key,
        reason_code="graph-readiness-unavailable",
    )


def inspect_source_neutral_graph_readiness(
    *,
    kernel: SourceNeutralGraphProjectionKnowledgeKernel,
    adapter: ProjectionAdapter,
    namespace_key: str,
    scope_key: str,
) -> GraphRetrievalEvidence:
    """Classify graph readiness from KC durable evidence only.

    This function never queries Graphiti/FalkorDB, never calls the adapter search or
    projection methods, and never starts a model. It reads the adapter descriptor plus
    KC's projection/validation ledger and compares that evidence with the current
    source-neutral SR-2 graph profile.
    """

    namespace_key = namespace_key.strip()
    scope_key = scope_key.strip()
    if not namespace_key or not scope_key:
        raise KnowledgeInvariantError(
            "graph readiness requires explicit namespace and scope"
        )

    descriptor = adapter.descriptor
    backend_identity = descriptor.backend_identity.strip()
    config_digest = descriptor.config_digest.strip()
    if not backend_identity or not config_digest:
        raise KnowledgeInvariantError(
            "graph readiness requires a complete adapter descriptor"
        )

    rows = list(
        kernel.session.scalars(
            select(ProjectionAttempt)
            .where(
                ProjectionAttempt.projection_kind == _GRAPH_PROJECTION_KIND,
                ProjectionAttempt.target_kind == _GRAPH_TARGET_KIND,
                ProjectionAttempt.namespace_key == namespace_key,
                ProjectionAttempt.scope_key == scope_key,
                ProjectionAttempt.backend_identity == backend_identity,
            )
            .order_by(ProjectionAttempt.started_at.desc(), ProjectionAttempt.attempt_id.desc())
        ).all()
    )

    if not rows:
        return GraphRetrievalEvidence(
            state=GraphRetrievalState.NO_BUILD,
            namespace_key=namespace_key,
            scope_key=scope_key,
            reason_code="no-graph-build-recorded",
        )

    current = kernel.current_generation(derived_kind=DerivedKind.TEXT)
    if (
        current is None
        or current.model_identity != SR2_SEGMENT_MODEL_IDENTITY
        or current.model_version != SR2_SEGMENT_MODEL_VERSION
        or current.config_digest is None
    ):
        return GraphRetrievalEvidence(
            state=GraphRetrievalState.STALE,
            namespace_key=namespace_key,
            scope_key=scope_key,
            generation_id=current.generation_id if current is not None else None,
            attempt_ids=_bounded_attempt_ids(rows),
            reason_code="no-current-compatible-text-generation",
        )

    expected_profile_id, expected_profile_digest = (
        kernel.graph_projection_profile_identity(current)
    )
    compatible = [
        row
        for row in rows
        if row.backend_version == descriptor.backend_version
        and row.profile_id == expected_profile_id
        and row.profile_digest == expected_profile_digest
        and row.config_digest == config_digest
    ]

    if not compatible:
        return GraphRetrievalEvidence(
            state=GraphRetrievalState.STALE,
            namespace_key=namespace_key,
            scope_key=scope_key,
            generation_id=current.generation_id,
            attempt_ids=_bounded_attempt_ids(rows),
            reason_code="no-current-compatible-graph-build",
        )

    requirement = descriptor.validation_requirement
    ready: list[ProjectionAttempt] = []
    for row in compatible:
        if (
            row.disposition == ProjectionDisposition.SUCCEEDED.value
            and row.validation_state == ProjectionValidationState.VALIDATED.value
        ):
            if requirement is None or kernel.projection_satisfies_validation_requirement(
                attempt_id=row.attempt_id,
                requirement=requirement,
            ):
                ready.append(row)

    if ready:
        return GraphRetrievalEvidence(
            state=GraphRetrievalState.READY,
            namespace_key=namespace_key,
            scope_key=scope_key,
            generation_id=current.generation_id,
            attempt_ids=_bounded_attempt_ids(ready),
        )

    pending = [
        row
        for row in compatible
        if row.disposition == ProjectionDisposition.PENDING.value
    ]
    if pending:
        return GraphRetrievalEvidence(
            state=GraphRetrievalState.PENDING,
            namespace_key=namespace_key,
            scope_key=scope_key,
            generation_id=current.generation_id,
            attempt_ids=_bounded_attempt_ids(pending),
            reason_code="current-compatible-graph-build-pending",
        )

    unvalidated = [
        row
        for row in compatible
        if row.disposition == ProjectionDisposition.SUCCEEDED.value
        and row.validation_state
        in (
            ProjectionValidationState.UNVALIDATED.value,
            ProjectionValidationState.VALIDATED.value,
        )
    ]
    if unvalidated:
        return GraphRetrievalEvidence(
            state=GraphRetrievalState.UNVALIDATED,
            namespace_key=namespace_key,
            scope_key=scope_key,
            generation_id=current.generation_id,
            attempt_ids=_bounded_attempt_ids(unvalidated),
            reason_code="current-compatible-graph-build-unvalidated",
        )

    return GraphRetrievalEvidence(
        state=GraphRetrievalState.FAILED,
        namespace_key=namespace_key,
        scope_key=scope_key,
        generation_id=current.generation_id,
        attempt_ids=_bounded_attempt_ids(compatible),
        reason_code="current-compatible-graph-build-failed",
    )
