# Controller Task Packet V1

Controller Task Packet V1 is the canonical informational handoff from the controller/Knowledge Core boundary into the current Invocation V3 workspace-write path.

## Contents

The packet binds:

- attempt/controller identity;
- user request;
- protected exercise identity and starting Git source state for the current coding capability;
- exact governed Knowledge Core segment evidence/content/provenance.

## Authority boundary

Knowledge Core evidence is informational only. Packet content cannot grant or modify writable/readable scope, sandbox mode, tools, policy/role, test plan, acceptance criteria, provider/model selection, Provider Binding, publication authority, or lifecycle transitions.

Worker Lab protected definitions remain authoritative for those facts.

## Current V3 handoff

The packet is canonical JSON. Worker Lab binds its digest into Invocation V3 and the provider-neutral dispatch envelope. The framework independently validates packet/invocation linkage before bounded execution can be reached.

Current public V3 preparation does not use a plain-text compatibility prompt path. A packet mismatch or provenance/content mismatch fails closed.

## Knowledge evidence

`worker-lab-knowledge-core-segment-evidence:v1` preserves generation/profile identity, source/version references, lifecycle state, exact byte/line coordinates, source-slice digest, and exact content. Only evidence accepted by the current consumer contract may be served into the packet.

Repository/source fields inside Knowledge Core provenance describe governed source evidence; they do not become ACL target identity or execution authority.
