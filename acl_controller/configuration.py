"""External Controller routing/profile configuration.

Configuration owns model/harness/runtime choices. Controller only resolves exact
configured mappings; it never guesses or silently falls back.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping

from .diagnostics import controller_span
from .errors import ControllerError


PROFILE_SCHEMA = "acl-controller-profile:v1"
ROUTING_SCHEMA = "acl-controller-routing:v1"


@dataclass(frozen=True)
class ProfileSelector:
    role: str
    work_type: str | None = None
    complexity: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "role": self.role,
            "work_type": self.work_type,
            "complexity": self.complexity,
        }


@dataclass(frozen=True)
class RoleProfile:
    profile_id: str
    role: str
    adapter_id: str
    settings: Mapping[str, Any] = field(default_factory=dict)
    instructions: Mapping[str, Any] = field(default_factory=dict)
    tool_profile: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RoleProfile":
        if not isinstance(value, Mapping) or value.get("schema_version") != PROFILE_SCHEMA:
            raise ControllerError("CONTROLLER_PROFILE_INVALID", "profile schema is invalid")
        for key in ("profile_id", "role", "adapter_id"):
            if not isinstance(value.get(key), str) or not value[key].strip():
                raise ControllerError("CONTROLLER_PROFILE_INVALID", f"{key} is required")
        return cls(
            profile_id=value["profile_id"],
            role=value["role"],
            adapter_id=value["adapter_id"],
            settings=dict(value.get("settings", {})),
            instructions=dict(value.get("instructions", {})),
            tool_profile=value.get("tool_profile"),
            metadata=dict(value.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PROFILE_SCHEMA,
            "profile_id": self.profile_id,
            "role": self.role,
            "adapter_id": self.adapter_id,
            "settings": dict(self.settings),
            "instructions": dict(self.instructions),
            "tool_profile": self.tool_profile,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class RouteRule:
    role: str
    profile_id: str
    work_type: str | None = None
    complexity: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RouteRule":
        if not isinstance(value, Mapping):
            raise ControllerError("CONTROLLER_ROUTING_INVALID", "routing rule must be a mapping")
        for key in ("role", "profile_id"):
            if not isinstance(value.get(key), str) or not value[key].strip():
                raise ControllerError("CONTROLLER_ROUTING_INVALID", f"{key} is required")
        work_type = value.get("work_type")
        if work_type is not None and (not isinstance(work_type, str) or not work_type.strip()):
            raise ControllerError("CONTROLLER_ROUTING_INVALID", "work_type must be nonblank text when present")
        complexity = value.get("complexity")
        if complexity is not None and (not isinstance(complexity, str) or not complexity.strip()):
            raise ControllerError("CONTROLLER_ROUTING_INVALID", "complexity must be nonblank text when present")
        return cls(value["role"], value["profile_id"], work_type, complexity)


class ProfileResolver:
    component = "controller.configuration"

    def __init__(self, config_root: Path) -> None:
        self.root = Path(config_root).expanduser().resolve()

    def resolve(self, selector: ProfileSelector) -> RoleProfile:
        with controller_span(
            "configuration.resolve",
            role=selector.role,
            work_type=selector.work_type,
            complexity=selector.complexity,
        ):
            routes = self._load_routes()
            matches = [
                rule for rule in routes
                if rule.role == selector.role
                and rule.work_type == selector.work_type
                and rule.complexity == selector.complexity
            ]
            if not matches:
                raise ControllerError(
                    "CONTROLLER_PROFILE_ROUTE_MISSING",
                    "no exact profile route is configured",
                    selector.to_dict(),
                )
            if len(matches) != 1:
                raise ControllerError(
                    "CONTROLLER_PROFILE_ROUTE_AMBIGUOUS",
                    "more than one exact profile route matches",
                    selector.to_dict(),
                )
            profile = self._load_profile(matches[0].profile_id)
            if profile.role != selector.role:
                raise ControllerError(
                    "CONTROLLER_PROFILE_ROLE_MISMATCH",
                    "resolved profile role differs from requested role",
                    {"selector": selector.to_dict(), "profile_id": profile.profile_id, "profile_role": profile.role},
                )
            return profile

    def profile(self, profile_id: str) -> RoleProfile:
        with controller_span("configuration.profile", profile_id=profile_id):
            return self._load_profile(profile_id)

    def _load_routes(self) -> tuple[RouteRule, ...]:
        value = self._read_json(self.root / "routing.json")
        if value.get("schema_version") != ROUTING_SCHEMA or not isinstance(value.get("routes"), list):
            raise ControllerError("CONTROLLER_ROUTING_INVALID", "routing configuration schema is invalid")
        return tuple(RouteRule.from_mapping(item) for item in value["routes"])

    def _load_profile(self, profile_id: str) -> RoleProfile:
        if not isinstance(profile_id, str) or not profile_id.strip() or any(ch in profile_id for ch in "\\/:"):
            raise ControllerError("CONTROLLER_PROFILE_INVALID", "profile ID is invalid")
        profile = RoleProfile.from_mapping(self._read_json(self.root / "profiles" / f"{profile_id}.json"))
        if profile.profile_id != profile_id:
            raise ControllerError(
                "CONTROLLER_PROFILE_ID_MISMATCH",
                "profile file identity differs from requested profile",
                {"requested": profile_id, "observed": profile.profile_id},
            )
        return profile

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ControllerError("CONTROLLER_CONFIG_MISSING", "configuration file is missing", {"path": str(path)}) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ControllerError("CONTROLLER_CONFIG_INVALID", "configuration file cannot be read", {"path": str(path)}) from exc
        if not isinstance(value, dict):
            raise ControllerError("CONTROLLER_CONFIG_INVALID", "configuration file must contain a JSON object", {"path": str(path)})
        return value
