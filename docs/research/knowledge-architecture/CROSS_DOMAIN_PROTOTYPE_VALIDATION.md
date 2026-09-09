# Small Hand-Authored Cross-Domain Prototype / Validation

**Campaign:** Knowledge Architecture Evidence Campaign  
**Phase:** Small Hand-Authored Cross-Domain Prototype / Validation  
**Status:** technology-neutral conceptual validation; no production code, physical schema, or storage selection

---

# Purpose

This document falsification-tests the synthesized conceptual architecture using a deliberately small hand-authored cross-domain example model.

The prototype is not an implementation. It is a worked semantic dataset plus manual query/acceptance walkthrough intended to answer one question:

> Can the six synthesized primitive families represent ACL/Vera knowledge across people, research, software/resources, devices, history, conflict, authorization boundaries, effects, deletion, and profile evolution without introducing hidden special cases or collapsing distinctions the evidence campaign requires?

The six synthesized primitive families under test are:

1. **ENTITY**
2. **ASSERTION**
3. **OCCURRENCE**
4. **RESOURCE**
5. **EVIDENCE / PROVENANCE LINK**
6. **SEMANTIC PROFILE / VOCABULARY DEFINITION**

Systems deliberately outside the canonical knowledge core remain:

- **AUTHORITY / POLICY**
- **EFFECT / EXECUTION LEDGER**
- **DERIVED RETRIEVAL PROJECTIONS**
- **CONTEXT CONSTRUCTION**

This prototype does not choose PostgreSQL, Neo4j, RDF, a vector store, object store, graph engine, policy engine, or API design.

---

# Governing test rule

The model passes only if it can preserve the following separation throughout the worked examples:

> **Knowledge does not grant authority. Authority does not prove execution. Execution acknowledgement does not prove world settlement.**

A worked answer that silently merges identity, time, provenance, authority, execution, or deletion states counts as a failure even if the human-readable answer appears plausible.

---

# Prototype notation

The examples below use compact pseudo-records.

They are not a serialization proposal.

```text
E-*   ENTITY
A-*   ASSERTION occurrence
O-*   OCCURRENCE
R-*   RESOURCE
P-*   SEMANTIC PROFILE / VOCABULARY revision
PV-*  EVIDENCE / PROVENANCE LINK
AUTH-* external authority decision example
FX-*  external effect-ledger example
D-*   derived projection example
```

`recorded_at` represents system/transaction knowledge time.

`valid_from` / `valid_to` represent world-valid applicability time where known.

`basis` is epistemic basis, not a confidence score.

---

# Domain profiles

## P-CORE-1 — Core semantic profile

Defines generic semantics required across domains:

- `same_as_candidate`
- `alias_of`
- `supersedes`
- `contradicts`
- `located_in`
- `assigned_to`
- `works_for`
- `prefers`
- `supports`
- `derived_from`
- `observed_state`
- `current_state_projection`

No relation name grants authorization.

## P-PEOPLE-1 — People profile revision 1

Defines:

- person identity and alias evidence vocabulary;
- identity-resolution statuses: `unresolved`, `candidate`, `confirmed`, `split`, `replaced`;
- merge/split transitions require explicit OCCURRENCE and provenance.

## P-RESEARCH-1 — Research profile revision 1

Defines:

- source document;
- research finding;
- observation/extraction occurrence;
- claim/evidence relationship;
- finding verification states.

## P-SOFTWARE-1 — Software/resource profile revision 1

Defines:

- repository;
- branch locator;
- immutable commit/version;
- source file;
- issue/defect;
- exact-version derivation requirements.

## P-HOME-1 — Household/device profile revision 1

Defines:

- physical device;
- logical capability;
- room/area relationship;
- direct state observation;
- derived current state;
- `unknown`, `unavailable`, `stale`, and known-value semantics.

## P-HOME-2 — Household/device profile revision 2

Introduces a narrower interpretation of `present_in` for person-presence derivation: a person is considered `present_in` an area only when at least one eligible tracker is fresh within the profile-defined freshness window and no higher-priority contradictory source is active.

Historical records created under P-HOME-1 remain interpreted under P-HOME-1 unless explicitly re-derived.

---

# Entities

## People

```text
E-P1
kind: person
canonical_label: Robert Smith

E-P2
kind: person
canonical_label: John Smith

E-P3
kind: person
canonical_label: John Smith
```

E-P2 and E-P3 intentionally have the same display label and remain separate semantic entities.

## Projects / organizations / places

```text
E-ORG1
kind: organization
label: Acme Mining

E-PORTAL-A
kind: operational_area
label: Portal A

E-PORTAL-B
kind: operational_area
label: Portal B

E-PROJ1
kind: project
label: Project Atlas

E-ROOM-KITCHEN
kind: room
label: Kitchen
```

## Devices

```text
E-THERMO-OLD
kind: physical_device
label: Kitchen Thermostat (old hardware)

E-THERMO-NEW
kind: physical_device
label: Kitchen Thermostat (replacement hardware)

E-LOCK-BACK
kind: physical_device
label: Back Door Lock
```

