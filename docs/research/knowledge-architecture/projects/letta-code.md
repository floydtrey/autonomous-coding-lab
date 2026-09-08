# KA-3 — Letta Code Knowledge-Architecture Revisit

**Campaign:** Knowledge Architecture Evidence Campaign  
**Task:** KA-3  
**Research date:** 2026-09-08  
**ACL branch:** `research/agent-landscape`  
**ACL parent checkpoint:** `4aece181bab2720bba77db5a256c7a4ae068d7d4`  
**Canonical upstream:** `letta-ai/letta-code`  
**Current upstream revision inspected:** `2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8`  
**Current package version observed:** `0.31.13`  
**Historical Letta report revision:** `701f2a5367828847313876c735ade27b9df97689`  
**Status:** bounded revisit complete; no architecture, database, storage engine, ontology, framework, benchmark or implementation selection made.

---

## 1. Task boundary

KA-3 revisits Letta Code only through the question defined by the Knowledge Architecture Evidence Campaign:

> What does current primary evidence from Letta Code tell us about building a durable, general knowledge substrate?

This is deliberately different from the original project-landscape question of whether Letta Code is a good agent harness.

The task therefore concentrates on:

- persistent identity and identity boundaries;
- raw experience versus curated long-term memory;
- MemFS canonical and projected state;
- provenance and epistemic status;
- temporal and historical semantics;
- conflict, correction and supersession;
- personal versus shared knowledge domains;
- permissions, security and authority boundaries;
- active-context construction;
- recall/search behavior;
- reflection/dreaming as background knowledge integration;
- concurrency and settlement;
- restore, sync and recovery;
- canonical versus derived views;
- deletion/retention implications;
- reproducibility when persistent memory affects execution;
- current failure evidence that exposes architecture-level risks.

KA-3 does **not**:

- choose Letta Code for ACL or Vera;
- choose Git as the canonical knowledge database;
- choose a vector database, graph database or filesystem format;
- define the final ontology or record schema;
- implement memory, retrieval, policy or execution systems;
- benchmark Letta Code or models;
- migrate existing research data;
- start KA-4 LlamaIndex;
- perform cross-project synthesis beyond recurrence bookkeeping in the campaign ledgers.

---

## 2. Evidence discipline

This report separates four evidence classes:

1. **Observed current mechanism** — directly inspected in current source or first-party project material at the pinned revision.
2. **Failure evidence** — current/open issue reports or controlled reproductions that expose a mechanism failure. Issue evidence is not treated as proof that every deployment fails.
3. **Derived architecture lesson** — what the observed mechanism/failure implies for a general knowledge substrate.
4. **Non-conclusion** — what the evidence does *not* establish.

The current upstream `main` revision was compared to the historical Task 18 revision. It had advanced only eight commits, and the inspected memory architecture remained materially recognizable: persistent agent identity, conversation identity, Git-backed MemFS, recall history, reflection worktrees, prompt compilation from committed memory and shared-memory repositories remain the key mechanisms.

The revisit intentionally uses current source rather than copying the historical report's conclusions forward.

---

# 3. Executive assessment

Letta Code remains one of the strongest architecture references in the campaign for **persistent-agent knowledge organization** and **background memory integration**, but it is not a general epistemic truth substrate.

Its most valuable current design ideas are:

1. **Persistent agent identity is separate from conversation identity.** One long-lived `agent_id` can participate in multiple `conversation_id`s while carrying the same long-term memory.
2. **Recall history is separate from curated long-term memory.** Conversation history is searchable experience; MemFS is editable future-facing memory.
3. **Only committed MemFS state is compiled as active memory.** The local compiler reads Markdown from Git `HEAD` and records the exact `memfsRevision` in the compiled system-prompt envelope.
4. **Memory, skills and harness policy/configuration are separate state classes.** Current prompts explicitly send credentials to a harness secret store and say security/compliance behavior that must not depend on recall belongs in the harness.
5. **Reflection is an integration workflow, not just an LLM summarization call.** Dedicated worktrees, branches, dirty-state checks, parent refresh, merge/conflict handling, cleanup and explicit final statuses determine whether reflection input counts as consumed.
6. **Shared memory is a separate organization-owned domain.** Repositories can be attached to multiple agents without becoming part of each agent's in-context personal memory.
7. **Git provides strong mutation lineage but not epistemic truth.** A commit can prove what changed and when in repository history; it does not prove that the learned claim is true, verified, current or authorized.
8. **The current reflection conflict rule is too weak for a general truth model.** An open controlled evaluation shows the current “latest evidence” heuristic can incorrectly weaken confirmed facts or confabulate merged facts.
9. **Local commit, reflection integration and remote synchronization are different settlement phases.** Current failure reports show valid commits can be discarded before integration or fail to synchronize afterward.
10. **Persistent memory is part of execution identity when reproducibility matters.** A headless-orchestration request explicitly documents that undeclared inherited memory makes same-input retries diverge for reasons outside the task record.
11. **Views and projections can lie without canonical state being lost.** Current issue evidence shows UI surfaces can report zero memory or hide valid non-Markdown MemFS resources.
12. **Restore is an authority-bearing replacement operation.** Current source still removes active memory before copying the selected backup, making restore non-atomic on failure.

The strongest KA-3 conclusion is therefore not “use Letta memory.” It is:

> Durable knowledge needs explicit identity, source/evidence separation, committed revision identity, epistemic metadata, authority boundaries, integration settlement, and reproducible context construction. Git-backed editable memory supplies only some of those properties.

---

# 4. Current upstream boundary

## 4.1 Revision and change since historical research

Current `letta-ai/letta-code` `main` was inspected at:

`2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8`

Observed package version:

`0.31.13`

The historical Task 18 report inspected:

`701f2a5367828847313876c735ade27b9df97689`

The compare showed only eight newer commits. Those changes did not replace the fundamental knowledge architecture inspected in Task 18.

## 4.2 Why exact profile still matters

Even in this narrow version interval, behavior depends on more than the package label:

- local versus API backend changes recall-search capabilities;
- Cloud/Desktop versus local runtime can change transcript projection behavior;
- reflection safety depends materially on the chosen model family under the same prompt;
- existing versus freshly initialized memory repositories can differ in Git credential configuration;
- shared-memory projection and sync depend on runtime/harness state.

Therefore `letta-code 0.31.x` is not a complete behavior identity for knowledge derivation or retrieval.

---

# 5. Core state planes

The current implementation is easiest to reason about as several distinct planes.

## 5.1 Persistent agent identity

Current MemFS prompts describe one long-lived agent identity identified by `agent_id`.

The agent can have multiple concurrent conversations identified by `conversation_id`.

This separation is important because a conversation is an episode/context thread, not the long-term identity that owns knowledge.

### Derived lesson

A general substrate should not use a chat/session/thread identifier as a substitute for persistent subject/agent/person identity.

### Non-conclusion

Letta's `agent_id` is still an application identity. It does not itself prove a real-world person's identity, authenticated principal identity, or canonical cross-system identity.

---

## 5.2 Recall memory / conversation history

Current prompts describe recall as the agent's historical experience across conversations.

The local recall subagent uses transcript-backed full-text search with date filters and message-ID expansion. The API recall subagent exposes `vector`, `fts` and `hybrid` modes, with hybrid described as vector similarity plus full-text ranking.

This plane answers questions such as:

- what was said?
- when was it discussed?
- what decision/outcome appeared in that conversation?

It is not the same as the agent's compact long-term MemFS knowledge.

### Derived lesson

Raw or near-raw experience should remain separately addressable from curated durable knowledge. A derived statement such as “the user prefers X” must not destroy the underlying conversation evidence that led to it.

### Non-conclusion

Recall history is not automatically pristine evidentiary truth. Runtime projection bugs can affect how provider events become persisted/rendered message records. It is a source plane, not a cryptographically complete evidentiary ledger.

---

## 5.3 Agent-owned MemFS

Current MemFS is a Git-backed filesystem rooted per agent. It can contain:

- system memory files that become in-context memory;
- external Markdown/files used on demand;
- skills and related procedural resources;
- other structured resources within the configured constraints.

This plane answers a different question from recall:

> What has the agent chosen to carry forward as durable memory or reusable procedure?

That distinction is one of the strongest reusable Letta ideas.

---

## 5.4 Shared memory repositories

Current first-party shared-memory guidance says shared memory is created independently of any one agent, owned by the organization, stored as its own Git repository, and attachable to one or more agents.

Each attached repository has:

- its own local projection root;
- its own remote origin;
- its own Git history;
- separate synchronization behavior;
- possible concurrent writers.

The shared repository is not automatically inserted into the agent's system prompt.

### Derived lesson

Knowledge ownership/domain and context inclusion are separate concerns. Shared project knowledge can be available without becoming personal identity memory.

---

## 5.5 Skills/procedures

Letta explicitly distinguishes reusable procedures/skills from ordinary memory.

This is important because a statement of fact and a procedure that causes tool use are different risk classes even if both are stored as text files.

---

## 5.6 Harness policy, permissions, credentials and trusted runtime configuration

Current prompts explicitly warn not to place secrets in memory because MemFS is Git-tracked and can be synchronized off-machine. Credentials belong in the harness secret store and are referenced indirectly.

The prompts also distinguish memory from harness-enforced permissions/tools/configuration and note that safety or compliance behavior that must not depend on model recall belongs in the harness.

### Derived lesson

This directly reinforces the campaign's central invariant:

**Knowledge != Authority != Execution.**

A remembered sentence saying “you may execute X” is not permission to execute X.

---

# 6. Committed memory versus working state

Current local system-prompt compilation is unusually explicit about the active memory revision.

The compiler:

1. resolves the agent's memory directory;
2. reads Git `HEAD`;
3. enumerates committed Markdown files using `git ls-tree`;
4. reads file contents with `git show HEAD:<path>`;
5. builds the system/external projection;
6. records `memfsRevision` in the compiled-prompt result;
7. separately records compile time, agent ID and conversation ID.

Uncommitted working-tree files are not active compiled memory.

## 6.1 Architecture significance

This creates three useful states:

- **working/pending memory** — files edited but not committed;
- **committed memory revision** — Git `HEAD`;
- **compiled context projection** — a model-context representation produced from a specific committed revision.

These should not be collapsed.

A general substrate should be able to answer:

- What is the canonical settled revision?
- What mutations are pending?
- Which revision was used to construct this model context?
- Has a newer revision appeared since this context was compiled?

## 6.2 Positive pattern

