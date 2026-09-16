from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import re


WORKING_CONTEXT_CONTRACT_VERSION = "kc-worker-context-checkpoint-v1"
TOOL_OUTPUT_REDUCTION_VERSION = "kc-tool-output-reduction-v1"
MAX_CHECKPOINT_UTF8_BYTES = 32_768
MAX_SECTION_ITEMS = 32
MAX_TEXT_ITEM_UTF8_BYTES = 4_096
DEFAULT_TOOL_EXCERPT_UTF8_BYTES = 8_192

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CHECKPOINT_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_DIAGNOSTIC_TERMS = (
    "error",
    "failed",
    "failure",
    "exception",
    "traceback",
    "warning",
    "denied",
    "blocked",
    "timeout",
    "timed out",
    "not found",
    "invalid",
    "mismatch",
)


def _utf8_len(value: str) -> int:
    return len(value.encode("utf-8"))


def _require_text(name: str, value: str, *, max_bytes: int = MAX_TEXT_ITEM_UTF8_BYTES) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-blank")
    if _utf8_len(normalized) > max_bytes:
        raise ValueError(f"{name} must be at most {max_bytes} UTF-8 bytes")
    return normalized


def _require_text_items(name: str, values: tuple[str, ...]) -> None:
    if len(values) > MAX_SECTION_ITEMS:
        raise ValueError(f"{name} must contain at most {MAX_SECTION_ITEMS} items")
    for index, value in enumerate(values):
        _require_text(f"{name}[{index}]", value)


def _clip_utf8(value: str, max_bytes: int) -> str:
    if max_bytes < 1:
        return ""
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    marker = "…"
    marker_bytes = marker.encode("utf-8")
    if max_bytes <= len(marker_bytes):
        return encoded[:max_bytes].decode("utf-8", errors="ignore")
    prefix = encoded[: max_bytes - len(marker_bytes)].decode("utf-8", errors="ignore")
    return prefix + marker


class ContextReferenceKind(StrEnum):
    KC_EVIDENCE = "kc_evidence"
    SOURCE = "source"
    TOOL_OUTPUT = "tool_output"
    ARTIFACT = "artifact"
    OTHER = "other"


class RecentActionOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ContextReference:
    kind: ContextReferenceKind
    ref: str
    sha256_hex: str | None = None

    def __post_init__(self) -> None:
        _require_text("context reference", self.ref)
        if self.sha256_hex is not None and not _SHA256_RE.fullmatch(self.sha256_hex):
            raise ValueError("context reference sha256_hex must be 64 lowercase hex characters")

    def to_payload(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "ref": self.ref,
            "sha256": self.sha256_hex,
        }


@dataclass(frozen=True)
class RecentAction:
    action: str
    outcome: RecentActionOutcome
    refs: tuple[ContextReference, ...] = ()

    def __post_init__(self) -> None:
        _require_text("recent action", self.action)
        if len(self.refs) > MAX_SECTION_ITEMS:
            raise ValueError(f"recent action refs must contain at most {MAX_SECTION_ITEMS} items")

    def to_payload(self) -> dict[str, object]:
        return {
            "action": self.action,
            "outcome": self.outcome.value,
            "refs": [ref.to_payload() for ref in self.refs],
        }


