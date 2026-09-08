# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** KA-7 + KA-8 bounded research block complete; stopped before next project  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

## Governing plan

Read `CAMPAIGN_PLAN.md` before doing any work in this campaign.

The completed Tasks 1–31 project-by-project campaign remains historical evidence. Do not restart it and do not rewrite its catalogs.

The campaign plan originally described one revisit per bounded task. After KA-6, the user explicitly authorized **KA-7 Google ADK and KA-8 Microsoft Agent Framework together as one bounded research block** to reduce per-task overhead while preserving separate evidence attribution and reports. That user instruction authorizes only this two-project block; it does not authorize later queue items.

## Completed tasks

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

**Status:** complete within the user-authorized KA-7 + KA-8 bounded block.  
Detailed report: `projects/google-adk.md`

### KA-8 — Microsoft Agent Framework Knowledge-Architecture Revisit

**Status:** complete within the user-authorized KA-7 + KA-8 bounded block.  
Detailed report: `projects/microsoft-agent-framework.md`

Cumulative ledgers updated:

- `invariants.md`
- `failure-patterns.md`

---

## KA-7 + KA-8 block boundary and verification

- Re-read root research governance, campaign plan/state, cumulative invariant/failure ledgers and the historical Google ADK / Microsoft Agent Framework reports before writing campaign changes.
- Verified the ACL branch remained on the legitimate KA-6 LangGraph commit `df5d7c1a4fdcf3072107ae90c1aac59b93c73473` before any KA-7/KA-8 branch mutation.
- Confirmed no partial KA-7 or KA-8 files existed on the branch; research report blobs were staged detached from the branch until the final atomic commit.
- Preserved the user's explicit block-level authorization while keeping Google and Microsoft evidence in separate project reports.
- Did not reopen or rewrite the historical Tasks 1–31 catalogs/reports.
- Did not begin OpenAI Agents SDK research.

### Google ADK upstream verification

- Canonical repo: `google/adk-python`.
- Current `main`: `b0180620f4c2f4f4467a89c37a30f75bf849700b`.
- Current source version: `google-adk 2.8.0`.
- This is the same source revision used by the historical Task 22 report, so KA-7 is a deeper knowledge-substrate pass plus current issue verification rather than a source-delta study.
- Inspected current session model, database session revision markers, generic memory service, `MemoryEntry`, Vertex AI Memory Bank integration, confirmation processing, resumability contracts, A2A/MCP boundaries and current issue evidence.
- Evaluated all 26 campaign evidence questions.

### Microsoft Agent Framework upstream verification

- Canonical repo: `microsoft/agent-framework`.
- Current `main`: `44dc76ce818b779a2ccf4ed73e0be505ec1552c8`.
- Current Python core version: `agent-framework-core 1.17.0`.
- Historical Task 21 used older upstream `afdc0db...`; KA-8 therefore includes a meaningful implementation-delta review.
- Inspected current workflow checkpoint lineage, staged/committed state, edge-runner delivery state, restore/orphan-task protection, session/history storage, Harness `MemoryContextProvider`, file-access/approval surfaces, serialization/profile behavior and current issue/PR evidence.
- Evaluated all 26 campaign evidence questions.

### Evidence handling rules retained

- Open issues are scoped failure evidence, not claims of universal production frequency.
- Merged/current source is preferred when it materially changes the interpretation of an older issue.
- A project-specific report does not borrow the other project's evidence except where it explicitly identifies independent recurrence in the cumulative block.
- Existing invariant/failure IDs are reused whenever the new evidence matches an existing concept; new IDs are created only for materially distinct concepts.
- No final architecture rule is selected during the evidence campaign.

---

## Highest-value KA-7 — Google ADK findings

