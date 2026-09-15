from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


_BASE_URL_ENV = "KNOWLEDGE_CORE_BASE_URL"
_KEY_ENV = "KNOWLEDGE_CORE_BOOTSTRAP_KEY"
_DEFAULT_BASE_URL = "http://127.0.0.1:8765"
_ALLOWED_OPERATIONS = frozenset({"kc_status", "kc_search", "kc_get_source", "kc_store"})


class MasonKnowledgeCoreBridgeError(RuntimeError):
    """Fail-closed error from the bounded Mason -> KC bridge."""


@dataclass(frozen=True)
class MasonKnowledgeCoreConfig:
    base_url: str
    api_key: str
    timeout_seconds: float = 15.0

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "MasonKnowledgeCoreConfig":
        source = os.environ if env is None else env
        base_url = source.get(_BASE_URL_ENV, _DEFAULT_BASE_URL).strip().rstrip("/")
        api_key = source.get(_KEY_ENV, "")
        if not api_key:
            raise MasonKnowledgeCoreBridgeError(f"{_KEY_ENV} is required")
        _require_loopback_http_url(base_url)
        return cls(base_url=base_url, api_key=api_key)


def _require_loopback_http_url(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "http":
        raise MasonKnowledgeCoreBridgeError("Task 5 V1 requires a local http Knowledge Core URL")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise MasonKnowledgeCoreBridgeError(
            "Task 5 V1 is qualified only for a loopback Knowledge Core endpoint"
        )
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise MasonKnowledgeCoreBridgeError("Knowledge Core base URL must not include a path/query/fragment")


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _deterministic_store_key(payload: dict[str, Any]) -> str:
    digest = sha256(_json_bytes(payload)).hexdigest()
    return f"mason-kc-v1:{digest}"


class MasonKnowledgeCoreBridge:
    """Exact four-operation local bridge from Mason/Anton to the KC front door."""

    def __init__(self, config: MasonKnowledgeCoreConfig):
        self.config = config

    def execute(self, operation: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if operation not in _ALLOWED_OPERATIONS:
            raise MasonKnowledgeCoreBridgeError(f"unsupported Knowledge Core operation: {operation}")
        body = dict(payload or {})
        if operation == "kc_status":
            self._require_exact_keys(body, set())
            return self._request("GET", "/v1/kc/status")
        if operation == "kc_search":
            return self._search(body)
        if operation == "kc_get_source":
            return self._get_source(body)
        return self._store(body)

    def _search(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_exact_keys(payload, {"query", "limit"}, required={"query"})
        query = str(payload["query"]).strip()
        if not query:
            raise MasonKnowledgeCoreBridgeError("kc_search query must not be blank")
        limit = int(payload.get("limit", 10))
        if limit < 1 or limit > 50:
            raise MasonKnowledgeCoreBridgeError("kc_search limit must be between 1 and 50")
        return self._request(
            "POST",
            "/v1/kc/search",
            {"query": query, "limit": limit, "include_superseded": False},
        )

    def _get_source(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_exact_keys(payload, {"resource_version_ref"}, required={"resource_version_ref"})
        ref = str(payload["resource_version_ref"]).strip()
        if not ref:
            raise MasonKnowledgeCoreBridgeError("kc_get_source resource_version_ref must not be blank")
        return self._request(
            "POST",
            "/v1/kc/get-source",
            {"resource_version_ref": ref},
        )

    def _store(self, payload: dict[str, Any]) -> dict[str, Any]:
        allowed = {"content", "project", "source_id", "source_event_time", "idempotency_key"}
        self._require_exact_keys(payload, allowed, required={"content", "project"})
        content = str(payload["content"])
        project = str(payload["project"]).strip()
        if not content.strip():
            raise MasonKnowledgeCoreBridgeError("kc_store content must not be blank")
        if not project:
            raise MasonKnowledgeCoreBridgeError("kc_store project must not be blank")
        if len(project) > 255:
            raise MasonKnowledgeCoreBridgeError("kc_store project must be 255 characters or fewer")

        body: dict[str, Any] = {
            "content": content,
            "project": project,
            "source_type": "user_note",
        }
        for name in ("source_id", "source_event_time"):
            value = payload.get(name)
            if value is not None:
                text = str(value).strip()
                if not text:
                    raise MasonKnowledgeCoreBridgeError(f"kc_store {name} must not be blank when supplied")
                body[name] = text
        explicit = payload.get("idempotency_key")
        idempotency_key = str(explicit).strip() if explicit is not None else _deterministic_store_key(body)
        if not idempotency_key:
            raise MasonKnowledgeCoreBridgeError("kc_store idempotency_key must not be blank")
        return self._request(
            "POST",
            "/v1/kc/store",
            body,
            extra_headers={"Idempotency-Key": idempotency_key},
        )

    @staticmethod
    def _require_exact_keys(
        payload: dict[str, Any],
        allowed: set[str],
        *,
        required: set[str] | None = None,
    ) -> None:
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise MasonKnowledgeCoreBridgeError(
                "unsupported field(s): " + ", ".join(unknown)
            )
        missing = sorted((required or set()) - set(payload))
        if missing:
            raise MasonKnowledgeCoreBridgeError(
                "missing required field(s): " + ", ".join(missing)
            )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "X-Knowledge-Key": self.config.api_key,
        }
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = _json_bytes(payload)
        if extra_headers:
            headers.update(extra_headers)
        request = Request(
            f"{self.config.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw) if raw else {}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise MasonKnowledgeCoreBridgeError(
                f"Knowledge Core returned HTTP {exc.code}: {detail}"
            ) from exc
        except URLError as exc:
            raise MasonKnowledgeCoreBridgeError(
                f"Knowledge Core is unreachable at {self.config.base_url}: {exc.reason}"
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MasonKnowledgeCoreBridgeError("Knowledge Core returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise MasonKnowledgeCoreBridgeError("Knowledge Core response must be a JSON object")
        return parsed


__all__ = [
    "MasonKnowledgeCoreBridge",
    "MasonKnowledgeCoreBridgeError",
    "MasonKnowledgeCoreConfig",
]
