# Knowledge Authorization and Actionability / Use-Purpose Gap Research

**Campaign:** Knowledge Architecture Evidence Campaign  
**Task:** KA-G4 — Knowledge Authorization + Actionability / Use-Purpose  
**Research date:** 2026-09-08  
**Starting ACL checkpoint:** `b141044032c9d3e9773b5f9d81078576799321bb`  
**Boundary:** research/requirements evidence only; no policy-engine selection, no authorization implementation, no privacy-erasure mechanics, no resource-storage design, no final conceptual schema, no database selection, and no ACL/Vera implementation

---

# Executive assessment

KA-G4 closes the remaining direct semantics gap around **who may use which knowledge, for what operation and purpose, under what context, and how that decision is separated from enforcement**.

The strongest conclusion is that ACL/Vera must not represent authorization as a generic property such as:

`principal X may access knowledge Y`

A consequential authorization decision needs to be scoped to at least:

- authenticated principal / requesting subject;
- target resource or knowledge object/domain;
- requested action/operation;
- purpose or use context where policy depends on it;
- relevant subject/resource/environment attributes and authorization relationships;
- current policy / authorization-model revision;
- transient request context where applicable;
- decision outcome and any mandatory obligations;
- freshness/expiry or other validity boundary when decisions can become stale.

The same underlying fact may therefore be:

- permitted for human display;
- prohibited from disclosure to another person;
- permitted for planning;
- prohibited as an automated-decision input;
- permitted to retrieve but not modify;
- permitted to summarize but not export;
- permitted to use only for a specific purpose;
- unavailable because the authorization decision is indeterminate or stale.

This task strengthens the campaign's existing separation:

> **Knowledge ≠ Authority ≠ Execution**

and adds an important refinement:

> **Readability ≠ usability-for-any-purpose.**

No policy language or engine is selected. NIST ABAC, XACML, ODRL, Zanzibar, and OpenFGA are used as evidence sources, not implementation commitments.

---

# Research boundary

## In scope

- subject/principal/resource/action/environment semantics;
- ABAC-style authorization requirements;
- ReBAC-style relationship-based authorization requirements;
- action-specific authorization;
- purpose/use constraints;
- read versus disclose/share versus transform/derive versus mutate/delete versus use-for-decision/automation;
- authorization decision versus enforcement separation;
- policy composition and explicit deny/indeterminate/not-applicable handling;
- mandatory obligations versus ignorable advice;
- authorization-model/policy revision identity and stale-decision concerns;
- transient request context;
- distinction between authorization relationships and canonical world relationships;
- interaction with existing knowledge/provenance invariants.

## Explicitly out of scope

- privacy erasure and retention execution mechanics;
- legal analysis of privacy statutes;
- final sensitivity taxonomy;
- credential-broker implementation;
- selecting XACML, OPA, Cedar, OpenFGA, Zanzibar-derived systems, or any other policy engine;
- resource/artifact identity research beyond what is required to identify a policy target;
- Home Assistant/Matter operational-domain modeling;
- final schema synthesis;
- database/storage selection;
- retrieval implementation;
- context-construction implementation;
- ACL/Vera implementation.

---

# Primary evidence

## NIST SP 800-162 — Attribute Based Access Control

Primary page:

https://csrc.nist.gov/pubs/sp/800/162/upd2/final

NIST defines ABAC as authorization of requested operations through evaluation of attributes associated with:

- the subject;
- the object/resource;
- requested operations;
- environment conditions where relevant;
- policy/rules/relationships describing allowed operations.

High-value lessons for ACL/Vera:

1. authorization is operation-specific rather than a permanent unrestricted right;
2. both human and non-person entities can be requesting subjects;
3. resource and environmental context can affect the same subject's authorization;
4. policy evaluates attributes/relationships rather than treating stored attributes as authority by themselves.

No conclusion is drawn that ACL/Vera should implement NIST ABAC literally.

## OASIS XACML 3.0

Primary specification:

https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-cos01-en.html

Used for:

- subject/resource/action/environment attribute categories;
- Policy Administration Point (PAP);
- Policy Information Point (PIP);
- Policy Decision Point (PDP);
- Policy Enforcement Point (PEP);
- Permit / Deny / Indeterminate / NotApplicable;
- policy/rule combining algorithms;
- deny-overrides / permit-overrides / first-applicable / only-one-applicable;
- deny-unless-permit top-level behavior;
- obligations versus advice;
- explicit distinction between decision and enforcement.

Key XACML lesson:

> policy evaluation is not enforcement, and an authorization decision may carry mandatory obligations that the enforcement side must honor.

This is architecture evidence only; no XML/XACML adoption decision is made.

## W3C ODRL 2.2

Primary specifications:

https://www.w3.org/TR/odrl-model/  
https://www.w3.org/TR/odrl-vocab/

Used for:

- Policy / Permission / Prohibition / Duty;
- Asset and Party;
- Action as an operation over an Asset;
- constraints refining permitted/prohibited usage;
- purpose as a first-class constraint operand;
- recipient, time, device, location, version and other usage constraints;
- differentiated actions including read, use, derive, transform, share, distribute, delete, write, execute, anonymize and secondaryUse;
- policy profiles extending action/constraint vocabularies.

ODRL is especially useful for the ACL/Vera question:

> permission to possess or read an asset does not imply permission to exercise every other action over that asset.

Again, no ODRL adoption decision is made.

## Google Zanzibar

Primary paper page:

https://research.google/pubs/zanzibar-googles-consistent-global-authorization-system/

Used for:

- relationship-based authorization at large scale;
- authorization policy expressed through relationships/ACL-style data and configuration;
- importance of causal ordering/external consistency when object contents and authorization relationships change;
- evidence that authorization state has its own consistency/freshness requirements.

Zanzibar is not used as a knowledge model. Its relationship tuples are authorization inputs, not automatically canonical assertions about the world.

## OpenFGA current documentation

Primary pages inspected:

https://openfga.dev/docs/learn/rebac  
https://openfga.dev/docs/modeling  
https://openfga.dev/docs/modeling/contextual-time-based-authorization  
https://openfga.dev/docs/interacting/contextual-tuples  
https://openfga.dev/docs/getting-started/tuples-api-best-practices

Current docs observed on 2026-09-08.

Used as current operational corroboration for:

- direct and implied authorization relationships;
- parent/child and userset traversal;
- contextual authorization inputs;
- ephemeral contextual tuples;
- time/location/network/organization context;
- token-claim staleness until expiration;
- recommendation to bind queries/commands to a specific authorization-model ID for stable behavior during model changes.

OpenFGA is not selected as ACL/Vera's policy engine.

---

# Highest-value findings

## 1. Authorization is a decision about an operation, not a property of knowledge

NIST ABAC and XACML both model authorization around a request to perform an operation on a resource/object.

For ACL/Vera, a knowledge item should not simply carry:

`allowed = true`

A meaningful authorization request instead has a shape closer to:

`principal + target + action + context/purpose + policy/model revision`

with policy consuming relevant trusted attributes/relationships.

Architecture consequence:

> authorization is evaluated per intended use, not inherited from possession or retrieval.

## 2. Read/retrieve is only one action class

ODRL provides direct standards evidence that different operations over the same asset are semantically distinct.

Examples include:

- read;
- use;
- derive;
- transform;
- share;
- distribute;
- export;
- execute;
- write;
- delete;
- anonymize;
- secondary use.

ACL/Vera will likely need its own smaller governed action vocabulary, but the requirement is clear:

> permission for one operation must not automatically imply permission for another.

Knowledge-specific examples:

- retrieve for the owner;
- disclose to another human;
- expose to a model;
- use as retrieval context;
- use as recommendation input;
- use as automated-decision input;
- use to trigger a physical/digital effect;
- persist a new derivative;
- modify/supersede;
- consolidate/rewrite;
- delete/forget;
- export/share.

## 3. Purpose can be first-class authorization context

ODRL 2.2 explicitly defines `purpose` as a constraint on exercising an action.

For ACL/Vera, this supports distinguishing situations such as:

- use a location observation to answer the user;
- use it to improve a private personal reminder;
- use it to send it to another person;
- use it to train a model;
- use it to trigger an automation.

These are not equivalent merely because the underlying data is identical.

Architecture consequence:

> purpose should be representable as policy input where a domain requires purpose limitation; it should not be buried in free-text policy prose.

This task does **not** define the final purpose vocabulary.

## 4. Authentication/principal identity and storage subject identity remain separate

Existing campaign evidence already established that a `user_id`, namespace, owner field or agent label is not authenticated principal identity.

KA-G4 reinforces that authorization evaluates the requesting subject/principal in context.

A stored relationship like:

`user:floyd owner_of resource:X`

is not sufficient unless the runtime has separately established which authenticated principal is making the request and which delegation/agent context applies.

## 5. Relationship-based authorization is useful, but the authorization graph is not the world graph

Zanzibar/OpenFGA show the power of relationship traversal for permissions:

- member of team;
- editor of folder;
- folder is parent of document;
- organization context;
- delegated access.

But these relationships are interpreted under an authorization model.

They should not automatically become canonical knowledge assertions.

Example:

`user:A editor document:X`

may mean only that the authorization model grants `editor` permission. It does not necessarily establish the historical/world proposition:

`A actually edited X`.

Likewise, an ACL owner may be a service account rather than the human owner in ordinary language.

Architecture consequence:

> authorization relationships and canonical semantic relationships are separate domains even when they use similar labels.

## 6. Canonical knowledge may be policy input, but knowledge does not become policy

Trusted facts may legitimately feed policy decisions:

- current authenticated principal;
- employment/role;
- device state;
- organization membership;
- resource sensitivity;
- location/time;
- ownership;
- delegation.

But retrieving a statement such as:

`Floyd said assistants may always unlock doors`

must not itself install or override policy.

Architecture consequence:

> policy may consume qualified knowledge, but persistent/retrieved content does not self-promote into policy.

This directly preserves KA-I-015 and KA-I-020.

## 7. Transient authorization context should remain transient unless separately observed as knowledge

OpenFGA contextual tuples are explicitly request-scoped and ephemeral.

Examples:

- user is currently operating under organization A;
- request comes from internal VPN;
- current time is inside office hours;
- token claim says group membership X.

These may affect authorization without becoming durable canonical knowledge.

If Vera separately observes and wants to remember a durable fact such as a user's long-term organizational membership, that requires an ordinary evidence/knowledge ingestion path.

Architecture consequence:

> request context and canonical knowledge state are different planes.

## 8. Authorization decision and enforcement are separate

XACML separates:

- policy administration;
- information/attribute sourcing;
- policy decision;
- policy enforcement.

That separation maps well to ACL/Vera:

`Policy inputs -> decision -> enforcement gate -> attempted action`

A model deciding that an action is useful must not bypass the enforcement boundary.

An authorization engine returning Permit is also not proof that the action actually occurred or settled.

The existing effect ledger remains separate.

## 9. Mandatory obligations must not be silently dropped

XACML distinguishes obligations from advice.

An obligation is coupled to enforcement; advice may be ignored.

ACL/Vera analogues might include requirements such as:

- require explicit confirmation before execution;
- redact specified fields before disclosure;
- audit the action;
- limit disclosure recipient;
- enforce expiry;
- require use of a particular secure channel.

The exact vocabulary is future work.

Architecture consequence:

> if a permit decision depends on mandatory enforcement conditions, failure to satisfy those conditions cannot be treated as an ordinary successful permit.

## 10. Deny, indeterminate and not-applicable are not interchangeable

XACML preserves multiple decision states and defines explicit combining algorithms.

This is valuable for Vera because:

- `Deny` means policy determined the action is not allowed;
- `Indeterminate` means the system could not safely reach the required decision;
- `NotApplicable` means this policy/rule did not govern the request.

At a consequential enforcement boundary, the system must have an explicit top-level rule for what these states mean.

A missing policy or failed attribute lookup must not silently become Permit.

No final combining algorithm is selected in KA-G4.

