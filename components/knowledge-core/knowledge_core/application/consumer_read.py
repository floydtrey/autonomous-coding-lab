from __future__ import annotations

from hashlib import sha256
from uuid import UUID

from knowledge_core.application.retrieval import RetrievalServiceKnowledgeKernel
from knowledge_core.application.section_generation import (
    SR2_SEGMENT_MODEL_IDENTITY,
    SR2_SEGMENT_MODEL_VERSION,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind, GenerationSnapshot
from knowledge_core.domain.retrieval import (
    CurrentSourceSnapshot,
    KnowledgeSourceUnavailableError,
    LEXICAL_EVIDENCE_CONTRACT_VERSION,
    RetrievalStatusSnapshot,
    TextReadinessState,
)
from knowledge_core.storage.resource_models import ResourceVersion
from knowledge_core.storage.section_retrieval_models import TextGenerationProfile


class ConsumerReadKnowledgeKernel(RetrievalServiceKnowledgeKernel):
    """Usable V1 read operations over the accepted lexical evidence boundary.

    This is deliberately a small consumer seam. Search remains the Task 2 lexical
    implementation; source follow-through returns only an exact ResourceVersion that
    belongs to the current TEXT generation and remains serving-eligible. No database,
    artifact-path, or provider credentials cross this boundary.
    """

    def _current_text_contract(
        self,
    ) -> tuple[GenerationSnapshot | None, str | None, str | None]:
        current = self._generation_kernel().current_generation(
            derived_kind=DerivedKind.TEXT
        )
        if current is None:
            return None, None, None

        if (
            current.model_identity == SR2_SEGMENT_MODEL_IDENTITY
            and current.model_version == SR2_SEGMENT_MODEL_VERSION
        ):
            profile = self.session.get(TextGenerationProfile, current.generation_id)
            if profile is None:
                raise KnowledgeInvariantError(
                    "current SR-2 generation is missing recoverable profile identity"
                )
            if profile.generation_config_digest != current.config_digest:
                raise KnowledgeInvariantError(
                    "current SR-2 generation config/profile identity mismatch"
                )
            lineage_mode, _sources = self._resolve_sr2_lineage(current=current)
            return current, "segment", lineage_mode

        if (
            current.model_identity == "postgresql-full-text"
            and current.model_version == "rf2-v1"
        ):
            return current, "resource_version", "rf2-v1"

        raise KnowledgeInvariantError(
            "current text generation has an unsupported retrieval implementation identity"
        )

    def read_current_source(
        self,
        *,
        resource_version_ref: UUID,
    ) -> CurrentSourceSnapshot:
        """Return exact canonical UTF-8 source bytes for a current retrieval source."""

        self._require_postgresql_retrieval()
        current, retrieval_mode, lineage_mode = self._current_text_contract()
        if current is None or retrieval_mode is None or lineage_mode is None:
            raise KnowledgeSourceUnavailableError("knowledge source is unavailable")

        current_refs = {source.source_ref for source in current.sources}
        if resource_version_ref not in current_refs:
            raise KnowledgeSourceUnavailableError("knowledge source is unavailable")

        version = self.session.get(ResourceVersion, resource_version_ref)
        if version is None:
            raise KnowledgeInvariantError(
                "current text generation references a missing ResourceVersion"
            )
        if not self.resource_version_serving_eligible(resource_version_ref):
            raise KnowledgeSourceUnavailableError("knowledge source is unavailable")
        if version.content_digest_algo != "sha256":
            raise KnowledgeInvariantError(
                "Usable V1 source retrieval supports only SHA-256 ResourceVersions"
            )

        content = self.artifact_store.read_bytes(version.artifact_key)
        if len(content) != int(version.byte_size):
            raise KnowledgeInvariantError(
                "resource version byte size does not match immutable artifact"
            )
        if sha256(content).hexdigest() != version.content_digest:
            raise KnowledgeInvariantError(
                "resource version digest does not match immutable artifact"
            )
        try:
            text = content.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise KnowledgeInvariantError(
                "current text source is not strict UTF-8"
            ) from exc

        return CurrentSourceSnapshot(
            generation_id=current.generation_id,
            source_revision_highwater=current.source_revision_highwater,
            retrieval_mode=retrieval_mode,
            lineage_mode=lineage_mode,
            evidence_contract_version=LEXICAL_EVIDENCE_CONTRACT_VERSION,
            generation_config_digest=current.config_digest,
            resource_ref=version.resource_ref_id,
            resource_version_ref=version.ref_id,
            content_digest_algo=version.content_digest_algo,
            content_digest=version.content_digest,
            byte_size=int(version.byte_size),
            media_type=version.media_type,
            content=text,
        )

    def retrieval_status(self) -> RetrievalStatusSnapshot:
        """Return bounded canonical/text readiness without backend implementation detail."""

        self._require_postgresql_retrieval()
        current, retrieval_mode, lineage_mode = self._current_text_contract()
        if current is None:
            return RetrievalStatusSnapshot(
                canonical_revision=self.current_revision(),
                text_state=TextReadinessState.EMPTY,
                text_generation_id=None,
                text_source_revision_highwater=None,
                text_source_count=0,
                retrieval_mode=None,
                lineage_mode=None,
                evidence_contract_version=LEXICAL_EVIDENCE_CONTRACT_VERSION,
                generation_config_digest=None,
            )

        return RetrievalStatusSnapshot(
            canonical_revision=self.current_revision(),
            text_state=TextReadinessState.READY,
            text_generation_id=current.generation_id,
            text_source_revision_highwater=current.source_revision_highwater,
            text_source_count=len(current.sources),
            retrieval_mode=retrieval_mode,
            lineage_mode=lineage_mode,
            evidence_contract_version=LEXICAL_EVIDENCE_CONTRACT_VERSION,
            generation_config_digest=current.config_digest,
        )
