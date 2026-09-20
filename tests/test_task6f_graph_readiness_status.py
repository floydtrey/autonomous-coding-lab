from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapContract
from knowledge_core.application.consumer_read import ConsumerReadKnowledgeKernel
from knowledge_core.application.graph_readiness import (
    inspect_source_neutral_graph_readiness,
)
from knowledge_core.application.section_generation import (
    SR2_SEGMENT_MODEL_IDENTITY,
    SR2_SEGMENT_MODEL_VERSION,
)
from knowledge_core.application.source_neutral_graph import (
    SourceNeutralGraphProjectionKnowledgeKernel,
)
from knowledge_core.application.unified_retrieval import UnifiedGraphSearchBinding
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.projection_adapter import ProjectionAdapterDescriptor
from knowledge_core.domain.projection_evidence import (
    ProjectionDisposition,
    ProjectionValidationState,
)
from knowledge_core.domain.projection_validation import ProjectionValidationRequirement
from knowledge_core.domain.retrieval import (
    LEXICAL_EVIDENCE_CONTRACT_VERSION,
    RetrievalStatusSnapshot,
    TextReadinessState,
)
from knowledge_core.domain.unified_retrieval import (
    GraphRetrievalEvidence,
    GraphRetrievalState,
)


_BOOTSTRAP_KEY = "task6f-bootstrap-key"
_NAMESPACE = "kc:graphiti-source-neutral-v1"
_SCOPE = "project:knowledge-core"
_BACKEND = "graphiti-falkordb"
_BACKEND_VERSION = "task6f-test"
_CONFIG_DIGEST = "sha256:task6f-config"


@dataclass
class _Attempt:
    attempt_id: UUID
    backend_version: str | None
    profile_id: str | None
    profile_digest: str | None
    config_digest: str | None
    disposition: str
    validation_state: str


class _ScalarResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)


class _LedgerSession:
    def __init__(self, rows):
        self.rows = list(rows)

    def scalars(self, _statement):
        return _ScalarResult(self.rows)


@dataclass
class _CurrentGeneration:
    generation_id: UUID
    config_digest: str
    model_identity: str = SR2_SEGMENT_MODEL_IDENTITY
    model_version: str = SR2_SEGMENT_MODEL_VERSION


class _Kernel:
    graph_projection_profile_identity = staticmethod(
        SourceNeutralGraphProjectionKnowledgeKernel.graph_projection_profile_identity
    )

    def __init__(self, *, rows, current, satisfying_attempts=()):
        self.session = _LedgerSession(rows)
        self._current = current
        self._satisfying_attempts = set(satisfying_attempts)

    def current_generation(self, *, derived_kind):
        return self._current

    def projection_satisfies_validation_requirement(self, *, attempt_id, requirement):
        return attempt_id in self._satisfying_attempts


class _Adapter:
    def __init__(self, *, requirement=None):
        self._descriptor = ProjectionAdapterDescriptor(
            backend_identity=_BACKEND,
            backend_version=_BACKEND_VERSION,
            adapter_identity="task6f-adapter",
            adapter_version="1",
            config_digest=_CONFIG_DIGEST,
            validation_requirement=requirement,
        )

    @property
    def descriptor(self):
        return self._descriptor

    async def search(self, **_kwargs):
        raise AssertionError("graph readiness must not query the provider")

    async def project(self, _request):
        raise AssertionError("graph readiness must not project or synchronize")


def _attempt(
    *,
    current,
    disposition: ProjectionDisposition,
    validation_state: ProjectionValidationState,
    stale: bool = False,
) -> _Attempt:
    profile_id, profile_digest = (
        SourceNeutralGraphProjectionKnowledgeKernel.graph_projection_profile_identity(
            current
        )
    )
    if stale:
        profile_id = "sr2-governed-graph:stale-generation"
    return _Attempt(
        attempt_id=uuid4(),
        backend_version=_BACKEND_VERSION,
        profile_id=profile_id,
        profile_digest=profile_digest,
        config_digest=_CONFIG_DIGEST,
        disposition=disposition.value,
        validation_state=validation_state.value,
    )


def _classify(*, rows, current, adapter=None, satisfying_attempts=()):
    return inspect_source_neutral_graph_readiness(
        kernel=_Kernel(
            rows=rows,
            current=current,
            satisfying_attempts=satisfying_attempts,
        ),
        adapter=adapter or _Adapter(),
        namespace_key=_NAMESPACE,
        scope_key=_SCOPE,
    )


def test_graph_readiness_distinguishes_no_build_stale_pending_unvalidated_failed_and_ready():
    current = _CurrentGeneration(
        generation_id=uuid4(),
        config_digest="sha256:current-text",
    )

    assert _classify(rows=[], current=current).state is GraphRetrievalState.NO_BUILD

    stale = _attempt(
        current=current,
        disposition=ProjectionDisposition.SUCCEEDED,
        validation_state=ProjectionValidationState.VALIDATED,
        stale=True,
    )
    stale_state = _classify(rows=[stale], current=current)
    assert stale_state.state is GraphRetrievalState.STALE
    assert stale_state.attempt_ids == (stale.attempt_id,)

    pending = _attempt(
        current=current,
        disposition=ProjectionDisposition.PENDING,
        validation_state=ProjectionValidationState.UNVALIDATED,
    )
    assert _classify(rows=[pending], current=current).state is GraphRetrievalState.PENDING

    unvalidated = _attempt(
        current=current,
        disposition=ProjectionDisposition.SUCCEEDED,
        validation_state=ProjectionValidationState.UNVALIDATED,
    )
    assert (
        _classify(rows=[unvalidated], current=current).state
        is GraphRetrievalState.UNVALIDATED
    )

    failed = _attempt(
        current=current,
        disposition=ProjectionDisposition.FAILED,
        validation_state=ProjectionValidationState.REJECTED,
    )
    assert _classify(rows=[failed], current=current).state is GraphRetrievalState.FAILED

    ready = _attempt(
        current=current,
        disposition=ProjectionDisposition.SUCCEEDED,
        validation_state=ProjectionValidationState.VALIDATED,
    )
    ready_state = _classify(rows=[ready], current=current)
    assert ready_state.state is GraphRetrievalState.READY
    assert ready_state.generation_id == current.generation_id
    assert ready_state.attempt_ids == (ready.attempt_id,)


