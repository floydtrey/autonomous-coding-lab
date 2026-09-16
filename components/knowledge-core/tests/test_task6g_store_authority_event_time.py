from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapContract
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.authority.store import CanonicalStoreAuthorityDecision


class _Session:
    def close(self) -> None:
        pass


class _CaptureDeniedEvaluator:
    def __init__(self) -> None:
        self.requests = []

    def evaluate_canonical_store(self, request):
        self.requests.append(request)
        return CanonicalStoreAuthorityDecision(
            allowed=False,
            decision_ref="store-review:denied",
            reason_code="test-stop-before-canonical-write",
        )


def test_kc_store_authority_binds_source_event_time_before_any_write(tmp_path):
    evaluator = _CaptureDeniedEvaluator()
    admission = BootstrapAdmission(
        contract=BootstrapContract(),
        api_key="task6g-exact-write-key",
    )
    event_time = datetime(2026, 9, 16, 6, 35, tzinfo=timezone.utc)
    app = create_app(
        session_factory=lambda: _Session(),
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
        bootstrap_admission=admission,
        canonical_store_authority_evaluator=evaluator,
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/kc/store",
            headers={
                "X-Knowledge-Key": "task6g-exact-write-key",
                "Idempotency-Key": "event-time-exactness",
            },
            json={
                "content": "Exact authority must bind durable provenance time.",
                "project": "knowledge-core",
                "source_type": "user_note",
                "source_id": "event-time-bound-note",
                "source_event_time": event_time.isoformat(),
            },
        )

    assert response.status_code == 403
    assert response.json()["error_code"] == "CANONICAL_STORE_NOT_AUTHORIZED"
    assert len(evaluator.requests) == 1
    request = evaluator.requests[0]
    assert request.source_event_time == event_time
    assert request.source_id == "event-time-bound-note"
    assert request.project_key == "knowledge-core"
