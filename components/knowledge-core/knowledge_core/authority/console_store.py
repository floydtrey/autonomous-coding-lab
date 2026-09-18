from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from knowledge_core.api.bootstrap_contract import BOOTSTRAP_PRINCIPAL_REF
from knowledge_core.authority.store import (
    CanonicalStoreAuthorityDecision,
    CanonicalStoreAuthorityRequest,
)


@dataclass(frozen=True)
class ConsoleCanonicalStoreAuthorityEvaluator:
    """Trusted owner-only canonical-store decision for console requests."""

    allowed_projects: frozenset[str]

    def __post_init__(self) -> None:
        if not self.allowed_projects:
            raise ValueError("console authority requires at least one project")
        if any(not project.strip() for project in self.allowed_projects):
            raise ValueError("console project keys must be non-blank")

    def evaluate_canonical_store(
        self,
        request: CanonicalStoreAuthorityRequest,
    ) -> CanonicalStoreAuthorityDecision:
        if request.caller_principal_ref != BOOTSTRAP_PRINCIPAL_REF:
            return CanonicalStoreAuthorityDecision(
                allowed=False,
                decision_ref="console-owner:principal-denied",
                reason_code="console-owner-principal-mismatch",
            )
        if request.project_key not in self.allowed_projects:
            return CanonicalStoreAuthorityDecision(
                allowed=False,
                decision_ref="console-owner:project-denied",
                reason_code="console-owner-project-not-allowed",
            )

        payload = {
            "principal_ref": request.caller_principal_ref,
            "operation_id": str(request.operation_id),
            "project_key": request.project_key,
            "content_sha256": request.content_sha256,
            "source_id": request.source_id,
            "source_event_time": (
                request.source_event_time.isoformat()
                if request.source_event_time is not None
                else None
            ),
            "capture_metadata_digest": request.capture_metadata_digest,
        }
        digest = sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        return CanonicalStoreAuthorityDecision(
            allowed=True,
            decision_ref=f"console-owner:sha256:{digest}",
            reason_code="console-owner-session-and-project-authorized",
        )
