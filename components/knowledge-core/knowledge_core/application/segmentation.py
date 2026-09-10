from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID

from knowledge_core.domain.assertions import KnowledgeInvariantError


SUPPORTED_STRUCTURAL_MEDIA = frozenset({"text/markdown", "text/plain"})


@dataclass(frozen=True)
class SectionSegmentationProfile:
    profile_id: str = "kc-section-segmentation-v1"
    soft_target_bytes: int = 16384
    hard_max_bytes: int = 32768
    markdown_grammar_version: str = "atx-fence-v1"
    segment_key_version: int = 1

    def __post_init__(self) -> None:
        if self.soft_target_bytes < 1:
            raise KnowledgeInvariantError("soft_target_bytes must be positive")
        if self.hard_max_bytes < 1:
            raise KnowledgeInvariantError("hard_max_bytes must be positive")
        if self.soft_target_bytes > self.hard_max_bytes:
            raise KnowledgeInvariantError(
                "soft_target_bytes must not exceed hard_max_bytes"
            )
        if self.segment_key_version != 1:
            raise KnowledgeInvariantError("unsupported segment key version")

    @property
    def canonical_config(self) -> dict[str, object]:
        return {
            "hard_max_bytes": self.hard_max_bytes,
            "markdown_grammar_version": self.markdown_grammar_version,
            "profile_id": self.profile_id,
            "segment_key_version": self.segment_key_version,
            "soft_target_bytes": self.soft_target_bytes,
            "strict_utf8": True,
            "supported_media": sorted(SUPPORTED_STRUCTURAL_MEDIA),
        }

    @property
    def digest(self) -> str:
        encoded = json.dumps(
            self.canonical_config,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return "sha256:" + sha256(encoded).hexdigest()


DEFAULT_SECTION_SEGMENTATION_PROFILE = SectionSegmentationProfile()


@dataclass(frozen=True)
class HeadingPathElement:
    level: int
    display_text: str
    source_line: int
    source_byte_start: int
    source_byte_end: int


@dataclass(frozen=True)
class StructuralSegment:
    resource_version_ref: UUID
    segment_ordinal: int
    structural_kind: str
    base_block_ordinal: int
    part_index: int
    part_count: int
    source_byte_start: int
    source_byte_end: int
    source_line_start: int
    source_line_end: int
    heading_path: tuple[HeadingPathElement, ...]
    source_slice_sha256: str
    segment_key: str


@dataclass(frozen=True)
class StructuralSegmentation:
    resource_version_ref: UUID
    media_type: str
    profile_id: str
    profile_digest: str
    segments: tuple[StructuralSegment, ...]


@dataclass(frozen=True)
class _Line:
    number: int
    start: int
    end: int
    content_end: int
    content: bytes

    @property
    def is_blank(self) -> bool:
        return not self.content.strip(b" \t")


@dataclass(frozen=True)
class _FenceSpan:
    start: int
    end: int


@dataclass(frozen=True)
class _Heading:
    start: int
    end: int
    path: tuple[HeadingPathElement, ...]


@dataclass(frozen=True)
class _BaseBlock:
    start: int
    end: int
    kind: str
    heading_path: tuple[HeadingPathElement, ...]


def segment_structural_content(
    *,
    resource_version_ref: UUID,
    media_type: str,
    content: bytes,
    profile: SectionSegmentationProfile = DEFAULT_SECTION_SEGMENTATION_PROFILE,
) -> StructuralSegmentation:
    """Partition exact UTF-8 source bytes into deterministic structural segments.

    This stage is intentionally lifecycle-blind. Governed lifecycle/classification
    validation and projection belong to the later retrieval-projection stage.
    """

    if media_type not in SUPPORTED_STRUCTURAL_MEDIA:
        raise KnowledgeInvariantError(
            f"unsupported structural segmentation media type: {media_type}"
        )

    try:
        content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise KnowledgeInvariantError(
            "structural segmentation requires strict UTF-8 source bytes"
        ) from exc

    lines = _scan_lines(content)

    if not content:
        empty_digest = sha256(b"").hexdigest()
        segment = _build_segment(
            resource_version_ref=resource_version_ref,
            profile_digest=profile.digest,
            ordinal=0,
            kind="document",
            base_block_ordinal=0,
            part_index=1,
            part_count=1,
            start=0,
            end=0,
            line_start=1,
            line_end=1,
            heading_path=(),
            slice_digest=empty_digest,
        )
        return StructuralSegmentation(
            resource_version_ref=resource_version_ref,
            media_type=media_type,
            profile_id=profile.profile_id,
            profile_digest=profile.digest,
            segments=(segment,),
        )

    if media_type == "text/markdown":
        headings, fence_spans = _scan_markdown(lines, len(content))
        base_blocks = _markdown_base_blocks(headings, len(content))
    else:
        fence_spans = ()
        base_blocks = (
            _BaseBlock(
                start=0,
                end=len(content),
                kind="document",
                heading_path=(),
            ),
        )

    pieces: list[
        tuple[int, int, str, int, int, int, tuple[HeadingPathElement, ...]]
    ] = []
    for base_ordinal, block in enumerate(base_blocks):
        ranges = _split_block(
            block=block,
            lines=lines,
            fence_spans=fence_spans,
            profile=profile,
        )
        part_count = len(ranges)
        for part_index, (start, end) in enumerate(ranges, start=1):
            pieces.append(
                (
                    start,
                    end,
                    block.kind if part_index == 1 else "continuation",
                    base_ordinal,
                    part_index,
                    part_count,
                    block.heading_path,
                )
            )

    segments: list[StructuralSegment] = []
    for ordinal, (
        start,
        end,
        kind,
        base_ordinal,
        part_index,
        part_count,
        heading_path,
    ) in enumerate(pieces):
        line_start, line_end = _line_range(lines, start, end)
        slice_digest = sha256(content[start:end]).hexdigest()
        segments.append(
            _build_segment(
                resource_version_ref=resource_version_ref,
                profile_digest=profile.digest,
                ordinal=ordinal,
                kind=kind,
                base_block_ordinal=base_ordinal,
                part_index=part_index,
                part_count=part_count,
                start=start,
                end=end,
                line_start=line_start,
                line_end=line_end,
                heading_path=heading_path,
                slice_digest=slice_digest,
            )
        )

    _verify_partition(content, segments)

    return StructuralSegmentation(
        resource_version_ref=resource_version_ref,
        media_type=media_type,
        profile_id=profile.profile_id,
        profile_digest=profile.digest,
        segments=tuple(segments),
    )


def _scan_lines(content: bytes) -> tuple[_Line, ...]:
    lines: list[_Line] = []
    cursor = 0
    number = 1
    while cursor < len(content):
        newline = content.find(b"\n", cursor)
        if newline < 0:
            end = len(content)
            content_end = end
        else:
            end = newline + 1
            content_end = newline - 1 if newline > cursor and content[newline - 1] == 13 else newline
        lines.append(
            _Line(
                number=number,
                start=cursor,
                end=end,
                content_end=content_end,
                content=content[cursor:content_end],
            )
        )
        cursor = end
        number += 1
    return tuple(lines)


def _scan_markdown(
    lines: tuple[_Line, ...],
    content_size: int,
) -> tuple[tuple[_Heading, ...], tuple[_FenceSpan, ...]]:
    headings: list[_Heading] = []
    fences: list[_FenceSpan] = []
    heading_stack: list[HeadingPathElement] = []
    active_fence: tuple[int, int] | None = None
    active_fence_start: int | None = None

    for line in lines:
        if active_fence is not None:
            fence_char, opener_length = active_fence
            if _is_fence_closer(line.content, fence_char, opener_length):
                if active_fence_start is None:
                    raise KnowledgeInvariantError("fence scanner lost opener position")
                fences.append(_FenceSpan(start=active_fence_start, end=line.end))
                active_fence = None
                active_fence_start = None
            continue

        opener = _fence_opener(line.content)
        if opener is not None:
            active_fence = opener
            active_fence_start = line.start
            continue

        heading = _atx_heading(line)
        if heading is None:
            continue

        while heading_stack and heading_stack[-1].level >= heading.level:
            heading_stack.pop()
        heading_stack.append(heading)
        headings.append(
            _Heading(
                start=line.start,
                end=line.end,
                path=tuple(heading_stack),
            )
        )

    if active_fence is not None:
        if active_fence_start is None:
            raise KnowledgeInvariantError("fence scanner lost opener position")
        fences.append(_FenceSpan(start=active_fence_start, end=content_size))

    return tuple(headings), tuple(fences)


def _leading_spaces(content: bytes) -> int:
    count = 0
    while count < len(content) and count < 4 and content[count] == 32:
        count += 1
    return count


def _fence_opener(content: bytes) -> tuple[int, int] | None:
    indent = _leading_spaces(content)
    if indent > 3 or indent >= len(content):
        return None
    marker = content[indent]
    if marker not in (96, 126):
        return None
    cursor = indent
    while cursor < len(content) and content[cursor] == marker:
        cursor += 1
    length = cursor - indent
    if length < 3:
        return None
    return marker, length


def _is_fence_closer(content: bytes, marker: int, opener_length: int) -> bool:
    indent = _leading_spaces(content)
    if indent > 3 or indent >= len(content) or content[indent] != marker:
        return False
    cursor = indent
    while cursor < len(content) and content[cursor] == marker:
        cursor += 1
    if cursor - indent < opener_length:
        return False
    return not content[cursor:].strip(b" \t")


def _atx_heading(line: _Line) -> HeadingPathElement | None:
    content = line.content
    indent = _leading_spaces(content)
    if indent > 3 or indent >= len(content) or content[indent] != 35:
        return None

    cursor = indent
    while cursor < len(content) and content[cursor] == 35:
        cursor += 1
    level = cursor - indent
    if level < 1 or level > 6:
        return None
    if cursor < len(content) and content[cursor] not in (32, 9):
        return None

    if cursor < len(content):
        cursor += 1
    display = _heading_display_text(content[cursor:])

    return HeadingPathElement(
        level=level,
        display_text=display,
        source_line=line.number,
        source_byte_start=line.start,
        source_byte_end=line.end,
    )


def _heading_display_text(body: bytes) -> str:
    body = body.strip(b" \t")
    if body.endswith(b"#"):
        run_start = len(body)
        while run_start > 0 and body[run_start - 1] == 35:
            run_start -= 1
        if run_start > 0 and body[run_start - 1] in (32, 9):
            body = body[:run_start].rstrip(b" \t")
    return body.decode("utf-8", errors="strict")


def _markdown_base_blocks(
    headings: tuple[_Heading, ...],
    content_size: int,
) -> tuple[_BaseBlock, ...]:
    if not headings:
        return (
            _BaseBlock(
                start=0,
                end=content_size,
                kind="document",
                heading_path=(),
            ),
        )

    blocks: list[_BaseBlock] = []
    if headings[0].start > 0:
        blocks.append(
            _BaseBlock(
                start=0,
                end=headings[0].start,
                kind="preamble",
                heading_path=(),
            )
        )

    for index, heading in enumerate(headings):
        end = headings[index + 1].start if index + 1 < len(headings) else content_size
        blocks.append(
            _BaseBlock(
                start=heading.start,
                end=end,
                kind="section",
                heading_path=heading.path,
            )
        )
    return tuple(blocks)


def _split_block(
    *,
    block: _BaseBlock,
    lines: tuple[_Line, ...],
    fence_spans: tuple[_FenceSpan, ...],
    profile: SectionSegmentationProfile,
) -> tuple[tuple[int, int], ...]:
    if block.end - block.start <= profile.hard_max_bytes:
        return ((block.start, block.end),)

    ranges: list[tuple[int, int]] = []
    cursor = block.start

    while cursor < block.end:
        remaining = block.end - cursor
        if remaining <= profile.hard_max_bytes:
            ranges.append((cursor, block.end))
            break

        limit = cursor + profile.hard_max_bytes
        eligible = [
            line
            for line in lines
            if cursor < line.end <= limit
            and line.end <= block.end
            and not _boundary_inside_fence(line.end, fence_spans)
        ]

        blank_boundaries = [line.end for line in eligible if line.is_blank]
        if blank_boundaries:
            boundary = min(
                blank_boundaries,
                key=lambda item: (
                    abs((item - cursor) - profile.soft_target_bytes),
                    item,
                ),
            )
        else:
            ordinary_boundaries = [line.end for line in eligible]
            if not ordinary_boundaries:
                raise KnowledgeInvariantError(
                    "deterministic structural segmentation has no legal boundary "
                    "within hard_max_bytes"
                )
            boundary = max(ordinary_boundaries)

        if boundary <= cursor:
            raise KnowledgeInvariantError(
                "deterministic structural segmentation made no forward progress"
            )
        ranges.append((cursor, boundary))
        cursor = boundary

    return tuple(ranges)


def _boundary_inside_fence(
    boundary: int,
    fence_spans: tuple[_FenceSpan, ...],
) -> bool:
    return any(span.start < boundary < span.end for span in fence_spans)


def _line_range(
    lines: tuple[_Line, ...],
    start: int,
    end: int,
) -> tuple[int, int]:
    if end <= start:
        return 1, 1
    starts = [line.start for line in lines]
    ends = [line.end for line in lines]
    return bisect_right(starts, start), bisect_left(ends, end) + 1


def _build_segment(
    *,
    resource_version_ref: UUID,
    profile_digest: str,
    ordinal: int,
    kind: str,
    base_block_ordinal: int,
    part_index: int,
    part_count: int,
    start: int,
    end: int,
    line_start: int,
    line_end: int,
    heading_path: tuple[HeadingPathElement, ...],
    slice_digest: str,
) -> StructuralSegment:
    key_payload = {
        "key_version": 1,
        "profile_digest": profile_digest,
        "resource_version_ref": str(resource_version_ref).lower(),
        "segment_ordinal": ordinal,
        "source_byte_start": start,
        "source_byte_end": end,
        "source_slice_sha256": slice_digest,
    }
    encoded = json.dumps(
        key_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    segment_key = "sha256:" + sha256(encoded).hexdigest()
    return StructuralSegment(
        resource_version_ref=resource_version_ref,
        segment_ordinal=ordinal,
        structural_kind=kind,
        base_block_ordinal=base_block_ordinal,
        part_index=part_index,
        part_count=part_count,
        source_byte_start=start,
        source_byte_end=end,
        source_line_start=line_start,
        source_line_end=line_end,
        heading_path=heading_path,
        source_slice_sha256=slice_digest,
        segment_key=segment_key,
    )


def _verify_partition(
    content: bytes,
    segments: list[StructuralSegment],
) -> None:
    if not segments:
        raise KnowledgeInvariantError("structural segmentation produced no segments")
    if segments[0].source_byte_start != 0:
        raise KnowledgeInvariantError("structural segmentation does not start at byte zero")
    if segments[-1].source_byte_end != len(content):
        raise KnowledgeInvariantError("structural segmentation does not end at artifact size")

    cursor = 0
    reconstructed = bytearray()
    for expected_ordinal, segment in enumerate(segments):
        if segment.segment_ordinal != expected_ordinal:
            raise KnowledgeInvariantError("structural segment ordinals are not contiguous")
        if segment.source_byte_start != cursor:
            raise KnowledgeInvariantError("structural segment ranges have a gap or overlap")
        source_slice = content[segment.source_byte_start : segment.source_byte_end]
        if sha256(source_slice).hexdigest() != segment.source_slice_sha256:
            raise KnowledgeInvariantError("structural segment source-slice digest mismatch")
        reconstructed.extend(source_slice)
        cursor = segment.source_byte_end

    if bytes(reconstructed) != content:
        raise KnowledgeInvariantError("structural segments do not reconstruct exact source")
