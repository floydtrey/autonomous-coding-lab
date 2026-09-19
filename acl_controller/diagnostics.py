"""Controller diagnostic helpers built on ACL Core diagnostics."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from acl_core import Correlation, current_correlation, pop_correlation, push_correlation
from acl_core.diagnostics import emit, span


def controller_emit(level: str, operation_name: str, event: str, **details: Any) -> None:
    emit(level, "controller", operation_name, event, **details)


@contextmanager
def controller_span(
    operation_name: str,
    *,
    workflow_id: str | None = None,
    request_id: str | None = None,
    task_id: str | None = None,
    attempt_id: str | None = None,
    grant_id: str | None = None,
    **details: Any,
) -> Iterator[None]:
    current = current_correlation()
    correlation = Correlation(
        request_id=request_id if request_id is not None else current.request_id,
        run_id=workflow_id if workflow_id is not None else current.run_id,
        task_id=task_id if task_id is not None else current.task_id,
        attempt_id=attempt_id if attempt_id is not None else current.attempt_id,
        grant_id=grant_id if grant_id is not None else current.grant_id,
    )
    token = push_correlation(correlation)
    try:
        with span("controller", operation_name, **details):
            yield
    finally:
        pop_correlation(token)
