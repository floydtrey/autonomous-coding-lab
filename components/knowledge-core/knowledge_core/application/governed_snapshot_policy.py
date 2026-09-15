from __future__ import annotations

from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.governed_sources import GovernedRetrievalSnapshot


COMPLETE_CORPUS_SELECTION_POLICY_ID = "kc-complete-corpus-selection-v1"


def validate_complete_snapshot(snapshot: GovernedRetrievalSnapshot) -> None:
    """Validate source-neutral complete-corpus selection invariants.

    A source identity may not be both selected and explicitly excluded in the same
    governed snapshot. This rule belongs to the generic governed corpus boundary,
    not to any producer adapter such as Git repository import or direct notes.
    """

    member_identities = {item.source_identity_digest for item in snapshot.members}
    exclusion_identities = {
        item.source_identity_digest for item in snapshot.exclusions
    }
    overlap = member_identities & exclusion_identities
    if overlap:
        raise KnowledgeInvariantError(
            "complete governed snapshot both selects and excludes a source identity"
        )
