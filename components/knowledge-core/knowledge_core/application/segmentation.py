from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from uuid import UUID

from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.retrieval import RetrievalLifecycleState


_PROFILE_NAME = "kc-section-segmentation-v1"
_RESERVED_LIFECYCLE_TOKEN = "kc:retrieval-lifecycle"
_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+|$)(.*)$")
_FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_DIRECTIVE_RE = re.compile(
    r"^ {0,3}<!-- kc:retrieval-lifecycle=(current|unknown|superseded) -->$"
)
_LIFECYCLE_ORDER = {
    RetrievalLifecycleState.CURRENT: 0,
    RetrievalLifecycleState.UNKNOWN: 1,
    RetrievalLifecycleState.SUPERSEDED: 2,
}


@dataclass(frozen=True)
class SectionSegmentationProfile:
    soft_target_bytes: int = 16384
    hard_max_bytes: int = 32768
    name: str = _PROFILE_NAME

    def __post_init__(self) -> None:
        if self.soft_target_bytes <= 0:
            raise KnowledgeInvariantError("soft_target_bytes must be positive")
        if self.hard_max_bytes < self.soft_target_bytes:
            raise KnowledgeInvariantError(
                "hard_max_bytes must be greater than or equal to soft_target_bytes"
            )

    @property
    def canonical_config(self) -> dict:
        return {
            "name": self.name,
            "supported_media": ["text/markdown", "text/plain"],
            "strict_utf8": True,
            "markdown_grammar": "atx-fence-v1",
            "lifecycle_directive_grammar": "kc-retrieval-lifecycle-v1",
            "lifecycle_order": ["current", "unknown", "superseded"],
            "large_block_split": {
                "soft_target_bytes": self.soft_target_bytes,
                "hard_max_bytes": self.hard_max_bytes,
                "split_unit": "exact-line-boundary",
                "fenced_code_indivisible": True,
            },
            "segment_key_version": 1,
            "lexical": {
                "language": "english",
                "local_weight": "A",
                "heading_context_weight": "B",
                "directive_removed_from_projection": True,
            },
            "ranking": [
                "ts_rank_cd:desc",
                "lifecycle:current-unknown-superseded",
                "authority_rank:asc:nulls-last",
                "created_revision_id:desc",
                "resource_version_ref:asc",
                "segment_ordinal:asc",
                "segment_key:asc",
            ],
        }

    @property
    def digest(self) -> str:
        payload = json.dumps(
            self.canonical_config,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return "sha256:" + sha256(payload).hexdigest()


DEFAULT_SECTION_SEGMENTATION_PROFILE = SectionSegmentationProfile()


@dataclass(frozen=True)
class HeadingPathElement:
    level: int
    text: str
    line: int
    byte_start: int
    byte_end: int

    def as_dict(self) -> dict:
        return {
            "level": self.level,
            "text": self.text,
            "line": self.line,
            "byte_start": self.byte_start,
            "byte_end": self.byte_end,
        }


@dataclass(frozen=True)
class DerivedTextSegment:
    segment_ordinal: int
    segment_key: str
    segment_kind: str
    base_block_ordinal: int
    part_index: int
    part_count: int
    source_byte_start: int
    source_byte_end: int
    source_line_start: int
    source_line_end: int
    source_slice_sha256: str
    heading_path: tuple[HeadingPathElement, ...]
    lifecycle_state: RetrievalLifecycleState
    parent_lifecycle_state: RetrievalLifecycleState
    lifecycle_origin: str
    lifecycle_directive_line: int | None
    local_search_text: str
    heading_context_text: str


@dataclass(frozen=True)
class _Heading:
    level: int
    text: str
    line: int
    byte_start: int
    byte_end: int

    def public(self) -> HeadingPathElement:
        return HeadingPathElement(
            level=self.level,
            text=self.text,
            line=self.line,
            byte_start=self.byte_start,
            byte_end=self.byte_end,
        )


@dataclass(frozen=True)
class _Line:
    index: int
    number: int
    start: int
    end: int
    content_end: int
    text: str
    boundary_after_eligible: bool
    blank: bool
    heading: _Heading | None
    valid_directive: RetrievalLifecycleState | None


def _strip_line_ending(raw: bytes) -> bytes:
    if raw.endswith(b"\r\n"):
        return raw[:-2]
    if raw.endswith(b"\n"):
        return raw[:-1]
    return raw


def _heading_from_text(
    text: str,
    *,
    line: int,
    byte_start: int,
    byte_end: int,
) -> _Heading | None:
    match = _HEADING_RE.match(text)
    if match is None:
        return None
    level = len(match.group(1))
    display = match.group(2).rstrip(" \t")
    closing = re.match(r"^(.*?)[ \t]+#+$", display)
    if closing is not None:
        display = closing.group(1)
    display = display.strip(" \t")
    return _Heading(
        level=level,
        text=display,
        line=line,
        byte_start=byte_start,
        byte_end=byte_end,
    )


def _scan_lines(content: bytes, *, markdown: bool) -> list[_Line]:
    try:
        content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise KnowledgeInvariantError(
            "section segmentation requires strict UTF-8"
        ) from exc

    spans: list[tuple[int, int, int, int, str]] = []
    cursor = 0
    while cursor < len(content):
        newline = content.find(b"\n", cursor)
        end = len(content) if newline < 0 else newline + 1
        raw = content[cursor:end]
        core = _strip_line_ending(raw)
        spans.append(
            (
                cursor,
                end,
                cursor + len(core),
                len(spans) + 1,
                core.decode("utf-8", errors="strict"),
            )
        )
        cursor = end

    lines: list[_Line] = []
    fence_char: str | None = None
    fence_length = 0
    for index, (start, end, content_end, number, text) in enumerate(spans):
        heading: _Heading | None = None
        valid_directive: RetrievalLifecycleState | None = None
        boundary_after_eligible = True

        if markdown:
            if fence_char is None:
                opener = _FENCE_OPEN_RE.match(text)
                if opener is not None:
                    run = opener.group(1)
                    fence_char = run[0]
                    fence_length = len(run)
                    boundary_after_eligible = False
                else:
                    heading = _heading_from_text(
                        text,
                        line=number,
                        byte_start=start,
                        byte_end=content_end,
                    )
                    if _RESERVED_LIFECYCLE_TOKEN in text:
                        directive = _DIRECTIVE_RE.match(text)
                        if directive is None:
                            raise KnowledgeInvariantError(
                                "invalid reserved lifecycle directive "
                                f"at source line {number}"
                            )
                        valid_directive = RetrievalLifecycleState(
                            directive.group(1)
                        )
            else:
                closer = re.compile(
                    rf"^ {{0,3}}{re.escape(fence_char)}"
                    rf"{{{fence_length},}}[ \t]*$"
                )
                if closer.match(text) is not None:
                    fence_char = None
                    fence_length = 0
                    boundary_after_eligible = True
                else:
                    boundary_after_eligible = False

        lines.append(
            _Line(
                index=index,
                number=number,
                start=start,
                end=end,
                content_end=content_end,
                text=text,
                boundary_after_eligible=boundary_after_eligible,
                blank=text.strip(" \t") == "",
                heading=heading,
                valid_directive=valid_directive,
            )
        )
    return lines


def _source_line_start(content: bytes, start: int) -> int:
    if start <= 0:
        return 1
    return content[:start].count(b"\n") + 1


def _source_line_end(content: bytes, end: int) -> int:
    if end <= 0:
        return 1
    return content[: end - 1].count(b"\n") + 1


def _partition_block(
    *,
    content: bytes,
    lines: list[_Line],
    start: int,
    end: int,
    profile: SectionSegmentationProfile,
) -> list[tuple[int, int]]:
    if end - start <= profile.hard_max_bytes:
        return [(start, end)]

    line_boundaries: list[int] = []
    blank_boundaries: list[int] = []
    for line in lines:
        if line.end <= start:
            continue
        if line.end > end:
            break
        if not line.boundary_after_eligible:
            continue
        if line.end <= start:
            continue
        line_boundaries.append(line.end)
        if line.blank:
            blank_boundaries.append(line.end)

    parts: list[tuple[int, int]] = []
    cursor = start
    while end - cursor > profile.hard_max_bytes:
        hard_limit = cursor + profile.hard_max_bytes
        blank_candidates = [
            boundary
            for boundary in blank_boundaries
            if cursor < boundary <= hard_limit
        ]
        if blank_candidates:
            cut = min(
                blank_candidates,
                key=lambda boundary: (
                    abs((boundary - cursor) - profile.soft_target_bytes),
                    boundary,
                ),
            )
        else:
            line_candidates = [
                boundary
                for boundary in line_boundaries
                if cursor < boundary <= hard_limit
            ]
            if not line_candidates:
                raise KnowledgeInvariantError(
                    "deterministic section segmentation cannot split "
                    "an oversized block at a legal line boundary"
                )
            cut = max(line_candidates)
        if cut <= cursor:
            raise KnowledgeInvariantError(
                "deterministic section segmentation did not make progress"
            )
        parts.append((cursor, cut))
        cursor = cut
    parts.append((cursor, end))
    return parts


def _segment_key(
    *,
    profile_digest: str,
    resource_version_ref: UUID,
    segment_ordinal: int,
    source_byte_start: int,
    source_byte_end: int,
    source_slice_sha256: str,
) -> str:
    payload = {
        "key_version": 1,
        "profile_digest": profile_digest,
        "resource_version_ref": str(resource_version_ref),
        "segment_ordinal": segment_ordinal,
        "source_byte_start": source_byte_start,
        "source_byte_end": source_byte_end,
        "source_slice_sha256": source_slice_sha256,
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + sha256(canonical).hexdigest()


def segment_text_resource(
    *,
    content: bytes,
    media_type: str,
    resource_version_ref: UUID,
    parent_lifecycle_state: RetrievalLifecycleState,
    profile: SectionSegmentationProfile = DEFAULT_SECTION_SEGMENTATION_PROFILE,
) -> tuple[DerivedTextSegment, ...]:
    if media_type not in {"text/markdown", "text/plain"}:
        raise KnowledgeInvariantError(
            f"unsupported media type for section segmentation: {media_type}"
        )

    markdown = media_type == "text/markdown"
    lines = _scan_lines(content, markdown=markdown)
    profile_digest = profile.digest

    if not content:
        empty_digest = sha256(b"").hexdigest()
        return (
            DerivedTextSegment(
                segment_ordinal=0,
                segment_key=_segment_key(
                    profile_digest=profile_digest,
                    resource_version_ref=resource_version_ref,
                    segment_ordinal=0,
                    source_byte_start=0,
                    source_byte_end=0,
                    source_slice_sha256=empty_digest,
                ),
                segment_kind="document",
                base_block_ordinal=0,
                part_index=1,
                part_count=1,
                source_byte_start=0,
                source_byte_end=0,
                source_line_start=1,
                source_line_end=1,
                source_slice_sha256=empty_digest,
                heading_path=(),
                lifecycle_state=parent_lifecycle_state,
                parent_lifecycle_state=parent_lifecycle_state,
                lifecycle_origin="document",
                lifecycle_directive_line=None,
                local_search_text="",
                heading_context_text="",
            ),
        )

    headings: list[tuple[int, _Heading, tuple[_Heading, ...]]] = []
    heading_stack: list[_Heading] = []
    if markdown:
        for line in lines:
            if line.heading is None:
                continue
            heading = line.heading
            heading_stack = [
                existing
                for existing in heading_stack
                if existing.level < heading.level
            ]
            heading_stack.append(heading)
            headings.append((line.index, heading, tuple(heading_stack)))

    blocks: list[dict] = []
    if markdown and headings:
        first_heading_start = lines[headings[0][0]].start
        if first_heading_start > 0:
            blocks.append(
                {
                    "kind": "preamble",
                    "start": 0,
                    "end": first_heading_start,
                    "heading_path": (),
                    "heading_index": None,
                    "level": None,
                }
            )
        for position, (line_index, heading, path) in enumerate(headings):
            block_end = (
                lines[headings[position + 1][0]].start
                if position + 1 < len(headings)
                else len(content)
            )
            blocks.append(
                {
                    "kind": "section",
                    "start": lines[line_index].start,
                    "end": block_end,
                    "heading_path": tuple(item.public() for item in path),
                    "heading_index": line_index,
                    "level": heading.level,
                }
            )
    else:
        blocks.append(
            {
                "kind": "document",
                "start": 0,
                "end": len(content),
                "heading_path": (),
                "heading_index": None,
                "level": None,
            }
        )

    valid_directives = {
        line.index: line
        for line in lines
        if line.valid_directive is not None
    }
    used_directives: set[int] = set()
    lifecycle_stack: list[dict] = []

    for block in blocks:
        block["lifecycle_state"] = parent_lifecycle_state
        block["lifecycle_origin"] = "document"
        block["lifecycle_directive_line"] = None
        block["directive_index"] = None

        if block["kind"] != "section":
            continue

        level = int(block["level"])
        lifecycle_stack = [
            item for item in lifecycle_stack if int(item["level"]) < level
        ]
        if lifecycle_stack:
            inherited_state = lifecycle_stack[-1]["effective_state"]
            active_directive_line = lifecycle_stack[-1]["active_directive_line"]
        else:
            inherited_state = parent_lifecycle_state
            active_directive_line = None

        heading_index = int(block["heading_index"])
        body_lines = [
            line
            for line in lines
            if line.index > heading_index and line.start < int(block["end"])
        ]
        first_nonblank = next(
            (line for line in body_lines if not line.blank),
            None,
        )
        directive_lines = [
            line for line in body_lines if line.valid_directive is not None
        ]
        if len(directive_lines) > 1:
            raise KnowledgeInvariantError(
                "multiple lifecycle directives are not allowed for one heading"
            )

        direct = directive_lines[0] if directive_lines else None
        if direct is not None:
            if first_nonblank is None or direct.index != first_nonblank.index:
                raise KnowledgeInvariantError(
                    "lifecycle directive must be the first non-blank body line "
                    f"after its heading; source line {direct.number}"
                )
            used_directives.add(direct.index)
            direct_state = direct.valid_directive
            assert direct_state is not None
            if (
                _LIFECYCLE_ORDER[direct_state]
                < _LIFECYCLE_ORDER[inherited_state]
            ):
                raise KnowledgeInvariantError(
                    "lifecycle directive cannot promote section currentness; "
                    f"source line {direct.number}"
                )
            effective_state = direct_state
            lifecycle_origin = "section-directive"
            directive_line = direct.number
            descendant_directive_line = direct.number
        else:
            effective_state = inherited_state
            if active_directive_line is not None:
                lifecycle_origin = "ancestor-directive"
                directive_line = int(active_directive_line)
            else:
                lifecycle_origin = "document"
                directive_line = None
            descendant_directive_line = active_directive_line

        block["lifecycle_state"] = effective_state
        block["lifecycle_origin"] = lifecycle_origin
        block["lifecycle_directive_line"] = directive_line
        block["directive_index"] = direct.index if direct is not None else None
        lifecycle_stack.append(
            {
                "level": level,
                "effective_state": effective_state,
                "active_directive_line": descendant_directive_line,
            }
        )

    unused_directives = set(valid_directives) - used_directives
    if unused_directives:
        first = lines[min(unused_directives)]
        raise KnowledgeInvariantError(
            "lifecycle directive is not attached to a valid heading; "
            f"source line {first.number}"
        )

    segments: list[DerivedTextSegment] = []
    segment_ordinal = 0
    for base_block_ordinal, block in enumerate(blocks):
        parts = _partition_block(
            content=content,
            lines=lines,
            start=int(block["start"]),
            end=int(block["end"]),
            profile=profile,
        )
        for part_index, (start, end) in enumerate(parts, start=1):
            source_slice = content[start:end]
            source_slice_sha256 = sha256(source_slice).hexdigest()
            directive_line = None
            directive_index = block.get("directive_index")
            if directive_index is not None:
                candidate = lines[int(directive_index)]
                if start <= candidate.start and candidate.end <= end:
                    directive_line = candidate

            if directive_line is None:
                local_search_text = source_slice.decode("utf-8", errors="strict")
            else:
                local_search_text = (
                    content[start : directive_line.start]
                    + content[directive_line.end : end]
                ).decode("utf-8", errors="strict")

            heading_path = tuple(block["heading_path"])
            segments.append(
                DerivedTextSegment(
                    segment_ordinal=segment_ordinal,
                    segment_key=_segment_key(
                        profile_digest=profile_digest,
                        resource_version_ref=resource_version_ref,
                        segment_ordinal=segment_ordinal,
                        source_byte_start=start,
                        source_byte_end=end,
                        source_slice_sha256=source_slice_sha256,
                    ),
                    segment_kind=(
                        str(block["kind"]) if part_index == 1 else "continuation"
                    ),
                    base_block_ordinal=base_block_ordinal,
                    part_index=part_index,
                    part_count=len(parts),
                    source_byte_start=start,
                    source_byte_end=end,
                    source_line_start=_source_line_start(content, start),
                    source_line_end=_source_line_end(content, end),
                    source_slice_sha256=source_slice_sha256,
                    heading_path=heading_path,
                    lifecycle_state=block["lifecycle_state"],
                    parent_lifecycle_state=parent_lifecycle_state,
                    lifecycle_origin=str(block["lifecycle_origin"]),
                    lifecycle_directive_line=block["lifecycle_directive_line"],
                    local_search_text=local_search_text,
                    heading_context_text="\n".join(
                        heading.text for heading in heading_path
                    ),
                )
            )
            segment_ordinal += 1

    if not segments:
        raise KnowledgeInvariantError(
            "non-empty supported resource produced no retrieval segments"
        )
    if segments[0].source_byte_start != 0:
        raise KnowledgeInvariantError("segment coverage does not start at byte zero")
    if segments[-1].source_byte_end != len(content):
        raise KnowledgeInvariantError(
            "segment coverage does not end at the exact artifact size"
        )
    for left, right in zip(segments, segments[1:], strict=False):
        if left.source_byte_end != right.source_byte_start:
            raise KnowledgeInvariantError("segment coverage contains a gap or overlap")
    reconstructed = b"".join(
        content[item.source_byte_start : item.source_byte_end]
        for item in segments
    )
    if reconstructed != content:
        raise KnowledgeInvariantError(
            "segment coverage failed exact byte reconstruction"
        )
    for expected_ordinal, item in enumerate(segments):
        if item.segment_ordinal != expected_ordinal:
            raise KnowledgeInvariantError("segment ordinals are not contiguous")
        exact = content[item.source_byte_start : item.source_byte_end]
        if sha256(exact).hexdigest() != item.source_slice_sha256:
            raise KnowledgeInvariantError(
                "segment source-slice digest does not match canonical bytes"
            )

    keys = [item.segment_key for item in segments]
    if len(set(keys)) != len(keys):
        raise KnowledgeInvariantError(
            "deterministic segmentation produced duplicate segment keys"
        )
    return tuple(segments)
