# Privacy Deletion, Retention and Erasure Reconciliation Gap Research

**Campaign:** Knowledge Architecture Evidence Campaign  
**Task:** KA-G6 — Privacy Deletion / Retention / Erasure Reconciliation  
**Research date:** 2026-09-08  
**Starting ACL checkpoint:** `5f4e0fcb67ec2f697a27da12821b912141c366fe`  
**Boundary:** research/requirements evidence only; no legal-regime selection, no retention-policy adoption, no storage/database choice, no implementation

---

# Executive assessment

KA-G6 closes the remaining direct privacy-lifecycle semantics gap before non-AI operational validation.

The strongest conclusion is that **delete/forget/erase cannot be modeled as one successful mutation against one canonical row**.

For ACL/Vera, deletion completion is a reconciliation result across every plane that can still make the targeted information usable or resurrectable:

- canonical knowledge;
- raw/source evidence where in scope;
- derived assertions;
- indexes;
- embeddings;
- summaries;
- caches;
- replicas;
- exports/recipients where the system remains responsible for propagation;
- backup/restore paths;
- model/context projections;
- task/workflow state that could reintroduce the information.

This directly and strongly reinforces existing **KA-I-016**:

> Delete/forget completion is a multi-plane reconciliation result, not a single successful delete return or current-view removal.

No new invariant ID is needed because KA-I-016 already captures the architectural core.

KA-G6 also establishes several important lifecycle distinctions:

1. **soft delete != erasure**;
2. **retention != ordinary usability**;
3. **restriction/beyond-use != active use**;
4. **backup presence != active knowledge** if the data is fenced from ordinary use and restore procedures preserve deletion;
5. **source deletion and derivative deletion are related but not identical operations**;
6. **deletion proof requires scope and reconciliation evidence**;
7. **retention must be purpose-specific rather than one global maximum**;
8. **restoring an older backup must not silently resurrect data that was already erased/restricted after that backup was taken**;
9. **auditability and erasure must be designed together rather than solved by keeping all historical personal data indefinitely**;
10. **media sanitization is a separate final-disposal concern from logical knowledge deletion**.

KA-G6 does **not** select GDPR, UK GDPR, CCPA/CPRA or any other privacy regime as Vera's governing legal model. Legal and jurisdiction-specific compliance remain deployment concerns. The standards/regulatory sources here are used to derive architecture requirements that are useful even outside any one jurisdiction.

---

# Research questions

KA-G6 was bounded around the following questions.

1. What does “deleted” mean when information exists in canonical, derived, replicated and backup planes?
2. What is the semantic difference between soft delete, restriction, beyond-use, logical deletion, hard deletion and media sanitization?
3. What must happen to embeddings, indexes, summaries and caches after source/canonical deletion?
4. How should backup retention interact with deletion requests?
5. How do we prevent deletion reversal after restore?
6. How should retention purpose and retention expiry be represented conceptually?
7. How do legal/operational holds affect ordinary usability without converting retained data into unrestricted active knowledge?
8. How much evidence is needed before the system can report deletion as complete?
9. What happens when deletion cannot be completed immediately in every plane?
10. What distinctions are needed between deletion, anonymization, disassociation and restriction?
11. How should deletion propagate to recipients/replicas where propagation obligations exist?
12. Which existing knowledge-architecture invariants already cover these requirements?

---

# Explicit exclusions

KA-G6 does **not**:

- provide legal advice;
- determine which privacy law applies to ACL/Vera deployments;
- define final retention periods;
- define a legal-hold policy;
- choose a final sensitivity taxonomy;
- choose a final anonymization standard;
- choose a database, object store, backup system or archive technology;
- choose a cryptographic-erasure implementation;
- define the final deletion API;
- define the final schema;
- implement deletion;
- implement retention jobs;
- implement backup/restore logic;
- implement privacy request workflows;
- perform Home Assistant/Matter operational validation;
- construct the final retrieval-requirements corpus;
- execute hostile scenarios;
- synthesize the final architecture.