The old and replacement thermostat are separate physical entities even though the user-facing role remains “Kitchen Thermostat.”

## Software / knowledge entities

```text
E-REPO1
kind: repository
label: autonomous-coding-lab

E-ISSUE-1
kind: software_defect
label: stale approval reuse bug
```

---

# Resources

## R-REPO-LOGICAL

```text
kind: logical_repository_resource
entity: E-REPO1
locator: github://floydtrey/autonomous-coding-lab
```

## R-BRANCH-MAIN

```text
kind: mutable_reference
resource: R-REPO-LOGICAL
locator: refs/heads/main
```

This is a mutable locator/reference, not immutable source identity.

## R-COMMIT-A

```text
kind: immutable_repository_snapshot
resource: R-REPO-LOGICAL
content_version: commit:aaa111
```

## R-COMMIT-B

```text
kind: immutable_repository_snapshot
resource: R-REPO-LOGICAL
content_version: commit:bbb222
```

At prototype time the mutable `main` locator initially resolves to R-COMMIT-A, then later resolves to R-COMMIT-B.

## R-RESEARCH-DOC

```text
kind: logical_document
label: Authorization Design Note
locator: file:///research/authorization-note.md
```

## R-RESEARCH-DOC-V1

```text
kind: immutable_observed_representation
logical_resource: R-RESEARCH-DOC
content_digest: sha256:v1-example
```

## R-PRIVATE-NOTE

```text
kind: logical_document
label: Private household note
sensitivity_class: private
```

## R-PRIVATE-NOTE-V1

```text
kind: immutable_observed_representation
logical_resource: R-PRIVATE-NOTE
content_digest: sha256:private-v1
```

---

# Occurrences

## O-STATEMENT-1 — user states a benchmark preference

```text
kind: user_statement
occurred_at: 2026-09-01T10:00:00-05:00
actor: E-P1
```

## O-IDENTITY-REVIEW-1 — alias evidence reviewed

```text
kind: identity_resolution_review
occurred_at: 2026-09-02T09:00:00-05:00
```

## O-IDENTITY-MERGE-1 — explicit identity confirmation

```text
kind: identity_transition
transition: confirm_alias_same_entity
occurred_at: 2026-09-02T09:10:00-05:00
subject_entity: E-P1
```

## O-DEVICE-REPLACE-1 — thermostat physically replaced

```text
kind: replacement_event
occurred_at: 2026-09-03T14:00:00-05:00
old_entity: E-THERMO-OLD
new_entity: E-THERMO-NEW
role_continuity: Kitchen Thermostat
```

## O-OBS-LOCK-1 — lock reports locked

```text
kind: sensor_observation
occurred_at: 2026-09-04T06:00:00-05:00
source_entity: E-LOCK-BACK
```

## O-OBS-LOCK-2 — lock becomes unavailable

```text
kind: integration_status_observation
occurred_at: 2026-09-04T06:40:00-05:00
source_entity: E-LOCK-BACK
```

## O-RESEARCH-1 — research task consumes exact version

```text
kind: research_activity
started_at: 2026-09-05T08:00:00-05:00
settled_at: 2026-09-05T08:20:00-05:00
```

## O-UPDATE-MAIN — mutable branch advances

```text
kind: mutable_reference_change
occurred_at: 2026-09-05T09:00:00-05:00
reference: R-BRANCH-MAIN
old_target: R-COMMIT-A
new_target: R-COMMIT-B
```

## O-PORTAL-CORRECTION — late assignment correction recorded

```text
kind: correction_event
world_fact_effective_at: 2026-03-10T00:00:00-05:00
recorded_at: 2026-03-12T15:00:00-05:00
```

## O-CMD-UNLOCK-1 — unlock command requested

```text
kind: command_attempt
occurred_at: 2026-09-06T07:00:00-05:00
target: E-LOCK-BACK
command: unlock
```

## O-OBS-UNLOCK-1 — later physical observation

```text
kind: sensor_observation
occurred_at: 2026-09-06T07:00:04-05:00
source_entity: E-LOCK-BACK
```

## O-DELETE-1 — private-note erasure requested

```text
kind: deletion_request
occurred_at: 2026-09-07T12:00:00-05:00
scope: R-PRIVATE-NOTE and descendants
```

## O-RESTORE-1 — old backup restored

```text
kind: restore_event
occurred_at: 2026-09-08T03:00:00-05:00
snapshot_time: 2026-09-06T23:00:00-05:00
```

---

# Assertions — identity and aliases

## A-ID-1 — “Bob at work” candidate alias

```text
subject: E-P1
predicate: alias
value: "Bob at work"
basis: imported_source_identity
status: candidate
recorded_at: 2026-09-01T12:00:00-05:00
profile: P-PEOPLE-1
```

## A-ID-2 — Robert Smith email identifier