def test_graph_readiness_requires_the_current_validation_requirement_without_provider_calls():
    current = _CurrentGeneration(
        generation_id=uuid4(),
        config_digest="sha256:current-text",
    )
    attempt = _attempt(
        current=current,
        disposition=ProjectionDisposition.SUCCEEDED,
        validation_state=ProjectionValidationState.VALIDATED,
    )
    requirement = ProjectionValidationRequirement(
        validator_identity="task6f-validator",
        validator_version="1",
        ruleset_id="task6f-rules",
        ruleset_digest="sha256:task6f-rules",
        required_check_codes=("source-correlation",),
    )
    adapter = _Adapter(requirement=requirement)

    unmet = _classify(rows=[attempt], current=current, adapter=adapter)
    assert unmet.state is GraphRetrievalState.UNVALIDATED

    met = _classify(
        rows=[attempt],
        current=current,
        adapter=adapter,
        satisfying_attempts=(attempt.attempt_id,),
    )
    assert met.state is GraphRetrievalState.READY


class _Session:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def _session_factory(created):
    def factory():
        session = _Session()
        created.append(session)
        return session

    return factory


def _admission() -> BootstrapAdmission:
    return BootstrapAdmission(
        contract=BootstrapContract(),
        api_key=_BOOTSTRAP_KEY,
    )


def _headers() -> dict[str, str]:
    return {"X-Knowledge-Key": _BOOTSTRAP_KEY}


def _status(*, generation_id) -> RetrievalStatusSnapshot:
    return RetrievalStatusSnapshot(
        canonical_revision=42,
        text_state=TextReadinessState.READY,
        text_generation_id=generation_id,
        text_source_revision_highwater=42,
        text_source_count=3,
        retrieval_mode="segment",
        lineage_mode="source-neutral-sr2",
        evidence_contract_version=LEXICAL_EVIDENCE_CONTRACT_VERSION,
        generation_config_digest="sha256:current-text",
    )


def _binding(adapter) -> UnifiedGraphSearchBinding:
    return UnifiedGraphSearchBinding(
        adapter=adapter,
        authority_evaluator=None,
        caller_principal_ref="local_owner",
        namespace_key=_NAMESPACE,
        scope_key=_SCOPE,
    )


def test_kc_status_adds_disabled_graph_state_without_graph_binding(
    monkeypatch,
    tmp_path: Path,
):
    generation_id = uuid4()
    created = []

    monkeypatch.setattr(
        ConsumerReadKnowledgeKernel,
        "retrieval_status",
        lambda self: _status(generation_id=generation_id),
    )

    app = create_app(
        session_factory=_session_factory(created),
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
        bootstrap_admission=_admission(),
    )
    with TestClient(app) as client:
        response = client.get("/v1/kc/status", headers=_headers())

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["canonical_revision"] == 42
    assert payload["text_state"] == "ready"
    assert payload["text_generation_id"] == str(generation_id)
    assert payload["graph"]["state"] == "disabled"
    assert payload["graph"]["reason_code"] == "graph-augmentation-not-configured"
    assert payload["graph"]["results"] == []
    assert created and all(session.closed for session in created)


def test_kc_status_uses_durable_graph_readiness_without_searching_provider(
    monkeypatch,
    tmp_path: Path,
):
    generation_id = uuid4()
    attempt_id = uuid4()
    created = []
    adapter = _Adapter()
    calls = []

    monkeypatch.setattr(
        ConsumerReadKnowledgeKernel,
        "retrieval_status",
        lambda self: _status(generation_id=generation_id),
    )

    def fake_readiness(*, kernel, adapter, namespace_key, scope_key):
        calls.append((adapter, namespace_key, scope_key))
        return GraphRetrievalEvidence(
            state=GraphRetrievalState.READY,
            namespace_key=namespace_key,
            scope_key=scope_key,
            generation_id=generation_id,
            attempt_ids=(attempt_id,),
        )

    monkeypatch.setattr(
        "knowledge_core.api.app.inspect_source_neutral_graph_readiness",
        fake_readiness,
    )

    app = create_app(
        session_factory=_session_factory(created),
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
        bootstrap_admission=_admission(),
        unified_graph_search_binding=_binding(adapter),
    )
    with TestClient(app) as client:
        response = client.get("/v1/kc/status", headers=_headers())

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["graph"]["state"] == "ready"
    assert payload["graph"]["generation_id"] == str(generation_id)
    assert payload["graph"]["attempt_ids"] == [str(attempt_id)]
    assert calls == [(adapter, _NAMESPACE, _SCOPE)]
    assert created and all(session.closed for session in created)
