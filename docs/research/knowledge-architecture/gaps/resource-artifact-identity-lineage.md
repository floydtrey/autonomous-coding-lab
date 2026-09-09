# Resource / Artifact Identity and Lineage Gap Research

**Campaign:** Knowledge Architecture Evidence Campaign  
**Task:** KA-G5 — Resource / Artifact Identity and Lineage  
**Research date:** 2026-09-08  
**Starting ACL checkpoint:** `3c82cc60189a640020d1c63c1c7516cc40f34534`  
**Boundary:** research/requirements evidence only; no storage-engine, object-store, database, URI scheme, CAS implementation, or ACL/Vera implementation decision

---

# Executive assessment

KA-G5 closes the direct resource/artifact gap left by the earlier project and standards work.

The strongest result is that a general ACL/Vera knowledge substrate must keep at least these concepts distinct:

1. **logical resource identity** — the durable thing/concept being referred to;
2. **locator/address/reference** — where or how a resource can currently be reached;
3. **representation** — one concrete transferable encoding/view of resource state;
4. **immutable observed version/content identity** — the exact bytes/object/snapshot actually consumed;
5. **mutable alias/reference** — a name such as a branch, tag-like alias, path, URL, latest pointer, or mutable external record that may later resolve differently;
6. **derived artifact identity** — extraction, chunk, normalized copy, summary, embedding, index entry, or other output produced from a source artifact/version;
7. **provenance context** — origin, visit, path, representation profile, transform/run, and other context required to explain how the observed artifact was obtained.

A single `url`, `path`, `filename`, `etag`, `hash`, or `resource_id` field cannot safely carry all of those meanings.

This task does **not** select HTTP, Git, OCI, SWHID, content-addressable storage, RDF, object storage, SQL, graph storage, or any other implementation technology. The standards and systems are used only as independent evidence for identity/lineage requirements.

---

# Scope

KA-G5 covered:

- logical resource identity;
- URI/locator/address identity;
- resource versus representation semantics;
- mutable versus immutable references;
- digest/content identity;
- representation validators and revision checks;
- content-addressed object identity;
- source artifact versus derived artifact identity;
- software snapshot/revision/content distinctions;
- origin/context qualifiers;
- conditional mutation and lost-update prevention;
- lineage from exact consumed version to derived output;
- implications for future retrieval/context construction.

Explicitly excluded:

- privacy erasure/retention mechanics;
- legal records-retention policy;
- final canonical schema;
- final URI or identifier scheme;
- final hash algorithm;
- final content-addressable store;
- Git/OCI/SWHID adoption decisions;
- object-store selection;
- database selection;
- retrieval implementation;
- embeddings implementation;
- Home Assistant/Matter domain validation;
- hostile-scenario execution;
- physical implementation.

---

# Primary evidence

## RFC 3986 — Uniform Resource Identifier Generic Syntax

https://www.rfc-editor.org/rfc/rfc3986.html

Used for:

- broad definition of a resource;
- identifier versus access distinction;
- URI as a means to distinguish a resource within a scope;
- identifiers not necessarily defining intrinsic identity;
- resources not necessarily being network-accessible;
- fragment identifiers referring to secondary resources without implying retrieval.

## RFC 9110 — HTTP Semantics

https://www.rfc-editor.org/rfc/rfc9110.html

Used for:

- resource versus representation distinction;
- multiple representations of one resource;
- representation metadata;
- ETag as an opaque validator for selected representations;
- Content-Location versus target resource identity;
- specific-representation identification;
- If-Match / precondition use for lost-update avoidance;
- representation state versus target resource semantics.

## Git object model

https://git-scm.com/book/en/v2/Git-Internals-Git-Objects.html

Used for:

- content-addressable object identity;
- blobs versus trees versus commits;
- immutable object graph relationships;
- commit identity including tree, parents and metadata rather than file bytes alone;
- distinction between content objects and higher-level snapshot/history objects.

