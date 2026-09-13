from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from knowledge_core.api.repository_import_app import create_repository_import_app
from knowledge_core.application.repository_source import GitRepositorySourceReader
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.generation_models import DerivedGeneration
from knowledge_core.storage.repository_import_models import (
    RepositoryDocumentBinding,
    RepositoryImportReceipt,
    RepositorySourceObservation,
)
from knowledge_core.storage.resource_models import Resource, ResourceLocator, ResourceVersion
from knowledge_core.storage.retrieval_models import ResourceTextSearch


_CALLER = {"X-Knowledge-Caller": "ri4-host-qualification"}


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _count(session, model) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _snapshot(sessions, artifacts: LocalArtifactStore, manifest_digest: str) -> dict:
    session = sessions()
    try:
        counts = {
            "bindings": _count(session, RepositoryDocumentBinding),
            "receipts": _count(session, RepositoryImportReceipt),
            "observations": _count(session, RepositorySourceObservation),
            "resources": _count(session, Resource),
            "resource_versions": _count(session, ResourceVersion),
            "locators": _count(session, ResourceLocator),
            "generations": _count(session, DerivedGeneration),
            "search_rows": _count(session, ResourceTextSearch),
        }
        observations = session.scalars(
            select(RepositorySourceObservation)
            .where(RepositorySourceObservation.manifest_digest == manifest_digest)
            .order_by(RepositorySourceObservation.source_document_key)
        ).all()
        provenance = []
        for observation in observations:
            version = session.get(ResourceVersion, observation.resource_version_ref)
            if version is None:
                raise AssertionError("source observation lost its exact ResourceVersion")
            artifacts.verify(version.artifact_key)
            provenance.append(
                {
                    "source_document_key": observation.source_document_key,
                    "source_commit": observation.source_commit,
                    "path": observation.path,
                    "git_blob_sha": observation.git_blob_sha,
                    "resource_ref": str(observation.resource_ref),
                    "resource_version_ref": str(observation.resource_version_ref),
                    "content_digest_algo": version.content_digest_algo,
                    "content_digest": version.content_digest,
                    "artifact_verified": True,
                }
            )
        return {"counts": counts, "provenance": provenance}
    finally:
        session.close()


def _post(client: TestClient, route: str, payload: dict) -> dict:
    response = client.post(route, headers=_CALLER, json=payload)
    if response.status_code != 200:
        raise AssertionError(f"{route} failed: {response.status_code} {response.text}")
    return response.json()


def _search(client: TestClient, query: str, *, include_superseded: bool) -> dict:
    return _post(
        client,
        "/v1/retrieval/search",
        {
            "query": query,
            "limit": 10,
            "include_superseded": include_superseded,
        },
    )


def _plan(client: TestClient, manifest: dict) -> dict:
    return _post(client, "/v1/repository-import/plan", {"manifest": manifest})


def _apply(client: TestClient, manifest: dict, plan_digest: str) -> dict:
    return _post(
        client,
        "/v1/repository-import/apply",
        {"manifest": manifest, "plan_digest": plan_digest},
    )


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
    app = create_repository_import_app(
        session_factory=sessions,
        artifact_store=artifacts,
        source_readers={manifest["source_repository_key"]: reader},
    )

    try:
        with TestClient(app) as client:
            if args.phase == "apply":
                plan = _plan(client, manifest)
                if plan["replay"]:
                    raise AssertionError("RI-4 first apply unexpectedly resolved as replay")
                receipt = _apply(client, manifest, plan["plan_digest"])
                if receipt["status"] != "settled":
                    raise AssertionError("RI-4 import receipt did not settle")
                current = _search(
                    client,
                    "application process persistence",
                    include_superseded=False,
                )
                historical_default = _search(
                    client,
                    "operational receipt status transitions",
                    include_superseded=False,
                )
                historical_explicit = _search(
                    client,
                    "operational receipt status transitions",
                    include_superseded=True,
                )
                snapshot = _snapshot(sessions, artifacts, receipt["manifest_digest"])
                result = {
                    "phase": "apply",
                    "plan": plan,
                    "receipt": receipt,
                    "current": current,
                    "historical_default": historical_default,
                    "historical_explicit": historical_explicit,
                    "snapshot": snapshot,
                }
            else:
                plan = _plan(client, manifest)
                if not plan["replay"]:
                    raise AssertionError(
                        "accepted RI-4 manifest did not survive PostgreSQL restart"
                    )
                lookup_session = sessions()
                try:
                    receipt_row = lookup_session.get(
                        RepositoryImportReceipt,
                        plan["manifest_digest"],
                    )
                    if receipt_row is None or receipt_row.status != "settled":
                        raise AssertionError(
                            "accepted RI-4 receipt did not survive PostgreSQL restart"
                        )
                    manifest_digest = receipt_row.manifest_digest
                finally:
                    lookup_session.close()

                current_before_replay = _search(
                    client,
                    "application process persistence",
                    include_superseded=False,
                )
                historical_before_replay = _search(
                    client,
                    "operational receipt status transitions",
                    include_superseded=True,
                )
                before = _snapshot(sessions, artifacts, manifest_digest)
                receipt = _apply(client, manifest, plan["plan_digest"])
                after = _snapshot(sessions, artifacts, manifest_digest)
                result = {
                    "phase": "recovery",
                    "plan": plan,
                    "receipt": receipt,
                    "current_before_replay": current_before_replay,
                    "historical_before_replay": historical_before_replay,
                    "before": before,
                    "after": after,
                }
    finally:
        engine.dispose()

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
