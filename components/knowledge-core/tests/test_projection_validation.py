from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from knowledge_core.application.projection_validation import ProjectionValidationKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.projection_evidence import (
    ProjectionDisposition,
    ProjectionValidationState,
)
from knowledge_core.domain.projection_validation import (
    ProjectionCheckOutcome,
    ProjectionValidationCheck,
    ProjectionValidationOutcome,
    ProjectionValidationReport,
    ProjectionValidationReuseError,
    ProjectionValidationStateError,
    ProjectionValidatorDescriptor,
)
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)
from knowledge_core.storage.projection_validation_models import ProjectionValidationRecord


class FakeValidator:
    def __init__(
        self,
        report: ProjectionValidationReport | None,
        *,
        descriptor: ProjectionValidatorDescriptor | None = None,
        error: Exception | None = None,
    ):
        self._report = report
        self._descriptor = descriptor or ProjectionValidatorDescriptor(
            validator_identity="deterministic-projection-validator",
            validator_version="1",
            ruleset_id="projection-integrity-v1",
            ruleset_digest="sha256:rules-a",
        )
        self.error = error
        self.calls = 0

    @property
    def descriptor(self) -> ProjectionValidatorDescriptor:
        return self._descriptor

    def validate(self, _attempt):
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert self._report is not None
        return self._report


