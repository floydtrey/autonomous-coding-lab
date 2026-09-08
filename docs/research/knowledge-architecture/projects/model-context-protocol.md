# Model Context Protocol Knowledge-Architecture Revisit — KA-10

**Task:** KA-10 — Model Context Protocol (MCP) Knowledge-Architecture Revisit  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Research date:** 2026-09-08  
**Canonical core repository:** `modelcontextprotocol/modelcontextprotocol`  
**Current core revision inspected:** `aa8ce049f089f92618340190d4ece141f663310d`  
**Current specification revision:** `2026-07-28`  
**Tasks extension repository:** `modelcontextprotocol/ext-tasks`  
**Tasks extension revision:** `9263312d11a682ac83f83fe84794d4627efd22f5`  
**Historical report:** `docs/research/projects/model-context-protocol.md`

## Scope and stop boundary

KA-10 revisits MCP as an interoperability, resource and authority-boundary protocol for the ACL/Vera knowledge architecture. MCP is not being selected as the canonical memory store, global scheduler, effect ledger or policy engine.

Historical Task 15 already deeply studied the `2026-07-28` transition to a stateless core, MRTR, Tasks, authorization, tools/resources/prompts, cancellation/subscriptions and compatibility. KA-10 therefore focuses on:

- current validation of those semantics;
- whether any core behavior changed since Task 15;
- what MCP tells us about explicit continuation identity, task state and transport/session separation;
- how remote resources relate to canonical resource identity and mutation authority;
- how current ecosystem proposals expose gaps between protocol success and effect outcome;
- which MCP primitives can carry knowledge without themselves establishing truth or authority;
- current issue/spec contradictions that should become ACL/Vera compatibility fixtures.

KA-10 is the second half of the user-authorized KA-9 + KA-10 bounded block. It stops before the required coverage scan and before cross-project architecture synthesis.

---

# 1. Upstream verification and delta from historical Task 15

## Observed

Historical Task 15 inspected core revision:

`e76e9c572c6f2bfcb730357101acc90f2f802e02`

Current core `main` is:

`aa8ce049f089f92618340190d4ece141f663310d`

The comparison is seven commits ahead, but the only substantive repository content delta is:

- new `docs/community/working-groups/filesystems.mdx`;
- one docs-navigation update.

The released core protocol remains `2026-07-28` and its normative specification content relevant to this campaign is unchanged.

The Tasks extension remains exactly at the historical revision:

`9263312d11a682ac83f83fe84794d4627efd22f5`

Thus KA-10 is mostly a **current validation and knowledge-architecture reinterpretation**, not a broad implementation-delta study.

## Architectural lesson

Protocol revision and extension revision must be tracked separately. A project's repository HEAD can move without changing the released wire semantics, while extensions can remain pinned independently.

This reinforces KA-I-018.

## Confidence

High.

---

# 2. Executive assessment

MCP is one of the strongest sources in the campaign for the principle that **transport, knowledge content, authorization and execution lifecycle are separate layers**.

The highest-value current findings are:

1. the `2026-07-28` core remains explicitly stateless: a connection/process is not a conversation, session, task or authority context.
2. state spanning requests must use explicit handles/identifiers rather than hidden connection state.
3. MRTR continuation `requestState` is explicitly client-carried attacker-controlled state; if it affects authorization or business logic, the server must integrity-protect and bind it to authenticated principal, short expiry and originating operation/parameter digest. Even that does not guarantee single-use.
4. Tasks are explicit durable execution state machines with receiver-generated task IDs; they are an execution-status abstraction, not proof of external effect settlement or semantic truth.
5. tools are model-controlled protocol capabilities, but MCP recommends human denial capability and leaves host policy separate.
6. tool availability may vary by **per-request authorization**, reinforcing that connection identity is not authority state.
7. resources are addressable content, not trusted facts or filesystem authority.
8. the newly added Filesystems Working Group explicitly plans resource writes with create/update/delete/stat, optimistic concurrency and cache/change-notification coherence while leaving host sandbox semantics and write-authorization policy outside that wire-format work.
9. open #3348 still shows normative cancellation/subscription wording contradicting the schema/SDK behavior; exact spec/SDK profile remains behavior-bearing.
10. open #3350 is a community extension proposal whose premise is that MCP protocol success does not currently provide a shared attested **delivery outcome**. It is gap evidence, not an adopted MCP feature.
11. MCP remains a protocol/interoperability substrate; it does not supply the canonical epistemic model Vera needs for verified/inferred/disputed/current/historical truth.

