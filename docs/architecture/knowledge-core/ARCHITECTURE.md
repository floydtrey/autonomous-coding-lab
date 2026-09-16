# Knowledge Core — Architecture and Contracts

**Authoritative current KC invariants.** Read [CURRENT_STATE.md](CURRENT_STATE.md) for implementation/acceptance status and [OPERATIONS.md](OPERATIONS.md) for evidence and operating procedures. Historical documents under `legacy/` preserve their original scope and evidence; they do not supersede this current contract.

## Ownership and trust

Knowledge Core is a standalone semantic service. PostgreSQL is canonical; immutable artifacts carry exact source bytes; lexical indexes, Graphiti/FalkorDB state, embeddings, summaries, caches and other retrieval projections are derived and rebuildable.

```text
Mason / MindsHub (accepted local consumer)    ACL Controller / Worker Lab    Vera (future)
                    \                                  |                    /
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

The 2026-09-14 Task 2 source-model audit found that the canonical Resource/ResourceVersion/artifact foundation was largely source-neutral while governed retrieval had repository/Git assumptions below the adapter boundary. Tasks 2A–2F implement and qualify the correction through governed evidence, complete SR-2 selection/lineage/publication, authenticated direct-note storage, and source-neutral lexical serving/evidence.

Historical repository/SR-2/Graphiti qualifications retain their exact original scope and must not be relabeled as qualification of later behavior. Task 4 subsequently adds a source-neutral graph-plan path for generic governed SR-2 sources while preserving historical repository-shaped Graphiti evidence under its original semantics. Some downstream ACL compatibility schemas remain separate bounded work and do not redefine generic KC source identity.

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

## Lexical service and Usable V1 consumer-read contract

The composed [public API](../../../components/knowledge-core/knowledge_core/api/app.py) retains `POST /v1/retrieval/search` as the Authority-first semantic search route. It accepts `query`, `limit` (1–50, default 10) and `include_superseded` (default false). `X-Knowledge-Caller` is required and the trusted host must inject a retrieval Authority evaluator; the header alone is not authorization. Missing caller returns 400, denied retrieval is nondisclosing 404, and unavailable Authority returns 503 before protected search.

PostgreSQL performs lexical matching and deterministic ranking against the current eligible generation. Score is neither truth nor authority. The response carries generation/config and structural/projection profile identities, exact Resource/ResourceVersion references/digests, and `evidence_contract_version="kc-lexical-evidence-v2"`.

For source-neutral V2 SR-2 generations, retrieval reconstructs the complete governing snapshot and validates every `TextGenerationSource` against exact generic observation, decision, snapshot, projection and canonical ResourceVersion evidence before serving any result. Partial/mixed lineage, conflicting snapshots, source-set mismatch or tampered projection evidence fails closed. Matching segment content is then reconstructed from exact canonical artifact byte coordinates and slice SHA-256; parent Resource/ResourceVersion eligibility is rechecked at serve time so restriction/erasure remains dominant even if stale derived rows survive.

Source-neutral segment provenance includes source identity, project memberships, producer metadata, observation/decision digests and times, governing snapshot, projection digest, governance policy/rationale/lifecycle, and exact structural coordinates. Repository fields are nullable compatibility projection only. Direct notes therefore return honest generic provenance with null repository/path/version compatibility fields.

Historical pre-2D SR-2 generations retain explicit `repository-sr2-v1` provenance rather than being relabeled. Current source-neutral generations use `governed-source-sr2-v2`. Existing repository consumers retain the `governed_observation_id` compatibility alias described above, while new generic consumers should use `governed_source_observation_id` when they need the generic observation identity.

Task 3 adds the bounded local Usable V1 front door only when the trusted host explicitly supplies `BootstrapAdmission`:

- `POST /v1/kc/search` requires `X-Knowledge-Key`, admits operation `kc.search`, maps success to fixed principal `local_owner`, and preserves the accepted lexical request/evidence path. Tasks 6B–6D extend its response additively with `kc-unified-retrieval-evidence-v1`: lexical fields remain top-level and an optional separately stateful graph lane/warnings are added behind the KC coordinator. No graph binding produces lexical evidence plus `graph.state="disabled"`; it does not create or synchronize a graph. If the host also supplies the separate lexical retrieval Authority evaluator, that evaluator remains an additional fail-closed policy layer before lexical search.
- `POST /v1/kc/get-source` requires `X-Knowledge-Key`, admits `kc.get_source`, and accepts an exact `resource_version_ref`. It serves only a ResourceVersion referenced by the current TEXT generation and still serving-eligible. For SR-2 it first revalidates the current generation/profile and generic-or-legacy lineage mode, then reads the full immutable artifact, verifies stored byte size and SHA-256, requires strict UTF-8, and returns the exact canonical source bytes as text. Unknown, non-current or restricted refs are nondisclosing 404. Artifact keys/backends, filesystem paths, database URLs and raw SQL do not cross this contract.
- `GET /v1/kc/status` requires `X-Knowledge-Key`, admits `kc.status`, and preserves the accepted canonical/text fields: canonical revision, text state (`empty` or `ready`), current text generation/source revision highwater/source count, retrieval mode, lineage mode, evidence-contract version and generation-config digest. Task 6F adds a bounded `graph` object using `disabled`, `no_build`, `ready`, `stale`, `pending`, `unvalidated`, `failed`, or `unavailable`. Without a graph binding the state is `disabled`. With a binding, the status classifier inspects only KC's durable projection/validation ledger, the current TEXT generation/profile, and the adapter descriptor/current validation requirement. It exposes at most one representative attempt ID. It does not query Graphiti/FalkorDB for facts, call graph search/projection, launch embeddings/reranking/models, or start synchronization/background work. `ready` means KC has current-compatible durably validated build evidence; it is not a provider-liveness claim or Task 4 intended-host acceptance.

These bootstrap read routes are absent when bootstrap admission is not configured. Operation admission remains independently scoped, so a contract allowing only status cannot search or fetch source. Task 3 does not make arbitrary historical ResourceVersions addressable, weaken privacy fences, expose a generic CRUD API, or replace the separate Authority architecture.

KC Consumer V1 exact segment evidence feeds the [Controller Task Packet V1](../../CONTROLLER_TASK_PACKET_V1.md) boundary. Retrieval remains informational and cannot choose providers, authorize tools/files or accept worker results.

## Mason / MindsHub consumer contract — Task 5 accepted

Mason is an accepted local KC consumer through the project-local bounded bridge. The bridge exposes only the literal operations `kc_status`, `kc_search`, `kc_get_source`, and `kc_store`; unsupported aliases or operation names fail closed.

The bridge is loopback-only for the accepted V1 path and does not expose SQL, artifact-store authority, FalkorDB/Graphiti mutation, arbitrary HTTP, or arbitrary KC access. Mason follows retrieval results through `kc_get_source` when exact canonical source content is required.

Task 5 acceptance qualifies explicit Mason -> KC canonical/lexical use. Tasks 6B–6D add a compatible unified `kc_search` response behind that same literal operation; Task 6E qualifies Mason's procedural interpretation of that additive graph lane; Task 6F adds bounded graph readiness/freshness through the same existing `kc_status` operation. None of this gives Mason direct graph-maintenance authority or qualifies source-neutral Graphiti runtime readiness.

## Graphiti derived projection and trust admission

Graphiti `0.30.2` over FalkorDB uses local model extraction and embeddings. Graph state is derived and rebuildable; canonical Resource/ResourceVersion evidence and valid text retrieval do not depend on graph success.

The historical accepted `governed-document-v1` path remains valid only for its exact repository-shaped qualification. Durable attempts bind KC source refs/revisions, SR-2 generation/profile/config, backend/config identity, namespace/scope and request digest. Candidate physical partitions bind namespace, scope, profile, attempt ID and adapter behavioral digest. Provider success remains insufficient until independent validation succeeds.

Every successful segment requires exact durable provider-source correlation. Integrity warnings prevent success. Exceptions after opening an attempt are retained as failure/quarantine evidence; ambiguous pending attempts are not silently rerun. Independent validation checks attempt contract, source bindings, integrity warnings, episode presence, lifecycle inventory, namespace isolation and source attribution before a build is trusted.

Authority is evaluated before protected graph search. Explicit namespace/scope, compatible current generation/profile/config, successful disposition and complete matching validation are required. Every accepted hit must resolve through the build's source bindings to eligible exact canonical evidence; stale, superseded, unattributed or wrong-partition hits are rejected.

### Task 4 source-neutral graph path

Task 4 adds `kc-source-neutral-graph-plan-v1` above the accepted source-neutral SR-2 evidence model rather than relabeling historical repository-shaped attempts.

For generic current SR-2 sources the graph plan carries:

- exact ResourceVersion and canonical revision;
- segment key/ordinal/coordinates/source-slice SHA-256/body;
- generic source identity and project memberships;
- governed observation and decision IDs/digests;
- governing snapshot and projection digests;
- producer identity/version and distinct source times;
- nullable repository compatibility only when exact legacy mapping exists.

The reference-time policy is `source-event-then-revision-then-observed-v1`. The graph projection profile digest binds this policy, the source-neutral graph-plan version and current TEXT generation config so semantic behavior cannot silently reuse an incompatible validated build.

`SourceNeutralGraphProjectionKnowledgeKernel.sync_current_sr2_projection()` is an explicit bounded operator/application boundary. It is not called by `kc_store`, and current design deliberately does not add a scheduler, continuous graph queue, automatic model launch or cross-generation graph reuse.

Task 4.1 hardens the intended local Graphiti/Falkor runtime by serializing KC-visible Falkor access, forcing bounded Graphiti concurrency, disabling telemetry for the qualified profile and explicitly closing async clients used by the one-shot operator path.

**Qualification status:** implementation and deterministic CI qualification are merged. Historical repository-shaped graph acceptance remains valid. Live intended-host acceptance of the new source-neutral mixed-source path is still pending and must not be inferred from Tasks 6B–6F consumer/status qualification or from Task 5 Mason acceptance.

## Unified retrieval and graph status integration — Tasks 6B–6F accepted

The existing Mason operation `kc_search` is the consumer surface for unified retrieval. Graph augmentation remains behind the KC service boundary rather than exposing Graphiti directly to Mason. The existing `kc_status` operation separately reports bounded durable graph-build readiness without querying the provider.

The accepted additive search contract is `kc-unified-retrieval-evidence-v1`. The live bootstrap `POST /v1/kc/search` keeps every existing lexical `RetrievalSearchResponse` field at top level under its existing `kc-lexical-evidence-v2` meaning, then adds a separate `graph` evidence lane and bounded `warnings`.

```text
kc_search
  -> lexical/current canonical evidence      (required baseline)
  -> validated compatible graph evidence     (optional augmentation)
