# Knowledge Core Repository Import RI-1 — Contract and Falsifiable Acceptance Design

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Phase:** RI-1 repository-import design  
**Status:** **design complete; implementation not started**  
**Starting checkpoint:** `f509de0a22141a252a37a56f52c3a2a5e56faea0`

## Purpose

RI-1 defines the smallest safe contract for importing an explicitly approved Git repository manifest into Knowledge Core without trusting mutable paths, inferring lifecycle, scanning unapproved repository content, or allowing a partial update to replace the last accepted retrieval generation.

RI-1 is design and falsification only. It does not implement an importer, persist a production corpus, add chunking/extraction, or broaden the approved corpus.

## Design goals

A later implementation must preserve these properties:

1. exact Git source identity is verified before artifact ingest;
2. logical document identity survives content edits and renames;
3. two different documents remain distinct even when their bytes are identical;
4. unchanged manifest replay is idempotent;
5. manifest evolution is explicit and chained to the last accepted manifest;
6. omission never silently means retirement, deletion, or supersession;
7. lifecycle and authority metadata are supplied explicitly rather than inferred;
8. a failed/stale import cannot replace the last current retrieval generation;
9. normal clients never receive database, artifact-store, or repository credentials;
10. the importer reads only paths explicitly present in the approved manifest.

## Core identity model

### Repository identity

Each managed repository receives an immutable, governed `source_repository_key` in import configuration/manifest state. It is an opaque stable identifier for import continuity and must not be derived automatically from a mutable checkout path, remote URL, branch name, or display name.

Observed repository locators may change without changing `source_repository_key`.

### Logical document identity

Every managed document receives an immutable, explicitly assigned `source_document_key`.

The stable Knowledge Core binding is:

```text
(source_repository_key, source_document_key) -> one logical Resource ref
```

`source_document_key` is never generated from file path or content digest. It may be a UUID or another governed opaque identifier; the importer treats it as identity, not as a filename.

Consequences:

- same document key + changed bytes -> same logical `Resource`, new exact `ResourceVersion`;
- same document key + changed path + same bytes -> same logical `Resource`, same exact `ResourceVersion`, new observed path locator;
- same document key + changed path + changed bytes -> same logical `Resource`, new exact `ResourceVersion`; the changed manifest must carry an explicit continuity rationale because both observable anchors changed;
- different document keys + identical bytes -> different logical `Resource` refs; immutable artifact bytes may deduplicate physically by content hash without merging logical identity;
- a true replacement by a different logical document receives a new document key and may explicitly name the old key as superseded/replaced. It must not steal the old key.

Path is a locator. Blob identity is version evidence. Neither is logical identity.

## Manifest V2 contract

A later RI implementation should accept only an explicit schema-versioned manifest. The exact serialization may evolve during implementation, but the following semantic fields are mandatory.

### Manifest-level fields

```text
schema_version
manifest_id
source_repository_key
repository_locator
source_commit
previous_manifest_digest
history_policy
entries[]
retirements[]
```

Rules:

- `source_commit` is an exact immutable Git commit object ID, never a branch/tag such as `main`, `HEAD`, or `architecture/knowledge-core`;
- `previous_manifest_digest` is null only for the first accepted manifest for a repository key;
- every later manifest must name the exact SHA-256 canonical digest of the previously accepted manifest;
- `history_policy` for the first implementation is fixed to `retain_prior_versions_as_superseded` so exact prior versions remain historically retrievable unless an explicit retirement says otherwise;
- arrays are explicit allowlists, not discovery requests or glob patterns.

### Present-entry fields

Each `entries[]` item requires:

```text
source_document_key
path
git_blob_sha
media_type
classification
retrieval_lifecycle
authority_rank
rationale
continuity_rationale   # required when both path and bytes change for an existing key
supersedes_document_key # optional; only for a distinct logical replacement
```

Rules:

- path is repository-relative, normalized, non-empty, and unique among present entries;
- document key is unique within the manifest;
- Git object at exact `source_commit:path` must be a regular blob, not a tree, symlink, or submodule;
- first implementation accepts only strict UTF-8 `text/plain` and `text/markdown`, matching RF-2;
- `retrieval_lifecycle` is explicitly one of `current`, `unknown`, or `superseded`;
- `authority_rank` is explicitly supplied as an integer or explicit null; null remains a deliberate "unspecified" value and ranks after numeric authority under RF-2;
- classification/rationale are required review metadata and are never inferred from path, recency, keywords, or Git history;
- duplicate content digests across different keys are permitted;
- duplicate active paths or duplicate document keys are rejected.

