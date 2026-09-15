from __future__ import annotations

import asyncio
from dataclasses import dataclass
from hashlib import sha256
import inspect
import json
import os
from typing import Any

# Graphiti reads SEMAPHORE_LIMIT at module-import time in helpers.py. Keep these
# settings above every graphiti_core import in this module. The operator wrapper
# imports this module before the historical Task 4 tool/provider can import
# Graphiti itself.
os.environ["SEMAPHORE_LIMIT"] = "1"
os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "false"

from knowledge_core.domain.projection_adapter import ProjectionAdapterDescriptor
from knowledge_core_providers.graphiti import (
    GraphitiProjectionAdapter,
    _governed_document_graphiti_type,
    _reasoning_disabled_client,
    _require_graphiti_version,
)


_HARDENED_ADAPTER_IDENTITY = "kc-graphiti-falkordb-ollama-serialized"
_HARDENED_ADAPTER_VERSION = "3"
QUALIFIED_GRAPH_SEARCH_MODE = "edge-hybrid-rrf"
GRAPHITI_MAX_COROUTINES = 1
GRAPHITI_SEMAPHORE_LIMIT = 1
GRAPHITI_TELEMETRY_ENABLED = False


@dataclass(frozen=True)
class GraphitiHardeningContract:
    graphiti_max_coroutines: int = GRAPHITI_MAX_COROUTINES
    semaphore_limit: int = GRAPHITI_SEMAPHORE_LIMIT
    telemetry_enabled: bool = GRAPHITI_TELEMETRY_ENABLED
    search_mode: str = QUALIFIED_GRAPH_SEARCH_MODE
    falkor_access: str = "serialized-driver-and-session"
    async_client_cleanup: str = "explicit"

    def digest(self, *, base_config_digest: str) -> str:
        payload = {
            "async_client_cleanup": self.async_client_cleanup,
            "base_config_digest": base_config_digest,
            "falkor_access": self.falkor_access,
            "graphiti_max_coroutines": self.graphiti_max_coroutines,
            "search_mode": self.search_mode,
            "semaphore_limit": self.semaphore_limit,
            "telemetry_enabled": self.telemetry_enabled,
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return "sha256:" + sha256(encoded).hexdigest()


HARDENING_CONTRACT = GraphitiHardeningContract()


def _serialized_falkor_types(base_driver_type, base_session_type):
    """Build Falkor classes that serialize all KC-visible graph queries.

    FalkorDriver 0.30.2 exposes two query routes used by Graphiti: direct
    ``execute_query`` calls and ``session().run`` calls. Both share one async
    Falkor client/connection, so the hardened profile puts one lock in front of
    both routes. Clones share that same lock with the same underlying client.
    """

    class SerializedFalkorSession(base_session_type):
        def __init__(self, graph, query_lock: asyncio.Lock):
            super().__init__(graph)
            self._kc_query_lock = query_lock

        async def run(self, query, **kwargs):
            async with self._kc_query_lock:
                return await super().run(query, **kwargs)

    class SerializedFalkorDriver(base_driver_type):
        def __init__(self, *args, _kc_query_lock: asyncio.Lock | None = None, **kwargs):
            self._kc_query_lock = _kc_query_lock or asyncio.Lock()
            super().__init__(*args, **kwargs)

        async def execute_query(self, cypher_query_, **kwargs):
            async with self._kc_query_lock:
                return await super().execute_query(cypher_query_, **kwargs)

        def session(self, database: str | None = None):
            return SerializedFalkorSession(
                self._get_graph(database),
                self._kc_query_lock,
            )

        def clone(self, database: str):
            if database == self._database:
                return self
            target = None if database == self.default_group_id else database
            kwargs: dict[str, Any] = {
                "falkor_db": self.client,
                "_kc_query_lock": self._kc_query_lock,
            }
            if target is not None:
                kwargs["database"] = target
            return SerializedFalkorDriver(**kwargs)

    SerializedFalkorSession.__name__ = "KCSerializedFalkorSession"
    SerializedFalkorDriver.__name__ = "KCSerializedFalkorDriver"
    return SerializedFalkorDriver, SerializedFalkorSession


async def _close_async_client(client: Any) -> None:
    if client is None:
        return
    close = getattr(client, "close", None)
    if close is None:
        close = getattr(client, "aclose", None)
    if close is None:
        return
    result = close()
    if inspect.isawaitable(result):
        await result


def _hardened_graphiti_type(base_type: type[Any]) -> type[Any]:
    class HardenedGraphiti(base_type):
        async def close(self):
            first_error: BaseException | None = None
            try:
                await super().close()
            except BaseException as exc:  # cleanup must continue across all clients
                first_error = exc

            # graphiti-core 0.30.2 closes its graph driver but does not close the
            # OpenAI-compatible async HTTP clients used by the LLM/embedder/reranker.
            # Explicitly close each unique underlying client before the event loop
            # exits so one-shot host tools do not leave httpx close tasks behind.
            targets = (
                getattr(getattr(self, "llm_client", None), "client", None),
                getattr(getattr(self, "embedder", None), "client", None),
                getattr(getattr(self, "cross_encoder", None), "client", None),
            )
            seen: set[int] = set()
            for target in targets:
                if target is None or id(target) in seen:
                    continue
                seen.add(id(target))
                try:
                    await _close_async_client(target)
                except BaseException as exc:
                    if first_error is None:
                        first_error = exc
            if first_error is not None:
                raise first_error

    HardenedGraphiti.__name__ = "KCHardenedGovernedDocumentGraphiti"
    return HardenedGraphiti


class HardenedGraphitiProjectionAdapter(GraphitiProjectionAdapter):
    """Task 4.1 local Graphiti profile hardened for FalkorDB/Ollama.

    This preserves the accepted governed-document projection and validator
    semantics while changing runtime behavior only: serialized Falkor queries,
    single-coroutine Graphiti fan-out, telemetry disabled, explicit HTTP-client
    cleanup, and the already-qualified RRF search path.
    """

    @property
    def descriptor(self) -> ProjectionAdapterDescriptor:
        base = super().descriptor
        return ProjectionAdapterDescriptor(
            backend_identity=base.backend_identity,
            backend_version=base.backend_version,
            adapter_identity=_HARDENED_ADAPTER_IDENTITY,
            adapter_version=_HARDENED_ADAPTER_VERSION,
            config_digest=HARDENING_CONTRACT.digest(
                base_config_digest=base.config_digest,
            ),
            validation_requirement=base.validation_requirement,
        )

    def _build_graphiti(self, *, partition_key: str):
        _require_graphiti_version()

        # Be robust even if another caller imported graphiti_core before this
        # adapter. The env var remains the process contract; assigning the loaded
        # helper constant closes the import-order hole for this dedicated profile.
        os.environ["SEMAPHORE_LIMIT"] = str(GRAPHITI_SEMAPHORE_LIMIT)
        os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "false"

        from graphiti_core import Graphiti
        from graphiti_core import helpers as graphiti_helpers
        from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
        from graphiti_core.driver.falkordb_driver import FalkorDriver, FalkorDriverSession
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
        from graphiti_core.llm_client.config import LLMConfig

        graphiti_helpers.SEMAPHORE_LIMIT = GRAPHITI_SEMAPHORE_LIMIT

        GovernedGraphiti = _governed_document_graphiti_type(Graphiti)
        HardenedGraphiti = _hardened_graphiti_type(GovernedGraphiti)
        SerializedFalkorDriver, _ = _serialized_falkor_types(
            FalkorDriver,
            FalkorDriverSession,
        )

        llm_config = LLMConfig(
            api_key=self.config.ollama_api_key,
            model=self.config.llm_model,
            small_model=self.config.llm_model,
            base_url=self.config.ollama_base_url,
            temperature=self.config.temperature,
            max_tokens=self.config.llm_max_tokens,
        )
        llm_client = _reasoning_disabled_client(
            llm_config,
            max_tokens=self.config.llm_max_tokens,
            structured_output_mode=self.config.structured_output_mode,
        )
        embedder = OpenAIEmbedder(
            config=OpenAIEmbedderConfig(
                api_key=self.config.ollama_api_key,
                base_url=self.config.ollama_base_url,
                embedding_model=self.config.embed_model,
                embedding_dim=self.config.embed_dim,
            )
        )

        # The accepted V1 retrieval path calls Graphiti.search(), whose 0.30.2
        # recipe is EDGE_HYBRID_SEARCH_RRF. The cross encoder is retained only to
        # satisfy the Graphiti object contract; Task 4.1 does not qualify search_()
        # or the OpenAI-token-ID reranker path.
        reranker = OpenAIRerankerClient(config=llm_config, client=llm_client.client)
        driver = SerializedFalkorDriver(
            host=self.config.falkor_host,
            port=self.config.falkor_port,
            username=self.config.falkor_username,
            password=self.config.falkor_password,
            database=partition_key,
        )
        return HardenedGraphiti(
            graph_driver=driver,
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=reranker,
            max_coroutines=GRAPHITI_MAX_COROUTINES,
        )
