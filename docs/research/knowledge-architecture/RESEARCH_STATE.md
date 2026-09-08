# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** ten-project high-yield revisit sequence, bounded coverage scan and promoted KA-11 Agno revisit complete; stopped before standards/domain gap research  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

## Governing plan

Read `CAMPAIGN_PLAN.md` before doing any further work in this campaign.

The completed Tasks 1–31 project-by-project campaign remains historical evidence. Do not restart it and do not rewrite its catalogs.

The following campaign work is complete:

- ten planned high-yield knowledge-architecture revisits;
- one bounded post-revisit coverage scan;
- one coverage-scan-promoted project revisit: Agno.

No final architecture rule, schema, storage choice, retrieval implementation or ACL/Vera implementation is authorized by completion of these tasks.

Detailed reports:

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
- `projects/agno.md`

Coverage scan:

- `COVERAGE_SCAN.md`

Cumulative ledgers:

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
12. **KA-11 — Agno Knowledge-Architecture Revisit** — complete

---

## Coverage-scan result retained

The coverage scan reviewed the 17 historical project reports not already included in KA-1 through KA-10:

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

Agno was the only project promoted because its historical evidence exposed a persistent-knowledge ownership/mutation failure not adequately covered by the ten high-yield revisits.

The other reports either reinforced already-established execution/recovery/authority/profile families or pointed more efficiently to standards/domain gap research.

---

## KA-11 boundary and verification

The user explicitly authorized KA-11 after the coverage scan.

KA-11:

- verified the ACL starting branch at coverage-scan checkpoint `4b10868c26a609c657b97a41298edd0fa553c232`;
- re-read campaign state, cumulative ledgers and historical Agno report;
- rechecked current Agno upstream rather than treating the historical report as current proof;
- evaluated Agno against all 26 evidence questions;
- focused on persistent memory ownership, destructive mutation scope, authenticated principal versus `user_id`, user/global/custom sharing domains, identity migration, ambiguity handling, fact supersession/history, context projection, concurrency and deletion/retention;
- reused existing invariant/failure IDs wherever possible;
- added one materially distinct failure class only;
- did not modify runtime code, historical catalogs, root historical research state or historical project reports;
- did not begin standards/domain gap research, retrieval requirements, hostile scenarios, synthesis, schema/storage selection or implementation.

### Current Agno upstream verification

Canonical repo:

`agno-agi/agno`

Historical Task 28 profile:

- stable `v3.0.6`;
- historical main `d703c34f3abf3c41275d3fb2da6e0518a8881f24`.

Current main inspected:

`e75921a683d015e82d271ca96e52b11beec095e1`

Current package / stable release:

`3.0.7` / `v3.0.7`

Current source/issues inspected included:

- `libs/agno/agno/memory/manager.py`;
- `libs/agno/agno/tools/memory.py`;
- `libs/agno/agno/db/base.py`;
- SQLite memory/session storage source;
- `libs/agno/agno/os/routers/memory/memory.py`;
- `libs/agno/agno/os/middleware/user_scope.py`;
- `libs/agno/agno/learn/config.py`;
- `libs/agno/agno/learn/schemas.py`;
- `libs/agno/agno/learn/utils.py`;
- `libs/agno/agno/learn/stores/user_memory.py`;
- `libs/agno/agno/learn/stores/entity_memory.py`;
- `libs/agno/agno/learn/migrations.py`;
- current unit-test references for entity identity/isolation;
- issue #9983 and comments;
- PR #9986;
- issue #8334.

---

## Highest-value KA-11 findings

### 1. #9983 remains current, but its scope must be stated precisely

Current 3.0.7/main still contains the generic `MemoryManager` `clear_memory` tool closure calling database-global `db.clear_memories()` in sync and async variants.

Agno also already has correctly user-scoped `clear_user_memories(user_id)` / async equivalents.

Issue #9983 remains open and proposed fix PR #9986 remains open/unmerged.

Current ordinary create/update extraction has been narrowed and explicitly disables clear-all. Therefore KA-11 does **not** claim every normal Agno memory update exposes global clear. The defect is bounded to paths that actually expose the generic clear tool.

Architecture lesson:

> database-global administration and subject-scoped user forgetting are different capability identities and must not share authority merely because both are called “clear memory.”

### 2. Current `MemoryTools` drops owner scope on ID-based update/delete

Current standalone `MemoryTools`:

- scopes `get_memories` by `run_context.user_id`;
- stamps `user_id` on `add_memory`;
- but `update_memory(memory_id)` fetches by bare `memory_id` without current user scope;
- and `delete_memory(memory_id)` fetches/deletes by bare `memory_id` without current user scope.

The BaseDb interface makes `user_id` optional on lookup/delete. SQLite only adds an owner predicate when a user ID is provided.

Current AgentOS REST memory deletion demonstrates the intended safer pattern: resolve authenticated effective user scope and pass it into the DB mutation.

KA-11 did not find a current issue or execute a PoC for this exact path; it is recorded as source-observed failure semantics.

