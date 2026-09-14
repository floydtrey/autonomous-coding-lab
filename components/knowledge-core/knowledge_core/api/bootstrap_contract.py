from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
import os


DEFAULT_BIND_HOST = "127.0.0.1"
BOOTSTRAP_PRINCIPAL_REF = "local_owner"


class BootstrapOperation(StrEnum):
    STORE = "kc.store"
    SEARCH = "kc.search"
    GET_SOURCE = "kc.get_source"
    STATUS = "kc.status"


_DEFAULT_ALLOWED_OPERATIONS = frozenset(BootstrapOperation)


@dataclass(frozen=True)
class BootstrapContract:
    """Replaceable KC Usable V1 deployment/admission contract."""

    bind_host: str = DEFAULT_BIND_HOST
    principal_ref: str = BOOTSTRAP_PRINCIPAL_REF
    allowed_operations: frozenset[BootstrapOperation] = field(
        default_factory=lambda: _DEFAULT_ALLOWED_OPERATIONS
    )

    def __post_init__(self) -> None:
        if not self.bind_host.strip():
            raise ValueError("bootstrap bind host must be non-empty")
        if self.principal_ref != BOOTSTRAP_PRINCIPAL_REF:
            raise ValueError("bootstrap principal must remain local_owner in Usable V1")
        if not self.allowed_operations:
            raise ValueError("bootstrap allowed operations must be non-empty")
        if not all(
            isinstance(operation, BootstrapOperation)
            for operation in self.allowed_operations
        ):
            raise TypeError("bootstrap allowed operations must use BootstrapOperation")

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
    ) -> "BootstrapContract":
        source = os.environ if env is None else env
        return cls(
            bind_host=source.get("KNOWLEDGE_CORE_BIND_HOST", DEFAULT_BIND_HOST),
        )
