from __future__ import annotations

import json
from pathlib import Path

from knowledge_core_providers.graphiti import GraphitiLocalConfig, GraphitiProjectionAdapter
from knowledge_core_providers.qualification_events import (
    ObservableGraphitiProjectionAdapter,
    QualificationEventRecorder,
    aggregate_llm_metrics,
    latest_event,
    open_llm_requests,
)
from knowledge_core_providers.qualification_preflight import (
    PreflightCheck,
    PreflightReport,
    model_is_installed,
)


def test_event_recorder_writes_jsonl_and_keeps_recent_events(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    recorder = QualificationEventRecorder(path)

    first = recorder.emit("qualification_started", attempt_id="a")
    second = recorder.emit("segment_started", segment_key="s1")

    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert [item["event_type"] for item in recorder.snapshot()] == [
        "qualification_started",
        "segment_started",
    ]
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["sequence"] for row in rows] == [1, 2]
    assert recorder.errors == ()


def test_llm_metric_aggregation_and_open_request_detection() -> None:
    events = [
        {
            "event_type": "llm_request_started",
            "request_id": "r1",
            "stage": "ExtractedNodes",
            "prompt_characters": 100,
        },
        {
            "event_type": "llm_request_completed",
            "request_id": "r1",
            "stage": "ExtractedNodes",
            "duration_seconds": 2.0,
            "prompt_tokens": 25,
            "completion_tokens": 10,
            "total_tokens": 35,
            "response_characters": 80,
        },
        {
            "event_type": "llm_request_started",
            "request_id": "r2",
            "stage": "ExtractedEdges",
            "prompt_characters": 200,
        },
    ]

    metrics = aggregate_llm_metrics(events)
    assert metrics["request_count"] == 1
    assert metrics["prompt_tokens"] == 25
    assert metrics["completion_tokens"] == 10
    assert metrics["aggregate_completion_tokens_per_second"] == 5.0
    assert metrics["prompt_characters"] == 300
    assert metrics["response_characters"] == 80
    assert metrics["stages"] == {"ExtractedNodes": 1}
    assert [item["request_id"] for item in open_llm_requests(events)] == ["r2"]
    assert latest_event(events, "llm_request_started")["request_id"] == "r2"


def test_model_alias_matching_accepts_implicit_latest() -> None:
    installed = {"graphiti-qwen35-9b-32k:latest", "nomic-embed-text:latest"}
    assert model_is_installed("graphiti-qwen35-9b-32k", installed)
    assert model_is_installed("nomic-embed-text:latest", installed)
    assert not model_is_installed("qwen3.8:27b", installed)


def test_preflight_ready_uses_only_required_checks() -> None:
    report = PreflightReport(
        (
            PreflightCheck("required", True, "PASS", "ok"),
            PreflightCheck("optional", False, "WARN", "offline"),
        )
    )
    assert report.ready

    blocked = PreflightReport(
        (
            PreflightCheck("required", True, "FAIL", "offline"),
            PreflightCheck("optional", False, "PASS", "ok"),
        )
    )
    assert not blocked.ready


def test_observable_adapter_preserves_behavioral_descriptor(tmp_path: Path) -> None:
    config = GraphitiLocalConfig(llm_model="graphiti-qwen35-9b-32k")
    base = GraphitiProjectionAdapter(config)
    observed = ObservableGraphitiProjectionAdapter(
        config,
        recorder=QualificationEventRecorder(tmp_path / "events.jsonl"),
    )

    assert observed.descriptor == base.descriptor
    assert observed.config.behavioral_digest() == base.config.behavioral_digest()
