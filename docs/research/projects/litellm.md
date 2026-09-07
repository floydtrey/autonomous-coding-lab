# LiteLLM — Task 23 Deep Research

**Research date:** 2026-09-07  
**Research target:** current LiteLLM provider-normalization, gateway, router, local-provider, tool/schema, retry/fallback, streaming, auth/network, observability and reproducibility architecture  
**Canonical repository:** `BerriAI/litellm`  
**Revision inspected:** `168a0055a244acdcf97c330c52e085ab40b1424c` (2026-09-06)  
**Latest stable release observed:** `v1.100.0` (2026-09-06)  
**Latest prerelease observed:** `v1.101.0-rc.1` (2026-09-06)  
**Default upstream branch observed:** `litellm_internal_staging`  
**License:** MIT for content outside the separately licensed `enterprise/` directory  
**Decision status:** research only; no gateway/provider/runtime/model/router adoption decision

## Scope

Task 23 studies LiteLLM as a provider-normalization SDK and credential-bearing AI gateway relevant to ACL/Vera.

The research focuses on:

- Python SDK versus Proxy/AI Gateway deployment boundaries;
- provider request/response translation and capability normalization;
- OpenAI-compatible and local-model provider paths;
- tool calling and structured-output/schema translation;
- router/load-balancing/retry/fallback/cooldown semantics;
- provider-scoped resources and effect-aware fallback;
- fallback authorization and tenant/model access;
- streaming, transport commitment, cancellation and timeout semantics;
- proxy authentication, network destination and credential authority;
- security hardening and current/historical failure evidence;
- operational logging, tracing, spend/routing evidence and redaction;
- distributed cache/cooldown state and deployment identity;
- reproducibility and container/supply-chain identity;
- reusable mechanisms and explicit non-conclusions for ACL/Vera.

Task 23 does **not** deep-research vLLM as an independent project, benchmark local models, select an ACL inference gateway, adopt LiteLLM, change ACL/Vera architecture, or begin Task 24.

---

# Executive assessment

LiteLLM is a high-value ACL reference for the layer between an agent harness and heterogeneous model/provider endpoints. It offers two materially different modes:

1. an in-process Python SDK that translates a common request into provider-specific APIs; and
2. a network AI Gateway/Proxy that additionally owns virtual-key authentication, model access, spend/rate policy, routing, retries/fallbacks, guardrails, logging, MCP/A2A gateways and provider credentials.

That distinction is critical. A gateway with stored provider credentials, configurable outbound destinations, fallback routing and management APIs is an authority-bearing service. It must be qualified as infrastructure, not treated as a transparent formatting shim.

The strongest Task 23 conclusion is:

> LiteLLM's common OpenAI-shaped interface is a translation contract, not proof of behavioral equivalence across providers, models, serving backends, streaming modes, tool/schema paths or retry semantics.

Current source makes this explicit. Provider adapters implement their own supported-parameter declarations, parameter mappings, environment/auth validation, request transforms, URL construction, response transforms, streaming transforms and exceptional retry logic. Some capabilities are emulated rather than passed through natively. Unsupported parameters may raise or, when `drop_params=True`, disappear from the request. A provider capability declaration therefore nominates a test; it does not establish a verified ACL capability profile.

LiteLLM's router contains several unusually valuable mechanisms for ACL:

- attempt identity prevents cyclic fallback replays;
- fallback access can be re-authorized against the caller's key/team/project model permissions;
- provider-scoped resources such as files/batches/fine-tuning IDs block inappropriate cross-provider fallback;
- cooldown decisions reject some caller-attributable failures so one malicious/bad request cannot poison deployment health;
- only server-stamped failed-deployment identity is trusted for cooldown selection;
- deployment cooldown state can be shared through a dual cache and reconciled against Redis TTL.

These mechanisms show that reliable routing requires understanding identity, authorization, resource ownership and state—not merely status-code retry tables.

At the same time, current/open evidence demonstrates why ACL should not outsource authoritative effect/recovery evidence to the gateway:

- open #38142 asks for structured per-attempt routing evidence because final success can hide failed upstream attempts;
- open #38927 shows observability metadata mutation can corrupt retry state and convert a recoverable provider failure into a 400;
- open #38610 shows streaming fallback can commit HTTP 200/message-start before a second failure is known, turning a failure into an error inside an already-successful-looking stream;
- open #37140 reports non-streaming client disconnects do not cancel upstream generation;
- open #35711 plus current source show the legacy `ollama/` streaming path still lacks the non-streaming tool-call reconstruction logic;
- open #32281 shows MCP-to-OpenAI tool translation can be rejected by a strict `hosted_vllm` backend even though other providers may tolerate the malformed shape;
- open #35677 shows structured-output tool emulation can leak its synthetic tool envelope instead of producing the expected bare object.

Security history is also directly relevant. LiteLLM's gateway has had 2026 advisories involving authentication, MCP, host-header routing, code/guardrail surfaces, endpoint override and credential exfiltration. Current source contains substantial hardening: endpoint/credential fields are blocked by default, nested config/metadata is inspected, fallback destination URLs are constrained, auth uses the server's dispatched ASGI route rather than a Host-derived reconstructed route, and server-stamped deployment identity is preferred over caller metadata. Stable `v1.100.0` is newer than the specific fixed versions examined during this task, but exact patch level/configuration remains part of the security profile.

For the user's future 32K local-worker benchmark, LiteLLM should be treated as a candidate **adapter/gateway profile**, not part of the model name. A result such as:

`model = Qwen-X`

is insufficient. A meaningful deployment/benchmark identity would include at least:

