"""Configuration-driven runtime-adapter loader."""
from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import json
from pathlib import Path
from typing import Any, Mapping

from acl_core import CoreServices
from acl_core.diagnostics import emit, span
from acl_core.errors import CoreError


ADAPTER_CONFIG_SCHEMA = "acl-adapters:v1"


@dataclass(frozen=True)
class AdapterConfig:
    adapter_id: str
    implementation: str
    settings: Mapping[str, Any] = field(default_factory=dict)
    enabled: bool = True

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AdapterConfig":
        if not isinstance(value, Mapping):
            raise CoreError("ADAPTER_CONFIG_INVALID", "adapter configuration must be a mapping")
        adapter_id = value.get("adapter_id")
        implementation = value.get("implementation")
        if not isinstance(adapter_id, str) or not adapter_id.strip():
            raise CoreError("ADAPTER_CONFIG_INVALID", "adapter_id is required")
        if not isinstance(implementation, str) or ":" not in implementation:
            raise CoreError(
                "ADAPTER_CONFIG_INVALID",
                "implementation must use module:object syntax",
                {"adapter_id": adapter_id},
            )
        settings = value.get("settings", {})
        if not isinstance(settings, Mapping):
            raise CoreError("ADAPTER_CONFIG_INVALID", "adapter settings must be a mapping")
        enabled = value.get("enabled", True)
        if not isinstance(enabled, bool):
            raise CoreError("ADAPTER_CONFIG_INVALID", "enabled must be boolean")
        return cls(adapter_id, implementation, dict(settings), enabled)


class AdapterLoader:
    component = "adapters.loader"

    @classmethod
    def load_file(cls, core: CoreServices, path: Path) -> tuple[str, ...]:
        path = Path(path).expanduser().resolve()
        with span(cls.component, "load_file", path=str(path)):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                emit("DEBUG", cls.component, "load_file", "adapter_config_absent", path=str(path))
                return ()
            except (OSError, json.JSONDecodeError) as exc:
                raise CoreError(
                    "ADAPTER_CONFIG_READ_FAILED",
                    "adapter configuration could not be read",
                    {"path": str(path)},
                ) from exc

            if not isinstance(value, Mapping) or value.get("schema_version") != ADAPTER_CONFIG_SCHEMA:
                raise CoreError("ADAPTER_CONFIG_INVALID", "adapter configuration schema is invalid")
            items = value.get("adapters", [])
            if not isinstance(items, list):
                raise CoreError("ADAPTER_CONFIG_INVALID", "adapters must be a list")

            loaded = []
            for item in items:
                config = AdapterConfig.from_mapping(item)
                if not config.enabled:
                    emit(
                        "DEBUG",
                        cls.component,
                        "load_file",
                        "adapter_skipped",
                        adapter_id=config.adapter_id,
                        implementation=config.implementation,
                    )
                    continue
                adapter = cls.instantiate(config, services=core)
                core.adapters.register(adapter)
                loaded.append(config.adapter_id)
                emit(
                    "INFO",
                    cls.component,
                    "load_file",
                    "adapter_loaded",
                    adapter_id=config.adapter_id,
                    implementation=config.implementation,
                )
            return tuple(loaded)

    @classmethod
    def instantiate(cls, config: AdapterConfig, *, services: CoreServices | None = None):
        with span(
            cls.component,
            "instantiate",
            adapter_id=config.adapter_id,
            implementation=config.implementation,
        ):
            module_name, object_name = config.implementation.split(":", 1)
            try:
                module = importlib.import_module(module_name)
                factory = getattr(module, object_name)
            except (ImportError, AttributeError) as exc:
                raise CoreError(
                    "ADAPTER_IMPLEMENTATION_MISSING",
                    "configured adapter implementation could not be imported",
                    {
                        "adapter_id": config.adapter_id,
                        "implementation": config.implementation,
                    },
                ) from exc
            try:
                adapter = factory(
                    adapter_id=config.adapter_id,
                    settings=dict(config.settings),
                    services=services,
                )
            except Exception as exc:
                raise CoreError(
                    "ADAPTER_INITIALIZATION_FAILED",
                    "configured adapter could not be initialized",
                    {
                        "adapter_id": config.adapter_id,
                        "implementation": config.implementation,
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                    },
                ) from exc
            observed = getattr(adapter, "adapter_id", None)
            if observed != config.adapter_id:
                raise CoreError(
                    "ADAPTER_ID_MISMATCH",
                    "adapter implementation returned a different adapter ID",
                    {"configured": config.adapter_id, "observed": observed},
                )
            return adapter
