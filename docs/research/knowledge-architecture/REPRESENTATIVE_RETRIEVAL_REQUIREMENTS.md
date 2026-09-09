# Representative Retrieval Requirements

**Campaign:** Knowledge Architecture Evidence Campaign  
**Phase:** Representative Retrieval Requirements  
**Status:** requirements-only; no retrieval implementation, schema selection, or storage selection

---

# Purpose

This document turns the completed knowledge-architecture evidence campaign into concrete acceptance requirements.

The goal is not to prescribe a database, query language, graph engine, vector store, ontology, or retrieval implementation. The goal is to define what the future ACL/Vera knowledge substrate must be able to answer or support correctly.

A future conceptual schema, storage design, retrieval stack, and prototype should be rejected if they cannot satisfy these requirements without violating the campaign invariants.

These are not merely natural-language prompts. Each requirement identifies the semantic distinctions the substrate must preserve so a correct answer can be constructed.

---

# General acceptance rules

For all requirements below:

1. **Knowledge, authority, and execution remain separate.** Retrieval never grants permission to act.
2. **Current truth, historical truth, and historical belief are different query intents.**
3. **Direct evidence, assertion, inference, derived projection, and presentation remain distinguishable.**
4. **Unknown, unavailable, stale, conflicting, known false, and known no-value remain distinct.**
5. **Source/provenance must be available when the answer depends on it.**
6. **Permission and purpose filtering must occur before protected content is exposed to a model or caller that lacks authority.**
7. **Mutable locators/aliases must not substitute for exact version identity when reproducibility matters.**
8. **Derived/indexed results must not silently outrank canonical/evidence state.**
9. **Deletion/restriction state must remove or fence data from ordinary retrieval according to the settled reconciliation state.**
10. **A query that cannot be answered safely should return a semantically honest unresolved/partial/unknown result rather than fabricate certainty.**

---

# Requirement format

Each requirement contains:

- **Request** — representative user/agent question or task.
- **Must distinguish** — semantic distinctions required for correctness.
- **Minimum evidence/output** — what the retrieval/context layer must be able to expose.
- **Primary retrieval mode** — expected dominant path; implementation is deliberately unspecified.

---

# A. Identity, people, aliases, and ambiguity

## RR-01 — Resolve a person across aliases without forced merge

**Request:** “What do we know about Robert Smith? I may also have called him Bob Smith.”

**Must distinguish:**
- semantic person identity from display name/alias;
- one person with multiple aliases from two similarly named people;
- resolved identity from ambiguous candidate identity.

**Minimum evidence/output:**
- the resolved person only if evidence is sufficient;
- aliases/source identities used in the resolution;
- ambiguity surfaced explicitly when unresolved.

**Primary retrieval mode:** structured identity lookup + relationship/evidence resolution.

## RR-02 — Preserve two same-name people

**Request:** “Show me what we know about the two John Smiths I’ve encountered.”

**Must distinguish:**
- stable entity identities;
- source-specific identifiers;
- namespaces/domains;
- unresolved or conflicting identity evidence.

**Minimum evidence/output:** separate records with supporting distinguishing context; no forced merge.

**Primary retrieval mode:** structured identity retrieval.

## RR-03 — Explain an identity merge

**Request:** “Why does Vera think ‘Bob at work’ and Robert Smith are the same person?”

**Must distinguish:**
- identity assertion from ordinary facts about the person;
- evidence supporting the merge;
- automated inference versus explicit user confirmation.

**Minimum evidence/output:** merge/identity-resolution provenance and confidence/status; reversible transition identity if a merge occurred.

**Primary retrieval mode:** provenance + identity relationship traversal.

## RR-04 — Handle replacement hardware without rewriting device history

**Request:** “Is the new kitchen thermostat the same device as the old one?”

**Must distinguish:**
- physical device identity;
- user-facing role/name;
- platform/entity IDs;
- replacement/recommissioning event.

**Minimum evidence/output:** whether the role/location is continuous while the physical device identity changed; evidence of replacement.

**Primary retrieval mode:** structured identity + temporal relationship history.

---

# B. Current truth, historical truth, and historical belief

## RR-05 — Current state

**Request:** “Where are my keys?”

**Must distinguish:**
- current best-supported state;
- last-known state;
- stale/unavailable observations;
- direct versus inferred location.