## OCI Image Specification — Content Descriptors

https://github.com/opencontainers/image-spec/blob/main/descriptor.md

Used for:

- digest-based content identity;
- media type and byte size as independent descriptor fields;
- one content object potentially reachable from multiple URLs;
- retrieved content verification against digest/size;
- Merkle-DAG artifact composition;
- distinction between locator list and content identifier.

## Software Heritage persistent identifiers (SWHID)

https://docs.softwareheritage.org/devel/swh-model/persistent-identifiers.html  
https://www.softwareheritage.org/2025/06/13/software-hash-identifier-swhid-tutorial/

Used for:

- intrinsic identifiers for contents/directories/revisions/releases/snapshots;
- typed object identity;
- Merkle-DAG structure;
- separation of intrinsic identifier from origin/visit/anchor/path/line context;
- path/subpart context as qualifier rather than intrinsic content identity;
- stable historical references even when origins evolve.

---

# Highest-value findings

## 1. Resource identity is not its locator

RFC 3986 and HTTP independently support a distinction between the resource being identified and the mechanism/address used to refer to or retrieve it.

A URL/path/location can change while the intended logical resource remains the same.

Conversely, one stable locator can expose different representations or states over time.

Architecture consequence:

> ACL/Vera must not use locator equality as universal resource-identity equality.

## 2. Resource and representation are different

HTTP explicitly separates a resource from representations that reflect a past, current or desired state of that resource.

One resource can legitimately have:

- multiple formats;
- multiple negotiated representations;
- multiple historical states;
- a mutable current representation.

Therefore a downloaded PDF, JSON payload, HTML page, thumbnail, rendered view and source document may be representations/derivatives related to one logical resource without being the same artifact object.

## 3. Representation validators are not universal resource IDs

HTTP ETags identify/validate selected representations according to origin-server semantics.

They are useful for:

- change detection;
- cache validation;
- conditional updates;
- lost-update prevention.

But they are not automatically:

- global content hashes;
- stable logical-resource identifiers;
- provenance-complete version IDs;
- cross-origin identity proofs.

Architecture consequence:

> Store validator type/scope alongside its value; never infer stronger identity semantics than the producer guarantees.

## 4. Content identity and retrieval location are separable

OCI descriptors make this explicit:

- `digest` identifies targeted content;
- `mediaType` describes its type;
- `size` describes expected bytes;
- `urls` are optional locations from which the same content may be retrieved.

This is a direct positive model for separating immutable observed content identity from mutable/multiple locators.

## 5. A content hash identifies bytes/object semantics, not every higher-level resource concept

Git provides concrete evidence:

- a blob identifies file content;
- a tree identifies directory structure plus names/modes/object links;
- a commit identifies a snapshot plus parent/history and author/committer metadata.

Identical file bytes can therefore occur in different paths, trees, commits, repositories or logical documents.

Architecture consequence:

> A digest can establish content equality within its scheme/profile without proving logical-resource identity, provenance equivalence, ownership equivalence or contextual equivalence.

## 6. Typed immutable object identity matters

Software Heritage distinguishes content, directory, revision, release and snapshot identifiers.

The same underlying content can participate in different higher-level historical objects.

ACL/Vera therefore needs enough type/profile identity to know what a digest/version identifies.

A naked hash string is insufficient.

## 7. Intrinsic identity and context qualifiers are different

SWHID core identifiers are intrinsic object identifiers.

Qualifiers such as origin, visit, anchor, path and line range explain where/how the object was observed or which subpart is intended.

The same object can be reachable through multiple origins or paths.

Architecture consequence:

> Origin/path/context should be modeled as provenance/addressing context, not silently folded into intrinsic content identity.

## 8. Mutable aliases/references are useful but are not immutable evidence

Examples include:

- a Git branch name;
- `latest`-style references;
- mutable document URLs;
- filesystem paths;
- cloud-document aliases;
- package channels;
- repository default branches.

