# Model Context Protocol (MCP) — Task 15 Deep Research

**Research date:** 2026-09-06  
**Research target:** Model Context Protocol current specification and directly relevant official extensions  
**Canonical core repository:** `modelcontextprotocol/modelcontextprotocol`  
**Core revision inspected:** `e76e9c572c6f2bfcb730357101acc90f2f802e02` (2026-09-04)  
**Current specification revision inspected:** `2026-07-28`  
**Tasks extension repository:** `modelcontextprotocol/ext-tasks`  
**Tasks extension revision inspected:** `9263312d11a682ac83f83fe84794d4627efd22f5` (2026-09-04)  
**Decision status:** research only; no adoption/fork/dependency decision

## Scope

This task studies MCP as an interoperability and authority-boundary protocol for ACL/Vera, not as an agent runtime replacement. The research focuses on:

- current protocol lifecycle and capability negotiation;
- tools, resources and prompts as distinct primitive/trust surfaces;
- Tasks and long-running operations;
- cancellation, progress, errors and subscriptions;
- server/client trust, authorization and credentials;
- filesystem/root/network implications;
- transport, reconnect, retry and identity semantics;
- specification/SDK versioning and extension compatibility;
- current security guidance and failure/ambiguity surfaces;
- local-first implications for ACL/Vera;
- reusable mechanisms and candidate invariants.

Task 15 does **not** research Goose, choose a framework winner, redesign ACL/Vera governance, or authorize runtime/model work.

---

## Executive assessment

MCP remains a high-value ACL/Vera interoperability reference, but the most important finding is that **the current MCP is substantially different from the stateful protocol many older integrations describe**.

The `2026-07-28` revision intentionally changed MCP into a stateless request/response protocol:

- no `initialize`/`initialized` handshake in the modern era;
- no protocol-level session ID;
- each request carries protocol version and client capability information;
- application state spanning calls is represented by explicit handles/IDs rather than hidden transport session state;
- long-running work moved to the optional Tasks extension;
- server-to-client interaction moved toward Multi Round-Trip Requests (MRTR);
- resumable SSE / `Last-Event-ID` was removed;
- Roots, Sampling and Logging were deprecated;
- legacy HTTP+SSE was deprecated;
- authorization was materially hardened;
- extension negotiation became first class.

For ACL/Vera, this is a strong external validation of several patterns already emerging from Tasks 5–14:

1. **Transport identity is not task/run/effect identity.**
2. **Hidden connection/session state should not be authoritative application state.**
3. **Long-running operations need explicit durable handles.**
4. **A protocol cancellation acknowledgment is not execution/effect settlement.**
5. **Remote tool metadata, prompts, resources and discovery instructions remain untrusted content even when syntactically valid.**
6. **Service authentication and authorization do not automatically authorize a model-selected effect.**
7. **Credential/token authority should be audience bound and service scoped; token passthrough is structurally unsafe.**
8. **MCP should sit below ACL/Vera governance as an interoperability boundary, not become the global scheduler, memory owner, verifier, or effect ledger.**

The new revision also exposes migration and compatibility risk: “MCP support” is too broad. A reliable compatibility profile needs at least protocol era/version, transport, SDK implementation/revision, extension set, auth mode and task/tool/resource semantics.

---

# 1. Project health and current-generation boundary

## 1.1 Current canonical project

Observed:

- canonical repository: `modelcontextprotocol/modelcontextprotocol`;
- public and active;
- core revision inspected: `e76e9c572c6f2bfcb730357101acc90f2f802e02` from 2026-09-04;
- current released specification: `2026-07-28`;
- the official release post is authored by lead maintainers David Soria Parra and Den Delimarsky;
- the release describes `2026-07-28` as MCP's move from a bidirectional stateful protocol to a stateless request/response protocol.

The four Tier 1 SDKs named by the release are:

- TypeScript;
- Python;
- Go;
- C#.

The release states all four supported `2026-07-28` at GA. Rust support was described as beta.

### ACL implication

Protocol version and SDK/runtime revision belong in compatibility evidence. A client saying “supports MCP” is not enough to infer which lifecycle generation it implements.

Primary sources:

- https://github.com/modelcontextprotocol/modelcontextprotocol
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/blog/content/posts/2026-07-28-spec-ga/index.md
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/changelog.mdx

---

# 2. Stateless core and explicit state identity

## 2.1 No protocol-level session in the current era