`model artifact + serving runtime + LiteLLM revision/container + provider adapter + endpoint mode + tool/schema mode + stream mode + context settings + routing/retry/fallback policy + cache + auth/credential profile`.

The architectural conclusion is not “use LiteLLM.” It is:

> LiteLLM is strong reference material for provider adapters, effect-aware fallback, model-access-aware routing, credential/network hardening, gateway observability and deployment normalization. ACL should still own task/effect identity, idempotency/reconciliation, verified capability profiles, protected policy/verifier state and authoritative acceptance evidence above any gateway.

---

# 1. Current project identity, release and reproducibility

## 1.1 Canonical upstream

Observed at the Task 23 checkpoint:

- repository: `BerriAI/litellm`;
- repository active and not archived;
- observed default branch: `litellm_internal_staging`;
- default-branch revision inspected: `168a0055a244acdcf97c330c52e085ab40b1424c`;
- latest stable release observed: `v1.100.0`, published 2026-09-06;
- prerelease observed: `v1.101.0-rc.1`;
- non-enterprise source is MIT licensed, with `enterprise/` separately licensed.

Primary sources:

- https://github.com/BerriAI/litellm
- https://github.com/BerriAI/litellm/tree/168a0055a244acdcf97c330c52e085ab40b1424c
- https://github.com/BerriAI/litellm/releases/tag/v1.100.0
- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/LICENSE

## 1.2 The default branch is itself a reproducibility warning

The observed default branch is named `litellm_internal_staging`, while public releases use semantic version tags and Docker images.

That does not imply instability by itself, but it makes a general rule obvious:

`package = litellm`

is not enough identity for benchmark, checkpoint, security or production evidence.

### ACL invariant

Record an immutable gateway/runtime identity such as:

- exact LiteLLM commit;
- package version;
- container digest;
- provider adapter/provider mode;
- routing settings;
- database/cache configuration;
- enabled proxy features;
- security-relevant general settings.

## 1.3 Signed release containers are a useful supply-chain pattern

Current stable and prerelease notes state that LiteLLM Docker images are signed with Cosign and recommend verifying against a public signing key pinned to immutable commit `0112e53046018d726492c814b3644b7d376029d0`.

Primary source:

- https://github.com/BerriAI/litellm/releases/tag/v1.100.0

### ACL reuse candidate

A future ACL deployment manifest should prefer:

`immutable image digest + signature verification + source commit`

over a mutable image tag alone.

---

# 2. LiteLLM is two materially different products from an authority perspective

Current README distinguishes:

- **Python SDK:** direct in-process integration;
- **AI Gateway / Proxy:** centralized network service.

Primary source:

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/README.md

The proxy adds authority-bearing functions including:

- virtual keys;
- authentication/authorization hooks;
- team/project/user model access;
- spend/budgets;
- rate limits;
- routing/load balancing;
- retries/fallbacks;
- provider credentials;
- logs/traces;
- guardrails;
- management/configuration routes;
- MCP and A2A gateway surfaces.

### ACL/Vera lesson

Do not use one generic deployment label `litellm`.

At minimum distinguish:

- in-process adapter library;
- localhost-only gateway;
- LAN gateway;
- remotely exposed authenticated gateway;
- gateway with database/Redis state;
- gateway with MCP/A2A/management surfaces.

Each has a different attack surface and failure model.

---

# 3. Provider normalization is explicit translation code

LiteLLM's common interface is implemented through provider-specific transformation classes rather than through one universal provider protocol.

Current `BaseConfig` defines/coordinates behavior such as:

- `get_supported_openai_params`;
- `map_openai_params`;
- `validate_environment`;
- `get_complete_url`;
- `transform_request`;
- `transform_response`;
- streaming behavior;
- provider-specific internal retry on particular HTTP errors;
- developer-role conversion;
- structured-output emulation.

Primary source:

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/llms/base_llm/chat/transformation.py

## 3.1 Common wire shape does not imply common semantics

Two calls can have the same OpenAI-shaped request but differ in:

- supported fields;
- translated parameter meaning;
- tool schema;
- response-format enforcement;
- streaming event shape;
- reasoning/thinking representation;
- token accounting;
- provider error mapping;
- retry behavior;
- timeout/cancellation behavior.

### ACL invariant

Provider normalization is a **behavior-bearing adapter layer** and belongs in benchmark identity.

---

# 4. Capability metadata is advisory until tested

LiteLLM adapters expose supported-parameter/capability information, and broader model metadata contains capability flags.

This is useful for discovery and routing.

It is not sufficient for worker promotion.

## 4.1 `drop_params` changes semantics

Provider/model transforms can reject unsupported parameters with `UnsupportedParamsError` or drop them when configured to do so.

That is operationally convenient, but it creates a dangerous benchmark ambiguity:

- requested strict feature: present;
- adapter silently removes it;
- provider returns a plausible answer;
- harness incorrectly marks the deployment as supporting the feature.

### ACL rule

For required benchmark/authority features, unsupported or dropped parameters must produce an explicit capability failure. Silent degradation cannot retain the same verified profile.

---

# 5. Structured output can be native or emulated

Current base transformation contains a generic structured-output fallback.

When native response-format support is absent, LiteLLM can translate a JSON schema into a synthetic forced tool and mark the request as JSON mode.

Primary source:

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/llms/base_llm/chat/transformation.py

This is a useful compatibility technique, but native constrained decoding and tool-emulated JSON are different capability profiles.

## 5.1 Current open #35677: emulation envelope leakage

