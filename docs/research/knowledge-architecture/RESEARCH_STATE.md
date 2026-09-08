# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** KA-9 + KA-10 bounded research block complete; ten-project high-yield revisit sequence complete; stopped before coverage scan  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

## Governing plan

Read `CAMPAIGN_PLAN.md` before doing any further work in this campaign.

The completed Tasks 1–31 project-by-project campaign remains historical evidence. Do not restart it and do not rewrite its catalogs.

The campaign originally used one project revisit per bounded task. After KA-6, the user explicitly authorized two-project bounded blocks provided that:

- each project retains separate evidence attribution/reporting;
- the same 26 evidence questions are evaluated per project;
- cumulative ledgers are reconciled only after project-specific analysis;
- the block produces one atomic research-only commit;
- work stops before the next unauthorized campaign phase.

The user explicitly authorized the current **KA-9 OpenAI Agents SDK + KA-10 Model Context Protocol** block.

---

## Completed high-yield revisit sequence

### KA-1 — Graphiti Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/graphiti.md`

### KA-2 — Mem0 Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/mem0.md`

### KA-3 — Letta Code Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/letta-code.md`

### KA-4 — LlamaIndex Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/llamaindex.md`

### KA-5 — Mastra Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/mastra.md`

### KA-6 — LangGraph Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/langgraph.md`

### KA-7 — Google ADK Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/google-adk.md`

### KA-8 — Microsoft Agent Framework Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/microsoft-agent-framework.md`

### KA-9 — OpenAI Agents SDK Knowledge-Architecture Revisit

**Status:** complete within the user-authorized KA-9 + KA-10 bounded block.  
Detailed report: `projects/openai-agents-sdk.md`

### KA-10 — Model Context Protocol Knowledge-Architecture Revisit

**Status:** complete within the user-authorized KA-9 + KA-10 bounded block.  
Detailed report: `projects/model-context-protocol.md`

Cumulative ledgers updated:

- `invariants.md`
- `failure-patterns.md`

The planned ten-project high-yield revisit sequence is now complete.

---

## KA-9 + KA-10 block boundary and verification

- Re-read root research governance, campaign plan/state, cumulative ledgers and historical OpenAI Agents SDK / MCP reports before research writes.
- Verified the ACL starting branch head at `1cb06faac3b75cd89c2cad7f372788eb512c5c5e` (`research: complete ADK and MAF knowledge architecture block`).
- Preserved separate OpenAI and MCP project reports despite the shared block.
- Used current upstream source, current issue evidence and current official documentation where relevant.
- Evaluated both projects against all 26 campaign evidence questions.
- Reused existing invariant/failure IDs wherever possible.
- Added only one materially distinct invariant family and no new failure-pattern IDs.
- Did not modify runtime code, historical catalogs, root historical research state or historical project reports.
- Did not begin the required post-revisit coverage scan.
- Did not begin synthesis, storage selection, retrieval design or implementation.

### OpenAI Agents SDK upstream verification

Canonical repo:

`openai/openai-agents-python`

Historical Task 14 revision:

`1d471a4775bf2f40179f411824da383deb4c3fca`

Current `main` inspected:

`544b8b03b8cf95e62c7f5ebb89adfc4bd66c9d1f`

Current package metadata:

`openai-agents 0.22.1`

The current source is 27 commits ahead of the historical revision. Relevant current changes include Session/RunState persistence, compaction, guardrail documentation and runner-owned model-provider lifecycle behavior.

Current source/docs/issues inspected included:

- `src/agents/run_state.py` (`CURRENT_SCHEMA_VERSION = "1.17"`);
- `src/agents/run_internal/session_persistence.py`;
- `src/agents/run_internal/model_provider_lifecycle.py`;
- `src/agents/memory/openai_responses_compaction_session.py`;
- current HITL/guardrail/session/RunState documentation;
- #4775, #4896, #4679 and #4889.

Official current OpenAI Agents SDK web documentation was rechecked as an external/current source.

### MCP upstream verification

Canonical core repo:

`modelcontextprotocol/modelcontextprotocol`

Historical Task 15 revision:

`e76e9c572c6f2bfcb730357101acc90f2f802e02`

Current core `main` inspected:

`aa8ce049f089f92618340190d4ece141f663310d`

The core repository is seven commits ahead, but its only substantive content delta relevant here is the new Filesystems Working Group charter plus docs navigation. The released normative specification remains `2026-07-28` and the previously studied core lifecycle semantics are unchanged.

Tasks extension:

`modelcontextprotocol/ext-tasks@9263312d11a682ac83f83fe84794d4627efd22f5`

This is unchanged from the historical Task 15 report.

Current source/issues inspected included:

- core `2026-07-28` statelessness/request-response specification;
- MRTR and `requestState` security requirements;
- Tools;
- Resources/authorization/cancellation/subscription semantics revalidated from historical report;
- Tasks extension source/specification;
- new Filesystems Working Group charter;
- #3348, #3350 and #3268.