**Minimum evidence/output:** current best answer with freshness and epistemic basis; “unknown/not established” when evidence is stale or insufficient.

**Primary retrieval mode:** structured current-state projection + freshness filter.

## RR-06 — Historical world truth

**Request:** “Where were my keys at 6:30 this morning?”

**Must distinguish:**
- world-valid time;
- observation/record time;
- later corrections.

**Minimum evidence/output:** best current reconstruction of the 06:30 state with supporting evidence and validity interval.

**Primary retrieval mode:** temporal structured retrieval.

## RR-07 — Historical belief

**Request:** “What did Vera believe about the keys at 6:30 this morning?”

**Must distinguish:**
- what is now believed to have been true;
- what the system actually believed/knew at that historical transaction time.

**Minimum evidence/output:** historical belief snapshot/revision and evidence available then.

**Primary retrieval mode:** bitemporal/revision retrieval.

## RR-08 — Late correction without history rewrite

**Request:** “When did Vera learn that the device actually failed at 2:10 AM?”

**Must distinguish:**
- valid/event time of failure;
- observation time;
- record/transaction time of the later correction.

**Minimum evidence/output:** all relevant times and provenance of correction.

**Primary retrieval mode:** temporal + provenance retrieval.

## RR-09 — Historical relationship

**Request:** “Which portal was Floyd assigned to on March 10?”

**Must distinguish:**
- person identity;
- portal relationship;
- relationship validity interval;
- current assignment versus historical assignment.

**Minimum evidence/output:** applicable assignment for the requested date with source/evidence.

**Primary retrieval mode:** temporal relationship lookup.

---

# C. Epistemic state, unknowns, conflicts, and negative knowledge

## RR-10 — Missing is not false

**Request:** “Does Bob own a truck?”

**Must distinguish:**
- no matching assertion found;
- explicitly known false;
- known no-value under a complete authoritative scope;
- unknown/not established.

**Minimum evidence/output:** “not established” unless a valid negative/completeness basis exists.

**Primary retrieval mode:** structured assertion lookup + completeness contract check.

## RR-11 — Known value exists, exact value unknown

**Request:** “Do we have a spare key, and where is it?”

**Must distinguish:**
- some-value-known-to-exist;
- known concrete value;
- no-value;
- not established.

**Minimum evidence/output:** e.g. “A spare is known to exist, but its location is unknown.”

**Primary retrieval mode:** structured epistemic-state retrieval.

## RR-12 — Conflicting sources

**Request:** “Where does Sarah work? I remember seeing two different employers.”

**Must distinguish:**
- multiple assertion occurrences;
- source/evidence per assertion;
- validity intervals;
- currentness/rank/verification state.

**Minimum evidence/output:** conflict surfaced rather than silently picking one unless selection policy has sufficient evidence.

**Primary retrieval mode:** assertion/evidence retrieval + conflict analysis.

## RR-13 — Formerly true versus false

**Request:** “Does Bob still work at Acme?”

**Must distinguish:**
- historically true but no longer current;
- currently false;
- unknown current status.

**Minimum evidence/output:** current applicability plus historical relationship if relevant.

**Primary retrieval mode:** temporal assertion/relationship retrieval.

## RR-14 — Observation versus inference

**Request:** “How do you know I’m home?”

**Must distinguish:**
- direct tracker/sensor observations;
- derived person-presence state;
- derivation/selection rules.

**Minimum evidence/output:** source observations and the derivation path used.

**Primary retrieval mode:** derived-state provenance traversal.

## RR-15 — Stale state

**Request:** “Is the back door locked?”

**Must distinguish:**
- fresh observed locked state;
- stale last-known locked state;
- unavailable device;
- unknown state.

**Minimum evidence/output:** never present stale last-known state as fresh current truth.

**Primary retrieval mode:** structured state + freshness/availability filter.

---

# D. Provenance, evidence, and derivation

## RR-16 — Why do you believe this?

**Request:** “Why do you think the LightOn recommendation behavior should work that way?”

**Must distinguish:**
- conclusion/assertion;
- direct evidence;
- source/resource version;
- transformation/research activity;
- derived summary versus primary evidence.

**Minimum evidence/output:** backward evidence chain sufficient to inspect the basis.

**Primary retrieval mode:** provenance graph/relationship traversal.

## RR-17 — Exact source version

**Request:** “Which exact version of the Agno source supported this finding?”