---

# 3. Stateless core: connection identity is intentionally weak

## Observed

Current `2026-07-28` core states that all information required to process a request is contained in the request itself.

Servers must not infer from previous requests on the same connection:

- protocol version;
- capabilities;
- client identity;
- application state.

State spanning requests must be referenced by explicit identifiers passed on requests.

The specification explicitly notes that an open stdio process or HTTP connection is **not** a conversation/session.

## Architecture lesson

This strongly reinforces KA-I-029 and KA-I-044's conceptual separation:

- transport connection;
- authenticated request principal;
- logical conversation;
- task;
- continuation;
- project;
- run/attempt;
- effect record

are different identities.

MCP's modern statelessness is particularly useful evidence against making a socket/process ID into durable Vera knowledge or authority state.

## Confidence

High.

---

# 4. Every request carries realized compatibility metadata

## Observed

Modern MCP requests carry metadata including protocol version, client information and client capabilities. Extensions can add supported result types/capabilities.

Earlier protocol eras have materially different lifecycle semantics.

## Architecture lesson

A reliable ACL/Vera MCP adapter profile should record at least:

- protocol revision/era;
- client SDK implementation/revision;
- server implementation identity where known;
- transport;
- negotiated/advertised extension set;
- authorization mode;
- tool/resource schema/profile;
- fallback behavior.

This reinforces KA-I-012 and KA-I-018.

## Confidence

High.

---

# 5. Explicit request identity is occurrence identity, not task identity

## Observed

JSON-RPC request IDs must be unique among outstanding requests and response IDs correspond to those request occurrences.

In MRTR, the retried operation uses a **different JSON-RPC request ID** because it is a new independent request.

A durable task uses a separate task ID.

## Architecture lesson

Request occurrence, durable task and semantic operation/effect identity must not be collapsed.

This reinforces KA-I-041 and KA-I-042 conceptually: occurrence identities need stable roles and must not be replaced by a tool name or transport session.

## Confidence

High.

---

# 6. MRTR makes continuation state explicit

## Observed

MRTR allows `prompts/get`, `resources/read` and `tools/call` to return `resultType: "input_required"`.

The response can contain:

- an `inputRequests` map;
- an opaque `requestState` string.

The client later retries the original operation with a new request ID and echoes `requestState` exactly.

This design allows server instances to reconstruct continuation without shared hidden connection/session state.

## Architecture lesson

This is a useful reference for explicit continuation artifacts. A continuation token is not the same as the transport connection or the durable task record.

## Confidence

High.

---

# 7. `requestState` is explicitly attacker-controlled

## Observed

The current spec requires servers to treat client-returned `requestState` as attacker-controlled.

If the state influences:

- authorization;
- resource access;
- business logic,

its integrity must be protected and invalid state rejected.

To reduce replay, the spec recommends binding protected state to:

- authenticated principal;
- short TTL;
- originating method plus digest of salient parameters.

It explicitly warns that these controls **do not guarantee single-use**. True at-most-once consumption requires server-side enforcement.

## Architecture lesson

This contributes the second independent half of new **KA-I-046**:

> Durable approval or continuation authority must be bound to the exact operation semantics and current authority context/version under which it was created; if principal, policy, capability definition or salient effect parameters change, reuse is invalid and requires a new authority/operation boundary.

OpenAI KA-9 supplies the policy-version/approval side; MCP supplies the principal/operation/parameter/expiry continuation side.

Together, KA-I-046 can be marked **reinforced** within this bounded block.

## Confidence

High.

---

# 8. Integrity protection is not single-use settlement

## Observed

MCP explicitly distinguishes integrity/replay-window binding from one-time consumption. A valid protected token can still be replayed inside the allowed window unless the server tracks consumption.

## Architecture lesson

For Vera/ACL:

- authenticated token != unspent token;
- approved continuation != not-yet-consumed continuation;
- cryptographic integrity != exactly-once effect.

This reinforces KA-I-028, KA-I-045 and KA-F-038 conceptually.

## Confidence

High.

---

# 9. Tools are protocol capabilities, not host authority

## Observed

MCP defines tools as model-controlled: language models can discover and invoke them.

The spec still recommends human ability to deny tool invocations and lets applications choose their own interaction/gating model.

