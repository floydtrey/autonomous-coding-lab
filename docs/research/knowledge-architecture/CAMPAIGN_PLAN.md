# Knowledge Architecture Evidence Campaign Plan

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Planning checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`  
**Status:** campaign plan established; no architecture implementation or project revisit has begun

## Purpose

This campaign exists to turn the completed agent-landscape research into a rigorous evidence base for a future **general-purpose ACL/Vera knowledge architecture**.

The completed Tasks 1–31 remain historical evidence. This campaign does not restart them and does not treat their research-specific data structures as the future knowledge schema.

The new question is narrower and different:

> What does current primary evidence from these projects tell us about building a durable, general knowledge substrate for ACL, Vera, research, people, devices, projects, tools, observations, resources and future domains?

The campaign is deliberately slow and bounded. Each task must finish and stop before the next begins.

## Non-goals during this campaign

Do **not**:

- select the final knowledge architecture;
- select a database or graph engine;
- implement ACL or Vera;
- implement a knowledge store;
- implement retrieval software;
- create embeddings;
- bulk-migrate `catalog.jsonl` or `catalog-part2.jsonl`;
- benchmark models;
- select frameworks/providers/runtimes;
- run autonomous workers;
- convert retrieved content into policy or authority;
- infer an unassigned next task.

The campaign is evidence gathering, architecture requirements discovery and validation only.

## Evidence questions every source must be tested against

Every project revisit or standards/gap task should examine only evidence relevant to one or more of these questions:

1. **Stable identity** — how are people, agents, devices, sessions, resources, repositories, artifacts, facts and actions identified across time and migration?
2. **Identity versus namespace** — which IDs are only scoping/routing metadata and which, if any, are authenticated principal identity?
3. **Provenance** — can raw source, extracted evidence, derived claim, summary, decision and action be traced separately?
4. **Epistemic state** — can the system distinguish observation, explicit statement, inference, third-party claim, authenticated configuration, derived summary, verified fact, dispute and uncertainty?
5. **Temporal truth** — how are world-valid time, observation time, record/transaction time, current state, historical state and corrections represented?
6. **Conflict and supersession** — how are contradictions, stale facts, corrections, replacements and invalidations represented without destroying history?
7. **Relationships** — are typed many-to-many relationships first-class, provenance-bearing and temporally meaningful?
8. **Permissions and sensitivity** — can read/write/use scope be bound to a principal, purpose, sensitivity and retention policy without confusing data partitioning with authorization?
9. **Actionability** — can retrieved knowledge be classified as informational, planning input, automation input, policy evidence, verification-required or explicitly non-authoritative?
10. **Knowledge versus authority** — can learned/retrieved content remain separate from policy, credentials, approval and execution authority?
11. **Resources and artifacts** — can large files and external objects retain stable identity, version, checksum, provenance, extracted text and derived representations without embedding bytes into canonical records?
12. **Canonical versus derived state** — what remains authoritative if summaries, graph projections, embeddings, search indexes or generated views are deleted and rebuilt?
13. **Structured retrieval** — can deterministic current facts/state/configuration be queried without semantic guessing?
14. **Relationship retrieval** — can evidence, dependencies, ownership, capability, policy and impact chains be traversed?
15. **Full-text retrieval** — can source/evidence/procedure/document text remain searchable and source-addressable?
16. **Semantic retrieval** — can conceptually equivalent material be found across differing terminology without treating similarity rank as truth?
17. **Composite retrieval** — can structured, graph, temporal, semantic, permission and provenance constraints be composed safely?
18. **Context construction** — can retrieved material be filtered/ranked by principal, purpose, trust, freshness, confidence, token budget and actionability before model exposure?
19. **Memory poisoning and prompt injection** — can persistent or retrieved text remain untrusted content even when projected into privileged prompt positions?
20. **Concurrency** — what happens when multiple writers create, update, invalidate, delete or derive state simultaneously?
21. **Derived-state integrity** — can vectors, graph links, summaries, entity resolution, caches and indexes drift from canonical evidence, and how is that detected/reconciled?
22. **Deletion and retention** — can forget/erasure requests account for canonical, derived, historical, cached and backup planes without confusing audit retention with user-data retention?
23. **Schema/version evolution** — can records, relationships, policies, procedures and derived representations survive semantic version changes and storage migration?
24. **Recovery semantics** — can persistence/replay state be distinguished from proof that an external effect occurred exactly once?
25. **Unknown/negative knowledge** — can the system distinguish known-false, unknown, not-established, conflicting and historically-true-but-no-longer-current states?
26. **Scope of truth** — can facts be qualified by environment, machine, project, version, time, person or operating context without degenerating into arbitrary key/value blobs?

## Evidence discipline

For each substantive finding, record separately:

- **Observed upstream behavior** — current docs/code/specification behavior actually inspected.
- **Failure evidence** — issue, regression, incident, test, advisory or reproducible report, with version scope.
- **Architectural lesson** — the requirement or warning we derive for ACL/Vera.
- **Confidence** — how strongly the sources support the conclusion.
- **Non-conclusion** — what the evidence does *not* prove.

Prefer primary sources. Existing ACL research reports are discovery maps, not substitutes for rechecking current upstream evidence where the new question requires more context.

## Per-project revisit procedure

Each revisit is one bounded task.

1. Read this plan, the dedicated knowledge-architecture state file, root research governance, and the project's existing deep-research report.
2. Extract only references/findings relevant to the evidence-question matrix above.
3. Revisit the current upstream repository, docs, specifications, papers and linked issues/PRs for those references.
4. Check whether behavior has changed since the original ACL research revision.
5. Follow high-value references deeper where the old campaign stopped because the detail was outside its prior scope.
6. Record observed mechanism, failure evidence, architectural significance, confidence and explicit limits.
7. Add candidate invariants and failure patterns only when supported by evidence.
8. Update the dedicated knowledge-architecture state.
9. Commit documentation/research changes only.
10. **Stop. Do not begin the next project.**

## Planned high-yield revisit sequence

The initial sequence is intentionally ordered by direct relevance to knowledge/memory architecture:

1. **Graphiti**
2. **Mem0**
3. **Letta Code**
4. **LlamaIndex**
5. **Mastra**
6. **LangGraph**
7. **Google ADK**
8. **Microsoft Agent Framework**
9. **OpenAI Agents SDK**
10. **Model Context Protocol**

This is a research sequence, not an adoption ranking.

A task may not begin merely because it is next in this list. It must be explicitly assigned.

## Coverage scan after the high-yield revisits

After the ten revisits are complete, perform one bounded coverage-scan task over the remaining completed project reports.

The only question is:

> Does this project contain a unique knowledge-architecture lesson or failure class not already covered adequately?

Do not automatically deep-revisit every project.

Likely candidates for promotion include, but are not limited to:

- Pydantic AI / Harness;
- OpenHands;
- Codex;
- Cline;
- Goose;
- Gemini CLI;
- OpenCode;
- CrewAI;
- Agno.

A promoted project becomes its own separately assigned bounded task.

## Cross-project ledgers

Maintain two cumulative evidence ledgers during the campaign.

### 1. Candidate invariant ledger

Examples of the kind of invariant that may emerge:

- namespace ID is not authenticated principal identity;
- persistence is not truth;
- retrieval rank is not epistemic confidence;
- prompt position is not source authority;
- current state and history are separate retrieval intents;
- derived state must retain lineage to canonical evidence;
- memory text does not gain policy/tool/credential authority by persistence;
- replayable orchestration is not an exactly-once effect ledger.

Do not promote an invariant to a final architectural rule merely because one framework uses it. Track recurrence, counterexamples and scope.

### 2. Failure / anti-pattern ledger

Examples:

- newest statement automatically wins;
- group/session/user string treated as authorization;
- LLM contradiction decision directly retires canonical truth without structural/trust checks;
- deleting the primary fact while derived indexes retain the data;
- model-visible memory becoming system policy;
- semantic similarity returning superseded facts as current;
- stale pre-write dedup used as a uniqueness guarantee;
- current prompt projection drifting from canonical state;
- a successful SDK return treated as proof of settlement;
- checkpoint/replay state treated as proof of external effect completion.

Record exact evidence and version scope.

## Gap-research phase

Only after the project revisits/coverage scan, perform separately assigned bounded research tasks for important areas the agent-framework campaign could not answer adequately.

Candidate subjects include:

- W3C provenance models and related evidence-lineage standards;
- temporal and bitemporal data semantics;
- event sourcing, correction history and immutable audit concepts;
- identity, aliases, identifiers and entity resolution;
- controlled relationship vocabularies / ontology evolution;
- structured + graph + full-text + semantic hybrid retrieval;
- ABAC/ReBAC-style principal/purpose/access semantics;
- privacy retention, erasure and derived-data deletion;
- content-addressed resource/artifact identity and provenance;
- non-AI operational entity/state models, especially Home Assistant and Matter-style devices/locations/state.

Each is its own task. Do not turn this phase into an unbounded standards survey.

## Retrieval-requirements study

After evidence gathering, define representative retrieval questions **before** selecting storage technology.

Target approximately 40–60 questions covering:

- deterministic structured facts;
- current versus historical state;
- evidence/provenance tracing;
- conflicts and supersession;
- graph/relationship traversal;
- semantic recall across differing terminology;
- permission/sensitivity filtering;
- source/resource retrieval;
- capability/policy lookup;
- composite authorization-support queries;
- unknown/negative knowledge;
- freshness and confidence;
- context construction under a token budget.

These questions become architecture acceptance tests, not implementation benchmarks yet.

## Hostile / adversarial scenario review

Before approving a conceptual model, test deliberately difficult scenarios including at least:

- two people with the same name;
- one person with several identities/aliases/accounts;
- mistaken facial recognition with confidence;
- contradictory sensors;
- explicit preference changing over time;
- inferred preference conflicting with explicit preference;
- stale network/device state;
- replacement hardware reusing a friendly device name;
- malicious instructions inside a retrieved document;
- superseded research finding ranking highly semantically;
- deleted personal data surviving in embeddings/indexes/history;
- two writers racing to update one fact;
- low-trust recent evidence contradicting stronger older evidence;
- an action succeeding while its acknowledgement is lost;
- a historical software defect that must remain searchable but not appear current;
- unknown versus known-false versus disputed state.

Use failures to revise requirements before schema design.

## Architecture synthesis phase

Only after the evidence campaign, gap research, retrieval questions and hostile scenarios are complete should the project synthesize the conceptual model.

At that point explicitly test questions such as:

- Should `Assertion` be the common semantic primitive for facts, preferences, state and relationships?
- Which concepts require independent first-class identity?
- Which metadata is intrinsic versus attached provenance/evidence?
- How should controlled relationship vocabulary extension work?
- What is canonical versus rebuildable derived data?
- What integrity constraints are non-negotiable?

Do not preserve an early schema idea merely because it appeared in a handoff or prior chat.

## Deliberately small cross-domain prototype

After conceptual synthesis, create a small hand-authored sample before any bulk migration.

It should contain diverse examples such as:

- research finding;
- Git repository/commit/dependency;
- person and multiple identities;
- explicit preference;
- inferred preference;
- camera/facial observation;
- Home Assistant device and state;
- network relationship;
- tool/capability;
- policy-governed high-risk action reference;
- routine/schedule;
- historical event;
- procedure/skill;
- large external resource;
- contradiction/supersession;
- deletion/retention example.

Run the representative retrieval questions against the conceptual model. Revise the model where representation or retrieval becomes awkward.

Only after this stage should physical storage prototypes be considered.

## Anti-drift rules

1. **One bounded task at a time.**
2. **No automatic next-task execution.**
3. **Existing research is evidence, not architecture authority.**
4. **Do not select implementation technology while requirements are still being discovered.**
5. **Do not let AI/coding use cases dominate general-domain modeling.**
6. **Do not convert untrusted retrieved content into policy or execution authority.**
7. **Do not rewrite historical research catalogs merely to fit the future model.**
8. **Do not bulk migrate before the diverse sample and retrieval tests pass.**
9. **Separate observed fact, failure evidence, inference and proposed invariant.**
10. **If a task expands beyond its stated boundary, stop and record the follow-up rather than absorbing it.**

## Immediate next bounded task

**KA-1 — Graphiti Knowledge-Architecture Revisit**

When explicitly authorized, perform **Graphiti only**.

Focus on:

- episodic/raw evidence versus derived semantic facts;
- entity resolution and identity;
- relationship representation;
- bitemporal semantics;
- provenance chains;
- contradiction/invalidation behavior;
- current versus historical retrieval;
- hybrid vector/full-text/graph retrieval;
- graph partitioning versus authorization;
- concurrency and cross-group isolation;
- derived-state/embedding integrity;
- deletion/retention/reconciliation;
- memory poisoning and trust boundaries;
- anything newly discovered upstream that materially affects a general knowledge substrate.

Re-open the current Graphiti repository/docs/issues rather than relying only on `projects/graphiti.md`.

At completion, save the revisit findings, update the dedicated campaign state, commit documentation/research changes, and stop before Mem0.

## Campaign completion condition

This campaign is not complete when every old report has been reread. It is complete when there is enough evidence to state and test durable general-knowledge requirements across multiple domains without relying on one framework's vocabulary or implementation.