**Must distinguish:**
- repository/project identity;
- branch/tag/locator;
- exact commit/content version used;
- later repository state.

**Minimum evidence/output:** immutable observed version plus locator context.

**Primary retrieval mode:** resource identity + provenance.

## RR-18 — Provenance precision

**Request:** “Which exact inputs produced this conclusion?”

**Must distinguish:**
- exact usage edges;
- coarse shared-run co-occurrence;
- transformation occurrence;
- output generation.

**Minimum evidence/output:** exact inputs when known; explicitly lower-precision provenance when exact lineage was not recorded.

**Primary retrieval mode:** provenance retrieval.

## RR-19 — Forward impact

**Request:** “If this source document is withdrawn, what findings or summaries depend on it?”

**Must distinguish:**
- direct derivations;
- multi-source aggregates;
- indexes/embeddings/projections;
- source-independent results.

**Minimum evidence/output:** affected descendants and whether each requires deletion, invalidation, or rebuild.

**Primary retrieval mode:** forward provenance traversal.

## RR-20 — Provenance of provenance

**Request:** “Where did this provenance record itself come from?”

**Must distinguish:**
- source content;
- provenance record;
- provider/agent that asserted the provenance;
- transformation that generated/aggregated it.

**Minimum evidence/output:** provenance provider and generation lineage.

**Primary retrieval mode:** provenance-of-provenance retrieval.

---

# E. Relationships and graph/path semantics

## RR-21 — Direct relationship only

**Request:** “Which projects is Alice directly assigned to?”

**Must distinguish:**
- directly asserted relationship;
- inferred membership through team/org structure;
- mere graph connectivity.

**Minimum evidence/output:** only direct assignment assertions unless user asks for inferred relationships.

**Primary retrieval mode:** direct relationship lookup.

## RR-22 — Derived relationship explanation

**Request:** “Why is Alice considered part of Project X?”

**Must distinguish:**
- direct edge(s);
- inferred relationship;
- relation semantics/inference profile.

**Minimum evidence/output:** asserted path and inference rule/profile that produced the derived membership.

**Primary retrieval mode:** relationship traversal + inference explanation.

## RR-23 — Multiple independent assertions of same relationship

**Request:** “Who says Alice reports to Bob?”

**Must distinguish:**
- abstract relationship proposition;
- separately sourced relationship assertion occurrences.

**Minimum evidence/output:** each supporting statement occurrence with source/time/qualifiers.

**Primary retrieval mode:** relationship assertion + provenance retrieval.

## RR-24 — Time-qualified relationship

**Request:** “When did this sensor belong to the kitchen?”

**Must distinguish:**
- sensor identity;
- area relationship;
- validity interval;
- current versus historical area.

**Minimum evidence/output:** relationship timeline.

**Primary retrieval mode:** temporal relationship retrieval.

## RR-25 — Exact vs approximate mapping

**Request:** “Are these two ontology terms actually equivalent, or just close matches?”

**Must distinguish:**
- exact equivalence;
- close/broad/narrow mapping;
- deprecated/replaced term;
- ontology/version context.

**Minimum evidence/output:** mapping semantics and vocabulary versions.

**Primary retrieval mode:** structured vocabulary/relationship lookup.

---

# F. Resources, files, documents, repositories, and versions

## RR-26 — Logical document versus current file

**Request:** “Show me the current RiskCardOCR handoff document and tell me which version you used last time.”

**Must distinguish:**
- logical resource/document;
- mutable file/path/current locator;
- exact previously consumed version.

**Minimum evidence/output:** current locator/version plus prior exact version identity.

**Primary retrieval mode:** resource registry + version lineage.

## RR-27 — Same bytes, different meaning/provenance

**Request:** “Are these two identical files the same resource?”

**Must distinguish:**
- content equality;
- logical resource identity;
- provenance/owner/domain differences.

**Minimum evidence/output:** content-equivalent may be true while logical-resource identity remains separate.

**Primary retrieval mode:** content/version + resource identity comparison.

## RR-28 — Mutable alias resolution

**Request:** “What did `main` point to when the benchmark was run?”

**Must distinguish:**
- mutable branch/reference;
- historical ref target;
- exact commit consumed.

**Minimum evidence/output:** exact historical target and run provenance.

**Primary retrieval mode:** temporal resource/reference lookup.

## RR-29 — Chunk citation after parent revision