New **KA-F-049** captures this reusable class.

### 3. AgentOS now has explicit authenticated user-scope machinery

Current user-scope middleware explicitly separates:

- authenticated principal;
- storage `user_id`;
- admin unscoped access;
- service-account self-scope;
- opt-in human/JWT user isolation;
- scheduler ownership.

The source warns new routes can silently bypass isolation if they omit the helper/threaded user scope.

This is strong positive evidence for principal/scope separation, but also shows authorization correctness is end-to-end and surface-specific.

### 4. Personal/shared/custom knowledge domains are explicit

Current Learning configuration distinguishes:

- user profile — user scope;
- user memory — user scope;
- session context — session scope;
- decision log — agent scope;
- learned knowledge — user/global/custom namespace;
- entity memory — user/global/custom namespace.

This independently reinforces the need for different ownership/read-write semantics across personal and shared domains.

### 5. #8334's old cross-user EntityMemory collision is fixed in current source

Issue #8334 remains open but its reported vulnerable user-less entity key is no longer current behavior.

Current `build_learning_id()`:

- requires `user_id` for `namespace="user"` EntityMemory;
- includes a fixed-width digest of user identity in the deterministic row key;
- avoids raw user IDs in URL/log-visible IDs;
- prevents delimiter-shifting/crafted-ID collisions;
- gives two users with the same entity name/type different keys.

Current source also includes explicit migration/quarantine logic for old user-less keys.

The migration:

- rekeys recoverable rows;
- merges safe old/new duplicates;
- reports/quarantines contaminated rows;
- does not silently reassign mixed-owner data;
- verifies replacement before deleting source;
- acknowledges lack of transaction/CAS over the whole migration and instructs offline execution.

This is positive identity/migration evidence, not a claim #8334 is still exploitable.

### 6. Ambiguous identity is intentionally preserved

Current EntityMemory explicitly handles same-name siblings and ambiguous references.

Source/tests show:

- same name across different real entity types can remain separate;
- ambiguous operations refuse to guess;
- qualified forms such as `project/Harbor` can disambiguate;
- only an `unknown` placeholder can safely merge into a real type;
- source comments state fragmentation is recoverable while wrong merge is not because there is no general unmerge.

This independently reinforces **KA-I-005**.

It does **not** reinforce KA-I-004's reversible merge/split requirement; Agno is evidence for why such a requirement matters.

### 7. Entity facts/history are stronger than plain memory prose

Current EntityMemory supports:

- fact IDs;
- events with dates;
- relationships with IDs/direction;
- fact retirement using `superseded_at`/`superseded_by` rather than deletion;
- archived entities excluded from current recall but retained for search/history;
- visible bounded context projections.

This reinforces current-vs-history and non-destructive supersession requirements.

### 8. Supersession remains model-derived

Current EntityMemory uses an LLM supersession judge with exact old fact IDs and a configurable default confidence threshold of 0.8.

This is structurally safer than unrestricted rewriting, but the decision still lacks required source-trust/verification/derivation provenance for high-risk truth retirement.

### 9. Epistemic and bitemporal semantics remain incomplete

Agno supplies useful fields and domain decomposition, but no substrate-wide required semantics for:

- explicit vs inferred vs verified vs disputed;
- known false vs unknown vs not established;
- source trust;
- world-valid intervals distinct from record/update time.

The standards/domain gap phase remains necessary.

### 10. Delete/clear/retire/archive/quarantine/purge are distinct

Agno's multiple deletion-like operations reinforce that “forget” is not one storage verb and ordinary deletion is not proof of privacy erasure across transcripts, derived state and backups.

---

## Cumulative ledger state after KA-11

### Invariants

Invariant IDs remain **KA-I-001 through KA-I-046**.

Status changes:

- **KA-I-005 — candidate → reinforced**
  - Graphiti + Agno independent evidence for explicit ambiguity / refusal to force merge.
- **KA-I-034 — candidate → reinforced**
  - Letta + Agno independent evidence for personal/shared ownership and explicit read/write authority.
- **KA-I-043 — candidate → reinforced**
  - Microsoft Agent Framework + Agno independent evidence that persistent-knowledge mutation classes require policy separation from retrieval.

Candidates remaining:

- KA-I-004
- KA-I-007
- KA-I-031
- KA-I-037
- KA-I-038
- KA-I-039
- KA-I-040
- KA-I-044
- KA-I-045

Important Agno recurrence without status changes:

- KA-I-003 — namespace/user field != authenticated principal;
- KA-I-006/009 — non-destructive supersession/current vs history;
- KA-I-012 — backend semantics qualification;
- KA-I-014/019/020 — hard security/authority boundaries;
- KA-I-015 — persistent memory remains untrusted despite system-prompt placement;
- KA-I-016 — delete/forget is multi-plane reconciliation;
- KA-I-017 — semantic identity migration;
- KA-I-023 — transformation/supersession provenance;
- KA-I-024/027 — bounded context construction/coverage;
- KA-I-028 — settlement verification;
- KA-I-029 — session context vs persistent user knowledge;
- KA-I-035 — stage/verify replacement before deleting old state.

