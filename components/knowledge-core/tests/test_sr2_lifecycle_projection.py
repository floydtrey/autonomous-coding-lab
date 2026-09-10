from __future__ import annotations

from uuid import UUID

import pytest

from knowledge_core.application.lifecycle_projection import (
    GovernedRetrievalObservation,
    LifecycleControlOrigin,
    RetrievalProjectionProfile,
    project_governed_lifecycle,
)
from knowledge_core.application.segmentation import segment_structural_content
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.retrieval import RetrievalLifecycleState


RESOURCE = UUID("11111111-1111-1111-1111-111111111111")
OBS_CURRENT = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OBS_SUPERSEDED = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _observation(
    *,
    observation_id=OBS_CURRENT,
    lifecycle=RetrievalLifecycleState.CURRENT,
    resource_version_ref=RESOURCE,
):
    return GovernedRetrievalObservation(
        observation_id=observation_id,
        manifest_digest="m" * 64,
        source_repository_key="acl",
        repository_locator="git://acl",
        source_document_key="doc",
        source_commit="c" * 40,
        source_path="doc.md",
        git_blob_sha="b" * 40,
        resource_version_ref=resource_version_ref,
        classification="approved",
        document_lifecycle=lifecycle,
        authority_rank=5,
        rationale="explicit fixture classification",
    )


def _by_heading(projection, name):
    for item in projection.segments:
        if item.structural_segment.heading_path:
            if item.structural_segment.heading_path[-1].display_text == name:
                return item
    raise AssertionError(name)


def test_sr2_g11_exact_controls_and_ordinary_mentions_are_distinguished():
    content = (
        b"discussion kc:retrieval-lifecycle=current\n"
        b"`<!-- kc:retrieval-lifecycle=current -->`\n"
        b"> <!-- kc:retrieval-lifecycle=current -->\n"
        b"# Alpha\n"
        b"\n"
        b"<!-- kc:retrieval-lifecycle=unknown -->   \n"
        b"alpha\n"
        b"## Child\n"
        b"```md\n"
        b"<!-- kc:retrieval-lifecycle=superseded -->\n"
        b"```\n"
        b"child\n"
    )
    structural = segment_structural_content(
        resource_version_ref=RESOURCE,
        media_type="text/markdown",
        content=content,
    )
    projected = project_governed_lifecycle(
        structural=structural,
        content=content,
        observation=_observation(),
    )

    alpha = _by_heading(projected, "Alpha")
    child = _by_heading(projected, "Child")
    assert alpha.declared_lifecycle == RetrievalLifecycleState.UNKNOWN
    assert alpha.declaration is not None
    assert alpha.declaration.source_line == 6
    assert alpha.effective_lifecycle == RetrievalLifecycleState.UNKNOWN
    assert [x.origin for x in alpha.effective_controls] == [
        LifecycleControlOrigin.OWN
    ]

    assert child.declared_lifecycle is None
    assert child.effective_lifecycle == RetrievalLifecycleState.UNKNOWN
    assert [x.origin for x in child.effective_controls] == [
        LifecycleControlOrigin.ANCESTOR
    ]


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (
            b"# H\n<!-- kc:retrieval-lifecycle=banana -->\n",
            "malformed",
        ),
        (
            b"# H\nbody\n<!-- kc:retrieval-lifecycle=current -->\n",
            "misplaced",
        ),
        (
            b"# H\n<!-- kc:retrieval-lifecycle=current -->\n"
            b"<!-- kc:retrieval-lifecycle=unknown -->\n",
            "duplicate",
        ),
        (
            b"<!-- kc:retrieval-lifecycle=current -->\n# H\nbody\n",
            "misplaced",
        ),
    ],
)
def test_sr2_g11_control_looking_malformed_misplaced_and_duplicate_fail(
    content,
    message,
):
    structural = segment_structural_content(
        resource_version_ref=RESOURCE,
        media_type="text/markdown",
        content=content,
    )
    with pytest.raises(KnowledgeInvariantError, match=message):
        project_governed_lifecycle(
            structural=structural,
            content=content,
            observation=_observation(),
        )


def test_sr2_g12_ancestor_superseded_child_current_preserves_declaration():
    content = (
        b"# Parent\n"
        b"<!-- kc:retrieval-lifecycle=superseded -->\n"
        b"parent\n"
        b"## Child\n"
        b"<!-- kc:retrieval-lifecycle=current -->\n"
        b"child\n"
    )
    structural = segment_structural_content(
        resource_version_ref=RESOURCE,
        media_type="text/markdown",
        content=content,
    )
    projected = project_governed_lifecycle(
        structural=structural,
        content=content,
        observation=_observation(),
    )

    parent = _by_heading(projected, "Parent")
    child = _by_heading(projected, "Child")
    assert parent.declared_lifecycle == RetrievalLifecycleState.SUPERSEDED
    assert parent.effective_lifecycle == RetrievalLifecycleState.SUPERSEDED
    assert child.declared_lifecycle == RetrievalLifecycleState.CURRENT
    assert child.effective_lifecycle == RetrievalLifecycleState.SUPERSEDED
    assert [x.origin for x in child.effective_controls] == [
        LifecycleControlOrigin.ANCESTOR
    ]


