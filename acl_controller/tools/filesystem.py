"""Shared ACL filesystem tools.

These tools are role-neutral. Worker is the first mutating consumer, but any role
with the same tool profile + authority grant can use them. Every operation checks
both the persistent filesystem protection policy and the Pass-scoped resource
grant before touching disk.
"""
from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any, Mapping

from acl_core import AuthorityGrant, FilesystemOperation, ToolCall, ToolDefinition, ToolRegistry
from acl_core.errors import CoreError

from ..authority.filesystem import FilesystemAuthorityCoordinator


FS_READ_TEXT = "filesystem.read_text"
FS_LIST_DIRECTORY = "filesystem.list_directory"
FS_SEARCH = "filesystem.search"
FS_WRITE_TEXT = "filesystem.write_text"
FS_CREATE_TEXT = "filesystem.create_text"
FS_DELETE_PATH = "filesystem.delete_path"
FS_MOVE_PATH = "filesystem.move_path"

FILESYSTEM_TOOL_IDS = (
    FS_CREATE_TEXT,
    FS_DELETE_PATH,
    FS_LIST_DIRECTORY,
    FS_SEARCH,
    FS_MOVE_PATH,
    FS_READ_TEXT,
    FS_WRITE_TEXT,
)


def filesystem_scope(operation: FilesystemOperation | str, path: str) -> str:
    operation = FilesystemOperation(operation)
    return f"filesystem:{operation.value}:{path}"


def parse_filesystem_scope(value: str) -> tuple[FilesystemOperation, str] | None:
    if not isinstance(value, str) or not value.startswith("filesystem:"):
        return None
    parts = value.split(":", 2)
    if len(parts) != 3:
        return None
    try:
        operation = FilesystemOperation(parts[1])
    except ValueError:
        return None
    return operation, parts[2]