A future lookup of the same alias may resolve to different content.

For consequential derivation/replay, the system must retain the exact observed version/content identity that the alias resolved to at consumption time.

## 9. Exact consumed version belongs in derivation provenance

Suppose Vera summarizes:

`https://example.com/policy/current`

If the resource changes tomorrow, the statement:

`summary derived from https://example.com/policy/current`

is insufficient for reproducibility.

The lineage needs the exact observed representation/version identity plus the locator/origin context.

Architecture consequence:

`mutable locator/reference -> observed immutable version/representation -> transformation occurrence -> derived artifact`

is the minimum reliable shape for consequential transformations.

## 10. Content equality does not imply provenance equality

Two byte-identical artifacts can arrive from:

- different sources;
- different principals;
- different times;
- different authorization domains;
- different validation profiles.

Deduplicating storage bytes may be reasonable later, but canonical provenance/ownership/authorization context must not be lost merely because content hashes match.

## 11. Logical resource continuity can span changing bytes

A document, repository, person-authored report, device configuration or policy may retain one logical identity while accumulating revisions.

Therefore immutable content objects and mutable logical-resource history are complementary rather than competing identity models.

## 12. Source, extraction, chunk and derivative identities must remain separate

A source PDF may produce:

- extracted text;
- page images;
- chunks;
- normalized text;
- OCR output;
- metadata extraction;
- summary;
- embedding/index records.

Those derived objects need their own identity and lineage.

Reusing the source resource ID for a chunk or derivative destroys provenance precision.

This strongly reinforces KA-I-036.

## 13. Derived indexes should point back to exact source revision/version

An embedding or search index generated from source version V1 should not silently remain authoritative after the logical resource moves to V2.

The derived projection needs enough generation/source identity to detect staleness and rebuild/reconcile.

This reinforces KA-I-011 and KA-I-027.

## 14. Conditional mutation requires version-scoped preconditions

HTTP If-Match demonstrates a general lost-update pattern:

- observe version/validator;
- attempt mutation only if the target still matches that expected version;
- reject rather than silently overwrite when it changed.

Architecture consequence:

> Resource mutation should support optimistic-concurrency/version preconditions where stale overwrite would be harmful.

This is a requirement pattern, not a decision to use HTTP ETags internally.

## 15. Locator-provided identity claims may require independent verification

HTTP explicitly warns that Content-Location assertions cannot automatically be trusted merely because a sender supplied them.

Likewise, a remote service claiming that two URLs or files represent the same resource is provenance evidence, not self-authenticating truth.

## 16. Partial/subresource identity requires context

Fragment identifiers, SWHID path/line qualifiers, chunks and page ranges show that subresources need explicit relationship to their containing artifact/version.

A chunk hash or line range without source-version context is not enough for stable long-lived citation when the parent changes.

## 17. Hash/profile migration must not reinterpret old IDs

Content-address schemes include algorithm/profile semantics.

Changing hashing or serialization/profile rules later must not cause old identifiers to be silently reinterpreted.

The identifier scheme/profile itself belongs in identity metadata.

This aligns with KA-I-017/018.

---

# Requirements carried forward

1. Represent logical resource identity separately from locators/addresses.
2. Allow multiple locators/replicas for one observed resource/object.
3. Represent concrete representations/versions separately from logical resource continuity.
4. Keep immutable content/version identity distinct from mutable aliases/references.
5. Bind validators to their producer/scope/semantics.
6. Preserve identifier type/scheme/profile, not only identifier text.
7. Do not infer logical-resource equality from content-hash equality alone.
8. Do not infer content equality from locator equality.
9. Preserve exact observed source version for consequential derivations.
10. Preserve mutable alias/origin context alongside exact consumed version.
11. Give extracted/chunked/normalized/summary/index artifacts distinct identities.
12. Preserve lineage from derivative back to exact source artifact/version.
13. Derived projections expose source revision/generation identity and staleness.
14. Permit optimistic version/precondition checks for stale-write prevention.
15. Treat externally asserted identity/location equivalence as evidence requiring appropriate verification.
16. Preserve subresource context such as page/path/line/chunk relative to the correct source version.
17. Keep storage deduplication independent from provenance/ownership/authorization semantics.
18. Version identifier/hash/serialization profiles when they affect identity.
19. Keep resource identity and access authority separate.
20. Do not select physical storage from these conceptual requirements alone.

