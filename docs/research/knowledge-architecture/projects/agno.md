# Agno Knowledge-Architecture Revisit

**Campaign:** Knowledge Architecture Evidence Campaign  
**Task:** KA-11 — Agno Knowledge-Architecture Revisit  
**Research date:** 2026-09-08  
**Historical report:** `docs/research/projects/agno.md`  
**Starting ACL checkpoint:** `4b10868c26a609c657b97a41298edd0fa553c232`  
**Canonical upstream:** `agno-agi/agno`  
**Current upstream inspected:** `e75921a683d015e82d271ca96e52b11beec095e1`  
**Current package / latest stable observed:** `3.0.7` / `v3.0.7`  
**Boundary:** research only; no Agno adoption, schema selection, storage selection, retrieval implementation, model assignment, or ACL/Vera implementation decision

## Executive assessment

Agno was promoted by the post-KA-10 coverage scan because its historical report contained a knowledge-specific authority failure that was not adequately covered by the ten high-yield revisits: a model-facing memory-clear operation could reach a database-global clear operation and destroy another user's persistent memories.

The current-upstream revisit confirms that this promotion was justified.

At current Agno `3.0.7` / `main`:

- the original `MemoryManager` still contains both correctly scoped and database-global memory-clear operations;
- the `clear_memory` tool closure in the generic memory-task path still calls the global `db.clear_memories()` path;
- issue #9983 remains open;
- proposed fix PR #9986 remains open and unmerged;
- the ordinary create/update extraction path has been narrowed since the reported configuration and now explicitly disables clear-all, so the current defect must be scoped to the paths that actually expose the generic clear tool rather than described as universal to every memory update;
- the standalone `MemoryTools` toolkit correctly scopes list/add by `run_context.user_id`, but its current update/delete paths resolve and mutate by bare `memory_id` without passing the caller's `user_id`; the database interface treats user scope as optional and the SQLite deletion implementation only applies a user filter when one is supplied;
- the authenticated AgentOS REST memory router demonstrates the safer pattern by resolving the authenticated caller scope and threading the resulting `user_id` into memory mutations;
- the newer Learning subsystem explicitly separates user memory, user profile, session context, learned knowledge, entity memory and decision logs, and makes user/global/custom sharing scope visible in configuration;
- current user-scoped EntityMemory identity now embeds a digest of the user identity into its deterministic row key and includes a migration for legacy unscoped keys, directly addressing the cross-tenant collision class reported in still-open #8334;
- current EntityMemory also provides unusually useful positive reference material for ambiguity handling, current-versus-retired facts, archived entities, relationship retirement and migration quarantine, while still lacking a general epistemic truth model and governed relationship vocabulary.

The strongest architecture lesson is therefore broader than the individual #9983 bug:

> **A knowledge record's storage key, retrieval namespace, authenticated owner and mutation authority are separate things. Every persistent knowledge mutation must re-bind the current principal/domain and operation class at the mutation boundary; a globally addressable object ID or database method must not silently widen a model-facing operation.**

KA-11 independently reinforces three prior candidate invariants:

- **KA-I-005** — ambiguous identity must be representable and resolution must not force a merge;
- **KA-I-034** — personal/private and shared/project knowledge domains require distinct ownership plus explicit read/write authority;
- **KA-I-043** — persistent knowledge read and mutation authority are distinct, and add/update/delete/clear/consolidate-style operations need separately governable action classes.

It also independently reinforces **KA-F-045**, because Agno exposes configurations/toolkits where persistent-memory retrieval and multiple mutation operations are bundled into one model-facing capability surface.

KA-11 adds one new observed failure class:

- **KA-F-049** — an owner-scoped knowledge surface resolves update/delete by a globally addressable object ID without reapplying the caller's owner/domain scope at mutation time.

The revisit does **not** support promoting KA-I-004 (reversible merge/split) or KA-I-007 (governed relationship semantics). Agno's current source explicitly prefers fragmentation to unsafe merge because a wrong merge has no unmerge, and its relationship labels remain open strings rather than a governed semantic vocabulary.

---

# 1. Upstream identity and delta since historical Task 28

## Observed upstream behavior

Historical Task 28 inspected Agno 3.0.6-era source. Current upstream is:

- repository: `agno-agi/agno`;
- main: `e75921a683d015e82d271ca96e52b11beec095e1`;
- package version: `3.0.7`;
- stable release observed: `v3.0.7`, published 2026-09-08.

Current 3.0.7 contains substantial knowledge/lifecycle changes beyond the historical report, including:

- a newer `agno.learn` subsystem with typed learning domains;
- user-scoped entity-memory identity migration machinery;
- newer AgentOS user-isolation routing;
- page-oriented Knowledge storage and read-only page filesystem tooling;
- fixes for workflow state finalization and provider adapters;
- SQLite session JSON serialization changes at current main.

## Architectural lesson

Agno's package/version label is insufficient for knowledge behavior. Exact source revision remains behavior-bearing because current main contains post-release or same-version correctness changes and because memory/learning semantics are evolving quickly.

## Confidence

High — current repository source and release metadata inspected directly.

## Non-conclusion

This revisit does not compare Agno as a framework candidate or claim 3.0.7 is unsuitable for production generally.

