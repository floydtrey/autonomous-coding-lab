# Knowledge Core — Architecture and Contracts

**Authoritative current KC invariants.** Read [CURRENT_STATE.md](CURRENT_STATE.md) for implementation/acceptance status and [OPERATIONS.md](OPERATIONS.md) for evidence and operating procedures. Historical documents under `legacy/` preserve their original scope and evidence; they do not supersede this current contract.

## Ownership and trust

Knowledge Core is a standalone semantic service. PostgreSQL is canonical; immutable artifacts carry exact source bytes; lexical indexes, Graphiti/FalkorDB state, embeddings, summaries, caches and other retrieval projections are derived and rebuildable.

```text
Mason / MindsHub (future)       ACL Controller / Worker Lab       Vera (future)
             \                       |                         /
                      KC semantic service boundary
                     Authority evaluation for retrieval
                                |
           PostgreSQL canonical state + immutable source artifacts
                                |
           governed observations -> deterministic SR-2 segments
                                |
               PostgreSQL lexical       Graphiti / FalkorDB
                                          derived builds
```

Knowledge does not grant authority. Authority does not prove execution. Execution acknowledgement does not prove world settlement. Worker Lab owns ACL policy, lifecycle, Provider Binding, task authorization and result acceptance; Autonomous Worker Framework executes bounded work. KC supplies informational evidence only.

Clients use semantic operations rather than direct database/artifact credentials, arbitrary SQL/CRUD, or provider-owned identities. AI processes, retrieved text and graph output cannot enlarge protected scope. Authority remains a separate deterministic boundary. The current injected retrieval evaluator is a seam for that boundary, not proof of production authentication or a deployed Authority service.

## Canonical state and identity

The accepted KC-D001–KC-D024 foundations remain:

- PostgreSQL schemas separate `kc` canonical semantic/history records, `kc_control` operation/qualification/deletion controls, and `kc_derived` rebuildable projections. UUID references address records; canonical revisions order commits.
- ENTITY, ASSERTION, OCCURRENCE, RESOURCE, EVIDENCE/PROVENANCE LINK, and SEMANTIC PROFILE/VOCABULARY DEFINITION are semantic families, not a demand for one table per family. Assertions use typed relational values with bounded profile-governed JSON extensions.
- Ordinary correction/reversal appends history. World-valid time and immutable knowledge-record time are independent; current views are derived. Identity transitions preserve stable entities and history; replacement is not equivalence.
- Provenance is typed, traversable lineage distinct from truth, semantic relationships, lifecycle and authority. Exact ResourceVersion, source activity and revision references support backward explanation and forward impact.
- Immutable artifacts are SHA-256-addressed outside PostgreSQL. Deduplicated bytes do not merge logical ownership or provenance. Semantic profiles/vocabularies are immutable and versioned; changes cannot silently reinterpret old assertions.
- State-dependent writes use expected revisions, stable operation IDs and idempotent replay. Reusing an operation identity with different inputs fails; derived publication fences stale finishers and permits only one current generation.
- Privacy restriction/erasure fences access before cleanup. Parent Resource/ResourceVersion eligibility dominates every derivative, including stale rows. Ordinary supersession/retirement-retain preserves history and is not privacy erasure.

Accepted deployment requirements include distinct least-privilege service identities, an independently protectable Authority Root, scoped secrets outside KC/prompts/source control, and coordinated PostgreSQL/artifact backup with deletion/restriction controls reapplied before restored serving. These are architectural requirements; historical kernel/host tests do not establish full production deployment, physical erasure across every external system, or operational backup/restore qualification.

Python 3.12+, FastAPI/Pydantic and versioned HTTP/JSON are the implementation baseline. Exact physical schema is defined by committed models/migrations, not an archived preimplementation schema candidate.

## Source-neutral governed knowledge boundary — Task 2 accepted contract

The 2026-09-14 Task 2 source-model audit found that the canonical Resource/ResourceVersion/artifact foundation was largely source-neutral while governed retrieval had repository/Git assumptions below the adapter boundary. Tasks 2A–2F now implement and qualify the correction through governed evidence, complete SR-2 selection/lineage/publication, authenticated direct-note storage, and source-neutral lexical serving/evidence.

Historical repository/SR-2/Graphiti qualifications retain their exact original scope and must not be relabeled as qualification of later behavior. The remaining repository-shaped Graphiti plan/reference-time input and some downstream ACL compatibility schemas are later bounded work; they do not redefine the accepted generic KC source model.

