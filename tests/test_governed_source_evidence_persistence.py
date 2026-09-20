from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha1
import os
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.engine import Engine

from knowledge_core.application.governed_source_evidence import (
    GovernedSourceEvidenceKnowledgeKernel,
    LEGACY_REPOSITORY_MAPPING_VERSION,
)
from knowledge_core.application.repository_import import RepositoryImportKnowledgeKernel
from knowledge_core.application.resources import ResourceKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind
from knowledge_core.domain.governed_sources import (
    GovernedRetrievalSnapshot,
    GovernedSnapshotMember,
    GovernedSourceBinding,
    GovernedSourceDecision,
    GovernedSourceIdentity,
    GovernedSourceObservation,
    SourceEvidenceRef,
)
from knowledge_core.domain.repository_import import RepositorySourceProof
from knowledge_core.domain.retrieval import RetrievalLifecycleState
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.generation_models import DerivedGeneration
from knowledge_core.storage.governed_source_models import (
    GovernedRetrievalSnapshotRecord,
    GovernedSnapshotExclusionRecord,
    GovernedSnapshotMemberRecord,
    GovernedSourceBindingRecord,
    GovernedSourceDecisionRecord,
    GovernedSourceObservationRecord,
    LegacyRepositoryDecisionMap,
    LegacyRepositoryObservationMap,
    LegacyRepositorySnapshotMap,
)
from knowledge_core.storage.repository_import_models import (
    RepositoryImportReceipt,
    RepositorySourceObservation,
)


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)


def _blob_sha(content: bytes) -> str:
    digest = sha1()
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return digest.hexdigest()


class FakeRepositoryReader:
    def __init__(self):
        self.repository_locator = "memory://governed-evidence"
        self.objects: dict[tuple[str, str], bytes] = {}

    def put(self, commit: str, path: str, content: bytes) -> None:
        self.objects[(commit, path)] = content

    def read_exact(self, *, source_commit: str, path: str) -> RepositorySourceProof:
        try:
            content = self.objects[(source_commit, path)]
        except KeyError as exc:
            raise KnowledgeInvariantError(
                f"source path does not exist at exact commit: {path}"
            ) from exc
        return RepositorySourceProof(
            source_commit=source_commit,
            path=path,
            git_blob_sha=_blob_sha(content),
            content=content,
            object_mode="100644",
            object_type="blob",
        )


def _entry(
    key: str,
    path: str,
    content: bytes,
    *,
    lifecycle: str = "current",
    authority: int | None = 10,
    classification: str = "approved",
    rationale: str = "explicit governed-evidence fixture",
) -> dict:
    return {
        "source_document_key": key,
        "path": path,
        "git_blob_sha": _blob_sha(content),
        "media_type": "text/markdown",
        "classification": classification,
        "retrieval_lifecycle": lifecycle,
        "authority_rank": authority,
        "rationale": rationale,
    }


def _manifest(
    *,
    manifest_id: str,
    commit: str,
    entries: list[dict],
    previous: str | None = None,
    retirements: list[dict] | None = None,
) -> dict:
    return {
        "schema_version": 2,
        "manifest_id": manifest_id,
        "source_repository_key": "repo-generic-map",
        "repository_locator": "memory://governed-evidence",
        "source_commit": commit,
        "previous_manifest_digest": previous,
        "history_policy": "retain_prior_versions_as_superseded",
        "entries": entries,
        "retirements": retirements or [],
    }