---

# 2. Knowledge planes in current Agno

Current Agno contains several distinct information/state planes that should not be collapsed into one generic `memory` concept.

## Legacy/current `MemoryManager` / `UserMemory`

The older `UserMemory` record includes:

- memory text;
- memory ID;
- topics;
- `user_id`;
- original input;
- created/updated timestamps;
- feedback;
- agent/team attribution.

This is useful operational memory metadata, but it does not structurally require:

- explicit-statement versus inference basis;
- verification state;
- source trust;
- confidence semantics;
- dispute state;
- world-valid interval;
- supersession lineage;
- actionability classification.

## New `LearningMachine` domains

Current configuration explicitly distinguishes:

- `UserProfile` — structured long-term user profile;
- `UserMemory` — unstructured long-term observations about a user;
- `SessionContext` — current-session summary/goal/plan/progress;
- `LearnedKnowledge` — reusable learned knowledge with namespace scope;
- `EntityMemory` — facts/events/relationships about third-party entities;
- `DecisionLog` — agent-scoped decision records.

This is valuable because it prevents one persistence primitive from silently serving every semantic purpose.

## Knowledge pages

Agno 3.0.7 additionally introduces page-oriented Knowledge capabilities whose release notes describe coordinated publication of catalog metadata, text and vectors, preserving prior revision on failed refresh and supporting pinned-revision read-only page access.

That is positive derived-state/resource evidence, but KA-11 did not deep-expand into page storage because Agno was promoted specifically for persistent knowledge ownership/mutation and the campaign already has strong canonical-vs-derived evidence.

## Architectural lesson

Different retention, authority and truth rules apply to:

- user facts/preferences;
- session continuation;
- reusable project/shared knowledge;
- third-party entity knowledge;
- decision/audit evidence;
- reference pages/resources;
- runtime execution state.

## Confidence

High for the decomposition; medium for page-storage conclusions because only the current release/source references needed for boundary confirmation were inspected.

## Non-conclusion

Agno's domain decomposition is not itself the future Vera schema.

---

# 3. Storage scope is not authenticated principal identity

Current Agno reinforces the campaign-wide distinction between a stored `user_id` and an authenticated principal.

## Direct memory APIs

Many low-level memory methods accept optional `user_id`. When absent, some legacy APIs use `"default"`; database methods may also operate unscoped when `user_id=None`.

Those values are storage/routing metadata unless an authenticated boundary binds them.

## AgentOS route layer

Current AgentOS introduces explicit user-scope helpers. `get_scoped_user_id()` distinguishes:

- authenticated non-admin user under opt-in user isolation;
- admin;
- service-account principal;
- non-isolated deployment;
- scheduler-owned/unowned execution.

The source explicitly warns that every new endpoint handling user-owned data must thread the scoped user into reads/writes and that omission can silently bypass isolation.

Current behavior is important:

- ordinary human/JWT user isolation is opt-in;
- service accounts self-scope even without the general user-isolation flag unless admin;
- admins are intentionally unscoped;
- authenticated callers missing usable identity under isolation fail closed.

## Architectural lesson

A `user_id` field should not be treated as proof of who is acting. Vera/ACL need:

1. authenticated principal identity;
2. knowledge subject/owner identity;
3. storage namespace/domain;
4. requested target identity;
5. authorization decision connecting them.

These can coincide but are not interchangeable.

## Ledger effect

Reinforces existing KA-I-003 / KA-F-001; no status change needed because those are already strongly reinforced.

---

# 4. #9983 — current cross-user clear-memory authority defect

## Failure evidence

Issue #9983 remains open in current upstream.

The reported defect is narrow and concrete:

- `MemoryManager._get_db_tools()` and `_aget_db_tools()` can register model-facing `clear_memory`;
- sibling add/update/delete closures carry the caller's `user_id`;
- `clear_memory` calls `db.clear_memories()`;
- database `clear_memories()` is a global operation by contract;
- SQLite, PostgreSQL, MySQL and other adapters implement it as unscoped all-memory deletion;
- Agno already has `clear_user_memories(user_id=...)` / async equivalent that perform a scoped delete.

Current 3.0.7/main still contains the unscoped sync and async tool closures.

PR #9986 proposes routing those closures to the existing user-scoped methods and includes a two-user regression fixture. The PR remains open and unmerged at this revisit.

## Important current qualification

The current ordinary `create_or_update_memories()` / async extraction path explicitly calls `_get_db_tools(... enable_clear_memory=False)` and its system prompt also disables clear-all.

Therefore the current conclusion is **not**:

> every normal Agno memory update exposes a database-global clear by default.

The defensible conclusion is:

> any path that exposes the generic `clear_memory` closure in the current `MemoryManager` gives a model-facing user-memory operation access to a database-global primitive rather than the already-available caller-scoped primitive.

`update_memory_task()` / `run_memory_task()` retain this generic clear-capable path depending on configuration.

## Architectural lesson

Global administrative operations and subject-scoped user operations must have separate capability identity.

A low-level API such as:

- `clear_all_memories(database)`

must never become equivalent to:

- `forget_my_memories(principal=user-A)`

merely because both have a friendly tool name `clear_memory`.

## Ledger effect

Strong independent evidence for:

- KA-I-034 — ownership and read/write authority;
- KA-I-043 — mutation action classes;
- KA-F-045 — model-facing read/mutation capability bundling.

---

# 5. `MemoryTools` — target ownership must be rechecked on ID mutation

A second current-source finding is distinct from #9983.

## Positive paths

Current standalone `MemoryTools`:

- `get_memories(run_context)` obtains `run_context.user_id` and queries `get_user_memories(user_id=...)`;
- `add_memory(run_context, ...)` obtains `run_context.user_id` and stamps it onto the new `UserMemory`.

## Current update path

`update_memory(run_context, memory_id, ...)`:

1. calls `db.get_user_memory(memory_id)` without the run-context user ID;
2. obtains the existing record if globally addressable by ID;
3. constructs replacement content preserving the record's existing `user_id`;
4. calls `upsert_user_memory()`.

The caller's current `run_context.user_id` is not used for owner authorization in that path.

## Current delete path

`delete_memory(run_context, memory_id)`:

1. calls `db.get_user_memory(memory_id)` without the current user ID;
2. calls `db.delete_user_memory(memory_id)` without the current user ID.

The BaseDb contract makes `user_id` optional for both lookup and deletion. Current SQLite source applies the `user_id` deletion predicate only when a non-null user ID is supplied.

## Contrast: AgentOS REST memory router

The current authenticated REST router does the stronger thing:

- resolves the effective caller scope using `resolve_db_and_scope()`;
- passes `effective_user_id` into remote deletion;
- passes local `user_id` into `delete_user_memory()` when the caller is scoped.

That contrast demonstrates that the DB supports scoped mutation and that the missing scope is surface-specific rather than an unavoidable backend property.

## Failure classification

KA-11 did not find a current public issue specifically documenting exploitation of this `MemoryTools` update/delete path, and the revisit did not execute a live PoC. Therefore this is classified as **current-source-observed failure semantics**, not as an independently reproduced incident.

## New anti-pattern

**KA-F-049:**

> An owner-scoped knowledge surface resolves update/delete by a globally addressable object ID without reapplying the current caller's owner/domain scope at mutation time.

## Architectural lesson

Authorization must be evaluated at the target mutation boundary:

`principal + action class + knowledge domain + target owner + target record/version`

A record ID proves which object was named; it does not prove the caller may mutate that object.

---

# 6. Current user-memory mutation classes are structurally visible

The new `UserMemoryConfig` explicitly separates operation toggles:

- add memory;
- update memory;
- delete memory;
- clear memories.

Current defaults are informative:

- add/update/delete enabled for extraction;
- clear disabled by default and explicitly labeled dangerous;
- agent tools disabled by default under ordinary ALWAYS mode;
- agent may be given an `update_user_memory` tool under AGENTIC/explicit-tool mode.

This independently supports the campaign requirement that different persistent-knowledge mutations are distinct action classes.

## Why this matters for Vera

Reading a preference is qualitatively different from:

- recording a new preference;
- rewriting a remembered preference;
- declaring an old belief superseded;
- deleting/forgetting a record;
- clearing a whole personal domain;
- consolidating many source memories into fewer derived records;
- changing a record from personal to shared;
- changing sensitivity/retention.

The final policy design may group some classes, but the data/action model must be able to distinguish them first.

## Ledger effect

**KA-I-043 candidate → reinforced.**

Independent evidence now exists from Microsoft Agent Framework and Agno.

---

# 7. Personal, shared and custom knowledge domains

Current Agno's Learning subsystem makes sharing domain explicit in multiple places.

## Fixed user-scoped domains

- UserProfile is user-scoped.
- UserMemory is user-scoped.
- SessionContext is session-scoped.
- DecisionLog is agent-scoped.

## Configurable domains

LearnedKnowledge supports:

- `namespace="user"` — private per user;
- `namespace="global"` — shared with everyone;
- custom grouping such as a team/domain namespace.

EntityMemory supports the same high-level namespace choices:

- user-private entity graph;
- global shared graph;
- custom grouping.

## Architectural lesson

Personal and shared knowledge are not simply different query filters over one undifferentiated domain. They carry different ownership and mutation implications.

A shared project fact might be readable by many principals but writable only through a project-authorized workflow. A personal preference might be writable by the subject plus explicitly delegated assistants. A global reference corpus may be read-only to ordinary agents.

## Ledger effect

**KA-I-034 candidate → reinforced.**

Letta provided the first separation evidence; Agno now independently provides both explicit scope mechanisms and concrete cross-user mutation failures when that scope is dropped.

---

# 8. #8334 — identity keys must contain the ownership scope

Open issue #8334 reports an older EntityMemory cross-tenant collision:

- entity row primary identity omitted `user_id` under a supposedly user-private namespace;
- two users recording the same entity slug/type could collide on one database key;
- writes could overwrite the other user's entity content while reads remained user-filtered;
- one user's write could therefore corrupt another user's data and become unreadable to the writer.

The issue remains open, but **current source no longer matches the reported vulnerable identity formula**.

## Current positive fix

`build_learning_id()` is now the central identity-key constructor for identity-keyed learning types.

For user-scoped EntityMemory:

- `user_id` is required;
- a fixed-width SHA-256-derived user segment is included in the row key;
- raw user IDs are not embedded directly in URL/log-visible IDs;
- the digest avoids separator-shifting collisions from crafted IDs;
- same entity/type under different users maps to physically distinct keys.

Current tests explicitly cover user-isolated entity memory.

## Migration support

Agno also ships migration machinery for legacy user-less entity keys.

The migration:

- identifies already-correct rows;
- rekeys recoverable legacy rows;
- merges a legacy row into a newer target when safe;
- detects owner/content disagreement where structurally visible;
- quarantines contaminated rows rather than silently assigning them to a user;
- preserves unrecoverable evidence for operator review unless explicitly purged;
- copies/read-verifies a new row before deleting the old row;
- warns that the DB surface lacks transactional/CAS protection for the entire migration and instructs operators to run it offline.

The source also explicitly notes that some Mongo historical contamination is structurally undetectable because a collision can overwrite both content and owner consistently. Absence of detectable contamination is therefore not interpreted as proof no collision happened.

## Architectural lessons

1. **Ownership scope belongs in identity when identity is intended to be tenant-local.**
2. Identity-formula changes are schema migrations, not cosmetic refactors.
3. Migration must preserve uncertainty: corrupted mixed-owner data must not be silently reassigned.
4. Copy/read-verify before deleting old state is safer than delete-first migration.
5. A migration tool that cannot obtain atomic/CAS semantics must state the operational quiescence requirement explicitly.

## Ledger effect

Reinforces:

- KA-I-017 schema/identity migration;
- KA-I-034 ownership domains;
- KA-I-035 staged replacement;
- KA-F-023 concurrency qualification.

No new IDs required.

---

# 9. Ambiguous entity identity is explicitly representable

Agno current EntityMemory contains unusually direct source comments and tests around identity ambiguity.

## Observed behavior

The store:

- derives stable entity slugs from names;
- normalizes some identity-bearing punctuation so `C`, `C++` and `C#` do not collapse;
- preserves non-Latin identity text rather than dropping it;
- normalizes entity types conservatively;
- permits same-name entities under different named types;
- treats only the special `unknown` placeholder type as safely mergeable into a real type;
- warns/refuses ambiguous operations and teaches a qualified form such as `project/Harbor` when two same-name entities exist;
- explicitly describes fragmentation as the recoverable failure and wrong merge as dangerous because there is no unmerge.

Current tests verify same-name siblings remain separate and that ambiguous relationship/forget operations refuse to guess.

## Architectural lesson

A knowledge substrate must be able to say:

> `Harbor` is ambiguous between these candidate entities; no merge/resolution has been established.

It must not force every mention into one canonical entity simply because retrieval needs an ID.

## Ledger effect

**KA-I-005 candidate → reinforced.**

Graphiti supplied the first evidence; Agno independently demonstrates a current implementation that intentionally preserves ambiguity and asks for qualification.

## Non-conclusion

KA-I-004 remains candidate. Agno explicitly avoids unsafe merges because it lacks a general unmerge mechanism; it does not provide the full auditable/reversible merge/split transition required by KA-I-004.

---

# 10. Facts, events and relationships are semantically different

Current `EntityMemory` distinguishes:

- core properties;
- facts;
- events;
- relationships;
- aliases;
- archive state.

## Facts

Facts receive IDs and framework-owned created/updated timestamps.

Current facts can be retired without deletion using:

- `superseded_at`;
- `superseded_by`.

`live_facts()` excludes retired facts from normal current rendering.

## Events

Events carry occurrence `date` separately from framework created/updated timestamps.

This is useful temporal separation, although event `date` is still an application/model field rather than a general validated world-valid interval.

## Relationships

Relationships carry:

- own ID;
- far entity ID;
- relation string;
- direction;
- far entity type as part of identity where supplied;
- created/updated timestamps.

Duplicate reassertion updates the existing edge rather than appending indistinguishable duplicates.

## Archive

Entities archived via `forget` receive `archived_at`; they leave ordinary recall/context but remain searchable and can be revived by later evidence.

## Architectural lesson

Current-versus-history is not equivalent to deletion. Facts and entities can leave active recall while remaining addressable historical evidence.

## Ledger effect

Reinforces KA-I-006 and KA-I-009.

---

# 11. Supersession is useful but still model-derived

Agno's EntityMemory has a current LLM-based supersession judge.

The prompt asks the model to:

- inspect existing live facts;
- identify old facts contradicted/replaced by new facts;
- return exact old fact IDs and confidence values;
- be conservative;
- return no supersession when uncertain.

`EntityMemoryConfig.supersession_threshold` defaults to 0.8.

## Positive mechanisms

Compared with unrestricted prose rewriting, this is structurally better because:

- exact target fact IDs are required;
- retirement is represented instead of physical deletion;
- confidence threshold is explicit;
- historical facts remain stored;
- current rendering uses only live facts.

## Remaining epistemic gap

The judge is still a model-derived transformation. The record does not require:

- source trust comparison;
- authenticated source/principal;
- verification status;
- evidence references per supersession decision;
- model/prompt/profile lineage on the decision itself;
- explicit dispute state.

Therefore an LLM's contradiction judgment remains insufficient as Vera's final truth-retirement authority in higher-risk domains.