**Request:** “Does this cited chunk still correspond to the current document?”

**Must distinguish:**
- chunk identity;
- parent resource/version;
- current parent version;
- derivative staleness.

**Minimum evidence/output:** valid/current or stale, with exact parent revision.

**Primary retrieval mode:** derivative lineage + version comparison.

## RR-30 — Current derived-index generation

**Request:** “Is the semantic index current for this document set?”

**Must distinguish:**
- canonical source revisions;
- index generation/profile;
- stale/missing descendants.

**Minimum evidence/output:** generation coverage and source revision comparison.

**Primary retrieval mode:** derived-state metadata + structured comparison.

---

# G. Projects, ACL, research, and software knowledge

## RR-31 — Recover a prior project decision

**Request:** “What did we decide about starting ACL model benchmarks at 32K context, and why?”

**Must distinguish:**
- explicit user decision/preference;
- supporting rationale;
- later supersession if any;
- project scope.

**Minimum evidence/output:** current applicable decision, provenance, and whether superseded.

**Primary retrieval mode:** structured project/decision retrieval + semantic search for rationale.

## RR-32 — Current task versus historical backlog

**Request:** “What is the currently authorized research task?”

**Must distinguish:**
- queue/planned candidate;
- explicitly authorized current task;
- completed historical task.

**Minimum evidence/output:** current authorization state without treating “next in queue” as authority.

**Primary retrieval mode:** structured workflow/project-state lookup.

## RR-33 — Software-version applicability

**Request:** “Does this Agno failure still apply to the version we are using?”

**Must distinguish:**
- historical defect evidence;
- exact affected version/source revision;
- current observed version;
- fixed/unknown/current applicability.

**Minimum evidence/output:** version-qualified applicability with evidence.

**Primary retrieval mode:** structured version + evidence retrieval.

## RR-34 — Research finding versus final rule

**Request:** “Is KA-I-047 a final architecture rule?”

**Must distinguish:**
- candidate/reinforced/final status;
- evidence tasks;
- synthesis-stage decisions.

**Minimum evidence/output:** ledger status and evidence, without upgrading it prematurely.

**Primary retrieval mode:** structured ledger lookup.

## RR-35 — Related research by meaning

**Request:** “Find the work we did on stale state, even if the reports used different terminology.”

**Must distinguish:**
- semantic relevance;
- exact source reports;
- currentness/status;
- retrieval relevance from truth.

**Minimum evidence/output:** semantically relevant candidates with source identities; ranking not presented as confidence/truth.

**Primary retrieval mode:** semantic candidate retrieval + structured reranking/filtering.

---

# H. Authorization, sensitivity, purpose, and actionability

## RR-36 — Read versus disclose

**Request:** “Can I tell Bob this information about Alice?”

**Must distinguish:**
- caller identity;
- knowledge owner/subject;
- read permission;
- disclose-to-recipient permission;
- purpose/context;
- sensitivity.

**Minimum evidence/output:** authorization decision or safe refusal; protected content must not be revealed merely to explain denial.

**Primary retrieval mode:** policy-gated structured retrieval.

## RR-37 — Read versus model exposure

**Request:** “Can this private record be included in the context for this model?”

**Must distinguish:**
- user/caller authority;
- model/processor exposure authority;
- purpose;
- sensitivity;
- resource/knowledge scope.

**Minimum evidence/output:** exposure eligibility and obligations/redactions before model context construction.

**Primary retrieval mode:** pre-context authorization gate.

## RR-38 — Knowledge versus automation authority

**Request:** “You know I usually start the car before work. Start it now.”

**Must distinguish:**
- remembered routine/preference;
- current action request;
- current principal authorization;
- tool/capability authority;
- confirmation/verification requirements.

**Minimum evidence/output:** retrieval of the routine cannot itself authorize execution.

**Primary retrieval mode:** knowledge retrieval followed by separate policy/effect pipeline.

## RR-39 — Historical Permit is not current authority

**Request:** “You allowed this action yesterday; can you reuse that approval?”

**Must distinguish:**
- historical decision evidence;
- current policy/model revision;
- current principal/context;
- exact operation parameters.

**Minimum evidence/output:** fresh authorization required when decision context/version no longer matches.

**Primary retrieval mode:** decision provenance + current policy evaluation.

## RR-40 — Purpose-constrained use