```text
subject: E-P1
predicate: source_identifier
value: robert.smith@example.test
basis: imported_directory_record
recorded_at: 2026-09-01T12:01:00-05:00
profile: P-PEOPLE-1
```

## A-ID-3 — explicit confirmation of alias identity

```text
subject: E-P1
predicate: alias
value: "Bob at work"
basis: explicit_user_confirmation
status: confirmed
valid_from: 2026-09-02T09:10:00-05:00
recorded_at: 2026-09-02T09:10:00-05:00
supersedes: A-ID-1
profile: P-PEOPLE-1
```

A-ID-1 remains historical evidence; A-ID-3 supersedes its unresolved status rather than deleting it.

## A-ID-4 / A-ID-5 — same-name people remain separate

```text
A-ID-4
subject: E-P2
predicate: display_name
value: "John Smith"
basis: imported_directory_record

A-ID-5
subject: E-P3
predicate: display_name
value: "John Smith"
basis: imported_contact_record
```

There is no `same_as` assertion between E-P2 and E-P3.

---

# Assertions — preference and explicit statement

## A-PREF-1

```text
subject: E-P1
predicate: prefers
object: benchmark_context=32K
basis: explicit_user_statement
valid_from: 2026-09-01T10:00:00-05:00
recorded_at: 2026-09-01T10:00:02-05:00
profile: P-CORE-1
```

A preference is represented as ASSERTION, not a separate universal primitive.

---

# Assertions — temporal relationship and late correction

## A-PORTAL-1 — initially recorded assignment

```text
subject: E-P1
predicate: assigned_to
object: E-PORTAL-A
basis: imported_schedule
valid_from: 2026-03-10T00:00:00-05:00
valid_to: 2026-03-10T23:59:59-05:00
recorded_at: 2026-03-10T05:00:00-05:00
profile: P-CORE-1
```

## A-PORTAL-2 — late correction

```text
subject: E-P1
predicate: assigned_to
object: E-PORTAL-B
basis: verified_correction
valid_from: 2026-03-10T00:00:00-05:00
valid_to: 2026-03-10T23:59:59-05:00
recorded_at: 2026-03-12T15:00:00-05:00
supersedes: A-PORTAL-1
profile: P-CORE-1
```

Best current reconstruction for March 10 is Portal B.

Historical belief as of March 10 still shows Portal A because A-PORTAL-2 had not yet been recorded.

---

# Assertions — conflict preservation

## A-EMPLOY-1

```text
subject: E-P2
predicate: works_for
object: E-ORG1
basis: explicit_source_claim
recorded_at: 2026-09-01T08:00:00-05:00
verification: unverified
profile: P-CORE-1
```

## A-EMPLOY-2

```text
subject: E-P2
predicate: works_for
object: E-PROJ1
basis: explicit_source_claim
recorded_at: 2026-09-01T08:05:00-05:00
verification: unverified
profile: P-CORE-1
```

For prototype purposes the second source is intentionally semantically inconsistent with the first: Project Atlas is a project, not an employer organization under P-CORE-1.

The system retains both assertion occurrences and reports conflict/schema incompatibility rather than silently discarding one or coercing the project into an organization.

---

# Assertions — known-negative and completeness

## A-KEY-INVENTORY-COMPLETE

```text
subject: E-P1
predicate: inventory_scope_complete
object: household_spare_keys
basis: authoritative_inventory_snapshot
valid_from: 2026-09-05T00:00:00-05:00
valid_to: 2026-09-05T23:59:59-05:00
recorded_at: 2026-09-05T00:05:00-05:00
profile: P-CORE-1
```

## A-NO-GARAGE-SPARE

```text
subject: E-P1
predicate: has_spare_key_for_garage
value_state: known_no_value
basis: closed_world_inventory_evaluation
valid_from: 2026-09-05T00:00:00-05:00
valid_to: 2026-09-05T23:59:59-05:00
recorded_at: 2026-09-05T00:06:00-05:00
profile: P-CORE-1
```

A-NO-GARAGE-SPARE is valid only because A-KEY-INVENTORY-COMPLETE establishes completeness for the relevant scope and time.

For `owns_a_truck`, no completeness contract exists; absence of a matching assertion therefore remains `not-established` rather than known false.

---

# Assertions — device replacement and role continuity

## A-DEVICE-ROLE-OLD

```text
subject: E-THERMO-OLD
predicate: located_in
object: E-ROOM-KITCHEN
basis: configured
valid_to: 2026-09-03T13:59:59-05:00
recorded_at: 2026-08-01T10:00:00-05:00
profile: P-HOME-1
```

## A-DEVICE-ROLE-NEW

```text
subject: E-THERMO-NEW
predicate: located_in
object: E-ROOM-KITCHEN
basis: configured_after_replacement
valid_from: 2026-09-03T14:00:00-05:00
recorded_at: 2026-09-03T14:05:00-05:00
profile: P-HOME-1
```