Available tools can vary based on **authorization presented on the current request**.

## Architecture lesson

Service capability discovery and model selection do not authorize execution.

The host must evaluate:

- principal;
- purpose;
- policy;
- trusted server/tool identity;
- exact arguments;
- current capability profile;
- approval requirements.

This reinforces KA-I-020 and KA-I-042.

## Confidence

High.

---

# 10. Tool name remains server-local identity

## Observed

Within the tools primitive, a tool is identified by name and schema in the server's catalog. Tool lists may change over time and by current authorization context.

Across multiple servers/proxies, names are not a globally sufficient trusted identity.

## Architecture lesson

An ACL/Vera authority identity for an MCP tool should include something like:

`trusted server identity + protocol/profile + tool name + observed definition/schema digest + capability/policy profile`

This independently supports KA-I-042 and KA-F-044.

## Confidence

High.

---

# 11. Tool metadata is not epistemic or policy truth

## Observed

Tool names, descriptions and schemas are provided by the MCP server and shown to the model/host.

They describe capability but do not establish:

- the truth of returned content;
- whether the tool is safe for a particular principal;
- whether annotations can be trusted;
- whether a successful protocol response proves the external effect occurred.

## Architecture lesson

Remote tool metadata should be provenance-bearing untrusted capability content until the server/definition/profile is separately trusted.

This reinforces KA-I-015 and KA-I-019.

## Confidence

High.

---

# 12. Resources are addressable content, not canonical truth

## Observed

MCP Resources provide URI-addressed content for files, documents, schemas and other resource-like information.

A URI can identify what to read, but the core resource abstraction is not a universal identity/version/trust envelope for Vera.

It does not automatically tell the host:

- observed content digest;
- immutable version;
- canonical semantic entity identity;
- owner/sensitivity authority;
- epistemic verification;
- retention obligation.

## Architecture lesson

This remains strong supporting context for KA-I-037:

`logical resource identity != locator/URI != observed content/version`.

KA-I-037 remains candidate because MCP reinforces the need for distinction but does not itself provide independent complete evidence for all three identities.

## Confidence

High.

---

# 13. New current delta: Filesystems Working Group makes resource mutation explicit

## Observed

The only meaningful core-repository delta since Task 15 is the new Filesystems Working Group charter.

Its mission is to make Resources bidirectional. Planned extension work includes:

- create;
- update;
- delete;
- `stat`;
- optimistic concurrency control;
- create-if-absent;
- interaction with resource change notification and caching (`ttlMs`, `cacheScope`, `lastModified`).

The charter explicitly leaves these out of scope:

- host sandbox/local-disk semantics;
- write authorization policy beyond where existing MCP authorization applies.

## Architecture lesson

This is useful **directional** evidence, not current protocol semantics.

It supports several existing campaign ideas:

- read authority and mutation authority are distinct (KA-I-043);
- mutable resources need revision/precondition semantics (KA-I-028/KA-F-023);
- cache/derived view freshness must reconcile with writes (KA-I-027);
- wire resource identity does not define host sandbox identity (KA-I-037).

## Confidence

High for the charter; low-to-medium for the eventual exact extension design because it is still future work.

## Non-conclusion

KA-10 does not claim MCP Resources currently support those writes or that the Working Group's future SEP has been accepted.

---

# 14. Resource write path versus tool effect path is an important distinction

## Observed

The Filesystems charter explicitly plans guidance on when to use a resource write path versus a tool-based write path.

## Architecture lesson

Two operations may produce a similar external result while having different protocol semantics, authority expectations, concurrency controls and audit evidence.

Vera's action model should therefore classify effect semantics rather than authorize based only on user-facing intent like “save this file.”

This is adjacent evidence for KA-I-043 and KA-I-042.

## Confidence

High as a design concern; extension details are not final.

---

# 15. Prompts/resources remain content, not policy

## Observed

MCP prompts are server-authored even when selected by a user. Resources are server-provided/addressed content. Both can enter model context.

## Architecture lesson

User selection or transport authenticity does not promote server-authored instructions into Vera governance.

Preserve provenance such as:

- user selected;
- server authored;
- observed revision/digest if known;
- lower-trust model-visible content.

This reinforces KA-I-015 and KA-F-017.

## Confidence

High.

---

# 16. Tasks are durable execution state, not truth or effect evidence

## Observed

The official Tasks extension describes tasks as durable state machines representing underlying execution state and providing polling/deferred result retrieval. Each task has a receiver-generated task ID.