### Retirement fields

Every `retirements[]` item requires:

```text
source_document_key
reason
historical_retrieval   # retain | exclude
replacement_document_key # optional
```

A retirement means the source is no longer part of the current managed set. It is not privacy deletion or canonical erasure.

- `retain` keeps the last accepted exact version in the new retrieval generation as `superseded` historical material;
- `exclude` removes the document from the new retrieval generation but leaves canonical Resource/ResourceVersion/import history intact;
- privacy restriction/erasure continues to use the existing privileged deletion lifecycle and is outside RI-1.

## Manifest-chain completeness rule

For every previously managed `source_document_key`, the next manifest must contain exactly one of:

1. a present entry for the same key; or
2. an explicit retirement for that key.

Silent omission is invalid.

This rule is checked against the previously accepted manifest/import state. It does not require scanning the repository for extra files. New repository files that are not listed in the manifest are ignored and cannot be ingested.

## Exact Git source verification

All source verification completes before any canonical/resource write begins.

For each present entry, the source reader must verify:

1. configured repository identity matches `source_repository_key`;
2. exact `source_commit` exists and is immutable input;
3. exact repository-relative `path` exists at that commit;
4. object mode/type is an accepted regular blob;
5. resolved Git blob object ID equals manifest `git_blob_sha`;
6. exact blob bytes are read from that commit/object, not from the mutable working tree;
7. Git blob identity recomputed from those bytes matches `git_blob_sha`;
8. bytes satisfy strict UTF-8 and declared RF-2-supported media type;
9. immutable artifact SHA-256 is computed independently by the existing artifact store during ingest.

A mismatch anywhere fails the entire plan before writes.

The importer must not substitute current working-tree bytes for bytes from the pinned commit. The real-corpus replay-fence failure demonstrated why this is mandatory.

## Repository source-reader boundary

Repository access is a trusted import dependency, not a capability granted to ordinary retrieval clients.

A later implementation should expose a narrow `RepositorySourceReader`-style application interface that can resolve only the exact repository/commit/path objects supplied by an approved manifest. The first implementation may use a local read-only Git adapter or a deterministic test adapter, but:

- clients cannot supply arbitrary server filesystem roots;
- repository credentials/access remain outside API responses and Knowledge Core document content;
- manifest strings must never become unquoted shell commands;
- the adapter cannot glob, recursively scan, or auto-add files outside the manifest.

## Persistent import-control state

RI-1 selects the need for three durable control concepts. Exact table names are implementation details, but their semantics are required.

### Repository document binding

An immutable mapping stores:

```text
source_repository_key
source_document_key
resource_ref
created/import revision metadata
```

This mapping is the authority for reuse of logical `Resource` identity on later manifests.

### Repository source observation

Each accepted present entry records immutable source evidence sufficient to reconstruct import lineage:

```text
manifest_digest
source_repository_key
source_document_key
source_commit
path
git_blob_sha
resource_version_ref
classification
retrieval_lifecycle
authority_rank
```

This complements canonical ResourceVersion/artifact/locator history; it does not replace them.

### Repository import receipt

Each accepted manifest has an immutable receipt containing at least:

```text
manifest_digest
previous_manifest_digest
source_repository_key
source_commit
status
resulting_text_generation_id
settled revision/time
```

Manifest digest uniqueness provides stable replay identity.

These records belong in control/import state, not in the RF-2 search projection. Derived search rows remain rebuildable.

## Planning and apply protocol

### Plan phase

A dry-run validates the entire manifest and source set without canonical or derived writes and produces a deterministic `ImportPlan`.

The plan records:

- canonical manifest SHA-256 digest;
- expected previous accepted manifest digest;
- expected current text generation identity/high-water precondition;
- exact source proofs for each present entry;
- per-document action: `create_resource`, `reuse_resource`, `create_version`, `reuse_version`, `add_locator`, `classification_only`, or retirement disposition;
- exact new generation source set, including retained historical versions;
- a deterministic plan digest.

Dry-run cannot mutate Knowledge Core.

### Apply phase