def _kernel(tmp_path):
    engine = create_database_engine(
        f"sqlite+pysqlite:///{tmp_path / 'projection-validation.db'}",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    sessions = create_session_factory(engine)
    store = LocalArtifactStore(tmp_path / "artifacts")
    return engine, sessions, store


def _settled_attempt(kernel, *, disposition=ProjectionDisposition.SUCCEEDED):
    refs = kernel.bootstrap_core_test_profile()
    entity = kernel.create_entity(refs.person_kind_revision_ref)
    highwater = kernel.current_revision()
    attempt = kernel.start_projection_attempt(
        attempt_id=uuid4(),
        projection_kind="relationship_graph",
        target_kind="knowledge_relationship_projection",
        namespace_key="acl:project-alpha",
        scope_key="project:alpha",
        backend_identity="graph-adapter",
        backend_version="1",
        profile_id="graph-projection-v1",
        profile_digest="sha256:profile-a",
        config_digest="cfg-a",
        sources=((entity, highwater),),
    )
    settled = kernel.settle_projection_attempt(
        attempt_id=attempt.attempt_id,
        disposition=disposition,
    )
    return settled, highwater


def _check(code, outcome, **evidence):
    return ProjectionValidationCheck(
        check_code=code,
        outcome=outcome,
        evidence=evidence,
    )


def test_validated_projection_requires_all_checks_and_preserves_canonical_revision(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = ProjectionValidationKnowledgeKernel(session, artifact_store=store)
            attempt, canonical_revision = _settled_attempt(kernel)
            validator = FakeValidator(
                ProjectionValidationReport(
                    outcome=ProjectionValidationOutcome.VALIDATED,
                    checks=(
                        _check("source-correlation", ProjectionCheckOutcome.PASSED, matched=1),
                        _check("namespace-isolation", ProjectionCheckOutcome.PASSED, leaks=0),
                    ),
                )
            )

            validation = kernel.validate_projection_attempt(
                validation_id=uuid4(),
                attempt_id=attempt.attempt_id,
                validator=validator,
                config_digest="sha256:validator-config-a",
            )
            refreshed = kernel.read_projection_attempt(attempt.attempt_id)

            assert validation.outcome is ProjectionValidationOutcome.VALIDATED
            assert refreshed.validation_state is ProjectionValidationState.VALIDATED
            assert len(validation.checks) == 2
            assert validation.checks[0].evidence_digest
            assert validation.checks[0].evidence == {"matched": 1}
            assert kernel.current_revision() == canonical_revision

            with pytest.raises(ProjectionValidationStateError):
                kernel.validate_projection_attempt(
                    validation_id=uuid4(),
                    attempt_id=attempt.attempt_id,
                    validator=validator,
                )
            assert validator.calls == 1
    finally:
        engine.dispose()


def test_validation_replay_is_idempotent_and_does_not_rerun_validator(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = ProjectionValidationKnowledgeKernel(session, artifact_store=store)
            attempt, _ = _settled_attempt(kernel)
            validation_id = uuid4()
            validator = FakeValidator(
                ProjectionValidationReport(
                    outcome=ProjectionValidationOutcome.VALIDATED,
                    checks=(_check("complete", ProjectionCheckOutcome.PASSED, count=1),),
                )
            )

            first = kernel.validate_projection_attempt(
                validation_id=validation_id,
                attempt_id=attempt.attempt_id,
                validator=validator,
            )
            replay = kernel.validate_projection_attempt(
                validation_id=validation_id,
                attempt_id=attempt.attempt_id,
                validator=validator,
            )

            assert replay == first
            assert validator.calls == 1
            assert session.scalar(select(func.count()).select_from(ProjectionValidationRecord)) == 1
    finally:
        engine.dispose()


def test_validation_identity_rejects_changed_ruleset_or_config(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = ProjectionValidationKnowledgeKernel(session, artifact_store=store)
            attempt, _ = _settled_attempt(kernel)
            validation_id = uuid4()
            report = ProjectionValidationReport(
                outcome=ProjectionValidationOutcome.VALIDATED,
                checks=(_check("complete", ProjectionCheckOutcome.PASSED, count=1),),
            )
            validator = FakeValidator(report)

            kernel.validate_projection_attempt(
                validation_id=validation_id,
                attempt_id=attempt.attempt_id,
                validator=validator,
                config_digest="cfg-a",
            )
            changed = FakeValidator(
                report,
                descriptor=replace(
                    validator.descriptor,
                    ruleset_digest="sha256:rules-b",
                ),
            )

            with pytest.raises(ProjectionValidationReuseError):
                kernel.validate_projection_attempt(
                    validation_id=validation_id,
                    attempt_id=attempt.attempt_id,
                    validator=changed,
                    config_digest="cfg-a",
                )
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("outcome", "expected_state"),
    (
        (ProjectionValidationOutcome.INCOMPLETE, ProjectionValidationState.INCOMPLETE),
        (ProjectionValidationOutcome.REJECTED, ProjectionValidationState.REJECTED),
    ),
)
def test_failed_checks_produce_durable_nontrusted_validation_states(
    tmp_path,
    outcome,
    expected_state,
):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = ProjectionValidationKnowledgeKernel(session, artifact_store=store)
            attempt, _ = _settled_attempt(kernel)
            validator = FakeValidator(
                ProjectionValidationReport(
                    outcome=outcome,
                    checks=(
                        _check(
                            "relationship-endpoints",
                            ProjectionCheckOutcome.FAILED,
                            expected=2,
                            observed=1,
                        ),
                    ),
                )
            )

            validation = kernel.validate_projection_attempt(
                validation_id=uuid4(),
                attempt_id=attempt.attempt_id,
                validator=validator,
            )

            assert validation.outcome is outcome
            assert kernel.read_projection_attempt(attempt.attempt_id).validation_state is expected_state
    finally:
        engine.dispose()


def test_validator_exception_is_durable_quarantine_and_can_be_retried_with_new_identity(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = ProjectionValidationKnowledgeKernel(session, artifact_store=store)
            attempt, _ = _settled_attempt(kernel)

            quarantined = kernel.validate_projection_attempt(
                validation_id=uuid4(),
                attempt_id=attempt.attempt_id,
                validator=FakeValidator(None, error=RuntimeError("inspection unavailable")),
            )
            assert quarantined.outcome is ProjectionValidationOutcome.QUARANTINED
            assert quarantined.error_code == "RuntimeError"
            assert kernel.read_projection_attempt(attempt.attempt_id).validation_state is ProjectionValidationState.QUARANTINED

            recovered = kernel.validate_projection_attempt(
                validation_id=uuid4(),
                attempt_id=attempt.attempt_id,
                validator=FakeValidator(
                    ProjectionValidationReport(
                        outcome=ProjectionValidationOutcome.VALIDATED,
                        checks=(_check("complete", ProjectionCheckOutcome.PASSED, count=1),),
                    )
                ),
            )
            assert recovered.outcome is ProjectionValidationOutcome.VALIDATED
            assert kernel.read_projection_attempt(attempt.attempt_id).validation_state is ProjectionValidationState.VALIDATED
    finally:
        engine.dispose()


def test_validator_cannot_promote_incomplete_projection_or_malformed_report_to_trusted(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = ProjectionValidationKnowledgeKernel(session, artifact_store=store)
            attempt, _ = _settled_attempt(
                kernel,
                disposition=ProjectionDisposition.INCOMPLETE,
            )
            invalid = FakeValidator(
                ProjectionValidationReport(
                    outcome=ProjectionValidationOutcome.VALIDATED,
                    checks=(_check("complete", ProjectionCheckOutcome.PASSED, count=1),),
                )
            )

            validation = kernel.validate_projection_attempt(
                validation_id=uuid4(),
                attempt_id=attempt.attempt_id,
                validator=invalid,
            )

            assert validation.outcome is ProjectionValidationOutcome.QUARANTINED
            assert validation.error_code == "ProjectionValidationStateError"
            assert kernel.read_projection_attempt(attempt.attempt_id).validation_state is ProjectionValidationState.QUARANTINED
    finally:
        engine.dispose()


def test_failed_or_pending_projection_attempts_are_not_validation_candidates(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = ProjectionValidationKnowledgeKernel(session, artifact_store=store)
            attempt, _ = _settled_attempt(kernel, disposition=ProjectionDisposition.FAILED)
            validator = FakeValidator(
                ProjectionValidationReport(
                    outcome=ProjectionValidationOutcome.VALIDATED,
                    checks=(_check("complete", ProjectionCheckOutcome.PASSED, count=1),),
                )
            )

            with pytest.raises(ProjectionValidationStateError):
                kernel.validate_projection_attempt(
                    validation_id=uuid4(),
                    attempt_id=attempt.attempt_id,
                    validator=validator,
                )
            assert validator.calls == 0
    finally:
        engine.dispose()
