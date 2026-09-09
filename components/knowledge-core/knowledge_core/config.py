from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        value = os.environ.get("KNOWLEDGE_CORE_DATABASE_URL")
        if not value:
            raise RuntimeError("KNOWLEDGE_CORE_DATABASE_URL is required")
        return cls(database_url=value)
