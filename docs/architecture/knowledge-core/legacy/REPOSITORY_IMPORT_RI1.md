# Knowledge Core Repository Import RI-1 — Contract and Falsifiable Acceptance Design

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Phase:** RI-1 repository-import design  
**Original status:** design complete; RI-2 implementation was later completed  
**Starting checkpoint:** `f509de0a22141a252a37a56f52c3a2a5e56faea0`  
**Post-acceptance clarification:** **2026-09-10 — exact-version A→B→A semantics clarified by `KC-D025`; no historical RI-1 evidence is invalidated**

## Post-acceptance exact-version clarification

The original RI-1 shorthand “changed bytes -> new exact `ResourceVersion`” must be read consistently with the already-accepted content-addressed physical identity:

```text
UNIQUE(resource_ref_id, content_digest_algo, content_digest)
```

For one governed logical Resource:

- a **previously unseen exact byte representation** creates a new `ResourceVersion`;
- a later observation whose exact bytes/digest match an **already existing version** reuses that exact `ResourceVersion`;
- therefore A → B → A reuses A's original exact version on the final observation;
- the final A is still a new governed repository observation/import receipt and may produce a new retrieval generation because source commit/path/classification/lifecycle/authority/rationale may have changed;
- physical artifact deduplication still does not merge different logical Resources.

This clarification supersedes any sentence or gate below that could be read as requiring a duplicate exact version merely because an edit event or source commit occurred. It does **not** change stable document-key identity, exact Git verification, manifest chaining, omission safety, retirement behavior, or RI-2's accepted qualification evidence.

For section retrieval, the later audit-amended `SECTION_RETRIEVAL_SR1.md` and `KC-D025` additionally require a retrieval generation to identify the exact governed observation/classification snapshot used for lifecycle/source projection. That later requirement does not retroactively alter what RI-1/RI-2 historically qualified.

## Purpose

RI-1 defines the smallest safe contract for importing an explicitly approved Git repository manifest into Knowledge Core without trusting mutable paths, inferring lifecycle, scanning unapproved repository content, or allowing a partial update to replace the last accepted retrieval generation.

## Design goals

The importer preserves:

1. exact Git source verification before artifact ingest;
2. stable logical document identity across edits/renames/re-observations;
3. distinct logical documents even when bytes are identical;
4. idempotent exact-manifest replay;
5. explicit chained manifest evolution;
6. explicit omission/retirement handling;
7. explicit lifecycle/authority/classification rather than inference;
8. generation publication fencing;
9. service-only credential boundaries;
10. reads limited to explicit approved manifest paths.

## Core identity model

### Repository identity

Each managed repository has an immutable governed `source_repository_key`. Mutable checkout paths, URLs, branches, tags, and display names are locators/observations rather than repository identity.

### Logical document identity

Each managed document has an immutable explicitly assigned `source_document_key`.

```text
(source_repository_key, source_document_key) -> one logical Resource ref
```

Path and content digest do not define logical document identity.

Consequences:

- same document key + previously unseen changed bytes -> same logical Resource, new exact ResourceVersion;
- same document key + bytes matching any prior exact version -> same logical Resource, reuse that exact ResourceVersion;
- same document key + changed path + same bytes -> same Resource/version plus new observed locator;
- same key + changed path + previously unseen bytes -> same Resource, new exact version, continuity rationale required;
- A → B → A -> same Resource; versions A and B remain exact history; final A reuses the original A version and records a new source observation;
- different document keys + identical bytes -> different logical Resources and ResourceVersion identities even if artifact bytes deduplicate physically;
- a true replacement receives a different document key and may explicitly supersede/replace the old key.

## Manifest V2 contract

Manifest-level fields:

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

Rules include:

- `source_commit` is one exact immutable Git commit, never mutable `HEAD`/branch/tag input;
- only the first accepted manifest has null `previous_manifest_digest`;
- later manifests name the exact prior accepted manifest digest;
- first implementation history policy is `retain_prior_versions_as_superseded`;
- entries/retirements are explicit allowlists, not discovery/globs.

Each present entry requires:

```text
source_document_key
path
git_blob_sha
media_type
classification
retrieval_lifecycle
authority_rank
rationale
continuity_rationale       # when path and bytes both change for existing key
supersedes_document_key    # optional distinct logical replacement
```