### Failure patterns

Failure IDs now run **KA-F-001 through KA-F-049**.

Status change:

- **KA-F-045 — observed → reinforced**
  - Microsoft Agent Framework + Agno independently show model-facing persistent-memory retrieval/mutation surfaces without a separately established knowledge-mutation authority class for each operation.

New:

- **KA-F-049 — observed**
  - owner-scoped knowledge surface mutates by globally addressable object ID without reapplying caller owner/domain scope at update/delete boundary.

Important qualification:

- #9983 is not encoded as its own universal failure ID because existing KA-F-045 plus KA-F-049 capture the reusable architecture risks.
- #8334 is retained as historical/regression evidence; current source has a user-scoped identity fix/migration.

---

## Twenty-six-question campaign disposition after KA-11

### Strong project evidence; no additional agent-framework revisit currently justified

- 1 Stable identity
- 2 Identity versus namespace
- 8 Permissions/sensitivity — project evidence now materially stronger after Agno; formal ABAC/ReBAC/privacy research still required
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

### Requirement evidence adequate; later formal/domain research still needed

- 3 Provenance
- 5 Temporal truth
- 6 Conflict and supersession
- 22 Deletion and retention
- 23 Schema/version evolution

### Weak/under-specified positive semantics; bounded gap research required

- 4 Epistemic state
- 7 Relationships
- 9 Actionability
- 11 Resources and artifacts
- 14 Relationship retrieval
- 25 Unknown/negative knowledge
- 26 Scope of truth

The campaign should now move to direct standards/domain evidence rather than automatically promote more coding-agent frameworks.

---

## Prioritized later gap-research map

These are **candidates only**. No specific task is assigned automatically.

### A — epistemic, temporal, conflict and negative knowledge

Relevant questions: 4, 5, 6, 25, 26.

Candidate bounded subjects:

- temporal/bitemporal semantics;
- event sourcing/correction history;
- identity/entity resolution;
- structured assertion applicability.

### B — relationships and ontology evolution

Relevant questions: 7, 14, parts of 23/26.

Candidate bounded subjects:

- controlled relationship vocabulary;
- relationship provenance/time;
- ontology evolution/migration;
- canonical relationship assertions vs derived association graphs.

### C — formal provenance

Relevant question: 3 plus parts of 11/21/23.

Candidate bounded subject:

- W3C PROV and related evidence-lineage standards, scoped to ACL/Vera needs.

### D — knowledge authorization, purpose and sensitivity

Relevant questions: 8, 9, 10, 22.

Agno has closed the project-evidence gap enough to move to direct formal study:

- ABAC/ReBAC-style knowledge access;
- principal/subject/owner/purpose separation;
- read/write/delete/consolidate/use-for-automation classes;
- sensitivity and retention.

### E — content-addressed resource/artifact identity

Relevant question: 11.

Candidate bounded subjects:

- logical resource identity;
- locators/replicas;
- content digest/version;
- extraction/derivation provenance;
- cache/index/embedding relationships.

### F — privacy deletion and retention

Relevant question: 22.

Candidate bounded subjects:

- canonical/derived/cache/backup erasure;
- audit retention vs user-data retention;
- tombstones/fencing;
- delayed cleanup and erasure verification.

### G — non-AI operational-domain validation

Relevant question: 26 and generality of the eventual model.

Candidate bounded subject:

- Home Assistant / Matter-style devices, entities, locations, sensor observations, stale/unavailable state, capabilities and shared-household authority.

This remains important to prevent coding-agent vocabulary from becoming Vera's general schema by accident.

---

## Current task

**No task is currently assigned.**

KA-11 Agno is complete.

## Planned next phase

**Bounded standards/domain gap research.**

No specific gap subject is authorized merely because the phase is next.

A future task should choose one bounded subject from the gap map, research it deeply with primary sources, update the cumulative evidence as warranted, commit research-only changes, and stop before the next subject.

## Prohibited work at this state

Do not:

- begin a standards/domain gap task without explicit authorization;
- automatically revisit additional agent frameworks;
- begin the representative retrieval-requirements set;
- begin hostile/adversarial scenario synthesis;
- synthesize the final conceptual schema;
- select a database/storage engine;
- implement retrieval or context construction;
- create embeddings;
- migrate historical catalogs;
- benchmark models;
- implement ACL or Vera;
- run autonomous workers;
- convert candidate/reinforced invariants into final architecture rules.

## Stop point

The ten high-yield revisits, coverage scan and the single promoted Agno revisit are complete. Agno materially strengthened persistent-knowledge ownership, mutation-authority and identity-ambiguity evidence while adding one new owner-scope-on-ID-mutation failure class. The remaining major uncertainties are now standards/domain questions rather than reasons to continue broad agent-framework research. No gap research, retrieval study, hostile review, synthesis, schema/storage selection or implementation has begun.