The current base protocol states that servers **must not** infer protocol version, client capabilities, client identity or application state from previous requests. State spanning multiple requests needs an explicit identifier or handle in protocol/application data.

A persistent stdio process or an open HTTP connection is explicitly **not** a conversation/session identity.

This is materially different from the `2025-11-25` and earlier “legacy” era, which used an `initialize` handshake and session-oriented transport behavior.

### ACL candidate invariant

Keep these identities separate:

- transport connection;
- MCP JSON-RPC request;
- MCP server/service;
- MCP task handle;
- ACL project;
- ACL logical task;
- ACL run/attempt;
- ACL effect/idempotency record;
- Vera conversation/memory identity.

A long-lived socket/process must never become implicit authority for any of the higher-level identities.

Primary sources:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/index.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/versioning.mdx

## 2.2 Modern and legacy protocol eras

Current versioning documentation distinguishes:

- **modern**: `2026-07-28` and later; per-request metadata;
- **legacy**: `2025-11-25` and earlier; initialization handshake;
- **dual-era** implementations: support both.

Unsupported versions are represented explicitly rather than silently interpreted. Extension capabilities are also advertised per request.

### ACL lesson

Protocol fallback is behavior-bearing configuration. If ACL ever supports both eras, record:

- requested version;
- realized version;
- transport;
- capability/extension set;
- fallback reason;
- server implementation identity/evidence.

Do not silently fall back from modern stateless semantics to legacy stateful semantics while preserving the same “capability verified” label.

---

# 3. Host/client/server trust topology

MCP's architecture separates:

- **host**: application coordinating one or more MCP clients, user consent/security, LLM integration and cross-server context;
- **client**: one protocol connection/logical endpoint to one server;
- **server**: focused provider of tools/resources/prompts.

The architecture intentionally keeps broader application conversation/context out of individual MCP servers unless the host chooses to provide it.

### ACL/Vera relevance

This maps well to Vera/ACL if the host remains authoritative:

- Vera/ACL owns policy, task scope, credential grants, memory and cross-service orchestration;
- MCP clients/adapters expose server capabilities under that policy;
- MCP servers do not become project/global truth;
- a model can propose tool use, but host policy still authorizes the actual action.

Primary source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/architecture/index.mdx

---

# 4. Primitive boundaries: tools, resources and prompts

## 4.1 Tools: model-controlled protocol primitive, not authority

The spec characterizes tools as model-controlled. Hosts can implement stricter human/policy gating.

Important current details:

- tool lists may vary by per-request authorization context;
- tool names are unique only within one server;
- aggregating clients/proxies can face collisions;
- `serverInfo.name` is not guaranteed globally unique;
- tool annotations are explicitly untrusted unless the server itself is trusted;
- tool input/output schemas use JSON Schema;
- `x-mcp-header` can project selected primitive parameters into routing headers.

### ACL candidate identity

An authority-bearing MCP tool identity should include more than `tool.name`, for example:

`server/trust identity + protocol version + tool name + tool-definition/schema digest + capability profile`

Tool collisions should be resolved before model exposure, preferably by fail-closed canonical identity rather than “last/current server wins.”

### `x-mcp-header` boundary

Header projection can be useful for gateways, rate limiting and routing, but the annotation originates in server-provided tool schema. ACL should allow only policy-approved header names/uses and must not let an untrusted MCP server invent privileged routing/authorization headers.

Primary source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/server/tools.mdx

## 4.2 Resources: application-driven context, still untrusted content

Resources are application-driven rather than model-selected primitives. They can represent files, documents, schemas or network-addressable content.

Current considerations:

- resource lists/reads can vary with authorization context;
- direct `https://` resource references can cause client-side fetches;
- resources may be cached/subscribed;
- a resource URI identifies content but does not make content trusted.

### ACL/Vera implications

- remote resource content is lower-trust input and can carry prompt injection;
- network dereference needs SSRF and size/time protections;
- resource provenance should be retained alongside model-visible excerpts;
- a resource URI is not filesystem/sandbox authority.

Primary source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/server/resources.mdx

## 4.3 Prompts: user selection does not make server-authored text governance

Prompts are described as user-controlled in the sense that users/clients select them, but the actual prompt content is authored by the MCP server.

Prompt content can also include resource links and embedded resources.

### ACL/Vera candidate rule

Do not promote an MCP prompt into protected system/governance authority simply because the user selected it. Preserve provenance:

- selected by user;
- authored by server X;
- observed version/digest;
- lower-trust model-visible instruction content.

Primary source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/server/prompts.mdx

---

# 5. Multi Round-Trip Requests (MRTR)

MRTR replaces modern server-initiated JSON-RPC request flows for nested interactions inside `prompts/get`, `resources/read` and `tools/call`.

The server returns `resultType: "input_required"` containing:

- an `inputRequests` map;
- optional opaque `requestState`.

The client later retries the original operation with a **new JSON-RPC request ID**, returning responses and echoing `requestState`.

## 5.1 `requestState` is attacker-controlled unless protected

The specification is unusually explicit here: the client carries `requestState`, so a server using it for authorization, resource selection or business logic must treat it as attacker-controlled.

If integrity matters, the server must protect it (for example HMAC/AEAD) and should bind it to:

- authenticated principal;
- short expiration;
- originating request method;
- salient parameter digest.

Even those protections do not make it single-use. True one-time use requires server-side state.

### ACL/Vera candidate invariant

An opaque continuation token that can resume privileged work is an authorization/effect artifact. Bind it to:

- project/task;
- principal/user;
- server/service identity;
- operation/method + normalized parameter digest;
- policy/approval version;
- expiry;
- replay/idempotency state.

Do not confuse integrity protection with exactly-once execution.

Primary source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/patterns/mrtr.mdx

## 5.2 Open MRTR ambiguity: out-of-band waiting/cancel flow

Open issue #2920 reports that URL-mode elicitation has no clearly standardized bounded “still waiting, retry later” behavior/cancel path for out-of-band flows.

This is issue evidence, not a settled protocol fact.

### ACL lesson

Do not build critical human approval state solely around an implicit retry convention. ACL approvals need a first-class state machine with stable ID, active/answered/expired/cancelled terminal semantics.

Source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2920

---

# 6. Cancellation, progress and subscriptions

## 6.1 Request cancellation is cooperative

For current Streamable HTTP, closing the request SSE stream is the request-level cancellation mechanism. On stdio, cancellation uses a cancellation notification.

The specification recognizes races and allows a server to ignore cancellation if the request already completed or cannot be cancelled.

It recommends per-request timeouts and separates idle/progress-based timeout extension from a maximum absolute timeout.

### ACL invariant

Record at least:

- `cancel_requested`;
- transport/request cancelled;
- worker/process termination requested;
- worker/process termination settled/failed;
- external effects settled/unknown;
- final run terminal state.

Protocol cancellation cannot stand in for effect settlement.

Primary source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/patterns/cancellation.mdx

## 6.2 Progress is advisory

Progress is optional, token-addressed and monotonic when sent. A server may send none.

### ACL implication

Use MCP progress for GUI/idle-deadline hints, not as proof of:

- effect completion;
- checkpoint safety;
- acceptance success;
- task liveness.

Primary source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/patterns/progress.mdx

## 6.3 Subscription streams are transport continuity, not durable state

`subscriptions/listen` provides a long-lived notification stream. Multiple subscriptions can coexist and notification identity is explicit.

After reconnect, clients must resubscribe; server subscription state is not assumed to survive reconnect.

### Open same-day spec contradiction: #3348

Issue #3348, opened 2026-09-06 against the exact revision inspected, identifies conflicting normative text:

- `cancellation.mdx` describes one server teardown path;
- `subscriptions.mdx` describes graceful closure using a successful `subscriptions/listen` response;
- official SDK implementations reportedly follow the subscriptions behavior.

The issue is open. It is strong evidence of a current documentation/schema consistency failure surface, not proof of one universal runtime bug.

### ACL lesson

A transport stream ending must have an explicit reason class:

- graceful terminal result;
- client cancellation;
- server cancellation;
- transport loss;
- timeout;
- protocol error.

Do not infer durable task state from stream termination alone.

Sources:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/patterns/subscriptions.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/3348

---

# 7. Streamable HTTP and reconnect/replay boundary

Current Streamable HTTP uses one POST endpoint. Each JSON-RPC request is a new POST and may receive either JSON or a request-scoped SSE response.

Security requirements include:

- validate `Origin` to defend against DNS rebinding;
- local servers should bind localhost rather than all interfaces;
- authorization is recommended for protected deployments.

Current headers include:

- `MCP-Protocol-Version`;
- `Mcp-Method`;
- `Mcp-Name` for named primitives/task IDs.