Current MCP release/specification material was also rechecked through official project web sources.

---

## Highest-value KA-9 — OpenAI Agents SDK findings

1. **`RunState` is a semantic recovery snapshot, not generic memory.** Current schema version `1.17` explicitly tracks behavior-bearing resume semantics and rejects unknown newer schema versions rather than guessing.
2. **Session history, RunState, provider continuation, sandbox/workspace and external effects are separate planes.** They should not be collapsed into one agent-state record.
3. **Exact-call approval is strong occurrence-bound authority.** Per-call approvals bind call identity; hosted MCP sticky approval additionally scopes by server label + tool name.
4. **Approval freshness across time is a separate host responsibility.** #4896 and maintainer guidance state approval is final for that invocation, while a policy-sensitive host should persist a policy/approval version and refuse to resume the old invocation if authority semantics changed.
5. **Resume is therefore a trust/authority boundary.** Principal, policy, tool/capability definition, credential/resource generation and approval validity may need to be re-established before execution resumes.
6. **Pending source input has settlement states.** Client Session persistence and server-managed acceptance differ; accepted occurrences are tracked separately from still-pending input.
7. **#4775 exposes a lost-ack ambiguity.** Session history may have committed a staged input while RunState still sees it pending, causing duplicate logical input and repeated guardrail work on retry.
8. **Compaction is derived destructive replacement.** #4679 demonstrated stale-snapshot history loss/resurrection; current source now protects snapshot-through-replacement with mutation locking/generation checks and rollback state.
9. **History rewrite needs occurrence lineage.** Current nested-history ownership uses occurrence identity/digest reconciliation rather than assuming presentation identity equals source identity.
10. **Parallel guardrails are not pre-effect gates.** Current docs explicitly warn that model/tool execution may already have begun before a parallel input guardrail trips; blocking mode is required when policy means “no execution before pass.”
11. **Preapproval and pre-effect validation are different transitions.** Tool input guardrails can run before approval and again immediately before execution.
12. **Runner-owned provider cleanup is fenced through cancellation.** Cleanup is shielded until it settles, reinforcing generation-transition closure.
13. **Output presentation and effect evidence differ.** A rejected terminal tool output may be sanitized or dropped from the replay-visible suffix even though the tool effect already occurred.
14. **#4889 adds resource-identity evidence:** two lexical paths can denote one filesystem object under case-folding; locator-string inequality is not resource-object identity.
15. **Sessions/RunState remain execution/conversation evidence, not a canonical truth ontology.** They lack general verified/inferred/disputed/superseded/world-valid-time/unknown semantics.

---

## Highest-value KA-10 — MCP findings

1. **Modern MCP remains explicitly stateless at the transport core.** An open connection/process is not a conversation, task, session or authority context.
2. **Cross-request state must use explicit identifiers/handles.** Hidden connection state is intentionally non-authoritative.
3. **MRTR continuation state is explicit and attacker-controlled.** Authority-relevant `requestState` must be integrity-protected and bound to authenticated principal, short expiry and originating method/parameter digest.
4. **Integrity does not guarantee single-use.** If a continuation must be consumed at most once, the server must enforce consumption state separately.
5. **Tasks are durable execution state machines with receiver-generated task IDs.** Task state is not canonical semantic truth and does not itself prove domain effect delivery.
6. **Cancellation request/state is not universal effect settlement.** Protocol cleanup and external-world final state remain distinct.
7. **Tools are model-controlled capabilities below host governance.** Tool availability may vary by per-request authorization; service auth does not automatically approve an exact model-selected effect.
8. **Tool name is server-local presentation/discovery identity, not globally sufficient authority identity.** Trusted server/profile/schema context matters.
9. **Resources are addressable content, not canonical truth or complete resource-version identity.** URI, logical resource and observed content/version remain distinct concepts.
10. **The new Filesystems WG is directional evidence only.** Planned create/update/delete/stat, optimistic concurrency and cache/write coherence confirm mutable-resource concerns, while host sandbox semantics and write policy remain outside that proposed wire work.
11. **#3348 remains open:** cancellation and subscription documents disagree on stream teardown semantics, reinforcing exact spec/schema/SDK profile identity.
12. **#3350 is gap evidence, not adopted protocol.** Its Tool Outcome Attestation proposal starts from the fact that protocol/HTTP success is not a shared attested delivery outcome.
13. **Core conformance and extension conformance are independently qualified.** A generic MCP/Tier claim does not prove Tasks or another extension/profile behaves identically.
14. **Prompts/resources/tool metadata remain remote content.** Transport authenticity does not convert them into Vera policy.
15. **MCP remains an interoperability substrate, not Vera's epistemic truth model.**

---

## Cross-project result: KA-I-046

