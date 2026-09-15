from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

from knowledge_core_providers.graphiti import GraphitiProjectionAdapter
from knowledge_core_providers.graphiti_hardened import (
    GRAPHITI_MAX_COROUTINES,
    GRAPHITI_SEMAPHORE_LIMIT,
    GRAPHITI_TELEMETRY_ENABLED,
    HARDENING_CONTRACT,
    QUALIFIED_GRAPH_SEARCH_MODE,
    HardenedGraphitiProjectionAdapter,
    _hardened_graphiti_type,
    _serialized_falkor_types,
)


def test_task4_1_hardening_contract_is_behavior_versioned_and_local():
    base = GraphitiProjectionAdapter().descriptor
    hardened = HardenedGraphitiProjectionAdapter().descriptor

    assert hardened.backend_identity == base.backend_identity
    assert hardened.backend_version == base.backend_version
    assert hardened.validation_requirement == base.validation_requirement
    assert hardened.adapter_identity == "kc-graphiti-falkordb-ollama-serialized"
    assert hardened.adapter_version == "3"
    assert hardened.config_digest != base.config_digest

    assert HARDENING_CONTRACT.graphiti_max_coroutines == 1
    assert HARDENING_CONTRACT.semaphore_limit == 1
    assert HARDENING_CONTRACT.telemetry_enabled is False
    assert HARDENING_CONTRACT.search_mode == "edge-hybrid-rrf"
    assert GRAPHITI_MAX_COROUTINES == 1
    assert GRAPHITI_SEMAPHORE_LIMIT == 1
    assert GRAPHITI_TELEMETRY_ENABLED is False
    assert QUALIFIED_GRAPH_SEARCH_MODE == "edge-hybrid-rrf"
    assert os.environ["SEMAPHORE_LIMIT"] == "1"
    assert os.environ["GRAPHITI_TELEMETRY_ENABLED"] == "false"


class _ConcurrencyProbe:
    def __init__(self):
        self.active = 0
        self.max_active = 0

    async def touch(self):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.001)
        self.active -= 1
        return "ok"


class _FakeSession:
    provider = "fake"

    def __init__(self, graph):
        self.graph = graph

    async def run(self, query, **kwargs):
        return await self.graph.touch()


class _FakeDriver:
    default_group_id = "_"

    def __init__(self, *args, falkor_db=None, database="default_db", **kwargs):
        self.client = falkor_db or SimpleNamespace()
        self._database = database
        self._init_task = None
        self.probe = kwargs.pop("probe", None) or _ConcurrencyProbe()

    async def execute_query(self, cypher_query_, **kwargs):
        return await self.probe.touch()

    def _get_graph(self, database=None):
        return self.probe


def test_task4_1_serialized_driver_covers_direct_and_session_query_paths():
    SerializedDriver, _ = _serialized_falkor_types(_FakeDriver, _FakeSession)
    driver = SerializedDriver()

    async def exercise():
        direct = [driver.execute_query("RETURN 1") for _ in range(8)]
        session = driver.session()
        indirect = [session.run("RETURN 1") for _ in range(8)]
        await asyncio.gather(*(direct + indirect))

    asyncio.run(exercise())
    assert driver.probe.max_active == 1


class _ClosingClient:
    def __init__(self):
        self.close_count = 0

    async def close(self):
        self.close_count += 1


class _FakeGraphitiBase:
    def __init__(self):
        self.base_close_count = 0

    async def close(self):
        self.base_close_count += 1


def test_task4_1_hardened_graphiti_closes_unique_async_clients_before_loop_exit():
    Hardened = _hardened_graphiti_type(_FakeGraphitiBase)
    graphiti = Hardened()
    shared = _ClosingClient()
    embedder = _ClosingClient()
    graphiti.llm_client = SimpleNamespace(client=shared)
    graphiti.cross_encoder = SimpleNamespace(client=shared)
    graphiti.embedder = SimpleNamespace(client=embedder)

    asyncio.run(graphiti.close())

    assert graphiti.base_close_count == 1
    assert shared.close_count == 1
    assert embedder.close_count == 1