Recording `memfsRevision` in the compilation result is a strong pattern for reproducibility and debugging.

## 6.3 Limitation

Git `HEAD` identifies repository state, not epistemic validity. A wrong fact can be perfectly committed.

---

# 7. Git provenance is mutation provenance, not epistemic provenance

Git supplies useful lineage:

- content hashes;
- commits;
- diffs;
- authorship fields;
- branch/worktree history;
- merge relationships;
- rollback material;
- synchronization ancestry.

Reflection commits can also carry generated-by/agent-style trailers.

These properties are valuable, but they answer:

> What repository mutation happened?

They do not fully answer:

- Which source observation supports this claim?
- Was it explicit or inferred?
- Was it verified?
- What confidence or trust class applies?
- Was the source user-authored, document-derived, sensor-derived or model-generated?
- Is the statement current in the world?
- Is it disputed?
- What contradicted it?
- Which transformation produced this summary?
- May the claim influence a high-risk action?

A general knowledge substrate needs both mutation lineage and epistemic lineage.

---

# 8. Temporal semantics

Letta has strong **record history** but limited structured **world-valid truth**.

Git history and message timestamps establish when the system recorded or changed content. Conversation messages also carry creation timestamps. Reflection state records progress through transcript ranges/steps.

However, MemFS text generally expresses world-time semantically in prose rather than through a general bitemporal assertion model.

Examples:

- “User lives in Birmingham” may be edited to another city.
- Git can show when the file changed.
- That does not necessarily encode exactly when the user moved, when the old statement ceased being valid, or when the system learned the correction.

### Derived lesson

Record/transaction time and world/event-valid time remain separate requirements. Git solves the former better than the latter.

### Non-conclusion

KA-3 does not treat Git commit timestamps as a substitute for bitemporal knowledge semantics.

---

# 9. Conflict, correction and supersession

Current reflection guidance tells the reflection subagent to resolve contradictions in favor of the latest evidence and to fix stale information at its source rather than append duplicate versions.

This gives compact current memory, but it is epistemically under-specified.

## 9.1 Current failure evidence: issue #4029

Open issue #4029 reports a controlled prompt-level evaluation using the current conflict rule:

- four conflict cases;
- ten models;
- three runs per model/case;
- 120 total runs;
- all runs manually adjudicated by the issue author.

Reported results:

- direct stale-address update: 30/30 pass;
- compatible-fact split: 30/30 pass;
- temporary-stay versus new-home restraint: 17/30 fail;
- anecdote versus confirmed severe-allergy restraint: 13/30 fail.

The issue documents failures including:

- weakening/deleting a confirmed severe shellfish allergy after one anecdote;
- fabricating a composite address by joining pieces of old and new statements.

The issue explicitly notes the evaluation is prompt-level rather than a full runtime tool-loop test.

## 9.2 Architecture significance

“Latest evidence wins” is not a valid universal truth rule.

Conflict handling needs at least:

- source class;
- source trust;
- explicit versus inferred basis;
- confidence/verification;
- domain/risk class;
- whether the newer evidence explicitly states a change;
- possibility of both statements being simultaneously true in different scopes/times;
- unresolved/disputed state;
- escalation/confirmation where appropriate.

## 9.3 Important distinction

Git rollback makes a mistaken memory edit mechanically reversible. It does not prevent the mistake, identify the stronger evidence, or tell the runtime that the current claim is disputed.

---

# 10. Background reflection as a state-integration workflow

Letta's reflection worktree architecture is one of the most valuable mechanisms in the campaign.

Current source creates a dedicated branch/worktree from the parent memory `HEAD`, gives the reflection process a constrained memory scope, then explicitly finalizes the result.

Observed final statuses include:

- `merged`;
- `no_changes`;
- `parent_dirty`;
- `merge_conflict`;
- `dirty_uncommitted`;
- `failed`.

The implementation treats the transcript as consumed only for:

- `merged`;
- `no_changes`.

A recompile is required only when the result is `merged`.

## 10.1 Architecture significance

This correctly rejects the naive model:

`LLM produced memory edits -> memory learned`

Instead, the shape is closer to:

`evidence slice -> proposed changes -> isolated worktree -> commit(s) -> validation -> parent refresh -> integration -> settled revision -> context recompile`

with failure/retry states at multiple boundaries.

## 10.2 General lesson

A background knowledge worker should not be allowed to mark its source material “processed” merely because it produced output. Input-consumption state should advance only after the authoritative knowledge mutation settles.

---

# 11. Settlement failure: committed does not mean integrated

Current issue #4266 provides a concrete example.

The reporter observed reflection subagents that:

- generated valid memory commits;
- left helper scripts untracked in the worktree;
- triggered `dirty_uncommitted` during finalization;
- caused the worktree/branch to be force-removed;
- left the transcript eligible for retry.

The reporter found dangling blobs and 29 dangling reflection commits, including duplicate/triplicate attempts over the same transcript content.

## 11.1 Architecture lesson

A commit is only one settlement milestone.

For a background knowledge mutation, distinguish at minimum:

- proposed;
- locally committed;
- integration validated;
- merged into canonical parent;
- synchronized/replicated where required;
- context projection updated;
- source input marked consumed.

## 11.2 Retry/idempotency lesson

