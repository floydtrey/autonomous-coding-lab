from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
import secrets
from threading import RLock


_CONSOLE_ENABLED_ENV = "KNOWLEDGE_CORE_CONSOLE_ENABLED"
_CONSOLE_KEY_ENV = "KNOWLEDGE_CORE_CONSOLE_KEY"
_CONSOLE_PROJECTS_ENV = "KNOWLEDGE_CORE_CONSOLE_PROJECTS"
_CONSOLE_DEFAULT_PROJECT_ENV = "KNOWLEDGE_CORE_CONSOLE_DEFAULT_PROJECT"


class ConsoleAuthenticationError(RuntimeError):
    pass


class ConsoleSessionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConsoleOwnerContract:
    allowed_projects: tuple[str, ...] = ("inbox",)
    default_project: str = "inbox"

    def __post_init__(self) -> None:
        projects = tuple(project.strip() for project in self.allowed_projects)
        if not projects or any(not project for project in projects):
            raise ValueError("console allowed projects must be non-empty")
        if len(set(projects)) != len(projects):
            raise ValueError("console allowed projects must be unique")
        if any(len(project) > 255 for project in projects):
            raise ValueError("console project keys must be at most 255 characters")
        default = self.default_project.strip()
        if default not in projects:
            raise ValueError("console default project must be in allowed projects")
        object.__setattr__(self, "allowed_projects", projects)
        object.__setattr__(self, "default_project", default)

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
    ) -> "ConsoleOwnerContract":
        source = os.environ if env is None else env
        raw_projects = source.get(_CONSOLE_PROJECTS_ENV, "inbox")
        projects = tuple(
            value.strip()
            for value in raw_projects.split(",")
            if value.strip()
        )
        default_project = source.get(
            _CONSOLE_DEFAULT_PROJECT_ENV,
            projects[0] if projects else "inbox",
        )
        return cls(
            allowed_projects=projects,
            default_project=default_project,
        )


@dataclass(frozen=True)
class ConsoleOwnerAdmission:
    contract: ConsoleOwnerContract
    owner_key: str

    def __post_init__(self) -> None:
        if not self.owner_key:
            raise ValueError("console owner key must be non-empty")

    @classmethod
    def optional_from_env(
        cls,
        env: Mapping[str, str] | None = None,
    ) -> "ConsoleOwnerAdmission | None":
        source = os.environ if env is None else env
        enabled = source.get(_CONSOLE_ENABLED_ENV, "").strip().lower()
        if enabled not in {"1", "true", "yes", "on"}:
            return None
        owner_key = source.get(_CONSOLE_KEY_ENV)
        if not owner_key:
            raise RuntimeError(
                f"{_CONSOLE_KEY_ENV} is required when {_CONSOLE_ENABLED_ENV} is enabled"
            )
        return cls(
            contract=ConsoleOwnerContract.from_env(source),
            owner_key=owner_key,
        )

    def authenticate(self, supplied_key: str | None) -> None:
        if supplied_key is None or not secrets.compare_digest(
            supplied_key,
            self.owner_key,
        ):
            raise ConsoleAuthenticationError("console owner authentication failed")


@dataclass(frozen=True)
class ConsoleSessionRecord:
    session_id: str
    csrf_token: str
    expires_at: datetime


class ConsoleSessionManager:
    def __init__(self, *, lifetime: timedelta = timedelta(hours=12)):
        if lifetime.total_seconds() <= 0:
            raise ValueError("console session lifetime must be positive")
        self._lifetime = lifetime
        self._records: dict[str, ConsoleSessionRecord] = {}
        self._lock = RLock()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def issue(self) -> ConsoleSessionRecord:
        now = self._now()
        record = ConsoleSessionRecord(
            session_id=secrets.token_urlsafe(32),
            csrf_token=secrets.token_urlsafe(32),
            expires_at=now + self._lifetime,
        )
        with self._lock:
            self._records[record.session_id] = record
        return record

    def get(self, session_id: str | None) -> ConsoleSessionRecord:
        if not session_id:
            raise ConsoleSessionError("console session is required")
        with self._lock:
            record = self._records.get(session_id)
            if record is None:
                raise ConsoleSessionError("console session is invalid")
            if record.expires_at <= self._now():
                self._records.pop(session_id, None)
                raise ConsoleSessionError("console session expired")
            return record

    def require_csrf(
        self,
        *,
        session_id: str | None,
        supplied_csrf: str | None,
    ) -> ConsoleSessionRecord:
        record = self.get(session_id)
        if supplied_csrf is None or not secrets.compare_digest(
            supplied_csrf,
            record.csrf_token,
        ):
            raise ConsoleSessionError("console CSRF token is invalid")
        return record

    def revoke(self, session_id: str | None) -> None:
        if not session_id:
            return
        with self._lock:
            self._records.pop(session_id, None)
