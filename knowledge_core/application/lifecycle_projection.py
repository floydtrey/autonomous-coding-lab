from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import re
from uuid import UUID

from knowledge_core.application.segmentation import (
    MarkdownFenceSpan,
    MarkdownHeading,
    StructuralSegmentation,
    StructuralSegment,
    scan_markdown_structure,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.retrieval import RetrievalLifecycleState


_VALID_DIRECTIVE = re.compile(
    rb"^ {0,3}<!-- kc:retrieval-lifecycle=(current|unknown|superseded) -->[ \t]*$"
)
_CONTROL_PREFIX = b"<!-- kc:retrieval-lifecycle"
_LIFECYCLE_PRIORITY = {
    RetrievalLifecycleState.CURRENT: 0,
    RetrievalLifecycleState.UNKNOWN: 1,
    RetrievalLifecycleState.SUPERSEDED: 2,
}


@dataclass(frozen=True)
class RetrievalProjectionProfile:
    structural_profile_digest: str
    profile_id: str = "kc-section-retrieval-projection-v1"
    lifecycle_directive_grammar_version: str = "kc-retrieval-lifecycle-v1"
    effective_lifecycle_rule: str = "most-restrictive-v1"
    lexical_language: str = "english"
    lexical_projection: str = "local-minus-own-directive-A-heading-context-B"

    @property
    def canonical_config(self) -> dict[str, object]:
        return {
            "effective_lifecycle_rule": self.effective_lifecycle_rule,
            "lexical_language": self.lexical_language,
            "lexical_projection": self.lexical_projection,
            "lifecycle_directive_grammar_version": (
                self.lifecycle_directive_grammar_version
            ),
            "profile_id": self.profile_id,
            "ranking": [
                "lexical_score:desc",
                "effective_lifecycle:current-unknown-superseded",
                "authority_rank:asc:nulls-last",
                "parent_created_revision_id:desc",
                "resource_version_ref:asc",
                "segment_ordinal:asc",
                "segment_key:asc",
            ],
            "structural_profile_digest": self.structural_profile_digest,
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


@dataclass(frozen=True)
class GovernedRetrievalObservation:
    observation_id: UUID
    manifest_digest: str
    source_repository_key: str
    repository_locator: str
    source_document_key: str
    source_commit: str
    source_path: str
    git_blob_sha: str
    resource_version_ref: UUID
    classification: str
    document_lifecycle: RetrievalLifecycleState
    authority_rank: int | None
    rationale: str


@dataclass(frozen=True)
class LifecycleDeclaration:
    lifecycle_state: RetrievalLifecycleState
    heading_source_byte_start: int
    source_line: int
    source_byte_start: int
    source_byte_end: int


class LifecycleControlOrigin(StrEnum):
    DOCUMENT = "document"
    ANCESTOR = "ancestor"
    OWN = "own"


@dataclass(frozen=True)
class EffectiveLifecycleControl:
    origin: LifecycleControlOrigin
    lifecycle_state: RetrievalLifecycleState
    declaration: LifecycleDeclaration | None


@dataclass(frozen=True)
class SegmentLifecycleProjection:
    structural_segment: StructuralSegment
    governed_observation: GovernedRetrievalObservation
    declared_lifecycle: RetrievalLifecycleState | None
    declaration: LifecycleDeclaration | None
    effective_lifecycle: RetrievalLifecycleState
    effective_controls: tuple[EffectiveLifecycleControl, ...]


@dataclass(frozen=True)
class GovernedLifecycleProjection:
    resource_version_ref: UUID
    structural_profile_digest: str
    projection_profile_id: str
    projection_profile_digest: str
    governed_observation_id: UUID
    segments: tuple[SegmentLifecycleProjection, ...]


@dataclass(frozen=True)
class _Line:
    number: int
    start: int
    end: int
    content: bytes

    @property
    def is_blank(self) -> bool:
        return not self.content.strip(b" \t")


def project_governed_lifecycle(
    *,
    structural: StructuralSegmentation,
    content: bytes,
    observation: GovernedRetrievalObservation,
    profile: RetrievalProjectionProfile | None = None,
) -> GovernedLifecycleProjection:
    """Project governed and source-declared lifecycle over stable structure."""

    if observation.resource_version_ref != structural.resource_version_ref:
        raise KnowledgeInvariantError(
            "governed observation resource version does not match structural parent"
        )

    _verify_structural_input(structural, content)

    projection_profile = profile or RetrievalProjectionProfile(
        structural_profile_digest=structural.profile_digest
    )
    if projection_profile.structural_profile_digest != structural.profile_digest:
        raise KnowledgeInvariantError(
            "retrieval projection profile does not bind structural profile digest"
        )

    declarations: dict[int, LifecycleDeclaration]
    if structural.media_type == "text/markdown":
        declarations = _parse_markdown_declarations(content)
    else:
        declarations = {}

    projected: list[SegmentLifecycleProjection] = []
    for segment in structural.segments:
        own_heading_start = (
            segment.heading_path[-1].source_byte_start
            if segment.heading_path
            else None
        )
        own_declaration = (
            declarations.get(own_heading_start)
            if own_heading_start is not None
            else None
        )

        controls: list[EffectiveLifecycleControl] = [
            EffectiveLifecycleControl(
                origin=LifecycleControlOrigin.DOCUMENT,
                lifecycle_state=observation.document_lifecycle,
                declaration=None,
            )
        ]
        for heading in segment.heading_path:
            declaration = declarations.get(heading.source_byte_start)
            if declaration is None:
                continue
            controls.append(
                EffectiveLifecycleControl(
                    origin=(
                        LifecycleControlOrigin.OWN
                        if heading.source_byte_start == own_heading_start
                        else LifecycleControlOrigin.ANCESTOR
                    ),
                    lifecycle_state=declaration.lifecycle_state,
                    declaration=declaration,
                )
            )

        effective = max(
            (control.lifecycle_state for control in controls),
            key=_LIFECYCLE_PRIORITY.__getitem__,
        )
        effective_controls = tuple(
            control for control in controls if control.lifecycle_state == effective
        )

        projected.append(
            SegmentLifecycleProjection(
                structural_segment=segment,
                governed_observation=observation,
                declared_lifecycle=(
                    own_declaration.lifecycle_state
                    if own_declaration is not None
                    else None
                ),
                declaration=own_declaration,
                effective_lifecycle=effective,
                effective_controls=effective_controls,
            )
        )

    return GovernedLifecycleProjection(
        resource_version_ref=structural.resource_version_ref,
        structural_profile_digest=structural.profile_digest,
        projection_profile_id=projection_profile.profile_id,
        projection_profile_digest=projection_profile.digest,
        governed_observation_id=observation.observation_id,
        segments=tuple(projected),
    )


def _parse_markdown_declarations(
    content: bytes,
) -> dict[int, LifecycleDeclaration]:
    markdown = scan_markdown_structure(content)
    lines = _scan_lines(content)
    headings = markdown.headings
    attempted_by_heading: dict[int, list[_Line]] = {}

    for line in lines:
        if _line_inside_fence(line, markdown.fence_spans):
            continue
        if not _is_control_looking(line.content):
            continue

        heading = _owning_heading(line, headings, len(content))
        if heading is None:
            raise KnowledgeInvariantError(
                "standalone lifecycle control is misplaced outside a heading body"
            )
        attempted_by_heading.setdefault(heading.start, []).append(line)

    declarations: dict[int, LifecycleDeclaration] = {}
    for heading in headings:
        attempts = attempted_by_heading.get(heading.start, [])
        if not attempts:
            continue
        if len(attempts) > 1:
            raise KnowledgeInvariantError(
                "duplicate standalone lifecycle controls for one heading"
            )

        attempted = attempts[0]
        first_nonblank = _first_nonblank_body_line(
            heading=heading,
            headings=headings,
            lines=lines,
            content_size=len(content),
        )
        if first_nonblank is None or first_nonblank.start != attempted.start:
            raise KnowledgeInvariantError(
                "standalone lifecycle control is misplaced; it must be the first "
                "non-blank body line after its heading"
            )

        matched = _VALID_DIRECTIVE.fullmatch(attempted.content)
        if matched is None:
            raise KnowledgeInvariantError(
                "malformed standalone lifecycle control"
            )

        state = RetrievalLifecycleState(matched.group(1).decode("ascii"))
        declarations[heading.start] = LifecycleDeclaration(
            lifecycle_state=state,
            heading_source_byte_start=heading.start,
            source_line=attempted.number,
            source_byte_start=attempted.start,
            source_byte_end=attempted.end,
        )

    return declarations


def _scan_lines(content: bytes) -> tuple[_Line, ...]:
    try:
        content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise KnowledgeInvariantError(
            "lifecycle projection requires strict UTF-8 source bytes"
        ) from exc

    result: list[_Line] = []
    cursor = 0
    number = 1
    while cursor < len(content):
        newline = content.find(b"\n", cursor)
        if newline < 0:
            end = len(content)
            content_end = end
        else:
            end = newline + 1
            content_end = (
                newline - 1
                if newline > cursor and content[newline - 1] == 13
                else newline
            )
        result.append(
            _Line(
                number=number,
                start=cursor,
                end=end,
                content=content[cursor:content_end],
            )
        )
        cursor = end
        number += 1
    return tuple(result)


def _line_inside_fence(
    line: _Line,
    fence_spans: tuple[MarkdownFenceSpan, ...],
) -> bool:
    return any(span.start <= line.start < span.end for span in fence_spans)


def _is_control_looking(content: bytes) -> bool:
    leading = 0
    while leading < len(content) and leading < 4 and content[leading] == 32:
        leading += 1
    if leading > 3:
        return False
    return content[leading:].startswith(_CONTROL_PREFIX)


def _owning_heading(
    line: _Line,
    headings: tuple[MarkdownHeading, ...],
    content_size: int,
) -> MarkdownHeading | None:
    for index, heading in enumerate(headings):
        end = headings[index + 1].start if index + 1 < len(headings) else content_size
        if heading.end <= line.start < end:
            return heading
    return None


def _first_nonblank_body_line(
    *,
    heading: MarkdownHeading,
    headings: tuple[MarkdownHeading, ...],
    lines: tuple[_Line, ...],
    content_size: int,
) -> _Line | None:
    index = next(
        item for item, candidate in enumerate(headings) if candidate.start == heading.start
    )
    body_end = headings[index + 1].start if index + 1 < len(headings) else content_size
    for line in lines:
        if heading.end <= line.start < body_end and not line.is_blank:
            return line
    return None


def _verify_structural_input(
    structural: StructuralSegmentation,
    content: bytes,
) -> None:
    if not structural.segments:
        raise KnowledgeInvariantError("lifecycle projection requires structural segments")

    cursor = 0
    reconstructed = bytearray()
    for ordinal, segment in enumerate(structural.segments):
        if segment.segment_ordinal != ordinal:
            raise KnowledgeInvariantError(
                "lifecycle projection received non-contiguous structural ordinals"
            )
        if segment.source_byte_start != cursor:
            raise KnowledgeInvariantError(
                "lifecycle projection received gapped/overlapping structural input"
            )
        source_slice = content[segment.source_byte_start : segment.source_byte_end]
        if sha256(source_slice).hexdigest() != segment.source_slice_sha256:
            raise KnowledgeInvariantError(
                "lifecycle projection source bytes do not match structural slice digest"
            )
        reconstructed.extend(source_slice)
        cursor = segment.source_byte_end

    if cursor != len(content) or bytes(reconstructed) != content:
        raise KnowledgeInvariantError(
            "lifecycle projection source bytes do not reconstruct structural parent"
        )