@dataclass(frozen=True)
class ToolOutputReduction:
    contract_version: str
    tool_name: str
    invocation_ref: str
    raw_output_ref: str
    raw_sha256: str
    raw_utf8_bytes: int
    raw_line_count: int
    truncated: bool
    omitted_line_count: int
    selected_line_numbers: tuple[int, ...]
    excerpt: str

    def __post_init__(self) -> None:
        if self.contract_version != TOOL_OUTPUT_REDUCTION_VERSION:
            raise ValueError("unsupported tool-output reduction contract version")
        _require_text("tool_name", self.tool_name)
        _require_text("invocation_ref", self.invocation_ref)
        _require_text("raw_output_ref", self.raw_output_ref)
        if not _SHA256_RE.fullmatch(self.raw_sha256):
            raise ValueError("raw_sha256 must be 64 lowercase hex characters")
        if self.raw_utf8_bytes < 0 or self.raw_line_count < 0 or self.omitted_line_count < 0:
            raise ValueError("tool-output counts must be non-negative")
        if tuple(sorted(set(self.selected_line_numbers))) != self.selected_line_numbers:
            raise ValueError("selected_line_numbers must be sorted and unique")
        if any(number < 1 or number > self.raw_line_count for number in self.selected_line_numbers):
            raise ValueError("selected_line_numbers must address raw output lines")
        if not self.truncated and self.omitted_line_count != 0:
            raise ValueError("untruncated tool output cannot report omitted lines")
        if _utf8_len(self.excerpt) > DEFAULT_TOOL_EXCERPT_UTF8_BYTES:
            raise ValueError("tool-output excerpt exceeds the qualified default bound")

    def to_payload(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "tool_name": self.tool_name,
            "invocation_ref": self.invocation_ref,
            "raw_output_ref": self.raw_output_ref,
            "raw_sha256": self.raw_sha256,
            "raw_utf8_bytes": self.raw_utf8_bytes,
            "raw_line_count": self.raw_line_count,
            "truncated": self.truncated,
            "omitted_line_count": self.omitted_line_count,
            "selected_line_numbers": list(self.selected_line_numbers),
            "excerpt": self.excerpt,
        }


