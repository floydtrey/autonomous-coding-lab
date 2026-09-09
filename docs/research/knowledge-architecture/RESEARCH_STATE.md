# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** project revisits, coverage scan, promoted Agno revisit, and all seven bounded standards/domain gap tasks complete; stopped before representative retrieval-requirements construction  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

---

# Scope lock

This campaign remains **research/requirements discovery and validation only**.

The user explicitly requested scope-drift protection before KA-G3. That remains controlling.

Do **not**:

- restart broad agent-framework research;
- reopen completed project/domain revisits without a concrete evidence gap;
- select a final conceptual schema yet;
- select PostgreSQL, Neo4j, RDF, graph databases, vector stores, object stores, content-addressable stores, policy engines, Home Assistant/Matter implementation stacks, or other implementation technologies;
- implement a knowledge/resource store;
- implement authorization, deletion, retention, retrieval or context-construction services;
- create embeddings;
- migrate historical catalogs;
- benchmark models;
- implement ACL or Vera;
- run autonomous workers;
- skip retrieval-question, hostile-scenario, synthesis, and small-prototype gates;
- treat Home Assistant or Matter concepts as universal core primitives merely because they validated the model.

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
19. **KA-G7 — Non-AI Operational-Domain Validation (Home Assistant / Matter-style)** — complete

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
- `gaps/non-ai-operational-domain-validation.md`

Cumulative ledgers:

- `invariants.md`
- `failure-patterns.md`

Detailed evidence remains in dedicated reports. This file is the compact current checkpoint.

---

# KA-G7 verification and boundary

User authorization:

- after KA-G6, user explicitly instructed `continue`;
- the documented next candidate was KA-G7;
- this authorized KA-G7 only.

Starting branch/head:

`054b74dabdbaa3b6dbe41a50accbef20a3b21dc9`

Starting commit message:

`research: complete privacy deletion retention gap`

KA-G7 was bounded to non-AI operational validation using current Home Assistant/Matter-style evidence:

- physical device versus platform/device-registry identity;
- device versus logical entity/endpoint/capability identity;
- display/locator identity versus stable identity;
- observations/state versus entity identity;
- current state versus history;
- direct observation versus derived state;
- unknown/unavailable/stale distinctions;
- mutable room/area relationships;
- people versus source trackers;
- capability discovery/profile version drift;
- command/effect versus observed settlement;
- multi-admin/fabric/household authority;
- replacement/recommissioning hazards;
- generality of accumulated primitives.

Explicitly excluded:

- Home Assistant implementation;
- Matter implementation;
- Vera smart-home automation implementation;
- hardware selection;
- final device ontology;
- retrieval-requirements construction;
- hostile-scenario execution;
- conceptual synthesis;
- storage selection;
- implementation.

---

# KA-G7 primary evidence

## Home Assistant

Current documentation inspected on 2026-09-08 included:

- Device registry: `https://developers.home-assistant.io/docs/device_registry_index/`
- 2026.8 device-registry ownership/splitting change: `https://developers.home-assistant.io/blog/2026/07/21/device-registry-single-config-entry/`
- Entity registry: `https://developers.home-assistant.io/docs/entity_registry_index/`
- Devices/services architecture: `https://developers.home-assistant.io/docs/architecture/devices-and-services/`
- Unknown/unavailable guidance: `https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/entity-unavailable/`
- State objects: `https://www.home-assistant.io/docs/configuration/state_object`
- Device tracker: `https://www.home-assistant.io/integrations/device_tracker/`
- Person: `https://www.home-assistant.io/integrations/person/`
- Areas: `https://www.home-assistant.io/docs/organizing/areas/`

Important current observations:

- a physical device supported by several config entries can have one device-registry entry per config entry rather than one universal merged platform object;
- one device exposes multiple entities/capabilities;
- stable entity unique IDs are distinct from editable names/entity presentation;
- IP/name/hostname/URL are unsuitable intrinsic entity IDs;
- `unknown` and `unavailable` are distinct operational states;
- stale last-known state should not masquerade as fresh current state;
- Person presence is a derived result from multiple trackers with source-selection rules;
- Areas are mutable logical groupings/relationships.

## Matter

Current specification catalog inspected:

`https://csa-iot.org/developer-resource/specifications-download-request/`

Observed on 2026-09-08:

- Matter 1.6 is the newest listed family;
- earlier version families remain separately published.

Additional evidence:

- Matter 1.4.2 architecture/security overview: `https://csa-iot.org/newsroom/matter-1-4-2-enhancing-security-and-scalability-for-smart-homes/`
- Matter device-data/fabric primers from Google Home Developers.

Important observations:

- node, endpoint, cluster/capability and fabric are separate scopes;
- multiple fabrics/admins can coexist for one node;
- operational credentials/authority are fabric-specific while device data model can be shared;
- endpoint numbers were not always stable enough across admins/recommissioning, motivating Endpoint Unique IDs in Matter 1.4.2;
- capability changes can occur after commissioning and require re-evaluation;
- access control distinguishes subject/fabric/endpoint/cluster and privilege such as View/Operate/Manage/Administer;
- action attribution is distinct from authorization-entry contents.

No Home Assistant or Matter implementation technology was selected.

---

# Highest-value KA-G7 findings

