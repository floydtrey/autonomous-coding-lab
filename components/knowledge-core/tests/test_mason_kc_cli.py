from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


def _load_tool(filename: str, module_name: str):
    tools = Path(__file__).resolve().parents[1] / "tools"
    path = tools / filename
    added = str(tools)
    if added not in sys.path:
        sys.path.insert(0, added)
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("argv", "operation", "payload"),
    [
        (["status"], "kc_status", {}),
        (["search", "--query", "What is Mason?", "--limit", "7"], "kc_search", {"query": "What is Mason?", "limit": 7}),
        (["get-source", "--ref", "rv-1"], "kc_get_source", {"resource_version_ref": "rv-1"}),
        (["propose-memory", "--project", "knowledge-core", "--content", "Observed bounded continuation."], "kc_propose_memory", {"project": "knowledge-core", "content": "Observed bounded continuation."}),
        (["store", "--project", "local-ai", "--content", "Explicit fact.", "--source-id", "explicit-fact"], "kc_store", {"project": "local-ai", "content": "Explicit fact.", "source_id": "explicit-fact"}),
    ],
)
def test_mason_kc_cli_maps_commands_to_exact_bridge_operations(argv, operation, payload, monkeypatch, capsys):
    module = _load_tool("mason_kc_cli.py", "task6i_mason_kc_cli")
    calls = []

    def fake_execute(op, body):
        calls.append((op, body))
        return {"state": "ok"}

    monkeypatch.setattr(module.mason_kc_bridge, "execute", fake_execute)
    assert module.main(argv) == 0
    assert calls == [(operation, payload)]
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert output["contract"] == "mason-kc-cli-v1"
    assert output["operation"] == operation


def test_mason_kc_cli_fails_closed_on_bridge_error(monkeypatch, capsys):
    module = _load_tool("mason_kc_cli.py", "task6i_mason_kc_cli_error")

    def fail_execute(_operation, _payload):
        raise module.mason_kc_bridge.BridgeError("bridge unavailable")

    monkeypatch.setattr(module.mason_kc_bridge, "execute", fail_execute)
    assert module.main(["status"]) == 1
    error = json.loads(capsys.readouterr().err)
    assert error["ok"] is False
    assert error["contract"] == "mason-kc-cli-v1"
    assert error["operation"] == "kc_status"