The `2026-07-28` changelog removed resumable SSE / `Last-Event-ID`. If a stream breaks, an application that retries is issuing a **new request with a new JSON-RPC ID**.

### ACL candidate invariant

Network retry after ambiguous disconnect must never automatically mean “safe to re-execute effect.”

For effect-bearing tool calls, ACL still needs its own durable logical request/effect ID and reconciliation/idempotency policy above MCP request IDs.

Primary sources:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/transports/streamable-http.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/changelog.mdx

---

# 8. Tasks extension and long-running operations

The Tasks extension (`io.modelcontextprotocol/tasks`) is now separate from the core protocol.

The official extension repository is active:

- `modelcontextprotocol/ext-tasks`;
- revision inspected: `9263312d11a682ac83f83fe84794d4627efd22f5` (2026-09-04).

Current task-augmented execution supports `tools/call`.

## 8.1 Task as durable remote-operation handle

A server may return a `CreateTaskResult` instead of the normal result if both sides negotiated the extension.

A task carries:

- `taskId`;
- status;
- created/updated timestamps;
- TTL;
- optional polling interval;
- for input-required: outstanding input requests;
- for completed: original final result;
- for failed: JSON-RPC error.

Task states:

- `working`;
- `input_required`;
- `completed`;
- `failed`;
- `cancelled`.

Terminal states are immutable.

A server must not return the task handle until it is durably created and findable through `tasks/get`, including waiting for consistency in eventually-consistent stores.

### ACL reuse candidate

This is a good remote-job interoperability pattern:

- create durable handle before acknowledgement;
- explicit terminal state;
- poll/notification observation;
- mid-flight input keyed by stable IDs;
- reconnect by durable handle.

But it remains **remote job state**, not an ACL continuation checkpoint.

Primary sources:

- https://github.com/modelcontextprotocol/ext-tasks/blob/9263312d11a682ac83f83fe84794d4627efd22f5/index.md
- https://github.com/modelcontextprotocol/ext-tasks/blob/9263312d11a682ac83f83fe84794d4627efd22f5/specification/2026-07-28/tasks.md

## 8.2 Task input identity

Each `inputRequests` key must remain unique for the lifetime of the task and must not be reused after satisfaction.

Clients should deduplicate repeated appearances across polls. Servers ignore unknown/already-satisfied responses.

### ACL relevance

This is directly aligned with stable exactly-addressed approval/input IDs. For Vera phone/remote approvals, preserve:

- request ID;
- task/effect context;
- terminal answered/expired/cancelled state;
- duplicate response handling.

## 8.3 Task cancellation is intent, not settlement

`tasks/cancel` returns an acknowledgement, but:

- processing is eventually consistent;
- the task may remain working after ack;
- the operation may finish before cancellation takes effect;
- the server is not required to stop the work;
- a task can reach a non-cancelled terminal result.

Contributor discussion in open issue #11 explicitly confirms that the distinction between stored task-state retention and termination of underlying computation is intentional; servers retain freedom for eventually-consistent dependencies.

### ACL invariant

Never map:

`tasks/cancel ack` → `effect stopped`

or:

`task TTL expired/deleted` → `worker/effect stopped`

Instead reconcile the backing execution/effect owner independently.

Sources:

- https://github.com/modelcontextprotocol/ext-tasks/blob/9263312d11a682ac83f83fe84794d4627efd22f5/specification/2026-07-28/tasks.md
- https://github.com/modelcontextprotocol/ext-tasks/issues/11

## 8.4 Task handles and authorization

Current Tasks security guidance says:

- task IDs may function as bearer tokens for server-stored state;
- IDs must have sufficient entropy;
- servers **must** perform authentication/authorization checks on every task-related request;
- no `tasks/list` exists, reducing cross-caller enumeration risk;
- input requests do not become higher-trust merely because they arrived through a task.

Open issue #20 points out that the protocol does not yet provide one clearly standardized JSON-RPC representation for task authorization denial across all transport/auth modes. A contributor responds that this is partly a protocol-wide concern because HTTP OAuth has HTTP-level auth errors while authorization is not uniformly defined for every transport.

### ACL/Vera candidate rule

Treat remote task handle possession as **reference**, not sufficient authorization.

Bind ACL's record to:

- authenticated principal/user;
- MCP server/service trust identity;
- taskId;
- ACL project/task/run/effect;
- creation operation digest;
- protocol/extension version;
- current policy/credential grant;
- expiry/revocation state.

