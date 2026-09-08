# Knowledge Architecture Coverage Scan

**Campaign:** Knowledge Architecture Evidence Campaign  
**Task:** bounded post-revisit coverage scan  
**Research date:** 2026-09-08  
**Starting branch:** `research/agent-landscape`  
**Starting checkpoint:** `5f22e168cec42a4df3c58f21429a33615b721758`  
**Scope:** historical report scan only; no new upstream deep revisit, no architecture synthesis, no storage/retrieval selection, no implementation

## Purpose

The ten planned high-yield knowledge-architecture revisits are complete. This bounded scan applies the campaign plan's one question to every remaining completed project report:

> Does this project contain a unique knowledge-architecture lesson or failure class not already covered adequately?

The scan is deliberately **not** another broad research campaign. Historical project reports are used as discovery evidence. A project is promoted only when its existing report points to a materially under-covered knowledge-architecture boundary that warrants a separately authorized current-upstream revisit.

No historical report is rewritten. No cumulative invariant or failure status is changed merely from this scan, because promoted evidence should be reverified against current upstream before it changes the campaign ledgers.

---

## Executive result

**Promote one project only: Agno.**

The other sixteen historical project reports either:

- reinforce already-reinforced execution/recovery/authority/profile families;
- contain memory/retrieval mechanisms already covered more directly by the ten high-yield revisits; or
- point to a domain/standards gap that should be researched directly rather than through another coding-agent framework.

The decisive Agno finding is its current historical evidence around **destructive persistent-memory scope**: an LLM-facing memory-clear path can call an unscoped database-level clear, so one user's action can remove another user's memories when the tool is enabled. This directly targets two still-under-supported candidate areas:

- `KA-I-034` — distinct ownership plus explicit read/write authority for personal/private versus shared/project knowledge;
- `KA-I-043` / `KA-F-045` — persistent knowledge mutation authority must be separate from retrieval authority and must bind the correct subject/domain/effect scope.

That is a knowledge-specific authority failure, not merely another generic tool-permission or sandbox failure. It therefore justifies a bounded current-upstream Agno revisit.

The scan also shows that several remaining weaknesses are **not project-selection problems**. Epistemic state, temporal/bitemporal truth, conflict semantics, typed world relationships, knowledge-level ABAC/ReBAC, privacy erasure, resource/artifact identity, semantic schema evolution, unknown/negative knowledge and cross-domain truth scope need the planned standards/domain gap phase.

---

# 1. Scan set

The historical reports scanned were the completed project tasks not already included in KA-1 through KA-10:

1. Pydantic AI / official Harness — `docs/research/projects/pydantic-ai.md`
2. Cline — `docs/research/projects/cline.md`
3. promptfoo — `docs/research/projects/promptfoo.md`
4. Strands Harness SDK — `docs/research/projects/strands-harness-sdk.md`
5. Codex — `docs/research/projects/codex.md`
6. OpenHands — `docs/research/projects/openhands.md`
7. SWE-agent / SWE-ReX / mini-swe-agent — `docs/research/projects/swe-agent-mini-swe-agent.md`
8. llama.cpp — `docs/research/projects/llama-cpp.md`
9. Goose — `docs/research/projects/goose.md`
10. Ollama — `docs/research/projects/ollama.md`
11. Gemini CLI — `docs/research/projects/gemini-cli.md`
12. LiteLLM — `docs/research/projects/litellm.md`
13. vLLM — `docs/research/projects/vllm.md`
14. OpenCode — `docs/research/projects/opencode.md`
15. smolagents — `docs/research/projects/smolagents.md`
16. Agno — `docs/research/projects/agno.md`
17. CrewAI — `docs/research/projects/crewai.md`

The ten already revisited projects remain the primary evidence base and were not re-scanned as candidates for another immediate revisit.

---

# 2. Twenty-six-question coverage matrix

Coverage labels used here:

- **strong** — multiple current campaign revisits independently support the requirement/failure family well enough that another historical project is unlikely to add a unique class.
- **adequate / formal gap** — project evidence is sufficient to define the requirement, but a later standards/domain task is still needed for a positive/general semantics model.
- **weak / gap** — evidence is mostly absence/negative evidence, single-source, or too implementation-specific; a later bounded gap task is warranted.
- **project promotion** — a remaining historical report contains a unique enough lesson to justify a current-upstream revisit.