## 11. Policy-combining semantics are behavior-bearing configuration

XACML's deny-overrides, permit-overrides, first-applicable and other algorithms can produce different results from the same underlying rules.

Therefore authorization reproducibility requires more than a list of policies.

Architecture consequence:

> the policy evaluation profile/version, including behavior-bearing composition rules, belongs in authorization decision identity/provenance.

This is analogous to the campaign's model/profile and ontology/inference-profile requirements.

## 12. Authorization model revision matters

OpenFGA recommends specifying the authorization-model ID to maintain consistent behavior while a new model is being introduced.

Zanzibar emphasizes consistency when authorization state changes.

This reinforces a requirement that a consequential authorization decision be attributable to the policy/model revision actually evaluated.

A cached decision from policy V1 should not be presented as if it was freshly evaluated under policy V2.

## 13. Authorization relationship and attribute freshness matter

OpenFGA explicitly warns that token claims used as context may remain effective until token expiration even if underlying claims change.

Similar problems apply to:

- revoked group membership;
- expired employment role;
- changed ownership;
- changed sensitivity;
- changed device trust;
- changed household membership.

Architecture consequence:

> authorization inputs need freshness/validity semantics appropriate to their source; stale attributes must not silently masquerade as current authority.

KA-G4 does not choose TTLs or refresh mechanisms.

## 14. Policy decisions need provenance, but provenance is not authority

A durable decision/audit record should be able to identify, where warranted:

- principal/requestor;
- target;
- action;
- purpose/context;
- policy/model revision;
- relevant attribute/relationship revisions;
- outcome;
- obligations;
- decision time.

This is **authorization-decision provenance**.

It explains why a decision occurred.

It does not itself grant future authority.

Replaying an old Permit record is not equivalent to reauthorizing the new request.

## 15. Delegation must be bounded to the delegated operation/context

KA-G3 established that provenance delegation (`actedOnBehalfOf`) is not authorization.

KA-G4 strengthens the inverse:

> an authorization delegation must explicitly constrain the delegate's allowed actions/scope/context; general provenance that one agent acted for another cannot supply those constraints.

This is directly relevant to ACL workers and Vera subagents.

## 16. Permission to expose knowledge to a model is distinct from permission to execute based on it

A safe path may allow Vera's reasoning model to see a fact while still prohibiting any autonomous effect based on that fact.

Conversely, an automation may be allowed to consume a narrow machine-readable state without exposing unrelated sensitive context to a general model.

Architecture consequence:

> disclosure-to-model and use-for-effect are independent policy actions.

## 17. Actionability is not epistemic confidence

A claim can be highly credible but non-actionable because policy forbids its use.

A low-risk automation input may be actionable even though its epistemic confidence is lower, if policy and verification rules permit the bounded action.

Therefore these dimensions remain separate:

- truth/epistemic confidence;
- relevance;
- sensitivity;
- authorization;
- actionability;
- required verification/confirmation.

## 18. Actionability can be represented as a policy/use classification, not a truth status

A future ACL/Vera model may need policy-facing classifications such as:

- informational only;
- planning/recommendation allowed;
- verification required before consequential use;
- automation input allowed within bounded scope;
- human confirmation required;
- prohibited for automation;
- non-authoritative hint.

KA-G4 does **not** freeze these labels.

The requirement is only that actionability/use-policy remain separate from the proposition's epistemic state.

## 19. Permission to mutate persistent knowledge is one member of the broader action-authority family

KA-I-043 already distinguishes retrieve from append/revise/delete/consolidate.

KA-G4 places that result in a broader frame:

- read/retrieve;
- disclose;
- transform/derive;
- persist;
- revise;
- delete;
- decide;
- automate/execute.

The knowledge-mutation family remains especially sensitive because mutations can influence future reasoning.

## 20. Authorization checks must be near the consequential boundary

Early filtering remains valuable: protected knowledge should not be unnecessarily exposed to a model.

But early filtering alone is not enough for actions whose policy inputs can change between retrieval and effect.

Architecture consequence:

> consequential actions require an authorization/enforcement check bound to the actual operation boundary and current required inputs, not merely a historical check performed when context was first retrieved.