The user-facing role is continuous while physical identity changes.

---

# Assertions — direct observation, stale/unavailable state, derived state

## A-LOCK-OBS-1

```text
subject: E-LOCK-BACK
predicate: observed_state
value: locked
basis: direct_observation
valid_from: 2026-09-04T06:00:00-05:00
recorded_at: 2026-09-04T06:00:01-05:00
observation_occurrence: O-OBS-LOCK-1
profile: P-HOME-1
```

## A-LOCK-UNAVAILABLE

```text
subject: E-LOCK-BACK
predicate: availability
value: unavailable
basis: direct_integration_status
valid_from: 2026-09-04T06:40:00-05:00
recorded_at: 2026-09-04T06:40:01-05:00
observation_occurrence: O-OBS-LOCK-2
profile: P-HOME-1
```

At 07:00, a “current lock state” projection must not claim `locked` as fresh current truth solely from A-LOCK-OBS-1. Correct result is `unavailable; last observed locked at 06:00`.

## D-LOCK-CURRENT-1

```text
kind: derived_current_state_projection
subject: E-LOCK-BACK
generation: projection-gen-17
source_assertions: [A-LOCK-OBS-1, A-LOCK-UNAVAILABLE]
result: unavailable
last_known_value: locked
last_known_value_time: 2026-09-04T06:00:00-05:00
profile: P-HOME-1
```

D-LOCK-CURRENT-1 is derived/rebuildable and not canonical world truth.

---

# Assertions — relationships and inference

## A-REL-1

```text
subject: E-P1
predicate: assigned_to
object: E-PROJ1
basis: explicit_project_assignment
recorded_at: 2026-09-05T09:00:00-05:00
profile: P-CORE-1
```

## A-REL-2

```text
subject: E-PROJ1
predicate: owned_by
object: E-ORG1
basis: project_registry
recorded_at: 2026-09-05T09:01:00-05:00
profile: P-CORE-1
```

Suppose P-CORE-1 permits a derived query relationship `participates_in_org_project(Person, Org)` through the chain `assigned_to(Project) + owned_by(Org)`.

## A-REL-DERIVED-1

```text
subject: E-P1
predicate: participates_in_org_project
object: E-ORG1
basis: inferred
source_assertions: [A-REL-1, A-REL-2]
profile: P-CORE-1
recorded_at: 2026-09-05T09:02:00-05:00
```

A-REL-DERIVED-1 is not presented as a direct source assertion; its explanation must expose A-REL-1 and A-REL-2.

---

# Research/resource lineage

## A-FINDING-1

```text
subject: E-ISSUE-1
predicate: affected_by
object: stale_approval_reuse
basis: derived_research_finding
recorded_at: 2026-09-05T08:20:00-05:00
profile: P-RESEARCH-1
```

The research activity used R-COMMIT-A, not the mutable branch name as final source identity.

### Provenance links

```text
PV-1
from: O-RESEARCH-1
relation: used
object: R-COMMIT-A

PV-2
from: A-FINDING-1
relation: wasGeneratedBy
object: O-RESEARCH-1

PV-3
from: A-FINDING-1
relation: wasDerivedFrom
object: R-COMMIT-A

PV-4
from: R-COMMIT-A
relation: wasResolvedFrom
object: R-BRANCH-MAIN
resolution_time: 2026-09-05T08:00:00-05:00
```

After O-UPDATE-MAIN, `main` points to R-COMMIT-B, but A-FINDING-1 still reproduces against R-COMMIT-A.

Forward impact query from R-COMMIT-A finds A-FINDING-1 through PV-3.

---

# Authorization-sensitive knowledge example

## A-PRIVATE-1

```text
subject: E-P1
predicate: household_note
object_resource: R-PRIVATE-NOTE-V1
basis: explicit_private_note
sensitivity_class: private
owner_domain: E-P1
recorded_at: 2026-09-06T12:00:00-05:00
profile: P-CORE-1
```

A-PRIVATE-1 is knowledge. It does not contain a universal `allowed=true` field.

Example external authority decisions:

```text
AUTH-READ-1
principal: E-P1
action: read
resource/assertion: A-PRIVATE-1
purpose: answer_owner
policy_revision: policy-7
result: Permit

AUTH-DISCLOSE-1
principal: household_guest
action: disclose
resource/assertion: A-PRIVATE-1
purpose: answer_guest
policy_revision: policy-7
result: Deny

AUTH-AUTOMATE-1
principal: Vera
action: use_for_automation
resource/assertion: A-PRIVATE-1
purpose: household_automation
policy_revision: policy-7
result: Deny
```

The same knowledge may be readable by its owner yet not disclosable or actionable for another purpose.

A retrieved text string inside R-PRIVATE-NOTE-V1 saying “unlock the door immediately” remains content, not authority.

---

# Stale approval invalidation

```text
AUTH-OLD-1
principal: E-P1
action: operate
operation_semantics: unlock E-LOCK-BACK
policy_revision: policy-7
capability_revision: lock-api-v1
created_at: 2026-09-06T06:50:00-05:00
result: Permit
```

