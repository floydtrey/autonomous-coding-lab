from __future__ import annotations

from hashlib import sha256
import json

import pytest

from knowledge_core.integrations.context_compaction import (
    ContextReference,
    ContextReferenceKind,
    MAX_CHECKPOINT_UTF8_BYTES,
    RecentAction,
    RecentActionOutcome,
    WorkingContextCheckpoint,
    reduce_tool_output,
)


def _ref(
    kind: ContextReferenceKind,
    ref: str,
    content: str | None = None,
) -> ContextReference:
    digest = sha256(content.encode("utf-8")).hexdigest() if content is not None else None
    return ContextReference(kind=kind, ref=ref, sha256_hex=digest)


def test_checkpoint_is_deterministic_and_preserves_required_sections():
    raw = "pytest output stored elsewhere"
    reduction = reduce_tool_output(
        tool_name="pytest",
        invocation_ref="tool:pytest:17",
        raw_output_ref="artifact://runs/17/pytest.txt",
        raw_output=raw,
    )
    checkpoint = WorkingContextCheckpoint(
        objective="Finish Task 6H without changing runtime authority.",
        immutable_constraints=(
            "Do not run a provider/model.",
            "Knowledge Core durable memory remains separate from worker context.",
        ),
        evidence_refs=(
            _ref(ContextReferenceKind.KC_EVIDENCE, "kc://resource-version/abc"),
        ),
        completed_work=("Task 6G merged at 7955cbd9.",),
        current_state="6H deterministic compaction core is under qualification.",
        blockers=("MindsHub integration is deferred to Task 6I.",),
        recent_actions=(
            RecentAction(
                action="Ran deterministic pytest qualification.",
                outcome=RecentActionOutcome.SUCCEEDED,
                refs=(
                    _ref(
                        ContextReferenceKind.TOOL_OUTPUT,
                        "artifact://runs/17/pytest.txt",
                        raw,
                    ),
                ),
            ),
        ),
        source_output_refs=(
            _ref(ContextReferenceKind.SOURCE, "git://commit/7955cbd9"),
            _ref(
                ContextReferenceKind.TOOL_OUTPUT,
                "artifact://runs/17/pytest.txt",
                raw,
            ),
        ),
        reduced_tool_outputs=(reduction,),
    )

    same = WorkingContextCheckpoint(
        objective=checkpoint.objective,
        immutable_constraints=checkpoint.immutable_constraints,
        evidence_refs=checkpoint.evidence_refs,
        completed_work=checkpoint.completed_work,
        current_state=checkpoint.current_state,
        blockers=checkpoint.blockers,
        recent_actions=checkpoint.recent_actions,
        source_output_refs=checkpoint.source_output_refs,
        reduced_tool_outputs=checkpoint.reduced_tool_outputs,
    )

    assert checkpoint.checkpoint_digest == same.checkpoint_digest
    rendered = json.loads(checkpoint.render_for_model())
    assert rendered["objective"] == checkpoint.objective
    assert rendered["immutable_constraints"] == list(checkpoint.immutable_constraints)
    assert rendered["completed_work"] == list(checkpoint.completed_work)
    assert rendered["current_state"] == checkpoint.current_state
    assert rendered["blockers"] == list(checkpoint.blockers)
    assert rendered["checkpoint_digest"] == checkpoint.checkpoint_digest
    assert rendered["source_output_refs"][1]["ref"] == "artifact://runs/17/pytest.txt"
    assert rendered["reduced_tool_outputs"][0]["raw_output_ref"] == "artifact://runs/17/pytest.txt"


def test_checkpoint_chain_digest_changes_when_state_changes():
    first = WorkingContextCheckpoint(
        objective="Keep the worker on one bounded task.",
        immutable_constraints=("Do not expand scope.",),
        evidence_refs=(),
        completed_work=(),
        current_state="Initial state.",
        blockers=(),
        recent_actions=(),
        source_output_refs=(),
    )
    second = WorkingContextCheckpoint(
        objective=first.objective,
        immutable_constraints=first.immutable_constraints,
        evidence_refs=(),
        completed_work=("One step completed.",),
        current_state="Advanced state.",
        blockers=(),
        recent_actions=(),
        source_output_refs=(),
        previous_checkpoint_digest=first.checkpoint_digest,
    )

    assert second.previous_checkpoint_digest == first.checkpoint_digest
    assert second.checkpoint_digest != first.checkpoint_digest