@pytest.mark.parametrize(
    "document_lifecycle",
    [
        RetrievalLifecycleState.UNKNOWN,
        RetrievalLifecycleState.SUPERSEDED,
    ],
)
def test_sr2_g12_less_restrictive_child_cannot_promote_document(
    document_lifecycle,
):
    content = (
        b"# H\n"
        b"<!-- kc:retrieval-lifecycle=current -->\n"
        b"body\n"
    )
    structural = segment_structural_content(
        resource_version_ref=RESOURCE,
        media_type="text/markdown",
        content=content,
    )
    projected = project_governed_lifecycle(
        structural=structural,
        content=content,
        observation=_observation(lifecycle=document_lifecycle),
    )
    item = _by_heading(projected, "H")
    assert item.declared_lifecycle == RetrievalLifecycleState.CURRENT
    assert item.effective_lifecycle == document_lifecycle
    assert [x.origin for x in item.effective_controls] == [
        LifecycleControlOrigin.DOCUMENT
    ]


def test_sr2_g7_g12_parent_downgrade_reprojects_same_structural_keys():
    content = (
        b"# H\n"
        b"<!-- kc:retrieval-lifecycle=current -->\n"
        b"body\n"
    )
    structural = segment_structural_content(
        resource_version_ref=RESOURCE,
        media_type="text/markdown",
        content=content,
    )
    current = project_governed_lifecycle(
        structural=structural,
        content=content,
        observation=_observation(),
    )
    superseded = project_governed_lifecycle(
        structural=structural,
        content=content,
        observation=_observation(
            observation_id=OBS_SUPERSEDED,
            lifecycle=RetrievalLifecycleState.SUPERSEDED,
        ),
    )

    assert [
        x.structural_segment.segment_key for x in current.segments
    ] == [
        x.structural_segment.segment_key for x in superseded.segments
    ]
    assert _by_heading(current, "H").effective_lifecycle == RetrievalLifecycleState.CURRENT
    assert (
        _by_heading(superseded, "H").effective_lifecycle
        == RetrievalLifecycleState.SUPERSEDED
    )
    assert current.governed_observation_id == OBS_CURRENT
    assert superseded.governed_observation_id == OBS_SUPERSEDED
    assert current.projection_profile_digest == superseded.projection_profile_digest


def test_heading_named_historical_does_not_infer_lifecycle():
    content = b"# Historical\nstill current\n"
    structural = segment_structural_content(
        resource_version_ref=RESOURCE,
        media_type="text/markdown",
        content=content,
    )
    projected = project_governed_lifecycle(
        structural=structural,
        content=content,
        observation=_observation(),
    )
    item = _by_heading(projected, "Historical")
    assert item.declared_lifecycle is None
    assert item.effective_lifecycle == RetrievalLifecycleState.CURRENT
    assert [x.origin for x in item.effective_controls] == [
        LifecycleControlOrigin.DOCUMENT
    ]


def test_plain_text_control_like_content_has_no_directive_semantics():
    content = b"<!-- kc:retrieval-lifecycle=superseded -->\nplain\n"
    structural = segment_structural_content(
        resource_version_ref=RESOURCE,
        media_type="text/plain",
        content=content,
    )
    projected = project_governed_lifecycle(
        structural=structural,
        content=content,
        observation=_observation(),
    )
    assert projected.segments[0].declared_lifecycle is None
    assert (
        projected.segments[0].effective_lifecycle
        == RetrievalLifecycleState.CURRENT
    )


def test_projection_rejects_wrong_observation_or_structural_profile_binding():
    content = b"# H\nbody\n"
    structural = segment_structural_content(
        resource_version_ref=RESOURCE,
        media_type="text/markdown",
        content=content,
    )

    with pytest.raises(KnowledgeInvariantError, match="resource version"):
        project_governed_lifecycle(
            structural=structural,
            content=content,
            observation=_observation(
                resource_version_ref=UUID(
                    "33333333-3333-3333-3333-333333333333"
                )
            ),
        )

    with pytest.raises(KnowledgeInvariantError, match="structural profile"):
        project_governed_lifecycle(
            structural=structural,
            content=content,
            observation=_observation(),
            profile=RetrievalProjectionProfile(
                structural_profile_digest="sha256:" + ("0" * 64)
            ),
        )
