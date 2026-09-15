from __future__ import annotations

from knowledge_core.application.repository_governed_producer import (
    RepositoryGovernedProducerKnowledgeKernel,
)
from knowledge_core.application.repository_import import (
    RepositoryImportKnowledgeKernel,
    _receipt_snapshot,
)
from knowledge_core.application.section_publication_v2 import (
    SourceNeutralSectionPublicationKnowledgeKernel,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.resources import ResourceLocatorKind
from knowledge_core.storage.repository_import_models import (
    RepositoryDocumentBinding,
    RepositoryImportReceipt,
)


class SectionRepositoryImportKnowledgeKernel(RepositoryImportKnowledgeKernel):
    """Verified repository producer with source-neutral SR-2 publication."""

    def _section_publication_kernel(
        self,
    ) -> SourceNeutralSectionPublicationKnowledgeKernel:
        return SourceNeutralSectionPublicationKnowledgeKernel(
            self.session,
            artifact_store=self.artifact_store,
        )

    def _repository_governed_producer(
        self,
    ) -> RepositoryGovernedProducerKnowledgeKernel:
        return RepositoryGovernedProducerKnowledgeKernel(self.session)

    def apply_repository_import(
        self,
        *,
        manifest: dict,
        expected_plan_digest: str,
        before_publish_hook=None,
    ):
        """Preserve RI-2 verification while publishing one complete generic corpus."""

        plan = self.plan_repository_import(manifest)
        if plan.replay_receipt is not None:
            if expected_plan_digest != plan.plan_digest:
                raise KnowledgeInvariantError(
                    "plan digest does not match accepted replay"
                )
            return plan.replay_receipt
        if expected_plan_digest != plan.plan_digest:
            raise KnowledgeInvariantError(
                "repository import plan is stale or unapproved"
            )

        receipt = self._ensure_receipt(plan)
        if receipt.status == "settled":
            return _receipt_snapshot(receipt)

        foundation = self.bootstrap_resource_test_profile()
        proof_by_path = {proof.path: proof for proof in plan.source_proofs}
        action_by_key = {
            action.source_document_key: action for action in plan.actions
        }
        try:
            for entry in plan.manifest["entries"]:
                key = entry["source_document_key"]
                proof = proof_by_path[entry["path"]]
                action = action_by_key[key]
                binding = self._binding(
                    plan.manifest["source_repository_key"],
                    key,
                )
                if binding is None:
                    resource = self.create_resource(
                        kind_revision_ref=foundation.artifact_kind_revision_ref
                    )
                    binding = RepositoryDocumentBinding(
                        source_repository_key=plan.manifest[
                            "source_repository_key"
                        ],
                        source_document_key=key,
                        resource_ref=resource.resource_ref,
                    )
                    self.session.add(binding)
                    self._commit()

                version = self._matching_version(
                    binding.resource_ref,
                    proof.content,
                )
                if version is None:
                    snapshot = self.ingest_resource_version(
                        resource_ref=binding.resource_ref,
                        content=proof.content,
                        ingestion_kind_revision_ref=(
                            foundation.resource_ingestion_kind_revision_ref
                        ),
                        media_type=entry["media_type"],
                        locator_kind=ResourceLocatorKind.PATH,
                        locator_text=entry["path"],
                    )
                    version_ref = snapshot.resource_version_ref
                else:
                    if action.action == "add_locator":
                        snapshot = self.ingest_resource_version(
                            resource_ref=binding.resource_ref,
                            content=proof.content,
                            ingestion_kind_revision_ref=(
                                foundation.resource_ingestion_kind_revision_ref
                            ),
                            media_type=entry["media_type"],
                            locator_kind=ResourceLocatorKind.PATH,
                            locator_text=entry["path"],
                        )
                        version_ref = snapshot.resource_version_ref
                    else:
                        version_ref = version.ref_id
                self._record_observation(
                    plan=plan,
                    entry=entry,
                    resource_ref=binding.resource_ref,
                    resource_version_ref=version_ref,
                )

            if before_publish_hook is not None:
                before_publish_hook()

            publication = self._section_publication_kernel()
            expected_predecessor = publication.current_serving_snapshot_digest()
            governed_snapshot = self._repository_governed_producer().prepare_complete_snapshot(
                governing_manifest_digest=plan.manifest_digest,
                expected_predecessor_snapshot_digest=expected_predecessor,
            )
            publication.stale_unpublished_candidates_for_snapshot(
                governing_snapshot_digest=governed_snapshot.digest
            )
            candidate = publication.build_segment_generation_candidate(
                governing_snapshot_digest=governed_snapshot.digest
            )
            publication.promote_segment_generation(
                generation_id=candidate.generation_id,
                governing_snapshot_digest=governed_snapshot.digest,
                expected_predecessor_snapshot_digest=expected_predecessor,
                commit_transaction=False,
            )

            receipt = self.session.get(
                RepositoryImportReceipt,
                plan.manifest_digest,
            )
            if receipt is None or receipt.status != "applying":
                raise KnowledgeInvariantError(
                    "repository receipt changed before source-neutral settlement"
                )
            receipt.status = "settled"
            receipt.resulting_text_generation_id = candidate.generation_id
            receipt.settled_at = self._now()
            self._commit()
            return _receipt_snapshot(receipt)
        except Exception:
            self.session.rollback()
            receipt = self.session.get(
                RepositoryImportReceipt,
                plan.manifest_digest,
            )
            if receipt is not None and receipt.status != "settled":
                receipt.status = "failed"
                self._commit()
            raise