Sources:

- https://github.com/modelcontextprotocol/ext-tasks/blob/9263312d11a682ac83f83fe84794d4627efd22f5/specification/2026-07-28/tasks.md
- https://github.com/modelcontextprotocol/ext-tasks/issues/20

---

# 9. Elicitation and sensitive user input

Current elicitation has two modes:

- **form**: structured in-band user data;
- **URL**: out-of-band sensitive interactions.

The spec explicitly forbids servers from requesting passwords, API keys, access tokens or payment credentials in form-mode elicitation. Sensitive operations must use URL mode.

Clients must clearly identify the requesting server and let users review/decline. For URL mode, they must show the destination host and obtain consent before navigation.

### Vera reuse candidate

This is a strong pattern for future service connection:

- agent sees only that sensitive interaction is required;
- user completes auth/credential/payment flow outside model-visible content;
- application stores/brokers credential authority;
- model receives only a bounded success/failure/result reference.

### Warning

URL mode itself is a phishing/navigation surface. Vera should allow only trusted/expected authorization domains for high-authority service connections and preserve provenance of who requested navigation.

Primary source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/client/elicitation.mdx

---

# 10. Roots and Sampling deprecations

## 10.1 Roots

Roots are deprecated in `2026-07-28` and new implementations should not adopt them.

Even before deprecation, Roots were explicitly informational guidance, **not access control**. The protocol does not enforce that a server stays inside a root.

### ACL consequence

Do not use MCP roots as worker filesystem permissions. Use OS/container/filesystem capability enforcement under ACL-owned policy.

Primary source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/client/roots.mdx

## 10.2 Sampling

Sampling is also deprecated in `2026-07-28`; new implementations are directed toward direct model-provider APIs.

### ACL consequence

This independently supports keeping local/cloud model execution separate from MCP. MCP can provide interoperability for context/tools/services without owning ACL's model runtime or model qualification layer.

Primary source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/client/sampling.mdx

---

# 11. Authorization and credential boundaries

MCP's HTTP authorization layer is now a serious OAuth-based service boundary, not a simple API-key convention.

Current requirements/guidance include:

- MCP server acts as OAuth resource server;
- MCP client acts as OAuth client;
- Protected Resource Metadata discovery;
- Authorization Server/OIDC discovery;
- PKCE required;
- resource indicators/audience binding;
- issuer (`iss`) validation for mix-up defense;
- exact redirect URI validation;
- short-lived/secure token handling;
- least-privilege scope challenge/step-up behavior;
- Client ID Metadata Documents preferred;
- Dynamic Client Registration deprecated.

## 11.1 Token passthrough is explicitly forbidden

The MCP server must validate tokens intended for itself. If it calls a downstream API, that API uses a **separate** token issued for the downstream resource. The inbound MCP token must not simply be forwarded.

### Vera architecture relevance

This strongly supports a service credential broker pattern:

`user/service grant -> service-specific credential/reference -> MCP/server access -> separate downstream token if needed`

rather than:

`one broad bearer token -> model/runtime -> arbitrary downstream services`

Primary sources:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/authorization/index.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/authorization/security-considerations.mdx

## 11.2 Discovery itself is a network security surface

Security guidance explicitly calls out SSRF through server-provided OAuth discovery URLs, including:

- private/internal IPs;
- cloud metadata endpoints;
- localhost services;
- DNS rebinding;
- redirect chains.

### ACL/Vera candidate invariant

Any remote server-controlled URL dereference belongs to a network policy layer:

- HTTPS rules;
- DNS/IP validation at connect time, not only parse time;
- private/link-local/loopback policy;
- redirect revalidation;
- response-size/time limits;
- safe logging/redaction.

Primary source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/docs/2026-07-28/tutorials/security/security_best_practices.mdx

## 11.3 STDIO credentials

The HTTP OAuth authorization spec says stdio implementations should instead obtain credentials from environment/application configuration.

### ACL qualification

This must **not** be interpreted as “pass the supervisor's whole environment.” ACL's existing invariant remains stronger: construct a minimal child environment with only explicitly granted credentials/configuration.

---

# 12. JSON Schema and network dereference boundary

The modern base protocol uses JSON Schema 2020-12 and explicitly addresses external `$ref` dereferencing.

Current guidance:

- external network references must not be fetched automatically;
- network dereference should be opt-in and disabled by default;
- loopback/link-local/private destinations should be blocked;
- time/size limits should exist;
- unresolved external refs should cause validation rejection rather than permissive degradation;
- complex composition can create validation DoS and should be bounded.