| # | Evidence question | Coverage after KA-10 + scan | Disposition |
|---|---|---|---|
| 1 | Stable identity | **strong** | No additional project revisit. Exact source/resource/run/tool/effect identities recur across nearly every high-yield task. |
| 2 | Identity versus namespace | **strong** | No additional project revisit. Namespace/group/user/session strings repeatedly fail as principal identity. |
| 3 | Provenance | **adequate / formal gap** | Operational source→derived lineage is well covered; later formal provenance study should test W3C-style models and transformation lineage. |
| 4 | Epistemic state | **weak / gap** | Most frameworks do not structurally distinguish explicit/inferred/verified/disputed/unknown. Research the semantics directly rather than another agent framework. |
| 5 | Temporal truth | **adequate / formal gap** | Bitemporal requirements are clear, but positive cross-domain semantics are still narrow. Later temporal/bitemporal study. |
| 6 | Conflict and supersession | **adequate / formal gap** | Failure evidence is strong; general correction/conflict semantics still need dedicated study. |
| 7 | Relationships | **weak / gap** | Graphiti is the main canonical-relationship source; most other graphs are derived retrieval structures. Later ontology/relationship-vocabulary study. |
| 8 | Permissions and sensitivity | **project promotion + formal gap** | Execution authority is strong; persistent-knowledge ownership/mutation scope remains under-covered. **Promote Agno**, then later ABAC/ReBAC/privacy study. |
| 9 | Actionability | **weak / gap** | The requirement is clear, but no framework supplies a general knowledge actionability taxonomy. Carry into retrieval-requirements/architecture synthesis rather than promote a project. |
| 10 | Knowledge versus authority | **strong** | No additional project revisit. This is one of the most independently reinforced campaign boundaries. |
| 11 | Resources and artifacts | **adequate / formal gap** | Logical resource / locator / content-version separation is still candidate-level. Later content-addressed artifact/resource provenance study is more direct than another runtime revisit. |
| 12 | Canonical versus derived state | **strong** | No additional project revisit. Raw/source vs summary/index/vector/projection separation is well reinforced. |
| 13 | Structured retrieval | **strong enough** | LlamaIndex/Mem0/Graphiti/backend evidence is sufficient for requirements; implementation selection remains later. |
| 14 | Relationship retrieval | **weak / gap** | Traversal mechanisms exist, but canonical relationship semantics are under-developed. Pair with relationship/ontology gap research. |
| 15 | Full-text retrieval | **strong enough** | Source-addressable lexical/full-text retrieval is adequately represented. |
| 16 | Semantic retrieval | **strong** | Similarity/rank limitations and semantic retrieval behavior are well covered. |
| 17 | Composite retrieval | **strong enough** | Candidate-introducer/rerank/hard-gate semantics are explicitly captured; later retrieval-requirements study should turn them into tests. |
| 18 | Context construction | **strong** | Multiple frameworks independently show retrieval and model-visible context are separate, version/freshness/trust-sensitive planes. |
| 19 | Memory poisoning / prompt injection | **strong** | Persistent/retrieved/remote text remains untrusted regardless of prompt position. CrewAI/Gemini/Cline add recurrence but no new class. |
| 20 | Concurrency | **strong** | Lost updates, stale snapshots, shared mutable filters, generation races and background writers are well represented. |
| 21 | Derived-state integrity | **strong** | Index/vector/summary/projection drift and generation identity are extensively covered. |
| 22 | Deletion and retention | **adequate / formal gap** | Failure evidence is strong; positive privacy-erasure/retention semantics across derived/backups/audit remain a dedicated gap-research topic. |
| 23 | Schema/version evolution | **adequate / formal gap** | Runtime/checkpoint/migration failures are strong; semantic ontology evolution still needs direct study. |
| 24 | Recovery semantics | **strong** | Persistence/replay versus exactly-once external effect is one of the strongest campaign families. |
| 25 | Unknown / negative knowledge | **weak / gap** | Requirement is strongly recognized, but positive representation is still mostly absent. Needs epistemic/temporal gap research. |
| 26 | Scope of truth | **weak / gap** | Structured applicability is required, but a general cross-domain model remains under-specified. Later domain/ontology and Home Assistant/Matter-style operational study should test it. |

---

# 3. Project disposition matrix

## Promote

### Agno — **PROMOTE to a separately authorized bounded revisit**

Historical evidence uniquely relevant to the remaining knowledge gaps:

1. Agno has first-class persistent `UserMemory` / `MemoryManager` behavior with LLM-managed add/update/delete operations.
2. Historical issue/source evidence #9983 shows the model-facing `clear_memory` path can call unscoped `db.clear_memories()`. In a shared database, one user's clear can remove another user's memories.
3. This is not merely “namespace != principal.” It tests whether the **effect target of a knowledge mutation** is structurally bound to the authenticated subject/domain and whether destructive authority is narrower than the backing database API.
4. It is a strong candidate to independently reinforce `KA-I-034` and `KA-I-043`, and to strengthen or refine `KA-F-045` after current-upstream verification.
5. Agno's DB-backed FileSystem CAS plus immutable Studio revisions are useful secondary positive evidence for capability-honest mutation/version semantics, but they are not the primary reason for promotion.

Required boundary for the future revisit:

- reverify current memory manager/database scope against current upstream;
- distinguish user/storage scope from authenticated principal;
- inspect read/add/update/delete/clear/consolidate authority separately;
- check shared/team/agent/user memory ownership semantics;
- inspect current memory provenance/epistemic/temporal fields only as relevant;
- inspect deletion settlement and cross-plane cleanup only where the memory subsystem provides evidence;
- evaluate all 26 questions but do not broaden into another general Agno harness review;
- stop after the Agno revisit.

## Hold — no separate KA revisit justified by current uniqueness test

### CrewAI — HOLD

Useful evidence: unified Memory, explicit `drain_writes()`, LLM-driven scope/importance/consolidation, memory-vs-Knowledge-vs-Flow separation, and persistent memory injected into a system message.

Disposition: these strongly recur with Mem0/Mastra/MAF/Letta and KA-F-017/019/020/027. No unique failure class remains after the high-yield revisits.

### OpenHands — HOLD

Useful evidence: branch-aware event history, action/result relationship, authoritative `leaf_event_id`, lease generations and crash-recovery repair.

Disposition: excellent recovery/provenance mechanics, but current campaign already covers checkpoint lineage, generation fencing, replay consistency and source/presentation identity. It does not supply a missing general world-relationship model.

### Codex — HOLD

Useful evidence: protected workspace metadata, authority/capability inheritance separation, versioned Guardian authorization evidence and narrow child/reviewer capability surfaces.

Disposition: highly valuable ACL execution-authority evidence, but KA-I-020/041/042/046 and related failure families already cover it. Not a unique knowledge-substrate gap.

### Gemini CLI — HOLD

Useful evidence: rich deterministic policy matching, MCP origin identity, fail-closed non-interactive behavior, checkpoint/session distinctions and persistent instruction/memory surfaces.

Disposition: strengthens authority/injection/profile boundaries already reinforced. It does not provide a missing positive epistemic/relationship/temporal model.

### Strands Harness SDK — HOLD

Useful evidence: Cedar authorization, interrupt identity, snapshots, sessions, context managers, sandbox routing and evaluator surfaces.

Disposition: useful execution authorization and persistence reference, but knowledge-level principal/purpose/sensitivity/retention semantics remain outside it. Later ABAC/ReBAC research should target that domain directly.

### Pydantic AI / Harness — HOLD

Useful evidence: typed tool contracts, durable operations, filesystem hashes/expected-hash writes, bounded persistent memory, compaction and explicit application-vs-OS sandbox boundaries.

Disposition: strong mechanism evidence, but no unique knowledge-architecture lesson beyond already-covered versioning, derived context, execution authority and resource/profile identity.

### Cline — HOLD

Useful evidence: stateless model loop vs stateful orchestration, Plan-mode enforcement failures, approval/policy inconsistencies, checkpoints, provider authority and context compaction.

Disposition: strong outer-harness evidence, not a missing semantic knowledge model.

### Goose — HOLD

Useful evidence: durable conversation-derived agent state machine, persistent session metadata, session run registry, MCP extensions and recipe checks.

Disposition: reinforces replay/continuation and session-state separation. Does not add a unique canonical knowledge or epistemic class.

### OpenCode — HOLD

Useful evidence: explicit “permissions are not sandboxing,” session/event versus ACL continuation, MCP process lifecycle and stable-vs-V2 runtime identity.

Disposition: runtime lifecycle/profile lessons already strongly covered.

### smolagents — HOLD

Useful evidence: thin model loop, `AgentMemory`, child summary information-flow leak, shared managed-agent state and deterministic final-answer-check seam.

Disposition: memory is mainly run history; parent/child information-flow and verifier boundaries already have stronger coverage elsewhere.

### promptfoo — HOLD

Useful evidence: independent evaluator, deterministic trajectory assertions, protected evidence and trace availability.

Disposition: important for later hostile/retrieval acceptance testing, but it is an evaluation subsystem rather than a missing knowledge-substrate semantics source.

