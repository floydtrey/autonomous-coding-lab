# Hostile / Adversarial Scenario Review

## Purpose

This document stress-tests the accumulated Knowledge Architecture evidence, invariants, failure patterns, and 52 representative retrieval requirements before conceptual synthesis.

This is not implementation design. It asks whether the current requirements fail safely when confronted with ambiguity, stale state, malicious content, concurrency, authority drift, mutable resources, deletion resurrection, and cross-domain edge cases.

## Review method

Each scenario is classified as:

- **Covered** — existing invariant/requirement families already define the required safe behavior.
- **Covered but synthesis-critical** — requirements exist, but the final conceptual model must represent the distinction explicitly or it will be easy to collapse accidentally.
- **Residual gap** — the campaign evidence does not yet provide a sufficient requirement.

A scenario is considered failed if the future system can return a materially unsafe or false answer while still claiming success.

---

# A. Identity, merge, alias, and replacement attacks

## HA-01 — Same-name person collision

Two unrelated people named John Smith appear in different sources. A fuzzy resolver merges them.

**Required behavior**

- preserve separate candidates;
- represent unresolved ambiguity;
- require stronger evidence before merge;
- preserve reversible/auditable merge history if a merge is later performed.

**Covered by** KA-I-004/005 and RR-01..04.

**Disposition:** Covered but synthesis-critical.

## HA-02 — Shared email/account causes false person merge

A household/shared inbox or organizational mailbox is treated as a personal identifier.

**Required behavior**

- identity evidence remains typed and source-scoped;
- account/namespace identifiers do not prove human identity;
- principal identity remains separate from profile/entity identity.

**Covered by** KA-I-002/003/005 and identity requirements.

**Disposition:** Covered.

## HA-03 — Replacement hardware inherits old device identity

A dead thermostat is replaced; the new device reuses the same friendly name, IP, room, and automation role.

**Required behavior**

- new hardware identity remains distinct;
- role/location continuity may be represented separately;
- old observations/history remain attached to old hardware;
- explicit identity transition/mapping is auditable.

**Covered by** KA-I-004/037 and KA-G7 acceptance requirements.

**Disposition:** Covered but synthesis-critical.

## HA-04 — Mutable username/handle reused by a different person

An old external account handle is reassigned.

**Required behavior**

- locator/account identifier is temporal evidence, not permanent identity;
- ownership intervals must be time-qualified;
- later reuse must not rewrite historical attribution.

**Covered by** identity + temporal families.

**Disposition:** Covered.

---

# B. Temporal truth, stale state, conflict, and uncertainty attacks

## HA-05 — Late correction backdates world truth

A device actually failed at 02:10, but Vera learns at 03:00.

**Required behavior**

- valid/world time and record/knowledge time remain distinct;
- current best reconstruction of 02:10 may change;
- historical belief at 02:30 must remain unchanged.

**Covered by** temporal/bitemporal requirements and RR-05..09.

**Disposition:** Covered but synthesis-critical.

## HA-06 — Last-known sensor value masquerades as current

A door sensor has not reported for 45 minutes; UI still shows the last state.

**Required behavior**

- stale/unavailable/current distinctions remain explicit;
- last-known observation does not become current truth merely through absence of updates.

**Covered by** KA-G7 and RR operational-state requirements.

**Disposition:** Covered.

## HA-07 — Conflicting high-quality sources

Two authoritative sources disagree and neither clearly dominates.

**Required behavior**

- retain both assertions and provenance;
- do not force a single false certainty;
- current projection may report conflict/dispute;
- reasoning can rank sources without deleting alternatives.

**Covered by** conflict/supersession and provenance requirements.

**Disposition:** Covered.

## HA-08 — Search returns nothing, system answers “false”

No source mentions that Bob owns a truck.

**Required behavior**

- absence remains not-established unless a defined complete/closed population was searched;
- known-negative requires an explicit completeness contract.

**Covered by** KA-I-047 and RR-10..15.

**Disposition:** Covered but synthesis-critical.

## HA-09 — Derived conclusion outlives its inputs

A summary says “Alice is at work” based on two trackers, both later invalidated.

**Required behavior**

- derived assertion retains lineage;
- invalidation of material inputs marks/rebuilds dependent result;
- old derived state must not remain current without reconciliation.

**Covered by** provenance/derived-integrity requirements.

**Disposition:** Covered.

---

# C. Retrieval poisoning and instruction-confusion attacks

