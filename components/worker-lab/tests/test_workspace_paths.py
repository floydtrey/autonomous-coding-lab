from pathlib import Path

import worker_lab.workspace as workspace_module


def test_windows_extended_path_formats_drive_unc_and_existing_prefixes() -> None:
    assert workspace_module._windows_extended_path(
        r"C:\worker\workspace"
    ) == r"\\?\C:\worker\workspace"
    assert workspace_module._windows_extended_path(
        r"\\server\share\workspace"
    ) == r"\\?\UNC\server\share\workspace"
    assert workspace_module._windows_extended_path(
        r"\\?\C:\worker\workspace"
    ) == r"\\?\C:\worker\workspace"


def test_remove_tree_uses_same_native_path_for_safety_and_deletion(monkeypatch) -> None:
    requested = Path("requested")
    removal = Path("native-removal")
    calls: list[tuple[str, Path, object | None]] = []

    monkeypatch.setattr(workspace_module, "_removal_path", lambda path: removal)
    monkeypatch.setattr(
        workspace_module,
        "_assert_no_reparse_tree",
        lambda path: calls.append(("validate", path, None)),
    )

    def record_rmtree(path: Path, *, onexc: object) -> None:
        calls.append(("remove", path, onexc))

    monkeypatch.setattr(workspace_module.shutil, "rmtree", record_rmtree)

    workspace_module._remove_tree(requested)

    assert calls == [
        ("validate", removal, None),
        ("remove", removal, workspace_module._remove_readonly),
    ]