1. **Physical entity identity and platform-registry identity are distinct.** One physical device can have several platform representations.
2. **Device and capability/entity/endpoint identity are distinct.** One thing may expose many behavior-bearing capabilities.
3. **Names, IPs, URLs and room assignments are not intrinsic identity.**
4. **Hardware replacement requires explicit identity transition.** Reusing the old friendly name/role must not rewrite history.
5. **Area/location is a mutable relationship.** Moving a device does not create a new device.
6. **Entity identity and temporal state observation are distinct.**
7. **Unknown, unavailable, stale and known false/off are distinct.**
8. **Last-known state does not silently become current truth.**
9. **Person presence is a derived projection.** Multiple trackers can support one person state under explicit selection rules.
10. **Person != tracker.** Sensor/source identity remains separate from semantic person identity.
11. **Capability schema != current availability.** A supported capability may be disabled/unavailable or change with profile/version.
12. **Capability/profile revision is behavior-bearing.** Firmware/reconfiguration can change operational semantics.
13. **Endpoint address != stable endpoint semantic identity.** Matter 1.4.2 Endpoint Unique IDs directly demonstrate this.
14. **Node/endpoint/cluster/fabric/principal scopes must not collapse into one `device_id`.**
15. **Authorization relationships are not automatically canonical world relationships.** Multi-admin/fabric authority does not itself prove human ownership.
16. **View/read != Operate/Manage/Administer.** Non-AI device control independently validates operation-specific authority.
17. **Command attempt != observed world result.** Sending `unlock` or `turn_on` is not the same fact as the later lock/light state.
18. **API acknowledgement != physical settlement.** Effect verification remains separate.
19. **Disabled/hidden != deleted.** Operational lifecycle/status must not be conflated with erasure.
20. **Area/group target expansion is a transformation.** The concrete target set can change over time.
21. **Direct observation != derived operational conclusion.** Derived states need explainable source lineage.
22. **No smart-home-specific universal primitive is required.** Existing candidate concepts generalize adequately.

---

# Cumulative ledger disposition after KA-G7

## Invariants

Invariant IDs remain **KA-I-001 through KA-I-049**.

No new invariant ID or status change is required.

KA-G7 independently validates many already-reinforced families outside AI/software-agent systems, including:

- KA-I-002
- KA-I-005
- KA-I-007
- KA-I-008/009
- KA-I-011
- KA-I-014
- KA-I-017/018
- KA-I-020/021/022/023/024/025
- KA-I-027/030/034
- KA-I-036/037
- KA-I-041/042/046
- KA-I-048/049

KA-I-004 remains candidate because replacement-device scenarios motivate explicit identity transitions but do not independently prove a universal reversible merge/split mechanism.

KA-I-047 remains candidate because `unknown`/`unavailable` validates absence-state distinctions but does not independently prove the closed-world completeness contract required for known-negative inference.

No invariant becomes a final architecture rule during KA-G7.

## Failure patterns

Failure IDs remain **KA-F-001 through KA-F-049**.

No new failure ID/status change is made because this task is cross-domain validation, not a reproduced ACL/Vera implementation incident.

---

# Twenty-six-question disposition after KA-G7

**All 26 campaign evidence questions now have sufficient project, standards/domain, or cross-domain evidence to proceed to requirements/synthesis gates without another broad research pass.**

KA-G7 closes the remaining direct gap:

- **26 Scope of truth / generality**

The architecture has now been challenged with a non-AI operational domain involving physical devices, rooms, people, observations, derived state, capabilities, commands and multi-party authority without exposing a missing universal primitive.

No additional direct gap-research task is currently assigned or justified.

---

# Cross-domain acceptance requirements carried forward

1. Platform/internal object identity is not automatically world identity.
2. Physical device, logical endpoint/entity and capability remain separable.
3. Display names and network/location addresses are not intrinsic identity.
4. Replacement/recommissioning does not silently inherit historical identity.
5. Location/area assignment is temporal relationship knowledge.
6. State observations remain separate from entity identity.
7. Unknown/unavailable/stale/known-value semantics remain distinct.
8. Derived operational state retains source/derivation lineage when consequential.
9. Person identity remains separate from tracker/source identity.
10. Capability profile and availability remain distinct and version-aware.
11. Operational address/endpoint numbers may differ from stable semantic identity.
12. Authorization fabric/context remains separate from world relationship truth.
13. Read/View and Operate/Manage/Administer remain distinct authority classes.
14. Command attempt and physical/effect settlement remain distinct.
15. Disabled/hidden/recoverable lifecycle states remain distinct from deletion.
16. Group/area targeting expansion remains a behavior-bearing selection step.
17. The universal substrate must support this domain without embedding Home Assistant/Matter concepts into the core schema.

---

# Pre-build scope-locked roadmap

Direct gap research is now complete.

Remaining path before physical implementation:

1. **Representative Retrieval Requirements** — approximately 40–60 concrete cross-domain questions and expected semantics
2. **Hostile / Adversarial Scenario Review**
3. **Conceptual Architecture Synthesis**
4. **Small Hand-Authored Cross-Domain Prototype / Validation**
5. **Only then: physical storage selection and implementation**

This sequence is a scope guard, not blanket authorization.

---

# Current task

**No task is currently assigned.**

KA-G7 is complete.

---

# Planned next candidate

**Representative Retrieval Requirements**

Suggested bounded focus:

- construct approximately 40–60 concrete queries/tasks spanning ACL, Vera, research, people, devices, projects, software versions, resources, permissions, history, conflict, provenance and deletion;
- define what each query must distinguish and what evidence/authority it requires;
- include current-state, historical, conflict, evidence, direct-vs-derived, structured, relationship, full-text, semantic, composite and authorization-sensitive cases;
- use these as acceptance requirements for later conceptual synthesis and storage evaluation;
- do not implement retrieval yet.

Queue position alone is not authorization.

---

# Stop point

KA-G7 is complete and all planned direct gap research is complete.

No retrieval-requirements construction, hostile-scenario execution, conceptual synthesis, prototype construction, storage selection or implementation was started inside KA-G7.