### ACL relevance

This aligns with llama.cpp Task 13:

- schema compiler/validator is trusted authority-path code;
- schema validity does not authorize an effect;
- network-resolving schemas create a separate SSRF capability;
- authority-bearing schemas should be preflighted offline whenever possible.

Primary source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/index.mdx

---

# 13. Caching, provenance and stale trust

Current cacheable operations include discovery, tool/prompt/resource lists and resource reads.

Cache hints include:

- `ttlMs` freshness hint;
- `cacheScope: public | private`.

Important semantics:

- TTL is a hint, not guarantee underlying state remained unchanged;
- private cache entries cannot cross authorization contexts;
- public entries may be shared across callers;
- servers must still enforce primitive access control and must not rely on `cacheScope` as authorization;
- MRTR retry results are not cacheable;
- paginated lists do not guarantee cross-page snapshot consistency.

## 13.1 Open security reports #3207 / #3213

Open issue #3207 argues that a malicious/misconfigured server can mark attacker-controlled discovery/tool/prompt/resource metadata `public`, allowing a shared intermediary to replay that content across callers if the cache trusts the server's scope declaration without stronger provenance binding.

Open issue #3213 extends the concern to server `instructions`, which the discovery specification describes as natural-language guidance for LLMs. The issue argues that these server-authored instructions are an explicit prompt-injection surface, especially if cached/shared.

These issues are open and do not carry a maintainer resolution in the inspected discussion. Treat them as **current warning/evaluation cases**, not settled vulnerabilities of every conforming deployment.

However, the underlying protocol facts are clear:

- `serverInfo` is self-reported and explicitly not a security identity;
- `instructions` are server-supplied natural language;
- `cacheScope` is server-supplied metadata;
- public caching can cross authorization contexts when correctly used.

### ACL/Vera candidate invariants

1. Remote discovery instructions never become trusted system/governance instructions.
2. Cache key includes authoritative server/trust identity, protocol/profile and applicable authorization/provenance context, not merely RPC method/params.
3. Do not let server-declared `public` scope alone override host policy.
4. Retain source/digest/observed-at/freshness evidence for cached capability definitions.
5. Revalidate high-authority tool definitions before important effects even when list cache is nominally fresh.

Sources:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/server/utilities/caching.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/server/discover.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/3207
- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/3213

---

# 14. Extension lifecycle and interoperability

Extensions:

- use namespaced identifiers;
- are disabled by default;
- require explicit opt-in/negotiation;
- can evolve independently of the core;
- should document graceful fallback;
- may require version/capability flags if semantics change;
- need a new identifier if an unavoidable breaking change cannot be represented compatibly.

Official SDKs are not required to implement every extension even when they conform to core MCP.

### ACL capability profile

For each MCP connection/server, ACL should record something like:

```text
McpCapabilityProfile
  server_trust_id
  endpoint/transport
  protocol_era
  protocol_version
  sdk/client adapter + revision
  auth mode
  negotiated extensions + versions/settings
  discovered primitive definitions/digests
  task support
  MRTR modes
  cache behavior
  known deprecations/fallbacks
  last verified fixture set
```

A core-conformant MCP implementation with no Tasks extension is not equivalent to one with Tasks. A dual-era client is not behaviorally equivalent to a modern-only client.

Primary source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/extensions/overview.mdx

---

# 15. Current failure / ambiguity surfaces worth turning into ACL fixtures

## 15.1 Subscription teardown contradiction — open #3348

Fixture:

- server ends subscription stream;
- verify client distinguishes graceful result from transport loss/cancellation;
- verify no task/effect state is inferred merely from stream closure.

Source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/3348

## 15.2 MRTR out-of-band waiting ambiguity — open #2920

Fixture:

- URL-mode interaction remains incomplete across retries;
- ensure retry/backoff/cancel state is bounded and explicit;
- ensure stale continuation state expires and cannot authorize changed operation.

Source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2920

## 15.3 Task authorization denial semantics — open ext-tasks #20

Fixture:

- known task, wrong principal;
- unknown task;
- expired task;
- ensure ACL audit can distinguish policy denial internally even if wire protocol intentionally hides enumeration details.

Source:

- https://github.com/modelcontextprotocol/ext-tasks/issues/20

## 15.4 Stalled task / lost handle — open ext-tasks #11