If failed integration retries the same evidence slice, the retry needs stable operation/input identity and deduplication semantics. Otherwise repeated reflection can regenerate duplicate or diverging candidate mutations.

---

# 12. Settlement failure: integrated/local does not necessarily mean synchronized

Issue #4249 reports a Windows/Desktop case where reflection produced local memory commits but the parent memory repository could not be refreshed/pushed because of credential-helper state.

The report distinguishes fresh-repository credential configuration from existing repositories that lacked the newer local helper setup.

## 12.1 Architecture significance

A knowledge system that replicates/synchronizes canonical state needs explicit durability levels.

Examples:

- local working copy updated;
- local canonical commit exists;
- parent integration complete;
- remote acknowledged;
- replicas caught up;
- context compiler has observed the new revision.

A single boolean `saved=true` is insufficient.

## 12.2 Migration lesson

Runtime/configuration migrations can affect knowledge durability even when the knowledge schema itself has not changed. Existing repositories must be migrated/verified, not assumed to inherit fresh-install behavior.

---

# 13. Shared memory and authority domains

Current shared-memory behavior is architecturally useful:

- repository is organization-owned rather than agent-owned;
- multiple agents may attach it;
- each agent gets its own projection/mount;
- cross-agent direct path access is guarded;
- read/write repositories are pushed after a clean turn;
- push collisions use pull/rebase/retry behavior;
- dirty/conflicted state is not silently rewritten;
- repository history remains ordinary Git history.

## 13.1 What this gets right

It prevents “shared knowledge” from becoming indistinguishable from personal agent identity memory.

That maps naturally to future domains such as:

- household knowledge;
- project repositories;
- organizational procedures;
- team working state;
- public reference data;
- personal/private memory.

## 13.2 Current policy gap: issue #4267

Open enhancement issue #4267 explicitly asks for a projection/policy layer because attaching a whole repository does not express finer runtime boundaries such as:

- user;
- role;
- task;
- agent;
- organization;

or differing write semantics such as:

- private/direct write;
- collaborative commit;
- governed propose/review.

The issue is a feature request, not proof of a current exploit.

### Derived lesson

Repository attachment is a coarse resource boundary. A general knowledge substrate still needs principal-, purpose- and resource-sensitive read/write policy when different parts of one knowledge domain require different authority.

---

# 14. Knowledge, skills and policy must remain distinct

Letta provides unusually direct evidence for this campaign's `Knowledge != Authority != Execution` separation.

Current prompts distinguish:

### Memory

Durable facts, preferences, identity/context and future judgment.

### Skills

Reusable procedural knowledge that can be loaded when needed.

### Harness/mod/configuration

Runtime-enforced tools, permissions, provider behavior, credentials, hooks and security boundaries.

The prompt explicitly says rules that must not depend on LLM recall should live in the harness.

## 14.1 Architecture lesson

A background memory worker may learn:

> “The user often wants deployment X.”

That does **not** authorize:

- installing a tool;
- changing network policy;
- writing a credential;
- changing approval thresholds;
- modifying trusted code;
- executing deployment X.

Promotion from remembered content into policy/trusted procedure must be a separate authorized transition.

---

# 15. Secrets and sensitive data

Current prompts prohibit storing credentials/API keys/tokens in MemFS because memory is Git-tracked and may synchronize off the machine.

This is a strong practical reminder that persistent knowledge stores should assume replication/history unless proven otherwise.

## 15.1 Architecture lesson

Ordinary knowledge records should store references to secrets, not reusable secret material.

The credential broker/secret store should remain a different authority plane with narrower access and retention semantics.

## 15.2 Non-conclusion

This design guidance does not by itself provide a complete privacy/sensitivity classification model for ordinary personal knowledge.

---

# 16. Retrieval and context construction are separate

Letta demonstrates multiple retrieval/context paths rather than one universal memory query.

## 16.1 Recall search

API-backed recall can use:

- vector;
- full-text;
- hybrid.

Local recall is documented as transcript-backed full-text search.

## 16.2 MemFS context

Committed system memory is compiled directly into the system prompt.

External memory is represented primarily through a discoverability projection and can be opened on demand.

## 16.3 Shared memory

Attached shared repositories are not automatically in the system prompt.

## 16.4 Skills

Skill names/descriptions can be exposed as available capabilities while detailed procedure content is loaded separately.

### Architecture significance

Retrieval is not context construction.

A future context builder must decide:

- deterministic/pinned material;
- evidence fetched from recall;
- current settled memory revision;
- resources that should remain outside context until requested;
- permissions/sensitivity;
- freshness/currentness;
- epistemic basis;
- token budget;
- whether content is descriptive knowledge or executable/policy-bearing state.

---

# 17. Retrieval rank is not truth

Letta's recall search exists to find relevant past messages.

Whether a message ranks highly under FTS/vector/hybrid search says nothing by itself about:

- truth;
- authority;
- confidence;
- current validity;
- whether the message was later corrected.

This independently reinforces the campaign distinction between retrieval relevance and epistemic confidence.

---

# 18. Backend/profile-specific retrieval semantics

Current recall behavior is materially backend-dependent:

- API prompt advertises vector/FTS/hybrid modes;
- local prompt describes transcript-backed full-text search and direct underlying-file inspection.

This means a declarative capability such as “recall search” is incomplete without a realized backend/profile identity.