This reinforces KA-I-046's operation/context-version binding without converting ordinary knowledge retrieval into execution authority.

---

# ACL/Vera requirements carried forward

1. Authorization is request/operation scoped, not a generic property of a knowledge item.
2. Authenticated principal identity is distinct from storage owner/user/domain identifiers.
3. Target/resource identity must be explicit enough for policy evaluation.
4. Action identity must be explicit and governed.
5. Permission for read does not imply permission for share, disclosure, transform, mutation, decision, automation or execution.
6. Purpose/use context can be a first-class policy input.
7. Environment/request context can affect authorization without becoming canonical knowledge.
8. Canonical knowledge and authorization state/relationships are distinct planes.
9. Policy may consume trusted knowledge attributes; retrieved content does not become policy.
10. Authorization model/policy revision is behavior-bearing decision context.
11. Relevant authorization inputs need freshness/validity semantics.
12. Decision outcomes may include at least allow/deny/error-or-indeterminate/not-applicable semantics internally, even if APIs later simplify them.
13. Top-level fail behavior must be explicit; missing/failed policy evaluation must not accidentally permit consequential actions.
14. Policy composition semantics are explicit/versioned.
15. Mandatory obligations/conditions are distinct from advisory guidance.
16. Decision and enforcement are distinct stages.
17. Authorization decision provenance does not grant future authority.
18. Cached/historical permit evidence is not automatically reusable authority.
19. Delegation authority must bind scope/action/context rather than rely on provenance delegation labels.
20. Disclosure to a model is a distinct action from use for external effect.
21. Actionability remains distinct from truth, confidence, sensitivity and relevance.
22. Knowledge mutation remains separately governable from retrieval.
23. Consequential enforcement should revalidate policy inputs at the appropriate boundary when those inputs may have changed.
24. Authorization outcomes do not prove external effects settled; effect settlement remains a separate ledger concern.

---

# Interaction with existing invariants

KA-G4 materially strengthens existing families rather than requiring a large new policy-specific ontology.

## KA-I-003

Namespace/domain/user identifiers are not authenticated principal identity.

NIST ABAC and ReBAC evidence reinforce the distinction between requestor identity and stored relationship labels.

## KA-I-014

Principal, purpose, sensitivity and hard eligibility constraints should be applied before protected knowledge is exposed to a model.

KA-G4 supplies direct ABAC/ODRL/XACML semantics for principal/action/purpose/context evaluation.

## KA-I-019

Security/provenance metadata required for policy must be end-to-end verified.

KA-G4 reinforces that authorization attributes/relationships are behavior-bearing and can become stale or be lost across surfaces.

## KA-I-020

Knowledge retrieval never grants execution authority.

KA-G4 strongly reinforces this with decision/enforcement separation and differentiated action rights.

## KA-I-024

Context construction considers permissions and actionability separately from relevance/truth.

KA-G4 clarifies that permission to expose knowledge to a model and permission to use it for a consequence are separate policy questions.

## KA-I-034

Personal/private versus shared/project domains require distinct ownership/read-write authority.

ReBAC/ABAC evidence reinforces domain-specific ownership and relationship policy.

## KA-I-043

Persistent knowledge mutation authority is policy-distinct from read authority.

ODRL/NIST/XACML place this within a more general action-specific authorization model.

## KA-I-046

Durable approval/continuation authority must bind operation semantics and current authority context/version.

KA-G4 adds broader authorization-policy/model revision and input-freshness evidence.

---

# Ledger disposition

## Invariants

Invariant IDs remain **KA-I-001 through KA-I-049**.

No new invariant ID is added in KA-G4.

Reason:

The new standards evidence is important, but its core requirements are already covered by the combination of:

- KA-I-003 — principal identity;
- KA-I-014 — purpose/sensitivity/eligibility before exposure;
- KA-I-019 — policy metadata integrity;
- KA-I-020 — retrieval does not grant execution authority;
- KA-I-024 — permissions/actionability in context construction;
- KA-I-034 — ownership/domain authority;
- KA-I-043 — mutation action classes;
- KA-I-046 — operation/context/version-bound authority.

