"""Shared role tool-profile configuration."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from ..errors import ControllerError


TOOL_PROFILE_SCHEMA = "acl-tool-profiles:v1"


@dataclass(frozen=True)
class ToolProfile:
    profile_id: str
    tool_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id.strip():
            raise ControllerError("CONTROLLER_TOOL_PROFILE_INVALID", "tool profile ID is required")
        if self.tool_ids != tuple(sorted(set(self.tool_ids))):
            raise ControllerError("CONTROLLER_TOOL_PROFILE_INVALID", "tool IDs must be sorted and unique")
        if any(not isinstance(item, str) or not item.strip() for item in self.tool_ids):
            raise ControllerError("CONTROLLER_TOOL_PROFILE_INVALID", "tool IDs must be nonblank text")


class ToolProfileResolver:
    """Resolve configured tool sets for any ACL role profile."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()

    def resolve(self, profile_id: str | None) -> tuple[str, ...]:
        if profile_id is None:
            return ()
        value = self._load()
        items = value.get("profiles", [])
        matches = [
            item for item in items
            if isinstance(item, Mapping) and item.get("profile_id") == profile_id
        ]
        if len(matches) != 1:
            raise ControllerError(
                "CONTROLLER_TOOL_PROFILE_MISSING" if not matches else "CONTROLLER_TOOL_PROFILE_AMBIGUOUS",
                "tool profile could not be resolved uniquely",
                {"profile_id": profile_id, "path": str(self.path)},
            )
        tools = matches[0].get("tool_ids", [])
        if not isinstance(tools, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in tools
        ):
            raise ControllerError(
                "CONTROLLER_TOOL_PROFILE_INVALID",
                "tool profile tool_ids must be a list of nonblank text values",
                {"profile_id": profile_id},
            )
        return ToolProfile(
            profile_id,
            tuple(sorted(set(item.strip() for item in tools))),
        ).tool_ids

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ControllerError(
                "CONTROLLER_TOOL_PROFILE_MISSING",
                "tool profile configuration is missing",
                {"path": str(self.path)},
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ControllerError(
                "CONTROLLER_TOOL_PROFILE_INVALID",
                "tool profile configuration cannot be read",
                {"path": str(self.path)},
            ) from exc
        if (
            not isinstance(value, dict)
            or value.get("schema_version") != TOOL_PROFILE_SCHEMA
            or not isinstance(value.get("profiles"), list)
        ):
            raise ControllerError(
                "CONTROLLER_TOOL_PROFILE_INVALID",
                "tool profile configuration schema is invalid",
                {"path": str(self.path)},
            )
        return value
