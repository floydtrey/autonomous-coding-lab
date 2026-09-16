from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


_BASE_URL_ENV = "KNOWLEDGE_CORE_BASE_URL"
_KEY_ENV = "KNOWLEDGE_CORE_BOOTSTRAP_KEY"
_DEFAULT_BASE_URL = "http://127.0.0.1:8765"
MASON_PROPOSER_REF = "mason"
_ALLOWED_OPERATIONS = frozenset(
    {"kc_status", "kc_search", "kc_get_source", "kc_store", "kc_propose_memory"}
)


class BridgeError(RuntimeError):
    """Fail-closed error from the bounded Mason -> KC bridge."""


@dataclass(frozen=True)
class BridgeConfig:
    base_url: str
    api_key: str
    timeout_seconds: float = 15.0

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "BridgeConfig":
        source = os.environ if env is None else env
        base_url = source.get(_BASE_URL_ENV, _DEFAULT_BASE_URL).strip().rstrip("/")
        api_key = source.get(_KEY_ENV, "")
        if not api_key:
            raise BridgeError(f"{_KEY_ENV} is required")
        _require_loopback_http_url(base_url)
        return cls(base_url=base_url, api_key=api_key)


def _require_loopback_http_url(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "http":
        raise BridgeError("Mason V1 requires a local http Knowledge Core URL")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise BridgeError("Mason V1 is qualified only for a loopback Knowledge Core endpoint")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise BridgeError("Knowledge Core base URL must not include a path/query/fragment")


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _deterministic_store_key(payload: dict[str, Any]) -> str:
    return f"mason-kc-v1:{sha256(_json_bytes(payload)).hexdigest()}"


def _deterministic_memory_proposal_key(payload: dict[str, Any]) -> str:
    return f"mason-kc-memory-v1:{sha256(_json_bytes(payload)).hexdigest()}"


def _require_exact_keys(
    payload: dict[str, Any],
    allowed: set[str],
    *,
    required: set[str] | None = None,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise BridgeError("unsupported field(s): " + ", ".join(unknown))
    missing = sorted((required or set()) - set(payload))
    if missing:
        raise BridgeError("missing required field(s): " + ", ".join(missing))


def _request(
    config: BridgeConfig,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "X-Knowledge-Key": config.api_key,
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = _json_bytes(payload)
    if extra_headers:
        headers.update(extra_headers)

    request = Request(
        f"{config.base_url}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=config.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise BridgeError(f"Knowledge Core returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise BridgeError(
            f"Knowledge Core is unreachable at {config.base_url}: {exc.reason}"
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BridgeError("Knowledge Core returned invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise BridgeError("Knowledge Core response must be a JSON object")
    return parsed


def _propose_memory(
    config: BridgeConfig,
    payload: dict[str, Any],
) -> dict[str, Any]:
    allowed = {"content", "project", "source_event_time", "idempotency_key"}
    _require_exact_keys(payload, allowed, required={"content", "project"})
    content = str(payload["content"])
    project = str(payload["project"]).strip()
    if not content.strip():
        raise BridgeError("kc_propose_memory content must not be blank")
    if not project:
        raise BridgeError("kc_propose_memory project must not be blank")
    if len(project) > 255:
        raise BridgeError("kc_propose_memory project must be 255 characters or fewer")

    request_body: dict[str, Any] = {
        "content": content,
        "project": project,
        "proposer_ref": MASON_PROPOSER_REF,
    }
    event_time = payload.get("source_event_time")
    if event_time is not None:
        text = str(event_time).strip()
        if not text:
            raise BridgeError(
                "kc_propose_memory source_event_time must not be blank when supplied"
            )
        request_body["source_event_time"] = text

    explicit = payload.get("idempotency_key")
    idempotency_key = (
        str(explicit).strip()
        if explicit is not None
        else _deterministic_memory_proposal_key(request_body)
    )
    if not idempotency_key:
        raise BridgeError("kc_propose_memory idempotency_key must not be blank")
    return _request(
        config,
        "POST",
        "/v1/kc/memory-candidates",
        request_body,
        extra_headers={"Idempotency-Key": idempotency_key},
    )


def _store(config: BridgeConfig, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"content", "project", "source_id", "source_event_time", "idempotency_key"}
    _require_exact_keys(payload, allowed, required={"content", "project"})
    content = str(payload["content"])
    project = str(payload["project"]).strip()
    if not content.strip():
        raise BridgeError("kc_store content must not be blank")
    if not project:
        raise BridgeError("kc_store project must not be blank")
    if len(project) > 255:
        raise BridgeError("kc_store project must be 255 characters or fewer")

    request_body: dict[str, Any] = {
        "content": content,
        "project": project,
        "source_type": "user_note",
    }
    for name in ("source_id", "source_event_time"):
        value = payload.get(name)
        if value is not None:
            text = str(value).strip()
            if not text:
                raise BridgeError(f"kc_store {name} must not be blank when supplied")
            request_body[name] = text

    explicit = payload.get("idempotency_key")
    idempotency_key = (
        str(explicit).strip()
        if explicit is not None
        else _deterministic_store_key(request_body)
    )
    if not idempotency_key:
        raise BridgeError("kc_store idempotency_key must not be blank")

    return _request(
        config,
        "POST",
        "/v1/kc/store",
        request_body,
        extra_headers={"Idempotency-Key": idempotency_key},
    )


def execute(
    operation: str,
    payload: dict[str, Any] | None = None,
    *,
    config: BridgeConfig | None = None,
) -> dict[str, Any]:
    if operation not in _ALLOWED_OPERATIONS:
        raise BridgeError(f"unsupported Knowledge Core operation: {operation}")

    body = dict(payload or {})
    resolved = config or BridgeConfig.from_env()

    if operation == "kc_status":
        _require_exact_keys(body, set())
        return _request(resolved, "GET", "/v1/kc/status")

    if operation == "kc_search":
        _require_exact_keys(body, {"query", "limit"}, required={"query"})
        query = str(body["query"]).strip()
        if not query:
            raise BridgeError("kc_search query must not be blank")
        limit = int(body.get("limit", 10))
        if limit < 1 or limit > 50:
            raise BridgeError("kc_search limit must be between 1 and 50")
        return _request(
            resolved,
            "POST",
            "/v1/kc/search",
            {"query": query, "limit": limit, "include_superseded": False},
        )

    if operation == "kc_get_source":
        _require_exact_keys(
            body,
            {"resource_version_ref"},
            required={"resource_version_ref"},
        )
        ref = str(body["resource_version_ref"]).strip()
        if not ref:
            raise BridgeError("kc_get_source resource_version_ref must not be blank")
        return _request(
            resolved,
            "POST",
            "/v1/kc/get-source",
            {"resource_version_ref": ref},
        )

    if operation == "kc_propose_memory":
        return _propose_memory(resolved, body)

    return _store(resolved, body)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": (
                        "usage: mason_kc_bridge.py "
                        "<kc_status|kc_search|kc_get_source|kc_store|kc_propose_memory>"
                    ),
                }
            ),
            file=sys.stderr,
        )
        return 2

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            raise BridgeError("bridge input must be a JSON object")
        result = execute(args[0], payload)
    except (json.JSONDecodeError, BridgeError, TypeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1

    print(
        json.dumps(
            {"ok": True, "operation": args[0], "result": result},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