Open #35677 reports that the Anthropic Responses API can fall back from native structured output to tool emulation for model names outside a hardcoded allowlist, and the synthetic tool envelope can intermittently leak into `output_text` instead of yielding the expected bare schema object.

Primary source:

- https://github.com/BerriAI/litellm/issues/35677

### ACL fixture

For every structured-output provider profile:

1. validate the final returned object against the authoritative schema;
2. assert no adapter/tool envelope remains;
3. distinguish native schema enforcement from tool/prompt emulation;
4. test streaming and non-streaming separately;
5. pin adapter/model revision.

---

# 6. Ollama illustrates why the adapter path is part of model capability

Task 17 researched Ollama itself. Task 23 only studies LiteLLM's Ollama integration surfaces.

LiteLLM currently has materially different Ollama paths including `ollama/` and `ollama_chat/`.

## 6.1 `ollama_chat/` uses native chat/tool mapping

Current `OllamaChatConfig`:

- maps OpenAI token/sampling fields into Ollama fields;
- maps JSON object/schema response formats into Ollama `format`;
- forwards native tools;
- maps reasoning effort into Ollama `think` behavior;
- transforms Ollama tool/reasoning responses back to the common response shape.

Primary source:

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/llms/ollama/chat/transformation.py

## 6.2 A capability-declaration contradiction exists in current source

`OllamaChatConfig.get_supported_openai_params()` includes `tool_choice`.

But `map_openai_params()` explicitly removes `tool_choice` with the comment that it causes Ollama requests to hang.

That is exactly why ACL cannot equate provider capability metadata with verified behavior.

### Candidate fixture

If a profile claims `tool_choice`, test:

- `auto`;
- required/named tool;
- no-tool;
- one tool and multiple tools;
- streaming/non-streaming.

If the adapter deliberately drops one mode, the profile must record that limitation.

## 6.3 Legacy `ollama/` streaming tool reconstruction remains absent on pinned source

Open #35711 reports that the `ollama/` path emulates function calling through JSON text on `/api/generate`.

The non-streaming response transform recognizes `{name, arguments}` JSON and turns it into an OpenAI-style tool call.

Current pinned source still contains that reconstruction in the non-streaming transform.

Current pinned streaming `OllamaTextCompletionResponseIterator.chunk_parser()` still forwards response text chunks and uses final `finish_reason="stop"`; the inspected iterator contains no equivalent reconstruction into streaming `tool_calls`.

Primary sources:

- https://github.com/BerriAI/litellm/issues/35711
- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/llms/ollama/completion/transformation.py

### Status

This Task 23 finding is current-source corroborated, not merely an old issue report.

### ACL lesson

`model + LiteLLM + Ollama`

is still insufficient identity.

At least distinguish:

- `ollama/` versus `ollama_chat/`;
- streaming versus non-streaming;
- native tool transport versus emulated JSON reconstruction.

---

# 7. OpenAI-compatible serving does not eliminate adapter behavior

LiteLLM includes `hosted_vllm` as a provider identity and has OpenAI-compatible transformation special cases such as reasoning-field normalization.

Task 23 does **not** research vLLM itself; this section is limited to LiteLLM's adapter behavior.

## 7.1 Open #32281: MCP tool conversion rejected by strict hosted_vllm schema

Open #32281 reports a LiteLLM MCP-to-OpenAI tool conversion path where tools were flattened rather than wrapped under the required `function` field.

A strict `hosted_vllm` OpenAI-compatible server rejected the malformed tool array with a 400.

Primary source:

- https://github.com/BerriAI/litellm/issues/32281

### ACL lesson

“OpenAI-compatible” is not a universal conformance level.

A lenient backend can hide an invalid adapter transform that a stricter backend rejects.

Require schema-contract fixtures against each exact serving endpoint.

---

# 8. Router identity is broader than model name

The current Router contains configurable state including:

- model/deployment list;
- routing strategy;
- retry policy;
- fallback graph;
- context-window fallback;
- allowed failures;
- cooldown time;
- timeouts;
- deployment affinity;
- health state;
- cache/Redis state;
- access checks.

Primary sources:

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/router.py
- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/types/router.py

### ACL deployment identity

A routed benchmark should preserve:

`logical model group + candidate deployments + deployment IDs + strategy + retry policy + fallback graph + cooldown policy + context policy + affinity policy + cache profile`.

Otherwise two executions nominally using the same model may have been served by different providers/backends.

---

# 9. Fallback attempts have explicit request-local identity

Current fallback code carries an `AttemptedFallbackTargets` structure for the logical request.

Fallback attempt keys distinguish:

- a bare model group;
- an equivalent `{model: name}` entry;
- a materially different fallback object carrying overrides;
- retargeting inside the same model group.

A serialized target is hashed so large overrides do not require holding a second full payload copy.

Primary source:

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/router_utils/fallback_event_handlers.py

## 9.1 Cycles are treated as attempts, not graph paths

The current source explicitly says shared attempt state prevents a cyclic fallback graph or re-walked client fallback list from retrying one deterministic failure once per path.

### ACL reuse candidate

Give retries/fallbacks durable/request-local attempt identity and bounded attempt counts.

Do not allow graph topology to multiply one failed logical action indefinitely.

---

# 10. Fallback must respect resource ownership

This is one of LiteLLM's strongest Task 23 mechanisms.

Current fallback code identifies provider-scoped resource operations involving examples such as:

- files;
- batches;
- fine-tuning jobs.

A resource ID issued under one provider's credentials cannot be assumed meaningful under another provider/model group.

The current code therefore blocks inappropriate cross-model-group fallback when a request references provider-scoped resources.

