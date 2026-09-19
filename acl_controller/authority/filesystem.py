"""Controller-owned loading and exposure of filesystem authority policy."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from acl_core import (
    FilesystemAuthorityService,
    FilesystemDecision,
    FilesystemOperation,
)

from ..diagnostics import controller_span
from ..errors import ControllerError


FILESYSTEM_AUTHORITY_SCHEMA = "acl-filesystem-authority:v1"


@dataclass(frozen=True)
class UserProtectedPath:
    path: str
    reason: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "UserProtectedPath":
        if not isinstance(value, Mapping):
            raise ControllerError(
                "CONTROLLER_FILESYSTEM_AUTHORITY_INVALID",
                "protected path entry must be a mapping",
            )
        path = value.get("path")
        reason = value.get("reason", "operator-protected path")
        if not isinstance(path, str) or not path.strip():
            raise ControllerError(
                "CONTROLLER_FILESYSTEM_AUTHORITY_INVALID",
                "protected path is required",
            )
        if not isinstance(reason, str) or not reason.strip():
            raise ControllerError(
                "CONTROLLER_FILESYSTEM_AUTHORITY_INVALID",
                "protected path reason must be nonblank text",
            )
        return cls(path=path.strip(), reason=reason.strip())


class FilesystemAuthorityCoordinator:
    """Load persistent operator protections and delegate decisions to Core."""

    component = "controller.filesystem_authority"

    def __init__(
        self,
        *,
        service: FilesystemAuthorityService,
        policy_path: Path,
    ) -> None:
        self.service = service
        self.policy_path = Path(policy_path).expanduser().resolve()

    @classmethod
    def create(
        cls,
        *,
        project_root: Path,
        state_root: Path,
        config_root: Path,
    ) -> "FilesystemAuthorityCoordinator":
        project_root = Path(project_root).expanduser().resolve()
        state_root = Path(state_root).expanduser().resolve()
        config_root = Path(config_root).expanduser().resolve()
        policy_path = config_root / "filesystem_authority.json"
        protected = cls._load_user_protections(policy_path)

        service = FilesystemAuthorityService.for_acl(
            project_root=project_root,
            state_root=state_root,
            control_config_root=config_root,
            authority_config_path=policy_path,
            user_protected_paths=((item.path, item.reason) for item in protected),
        )
        return cls(service=service, policy_path=policy_path)

    def evaluate(
        self,
        operation: FilesystemOperation | str,
        path: str | Path,
        *,
        destination: str | Path | None = None,
    ) -> FilesystemDecision:
        with controller_span(
            "filesystem_authority.evaluate",
            operation=str(operation),
            path=str(path),
            destination=None if destination is None else str(destination),
        ):
            return self.service.evaluate(
                operation,
                path,
                destination=destination,
            )

    def require_allowed(
        self,
        operation: FilesystemOperation | str,
        path: str | Path,
        *,
        destination: str | Path | None = None,
    ) -> FilesystemDecision:
        with controller_span(
            "filesystem_authority.require_allowed",
            operation=str(operation),
            path=str(path),
            destination=None if destination is None else str(destination),
        ):
            return self.service.require_allowed(
                operation,
                path,
                destination=destination,
            )

    @staticmethod
    def _load_user_protections(path: Path) -> tuple[UserProtectedPath, ...]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ControllerError(
                "CONTROLLER_FILESYSTEM_AUTHORITY_MISSING",
                "filesystem authority policy file is missing",
                {"path": str(path)},
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ControllerError(
                "CONTROLLER_FILESYSTEM_AUTHORITY_INVALID",
                "filesystem authority policy file cannot be read",
                {"path": str(path)},
            ) from exc

        if not isinstance(value, Mapping) or value.get("schema_version") != FILESYSTEM_AUTHORITY_SCHEMA:
            raise ControllerError(
                "CONTROLLER_FILESYSTEM_AUTHORITY_INVALID",
                "filesystem authority policy schema is invalid",
                {"path": str(path)},
            )
        entries = value.get("protected_paths", [])
        if not isinstance(entries, list):
            raise ControllerError(
                "CONTROLLER_FILESYSTEM_AUTHORITY_INVALID",
                "protected_paths must be a list",
                {"path": str(path)},
            )
        result = tuple(UserProtectedPath.from_mapping(item) for item in entries)
        normalized = [item.path.casefold() for item in result]
        if len(normalized) != len(set(normalized)):
            raise ControllerError(
                "CONTROLLER_FILESYSTEM_AUTHORITY_INVALID",
                "protected_paths contains duplicate entries",
                {"path": str(path)},
            )
        return result