The governing rule is to keep the generic evidence and source-set boundary **above canonical ResourceVersion and below derived retrieval**, while keeping source verification strongly source-specific.

### Distinct identities and evidence meanings

The generic contract keeps these meanings separate:

1. **Resource** — KC-owned logical canonical object.
2. **ResourceVersion** — exact canonical content/bytes identity for one Resource.
3. **Governed source identity** — logical origin item represented with typed source kind, origin scope/account/workspace as applicable, collection/container identity, and item identity. Source identity is not inferred from content hash alone.
4. **Observation/admission evidence** — immutable evidence that a producer submitted/captured a specific ResourceVersion in a specific source context, with producer-specific proof and relevant times. Re-observation of the same bytes is not automatically the same observation.
5. **Governance decision/state** — lifecycle/classification/ranking inputs accepted by KC. Producer claims are evidence until admitted; they are not an independent source of authority.
6. **Governed retrieval snapshot** — immutable, digest-bound selection of exact observations/versions plus policy inputs, exclusions/retentions and predecessor state used to build one complete serving corpus.
7. **Project/context membership** — separate association from source origin identity. One source may be relevant to multiple projects; project must not be smuggled into a renamed repository key.

Captured/origin locators and current display/navigation locators are also distinct where needed. Typed Git paths, URLs, mailbox locators, file paths and other source-specific locator evidence are valid; no one locator type becomes universal identity.

### Source-specific proof remains source-specific

Repository import remains a verified Git producer. Its exact commit/path/blob proof, configured readers, path safety, manifest chain, continuity/retirement rules, Git object identity and receipt/replay semantics stay inside the repository producer boundary. Do not fabricate repository names, commits, paths, blob hashes or manifests for notes, chats, files, email, benchmark evidence or Vera observations.

The first accepted non-Git producer is authenticated local `user_note`. Its source proof is the admitted `local_owner` submission plus exact canonical byte custody and deterministic operation evidence. Email/chat/file/benchmark producers will require their own source identities and capture evidence and are not implemented merely because the generic contract can represent them.

### Observation identity and time

One ResourceVersion may participate in multiple observations or governance contexts. A→B→A content reuse remains valid without collapsing the later A observation into the earlier one. Repeated capture, replay, reclassification and a new intentional identical submission are distinct cases and require explicit semantics.

Where applicable, keep separate:

- source event time;
- source revision time;
- KC observation/capture/admission time;
- derived-provider reference-time policy.

Repository receipt/import time is not a universal event clock. Any time that changes derived semantic behavior must be bound into the appropriate versioned snapshot/config/evidence rather than silently reinterpreting historical attempts.

### Complete-corpus snapshot and publication

KC retains one-current-generation fencing for TEXT. A producer must not publish only its own contribution and displace other current sources.

```text
source-specific producer proof
        -> canonical Resource / ResourceVersion
        -> generic governed observation/admission
        -> complete immutable governed retrieval snapshot
        -> deterministic SR-2 candidate
        -> validation
        -> atomic one-current-generation publication
```

A new or changed producer contribution is applied to the intended current corpus and publishes a complete replacement snapshot. Snapshot/predecessor checking prevents stale producers from losing other current contributions or resurrecting excluded/restricted sources. Failed candidate publication leaves the previous current generation serving; already committed canonical evidence remains durable and reports derived text state as pending/failed rather than being rolled back.

Canonical revision highwater alone is insufficient to order governance-only changes. Snapshot identity/predecessor semantics cover metadata-only governance changes as well as new bytes.

### Versioning and historical compatibility

Existing repository manifests, observations, digests, historical SR-2 lineage serializers, migrations, accepted generations, Graphiti attempts and qualification evidence retain their original meaning. Applied migrations and old digest interpretation are not rewritten. Source-neutral semantics use new versioned durable contracts/digests and explicit legacy mappings.

Task 2C migrated the live repository HTTP path to SR-2 and added a central generation fence so the legacy RF-2 writer cannot replace an established SR-2 current TEXT generation. Historical RF-2 reconstruction from an empty/RF-2 state remains available for its original qualification scope.

Task 2F establishes the lexical compatibility boundary:

- the response-level evidence contract is `kc-lexical-evidence-v2`;
- current source-neutral SR-2 hits use provenance contract `governed-source-sr2-v2`;
- source-neutral provenance exposes generic source identity, generic observation/digest, governance decision/digest, governing snapshot, projection digest, project memberships, producer identity/version and distinct source/observation times;
- repository compatibility fields are populated only when exact legacy mapping exists. Non-Git sources leave repository/commit/path/manifest compatibility fields null rather than fabricating values;
- historical pre-2D SR-2 generations retain an explicit repository evidence mode instead of being silently reinterpreted as V2;
- any partial/mixed generic lineage or mismatch between the serving generation, generic snapshot, ResourceVersion, decision, projection digest or repository compatibility mapping fails closed before results are trusted;
- the entire current SR-2 source set is validated before serving a matching hit, preventing corruption in an unqueried source from remaining silently trusted;
- for compatibility with existing repository consumers and accepted G22 behavior, `segment.governed_observation_id` continues to expose the legacy verified repository observation ID when such a mapping exists. `segment.governed_source_observation_id` is the unambiguous generic observation ID. For non-repository sources, where no legacy observation exists, the compatibility field identifies the generic observation as well.

This compatibility rule is lexical evidence compatibility only. It does not make legacy repository identity authoritative for generic KC knowledge.

## Governed repository import

Stable repository identity is `(source_repository_key, source_document_key) -> Resource`. A path/commit is bounded Git-source evidence, not logical canonical identity. A changed path does not independently authorize a new document or retirement.

The importer verifies manifest-listed exact commit/path/blob objects through trusted configured repository readers before canonical writes; clients do not supply roots/credentials or request recursive discovery. Receipts and immutable source observations retain the manifest chain, plan/source evidence, classification and resulting generation. No unlisted content is authorized by a pilot manifest.

ResourceVersion is content-addressed within one logical Resource: unseen bytes create a version; A → B → A reuses the original A version. The later observation/receipt/generation records the new event. Source lifecycle, classification and authority are governed metadata, never inferred from recency, names, paths or prose.

Repository import is one producer of source-neutral governed evidence and complete SR-2 snapshots, not the definition of every downstream governed source.

## SR-2 structure, lifecycle and publication — KC-D025

```text
exact ResourceVersion artifact + structural profile
    -> deterministic structural segments
segments + exact governed observation/classification snapshots + projection profile
    -> lifecycle/ranking projection -> complete generation -> atomic publication
```

Segments are derived source slices, never new canonical resources. Structural identity ignores lifecycle/ranking changes for unchanged source bytes/profile. Full generation reproducibility additionally requires the exact governed snapshots, both profiles and configuration digest; ResourceVersion alone is insufficient.

The structural contract is deterministic UTF-8 `text/plain` / `text/markdown` segmentation. It preserves every original byte, including LF/CRLF. Concatenating ordinal slices reconstructs the source without gaps or overlap. Byte coordinates are zero-based half-open; line coordinates are one-based inclusive. An empty source has one `[0,0)` root segment, lines 1–1.

Markdown uses ATX headings (0–3 leading spaces, 1–6 `#`, then space/tab or end of line) with fenced-code awareness. Setext headings and ordinary prose/HTML/lists/quotes do not create sections. Bytes before the first heading form a preamble; each heading starts a block ending at the next heading of any level. Hierarchy is heading-path metadata, without duplicated child bytes. Plain text has a root document block.

The structural profile uses `soft_target_bytes=16384`, `hard_max_bytes=32768`. Oversized blocks split only at legal whole-line boundaries outside indivisible fences: prefer the blank-line boundary closest to soft target (lower offset breaks ties), otherwise the greatest legal boundary within hard max. Emit the final suffix whole when within hard max. An indivisible line/fenced region with no legal boundary fails closed. No tokenizer or model participates.

Each segment retains ordinal/key, kind, base-block ordinal, part index/count, heading path, exact byte/line coordinates and source-slice SHA-256. Candidate generations stay non-serving until complete. Existing serving continues until a complete replacement generation publishes; no partial cutover or mixed-generation retrieval is permitted.

The segmentation/lifecycle algorithms remain accepted. Task 2D makes live SR-2 candidate construction/publication source-neutral, Task 2E proves a non-Git note can enter the same complete generation, and Task 2F makes the lexical serving/evidence path source-neutral without weakening repository proof.

### Lifecycle rules

Lifecycle restrictiveness is `current < unknown < superseded`. Effective lifecycle is the most restrictive of governed parent-document state, applicable ancestor declarations and the section's own declaration. A less restrictive child declaration remains source evidence but cannot promote effective lifecycle. Parent downgrade can publish new lifecycle metadata over unchanged structural identities.