It also blocks cross-group fallback for some resource-creation calls because doing so could silently create the resource in the wrong provider account and return an ID unusable by later calls against the originally requested provider.

Primary source:

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/router_utils/fallback_event_handlers.py

## 10.1 ACL generalization

Classify operations before retry/fallback:

- stateless/replay-safe inference;
- read of provider-scoped object;
- creation of provider-scoped object;
- externally effect-bearing mutation;
- ambiguous effect after transport loss.

Cross-provider fallback is safe only when semantic/effect/resource equivalence is demonstrated.

---

# 11. Fallback authorization can be rechecked

Router-level fallbacks may be configured by the operator after initial request authentication rather than supplied directly by the caller.

Current `fallback_model_access.py` provides a proxy fallback-access predicate that reuses key/team/project model authorization before a fallback target is attempted.

It is controlled by `general_settings.enforce_fallback_model_access`.

Primary source:

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/proxy/auth/fallback_model_access.py

## 11.1 Important configuration boundary

This mechanism is **opt-in**.

When enforcement is enabled and a token is available, authorization lookup errors fail closed for that fallback.

### ACL rule

A reliability feature must never widen caller authority.

A fallback target should be callable only if the authenticated principal could call that target under current policy.

For ACL this should be mandatory structural behavior, not an optional compatibility setting.

---

# 12. Deployment health must distinguish provider failure from caller-induced failure

Current fallback/cooldown logic contains several sophisticated safeguards.

Examples observed:

- a generic API call returning 404 for a caller-supplied object ID is not automatically treated as deployment failure;
- a 408 caused by a caller-supplied extremely short `x-litellm-timeout` does not automatically cool the deployment;
- fallback cooldown trusts a server-stamped `failed_deployment_id` rather than arbitrary caller metadata;
- client-side-credential calls can use dynamic deployment identity so one tenant's bad credentials do not cool the shared deployment for other tenants.

Primary sources:

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/router_utils/fallback_event_handlers.py
- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/router.py

### ACL reuse candidate

Health/quarantine decisions require trusted causal evidence.

Do not allow attacker/user-controlled request fields to poison shared worker/model/backend health state.

---

# 13. Cooldown is distributed operational state, not durable task state

Current `CooldownCache` uses the Router's dual cache and keeps local in-memory acceleration.

It stores:

- deployment ID-derived key;
- masked exception text;
- status;
- timestamp;
- cooldown duration;
- TTL.

It also contains logic to correct an in-memory TTL after a Redis value has been promoted with an inappropriate/default local TTL, forcing periodic Redis rechecks.

Primary source:

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/router_utils/cooldown_cache.py

### ACL lesson

Distributed router-health state is useful coordination state.

It is not:

- task checkpoint state;
- effect settlement evidence;
- model capability proof;
- permanent backend health truth.

Record cache backend/profile when router behavior is part of a benchmark.

---

# 14. Retry/fallback state must not be mutable observability state

Open #38927 is a high-value state-isolation fixture.

The issue reproduces a path where a Langfuse request header changes shared retry metadata `tags` from the list shape expected by the router into a string. After the first provider attempt fails, the retry/fallback setup can then crash while appending a credential tag, returning an internal 400 instead of failing over.

Primary source:

- https://github.com/BerriAI/litellm/issues/38927

Task 23 also inspected current pinned `LangFuseLogger.add_metadata_from_header`.

It still writes `langfuse_*` header values directly into the supplied metadata mapping and returns that mapping.

Primary source:

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/integrations/langfuse/langfuse.py

The issue is still open. Task 23 did not execute its reproduction against the pinned build, so the report does not claim a fresh end-to-end reproduction.

### ACL fixture

Create a frozen canonical logical request plus separate per-attempt and observability projections.

A logging callback must not be able to mutate:

- authorization identity;
- route selection;
- retry counters;
- provider credentials;
- tool schema;
- effect parameters.

---

# 15. Final success can hide failed attempts

Open #38142 requests structured per-attempt routing evidence.

The issue accurately distinguishes several reasons that requested and served model identities may differ:

- normal load balancing;
- aliases;
- weighted routing;
- experiments;
- capacity/cost/compliance routing;
- actual retry/fallback.

Therefore this inference is invalid:

`requested_model != served_model` -> `fallback happened`.

The useful evidence is the actual ordered attempt sequence.

Primary source:

- https://github.com/BerriAI/litellm/issues/38142

### Candidate ACL route-attempt record

For each provider/model attempt record:

- logical request ID;
- attempt ID/order;
- deployment ID;
- provider/backend/model;
- initial/retry/fallback classification;
- start/end/latency;
- outcome;
- normalized error/status;
- response/request correlation IDs;
- selected routing policy version;
- final served attempt.

### Important boundary

Gateway routing telemetry still does not replace ACL task/effect settlement evidence.

---

# 16. Provider error normalization remains a live interoperability problem

Open #33371 asks LiteLLM to expose the error/retryability classification it already partially uses internally as a stable machine-readable contract.

Primary source:

- https://github.com/BerriAI/litellm/issues/33371

The reported need is directly relevant to ACL because downstream agent frameworks otherwise reimplement brittle provider-message regexes.

### ACL rule

Keep two concepts separate:

1. provider/gateway error classification;
2. ACL decision whether replay/fallback is safe for this task/effect.

A provider can say `retryable=true` while ACL must still say `do_not_replay` because an external effect may already have happened.

---

# 17. Streaming has an irreversible transport-commit boundary

Open #38610 reproduces a double-failure case on `/v1/messages` streaming.