---

# Primary evidence inspected

## EU GDPR — Articles 5, 17, 18 and 19

Primary text:

https://eur-lex.europa.eu/eli/reg/2016/679/2016-05-04

Used for:

- storage limitation;
- right to erasure;
- exceptions to erasure where processing remains necessary for specified reasons;
- restriction of processing as distinct from erasure;
- notification of rectification/erasure/restriction to recipients;
- copies/replications and reasonable technical measures;
- evidence that erasure is not purely a local-row operation.

Architecture lesson:

- deletion, restriction and retention are distinct lifecycle states;
- a system may need to preserve narrower-use retained material without treating it as ordinary active knowledge;
- deletion propagation can extend beyond one local representation.

Qualification:

GDPR is not adopted as ACL/Vera's universal legal regime. The task uses its mature lifecycle distinctions as architecture evidence.

---

## European Data Protection Board — storage limitation / right-to-erasure materials

Current materials inspected include:

- Data protection basics / storage limitation:
  https://www.edpb.europa.eu/sme/learn-the-basics/data-protection-basics_en

- 2026 coordinated enforcement report on right to erasure:
  https://www.edpb.europa.eu/documents/coordinated-enforcement-framework/coordinated-enforcement-action-implementation-of-the-0_en

- 2026 report PDF/search evidence for backup deletion and retention challenges.

Used for:

- purpose-specific retention periods;
- deletion/anonymization when data is no longer necessary;
- practical backup-erasure challenges;
- requirement for procedures that prevent deleted data from returning after restore;
- concerns with applying one longest retention period to all processing;
- need to track deletion requests across backup restoration;
- retention-policy accountability.

Highest-value current evidence:

The 2026 EDPB enforcement work specifically identifies backup restoration as a deletion hazard: organizations need procedures that prevent previously erased/restricted data from becoming active again after restore.

This is unusually direct support for Vera's future restore/reconciliation requirements.

---

## UK ICO — Right to erasure / backup systems

https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/individual-rights/right-to-erasure/

Used for:

- live-system erasure versus delayed backup overwrite;
- backup data may remain temporarily where immediate selective deletion is impractical;
- such backup data should be put “beyond use” during the retention interval;
- transparency about what remains in backups;
- no ordinary-purpose use of backup-held erased data.

Architecture lesson:

A backup copy can exist physically without remaining an active/usable knowledge source if policy and restore mechanics reliably fence it.

Qualification:

This is regulatory guidance, not a universal implementation prescription.

---

## NIST SP 800-88 Rev. 2 — Guidelines for Media Sanitization

Current final publication:

https://csrc.nist.gov/pubs/sp/800/88/r2/final

Publication date: September 2025.

Used for:

- media sanitization as making access to target data infeasible for a defined effort level;
- sanitization program design;
- clear/purge/cryptographic-erasure style distinctions at the media-disposal layer;
- logical sanitization in modern/cloud environments;
- validation of sanitization effectiveness;
- separation of logical lifecycle deletion from physical/media disposal.

Architecture lesson:

Deleting a knowledge record and sanitizing storage media are different layers.

Vera must not claim physical destruction merely because a logical record disappeared from the active store.

---

## NIST Privacy Framework / lifecycle terminology

https://www.nist.gov/privacy-framework

https://csrc.nist.gov/glossary/term/Data_Processing

Used for:

- complete data lifecycle including retention, transformation, use, disclosure and disposal;
- privacy risk as lifecycle-wide rather than storage-only;
- evidence that disposal is one data action among many, not synonymous with stopping one application view.

---

## Microsoft Azure / Entra backup soft-delete documentation

Current 2026 operational documentation inspected:

- Azure Backup security/soft delete:
  https://learn.microsoft.com/en-us/azure/backup/azure-backup-data-protection-best-practices

- Microsoft Entra soft deletion:
  https://learn.microsoft.com/en-us/entra/backup/soft-deletion

Used only as operational corroboration for:

- soft delete as deliberately recoverable state;
- configurable retention window;
- recoverability versus permanent deletion;
- backup integrity/recovery tension;
- need to distinguish deletion request state from physical copy elimination.

No Microsoft technology is selected.

---

# Highest-value KA-G6 findings

## 1. Delete/forget completion is a reconciliation result

A successful delete against the active/canonical store proves only that one mutation completed.

It does not prove that the targeted information can no longer be:

- retrieved from a derived index;
- reconstructed from a summary;
- surfaced from a cache;
- reintroduced from a replica;
- restored from backup;
- replayed from a workflow/checkpoint;
- exposed from an export/recipient copy;
- regenerated from an unexpired derivative.

Therefore deletion needs a scoped reconciliation model.

This strongly reinforces **KA-I-016**.

---

## 2. Soft delete is not erasure

Soft deletion intentionally retains enough state for restoration.

Useful lifecycle states can include conceptually:

- active;
- hidden/inactive;
- soft-deleted/recoverable;
- restricted/beyond-use;
- pending-erasure/reconciliation;
- erased from a specific plane;
- expired;
- retained under explicit hold/purpose;
- physically/media sanitized where applicable.

KA-G6 does not freeze these as final enum values.

The requirement is that recoverable deletion must not be reported as irreversible erasure.

---

## 3. Retained does not mean ordinarily usable

A bounded retention obligation or backup retention period can justify continued physical/logical possession without authorizing ordinary use.

Retained data may need a much narrower allowed-purpose set than active data.

For Vera, ordinary reasoning/context inclusion, automated actions, model training and disclosure should not automatically consume retained/restricted material.

This reinforces:

- KA-I-014 — eligibility before model exposure;
- KA-I-020 — knowledge never grants authority;
- KA-I-024 — context construction considers permissions/actionability;
- KA-I-043 — mutation/use actions are separately governable.

---

## 4. Backup presence and active knowledge are distinct

An immutable or append-oriented backup may still contain historical bytes after active erasure.

That does not have to mean the data remains active knowledge if:

- ordinary retrieval paths cannot access it;
- it is not used for new processing;
- retention is bounded;
- restore procedures know the deletion/restriction ledger;
- any restored data is re-erased/restricted before the restored system becomes active.

This turns backup restore into a **reconciliation event**, not merely a storage copy operation.

---

## 5. Restore can reverse deletion unless deletion intent survives independently

If deletion state exists only inside the backup being restored, then restoring an older backup can erase the evidence that a later deletion occurred.

A future implementation therefore needs a way to preserve deletion/restriction intent across restore boundaries.

Conceptually:

`backup snapshot time < deletion event time < restore time`

must not result in the deleted item becoming current again merely because the backup predates deletion.

KA-G6 does not choose the mechanism.

Possible implementation families later may include external tombstone journals, deletion ledgers, restore-time reconciliation streams or policy-controlled restore gates.

No mechanism is selected now.

---

## 6. Tombstones are control evidence, not retained personal content by default

Some persistent marker may be required to prevent resurrection or repeated ingestion.

But a tombstone should retain only the minimum identity/control information needed for its purpose.

A deletion marker that preserves the entire erased content defeats the purpose of erasure.

The future design must distinguish:

- content retention;
- minimal anti-resurrection marker;
- deletion request/decision evidence;
- audit evidence;
- legal/operational hold metadata.

---

## 7. Source deletion and derivative deletion require lineage-aware propagation

If source artifact/version A generated:

- chunk B;
- extracted assertion C;
- summary D;
- embedding E;
- search index entries F;

then a scoped deletion/forget request needs rules for which descendants:

- must be erased;
- must be invalidated;
- may remain as non-personal/anonymous aggregate;
- must be rebuilt without the source;
- must be marked stale;
- must become inaccessible.

Provenance from KA-G3 and resource identity from KA-G5 are therefore prerequisites for reliable erasure propagation.

---

## 8. Derived data may need re-computation, not only deletion