Statuses include execution states such as:

- submitted/working;
- input required;
- completed;
- failed;
- cancelled.

## Architecture lesson

This is useful execution-lifecycle structure. It is not a canonical semantic knowledge record.

A task saying `completed` can mean the protocol operation completed and a result is available. It does not, without further domain evidence, prove a real-world effect such as:

- money transferred;
- email delivered;
- machine stopped;
- file durably replicated;
- human received notification.

This reinforces Knowledge ≠ Authority ≠ Execution and KA-I-028.

## Confidence

High.

---

# 17. Task cancellation is not universal effect settlement

## Observed

The Tasks specification lets clients send cancellation and permits client-side task state cleanup without necessarily polling until the task reports a cancelled terminal state.

## Architecture lesson

That is appropriate protocol flexibility, but ACL/Vera cannot map “cancellation requested/sent” directly to “effect safely stopped.”

The effect ledger still needs:

- cancel requested;
- remote cancel accepted/unknown;
- worker/process stopped;
- external effect final/unknown;
- reconciliation evidence.

This reinforces KA-F-019.

## Confidence

High.

---

# 18. Current ecosystem gap evidence: protocol success versus delivery outcome

## Evidence: open #3350

Open #3350 proposes a Tool Outcome Attestation extension. Its premise is explicit:

MCP defines tool invocation, but does not currently provide a shared negotiable mechanism for attested **delivery outcomes**; a JSON-RPC/HTTP success response is not necessarily delivery success.

The proposal includes a reference implementation and signed attestation format, but it is not an accepted core/extension feature.

## Architecture lesson

The important evidence is the gap, not the proposed solution.

For ACL/Vera, protocol success should remain one item in effect evidence rather than the final settlement verdict.

This reinforces KA-I-028 and KA-F-019.

## Confidence

Medium-high as ecosystem gap evidence; low for future adoption/design of the proposed extension.

## Non-conclusion

KA-10 does not state that Tool Outcome Attestation is part of MCP.

---

# 19. Cancellation/subscription normative contradiction remains open: #3348

## Failure evidence

Issue #3348 identifies conflicting normative descriptions for a server ending a `subscriptions/listen` stream:

- cancellation documentation describes server-sent cancellation behavior;
- subscription documentation/schema and official SDK behavior use a successful `subscriptions/listen` response for graceful closure.

The issue remains open on the current core revision; the core spec pages were not changed by the new repository commits.

## Architecture lesson

A declared protocol revision alone may still contain internal ambiguity. Realized compatibility identity may require:

- spec page/schema revision;
- SDK implementation behavior;
- transport;
- tested conformance fixture.

Stream closure reason should be explicit rather than inferred from EOF/disconnect.

This reinforces KA-I-012, KA-I-018 and KA-F-013.

## Confidence

High for the contradiction; no claim is made that all SDKs are broken.

---

# 20. Core conformance and extension conformance are distinct

## Evidence

The TypeScript SDK Tier 1 assessment updated/closed on September 7 reports full scored core conformance for frozen supported revisions, while extension-tagged scenarios such as Tasks are separately categorized and may have expected failures without affecting the same core score.

## Architecture lesson

“MCP conformant” is too coarse for ACL/Vera deployment evidence.

Record compatibility separately for:

- core protocol revision;
- extension/version;
- client/server role;
- transport;
- auth profile;
- specific conformance suite/version.

This reinforces KA-I-018 and KA-I-012.

## Confidence

High for the assessment's reported methodology; it remains project governance/conformance evidence rather than an independent formal proof of all deployments.

---

# 21. Authorization is per request, not connection inheritance

## Observed

Tool availability can vary by authorization presented on each request. Modern statelessness prevents connection history from becoming implicit client identity/authority.

## Architecture lesson

This is a strong positive boundary for Vera:

- current authenticated principal and grants travel/evaluate at the operation boundary;
- a long-lived transport should not retain authority simply because it was previously authenticated for another context.

This reinforces KA-I-003, KA-I-014 and KA-I-020.

## Confidence

High.

---

# 22. Authorization does not equal model-selected effect approval

## Observed

MCP authorization governs client/server access. Tools are model-controlled and the spec recommends human denial capability.

## Architecture lesson

OAuth/service scope answers “may this client call this service/tool?” It does not necessarily answer “should this model perform this exact irreversible effect now for this user?”