def reduce_tool_output(
    *,
    tool_name: str,
    invocation_ref: str,
    raw_output_ref: str,
    raw_output: str,
    max_excerpt_utf8_bytes: int = DEFAULT_TOOL_EXCERPT_UTF8_BYTES,
    head_lines: int = 4,
    tail_lines: int = 4,
    max_diagnostic_lines: int = 12,
) -> ToolOutputReduction:
    """Produce a deterministic bounded excerpt while preserving the exact raw reference.

    The excerpt is never the source of truth. Callers must retain ``raw_output_ref`` and
    ``raw_sha256`` so later verification can return to the exact complete output.
    """

    tool = _require_text("tool_name", tool_name)
    invocation = _require_text("invocation_ref", invocation_ref)
    raw_ref = _require_text("raw_output_ref", raw_output_ref)
    if max_excerpt_utf8_bytes < 256 or max_excerpt_utf8_bytes > DEFAULT_TOOL_EXCERPT_UTF8_BYTES:
        raise ValueError(
            f"max_excerpt_utf8_bytes must be between 256 and {DEFAULT_TOOL_EXCERPT_UTF8_BYTES}"
        )
    for name, value in (
        ("head_lines", head_lines),
        ("tail_lines", tail_lines),
        ("max_diagnostic_lines", max_diagnostic_lines),
    ):
        if value < 0 or value > 64:
            raise ValueError(f"{name} must be between 0 and 64")

    raw_bytes = raw_output.encode("utf-8")
    raw_digest = sha256(raw_bytes).hexdigest()
    lines = raw_output.splitlines()
    raw_line_count = len(lines)

    if len(raw_bytes) <= max_excerpt_utf8_bytes:
        return ToolOutputReduction(
            contract_version=TOOL_OUTPUT_REDUCTION_VERSION,
            tool_name=tool,
            invocation_ref=invocation,
            raw_output_ref=raw_ref,
            raw_sha256=raw_digest,
            raw_utf8_bytes=len(raw_bytes),
            raw_line_count=raw_line_count,
            truncated=False,
            omitted_line_count=0,
            selected_line_numbers=(),
            excerpt=raw_output,
        )

    diagnostic_indexes: list[int] = []
    for index, line in enumerate(lines):
        lowered = line.casefold()
        if any(term in lowered for term in _DIAGNOSTIC_TERMS):
            diagnostic_indexes.append(index)
            if len(diagnostic_indexes) >= max_diagnostic_lines:
                break

    selected_indexes = set(range(min(head_lines, raw_line_count)))
    if tail_lines:
        selected_indexes.update(range(max(0, raw_line_count - tail_lines), raw_line_count))
    selected_indexes.update(diagnostic_indexes)
    ordered_indexes = tuple(sorted(selected_indexes))

    if not ordered_indexes and raw_line_count:
        ordered_indexes = (0,)

    if ordered_indexes:
        line_budget = max(32, max_excerpt_utf8_bytes // len(ordered_indexes) - 24)
        rendered_lines = [
            f"[L{index + 1}] {_clip_utf8(lines[index], line_budget)}"
            for index in ordered_indexes
        ]
        excerpt = "\n".join(rendered_lines)
        excerpt = _clip_utf8(excerpt, max_excerpt_utf8_bytes)
    else:
        excerpt = _clip_utf8(raw_output, max_excerpt_utf8_bytes)

    return ToolOutputReduction(
        contract_version=TOOL_OUTPUT_REDUCTION_VERSION,
        tool_name=tool,
        invocation_ref=invocation,
        raw_output_ref=raw_ref,
        raw_sha256=raw_digest,
        raw_utf8_bytes=len(raw_bytes),
        raw_line_count=raw_line_count,
        truncated=True,
        omitted_line_count=max(0, raw_line_count - len(ordered_indexes)),
        selected_line_numbers=tuple(index + 1 for index in ordered_indexes),
        excerpt=excerpt,
    )


@dataclass(frozen=True)
class WorkingContextCheckpoint:
    objective: str
    immutable_constraints: tuple[str, ...]
    evidence_refs: tuple[ContextReference, ...]
    completed_work: tuple[str, ...]
    current_state: str
    blockers: tuple[str, ...]
    recent_actions: tuple[RecentAction, ...]
    source_output_refs: tuple[ContextReference, ...]
    reduced_tool_outputs: tuple[ToolOutputReduction, ...] = ()
    previous_checkpoint_digest: str | None = None
    contract_version: str = WORKING_CONTEXT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != WORKING_CONTEXT_CONTRACT_VERSION:
            raise ValueError("unsupported working-context checkpoint contract version")
        _require_text("objective", self.objective)
        _require_text("current_state", self.current_state)
        _require_text_items("immutable_constraints", self.immutable_constraints)
        _require_text_items("completed_work", self.completed_work)
        _require_text_items("blockers", self.blockers)
        for name, values in (
            ("evidence_refs", self.evidence_refs),
            ("recent_actions", self.recent_actions),
            ("source_output_refs", self.source_output_refs),
            ("reduced_tool_outputs", self.reduced_tool_outputs),
        ):
            if len(values) > MAX_SECTION_ITEMS:
                raise ValueError(f"{name} must contain at most {MAX_SECTION_ITEMS} items")
        if self.previous_checkpoint_digest is not None and not _CHECKPOINT_DIGEST_RE.fullmatch(
            self.previous_checkpoint_digest
        ):
            raise ValueError("previous_checkpoint_digest must use sha256:<64 lowercase hex>")
        if _utf8_len(self._canonical_json()) > MAX_CHECKPOINT_UTF8_BYTES:
            raise ValueError(
                f"working-context checkpoint must be at most {MAX_CHECKPOINT_UTF8_BYTES} UTF-8 bytes"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "objective": self.objective,
            "immutable_constraints": list(self.immutable_constraints),
            "evidence_refs": [ref.to_payload() for ref in self.evidence_refs],
            "completed_work": list(self.completed_work),
            "current_state": self.current_state,
            "blockers": list(self.blockers),
            "recent_actions": [action.to_payload() for action in self.recent_actions],
            "source_output_refs": [ref.to_payload() for ref in self.source_output_refs],
            "reduced_tool_outputs": [output.to_payload() for output in self.reduced_tool_outputs],
            "previous_checkpoint_digest": self.previous_checkpoint_digest,
        }

    def _canonical_json(self) -> str:
        return json.dumps(
            self.to_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    @property
    def checkpoint_digest(self) -> str:
        return "sha256:" + sha256(self._canonical_json().encode("utf-8")).hexdigest()

    def render_for_model(self) -> str:
        """Render deterministic structured working memory without additional synthesis."""

        payload = self.to_payload()
        payload["checkpoint_digest"] = self.checkpoint_digest
        return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False)


__all__ = [
    "ContextReference",
    "ContextReferenceKind",
    "DEFAULT_TOOL_EXCERPT_UTF8_BYTES",
    "MAX_CHECKPOINT_UTF8_BYTES",
    "RecentAction",
    "RecentActionOutcome",
    "TOOL_OUTPUT_REDUCTION_VERSION",
    "ToolOutputReduction",
    "WORKING_CONTEXT_CONTRACT_VERSION",
    "WorkingContextCheckpoint",
    "reduce_tool_output",
]
