from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, inspect, select

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapContract, BootstrapOperation
from knowledge_core.api.memory_candidate_schemas import MemoryCandidateProposalRequest
from knowledge_core.application.memory_candidates import (
    MAX_MEMORY_CANDIDATE_BYTES,
    MemoryCandidateKnowledgeKernel,
    memory_candidate_operation_id,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.authority.memory import (
    MemoryCandidateReviewDecision,
    MemoryCandidateReviewOutcome,
    MemoryCandidateReviewUnavailableError,
)
from knowledge_core.authority.store import (
    CanonicalStoreAuthorityDecision,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.memory_candidates import MemoryCandidateState
from knowledge_core.domain.operations import OperationReuseError
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.generation_models import DerivedGeneration
from knowledge_core.storage.memory_candidate_models import MemoryCandidateRecord
from knowledge_core.storage.models import Revision
from knowledge_core.storage.resource_models import ResourceVersion


_BOOTSTRAP_KEY = "task6g-bootstrap-key"
_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)


class _ApproveEvaluator:
    def evaluate_memory_candidate(self, request):
        return MemoryCandidateReviewDecision(
            outcome=MemoryCandidateReviewOutcome.APPROVE_FOR_STORE,
            decision_ref=f"review:{request.candidate_id}",
            reason_code="explicit-review-approved",
        )


class _RejectEvaluator:
    def evaluate_memory_candidate(self, request):
        return MemoryCandidateReviewDecision(
            outcome=MemoryCandidateReviewOutcome.REJECT,
            decision_ref=f"review:{request.candidate_id}",
            reason_code="explicit-review-rejected",
        )


class _CaptureStoreEvaluator:
    def __init__(self):
        self.requests = []

    def evaluate_canonical_store(self, request):
        self.requests.append(request)
        return CanonicalStoreAuthorityDecision(
            allowed=True,
            decision_ref=f"explicit-store:{request.operation_id}",
            reason_code="explicit-user-directed-store",
        )


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("PostgreSQL qualification URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("memory candidate qualification requires PostgreSQL")
    return engine


def _truncate_kernel_tables(engine) -> None:
    inspector = inspect(engine)
    preparer = engine.dialect.identifier_preparer
    tables: list[str] = []
    for schema in ("kc", "kc_control", "kc_derived"):
        for table_name in inspector.get_table_names(schema=schema):
            tables.append(
                f"{preparer.quote_schema(schema)}.{preparer.quote(table_name)}"
            )
    if not tables:
        raise AssertionError("Knowledge Core schemas are not migrated")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "TRUNCATE TABLE " + ", ".join(tables) + " RESTART IDENTITY CASCADE"
        )


def _admission(*, allowed_operations=None) -> BootstrapAdmission:
    return BootstrapAdmission(
        contract=BootstrapContract(
            allowed_operations=(
                frozenset(BootstrapOperation)
                if allowed_operations is None
                else frozenset(allowed_operations)
            )
        ),
        api_key=_BOOTSTRAP_KEY,
    )


def test_memory_candidate_operation_identity_is_deterministic_and_separate():
    first = memory_candidate_operation_id(
        principal_ref="local_owner",
        idempotency_key="candidate-1",
    )
    second = memory_candidate_operation_id(
        principal_ref="local_owner",
        idempotency_key="candidate-1",
    )
    different = memory_candidate_operation_id(
        principal_ref="local_owner",
        idempotency_key="candidate-2",
    )
    assert first == second
    assert first != different


def test_memory_candidate_schema_enforces_utf8_byte_bound():
    MemoryCandidateProposalRequest(
        content="x" * MAX_MEMORY_CANDIDATE_BYTES,
        project="knowledge-core",
        proposer_ref="mason",
    )
    with pytest.raises(ValidationError):
        MemoryCandidateProposalRequest(
            content="é" * (MAX_MEMORY_CANDIDATE_BYTES // 2 + 1),
            project="knowledge-core",
            proposer_ref="mason",
        )


@pytest.mark.postgresql
def test_proposal_and_review_remain_noncanonical_until_explicit_store():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    sessions = create_session_factory(engine)
    try:
        with sessions() as session:
            kernel = MemoryCandidateKnowledgeKernel(session)
            proposal_id = memory_candidate_operation_id(
                principal_ref="local_owner",
                idempotency_key="proposal-1",
            )
            candidate = kernel.propose_candidate(
                operation_id=proposal_id,
                caller_principal_ref="local_owner",
                proposer_ref="mason",
                project_key="knowledge-core",
                content="Remember that graph readiness is derived from the KC ledger.",
            )
            assert candidate.state is MemoryCandidateState.PENDING
            assert candidate.candidate_id == proposal_id
            assert kernel.current_revision() == 0
            assert session.scalar(select(func.count()).select_from(Revision)) == 0
            assert session.scalar(select(func.count()).select_from(ResourceVersion)) == 0
            assert session.scalar(select(func.count()).select_from(DerivedGeneration)) == 0

            replay = kernel.propose_candidate(
                operation_id=proposal_id,
                caller_principal_ref="local_owner",
                proposer_ref="mason",
                project_key="knowledge-core",
                content="Remember that graph readiness is derived from the KC ledger.",
            )
            assert replay == candidate

            with pytest.raises(OperationReuseError):
                kernel.propose_candidate(
                    operation_id=proposal_id,
                    caller_principal_ref="local_owner",
                    proposer_ref="mason",
                    project_key="knowledge-core",
                    content="Different content must not reuse the proposal identity.",
                )

            with pytest.raises(MemoryCandidateReviewUnavailableError):
                kernel.review_candidate(
                    operation_id=uuid4(),
                    candidate_id=candidate.candidate_id,
                    reviewer_principal_ref="local_owner",
                    evaluator=None,
                )
            assert kernel.read_candidate(candidate.candidate_id).state is MemoryCandidateState.PENDING

            review_operation_id = uuid4()
            approved = kernel.review_candidate(
                operation_id=review_operation_id,
                candidate_id=candidate.candidate_id,
                reviewer_principal_ref="local_owner",
                evaluator=_ApproveEvaluator(),
            )
            assert approved.state is MemoryCandidateState.APPROVED
            assert approved.review_operation_id == review_operation_id
            assert approved.review_decision_ref == f"review:{candidate.candidate_id}"

            replay_review = kernel.review_candidate(
                operation_id=review_operation_id,
                candidate_id=candidate.candidate_id,
                reviewer_principal_ref="local_owner",
                evaluator=_ApproveEvaluator(),
            )
            assert replay_review == approved

            # Approval is eligibility only. It does not invoke kc_store or create
            # canonical/retrieval state on the worker's behalf.
            assert kernel.current_revision() == 0
            assert session.scalar(select(func.count()).select_from(Revision)) == 0
            assert session.scalar(select(func.count()).select_from(ResourceVersion)) == 0
            assert session.scalar(select(func.count()).select_from(DerivedGeneration)) == 0
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


@pytest.mark.postgresql
def test_rejection_is_durable_and_cannot_be_re_reviewed_by_another_operation():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    sessions = create_session_factory(engine)
    try:
        with sessions() as session:
            kernel = MemoryCandidateKnowledgeKernel(session)
            candidate = kernel.propose_candidate(
                operation_id=uuid4(),
                caller_principal_ref="local_owner",
                proposer_ref="mason",
                project_key="knowledge-core",
                content="Candidate that should be rejected.",
            )
            rejected = kernel.review_candidate(
                operation_id=uuid4(),
                candidate_id=candidate.candidate_id,
                reviewer_principal_ref="local_owner",
                evaluator=_RejectEvaluator(),
            )
            assert rejected.state is MemoryCandidateState.REJECTED
            assert session.get(MemoryCandidateRecord, candidate.candidate_id).state == "rejected"

            with pytest.raises(KnowledgeInvariantError, match="already reviewed"):
                kernel.review_candidate(
                    operation_id=uuid4(),
                    candidate_id=candidate.candidate_id,
                    reviewer_principal_ref="local_owner",
                    evaluator=_ApproveEvaluator(),
                )
            assert session.scalar(select(func.count()).select_from(ResourceVersion)) == 0
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


@pytest.mark.postgresql
def test_memory_candidate_endpoint_returns_pending_without_canonical_storage(tmp_path: Path):
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    sessions = create_session_factory(engine)
    try:
        app = create_app(
            session_factory=sessions,
            artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
            bootstrap_admission=_admission(),
        )
        with TestClient(app) as client:
            response = client.post(
                "/v1/kc/memory-candidates",
                headers={
                    "X-Knowledge-Key": _BOOTSTRAP_KEY,
                    "Idempotency-Key": "api-proposal-1",
                },
                json={
                    "content": "Autonomous observation proposed for later review.",
                    "project": "knowledge-core",
                    "proposer_ref": "mason",
                },
            )
        assert response.status_code == 202, response.text
        payload = response.json()
        assert payload["state"] == "pending"
        assert payload["canonical_state"] == "not_stored"
        assert payload["proposer_ref"] == "mason"

        with sessions() as session:
            assert session.get(MemoryCandidateRecord, UUID(payload["candidate_id"])) is not None
            assert session.scalar(select(func.count()).select_from(Revision)) == 0
            assert session.scalar(select(func.count()).select_from(ResourceVersion)) == 0
            assert session.scalar(select(func.count()).select_from(DerivedGeneration)) == 0
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


@pytest.mark.postgresql
def test_memory_candidate_endpoint_can_be_scoped_out_of_bootstrap_contract(tmp_path: Path):
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    sessions = create_session_factory(engine)
    try:
        app = create_app(
            session_factory=sessions,
            artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
            bootstrap_admission=_admission(allowed_operations={BootstrapOperation.STATUS}),
        )
        with TestClient(app) as client:
            response = client.post(
                "/v1/kc/memory-candidates",
                headers={
                    "X-Knowledge-Key": _BOOTSTRAP_KEY,
                    "Idempotency-Key": "api-proposal-denied",
                },
                json={
                    "content": "This proposal operation is not allowed.",
                    "project": "knowledge-core",
                    "proposer_ref": "mason",
                },
            )
        assert response.status_code == 403
        with sessions() as session:
            assert session.scalar(select(func.count()).select_from(MemoryCandidateRecord)) == 0
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


@pytest.mark.postgresql
def test_kc_store_fails_closed_without_exact_store_authority(tmp_path: Path):
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    sessions = create_session_factory(engine)
    try:
        app = create_app(
            session_factory=sessions,
            artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
            bootstrap_admission=_admission(),
            canonical_store_authority_evaluator=None,
        )
        with TestClient(app) as client:
            response = client.post(
                "/v1/kc/store",
                headers={
                    "X-Knowledge-Key": _BOOTSTRAP_KEY,
                    "Idempotency-Key": "unauthorized-store",
                },
                json={
                    "content": "This must not become canonical without exact authority.",
                    "project": "knowledge-core",
                    "source_type": "user_note",
                },
            )
        assert response.status_code == 503
        assert response.json()["error_code"] == "CANONICAL_STORE_AUTHORITY_UNAVAILABLE"
        with sessions() as session:
            assert session.scalar(select(func.count()).select_from(Revision)) == 0
            assert session.scalar(select(func.count()).select_from(ResourceVersion)) == 0
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


@pytest.mark.postgresql
def test_explicit_exact_store_authority_preserves_user_directed_kc_store(tmp_path: Path):
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    sessions = create_session_factory(engine)
    evaluator = _CaptureStoreEvaluator()
    content = "Explicit user-directed canonical memory."
    try:
        app = create_app(
            session_factory=sessions,
            artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
            bootstrap_admission=_admission(),
            canonical_store_authority_evaluator=evaluator,
        )
        with TestClient(app) as client:
            response = client.post(
                "/v1/kc/store",
                headers={
                    "X-Knowledge-Key": _BOOTSTRAP_KEY,
                    "Idempotency-Key": "explicit-store",
                },
                json={
                    "content": content,
                    "project": "knowledge-core",
                    "source_type": "user_note",
                    "source_id": "explicit-store-note",
                },
            )
        assert response.status_code == 201, response.text
        assert len(evaluator.requests) == 1
        request = evaluator.requests[0]
        assert request.caller_principal_ref == "local_owner"
        assert request.project_key == "knowledge-core"
        assert request.source_id == "explicit-store-note"
        assert request.content_sha256 == sha256(content.encode("utf-8")).hexdigest()
        with sessions() as session:
            assert session.scalar(select(func.count()).select_from(ResourceVersion)) == 1
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()
