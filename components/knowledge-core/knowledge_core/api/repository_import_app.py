from __future__ import annotations

from typing import Callable, Mapping

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from knowledge_core.api.app import create_app
from knowledge_core.api.repository_import_schemas import (
    RepositoryImportActionResponse,
    RepositoryImportApplyRequest,
    RepositoryImportPlanRequest,
    RepositoryImportPlanResponse,
    RepositoryImportReceiptResponse,
)
from knowledge_core.application.repository_source import RepositorySourceReader
from knowledge_core.application.section_repository_import import (
    SectionRepositoryImportKnowledgeKernel,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.authority.retrieval import RetrievalAuthorityEvaluator


SessionFactory = Callable[[], Session]


def create_repository_import_app(
    *,
    session_factory: SessionFactory,
    artifact_store: LocalArtifactStore,
    source_readers: Mapping[str, RepositorySourceReader],
    retrieval_authority_evaluator: RetrievalAuthorityEvaluator | None = None,
):
    """Create an explicitly import-capable Knowledge Core service.

    The ordinary create_app() remains retrieval/resource only. Repository access
    exists only when the host injects governed readers into this factory. Live
    repository application uses the SR-2 producer; the older RF-2 importer remains
    available only for historical qualification/reconstruction code paths.
    Retrieval remains fail-closed unless the trusted host also injects an Authority
    evaluator.
    """

    app_kwargs = {
        "session_factory": session_factory,
        "artifact_store": artifact_store,
    }
    if retrieval_authority_evaluator is not None:
        app_kwargs["retrieval_authority_evaluator"] = retrieval_authority_evaluator
    app = create_app(**app_kwargs)

    def get_import_kernel():
        session = session_factory()
        try:
            yield SectionRepositoryImportKnowledgeKernel(
                session,
                artifact_store=artifact_store,
                source_readers=source_readers,
            )
        finally:
            session.close()

    def caller_context(
        x_knowledge_caller: str | None = Header(
            default=None,
            alias="X-Knowledge-Caller",
        ),
    ) -> str:
        if x_knowledge_caller is None or not x_knowledge_caller.strip():
            raise HTTPException(
                status_code=400,
                detail="X-Knowledge-Caller is required for repository import",
            )
        return x_knowledge_caller.strip()

    @app.post(
        "/v1/repository-import/plan",
        response_model=RepositoryImportPlanResponse,
    )
    def plan_repository_import(
        body: RepositoryImportPlanRequest,
        kernel: SectionRepositoryImportKnowledgeKernel = Depends(get_import_kernel),
        _caller: str = Depends(caller_context),
    ) -> RepositoryImportPlanResponse:
        plan = kernel.plan_repository_import(body.manifest)
        return RepositoryImportPlanResponse(
            manifest_digest=plan.manifest_digest,
            previous_manifest_digest=plan.previous_manifest_digest,
            expected_current_generation_id=plan.expected_current_generation_id,
            plan_digest=plan.plan_digest,
            replay=plan.replay_receipt is not None,
            actions=[
                RepositoryImportActionResponse(
                    source_document_key=item.source_document_key,
                    action=item.action,
                    resource_ref=item.resource_ref,
                    resource_version_ref=item.resource_version_ref,
                )
                for item in plan.actions
            ],
        )

    @app.post(
        "/v1/repository-import/apply",
        response_model=RepositoryImportReceiptResponse,
    )
    def apply_repository_import(
        body: RepositoryImportApplyRequest,
        kernel: SectionRepositoryImportKnowledgeKernel = Depends(get_import_kernel),
        _caller: str = Depends(caller_context),
    ) -> RepositoryImportReceiptResponse:
        receipt = kernel.apply_repository_import(
            manifest=body.manifest,
            expected_plan_digest=body.plan_digest,
        )
        return RepositoryImportReceiptResponse(
            manifest_digest=receipt.manifest_digest,
            previous_manifest_digest=receipt.previous_manifest_digest,
            source_repository_key=receipt.source_repository_key,
            source_commit=receipt.source_commit,
            status=receipt.status,
            plan_digest=receipt.plan_digest,
            resulting_text_generation_id=receipt.resulting_text_generation_id,
        )

    return app