Vera still needs a host effect-policy/approval layer above MCP.

This reinforces KA-I-020.

## Confidence

High.

---

# 23. MCP does not provide a canonical epistemic truth model

## Observed

Core MCP transports structured content and capabilities, but it has no general required proposition envelope for:

- observed versus inferred;
- verified/unverified;
- confidence;
- disputed/conflicting;
- superseded;
- known false;
- unknown/not established;
- world-valid interval;
- claim evidence graph;
- authority-use classification.

## Architecture lesson

MCP can transport Vera knowledge/resources and expose knowledge services, but it should not define what “true” means inside Vera.

## Confidence

High.

---

# 24. Temporal truth differs from protocol/task time

## Observed

MCP has request/task lifecycle, TTL/cache metadata, expiration guidance for continuation tokens and resource cache freshness.

These are operational times.

They do not define the world-valid interval of a semantic assertion.

## Architecture lesson

Do not reuse protocol TTL, task status time or cache freshness as proposition validity time.

This reinforces KA-I-008.

## Confidence

High.

---

# 25. Relationship structures are protocol associations, not world relations

## Observed

MCP can associate:

- request/response;
- task/result;
- tool/schema;
- resource/URI;
- MRTR input request/response;
- subscriptions/notifications.

These are protocol relationships.

They do not constitute canonical Vera world relationships such as ownership, location, dependency, contradiction or evidence support.

## Architecture lesson

Protocol graphs and semantic knowledge graphs remain separate layers.

## Confidence

High.

---

# 26. Unknown/negative semantics are not first-class truth states

## Observed

An MCP error, missing resource, empty list or inaccessible tool can have several operational meanings. The protocol does not convert these into a universal epistemic taxonomy.

## Architecture lesson

Vera should not infer “false” from no MCP result without knowing whether the cause was:

- no match;
- permission filtering;
- unsupported capability;
- unavailable server;
- stale cache;
- protocol error;
- not searched.

This reinforces KA-I-021.

## Confidence

High.

---

# 27. Full 26-question evidence matrix

| # | Evidence question | KA-10 assessment |
|---|---|---|
| 1 | Stable identity | Strong request/task/continuation identifiers; no universal semantic entity identity. |
| 2 | Identity vs namespace/principal | Modern core separates transport from client identity; authorization is per request. |
| 3 | Provenance | Server/tool/resource/request origin can be recorded; semantic claim-level provenance is application-defined. |
| 4 | Epistemic state | Not first-class. |
| 5 | Temporal truth | TTL/cache/task/continuation time exists; no proposition-level bitemporal truth. |
| 6 | Conflict/supersession | No canonical truth-conflict system; future resource OCC is proposed but distinct from semantic supersession. |
| 7 | Relationships | Protocol associations, not canonical world relationships. |
| 8 | Permissions/sensitivity | Strong service/request auth mechanisms; host knowledge/effect policy remains separate. |
| 9 | Actionability | Tools and Tasks are explicit operation primitives; exact host approval remains application responsibility. |
| 10 | Knowledge vs authority | Strongly separated: resources/prompts/tool content do not themselves grant effect authority. |
| 11 | Resources | URI-addressed Resources are useful but incomplete canonical resource identity/version envelopes; future write/OCC WG confirms mutation concerns. |
| 12 | Canonical vs derived | Protocol carries content/results, but host must decide which are source evidence, derived views and canonical semantic records. |
| 13 | Structured retrieval | Resource/tool list/read APIs are structured protocol access, not a general truth query engine. |
| 14 | Relationship retrieval | Not a general semantic relationship retrieval primitive. |
| 15 | Full-text retrieval | Server/application-specific; not core. |
| 16 | Semantic retrieval | Server/application-specific; not core. |
| 17 | Composite retrieval | Host/application responsibility. |
| 18 | Context construction | Host chooses which MCP resources/prompts/tool results enter model context. |
| 19 | Poisoning/injection | Remote prompts/resources/tool metadata remain untrusted content unless source separately trusted. |
| 20 | Concurrency | Stateless core avoids hidden connection state; future Filesystems WG explicitly targets optimistic write concurrency. |
| 21 | Derived integrity | Cache/resource mutation coherence and task/result settlement remain explicit concerns; protocol success != attested delivery outcome. |
| 22 | Deletion/retention | Resource/task cleanup is protocol-specific; no universal privacy erasure contract. |
| 23 | Schema evolution | Strong dated protocol revisions/extensions; core vs extension compatibility must be independently qualified. |
| 24 | Recovery | Explicit MRTR state and Tasks handles support recovery without hidden transport sessions; token validity/single-use/effect settlement remain host/server responsibilities. |
| 25 | Unknown/negative | Not first-class semantic truth state. |
| 26 | Scope of truth | Request/service/resource scope does not express arbitrary semantic assertion applicability. |