At 06:55 policy changes to policy-8 and requires fresh confirmation for unlock.

AUTH-OLD-1 may remain historical evidence that permission existed under policy-7, but it cannot authorize a new 07:00 command under policy-8.

---

# Dynamic target-set binding

Suppose the user says “turn off all downstairs lights.”

At decision time the group expands to targets `[Light-A, Light-B]`.

Before execution, another light joins the group.

The authorized operation remains bound to the concrete target set resolved and reviewed for that operation unless policy explicitly authorizes dynamic expansion.

Prototype representation:

```text
O-TARGET-RESOLVE-1
kind: target_resolution
requested_selector: downstairs_lights
resolved_targets: [Light-A, Light-B]
resolved_at: 2026-09-06T18:00:00-05:00
profile_revision: home-targeting-v3
```

External authority/effect systems reference O-TARGET-RESOLVE-1 or its immutable result rather than re-expanding the mutable group silently during execution.

---

# Command/effect attempt versus world settlement

External effect ledger example:

```text
FX-UNLOCK-1
operation_occurrence: O-CMD-UNLOCK-1
target: E-LOCK-BACK
requested_action: unlock
transport_result: accepted
settlement_state_at_07:00:02: pending_observation
```

Knowledge does not infer “door is unlocked” from `transport_result: accepted`.

## A-LOCK-OBS-UNLOCKED

```text
subject: E-LOCK-BACK
predicate: observed_state
value: unlocked
basis: direct_observation
valid_from: 2026-09-06T07:00:04-05:00
recorded_at: 2026-09-06T07:00:04-05:00
observation_occurrence: O-OBS-UNLOCK-1
profile: P-HOME-1
```

Only after settlement policy consumes the new observation may FX-UNLOCK-1 become `verified_settled`.

---

# Retry / duplicate ambiguity

Assume the client times out after sending an external `start_vehicle` command and receives no acknowledgement.

Correct model requirement:

- retain stable operation occurrence identity;
- preserve `attempted / acknowledgement_unknown` rather than inventing failure;
- do not blindly retry a non-idempotent operation as a fresh occurrence without reconciliation;
- later observation may settle the original attempt.

This condition is representable with OCCURRENCE identity plus external effect-ledger state; no new knowledge primitive is required.

---

# Deletion / derivative reconciliation

## Source and derivatives before erasure

```text
R-PRIVATE-NOTE-V1
  -> D-PRIVATE-SUMMARY-1
  -> D-PRIVATE-EMBEDDING-1
  -> D-PRIVATE-SEARCH-ENTRY-1
```

Lineage:

```text
PV-DEL-1: D-PRIVATE-SUMMARY-1 wasDerivedFrom R-PRIVATE-NOTE-V1
PV-DEL-2: D-PRIVATE-EMBEDDING-1 wasDerivedFrom R-PRIVATE-NOTE-V1
PV-DEL-3: D-PRIVATE-SEARCH-ENTRY-1 wasDerivedFrom R-PRIVATE-NOTE-V1
```

O-DELETE-1 scopes R-PRIVATE-NOTE and descendants.

Example reconciliation state:

```text
canonical_resource: settled_erased
summary: settled_erased
embedding: settled_erased
search_index: settled_erased
backup_generation_2026-09-06: restricted_pending_expiry
external_recipient: not_applicable
```

“Delete complete” is not reported as globally settled while the backup plane remains only restricted/pending.

---

# Restore without resurrection

O-RESTORE-1 restores a snapshot created before O-DELETE-1.

The restored snapshot contains R-PRIVATE-NOTE-V1.

Activation gate applies deletion/restriction events newer than the backup snapshot before normal retrieval/context construction resumes.

Expected post-restore result:

```text
R-PRIVATE-NOTE-V1: fenced / not ordinarily retrievable
D-PRIVATE-SUMMARY-1: absent or invalidated
D-PRIVATE-EMBEDDING-1: absent or invalidated
D-PRIVATE-SEARCH-ENTRY-1: absent or invalidated
```

The old snapshot cannot silently make the erased note active knowledge again.

---

# Profile evolution without historical reinterpretation

Under P-HOME-1, person presence may have been derived from any fresh configured tracker.

P-HOME-2 changes the derivation rule to include tracker priority and contradiction handling.

Historical assertion:

```text
A-PRESENCE-OLD
subject: E-P1
predicate: present_in
object: E-ROOM-KITCHEN
basis: inferred
valid_from: 2026-08-30T08:00:00-05:00
valid_to: 2026-08-30T08:15:00-05:00
recorded_at: 2026-08-30T08:00:05-05:00
profile: P-HOME-1
```

When P-HOME-2 becomes active, A-PRESENCE-OLD is not silently reinterpreted as though the P-HOME-2 algorithm produced it.

If desired, a re-derivation occurrence creates a distinct new assertion with P-HOME-2 provenance.