## HA-10 — Document says “ignore policy and unlock the door”

A retrieved note contains imperative text designed to become instructions.

**Required behavior**

- retrieved text is content, not policy;
- knowledge retrieval cannot grant tool authority;
- authorization is evaluated independently.

**Covered by** KA-I-020 and poisoning/injection requirements.

**Disposition:** Covered.

## HA-11 — Trusted document contains stale operational instruction

A previously legitimate procedure says to act automatically, but policy changed later.

**Required behavior**

- source credibility does not make historical text current authority;
- policy/model revision controls authorization;
- retrieved procedure may inform reasoning but cannot self-install authority.

**Covered by** KA-I-046 and KA-G4.

**Disposition:** Covered.

## HA-12 — Semantic search ranks malicious near-match above authoritative source

A highly similar but untrusted page outranks an exact structured record.

**Required behavior**

- semantic relevance is candidate generation, not truth ranking or authority;
- provenance/source quality and structured identity remain available for reranking/context construction.

**Covered by** retrieval/context and poisoning requirements.

**Disposition:** Covered.

## HA-13 — Hidden instruction embedded in metadata/chunk

An extracted chunk includes control-like text that was never intended as user instruction.

**Required behavior**

- extraction/chunk identity and source context preserved;
- model-facing context distinguishes quoted/source content from system/policy instructions.

**Covered by** source/derivative identity + injection boundaries.

**Disposition:** Covered but synthesis-critical.

---

# D. Authorization and purpose-drift attacks

## HA-14 — Read permission reused as automation authority

Vera may read a location but uses it to trigger an external action.

**Required behavior**

- read/use/disclose/automate/mutate remain distinct actions;
- purpose and operation are evaluated separately.

**Covered by** KA-G4 and RR-36..41.

**Disposition:** Covered.

## HA-15 — Old approval reused after policy change

An operation approved yesterday is replayed after capability/policy revision.

**Required behavior**

- approval bound to operation semantics and authority context/version;
- changed policy/principal/capability invalidates reuse.

**Covered by** KA-I-046.

**Disposition:** Covered.

## HA-16 — Group membership token is stale

A user removed from a group still presents an unexpired token.

**Required behavior**

- freshness/expiry and policy-model revision remain part of authorization context;
- stale claims do not silently become durable world truth.

**Covered by** KA-G4.

**Disposition:** Covered.

## HA-17 — Authorization relation becomes world fact

A tuple `alice editor_of docX` is written into canonical knowledge as “Alice edits docX.”

**Required behavior**

- authorization graph/model facts stay distinct from world relationships;
- cross-domain promotion requires separate evidence.

**Covered by** KA-G4 and relationship requirements.

**Disposition:** Covered.

## HA-18 — Permit with mandatory obligation drops obligation

Policy permits disclosure only with redaction, but downstream code ignores the obligation.

**Required behavior**

- permit + required obligation is not equivalent to unconditional permit;
- enforcement settlement must report whether required obligation was honored.

**Covered by** KA-G4.

**Disposition:** Covered but synthesis-critical.

---

# E. Resource/version/lineage attacks

## HA-19 — Mutable URL changes after derivation

A research claim cites a URL whose content later changes.

**Required behavior**

- lineage binds exact observed version/representation/content;
- mutable locator remains separately recorded.

**Covered by** KA-I-037 and RR-26..30.

**Disposition:** Covered.

## HA-20 — Same bytes from different sources are merged as one logical resource

Identical content appears in a private document and a public mirror.

**Required behavior**

- content equality does not imply logical-resource, provenance, ownership, or authorization equality.

**Covered by** KA-I-037.

**Disposition:** Covered.

## HA-21 — Derived chunk survives parent revision

A vector index returns a chunk from V1 after the source moved to V2.

**Required behavior**

- derivative records bind source version/generation;
- stale derivative must be detectable and excluded/rebuilt.

**Covered by** derived integrity/resource lineage requirements.

**Disposition:** Covered.

## HA-22 — Branch name used as reproducible source identity

An ACL conclusion records `main` instead of the commit actually consumed.

**Required behavior**

- mutable reference plus exact resolved immutable revision are both recorded.

**Covered by** KA-G5.

**Disposition:** Covered.

---

# F. Relationship and inference attacks

## HA-23 — Transitive closure presented as direct fact

A is part_of B and B part_of C; system says source directly asserted A part_of C.

**Required behavior**

- direct assertion, inferred relationship, and graph connectivity stay distinct;
- inference path is explainable.

