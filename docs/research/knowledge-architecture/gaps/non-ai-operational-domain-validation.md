# KA-G7 — Non-AI Operational-Domain Validation

**Campaign:** Knowledge Architecture Evidence Campaign  
**Task:** KA-G7  
**Domain:** Home Assistant / Matter-style smart-home and IoT operations  
**Status:** complete  

---

# Purpose

KA-G7 is a bounded cross-domain validation task.

The prior evidence campaign was dominated by agent frameworks, memory systems, retrieval systems, software tooling, provenance standards, authorization systems and data-governance concerns. That creates a risk that the resulting knowledge model could accidentally become an AI/coding schema rather than a general-purpose architecture suitable for Vera.

KA-G7 therefore asks one question:

> Do the accumulated knowledge-architecture separations survive contact with a non-AI operational domain involving physical devices, capabilities, rooms/areas, sensor observations, derived presence, commands, authority and changing hardware?

This task does **not** design Vera's smart-home subsystem and does not select Home Assistant, Matter, a device database, a message bus, a policy engine, or a physical schema.

---

# Scope

Included:

- physical device versus platform/device-registry identity;
- logical entity/endpoint versus physical-device identity;
- display/user-facing IDs versus stable integration/device IDs;
- device capability versus current state;
- observation/state versus durable entity identity;
- current state versus historical observation;
- direct observation versus derived state;
- `unknown` versus `unavailable` semantics;
- stale/fresh state implications;
- area/room assignment as a relationship rather than device identity;
- people versus device trackers;
- actions/commands versus observed effects;
- capability discovery/version drift;
- Matter node/endpoint/cluster/fabric/access-control separation;
- multi-admin/shared-household implications;
- hardware replacement/recommissioning hazards;
- whether the existing candidate primitives remain sufficient.

Explicitly excluded:

- Home Assistant installation or configuration;
- Matter implementation;
- smart-home hardware selection;
- Vera automation implementation;
- final conceptual schema synthesis;
- final relationship vocabulary;
- final device identity scheme;
- final authorization policy;
- retrieval-requirements construction;
- hostile-scenario execution;
- storage/database selection;
- implementation.

---

# Primary evidence inspected

## Home Assistant — device registry

https://developers.home-assistant.io/docs/device_registry_index/

Used for:

- device versus entity separation;
- one device exposing multiple entities;
- attached sensor/device distinction;
- physical-device representation rules;
- current 2026 behavior where one physical device supported by several integrations can have one device-registry entry per config entry.

## Home Assistant — 2026 device-registry architecture changes

https://developers.home-assistant.io/blog/2026/07/21/device-registry-single-config-entry/

Used for:

- explicit evidence that one physical device does not imply one universal platform registry identity;
- config-entry ownership of device-registry objects;
- splitting previously merged device representations;
- evidence against treating a platform-internal device ID as canonical physical-world identity.

## Home Assistant — entity registry

https://developers.home-assistant.io/docs/entity_registry_index/

Used for:

- platform/integration/unique-ID identity tuple;
- stable entity-registry identity distinct from editable names;
- stable entity ID behavior;
- requirement that user-facing names not serve as intrinsic identity.

## Home Assistant — entity unique-ID guidance

https://developers.home-assistant.io/docs/entity_registry_index/

Used for:

- serial/MAC/device-generated stable IDs as acceptable sources;
- IP address, device name, hostname, URL, email and username as unacceptable unique IDs;
- evidence that locators/display labels are weaker identity evidence than intrinsic or device-issued identifiers.

## Home Assistant — entities/devices/services architecture

https://developers.home-assistant.io/docs/architecture/devices-and-services/

Used for:

- integration -> entity -> state-machine boundary;
- entity registry versus live entity object;
- unavailable state when a registered entity has no current backing entity object;
- command/action handling separated from the state written to the state machine.

## Home Assistant — unavailable versus unknown

https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/entity-unavailable/

Used for:

- `unavailable` when current data cannot be fetched/reached;
- `unknown` when the entity exists and is reachable enough but its value is not presently known;
- explicit rejection of merely retaining the last known value as though it were current.

## Home Assistant — state objects

https://www.home-assistant.io/docs/configuration/state_object

Used for:

- state object as a current representation of an entity plus attributes at a moment;
- evidence that entity identity and one temporal state observation are distinct.

## Home Assistant — device trackers and Person

https://www.home-assistant.io/integrations/device_tracker/  
https://www.home-assistant.io/integrations/person/

Used for:

- exact-position versus connection-based observations;
- zone membership and `in_zones`;
- `unknown` and `unavailable`;
- one person derived from multiple tracker entities;
- explicit source selection rules based on tracker type/update recency;
- evidence that a person's current presence state is a derived projection with source lineage, not the person's identity itself.

## Home Assistant — areas

https://www.home-assistant.io/docs/organizing/areas/

Used for:

- area as a logical grouping intended to map rooms/areas in the physical home;
- devices/entities assigned to areas;
- area-targeted actions;
- evidence that location/area membership is a mutable relationship rather than intrinsic device identity.

## Matter — current specification availability

https://csa-iot.org/developer-resource/specifications-download-request/

Observed on 2026-09-08:

- Matter 1.6 is the newest listed specification family;
- Matter 1.5.1, 1.5, 1.4.2 and earlier remain separately published/versioned.

Used only to establish that Matter semantics are versioned and evolve; no Matter version is selected for implementation.

## Matter 1.4.2 architecture/security changes

https://csa-iot.org/newsroom/matter-1-4-2-enhancing-security-and-scalability-for-smart-homes/

Used for:

- multi-admin/controller trust;
- capability changes after commissioning;
- standardized reconfiguration notification;
- endpoint unique IDs designed to remain persistent across admins/recommissioning;
- evidence that endpoint number and endpoint semantic identity are not necessarily the same thing.

## Matter device data model / fabrics

https://developers.home.google.com/matter/primer/device-data-model  
https://developers.home.google.com/matter/primer/fabric

Used for:

- Node -> Endpoint -> Cluster hierarchy;
- server/client cluster roles;
- device-type descriptors;
- controllers versus controlees;
- multiple fabrics coexisting around one node;
- shared node data model versus fabric-specific operational credentials.

## Matter access-control model

CSA Matter core specification family.

Used for:

- access decisions scoped by incoming subject, endpoint, cluster and fabric;
- privilege classes such as View/Operate/Manage/Administer;
- evidence that authorization identity/scope is separate from physical-device identity and world knowledge;
- action attribution distinct from access-control-entry contents.

---

# Validation findings

## 1. A physical thing and a platform registry object are not the same identity

Home Assistant 2026.8 explicitly moved away from merging one physical device across config entries.

One physical device supported through several integrations can now produce several Home Assistant device-registry entries.

Therefore:

`physical device identity != Home Assistant device-registry ID`

This directly validates the campaign's distinction between internal/source identity and canonical semantic identity.

It also argues against defining Vera's durable device identity by whichever integration discovered the device first.

## 2. Device identity and entity/capability identity are different

A single physical device may expose:

- temperature;
- humidity;
- battery;
- switch state;
- brightness;
- occupancy;
- lock state;
- diagnostic signals.

Home Assistant models these as separate entities associated with a device.

Matter similarly decomposes a node into endpoints, clusters and device types.

Therefore the architecture must support:

`physical/logical thing -> capabilities/endpoints/entities`

without making every capability a new physical thing or collapsing all capabilities into one untyped state blob.

## 3. Entity display identity is not semantic identity

Home Assistant lets users rename entities while preserving stable entity-registry identity based on platform/integration/unique ID.

Names, hostnames, IP addresses and URLs are explicitly unsuitable unique IDs.

This independently validates:

- stable identity independent of display label;
- locator != identity;
- source/platform identity != global semantic identity.