class FilesystemToolService:
    """Register and execute the shared bounded filesystem tool set."""

    def __init__(self, authority: FilesystemAuthorityCoordinator) -> None:
        self.authority = authority

    def register(self, registry: ToolRegistry) -> tuple[str, ...]:
        definitions = (
            ToolDefinition(
                FS_READ_TEXT,
                "Read UTF-8 text from one authorized file.",
                ("filesystem.read",),
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "max_chars": {"type": "integer", "minimum": 1, "maximum": 1000000},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            ),
            ToolDefinition(
                FS_LIST_DIRECTORY,
                "List entries in one authorized directory.",
                ("filesystem.read",),
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "max_entries": {"type": "integer", "minimum": 1, "maximum": 5000},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            ),
            ToolDefinition(
                FS_SEARCH,
                "Search authorized UTF-8 text files recursively by filename/path or text content.",
                ("filesystem.read",),
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "query": {"type": "string"},
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 200},
                        "max_files": {"type": "integer", "minimum": 1, "maximum": 10000}
                    },
                    "required": ["path", "query"],
                    "additionalProperties": False
                },
            ),
            ToolDefinition(
                FS_WRITE_TEXT,
                "Replace UTF-8 text in an existing authorized file.",
                ("filesystem.write",),
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
                repeat_policy="suppress_identical_success",
            ),
            ToolDefinition(
                FS_CREATE_TEXT,
                "Create one new UTF-8 text file at an authorized path.",
                ("filesystem.create",),
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
                repeat_policy="suppress_identical_success",
            ),
            ToolDefinition(
                FS_DELETE_PATH,
                "Delete one authorized regular file.",
                ("filesystem.delete",),
                {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                    "additionalProperties": False,
                },
                repeat_policy="suppress_identical_success",
            ),
            ToolDefinition(
                FS_MOVE_PATH,
                "Move or rename one authorized file to another authorized path.",
                ("filesystem.move",),
                {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "destination": {"type": "string"},
                    },
                    "required": ["source", "destination"],
                    "additionalProperties": False,
                },
                repeat_policy="suppress_identical_success",
            ),
        )
        handlers = {
            FS_READ_TEXT: self._read_text,
            FS_LIST_DIRECTORY: self._list_directory,
            FS_SEARCH: self._search,
            FS_WRITE_TEXT: self._write_text,
            FS_CREATE_TEXT: self._create_text,
            FS_DELETE_PATH: self._delete_path,
            FS_MOVE_PATH: self._move_path,
        }
        for definition in definitions:
            registry.register(definition, handlers[definition.tool_id])
        return tuple(item.tool_id for item in definitions)

    def _read_text(self, call: ToolCall, grant: AuthorityGrant) -> Mapping[str, Any]:
        path = self._path_arg(call, "path")
        canonical = self._require_scope(grant, FilesystemOperation.READ, path)
        target = Path(canonical)
        if not target.is_file():
            raise CoreError("TOOL_FILE_MISSING", "read target is not a regular file", {"path": canonical})
        max_chars = call.arguments.get("max_chars", 200000)
        if isinstance(max_chars, bool) or not isinstance(max_chars, int) or not 1 <= max_chars <= 1000000:
            raise CoreError("TOOL_ARGUMENTS_INVALID", "max_chars is invalid")
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise CoreError("TOOL_FILE_READ_FAILED", "file could not be read as UTF-8", {"path": canonical}) from exc
        truncated = len(text) > max_chars
        return {
            "path": canonical,
            "content": text[:max_chars],
            "characters": len(text),
            "truncated": truncated,
        }

    def _list_directory(self, call: ToolCall, grant: AuthorityGrant) -> Mapping[str, Any]:
        path = self._path_arg(call, "path")
        canonical = self._require_scope(grant, FilesystemOperation.READ, path)
        target = Path(canonical)
        if not target.is_dir():
            raise CoreError("TOOL_DIRECTORY_MISSING", "list target is not a directory", {"path": canonical})
        maximum = call.arguments.get("max_entries", 500)
        if isinstance(maximum, bool) or not isinstance(maximum, int) or not 1 <= maximum <= 5000:
            raise CoreError("TOOL_ARGUMENTS_INVALID", "max_entries is invalid")
        try:
            entries = sorted(target.iterdir(), key=lambda item: item.name.casefold())
        except OSError as exc:
            raise CoreError("TOOL_DIRECTORY_READ_FAILED", "directory could not be listed", {"path": canonical}) from exc
        selected = entries[:maximum]
        return {
            "path": canonical,
            "entries": [
                {
                    "name": item.name,
                    "path": str(item),
                    "kind": "directory" if item.is_dir() else ("file" if item.is_file() else "other"),
                }
                for item in selected
            ],
            "entry_count": len(entries),
            "truncated": len(entries) > maximum,
        }

    def _search(self, call: ToolCall, grant: AuthorityGrant) -> Mapping[str, Any]:
        root_arg = self._path_arg(call, "path")
        query = self._text_arg(call, "query").strip()
        if not query:
            raise CoreError("TOOL_ARGUMENTS_INVALID", "query must be nonblank text")
        canonical = self._require_scope(grant, FilesystemOperation.READ, root_arg)
        root = Path(canonical)
        if not root.is_dir():
            raise CoreError(
                "TOOL_DIRECTORY_MISSING",
                "search path must be a directory",
                {"path": canonical},
            )

        max_results = call.arguments.get("max_results", 50)
        max_files = call.arguments.get("max_files", 3000)
        if (
            isinstance(max_results, bool)
            or not isinstance(max_results, int)
            or not 1 <= max_results <= 200
        ):
            raise CoreError("TOOL_ARGUMENTS_INVALID", "max_results is invalid")
        if (
            isinstance(max_files, bool)
            or not isinstance(max_files, int)
            or not 1 <= max_files <= 10000
        ):
            raise CoreError("TOOL_ARGUMENTS_INVALID", "max_files is invalid")

        query_fold = query.casefold()
        matches: list[dict[str, Any]] = []
        scanned_files = 0
        skipped_dirs = {".git", ".venv", "node_modules", "__pycache__"}

        try:
            candidates = root.rglob("*")
            for candidate in candidates:
                if any(part in skipped_dirs for part in candidate.parts):
                    continue
                if not candidate.is_file():
                    continue
                scanned_files += 1
                if scanned_files > max_files:
                    break

                candidate_text = str(candidate)
                path_match = query_fold in candidate_text.casefold()
                excerpts: list[dict[str, Any]] = []
                try:
                    with candidate.open(
                        "r",
                        encoding="utf-8",
                        errors="strict",
                    ) as handle:
                        for line_number, line in enumerate(handle, start=1):
                            if query_fold in line.casefold():
                                excerpts.append({
                                    "line": line_number,
                                    "text": line.rstrip("\r\n")[:500],
                                })
                                if len(excerpts) >= 3:
                                    break
                except (OSError, UnicodeError):
                    pass

                if path_match or excerpts:
                    matches.append({
                        "path": candidate_text,
                        "path_match": path_match,
                        "matches": excerpts,
                    })
                    if len(matches) >= max_results:
                        break
        except OSError as exc:
            raise CoreError(
                "TOOL_DIRECTORY_READ_FAILED",
                "search directory could not be traversed",
                {"path": canonical},
            ) from exc

        return {
            "path": canonical,
            "query": query,
            "results": matches,
            "result_count": len(matches),
            "scanned_files": min(scanned_files, max_files),
            "truncated": len(matches) >= max_results or scanned_files > max_files,
        }

    def _write_text(self, call: ToolCall, grant: AuthorityGrant) -> Mapping[str, Any]:
        path = self._path_arg(call, "path")
        content = self._text_arg(call, "content")
        canonical = self._require_scope(grant, FilesystemOperation.WRITE, path)
        target = Path(canonical)
        if not target.is_file():
            raise CoreError("TOOL_FILE_MISSING", "write target must already be a regular file", {"path": canonical})
        try:
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise CoreError("TOOL_FILE_WRITE_FAILED", "file could not be written", {"path": canonical}) from exc
        return {"path": canonical, "characters_written": len(content)}

    def _create_text(self, call: ToolCall, grant: AuthorityGrant) -> Mapping[str, Any]:
        path = self._path_arg(call, "path")
        content = self._text_arg(call, "content")
        canonical = self._require_scope(grant, FilesystemOperation.CREATE, path)
        target = Path(canonical)
        if target.exists():
            raise CoreError("TOOL_FILE_EXISTS", "create target already exists", {"path": canonical})
        if not target.parent.is_dir():
            raise CoreError("TOOL_PARENT_MISSING", "create target parent directory does not exist", {"path": canonical})
        try:
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise CoreError("TOOL_FILE_CREATE_FAILED", "file could not be created", {"path": canonical}) from exc
        return {"path": canonical, "characters_written": len(content)}

    def _delete_path(self, call: ToolCall, grant: AuthorityGrant) -> Mapping[str, Any]:
        path = self._path_arg(call, "path")
        canonical = self._require_scope(grant, FilesystemOperation.DELETE, path)
        target = Path(canonical)
        if not target.is_file():
            raise CoreError("TOOL_FILE_MISSING", "delete target must be a regular file", {"path": canonical})
        try:
            target.unlink()
        except OSError as exc:
            raise CoreError("TOOL_FILE_DELETE_FAILED", "file could not be deleted", {"path": canonical}) from exc
        return {"path": canonical, "deleted": True}

    def _move_path(self, call: ToolCall, grant: AuthorityGrant) -> Mapping[str, Any]:
        source = self._path_arg(call, "source")
        destination = self._path_arg(call, "destination")
        decision = self.authority.require_allowed(
            FilesystemOperation.MOVE,
            source,
            destination=destination,
        )
        self._require_resource_scope(grant, FilesystemOperation.MOVE, decision.path)
        if decision.destination is None:
            raise CoreError("TOOL_MOVE_INVALID", "move destination was not resolved")
        self._require_resource_scope(grant, FilesystemOperation.MOVE, decision.destination)
        source_path = Path(decision.path)
        destination_path = Path(decision.destination)
        if not source_path.is_file():
            raise CoreError("TOOL_FILE_MISSING", "move source must be a regular file", {"path": decision.path})
        if destination_path.exists():
            raise CoreError("TOOL_FILE_EXISTS", "move destination already exists", {"path": decision.destination})
        if not destination_path.parent.is_dir():
            raise CoreError("TOOL_PARENT_MISSING", "move destination parent does not exist", {"path": decision.destination})
        try:
            shutil.move(str(source_path), str(destination_path))
        except OSError as exc:
            raise CoreError("TOOL_FILE_MOVE_FAILED", "file could not be moved", {"source": decision.path, "destination": decision.destination}) from exc
        return {"source": decision.path, "destination": decision.destination, "moved": True}

    def _require_scope(
        self,
        grant: AuthorityGrant,
        operation: FilesystemOperation,
        path: str,
    ) -> str:
        decision = self.authority.require_allowed(operation, path)
        self._require_resource_scope(grant, operation, decision.path)
        return decision.path

    def _require_resource_scope(
        self,
        grant: AuthorityGrant,
        operation: FilesystemOperation,
        candidate: str,
    ) -> None:
        for raw in grant.authority.resource_scopes:
            parsed = parse_filesystem_scope(raw)
            if parsed is None:
                continue
            scope_operation, scope_path = parsed
            if scope_operation is not operation:
                continue
            if operation is FilesystemOperation.READ and scope_path == "*":
                return
            if self.authority.service.scope_contains(scope_path, candidate):
                return
        raise CoreError(
            "AUTHORITY_DENIED",
            "filesystem path is outside the granted Pass scope",
            {"operation": operation.value, "path": candidate},
        )

    @staticmethod
    def _path_arg(call: ToolCall, key: str) -> str:
        value = call.arguments.get(key)
        if not isinstance(value, str) or not value.strip():
            raise CoreError("TOOL_ARGUMENTS_INVALID", f"{key} must be nonblank text")
        return value.strip()

    @staticmethod
    def _text_arg(call: ToolCall, key: str) -> str:
        value = call.arguments.get(key)
        if not isinstance(value, str):
            raise CoreError("TOOL_ARGUMENTS_INVALID", f"{key} must be text")
        return value