The same is true for transcript projection: issue #4248 reports large Cloud/Desktop-versus-local differences in reasoning-record preservation under the same model/provider.

### Architecture lesson

A derived knowledge/retrieval profile should identify the concrete source/runtime/backend/parser/model configuration that produced it.

---

# 19. Transcript projection integrity

Issue #4248 reports that Cloud/Desktop runtime sometimes fails to preserve reasoning as a separate reasoning record while a local comparison with the same model/provider is much more consistent.

This issue concerns reasoning/UI/runtime representation, not a direct demonstration that ordinary user-message facts are lost.

However, it exposes a broader requirement:

> A projected transcript/event stream should not be assumed complete merely because the provider emitted data.

If transcript projections become evidence for memory/reflection, their ingestion profile and completeness state matter.

### Derived lesson

Source evidence should ideally preserve stable event/message identity and record transformation/loss where collector/runtime normalization changes the representation.

### Non-conclusion

KA-3 does not treat hidden model reasoning as canonical user knowledge or require storing private chain-of-thought. The architecture lesson is about projection integrity, not about retaining hidden reasoning.

---

# 20. Canonical versus derived views

Two current issue reports make this distinction concrete.

## 20.1 Issue #3845 — false zero

The startup profile selector uses legacy memory-block metadata and can display `0 memory blocks` for a MemFS-backed agent whose actual active memory is committed Markdown under `system/`.

The issue explicitly proposes counting committed files from `HEAD`, because uncommitted files are not active compiled context.

## 20.2 Issue #3894 — incomplete viewer

The `/palace` memory viewer was reported to hide non-Markdown MemFS files even though skills legitimately contain scripts/assets/references alongside Markdown.

## 20.3 Architecture lesson

A derived view, dashboard, index or count must never turn “not represented by this projection” into “does not exist.”

Derived surfaces should carry:

- source revision;
- coverage/type scope;
- generation profile;
- completeness/readiness state;
- explicit unknown/unavailable status where appropriate.

This is the same general class as a summary that omits source evidence: absence in a derivative is not proof of absence in canonical state.

---

# 21. Restore and replacement semantics

Issue #4195 reports that `letta memory restore` removes the active memory directory before copying the selected backup into place.

Current source at the inspected revision still shows the destructive order:

1. remove active root;
2. copy backup to root.

If the copy fails, active memory may be missing/partial. A backup nested under the active root can also be deleted before it is copied.

## 21.1 Architecture lesson

Canonical knowledge replacement should use staged/validated cutover semantics, for example:

`validate source -> stage replacement -> verify -> atomic swap/fence -> retain rollback point -> reconcile projections`

rather than:

`delete canonical -> try copy`.

Restore is an authority-bearing state transition and should have a settlement record of its own.

---

# 22. Deletion, forgetting and Git history

Current MemFS guidance emphasizes Git history and the ability to inspect/revert past changes.

That is useful for correction and recovery, but it means deleting a file or editing a fact in current `HEAD` is not automatically equivalent to privacy erasure from repository history, remotes or backups.

The reflection guidance includes deleting content that the user asked to forget, but ordinary Git deletion still leaves historical commit reachability unless a separate history-rewrite/retention process occurs.

## 22.1 Architecture lesson

The substrate needs distinct operations for:

- remove from current knowledge;
- supersede but retain history;
- archive;
- hide from ordinary retrieval;
- privacy erasure across canonical and derived planes;
- retention/legal hold;
- backup/replica reconciliation.

## 22.2 Non-conclusion

KA-3 did not establish Letta's complete server-side deletion/GC policy for every remote/backup plane, so this report does not claim an unfixable privacy defect. It identifies the semantic gap between ordinary Git deletion and verified erasure.

---

# 23. Reproducibility and hidden persistent state

Issue #3807 is especially relevant to ACL-style orchestration.

The reporter describes a scheduler that treats each task as a function of declared inputs. Letta headless mode reuses persistent agent memory across runs, so a retry can inherit knowledge created by an earlier failed attempt even when that memory state is not part of the scheduler's recorded inputs.

A Letta maintainer replied that ephemeral conversations were being developed for one-off programmatic workflows.

## 23.1 Architecture lesson

When reproducibility matters, execution identity must include the persistent knowledge revision/profile that influenced the run.

A trace should be able to name:

- agent identity;
- conversation/run identity;
- exact active memory revision;
- prompt/config profile;
- model/provider profile;
- relevant attached/shared resource revisions;
- policy/authority revision.

Otherwise “same task inputs” may not actually mean same effective inputs.

## 23.2 Important distinction

Persistent memory is valuable for long-lived Vera behavior and undesirable for some deterministic batch jobs. The architecture needs explicit execution modes rather than treating persistence as universally correct.

---

# 24. Concurrency and multi-writer state

Letta's current memory design contains several concurrency-aware mechanisms:

- reflection uses isolated worktrees/branches;
- parent dirtiness blocks unsafe merge;
- parent refresh handles fast-forward/rebase paths;
- shared-memory push collisions use pull/rebase/retry;
- dirty/conflicted shared repositories are not silently overwritten.

These are positive patterns.

At the same time, issue #4266 shows retries can repeatedly process the same reflection slice when integration fails, producing duplicate dangling attempts.

### Derived lesson

Multi-writer knowledge mutation requires both:

- repository/storage concurrency control;
- semantic operation identity/idempotency.

Git branch isolation alone does not solve repeated semantic mutation of the same source evidence.

---

# 25. Epistemic classes still missing from MemFS

Letta's current memory can encode nuanced prose, but the general substrate still needs structured states that plain Markdown/Git do not guarantee.

Examples include:

- explicit user statement;
- inferred preference;
- model-generated hypothesis;
- observation;
- verified fact;
- disputed fact;
- known false;
- unknown;
- searched/not-established;
- historically true but no longer current;
- tentative identity match;
- source trust class;
- confidence;
- sensitivity;
- authority-use eligibility.

Issue #4029 is a practical demonstration of why these distinctions matter: without structured epistemic basis, a reflection model has to infer whether new content is a true update, a temporary state, an anecdote or a contradiction that should remain unresolved.

---

# 26. Relationship semantics

Letta MemFS can of course contain textual relationships, and shared repositories/agent IDs create operational associations, but KA-3 did not find a general typed relationship-truth model comparable to a canonical graph assertion system.

This is important because:

- “agent is attached to repository” is runtime/resource state;
- “Alice manages Bob” is a world claim;
- “device belongs to household” is a domain relationship;
- “principal may write resource” is authority/policy;
- “memory derived from transcript” is provenance.

These should not become one undifferentiated edge type merely because all can be represented as links.

---

# 27. Resource identity and large artifacts

MemFS/shared memory can hold files and skills can include scripts, assets and reference material.

This is useful as a resource plane, but a general substrate still needs stable resource metadata beyond pathname alone, including where applicable:

- resource ID;
- canonical/source location;
- content hash;
- media type;
- version/revision;
- extraction profile;
- provenance;
- sensitivity/owner;
- retention status;
- derived text/chunk identity.

Issue #3894 reinforces that user-facing views may cover only some file types even when the repository contains more.

---

# 28. Unknown and negative knowledge

Letta's Markdown memory can state “unknown” in prose, but the substrate does not structurally require distinctions such as:

- false;
- unknown;
- not yet checked;
- checked and not established;
- conflicting evidence;
- expired/stale;
- retired/superseded;
- impossible within a scope.

This remains a gap for a general cross-domain system.

---

# 29. Schema/ontology evolution

MemFS is intentionally flexible and file-oriented. That reduces rigid schema migration pressure, but flexibility does not eliminate semantic migration.

Changing:

- frontmatter conventions;
- prompt compilation rules;
- memory constraints;
- skill format;
- reflection policy;
- repository synchronization configuration;
- backend/runtime interpretation

can change the meaning or behavior of existing state.

Issue #4249's fresh-versus-existing repository credential configuration is an operational example: newer initialization behavior does not retroactively exist in already-created repositories.

### Derived lesson

Knowledge-format and runtime-profile migrations need explicit detection/validation even when the underlying files remain readable.

---

# 30. Security and injection boundary

Letta's strongest relevant design decision is to keep critical authority outside ordinary remembered text.

That is necessary because MemFS content is model-visible and model-editable by design.

A malicious or mistaken memory entry could influence future model reasoning. It must not, by persistence alone, gain authority to:

- expand tool permissions;
- bypass approvals;
- obtain credentials;
- change security policy;
- change principal identity;
- authorize external effects.

This independently reinforces the campaign rule that persistent/retrieved content remains untrusted unless its provenance and authority class say otherwise.

---

# 31. Current evidence matrix — 26 campaign questions

The table below applies the campaign's standard questions directly to current Letta evidence.

