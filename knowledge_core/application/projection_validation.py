from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Mapping
from uuid import UUID

from sqlalchemy import select

from knowledge_core.application.projection_evidence import ProjectionEvidenceKnowledgeKernel
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.projection_evidence import (
    ProjectionDisposition,
    ProjectionValidationState,
)
from knowledge_core.domain.projection_validation import (
    ProjectionCheckOutcome,
    ProjectionValidationCheck,
    ProjectionValidationCheckSnapshot,
    ProjectionValidationOutcome,
    ProjectionValidationReport,
    ProjectionValidationRequirement,
    ProjectionValidationReuseError,
    ProjectionValidationSnapshot,
    ProjectionValidationStateError,
    ProjectionValidator,
    ProjectionValidatorDescriptor,
)
from knowledge_core.storage.projection_models import ProjectionAttempt
from knowledge_core.storage.projection_validation_models import (
    ProjectionValidationCheckRecord,
    ProjectionValidationRecord,
)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _required_text(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise KnowledgeInvariantError(f"{name} must not be empty")
    return normalized


def _canonical_json(value: Mapping[str, object]) -> tuple[dict[str, object], str]:
    try:
        normalized = dict(value)
        encoded = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProjectionValidationStateError(
            "projection validation evidence must be deterministic JSON"
        ) from exc
    return normalized, sha256(encoded).hexdigest()


def _request_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _normalize_descriptor(descriptor: ProjectionValidatorDescriptor) -> ProjectionValidatorDescriptor:
    return ProjectionValidatorDescriptor(
        validator_identity=_required_text("validator_identity", descriptor.validator_identity),
        validator_version=descriptor.validator_version,
        ruleset_id=descriptor.ruleset_id,
        ruleset_digest=descriptor.ruleset_digest,
    )


def _normalize_report(
    report: ProjectionValidationReport,
    *,
    projection_disposition: ProjectionDisposition,
) -> tuple[ProjectionValidationOutcome, tuple[tuple[ProjectionValidationCheck, dict[str, object], str], ...]]:
    outcome = ProjectionValidationOutcome(report.outcome)
    if outcome is ProjectionValidationOutcome.PENDING:
        raise ProjectionValidationStateError("validator cannot return a pending terminal report")

    normalized: list[tuple[ProjectionValidationCheck, dict[str, object], str]] = []
    seen_codes: set[str] = set()
    for check in report.checks:
        check_code = _required_text("check_code", check.check_code)
        if check_code in seen_codes:
            raise ProjectionValidationStateError(
                f"duplicate projection validation check code: {check_code}"
            )
        seen_codes.add(check_code)
        evidence, evidence_digest = _canonical_json(check.evidence)
        normalized.append(
            (
                ProjectionValidationCheck(
                    check_code=check_code,
                    outcome=ProjectionCheckOutcome(check.outcome),
                    evidence=evidence,
                    detail=check.detail,
                ),
                evidence,
                evidence_digest,
            )
        )

    checks = tuple(normalized)
    outcomes = tuple(item[0].outcome for item in checks)

    if outcome is ProjectionValidationOutcome.VALIDATED:
        if projection_disposition is not ProjectionDisposition.SUCCEEDED:
            raise ProjectionValidationStateError(
                "only a succeeded projection attempt can be validated"
            )
        if not checks or any(outcome is not ProjectionCheckOutcome.PASSED for outcome in outcomes):
            raise ProjectionValidationStateError(
                "validated projection requires one or more passing checks and no failed or indeterminate checks"
            )
    elif outcome in (
        ProjectionValidationOutcome.INCOMPLETE,
        ProjectionValidationOutcome.REJECTED,
    ):
        if not checks or ProjectionCheckOutcome.FAILED not in outcomes:
            raise ProjectionValidationStateError(
                f"{outcome.value} validation requires at least one failed check"
            )
    elif outcome is ProjectionValidationOutcome.QUARANTINED:
        if not checks or ProjectionCheckOutcome.INDETERMINATE not in outcomes:
            raise ProjectionValidationStateError(
                "quarantined validation requires at least one indeterminate check"
            )

    return outcome, checks


class ProjectionValidationKnowledgeKernel(ProjectionEvidenceKnowledgeKernel):
    """Independent deterministic trust gate for provider-neutral projection evidence."""

    def read_projection_validation(self, validation_id: UUID) -> ProjectionValidationSnapshot:
        row = self.session.get(ProjectionValidationRecord, validation_id)
        if row is None:
            raise KnowledgeInvariantError(f"unknown projection validation: {validation_id}")
        check_rows = self.session.scalars(
            select(ProjectionValidationCheckRecord)
            .where(ProjectionValidationCheckRecord.validation_id == validation_id)
            .order_by(ProjectionValidationCheckRecord.ordinal)
        ).all()
        return ProjectionValidationSnapshot(
            validation_id=row.validation_id,
            attempt_id=row.attempt_id,
            attempt_request_digest=row.attempt_request_digest,
            request_digest=row.request_digest,
            validator_identity=row.validator_identity,
            validator_version=row.validator_version,
            ruleset_id=row.ruleset_id,
            ruleset_digest=row.ruleset_digest,
            config_digest=row.config_digest,
            outcome=ProjectionValidationOutcome(row.outcome),
            started_at=_utc(row.started_at),
            settled_at=_utc(row.settled_at) if row.settled_at is not None else None,
            error_code=row.error_code,
            error_detail=row.error_detail,
            checks=tuple(
                ProjectionValidationCheckSnapshot(
                    check_code=check.check_code,
                    outcome=ProjectionCheckOutcome(check.outcome),
                    evidence_digest=check.evidence_digest,
                    evidence=dict(check.evidence_json),
                    detail=check.detail,
                )
                for check in check_rows
            ),
        )

    def projection_satisfies_validation_requirement(
        self,
        *,
        attempt_id: UUID,
        requirement: ProjectionValidationRequirement,
    ) -> bool:
        validation_ids = tuple(
            self.session.scalars(
                select(ProjectionValidationRecord.validation_id).where(
                    ProjectionValidationRecord.attempt_id == attempt_id,
                    ProjectionValidationRecord.validator_identity
                    == requirement.validator_identity,
                    ProjectionValidationRecord.validator_version
                    == requirement.validator_version,
                    ProjectionValidationRecord.ruleset_id == requirement.ruleset_id,
                    ProjectionValidationRecord.ruleset_digest == requirement.ruleset_digest,
                    ProjectionValidationRecord.outcome
                    == ProjectionValidationOutcome.VALIDATED.value,
                )
            ).all()
        )
        if not validation_ids:
            return False

        required_codes = {code.strip() for code in requirement.required_check_codes}
        if "" in required_codes or len(required_codes) != len(
            requirement.required_check_codes
        ):
            return False
        if not required_codes:
            return True

        observed_by_validation = {validation_id: set() for validation_id in validation_ids}
        for validation_id, check_code in self.session.execute(
            select(
                ProjectionValidationCheckRecord.validation_id,
                ProjectionValidationCheckRecord.check_code,
            ).where(ProjectionValidationCheckRecord.validation_id.in_(validation_ids))
        ):
            observed_by_validation[validation_id].add(check_code)
        return any(
            required_codes.issubset(observed_codes)
            for observed_codes in observed_by_validation.values()
        )

    def validate_projection_attempt(
        self,
        *,
        validation_id: UUID,
        attempt_id: UUID,
        validator: ProjectionValidator,
        config_digest: str | None = None,
    ) -> ProjectionValidationSnapshot:
        attempt = self.read_projection_attempt(attempt_id)
        if attempt.disposition is ProjectionDisposition.PENDING:
            raise ProjectionValidationStateError(
                "projection attempt must be settled before validation"
            )
        if attempt.disposition in (
            ProjectionDisposition.FAILED,
            ProjectionDisposition.QUARANTINED,
        ):
            raise ProjectionValidationStateError(
                f"projection attempt with disposition {attempt.disposition.value} is not eligible for validation"
            )

        descriptor = _normalize_descriptor(validator.descriptor)
        request_digest = _request_digest(
            {
                "attempt_id": str(attempt_id).lower(),
                "attempt_request_digest": attempt.request_digest,
                "config_digest": config_digest,
                "ruleset_digest": descriptor.ruleset_digest,
                "ruleset_id": descriptor.ruleset_id,
                "validator_identity": descriptor.validator_identity,
                "validator_version": descriptor.validator_version,
            }
        )

        record = self.session.get(ProjectionValidationRecord, validation_id)
        if record is not None:
            if record.request_digest != request_digest:
                raise ProjectionValidationReuseError(
                    f"projection validation {validation_id} was reused with different inputs"
                )
            if ProjectionValidationOutcome(record.outcome) is not ProjectionValidationOutcome.PENDING:
                return self.read_projection_validation(validation_id)
        else:
            if attempt.validation_state in (
                ProjectionValidationState.VALIDATED,
                ProjectionValidationState.INCOMPLETE,
                ProjectionValidationState.REJECTED,
            ):
                raise ProjectionValidationStateError(
                    f"projection attempt {attempt_id} already has terminal validation state "
                    f"{attempt.validation_state.value}"
                )
            record = ProjectionValidationRecord(
                validation_id=validation_id,
                attempt_id=attempt_id,
                attempt_request_digest=attempt.request_digest,
                request_digest=request_digest,
                validator_identity=descriptor.validator_identity,
                validator_version=descriptor.validator_version,
                ruleset_id=descriptor.ruleset_id,
                ruleset_digest=descriptor.ruleset_digest,
                config_digest=config_digest,
                outcome=ProjectionValidationOutcome.PENDING.value,
                started_at=self._now(),
                settled_at=None,
                error_code=None,
                error_detail=None,
            )
            self.session.add(record)
            self.session.commit()

        attempt_row = self.session.get(ProjectionAttempt, attempt_id)
        if attempt_row is None:
            raise KnowledgeInvariantError(f"unknown projection attempt: {attempt_id}")

        try:
            report = validator.validate(attempt)
            outcome, normalized_checks = _normalize_report(
                report,
                projection_disposition=attempt.disposition,
            )
        except Exception as exc:
            record.outcome = ProjectionValidationOutcome.QUARANTINED.value
            record.settled_at = self._now()
            record.error_code = type(exc).__name__
            record.error_detail = str(exc)
            attempt_row.validation_state = ProjectionValidationState.QUARANTINED.value
            self.session.commit()
            return self.read_projection_validation(validation_id)

        for ordinal, (check, evidence, evidence_digest) in enumerate(normalized_checks):
            self.session.add(
                ProjectionValidationCheckRecord(
                    validation_id=validation_id,
                    ordinal=ordinal,
                    check_code=check.check_code,
                    outcome=check.outcome.value,
                    evidence_digest=evidence_digest,
                    evidence_json=evidence,
                    detail=check.detail,
                )
            )

        record.outcome = outcome.value
        record.settled_at = self._now()
        record.error_code = None
        record.error_detail = None
        attempt_row.validation_state = ProjectionValidationState(outcome.value).value
        self.session.commit()
        return self.read_projection_validation(validation_id)