**Request:** “Can this location history be used to answer me, shared with another household member, and used to trigger an automation?”

**Must distinguish:** three separate requested uses/purposes.

**Minimum evidence/output:** independent decisions for answer/disclosure/automation; no generic `can_access` result.

**Primary retrieval mode:** action/purpose-specific authorization.

## RR-41 — Indeterminate is not Permit

**Request:** “May this agent access the protected project notes?” when one required policy attribute cannot be resolved.

**Must distinguish:**
- Deny;
- Indeterminate;
- NotApplicable;
- Permit.

**Minimum evidence/output:** unresolved policy input must not silently become Permit.

**Primary retrieval mode:** policy decision path.

---

# I. Commands, effects, observations, and operational state

## RR-42 — Command attempt versus settlement

**Request:** “Did the front door actually unlock?”

**Must distinguish:**
- requested command;
- tool/API acknowledgement;
- effect ledger state;
- later physical observation.

**Minimum evidence/output:** actual settlement only when supported; otherwise attempted/pending/unknown.

**Primary retrieval mode:** effect ledger + observation retrieval.

## RR-43 — Capability versus availability

**Request:** “Can the thermostat set heating mode right now?”

**Must distinguish:**
- schema/profile says capability exists;
- current device availability;
- current authorization;
- capability/version drift.

**Minimum evidence/output:** supported-by-profile versus currently operable.

**Primary retrieval mode:** capability profile + current state + policy.

## RR-44 — Group/area target expansion

**Request:** “Which lights would ‘turn off the downstairs lights’ target right now?”

**Must distinguish:**
- area/group identity;
- current membership expansion;
- concrete entity/device targets;
- authorization per resulting target where required.

**Minimum evidence/output:** reproducible target set and expansion revision/time.

**Primary retrieval mode:** relationship/group expansion + policy filter.

## RR-45 — Derived person presence

**Request:** “Which tracker caused Vera to mark Sarah as home?”

**Must distinguish:**
- person identity;
- tracker identities;
- source observations;
- person-state derivation/selection rule.

**Minimum evidence/output:** exact supporting tracker/observation and derivation rule.

**Primary retrieval mode:** provenance + derived-state lookup.

---

# J. Deletion, restriction, retention, and reconciliation

## RR-46 — Deletion status across planes

**Request:** “Has everything about this private note been deleted?”

**Must distinguish:**
- canonical store;
- derived assertions/chunks;
- indexes/embeddings/summaries/caches;
- replicas;
- backups;
- exports/recipients;
- pending/unresolved planes.

**Minimum evidence/output:** plane-qualified reconciliation state; never a false single Boolean completion.

**Primary retrieval mode:** deletion/effect reconciliation status.

## RR-47 — Soft deleted versus erased

**Request:** “Can this deleted item still be recovered?”

**Must distinguish:**
- active;
- soft-deleted/recoverable;
- restricted/beyond-use;
- erased;
- backup-retained.

**Minimum evidence/output:** exact lifecycle status and allowed uses.

**Primary retrieval mode:** structured lifecycle retrieval.

## RR-48 — Restore anti-resurrection

**Request:** “After restoring yesterday’s backup, which later deletions/restrictions still need to be reapplied?”

**Must distinguish:**
- backup snapshot time/generation;
- later deletion/restriction events;
- restored data;
- derivative rebuild/reconciliation state.

**Minimum evidence/output:** all post-snapshot deletion/restriction intents that must fence restored content before activation.

**Primary retrieval mode:** temporal deletion ledger + restore reconciliation.

## RR-49 — Source deletion and aggregate rebuild

**Request:** “If Alice’s private record is erased, can this aggregate statistic remain?”

**Must distinguish:**
- direct derivative that contains the erased fact;
- multi-source aggregate;
- rebuildability without the source;
- privacy/use policy.

**Minimum evidence/output:** delete/invalidate/rebuild decision with source-lineage coverage.

**Primary retrieval mode:** forward lineage + policy.

## RR-50 — Restricted retention

**Request:** “This record must be retained for a bounded reason; may Vera still use it in normal reasoning?”

**Must distinguish:**
- possession/retention;
- ordinary retrieval eligibility;
- purpose-specific use authorization;
- restricted/beyond-use state.

**Minimum evidence/output:** retained does not imply normally retrievable/actionable.

**Primary retrieval mode:** lifecycle + purpose authorization gate.

