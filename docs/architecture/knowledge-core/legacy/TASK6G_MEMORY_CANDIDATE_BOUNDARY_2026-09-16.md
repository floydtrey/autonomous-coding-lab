# Task 6G — Memory Candidate Containment Boundary

**Accepted behavior-bearing checkpoint:** `80f3804ce2c1a905c3853f9e7c507066a5ca9431`

**Qualification:** GitHub Actions `35064560448` — green across migration, fast semantic suite, PostgreSQL G1–G21, pinned G22 real-document pilot, RI-4 restart rehearsal, and SR-2 restart/replay rehearsal.

## Purpose

Task 6G separates autonomous/self-initiated worker observations from explicit trusted canonical storage. A worker may propose information for later consideration without that proposal becoming KC truth, searchable evidence, graph input, or a current canonical source. Canonical `kc_store` remains available for explicit trusted/user-directed storage, but bootstrap possession alone can no longer authorize the write.

## Accepted boundary

The accepted implementation adds a durable `kc_control.memory_candidate` ledger and migration `0018_memory_candidate`. Candidate proposal is exposed as `POST /v1/kc/memory-candidates` behind the separately scoped bootstrap operation `kc.memory_propose`.

Proposal and review operations remain outside canonical KC revision history. They do not create a `Revision`, `Resource`, `ResourceVersion`, governed source observation/decision, TEXT generation, graph projection, or provider/model work.

Candidate states are:

- `pending` — proposed and awaiting an explicit trusted review;
- `approved` — eligible for a later explicit trusted store decision, but still non-canonical;
- `rejected` — explicitly rejected and still non-canonical.

Review uses the separate deterministic `MemoryCandidateReviewEvaluator`. Approval never invokes `kc_store`, never creates canonical knowledge, and is not itself promotion.

Task 6G intentionally adds no public review/promote endpoint. Wrapper/user workflow integration remains later work.

## Canonical store containment

`POST /v1/kc/store` still represents explicit canonical `user_note` storage. Task 6G adds a second fail-closed `CanonicalStoreAuthorityEvaluator` after bootstrap admission and before any canonical mutation.

The authority request is bound to the exact semantic write inputs:

- authenticated caller principal;
- deterministic store operation ID;
- project key;
- content SHA-256;
- optional stable source ID;
- optional timezone-aware source event time.

If the authority seam is absent, canonical storage fails with bounded authority-unavailable state before canonical mutation. If authority denies the exact request, storage fails with bounded denial before canonical mutation. An allow decision permits the preexisting direct-note canonical path to continue.

The first fully green Task 6G head, `9597da247beb4924cc3618c3da151e2d03ea5573`, established the candidate ledger and store-authority containment. Architecture review then found that the exact authority request did not yet bind optional `source_event_time`, even though that timestamp becomes durable provenance and can influence graph reference-time policy. The request contract, API binding, and focused fast test were corrected; the complete KC workflow was rerun green on the accepted checkpoint `80f3804ce2c1a905c3853f9e7c507066a5ca9431`.

## Explicit non-scope

Task 6G does **not**:

- automatically promote approved candidates;
- let a model decide canonical truth;
- expose a public candidate review/promote operation;
- change the Mason bridge protocol or add a worker-visible proposal command;
- implement context compaction;
- synchronize/build/query Graphiti as part of memory admission;
- launch a model/provider/background worker;
- perform live Mason/Cowork qualification.

The existing Mason bridge therefore still contains its historical `kc_store` operation, but possession of the bridge/bootstrap key alone is insufficient to make that call canonical. A trusted host must supply the exact-write authority decision. Task 6I owns worker-wrapper proposal routing and integration.

## Qualification meaning

Acceptance proves the deterministic containment boundary and its database/migration compatibility. It does not claim that a future wrapper applies the right human-intent policy, that Mason has been live-tested against the proposal workflow, or that candidate approval automatically means the information should become canonical. Those are separate integration/qualification questions.

## Next boundary

Task 6H may implement wrapper-side working-context compaction/checkpointing. Task 6H must not silently absorb Task 6I MindsHub/Cowork integration.