A group summary or aggregate may combine many sources.

Removing one source does not always mean deleting the whole aggregate permanently.

The correct outcome may be:

1. invalidate the aggregate;
2. rebuild it from remaining eligible inputs;
3. record the new generation/revision;
4. ensure the removed source no longer contributes.

This reinforces KA-I-011, KA-I-023, KA-I-027 and KA-I-035.

---

## 9. Retention should be purpose-specific

Applying the longest available retention period globally is semantically unsafe.

Different records may have different:

- purposes;
- owners/controllers;
- contractual/legal obligations;
- operational dependencies;
- sensitivity;
- retention start events;
- expiry conditions.

The knowledge architecture therefore needs enough policy metadata to support scoped retention decisions later.

KA-G6 does not define the final retention policy language.

---

## 10. Expiry is not necessarily immediate physical destruction

A retention expiry can trigger a lifecycle transition such as:

- remove from active use;
- queue derivative reconciliation;
- remove replicas/caches;
- wait for bounded backup expiration;
- schedule media sanitization where relevant.

Therefore “expired” and “fully reconciled erasure complete” can be distinct states.

---

## 11. Restriction and erasure are different

Restriction-of-processing semantics are useful when material must remain stored but ordinary processing is prohibited.

This distinction is valuable even outside GDPR deployments.

For Vera:

- restricted data should generally not enter normal context;
- it should not drive automations;
- it should not be disclosed unless the restricted purpose permits it;
- the restriction state itself should have provenance/policy identity.

---

## 12. Deletion requests need stable scope

A deletion request such as “forget Bob” is dangerously ambiguous.

Scope may need to specify:

- canonical entity or unresolved identity set;
- exact assertions;
- source artifacts;
- personal/private domain;
- shared/project domain;
- derived descendants;
- time range;
- specific processing purpose;
- retention exceptions/holds;
- external recipients/replicas;
- backup generations.

This ties deletion safety to identity resolution and ownership invariants.

---

## 13. Unknown deletion scope should fail safe

If the system cannot confidently determine whether two records belong to the same person/entity, it should not silently delete unrelated records nor silently declare completion.

Possible safe outcomes include:

- partial completion + unresolved scope;
- manual review;
- explicit ambiguity record;
- staged deletion pending identity resolution.

This reinforces KA-I-004/005 and KA-I-028.

---

## 14. Recipient/export propagation is a separate plane

When data has been exported or disclosed, local deletion does not automatically retract external copies.

The system may need to track:

- recipients;
- propagation duties;
- revocation/deletion requests sent;
- acknowledgements;
- impossible/unverified external deletion.

Deletion completion should therefore be scoped:

`local reconciliation complete`

is different from:

`all externally propagated copies verified removed`.

---

## 15. Auditability and erasure must coexist without retaining full erased content

The system may need evidence that:

- a deletion request existed;
- policy evaluated it;
- a deletion operation ran;
- particular planes reconciled;
- unresolved exceptions remain.

That audit evidence does not necessarily require retaining the deleted content itself.

The future design should prefer minimum necessary control metadata.

---

## 16. Media sanitization is a different layer

Logical deletion from a database, removal from indexes and backup expiration do not automatically prove physical sanitization.

NIST SP 800-88r2 treats sanitization as a media/confidentiality program with validation appropriate to the storage context.

Therefore Vera/ACL must use precise claims such as:

- removed from active knowledge store;
- removed from derived index;
- backup retained beyond use until date X;
- cryptographically erased;
- media sanitized/validated;

rather than one generic “deleted forever” status.

---

## 17. Deletion status must be monotonic only within a defined plane/generation

A record can be erased from current storage but still exist in an older backup generation.

Similarly, a derivative can be invalidated before it is physically removed.

Therefore deletion status needs plane/generation qualification.

A single global Boolean encourages false certainty.

---

## 18. Reconciliation completion should be evidence-bearing

For a deletion request, the future system should be able to explain:

- what was in scope;
- why it was erasable/restricted/retained;
- which planes were processed;
- which descendants were invalidated/rebuilt;
- what remains and why;
- whether backup copies are beyond use;
- what will happen on restore;
- whether any recipient propagation is unresolved;
- when the operation becomes fully settled.

This is an effect/knowledge lifecycle state, not only an API response.

---

# Cumulative ledger disposition after KA-G6

## Invariants

Invariant IDs remain **KA-I-001 through KA-I-049**.

No new invariant ID is created.

Reason:

KA-G6 provides direct, high-quality privacy/regulatory/operational evidence for an invariant already present since early project research:

### KA-I-016 — remains reinforced, now with direct domain evidence

> Delete/forget completion is a multi-plane reconciliation result, not a single successful delete return or current-view removal.

Prior support came from multiple agent/memory projects.

KA-G6 adds independent direct evidence from:

- GDPR Articles 17–19;
- EDPB 2026 erasure-enforcement findings;
- ICO backup-erasure guidance;
- NIST media-sanitization guidance;
- modern soft-delete/backup operational behavior.

Strong recurrence also applies to:

- KA-I-001 — raw/source vs derived separation;
- KA-I-004/005 — safe identity scope;
- KA-I-011 — derived state rebuildability;
- KA-I-014 — restricted data eligibility before model exposure;
- KA-I-019 — policy metadata must survive lifecycle operations;
- KA-I-023 — re-derivation/invalidation provenance;
- KA-I-027 — generation/coverage identity;
- KA-I-028 — settlement drives success reporting;
- KA-I-034 — ownership/domain scope;
- KA-I-035 — validated replacement/rebuild;
- KA-I-036/037 — source/derivative/resource identity;
- KA-I-043 — delete/forget is separately governable.

No invariant becomes a final architecture rule yet.

---

## Failure patterns

Failure IDs remain **KA-F-001 through KA-F-049**.

No new failure ID/status change is made.

Reason:

KA-G6 supplies standards/regulatory/operational requirements rather than a newly reproduced project defect.

Existing failure families already cover the relevant architecture risks, especially:

- current-view removal mistaken for full settlement;
- stale derived state;
- lost lineage;
- cross-scope destructive mutation;
- restore/replay of stale state.

Nominated hostile scenarios are listed below for the later adversarial-review phase.

---

# Twenty-six-question disposition after KA-G6

## Strong enough for later requirements/synthesis without another agent-framework revisit

- 1 Stable identity
- 2 Identity vs namespace/principal
- 3 Provenance
- 4 Epistemic state
- 5 Temporal truth
- 6 Conflict/supersession
- 7 Relationships
- 8 Permissions/sensitivity
- 9 Actionability/use-purpose
- 10 Knowledge vs authority
- 11 Resources/artifacts
- 12 Canonical vs derived
- 13 Structured retrieval
- 14 Relationship retrieval
- 15 Full-text retrieval
- 16 Semantic retrieval
- 17 Composite retrieval
- 18 Context construction
- 19 Memory poisoning/prompt injection
- 20 Concurrency
- 21 Derived-state integrity
- **22 Privacy deletion/retention — direct positive semantics materially improved by KA-G6**
- 23 Schema/version evolution
- 24 Recovery semantics
- 25 Unknown/negative knowledge

## Remaining bounded direct gap

- **26 Scope of truth/generality — non-AI operational-domain validation**

This means KA-G7 is the final planned direct gap-research task before requirements/hostile/synthesis/prototype gates.

---

# Requirements carried forward from KA-G6

