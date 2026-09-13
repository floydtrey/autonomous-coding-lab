from __future__ import annotations

from dataclasses import dataclass, field

from fastapi.testclient import TestClient

from knowledge_core.api.app import create_app
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.authority.retrieval import (
    RetrievalAuthorityDecision,
    RetrievalAuthorityOperation,
    RetrievalAuthorityRequest,
    require_retrieval_authority,
)


class _NoSearchSession:
    """Session double that fails if a denied request reaches retrieval storage."""

    def __init__(self):
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def __getattr__(self, name):
        raise AssertionError(f"denied retrieval touched session method: {name}")


@dataclass
class _RecordingAuthority:
    allowed: bool
    fail: bool = False
    requests: list[RetrievalAuthorityRequest] = field(default_factory=list)

    def evaluate_retrieval(
        self,
        request: RetrievalAuthorityRequest,
    ) -> RetrievalAuthorityDecision:
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("simulated authority transport failure")
        return RetrievalAuthorityDecision(
            allowed=self.allowed,
            decision_ref="authority-test-decision",
            reason_code="test-policy",
        )


class _MalformedAuthority:
    def evaluate_retrieval(self, request: RetrievalAuthorityRequest):
        return True


def _client(tmp_path, evaluator):
    sessions: list[_NoSearchSession] = []

    def session_factory():
        session = _NoSearchSession()
        sessions.append(session)
        return session

    app = create_app(
        session_factory=session_factory,
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
        retrieval_authority_evaluator=evaluator,
    )
    return TestClient(app), sessions


def test_authority_contract_returns_explicit_allow_decision():
    evaluator = _RecordingAuthority(allowed=True)
    request = RetrievalAuthorityRequest(
        caller_principal_ref="consumer-a",
        operation=RetrievalAuthorityOperation.SEARCH_TEXT,
        limit=7,
        include_superseded=True,
    )

    decision = require_retrieval_authority(evaluator, request)

    assert decision.allowed is True
    assert decision.decision_ref == "authority-test-decision"
    assert evaluator.requests == [request]


def test_retrieval_api_denies_before_search_and_uses_caller_identity(tmp_path):
    evaluator = _RecordingAuthority(allowed=False)
    client, sessions = _client(tmp_path, evaluator)
    try:
        response = client.post(
            "/v1/retrieval/search",
            headers={"X-Knowledge-Caller": "denied-consumer"},
            json={
                "query": "protected sentinel that must never be searched",
                "limit": 3,
                "include_superseded": True,
            },
        )
    finally:
        client.close()

    assert response.status_code == 404
    assert response.json() == {"detail": "knowledge item is unavailable"}
    assert "protected sentinel" not in response.text
    assert len(evaluator.requests) == 1
    request = evaluator.requests[0]
    assert request.caller_principal_ref == "denied-consumer"
    assert request.operation is RetrievalAuthorityOperation.SEARCH_TEXT
    assert request.limit == 3
    assert request.include_superseded is True
    assert sessions and all(session.closed for session in sessions)


def test_retrieval_api_fails_closed_when_authority_is_unconfigured(tmp_path):
    client, sessions = _client(tmp_path, None)
    try:
        response = client.post(
            "/v1/retrieval/search",
            headers={"X-Knowledge-Caller": "consumer-a"},
            json={"query": "must not execute"},
        )
        health = client.get("/health")
    finally:
        client.close()

    assert response.status_code == 503
    assert response.json() == {
        "detail": "retrieval authority is unavailable",
        "error_code": "RETRIEVAL_AUTHORITY_UNAVAILABLE",
    }
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert sessions and all(session.closed for session in sessions)


def test_retrieval_api_fails_closed_on_authority_error_or_invalid_decision(tmp_path):
    for evaluator in (
        _RecordingAuthority(allowed=True, fail=True),
        _MalformedAuthority(),
    ):
        client, sessions = _client(tmp_path, evaluator)
        try:
            response = client.post(
                "/v1/retrieval/search",
                headers={"X-Knowledge-Caller": "consumer-a"},
                json={"query": "must not execute"},
            )
        finally:
            client.close()

        assert response.status_code == 503
        assert response.json()["error_code"] == "RETRIEVAL_AUTHORITY_UNAVAILABLE"
        assert sessions and all(session.closed for session in sessions)


def test_retrieval_api_still_requires_explicit_caller(tmp_path):
    evaluator = _RecordingAuthority(allowed=True)
    client, sessions = _client(tmp_path, evaluator)
    try:
        response = client.post(
            "/v1/retrieval/search",
            json={"query": "must not execute"},
        )
    finally:
        client.close()

    assert response.status_code == 400
    assert evaluator.requests == []
    assert sessions and all(session.closed for session in sessions)
