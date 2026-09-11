from __future__ import annotations

from worker_lab import workspace as workspace_module


def test_remove_readonly_accepts_entry_missing_before_callback(monkeypatch) -> None:
    def unexpected_chmod(path: str, mode: int) -> None:
        raise AssertionError("chmod must not run for an entry that is already absent")

    def unexpected_retry(path: str) -> None:
        raise AssertionError("deletion must not retry for an entry that is already absent")

    monkeypatch.setattr(workspace_module.os, "chmod", unexpected_chmod)

    workspace_module._remove_readonly(
        unexpected_retry,
        "already-removed",
        FileNotFoundError("already removed"),
    )


def test_remove_readonly_accepts_entry_removed_before_retry(monkeypatch) -> None:
    chmod_calls: list[tuple[str, int]] = []

    def record_chmod(path: str, mode: int) -> None:
        chmod_calls.append((path, mode))

    def missing_on_retry(path: str) -> None:
        raise FileNotFoundError("removed after chmod")

    monkeypatch.setattr(workspace_module.os, "chmod", record_chmod)

    workspace_module._remove_readonly(
        missing_on_retry,
        "removed-during-retry",
        PermissionError("read-only"),
    )

    assert chmod_calls == [("removed-during-retry", workspace_module.stat.S_IWRITE)]


def test_remove_readonly_preserves_original_error_on_genuine_retry_failure(monkeypatch) -> None:
    original_error = PermissionError("read-only")

    monkeypatch.setattr(workspace_module.os, "chmod", lambda path, mode: None)

    def fail_retry(path: str) -> None:
        raise OSError("still unavailable")

    try:
        workspace_module._remove_readonly(fail_retry, "still-present", original_error)
    except PermissionError as exc:
        assert exc is original_error
    else:
        raise AssertionError("the original deletion error must be preserved")
