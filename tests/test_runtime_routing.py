from pathlib import Path

import pytest

from acl_controller.authority import FilesystemAuthorityCoordinator
from acl_controller.configuration import ProfileResolver, ProfileSelector
from acl_controller.tools import ToolProfileResolver
from acl_controller.tools.filesystem import FilesystemToolService
from acl_core import AuthorityEnvelope, AuthorityGrant, FilesystemOperation
from acl_core.errors import CoreError
from acl_runtime.pipeline import _accepted_determiner_route


ROOT = Path(__file__).resolve().parents[1]


def test_central_runtime_catalog_selects_role_models():
    resolver = ProfileResolver(ROOT / "config")

    determiner = resolver.resolve(ProfileSelector("determiner", None, None))
    planner = resolver.resolve(ProfileSelector("planner", "1127", "SMALL"))
    worker = resolver.resolve(ProfileSelector("worker", "1127", "SMALL"))

    assert determiner.settings["model"] == "qwen3.5:9b-16k"
    assert determiner.adapter_id == "openai-compatible.chat"
    assert determiner.metadata["runtime_id"] == "determiner-qwen35-9b-16k"

    assert planner.settings["model"] == "qwen3.5:9b-16k"
    assert planner.adapter_id == "openai-compatible.agent"
    assert planner.metadata["runtime_id"] == "planner-qwen35-9b-16k"
    assert planner.metadata["harness_id"] == "openai-compatible.agent"
    assert planner.tool_profile == "planner-readonly-v1"

    assert worker.settings["model"] == "qwen3-coder:30b-16k"
    assert worker.adapter_id == "openai-compatible.agent"
    assert worker.metadata["runtime_id"] == "worker-qwen3-coder-30b-16k"


def test_pipeline_extracts_accepted_determiner_route():
    result = {
        "inspection": {
            "results": [
                {
                    "executor": "ROLE",
                    "payload": {
                        "classification": "CLASSIFIED",
                        "work_type_id": "1127",
                        "complexity": "SMALL",
                    },
                }
            ]
        }
    }

    assert _accepted_determiner_route(result) == ("1127", "SMALL")


def test_pipeline_stops_when_determiner_does_not_classify():
    result = {
        "inspection": {
            "results": [
                {
                    "executor": "ROLE",
                    "payload": {
                        "classification": "UNKNOWN",
                        "work_type_id": None,
                        "complexity": None,
                    },
                }
            ]
        }
    }

    assert _accepted_determiner_route(result) is None

def test_planner_inspects_material_files_with_read_only_tools():
    resolver = ProfileResolver(ROOT / "config")
    planner = resolver.resolve(ProfileSelector("planner", "1127", "SMALL"))

    rules = planner.instructions["planning_rules"]
    assert any(
        "inspect them with available read-only tools before planning" in rule
        for rule in rules
    )

    tool_profiles = ToolProfileResolver(ROOT / "config" / "tool_profiles.json")
    assert tool_profiles.resolve(planner.tool_profile) == (
        "filesystem.list_directory",
        "filesystem.read_text",
    )


def test_planner_read_wildcard_does_not_grant_mutation():
    coordinator = FilesystemAuthorityCoordinator.create(
        project_root=ROOT,
        state_root=ROOT / ".acl-state-test-read",
        config_root=ROOT / "config",
    )
    tools = FilesystemToolService(coordinator)
    grant = AuthorityGrant(
        grant_id="grant:test-planner-read",
        issuer="test",
        subject="planner",
        authority=AuthorityEnvelope(
            capabilities=("filesystem.read",),
            resource_scopes=("filesystem:READ:*",),
            tool_scopes=(
                "filesystem.list_directory",
                "filesystem.read_text",
            ),
        ),
    )

    tools._require_resource_scope(
        grant,
        FilesystemOperation.READ,
        str(ROOT / "worker_probe_case2" / "task_spec.txt"),
    )

    with pytest.raises(CoreError):
        tools._require_resource_scope(
            grant,
            FilesystemOperation.WRITE,
            str(ROOT / "worker_probe_case2" / "calculator.py"),
        )