## Ledger effect

Reinforces the rationale behind KA-I-006/023 and KA-F-003. No new status change needed.

---

# 12. Current/entity-history rendering is bounded and visibly incomplete

EntityMemory context rendering is bounded by configuration:

- maximum entities expanded;
- directory size;
- live facts per entity;
- recent events per entity.

Current rendering explicitly marks truncation and shows facts with an `as of` display derived from updated/created timestamp.

This is positive because a partial context projection is not presented as an exhaustive record.

However, the `as of` timestamp is primarily record/mutation time, not necessarily the proposition's world-valid time.

## Architectural lesson

A model-visible memory projection needs:

- explicit coverage/truncation markers;
- source revision/generation;
- distinction between record freshness and world-validity.

## Ledger effect

Reinforces KA-I-024/027 and KA-F-027.

---

# 13. Memory injection remains a prompt-trust boundary

`UserMemoryStore.build_context()` formats remembered user content for injection into the agent's system prompt and instructs the agent to apply it naturally.

This is a product UX pattern, not a provenance upgrade.

Memory contents may originate from:

- explicit user statements;
- model extraction;
- model-driven update tools;
- older potentially poisoned conversation content;
- imported/migrated data.

Therefore prompt position cannot establish policy or truth.

## Ledger effect

Reinforces KA-I-015 and KA-F-017; no status change needed.

---

# 14. Epistemic state remains incomplete

Neither legacy `UserMemory` nor new `Memories` supplies a general required taxonomy for:

- explicit user statement;
- observation;
- inference;
- third-party claim;
- authenticated configuration;
- verified fact;
- disputed claim;
- known false;
- unknown/not-established.

EntityMemory fact dictionaries can carry arbitrary extras such as `confidence` or `source`, but those are optional unconstrained fields rather than substrate-wide epistemic semantics.

## Architectural lesson

Agno gives useful domain decomposition but does not resolve evidence question 4. The planned epistemic-state gap research remains necessary.

---

# 15. Temporal truth remains partial

Agno distinguishes several timestamps:

- row-level created/updated times;
- per-entry memory/fact/event/relationship created/updated times;
- event date;
- fact superseded time;
- entity archived time.

This is useful operational history.

But the general substrate still lacks a required bitemporal representation for arbitrary assertions:

- proposition valid-from/valid-until in the world;
- observation time;
- transaction/record time;
- correction time.

A fact's `updated_at` should not automatically become its world-valid `as of` semantics.

## Conclusion

Evidence question 5 remains a standards/domain gap, consistent with the coverage scan.

---

# 16. Relationship semantics remain open-ended

Agno EntityMemory relationships are first-class stored edges with IDs, direction and retirement support. This is better than storing all relationships only in prose.

However:

- `relation` is an arbitrary string;
- there is no governed relation vocabulary;
- inverse/transitive/symmetric semantics are not structurally declared;
- consequences of relationship types are not standardized;
- relationship provenance/trust is not required at the schema level.

## Ledger consequence

KA-I-007 remains **candidate**.

Agno provides more typed-edge evidence but not the governed semantic layer that KA-I-007 requires.

---

# 17. Read, search and mutation are different authority surfaces

Current Agno demonstrates several distinct ways knowledge reaches a model:

- automatic recall/context construction;
- search tools;
- model-driven update tools;
- REST management APIs;
- administrative database APIs;
- learned-knowledge/entity tools.

The #9983 and `MemoryTools` findings show why those surfaces cannot inherit authority merely from sharing one database class.

## Architectural lesson

For Vera, tool exposure should be derived from policy by action class, not generated mechanically from CRUD availability.

A principal might be allowed:

- read own memories;
- suggest a new memory;
- not directly overwrite an existing verified preference;
- request forget;
- never global-clear;
- search shared project knowledge;
- not publish shared knowledge.

## Ledger effect

Core independent evidence for KA-I-043 and KA-F-045.

---

# 18. Mutation success and durable semantic settlement

Several Agno memory paths return simple success strings after DB calls. The newer Learning subsystem frequently catches exceptions and logs debug-level failure, returning false/none or user-facing status.

The entity migration code explicitly compensates for adapter methods that can swallow failure by reading back target/deletion state before declaring migration success.

This is valuable positive evidence:

> mutation APIs can need postcondition verification when their return contract is not sufficient settlement evidence.

The migration also keeps explicit `failed`, `conflicts`, `contaminated`, `quarantined` and other buckets instead of flattening every row into migrated/not-migrated.

## Ledger effect

Reinforces KA-I-028 and KA-F-019.

---

# 19. Deletion, forgetting and privacy erasure are still different

Agno exposes several deletion-like operations with different semantics:

- delete one legacy UserMemory row;
- clear all legacy UserMemory rows for a user;
- database-global clear;
- new UserMemoryStore `clear` by replacing the aggregate with an empty content object;
- EntityMemory `forget` by retiring a fact/relationship or archiving an entity;
- migration quarantine/purge for contaminated data;
- session deletion with best-effort offloaded-result cascade.

These are not interchangeable.

A user-facing “forget” requirement may need to reconcile:

- canonical current knowledge;
- retired historical facts;
- source transcripts;
- derived projections/vectors/pages;
- backups;
- audit-required evidence;
- quarantined contamination records.

Agno does not present ordinary memory deletion as a complete privacy-erasure protocol.

## Ledger effect

Reinforces KA-I-016 and KA-F-026.

---

# 20. Concurrency remains backend/domain-specific

The historical Agno report already contained same-session lost-update and mixed-lock evidence. Current EntityMemory shows active engineering around concurrent writes:

- sync path re-resolves after a blocking supersession-model call before merging;
- async path uses a write lock and re-resolves inside the lock after awaited work;
- source comments explicitly warn that stale read-modify-write snapshots can overwrite sibling tool-call changes.

This is useful positive discipline.

However, the entity migration source explicitly states its DB surface cannot provide one transaction/CAS boundary for the migration and instructs operators to run it offline.

The new `UserMemoryStore` also models all a user's memories as one aggregate record and performs read-modify-save operations. KA-11 did not find a current public issue proving a lost update in that specific new path, so it is recorded as a concurrency review target rather than a confirmed new failure.

## Ledger effect

Reinforces KA-I-012 and KA-F-023 without a new ID.

---

# 21. Derived state and page revision evidence

Agno 3.0.7 release material describes Knowledge Page publication that coordinates metadata, text and vectors and preserves the prior revision when refresh fails. Read-only PageFileSystem tools operate against pinned revisions.

This direction fits established campaign invariants:

- derived/vector state must not be mistaken for source truth;
- publication/replacement needs generation identity;
- failed refresh should not destroy the previous active revision.

Because KA-11 did not inspect the entire page subsystem deeply, this remains recurrence evidence rather than a new resource-identity conclusion.

KA-I-037 therefore remains candidate.

---

# 22. Schema/version migration is semantic work

Current entity-memory rekeying is one of Agno's strongest positive references.

Changing the deterministic key from:

`entity_user_<type>_<slug>`

to a key that incorporates user identity changes:

- uniqueness semantics;
- ownership isolation;
- lookup identity;
- conflict behavior;
- migration/recovery requirements.

Agno correctly treats this as an explicit migration problem rather than assuming old rows magically gain new identity semantics.

The migration also distinguishes recoverable from contaminated rows and acknowledges some historical contamination cannot be reconstructed.

## Ledger effect

Strong recurrence for KA-I-017.

---

# 23. Recovery/replay state is still separate from knowledge

Agno workflows/sessions and learning/memory stores remain distinct. A recoverable workflow state does not prove:

- memory extraction completed;
- knowledge mutation settled;
- external effects settled;
- current principal/policy is unchanged.

Conversely, persistent user/entity memory is not a workflow continuation token.

This reinforces the campaign-wide separation between knowledge persistence and execution/recovery state.

No new Agno-specific invariant needed.

---

# 24. Unknown and negative knowledge remain incomplete

Agno can represent some negative/lifecycle states:

- absent memory;
- superseded fact;
- archived entity;
- migration contamination/conflict/failure;
- ambiguous entity identity.

But there is no general canonical distinction across all knowledge domains for:

- known false;
- unknown;
- not checked;
- searched but not established;
- disputed;
- stale;
- historically true but no longer current.

KA-I-021 remains necessary and the planned domain gap remains justified.

---

# 25. Scope of truth remains partly structural, partly ad hoc

Agno provides real structural scope fields:

- user;
- session;
- agent;
- team;
- namespace;
- entity type;
- project-like custom namespaces.

This is better than relying exclusively on arbitrary metadata blobs.

But assertion-level applicability such as:

- valid for software version X;
- valid only on device Y;
- valid in environment Z;
- valid during time interval T;
- valid for role R;
- valid only under policy revision P;

is not a universal part of memory/entity assertions.

KA-I-022 remains reinforced by earlier sources; Agno adds adjacent evidence, not a complete solution.

---

# 26. Twenty-six-question assessment

