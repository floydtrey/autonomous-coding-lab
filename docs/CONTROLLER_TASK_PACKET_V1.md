# Controller Task Packet V1

Controller Task Packet V1 is the canonical informational handoff from the controller/Knowledge Core boundary into the current Invocation V3 workspace-write path.

The packet contract is implemented; the sequential controller does **not** exist yet. Building that controller is the next implementation milestone. Initial V1 workers receive exact-file read/write authority, while protected tests and independent result validation run on the controller side through Worker Lab. The existence of a packet or preparation API does not establish a working end-to-end controller or a qualified provider.

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

S04 also admits explicit job-task records without creating curriculum exercises.
For these attempts, the existing packet `exercise_id` and `exercise_version`
slots carry the deterministic job-task key and plan revision. V3's definition
and task digests bind the full approved job record, including criterion/test
identities and authority. Packet canonicalization remains unchanged. See
[Job Plan V1](JOB_PLAN_V1.md) for the compatibility mapping
and the admission-only execution stop gate.

## Knowledge evidence

S05 adds `worker-lab-controller-task-packet:v2` for an explicit context choice.
V2 adds the required `context_mode` field: `none` means no KC context was
requested or required and requires `knowledge_evidence: []`; `knowledge-core`
requires one to four governed evidence items. Missing, unknown, or contradictory
context choices fail closed. The mode is included in canonical JSON and its digest.

Both `build_controller_task_packet` and `prepare_controller_task_invocation`
accept `no_context=True` for a self-contained task. Supply neither
`kc_search_response` nor `result_indexes` in that mode. This creates V2 directly,
without calling retrieval or constructing a pretend empty search response.
Omitting both KC input and the explicit no-context choice remains an error.

Existing KC-bearing calls continue to emit V1 with exactly the same fields,
canonical bytes, and digests. V1 still requires one to four evidence items.
Worker Lab and AWF accept both packet versions; AWF states the explicit
no-context choice in the worker prompt. No KC API or evidence schema changes.

`worker-lab-knowledge-core-segment-evidence:v1` preserves generation/profile identity, source/version references, lifecycle state, exact byte/line coordinates, source-slice digest, and exact content. Only evidence accepted by the current consumer contract may be served into the packet.

Repository/source fields inside Knowledge Core provenance describe governed source evidence; they do not become ACL target identity or execution authority.
