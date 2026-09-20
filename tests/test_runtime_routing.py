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

    assert determiner.settings["model"] == "laguna-xs-2.1:4k"
    assert determiner.settings["context_window"] == 4096
    assert determiner.settings["max_tokens"] == 2048
    assert determiner.adapter_id == "openai-compatible.chat"
    assert determiner.metadata["runtime_id"] == "determiner-laguna-xs-2-1-4k"

    assert planner.settings["model"] == "gpt-oss:20b-16k"
    assert planner.settings["context_window"] == 16384
    assert planner.settings["max_tokens"] == 8192
    assert planner.adapter_id == "openai-compatible.agent"
    assert planner.metadata["runtime_id"] == "planner-gpt-oss-20b-16k-dev"
    assert planner.metadata["harness_id"] == "openai-compatible.agent"
    assert planner.tool_profile == "planner-readonly-v1"

    assert worker.settings["model"] == "qwen3-coder:30b-131k"
    assert worker.settings["context_window"] == 131072
    assert worker.settings["max_tokens"] == 32768
    assert worker.settings.get("suppress_identical_success_calls") is not True
    assert worker.adapter_id == "openai-compatible.agent"
    assert worker.metadata["runtime_id"] == "worker-qwen3-coder-30b-131k"


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
        "inspect them with the available read-only list/read/search tools" in rule
        for rule in rules
    )

    tool_profiles = ToolProfileResolver(ROOT / "config" / "tool_profiles.json")
    assert tool_profiles.resolve(planner.tool_profile) == (
        "filesystem.list_directory",
        "filesystem.read_text",
        "filesystem.search",
    )


def test_production_planner_read_grant_includes_search_only_read_tools(tmp_path):
    from acl_controller.authority import AuthorityCoordinator, JsonGrantStore
    from acl_controller.dispatch.lifecycle import RoleAttemptLifecycleService
    from acl_controller.planner.runtime import ControllerPlannerRuntimeBackend
    from acl_controller.state import JsonWorkflowStore, WorkflowStateService
    from acl_core import CoreServices

    core = CoreServices.create()
    state = WorkflowStateService(JsonWorkflowStore(tmp_path / "state"))
    backend = ControllerPlannerRuntimeBackend(
        profiles=ProfileResolver(ROOT / "config"),
        role_dispatch=None,
        authority=AuthorityCoordinator(
            core.authority,
            JsonGrantStore(tmp_path / "grants"),
        ),
        lifecycle=RoleAttemptLifecycleService(state),
    )

    grant = backend._planner_read_grant()

    assert grant.authority.capabilities == ("filesystem.read",)
    assert grant.authority.tool_scopes == (
        "filesystem.list_directory",
        "filesystem.read_text",
        "filesystem.search",
    )
    assert not any(
        tool_id in grant.authority.tool_scopes
        for tool_id in (
            "filesystem.write_text",
            "filesystem.create_text",
            "filesystem.delete_path",
            "filesystem.move_path",
        )
    )


def test_planner_profile_exposes_small_semantic_contract():
    resolver = ProfileResolver(ROOT / "config")
    planner = resolver.resolve(ProfileSelector("planner", "1127", "SMALL"))

    contract = planner.instructions["semantic_contract"]
    execution = contract["execution_plan"]

    assert contract["schema_version"] == "acl-planner-semantic:v1"
    assert set(execution) == {
        "schema_version",
        "disposition",
        "objective",
        "constraints",
        "passes",
    }
    serialized = str(planner.instructions)
    for controller_field in (
        "worker_working_directory",
        "required_capabilities",
        "required_tools",
        "reference_material",
        "decomposition_reason",
        "filesystem_intent_shape",
    ):
        assert controller_field not in serialized
    assert "instruction_sources" not in planner.metadata
    assert planner.settings["response_envelope_mode"] == "payload"


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
                "filesystem.search",
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

