from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from knowledge_core.api.app import create_app
from knowledge_core.application.governed_snapshot_selection import (
    resolve_governed_snapshot_sources,
)
from knowledge_core.application.governed_source_selection import (
    resolve_governed_projection_sources,
)
from knowledge_core.application.lifecycle_projection import RetrievalProjectionProfile
from knowledge_core.application.repository_source import GitRepositorySourceReader
from knowledge_core.application.section_generation import (
    SR2_SEGMENT_MODEL_IDENTITY,
    SR2_SEGMENT_MODEL_VERSION,
)
from knowledge_core.application.section_generation_v2 import (
    source_neutral_segment_generation_config_digest,
)
from knowledge_core.application.section_repository_import import (
    SectionRepositoryImportKnowledgeKernel,
)
from knowledge_core.application.segmentation import (
    DEFAULT_SECTION_SEGMENTATION_PROFILE,
    segment_structural_content,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.generations import DerivedKind
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.generation_models import DerivedGeneration
from knowledge_core.storage.governed_source_models import LegacyRepositorySnapshotMap
from knowledge_core.storage.repository_import_models import (
    RepositoryDocumentBinding,
    RepositoryImportReceipt,
    RepositorySourceObservation,
)
from knowledge_core.storage.resource_models import Resource, ResourceLocator, ResourceVersion
from knowledge_core.storage.retrieval_models import ResourceTextSearch
from knowledge_core.storage.section_retrieval_models import (
    ResourceSegmentTextSearch,
    TextGenerationProfile,
    TextGenerationSource,
)


_CALLER_HEADERS = {"X-Knowledge-Caller": "sr2-host-qualification"}


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _count(session, model) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _plan_snapshot(plan) -> dict:
    return {
        "manifest_digest": plan.manifest_digest,
        "plan_digest": plan.plan_digest,
        "replay": plan.replay_receipt is not None,
    }


def _receipt_snapshot(receipt) -> dict:
    return {
        "manifest_digest": receipt.manifest_digest,
        "status": receipt.status,
        "resulting_text_generation_id": (
            str(receipt.resulting_text_generation_id)
            if receipt.resulting_text_generation_id is not None
            else None
        ),
    }


def _post(client: TestClient, route: str, payload: dict) -> dict:
    response = client.post(route, json=payload, headers=_CALLER_HEADERS)
    if response.status_code != 200:
        raise AssertionError(f"{route} failed: {response.status_code} {response.text}")
    return response.json()


def _search(client: TestClient, query: str, *, include_superseded: bool) -> dict:
    return _post(
        client,
        "/v1/retrieval/search",
        {
            "query": query,
            "limit": 20,
            "include_superseded": include_superseded,
        },
    )


def _structural_row_snapshot(row) -> dict:
    return {
        "segment_ordinal": int(row.segment_ordinal),
        "segment_key": row.segment_key,
        "structural_kind": row.structural_kind,
        "base_block_ordinal": int(row.base_block_ordinal),
        "part_index": int(row.part_index),
        "part_count": int(row.part_count),
        "source_byte_start": int(row.source_byte_start),
        "source_byte_end": int(row.source_byte_end),
        "source_line_start": int(row.source_line_start),
        "source_line_end": int(row.source_line_end),
        "source_slice_sha256": row.source_slice_sha256,
        "parent_lifecycle_state": row.parent_lifecycle_state,
        "declared_lifecycle_state": row.declared_lifecycle_state,
        "effective_lifecycle_state": row.effective_lifecycle_state,
    }


def _verify_structural_rows(*, content: bytes, resource_version_ref, media_type: str, rows) -> None:
    expected = segment_structural_content(
        resource_version_ref=resource_version_ref,
        media_type=media_type,
        content=content,
    )
    if len(rows) != len(expected.segments):
        raise AssertionError("persisted SR-2 segment count differs from deterministic rebuild")
    rebuilt = b"".join(
        content[row.source_byte_start : row.source_byte_end] for row in rows
    )
    if rebuilt != content:
        raise AssertionError("persisted SR-2 segment ranges do not reconstruct exact source bytes")

    fields = (
        "segment_ordinal",
        "segment_key",
        "structural_kind",
        "base_block_ordinal",
        "part_index",
        "part_count",
        "source_byte_start",
        "source_byte_end",
        "source_line_start",
        "source_line_end",
        "source_slice_sha256",
    )
    for row, structural in zip(rows, expected.segments, strict=True):
        for field in fields:
            if getattr(row, field) != getattr(structural, field):
                raise AssertionError(
                    f"persisted SR-2 structural field mismatch: {field}"
                )


def _snapshot(
    *,
    sessions,
    artifacts: LocalArtifactStore,
    manifest: dict,
    manifest_digest: str,
) -> dict:
    session = sessions()
    try:
        current = SectionRepositoryImportKnowledgeKernel(
            session,
            artifact_store=artifacts,
            source_readers={},
        )._generation_kernel().current_generation(derived_kind=DerivedKind.TEXT)
        if current is None:
            raise AssertionError("SR-2 host qualification has no current text generation")
        if current.model_identity != SR2_SEGMENT_MODEL_IDENTITY:
            raise AssertionError("current text generation is not the SR-2 segment implementation")
        if current.model_version != SR2_SEGMENT_MODEL_VERSION:
            raise AssertionError("current text generation has the wrong SR-2 implementation version")

        profile = session.get(TextGenerationProfile, current.generation_id)
        if profile is None:
            raise AssertionError("current SR-2 generation is missing its profile row")
        expected_projection = RetrievalProjectionProfile(
            structural_profile_digest=DEFAULT_SECTION_SEGMENTATION_PROFILE.digest
        )
        expected_config_digest = source_neutral_segment_generation_config_digest()
        expected_profile = {
            "structural_profile_id": DEFAULT_SECTION_SEGMENTATION_PROFILE.profile_id,
            "structural_profile_digest": DEFAULT_SECTION_SEGMENTATION_PROFILE.digest,
            "projection_profile_id": expected_projection.profile_id,
            "projection_profile_digest": expected_projection.digest,
            "generation_config_digest": expected_config_digest,
        }
        actual_profile = {
            "structural_profile_id": profile.structural_profile_id,
            "structural_profile_digest": profile.structural_profile_digest,
            "projection_profile_id": profile.projection_profile_id,
            "projection_profile_digest": profile.projection_profile_digest,
            "generation_config_digest": profile.generation_config_digest,
        }
        if actual_profile != expected_profile:
            raise AssertionError(
                "current SR-2 generation profile identity is not the source-neutral default"
            )
        if current.config_digest != expected_config_digest:
            raise AssertionError("current SR-2 generation config digest is not recoverable")

        selected = resolve_governed_projection_sources(
            session,
            governing_manifest_digest=manifest_digest,
        )
        selected_by_key = {
            source.observation.source_document_key: source for source in selected
        }
        manifest_by_key = {
            entry["source_document_key"]: entry for entry in manifest["entries"]
        }
        if set(selected_by_key) != set(manifest_by_key):
            raise AssertionError("governed SR-2 source selection differs from pinned manifest")

        snapshot_map = session.get(LegacyRepositorySnapshotMap, manifest_digest)
        if snapshot_map is None:
            raise AssertionError(
                "current repository generation is missing its governed snapshot mapping"
            )
        generic_selected = resolve_governed_snapshot_sources(
            session,
            governing_snapshot_digest=snapshot_map.snapshot_digest,
        )
        generic_by_version = {
            source.observation.resource_version_ref: source
            for source in generic_selected
        }
        if set(generic_by_version) != {
            source.observation.resource_version_ref for source in selected
        }:
            raise AssertionError(
                "source-neutral SR-2 selection differs from repository compatibility selection"
            )

        provenance = []
        total_segments = 0
        for document_key in sorted(manifest_by_key):
            entry = manifest_by_key[document_key]
            source = selected_by_key[document_key]
            observation = source.observation
            if observation.source_commit != manifest["source_commit"]:
                raise AssertionError("governed observation lost exact source commit")
            if observation.source_path != entry["path"]:
                raise AssertionError("governed observation lost exact source path")
            if observation.git_blob_sha != entry["git_blob_sha"]:
                raise AssertionError("governed observation lost exact Git blob")
            if observation.document_lifecycle.value != entry["retrieval_lifecycle"]:
                raise AssertionError("governed observation lost explicit parent lifecycle")

            version = session.get(ResourceVersion, observation.resource_version_ref)
            if version is None:
                raise AssertionError("governed source lost exact canonical ResourceVersion")
            artifacts.verify(version.artifact_key)
            content = artifacts.read_bytes(version.artifact_key)
            if version.content_digest_algo != "sha256":
                raise AssertionError("SR-2 host qualification expected SHA-256 canonical evidence")
            if sha256(content).hexdigest() != version.content_digest:
                raise AssertionError("canonical artifact bytes do not match ResourceVersion digest")

            lineage = session.get(
                TextGenerationSource,
                {
                    "generation_id": current.generation_id,
                    "resource_version_ref": observation.resource_version_ref,
                },
            )
            if lineage is None:
                raise AssertionError("SR-2 generation lost governed source lineage")
            if lineage.source_observation_id != observation.observation_id:
                raise AssertionError("SR-2 lineage does not bind the exact governed observation")
            if lineage.governing_manifest_digest != manifest_digest:
                raise AssertionError("SR-2 lineage does not bind the governing manifest")
            if lineage.projection_snapshot_digest != source.projection_snapshot_digest:
                raise AssertionError("SR-2 lineage projection digest is not reproducible")

            generic_source = generic_by_version.get(observation.resource_version_ref)
            if generic_source is None:
                raise AssertionError("SR-2 lineage lost source-neutral governed selection")
            if lineage.governed_observation_id != generic_source.observation.observation_id:
                raise AssertionError(
                    "SR-2 lineage does not bind the exact generic governed observation"
                )
            if lineage.governed_decision_id != generic_source.decision.decision_id:
                raise AssertionError(
                    "SR-2 lineage does not bind the exact generic governance decision"
                )
            if lineage.governing_snapshot_digest != snapshot_map.snapshot_digest:
                raise AssertionError(
                    "SR-2 lineage does not bind the complete governed snapshot"
                )
            if lineage.governed_projection_digest != generic_source.projection_digest:
                raise AssertionError(
                    "SR-2 generic projection digest is not reproducible"
                )

            rows = session.scalars(
                select(ResourceSegmentTextSearch)
                .where(
                    ResourceSegmentTextSearch.generation_id == current.generation_id,
                    ResourceSegmentTextSearch.resource_version_ref
                    == observation.resource_version_ref,
                )
                .order_by(ResourceSegmentTextSearch.segment_ordinal)
            ).all()
            if not rows:
                raise AssertionError("SR-2 governed source has no persisted segment rows")
            _verify_structural_rows(
                content=content,
                resource_version_ref=observation.resource_version_ref,
                media_type=version.media_type,
                rows=rows,
            )
            total_segments += len(rows)

            if not all(
                row.source_document_key == document_key
                and row.source_path == entry["path"]
                and row.source_version == manifest["source_commit"]
                for row in rows
            ):
                raise AssertionError("SR-2 segment rows lost pinned source provenance")

            provenance.append(
                {
                    "source_document_key": document_key,
                    "source_commit": observation.source_commit,
                    "path": observation.source_path,
                    "git_blob_sha": observation.git_blob_sha,
                    "resource_ref": str(version.resource_ref_id),
                    "resource_version_ref": str(observation.resource_version_ref),
                    "observation_id": str(observation.observation_id),
                    "content_digest_algo": version.content_digest_algo,
                    "content_digest": version.content_digest,
                    "artifact_verified": True,
                    "governing_manifest_digest": lineage.governing_manifest_digest,
                    "projection_snapshot_digest": lineage.projection_snapshot_digest,
                    "governed_observation_id": str(lineage.governed_observation_id),
                    "governed_decision_id": str(lineage.governed_decision_id),
                    "governing_snapshot_digest": lineage.governing_snapshot_digest,
                    "governed_projection_digest": lineage.governed_projection_digest,
                    "segment_count": len(rows),
                    "segments": [_structural_row_snapshot(row) for row in rows],
                }
            )

        counts = {
            "bindings": _count(session, RepositoryDocumentBinding),
            "receipts": _count(session, RepositoryImportReceipt),
            "observations": _count(session, RepositorySourceObservation),
            "resources": _count(session, Resource),
            "resource_versions": _count(session, ResourceVersion),
            "locators": _count(session, ResourceLocator),
            "generations": _count(session, DerivedGeneration),
            "resource_search_rows": _count(session, ResourceTextSearch),
            "segment_search_rows": _count(session, ResourceSegmentTextSearch),
            "text_generation_sources": _count(session, TextGenerationSource),
            "text_generation_profiles": _count(session, TextGenerationProfile),
        }
        if counts["segment_search_rows"] != total_segments:
            raise AssertionError("SR-2 segment row count disagrees with exact source provenance")

        return {
            "counts": counts,
            "serving_generation": {
                "generation_id": str(current.generation_id),
                "model_identity": current.model_identity,
                "model_version": current.model_version,
                "config_digest": current.config_digest,
                "profile": actual_profile,
                "governing_snapshot_digest": snapshot_map.snapshot_digest,
            },
            "provenance": provenance,
        }
    finally:
        session.close()


def _new_import_kernel(*, sessions, artifacts, reader, manifest):
    session = sessions()
    kernel = SectionRepositoryImportKnowledgeKernel(
        session,
        artifact_store=artifacts,
        source_readers={manifest["source_repository_key"]: reader},
    )
    return session, kernel


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("apply", "recovery"))
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    database_url = os.environ["KNOWLEDGE_CORE_DATABASE_URL"]
    manifest = _load_manifest(Path(args.manifest))
    artifacts = LocalArtifactStore(Path(args.artifact_root))
    reader = GitRepositorySourceReader(
        repository_locator=manifest["repository_locator"],
        repository_root=Path(args.repository_root),
    )
    engine = create_database_engine(database_url)
    sessions = create_session_factory(engine)
    app = create_app(session_factory=sessions, artifact_store=artifacts)

    try:
        if args.phase == "apply":
            session, kernel = _new_import_kernel(
                sessions=sessions,
                artifacts=artifacts,
                reader=reader,
                manifest=manifest,
            )
            try:
                plan = kernel.plan_repository_import(manifest)
                if plan.replay_receipt is not None:
                    raise AssertionError("SR-2 host first apply unexpectedly resolved as replay")
                receipt = kernel.apply_repository_import(
                    manifest=manifest,
                    expected_plan_digest=plan.plan_digest,
                )
                if receipt.status != "settled":
                    raise AssertionError("SR-2 host import receipt did not settle")
                plan_data = _plan_snapshot(plan)
                receipt_data = _receipt_snapshot(receipt)
                manifest_digest = receipt.manifest_digest
            finally:
                session.close()

            with TestClient(app) as client:
                current = _search(client, "qualified runtime", include_superseded=False)
                contract = _search(
                    client,
                    "deterministic large block continuation",
                    include_superseded=False,
                )
                historical_default = _search(
                    client,
                    "acceptance order invariant",
                    include_superseded=False,
                )
                historical_explicit = _search(
                    client,
                    "acceptance order invariant",
                    include_superseded=True,
                )
            snapshot = _snapshot(
                sessions=sessions,
                artifacts=artifacts,
                manifest=manifest,
                manifest_digest=manifest_digest,
            )
            result = {
                "phase": "apply",
                "plan": plan_data,
                "receipt": receipt_data,
                "current": current,
                "contract": contract,
                "historical_default": historical_default,
                "historical_explicit": historical_explicit,
                "snapshot": snapshot,
            }
        else:
            session, kernel = _new_import_kernel(
                sessions=sessions,
                artifacts=artifacts,
                reader=reader,
                manifest=manifest,
            )
            try:
                plan = kernel.plan_repository_import(manifest)
                if plan.replay_receipt is None:
                    raise AssertionError(
                        "accepted SR-2 host manifest did not survive PostgreSQL restart"
                    )
                plan_data = _plan_snapshot(plan)
                manifest_digest = plan.manifest_digest
            finally:
                session.close()

            with TestClient(app) as client:
                current_before_replay = _search(
                    client, "qualified runtime", include_superseded=False
                )
                contract_before_replay = _search(
                    client,
                    "deterministic large block continuation",
                    include_superseded=False,
                )
                historical_default_before_replay = _search(
                    client,
                    "acceptance order invariant",
                    include_superseded=False,
                )
                historical_explicit_before_replay = _search(
                    client,
                    "acceptance order invariant",
                    include_superseded=True,
                )

            before = _snapshot(
                sessions=sessions,
                artifacts=artifacts,
                manifest=manifest,
                manifest_digest=manifest_digest,
            )

            session, kernel = _new_import_kernel(
                sessions=sessions,
                artifacts=artifacts,
                reader=reader,
                manifest=manifest,
            )
            try:
                replay_receipt = kernel.apply_repository_import(
                    manifest=manifest,
                    expected_plan_digest=plan.plan_digest,
                )
                receipt_data = _receipt_snapshot(replay_receipt)
            finally:
                session.close()

            after = _snapshot(
                sessions=sessions,
                artifacts=artifacts,
                manifest=manifest,
                manifest_digest=manifest_digest,
            )
            result = {
                "phase": "recovery",
                "plan": plan_data,
                "receipt": receipt_data,
                "current_before_replay": current_before_replay,
                "contract_before_replay": contract_before_replay,
                "historical_default_before_replay": historical_default_before_replay,
                "historical_explicit_before_replay": historical_explicit_before_replay,
                "before": before,
                "after": after,
            }
    finally:
        engine.dispose()

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())