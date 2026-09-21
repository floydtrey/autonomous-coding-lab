"""Filesystem tool paging tests."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from acl_controller.authority import FilesystemAuthorityCoordinator
from acl_controller.tools.filesystem import FilesystemToolService
from acl_core import AuthorityEnvelope, AuthorityGrant, ToolCall


def _service(root: Path) -> FilesystemToolService:
    config = root / "config"
    config.mkdir(parents=True, exist_ok=True)
    (config / "filesystem_authority.json").write_text(
        json.dumps(
            {
                "schema_version": "acl-filesystem-authority:v1",
                "protected_paths": [],
            }
        ),
        encoding="utf-8",
    )
    coordinator = FilesystemAuthorityCoordinator.create(
        project_root=root,
        state_root=root / ".acl-state",
        config_root=config,
    )
    return FilesystemToolService(coordinator)


def _read_grant() -> AuthorityGrant:
    return AuthorityGrant(
        grant_id="grant:test-read-page",
        issuer="test",
        subject="planner",
        authority=AuthorityEnvelope(
            capabilities=("filesystem.read",),
            resource_scopes=("filesystem:READ:*",),
            tool_scopes=("filesystem.read_text",),
        ),
    )


def test_read_text_pages_large_file_by_line():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        target = root / "large.py"
        target.write_text(
            "".join(f"line-{index:03d}\n" for index in range(1, 301)),
            encoding="utf-8",
        )
        service = _service(root)

        first = service._read_text(
            ToolCall(
                tool_id="filesystem.read_text",
                arguments={
                    "path": str(target),
                    "start_line": 1,
                    "max_lines": 40,
                    "max_chars": 10000,
                },
            ),
            _read_grant(),
        )

        assert first["start_line"] == 1
        assert first["end_line"] == 40
        assert first["next_start_line"] == 41
        assert first["line_count"] == 300
        assert first["content"].startswith("line-001")
        assert "line-040" in first["content"]
        assert "line-041" not in first["content"]

        second = service._read_text(
            ToolCall(
                tool_id="filesystem.read_text",
                arguments={
                    "path": str(target),
                    "start_line": first["next_start_line"],
                    "max_lines": 40,
                    "max_chars": 10000,
                },
            ),
            _read_grant(),
        )

        assert second["start_line"] == 41
        assert second["content"].startswith("line-041")
        assert "line-080" in second["content"]


def test_read_text_default_page_is_bounded_and_reports_continuation():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        target = root / "large.txt"
        target.write_text(
            "".join(f"{index:04d}-" + ("x" * 100) + "\n" for index in range(1, 401)),
            encoding="utf-8",
        )
        service = _service(root)

        observed = service._read_text(
            ToolCall(
                tool_id="filesystem.read_text",
                arguments={"path": str(target)},
            ),
            _read_grant(),
        )

        assert observed["returned_characters"] <= 8000
        assert observed["start_line"] == 1
        assert observed["next_start_line"] is not None
        assert observed["truncated"] is True