---

# 28. Highest-value positive patterns for ACL/Vera

## 28.1 Stateless transport with explicit application handles

Do not make connection/process identity authoritative durable state.

## 28.2 Self-describing request compatibility

Carry exact protocol/capability profile at operation boundaries.

## 28.3 Authority-bound continuation tokens

Bind authority-relevant continuation state to principal, expiry and originating operation parameters; enforce one-time semantics server-side when required.

## 28.4 Explicit durable Tasks

Represent long-running operation state with stable task IDs rather than hidden socket/session state.

## 28.5 Host remains policy owner

Model tool discovery/invocation is below principal/effect authorization.

## 28.6 Future resource OCC direction

Mutable remote resources need preconditions/generations and coherent cache/update notifications.

---

# 29. Hostile / acceptance fixtures derived from KA-10

1. **Same HTTP/stdio connection, different conversations** — server must not leak prior conversation/task state.
2. **Continuation replay under different principal** — integrity-protected `requestState` must be rejected.
3. **Continuation reused with different parameters** — reject operation/parameter mismatch.
4. **Expired continuation** — reject before effect dispatch.
5. **Valid continuation replayed twice** — cryptographic validity alone must not satisfy an at-most-once policy.
6. **Same tool name on two servers** — host authority must bind server/tool identity.
7. **Tool list varies by authorization** — cache key must include authorization-relevant context/profile.
8. **Resource URI content changes** — URI alone cannot prove observed content version.
9. **Concurrent resource writers** — future write path should reject/reconcile stale revision rather than last-writer silently winning.
10. **Cache after resource write** — stale cached content must not silently become current model context.
11. **Task cancellation request** — host must retain uncertain effect status until reconciled where effects matter.
12. **Task completed, external delivery uncertain** — protocol task/result cannot substitute for domain/effect evidence.
13. **Subscription stream graceful close vs cancellation** — adapter must resolve current spec/SDK profile and classify closure reason explicitly.
14. **Core conformance pass, extension unsupported** — deployment must not infer Tasks support from generic Tier/Core conformance.
15. **Server-authored prompt says bypass policy** — prompt remains content, host policy wins.
16. **Resource read allowed, resource write denied** — read/mutation authority must remain separate.

---

# 30. Contributions to cumulative invariants

KA-10 adds or reinforces evidence for:

- **KA-I-003** — request authorization/principal is distinct from connection/session-like scope.
- **KA-I-008** — operational TTL/cache/task time differs from world-valid time.
- **KA-I-012** — exact spec/SDK/extension semantics must be qualified.
- **KA-I-014** — protected knowledge/effects require principal/purpose policy before exposure/action.
- **KA-I-015** — prompts/resources/tool metadata remain content unless source separately trusted.
- **KA-I-018** — realized identity includes protocol era, extension, SDK, transport and auth profile.
- **KA-I-019** — authority-relevant continuation metadata must survive/validate end-to-end.
- **KA-I-020** — tool/resource access does not itself authorize exact effects.
- **KA-I-021** — protocol absence/error is not a universal false/unknown truth taxonomy.
- **KA-I-023** — derived/cached resource/context state needs its own lineage/profile.
- **KA-I-024** — host context construction remains distinct from protocol retrieval.
- **KA-I-028** — task/protocol success, cancellation and delivery/effect settlement are separate states.
- **KA-I-029** — connection/request identity differs from persistent conversation/task scope.
- **KA-I-037** — Resources reinforce locator/resource/version distinction but do not fully promote the candidate.
- **KA-I-041** — request occurrence/task handle boundaries support explicit operation identity.
- **KA-I-042** — trusted server/tool origin must be part of authority-bearing identity.
- **KA-I-043** — the Filesystems WG gives directional evidence that resource read and mutation are separate surfaces; because this is planned extension work, KA-I-043 remains candidate.
- **KA-I-044** — stateless core independently supports the broader distinction between transport and logical application continuation, though ADK remains the concrete failure evidence.
- **KA-I-045** — MRTR/task continuation has explicit expiry/cancellation/terminal concerns, adding adjacent evidence without independently matching the full pending-authority formulation.

