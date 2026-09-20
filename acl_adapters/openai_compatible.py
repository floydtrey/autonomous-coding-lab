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
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping
from urllib import error as urlerror
from urllib import request as urlrequest

from acl_core import AdapterRequest, AdapterResponse, CoreServices
from acl_core.canonical import canonical_json
from acl_core.diagnostics import emit, span
from acl_core.errors import CoreError


@dataclass
class OpenAICompatibleChatAdapter:
    adapter_id: str
    settings: Mapping[str, Any] = field(default_factory=dict)
    services: CoreServices | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.adapter_id, str) or not self.adapter_id.strip():
            raise CoreError("ADAPTER_INVALID", "adapter_id is required")
        if not isinstance(self.settings, Mapping):
            raise CoreError("ADAPTER_INVALID", "adapter settings must be a mapping")
        self.settings = dict(self.settings)

    @property
    def recovery_capabilities(self) -> Mapping[str, Any]:
        policy = self.settings.get("interrupted_attempt_policy", "block")
        return {
            "status_query": False,
            "cancel": False,
            "interrupted_attempt_policy": policy,
        }

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
        body = self._build_chat_body(role_request, resolved)
        completion = self._request_completion(
            request_id=request.request_id,
            body=body,
            runtime=resolved,
        )
        if isinstance(completion, AdapterResponse):
            return completion
        parsed, telemetry = completion
        try:
            content = self._extract_content(parsed)
        except (KeyError, TypeError, ValueError) as exc:
            return AdapterResponse(
                request_id=request.request_id,
                ok=False,
                error={
                    "code": "RUNTIME_RESPONSE_INVALID",
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                },
                metadata=telemetry,
            )
        emit(
            "INFO",
            "adapter.openai_compatible",
            "invoke_role",
            "runtime_telemetry",
            request_id=request.request_id,
            **telemetry,
        )
        return AdapterResponse(
            request_id=request.request_id,
            ok=True,
            payload=content,
            metadata=telemetry,
        )

    def _request_completion(
        self,
        *,
        request_id: str,
        body: Mapping[str, Any],
        runtime: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], dict[str, Any]] | AdapterResponse:
        """Send one OpenAI-compatible completion.

        Shared by the single-turn chat adapter and tool-capable agent adapters so
        provider transport, authentication, error handling, and telemetry stay in
        one implementation.
        """
        url = runtime["url"]
        headers = {"Content-Type": "application/json"}
        api_key = self._resolve_api_key(runtime)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        extra_headers = runtime.get("headers", {})
        if isinstance(extra_headers, Mapping):
            for key, value in extra_headers.items():
                if isinstance(key, str) and isinstance(value, str):
                    headers[key] = value

        raw_body = canonical_json(dict(body)).encode("utf-8")
        emit(
            "INFO",
            "adapter.openai_compatible",
            "request_completion",
            "http_request",
            adapter_id=self.adapter_id,
            request_id=request_id,
            url=url,
            model=runtime["model"],
            timeout_seconds=runtime["timeout_seconds"],
            request_bytes=len(raw_body),
            temperature=runtime.get("temperature"),
            max_tokens=runtime.get("max_tokens"),
        )
        http_request = urlrequest.Request(
            url,
            data=raw_body,
            headers=headers,
            method="POST",
        )
        started = perf_counter()
        try:
            with urlrequest.urlopen(http_request, timeout=runtime["timeout_seconds"]) as response:
                raw = response.read()
                status_code = getattr(response, "status", 200)
        except urlerror.HTTPError as exc:
            raw = exc.read() if hasattr(exc, "read") else b""
            return AdapterResponse(
                request_id=request_id,
                ok=False,
                error={
                    "code": "RUNTIME_HTTP_ERROR",
                    "status_code": exc.code,
                    "body_excerpt": raw.decode("utf-8", errors="replace")[:2000],
                },
                metadata={
                    "adapter_id": self.adapter_id,
                    "model": runtime["model"],
                    "http_elapsed_ms": round((perf_counter() - started) * 1000, 3),
                    "request_bytes": len(raw_body),
                    "response_bytes": len(raw),
                },
            )
        except (urlerror.URLError, TimeoutError, OSError) as exc:
            return AdapterResponse(
                request_id=request_id,
                ok=False,
                error={
                    "code": "RUNTIME_TRANSPORT_ERROR",
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                },
                metadata={
                    "adapter_id": self.adapter_id,
                    "model": runtime["model"],
                    "http_elapsed_ms": round((perf_counter() - started) * 1000, 3),
                    "request_bytes": len(raw_body),
                },
            )

        http_elapsed_ms = round((perf_counter() - started) * 1000, 3)
        emit(
            "INFO",
            "adapter.openai_compatible",
            "request_completion",
            "http_response",
            adapter_id=self.adapter_id,
            request_id=request_id,
            status_code=status_code,
            response_bytes=len(raw),
            http_elapsed_ms=http_elapsed_ms,
        )
        try:
            parsed = json.loads(raw.decode("utf-8"))
            if not isinstance(parsed, Mapping):
                raise ValueError("runtime response must be an object")
            telemetry = {
                "adapter_id": self.adapter_id,
                **self._extract_telemetry(
                    parsed,
                    runtime=runtime,
                    http_elapsed_ms=http_elapsed_ms,
                    response_bytes=len(raw),
                    request_bytes=len(raw_body),
                ),
            }
            return parsed, telemetry
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            return AdapterResponse(
                request_id=request_id,
                ok=False,
                error={
                    "code": "RUNTIME_RESPONSE_INVALID",
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "body_excerpt": raw.decode("utf-8", errors="replace")[:2000],
                },
                metadata={
                    "adapter_id": self.adapter_id,
                    "model": runtime["model"],
                    "http_elapsed_ms": http_elapsed_ms,
                    "request_bytes": len(raw_body),
                    "response_bytes": len(raw),
                },
            )

    def _resolve_runtime(self, execution: Mapping[str, Any]) -> dict[str, Any]:
        merged = dict(self.settings)
        merged.update(dict(execution))

        base_url = self._value_or_env(
            merged,
            literal_key="base_url",
            env_key="base_url_env",
            required=True,
        )
        model = self._value_or_env(
            merged,
            literal_key="model",
            env_key="model_env",
            required=True,
        )

        endpoint = merged.get("endpoint", "/chat/completions")
        if not isinstance(endpoint, str) or not endpoint.startswith("/"):
            raise CoreError("ADAPTER_SETTINGS_INVALID", "endpoint must begin with '/'")
        timeout = merged.get("timeout_seconds", 120)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise CoreError("ADAPTER_SETTINGS_INVALID", "timeout_seconds must be positive")

        context_window = merged.get("context_window")
        if context_window is None:
            context_window_env = merged.get("context_window_env")
            if isinstance(context_window_env, str) and context_window_env.strip():
                raw_context_window = os.getenv(context_window_env.strip())
                if isinstance(raw_context_window, str) and raw_context_window.strip():
                    try:
                        context_window = int(raw_context_window.strip())
                    except ValueError as exc:
                        raise CoreError(
                            "ADAPTER_SETTINGS_INVALID",
                            "context_window_env must resolve to a positive integer",
                            {"env": context_window_env},
                        ) from exc
        if context_window is not None and (
            isinstance(context_window, bool)
            or not isinstance(context_window, int)
            or context_window <= 0
        ):
            raise CoreError(
                "ADAPTER_SETTINGS_INVALID",
                "context_window must be a positive integer when configured",
            )

        result = {
            **merged,
            "base_url": base_url.rstrip("/"),
            "model": model,
            "url": base_url.rstrip("/") + endpoint,
            "timeout_seconds": float(timeout),
            "context_window": context_window,
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
    def _value_or_env(
        runtime: Mapping[str, Any],
        *,
        literal_key: str,
        env_key: str,
        required: bool,
    ) -> str | None:
        literal = runtime.get(literal_key)
        if isinstance(literal, str) and literal.strip():
            return literal.strip()
        env_name = runtime.get(env_key)
        if isinstance(env_name, str) and env_name.strip():
            value = os.getenv(env_name.strip())
            if isinstance(value, str) and value.strip():
                return value.strip()
        if required:
            raise CoreError(
                "ADAPTER_SETTINGS_INVALID",
                f"{literal_key} is required directly or through {env_key}",
            )
        return None

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
        file_value = runtime.get("api_key_file")
        file_env = runtime.get("api_key_file_env")
        if not file_value and isinstance(file_env, str) and file_env:
            file_value = os.getenv(file_env)
        if isinstance(file_value, str) and file_value.strip():
            path = Path(file_value.strip()).expanduser()
            try:
                value = path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise CoreError(
                    "ADAPTER_API_KEY_FILE_FAILED",
                    "configured API-key file could not be read",
                    {"path": str(path)},
                ) from exc
            if value:
                return value
        return None

    @staticmethod
    def _extract_telemetry(
        value: Mapping[str, Any],
        *,
        runtime: Mapping[str, Any],
        http_elapsed_ms: float,
        response_bytes: int,
        request_bytes: int,
    ) -> dict[str, Any]:
        usage = value.get("usage")
        usage = dict(usage) if isinstance(usage, Mapping) else {}

        def token_value(*keys: str) -> int | None:
            for key in keys:
                candidate = usage.get(key)
                if (
                    isinstance(candidate, int)
                    and not isinstance(candidate, bool)
                    and candidate >= 0
                ):
                    return candidate
            return None

        prompt_tokens = token_value("prompt_tokens", "input_tokens")
        completion_tokens = token_value("completion_tokens", "output_tokens")
        total_tokens = token_value("total_tokens")

        context_window = runtime.get("context_window")
        if (
            isinstance(context_window, bool)
            or not isinstance(context_window, int)
            or context_window <= 0
        ):
            context_window = None
        context_utilization = (
            None
            if prompt_tokens is None or context_window is None
            else round(prompt_tokens / context_window, 6)
        )

        finish_reason = None
        choices = value.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], Mapping):
            observed = choices[0].get("finish_reason")
            if isinstance(observed, str):
                finish_reason = observed

        response_model = value.get("model")
        if not isinstance(response_model, str) or not response_model.strip():
            response_model = runtime.get("model")

        telemetry = {
            "runtime_family": "openai-compatible",
            "model": response_model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "context_window": context_window,
            "context_utilization": context_utilization,
            "http_elapsed_ms": http_elapsed_ms,
            "request_bytes": request_bytes,
            "response_bytes": response_bytes,
            "finish_reason": finish_reason,
            "runtime_response_id": value.get("id") if isinstance(value.get("id"), str) else None,
            "system_fingerprint": (
                value.get("system_fingerprint")
                if isinstance(value.get("system_fingerprint"), str)
                else None
            ),
        }
        return telemetry

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
