from __future__ import annotations

from dataclasses import replace
import os
from uuid import UUID

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from knowledge_core.application.lifecycle_projection import GovernedRetrievalObservation
from knowledge_core.application.projection_lineage import projection_snapshot_digest
from knowledge_core.domain.retrieval import RetrievalLifecycleState
from knowledge_core.storage.database import create_database_engine
from knowledge_core.storage.section_retrieval_models import TextGenerationSource


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
RESOURCE_VERSION = UUID("11111111-1111-1111-1111-111111111111")
OBSERVATION = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _observation() -> GovernedRetrievalObservation:
    return GovernedRetrievalObservation(
        observation_id=OBSERVATION,
        manifest_digest="a" * 64,
        source_repository_key="acl",
        repository_locator="git://acl",
        source_document_key="kc-doc",
        source_commit="b" * 40,
        source_path="docs/kc.md",
        git_blob_sha="c" * 40,
        resource_version_ref=RESOURCE_VERSION,
        classification="approved",
        document_lifecycle=RetrievalLifecycleState.CURRENT,
        authority_rank=5,
        rationale="explicit governed source fixture",
    )


def test_sr2_g7_g9_projection_snapshot_digest_binds_exact_governed_inputs():
    observation = _observation()
    governing_manifest = "d" * 64
    baseline = projection_snapshot_digest(
        observation=observation,
        governing_manifest_digest=governing_manifest,
    )

    assert baseline.startswith("sha256:")
    assert len(baseline) == 71
    assert baseline == projection_snapshot_digest(
        observation=observation,
        governing_manifest_digest=governing_manifest,
    )

    changed_observations = [
        replace(
            observation,
            observation_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        ),
        replace(observation, manifest_digest="e" * 64),
        replace(observation, source_repository_key="acl-other"),
        replace(observation, repository_locator="git://acl-other"),
        replace(observation, source_document_key="kc-doc-other"),
        replace(observation, source_commit="f" * 40),
        replace(observation, source_path="docs/other.md"),
        replace(observation, git_blob_sha="1" * 40),
        replace(
            observation,
            resource_version_ref=UUID("22222222-2222-2222-2222-222222222222"),
        ),
        replace(observation, classification="approved-other"),
        replace(
            observation,
            document_lifecycle=RetrievalLifecycleState.SUPERSEDED,
        ),
        replace(observation, authority_rank=6),
        replace(observation, rationale="changed rationale"),
    ]
    for changed in changed_observations:
        assert (
            projection_snapshot_digest(
                observation=changed,
                governing_manifest_digest=governing_manifest,
            )
            != baseline
        )

    assert (
        projection_snapshot_digest(
            observation=observation,
            governing_manifest_digest="2" * 64,
        )
        != baseline
    )


@pytest.mark.parametrize("field", ["source", "governing"])
def test_projection_snapshot_digest_rejects_noncanonical_manifest_digest(field):
    observation = _observation()
    governing_manifest = "d" * 64
    if field == "source":
        observation = replace(observation, manifest_digest="NOT-A-DIGEST")
    else:
        governing_manifest = "NOT-A-DIGEST"

    with pytest.raises(ValueError, match="manifest digest"):
        projection_snapshot_digest(
            observation=observation,
            governing_manifest_digest=governing_manifest,
        )


def test_text_generation_source_model_has_v2_generic_and_v1_compatibility_lineage():
    table = TextGenerationSource.__table__
    assert table.schema == "kc_derived"
    assert list(table.columns.keys()) == [
        "generation_id",
        "resource_version_ref",
        "governed_observation_id",
        "governed_decision_id",
        "governing_snapshot_digest",
        "governed_projection_digest",
        "source_observation_id",
        "governing_manifest_digest",
        "projection_snapshot_digest",
    ]
    assert [column.name for column in table.primary_key.columns] == [
        "generation_id",
        "resource_version_ref",
    ]


def _require_postgres_engine() -> Engine:
    if not _POSTGRES_URL:
        pytest.skip("SR-2 PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("SR-2 lineage qualification requires PostgreSQL")
    return engine


@pytest.mark.postgresql
def test_sr2_g9_projection_lineage_migration_has_exact_v2_foreign_keys():
    engine = _require_postgres_engine()
    try:
        inspector = inspect(engine)
        assert "text_generation_source" in inspector.get_table_names(
            schema="kc_derived"
        )

        columns = {
            column["name"]: column
            for column in inspector.get_columns(
                "text_generation_source",
                schema="kc_derived",
            )
        }
        assert set(columns) == {
            "generation_id",
            "resource_version_ref",
            "governed_observation_id",
            "governed_decision_id",
            "governing_snapshot_digest",
            "governed_projection_digest",
            "source_observation_id",
            "governing_manifest_digest",
            "projection_snapshot_digest",
        }
        assert columns["governed_observation_id"]["nullable"] is True
        assert columns["governed_decision_id"]["nullable"] is True
        assert columns["governing_snapshot_digest"]["nullable"] is True
        assert columns["governed_projection_digest"]["nullable"] is True
        assert columns["source_observation_id"]["nullable"] is True
        assert columns["governing_manifest_digest"]["nullable"] is True
        assert columns["projection_snapshot_digest"]["nullable"] is True
        assert getattr(columns["projection_snapshot_digest"]["type"], "length", None) == 71
        assert getattr(columns["governing_snapshot_digest"]["type"], "length", None) == 71
        assert getattr(columns["governed_projection_digest"]["type"], "length", None) == 71

        primary_key = inspector.get_pk_constraint(
            "text_generation_source",
            schema="kc_derived",
        )
        assert primary_key["constrained_columns"] == [
            "generation_id",
            "resource_version_ref",
        ]

        foreign_keys = {
            (
                tuple(item["constrained_columns"]),
                item["referred_schema"],
                item["referred_table"],
                tuple(item["referred_columns"]),
            )
            for item in inspector.get_foreign_keys(
                "text_generation_source",
                schema="kc_derived",
            )
        }
        assert foreign_keys == {
            (
                ("generation_id",),
                "kc_derived",
                "generation",
                ("generation_id",),
            ),
            (
                ("resource_version_ref",),
                "kc",
                "resource_version",
                ("ref_id",),
            ),
            (
                ("governed_observation_id",),
                "kc_control",
                "governed_source_observation",
                ("observation_id",),
            ),
            (
                ("governed_decision_id",),
                "kc_control",
                "governed_source_decision",
                ("decision_id",),
            ),
            (
                ("governing_snapshot_digest",),
                "kc_control",
                "governed_retrieval_snapshot",
                ("snapshot_digest",),
            ),
            (
                ("source_observation_id",),
                "kc_control",
                "repository_source_observation",
                ("observation_id",),
            ),
            (
                ("governing_manifest_digest",),
                "kc_control",
                "repository_import_receipt",
                ("manifest_digest",),
            ),
        }
    finally:
        engine.dispose()