The path is normalized repository-relative and unique. The object must be a regular Git blob. First implementation supports strict UTF-8 `text/plain` and `text/markdown`. Lifecycle is explicit `current|unknown|superseded`. Authority rank is explicit integer or null. Classification/rationale are explicit review metadata and are not inferred. Duplicate bytes across keys are permitted; duplicate active paths/document keys are not.

Retirement requires:

```text
source_document_key
reason
historical_retrieval       # retain | exclude
replacement_document_key   # optional
```

Retirement is not privacy deletion. `retain` keeps the last accepted exact version in a new generation as historical/superseded material. `exclude` removes it from that generation while canonical history remains.

## Manifest-chain completeness

Every previously managed document key must appear in the next manifest either as a present entry or explicit retirement. Silent omission fails closed. Unlisted repository files are ignored.

## Exact Git source verification

Before canonical/import writes, each present entry verifies:

1. governed repository identity;
2. exact source commit;
3. exact repository-relative path at that commit;
4. accepted regular-blob type/mode;
5. resolved Git blob equals manifest `git_blob_sha`;
6. exact bytes come from the pinned object, not mutable working tree;
7. Git blob identity recomputes from those bytes;
8. strict UTF-8/media constraints;
9. immutable SHA-256 artifact identity independently during ingest.

Any mismatch fails the whole plan before writes.

## Repository source-reader boundary

Repository access is a trusted import dependency. Normal clients cannot choose arbitrary server roots, receive repository credentials, inject shell commands, glob, recursively scan, or auto-add content beyond the approved manifest.

## Persistent import-control state

### Repository document binding

Stores stable:

```text
source_repository_key
source_document_key
resource_ref
```

### Repository source observation

Each accepted present entry records immutable source/classification evidence including:

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

A repeated exact `resource_version_ref` across later observations is valid and expected when exact bytes recur.

### Repository import receipt

Each manifest records chain/repository/commit/status/result-generation identity. Manifest digest uniqueness provides replay identity.

These control records complement canonical ResourceVersion/artifact history and are distinct from derived search rows.

## Planning and apply protocol

Dry-run validates the full manifest/source set and records manifest digest, prior-manifest/current-generation preconditions, exact source proofs, per-document action, exact generation source set, and deterministic plan digest.

Per-document actions include `create_resource`, `reuse_resource`, `create_version`, `reuse_version`, `add_locator`, `classification_only`, and retirement dispositions.

Apply revalidates stale-sensitive state/source proofs. No new text generation becomes current until all manifest entries/retirements settle. Failure before publication leaves prior current retrieval serving; safe append-only residue may be reconciled by exact retry.

## Version and locator behavior

### Unchanged exact observation/replay

Same accepted manifest replays the existing receipt with no new Resource, ResourceVersion, locator, observation, or generation.

### New source observation with unseen content

Same document key and a blob whose exact digest is not already represented for the Resource:

- reuse Resource;
- create one exact ResourceVersion;
- preserve prior versions;
- record new governed observation;
- publish new generation when accepted.

### Re-observation of prior exact content — including A → B → A

If the new source object resolves to bytes already represented by an existing `ResourceVersion` for the same Resource:

- reuse that exact version;
- do not create a duplicate exact version;
- record the new source observation/receipt;
- publish a new generation when governed source/classification state changed or manifest evolution requires it;
- fixed history policy may still retain other exact versions as superseded history.

### Rename/move only

Same key/bytes at new path reuses Resource/version and records the new observed locator/source observation.

### Rename plus previously unseen content

Same key with path and unseen bytes changed preserves Resource identity, requires `continuity_rationale`, creates one exact version, and records locator/observation.

If the changed path points to bytes matching a prior exact version, the prior version is reused while the continuity/source observation remains new.

### Duplicate bytes, different logical documents

Different keys remain different Resources. Each Resource owns its own exact version identity even when content digests match; physical artifact deduplication may occur.

## Classification-only and observation-only changes

Changing lifecycle, authority, classification, rationale, path/source commit, or equivalent governed observation metadata without introducing unseen canonical bytes must not manufacture a new ResourceVersion.

It may require a new observation, receipt, locator, and/or text generation because governed retrieval metadata changed.

## Retrieval-generation construction

