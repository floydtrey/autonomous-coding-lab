from __future__ import annotations

from hashlib import sha256
from uuid import UUID

import pytest

from knowledge_core.application.segmentation import (
    DEFAULT_SECTION_SEGMENTATION_PROFILE,
    SectionSegmentationProfile,
    segment_structural_content,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError


RESOURCE_A = UUID("11111111-1111-1111-1111-111111111111")
RESOURCE_B = UUID("22222222-2222-2222-2222-222222222222")


def _ranges(result):
    return [
        (segment.source_byte_start, segment.source_byte_end)
        for segment in result.segments
    ]


def _keys(result):
    return [segment.segment_key for segment in result.segments]


def test_sr2_g2_g3_g4_exact_partition_headings_fences_and_control_discussion():
    content = (
        b"preamble\r\n"
        b"Setext-looking\r\n"
        b"---\r\n"
        b"# Alpha\r\n"
        b"alpha body with `kc:retrieval-lifecycle=current`\r\n"
        b"> <!-- kc:retrieval-lifecycle=superseded -->\r\n"
        b"## Child ##\r\n"
        b"| a | b |\r\n"
        b"|---|---|\r\n"
        b"```md\r\n"
        b"# fake heading\r\n"
        b"<!-- kc:retrieval-lifecycle=superseded -->\r\n"
        b"```\r\n"
        b"#### Skipped\r\n"
        b"tail \xc3\xa9\r\n"
    )

    result = segment_structural_content(
        resource_version_ref=RESOURCE_A,
        media_type="text/markdown",
        content=content,
    )

    assert [segment.structural_kind for segment in result.segments] == [
        "preamble",
        "section",
        "section",
        "section",
    ]
    assert [segment.segment_ordinal for segment in result.segments] == [0, 1, 2, 3]

    alpha = result.segments[1]
    child = result.segments[2]
    skipped = result.segments[3]
    assert [(x.level, x.display_text) for x in alpha.heading_path] == [(1, "Alpha")]
    assert [(x.level, x.display_text) for x in child.heading_path] == [
        (1, "Alpha"),
        (2, "Child"),
    ]
    assert [(x.level, x.display_text) for x in skipped.heading_path] == [
        (1, "Alpha"),
        (2, "Child"),
        (4, "Skipped"),
    ]

    assert result.segments[0].source_line_start == 1
    assert alpha.source_line_start == 4
    assert child.source_line_start == 7
    assert skipped.source_line_start == 14

    rebuilt = b"".join(
        content[segment.source_byte_start : segment.source_byte_end]
        for segment in result.segments
    )
    assert rebuilt == content
    assert result.segments[0].source_byte_start == 0
    assert result.segments[-1].source_byte_end == len(content)
    for left, right in zip(result.segments, result.segments[1:]):
        assert left.source_byte_end == right.source_byte_start
    for segment in result.segments:
        source_slice = content[segment.source_byte_start : segment.source_byte_end]
        assert sha256(source_slice).hexdigest() == segment.source_slice_sha256


def test_sr2_g5_large_continuation_has_predeclared_boundaries_and_final_suffix():
    profile = SectionSegmentationProfile(
        soft_target_bytes=12,
        hard_max_bytes=18,
    )
    content = (
        b"# H\n"
        b"aaaa\n"
        b"\n"
        b"bbbb\n"
        b"cccc\n"
        b"\n"
        b"dddd\n"
        b"eeee\n"
        b"tail\n"
    )

    first = segment_structural_content(
        resource_version_ref=RESOURCE_A,
        media_type="text/markdown",
        content=content,
        profile=profile,
    )
    second = segment_structural_content(
        resource_version_ref=RESOURCE_A,
        media_type="text/markdown",
        content=content,
        profile=profile,
    )

    assert _ranges(first) == [(0, 10), (10, 21), (21, 36)]
    assert _ranges(second) == _ranges(first)
    assert _keys(second) == _keys(first)
    assert [segment.structural_kind for segment in first.segments] == [
        "section",
        "continuation",
        "continuation",
    ]
    assert [segment.part_index for segment in first.segments] == [1, 2, 3]
    assert [segment.part_count for segment in first.segments] == [3, 3, 3]
    assert all(segment.source_byte_end - segment.source_byte_start <= 18 for segment in first.segments)
    assert first.segments[-1].source_byte_end - first.segments[-1].source_byte_start == 15
    assert all(
        [(item.level, item.display_text) for item in segment.heading_path] == [(1, "H")]
        for segment in first.segments
    )


def test_sr2_g6_oversized_indivisible_line_and_fence_fail_closed():
    profile = SectionSegmentationProfile(
        soft_target_bytes=8,
        hard_max_bytes=16,
    )

    with pytest.raises(KnowledgeInvariantError, match="no legal boundary"):
        segment_structural_content(
            resource_version_ref=RESOURCE_A,
            media_type="text/plain",
            content=b"x" * 17 + b"\n",
            profile=profile,
        )

    oversized_fence = b"```\n" + (b"x\n" * 8) + b"```\n"
    assert len(oversized_fence) > profile.hard_max_bytes
    with pytest.raises(KnowledgeInvariantError, match="no legal boundary"):
        segment_structural_content(
            resource_version_ref=RESOURCE_A,
            media_type="text/markdown",
            content=oversized_fence,
            profile=profile,
        )


def test_sr2_g7_g8_structural_identity_is_content_profile_and_parent_bound():
    content_a = b"# A\nsame text\n"
    content_b = b"# A\nchanged text\n"

    first_a = segment_structural_content(
        resource_version_ref=RESOURCE_A,
        media_type="text/markdown",
        content=content_a,
    )
    repeat_a = segment_structural_content(
        resource_version_ref=RESOURCE_A,
        media_type="text/markdown",
        content=content_a,
    )
    version_b = segment_structural_content(
        resource_version_ref=RESOURCE_B,
        media_type="text/markdown",
        content=content_b,
    )
    return_to_a = segment_structural_content(
        resource_version_ref=RESOURCE_A,
        media_type="text/markdown",
        content=content_a,
    )

    assert first_a == repeat_a == return_to_a
    assert _keys(first_a) != _keys(version_b)

    duplicate_parent = segment_structural_content(
        resource_version_ref=RESOURCE_B,
        media_type="text/markdown",
        content=content_a,
    )
    assert [
        segment.source_slice_sha256 for segment in duplicate_parent.segments
    ] == [segment.source_slice_sha256 for segment in first_a.segments]
    assert _keys(duplicate_parent) != _keys(first_a)


def test_sr2_g21_structural_profile_change_changes_digest_and_key_space():
    content = b"# A\nsmall\n"
    default = segment_structural_content(
        resource_version_ref=RESOURCE_A,
        media_type="text/markdown",
        content=content,
    )
    changed_profile = SectionSegmentationProfile(
        soft_target_bytes=12000,
        hard_max_bytes=32768,
    )
    changed = segment_structural_content(
        resource_version_ref=RESOURCE_A,
        media_type="text/markdown",
        content=content,
        profile=changed_profile,
    )

    assert default.profile_digest == DEFAULT_SECTION_SEGMENTATION_PROFILE.digest
    assert changed.profile_digest != default.profile_digest
    assert _ranges(changed) == _ranges(default)
    assert _keys(changed) != _keys(default)


def test_empty_document_and_strict_utf8_are_deterministic():
    empty = segment_structural_content(
        resource_version_ref=RESOURCE_A,
        media_type="text/plain",
        content=b"",
    )
    assert len(empty.segments) == 1
    segment = empty.segments[0]
    assert (segment.source_byte_start, segment.source_byte_end) == (0, 0)
    assert (segment.source_line_start, segment.source_line_end) == (1, 1)
    assert segment.source_slice_sha256 == sha256(b"").hexdigest()

    with pytest.raises(KnowledgeInvariantError, match="strict UTF-8"):
        segment_structural_content(
            resource_version_ref=RESOURCE_A,
            media_type="text/plain",
            content=b"\xff",
        )

    with pytest.raises(KnowledgeInvariantError, match="unsupported"):
        segment_structural_content(
            resource_version_ref=RESOURCE_A,
            media_type="application/pdf",
            content=b"plain bytes",
        )
