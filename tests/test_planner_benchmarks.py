"""Planner benchmark separation and integration-config tests."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from acl_controller.configuration import ProfileResolver, ProfileSelector
from tools.planner_integration_benchmark import Candidate, _prepare_candidate_config


ROOT = Path(__file__).resolve().parents[1]


def test_integration_benchmark_uses_production_profile_with_candidate_runtime():
    with TemporaryDirectory() as directory:
        destination = Path(directory)
        config_root, runtime_id = _prepare_candidate_config(
            source_config_root=ROOT / "config",
            destination_root=destination,
            candidate=Candidate(
                name="candidate",
                model="candidate:model",
                context_window=24576,
            ),
        )

        resolver = ProfileResolver(config_root)
        planner = resolver.resolve(
            ProfileSelector("planner", "1127", "MEDIUM")
        )

        assert runtime_id == planner.metadata["runtime_id"]
        assert planner.settings["model"] == "candidate:model"
        assert planner.settings["context_window"] == 24576
        assert planner.settings["response_envelope_mode"] == "payload"
        assert planner.instructions["semantic_contract"]["schema_version"] == (
            "acl-planner-semantic:v1"
        )
        assert planner.tool_profile == "planner-readonly-v1"


def test_loose_and_integration_benchmarks_have_distinct_modes():
    semantic_source = (ROOT / "tools" / "planner_output_benchmark.py").read_text(
        encoding="utf-8"
    )
    integration_source = (
        ROOT / "tools" / "planner_integration_benchmark.py"
    ).read_text(encoding="utf-8")

    assert '"SEMANTIC_ONLY"' in semantic_source
    assert 'BENCHMARK_MODE = "PRODUCTION_INTEGRATION"' in integration_source