The primary failure triggers fallback. The fallback sends `HTTP 200` and a `message_start`, then fails before useful content. At that point the HTTP status has already been committed, so the later 503 is delivered as an error event inside the stream.

Primary source:

- https://github.com/BerriAI/litellm/issues/38610

## 17.1 ACL/Vera invariant

Separate at least:

- upstream attempt started;
- response headers committed;
- first semantic content emitted;
- logical response completed;
- durable result recorded;
- effect settled.

`HTTP 200`
and
`stream started`
are not equivalent to task success.

## 17.2 Retry clients can behave differently after transport commit

The issue specifically notes that SDK status-code retries cannot react to a later stream error as they would to an initial HTTP 503.

Therefore streaming/non-streaming must be separate capability/reliability fixtures.

---

# 18. Client disconnect is not cancellation settlement

Open #37140 reports that non-streaming proxy requests can continue upstream generation after the client disconnects, while the streaming chat path has separate cancellation handling.

Primary source:

- https://github.com/BerriAI/litellm/issues/37140

### ACL rule

Distinguish:

- client abandoned response;
- proxy coroutine cancelled;
- upstream provider request cancelled;
- model generation actually stopped;
- GPU/scheduler resources released;
- external effect cancelled/settled.

A disconnected HTTP client proves only the first condition.

---

# 19. Proxy authentication and model access are real policy layers

Current proxy auth source describes checks spanning:

- caller/model access;
- team/key/user relationships;
- budgets;
- model access groups;
- route permission;
- object permissions;
- end-user limits;
- tool-related policy surfaces.

Primary sources:

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/proxy/auth/auth_checks.py
- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/proxy/auth/model_checks.py

## 19.1 Routing handles are not ACL authority identity

LiteLLM key/team/project/model identities are valuable gateway authorization context.

They do not automatically equal:

- ACL user/principal identity;
- ACL project/task identity;
- Vera human identity;
- external-effect authorization identity.

A future ACL integration should authenticate at the ACL/Vera boundary, then issue a narrow gateway credential or workload identity appropriate to the task.

---

# 20. Endpoint selection and credentials form one authority domain

This is a major LiteLLM security lesson.

A proxy holding operator provider credentials can become a credential-exfiltration/SSRF primitive if an authenticated caller can also redirect the outbound request destination.

Current `auth_utils.py` contains substantial explicit hardening.

Primary source:

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/proxy/auth/auth_utils.py

Observed protections include:

- default banned request fields such as `api_base`/`base_url` and provider identity/endpoint selectors;
- coverage of nested `extra_body` and embedding configuration;
- coverage of metadata containers used by observability callbacks;
- fallback-target validation;
- restrictions on URL-valued fallback destinations;
- explicit admin opt-ins for client-side configurable credential/endpoint behavior;
- request safety before deeper auth/database operations.

## 20.1 Current source records the historical failure mode

Current comments in `is_request_body_safe` state that an older implicit caller-controlled path allowed a supplied API key to bypass the blocklist, turning missing blocklist entries into SSRF/credential-exfiltration risk.

Current code states that this implicit bypass was removed.

## 20.2 GitHub advisory evidence

GitHub advisory `GHSA-3cv6-jpf6-8222` / CVE-2026-84377 describes authenticated SSRF/provider-credential exfiltration via unvalidated request-body routing parameters and lists fixes in the 1.9x release lines including 1.96.2.

Primary source:

- https://github.com/BerriAI/litellm/security/advisories/GHSA-3cv6-jpf6-8222

Stable Task 23 `v1.100.0` is later than those fixed versions.

### ACL/Vera invariant

Outbound destination authorization and outbound credential selection must be evaluated together.

Never let lower-trust request data independently choose both:

- where a trusted service sends a request; and
- which trusted credential it attaches.

---

# 21. Security checks must inspect the value where it is actually consumed

Current auth hardening explicitly walks nested structures because provider adapters and logging integrations consume fields from places other than the root request object.

Examples include:

- `extra_body`;
- embedding configuration;
- `metadata`;
- `litellm_metadata`;
- encoded multipart metadata;
- fallback target objects.

### ACL generalization

Security validation belongs at canonicalization/authority boundaries and should operate on the final normalized effect request.

A root-level JSON schema alone is insufficient if nested adapter/config payloads can reach credential, URL, tool or logging code.

---

# 22. Route identity must come from server dispatch, not attacker-influenced reconstruction

Current `get_request_route()` prefers ASGI `scope["path"]` and documents why: a malformed Host header can affect Starlette URL reconstruction so `request.url.path` differs from the path FastAPI actually dispatched.

Primary source:

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/proxy/auth/auth_utils.py

This aligns with GitHub-reviewed advisory `GHSA-4xpc-pv4p-pm3w` / CVE-2026-49468, which describes a Host-header route/auth mismatch fixed in later releases.

Primary source:

- https://github.com/advisories/GHSA-4xpc-pv4p-pm3w

### ACL rule

Authorization should bind to the server's authoritative parsed action/route/tool identity, not to a user-controlled textual representation of it.

---

# 23. MCP is an additional credential/tool authority surface

Task 15 already deep-researched MCP itself.

Task 23 only records LiteLLM-specific implications.

LiteLLM Proxy can act as an MCP gateway, exposing configured server tools through its own API/auth surface.

The 2026 security history includes GitHub-reviewed MCP vulnerabilities, including authentication-bypass and command-execution classes in older versions.

Example reviewed advisory:

- https://github.com/advisories/GHSA-7488-6r32-c95q

