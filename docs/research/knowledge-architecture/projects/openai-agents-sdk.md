# OpenAI Agents SDK Knowledge-Architecture Revisit — KA-9

**Task:** KA-9 — OpenAI Agents SDK Knowledge-Architecture Revisit  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Research date:** 2026-09-08  
**Project:** OpenAI Agents SDK for Python  
**Canonical repository:** `openai/openai-agents-python`  
**Current upstream revision inspected:** `544b8b03b8cf95e62c7f5ebb89adfc4bd66c9d1f`  
**Current package version observed:** `0.22.1`  
**Historical report:** `docs/research/projects/openai-agents-sdk.md`

## Scope and stop boundary

KA-9 revisits the OpenAI Agents SDK specifically as evidence for ACL/Vera's general knowledge architecture. The SDK is not being selected as ACL's runtime, Vera's memory system, or the final persistence layer.

The historical Task 14 report already mapped the SDK's agent loop, tools, approvals, `RunState`, sessions, guardrails, sandboxing, retry, streaming and lifecycle behavior. This revisit therefore concentrates on the knowledge-architecture questions that follow from those mechanisms:

- which durable records are source evidence versus execution state versus derived context;
- which identities survive pause/resume and why;
- what an approval actually authorizes across time;
- when session/history mutation is considered settled;
- how compaction/replacement protects newer evidence;
- how model-visible context relates to canonical session history;
- which metadata is provenance, policy state, replay identity or merely attribution;
- what the SDK does **not** model as canonical epistemic truth.

The user explicitly authorized KA-9 and KA-10 MCP as one bounded two-project block. This report contains OpenAI Agents SDK evidence only. The block stops before the campaign's coverage scan and before any final architecture synthesis, storage selection or implementation.

---

# 1. Upstream verification and delta from historical Task 14

## Observed

Historical Task 14 inspected:

`1d471a4775bf2f40179f411824da383deb4c3fca`

Current `main` is:

`544b8b03b8cf95e62c7f5ebb89adfc4bd66c9d1f`

The current package metadata reports:

`openai-agents 0.22.1`

The upstream comparison is 27 commits ahead of the historical revision. The delta includes runtime/session source, `RunState`, session persistence, sandbox behavior, guardrail documentation and a new `model_provider_lifecycle.py` helper. A large fraction of file churn is translated documentation, so KA-9 does not treat raw file count as behavioral change.

Current official OpenAI Agents SDK documentation was also rechecked for HITL, `RunState`, sessions, guardrails and running-agent behavior.

## Architectural lesson

Exact source revision, package version, provider profile and backend remain part of realized behavior. “OpenAI Agents SDK” alone is too coarse an identity for replay/security evidence.

## Confidence

High.

## Non-conclusion

This report does not claim all current upstream changes are semantically important to ACL/Vera. Only changes and current behavior relevant to the 26 campaign questions are retained.

---

# 2. Executive assessment

The OpenAI Agents SDK is strongest in this campaign as evidence for **durable execution-state semantics, exact approval identity, replay-aware persistence and guarded derived-history replacement**.

It is not a canonical epistemic truth substrate.

The highest-value current findings are:

1. `RunState` remains a deliberately versioned execution snapshot (`1.17`) whose schema history records behavior-bearing resume semantics.
2. Sessions, `RunState`, provider continuation IDs, sandbox state and external effects remain separate planes.
3. approval decisions are scoped to tool-call occurrences; broader sticky approvals require a tool identity, and hosted MCP sticky identity includes server label plus tool name.
4. current maintainer guidance in #4896 makes **resume-time policy freshness an application responsibility**: approval is final for that invocation, so policy-version drift should invalidate resumption and create a new call/run boundary rather than silently reuse the old authority artifact.
5. current #4775 demonstrates an unresolved lost-acknowledgement problem for staged `RunState.add_input()` persisted to a client-managed Session: storage may have committed while the execution snapshot still treats the input as pending, causing duplicate logical input on retry.
6. a prior compaction stale-snapshot race (#4679) is now addressed in current source by holding a mutation lock across snapshot-through-replacement plus using mutation-generation checks and rollback state.
7. Runner-owned model-provider cleanup is shielded through repeated cancellation until cleanup settles, reinforcing old-generation fencing.
8. guardrail timing remains explicitly different from authority timing: parallel input guardrails can run after tool/model execution has already started; blocking checks are required if the policy means “nothing may execute before this passes.”
9. current session/history ownership code tracks occurrence identity and digests through rewrites, useful evidence that presentation/history transformation needs lineage distinct from source identity.
10. the SDK's memory/session abstractions still do not provide first-class truth confidence, world-valid time, contradiction/supersession, typed world relationships or structured unknown/negative knowledge.

---

# 3. Distinct durable planes

## Observed

The current SDK exposes multiple persistent or semi-persistent planes that must not be collapsed.

### 3.1 `RunState`

`RunState` is the durable pause/resume snapshot of one agent run. It can include:

- app context;
- usage;
- model responses;
- generated items;
- approval state;
- pending input;
- pending resumed Session writes;
- server-managed conversation identifiers;
- nested-agent state;
- tool identity/origin metadata;
- sandbox/resume metadata;
- trace state.

### 3.2 Session history

A Session is conversation history used across runs. It is a memory/context plane rather than the complete execution checkpoint.

### 3.3 Provider-managed continuation

OpenAI Responses continuation can use conversation/response identifiers distinct from client Session history and `RunState`.

### 3.4 Sandbox/workspace state

Sandbox state, mounts and files are operational resources/effects. They are not identical to transcript history.

### 3.5 External effects

A tool can mutate the external world before final history persistence or output guardrails settle.

## Architecture lesson

For ACL/Vera, a generic “agent state” object would hide critical recovery meaning. Conversation evidence, execution checkpoint, workspace/resource state, authority state and effect settlement require separate semantics even when one serialized envelope references all of them.

## Confidence

High.

---

# 4. `RunState` schema versioning is semantic versioning of recovery evidence

## Observed

Current source retains:

`CURRENT_SCHEMA_VERSION = "1.17"`

The schema changelog is behavior-oriented. Prior versions added semantics such as:

- reasoning-item ID handling;
- trace reattachment;
- request IDs;
- rejection messages;
- duplicate-name agent identities;
- custom-tool pending state;
- programmatic tool-caller and nested-history ownership;
- hosted MCP approval identity scoped by server label;
- canonical tool invocation identity;
- durable pending input;
- mount authority and trusted rebind metadata;
- Docker network isolation;
- exact-call approval precedence;
- current-response ownership;
- pending resumed Session writes and terminal-unrecoverable states.

Forward compatibility is fail-fast: older code rejects unsupported newer snapshot versions rather than guessing.

## Architecture lesson

A durable checkpoint version should describe **meaning**, not merely serialization shape. ACL/Vera checkpoint compatibility needs to include changes that alter authority, replay, workspace identity, evidence ownership or effect interpretation.

This reinforces KA-I-017 and KA-I-018.

## Confidence

High.

---

# 5. Execution identity is not semantic world identity

## Observed

Current SDK identity mechanisms include:

- run/checkpoint context;
- tool call IDs;
- canonical tool invocation identity;
- tool origin;
- function-tool namespaces/qualified names;
- hosted MCP server labels;
- nested-history occurrence keys;
- model response/request identifiers;
- sandbox/session identity.

These identities make replay and dispatch safer.

They do not identify a real-world person, device, project, mine, policy, claim or physical resource as a canonical semantic entity.

## Architecture lesson

Vera needs both:

- operational occurrence/continuation identity;
- semantic entity/assertion/resource identity.

Neither should be overloaded into the other.

## Confidence

High.

---

# 6. Exact tool-call approval is a strong authority pattern

## Observed

Current HITL documentation states that per-call approvals are scoped to the specific call ID. The approval rule receives parsed parameters and call ID. When arguments cannot be safely parsed, callable approval logic is not invoked and the call falls back to manual approval.

Sticky `always_approve` / `always_reject` decisions persist for the rest of the run. For hosted MCP tools, sticky identity is the combination of:

- `server_label`;
- tool name.

The SDK does not persist a sticky hosted-MCP decision when those identity fields are missing.

## Architecture lesson

This reinforces KA-I-042: authority identity must bind trusted origin/implementation/occurrence, not only the model-visible name.

Malformed effect parameters should fail closed because policy cannot evaluate an effect it cannot parse.

## Confidence

High.

---

# 7. New high-value lesson: approval validity has a policy/version boundary

## Evidence: issue #4896 and maintainer response

Issue #4896 asked what should happen when:

1. a tool call is approved;
2. `RunState` is persisted;
3. external policy changes while the run is parked;
4. the invocation is later resumed.

The deterministic reproduction showed:

- the old approval remains stored for that exact invocation;
- `needs_approval` is not recomputed;
- tool input guardrails can rerun and block execution;
- there is no public guardrail transition that reopens the same approved invocation into a fresh approval interruption.

Maintainer guidance stated:

- approval is a decision for that invocation;
- guardrails can revalidate execution but do not reopen the approval;
- applications with policy-sensitive approvals should persist the policy/approval version;
- compare that version before resuming saved state;
- if the authority semantics changed, do not resume the old invocation: create a new call/run boundary.

## Architecture lesson

This contributes one half of new cross-project invariant **KA-I-046**:

> Durable approval/continuation authority must be bound to the exact operation semantics and authority context/version under which it was created; if principal, policy, capability definition or salient effect parameters change, the old authority artifact must not be silently reused.

This is stronger and more precise than “approval is tied to call ID.” The call can remain identical while the **meaning of permission** changes.

## Confidence

High for intended current SDK lifecycle and maintainer guidance.

## Non-conclusion

This is not classified as an OpenAI Agents SDK security bug. The SDK intentionally treats approval as final for that invocation and leaves policy-version invalidation to the host application.

---

# 8. Resume itself is an authority boundary

## Observed

Long-running HITL guidance recommends storing a version marker for agent definitions or SDK alongside serialized state. `RunState` can contain approvals and runtime metadata that will influence what executes when resumed.

## Architecture lesson

For ACL/Vera, resume is not a passive deserialization step. Before execution resumes, the host should re-establish:

- principal identity;
- policy revision;
- capability/tool definition revision;
- credential grants;
- resource/workspace generation;
- approval validity;
- task/run status;
- any freshness conditions that cannot safely be replayed.

This reinforces KA-I-019, KA-I-033 and new KA-I-046.

## Confidence

High.

---

# 9. Pending input is source evidence whose settlement must be explicit

## Observed

Current `RunState` supports durable `pending_input`. `session_persistence.admit_pending_input()` distinguishes client-managed and server-managed ownership:

- client-managed Session input is saved before the next model call;
- server-managed continuation retains the input until the provider response proves which input occurrences were accepted.

The server path tracks accepted input IDs and retains unaccepted occurrences as pending.

## Architecture lesson

“Prepared for use,” “sent,” “accepted,” “persisted,” and “consumed” are separate source-evidence states.

This reinforces KA-I-028. Source evidence should not be removed from pending state simply because an attempt began.

## Confidence

High.

---

# 10. Lost acknowledgement remains a settlement ambiguity: #4775

## Failure evidence

Open #4775 demonstrates a client-managed Session path where:

1. `RunState.add_input()` stages logical input;
2. Session persistence commits the input;
3. the acknowledgement is lost and `Session.add_items()` raises;
4. `RunState` has no durable checkpoint proving that pending-input append committed;
5. retry sees the input as still pending;
6. the same logical input is appended again and the already-passing input guardrail runs again.

The same execution state cannot distinguish:

- fail-before-commit;
- commit-then-lost-ack.

## Architecture lesson

This is direct recurrence for KA-F-019 and KA-I-028.

It also reinforces the general settlement portion of KA-I-032: source input should be marked consumed only when integration/persistence is reconciled, and retries need stable operation/source identity sufficient to decide whether the mutation already occurred.

## Confidence

High for the reproduced issue; open status means no claim is made that current head has fully resolved it.

---

# 11. Session history can be canonical evidence for a run without being canonical world truth

## Observed

Sessions automatically load prior conversation history into subsequent runs and append new run items afterward.

That makes Session history an important source/evidence plane for a conversational execution.

But it does not carry required structured semantics for:

- verified fact;
- inferred claim;
- disputed/contradicted assertion;
- current versus historically true;
- world-valid interval;
- source trust;
- authority-use class;
- typed relationship;
- applicability scope.

## Architecture lesson

Conversation history can be canonical **for what was said/done in that conversation** while remaining raw evidence from which semantic knowledge is later derived.

This reinforces KA-I-001 and KA-I-025.

## Confidence

High.

---

# 12. Compaction is a derived destructive replacement operation

## Historical failure evidence: #4679

The earlier compaction implementation could:

1. snapshot Session history;
2. await a potentially long `responses.compact` operation;
3. let concurrent session mutations happen;
4. replace history from the stale pre-call snapshot.

Consequences included:

- a concurrent append disappearing;
- a concurrent clear being undone, resurrecting old history.

The issue is now closed.

## Current positive pattern

Current `OpenAIResponsesCompactionSession` holds `_mutation_lock` across the entire snapshot-through-replacement boundary.

It also has `_mutation_generation` semantics. Runner integration can capture the generation associated with the history it read and skip compaction if the Session history generation changed after that run appended its items.

Current source also prepares compacted output before destructive replacement and captures previous underlying items for rollback.

## Architecture lesson

This is strong current evidence for KA-I-035 and KA-I-027:

- derived replacement must know the source revision/generation it summarizes;
- replacement should not cut over against a target state it no longer represents;
- intervening mutations must be blocked, reconciled or cause retry/abort;
- rollback state should remain available until replacement settles.

It also reinforces KA-F-023 as a fixed/guarded stale-snapshot failure family.

## Confidence

High.

---

# 13. Compaction output is not exhaustive truth

## Observed

Compaction rewrites conversational input/history into a smaller representation. It can preserve enough context for later model calls, but the compacted representation is a derived projection optimized for context efficiency.

## Architecture lesson

Do not treat a compacted Session as the only provenance source if raw source evidence must remain audit-addressable.

This reinforces KA-I-011, KA-I-023 and KA-F-027.

## Confidence

High conceptually; exact provider-side compaction semantics remain profile-dependent.

---

# 14. Source/derived/presentation identity through history rewrites

## Observed

Current session persistence code tracks nested history ownership with:

- input indexes;
- digests;
- run-item identities;
- stable occurrence keys;
- reconciliation through history rewrites.

The code distinguishes object identity, stable occurrence identity and input digest while resolving which history items a nested run owns.

## Architecture lesson

This reinforces KA-I-036. A rewritten/presented item should not inherit source identity merely because it represents the same semantic content.

For Vera, derived summaries/excerpts should carry lineage to source occurrences, not overwrite or masquerade as them.

## Confidence

High.

---

# 15. Guardrail timing demonstrates knowledge/policy checks are not automatically authority gates

## Observed

Current guardrail docs explicitly distinguish:

- **parallel input guardrails**: default; agent/model/tool work may already have started before the tripwire returns;
- **blocking input guardrails**: complete before agent execution starts.

Function-tool input guardrails normally run after approval immediately before execution. Optionally they can also run before the approval interruption, and then run again after approval before the tool effect.

Tool guardrails do not universally cover every tool surface: handoffs, hosted tools, several built-in execution tools and `Agent.as_tool()` have different pipelines.

## Architecture lesson

A fact that a “guardrail exists” says nothing about whether it is an authority boundary. If policy requires no side effect before approval/check completion, the check must be blocking and positioned before authority grant/effect dispatch.

Knowledge/policy validation and execution gating must therefore be represented separately.

This reinforces KA-I-020 and KA-I-019.

## Confidence

High.

---

# 16. Revalidation and approval are different state machines

## Observed

The SDK can rerun a tool input guardrail after a human approval but before effect execution. That is a strong time-of-check/time-of-use pattern.

However, #4896 confirms that the guardrail cannot reopen an already-approved invocation into a new approval requirement.

## Architecture lesson

Vera should distinguish:

- approval state;
- policy validation state;
- current environmental precondition state;
- effect dispatch state.

A call may remain approved while becoming invalid to execute. Conversely, policy may say the operation remains allowed but requires a **new** approval because authority context changed. That should be represented as a new authority transition, not overloaded onto a boolean guardrail result.

## Confidence

High.

---

# 17. Provider cleanup demonstrates generation settlement

## Observed

Current `model_provider_lifecycle.py` creates a cleanup task for Runner-owned model providers, shields it from repeated cancellation, waits until it is done, handles cleanup failure, and only then restores cancellation to the caller.

## Architecture lesson

This reinforces KA-I-041 and KA-F-043: termination is not complete while old-generation components still own mutable resources/connections and can continue running.

ACL/Vera should treat cleanup/join/fencing as part of generation transition, not optional best effort after the new run starts.

## Confidence

High.

---

# 18. Streaming cancellation is not effect rollback

## Observed

The SDK can cancel streamed runs, but completed tool effects and already-persisted history remain separate facts.

## Architecture lesson

Cancellation needs layered status:

- caller requested cancellation;
- model/provider generation stopped;
- local background work joined;
- tool/process stopped;
- external effect committed/failed/unknown;
- session/checkpoint reconciled.

This reinforces KA-I-028 and KA-F-019.

## Confidence

High as an architectural requirement; no universal exactly-once guarantee is inferred.

---

# 19. Output guardrails distinguish presentation from evidence/effects

## Observed

Current docs describe detailed handling when a terminal tool output is rejected:

- the tool may already have executed;
- the rejected payload can be replaced with a data-free placeholder when a replay-valid call/output pair can be retained safely;
- validated call metadata may remain;
- when safe sanitization is not possible, the current response suffix can be dropped;
- a guardrail exception is treated differently from an explicit rejection verdict.

## Architecture lesson

A sanitized model-visible/persisted presentation is not proof the underlying effect never happened or that source evidence is absent.

This reinforces KA-I-036 and KA-F-032.

## Confidence

High.

---

# 20. Filesystem path identity remains a resource-identity warning

## Failure evidence: #4889

Current open #4889 reports a case-only `move_to` operation where path-string comparison can treat two lexical paths as different even when the sandbox filesystem maps them to the same file object, causing the newly written file to be removed.

## Architecture lesson

A locator/path string is not necessarily resource-object identity. Filesystem case-folding, normalization, symlinks and mount semantics can make several locators refer to one object or one locator refer to a changing object.

This adds adjacent evidence to KA-I-037 without fully promoting it: the issue strongly supports `resource identity != locator`, but does not by itself establish the full logical-resource/locator/content-digest formulation.

## Confidence

High for the reported mechanism; macOS-specific behavior in the issue was partly reasoned rather than directly run by the reporter, which is noted in the report itself.

---

# 21. Knowledge retrieval versus authority

## Observed

Sessions and context history can expose content to the model. The SDK also exposes tools and approvals.

No mechanism turns a remembered instruction into execution authority simply because it appears in Session history or `RunState` context.

## Architecture lesson

Persistent conversation text remains content. Policy/approval lives outside that text.

This reinforces KA-I-015 and KA-I-020.

## Confidence

High.

---

# 22. Epistemic state remains absent from the generic memory/session model

## Observed

The Session interface stores conversation items, not typed truth assertions.

It has no general required fields for:

- explicit user statement;
- observation;
- inference;
- verification status;
- confidence;
- contradiction/dispute;
- supersession;
- known false;
- unknown/not established;
- historical/current.

## Architecture lesson

The Agents SDK should be viewed as an execution and conversation-context system in this campaign, not the semantic truth model for Vera.

## Confidence

High.

---

# 23. Temporal truth remains application-level

## Observed

Execution state has ordering and lifecycle time, but ordinary Session/RunState data does not provide a generic proposition-level world-valid interval plus record-time history.

Approval also demonstrates a different time dimension: it may remain structurally stored while its policy context becomes stale.

## Architecture lesson

Vera needs separate world-valid time, observation time, record time, policy-version time and retention/expiry semantics.

This reinforces KA-I-008.

## Confidence

High.

---

# 24. Relationships are execution relationships, not canonical world relationships

## Observed

The SDK models:

- agent/handoff relationships;
- tool/caller relationships;
- parent/nested run ownership;
- call/output association;
- session sequence.

These are operational relationships.

They are not a canonical world-relation substrate for ownership, location, organizational membership, contradiction, evidence support or applicability.

## Architecture lesson

Agent graph/runtime lineage and knowledge relationships must remain distinct.

## Confidence

High.

---

# 25. Unknown/negative truth remains under-modeled

## Observed

An absent Session item or unavailable output does not tell the host whether a real-world proposition is:

- false;
- unknown;
- filtered;
- inaccessible;
- deleted;
- never checked;
- stale;
- superseded.

## Architecture lesson

Vera needs explicit epistemic negative/unknown states where decisions depend on them.

This reinforces KA-I-021.

## Confidence

High.

---

# 26. Scope of truth is wider than run/session scope

## Observed

`RunState` and Session scope are execution/conversation boundaries. A fact may instead apply to a person, machine, environment, project, software revision, location or time interval.

## Architecture lesson

Storage/execution scope is not proposition applicability.

This reinforces KA-I-022 conceptually; the SDK does not itself supply the structured applicability model.

## Confidence

High.

---

# 27. Full 26-question evidence matrix

| # | Evidence question | KA-9 assessment |
|---|---|---|
| 1 | Stable identity | Strong run/call/tool/origin/occurrence identity for execution; not universal semantic entity identity. |
| 2 | Identity vs namespace/principal | Session/run/tool namespaces are operational identities, not authenticated human principal identity. |
| 3 | Provenance | Strong operational lineage and occurrence metadata; canonical semantic claim/evidence provenance remains application-defined. |
| 4 | Epistemic state | Not first-class in Sessions/RunState. |
| 5 | Temporal truth | Execution ordering exists; no generic bitemporal proposition validity. Approval/policy freshness shows additional time/version axis. |
| 6 | Conflict/supersession | No canonical truth-conflict/supersession model. Compaction is history replacement, not semantic contradiction resolution. |
| 7 | Relationships | Runtime/caller/handoff relationships are strong; world semantic relationships are not modeled. |
| 8 | Permissions/sensitivity | HITL and capability identity are useful; host must own principal/policy/version/sensitivity governance. |
| 9 | Actionability | Exact call approvals, sticky tool identity and pre-effect guardrail mechanisms are strong execution evidence. |
| 10 | Knowledge vs authority | Clearly separable; Session/context content does not grant tool authority. |
| 11 | Resources | Sandbox/workspace paths are operational resources; #4889 shows locator != object identity. No full canonical resource/version envelope. |
| 12 | Canonical vs derived | Session source history, compacted history, model-visible presentation and `RunState` are distinct. |
| 13 | Structured retrieval | Sessions are ordered history, not a general structured knowledge query substrate. |
| 14 | Relationship retrieval | Runtime graph relationships exist, not canonical world-relation retrieval. |
| 15 | Full-text retrieval | Not a general core knowledge architecture feature. Backend/session implementation-specific. |
| 16 | Semantic retrieval | Not the core Session contract; external memory integrations may add it. |
| 17 | Composite retrieval | No universal structured/fulltext/semantic composite contract in core Session. |
| 18 | Context construction | Explicitly separate from persistence; history/compaction/filters determine model-visible context. |
| 19 | Poisoning/injection | Persistent conversation content remains model-visible content; guardrails/policy remain separate. |
| 20 | Concurrency | Current compaction generation/lock is a positive pattern; #4775 remains settlement ambiguity for Session append. |
| 21 | Derived integrity | Compaction now protects snapshot generation and rollback; pending inputs require settled ownership. |
| 22 | Deletion/retention | Session deletion/clearing is not complete cross-plane privacy erasure; sandbox/provider/trace planes remain separate. |
| 23 | Schema evolution | `RunState` schema is explicitly versioned and fail-fast; excellent recovery-schema reference. |
| 24 | Recovery | Strong durable RunState semantics, but external policy freshness and Session settlement must be revalidated. |
| 25 | Unknown/negative | Not first-class truth state. |
| 26 | Scope of truth | Run/session scope does not express arbitrary proposition applicability. |

---

# 28. Highest-value positive patterns for ACL/Vera

## 28.1 Semantic checkpoint versioning

Version behavior-bearing recovery state and fail closed on unknown newer versions.

## 28.2 Exact occurrence-bound approval

Bind approval to exact effect occurrence and trusted tool identity.

## 28.3 Policy-version check before resume

A parked approval must be revalidated against current authority context before the runner regains control.

## 28.4 Generation-bound destructive compaction

Hold/validate source generation across derived replacement and retain rollback state.

## 28.5 Accepted-versus-pending input identity

Track exact source occurrences through admission rather than clearing pending data on attempt start.

## 28.6 Cleanup shielding/fencing

Do not report cancellation complete while owned runtime components are still cleaning up.

---

# 29. Hostile / acceptance fixtures derived from KA-9

1. **Approval under old policy revision** — approve effect at policy P1, persist, change to P2, resume; old authority must not silently execute if P2 requires reapproval.
2. **Tool definition drift while approval parked** — schema/implementation digest changes; old approval must be invalidated or routed to compatible historical execution profile.
3. **Lost Session acknowledgement** — append commits but caller receives failure; retry must reconcile and avoid duplicate source input.
4. **Fail-before-commit versus lost-ack ambiguity** — system must represent uncertain settlement rather than guessing.
5. **Concurrent compaction plus append** — newer history must survive or compaction must abort/retry.
6. **Concurrent compaction plus clear** — clear must not be undone by stale summary replacement.
7. **Snapshot generation mismatch** — derived replacement must fail/skip when target revision changed.
8. **Parallel guardrail with side-effect tool** — prove parallel safety check cannot be used as “no effect before pass” policy gate.
9. **Preapproval + pre-effect revalidation** — conditions change during human review; final guardrail blocks effect.
10. **Provider cleanup under repeated cancellation** — old provider generation must settle/close before teardown completes.
11. **Same tool name, different origin/server** — sticky approval cannot cross trusted tool identity.
12. **Malformed tool arguments** — approval policy must fail closed rather than guess.
13. **Sanitized final output after completed tool effect** — presentation hides rejected payload but effect ledger still records tool outcome.
14. **Case-folding locator alias** — two paths denote same filesystem object; mutation logic must use resource semantics, not lexical inequality alone.
15. **Session history vs semantic truth** — contradictory user statements remain separate evidence until semantic layer resolves them.

---

# 30. Contributions to cumulative invariants

KA-9 independently reinforces or adds evidence to:

- **KA-I-001** — Session history can remain source evidence distinct from semantic/compacted derivatives.
- **KA-I-008** — operational/policy timing differs from world truth time.
- **KA-I-011** — compaction is derived state.
- **KA-I-012** — exact Session/provider/sandbox implementation matters.
- **KA-I-014** — protected context/effects require host policy.
- **KA-I-015** — persistent history remains content, not policy.
- **KA-I-017** — `RunState` semantic schema versioning is explicit.
- **KA-I-018** — exact SDK/provider/backend/profile matters.
- **KA-I-019** — authority/provenance metadata must survive pause/resume and be revalidated.
- **KA-I-020** — knowledge/context does not grant effect authority.
- **KA-I-021** — generic Session lacks structured unknown/false/disputed state.
- **KA-I-023** — compaction/transformation decisions affect future reasoning and need lineage.
- **KA-I-024** — model context construction is separate from history persistence.
- **KA-I-025** — authorship/history presence is not verification.
- **KA-I-027** — compacted projections need source generation/coverage.
- **KA-I-028** — accepted/persisted/consumed settlement drives pending-input and retry behavior.
- **KA-I-032** — #4775 supplies adjacent retry/idempotency evidence for source-input integration.
- **KA-I-035** — current compaction implementation validates/stages replacement under generation control and rollback.
- **KA-I-036** — occurrence/digest/rewritten-history identity remains distinct.
- **KA-I-041** — Runner-owned provider cleanup is shielded until old-generation cleanup settles.
- **KA-I-042** — sticky approval identity includes trusted server/tool origin for hosted MCP.

KA-9 contributes one half of new cross-project **KA-I-046**:

> Durable approval or continuation authority must be bound to the exact operation semantics and current authority context/version under which it was created; if principal, policy, capability definition or salient effect parameters change, reuse is invalid and requires a new authority/operation boundary.

The MCP half is evaluated separately in KA-10.

KA-I-037 receives adjacent filesystem evidence from #4889 but remains a candidate; the issue proves locator/object distinction but not the full locator/content-version formulation.

No final architecture rule is adopted here.

---

# 31. Contributions to cumulative failure patterns

KA-9 adds recurrence to:

- **KA-F-013** — exact package/backend/profile matters.
- **KA-F-019** — #4775 shows persistence acknowledgement and actual commit can diverge.
- **KA-F-020** — compacted/session presentation needs transformation provenance.
- **KA-F-023** — #4679 is a concrete stale-snapshot replacement failure, fixed in current source by stronger generation/locking semantics.
- **KA-F-027** — compacted context is not exhaustive source evidence.
- **KA-F-032** — sanitized/model-visible context differs from source/effect evidence.
- **KA-F-043** — provider/background generation cleanup must settle before teardown.
- **KA-F-044** — tool authority identity cannot collapse to tool name alone.

No new failure ID is created from #4896 because the current SDK behavior is explicitly intentional and maintainer guidance assigns policy-version invalidation to the application boundary. The lesson is retained as invariant evidence rather than mislabeled as an SDK defect.

No new failure ID is created for #4775 because KA-F-019 already captures the essential settlement ambiguity; duplicating it would inflate the ledger without adding a distinct failure mechanism.

---

# 32. Non-conclusions

KA-9 does **not** conclude that:

- the OpenAI Agents SDK is unsafe;
- its Sessions are intended to be a general truth database;
- every tool effect is exactly-once;
- `RunState` alone is a complete distributed effect ledger;
- every policy change requires discarding a paused run regardless of semantics;
- guardrails are ineffective;
- compaction is inherently unsafe;
- current #4775 affects every Session backend;
- current #4889 reproduces identically on every filesystem;
- ACL/Vera should adopt or reject the SDK;
- provider-managed conversation state and client-managed Session state are equivalent;
- the SDK should own Vera's canonical knowledge, policy engine or effect ledger.

---

# 33. Primary/current sources inspected

Pinned current source:

- `openai/openai-agents-python@544b8b03b8cf95e62c7f5ebb89adfc4bd66c9d1f`
- `pyproject.toml`
- `src/agents/run_state.py`
- `src/agents/run_internal/session_persistence.py`
- `src/agents/run_internal/model_provider_lifecycle.py`
- `src/agents/memory/openai_responses_compaction_session.py`
- current `docs/human_in_the_loop.md`
- current `docs/guardrails.md`

Issue evidence:

- #4775 — pending input duplicated after lost Session append acknowledgement — open.
- #4896 — policy drift/fresh approval lifecycle question — closed with maintainer guidance.
- #4679 — stale-snapshot compaction replacement — closed; current source contains generation/locking fix.
- #4889 — case-only path move/resource identity issue — open.

Official current documentation rechecked:

- https://openai.github.io/openai-agents-python/human_in_the_loop/
- https://openai.github.io/openai-agents-python/ref/run_state/
- https://openai.github.io/openai-agents-python/sessions/
- https://openai.github.io/openai-agents-python/guardrails/
- https://openai.github.io/openai-agents-python/running_agents/

---

# 34. Stop condition

KA-9 is complete when:

- current upstream/source version was verified;
- historical findings were revalidated rather than copied;
- current runtime/session changes and fresh issue evidence were inspected;
- all 26 evidence questions were evaluated;
- ledger contributions were identified conservatively;
- OpenAI evidence remained separate from MCP evidence;
- no architecture selection or implementation occurred.

This report stops at the OpenAI Agents SDK boundary. KA-10 MCP is documented separately in the same user-authorized bounded block.