```

The graph lane has public states `disabled`, `no_build`, `ready`, `stale`, `pending`, `unvalidated`, `failed`, and `unavailable`. Only `ready` may expose graph facts. Ready search evidence must identify explicit namespace/scope, at least one validated attempt and the exact same TEXT generation represented by the lexical lane. Every non-ready search state exposes zero graph results and requires a bounded reason code plus corresponding warning.

Lexical retrieval executes first. Graph failure cannot turn an otherwise-valid lexical result into failure. Historical `include_superseded=True` search remains lexical-only because the accepted graph path is current-only. A graph generation mismatch degrades to `stale`; lack of a compatible validated attempt or graph Authority/provider/integrity failure degrades nondisclosingly rather than exposing untrusted facts.

Graph authorization details are not a public state. Graph denial or provider/runtime unavailability may collapse into nondisclosing `unavailable`; this does not bypass or weaken independent lexical authorization. A separately configured lexical retrieval Authority evaluator remains a fail-closed pre-check before bootstrap lexical search.

Every graph fact retains exact ResourceVersion/segment/source-identity/observation/decision/snapshot/projection correlation. Full canonical source content is intentionally not duplicated into graph correlation output; consumers follow the returned `resource_version_ref` through `kc_get_source` when exact source content is needed.

The optional trusted-host graph binding must use the same bootstrap principal `local_owner`; application composition rejects a binding that substitutes another caller identity. Supplying a graph binding does not build, synchronize, or launch Graphiti or any model/provider.

`kc_status.graph` uses the same bounded state vocabulary but is not a fact-retrieval response. It inspects KC's durable attempt/validation evidence against the current source-neutral graph profile and injected adapter descriptor. `ready` requires a succeeded, validated, current-compatible attempt that satisfies the adapter's current independent validation requirement when present. A usable ready build takes precedence over simultaneous pending/failed attempts. If no ready build exists, current-compatible pending, unvalidated, or failed evidence is reported distinctly; incompatible historical build evidence is `stale`; no durable build is `no_build`. An inspection fault degrades graph status to nondisclosing `unavailable` while canonical/text readiness remains available. Status exposes at most one representative attempt ID and performs no provider search/projection, embedding/reranking, model launch, sync, or background work.

Lexical and graph scores are not interchangeable. The accepted contract defines no synthetic combined score and no graph score field. A future fusion/reranking policy would require a separately versioned contract and qualification.

Tasks 6B–6D qualify the search contract, coordinator, and bootstrap endpoint integration; Task 6E qualifies Mason interpretation of the additive search response; Task 6F qualifies the bounded graph readiness/freshness status surface. They do **not** qualify the pending Task 4 intended-host source-neutral Graphiti/FalkorDB/local-model build or current provider liveness.

## Contract maintenance

Preserve the accepted KC-D001–KC-D025 invariants and historical evidence while correcting accidental source-adapter leakage. Record any material superseding decision here, with affected contract, reason and qualification evidence; update current status and operations together. The archive preserves original wording and checkpoint evidence, not a competing instruction set. Scope-specific exclusions from early Kernel/RF/RI slices do not undo later accepted SR-2, source-neutral Task 2, Task 3 read-surface, Task 4 implementation/hardening, Task 5 Mason work or Tasks 6B–6F unified retrieval/status work, and historical acceptance must not be overstated as qualification of later behavior.