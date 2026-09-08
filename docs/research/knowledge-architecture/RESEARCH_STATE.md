# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** ten-project high-yield revisit sequence and bounded coverage scan complete; stopped before promoted Agno revisit  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

## Governing plan

Read `CAMPAIGN_PLAN.md` before doing any further work in this campaign.

The completed Tasks 1–31 project-by-project campaign remains historical evidence. Do not restart it and do not rewrite its catalogs.

The ten high-yield knowledge-architecture revisits are complete. The post-revisit coverage scan required by `CAMPAIGN_PLAN.md` is also complete.

Detailed project-specific evidence remains in:

- `projects/graphiti.md`
- `projects/mem0.md`
- `projects/letta-code.md`
- `projects/llamaindex.md`
- `projects/mastra.md`
- `projects/langgraph.md`
- `projects/google-adk.md`
- `projects/microsoft-agent-framework.md`
- `projects/openai-agents-sdk.md`
- `projects/model-context-protocol.md`

Coverage-scan detail is in:

- `COVERAGE_SCAN.md`

Cumulative evidence ledgers remain:

- `invariants.md`
- `failure-patterns.md`

---

## Completed campaign tasks

1. **KA-1 — Graphiti Knowledge-Architecture Revisit** — complete
2. **KA-2 — Mem0 Knowledge-Architecture Revisit** — complete
3. **KA-3 — Letta Code Knowledge-Architecture Revisit** — complete
4. **KA-4 — LlamaIndex Knowledge-Architecture Revisit** — complete
5. **KA-5 — Mastra Knowledge-Architecture Revisit** — complete
6. **KA-6 — LangGraph Knowledge-Architecture Revisit** — complete
7. **KA-7 — Google ADK Knowledge-Architecture Revisit** — complete
8. **KA-8 — Microsoft Agent Framework Knowledge-Architecture Revisit** — complete
9. **KA-9 — OpenAI Agents SDK Knowledge-Architecture Revisit** — complete
10. **KA-10 — Model Context Protocol Knowledge-Architecture Revisit** — complete
11. **Bounded post-revisit coverage scan** — complete

No final architecture rule, storage choice, retrieval implementation or ACL/Vera implementation has been authorized by completion of these tasks.

---

## Coverage-scan boundary and verification

The user explicitly authorized the required bounded coverage scan after KA-10.

The scan:

- re-read root research governance, campaign plan/state and cumulative ledgers;
- verified the branch began at `5f22e168cec42a4df3c58f21429a33615b721758` (`research: complete OpenAI Agents SDK and MCP knowledge architecture block`);
- reviewed the 17 completed historical project reports not already included in KA-1 through KA-10;
- applied the campaign plan's uniqueness test rather than automatically deep-revisiting every project;
- reviewed all 26 evidence questions for strong, partial and weak coverage;
- identified project gaps separately from domain/standards gaps;
- did not recheck promoted-project upstream source during the scan;
- therefore did not change invariant/failure status from historical report evidence alone;
- did not begin Agno, standards research, retrieval requirements, hostile scenarios, synthesis or implementation.

Historical reports scanned:

- Pydantic AI / Harness
- Cline
- promptfoo
- Strands Harness SDK
- Codex
- OpenHands
- SWE-agent / SWE-ReX / mini-swe-agent
- llama.cpp
- Goose
- Ollama
- Gemini CLI
- LiteLLM
- vLLM
- OpenCode
- smolagents
- Agno
- CrewAI

---

## Coverage-scan result

### One project promoted: Agno

The scan promotes **Agno only** to a future separately authorized bounded knowledge-architecture revisit.

Why Agno is unique enough:

- the historical report contains first-class persistent `UserMemory` / `MemoryManager` mutation behavior;
- issue/current-source evidence recorded in that report shows an LLM-facing `clear_memory` path can call unscoped database-level `clear_memories()`;
- with multiple users sharing the database, a clear initiated through one user's memory-management surface can remove another user's memory;
- this directly targets persistent-knowledge ownership and destructive mutation scope, not merely generic tool permissions or sandboxing;
- it can potentially independently reinforce `KA-I-034` and `KA-I-043`, and strengthen/refine `KA-F-045`, **but only after current-upstream revalidation**.