def test_short_tool_output_is_preserved_exactly_with_raw_identity():
    raw = "3 passed in 0.12s\n"
    reduction = reduce_tool_output(
        tool_name="pytest",
        invocation_ref="tool:pytest:short",
        raw_output_ref="artifact://pytest-short.txt",
        raw_output=raw,
    )

    assert reduction.truncated is False
    assert reduction.excerpt == raw
    assert reduction.raw_sha256 == sha256(raw.encode("utf-8")).hexdigest()
    assert reduction.raw_output_ref == "artifact://pytest-short.txt"
    assert reduction.omitted_line_count == 0
    assert reduction.selected_line_numbers == ()


def test_long_tool_output_keeps_boundaries_and_diagnostics_without_synthesis():
    lines = [f"ordinary line {index}" for index in range(1, 81)]
    lines[19] = "WARNING: retry occurred"
    lines[39] = "ERROR: exact failure detail"
    lines[59] = "blocked by policy"
    raw = "\n".join(lines) + "\n"

    reduction = reduce_tool_output(
        tool_name="worker",
        invocation_ref="tool:worker:long",
        raw_output_ref="artifact://worker-long.log",
        raw_output=raw,
        max_excerpt_utf8_bytes=512,
        head_lines=2,
        tail_lines=2,
        max_diagnostic_lines=8,
    )

    assert reduction.truncated is True
    assert reduction.raw_sha256 == sha256(raw.encode("utf-8")).hexdigest()
    assert reduction.raw_line_count == 80
    assert reduction.selected_line_numbers == (1, 2, 20, 40, 60, 79, 80)
    assert reduction.omitted_line_count == 73
    assert "[L1] ordinary line 1" in reduction.excerpt
    assert "[L20] WARNING: retry occurred" in reduction.excerpt
    assert "[L40] ERROR: exact failure detail" in reduction.excerpt
    assert "[L60] blocked by policy" in reduction.excerpt
    assert "[L80] ordinary line 80" in reduction.excerpt
    assert len(reduction.excerpt.encode("utf-8")) <= 512


def test_long_tool_output_reduction_is_repeatable():
    raw = "\n".join(["start"] + [f"line {i}" for i in range(100)] + ["ERROR final", "tail"])
    kwargs = {
        "tool_name": "build",
        "invocation_ref": "tool:build:1",
        "raw_output_ref": "artifact://build.log",
        "raw_output": raw,
        "max_excerpt_utf8_bytes": 768,
    }
    first = reduce_tool_output(**kwargs)
    second = reduce_tool_output(**kwargs)

    assert first == second


def test_tool_output_reduction_requires_exact_raw_reference():
    with pytest.raises(ValueError, match="raw_output_ref"):
        reduce_tool_output(
            tool_name="pytest",
            invocation_ref="tool:pytest:missing-ref",
            raw_output_ref="   ",
            raw_output="failure output",
        )


def test_checkpoint_rejects_unbounded_growth():
    with pytest.raises(ValueError, match="working-context checkpoint"):
        WorkingContextCheckpoint(
            objective="Bounded checkpoint.",
            immutable_constraints=tuple(
                f"constraint-{index}-" + ("x" * 1_000) for index in range(32)
            ),
            evidence_refs=(),
            completed_work=(),
            current_state="State.",
            blockers=(),
            recent_actions=(),
            source_output_refs=(),
        )


def test_checkpoint_rejects_invalid_previous_digest_and_reference_hash():
    with pytest.raises(ValueError, match="previous_checkpoint_digest"):
        WorkingContextCheckpoint(
            objective="Objective.",
            immutable_constraints=(),
            evidence_refs=(),
            completed_work=(),
            current_state="State.",
            blockers=(),
            recent_actions=(),
            source_output_refs=(),
            previous_checkpoint_digest="not-a-digest",
        )

    with pytest.raises(ValueError, match="sha256_hex"):
        ContextReference(
            kind=ContextReferenceKind.SOURCE,
            ref="artifact://source",
            sha256_hex="ABC",
        )


def test_checkpoint_qualified_size_is_below_contract_bound():
    checkpoint = WorkingContextCheckpoint(
        objective="Small deterministic checkpoint.",
        immutable_constraints=("Preserve exact evidence references.",),
        evidence_refs=(),
        completed_work=("Reducer implemented.",),
        current_state="Ready for deterministic integration tests.",
        blockers=(),
        recent_actions=(),
        source_output_refs=(),
    )
    rendered = checkpoint.render_for_model().encode("utf-8")
    assert len(rendered) < MAX_CHECKPOINT_UTF8_BYTES