1. Delete/forget completion is scoped multi-plane reconciliation.
2. Soft delete and irreversible erasure remain distinct.
3. Retention and ordinary usability remain distinct.
4. Restriction/beyond-use must prevent ordinary reasoning/action use.
5. Restore must reapply deletion/restriction events newer than the restored snapshot.
6. Deletion intent must survive independently enough to prevent resurrection.
7. Tombstones/control markers retain minimal data necessary for anti-resurrection/audit purposes.
8. Source deletion propagates through lineage to derivatives according to explicit policy.
9. Derived aggregates may require invalidation and rebuild rather than blind deletion.
10. Retention is purpose/scope specific.
11. Expiry and final reconciliation may occur at different times.
12. External recipients/exports are a separate reconciliation plane.
13. Local deletion cannot be reported as universal external deletion.
14. Deletion requests bind explicit identity/domain/time/purpose scope.
15. Ambiguous identity prevents unsafe global deletion and prevents false completion claims.
16. Audit proof should not require retaining erased content wholesale.
17. Logical deletion does not imply media sanitization.
18. Deletion status is qualified by plane/generation.
19. Completion evidence records settled, pending, exempt/retained and unresolved planes.
20. Backup-held erased data must not become ordinary active knowledge merely because a restore occurs.

---

# Nominated later hostile scenarios

Do not execute them during KA-G6.

- canonical row deleted but embedding still retrieves the text;
- summary retains deleted personal fact;
- vector index remains searchable after source erasure;
- cache resurrects deleted assertion;
- replica lag reintroduces deleted item;
- old backup restore resurrects post-backup deletion;
- tombstone itself stores the full deleted content;
- one longest retention policy applied to every data class;
- legal/operational hold leaves data available for normal model context;
- soft-deleted record reported as permanently erased;
- deletion succeeds locally while external recipient copy remains unresolved;
- ambiguous same-name identity causes deletion of the wrong person's knowledge;
- identity ambiguity causes false “all deleted” completion;
- source erased but derivative aggregate not rebuilt;
- derivative rebuilt but still consumes cached deleted input;
- deletion audit log contains full sensitive content;
- backup expires but derived cold index remains;
- logical delete presented as physical media sanitization;
- expired data remains usable while queued for cleanup;
- restore process ignores deletion ledger;
- deletion marker is restored from an older generation and loses later tombstones;
- restriction state leaks into normal assistant context;
- deleted source is re-ingested from an unchanged external connector because anti-resurrection state was lost;
- recipient deletion request sent but acknowledgement incorrectly treated as verified removal;
- cryptographic key destruction claimed without validation/evidence.

---

# Architecture consequences — requirements only

KA-G6 strengthens the conceptual pipeline:

`knowledge/resource lineage`

plus

`retention / deletion policy`

produces

`deletion scope + reconciliation plan`

which runs across

`canonical + derived + replica/cache + recipient + backup/restore planes`

and reports

`settled / pending / restricted-retained / exception / unresolved`

rather than a single Boolean.

This remains conceptual only.

No deletion service, retention scheduler, backup mechanism or physical schema is selected.

---

# What KA-G6 does not conclude

KA-G6 does **not** conclude that:

- every deletion request must erase every historical byte immediately;
- backups must always support selective in-place deletion;
- retaining data in backup is automatically compliant in every jurisdiction;
- “beyond use” is sufficient under every law or deployment;
- anonymization is always equivalent to deletion;
- one retention period can fit all information;
- immutable storage is incompatible with privacy if carefully architected;
- tombstones must be permanent;
- audit logs may retain unrestricted personal content forever;
- media sanitization is required for every logical delete;
- GDPR is the universal policy model for Vera.

Those are deployment/legal/implementation questions outside this bounded task.

---

# Pre-build roadmap after KA-G6

The remaining path before physical implementation is now:

1. **KA-G7 — Non-AI Operational-Domain Validation (Home Assistant / Matter-style)**
2. **Representative Retrieval Requirements** — approximately 40–60 questions
3. **Hostile / Adversarial Scenario Review**
4. **Conceptual Architecture Synthesis**
5. **Small Hand-Authored Cross-Domain Prototype / Validation**
6. **Only then: physical storage selection and implementation**

KA-G7 is the final planned direct research gap.

---

# Stop condition

KA-G6 is complete once:

- this report exists;
- campaign state records the result;
- no implementation or policy technology was selected;
- the branch is committed atomically;
- work stops before KA-G7.