| # | Evidence question | Agno KA-11 assessment | Architectural significance |
|---|---|---|---|
| 1 | Stable identity | **strong operational evidence** | User/entity/learning IDs are explicit; current user-entity keys show identity must include intended scope. |
| 2 | Identity vs namespace | **strong boundary evidence** | `user_id`/namespace are storage scope unless bound to authenticated principal by AgentOS middleware. |
| 3 | Provenance | **partial** | Agent/team/input/timestamps exist; transformation/model/prompt/evidence lineage remains incomplete. |
| 4 | Epistemic state | **weak** | Memory/entity fields do not require explicit/inferred/verified/disputed/unknown semantics. |
| 5 | Temporal truth | **partial** | Record timestamps, event date, superseded/archive times exist; general world-valid vs transaction time absent. |
| 6 | Conflict/supersession | **useful positive + caution** | Facts can retire without deletion; LLM judge remains derived and only partially provenance-bound. |
| 7 | Relationships | **partial** | First-class edges exist, but relation vocabulary/semantics are unconstrained. |
| 8 | Permissions/sensitivity | **high-value evidence** | #9983, `MemoryTools`, user-isolation middleware and user/global/custom namespaces directly expose ownership/mutation boundaries. |
| 9 | Actionability | **partial** | Tool/read/mutation classes exist; no general informational/planning/automation/policy-evidence taxonomy. |
| 10 | Knowledge vs authority | **strong boundary evidence** | Low-level global DB capability can be accidentally exposed as user memory tool; route auth is separate from stored knowledge. |
| 11 | Resources/artifacts | **adjacent** | Pages/pinned revisions useful, but KA-11 does not establish full logical-resource/locator/content-digest model. |
| 12 | Canonical vs derived | **good adjacent evidence** | Page publication and migration distinguish active/source/derived revisions; entity history remains separate from render. |
| 13 | Structured retrieval | **present** | User/entity DB lookups and deterministic scopes are queryable structurally. |
| 14 | Relationship retrieval | **present but limited** | Entity graph edges are searchable/renderable; semantics are not governed. |
| 15 | Full text | **present in pages/entity search** | Search exists, but not a complete source-provenance model. |
| 16 | Semantic retrieval | **present elsewhere in Agno** | Relevance remains retrieval behavior, not truth. No unique new lesson. |
| 17 | Composite retrieval | **partial** | Scope plus structured/search mechanisms exist, but not a general hard-gate/fusion contract for Vera. |
| 18 | Context construction | **strong evidence** | User/entity memory context is explicitly constructed/bounded and may be system-prompt projected. |
| 19 | Poisoning/injection | **reinforcement** | Persistent memory remains lower-trust content despite system-prompt placement. |
| 20 | Concurrency | **strong implementation evidence** | Entity re-resolution/locks and offline migration warning show concurrency semantics must be explicit per domain/backend. |
| 21 | Derived integrity | **adjacent** | Page coordinated publication and migration verification reinforce generation/reconciliation rules. |
| 22 | Deletion/retention | **high-value boundary evidence** | delete, clear, archive, retire, quarantine and purge have materially different semantics. |
| 23 | Schema evolution | **strong** | User-entity key migration demonstrates semantic identity migration and contamination handling. |
| 24 | Recovery semantics | **reinforcement** | Memory/learning state remains separate from workflow recovery/effect settlement. |
| 25 | Unknown/negative | **partial** | Ambiguity, superseded/archive/conflict states exist, but general taxonomy remains absent. |
| 26 | Scope of truth | **partial** | user/session/agent/team/namespace structural scopes exist; assertion applicability remains incomplete. |

---

# 27. Ledger decisions

## KA-I-005 — candidate → reinforced

> Ambiguous/unresolved identity must be representable; identity resolution must not force a merge.

Agno current EntityMemory independently supports this through same-name siblings, type-qualified disambiguation, refusal of ambiguous operations and explicit preference for recoverable fragmentation over irreversible wrong merge.

## KA-I-034 — candidate → reinforced

> Personal/private and shared/project knowledge domains require distinct ownership plus explicit read/write authority.

Agno provides independent current evidence through user/global/custom namespaces, authenticated route scoping, #9983's cross-user clear defect, #8334's historical identity collision and current user-scoped-key fix/migration.

## KA-I-043 — candidate → reinforced

> Persistent knowledge mutation authority must be policy-distinct from knowledge read/retrieval authority; append, revise/supersede, delete/forget, consolidate/rewrite and sensitivity/ownership changes require separately governable action classes.

Agno independently exposes distinct add/update/delete/clear controls and shows why database-global clear cannot be treated as ordinary user forget.

## KA-F-045 — observed → reinforced

> A model/runtime that is allowed to retrieve persistent knowledge is also implicitly allowed to append, delete or semantically consolidate that knowledge without an independently evaluated knowledge-mutation authority decision.

Agno's MemoryTools defaults bundle get/add/update/delete, and Agentic memory modes expose mutation surfaces to the model. This independently matches MAF's memory-tool authority evidence.

## KA-F-049 — new, observed

> An owner-scoped knowledge surface resolves update/delete by a globally addressable object ID without reapplying the current caller's owner/domain scope at mutation time.

Evidence: current Agno `MemoryTools.update_memory` / `delete_memory` omit `run_context.user_id` from target lookup/deletion while current AgentOS REST routes demonstrate the scoped pattern.

## Deliberate non-promotions

- **KA-I-004 stays candidate.** Agno explicitly says unsafe merge has no unmerge; it does not implement full reversible merge/split lineage.
- **KA-I-007 stays candidate.** Agno relationships are first-class edges, but relation strings are not governed semantic vocabulary.
- **KA-I-031 stays candidate.** Agno context rendering is bounded but KA-11 did not establish exact settled knowledge revision attached to every active model context.
- **KA-I-037 stays candidate.** Page/revision evidence is adjacent but does not independently establish the full logical-resource/locator/content-digest formulation.
- **KA-I-038–040 stay candidates.** No sufficiently direct independent Agno match was established.
- **KA-I-044–045 stay candidates.** Agno has adjacent lifecycle evidence but not a complete independent match.

---

# 28. Failure / regression fixtures to retain

