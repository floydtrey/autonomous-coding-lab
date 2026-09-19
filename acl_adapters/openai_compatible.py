"""Generic OpenAI-compatible chat-completions runtime adapter.

This adapter is deliberately model- and provider-neutral. Runtime/model choices
come from role-profile execution settings, with adapter defaults supplied by
config/adapters.json. Compatible servers can be swapped without role/controller
source changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from typing import Any, Mapping
from urllib import error as urlerror
from urllib import request as urlrequest

from acl_core import AdapterRequest, AdapterResponse
from acl_core.canonical import canonical_json
from acl_core.diagnostics import emit, span
from acl_core.errors import CoreError


@dataclass
class OpenAICompatibleChatAdapter:
    adapter_id: str
    settings: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.adapter_id, str) or not self.adapter_id.strip():
            raise CoreError("ADAPTER_INVALID", "adapter_id is required")
        if not isinstance(self.settings, Mapping):
            raise CoreError("ADAPTER_INVALID", "adapter settings must be a mapping")
        self.settings = dict(self.settings)

    def invoke(self, request: AdapterRequest) -> AdapterResponse:
        with span(
            "adapter.openai_compatible",
            "invoke",
            adapter_id=self.adapter_id,
            request_id=request.request_id,
            operation=request.operation,
        ):
            if request.operation == "role.invoke":
                return self._invoke_role(request)
            if request.operation in {"role.status", "role.cancel"}:
                return AdapterResponse(
                    request_id=request.request_id,
                    ok=False,
                    error={
                        "code": "ADAPTER_OPERATION_UNSUPPORTED",
                        "message": f"{request.operation} is not supported by stateless chat-completions transport",
                    },
                )
            return AdapterResponse(
                request_id=request.request_id,
                ok=False,
                error={
                    "code": "ADAPTER_OPERATION_UNSUPPORTED",
                    "message": "unsupported adapter operation",
                    "operation": request.operation,
                },
            )

    def _invoke_role(self, request: AdapterRequest) -> AdapterResponse:
        role_request = request.payload.get("role_request")
        if not isinstance(role_request, Mapping):
            return AdapterResponse(
                request_id=request.request_id,
                ok=False,
                error={"code": "ROLE_REQUEST_MISSING", "message": "role_request payload is required"},
            )
        execution = role_request.get("execution", {})
        if not isinstance(execution, Mapping):
            return AdapterResponse(
                request_id=request.request_id,
                ok=False,
                error={"code": "ROLE_EXECUTION_INVALID", "message": "role execution settings must be a mapping"},
            )

        resolved = self._resolve_runtime(execution)
        url = resolved["url"]
        body = self._build_chat_body(role_request, resolved)
        headers = {"Content-Type": "application/json"}
        api_key = self._resolve_api_key(resolved)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        extra_headers = resolved.get("headers", {})
        if isinstance(extra_headers, Mapping):
            for key, value in extra_headers.items():
                if isinstance(key, str) and isinstance(value, str):
                    headers[key] = value

        raw_body = canonical_json(body).encode("utf-8")
        emit(
            "INFO",
            "adapter.openai_compatible",
            "invoke_role",
            "http_request",
            adapter_id=self.adapter_id,
            request_id=request.request_id,
            url=url,
            model=resolved["model"],
            timeout_seconds=resolved["timeout_seconds"],
            request_bytes=len(raw_body),
            temperature=resolved.get("temperature"),
            max_tokens=resolved.get("max_tokens"),
        )

        http_request = urlrequest.Request(
            url,
            data=raw_body,
            headers=headers,
            method="POST",
        )
        try:
            with urlrequest.urlopen(http_request, timeout=resolved["timeout_seconds"]) as response:
                raw = response.read()
                status_code = getattr(response, "status", 200)
        except urlerror.HTTPError as exc:
            raw = exc.read() if hasattr(exc, "read") else b""
            emit(
                "ERROR",
                "adapter.openai_compatible",
                "invoke_role",
                "http_error",
                adapter_id=self.adapter_id,
                request_id=request.request_id,
                status_code=exc.code,
                response_bytes=len(raw),
            )
            return AdapterResponse(
                request_id=request.request_id,
                ok=False,
                error={
                    "code": "RUNTIME_HTTP_ERROR",
                    "status_code": exc.code,
                    "body_excerpt": raw.decode("utf-8", errors="replace")[:2000],
                },
            )
        except (urlerror.URLError, TimeoutError, OSError) as exc:
            emit(
                "ERROR",
                "adapter.openai_compatible",
                "invoke_role",
                "transport_error",
                adapter_id=self.adapter_id,
                request_id=request.request_id,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
            )
            return AdapterResponse(
                request_id=request.request_id,
                ok=False,
                error={
                    "code": "RUNTIME_TRANSPORT_ERROR",
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                },
            )

        emit(
            "INFO",
            "adapter.openai_compatible",
            "invoke_role",
            "http_response",
            adapter_id=self.adapter_id,
            request_id=request.request_id,
            status_code=status_code,
            response_bytes=len(raw),
        )
        try:
            parsed = json.loads(raw.decode("utf-8"))
            content = self._extract_content(parsed)
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            return AdapterResponse(
                request_id=request.request_id,
                ok=False,
                error={
                    "code": "RUNTIME_RESPONSE_INVALID",
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "body_excerpt": raw.decode("utf-8", errors="replace")[:2000],
                },
            )
        return AdapterResponse(
            request_id=request.request_id,
            ok=True,
            payload=content,
        )

    def _resolve_runtime(self, execution: Mapping[str, Any]) -> dict[str, Any]:
        merged = dict(self.settings)
        merged.update(dict(execution))

        base_url = merged.get("base_url")
        model = merged.get("model")
        if not isinstance(base_url, str) or not base_url.strip():
            raise CoreError("ADAPTER_SETTINGS_INVALID", "base_url is required")
        if not isinstance(model, str) or not model.strip():
            raise CoreError("ADAPTER_SETTINGS_INVALID", "model is required")

        endpoint = merged.get("endpoint", "/chat/completions")
        if not isinstance(endpoint, str) or not endpoint.startswith("/"):
            raise CoreError("ADAPTER_SETTINGS_INVALID", "endpoint must begin with '/'")
        timeout = merged.get("timeout_seconds", 120)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise CoreError("ADAPTER_SETTINGS_INVALID", "timeout_seconds must be positive")

        result = {
            **merged,
            "base_url": base_url.rstrip("/"),
            "model": model,
            "url": base_url.rstrip("/") + endpoint,
            "timeout_seconds": float(timeout),
        }
        return result

    def _build_chat_body(
        self,
        role_request: Mapping[str, Any],
        runtime: Mapping[str, Any],
    ) -> dict[str, Any]:
        instructions = role_request.get("instructions")
        instruction_content = {}
        if isinstance(instructions, Mapping):
            content = instructions.get("content")
            if isinstance(content, Mapping):
                instruction_content = dict(content)

        system_message = {
            "role": "system",
            "content": (
                "You are an ACL role runtime. Follow the supplied role instructions exactly. "
                "Return only one JSON object matching the shared ACL role response envelope. "
                "Do not wrap JSON in Markdown. Do not add prose outside the JSON object.\n\n"
                "ROLE INSTRUCTIONS:\n" + canonical_json(instruction_content)
            ),
        }
        user_message = {
            "role": "user",
            "content": canonical_json({
                "schema_version": role_request.get("schema_version"),
                "workflow_id": role_request.get("workflow_id"),
                "attempt_id": role_request.get("attempt_id"),
                "role": role_request.get("role"),
                "objective": role_request.get("objective"),
                "context": role_request.get("context"),
                "authority_grant_id": role_request.get("authority_grant_id"),
                "tool_ids": role_request.get("tool_ids"),
                "metadata": role_request.get("metadata"),
            }),
        }
        body: dict[str, Any] = {
            "model": runtime["model"],
            "messages": [system_message, user_message],
            "stream": False,
        }
        for key in ("temperature", "max_tokens", "top_p", "seed"):
            if runtime.get(key) is not None:
                body[key] = runtime[key]
        if runtime.get("response_format_json", True):
            body["response_format"] = {"type": "json_object"}
        extra_body = runtime.get("extra_body")
        if isinstance(extra_body, Mapping):
            for key, value in extra_body.items():
                if key not in body:
                    body[key] = value
        return body

    @staticmethod
    def _resolve_api_key(runtime: Mapping[str, Any]) -> str | None:
        direct = runtime.get("api_key")
        if isinstance(direct, str) and direct:
            return direct
        env_name = runtime.get("api_key_env")
        if isinstance(env_name, str) and env_name:
            value = os.getenv(env_name)
            if value:
                return value
        return None

    @staticmethod
    def _extract_content(value: Any) -> str:
        if not isinstance(value, Mapping):
            raise ValueError("runtime response must be an object")
        choices = value.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("runtime response contains no choices")
        first = choices[0]
        if not isinstance(first, Mapping):
            raise ValueError("runtime choice is invalid")
        message = first.get("message")
        if not isinstance(message, Mapping):
            raise ValueError("runtime choice contains no message")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("runtime message content is empty")
        return content