## 4. Hardware replacement must not be inferred from a friendly-name match

A replacement device may deliberately reuse:

- the old friendly name;
- the same room;
- the same dashboard slot;
- the same intended role;
- perhaps even the same automation target.

That does not prove it is the same physical device.

Conversely, recommissioning or integration changes may alter platform-specific IDs without changing the physical device.

The architecture therefore needs an explicit identity-resolution transition rather than automatic merge-by-name/room/role.

This reinforces unresolved identity and auditable merge/split requirements; it does not establish a new invariant beyond the existing identity family.

## 5. Area/location is a relationship, not identity

Home Assistant Areas are logical groupings intended to match rooms/areas in the physical world.

A sensor can be moved from one room to another without becoming a new sensor.

Therefore:

`device located_in area`

is mutable relationship knowledge with time/applicability, not part of the device's immutable identity.

This validates the campaign's first-class governed-relationship model.

## 6. Current state is not the entity

Home Assistant's state object is a current representation of an entity at a moment in time.

The entity persists through many state changes.

Therefore:

`entity identity != state value != state observation occurrence`

This is a direct non-AI validation of canonical entity versus temporal assertion/observation separation.

## 7. `unknown` and `unavailable` are operationally different

Home Assistant explicitly distinguishes:

- `unknown`: the value is not presently known;
- `unavailable`: the entity/device/service cannot currently supply the value / is not reachable in the expected way.

This matters because both differ from:

- known false/off;
- stale last-known value;
- entity nonexistent;
- entity disabled;
- capability unsupported.

The architecture must not collapse these states into null, false, or last-known-current.

This provides strong non-AI recurrence for the epistemic/negative-knowledge work from KA-G1.

## 8. Last known state must not silently become current truth

Home Assistant's quality guidance explicitly recommends marking entities unavailable when fresh data cannot be fetched rather than simply continuing to show the last state as current.

For Vera this implies:

- last-known value may remain historically useful;
- freshness/observation time must remain visible;
- automation eligibility may require stricter freshness than conversational retrieval;
- an unavailable sensor cannot silently supply a fresh current-state assertion.

This validates separate temporal truth, freshness and actionability dimensions.

## 9. Presence is a derived projection, not raw truth

Home Assistant Person can derive one person's location/presence from multiple device trackers with explicit source-selection rules.

Connection-based and position-based trackers have different semantics.

The resulting Person state is therefore a calculated projection over observations.

For Vera:

`person presence state`

should retain enough lineage to answer:

- which tracker(s) contributed;
- what rule/profile selected the current result;
- when the source observations occurred;
- what uncertainty or availability existed.

This strongly validates canonical-vs-derived and provenance requirements outside AI.

## 10. One person is not one tracker

A phone GPS tracker, router association, BLE beacon and car connection can all provide evidence about one person.

None is the person.

This independently reinforces:

`semantic entity identity != source sensor/tracker identity`

and makes identity/source provenance necessary in everyday Vera scenarios.

## 11. Capability description and current capability availability are different

Matter endpoints/clusters and Home Assistant entity classes describe supported capabilities.

But a capability may be:

- disabled;
- temporarily unavailable;
- unsupported in the current firmware/profile;
- newly added after device reconfiguration;
- reachable only through a secondary channel.

Therefore capability schema/profile and current operational availability are separate dimensions.

## 12. Capability/version drift is real operational knowledge

Matter 1.4.2 standardized notification when devices gain new capabilities or change configuration after commissioning.

Matter specification families are versioned and continue evolving.

Therefore:

- device model/profile revision matters;
- capability discovery may need refresh/reconciliation;
- old derived assumptions cannot silently remain current when device profile changes;
- capability profile belongs in reproducibility and authority evaluation where behavior changes.

This validates schema/profile-version invariants from the software research.

## 13. Endpoint number and endpoint semantic identity can differ