1. **Cross-user clear fixture:** seed Alice and Bob; invoke model-facing clear as Alice; Bob must survive.
2. **ID-only update fixture:** expose `MemoryTools` to Alice; provide Bob's memory ID; update must fail without revealing/mutating Bob.
3. **ID-only delete fixture:** same as above; delete must fail and Bob survives.
4. **Authenticated-route parity:** direct tool, REST, MCP/remote and async surfaces must enforce the same subject ownership semantics.
5. **Global admin separation:** an explicit global memory-clear capability must require a separately authorized admin/domain operation and must never be reachable through a user-forget alias.
6. **User-scoped entity collision:** two users create same entity slug/type under user namespace; two distinct physical/logical identities must remain.
7. **Crafted user-ID collision:** user IDs containing separators must not shift entity-key boundaries.
8. **Legacy migration:** rekey old entity rows without deleting source before verified target write.
9. **Contaminated migration:** mixed-owner row is quarantined/reported, not silently assigned.
10. **Ambiguous same-name entity:** two entity types with same display name remain separate; unqualified mutation/link/forget fails closed.
11. **Wrong-type correction:** placeholder `unknown` can resolve to real type; two real differing types do not silently merge.
12. **Fact supersession:** old fact retires rather than disappears; source history remains addressable.
13. **Low-confidence contradiction:** below-threshold model judgment must not retire live fact.
14. **Relationship retirement:** replacing a relationship does not implicitly delete the old edge unless explicit retirement semantics are invoked.
15. **Context truncation:** model-visible context must visibly disclose bounded projection rather than imply exhaustiveness.
16. **Concurrent entity writes:** interleaved assistant tool calls must not overwrite sibling changes after awaited model/DB calls.
17. **User-memory aggregate concurrency:** concurrent writes to one user aggregate require later dedicated qualification; a stale whole-record write must not silently lose another mutation.
18. **Delete vs privacy-erasure:** ordinary memory clear/delete must not be accepted as proof that source transcripts, derived indexes or backups are erased.

---

# 29. Reuse candidates for later architecture synthesis

These are evidence-backed mechanisms worth considering later, not implementation decisions:

- explicit user/global/custom knowledge domain scope;
- authenticated route scope resolved separately from client/storage `user_id`;
- user scope incorporated into deterministic tenant-local entity identity;
- fixed-width digest segments to avoid delimiter/crafted-ID collisions and raw-ID exposure;
- same-name ambiguity retained rather than forced merge;
- type-qualified disambiguation;
- facts retired through supersession metadata rather than physical deletion;
- archived entities remain searchable historical evidence;
- visible context truncation markers;
- copy/read-verify/delete migration sequence;
- contaminated historical data quarantined rather than falsely repaired;
- explicit operation toggles for add/update/delete/clear;
- dangerous wide-scope mutation disabled by default where possible;
- route-level user-scope helpers that make missing scope a documented programming hazard.

---

# 30. Explicit non-conclusions

KA-11 does **not** conclude that:

- Agno should or should not be adopted by ACL/Vera;
- every Agno memory API is cross-user unsafe;
- #8334 remains exploitable on current main — current source contains a user-scoped identity fix and migration despite the issue remaining open;
- every use of `clear_memories()` is a bug — an explicitly authorized administrator may legitimately need a global clear operation;
- the current `MemoryTools` ID-only mutation path has been independently exploited in production — the conclusion is based on current source contracts, not a live reproduction;
- Agno's EntityMemory is a complete world-knowledge ontology;
- Agno's LLM supersession judge is sufficient truth authority for Vera;
- Agno's event dates/timestamps implement general bitemporal semantics;
- Agno relationship strings provide governed ontology semantics;
- the new Page subsystem satisfies the full canonical resource/artifact model;
- any storage/database technology has been selected.

---

# 31. Primary sources inspected

Current upstream repository/release:

- `https://github.com/agno-agi/agno`
- current main `e75921a683d015e82d271ca96e52b11beec095e1`
- release `v3.0.7`

Memory ownership/mutation:

- `libs/agno/agno/memory/manager.py`
- `libs/agno/agno/tools/memory.py`
- `libs/agno/agno/db/base.py`
- `libs/agno/agno/db/sqlite/sqlite.py`
- `libs/agno/agno/os/routers/memory/memory.py`
- `libs/agno/agno/os/middleware/user_scope.py`
- issue `agno-agi/agno#9983`
- PR `agno-agi/agno#9986`

Learning/entity architecture:

- `libs/agno/agno/learn/config.py`
- `libs/agno/agno/learn/schemas.py`
- `libs/agno/agno/learn/utils.py`
- `libs/agno/agno/learn/stores/user_memory.py`
- `libs/agno/agno/learn/stores/entity_memory.py`
- `libs/agno/agno/learn/migrations.py`
- issue `agno-agi/agno#8334`
- current user-isolation/entity-memory tests discovered in `libs/agno/tests/unit/learn/`

Historical discovery map:

- `docs/research/projects/agno.md`
- `docs/research/knowledge-architecture/COVERAGE_SCAN.md`

---

# Stop point

KA-11 ends after the current Agno knowledge-ownership/mutation, identity, entity-history, migration, context and deletion evidence has been reconciled into the cumulative campaign ledgers.

No W3C provenance research, temporal/bitemporal standards work, ontology/relationship-vocabulary research, ABAC/ReBAC study, privacy-erasure study, resource/artifact standards study, Home Assistant/Matter domain study, retrieval-requirements work, hostile-scenario synthesis, schema selection, storage selection or implementation is begun by this task.