def _require_postgres_engine() -> Engine:
    if not _POSTGRES_URL:
        pytest.skip("governed evidence PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("governed evidence persistence requires PostgreSQL")
    return engine


def _truncate_kernel_tables(engine: Engine) -> None:
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


@pytest.fixture()
def evidence_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def _apply(kernel: RepositoryImportKnowledgeKernel, manifest: dict):
    plan = kernel.plan_repository_import(manifest)
    receipt = kernel.apply_repository_import(
        manifest=manifest,
        expected_plan_digest=plan.plan_digest,
    )
    return receipt


def _current_text_generation_id(session) -> UUID | None:
    return session.scalar(
        select(DerivedGeneration.generation_id).where(
            DerivedGeneration.derived_kind == DerivedKind.TEXT.value,
            DerivedGeneration.status == "current",
        )
    )


@pytest.mark.postgresql
def test_generic_note_evidence_round_trips_without_repository_fields(
    evidence_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(evidence_engine)
    session = sessions()
    resources = ResourceKnowledgeKernel(
        session,
        artifact_store=LocalArtifactStore(tmp_path / "artifacts-note"),
    )
    foundation = resources.bootstrap_resource_test_profile()
    resource = resources.create_resource(
        kind_revision_ref=foundation.artifact_kind_revision_ref
    )
    version = resources.ingest_resource_version(
        resource_ref=resource.resource_ref,
        content=b"Mason is my local MindsHub worker model.\n",
        ingestion_kind_revision_ref=foundation.resource_ingestion_kind_revision_ref,
        media_type="text/plain",
    )

    now = datetime(2026, 9, 14, 22, 0, tzinfo=timezone.utc)
    observation = GovernedSourceObservation(
        observation_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        binding=GovernedSourceBinding(
            source_identity=GovernedSourceIdentity(
                source_kind="local.user-note",
                origin_scope="local_owner",
                collection_key="personal-notes",
                item_key="note-mason",
            ),
            resource_ref=resource.resource_ref,
        ),
        resource_version_ref=version.resource_version_ref,
        producer_id="kc.local-note-fixture",
        producer_version="1",
        evidence=(
            SourceEvidenceRef(
                evidence_kind="local.authenticated-submission",
                evidence_ref="request:note-mason",
                evidence_digest="sha256:" + "1" * 64,
            ),
        ),
        observed_at=now,
    )
    decision = GovernedSourceDecision(
        decision_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        observation_id=observation.observation_id,
        policy_id="kc-local-note-governance-v1",
        classification="approved",
        retrieval_lifecycle=RetrievalLifecycleState.CURRENT,
        authority_rank=10,
        rationale="authenticated local-owner note fixture",
        decided_at=now,
    )
    member = GovernedSnapshotMember.from_selection(
        observation=observation,
        decision=decision,
        project_keys=("local-ai", "knowledge-core"),
    )
    snapshot = GovernedRetrievalSnapshot(
        selection_policy_id="kc-direct-note-fixture-selection-v1",
        created_at=now,
        members=(member,),
    )

    evidence = GovernedSourceEvidenceKnowledgeKernel(session)
    evidence.persist_observation(observation)
    evidence.persist_decision(decision)
    evidence.persist_snapshot(snapshot)
    session.commit()
    session.close()

    session = sessions()
    evidence = GovernedSourceEvidenceKnowledgeKernel(session)
    assert evidence.load_observation(observation.observation_id) == observation
    assert evidence.load_decision(decision.decision_id) == decision
    assert evidence.load_snapshot(snapshot.digest) == snapshot

    columns = {
        item["name"]
        for item in inspect(evidence_engine).get_columns(
            "governed_source_observation",
            schema="kc_control",
        )
    }
    assert {
        "source_repository_key",
        "source_document_key",
        "source_commit",
        "source_path",
        "git_blob_sha",
        "manifest_digest",
    }.isdisjoint(columns)
    session.close()


@pytest.mark.postgresql
def test_settled_repository_chain_maps_deterministically_without_changing_serving(
    evidence_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(evidence_engine)
    session = sessions()
    reader = FakeRepositoryReader()
    a, b = "a" * 40, "b" * 40
    alpha_a = b"# Alpha\nold apricot\n"
    alpha_b = b"# Alpha\nnew blackberry\n"
    beta = b"# Beta\nretained canyon\n"
    gamma = b"# Gamma\nexcluded delta\n"
    reader.put(a, "alpha.md", alpha_a)
    reader.put(a, "beta.md", beta)
    reader.put(a, "gamma.md", gamma)
    reader.put(b, "alpha.md", alpha_b)

    repository = RepositoryImportKnowledgeKernel(
        session,
        artifact_store=LocalArtifactStore(tmp_path / "artifacts-repository"),
        source_readers={"repo-generic-map": reader},
    )
    receipt_a = _apply(
        repository,
        _manifest(
            manifest_id="A",
            commit=a,
            entries=[
                _entry("alpha", "alpha.md", alpha_a, authority=7),
                _entry("beta", "beta.md", beta, authority=15),
                _entry("gamma", "gamma.md", gamma, authority=20),
            ],
        ),
    )
    alpha_obs_a = repository._observation_for_manifest(
        receipt_a.manifest_digest, "alpha"
    )
    assert alpha_obs_a is not None

    receipt_b = _apply(
        repository,
        _manifest(
            manifest_id="B",
            commit=b,
            previous=receipt_a.manifest_digest,
            entries=[
                _entry(
                    "alpha",
                    "alpha.md",
                    alpha_b,
                    lifecycle="unknown",
                    authority=3,
                    classification="reviewed",
                    rationale="new alpha revision under review",
                )
            ],
            retirements=[
                {
                    "source_document_key": "beta",
                    "reason": "retain historical beta",
                    "historical_retrieval": "retain",
                },
                {
                    "source_document_key": "gamma",
                    "reason": "exclude historical gamma",
                    "historical_retrieval": "exclude",
                },
            ],
        ),
    )

    current_before = _current_text_generation_id(session)
    assert current_before is not None
    legacy_alpha_before = session.get(
        RepositorySourceObservation,
        alpha_obs_a.observation_id,
    )
    legacy_alpha_payload = (
        legacy_alpha_before.manifest_digest,
        legacy_alpha_before.source_repository_key,
        legacy_alpha_before.source_document_key,
        legacy_alpha_before.source_commit,
        legacy_alpha_before.path,
        legacy_alpha_before.git_blob_sha,
        legacy_alpha_before.resource_ref,
        legacy_alpha_before.resource_version_ref,
        legacy_alpha_before.classification,
        legacy_alpha_before.retrieval_lifecycle,
        legacy_alpha_before.authority_rank,
        legacy_alpha_before.rationale,
    )

    mapper = GovernedSourceEvidenceKnowledgeKernel(session)
    snapshot_b = mapper.map_settled_repository_receipt(receipt_b.manifest_digest)
    assert len(snapshot_b.members) == 3
    assert len(snapshot_b.exclusions) == 1
    assert snapshot_b.predecessor_snapshot_digest is not None

    current_after = _current_text_generation_id(session)
    assert current_after is not None
    assert current_after == current_before

    legacy_alpha_after = session.get(
        RepositorySourceObservation,
        alpha_obs_a.observation_id,
    )
    assert legacy_alpha_payload == (
        legacy_alpha_after.manifest_digest,
        legacy_alpha_after.source_repository_key,
        legacy_alpha_after.source_document_key,
        legacy_alpha_after.source_commit,
        legacy_alpha_after.path,
        legacy_alpha_after.git_blob_sha,
        legacy_alpha_after.resource_ref,
        legacy_alpha_after.resource_version_ref,
        legacy_alpha_after.classification,
        legacy_alpha_after.retrieval_lifecycle,
        legacy_alpha_after.authority_rank,
        legacy_alpha_after.rationale,
    )

    map_a = session.get(LegacyRepositorySnapshotMap, receipt_a.manifest_digest)
    map_b = session.get(LegacyRepositorySnapshotMap, receipt_b.manifest_digest)
    assert map_a is not None and map_b is not None
    assert map_b.snapshot_digest == snapshot_b.digest
    assert map_b.mapping_version == LEGACY_REPOSITORY_MAPPING_VERSION
    assert snapshot_b.predecessor_snapshot_digest == map_a.snapshot_digest

    observation_map = session.get(
        LegacyRepositoryObservationMap,
        alpha_obs_a.observation_id,
    )
    assert observation_map is not None
    decision_a = session.get(
        LegacyRepositoryDecisionMap,
        (receipt_a.manifest_digest, alpha_obs_a.observation_id),
    )
    decision_b = session.get(
        LegacyRepositoryDecisionMap,
        (receipt_b.manifest_digest, alpha_obs_a.observation_id),
    )
    assert decision_a is not None and decision_b is not None
    assert decision_a.decision_id != decision_b.decision_id
    assert decision_a.selection_role == "current"
    assert decision_b.selection_role == "prior_version"

    generic_current = mapper.load_decision(decision_a.decision_id)
    generic_historical = mapper.load_decision(decision_b.decision_id)
    assert generic_current.observation_id == generic_historical.observation_id
    assert generic_current.retrieval_lifecycle == RetrievalLifecycleState.CURRENT
    assert generic_historical.retrieval_lifecycle == RetrievalLifecycleState.SUPERSEDED

    generic_alpha = mapper.load_observation(observation_map.generic_observation_id)
    assert generic_alpha.source_event_time is None
    assert generic_alpha.source_revision_time is None
    assert generic_alpha.binding.source_identity.source_kind == "git.repository-document"
    assert generic_alpha.binding.source_identity.item_key == "alpha"

    exclusion = session.execute(
        select(GovernedSnapshotExclusionRecord).where(
            GovernedSnapshotExclusionRecord.snapshot_digest == snapshot_b.digest
        )
    ).scalar_one()
    assert exclusion.reason_code == "legacy-retirement-exclude"

    counts_before = {
        model: session.scalar(select(func.count()).select_from(model))
        for model in (
            GovernedSourceBindingRecord,
            GovernedSourceObservationRecord,
            GovernedSourceDecisionRecord,
            GovernedRetrievalSnapshotRecord,
            GovernedSnapshotMemberRecord,
            LegacyRepositoryObservationMap,
            LegacyRepositoryDecisionMap,
            LegacyRepositorySnapshotMap,
        )
    }
    replay = mapper.map_settled_repository_receipt(receipt_b.manifest_digest)
    counts_after = {
        model: session.scalar(select(func.count()).select_from(model))
        for model in counts_before
    }
    assert replay.digest == snapshot_b.digest
    assert counts_after == counts_before
    session.close()

    session = sessions()
    reconstructed = GovernedSourceEvidenceKnowledgeKernel(session).load_snapshot(
        snapshot_b.digest
    )
    assert reconstructed.digest == snapshot_b.digest
    assert len(reconstructed.members) == 3
    assert len(reconstructed.exclusions) == 1
    session.close()


@pytest.mark.postgresql
@pytest.mark.parametrize("status", ["applying", "failed"])
def test_unsettled_repository_receipt_cannot_map_into_generic_snapshot(
    evidence_engine,
    status: str,
):
    sessions = create_session_factory(evidence_engine)
    session = sessions()
    manifest_digest = ("1" if status == "applying" else "2") * 64
    session.add(
        RepositoryImportReceipt(
            manifest_digest=manifest_digest,
            previous_manifest_digest=None,
            source_repository_key="repo-unsettled",
            source_commit="a" * 40,
            plan_digest="3" * 64,
            status=status,
            manifest_json={
                "schema_version": 2,
                "manifest_id": f"fixture-{status}",
                "source_repository_key": "repo-unsettled",
                "repository_locator": "memory://unsettled",
                "source_commit": "a" * 40,
                "previous_manifest_digest": None,
                "history_policy": "retain_prior_versions_as_superseded",
                "entries": [],
                "retirements": [],
            },
            resulting_text_generation_id=None,
            created_at=datetime.now(timezone.utc),
            settled_at=None,
        )
    )
    session.commit()

    mapper = GovernedSourceEvidenceKnowledgeKernel(session)
    with pytest.raises(
        KnowledgeInvariantError,
        match="only settled legacy repository receipts",
    ):
        mapper.map_settled_repository_receipt(manifest_digest)

    assert session.get(LegacyRepositorySnapshotMap, manifest_digest) is None
    assert (
        session.scalar(
            select(func.count()).select_from(GovernedRetrievalSnapshotRecord)
        )
        == 0
    )
    session.close()