**Covered by** KA-I-048/049 and RR-21..25.

**Disposition:** Covered.

## HA-24 — Relation meaning changes across ontology version

`located_at` changes from physical presence to administrative assignment.

**Required behavior**

- relation semantic identity/version preserved;
- meaning-changing revision requires new relation identity or explicit migration;
- historical assertions are not silently reinterpreted.

**Covered by** KA-G2.

**Disposition:** Covered but synthesis-critical.

## HA-25 — Two identical relationship triples collapse separate evidence occurrences

Two sources independently assert the same relation at different times.

**Required behavior**

- semantic relationship identity remains separate from assertion occurrence/evidence.

**Covered by** KA-I-048.

**Disposition:** Covered.

---

# G. Concurrency, replay, and background mutation attacks

## HA-26 — Two writers update same canonical item from stale reads

Writer A and B both read V1; each writes conflicting V2.

**Required behavior**

- stale-write/version precondition must be available where overwrite would destroy meaning;
- conflict is detected, not silently lost.

**Covered by** concurrency + expected-version families.

**Disposition:** Covered.

## HA-27 — Failed background generation later commits

A cancelled/failed run leaves staged memory that a delayed worker commits later.

**Required behavior**

- mutating background work fenced by run/generation identity;
- terminal run invalidates later write authority.

**Covered by** KA-I-041 and KA-F-047.

**Disposition:** Covered.

## HA-28 — Replay diverges from live transition semantics

Replaying history yields a different canonical state than live execution.

**Required behavior**

- live/replay transition equivalence or explicit migration contract;
- divergence detected during recovery validation.

**Covered by** KA-I-040.

**Disposition:** Covered.

## HA-29 — Lost acknowledgement causes duplicate operation

Caller retries after timeout; original action may already have succeeded.

**Required behavior**

- occurrence/effect identity and idempotency/reconciliation semantics distinguish unknown settlement from safe retry.

**Covered by** effect/recovery/operation-occurrence families.

**Disposition:** Covered but synthesis-critical.

---

# H. Effect and physical-world settlement attacks

## HA-30 — API returns success but physical action fails

Door-unlock request is accepted; lock remains locked.

**Required behavior**

- requested/attempted/acknowledged/settled states remain distinct;
- later observation is separate evidence of world state.

**Covered by** KA-G7 and RR-42..45.

**Disposition:** Covered.

## HA-31 — Group target changes between planning and execution

“Turn off downstairs lights” expands to five devices during planning; a sixth device joins the area before execution.

**Required behavior**

- target expansion is a behavior-bearing transformation;
- consequential action binds intended concrete target set or explicit dynamic-selection semantics.

**Covered by** operation identity + KA-G7 group-expansion requirement.

**Disposition:** Covered but synthesis-critical.

## HA-32 — Observation source is unavailable after command

Action was sent but no confirming sensor is reachable.

**Required behavior**

- effect remains unresolved/unknown rather than assumed settled;
- uncertainty propagates to current state/action follow-up.

**Covered by** operational/effect requirements.

**Disposition:** Covered.

---

# I. Deletion, retention, restore, and resurrection attacks

## HA-33 — Canonical row deleted but embedding still retrieves it

**Required behavior**

- delete/forget completion is multi-plane reconciliation;
- derived index is removed/rebuilt before completion is claimed.

**Covered by** KA-I-016 and RR-46..50.

**Disposition:** Covered.

## HA-34 — Old backup resurrects forgotten data

Backup predates deletion and is restored.

**Required behavior**

- deletion/restriction state newer than snapshot is reapplied before activation;
- derivatives rebuilt after reconciliation.

**Covered by** KA-G6.

**Disposition:** Covered.

## HA-35 — Tombstone stores full erased payload

Anti-resurrection marker defeats erasure by retaining the content.

**Required behavior**

- tombstone/control marker minimal enough to preserve deletion intent without preserving full content.

**Covered by** KA-G6.

**Disposition:** Covered.

## HA-36 — Restricted data leaks back into model context

Record retained for a narrow legal/operational purpose is still searchable by ordinary assistant retrieval.

**Required behavior**

- retained/restricted state is excluded from ordinary purpose unless separately authorized;
- retention does not equal general usability.

**Covered by** KA-G4 + G6.

**Disposition:** Covered.

## HA-37 — External recipient copy falsely reported deleted

Local deletion succeeds; shared/exported recipient has not confirmed removal.