Apply accepts the exact approved plan/manifest identity and revalidates all stale-sensitive preconditions, including source objects.

If manifest state, repository source proof, document binding, or current-generation precondition changed after planning, apply fails stale and requires a new plan.

Canonical resource/version ingestion may be append-only internally, but **no new text generation becomes current until every manifest entry and retirement has settled successfully**.

If apply fails before publication:

- the previously current text generation remains current and serving;
- any safely committed append-only resource/version rows are non-serving import residue until a later idempotent retry/reconciliation uses the same exact manifest identity;
- no partial manifest is represented as accepted.

The import receipt becomes settled only after the new generation is current.

## Version and locator behavior

### Unchanged document

Same key, path, and blob:

- reuse logical Resource;
- reuse exact ResourceVersion;
- no duplicate locator;
- no new canonical document content;
- unchanged full-manifest replay returns the accepted receipt and does not create a new text generation.

### Content edit

Same key/path, new verified blob:

- reuse logical Resource;
- create one new ResourceVersion from exact bytes;
- prior accepted versions remain canonical;
- under the fixed RI first-implementation history policy, prior indexed versions enter the new generation as `superseded` historical sources;
- new exact version receives the manifest's explicit lifecycle/authority/classification.

### Rename/move only

Same key/blob, new path:

- reuse logical Resource and exact ResourceVersion;
- record a new observed path locator tied to the source observation;
- do not create a fake content version solely because the filename changed.

### Rename plus content edit

Same key with both path and blob changed:

- preserve Resource identity because the governed key is unchanged;
- require explicit `continuity_rationale` in the changed manifest;
- create one new ResourceVersion and locator observation.

### Duplicate bytes, different logical documents

Different keys with same blob bytes:

- create/reuse separate logical Resources by their bindings;
- each has its own exact ResourceVersion identity/provenance;
- artifact-store physical deduplication is allowed;
- importer must never merge the logical resources based on hash equality.

### Distinct replacement

A genuinely new document replacing another gets a new key. The old key is explicitly retired or made superseded, and the new entry may reference it through `supersedes_document_key`/replacement metadata. Replacement does not create identity equivalence.

## Classification-only changes

Changing lifecycle, authority rank, classification, rationale, or historical-retention disposition without changing bytes must not create a ResourceVersion.

It does require a new import receipt and new text generation because derived retrieval metadata changed.

The previous generation remains immutable/historical; ordinary search serves only the newly current generation.

## Retrieval-generation construction

The new generation source set is constructed only from accepted import state:

- current manifest present versions;
- prior exact versions retained by the fixed history policy, classified `superseded`;
- explicitly retained retired documents, classified `superseded`;
- never an unapproved repository path;
- never a version from a failed/stale manifest.

Generation replacement uses the existing RF-2 generation fence. A late/failed builder cannot supersede the accepted current generation.

## Service and credential boundary

Normal API consumers remain service-only.

A future import API/CLI may expose plan/apply/status operations, but it must not expose:

- PostgreSQL URL/credentials;
- artifact backend paths/keys;
- repository credentials/tokens;
- arbitrary server filesystem paths;
- raw SQL or generic database access.

Import capability does not grant retrieval results execution authority. Knowledge remains separate from Authority and Execution.

## Falsifiable RI-2 acceptance gates

A later RI-2 implementation is not accepted until controlled fixtures prove all gates below.

### RI2-G1 — bounded manifest schema
Reject duplicate keys, duplicate present paths, malformed exact commit/blob IDs, unsupported media, missing classification/lifecycle fields, path traversal, symlink/submodule/tree entries, globs, and unapproved discovery behavior.

### RI2-G2 — verify all sources before writes
One wrong blob/path/commit in a multi-entry manifest causes zero import writes and leaves the existing current generation unchanged.

### RI2-G3 — first-import stable bindings
Two approved documents create two stable `(repository key, document key) -> Resource` bindings with exact versions and source observations.

### RI2-G4 — identical replay idempotency
Applying the exact same accepted manifest again returns/reuses the prior receipt; no new Resource, ResourceVersion, locator, source observation, or text generation is created.

### RI2-G5 — content update preserves logical identity
Same key/path with new exact blob reuses Resource, creates exactly one ResourceVersion, preserves old version, and publishes a generation containing the new classified version plus retained old superseded history.