### SWE-agent / SWE-ReX / mini-swe-agent — HOLD

Useful evidence: simplification lineage and deliberate separation of reasoning loop from execution infrastructure.

Disposition: reinforces runtime architecture and containment lessons, not a unique knowledge class.

### llama.cpp — HOLD

Useful evidence: exact model/template/parser/grammar/runtime identity and constrained-output semantics.

Disposition: crucial benchmark/runtime provenance, already absorbed into realized-profile invariants. Not a knowledge-substrate gap.

### Ollama — HOLD; retain as later resource/artifact evidence source

Useful evidence: model-reference resolution, manifests, content-addressed model layers, templates and immutable package/artifact digests.

Disposition: this is valuable positive evidence for `KA-I-037`, but a full Ollama KA revisit is not efficient. Use Ollama as one primary implementation example during the later **content-addressed resource/artifact identity and provenance** gap task.

### LiteLLM — HOLD

Useful evidence: provider/gateway identity, authorization-aware routing, provider-scoped resources, effect-aware fallback and credential/network boundaries.

Disposition: strengthens authority/profile/effect identity but does not fill the remaining epistemic/world-knowledge gaps.

### vLLM — HOLD

Useful evidence: realized runtime identity, scheduler/KV state, request-resource lifecycle and distributed trust boundaries.

Disposition: inference-runtime evidence only; no unique general knowledge semantics.

---

# 4. Candidate-invariant coverage after the scan

No ledger status is changed during the scan. The following candidate families deserve explicit disposition:

## Candidate families best addressed by later domain/standards research

- **KA-I-004** — identity merge/split as auditable reversible transition → identity/entity-resolution study.
- **KA-I-005** — ambiguous/unresolved identity representation → identity/entity-resolution study.
- **KA-I-007** — governed relationship semantics → controlled relationship vocabulary / ontology evolution study.
- **KA-I-037** — logical resource vs locator vs content/version digest → content-addressed resource/artifact identity study; Ollama is a useful example source.
- **KA-I-038** — canonical reads need value/snapshot semantics or explicit mutation contract → retain for hostile scenario / conceptual model tests; no project promotion needed.
- **KA-I-039** — persistence round-trip preserves semantic metadata → retain for schema/migration study.
- **KA-I-040** — live versus replay transition equivalence → retain for recovery/event-sourcing gap study if needed.
- **KA-I-044** — transport liveness vs logical session validity → sufficiently identified as a runtime boundary; no project promotion needed now.
- **KA-I-045** — pending continuation terminal/expiry lifecycle → sufficiently identified; later hostile/authority tests can determine final form.

## Candidate families with a promoted project follow-up

- **KA-I-034** — personal/private versus shared/project knowledge ownership and explicit read/write authority → **Agno revisit**.
- **KA-I-043** — persistent knowledge mutation classes separately governable from retrieval → **Agno revisit**.

## Candidate family that should remain until retrieval/context requirements are tested

- **KA-I-031** — model context identifies exact settled knowledge revision → no remaining historical project contains a clearly unique positive mechanism. Keep candidate until retrieval/context-construction requirements and hostile freshness scenarios test whether the formulation is necessary and sufficiently general.

---

# 5. Gap-research priorities surfaced by the scan

These are **not authorized tasks**. They are the later gap phase already contemplated by `CAMPAIGN_PLAN.md`, now prioritized by the coverage evidence.

## Priority A — epistemic + temporal + conflict semantics

Questions: 4, 5, 6, 25, 26.

Need positive, general semantics for:

- explicit statement versus observation versus inference versus verified configuration;
- confidence/trust versus epistemic basis;
- known-false versus unknown versus not-established versus disputed;
- world-valid time versus observation/record time;
- correction/supersession without historical destruction;
- applicability by person/device/project/environment/version/time.

Likely direct subjects:

- bitemporal data semantics;
- event sourcing/correction history;
- identity/entity resolution;
- cross-domain assertion applicability.

## Priority B — relationships and ontology evolution

Questions: 7 and 14, plus part of 23/26.

Need to test:

- first-class typed many-to-many relationships;
- relationship evidence/provenance/time;
- symmetric/inverse/transitive/cardinality semantics where applicable;
- controlled extension without arbitrary string drift;
- relationship changes across schema versions;
- traversal without confusing derived association graphs with canonical relationship truth.

## Priority C — provenance formalization

Question: 3, plus 11/21/23.