---

# Manual validation against the 22 synthesis acceptance rules

## V-01 — Same-name people without forced merge

**Input:** E-P2 and E-P3 are both labeled John Smith.

**Expected:** separate identities unless evidence resolves them.

**Observed in prototype:** PASS. The model stores labels/source identity independently from semantic entity identity and has no forced `same_as` relation.

## V-02 — Auditable/reversible identity transition

**Input:** “Bob at work” moves from candidate alias A-ID-1 to confirmed alias A-ID-3 through O-IDENTITY-MERGE-1.

**Expected:** preserve pre-transition evidence and the explicit transition.

**Observed:** PASS. A-ID-1 remains historical; A-ID-3 supersedes its unresolved status; O-IDENTITY-MERGE-1 and provenance explain the change.

**Qualification:** physical reversal mechanics are an implementation concern, but the conceptual model retains sufficient transition identity/evidence for a later split/correction.

## V-03 — World truth at T versus historical belief at T

**Input:** March 10 portal assignment corrected March 12.

**Expected:** current reconstruction of March 10 can differ from what the system believed March 10.

**Observed:** PASS. A-PORTAL-2 provides current best world reconstruction; transaction-time query as of March 10 only sees A-PORTAL-1.

## V-04 — Late correction without rewriting knowledge history

**Expected:** correction can backdate valid time but not erase record time.

**Observed:** PASS. A-PORTAL-2 valid time covers March 10 but `recorded_at` remains March 12.

## V-05 — Conflict with source provenance preserved

**Input:** A-EMPLOY-1 and A-EMPLOY-2 conflict/type-disagree.

**Expected:** retain competing assertion occurrences and source semantics.

**Observed:** PASS. Neither assertion is destructively overwritten; incompatibility remains inspectable.

## V-06 — Unknown versus known-negative under explicit completeness

**Input:** garage spare key versus Bob owning a truck.

**Expected:** known no-value only when a completeness contract exists.

**Observed:** PASS. A-NO-GARAGE-SPARE depends on A-KEY-INVENTORY-COMPLETE; truck ownership remains `not-established`.

## V-07 — Direct observation versus inferred current state

**Input:** lock observed locked at 06:00 then unavailable at 06:40.

**Expected:** do not claim stale locked observation as fresh current state.

**Observed:** PASS. canonical observations remain separate; D-LOCK-CURRENT-1 returns unavailable with last-known locked metadata.

## V-08 — Direct relationship versus inferred path

**Input:** E-P1 assigned_to E-PROJ1; E-PROJ1 owned_by E-ORG1.

**Expected:** inferred `participates_in_org_project` is distinct from direct edges.

**Observed:** PASS. A-REL-DERIVED-1 retains source assertions and `basis: inferred`.

## V-09 — Relationship semantic identity versus assertion occurrence identity

**Expected:** relation meaning is defined by profile, while each assertion occurrence has its own provenance.

**Observed:** PASS. `assigned_to` semantics live in P-CORE-1; A-PORTAL-1, A-PORTAL-2 and A-REL-1 remain separate occurrences.

## V-10 — Exact consumed artifact version despite mutable locator

**Input:** research begins while `main` resolves to R-COMMIT-A; later `main` moves to B.

**Expected:** finding remains reproducible against A.

**Observed:** PASS. PV-1/PV-3 bind the research occurrence/finding to R-COMMIT-A; R-BRANCH-MAIN is merely resolution context.

## V-11 — Backward explanation and forward impact provenance

**Expected:** explain A-FINDING-1 from exact source; identify findings affected by R-COMMIT-A.

**Observed:** PASS. backward path A-FINDING-1 -> O-RESEARCH-1/R-COMMIT-A; forward path R-COMMIT-A -> A-FINDING-1.

## V-12 — Derived projection generation/staleness

**Expected:** current-state/search/summary projections identify source generation and can become stale.

**Observed:** PASS. D-LOCK-CURRENT-1 carries generation/source assertions; private derivatives retain source lineage.

## V-13 — Pre-model permission/sensitivity filtering

**Input:** A-PRIVATE-1 private note.

**Expected:** policy gate occurs before exposure to an unauthorized model/caller.

**Observed:** PASS at conceptual-interface level. A-PRIVATE-1 carries ownership/sensitivity attributes; AUTH examples demonstrate external policy decisions before context use.

**Qualification:** actual enforcement is intentionally deferred to implementation and must be tested later.

## V-14 — Read/disclose/automate/mutate authority separation

**Expected:** read permission does not imply disclosure or automation.

**Observed:** PASS. AUTH-READ-1 permits owner read while AUTH-DISCLOSE-1/AUTH-AUTOMATE-1 deny other uses.

## V-15 — Stale approval invalidation

**Input:** AUTH-OLD-1 created under policy-7, policy becomes policy-8.

**Expected:** historical Permit cannot authorize a new operation under changed authority context.

