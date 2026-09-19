"""Externally configured Determiner work-type taxonomy."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Mapping

from acl_core.canonical import canonical_digest
from acl_core.diagnostics import emit, span

from acl_roles.common.errors import RoleContractError


TAXONOMY_SCHEMA = "acl-determiner-taxonomy:v2"
_WORK_TYPE_ID = re.compile(r"^[0-9]{4}$")


@dataclass(frozen=True)
class WorkTypeDefinition:
    work_type_id: str
    label: str
    description: str
    examples: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.work_type_id, str) or not _WORK_TYPE_ID.fullmatch(self.work_type_id):
            raise RoleContractError(
                "DETERMINER_TAXONOMY_INVALID",
                "work_type_id must be exactly four digits",
                {"work_type_id": self.work_type_id},
            )
        for value, label in (
            (self.label, "label"),
            (self.description, "description"),
        ):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise RoleContractError(
                    "DETERMINER_TAXONOMY_INVALID",
                    f"{label} must be trimmed nonblank text",
                )
        if any(not isinstance(item, str) or not item.strip() for item in self.examples):
            raise RoleContractError(
                "DETERMINER_TAXONOMY_INVALID",
                "examples must contain nonblank text",
            )
        if not isinstance(self.metadata, Mapping):
            raise RoleContractError(
                "DETERMINER_TAXONOMY_INVALID",
                "metadata must be a mapping",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_type_id": self.work_type_id,
            "label": self.label,
            "description": self.description,
            "examples": list(self.examples),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkTypeDefinition":
        if not isinstance(value, Mapping):
            raise RoleContractError(
                "DETERMINER_TAXONOMY_INVALID",
                "work type definition must be a mapping",
            )
        examples = value.get("examples", [])
        if not isinstance(examples, list):
            raise RoleContractError(
                "DETERMINER_TAXONOMY_INVALID",
                "work type examples must be a list",
            )
        return cls(
            work_type_id=value["work_type_id"],
            label=value["label"],
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
            raise RoleContractError(
                "DETERMINER_TAXONOMY_INVALID",
                "taxonomy requires at least one work type",
            )

        ids = tuple(item.work_type_id for item in self.work_types)
        labels = tuple(item.label for item in self.work_types)
        if len(ids) != len(set(ids)):
            raise RoleContractError(
                "DETERMINER_TAXONOMY_INVALID",
                "work type IDs must be unique",
            )
        if len(labels) != len(set(labels)):
            raise RoleContractError(
                "DETERMINER_TAXONOMY_INVALID",
                "work type labels must be unique",
            )

        if len(self.complexity_levels) != len(set(self.complexity_levels)):
            raise RoleContractError(
                "DETERMINER_TAXONOMY_INVALID",
                "complexity levels must be unique",
            )
        if any(not isinstance(item, str) or not item.strip() for item in self.complexity_levels):
            raise RoleContractError(
                "DETERMINER_TAXONOMY_INVALID",
                "complexity levels must be nonblank text",
            )

    @property
    def work_type_ids(self) -> tuple[str, ...]:
        return tuple(item.work_type_id for item in self.work_types)

    @property
    def work_type_labels(self) -> tuple[str, ...]:
        return tuple(item.label for item in self.work_types)

    def contains_work_type_id(self, value: str) -> bool:
        return value in self.work_type_ids

    def contains_complexity(self, value: str) -> bool:
        return value in self.complexity_levels

    def definition_for_id(self, work_type_id: str) -> WorkTypeDefinition:
        for item in self.work_types:
            if item.work_type_id == work_type_id:
                return item
        raise RoleContractError(
            "DETERMINER_WORK_TYPE_UNKNOWN",
            "work type ID is not configured",
            {"work_type_id": work_type_id},
        )

    def id_for_label(self, label: str) -> str | None:
        for item in self.work_types:
            if item.label == label:
                return item.work_type_id
        return None

    def label_for_id(self, work_type_id: str) -> str | None:
        for item in self.work_types:
            if item.work_type_id == work_type_id:
                return item.label
        return None

    def resolve_id(self, value: Any) -> str | None:
        """Resolve only exact configured IDs or labels; never fuzzy-match."""
        if not isinstance(value, str):
            return None
        if self.contains_work_type_id(value):
            return value
        return self.id_for_label(value)

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
            raise RoleContractError(
                "DETERMINER_TAXONOMY_INVALID",
                "taxonomy schema is invalid",
            )
        work_types = value.get("work_types")
        complexities = value.get("complexity_levels", [])
        if not isinstance(work_types, list) or not isinstance(complexities, list):
            raise RoleContractError(
                "DETERMINER_TAXONOMY_INVALID",
                "taxonomy lists are invalid",
            )
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
                work_type_ids=list(taxonomy.work_type_ids),
                work_type_labels=list(taxonomy.work_type_labels),
                complexity_levels=list(taxonomy.complexity_levels),
            )
            return taxonomy