---

# K. Composite retrieval and context construction

## RR-51 — Composite project answer with hard gates

**Request:** “Summarize the current ACL knowledge-architecture position and show the strongest supporting evidence, but exclude anything I am not authorized to expose to this model.”

**Must distinguish:**
- structured current campaign state;
- semantically relevant evidence;
- source/version/provenance;
- authorization/model-exposure eligibility;
- relevance versus truth/confidence;
- token/context budget.

**Minimum evidence/output:** policy-filtered context containing current authoritative project state plus source-addressable evidence; protected candidates must be excluded before model exposure.

**Primary retrieval mode:** composite retrieval + context construction.

## RR-52 — Cross-domain reasoning without schema leakage

**Request:** “What changed that explains why Vera now thinks the kitchen is empty and ACL’s current task is blocked?”

**Must distinguish:**
- two domains with different entity types and evidence;
- observations versus workflow state;
- temporal changes;
- derivations;
- project authorization/state;
- no dependence on Home Assistant- or agent-specific universal primitives.

**Minimum evidence/output:** independently sourced explanations for each domain, unified at the general knowledge/provenance/temporal layer rather than by domain-specific schema assumptions.

**Primary retrieval mode:** composite structured + provenance + semantic retrieval.

---

# Coverage matrix

The 52 requirements intentionally cover the campaign’s major semantic families:

- **Stable identity / ambiguity:** RR-01–04
- **Temporal truth / historical belief:** RR-05–09
- **Epistemic state / conflict / negative knowledge:** RR-10–15
- **Provenance / lineage:** RR-16–20
- **Relationships / ontology semantics:** RR-21–25
- **Resources / versions / derivatives:** RR-26–30
- **ACL/research/project knowledge:** RR-31–35
- **Authorization / sensitivity / purpose / actionability:** RR-36–41
- **Operational effect/state:** RR-42–45
- **Deletion / retention / erasure:** RR-46–50
- **Composite retrieval / context construction:** RR-51–52

Retrieval modalities exercised:

- deterministic structured lookup;
- temporal/bitemporal retrieval;
- direct relationship retrieval;
- inferred relationship/path explanation;
- provenance backward traversal;
- provenance forward-impact traversal;
- full-text/semantic candidate discovery;
- composite retrieval/reranking;
- policy-gated retrieval;
- context construction;
- effect/deletion reconciliation lookup.

---

# Acceptance properties for later storage/retrieval evaluation

A future architecture must be able to demonstrate all of the following using these requirements:

1. It can answer current-state questions without losing history.
2. It can answer historical-world and historical-belief questions differently.
3. It preserves source/evidence identities independently from derived conclusions.
4. It can represent identity ambiguity without forced merge.
5. It can expose conflicts rather than silently overwrite them.
6. It can distinguish missing/not-established from known-negative.
7. It can reconstruct direct support for consequential inferred relationships.
8. It can bind derivations to exact resource versions.
9. It can detect stale derived indexes/projections.
10. It can use semantic search for discovery without treating similarity rank as truth.
11. It can apply hard authorization gates before protected context exposure.
12. It can separate read/disclose/use/automate/mutate/delete authority.
13. It can distinguish tool acknowledgement from settled real-world effect.
14. It can distinguish capability existence from current availability/authority.
15. It can reconcile erasure across canonical, derived, backup and external planes.
16. It can prevent backup restore from resurrecting later deletion/restriction intent.
17. It can construct cross-domain context without embedding one domain’s ontology into universal primitives.
18. It can return partial/unknown/indeterminate results honestly when evidence or policy is incomplete.
19. It can expose enough provenance/revision identity for important answers to be audited.
20. It can satisfy these requirements without making storage technology itself the source of semantic truth.

---

# Explicit non-conclusions

This requirements set does **not** decide:

- final conceptual primitives/schema;
- relational versus graph versus document storage;
- PostgreSQL or any other database;
- vector store or embedding model;
- query language;
- authorization engine;
- effect-ledger implementation;
- deletion implementation;
- Home Assistant/Matter integration design;
- ACL/Vera implementation details.

Those decisions remain downstream of hostile review, conceptual synthesis, and small cross-domain prototype validation.

---

# Stop boundary

This phase ends after the requirements are documented and the campaign checkpoint is updated.

Do not begin the hostile/adversarial scenario review in this task.