Fixture:

- client loses task ID;
- no enumeration recovery exists;
- remote work may continue;
- verify ACL durable record keeps task handle until remote execution/effect settlement or explicit abandonment policy.

Source:

- https://github.com/modelcontextprotocol/ext-tasks/issues/11

## 15.5 Public-cache/server-instruction trust — open #3207 / #3213

Fixture:

- malicious server advertises high-TTL public tool/discovery content;
- another user/auth context shares gateway/cache;
- verify ACL does not cross server/trust identity and does not elevate discovery instructions into protected prompt authority.

Sources:

- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/3207
- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/3213

## 15.6 Modern/legacy version mismatch

Open historical-era issue #2721 documents ambiguity in the old initialize-body versus HTTP-header version relationship and cross-SDK divergence/testing.

The modern protocol removes that handshake path, so Task 15 treats #2721 primarily as **migration evidence**: version information duplicated across protocol layers can diverge unless one authoritative comparison/rejection rule exists.

Source:

- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2721

---

# 16. Concrete ACL/Vera candidate invariants from MCP

1. MCP transport connection/process identity is not ACL task/run/effect identity.
2. Every effect-bearing request has ACL-owned logical/effect identity above JSON-RPC request ID.
3. Modern-vs-legacy protocol era is explicit compatibility state, never silent fallback.
4. Negotiated protocol/extension capabilities are recorded per request/run profile.
5. MCP server self-reported names are display/debug metadata, not security identity.
6. Canonical MCP tool identity includes server trust identity and definition/schema version/digest.
7. Remote tool annotations are hints, not authority.
8. Remote prompts/discovery instructions/resources remain lower-trust model input regardless of user selection or valid schema.
9. Resource/network dereference obeys SSRF/network policy.
10. `requestState` or any continuation token that affects authority is integrity-bound to principal + operation + params + expiry + policy version.
11. Integrity-protected continuation is still replayable unless separately fenced/idempotent.
12. MCP request retry after broken transport is not authorization for effect replay.
13. Protocol cancellation acknowledgment is not process/effect settlement.
14. Progress is advisory, not authoritative liveness or success evidence.
15. Subscription stream state is transport observation state, not durable ACL state.
16. Task ID is a remote job handle, not an ACL checkpoint.
17. Task handle possession is not sufficient ACL authorization even if remote server permits bearer-handle semantics.
18. Task TTL/deletion is storage/visibility lifecycle, not evidence the underlying computation/effect terminated.
19. Lost task handles are unrecoverable by protocol enumeration; durable ACL state must retain handles until settlement/retirement.
20. Mid-flight input/approval IDs are unique and exactly addressed; duplicate/stale replies are terminally rejected/ignored.
21. Sensitive credentials are collected out-of-band and stored/brokered outside model-visible context.
22. Service tokens are audience/resource bound; inbound MCP token is never blindly forwarded downstream.
23. Current authority/credentials are rebound at execution time rather than assumed from old MCP/task snapshots.
24. STDIO child environment is minimal/explicit despite the protocol's environment-credential convention.
25. MCP Roots do not provide filesystem security.
26. Deprecated Sampling is not used as ACL's model-runtime abstraction.
27. Schema validation and external refs are trusted parser/network code and fail closed on unsupported/unresolved authority-bearing schemas.
28. Cache freshness and authorization are separate; TTL is not a state-version guarantee.
29. `cacheScope: public` never overrides ACL server/provenance/trust isolation.
30. High-authority capability definitions should carry server identity, digest, observed-at/freshness and qualification evidence.
31. Extension support is explicit opt-in and versioned behavior; core conformance does not imply Tasks/UI/auth-extension parity.
32. Protocol/SDK/spec regressions are classified separately from model/agent failure.

---

# 17. What MCP does not solve for ACL/Vera

Task 15 found no basis to treat MCP as a replacement for:

- ACL project/backlog/dependency scheduler;
- local model/runtime qualification;
- worker OS/container sandbox policy;
- Git/worktree authority;
- process-tree custody;
- distributed run leases/fencing;
- external-effect ledger/idempotency/reconciliation;
- independent acceptance verifier;
- benchmark fixture authority;
- Vera long-term memory/provenance governance;
- service credential broker/vault;
- task/objective approval provenance;
- workspace checkpoints;
- exactly-once side effects.

MCP is strongest as a **standardized interoperability boundary** through which ACL/Vera can discover and invoke externally provided capabilities while retaining host-owned authority and evidence.