That advisory states an OAuth2 passthrough fallback could allow a fabricated bearer token to reach MCP tooling and was fixed in `1.84.0`.

### Task 23 boundary

Stable `v1.100.0` is newer than the cited fixed version. The lesson is architectural/security-patch identity, not that the current release is vulnerable to the same issue.

### ACL/Vera rule

Gateway authentication does not make every configured MCP server/tool trustworthy. Retain ACL-owned tool identity, per-effect authorization and network/credential policy.

---

# 24. Observability is a privileged data plane

LiteLLM integrates with many logging/tracing systems and carries rich standard logging payloads.

Useful information can include:

- provider/model/deployment;
- timing;
- request/response;
- tools;
- token usage;
- spend;
- routing data;
- errors;
- metadata.

This is valuable operational evidence.

It is also a data-exfiltration surface.

Current release notes include repeated credential-redaction and logging-boundary fixes, including current prerelease work to redact credential kwargs and nested `extra_body` values.

Primary sources:

- https://github.com/BerriAI/litellm/releases/tag/v1.100.0
- https://github.com/BerriAI/litellm/releases/tag/v1.101.0-rc.1

## 24.1 Logging must not own routing state

Open #38927 demonstrates the stronger lesson: observability code should not mutate execution state at all.

### ACL/Vera rule

Maintain separate:

- canonical execution/effect state;
- immutable/frozen logging projection;
- redacted operator telemetry;
- verifier evidence;
- user-facing audit record.

---

# 25. Current routing evidence is useful but not sufficient as an ACL decision ledger

LiteLLM can expose call IDs, model/deployment information, retry/fallback counts, fallback errors, cost/spend and tracing data.

Open #38142 shows the remaining per-attempt linkage gap.

Even a future complete route-attempt log would still answer primarily:

`what did the gateway try?`

ACL also needs:

`why was this effect authorized?`
`what project/task/effect did it belong to?`
`could replay be safe?`
`did the external effect settle?`
`did independent verification accept it?`

Therefore gateway telemetry should feed, not replace, ACL's effect/decision evidence.

---

# 26. Cost/context/capability metadata are useful discovery state, not ground truth

LiteLLM maintains model/provider metadata for capabilities, context windows and costs and uses those values for routing/pre-call behavior.

This is useful infrastructure.

It also changes over time and can lag a provider/runtime/model configuration.

Current prerelease notes, for example, include a fix making context-window pre-call checks count tool definitions and Anthropic system prompts.

Primary source:

- https://github.com/BerriAI/litellm/releases/tag/v1.101.0-rc.1

### ACL 32K benchmark rule

The benchmark should provide/measure its own intended and realized context evidence rather than infer 32K capability solely from LiteLLM's model map or pre-call estimator.

Record:

- requested context;
- gateway-estimated prompt tokens;
- runtime's realized context/KV configuration;
- actual truncation/rejection behavior.

---

# 27. Cache hits and fresh inference are different evidence

LiteLLM supports response/prompt/semantic caching paths.

For an agent benchmark, a cache hit can make latency, provider invocation and sometimes output-repeatability look better than the actual runtime.

### ACL rule

Every inference/result record should identify:

- cache enabled/disabled;
- cache backend/scope;
- cache hit/miss;
- provider attempt actually made or not made.

Unless explicitly benchmarking cache behavior, model capability trials should avoid hidden cache reuse.

---

# 28. Current/fixed failure matrix

| Surface | Evidence | Task 23 classification | ACL/Vera lesson |
|---|---|---|---|
| `ollama/` streaming tool call | open #35711 + pinned source | current-source corroborated | streaming and non-streaming are separate provider capabilities |
| `ollama_chat` `tool_choice` | pinned source drops it despite declaration | current-source behavior | capability metadata is advisory until tested |
| MCP -> hosted_vllm tool shape | open #32281 | open/version-scoped; no fresh runtime reproduction | strict backend schema tests catch adapter normalization bugs |
| Anthropic structured-output emulation | open #35677 | open/version-scoped | native and emulated schema enforcement are distinct |
| retry + Langfuse tags | open #38927 + current header-mutation source | open/current-source seam; no fresh end-to-end reproduction | observability cannot mutate retry state |
| per-attempt routing evidence | open #38142 | current design/evidence gap | final success is not full route evidence |
| structured provider error contract | open #33371 | current RFC gap | error taxonomy and replay authority are separate |
| `/v1/messages` double-failure stream | open #38610 on v1.100.0-era code | current stable-version fixture | stream/HTTP commitment precedes semantic success |
| non-streaming disconnect cancellation | open #37140 | current open operational fixture | client disconnect != upstream settlement |
| request-body routing SSRF/key exfil | GHSA-3cv6-jpf6-8222 + current hardening | fixed historical security fixture for stable v1.100.0 | endpoint and credential authority are coupled |
| Host-header auth route mismatch | GHSA-4xpc-pv4p-pm3w + current ASGI path source | fixed historical security fixture | auth must use authoritative dispatch identity |
| MCP OAuth passthrough auth bypass | GHSA-7488-6r32-c95q | fixed historical security fixture | protocol auth fallback must fail closed |

---

# 29. Candidate ACL/Vera invariants derived from Task 23