Matter 1.4.2 introduced Endpoint Unique IDs because endpoint IDs could vary across administrators or recommissioning.

This is a concrete operational example of:

`address/locator within one operational context != stable semantic identity`

It strongly echoes KA-G5's resource locator/content identity separation in a physical-device setting.

## 14. Node, endpoint, cluster and fabric are separate scopes

Matter's hierarchy separates:

- node;
- endpoint;
- cluster/capability;
- fabric;
- controller/subject.

A single flat `device_id` plus arbitrary attributes would lose behavior-bearing scope.

The existing architecture can represent this through entities, relationships, scoped assertions, capability identities and authority context without inventing a special Matter-only primitive.

## 15. Shared-device authority is not ownership truth

Matter multi-admin/fabric semantics show that multiple ecosystems/controllers can possess operational authority over one node.

That does not mean:

- all controllers are the human owner;
- every household member has identical authority;
- controller presence is a permanent world relationship;
- one fabric's authorization state is globally authoritative.

This validates the separation of canonical world relationships from authorization relationships established in KA-G4.

## 16. Access control is endpoint/action/context scoped

Matter access control evaluates subject/fabric plus the target endpoint/cluster and required privilege.

Privileges such as View and Operate are distinct.

This is direct non-AI recurrence for:

`read != operate != administer`

and therefore for Knowledge != Authority != Execution.

## 17. A command is not proof of resulting world state

Sending `turn_on`, `unlock`, `set_temperature`, or another command is an attempted effect.

The later observed device/entity state is evidence about what actually happened.

These must remain separate:

`requested action -> authorization -> command attempt -> device/system response -> later observation/state`

This validates the separate effect-ledger/observation feedback loop.

## 18. Immediate API success is not necessarily physical settlement

Networked devices can acknowledge receipt before the physical world has reached the intended state, and state can subsequently diverge.

Consequential automation therefore needs effect settlement/verification appropriate to the action rather than equating command invocation with world truth.

No device-specific verification policy is selected here.

## 19. Disabling/hiding is not deletion

Home Assistant distinguishes registered entities that are disabled or hidden from entities that no longer exist.

This is another non-AI example of lifecycle/status semantics where presentation or active-use state must not be conflated with erasure.

## 20. A room/area-targeted command is derived targeting

When an action targets an area, the concrete set of devices/entities can depend on current assignments and supported action classes.

Therefore an area-targeted action should not be recorded merely as though every resulting device target had been directly named by the user.

Target expansion is a transformation/selection step with its own context/profile.

## 21. Direct observation and inferred relationship remain distinguishable

Examples:

- GPS says phone coordinates X;
- zone engine derives `phone in Home`;
- Person integration derives `Floyd is home`;
- automation reasons `occupant present`.

Those are progressively derived statements.

The endpoint conclusion should remain explainable through the observation/inference chain.

## 22. The existing primitives are sufficient at the conceptual level

KA-G7 did not uncover a missing universal primitive that forces a redesign.

The existing conceptual families remain adequate:

- Entity;
- Identity;
- Assertion/Claim;
- Observation;
- State;
- Occurrence/Event;
- Relationship;
- Capability;
- Resource;
- Evidence/Source;
- Rule/Policy;
- Procedure/Transformation;
- Effect/Action occurrence outside the knowledge-authority boundary.

The final synthesis may simplify or unify some of these, but the non-AI domain does not require a separate smart-home ontology at the substrate layer.

---

# Cross-domain mapping examples

## Example A — temperature sensor

World/entity:

`device D`  
`entity/capability temperature_sensor T belongs_to D`

Observation:

`T observed 23.1 C at 20:15 from integration X`

Derived current projection:

`current_temperature(T) = 23.1 C`

Later failure:

`T unavailable at 20:22`

Important consequence:

The historical observation remains valid as a past observation, but Vera must not silently present 23.1 C as fresh current truth at 21:00 without qualification.

## Example B — person presence

Sources:

- phone GPS tracker;
- Wi-Fi connection tracker;
- BLE tracker.

Derived state:

`Person P is_home`

Needed lineage:

- selected source tracker;
- observation time;
- tracker type;
- derivation/profile version;
- other conflicting/stale trackers when relevant.

## Example C — replacement smart plug

Old device:

`physical_device A`

User-facing role:

`Kitchen Coffee Plug`

Replacement:

`physical_device B`

The friendly name and automation role may intentionally transfer to B.

Safe architecture:

- preserve A historically;
- create/resolve B independently;
- create explicit replacement/succeeds relationship where verified;
- migrate user-facing role/automation binding deliberately;
- do not rewrite A's historical observations as B's.

## Example D — Matter multi-admin lock

World entity:

`Front Door Lock`

Operational representations:

- Matter node/endpoint on fabric A;
- Matter node/endpoint on fabric B;
- Home Assistant entity representation;
- vendor cloud representation.

Authority:

- controller on fabric A may Operate;
- another principal may View only;
- household policy may impose additional confirmation.

Knowledge:

`lock currently reports locked`

These identities/scopes must not collapse.

---

# Cumulative ledger disposition after KA-G7

## Invariants

Invariant IDs remain **KA-I-001 through KA-I-049**.

No new invariant ID or status change is required.

Reason:

KA-G7's value is independent cross-domain validation. It strongly recurs with existing reinforced requirements rather than exposing a new universal semantic primitive.

Strong non-AI recurrence includes:

- KA-I-002 — internal/source identity distinct from semantic identity;
- KA-I-005 — ambiguity/unresolved identity must remain representable;
- KA-I-007 — governed relationships matter;
- KA-I-008/009 — temporal/current/history query distinctions;
- KA-I-010 — rank/relevance is not truth/authority;
- KA-I-011 — derived state carries generation/profile identity;
- KA-I-014 — authorization gating before consequential use;
- KA-I-017/018 — profile/version changes are behavior-bearing;
- KA-I-020 — knowledge retrieval never grants execution authority;
- KA-I-021 — unknown/not-established/current-state distinctions;
- KA-I-022 — structured applicability/scope;
- KA-I-023 — behavior-changing transformations need provenance;
- KA-I-024 — context construction separate from retrieval;
- KA-I-025 — epistemic basis separate from attribution/state;
- KA-I-027 — derived outputs expose sources/generation;
- KA-I-030 — derived association graph distinct from canonical relationships;
- KA-I-034 — ownership/read-write authority distinctions;
- KA-I-036/037 — source/platform/location/version identity separations;
- KA-I-041/042/046 — occurrence/tool/authority identity and version binding;
- KA-I-048/049 — relationship assertion occurrence and direct-vs-derived explanation distinctions.

KA-I-004 remains candidate: replacement-device scenarios strongly motivate auditable identity transitions, but KA-G7 does not independently demonstrate a validated universal reversible merge/split mechanism.

KA-I-047 remains candidate: `unknown`/`unavailable` supports absence-state distinctions but does not independently establish the closed-world completeness contract needed for known-negative inference.

No invariant becomes a final architecture rule during KA-G7.

## Failure patterns

Failure IDs remain **KA-F-001 through KA-F-049**.

No new failure ID/status change is made because KA-G7 is domain/standards validation rather than a reproduced implementation incident in ACL/Vera.

---

# Twenty-six-question disposition after KA-G7

All 26 campaign evidence questions now have sufficient project, standards/domain or cross-domain evidence to proceed to requirements and synthesis gates without another broad framework/domain research pass.

KA-G7 materially closes:

- **26 Scope of truth / generality**

The architecture has now been tested against a non-AI operational domain involving people, physical devices, mutable location, observations, derived state, capabilities, commands and multi-party authority.

No new direct gap-research task is currently justified.

---

# Requirements carried forward from KA-G7

