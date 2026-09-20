from __future__ import annotations

from hashlib import sha256
import json
import re

from knowledge_core.application.lifecycle_projection import GovernedRetrievalObservation


_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def projection_snapshot_digest(
    *,
    observation: GovernedRetrievalObservation,
    governing_manifest_digest: str,
) -> str:
    """Digest the exact governed document-level inputs used for SR-2 projection."""

    if not _HEX64.fullmatch(observation.manifest_digest):
        raise ValueError(
            "source observation manifest digest must be 64 lowercase hexadecimal characters"
        )
    if not _HEX64.fullmatch(governing_manifest_digest):
        raise ValueError(
            "governing manifest digest must be 64 lowercase hexadecimal characters"
        )

    payload = {
        "governing_manifest_digest": governing_manifest_digest,
        "snapshot_version": 1,
        "source_observation": {
            "authority_rank": observation.authority_rank,
            "classification": observation.classification,
            "document_lifecycle": observation.document_lifecycle.value,
            "git_blob_sha": observation.git_blob_sha,
            "manifest_digest": observation.manifest_digest,
            "observation_id": str(observation.observation_id).lower(),
            "rationale": observation.rationale,
            "repository_locator": observation.repository_locator,
            "resource_version_ref": str(observation.resource_version_ref).lower(),
            "source_commit": observation.source_commit,
            "source_document_key": observation.source_document_key,
            "source_path": observation.source_path,
            "source_repository_key": observation.source_repository_key,
        },
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()