1. Provider gateway/adapter identity is part of model-runtime identity.
2. LiteLLM SDK and LiteLLM Proxy are different authority/deployment profiles.
3. A common API shape does not establish cross-provider semantic equivalence.
4. Capability metadata nominates a test; it does not pass the test.
5. Silent dropping of a required parameter invalidates the requested capability profile.
6. Native structured output and tool/prompt-emulated structured output are separate profiles.
7. Validate final structured output against ACL's authoritative schema after provider/gateway transforms.
8. Tool calling must be tested independently in streaming and non-streaming modes.
9. Exact local-provider prefix/adapter path is behavior-bearing (`ollama/` != `ollama_chat/`).
10. “OpenAI-compatible” server identity does not imply identical schema tolerance/stream semantics.
11. Fallback attempts require stable bounded identity to prevent cycles/repeated deterministic failures.
12. Reliability fallback must never widen authenticated caller authority.
13. Cross-provider fallback must preserve provider-scoped resource/effect semantics or be forbidden.
14. External resource creation cannot be transparently moved to another provider if returned IDs are provider/account scoped.
15. Provider/gateway `retryable` does not imply ACL effect replay is safe.
16. Caller-attributable failures should not poison shared deployment health.
17. Shared health/cooldown state must use trusted server-derived deployment identity, not caller metadata.
18. One tenant's dynamic credentials must not poison a shared deployment's health for other tenants.
19. Distributed cooldown/cache state is operational coordination, not durable task/effect state.
20. Observability callbacks cannot mutate canonical request, routing, authorization or effect state.
21. Every routed logical request should preserve ordered per-attempt identity/outcome.
22. Final successful response does not prove the preferred/initial upstream path was healthy.
23. HTTP response commitment, stream start, semantic completion and durable result are separate lifecycle states.
24. Client disconnect, task cancellation, provider cancellation and computation termination are separate states.
25. Endpoint selection and trusted credential selection are one combined authority decision.
26. Security validation must inspect nested/normalized fields where adapters actually consume them.
27. Authorization uses authoritative parsed route/tool/action identity rather than attacker-controlled reconstructed text.
28. Gateway virtual key/team/project identities do not replace ACL/Vera principal/task/effect identities.
29. Gateway MCP/A2A interoperability does not replace ACL/Vera tool/server trust policy.
30. Gateway logs/traces are operational evidence, not independent acceptance or effect settlement.
31. Cache hit/miss is benchmark/result evidence.
32. Model capability/context/cost maps are mutable metadata and must not replace measured runtime evidence.
33. Exact gateway security patch/container digest/configuration belongs in deployment qualification.
34. Signed immutable container/source identity is preferable to mutable tags.
35. Provider error classification is separate from application/ACL replay authorization.
36. Retry/fallback configuration is part of benchmark identity because it can change which provider actually answered.
37. Routing strategy and deployment list are part of benchmark identity.
38. A final answer must retain served deployment/provider evidence when routing can vary.
39. Gateway-held provider credentials should be narrower than the gateway host's ambient environment where possible.
40. Worker/model code should never receive gateway administrative credentials merely to invoke a model.

---

# 30. High-value future regression fixtures

## Fixture 1 — required parameter silently dropped

Request a feature the target adapter cannot support.

Expected ACL behavior:

- explicit unsupported-capability failure;
- no false promotion from a plausible fallback answer.

## Fixture 2 — claimed tool-choice support

Use a profile whose adapter declares tool choice but transforms/removes it.

Expected:

- benchmark detects realized semantics, not capability flag.

## Fixture 3 — local streaming tool call

Same local model, same tool schema, stream false vs true.

Expected:

- both either produce valid canonical tool calls or profile records mode-specific limitation.

## Fixture 4 — structured-output emulation envelope

Force adapter emulation rather than native schema support.

Expected:

- final output validates against authoritative schema;
- no synthetic tool wrapper leaks.

## Fixture 5 — strict OpenAI-compatible backend

Send tool schemas through a strict server implementation.

Expected:

- adapter produces valid canonical wire shape rather than relying on provider leniency.

## Fixture 6 — fallback cycle

Configure `A -> B -> A`.

Expected:

- bounded attempt identity prevents repeated path enumeration.

## Fixture 7 — unauthorized fallback target

Caller can invoke A but not B; router has `A -> B` fallback.

Expected:

- fallback B is not attempted;
- reliability policy cannot widen authority.

## Fixture 8 — provider-scoped object

Create/read a provider-scoped file or batch ID then induce primary failure.

Expected:

- no fallback to an incompatible provider/account.

## Fixture 9 — caller-induced timeout health poisoning

Caller selects extremely short timeout against healthy deployment.

Expected:

- request fails;
- shared deployment is not globally cooled solely from caller-induced 408.

## Fixture 10 — caller-supplied fake deployment metadata

Attempt to influence cooldown target through metadata.

Expected:

- only trusted server-stamped deployment identity affects health state.

## Fixture 11 — observability mutation across retry

Inject logging headers/metadata then fail the first attempt.

Expected:

- logging projection cannot mutate request/retry types or routing state.

## Fixture 12 — final success after failed preferred route

Primary fails, fallback succeeds.

Expected evidence:

- final success;
- both attempts recorded with deployment/provider/outcome;
- preferred path failure remains visible.

## Fixture 13 — double failure before streaming content

Primary and fallback both fail before semantic output.

Expected:

- no misleading successful lifecycle evidence where transport permits a clean error;
- attempt counts accurate.

## Fixture 14 — disconnect non-streaming generation

Disconnect client during long local generation.

Expected:

- cancellation ownership/state visible;
- test distinguishes proxy cancellation from backend termination.

## Fixture 15 — endpoint + stored credential exfiltration attempt

Authenticated low-privilege caller supplies nested/root/fallback destination overrides toward loopback/private/attacker host.

Expected:

- blocked unless an explicit authorized deployment capability permits it;
- stored provider credential never follows an unauthorized destination.