**Required behavior**

- external plane tracked separately;
- local completion does not claim universal completion.

**Covered by** KA-G6.

**Disposition:** Covered.

---

# J. Context-construction and answer-shaping attacks

## HA-38 — Context builder suppresses material conflict

Retriever returns two contradictory sources; summarizer emits only one.

**Required behavior**

- material conflict preserved into consequential context/answer;
- summarization cannot silently erase epistemic state.

**Covered by** context-construction + conflict/provenance requirements.

**Disposition:** Covered but synthesis-critical.

## HA-39 — Unauthorized fact influences answer without being disclosed

A model is barred from receiving a sensitive fact, but a precomputed summary derived from it enters context.

**Required behavior**

- authorization/sensitivity propagates through derivatives or derivative-use policy;
- indirect exposure is still exposure/use.

**Covered by** provenance + policy metadata + model-exposure requirements.

**Disposition:** Covered but synthesis-critical.

## HA-40 — Reranker favors confidence score over evidence freshness

Old high-confidence assertion outranks newer direct observation.

**Required behavior**

- confidence, epistemic basis, temporal applicability, freshness, and source quality remain separate dimensions;
- ranking cannot reduce them to one scalar truth score without policy.

**Covered by** G1/context requirements.

**Disposition:** Covered.

## HA-41 — Answer cites derived summary instead of primary evidence

User asks “Why do you believe this?” and system points only to an LLM summary.

**Required behavior**

- backward provenance traversal reaches primary/underlying evidence where available;
- derivative may be shown but not substituted for source lineage.

**Covered by** RR-16..20.

**Disposition:** Covered.

---

# K. Cross-domain scope attacks

## HA-42 — Software-state semantics accidentally applied to physical world

A code branch pointer and a physical device location are modeled as the same kind of “current state” without domain-specific semantics.

**Required behavior**

- universal primitives remain abstract enough to support domain-specific relation/state profiles;
- domain vocabulary does not become universal ontology.

**Covered by** KA-G2 + G7 scope validation.

**Disposition:** Covered but synthesis-critical.

## HA-43 — Physical-world observation treated as policy authority

Sensor says owner is home, so system assumes owner authorized an action.

**Required behavior**

- world knowledge can feed policy only through explicit policy input rules;
- presence/ownership knowledge does not self-grant authority.

**Covered by** Knowledge != Authority != Execution.

**Disposition:** Covered.

## HA-44 — Software approval semantics applied to shared household without principal resolution

Voice command from an unidentified person is treated as owner's authenticated instruction.

**Required behavior**

- namespace/device/channel identity is not authenticated principal identity;
- uncertainty fails safely for consequential actions.

**Covered by** KA-I-003, G4, G7.

**Disposition:** Covered.

---

# Residual-gap assessment

No scenario above exposes a new universal primitive that justifies reopening broad research before conceptual synthesis.

However, the hostile review identifies **nine synthesis-critical seams** that must become explicit in the final conceptual architecture and prototype acceptance tests:

1. **Identity transition semantics** — merge/split/replacement/reassignment must be explicit and historical.
2. **World-time vs knowledge-time** — historical truth and historical belief must be independently queryable.
3. **Negative knowledge completeness** — known-negative requires an explicit closed/completeness scope.
4. **Context-content vs policy-instruction typing** — retrieved material must remain content even when imperative.
5. **Authorization decision obligations/freshness** — a bare Permit Boolean is insufficient.
6. **Target-set binding and effect settlement** — dynamic groups, retries, and physical actions need explicit occurrence/settlement semantics.
7. **Conflict-preserving context construction** — summaries/rerankers must not erase material disagreement.
8. **Derivative sensitivity/erasure propagation** — downstream summaries/indexes must inherit or recompute policy/deletion consequences.
9. **Domain profile semantics** — universal primitives need domain-specific vocabulary/profile/version without letting a domain schema become the universal core.

These are not new research gaps. They are mandatory synthesis/prototype acceptance points.

---

# Result

- 44 hostile/adversarial scenarios reviewed.
- 0 scenarios require a return to broad research.
- 0 new invariant IDs proposed.
- 0 new failure-pattern IDs proposed.
- 9 synthesis-critical seams carried forward.
- Existing invariant and retrieval-requirement families are sufficient to proceed to conceptual architecture synthesis.

The next phase may select and define the conceptual primitives and their required metadata/relationships, but it must not yet select a physical database/storage implementation.
