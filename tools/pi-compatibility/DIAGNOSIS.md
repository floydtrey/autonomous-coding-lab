# S09 native tool-call diagnosis

**Diagnosis complete: reproduced upstream incompatibility; S09 remains blocked.**
Observed 2026-09-17 with the same approved qwen2.5-coder:7b model digest,
Ollama 0.34.1 and Pi 0.85.1. No model, server or production settings were changed.

| Bounded experiment | Result |
| --- | --- |
| Pi SDK, capture request and raw SSE response | HTTP 200; call-shaped JSON in content; no native tool calls; no files changed |
| Direct replay of exact Pi request, without Pi | HTTP 200; content only; no native tool calls |
| Ollama native `/api/chat`, equivalent messages/tools | HTTP 200; content only; no native tool calls |
| Direct request with explicit tool-protocol reminder | HTTP 200; content only; no native tool calls |

[Pi wire evidence](../../docs/evidence/S09_TOOL_DIAGNOSIS_PI.json) retains the exact
request and raw server stream alongside the independently rejected workspace.
[Direct comparison evidence](../../docs/evidence/S09_TOOL_DIAGNOSIS_DIRECT.json)
retains all three direct requests/responses and the installed template.
Each experiment was bounded to 256 output tokens; direct requests had 60-second
deadlines. Direct requests did not execute any returned text or tools.

The installed template advertises `tools` capability and instructs the model to
wrap function JSON in `<tool_call>` tags. Nevertheless, every observed API
response delivered text rather than the structured native call required by Pi.
The raw Pi stream itself lacks `delta.tool_calls`, so Pi did not discard a native
call. Failure on the native API also rules out a defect confined to Ollama's
OpenAI-compatible endpoint. The boundary is the model/template/Ollama parsing
combination, before Pi's response handling. The evidence does not distinguish
missing model-generated delimiters from server-side parser behavior; these API
responses are already processed by Ollama, not raw token output.

Ollama's [official tool-calling documentation](https://docs.ollama.com/capabilities/tool-calling)
uses structured `message.tool_calls`; call-shaped assistant text is insufficient.
The existing ACL adapter correctly avoided executing that text. A normal stop
and declared model capability are not proof of functioning tool use.

## Reproduction and next step

`tool-diagnostic.mjs` is an instrumented copy of the S09 disposable probe, with
request-body and raw-response capture. Run with the explicit `ACL_S09_PYTHON`
setting documented in S09.md. `diagnose-direct.mjs` replays the retained request
and performs the two additional comparisons without invoking any file tools.
The original S09 probe and its failed evidence are preserved.

No bounded configuration fix was established: explicitly reminding the model of
the installed protocol still failed. Do not install Pi again to address this, or
add text-to-tool interpretation. Proposed next task: inspect raw generation and
Ollama parser/template selection for this exact model digest, with at most one
isolated configuration correction and a native-call verification. If that cannot
establish compatibility, report it and separately select another approved pair.
No model download/switch, global template edit, parser redesign, S10 work or
production migration was performed.

[Subsequent server/path checks and official-template trial](REMEDIATION.md): server and paths verified; isolated template correction failed; alternative model qualification recommended.