1. **Session state and long-term memory are separate planes.** `Session`/events handle conversation/execution continuity; `BaseMemoryService` handles longer-lived `(app_name, user_id)` memory.
2. **Operational IDs are not universal semantic identity.** Session IDs, event IDs, function-call IDs, memory IDs and storage update markers solve different lifecycle problems.
3. **Current #7058 shows capability name != occurrence identity.** Two concurrent same-name streaming tool calls can overwrite task tracking so one survives teardown.
4. **Database session storage provides a strong positive revision pattern.** `_storage_update_marker`, locks and stale-session rejection distinguish a persisted revision from a generic mutable session object.
5. **Storage revision != truth revision.** A compare-and-write marker prevents stale mutation but does not verify semantic truth.
6. **`MemoryEntry` is useful provenance scaffolding but not a complete epistemic assertion.** It has content/ID/author/timestamp/metadata without universal verified/inferred/disputed/current/superseded/valid-interval fields.
7. **Memory/time semantics are multi-purpose.** Event/memory time, storage/update time and managed TTL/revision expiration are distinct.
8. **Managed Memory Bank is a derived/profile-dependent memory plane.** Generation/consolidation/revision behavior depends on backend/service/configuration.
9. **Managed ingest can be asynchronous.** Current source can schedule Memory Bank ingestion in a background task and return before remote settlement.
10. **Exact-call tool confirmation is a positive pattern.** Current confirmation logic resolves the original call and validates ID/name/args/tool requirements before applying approval.
11. **Exact call binding still needs authenticated principal binding.** A message/event role or memory namespace does not prove which real principal supplied authority.
12. **#6721 shows same function name != same continuation/origin.** A relayed remote confirmation can lose resume semantics when classification keys only on shared function name.
13. **#7060 shows transport liveness != remote logical-session validity.** A cached MCP session can be dead server-side while HTTP transport remains alive.
14. **A2A boundaries can change state semantics.** #6854 reports state not transparently crossing remote agent boundaries, so in-process behavior cannot define a distributed state contract.
15. **Resumability is explicitly best-effort and at-least-once.** Temporary/in-memory state is lost and resumed tools must be idempotent.
16. **Generic memory delete/forget is not a complete privacy-erasure contract.** Raw session events, managed derived memory and external copies remain separate planes.
17. **Knowledge retrieval does not grant tool authority.** Scope strings and model-visible content remain separate from authenticated principal/policy.
18. **ADK is strongest here as evidence for session/memory/call/remote-session boundaries, not as a complete general Vera truth ontology.**

---

## Highest-value KA-8 — Microsoft Agent Framework findings

1. **MAF now exposes both execution-recovery and knowledge-memory layers.** Current source provides a rich comparative substrate for ACL/Vera boundaries.
2. **Checkpoint lineage is explicit.** `checkpoint_id` + `previous_checkpoint_id` define history; current docs explicitly warn `iteration_count` is not unique.
3. **Hidden behavior-bearing delivery state must be checkpointed.** Merged PR #7948/current source carries fan-in edge state under `_edge_state` because omitting it caused lost or stale restored behavior.
4. **Old-generation work must be cancelled and joined before restore.** Current edge-delivery source explicitly prevents orphan siblings from mutating restored state after a failed superstep.
5. **Reproduced #7859 shows failed staged writes can leak into later runs.** `State._pending` can survive a failed generation and later be committed by a successful run when failure paths do not discard it.
6. **Harness memory has a clean layered shape:** raw transcript archive -> extracted topic records -> rebuildable `MEMORY.md` -> selected model context.
7. **Topic records retain contributing session IDs.** This provides useful coarse provenance but not claim-level evidence/derivation identity.
8. **Memory extraction/consolidation are semantic transforms.** Consolidation can remove duplicates and drop memories judged stale, so it needs transformation provenance/restraint.
9. **MAF's memory merge locks are process/event-loop/profile scoped.** They do not establish cross-replica conditional-write semantics for every backing store.
10. **Storage/memory owner/isolation keys are not authenticated principal identity.** Current #8147 further exposes lifecycle/hosting semantics around isolation-key providers.
11. **Persistent knowledge read vs mutation authority is a distinct policy boundary.** Current `MemoryContextProvider` gives model tools for read/search/write/delete/consolidate; knowledge mutation needs separately governable authority classes in Vera.
12. **Current file-access source explicitly warns about autoapproval by tool name.** Another local implementation using a trusted file-tool name may inherit approval and bypass the intended human boundary.
13. **Merged PR #6966 is a positive exact-invocation approval pattern.** Approval is bound to call ID, function, args, security label, session and response details and consumed once.
14. **Pending authority state needs terminal closure.** #7872 and reproduced #7890 show unresolved tool/approval state can remain indefinitely or accumulate without bound.
15. **Reproduced #8140 shows live/model projection can be clean while durable state is corrupt.** The model-facing list is deduplicated but the persisted AG-UI snapshot can retain duplicated tool calls and reopen an already-executed approval after reload.
16. **Context is explicitly partial.** Only selected topics/recent turns are auto-loaded, so prompt absence is not canonical absence.
17. **Workflow recovery remains distinct from external effect settlement.** Strong checkpointing does not imply exactly-once outside-world effects.
18. **MAF is strong evidence for recovery lineage, state-plane separation and layered memory, not a complete epistemic/world-relationship ontology.**

---

## Cross-project recurrence produced by the bounded block

The larger two-project unit produced two immediately reinforced concepts that would have remained single-project candidates if the projects had been closed in isolation.

### KA-I-041 / KA-F-043 — background occurrence identity and generation fencing

Independent evidence:

- Google ADK #7058: same-name concurrent streaming calls overwrite task tracking, leaving an orphan after run teardown.
- Microsoft Agent Framework current restore/orphan-task source: sibling work must be cancelled and awaited because old-generation tasks can mutate state after checkpoint restore.

Result:

- **KA-I-041 — reinforced**
- **KA-F-043 — reinforced**

### KA-I-042 / KA-F-044 — trusted tool/continuation identity cannot be name-only

Independent evidence:

- Google ADK #6721: same confirmation function name but different remote/local origin changes continuation semantics.
- Microsoft Agent Framework current file-access source: local autoapproval keys on tool name and explicitly warns name collisions can bypass the human boundary.

Result:

- **KA-I-042 — reinforced**
- **KA-F-044 — reinforced**

This supports continuing carefully bounded multi-project units where evidence attribution remains separate and block-level recurrence is reconciled only after each project report is complete.

---

## Cumulative ledger changes after KA-7 + KA-8

### New/changed invariants

- **KA-I-041 — reinforced:** every mutating concurrent/background operation needs occurrence identity bound to run/generation plus settle/cancel/fence semantics across generation transitions.
- **KA-I-042 — reinforced:** authority-bearing tool/continuation classification must bind trusted origin/implementation/occurrence/schema profile, not display/function name alone.
- **KA-I-043 — candidate:** persistent-knowledge mutation authority is policy-distinct from read/retrieval authority; append/revise/delete/consolidate/ownership changes need separate action classes.
- **KA-I-044 — candidate:** transport liveness is distinct from logical remote-session/continuation validity.
- **KA-I-045 — candidate:** pending authority/effect-continuation records need explicit terminal/expiry/drain semantics and bounded retention.
- MAF adds independent evidence to raw evidence vs derived memory, source/derived/presentation identity, transformation provenance, derived coverage and consolidation settlement families.
- Google ADK and MAF add recurrence to namespace/principal, temporal, backend/profile, context-construction and mutation-settlement families.

### New/changed failure patterns

- **KA-F-043 — reinforced:** background/mutating lifecycle coarsened or unfenced across generation change allows stale/orphan work to mutate post-teardown/restored state.
- **KA-F-044 — reinforced:** name-only authority/continuation classification lets same-name different-origin/implementation operations inherit or lose approval semantics.
- **KA-F-045 — observed:** memory retrieval authority implicitly extends to persistent append/delete/consolidation without an independent knowledge-mutation authority decision.
- **KA-F-046 — observed:** remote logical-session validity inferred from transport liveness causes retries to reuse a dead remote session generation.
- **KA-F-047 — observed:** staged mutation state from a failed/cancelled operation survives and later commits under an unrelated successful run.
- **KA-F-048 — observed:** pending approval/tool-continuation state lacks complete terminal/expiry/drain lifecycle and remains actionable or accumulates after its originating interaction.
- KA-F-032 gains ADK remote-projection and MAF #8140 live-vs-durable projection evidence.
- KA-F-038 gains MAF #8140 adjacent recurrence because durable historical duplication can reopen consumed approval state after reload.

No invariant/failure pattern becomes a final architecture rule during this block.

---

## Current task

**No task is currently assigned.**

The campaign is stopped after the user-authorized KA-7 + KA-8 bounded block.

## Planned next candidate

**KA-9 — OpenAI Agents SDK Knowledge-Architecture Revisit**

This is the next planned revisit in `CAMPAIGN_PLAN.md`, but queue order is **not authorization**.

Do not begin KA-9 until the user explicitly instructs the next bounded task/block to start.

When authorized, OpenAI Agents SDK must be researched against current upstream source/docs/issues and evaluated against all 26 evidence questions. Do not silently include MCP or later projects unless the user explicitly authorizes another multi-project block.

## Prohibited work at this state

Do not:

- begin OpenAI Agents SDK, MCP or any later revisit without explicit authorization;
- synthesize the final conceptual schema;
- select a database/storage engine;
- implement retrieval;
- create embeddings;
- migrate the old catalogs;
- benchmark models;
- implement ACL or Vera;
- run autonomous workers.

## Planned revisit queue

For orientation only; queue order is not authorization:

1. ~~KA-1 Graphiti~~ — complete
2. ~~KA-2 Mem0~~ — complete
3. ~~KA-3 Letta Code~~ — complete
4. ~~KA-4 LlamaIndex~~ — complete
5. ~~KA-5 Mastra~~ — complete
6. ~~KA-6 LangGraph~~ — complete
7. ~~KA-7 Google ADK~~ — complete
8. ~~KA-8 Microsoft Agent Framework~~ — complete
9. OpenAI Agents SDK — not started / not authorized
10. Model Context Protocol — not started / not authorized

After the planned revisits, the campaign plan requires a bounded coverage scan before any additional project revisit is promoted.

## Stop point

KA-7 Google ADK and KA-8 Microsoft Agent Framework research are complete as one user-authorized bounded block with separate reports and one cumulative ledger reconciliation. No OpenAI Agents SDK/MCP research, final synthesis, storage/retrieval selection, schema selection or implementation work has begun.