The KA-9 + KA-10 block produced one materially distinct invariant and independent evidence from both projects.

### KA-I-046 — reinforced

> Durable approval or continuation authority must be bound to the exact operation semantics and current authority context/version under which it was created; if principal, policy, capability definition or salient effect parameters change, reuse is invalid and requires a new authority/operation boundary.

Independent evidence:

- **KA-9 OpenAI Agents SDK:** #4896 plus maintainer guidance — approval remains final for the invocation; policy-sensitive hosts should persist a policy/approval version and create a new call/run boundary if authority context changed before resume.
- **KA-10 MCP:** MRTR requires authority-relevant `requestState` to be protected and bound to authenticated principal, expiry and originating method/parameter digest; true at-most-once use requires server-side consumption state.

This is not a final architecture decision, but it is now strong enough for **reinforced** status in the evidence ledger.

---

## Cumulative ledger state after KA-10

### Invariants

Invariant IDs now run through **KA-I-046**.

New this block:

- **KA-I-046 — reinforced** as described above.

No other invariant was promoted to a new status solely because of this block.

Important recurrence:

- KA-I-017/018 — semantic checkpoint/profile identity;
- KA-I-023/027/035 — compaction/derived replacement provenance and generation control;
- KA-I-028/032 — settlement must drive source-input consumption/retry;
- KA-I-036 — source/derived/presentation identity;
- KA-I-041 — old-generation cleanup/fencing;
- KA-I-042 — trusted tool/origin identity;
- KA-I-043–045 — receive adjacent MCP evidence but remain candidates.

Candidates remain:

- KA-I-004
- KA-I-005
- KA-I-007
- KA-I-031
- KA-I-034
- KA-I-037
- KA-I-038
- KA-I-039
- KA-I-040
- KA-I-043
- KA-I-044
- KA-I-045

### Failure patterns

Failure IDs remain **KA-F-001 through KA-F-048**.

No new failure ID is added in KA-9 + KA-10.

Important recurrence:

- KA-F-013 — realized deployment/profile identity;
- KA-F-019 — storage/protocol/task success != full settlement;
- KA-F-020 — transformation provenance;
- KA-F-023 — stale snapshot/replacement concurrency;
- KA-F-027 — derived summary not exhaustive evidence;
- KA-F-032 — model/protocol presentation != canonical source/effect evidence;
- KA-F-043 — generation cleanup/fencing;
- KA-F-044 — name-only authority identity.

OpenAI #4896 is deliberately retained as positive invariant/host-boundary guidance rather than mislabeled as an SDK bug. MCP #3350 is deliberately retained as gap/proposal evidence rather than treated as an adopted protocol or new failure class.

---

## Current task

**No task is currently assigned.**

The ten-project high-yield revisit sequence is complete.

The campaign is stopped after KA-10.

## Planned next candidate

**Bounded coverage scan**

This is the next campaign phase required by `CAMPAIGN_PLAN.md`, but it is **not authorized merely because the ten planned revisits are complete**.

Do not begin the coverage scan until the user explicitly authorizes it.

The coverage scan should:

- review all 26 evidence questions across the completed reports/ledgers;
- identify questions with weak, single-source, contradictory or missing evidence;
- identify domains/projects that materially cover those gaps;
- avoid broad new research unless a gap justifies promoting a specific follow-up;
- preserve candidate versus reinforced status;
- surface counterevidence/qualifications;
- stop before final synthesis unless separately authorized.

## Prohibited work at this state

Do not:

- begin the bounded coverage scan without explicit authorization;
- start additional project revisits merely because they are interesting;
- synthesize the final conceptual schema;
- select a database/storage engine;
- implement retrieval or context construction;
- create embeddings;
- migrate old catalogs;
- benchmark models;
- implement ACL or Vera;
- run autonomous workers;
- convert candidate invariants into final architecture rules.

## Planned campaign sequence status

1. ~~KA-1 Graphiti~~ — complete
2. ~~KA-2 Mem0~~ — complete
3. ~~KA-3 Letta Code~~ — complete
4. ~~KA-4 LlamaIndex~~ — complete
5. ~~KA-5 Mastra~~ — complete
6. ~~KA-6 LangGraph~~ — complete
7. ~~KA-7 Google ADK~~ — complete
8. ~~KA-8 Microsoft Agent Framework~~ — complete
9. ~~KA-9 OpenAI Agents SDK~~ — complete
10. ~~KA-10 Model Context Protocol~~ — complete
11. Bounded coverage scan — **next candidate; not authorized**

## Stop point

KA-9 OpenAI Agents SDK and KA-10 MCP research are complete as one user-authorized bounded block with separate reports and one cumulative ledger reconciliation. The ten-project revisit sequence is complete. No coverage scan, final synthesis, storage/retrieval selection, schema selection or implementation work has begun.