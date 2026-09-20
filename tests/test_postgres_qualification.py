from __future__ import annotations

import os
from queue import Queue
from threading import Barrier, Event, Thread
import time
from types import MethodType
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import Engine

from knowledge_core.application.generations import (
    GenerationKnowledgeKernel,
    _POSTGRES_DERIVED_GENERATION_LOCK,
)
from knowledge_core.application.operations import (
    OperationKnowledgeKernel,
    _POSTGRES_CANONICAL_WRITE_LOCK,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import TypedValue
from knowledge_core.domain.generations import DerivedKind, GenerationFenceError, GenerationStatus
from knowledge_core.domain.operations import StaleWriteError
from knowledge_core.storage.control_models import Operation
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.generation_models import DerivedGeneration
from knowledge_core.storage.models import Assertion, AssertionTransition, Revision


pytestmark = pytest.mark.postgresql

_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)


def _require_postgres_engine() -> Engine:
    if not _POSTGRES_URL:
        pytest.skip("PostgreSQL qualification URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("PostgreSQL qualification requires a PostgreSQL URL")
    return engine


def _truncate_kernel_tables(engine: Engine) -> None:
    inspector = inspect(engine)
    preparer = engine.dialect.identifier_preparer
    tables: list[str] = []
    for schema in ("kc", "kc_control", "kc_derived"):
        for table_name in inspector.get_table_names(schema=schema):
            tables.append(
                f"{preparer.quote_schema(schema)}.{preparer.quote(table_name)}"
            )
    if not tables:
        raise AssertionError("Knowledge Core schemas are not migrated")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "TRUNCATE TABLE " + ", ".join(tables) + " RESTART IDENTITY CASCADE"
        )


