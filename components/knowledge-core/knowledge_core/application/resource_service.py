from __future__ import annotations

from hashlib import sha256
from uuid import UUID

from knowledge_core.application.resources import ResourceKnowledgeKernel
from knowledge_core.application.service import ServiceKnowledgeKernel
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.deletion import KnowledgeRestrictedError
from knowledge_core.domain.resources import (
    EvidenceTrace,
    ImpactTrace,
    ResourceLocatorKind,
    ResourceSnapshot,
    ResourceVersionSnapshot,
)
from knowledge_core.storage.resource_models import ProvenanceLink, Resource


class ResourceServiceKnowledgeKernel(ServiceKnowledgeKernel):
    """Task 10 service-safe resource/provenance operations.

    The lower-level Task 4 resource methods remain available internally. This layer
    adds Task 3 operation semantics and Task 6 serving-fence enforcement required
    before those operations are exposed over HTTP.
    """

    def _read_resource_raw(self, resource_ref: UUID) -> ResourceSnapshot:
        row = self.session.get(Resource, resource_ref)
        if row is None:
            raise KnowledgeInvariantError(f"unknown resource: {resource_ref}")
        return ResourceSnapshot(
            resource_ref=row.ref_id,
            kind_revision_ref=row.kind_revision_ref,
            created_revision_id=row.created_revision_id,
        )

    def read_resource_serving(self, resource_ref: UUID) -> ResourceSnapshot:
        if not self._direct_ref_serving_eligible(resource_ref):
            raise KnowledgeRestrictedError(
                f"resource is unavailable to serving reads: {resource_ref}"
            )
        return self._read_resource_raw(resource_ref)

    def _require_serving_resource(self, resource_ref: UUID) -> None:
        self.read_resource_serving(resource_ref)

    def create_resource_operation(
        self,
        *,
        operation_id: UUID,
        kind_revision_ref: UUID,
        caller_principal_ref: str,
        expected_revision: int | None = None,
    ) -> ResourceSnapshot:
        payload = {"kind_revision_ref": str(kind_revision_ref)}

        def action() -> ResourceSnapshot:
            self._require_active_ref(kind_revision_ref)
            return ResourceKnowledgeKernel.create_resource(
                self,
                kind_revision_ref=kind_revision_ref,
            )

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="create_resource",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=expected_revision,
            action=action,
            encode_result=lambda result: {"resource_ref": str(result.resource_ref)},
            replay=lambda metadata: self._read_resource_raw(
                UUID(str(metadata["resource_ref"]))
            ),
        )

    def ingest_resource_version_operation(
        self,
        *,
        operation_id: UUID,
        resource_ref: UUID,
        content: bytes,
        ingestion_kind_revision_ref: UUID,
        caller_principal_ref: str,
        media_type: str | None = None,
        locator_kind: ResourceLocatorKind | None = None,
        locator_text: str | None = None,
        expected_revision: int | None = None,
    ) -> ResourceVersionSnapshot:
        payload = {
            "resource_ref": str(resource_ref),
            "content_sha256": sha256(content).hexdigest(),
            "content_size": len(content),
            "ingestion_kind_revision_ref": str(ingestion_kind_revision_ref),
            "media_type": media_type,
            "locator_kind": locator_kind.value if locator_kind is not None else None,
            "locator_text": locator_text,
        }

        def action() -> ResourceVersionSnapshot:
            self._require_serving_resource(resource_ref)
            self._require_active_ref(ingestion_kind_revision_ref)
            return ResourceKnowledgeKernel.ingest_resource_version(
                self,
                resource_ref=resource_ref,
                content=content,
                ingestion_kind_revision_ref=ingestion_kind_revision_ref,
                media_type=media_type,
                locator_kind=locator_kind,
                locator_text=locator_text,
            )

        # Exact duplicate re-ingest with no new locator is a valid semantic no-op.
        # The operation ledger must settle and replay it without fabricating a
        # canonical revision solely to satisfy retry bookkeeping.
        return self._execute_operation(
            operation_id=operation_id,
            operation_class="ingest_resource_version",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=expected_revision,
            action=action,
            encode_result=lambda result: {
                "resource_version_ref": str(result.resource_version_ref)
            },
            replay=lambda metadata: ResourceKnowledgeKernel.read_resource_version(
                self,
                UUID(str(metadata["resource_version_ref"])),
            ),
            allow_no_canonical_revision=True,
        )

    def _read_evidence_raw(self, link_id: UUID) -> EvidenceTrace:
        row = self.session.get(ProvenanceLink, link_id)
        if row is None:
            raise KnowledgeInvariantError(f"unknown provenance link: {link_id}")
        version = ResourceKnowledgeKernel.read_resource_version(self, row.target_ref_id)
        return EvidenceTrace(
            link_id=row.link_id,
            assertion_ref=row.source_ref_id,
            relation_revision_ref=row.relation_revision_ref,
            resource_version=version,
            activity_occurrence_ref=row.activity_occurrence_ref,
            created_revision_id=row.created_revision_id,
        )

    def read_evidence_serving(self, link_id: UUID) -> EvidenceTrace:
        trace = self._read_evidence_raw(link_id)
        if not self.assertion_serving_eligible(trace.assertion_ref):
            raise KnowledgeRestrictedError(
                f"evidence assertion is unavailable: {trace.assertion_ref}"
            )
        if not self.resource_version_serving_eligible(
            trace.resource_version.resource_version_ref
        ):
            raise KnowledgeRestrictedError(
                "evidence resource version is unavailable"
            )
        return trace

    def link_assertion_evidence_operation(
        self,
        *,
        operation_id: UUID,
        assertion_ref: UUID,
        resource_version_ref: UUID,
        relation_revision_ref: UUID,
        caller_principal_ref: str,
        expected_revision: int | None = None,
    ) -> EvidenceTrace:
        payload = {
            "assertion_ref": str(assertion_ref),
            "resource_version_ref": str(resource_version_ref),
            "relation_revision_ref": str(relation_revision_ref),
        }

        def action() -> EvidenceTrace:
            if not self.assertion_serving_eligible(assertion_ref):
                raise KnowledgeRestrictedError(
                    f"assertion is unavailable to serving mutations: {assertion_ref}"
                )
            if not self.resource_version_serving_eligible(resource_version_ref):
                raise KnowledgeRestrictedError(
                    f"resource version is unavailable to serving mutations: {resource_version_ref}"
                )
            self._require_active_ref(relation_revision_ref)
            return ResourceKnowledgeKernel.link_assertion_evidence(
                self,
                assertion_ref=assertion_ref,
                resource_version_ref=resource_version_ref,
                relation_revision_ref=relation_revision_ref,
            )

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="link_assertion_evidence",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=expected_revision,
            action=action,
            encode_result=lambda result: {"link_id": str(result.link_id)},
            replay=lambda metadata: self._read_evidence_raw(
                UUID(str(metadata["link_id"]))
            ),
        )

    def explain_assertion_serving(self, *, assertion_ref: UUID) -> list[EvidenceTrace]:
        if not self.assertion_serving_eligible(assertion_ref):
            raise KnowledgeRestrictedError(
                f"assertion is unavailable to explanation: {assertion_ref}"
            )
        traces = ResourceKnowledgeKernel.explain_assertion(
            self,
            assertion_ref=assertion_ref,
        )
        return [
            trace
            for trace in traces
            if self.resource_version_serving_eligible(
                trace.resource_version.resource_version_ref
            )
        ]

    def impact_from_resource_version_serving(
        self,
        *,
        resource_version_ref: UUID,
    ) -> list[ImpactTrace]:
        if not self.resource_version_serving_eligible(resource_version_ref):
            raise KnowledgeRestrictedError(
                f"resource version is unavailable to impact reads: {resource_version_ref}"
            )
        impact = ResourceKnowledgeKernel.impact_from_resource_version(
            self,
            resource_version_ref=resource_version_ref,
        )
        result: list[ImpactTrace] = []
        for item in impact:
            if item.dependent_ref_kind == "assertion":
                if self.assertion_serving_eligible(item.dependent_ref):
                    result.append(item)
            elif self._direct_ref_serving_eligible(item.dependent_ref):
                result.append(item)
        return result