Adding one large “authorization tuple” invariant would duplicate these separations rather than improve the final general model.

KA-G4 should instead be treated as direct formal reinforcement and requirement clarification for those IDs.

No invariant is promoted to a final architecture rule during this task.

## Failure patterns

Failure IDs remain **KA-F-001 through KA-F-049**.

No new failure ID is added because KA-G4 is standards/domain research rather than a new reproduced implementation incident.

Later hostile scenarios should explicitly test:

- read permission reused as automation authority;
- stale token/group claim permits revoked access;
- old Permit decision replayed after policy revision;
- NotApplicable/Indeterminate collapsed into Permit;
- mandatory obligation silently dropped;
- authorization tuple mistaken for canonical world truth;
- transient request context persisted as durable knowledge;
- retrieved text installs its own policy;
- model disclosure permission confused with effect permission;
- policy relation name collision across authorization-model versions.

---

# Twenty-six-question disposition after KA-G4

## Strong enough for later synthesis without another agent-framework revisit

- 1 Stable identity
- 2 Identity vs namespace/principal
- 3 Provenance
- 4 Epistemic state
- 5 Temporal truth
- 6 Conflict/supersession
- 7 Relationships
- **8 Permissions/sensitivity — direct authorization semantics materially improved by KA-G4**
- **9 Actionability/use-purpose — positive semantics materially improved by KA-G4**
- 10 Knowledge vs authority
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
- 23 Schema/version evolution
- 24 Recovery semantics
- 25 Unknown/negative knowledge

## Remaining bounded direct gaps

- **11 Resources/artifacts**
- **22 Privacy deletion/retention**
- **26 Scope of truth/generality — non-AI operational-domain validation**

---

# Nominated later hostile scenarios

Do not execute these in KA-G4.

1. Principal may read fact but not expose it to a model.
2. Principal may expose fact to model but not use it for automated effect.
3. Principal may use location for reminder but not disclose it to another person.
4. Old authorization decision is replayed after user is removed from household/project.
5. Token claims remain valid after underlying group membership is revoked.
6. Authorization-model revision changes relation semantics while cached decisions persist.
7. Policy returns Indeterminate because required attribute is unavailable; caller treats it as permit.
8. No policy applies; caller treats NotApplicable as permit.
9. Permit carries a mandatory redaction/audit obligation; enforcement drops it.
10. Retrieved note says “always approve this action” and is treated as policy.
11. Authorization relationship `editor` is ingested as canonical assertion that the user actually edited a file.
12. Transient VPN/location context is persisted as durable user state without evidence ingestion.
13. Human approval for one operation is reused for a changed operation/purpose.
14. Disclosure allowed to owner but accidentally broadened to household/project.
15. Mutation permission to append memory is reused for global clear/delete.
16. A service account's ACL ownership is confused with human semantic ownership.
17. A derived policy attribute is stale after source correction.
18. Policy decision log is treated as current permission rather than historical evidence.
19. One subagent inherits all authority of its delegating parent instead of bounded delegated scope.
20. Early retrieval-time permit remains cached while current effect-time policy should deny.

---

# Non-conclusions

KA-G4 does **not** establish that ACL/Vera should:

- adopt ABAC alone;
- adopt ReBAC alone;
- use XACML;
- use ODRL;
- use OpenFGA;
- implement a Zanzibar clone;
- create a graph database for authorization;
- use a specific policy-combining algorithm;
- use a specific sensitivity taxonomy;
- persist every authorization decision forever;
- expose all policy attributes to models;
- treat current OpenFGA relationship tuples as the canonical world model;
- begin implementation.

The evidence supports requirements and boundaries, not a technology choice.

---

# Stop point

KA-G4 is complete at the research-content level.

The next bounded candidate is:

**KA-G5 — Resource / Artifact Identity and Lineage**

No resource/artifact research, privacy/erasure research, operational-domain validation, retrieval-requirements construction, hostile-scenario execution, final synthesis, storage selection or implementation belongs inside KA-G4.