---

# 18. Later comparison questions

When this research campaign reaches synthesis, compare:

1. Should ACL expose its own internal tools as MCP, consume MCP only, or both?
2. Which MCP version/SDK should become the minimum supported profile?
3. Is modern-only `2026-07-28+` support sufficient, or is legacy compatibility necessary?
4. Should all remote MCP tools require explicit ACL tool-definition pinning/digest qualification before workers see them?
5. How should ACL map MCP `taskId` to internal project/task/run/effect IDs?
6. Should ACL ever trust a remote `cacheScope: public`, or always partition by server trust identity?
7. Which MCP transports can run safely under local-first/offline conditions?
8. How should Vera's credential broker integrate with HTTP OAuth and stdio environment injection without leaking secrets to workers?
9. Which MCP extension capabilities deserve support before real demand exists?
10. How should ACL test SDK/spec conformance independently from model tool-use quality?

No answer is selected in Task 15.

---

# 19. Primary source inventory

Core specification / project:

- https://github.com/modelcontextprotocol/modelcontextprotocol
- https://github.com/modelcontextprotocol/modelcontextprotocol/tree/e76e9c572c6f2bfcb730357101acc90f2f802e02
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/blog/content/posts/2026-07-28-spec-ga/index.md
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/architecture/index.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/index.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/versioning.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/changelog.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/patterns/mrtr.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/patterns/cancellation.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/patterns/progress.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/patterns/subscriptions.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/transports/streamable-http.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/server/tools.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/server/resources.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/server/prompts.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/server/discover.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/server/utilities/caching.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/client/elicitation.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/client/roots.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/client/sampling.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/authorization/index.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/specification/2026-07-28/basic/authorization/security-considerations.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/docs/2026-07-28/tutorials/security/security_best_practices.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/e76e9c572c6f2bfcb730357101acc90f2f802e02/docs/extensions/overview.mdx

Tasks extension:

- https://github.com/modelcontextprotocol/ext-tasks
- https://github.com/modelcontextprotocol/ext-tasks/tree/9263312d11a682ac83f83fe84794d4627efd22f5
- https://github.com/modelcontextprotocol/ext-tasks/blob/9263312d11a682ac83f83fe84794d4627efd22f5/index.md
- https://github.com/modelcontextprotocol/ext-tasks/blob/9263312d11a682ac83f83fe84794d4627efd22f5/specification/2026-07-28/tasks.md

Current/open failure or ambiguity evidence:

- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/3348
- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2920
- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/3207
- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/3213
- https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2721
- https://github.com/modelcontextprotocol/ext-tasks/issues/11
- https://github.com/modelcontextprotocol/ext-tasks/issues/20

---

# Conclusion

MCP's current-generation design is highly relevant to ACL/Vera, but primarily as an **interoperability protocol with explicit trust boundaries**, not an agent harness.

The `2026-07-28` redesign independently validates a direction already emerging from the agent-runtime research: remove hidden state from incidental transport, make capabilities and continuation handles explicit, and keep complex authority/lifecycle outside model prompt scaffolding.

The strongest mechanisms to carry into later comparison are:

- self-describing stateless requests;
- explicit protocol/extension capability profiles;
- host-owned cross-server security;
- canonical server+tool identity rather than name-only dispatch;
- integrity-bound continuation state;
- Tasks-style durable remote operation handles;
- exactly-addressed mid-flight input IDs;
- audience-bound OAuth/resource tokens and no token passthrough;
- out-of-band sensitive elicitation;
- explicit separation of request cancellation from underlying work settlement;
- explicit deprecation/migration policy.

The strongest warnings are equally important:

- modern and legacy MCP are different lifecycle generations;
- a task handle is not a checkpoint or effect ledger;
- transport retry can duplicate an uncertain effect unless the host adds idempotency/reconciliation;
- tool metadata, prompts, resources and discovery instructions are server-controlled content;
- cache freshness/scope does not establish provenance or authority;
- Roots are not access control;
- provider/server identity names are self-reported, not security identity;
- OAuth metadata/network discovery is an SSRF surface;
- current open issues show specification/SDK semantics can still diverge at stream teardown, task authorization and asynchronous interaction edges.

Task 15 therefore supports using MCP underneath an ACL/Vera-owned authority/evidence layer, while preserving all of ACL's existing project/task/effect/checkpoint/credential/verifier controls.