def _wait_for_advisory_waiter(engine: Engine, pid: int, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with engine.connect() as connection:
            waiting = connection.scalar(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM pg_locks
                        WHERE pid = :pid
                          AND locktype = 'advisory'
                          AND granted = false
                    )
                    """
                ),
                {"pid": pid},
            )
        if waiting:
            return True
        time.sleep(0.05)
    return False


@pytest.fixture()
def postgres_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def test_postgres_two_writers_from_same_revision_yield_one_stale_writer(postgres_engine):
    sessions = create_session_factory(postgres_engine)
    with sessions() as session:
        kernel = OperationKnowledgeKernel(session)
        refs = kernel.bootstrap_core_test_profile()
        person = kernel.create_entity(refs.person_kind_revision_ref)
        org_a = kernel.create_entity(refs.organization_kind_revision_ref)
        org_b = kernel.create_entity(refs.organization_kind_revision_ref)
        org_c = kernel.create_entity(refs.organization_kind_revision_ref)
        original = kernel.append_assertion(
            subject_ref=person,
            predicate_revision_ref=refs.works_for_predicate_revision_ref,
            profile_revision_ref=refs.profile_revision_ref,
            value=TypedValue.reference(org_a),
        )
        shared_revision = kernel.current_revision()

    barrier = Barrier(3)
    results: Queue[tuple[str, UUID, int | None]] = Queue()

    def writer(replacement: UUID) -> None:
        operation_id = uuid4()
        with sessions() as session:
            kernel = OperationKnowledgeKernel(session)
            barrier.wait()
            try:
                kernel.correct_assertion_operation(
                    operation_id=operation_id,
                    expected_revision=shared_revision,
                    source_assertion_ref=original,
                    replacement_value=TypedValue.reference(replacement),
                    correction_kind_revision_ref=refs.correction_kind_revision_ref,
                )
                results.put(("committed", operation_id, None))
            except StaleWriteError as exc:
                results.put(("stale", operation_id, exc.actual_revision))

    threads = [Thread(target=writer, args=(org_b,)), Thread(target=writer, args=(org_c,))]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=10)
        assert not thread.is_alive()

    outcomes = [results.get_nowait(), results.get_nowait()]
    assert sorted(outcome[0] for outcome in outcomes) == ["committed", "stale"]

    with sessions() as session:
        committed = session.scalar(
            select(func.count()).select_from(Operation).where(Operation.status == "committed")
        )
        conflicts = session.scalar(
            select(func.count()).select_from(Operation).where(Operation.status == "conflict")
        )
        transitions = session.scalar(select(func.count()).select_from(AssertionTransition))
        assert committed == 1
        assert conflicts == 1
        assert transitions == 1


def test_postgres_same_operation_id_race_replays_one_canonical_result(postgres_engine):
    sessions = create_session_factory(postgres_engine)
    with sessions() as session:
        kernel = OperationKnowledgeKernel(session)
        refs = kernel.bootstrap_core_test_profile()
        person = kernel.create_entity(refs.person_kind_revision_ref)
        expected_revision = kernel.current_revision()

    operation_id = uuid4()
    barrier = Barrier(3)
    results: Queue[UUID] = Queue()
    errors: Queue[BaseException] = Queue()

    def writer() -> None:
        with sessions() as session:
            kernel = OperationKnowledgeKernel(session)
            barrier.wait()
            try:
                result = kernel.append_assertion_operation(
                    operation_id=operation_id,
                    expected_revision=expected_revision,
                    subject_ref=person,
                    predicate_revision_ref=refs.has_name_predicate_revision_ref,
                    profile_revision_ref=refs.profile_revision_ref,
                    value=TypedValue.text("same operation race"),
                )
                results.put(result)
            except BaseException as exc:  # surfaced in the parent thread
                errors.put(exc)

    threads = [Thread(target=writer), Thread(target=writer)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=10)
        assert not thread.is_alive()

    assert errors.empty(), list(errors.queue)
    first = results.get_nowait()
    second = results.get_nowait()
    assert first == second

    with sessions() as session:
        assert session.scalar(
            select(func.count()).select_from(Operation).where(Operation.operation_id == operation_id)
        ) == 1
        assert session.scalar(
            select(func.count()).select_from(Revision).where(Revision.operation_id == operation_id)
        ) == 1
        assert session.scalar(
            select(func.count()).select_from(Assertion).where(Assertion.ref_id == first)
        ) == 1


def test_postgres_managed_write_waits_on_canonical_advisory_lock(postgres_engine):
    sessions = create_session_factory(postgres_engine)
    with sessions() as session:
        kernel = OperationKnowledgeKernel(session)
        refs = kernel.bootstrap_core_test_profile()
        person = kernel.create_entity(refs.person_kind_revision_ref)
        expected_revision = kernel.current_revision()

    worker_pid: Queue[int] = Queue()
    result: Queue[UUID] = Queue()
    errors: Queue[BaseException] = Queue()

    blocker = sessions()
    blocker.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _POSTGRES_CANONICAL_WRITE_LOCK},
    )

    def writer() -> None:
        with sessions() as session:
            worker_pid.put(int(session.scalar(text("SELECT pg_backend_pid()"))))
            kernel = OperationKnowledgeKernel(session)
            try:
                result.put(
                    kernel.append_assertion_operation(
                        operation_id=uuid4(),
                        expected_revision=expected_revision,
                        subject_ref=person,
                        predicate_revision_ref=refs.has_name_predicate_revision_ref,
                        profile_revision_ref=refs.profile_revision_ref,
                        value=TypedValue.text("lock waiter"),
                    )
                )
            except BaseException as exc:  # surfaced in the parent thread
                errors.put(exc)

    thread = Thread(target=writer)
    thread.start()
    pid = worker_pid.get(timeout=5)
    try:
        assert _wait_for_advisory_waiter(postgres_engine, pid)
    finally:
        blocker.commit()
        blocker.close()

    thread.join(timeout=10)
    assert not thread.is_alive()
    assert errors.empty(), list(errors.queue)
    assert isinstance(result.get_nowait(), UUID)


def test_postgres_new_generation_wins_while_older_finisher_is_fenced(postgres_engine, tmp_path):
    sessions = create_session_factory(postgres_engine)
    store = LocalArtifactStore(tmp_path / "artifacts")

    with sessions() as session:
        kernel = GenerationKnowledgeKernel(session, artifact_store=store)
        refs = kernel.bootstrap_core_test_profile()
        highwater = kernel.current_revision()
        old = kernel.start_generation(
            derived_kind=DerivedKind.IDENTITY,
            source_revision_highwater=highwater,
            profile_revision_ref=refs.profile_revision_ref,
        )
        new = kernel.start_generation(
            derived_kind=DerivedKind.IDENTITY,
            source_revision_highwater=highwater,
            profile_revision_ref=refs.profile_revision_ref,
        )

    new_has_lock = Event()
    allow_new_to_settle = Event()
    old_pid: Queue[int] = Queue()
    new_results: Queue[GenerationStatus] = Queue()
    old_results: Queue[str] = Queue()
    errors: Queue[BaseException] = Queue()

    def newer_finisher() -> None:
        with sessions() as session:
            session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": _POSTGRES_DERIVED_GENERATION_LOCK},
            )
            new_has_lock.set()
            if not allow_new_to_settle.wait(timeout=10):
                errors.put(RuntimeError("timed out waiting to settle newer generation"))
                session.rollback()
                return
            kernel = GenerationKnowledgeKernel(session, artifact_store=store)
            try:
                new_results.put(kernel.settle_generation(generation_id=new.generation_id).status)
            except BaseException as exc:
                errors.put(exc)

    def older_finisher() -> None:
        if not new_has_lock.wait(timeout=10):
            errors.put(RuntimeError("newer generation never acquired the generation lock"))
            return
        with sessions() as session:
            old_pid.put(int(session.scalar(text("SELECT pg_backend_pid()"))))
            kernel = GenerationKnowledgeKernel(session, artifact_store=store)
            try:
                kernel.settle_generation(generation_id=old.generation_id)
                old_results.put("unexpected-current")
            except GenerationFenceError:
                old_results.put("fenced")
            except BaseException as exc:
                errors.put(exc)

    newer = Thread(target=newer_finisher)
    older = Thread(target=older_finisher)
    newer.start()
    assert new_has_lock.wait(timeout=5)
    older.start()
    pid = old_pid.get(timeout=5)
    assert _wait_for_advisory_waiter(postgres_engine, pid)
    allow_new_to_settle.set()

    newer.join(timeout=10)
    older.join(timeout=10)
    assert not newer.is_alive()
    assert not older.is_alive()
    assert errors.empty(), list(errors.queue)
    assert new_results.get_nowait() is GenerationStatus.CURRENT
    assert old_results.get_nowait() == "fenced"

    with sessions() as session:
        kernel = GenerationKnowledgeKernel(session, artifact_store=store)
        current = kernel.current_generation(derived_kind=DerivedKind.IDENTITY)
        assert current is not None
        assert current.generation_id == new.generation_id
        assert kernel.read_generation(old.generation_id).status is GenerationStatus.STALE
        assert session.scalar(
            select(func.count())
            .select_from(DerivedGeneration)
            .where(
                DerivedGeneration.derived_kind == DerivedKind.IDENTITY.value,
                DerivedGeneration.status == GenerationStatus.CURRENT.value,
            )
        ) == 1


def test_postgres_failed_managed_write_rolls_back_partial_canonical_state(postgres_engine):
    sessions = create_session_factory(postgres_engine)
    with sessions() as session:
        kernel = OperationKnowledgeKernel(session)
        refs = kernel.bootstrap_core_test_profile()
        person = kernel.create_entity(refs.person_kind_revision_ref)
        expected_revision = kernel.current_revision()
        revision_count = session.scalar(select(func.count()).select_from(Revision))
        assertion_count = session.scalar(select(func.count()).select_from(Assertion))
        operation_count = session.scalar(select(func.count()).select_from(Operation))

        original_append_rows = kernel._append_assertion_rows

        def fail_after_assertion_rows(_self, *args, **kwargs):
            original_append_rows(*args, **kwargs)
            session.flush()
            raise RuntimeError("forced rollback after canonical rows were flushed")

        kernel._append_assertion_rows = MethodType(fail_after_assertion_rows, kernel)
        operation_id = uuid4()

        with pytest.raises(RuntimeError, match="forced rollback"):
            kernel.append_assertion_operation(
                operation_id=operation_id,
                expected_revision=expected_revision,
                subject_ref=person,
                predicate_revision_ref=refs.has_name_predicate_revision_ref,
                profile_revision_ref=refs.profile_revision_ref,
                value=TypedValue.text("must roll back"),
            )

        assert kernel.current_revision() == expected_revision
        assert session.scalar(select(func.count()).select_from(Revision)) == revision_count
        assert session.scalar(select(func.count()).select_from(Assertion)) == assertion_count
        assert session.scalar(select(func.count()).select_from(Operation)) == operation_count
        assert session.get(Operation, operation_id) is None
