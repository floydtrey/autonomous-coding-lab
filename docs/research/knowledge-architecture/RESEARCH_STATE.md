# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** project revisits, coverage scan, promoted Agno revisit, and six bounded standards/domain gap tasks complete; stopped before non-AI operational-domain validation  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

---

# Scope lock

This campaign remains **research/requirements discovery only**.

The user explicitly requested scope-drift protection before KA-G3. The remaining pre-build gates remain mandatory.

Do **not**:

- restart broad agent-framework research;
- reopen completed project revisits without a concrete evidence gap;
- select a final conceptual schema yet;
- select PostgreSQL, Neo4j, RDF, graph databases, vector stores, object stores, content-addressable stores, policy engines, backup systems, retention engines, or other implementation technologies;
- implement a knowledge/resource store;
- implement authorization, deletion, retention, retrieval or context-construction services;
- create embeddings;
- migrate historical catalogs;
- benchmark models;
- implement ACL or Vera;
- run autonomous workers;
- treat a local delete return, soft delete, backup expiry, tombstone, hash, locator, provenance record or historical authorization decision as stronger evidence than its actual semantics support;
- skip retrieval-question, hostile-scenario, synthesis, and small-prototype gates.

The campaign remains governed by `CAMPAIGN_PLAN.md`.

---

# Completed campaign work

## Project evidence

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

## Standards/domain gaps

13. **KA-G1 — Epistemic, Temporal, Conflict and Negative-Knowledge Semantics** — complete
14. **KA-G2 — Relationships and Ontology Evolution** — complete
15. **KA-G3 — Formal Provenance / Evidence Lineage** — complete
16. **KA-G4 — Knowledge Authorization + Actionability / Use-Purpose** — complete
17. **KA-G5 — Resource / Artifact Identity and Lineage** — complete
18. **KA-G6 — Privacy Deletion / Retention / Erasure Reconciliation** — complete

---

# Detailed reports

Project revisits:

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

Gap reports:

- `gaps/epistemic-temporal-conflict.md`
- `gaps/relationships-ontology-evolution.md`
- `gaps/formal-provenance-evidence-lineage.md`
- `gaps/knowledge-authorization-actionability.md`
- `gaps/resource-artifact-identity-lineage.md`
- `gaps/privacy-deletion-retention-erasure.md`

Cumulative ledgers:

- `invariants.md`
- `failure-patterns.md`

This state is intentionally a compact checkpoint. Detailed evidence remains in dedicated reports.

---

# KA-G6 verification and boundary

User authorization:

- after KA-G5, user explicitly instructed `ok continue`;
- the documented next candidate was KA-G6, so this authorized KA-G6 only.

Starting branch/head:

`5f4e0fcb67ec2f697a27da12821b912141c366fe`

Starting commit message:

`research: complete resource artifact identity gap`

The branch was verified at that exact checkpoint before KA-G6 writes.

KA-G6 was bounded to:

- delete/forget/erase lifecycle semantics;
- retention and expiry semantics;
- soft-delete versus irreversible erasure distinction;
- restriction/beyond-use semantics;
- canonical versus derived cleanup;
- indexes/embeddings/summaries/caches/replicas;
- backup/restore resurrection hazards;
- tombstones/anti-resurrection markers;
- recipient/export propagation as a separate plane;
- audit evidence versus retained content;
- source deletion versus derivative invalidation/rebuild;
- media sanitization as a separate final-disposal layer;
- multi-plane reconciliation evidence.

Explicitly excluded:

- legal advice;
- legal-regime selection;
- final retention periods;
- legal-hold policy selection;
- final sensitivity taxonomy;
- anonymization-standard selection;
- final deletion API/schema;
- database/storage/backup technology selection;
- cryptographic-erasure implementation selection;
- implementation;
- Home Assistant/Matter operational validation;
- retrieval-question construction;
- hostile-scenario execution;
- conceptual architecture synthesis.

---

# KA-G6 primary evidence

## GDPR / EUR-Lex

https://eur-lex.europa.eu/eli/reg/2016/679/2016-05-04

Used for:

- storage limitation;
- erasure;
- restriction-of-processing distinction;
- copies/replications;
- recipient notification;
- bounded exceptions/retained processing purposes.

Qualification: GDPR is architecture evidence here, not selected as Vera's universal legal regime.

## European Data Protection Board

Current 2026 right-to-erasure coordinated-enforcement material plus storage-limitation guidance.

Used for:

- purpose-specific retention;
- backup deletion challenges;
- requirement to prevent erased/restricted data from silently returning after restore;
- deletion-procedure accountability;
- evidence against one longest retention period for every data class.

## UK ICO right-to-erasure guidance

https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/individual-rights/right-to-erasure/

Used for:

- live-system deletion versus backup overwrite schedules;
- backup data placed beyond ordinary use when immediate overwrite is impractical;
- requirement not to reuse erased backup-held data for ordinary processing.

## NIST SP 800-88 Rev. 2

https://csrc.nist.gov/pubs/sp/800/88/r2/final

Current final publication: September 2025.

Used for:

- media sanitization as a distinct confidentiality/disposal layer;
- sanitization program/validation;
- logical sanitization/cloud relevance;
- evidence that application-level deletion does not itself prove physical/media sanitization.

## NIST Privacy Framework lifecycle terminology

Used for full lifecycle framing: collection, retention, transformation, use, disclosure, sharing, transmission and disposal.

## Microsoft Azure / Entra soft-delete documentation

Used only as operational corroboration that soft deletion is an intentionally recoverable state and therefore cannot be equated with erasure.

No implementation technology was selected.

---

# Highest-value KA-G6 findings

## 1. Deletion completion is multi-plane reconciliation

A successful active-store delete does not prove removal/inaccessibility from:

- derived indexes;
- embeddings;
- summaries;
- caches;
- replicas;
- workflow/checkpoint state;
- recipients/exports;
- backups/restore paths.

This directly reinforces **KA-I-016**.

## 2. Soft delete is not erasure

Recoverable deletion and irreversible erasure require different lifecycle states and different user/system claims.

## 3. Retained does not mean ordinarily usable

A bounded retention purpose or backup-retention interval may justify continued possession while ordinary reasoning, model exposure, automation, training or disclosure remain prohibited.

## 4. Backup presence and active knowledge are different

Backup-held data may remain physically present while being fenced from ordinary use, but restore must preserve later deletion/restriction intent before the restored system becomes active.

## 5. Restore is a reconciliation event

An older snapshot must not erase evidence that a newer deletion/restriction occurred.

Conceptually:

`backup snapshot < deletion event < restore`

must not resurrect the deleted information as current knowledge.

## 6. Tombstones/control markers should be minimal

Anti-resurrection/audit state must not defeat erasure by preserving the entire deleted content.

## 7. Source erasure propagates through lineage

Chunks, extracted assertions, summaries, embeddings and indexes must be invalidated, removed or rebuilt according to explicit policy and lineage.

## 8. Derived aggregates may require rebuild rather than blind deletion

A multi-source aggregate may remain legitimate after rebuilding without the erased source.

## 9. Retention is purpose-specific

One maximum retention interval applied indiscriminately is not a sound architecture assumption.

## 10. Expiry and final erasure completion can differ

Expiry may trigger asynchronous reconciliation across planes; the system must distinguish queued/pending cleanup from settled completion.

## 11. Restriction and erasure are different

Restricted data can remain stored while being barred from ordinary processing/use.

## 12. Deletion scope must be explicit

Identity, domain, assertions/resources, time range, derived descendants, recipients and backup generations may all matter.

## 13. Identity ambiguity prevents safe global deletion and false completion

Unknown scope should produce partial/unresolved status rather than unsafe over-deletion or an inaccurate success claim.

## 14. External recipient/export copies are separate reconciliation planes

Local completion is not universal external completion.

## 15. Audit proof should not require retaining erased content wholesale

Minimum control metadata can prove request/decision/reconciliation without keeping the content itself.

## 16. Logical deletion does not imply media sanitization

Deletion claims must identify the layer actually settled.

## 17. Deletion status is plane/generation qualified

A single Boolean cannot safely describe active-store, derived, backup and recipient states simultaneously.

## 18. Completion should be explainable

Future deletion status should identify what was in scope, which planes settled, what remains and why, and what restore-time behavior is required.

---

# Cumulative ledger disposition after KA-G6

## Invariants

Invariant IDs remain **KA-I-001 through KA-I-049**.

No new invariant ID or status change is required.

KA-G6 supplies direct independent domain evidence for already-reinforced:

### KA-I-016

> Delete/forget completion is a multi-plane reconciliation result, not a single successful delete return or current-view removal.

Strong recurrence also supports:

- KA-I-001
- KA-I-004/005
- KA-I-011
- KA-I-014
- KA-I-019
- KA-I-023
- KA-I-027/028
- KA-I-034/035
- KA-I-036/037
- KA-I-043