### RI2-G6 — rename-only preserves exact version
Same key/blob at a new path reuses Resource and ResourceVersion and adds only the new locator/source observation required by the move.

### RI2-G7 — rename-plus-edit requires explicit continuity
Same key with path and blob both changed fails without continuity rationale; succeeds with it, preserving Resource and creating one new version.

### RI2-G8 — duplicate content does not merge identity
Two different document keys with identical bytes produce distinct Resource/ResourceVersion identities while content digests may match.

### RI2-G9 — classification-only update
Same bytes with changed lifecycle/authority creates no ResourceVersion but creates a new accepted manifest receipt and new text generation with the new metadata.

### RI2-G10 — omission fails closed
A changed manifest that simply omits a previously managed key is rejected. Explicit retirement succeeds.

### RI2-G11 — retirement semantics
`retain` removes the document from ordinary current retrieval but keeps its last exact version historical/superseded. `exclude` removes it from the new generation while canonical history remains. Neither invokes privacy deletion.

### RI2-G12 — manifest-chain stale rejection
Wrong `previous_manifest_digest` or a stale current-generation precondition rejects apply without replacing the current generation.

### RI2-G13 — source changes after plan
If exact repository object/path/blob evidence no longer matches the approved plan at apply time, apply fails stale; no new generation is published.

### RI2-G14 — failed publication is non-serving
Inject failure after some append-only canonical ingestion but before generation settlement. Previous generation remains current; no partial source set is served; exact-manifest retry reconciles idempotently.

### RI2-G15 — generation isolation
After a successful changed manifest, normal retrieval uses exactly one newly current text generation. No old/current generation rows are mixed.

### RI2-G16 — exact provenance
Every returned hit can be traced through import observation to exact repository key, document key, source commit, path, Git blob, logical Resource, exact ResourceVersion, SHA-256 artifact digest, classification and generation.

### RI2-G17 — service-only boundary
A simulated client can plan/apply/query through approved service interfaces without database/artifact credentials, and API/open-schema responses do not disclose those internals or repository credentials.

### RI2-G18 — no broad scan
Instrument the source reader. A manifest containing N approved present paths causes reads only for the exact commit and those N paths/objects; unrelated repository paths are never enumerated or opened.

## Controlled fixture matrix

RI-2 should use a synthetic Git repository plus one tiny real-repository fixture, not a broad ACL import.

The synthetic history should include:

- commit A: `alpha.md`, `beta.md`, and an unapproved `secret.md`;
- `alpha.md` and `beta.md` initially different;
- an additional document key with bytes identical to `alpha.md`;
- commit B: edit `alpha.md` only;
- commit C: rename `beta.md` without changing bytes;
- commit D: rename and edit `alpha.md`;
- a symlink/submodule-style rejected path fixture where platform/tooling permits;
- a bad manifest with one incorrect blob SHA;
- a manifest that omits a previously managed key;
- explicit retain and exclude retirements;
- classification-only manifest revision.

Predeclare expected Resource/ResourceVersion/generation identity outcomes before implementation.

The tiny real fixture should contain only a handful of explicitly pinned Markdown/text files and should validate exact Git provenance and retrieval behavior. Do not reuse a mutable checkout while pretending it is an older commit; read exact Git objects.

## Decisions intentionally deferred

RI-1 does not decide or implement:

- automatic repository discovery/classification;
- broad ACL/Vera/RiskCardOCR import;
- chunking/section extraction;
- PDF/DOCX/HTML/OCR pipelines;
- embeddings/vector retrieval;
- LLM summaries/RAG/context assembly;
- semantic-profile expansion;
- production authorization service;
- production repository credential provisioning/network deployment;
- cross-repository identity merging;
- automatic document-key assignment or heuristic rename detection.

If document identity is uncertain, import must stop for explicit classification rather than guess.

## Next separately authorized task

### RI-2 — minimal repository import implementation and controlled fixtures

RI-2 may implement only the smallest code/schema/source-reader/test slice necessary to satisfy RI2-G1 through RI2-G18 against synthetic and tiny-real fixtures.

It must not perform a broad production import or add chunking, embeddings, RAG, semantic expansion, Authority, or execution work.

## Stop boundary

**RI-1 design is complete when this contract is checkpointed. Do not begin RI-2 implementation without separate authorization.**