Suggested future task label:

**KA-11 — Agno Knowledge-Architecture Revisit**

This label is orientation only. Queue position is not authorization.

### No other historical project promoted

The other 16 reports contain useful evidence but do not pass the uniqueness threshold for another full KA revisit now.

Key reasons:

- CrewAI memory/consolidation/prompt-injection behavior substantially overlaps Mem0/Mastra/MAF/Letta.
- OpenHands, Goose, Codex, Gemini CLI, Cline, Strands, OpenCode and Pydantic AI primarily deepen execution/recovery/authority/profile families already well covered.
- promptfoo is primarily evaluator/verifier evidence, not missing knowledge semantics.
- smolagents and the SWE-agent lineage primarily reinforce thin-loop/execution-boundary and delegation lessons.
- llama.cpp, LiteLLM and vLLM are runtime/gateway profile evidence rather than a missing knowledge model.
- Ollama contains useful content-addressed artifact evidence, but the efficient follow-up is the later general resource/artifact identity study rather than a whole Ollama KA revisit.

---

## Twenty-six-question coverage summary

### Strong enough for requirements without another project revisit

- 1 Stable identity
- 2 Identity versus namespace
- 10 Knowledge versus authority
- 12 Canonical versus derived state
- 13 Structured retrieval
- 15 Full-text retrieval
- 16 Semantic retrieval
- 17 Composite retrieval
- 18 Context construction
- 19 Memory poisoning / prompt injection
- 20 Concurrency
- 21 Derived-state integrity
- 24 Recovery semantics

### Requirement evidence adequate, but later formal/domain research still needed

- 3 Provenance
- 5 Temporal truth
- 6 Conflict and supersession
- 22 Deletion and retention
- 23 Schema/version evolution

### Weak/under-specified positive semantics; later gap research required

- 4 Epistemic state
- 7 Relationships
- 9 Actionability
- 11 Resources and artifacts
- 14 Relationship retrieval
- 25 Unknown/negative knowledge
- 26 Scope of truth

### Project follow-up plus later formal gap work

- 8 Permissions and sensitivity — **Agno promoted** for persistent-memory ownership/mutation scope; later ABAC/ReBAC/privacy work still needed.

---

## Cumulative ledger state after the scan

### Invariants

Invariant IDs remain **KA-I-001 through KA-I-046**.

No invariant status changes in the coverage scan.

Candidates that remain especially relevant:

- KA-I-004 — identity merge/split is auditable/reversible
- KA-I-005 — ambiguous/unresolved identity is representable
- KA-I-007 — governed relationship semantics
- KA-I-031 — active context identifies exact settled knowledge revision
- KA-I-034 — private/shared knowledge ownership and explicit read/write authority
- KA-I-037 — logical resource vs locator vs observed content/version digest
- KA-I-038 — canonical reads use snapshot/value semantics or explicit mutation contract
- KA-I-039 — persistence round-trip preserves semantic metadata
- KA-I-040 — live/replay transition equivalence
- KA-I-043 — knowledge mutation authority distinct from retrieval
- KA-I-044 — transport liveness distinct from logical continuation validity
- KA-I-045 — pending authority/continuation terminal-expiry lifecycle

Coverage-scan disposition:

- **Agno follow-up:** KA-I-034 and KA-I-043.
- **Identity/entity-resolution gap:** KA-I-004 and KA-I-005.
- **Relationship/ontology gap:** KA-I-007.
- **Resource/artifact gap:** KA-I-037.
- **Schema/recovery/hostile-test follow-up:** KA-I-038–040.
- **Retrieval/context requirements:** KA-I-031.
- **Runtime/authority hostile tests:** KA-I-044–045.

### Failure patterns

Failure IDs remain **KA-F-001 through KA-F-048**.