The campaign has strong operational lineage evidence but has not tested a formal provenance model. A W3C-PROV-style bounded study can determine which source/evidence/derivation/activity/agent relationships are actually useful versus over-general.

## Priority D — knowledge authorization, sensitivity and purpose

Question: 8, plus 9/10/22.

After Agno, study knowledge access directly:

- authenticated principal;
- subject/owner;
- read/write/delete/consolidate/use-for-automation distinctions;
- purpose and sensitivity;
- retention/erasure obligations;
- ABAC/ReBAC-style relationship-aware access;
- shared versus private domains.

## Priority E — resource/artifact identity and provenance

Question: 11.

Need a general model separating:

- logical object;
- current/historical locator(s);
- immutable observed content digest/version;
- MIME/size/metadata;
- source/owner/sensitivity;
- extracted representations;
- derived indexes/embeddings;
- replica/cache state.

Ollama's manifest/layer model and LlamaIndex `MediaResource` are useful primary implementation examples, but the research target should be the general resource problem rather than either project as a whole.

## Priority F — deletion, retention and privacy erasure

Question: 22.

Failure evidence is strong; positive requirements still need direct study of:

- canonical/derived/cache/backup planes;
- audit retention versus user-data retention;
- tombstones/generation fences;
- rebuildability after deletion;
- erasure verification and delayed cleanup;
- legal/policy retention classes without baking one jurisdiction into the conceptual model.

## Priority G — non-AI operational-domain validation

Question: 26 and general campaign scope.

Agent frameworks heavily bias evidence toward conversations, tools and software tasks. A later bounded Home Assistant / Matter-style device-location-state study should test whether the emerging concepts survive:

- devices with replacement hardware;
- entity IDs versus friendly names;
- rooms/areas/households;
- sensor observations versus inferred state;
- unavailable/stale state;
- device capabilities;
- automations and policy-governed actions;
- ownership/shared household permissions.

This is necessary to prevent the final model from becoming an AI-research schema disguised as a general knowledge architecture.

---

# 6. Counterevidence and qualification check

The scan found no historical project that invalidates the central campaign separation:

**Knowledge ≠ Authority ≠ Execution.**

Several reports actually strengthen the qualification:

- Codex/Gemini/Strands/Cline show rich tool policy is still separate from knowledge truth.
- promptfoo shows evaluation evidence is distinct from execution state and model opinion.
- OpenHands/Goose/OpenCode show durable conversation/event state is not enough for effect settlement or general world truth.
- llama.cpp/Ollama/LiteLLM/vLLM show infrastructure/resource/profile identity is behavior-bearing but is not semantic truth.
- CrewAI/Agno show that persistent memory features remain model-derived and authority-sensitive rather than self-authenticating truth.

The scan also found no reason to turn any current candidate invariant into a final architecture rule. That remains prohibited until the later gap, retrieval-question, hostile-scenario and synthesis phases.

---

# 7. Promotion decision

## Promoted project

**Agno — one future bounded knowledge-architecture revisit.**

Suggested label if/when explicitly authorized:

`KA-11 — Agno Knowledge-Architecture Revisit`

The numbering is only a convenient continuation of the completed KA-1 through KA-10 sequence; it is not authorization.

## Not promoted

All other scanned projects remain valuable historical evidence but do not justify a separate current-upstream KA revisit under the campaign's uniqueness test.

A project can be reconsidered later only if:

- new upstream evidence materially changes the gap picture;
- the Agno revisit exposes a new unresolved class that another historical project uniquely covers; or
- a separately authorized gap-research task identifies a project as the best primary implementation example for a narrow question.

---

# 8. Ledger decision

No edits to `invariants.md` or `failure-patterns.md` are made in this coverage scan.

Reason:

- the scan's purpose is project/gap selection, not current-upstream evidence revalidation;
- Agno evidence should be rechecked before it changes candidate/reinforced status;
- the remaining gap areas require direct domain/standards evidence rather than more agent-framework recurrence.

This preserves the campaign evidence discipline and prevents historical discovery reports from silently upgrading candidate rules.

---

# 9. Stop point

The bounded coverage scan is complete.

It stops with:

- one promoted future project candidate: **Agno**;
- a prioritized gap map across all 26 evidence questions;
- no new invariant/failure IDs;
- no invariant status changes;
- no current-upstream Agno revisit;
- no standards/gap research;
- no retrieval-requirements study;
- no hostile-scenario review;
- no conceptual schema synthesis;
- no database/storage/retrieval selection;
- no ACL/Vera implementation.

The next bounded task must be explicitly authorized.