from __future__ import annotations

import os
from pathlib import Path

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.consumer_admission import ConsumerAdmission
from knowledge_core.application.graph_runtime import KnowledgeGraphRuntime
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.storage.database import create_database_engine, create_session_factory


_DATABASE_URL_ENV = "KNOWLEDGE_CORE_DATABASE_URL"
_ARTIFACT_ROOT_ENV = "KNOWLEDGE_CORE_ARTIFACT_ROOT"
_PORT_ENV = "KNOWLEDGE_CORE_PORT"
_DEFAULT_PORT = 8765


def build_app():
    database_url = os.environ.get(_DATABASE_URL_ENV, "").strip()
    artifact_root = os.environ.get(_ARTIFACT_ROOT_ENV, "").strip()
    if not database_url:
        raise RuntimeError(f"{_DATABASE_URL_ENV} is required")
    if not artifact_root:
        raise RuntimeError(f"{_ARTIFACT_ROOT_ENV} is required")

    engine = create_database_engine(database_url)
    sessions = create_session_factory(engine)
    artifact_store = LocalArtifactStore(Path(artifact_root))
    admission = BootstrapAdmission.from_env()
    consumer_admission = ConsumerAdmission(
        session_factory=sessions,
        owner_bootstrap=admission,
    )
    consumer_admission.ensure_owner_principal()
    graph_runtime = KnowledgeGraphRuntime.from_env(
        session_factory=sessions,
        artifact_store=artifact_store,
    )
    app = create_app(
        session_factory=sessions,
        artifact_store=artifact_store,
        bootstrap_admission=admission,
        consumer_admission=consumer_admission,
        graph_runtime=graph_runtime,
    )
    app.state.knowledge_core_engine = engine
    app.state.knowledge_core_graph_runtime = graph_runtime
    return app


def main() -> int:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            'uvicorn is required for the local service; install Knowledge Core with the "service" extra'
        ) from exc

    admission = BootstrapAdmission.from_env()
    port = int(os.environ.get(_PORT_ENV, str(_DEFAULT_PORT)))
    if port < 1 or port > 65535:
        raise RuntimeError(f"{_PORT_ENV} must be a valid TCP port")
    uvicorn.run(
        build_app(),
        host=admission.contract.bind_host,
        port=port,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