No new failure ID and no status change is made during the scan.

Agno's historical destructive-memory-scope evidence must be reverified before deciding whether it:

- independently reinforces existing `KA-F-045`;
- is better represented as a narrower scope failure under `KA-F-001`/`KA-F-045`; or
- warrants a materially distinct new failure class.

---

## Prioritized later gap-research map

These are candidates only; none is authorized automatically.

### Priority A — epistemic, temporal, conflict and negative-knowledge semantics

Questions: 4, 5, 6, 25, 26.

Candidate subjects:

- temporal/bitemporal data semantics;
- event sourcing and correction history;
- identity/entity resolution;
- structured assertion applicability.

### Priority B — relationships and ontology evolution

Questions: 7 and 14, plus parts of 23/26.

Candidate subjects:

- controlled relationship vocabularies;
- relationship provenance/time;
- ontology evolution and migration;
- canonical relationship truth versus derived association graphs.

### Priority C — formal provenance

Question: 3 plus parts of 11/21/23.

Candidate subject:

- W3C PROV and related evidence-lineage standards, bounded to ACL/Vera usefulness.

### Priority D — knowledge authorization, purpose and sensitivity

Question: 8 plus 9/10/22.

After Agno, candidate subjects:

- ABAC/ReBAC-style knowledge access;
- ownership/shared/private domains;
- read/write/delete/consolidate/use-for-automation distinctions;
- purpose/sensitivity/retention.

### Priority E — content-addressed resource/artifact identity

Question: 11.

Candidate subjects:

- logical resource identity;
- locators/replicas;
- immutable content digest/version;
- extraction/derivation provenance;
- cache/index/embedding relationships.

Use Ollama and LlamaIndex as implementation examples rather than promoting a whole Ollama revisit.

### Priority F — privacy deletion and retention

Question: 22.

Candidate subjects:

- canonical/derived/cache/backup erasure;
- audit retention versus user-data retention;
- tombstones/fencing;
- delayed cleanup and erasure verification.

### Priority G — non-AI operational-domain validation

Question: 26 and generality of the eventual model.

Candidate subject:

- Home Assistant / Matter-style devices, entities, locations, sensor observations, stale/unavailable state, capabilities and shared-household authority.

This is intended to prevent AI/coding research vocabulary from becoming the shape of Vera's general knowledge system.

---

## Current task

**No task is currently assigned.**

The bounded coverage scan is complete.

## Planned next candidate

**KA-11 — Agno Knowledge-Architecture Revisit**

This is the only project promoted by the coverage scan, but it is **not authorized merely because it is next**.

When explicitly authorized, the Agno revisit should be narrow:

- reverify current upstream rather than trusting the historical report alone;
- focus on persistent memory ownership and subject/domain scope;
- distinguish authenticated principal from `user_id`/storage scope;
- inspect memory read/add/update/delete/clear/consolidate authority separately;
- inspect shared/team/agent/user memory domains where current source provides them;
- inspect deletion settlement/provenance/epistemic/temporal fields only where they bear on the 26 questions;
- reuse existing invariant/failure IDs unless evidence is materially distinct;
- research/docs only;
- one atomic commit;
- stop before any standards/gap task.

## Prohibited work at this state

Do not:

- begin Agno without explicit authorization;
- begin standards/domain gap research automatically;
- begin retrieval-requirements questions;
- begin hostile/adversarial scenario review;
- synthesize the final conceptual schema;
- select a database/storage engine;
- implement retrieval or context construction;
- create embeddings;
- migrate historical catalogs;
- benchmark models;
- implement ACL or Vera;
- run autonomous workers;
- convert candidate invariants into final architecture rules.

## Stop point

The ten high-yield revisits and the bounded coverage scan are complete. One historical project, Agno, is promoted for a separately authorized current-upstream revisit. The remaining weak evidence areas are classified as later standards/domain gaps rather than excuses to restart broad agent-framework research. No Agno revisit, gap research, retrieval study, hostile review, synthesis, storage selection or implementation has begun.