No invariant becomes a final architecture rule yet.

## Failure patterns

Failure IDs remain **KA-F-001 through KA-F-049**.

No new failure ID/status change is made because KA-G6 supplied direct standards/regulatory/operational semantics rather than a new reproduced project incident.

---

# Twenty-six-question disposition after KA-G6

Questions 1–25 now have sufficient direct/project evidence for later requirements/synthesis without another broad framework revisit.

KA-G6 materially strengthens:

- **22 Privacy deletion/retention**

The only remaining bounded direct research gap is:

- **26 Scope of truth/generality — non-AI operational-domain validation**

KA-G7 is therefore the final planned direct gap-research task.

---

# Requirements carried forward from KA-G6

1. Delete/forget completion is scoped multi-plane reconciliation.
2. Soft delete and erasure remain distinct.
3. Retention and ordinary usability remain distinct.
4. Restriction/beyond-use prevents ordinary reasoning/action use.
5. Restore reapplies deletion/restriction newer than the restored snapshot.
6. Deletion intent survives independently enough to prevent resurrection.
7. Tombstones/control markers minimize retained content.
8. Source deletion propagates to descendants according to lineage/policy.
9. Derived aggregates may invalidate/rebuild without erased inputs.
10. Retention is purpose/scope specific.
11. Expiry and final reconciliation may occur at different times.
12. Recipient/export copies are separate reconciliation planes.
13. Local deletion does not imply universal external deletion.
14. Deletion requests bind explicit identity/domain/time/purpose scope.
15. Ambiguous identity prevents unsafe over-deletion and false completion.
16. Audit proof need not retain full erased content.
17. Logical deletion does not imply media sanitization.
18. Deletion status is plane/generation qualified.
19. Completion evidence distinguishes settled, pending, restricted-retained, exempt and unresolved planes.
20. Backup restore cannot silently reactivate erased/restricted knowledge.

---

# Nominated later hostile scenarios

Do not execute during KA-G6.

- canonical row deleted but embedding still retrieves content;
- summary retains erased personal fact;
- vector/full-text index survives source deletion;
- cache or replica resurrects deleted data;
- old backup restore resurrects post-backup deletion;
- tombstone preserves full erased content;
- global longest-retention rule applied to every data class;
- held/restricted data enters normal model context;
- soft deletion reported as permanent erasure;
- local delete reported as external-recipient completion;
- same-name ambiguity deletes wrong person's knowledge;
- ambiguous identity produces false “all deleted” result;
- aggregate rebuilt from stale deleted input;
- audit log preserves deleted sensitive payload;
- logical delete reported as media sanitization;
- expired data remains ordinarily usable during cleanup;
- restore ignores deletion ledger;
- anti-resurrection state itself lost on restore;
- restricted backup becomes searchable after recovery;
- connector re-ingests a deliberately forgotten source;
- recipient acknowledgement treated as verified erasure without evidence.

---

# Pre-build scope-locked roadmap

Remaining path before physical implementation:

1. **KA-G7 — Non-AI Operational-Domain Validation (Home Assistant / Matter-style)**
2. **Representative Retrieval Requirements** — approximately 40–60 questions
3. **Hostile / Adversarial Scenario Review**
4. **Conceptual Architecture Synthesis**
5. **Small Hand-Authored Cross-Domain Prototype / Validation**
6. **Only then: physical storage selection and implementation**

This sequence is a scope guard, not blanket authorization.

---

# Current task

**No task is currently assigned.**

KA-G6 is complete.

---

# Planned next candidate

**KA-G7 — Non-AI Operational-Domain Validation (Home Assistant / Matter-style)**

Suggested bounded focus:

- devices/entities versus observations/state;
- physical device identity versus logical endpoint/entity identity;
- location/area relationships;
- state freshness/staleness/unavailable/unknown semantics;
- event versus current state;
- replacement hardware and stable user-facing identity;
- shared-household ownership/authority;
- automation inputs versus action authority;
- capability/feature discovery and version drift;
- whether the knowledge primitives developed from AI/coding domains generalize cleanly to household/IoT operations.

Explicit exclusions:

- Home Assistant/Matter implementation;
- smart-home hardware selection;
- Vera automation implementation;
- final conceptual synthesis;
- storage selection.

Queue position alone is not authorization.

---

# Stop point

KA-G6 is complete and the campaign is stopped before KA-G7.

No operational-domain validation, retrieval-requirements construction, hostile review, conceptual synthesis, storage selection, or implementation was started inside KA-G6.
