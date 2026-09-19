"""Externally configured Determiner work-type taxonomy."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping

from acl_core.canonical import canonical_digest
from acl_core.diagnostics import emit, span

from acl_roles.common.errors import RoleContractError


TAXONOMY_SCHEMA = "acl-determiner-taxonomy:v1"


@dataclass(frozen=True)
class WorkTypeDefinition:
    work_type: str
    description: str
    examples: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.work_type, "work_type"),
            (self.description, "description"),
        ):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise RoleContractError("DETERMINER_TAXONOMY_INVALID", f"{label} must be trimmed nonblank text")
        if any(not isinstance(item, str) or not item.strip() for item in self.examples):
            raise RoleContractError("DETERMINER_TAXONOMY_INVALID", "examples must contain nonblank text")
        if not isinstance(self.metadata, Mapping):
            raise RoleContractError("DETERMINER_TAXONOMY_INVALID", "metadata must be a mapping")

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_type": self.work_type,
            "description": self.description,
            "examples": list(self.examples),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkTypeDefinition":
        if not isinstance(value, Mapping):
            raise RoleContractError("DETERMINER_TAXONOMY_INVALID", "work type definition must be a mapping")
        examples = value.get("examples", [])
        if not isinstance(examples, list):
            raise RoleContractError("DETERMINER_TAXONOMY_INVALID", "work type examples must be a list")
        return cls(
            work_type=value["work_type"],
            description=value["description"],
            examples=tuple(examples),
            metadata=dict(value.get("metadata", {})),
        )


@dataclass(frozen=True)
class DeterminerTaxonomy:
    work_types: tuple[WorkTypeDefinition, ...]
    complexity_levels: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.work_types:
            raise RoleContractError("DETERMINER_TAXONOMY_INVALID", "taxonomy requires at least one work type")
        ids = tuple(item.work_type for item in self.work_types)
        if len(ids) != len(set(ids)):
            raise RoleContractError("DETERMINER_TAXONOMY_INVALID", "work type IDs must be unique")
        if len(self.complexity_levels) != len(set(self.complexity_levels)):
            raise RoleContractError("DETERMINER_TAXONOMY_INVALID", "complexity levels must be unique")
        if any(not isinstance(item, str) or not item.strip() for item in self.complexity_levels):
            raise RoleContractError("DETERMINER_TAXONOMY_INVALID", "complexity levels must be nonblank text")

    @property
    def work_type_ids(self) -> tuple[str, ...]:
        return tuple(item.work_type for item in self.work_types)

    def contains_work_type(self, value: str) -> bool:
        return value in self.work_type_ids

    def contains_complexity(self, value: str) -> bool:
        return value in self.complexity_levels

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": TAXONOMY_SCHEMA,
            "work_types": [item.to_dict() for item in self.work_types],
            "complexity_levels": list(self.complexity_levels),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "DeterminerTaxonomy":
        if not isinstance(value, Mapping) or value.get("schema_version") != TAXONOMY_SCHEMA:
            raise RoleContractError("DETERMINER_TAXONOMY_INVALID", "taxonomy schema is invalid")
        work_types = value.get("work_types")
        complexities = value.get("complexity_levels", [])
        if not isinstance(work_types, list) or not isinstance(complexities, list):
            raise RoleContractError("DETERMINER_TAXONOMY_INVALID", "taxonomy lists are invalid")
        return cls(
            work_types=tuple(WorkTypeDefinition.from_mapping(item) for item in work_types),
            complexity_levels=tuple(complexities),
        )

    @classmethod
    def load(cls, path: Path) -> "DeterminerTaxonomy":
        path = Path(path).expanduser().resolve()
        with span("roles.determiner", "taxonomy.load", path=str(path)):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError as exc:
                raise RoleContractError(
                    "DETERMINER_TAXONOMY_MISSING",
                    "Determiner taxonomy file does not exist",
                    {"path": str(path)},
                ) from exc
            except (OSError, json.JSONDecodeError) as exc:
                raise RoleContractError(
                    "DETERMINER_TAXONOMY_READ_FAILED",
                    "Determiner taxonomy file could not be read",
                    {"path": str(path)},
                ) from exc
            taxonomy = cls.from_mapping(value)
            emit(
                "INFO",
                "roles.determiner",
                "taxonomy.load",
                "taxonomy_loaded",
                path=str(path),
                taxonomy_digest=taxonomy.digest(),
                work_types=list(taxonomy.work_type_ids),
                complexity_levels=list(taxonomy.complexity_levels),
            )
            return taxonomy