Generation sources are selected only from accepted import state: present exact versions, retained prior versions/history, and explicitly retained retirements. Failed/stale manifests and unapproved repository paths never enter a current generation.

Later section-retrieval generations must additionally bind exact governed observation/classification inputs as defined by audit-amended SR-1/KC-D025.

## Falsifiable RI-2 acceptance gates — clarified

Historical RI-2 qualification remains accepted. The gate wording below reflects the content-addressed clarification for future reuse.

### RI2-G1 — bounded manifest schema
Reject duplicate keys/paths, malformed object IDs, unsupported media, missing classification/lifecycle, traversal, unsupported object kinds, globs, and discovery behavior.

### RI2-G2 — verify all sources before writes
One wrong source proof fails the multi-entry plan with zero import writes and no generation replacement.

### RI2-G3 — first-import stable bindings
Two document keys create two stable repository/document-key -> Resource bindings with exact versions/observations.

### RI2-G4 — exact accepted-manifest replay idempotency
Exact replay creates no new Resource, ResourceVersion, locator, observation, or generation.

### RI2-G5 — unseen content update preserves logical identity
Same key/path with a verified content representation not already present for that Resource reuses Resource, creates exactly one new exact ResourceVersion, preserves old versions, and publishes the classified generation.

### RI2-G5A — prior-content re-observation / A → B → A
Same key returning to bytes/digest of an earlier exact version reuses that original ResourceVersion, creates no duplicate version, records the new governed observation/receipt, and publishes a new generation when the manifest/classification state changed.

### RI2-G6 — rename-only preserves exact version
Same key/blob at new path reuses Resource/version and adds the required locator/source observation.

### RI2-G7 — rename-plus-edit continuity
Path plus source-content change requires explicit continuity rationale. Resource identity remains. Exact version creation versus reuse follows content-addressed identity, not the fact that an edit event occurred.

### RI2-G8 — duplicate content does not merge logical identity
Different document keys remain distinct Resources/ResourceVersions despite matching content digests.

### RI2-G9 — classification-only update
Same exact version with changed lifecycle/authority creates no ResourceVersion but creates required new accepted observation/receipt/generation.

### RI2-G10 — omission fails closed
Previously managed key cannot disappear without explicit retirement.

### RI2-G11 — retirement semantics
`retain` remains explicit historical/superseded retrieval; `exclude` removes from the new generation while canonical history remains. Neither is privacy deletion.

### RI2-G12 — manifest-chain stale rejection
Wrong previous digest/current-generation precondition rejects apply.

### RI2-G13 — source changes after plan
Changed exact source evidence rejects apply stale.

### RI2-G14 — failed publication non-serving
Failure before generation settlement leaves prior generation serving; retry reconciles idempotently.

### RI2-G15 — generation isolation
Successful changed manifest serves exactly one new current text generation.

### RI2-G16 — exact provenance
Every hit can trace to exact repository/document/source object, logical Resource, exact ResourceVersion, artifact digest, governed classification observation, and generation.

### RI2-G17 — service-only boundary
Clients need no storage/repository credentials and receive no internals.

### RI2-G18 — no broad scan
Only manifest-listed exact objects are read.

## Controlled fixture clarification

Future import regression coverage should include A → B → A for one document key so the content-addressed reuse rule cannot regress. Existing historical RI-2 acceptance evidence is not relabeled as having tested that later-added case.

## Decisions intentionally deferred

RI-1/RI-2 do not authorize automatic discovery/classification, broad ACL/Vera/RiskCardOCR import, section extraction beyond separately accepted SR-1/SR-2 work, PDF/DOCX/HTML/OCR, embeddings/vector retrieval, RAG, semantic-profile expansion, production Authority, credential/network deployment, cross-repository identity merging, or heuristic document-key assignment.

## Historical completion note

RI-2 was later implemented and accepted. See `REPOSITORY_IMPORT_RI2.md` for its exact historical qualification record. The 2026-09-10 clarification does not claim those older tests covered A → B → A; it records the already-consistent content-addressed identity rule for subsequent work.

## Stop boundary

**RI-1 remains an accepted historical design foundation as clarified above. Section-retrieval work must follow `KC-D025` and audit-amended `SECTION_RETRIEVAL_SR1.md`.**