**Observed:** PASS. decision identity binds policy/capability revision.

## V-16 — Dynamic target-set binding

**Input:** mutable downstairs group changes after approval.

**Expected:** operation remains bound to concrete resolved target set unless dynamic expansion was explicitly authorized.

**Observed:** PASS. O-TARGET-RESOLVE-1 provides immutable occurrence/context for the operation boundary.

## V-17 — Command acknowledgement versus physical settlement

**Input:** unlock API accepted; sensor later reports unlocked.

**Expected:** acknowledgement alone does not prove door state.

**Observed:** PASS. FX-UNLOCK-1 remains pending until A-LOCK-OBS-UNLOCKED supplies settlement evidence.

## V-18 — Retry / duplicate ambiguity

**Input:** external command sent but acknowledgement lost.

**Expected:** preserve unknown settlement and stable operation identity; no blind duplicate claim.

**Observed:** PASS. OCCURRENCE + effect-ledger interface can represent attempted/acknowledgement-unknown separately from failure/success.

## V-19 — Deletion propagation through derivatives

**Input:** erase private note with summary/embedding/search descendants.

**Expected:** lineage identifies affected descendants and reconciliation tracks each plane.

**Observed:** PASS. PV-DEL-* links make descendants discoverable; deletion state is plane-qualified.

## V-20 — Restore without forgotten-data resurrection

**Input:** backup predates deletion; restore occurs later.

**Expected:** deletion/restriction state newer than snapshot is reapplied before activation.

**Observed:** PASS. O-RESTORE-1 is treated as reconciliation event; restored private data remains fenced.

## V-21 — Domain-profile evolution without historical reinterpretation

**Input:** P-HOME-1 presence semantics replaced by P-HOME-2.

**Expected:** old assertions retain old profile interpretation; re-derivation creates new evidence.

**Observed:** PASS. A-PRESENCE-OLD remains bound to P-HOME-1.

## V-22 — Cross-domain representation with same universal core

**Expected:** people, preferences, projects, research findings, repository versions, devices, observations, relationships, effects references, deletions and domain profiles all fit without introducing a seventh primitive.

**Observed:** PASS.

People -> ENTITY + ASSERTION.  
Preferences -> ASSERTION + statement OCCURRENCE.  
Projects/organizations/rooms -> ENTITY.  
Research source/artifact -> RESOURCE.  
Research finding -> ASSERTION + provenance + OCCURRENCE.  
Repository version -> RESOURCE with immutable version identity.  
Device -> ENTITY.  
Device reading -> OCCURRENCE + ASSERTION.  
Current device state -> derived projection.  
Relationship -> governed ASSERTION.  
Authority -> external Authority system consuming knowledge attributes.  
External action -> OCCURRENCE reference + external Effect Ledger.  
Deletion -> OCCURRENCE + lineage/reconciliation state.  
Domain semantics -> SEMANTIC PROFILE.

---

# Representative retrieval spot checks

The prototype does not manually rerun all 52 retrieval requirements because many are variations of the same preserved distinctions. The following spot checks cover every retrieval family.

## Identity

**Question:** “Are the two John Smiths the same person?”

**Answer supported:** Not established. E-P2 and E-P3 share a label but lack sufficient identity evidence for merge.

## Current operational state

**Question:** “Is the back door locked at 07:00 on September 4?”

**Answer supported:** Current state unavailable; last direct observed value was locked at 06:00. Do not report locked as fresh current truth.

## Historical world truth

**Question:** “Which portal was Robert assigned to on March 10?”

**Answer supported now:** Portal B, based on the March 12 verified correction whose valid time applies to March 10.

## Historical belief

**Question:** “What did the system believe on March 10?”

**Answer supported:** Portal A, because the correction had not yet been recorded.

## Negative knowledge

**Question:** “Was there a garage spare key on September 5?”

**Answer supported:** Known no-value within the authoritative complete inventory scope for that day.

**Question:** “Does Robert own a truck?”

**Answer supported:** Not established; no completeness contract supports a negative conclusion.

## Provenance

**Question:** “Which exact source version supported the stale-approval finding?”

**Answer supported:** R-COMMIT-A / commit aaa111, resolved from `main` at research time.

## Forward impact

**Question:** “Which findings depend on commit aaa111?”

**Answer supported:** A-FINDING-1 through PV-3.

## Relationship explanation

**Question:** “Why is Robert connected to Acme’s Project Atlas?”

**Answer supported:** direct assignment A-REL-1 plus project ownership A-REL-2; any derived organization-level relationship is labeled inferred.

## Authorization-sensitive retrieval

**Question:** “May Vera use the private note to automate the door?”

**Answer supported:** Knowledge can identify the note and its sensitivity/ownership, but the external Authority result shown is Deny for automation. Retrieval itself cannot grant permission.

## Effect settlement

**Question:** “Did the door unlock?”

**Answer supported:** API accepted at 07:00; physical state is verified unlocked only after the 07:00:04 direct observation.