---

# Cumulative ledger disposition after KA-G5

## Invariants

Invariant IDs remain **KA-I-001 through KA-I-049**.

Status change:

- **KA-I-037 — candidate -> reinforced**
  - earlier project evidence came from LlamaIndex with adjacent OpenAI Agents SDK, MCP and Agno evidence;
  - KA-G5 independently supplies direct HTTP/RFC, OCI, Git and Software Heritage evidence that logical resource identity, locator/address, and immutable observed content/version identity are different semantics.

No new invariant ID is created.

Reason:

The principal result of KA-G5 is exactly the distinction already anticipated by KA-I-037. Creating a second invariant for mutable aliases versus immutable observed versions would mostly restate the same identity separation.

Strong recurrence also applies to:

- KA-I-001 — raw/source evidence remains addressable;
- KA-I-011 — derived indexes/projections carry generation identity;
- KA-I-017/018 — schema/identifier/profile changes are behavior-bearing;
- KA-I-023 — transformations need their own provenance;
- KA-I-027 — derived projections expose source revision/coverage;
- KA-I-036 — source versus derivative identities remain distinct;
- KA-I-038 — read/mutation contracts need explicit semantics;
- KA-I-039 — round-trip identity metadata can be behavior-bearing.

No invariant becomes a final architecture rule during this research task.

## Failure patterns

Failure IDs remain **KA-F-001 through KA-F-049**.

No new failure ID/status change is made because KA-G5 supplies standards/system semantics rather than a new reproduced ACL/Vera implementation incident.

Later hostile tests should cover:

- same URL returning different content;
- same bytes from two differently authorized/provenanced sources;
- branch/latest alias moving after derivation;
- stale ETag/revision overwrite;
- chunk citation reused after parent revision changes;
- hash equality incorrectly merging logical documents;
- filename/path equality treated as identity;
- derivative reusing source identity;
- index built from V1 served after V2 without staleness signal;
- content digest stored without algorithm/type/profile;
- externally asserted Content-Location/equivalence trusted without verification.

---

# Twenty-six-question disposition after KA-G5

## Strong enough for later requirements/synthesis without another agent-framework revisit

- 1 Stable identity
- 2 Identity vs namespace/principal
- 3 Provenance
- 4 Epistemic state
- 5 Temporal truth
- 6 Conflict/supersession
- 7 Relationships
- 8 Permissions/sensitivity
- 9 Actionability/use-purpose
- 10 Knowledge vs authority
- 11 Resources/artifacts — **positive identity/version/lineage semantics materially improved by KA-G5**
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

- **22 Privacy deletion/retention**
- **26 Scope of truth/generality — non-AI operational-domain validation**

---

# What KA-G5 does not conclude

KA-G5 does **not** conclude that ACL/Vera should:

- store everything in Git;
- use OCI manifests for knowledge;
- adopt SWHIDs as the internal identifier format;
- use URLs as primary keys;
- use a specific hash algorithm;
- content-address every logical entity;
- use an object database;
- use RDF;
- use a graph database;
- use a vector database;
- store all derivative bytes forever.

Those are later physical-design decisions.

---

# Stop point

KA-G5 ends after resource/artifact identity and lineage requirements are recorded.

Do not begin KA-G6 privacy/erasure research, KA-G7 operational validation, retrieval-question construction, hostile review, conceptual synthesis, prototype construction, storage selection, or implementation inside this task.