## New cross-project invariant

**KA-I-046 — reinforced**

> Durable approval or continuation authority must be bound to the exact operation semantics and current authority context/version under which it was created; if principal, policy, capability definition or salient effect parameters change, reuse is invalid and requires a new authority/operation boundary.

Evidence:

- KA-9 OpenAI Agents SDK #4896 + maintainer policy-version guidance;
- KA-10 MCP current MRTR requirements to bind authority-relevant `requestState` to principal, expiry and originating method/parameter digest, with server-side consumption where single-use matters.

No final architecture rule is adopted during the campaign.

---

# 31. Contributions to cumulative failure patterns

KA-10 adds recurrence to:

- **KA-F-013** — “supports MCP”/protocol name is insufficient realized deployment identity; #3348 shows spec/SDK semantic disagreement.
- **KA-F-017** — server-authored prompts/resources can become model-visible instruction content without becoming policy.
- **KA-F-019** — task/protocol success or cancellation is not complete effect settlement; #3350 supplies current ecosystem gap evidence.
- **KA-F-032** — transport/protocol projections can differ from domain outcome evidence.
- **KA-F-044** — name-only tool identity remains insufficient across servers/profiles.

No new failure ID is created for authority-token reuse because MCP provides a normative prevention rule rather than a concrete current core failure reproduction. Combined with KA-9, the evidence is stronger as a positive invariant than as a new failure class.

No new failure ID is created for #3348 because the realized-profile/spec-divergence concept is already represented by KA-F-013.

No new failure ID is created from the Filesystems Working Group because its design is proposed future work, not observed deployed failure evidence.

---

# 32. Non-conclusions

KA-10 does **not** conclude that:

- MCP is a memory database or agent runtime replacement;
- MCP Tasks are an effect ledger;
- `resultType: complete` proves a physical/business effect settled;
- all MCP servers are untrusted;
- user confirmation is mandatory for every tool call in every host;
- Tool Outcome Attestation is an adopted MCP extension;
- the Filesystems Working Group's planned resource write SEP is accepted or implemented;
- current Resources support create/update/delete/stat;
- #3348 proves every official SDK violates the protocol;
- Tier 1 core conformance implies every extension is supported;
- stateless transport means applications cannot maintain state;
- MCP should be rejected or adopted wholesale by ACL/Vera;
- a resource URI is useless as an address;
- authorization and approval are the same concept.

---

# 33. Primary/current sources inspected

Core current source:

- `modelcontextprotocol/modelcontextprotocol@aa8ce049f089f92618340190d4ece141f663310d`
- `docs/specification/2026-07-28/basic/index.mdx`
- `docs/specification/2026-07-28/basic/patterns/mrtr.mdx`
- `docs/specification/2026-07-28/server/tools.mdx`
- current Resources/Prompts/Authorization/Cancellation/Subscriptions material revalidated against historical report.
- new `docs/community/working-groups/filesystems.mdx`

Tasks extension:

- `modelcontextprotocol/ext-tasks@9263312d11a682ac83f83fe84794d4627efd22f5`
- `README.md`
- `specification/2026-07-28/tasks.md`
- `schema/2026-07-28/schema.ts`

Current issue/ecosystem evidence:

- #3348 — cancellation/subscriptions normative contradiction — open.
- #3350 — proposed Tool Outcome Attestation extension and explicit protocol-success/delivery-outcome gap — open, not adopted.
- #3268 — TypeScript SDK Tier 1 assessment, including core-vs-extension scoring distinction — closed September 7.

Official current release context rechecked:

- https://blog.modelcontextprotocol.io/posts/2026-07-28/
- current 2026-07-28 specification at modelcontextprotocol.io.

---

# 34. Stop condition

KA-10 is complete when:

- current core and Tasks revisions are verified;
- the unchanged normative core is explicitly distinguished from the new Filesystems WG repository delta;
- all 26 campaign questions are evaluated;
- current issue/proposal evidence is carefully scoped;
- new invariant evidence is reconciled without over-promoting proposed features;
- no coverage scan, final synthesis, storage selection or implementation begins.

Completion of KA-10 closes the planned ten-project high-yield revisit sequence. The campaign must stop before the separately authorized bounded coverage scan.