| # | Campaign question | Current Letta evidence | Architecture reading | Confidence |
|---|---|---|---|---|
| 1 | Stable identity | Persistent `agent_id`; multiple `conversation_id`s; per-agent MemFS root. | Long-lived knowledge identity should not be a chat/session ID. | high |
| 2 | Identity vs namespace | Agent/conversation/repository identifiers route state; shared-memory guards and harness auth remain separate concerns. | Namespace/resource IDs are not sufficient authenticated principal identity. | medium-high |
| 3 | Provenance | Git commits/diffs/branches; reflection trailers; recall message IDs/timestamps. | Strong mutation/source-location lineage, incomplete epistemic derivation lineage. | high |
| 4 | Epistemic state | Mostly represented in natural language; reflection prompt uses heuristic recency; #4029 exposes restraint failures. | Explicit/inferred/verified/disputed/confidence states need structured representation. | high |
| 5 | Temporal truth | Git/message timestamps are strong record time; world-valid intervals are not a general structured primitive. | Record time != validity time. | high |
| 6 | Conflict/supersession | Reflection edits stale memory in place; Git retains old revision; “latest evidence” rule is under-specified. | Supersession is authority-bearing and needs provenance/verification, not chronology alone. | high |
| 7 | Relationships | Operational agent↔repo attachments exist; world relationships mostly live as text. | Do not treat operational attachment or textual co-occurrence as canonical typed truth relations. | medium-high |
| 8 | Permissions/sensitivity | Harness permissions, secret store, cross-agent guards; shared attachment; fine-grained projection-policy request #4267. | Knowledge ownership/read/write policy must be separate from prompt instructions. | high |
| 9 | Actionability | Memory and skills can guide behavior, but harness controls tools/permissions. | Knowledge may inform action; it must not grant action authority. | high |
| 10 | Knowledge vs authority | Explicitly separated by prompts/harness architecture. | Strong positive reference for campaign invariant. | high |
| 11 | Resource identity | Git paths/repos/revisions identify files; not a complete cross-domain resource envelope. | Stable semantic resource IDs and content/version metadata remain needed. | medium-high |
| 12 | Canonical vs derived | Committed Git `HEAD` vs compiled prompt/UI/tree/view; #3845/#3894 show projection mismatch. | Derived view absence must not imply canonical absence. | high |
| 13 | Structured retrieval | Date/agent/message IDs and file paths provide deterministic retrieval dimensions. | Valuable alongside semantic search, not replaced by it. | high |
| 14 | Relationship/graph retrieval | No general canonical relationship traversal found in current MemFS architecture. | Letta does not answer this requirement by itself. | high |
| 15 | Full-text retrieval | Local recall is transcript-backed FTS; API supports FTS mode. | Exact/evidentiary retrieval remains useful and separate from semantic. | high |
| 16 | Semantic retrieval | API recall supports vector and hybrid modes. | Retrieval rank is relevance, not truth. | high |
| 17 | Composite retrieval | API recall exposes hybrid; local profile differs. | Realized retrieval profile/backend must be recorded. | high |
| 18 | Context construction | Compiler builds prompt from committed HEAD, metadata and available skills; shared repo not automatically injected. | Context construction is a distinct revisioned transformation. | high |
| 19 | Poisoning/injection | Model-visible persistent memory can influence future behavior; harness keeps secrets/policy separate. | Persistent text remains untrusted content unless separately governed. | high |
| 20 | Concurrency | Worktrees/merge checks/shared rebase; #4266 retry duplication. | Need writer isolation plus semantic idempotency/input identity. | high |
| 21 | Derived-state integrity | Compiled prompt carries revision; UI/view bugs can diverge; remote sync can fail. | Derived projections need revision/readiness/reconciliation state. | high |
| 22 | Deletion/retention | Git history intentionally preserves changes; ordinary current-file deletion is not verified erasure. | Current removal, historical retention and privacy erasure are separate operations. | medium-high |
| 23 | Schema evolution | Flexible files reduce hard schema coupling; initialization/prompt/constraint/runtime changes still alter semantics. | Exact profile/migration state remains part of knowledge interpretation. | medium-high |
| 24 | Recovery | Git rollback material exists; reflection has explicit failure states; restore ordering remains unsafe in #4195/current source. | Recovery/restore must be staged, atomic and reconciled. | high |
| 25 | Unknown/negative knowledge | No general structured taxonomy found. | Unknown/false/disputed/not-established need first-class states. | high |
| 26 | Scope of truth | Agent/conversation/shared repo scopes exist; role/task/purpose/write semantics remain coarse. | Claims and access policy need explicit applicability scope beyond storage location. | high |

---

# 32. Strong positive mechanisms worth preserving as candidates

These are mechanisms, not framework-selection conclusions.

## 32.1 Persistent identity separate from episode identity

Long-term memory owner and conversation thread should be separate IDs.

## 32.2 Exact committed revision in context compilation

A model invocation should be traceable to the exact settled knowledge revision used to construct context.

## 32.3 Source history separate from curated memory

Recall/evidence should remain separately searchable after long-term memory is condensed.

## 32.4 Background integration with explicit settlement states

Reflection input should be consumed only after canonical integration succeeds or is explicitly a no-op.

## 32.5 Separate personal and shared knowledge domains

Ownership and lifecycle differ even when both are Git-backed files.

## 32.6 Separate memory, procedures and trusted runtime authority

Learned knowledge must not silently become security policy or executable authority.

## 32.7 Pending versus committed state

Uncommitted memory should not silently appear in canonical active context.

## 32.8 Human-debuggable lineage

Diffs, commits and worktree states make background mutations inspectable and reversible.

---

# 33. Failure/anti-pattern evidence to carry forward

## 33.1 Latest-evidence heuristic used as universal conflict policy

Evidence: #4029.

Risk: strong older evidence can be weakened by anecdotal newer content; models can fabricate composites while trying to reconcile.

## 33.2 Background integration retry without stable semantic idempotency

Evidence: #4266.

Risk: the same transcript slice is repeatedly transformed, creating duplicate/different abandoned mutations.

## 33.3 Local commit interpreted as final durability

Evidence: #4249 plus reflection finalization design.

Risk: local persistence, canonical integration and synchronized durability are conflated.

## 33.4 Destructive restore before replacement validation

Evidence: #4195 and current source ordering.

Risk: recovery operation destroys the last good canonical state before proving the replacement is usable.

## 33.5 Derived view reports false absence

Evidence: #3845 and #3894.

Risk: user/agent decisions are based on an incomplete projection while canonical files still exist.

## 33.6 Hidden persistent memory omitted from execution identity

Evidence: #3807.

Risk: retries/replays differ despite identical declared task inputs.

## 33.7 Runtime transcript projection treated as complete evidence

Evidence: #4248, with scope caveat.

Risk: downstream reflection/retrieval can reason over a runtime-dependent projection without knowing that some event classes were lost or merged.

---

# 34. Reassessment of the assertion-centric hypothesis

KA-3 does not authorize final schema synthesis, but it provides useful evidence for the later question of whether knowledge should be assertion-centric.