For Markdown, the only valid section declarations are exactly `<!-- kc:retrieval-lifecycle=current -->`, `<!-- kc:retrieval-lifecycle=unknown -->`, or `<!-- kc:retrieval-lifecycle=superseded -->`, allowing 0–3 leading spaces and trailing ASCII whitespace. A declaration must be outside a code fence, the first nonblank body line after an ATX heading, and unique for that heading. It stays in source bytes/digest and is omitted only from lexical search text. Malformed, misplaced or duplicate standalone attempted directives fail lifecycle projection. Prose, inline examples, quotes and fenced examples are ordinary content.

Default retrieval excludes `superseded`; historical retrieval requires explicit inclusion. Preserve declared/effective state and controlling directive coordinates alongside exact governed-observation lineage. If a parent is physically purged, its derivatives must not remain; serving-time parent eligibility also protects against stale derivatives.

The detailed accepted [SR-1 specification](legacy/SECTION_RETRIEVAL_SR1.md) and [KC-D025 decision](legacy/DECISIONS.md#kc-d025--section-structure-is-content-derived-retrieval-lifecycle-is-governed-snapshot-derived) remain frozen contract lineage for targeted audits. Their old implementation status/next tasks are superseded by current status.

## Usable V1 direct-note store contract

When the trusted host explicitly supplies `BootstrapAdmission`, the composed API exposes `POST /v1/kc/store`. The route is deliberately absent from hosts that do not enable bootstrap admission; Task 1 bootstrap authentication is not retrofitted onto every low-level KC route.

The request accepts `content`, `project`, `source_type="user_note"`, optional stable `source_id`, and optional timezone-aware `source_event_time`. It requires `X-Knowledge-Key` and `Idempotency-Key`. Successful bootstrap admission maps the request to fixed principal `local_owner`; caller-supplied `X-Knowledge-Caller` cannot replace that principal.

The idempotency key identifies the logical store request. Internally KC composes deterministic ledger operations so the existing one-canonical-revision-per-operation invariant is preserved: source Resource creation when needed, ResourceVersion ingest, then a no-revision governed-admission parent operation for observation/decision evidence. Exact retry converges on the same canonical source/Resource/ResourceVersion/observation/decision evidence; reusing the same logical idempotency key with different content/source/project inputs fails. Derived generation/snapshot identity is not part of the idempotency guarantee and may legitimately advance during recovery or another accepted complete-corpus publication.

Project keys are validated against the durable 255-character storage contract before canonical writes. Updating the same logical direct-note source unions existing project memberships rather than replacing them.

Canonical Resource/ResourceVersion bytes and governed observation/decision evidence settle before derived SR-2 publication is attempted. The note is merged into a complete successor snapshot that preserves unrelated current producers. A serving-predecessor race is retryable and reports `text_state="pending"`; other derived build/invariant failures report `text_state="failed"`. In either case canonical evidence survives and the previous valid generation remains serving.

The store response reports `canonical_state="stored"`, `graph_state="pending"`, exact Resource/ResourceVersion IDs and SHA-256, plus text generation/snapshot state. `text_state="indexed"` describes successful derived publication; after Task 2F, a note included in the accepted current SR-2 generation is also searchable through the accepted lexical read contract. The store response itself does not claim that a particular query was executed.

## Lexical service and consumer contract

The composed [public API](../../../components/knowledge-core/knowledge_core/api/app.py) exposes `POST /v1/retrieval/search` with `query`, `limit` (1–50, default 10) and `include_superseded` (default false). `X-Knowledge-Caller` is required. The trusted host must inject a retrieval Authority evaluator; the header alone is not authorization. Missing caller returns 400, denied retrieval is nondisclosing 404, and unavailable Authority returns 503 before protected search.

PostgreSQL performs lexical matching and deterministic ranking against the current eligible generation. Score is neither truth nor authority. The response carries generation/config and structural/projection profile identities, exact Resource/ResourceVersion references/digests, and `evidence_contract_version="kc-lexical-evidence-v2"`.

For source-neutral V2 SR-2 generations, retrieval reconstructs the complete governing snapshot and validates every `TextGenerationSource` against exact generic observation, decision, snapshot, projection and canonical ResourceVersion evidence before serving any result. Partial/mixed lineage, conflicting snapshots, source-set mismatch or tampered projection evidence fails closed. Matching segment content is then reconstructed from exact canonical artifact byte coordinates and slice SHA-256; parent Resource/ResourceVersion eligibility is rechecked at serve time so restriction/erasure remains dominant even if stale derived rows survive.

Source-neutral segment provenance includes source identity, project memberships, producer metadata, observation/decision digests and times, governing snapshot, projection digest, governance policy/rationale/lifecycle, and exact structural coordinates. Repository fields are nullable compatibility projection only. Direct notes therefore return honest generic provenance with null repository/path/version compatibility fields.

Historical pre-2D SR-2 generations retain explicit `repository-sr2-v1` provenance rather than being relabeled. Current source-neutral generations use `governed-source-sr2-v2`. Existing repository consumers retain the `governed_observation_id` compatibility alias described above, while new generic consumers should use `governed_source_observation_id` when they need the generic observation identity.

KC Consumer V1 exact segment evidence feeds the [Controller Task Packet V1](../../CONTROLLER_TASK_PACKET_V1.md) boundary. Retrieval remains informational and cannot choose providers, authorize tools/files or accept worker results. General context assembly and MindsHub-specific front-door tools remain future work. Repository-shaped ACL evidence compatibility is not authority to force generic KC sources back into repository semantics.

## Graphiti derived projection and trust admission

Graphiti `0.30.2` over FalkorDB uses local model extraction and embeddings. Only eligible current SR-2 sources can enter the plan. Before external calls KC verifies immutable artifact size/digest, strict UTF-8, exact segment bounds/slice digest and lifecycle. Graphiti episode IDs are provider correlation evidence, never canonical KC identity.

Durable attempts bind KC source refs/revisions, current SR-2 generation/profile/config, backend/config identity, namespace/scope and request digest. Each candidate physical partition binds namespace, scope, SR-2 profile, **attempt ID and adapter behavioral digest**. It must be empty before first write. New attempts cannot append to an earlier validated build; exact settled replay does not call the provider again.

Under `governed-document-v1`, deterministic edge resolution consolidates only normalized exact facts with the same partition, endpoints and relation, preserving active contributing source IDs. It does not invoke semantic contradiction judgment or broad invalidation searches. Model-derived retirement fields are cleared before writes; existing retired edges are not revived. KC lifecycle remains authoritative.

Every successful segment needs one exact durable provider-source binding: attempt, canonical ResourceVersion/revision, segment key/slice digest, physical partition and provider episode UUID. Integrity warnings prevent success. Exceptions after opening an attempt are retained as quarantined evidence; ambiguous pending attempts are not automatically rerun.

Provider success remains unvalidated until independent validation. `kc-graphiti-live-validator` version `3`, ruleset `kc-graphiti-governed-document-v3`, requires all seven durable checks:

1. `attempt-contract`
2. `source-binding-contract`
3. `projection-integrity-warnings`
4. `source-episodes-present`
5. `governed-lifecycle-inventory`
6. `namespace-search-isolation`
7. `search-source-attribution`

The complete digest-bound edge inventory must have no retirement or invalid source attribution. Indeterminate/incomplete inspection cannot enter trusted retrieval. A summary claiming validation, an old ruleset or a missing required check is insufficient. Settled exact validation replay preserves evidence; failed or ambiguous evidence is not overwritten into success.

[GraphProjectionRetrievalKnowledgeKernel.search_validated_projection()](../../../components/knowledge-core/knowledge_core/application/graph_retrieval.py) evaluates `retrieval.search_graph` Authority **before** sending the query to any graph/embedder/reranker. Explicit namespace/scope, current generation, exact config, successful disposition and complete matching validation are required. Search stays within each immutable build; every sourcing episode on every accepted hit must map through that build's binding to an eligible exact canonical segment. Unknown, stale, superseded, unattributed or wrong-partition hits are rejected. KC rechecks current generation after external search.

The projection attempt/source-binding/validation ledger is substantially source-neutral and should be preserved. The current projection-plan input and reference-time reconstruction are repository-shaped; Task 4 will generalize those inputs only as required for generic governed SR-2 sources and will qualify mixed-source projection without weakening existing validation. New TEXT generations continue to make earlier graph attempts ineligible unless a future cross-generation reuse contract is separately proven and qualified.

This kernel path is implemented and has bounded host acceptance. The public HTTP retrieval route remains lexical. Neither direct database access nor raw Graphiti access is an accepted substitute for the future governed graph consumer interface.

## Contract maintenance

Preserve the accepted KC-D001–KC-D025 invariants and historical evidence while correcting accidental source-adapter leakage. Record any material superseding decision here, with affected contract, reason and qualification evidence; update current status and operations together. The archive preserves original wording and checkpoint evidence, not a competing instruction set. Scope-specific exclusions from early Kernel/RF/RI slices do not undo later accepted SR-2, source-neutral Task 2, or Graphiti work, and historical acceptance must not be overstated as qualification of later behavior.
