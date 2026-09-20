"""Generic OpenAI-compatible multi-turn tool harness.

This adapter is role-neutral. It uses the same ACL role/profile/dispatcher path as
single-turn chat roles, but permits an OpenAI-compatible model to call tools from
CoreServices.tools until it returns the normal ACL role-response envelope.

Worker is the first consumer; Reviewer, Planner query, and future roles may reuse
the same adapter without importing Worker code.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Mapping

from acl_core import (
    AdapterRequest,
    AdapterResponse,
    AuthorityEnvelope,
    AuthorityGrant,
    ToolCall,
)
from acl_core.canonical import canonical_json
from acl_core.diagnostics import emit
from acl_core.errors import CoreError

from .openai_compatible import OpenAICompatibleChatAdapter


@dataclass
class OpenAICompatibleAgentAdapter(OpenAICompatibleChatAdapter):
    """Run a bounded model/tool loop behind the generic adapter contract."""

    def _invoke_role(self, request: AdapterRequest) -> AdapterResponse:
        role_request = request.payload.get("role_request")
        if not isinstance(role_request, Mapping):
            return self._error(
                request,
                "ROLE_REQUEST_MISSING",
                "role_request payload is required",
            )
        execution = role_request.get("execution", {})
        if not isinstance(execution, Mapping):
            return self._error(
                request,
                "ROLE_EXECUTION_INVALID",
                "role execution settings must be a mapping",
            )

        resolved = self._resolve_runtime(execution)
        max_turns = self._positive_int(
            resolved.get("max_agent_turns", 64),
            "max_agent_turns",
        )
        max_tool_calls = self._positive_int(
            resolved.get("max_tool_calls", 128),
            "max_tool_calls",
        )
        max_identical_tool_failures = self._positive_int(
            resolved.get("max_identical_tool_failures", 3),
            "max_identical_tool_failures",
        )
        max_tool_result_chars_raw = resolved.get("max_tool_result_chars")
        max_tool_result_chars = (
            None
            if max_tool_result_chars_raw is None
            else self._positive_int(
                max_tool_result_chars_raw,
                "max_tool_result_chars",
            )
        )
        suppress_identical_success_calls = resolved.get(
            "suppress_identical_success_calls",
            False,
        )
        if not isinstance(suppress_identical_success_calls, bool):
            return self._error(
                request,
                "ADAPTER_SETTINGS_INVALID",
                "suppress_identical_success_calls must be boolean",
            )

        tool_ids_raw = role_request.get("tool_ids", [])
        if not isinstance(tool_ids_raw, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in tool_ids_raw
        ):
            return self._error(
                request,
                "ROLE_TOOLS_INVALID",
                "role_request.tool_ids must contain nonblank text",
            )
        tool_ids = tuple(sorted(set(tool_ids_raw)))

        try:
            tools = self._tool_schemas(tool_ids)
            grant = self._grant_from_request(request) if tool_ids else None
        except CoreError as exc:
            return AdapterResponse(
                request_id=request.request_id,
                ok=False,
                error=exc.to_dict(),
                metadata={
                    "adapter_id": self.adapter_id,
                    "model": resolved.get("model"),
                },
            )

        body = self._build_chat_body(role_request, resolved)
        messages = list(body.get("messages", []))
        body.pop("messages", None)
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        aggregate: dict[str, Any] = {
            "adapter_id": self.adapter_id,
            "runtime_family": "openai-compatible-agent",
            "model": resolved.get("model"),
            "turns": 0,
            "tool_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "http_elapsed_ms": 0.0,
            "request_bytes": 0,
            "response_bytes": 0,
            # context_window remains a compatibility alias. The generic adapter
            # does not know the provider's actually loaded capacity.
            "context_window": resolved.get("context_window"),
            "configured_context_window": resolved.get("context_window"),
            "observed_context_window": None,
            "context_capacity_source": (
                None
                if resolved.get("context_window") is None
                else "configured_route"
            ),
            "duplicate_success_tool_calls": 0,
            "repeated_failed_tool_calls": 0,
            "loop_control_interventions": 0,
            "final_response_retries": 0,
            "tool_result_truncations": 0,
            "tool_result_truncated_characters": 0,
            "tool_events": [],
        }
        successful_calls: dict[str, Mapping[str, Any]] = {}
        failed_call_counts: dict[str, int] = {}
        force_response_turn = False
        observed_token_field = {
            "prompt_tokens": False,
            "completion_tokens": False,
            "total_tokens": False,
        }

        for turn in range(1, max_turns + 1):
            request_body = {**body, "messages": messages}
            response_only_turn = bool(force_response_turn)
            if response_only_turn:
                # Some OpenAI-compatible runtimes ignore tool_choice="none" while
                # tool schemas remain present. Remove tool availability entirely
                # so loop control does not depend on provider compliance.
                request_body.pop("tools", None)
                request_body.pop("tool_choice", None)
                force_response_turn = False
                aggregate["loop_control_interventions"] += 1
            completion = self._request_completion(
                request_id=request.request_id,
                body=request_body,
                runtime=resolved,
            )
            if isinstance(completion, AdapterResponse):
                return AdapterResponse(
                    request_id=request.request_id,
                    ok=False,
                    error=completion.error,
                    metadata={
                        **aggregate,
                        **dict(completion.metadata),
                        "turns": turn,
                    },
                )

            parsed, telemetry = completion
            self._merge_telemetry(
                aggregate,
                telemetry,
                observed_token_field=observed_token_field,
            )
            aggregate["turns"] = turn

            try:
                message = self._extract_message(parsed)
            except ValueError as exc:
                return self._error(
                    request,
                    "RUNTIME_RESPONSE_INVALID",
                    str(exc),
                    metadata=aggregate,
                )

            tool_calls = message.get("tool_calls")
            if isinstance(tool_calls, list) and tool_calls:
                if response_only_turn:
                    return self._error(
                        request,
                        "AGENT_RESPONSE_ONLY_TOOL_CALL",
                        "model requested a tool during an ACL-forced response-only turn",
                        metadata=aggregate,
                    )
                if not tool_ids or grant is None:
                    return self._error(
                        request,
                        "AGENT_TOOL_CALL_UNAUTHORIZED",
                        "model requested a tool but no tool authority is available",
                        metadata=aggregate,
                    )
                messages.append(self._assistant_message(message))

                for raw_call in tool_calls:
                    aggregate["tool_calls"] += 1
                    if aggregate["tool_calls"] > max_tool_calls:
                        return self._error(
                            request,
                            "AGENT_TOOL_CALL_LIMIT",
                            "tool-call budget exhausted",
                            metadata=aggregate,
                        )

                    try:
                        call_id = self._tool_call_id(raw_call)
                        requested_tool_name = self._tool_call_name(raw_call)
                        tool_name = self._resolve_tool_name(
                            requested_tool_name,
                            tool_ids,
                        )
                        arguments = self._tool_call_arguments(raw_call)
                        signature = canonical_json({
                            "tool_id": tool_name,
                            "arguments": arguments,
                        })
                    except CoreError as exc:
                        return self._error(
                            request,
                            exc.code,
                            exc.message,
                            metadata=aggregate,
                        )

                    prior_success = successful_calls.get(signature)
                    definition = (
                        None
                        if self.services is None or tool_name not in tool_ids
                        else self.services.tools.definition(tool_name)
                    )
                    suppress_identical_success = (
                        suppress_identical_success_calls
                        or (
                            definition is not None
                            and definition.repeat_policy == "suppress_identical_success"
                        )
                    )
                    if prior_success is not None and suppress_identical_success:
                        aggregate["duplicate_success_tool_calls"] += 1
                        force_response_turn = True
                        emit(
                            "INFO",
                            "adapter.openai_agent",
                            "invoke_role",
                            "duplicate_success_tool_call_suppressed",
                            request_id=request.request_id,
                            tool_id=tool_name,
                            duplicate_count=aggregate["duplicate_success_tool_calls"],
                        )
                        aggregate["tool_events"].append({
                            "turn": turn,
                            "call_id": call_id,
                            "tool_id": tool_name,
                            "requested_tool_id": (
                                None
                                if requested_tool_name == tool_name
                                else requested_tool_name
                            ),
                            "arguments": arguments,
                            "ok": True,
                            "duplicate_suppressed": True,
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": tool_name,
                            "content": canonical_json({
                                "ok": True,
                                "tool_id": tool_name,
                                "duplicate_suppressed": True,
                                "prior_result": dict(prior_success),
                                "loop_control": (
                                    "This exact tool call already succeeded and was not "
                                    "executed again. Do not repeat it. On the next turn, "
                                    "return the final role response from observed results, "
                                    "or report continuation/blocker state if more work is needed."
                                ),
                            }),
                        })
                        continue

                    try:
                        tool_message = self._execute_tool_call(
                            raw_call,
                            allowed_tool_ids=tool_ids,
                            grant=grant,
                            resolved_tool_name=tool_name,
                        )
                        tool_message, result_limit = self._bound_tool_message(
                            tool_message,
                            max_chars=max_tool_result_chars,
                        )
                        if result_limit is not None:
                            aggregate["tool_result_truncations"] += 1
                            aggregate["tool_result_truncated_characters"] += (
                                result_limit["original_characters"]
                                - result_limit["visible_characters"]
                            )
                        try:
                            parsed_tool_result = json.loads(
                                tool_message["content"]
                            )
                        except (KeyError, TypeError, json.JSONDecodeError):
                            parsed_tool_result = {
                                "ok": True,
                                "tool_id": tool_name,
                            }
                        successful_calls[signature] = parsed_tool_result
                        aggregate["tool_events"].append({
                            "turn": turn,
                            "call_id": call_id,
                            "tool_id": tool_name,
                            "requested_tool_id": (
                                None
                                if requested_tool_name == tool_name
                                else requested_tool_name
                            ),
                            "arguments": arguments,
                            "ok": True,
                            "result_truncated": result_limit is not None,
                            "result_limit": result_limit,
                        })
                        failed_call_counts.pop(signature, None)
                    except CoreError as exc:
                        # Hard boundaries still deny the action. The structured
                        # denial is returned to the model so the role can BLOCK,
                        # choose another permitted action, or finish honestly.
                        failure_key = canonical_json({
                            "call": signature,
                            "error_code": exc.code,
                        })
                        observed_failures = failed_call_counts.get(failure_key, 0) + 1
                        failed_call_counts[failure_key] = observed_failures
                        repeated = observed_failures >= max_identical_tool_failures
                        if repeated:
                            aggregate["repeated_failed_tool_calls"] += 1
                            force_response_turn = True
                            emit(
                                "INFO",
                                "adapter.openai_agent",
                                "invoke_role",
                                "repeated_failed_tool_call_stopped",
                                request_id=request.request_id,
                                tool_id=tool_name,
                                error_code=exc.code,
                                identical_failure_count=observed_failures,
                            )
                        aggregate["tool_events"].append({
                            "turn": turn,
                            "call_id": call_id,
                            "tool_id": tool_name,
                            "requested_tool_id": (
                                None
                                if requested_tool_name == tool_name
                                else requested_tool_name
                            ),
                            "arguments": arguments,
                            "ok": False,
                            "error": exc.to_dict(),
                            "identical_failure_count": observed_failures,
                        })
                        tool_message = {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": tool_name,
                            "content": canonical_json({
                                "ok": False,
                                "tool_id": tool_name,
                                "error": exc.to_dict(),
                                "identical_failure_count": observed_failures,
                                "loop_control": (
                                    None
                                    if not repeated
                                    else (
                                        "ACL stopped repeated identical failing calls. "
                                        "Do not retry this exact action on the next turn. "
                                        "Return the final role response, choose a materially "
                                        "different permitted action, or report blocker/"
                                        "continuation state."
                                    )
                                ),
                            }),
                        }
                    messages.append(tool_message)
                continue

            finish_reason = telemetry.get("finish_reason")
            if finish_reason in {"length", "max_tokens"}:
                if aggregate["final_response_retries"] < 1:
                    aggregate["final_response_retries"] += 1
                    force_response_turn = True
                    messages.append({
                        "role": "user",
                        "content": (
                            "Your previous response reached the output limit before "
                            "the requested deliverable was complete. Stop investigating "
                            "and return only the final requested handoff now. Be concise. "
                            "Use the requested Pass/Task structure when applicable. "
                            "Do not narrate additional analysis or propose more inspection."
                        ),
                    })
                    continue
                aggregate["finish_reason"] = finish_reason
                return self._error(
                    request,
                    "AGENT_RESPONSE_TRUNCATED",
                    "model generation reached the output limit before a final response",
                    metadata=aggregate,
                )

            try:
                final_content = self._extract_content(parsed)
            except ValueError as exc:
                return self._error(
                    request,
                    "RUNTIME_RESPONSE_INVALID",
                    str(exc),
                    metadata=aggregate,
                )

            for key, seen in observed_token_field.items():
                if not seen:
                    aggregate[key] = None
            # Consumption counters are cumulative across turns. Context
            # utilization is the runtime's last-turn observation, not cumulative
            # prompt-token consumption divided by the context window.
            aggregate["finish_reason"] = telemetry.get("finish_reason")
            emit(
                "INFO",
                "adapter.openai_agent",
                "invoke_role",
                "agent_complete",
                request_id=request.request_id,
                turns=aggregate["turns"],
                tool_calls=aggregate["tool_calls"],
                model=aggregate.get("model"),
            )
            return AdapterResponse(
                request_id=request.request_id,
                ok=True,
                payload=final_content,
                metadata=aggregate,
            )

        return self._error(
            request,
            "AGENT_TURN_LIMIT",
            "agent turn budget exhausted before a final role response",
            metadata=aggregate,
        )

    def _tool_schemas(self, tool_ids: tuple[str, ...]) -> list[dict[str, Any]]:
        if not tool_ids:
            return []
        if self.services is None:
            raise CoreError(
                "ADAPTER_TOOL_SERVICES_MISSING",
                "tool-capable adapter was not given CoreServices",
            )
        schemas = []
        for tool_id in tool_ids:
            definition = self.services.tools.definition(tool_id)
            schemas.append({
                "type": "function",
                "function": definition.to_function_schema(),
            })
        return schemas

    def _grant_from_request(self, request: AdapterRequest) -> AuthorityGrant:
        authority_payload = request.payload.get("authority")
        if not isinstance(authority_payload, Mapping):
            raise CoreError(
                "ADAPTER_TOOL_AUTHORITY_MISSING",
                "tool-capable role request is missing authority",
            )
        raw = authority_payload.get("grant")
        if not isinstance(raw, Mapping):
            raise CoreError(
                "ADAPTER_TOOL_AUTHORITY_MISSING",
                "tool-capable role request is missing the full authority grant",
            )
        envelope = raw.get("authority")
        if not isinstance(envelope, Mapping):
            raise CoreError(
                "ADAPTER_TOOL_AUTHORITY_INVALID",
                "authority grant envelope is invalid",
            )
        try:
            return AuthorityGrant(
                grant_id=raw["grant_id"],
                issuer=raw["issuer"],
                subject=raw["subject"],
                authority=AuthorityEnvelope(
                    capabilities=tuple(envelope.get("capabilities", ())),
                    resource_scopes=tuple(envelope.get("resource_scopes", ())),
                    tool_scopes=tuple(envelope.get("tool_scopes", ())),
                ),
                parent_digest=raw.get("parent_digest"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CoreError(
                "ADAPTER_TOOL_AUTHORITY_INVALID",
                "authority grant is malformed",
            ) from exc

    def _execute_tool_call(
        self,
        value: Any,
        *,
        allowed_tool_ids: tuple[str, ...],
        grant: AuthorityGrant,
        resolved_tool_name: str | None = None,
    ) -> dict[str, Any]:
        if self.services is None:
            raise CoreError(
                "ADAPTER_TOOL_SERVICES_MISSING",
                "tool-capable adapter was not given CoreServices",
            )
        call_id = self._tool_call_id(value)
        requested_tool_name = self._tool_call_name(value)
        tool_name = (
            requested_tool_name
            if resolved_tool_name is None
            else resolved_tool_name
        )
        if tool_name not in allowed_tool_ids:
            raise CoreError(
                "AUTHORITY_DENIED",
                "model requested a tool outside the role grant",
                {"tool_id": tool_name},
            )
        arguments = self._tool_call_arguments(value)

        result = self.services.tools.invoke(
            ToolCall(
                tool_id=tool_name,
                arguments=dict(arguments),
                call_id=call_id,
            ),
            grant,
        )
        return {
            "role": "tool",
            "tool_call_id": call_id,
            "name": tool_name,
            "content": canonical_json(result.to_dict()),
        }

    @staticmethod
    def _bound_tool_message(
        tool_message: Mapping[str, Any],
        *,
        max_chars: int | None,
    ) -> tuple[dict[str, Any], dict[str, int] | None]:
        """Bound one model-visible tool result without changing tool execution.

        CoreServices has already executed the tool and produced its full result. This
        method only limits the serialized content appended to the model transcript.
        The replacement remains valid JSON and tells the model to request a narrower
        read/search when more detail is needed.
        """
        bounded = dict(tool_message)
        content = bounded.get("content")
        if (
            max_chars is None
            or not isinstance(content, str)
            or len(content) <= max_chars
        ):
            return bounded, None

        original_characters = len(content)
        reserve = min(768, max(128, max_chars // 4))
        excerpt_budget = max(0, max_chars - reserve)
        excerpt = content[:excerpt_budget]
        payload = {
            "ok": True,
            "result_truncated": True,
            "original_characters": original_characters,
            "content_excerpt": excerpt,
            "continuation": (
                "This tool result exceeded the model-visible result limit. "
                "Use a narrower path/query or a smaller max_chars/max_results "
                "request if more detail is required."
            ),
        }
        serialized = canonical_json(payload)
        while len(serialized) > max_chars and excerpt:
            overflow = len(serialized) - max_chars
            excerpt = excerpt[: max(0, len(excerpt) - overflow - 16)]
            payload["content_excerpt"] = excerpt
            serialized = canonical_json(payload)

        if len(serialized) > max_chars:
            payload = {
                "ok": True,
                "result_truncated": True,
                "original_characters": original_characters,
            }
            serialized = canonical_json(payload)

        bounded["content"] = serialized
        return bounded, {
            "original_characters": original_characters,
            "visible_characters": len(serialized),
        }


    @classmethod
    def _tool_call_signature(cls, value: Any) -> str:
        return canonical_json({
            "tool_id": cls._tool_call_name(value),
            "arguments": cls._tool_call_arguments(value),
        })

    @staticmethod
    def _tool_call_arguments(value: Any) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            raise CoreError("TOOL_CALL_INVALID", "tool call must be an object")
        function = value.get("function")
        if not isinstance(function, Mapping):
            raise CoreError("TOOL_CALL_INVALID", "tool call function is required")
        arguments_raw = function.get("arguments")
        if isinstance(arguments_raw, str):
            try:
                arguments = json.loads(arguments_raw)
            except json.JSONDecodeError as exc:
                raise CoreError(
                    "TOOL_ARGUMENTS_INVALID",
                    "tool arguments are not valid JSON",
                ) from exc
        elif isinstance(arguments_raw, Mapping):
            arguments = dict(arguments_raw)
        else:
            raise CoreError(
                "TOOL_ARGUMENTS_INVALID",
                "tool arguments must be a JSON object",
            )
        if not isinstance(arguments, Mapping):
            raise CoreError(
                "TOOL_ARGUMENTS_INVALID",
                "tool arguments must decode to an object",
            )
        return dict(arguments)

    @staticmethod
    def _extract_message(value: Mapping[str, Any]) -> Mapping[str, Any]:
        choices = value.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("runtime response contains no choices")
        first = choices[0]
        if not isinstance(first, Mapping):
            raise ValueError("runtime choice is invalid")
        message = first.get("message")
        if not isinstance(message, Mapping):
            raise ValueError("runtime choice contains no message")
        return message

    @staticmethod
    def _assistant_message(message: Mapping[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "role": "assistant",
            "content": message.get("content"),
        }
        for key in ("reasoning", "thinking", "reasoning_content"):
            value = message.get(key)
            if isinstance(value, str):
                result[key] = value
        if isinstance(message.get("tool_calls"), list):
            result["tool_calls"] = message["tool_calls"]
        return result

    @staticmethod
    def _tool_call_id(value: Any) -> str:
        if not isinstance(value, Mapping):
            raise CoreError("TOOL_CALL_INVALID", "tool call must be an object")
        call_id = value.get("id")
        if not isinstance(call_id, str) or not call_id.strip():
            raise CoreError("TOOL_CALL_INVALID", "tool call ID is required")
        return call_id.strip()

    @staticmethod
    def _tool_call_name(value: Any) -> str:
        if not isinstance(value, Mapping):
            raise CoreError("TOOL_CALL_INVALID", "tool call must be an object")
        function = value.get("function")
        if not isinstance(function, Mapping):
            raise CoreError("TOOL_CALL_INVALID", "tool call function is required")
        name = function.get("name")
        if not isinstance(name, str) or not name.strip():
            raise CoreError("TOOL_CALL_INVALID", "tool call function name is required")
        return name.strip()

    @staticmethod
    def _resolve_tool_name(
        requested: str,
        allowed_tool_ids: tuple[str, ...],
    ) -> str:
        if requested in allowed_tool_ids:
            return requested

        requested_fold = requested.casefold()
        matches = [
            tool_id
            for tool_id in allowed_tool_ids
            if tool_id.casefold() == requested_fold
        ]
        if len(matches) == 1:
            return matches[0]

        requested_parts = [
            part
            for part in re.split(r"[^a-z0-9_]+", requested_fold)
            if part
        ]
        requested_leaf = (
            requested_parts[-1]
            if requested_parts
            else requested_fold
        )
        leaf_matches = [
            tool_id
            for tool_id in allowed_tool_ids
            if re.split(r"[^a-z0-9_]+", tool_id.casefold())[-1]
            == requested_leaf
        ]
        if len(leaf_matches) == 1:
            return leaf_matches[0]

        # Preserve the model's requested name when no unique alias exists.
        # _execute_tool_call will reject it inside the normal structured tool
        # failure path, allowing the model to recover instead of aborting the
        # entire agent invocation.
        return requested

    @staticmethod
    def _positive_int(value: Any, label: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise CoreError(
                "ADAPTER_SETTINGS_INVALID",
                f"{label} must be a positive integer",
            )
        return value

    @staticmethod
    def _merge_telemetry(
        aggregate: dict[str, Any],
        observed: Mapping[str, Any],
        *,
        observed_token_field: dict[str, bool],
    ) -> None:
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = observed.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                aggregate[key] = int(aggregate.get(key) or 0) + value
                observed_token_field[key] = True
        for key in ("request_bytes", "response_bytes"):
            value = observed.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                aggregate[key] = int(aggregate.get(key) or 0) + value
        elapsed = observed.get("http_elapsed_ms")
        if isinstance(elapsed, (int, float)) and not isinstance(elapsed, bool):
            aggregate["http_elapsed_ms"] = round(
                float(aggregate.get("http_elapsed_ms") or 0.0) + float(elapsed),
                3,
            )
        if isinstance(observed.get("model"), str):
            aggregate["model"] = observed["model"]
        if isinstance(observed.get("context_window"), int):
            aggregate["context_window"] = observed["context_window"]
        utilization = observed.get("context_utilization")
        aggregate["context_utilization"] = (
            float(utilization)
            if isinstance(utilization, (int, float)) and not isinstance(utilization, bool)
            else None
        )
        for key in (
            "message_keys",
            "content_chars",
            "reasoning_chars",
            "thinking_chars",
        ):
            if key in observed:
                aggregate[key] = observed.get(key)

    def _error(
        self,
        request: AdapterRequest,
        code: str,
        message: str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> AdapterResponse:
        emit(
            "ERROR",
            "adapter.openai_agent",
            "invoke_role",
            "agent_error",
            request_id=request.request_id,
            code=code,
            message=message,
        )
        return AdapterResponse(
            request_id=request.request_id,
            ok=False,
            error={"code": code, "message": message},
            metadata=dict(metadata or {}),
        )