## Deletion

**Question:** “Is the private note deleted?”

**Answer supported:** active canonical and derived planes are settled erased, while the cited backup generation is restricted/pending expiry. Therefore universal erasure is not yet reported as fully settled.

## Profile evolution

**Question:** “Why was presence inferred on August 30 under an older rule?”

**Answer supported:** A-PRESENCE-OLD is explicitly interpreted under P-HOME-1; P-HOME-2 does not retroactively rewrite it.

---

# Prototype failure search

The prototype was deliberately inspected for the following failure signals.

## Hidden seventh primitive

**Result:** none found.

No example required a universal `Memory`, `Fact`, `Preference`, `State`, `Relationship`, `Observation`, `Device`, `Project`, or `DocumentChunk` primitive separate from the six-family model.

Domain-specific categories remain kinds/profiles or assertion types.

## Assertion overload

Potential concern: ASSERTION carries many semantic dimensions.

**Disposition:** acceptable at conceptual level, but physical design must avoid a monolithic “everything nullable in one row” implementation. The synthesis says semantic role, not table. Storage evaluation must demonstrate that typed values, participants, time, epistemic state and profile identity can remain queryable and constrained without turning ASSERTION into an untyped blob.

This is an implementation-selection criterion, not a conceptual failure.

## Provenance edge overload

Potential concern: EVIDENCE / PROVENANCE LINK may become a generic relation bucket.

**Disposition:** acceptable only if provenance relation vocabulary is governed and direction/semantics are typed. Arbitrary string edges would fail the synthesis.

This becomes a physical-design acceptance criterion.

## Authority metadata duplication

Potential concern: assertions carry sensitivity/ownership hints while policy remains external.

**Disposition:** acceptable if those fields are descriptive policy inputs, not cached authority conclusions. Storage design must separate durable knowledge classification from current authorization decisions/policy versions.

## Occurrence versus effect duplication

Potential concern: tool/command OCCURRENCE appears in knowledge while effect lifecycle lives externally.

**Disposition:** acceptable if OCCURRENCE is the stable referent/activity anchor and effect settlement remains authoritative in the external effect ledger. The knowledge side may later ingest observations/assertions about settlement but cannot replace the effect ledger.

## Deletion control state location

Potential concern: deletion reconciliation references canonical, derived, backup and external planes.

**Disposition:** conceptual model can represent the deletion request OCCURRENCE and lineage, but the authoritative per-plane reconciliation state likely belongs in a deletion/control service or lifecycle ledger adjacent to—rather than flattened into—ordinary assertions. Physical design must preserve this separation.

## Historical belief reconstruction cost

Potential concern: transaction-time historical belief may be expensive.

**Disposition:** performance is a storage-selection concern. The conceptual model requires the capability; storage candidates will be judged against it rather than dropping the requirement.

---

# Prototype verdict

## Overall result

**PASS — conceptual architecture survives the hand-authored cross-domain falsification gate.**

All 22 synthesis acceptance rules can be represented and answered without introducing a seventh universal primitive family or violating the governing Knowledge / Authority / Execution separation.

No broad research reopening is justified by this prototype.

No conceptual primitive must be removed or added before physical design.

## Important qualification

This pass validates the **semantic architecture**, not any physical storage design.

Several implementation-selection risks are now explicit and must be tested when choosing technology:

1. ASSERTION must remain typed/queryable rather than become an unstructured universal row/blob.
2. provenance links require governed relation semantics, not arbitrary labels.
3. bitemporal/history queries must be practical enough for expected use.
4. immutable version identity and mutable locator resolution must both be first-class.
5. relationship traversal must preserve direct-versus-inferred provenance.
6. derived projections must carry generation/source identity and be rebuildable.
7. authorization filtering must occur before protected content reaches models.
8. effect settlement must remain outside knowledge truth claims.
9. deletion/restore reconciliation must prevent resurrection across derived/backup planes.
10. profile/schema evolution must preserve historical interpretation.
11. concurrency/revision preconditions must prevent stale mutation.
12. the system must support structured, relationship, full-text and semantic retrieval without making semantic similarity the source of truth.

These are now storage/implementation evaluation criteria rather than reasons for additional conceptual research.

---

# Gate decision

The campaign's required pre-storage gates have now been exercised:

- project evidence campaign;
- post-revisit coverage scan;
- promoted Agno revisit;
- seven bounded standards/domain gaps;
- 52 representative retrieval requirements;
- 44 hostile/adversarial scenarios;
- conceptual architecture synthesis;
- 22-rule hand-authored cross-domain prototype.

**Gate result: PASS to begin a separately authorized physical storage / implementation architecture selection phase.**

This document does not itself authorize or perform that next phase.

---

# Stop point

No PostgreSQL, SQLite, Neo4j, RDF store, vector database, object store, graph engine, embedding model, policy engine, schema, API, production code, ACL/Vera implementation, or autonomous-worker implementation was selected or created in this prototype.