1. Platform/internal device identity is not automatically physical-world identity.
2. Physical device, logical endpoint/entity and capability identities remain distinguishable.
3. Display names/locations/network addresses are not intrinsic identity.
4. Replacement hardware does not inherit identity merely by name/room/role.
5. Area/location assignment is a mutable relationship with time/applicability.
6. Entity identity is distinct from temporal state/observation occurrences.
7. Unknown, unavailable, stale and known-value states remain distinct.
8. Last-known state does not silently become fresh current truth.
9. Derived states retain source/derivation lineage when consequential.
10. Person identity is distinct from tracker identities.
11. Capability schema and current availability are distinct.
12. Capability/profile revision is behavior-bearing.
13. Operational endpoint/address identifiers may differ from stable endpoint semantic identity.
14. Node/endpoint/cluster/fabric/principal scopes must not collapse.
15. Authorization relationships are not automatically world relationships.
16. View/read and operate/manage/administer remain distinct authority classes.
17. Command attempt and observed physical result remain distinct occurrences.
18. Effect settlement/verification is separate from command invocation.
19. Disabled/hidden/recoverable state is not deletion.
20. Group/area target expansion is a transformation with selection context.
21. Direct observations and derived operational conclusions remain explainable separately.
22. The general substrate should model the smart-home domain without embedding Home Assistant/Matter-specific primitives into the universal core.

---

# Nominated retrieval questions

Do not execute/build these during KA-G7; carry them into the next requirements task.

- What is the current temperature in the living room, and how fresh is it?
- What was the last observed temperature before the sensor became unavailable?
- Is the sensor offline, unknown, disabled, missing, or merely stale?
- Which physical device provides this temperature entity?
- Has this device been replaced, renamed, or merely moved to another room?
- Why does Vera believe Floyd is home?
- Which tracker produced the decisive presence evidence?
- What conflicting trackers existed at that time?
- What capabilities does the front-door lock support under the current device profile?
- Which controller/principal may view versus operate the lock?
- Did the unlock command settle physically or merely return success?
- Which devices were targeted when an area-level command was expanded?
- Which observations were direct and which states were inferred?
- What changed after the device firmware/capability profile changed?
- Does a second integration represent the same physical device or a distinct device?

---

# Nominated hostile scenarios

Do not execute during KA-G7.

- replacement bulb reuses old friendly name and is silently merged;
- same physical device appears through local and cloud integrations and is incorrectly duplicated/merged;
- IP address reused by another device and treated as stable identity;
- unavailable sensor's last value triggers automation as though current;
- `unknown` coerced to zero/false and used for consequential action;
- person location derived from stale tracker after fresher source disappears;
- area move retroactively rewrites historical room location;
- capability removed by firmware but old automation continues to assume it exists;
- Matter endpoint number changes after recommissioning and historical identity is lost;
- fabric/controller identity treated as human ownership;
- View permission reused as Operate permission;
- command acknowledgement recorded as physical state settlement;
- direct sensor observation and derived person/location conclusion share one identity;
- disabled entity reported as erased;
- area-target expansion changes between authorization and execution;
- physical replacement device inherits old device's historical observations.

---

# Conclusion

KA-G7 validates the campaign's general architecture direction.

The non-AI operational domain does **not** require abandoning or materially redesigning the accumulated conceptual separations.

Most importantly, the following survive intact:

`Identity != name/address/platform ID`

`Entity != observation != current projection`

`Unknown != unavailable != stale != false`

`Direct observation != derived state`

`Capability != authority`

`Knowledge != authorization != command/effect`

`Command attempt != physical settlement`

`Authorization relationship != canonical world relationship`

`Current platform profile != timeless device truth`

The next campaign phase should therefore stop direct evidence gathering and convert the accumulated evidence into representative retrieval/decision requirements before synthesis.

---

# Stop point

KA-G7 is complete.

Do not begin retrieval-requirements construction, hostile-scenario execution, conceptual synthesis, prototype construction, storage selection or implementation without separate authorization.