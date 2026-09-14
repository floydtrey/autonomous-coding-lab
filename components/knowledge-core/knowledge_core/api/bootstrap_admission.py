from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from knowledge_core.api.bootstrap_contract import (
    BOOTSTRAP_PRINCIPAL_REF,
    BootstrapContract,
    BootstrapOperation,
)


BOOTSTRAP_KEY_HEADER = "X-Knowledge-Key"
_api_key_header = APIKeyHeader(name=BOOTSTRAP_KEY_HEADER, auto_error=False)


@dataclass(frozen=True)
class BootstrapAdmission:
    contract: BootstrapContract
    api_key: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("bootstrap API key must be non-empty")

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
    ) -> "BootstrapAdmission":
        source = os.environ if env is None else env
        api_key = source.get("KNOWLEDGE_CORE_BOOTSTRAP_KEY")
        if not api_key:
            raise RuntimeError("KNOWLEDGE_CORE_BOOTSTRAP_KEY is required")
        return cls(
            contract=BootstrapContract.from_env(source),
            api_key=api_key,
        )

    def admit(self, *, supplied_key: str | None, operation: BootstrapOperation) -> str:
        if supplied_key != self.api_key:
            raise HTTPException(status_code=401, detail="bootstrap authentication failed")
        if operation not in self.contract.allowed_operations:
            raise HTTPException(status_code=403, detail="bootstrap operation is not allowed")
        return BOOTSTRAP_PRINCIPAL_REF


def bootstrap_principal_dependency(
    admission: BootstrapAdmission,
    *,
    operation: BootstrapOperation,
):
    async def dependency(
        supplied_key: str | None = Security(_api_key_header),
    ) -> str:
        return admission.admit(
            supplied_key=supplied_key,
            operation=operation,
        )

    return dependency