Letta's file model demonstrates the benefits of a flexible human-editable representation, but also exposes what plain mutable prose cannot reliably encode:

- explicit versus inferred basis;
- evidence links;
- confidence;
- dispute state;
- valid-time intervals;
- supersession lineage;
- authority-use eligibility;
- structured applicability scope.

This evidence **leans toward** giving individual claims/assertions a first-class epistemic envelope, because the current reflection failures arise precisely when the model must infer those properties from prose.

However, KA-3 does **not** settle whether Claim/State/Preference/Relationship should be one generalized Assertion family or multiple first-class record families. That decision remains reserved for the synthesis phase after all planned evidence and retrieval requirements are complete.

---

# 35. What KA-3 does not conclude

1. Letta Code is not selected as ACL/Vera's memory engine.
2. Git is not selected as the canonical knowledge database.
3. MemFS Markdown is not selected as the canonical schema.
4. The reflection prompt issue does not prove every Letta model/runtime corrupts memory.
5. Issue #4267 is a feature request, not evidence of an observed authorization breach.
6. Issue #4248 does not imply hidden reasoning must be stored as canonical knowledge.
7. Git history does not prove Letta cannot implement privacy erasure; it proves ordinary file deletion and verified erasure are different semantics.
8. Shared-memory repository ownership does not by itself establish a complete ABAC/ReBAC model.
9. Recall search does not satisfy all cross-domain structured/graph/resource retrieval requirements.
10. The current file model does not disprove an assertion-centric canonical model.
11. No storage engine, graph database, vector database or hybrid index has been selected.
12. No ACL/Vera implementation work has begun.
13. KA-4 LlamaIndex has not begun.

---

# 36. Highest-value KA-3 conclusions

1. **Persistent identity and conversation identity must remain separate.** Letta demonstrates this cleanly and directly.
2. **Raw experience and curated long-term memory are different knowledge planes.** Recall should remain source-addressable after memory consolidation.
3. **Active model context must identify the exact settled knowledge revision that produced it.** Letta's `memfsRevision` is an unusually strong pattern.
4. **Working, committed, integrated, synchronized and compiled states are distinct settlement phases.** A single `saved` flag cannot safely represent them.
5. **Background reflection is an authority-bearing knowledge transformation.** It needs explicit settlement, provenance, idempotency and conflict policy.
6. **Newest evidence is not automatically stronger evidence.** #4029 provides direct controlled evidence of the failure mode.
7. **Git provenance is not epistemic provenance.** Commits explain mutations; they do not establish truth, confidence, verification or world-valid time.
8. **Memory != skill != policy != credential != execution authority.** Letta's harness separation strongly reinforces this campaign invariant.
9. **Personal and shared memory need separate ownership/authority domains.** Repository attachment is useful but too coarse for fine-grained principal/purpose/write policy.
10. **Derived views must expose coverage and revision.** False zero/hidden-file issues show why a projection cannot be treated as canonical inventory.
11. **Restore and synchronization are first-class knowledge lifecycle operations.** They need staged validation, settlement and reconciliation.
12. **Persistent memory revision is part of reproducible execution identity.** Undeclared inherited memory makes replay semantics ambiguous.
13. **Record history is not world-valid temporal truth.** Git is strong transaction history but weak as a general bitemporal assertion model.
14. **Structured epistemic state remains necessary.** Markdown prose alone cannot safely distinguish explicit, inferred, verified, disputed, historical and unknown knowledge.
15. **Letta is a strong mechanism reference, not a complete general knowledge substrate.** Its gaps are directly useful evidence for the later architecture synthesis.

---

# 37. Confidence summary

### High confidence

- agent versus conversation identity separation;
- recall versus MemFS separation;
- committed `HEAD` as local compiled-memory source;
- `memfsRevision` context identity;
- reflection finalize state machine;
- transcript consumed only on merged/no-change reflection outcome;
- memory/skills/harness distinction;
- secrets excluded from MemFS by design guidance;
- shared repository ownership/attachment model;
- local/API recall mode difference;
- current restore delete-before-copy ordering;
- #4029 prompt-level evaluation as reported;
- #4266/#4249/#3845/#3894/#4195 issue evidence as bounded failure reports.

### Medium-high confidence

- need for fine-grained shared-memory projection/write policy, because current first-party repo behavior is clear but #4267 is an enhancement request rather than a demonstrated breach;
- Git-delete versus privacy-erasure distinction, because ordinary Git semantics are clear but complete remote retention/GC policy was not exhaustively inspected;
- transcript-projection completeness requirement from #4248, because the concrete issue concerns reasoning-record representation rather than ordinary user-fact loss.

### Explicitly unresolved

- final canonical record families;
- exact ABAC/ReBAC policy model;
- bitemporal representation;
- final resource identity model;
- final retrieval architecture;
- final storage technology;
- final migration strategy;
- whether Git is retained only for human-editable projections or any canonical plane;
- whether assertion-centric design survives later evidence.

---

# 38. KA-3 stop condition

KA-3 is complete when this report, the cumulative invariant/failure ledgers and campaign state are committed as research/documentation-only changes.

After that commit:

- Letta Code research is complete for this bounded revisit;
- no LlamaIndex research is authorized by queue order alone;
- no cross-project synthesis should begin;
- no database/schema/implementation selection should begin.