## Fixture 16 — Host/header route mismatch

Use malformed/hostile Host while addressing a protected route.

Expected:

- auth decision follows authoritative server-dispatched route.

## Fixture 17 — cache contamination

Repeat benchmark request under cache-enabled path.

Expected:

- cache hit is explicitly recorded and cannot be miscounted as a fresh model trial.

## Fixture 18 — context estimate with tools/system prompt

Near context limit with large system prompt/tool schemas.

Expected:

- gateway estimation and actual serving runtime behavior are compared;
- hidden truncation/fallback invalidates benchmark equivalence.

---

# 31. Reuse candidates for later build-vs-reuse analysis

## High-value pattern candidates

### Provider transform interface

LiteLLM's explicit provider transformation surface is useful reference for ACL's eventual inference-adapter contract.

### Effect/resource-aware fallback

The provider-scoped resource guard is one of the strongest directly reusable conceptual patterns in Task 23.

### Fallback authorization hook

Re-authorizing configured fallback targets against the original caller is strong precedent.

### Trusted deployment-health identity

Server-stamped deployment identity and caller-attributable-error filtering are useful for any shared local-model scheduler.

### Attempt-cycle prevention

Request-local attempted-target identity is a simple, deterministic reliability mechanism.

### Network/credential hardening

The current nested request-field/fallback destination block strategy and dispatch-route identity fixes are important gateway-security references.

### Signed container provenance

Cosign verification plus immutable source/digest identity is useful operational practice.

## Candidate direct dependency question

LiteLLM may later be attractive if ACL needs one or more of:

- many provider adapters;
- one OpenAI-compatible gateway in front of local/cloud models;
- centralized credentials;
- quotas/budgets;
- provider routing/fallback;
- MCP/A2A gateway translation.

But direct adoption should be compared against a much smaller ACL-owned local inference adapter if the user's near-term Worker Lab only needs a few local runtimes.

Importing a feature-rich credential-bearing gateway adds:

- a larger security patch surface;
- translation behavior to qualify;
- database/cache state;
- authorization configuration;
- routing complexity;
- operational telemetry concerns.

That tradeoff belongs to later synthesis, not Task 23.

---

# 32. Explicit non-conclusions

Task 23 does **not** establish that:

- ACL should adopt LiteLLM;
- LiteLLM should replace direct Ollama/llama.cpp/vLLM integration;
- LiteLLM is unsafe in current stable form;
- every 2026 historical advisory still affects v1.100.0;
- every open issue reproduces on pinned commit `168a0055...`;
- `hosted_vllm` findings establish anything about vLLM independent of LiteLLM;
- Ollama's underlying runtime is at fault for LiteLLM adapter defects;
- OpenAI-compatible providers are interchangeable;
- routing/fallback should be enabled in the future benchmark;
- cloud providers should be used for the user's local Worker Lab;
- LiteLLM's cost/context/capability metadata is authoritative runtime truth;
- LiteLLM telemetry is sufficient ACL verification evidence;
- a successful fallback is equivalent to one healthy/verified inference path;
- gateway authentication alone is sufficient Vera/ACL effect authorization.

No dependency, provider, model, gateway, router, cache, credential store, MCP/A2A, sandbox or benchmark winner was selected.

---

# 33. Primary source ledger

## Canonical project/release

- https://github.com/BerriAI/litellm
- https://github.com/BerriAI/litellm/tree/168a0055a244acdcf97c330c52e085ab40b1424c
- https://github.com/BerriAI/litellm/releases/tag/v1.100.0
- https://github.com/BerriAI/litellm/releases/tag/v1.101.0-rc.1
- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/README.md
- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/LICENSE

## Provider/translation/local paths

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/llms/base_llm/chat/transformation.py
- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/llms/ollama/chat/transformation.py
- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/llms/ollama/completion/transformation.py
- https://github.com/BerriAI/litellm/issues/35711
- https://github.com/BerriAI/litellm/issues/32281
- https://github.com/BerriAI/litellm/issues/35677

## Router/retry/fallback/state

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/router.py
- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/router_utils/fallback_event_handlers.py
- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/router_utils/cooldown_cache.py
- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/proxy/auth/fallback_model_access.py
- https://github.com/BerriAI/litellm/issues/38142
- https://github.com/BerriAI/litellm/issues/38927
- https://github.com/BerriAI/litellm/issues/33371

## Streaming/cancellation

- https://github.com/BerriAI/litellm/issues/38610
- https://github.com/BerriAI/litellm/issues/37140

## Proxy auth/network/security

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/proxy/auth/auth_utils.py
- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/proxy/auth/auth_checks.py
- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/proxy/auth/model_checks.py
- https://github.com/BerriAI/litellm/security/advisories/GHSA-3cv6-jpf6-8222
- https://github.com/advisories/GHSA-4xpc-pv4p-pm3w
- https://github.com/advisories/GHSA-7488-6r32-c95q

## Observability

- https://github.com/BerriAI/litellm/blob/168a0055a244acdcf97c330c52e085ab40b1424c/litellm/integrations/langfuse/langfuse.py
- https://github.com/BerriAI/litellm/releases/tag/v1.100.0
- https://github.com/BerriAI/litellm/releases/tag/v1.101.0-rc.1

---

# Stop condition

Task 23 is complete only after this report, the Task 23 catalog append, `RESEARCH_STATE.md` and `watchlist.md` are combined into one clean research commit directly above the finalized Task 22 checkpoint.

Task 23 does not authorize Task 24. **vLLM remains next-task-only.**
