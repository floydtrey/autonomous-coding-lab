# Knowledge Core Section Retrieval — SR-1 Deterministic Segmentation and Retrieval Contract

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Phase:** SR-1 deterministic document segmentation and section retrieval design  
**Status:** **design complete; SR-2 implementation not started**  
**Starting branch HEAD inspected:** `51b87be8037c360fc99913d9778e92276704d0ce`  
**Prior accepted phase:** RI-4 intended-host qualification  

## Purpose

SR-1 defines the deterministic contract by which Knowledge Core may derive smaller lexical retrieval units from exact immutable textual `ResourceVersion` artifacts without changing canonical evidence, requiring a model, manually splitting source documents, or allowing a partial derived rebuild to become serving state.

The design answers one bounded question:

> Given one exact immutable text `ResourceVersion`, how can deterministic Python derive reproducible source-aligned retrieval units, index and rank those units in PostgreSQL, and return enough provenance to resolve every hit to the exact parent document and exact source location?

SR-1 is design only. It does not add Python, migrations, tables, routes, embeddings, RAG, extraction, corpus expansion, Authority, or execution.

## Accepted foundation preserved

SR-1 does not reopen the frozen Kernel V1 or accepted RF-2 / RI-2 semantics.

The following remain authoritative:

- `(source_repository_key, source_document_key) -> Resource` is the governed logical repository-document identity.
- `ResourceVersion` plus its immutable SHA-256 artifact is the exact canonical document evidence.
- Repository import verifies exact manifest-listed Git objects before canonical writes.
- Retrieval lifecycle and source authority are explicit metadata; they are not inferred from lexical score, path, filename, recency, headings, or generated text.
- `kc_derived.generation` / `generation_source` provide derived-generation lineage and one-current-generation publication fencing.
- serving-time `resource_version_serving_eligible()` remains the final privacy/restriction/deletion fence.
- ordinary clients remain service-only and receive no database, artifact-store, or repository credentials.

## Core SR-1 decisions

1. **Canonical evidence stays whole.** A section/segment is never a new canonical `Resource`, `ResourceVersion`, or copied source document.
2. **Derived units are a deterministic projection.** The same exact `ResourceVersion` plus the same segmentation profile must reproduce the same ordered segment identities, coordinates, digests, lifecycle projection, and lexical projection.
3. **The source bytes are partitioned, not rewritten.** Segment source spans cover the exact artifact bytes in source order with no overlap and no gaps. Concatenating exact segment slices by ordinal reconstructs the exact parent artifact byte-for-byte.
4. **Markdown structure is deliberately narrow.** V1 uses deterministic ATX-heading structure plus fenced-code awareness. It does not require a general semantic Markdown interpreter.
5. **No model decides segmentation or currentness.** Parent lifecycle is explicit import input. Optional section lifecycle is accepted only from an exact source-controlled directive defined below; prose and heading semantics are never used as lifecycle evidence.
6. **Section metadata cannot promote trust/currentness.** A section directive may keep or reduce serving currentness relative to the document/ancestor, never promote it.
7. **PostgreSQL remains baseline retrieval.** Segment lexical search extends RF-2 native full-text search and deterministic ranking.
8. **Publication remains atomic at generation level.** A candidate segment generation is non-serving until all eligible parent sources segment/index successfully and the generation settles current.
9. **Parent serving fences dominate every child.** Restricting/erasing/fencing a parent `ResourceVersion` or logical `Resource` makes all of its derived segments non-serving even if stale derived rows remain.
10. **SR-2 must preserve an RF-2 serving transition.** A previously current whole-document RF-2 generation may remain serving until a complete segment generation is published; no empty/partial cutover is allowed.

## Canonical versus derived boundary

### Canonical / governed input

SR-1 treats these as canonical or governed source facts already accepted elsewhere:

- logical `resource_ref`;
- exact `resource_version_ref`;
- exact immutable artifact bytes;
- `content_digest_algo`, `content_digest`, byte size, media type, and canonical revision identity;
- repository import observation: repository key/locator, document key, exact source commit, path, Git blob, classification, explicit document retrieval lifecycle, authority rank, and rationale;
- resource/revision privacy/restriction/deletion state.

### Derived / rebuildable state

The following are disposable/rebuildable projection data:

- segmentation profile identity/digest;
- ordered segment rows;
- heading path and structural kind;
- segment byte/line coordinates;
- exact source-slice digest;
- deterministic segment key;
- effective segment lifecycle and its derivation origin;
- inherited retrieval annotations copied for ranking/filtering convenience;
- weighted PostgreSQL `tsvector`;
- lexical score;
- the derived generation containing the rows.

No derived segment is evidence independent of its exact parent `ResourceVersion`.

## Supported media in the first implementation

SR-2 preserves RF-2's deliberately bounded supported media:

- `text/markdown`, strict UTF-8;
- `text/plain`, strict UTF-8.

Unsupported media remain intentionally non-indexable in this slice. SR-1 does not define PDF, DOCX, HTML, image, OCR, or other extraction pipelines.

The exact artifact is read through the accepted artifact store and its SHA-256 identity is verified before segmentation. Decoding is strict UTF-8. The parser does not normalize or rewrite the canonical bytes.

## Segmentation profile

All rules that can affect segment boundaries, identities, lifecycle interpretation, or search projection belong to one explicit deterministic profile. The initial contract name is:

`kc-section-segmentation-v1`

Its canonical configuration must include at least:

- supported media set;
- UTF-8 strict-decoding requirement;
- Markdown heading/fence grammar version;
- lifecycle-directive grammar version;
- lifecycle monotonicity rules;
- large-block split parameters;
- exact segment-key serialization version;
- lexical language/configuration;
- lexical weighting/projection rules;
- deterministic ranking fields/order.

The profile is serialized as canonical UTF-8 JSON using sorted object keys, no insignificant whitespace, and `ensure_ascii=false`. Its identity is `sha256:<hex>` over those exact canonical JSON bytes.

A rule/configuration change that can alter any derived output requires a different profile digest and therefore a new derived generation. Existing canonical documents do not change.

### Initial size parameters

For falsifiable SR-2 behavior, profile V1 fixes:

- `soft_target_bytes = 16384`;
- `hard_max_bytes = 32768`.

These are byte limits, not token limits, so segmentation has no tokenizer/model dependency.

## Exact line and byte model

The segmenter operates on the verified exact artifact bytes and a strict UTF-8 decoded view with a byte-offset map.

Coordinates use:

- `source_byte_start`: zero-based inclusive byte offset;
- `source_byte_end`: zero-based exclusive byte offset;
- `source_line_start`: one-based inclusive logical line number;
- `source_line_end`: one-based inclusive logical line number containing the final byte of a non-empty segment.

`LF` and `CRLF` are both recognized as line endings while their exact original bytes remain unchanged. Split points occur only at exact line boundaries, never inside a UTF-8 code point or line-ending sequence.

An empty document is represented by one deterministic zero-length root segment with byte range `[0, 0)`, line range `1..1`, the SHA-256 digest of empty bytes, and an empty lexical vector. It will not match ordinary lexical queries.

## Markdown structural scan

For `text/markdown`, V1 performs one deterministic line-oriented scan.

### ATX headings

A structural heading is recognized only outside a fenced code block when a line contains:

- zero through three leading ASCII spaces;
- one through six `#` characters;
- then ASCII space/tab or end-of-line.

The heading level is the count of leading `#` markers. Heading display text is deterministically derived from that exact line by removing the opening marker/required separator, trimming surrounding ASCII whitespace, and removing an optional closing run of `#` characters only when that run is separated from heading text by ASCII whitespace.

Setext-style headings are **not** structural in V1. They remain ordinary body text. YAML/front matter, HTML, block quotes, lists, and tables do not create structure by themselves.

Skipped heading levels are allowed. For example, a `#` followed by `###` creates a path containing those two observed headings; the parser does not invent a missing `##` node.

### Fenced code blocks

Fence awareness exists so heading-like text and reserved directives inside code are not interpreted as structure or metadata.

A fence opener is recognized outside a fence with zero through three leading ASCII spaces followed by at least three identical backticks or tildes. A closer uses the same fence character, at least the opener length, zero through three leading ASCII spaces, and only ASCII whitespace after the fence run.

An unclosed fence extends to end-of-file and remains source content. No heading or lifecycle directive is recognized inside it.

### Heading path

The parser maintains the standard heading-level stack. When a level `L` heading is observed, prior headings at level `L` or deeper leave the active path; the new heading becomes the leaf.

Each segment stores a derived `heading_path` containing, for every active heading:

- level;
- derived display text;
- exact heading source line;
- exact heading byte start/end coordinates.

The heading path is navigation/context metadata derived from source text. It is **not** lifecycle, authority, truth, or execution metadata.

## Base structural blocks

The exact document bytes are first partitioned into base structural blocks.

### Preamble

Bytes from artifact start through the byte immediately before the first recognized ATX heading form one `preamble` block. If the document starts with a heading, no non-empty preamble block is created.

### Heading blocks

Every recognized ATX heading starts one `section` block. That block ends immediately before the next recognized ATX heading of **any** level or at EOF.

This means a section block contains its own heading line plus only the direct following bytes before the next heading. Child subsection bytes are separate blocks rather than duplicated inside the parent block. Hierarchy is preserved through `heading_path`.

### No-heading Markdown

A non-empty Markdown document with no recognized ATX headings becomes one root `document` block.

### Plain text

A non-empty `text/plain` document becomes one root `document` block. It has an empty heading path and no Markdown lifecycle directives.

This base partition is exact: every source byte belongs to exactly one block, in order, without duplication.

## Lists, tables, comments, and other body constructs

V1 does not semantically reinterpret lists, tables, block quotes, front matter, HTML, or ordinary comments. They remain exact source bytes in the current base block.

They do not create lifecycle/currentness, authority, source identity, or truth metadata.

If a base block is small enough, lists/tables remain entirely inside that block. If a block requires size continuation, ordinary lists/tables may be divided only at exact line boundaries under the deterministic size rules below. Fenced code is the one V1 body construct that is never split internally.

## Deterministic large-block continuation

A base structural block whose byte length is at most `hard_max_bytes` becomes one retrieval segment.

An oversized block is partitioned greedily from its current byte cursor using only boundaries outside fenced code:

1. Prefer the eligible blank-line boundary whose resulting segment length is closest to `soft_target_bytes`, considering only boundaries greater than the cursor and no farther than `hard_max_bytes`.
2. If two blank-line candidates are equally distant from the target, choose the lower byte offset.
3. If no eligible blank-line boundary exists within the hard maximum, choose the greatest eligible ordinary line boundary at or before `hard_max_bytes`.
4. If no eligible line boundary exists because an indivisible fenced-code region crosses the hard maximum, deterministic segmentation fails for that parent `ResourceVersion`.
5. Repeat until the base block is exhausted. The final continuation may be smaller than the soft target.

A boundary is the byte position immediately after the complete original line-ending sequence. No source byte is dropped or duplicated.

The first piece retains base kind `preamble`, `section`, or `document`; subsequent pieces have kind `continuation`. Every continuation retains the same heading path and effective lifecycle as its base block. `part_index` is one-based and `part_count` is the final deterministic number of pieces for that base block.

No token counter, embedding model, language model, sentence model, or semantic similarity algorithm participates in this split.

## Exact section lifecycle contract

### Document lifecycle remains primary

Each parent `TextIndexSource` already supplies explicit document lifecycle:

- `current`;
- `unknown`;
- `superseded`.

Every segment inherits that lifecycle unless an allowed source-controlled section directive makes the segment or subtree less current.

Authority rank, repository label, source path, source version, observed time, classification, and import rationale remain parent/document metadata in V1. There is **no segment-scope authority override**.

### Why headings do not determine lifecycle

The parser must never infer lifecycle from strings such as:

- `Historical`;
- `Old`;
- `Deprecated`;
- `Current`;
- `Archive`;
- dates, paths, filenames, or commit recency.

A heading with any of those words is still only a heading. This prevents unsupported source prose/structure from being transformed into lifecycle truth.

### Optional exact source-controlled lifecycle directive

For Markdown only, V1 reserves this exact semantic form outside fenced code:

`<!-- kc:retrieval-lifecycle=current -->`  
`<!-- kc:retrieval-lifecycle=unknown -->`  
`<!-- kc:retrieval-lifecycle=superseded -->`

The directive is recognized only when it is the first non-blank body line immediately following a recognized ATX heading. Leading zero through three ASCII spaces are permitted; otherwise the semantic token and values are exact.

The directive applies to that heading block and its descendant heading subtree until a descendant valid directive overrides it with an equal or **more restrictive** lifecycle.

Lifecycle restrictiveness order is:

`current < unknown < superseded`

A directive attempting to make a segment more current than its inherited document/ancestor state is invalid. Examples:

- parent `current` -> child `unknown`: allowed;
- parent `current` -> child `superseded`: allowed;
- parent `unknown` -> child `current`: invalid;
- parent `superseded` -> child `current` or `unknown`: invalid;
- ancestor directive `superseded` -> descendant `current`: invalid.

An invalid promotion fails deterministic segmentation for that parent version; it is not silently clamped or ignored.

A recognized directive line remains part of the canonical source slice and segment SHA-256 digest. It is omitted only from the derived lexical search text so metadata words do not win ordinary content searches.

Any occurrence outside a fence containing the reserved token `kc:retrieval-lifecycle` but using invalid syntax, invalid placement, or multiple directives for the same heading fails segmentation. This prevents a likely intended control marker from being silently treated as ordinary prose.

### Unlabeled mixed-status documents

SR-1 deliberately does not pretend deterministic syntax can discover unstated lifecycle intent.

If a current document contains historical/stale prose but has no explicit accepted section directive, those sections inherit the document's explicit lifecycle. The system will **not** guess that they are historical based on headings or content.

Therefore a known mixed-status document has only safe deterministic choices in this contract:

1. add source-controlled section lifecycle directives and create a new exact canonical `ResourceVersion`; or
2. classify the parent document conservatively (`unknown` or `superseded`) through the governed import process.

This is metadata/classification, not manual file splitting, and requires no model.

## Segment source integrity and identity

Every derived segment records:

- exact parent `resource_version_ref`;
- `segment_ordinal`, zero-based in source order;
- structural kind;
- base-block ordinal;
- one-based `part_index` / `part_count`;
- exact byte start/end;
- exact line start/end;
- exact `heading_path`;
- `source_slice_digest_algo = sha256`;
- SHA-256 of the exact source slice bytes;
- effective lifecycle;
- lifecycle origin (`document`, `section-directive`, or `ancestor-directive`) plus directive source coordinates when applicable;
- deterministic `segment_key`.

### Deterministic segment key

The segment key is SHA-256 over canonical UTF-8 JSON containing exactly:

```json
{
  "key_version": 1,
  "profile_digest": "sha256:...",
  "resource_version_ref": "canonical-lowercase-uuid",
  "segment_ordinal": 0,
  "source_byte_start": 0,
  "source_byte_end": 123,
  "source_slice_sha256": "..."
}
```

Serialization uses sorted keys, separators `,` and `:` with no insignificant whitespace, and `ensure_ascii=false`. The stored form is `sha256:<hex>`.

Consequences:

- rebuild of the same exact version/profile produces the same keys;
- rename-only/source-locator change with the same exact `ResourceVersion` does not change segment keys;
- any content edit creates a new `ResourceVersion`, therefore new segment keys even when some slices happen to be textually identical;
- moving/renaming a heading within document content creates a new exact parent version and new keys;
- identical slice text in two places remains distinct because ordinal/coordinates differ;
- identical artifact bytes belonging to two different logical documents remain distinct because their `resource_version_ref` values differ;
- a segmentation-profile change produces new keys without changing canonical source evidence.

A segment key is a derived locator, not a permanent cross-version semantic section identity.

## Exact coverage invariant

For every successfully segmented supported non-empty parent version:

- first segment starts at byte `0`;
- last segment ends at exact artifact byte size;
- each segment's end equals the next segment's start;
- ordinals are contiguous `0..N-1`;
- each stored slice SHA-256 equals the canonical artifact bytes at that exact range;
- concatenating those ranges reconstructs the exact parent bytes and parent SHA-256 digest.

This invariant is stronger than merely proving that searchable text exists. It proves the derived segmentation did not silently drop, overlap, reorder, or invent canonical source bytes.

## Lexical projection

Baseline retrieval remains PostgreSQL full-text search with fixed `english` configuration.

For each segment, the deterministic search vector is built from two source-derived components:

1. **local source text** — strict UTF-8 text from that exact segment source slice, with only a recognized lifecycle directive line removed from the search projection; weight `A`;
2. **heading context text** — display text from the segment's active heading path; weight `B`.

Conceptually:

```text
setweight(to_tsvector('english', local_search_text), 'A')
||
setweight(to_tsvector('english', heading_context_text), 'B')
```

This lets a continuation chunk remain discoverable by its section heading while keeping local source text stronger than inherited navigation context.

The heading path is source-derived context only. Its presence in a search vector does not convert the heading into lifecycle, authority, permission, or factual truth.

No copied decoded body is required in PostgreSQL. The immutable parent artifact remains the exact content source.

## PostgreSQL derived representation — contract level

SR-2 should add a separate derived segment-search representation rather than turning segments into canonical resources.

Conceptual table:

`kc_derived.resource_segment_text_search`

Required semantic fields:

| Field | Contract purpose |
| --- | --- |
| `generation_id` | FK to current/historical derived generation. |
| `resource_version_ref` | Exact canonical parent version. |
| `segment_ordinal` | Zero-based deterministic source order. |
| `segment_key` | Deterministic profile/version/coordinate identity. |
| `segment_kind` | `preamble`, `section`, `document`, or `continuation`. |
| `base_block_ordinal` | Deterministic structural block identity within parent/profile. |
| `part_index`, `part_count` | Large-block continuation coordinates. |
| `source_byte_start`, `source_byte_end` | Exact half-open source byte span. |
| `source_line_start`, `source_line_end` | Exact human-readable line span. |
| `source_slice_sha256` | Integrity digest of exact canonical slice. |
| `heading_path` | Derived structured heading context; JSON/JSONB is acceptable. |
| `lifecycle_state` | Effective segment retrieval lifecycle. |
| `parent_lifecycle_state` | Explicit parent/document lifecycle supplied by import/retrieval source. |
| `lifecycle_origin` | Document vs exact section/ancestor directive provenance. |
| `lifecycle_directive_line` | Nullable exact source line of directive origin. |
| `authority_rank` | Inherited parent ranking annotation. |
| `repository`, `source_path`, `source_version`, `observed_at` | Inherited approved source/provenance labels. |
| `search_vector` | PostgreSQL weighted lexical projection. |

Contract constraints include:

- primary identity unique within generation by `(generation_id, resource_version_ref, segment_ordinal)`;
- `segment_key` unique within one generation;
- non-negative ordered byte/line/part coordinates with `source_byte_start <= source_byte_end`;
- lifecycle constrained to RF-2 values;
- GIN index over `search_vector`;
- generation/lifecycle/authority lookup indexes sufficient for accepted query semantics.

Do not persist copied canonical segment body text merely to support search. Exact text remains recoverable internally from the parent artifact plus byte range.

The existing `kc_derived.resource_text_search` may remain as the RF-2 legacy whole-document projection for historical/transition compatibility. SR-2 must not reinterpret legacy rows as canonical evidence.

## Generation and rebuild contract

Segment retrieval remains a `DerivedKind.TEXT` projection so the accepted one-current-text-generation fence continues to define serving state.

`generation_source` remains one row per indexed exact parent `ResourceVersion`, not one row per segment. Segment rows provide child lineage beneath that canonical generation source.

A segment generation records deterministic implementation identity/profile through generation configuration/model lineage fields and `config_digest`. The field name `model_identity` does not imply an AI model; SR-2 may identify the deterministic segmenter/PostgreSQL projection there or leave AI-specific identity null if the existing interface permits. No model credential/runtime is part of the contract.

### Complete-build rule

For every RF-2-supported source selected for a candidate text generation:

1. exact artifact integrity verifies;
2. strict UTF-8 decode succeeds;
3. deterministic segmentation succeeds;
4. exact coverage/digest invariants succeed;
5. all segment rows and lexical vectors are produced;
6. only then may the candidate generation settle current.

If any supported source fails those steps, the candidate generation must not become current. The previous current generation remains serving. There is no model fallback, heuristic fallback, silent whole-document substitution, or partial-source publication.

Unsupported media may continue to be intentionally absent exactly as RF-2 defines; that is not parser failure.

### Profile changes

Changing any segmentation/search rule creates a new profile digest and requires a full new derived text generation for the selected source set. Old segment rows may remain historical/disposable. Canonical `ResourceVersion` and import observations are unchanged.

A rebuild using the same exact parent source set and same profile must reproduce the same segment payloads/keys/digests/lifecycle projection independent of generation UUID and operational timestamps.

## RF-2 transition compatibility

SR-2 must not create a serving gap during the first segment-generation cutover.

Before a complete SR-2 segment generation is current, the accepted RF-2 whole-document current generation remains the serving retrieval state. Implementation may dispatch by recognized generation configuration/projection version or use another equivalently deterministic transition mechanism, but it must prove:

- old RF-2 current generation remains queryable before segment publication;
- a failed candidate segment build does not change serving results;
- after successful settlement, exactly the new segment generation serves;
- old whole-document and new segment rows are never mixed into one result set.

Production rollout mechanics beyond that semantic transition are deferred.

## Retrieval behavior

### Candidate matching

Use PostgreSQL `websearch_to_tsquery('english', query)`, `@@`, and `ts_rank_cd()` against only the current text generation's applicable projection.

Whitespace-only input remains invalid. Stop-word-only or irrelevant input may return zero results; there is no arbitrary substring/semantic fallback.

### Default lifecycle behavior

`include_superseded=false` remains default.

Filtering now uses the **effective segment lifecycle**:

- `superseded` segments are excluded by default;
- `current` and `unknown` remain eligible;
- `include_superseded=true` explicitly enables historical segment hits.

A parent lifecycle of `superseded` makes every child segment superseded. Section directives cannot bypass it.

### Deterministic total order

After lexical matching and default lifecycle filtering, segment hits use this total order:

1. `ts_rank_cd(search_vector, query)` descending;
2. effective lifecycle priority: `current`, then `unknown`, then `superseded`;
3. inherited `authority_rank` ascending, NULL last;
4. canonical parent `resource_version.created_revision_id` descending;
5. parent `resource_version_ref` ascending;
6. `segment_ordinal` ascending;
7. `segment_key` ascending as final defensive tie-break.

Tests assert exact ordered identities, not exact floating-point rank values.

There is no implicit one-hit-per-document collapse in baseline SR-2. Multiple relevant segments from one parent may appear. Grouping, diversification, semantic reranking, and context assembly are separate future work.

### Serving eligibility and limit

As in RF-2, derived membership is insufficient for serving.

Before a hit is emitted, the application rechecks `resource_version_serving_eligible(parent_resource_version_ref)`. A failed parent check suppresses the hit regardless of stale segment-row presence.

For the bounded implementation, apply the response `limit` after serving eligibility so restricted stale rows cannot consume result slots.

A purge path may remove all derived segment rows for a fenced parent version/resource, but serving-time eligibility remains mandatory defense in depth.

## Retrieval result/API contract

SR-2 should preserve the existing semantic route shape:

`POST /v1/retrieval/search`

and existing request fields:

```json
{
  "query": "Atlas emergency shutdown token",
  "limit": 10,
  "include_superseded": false
}
```

A segment-mode result retains all RF-2 parent provenance and adds exact child coordinates. Conceptually each hit contains:

```json
{
  "rank": 1,
  "resource_ref": "...",
  "resource_version_ref": "...",
  "content_digest_algo": "sha256",
  "content_digest": "...",
  "media_type": "text/markdown",
  "created_revision_id": 117,
  "segment_key": "sha256:...",
  "segment_ordinal": 4,
  "segment_kind": "section",
  "base_block_ordinal": 3,
  "part_index": 1,
  "part_count": 1,
  "source_byte_start": 892,
  "source_byte_end": 1310,
  "source_line_start": 42,
  "source_line_end": 57,
  "source_slice_sha256": "...",
  "heading_path": [
    {"level": 1, "text": "Atlas", "line": 1},
    {"level": 2, "text": "Emergency shutdown", "line": 42}
  ],
  "parent_lifecycle_state": "current",
  "lifecycle_state": "current",
  "lifecycle_origin": "document",
  "authority_rank": 10,
  "repository": "synthetic/ops",
  "source_path": "docs/atlas.md",
  "source_version": "exact-source-version",
  "lexical_score": 0.0
}
```

Top-level response continues to identify the serving `generation_id` and `source_revision_highwater` and should expose the active deterministic projection/profile identifier or digest so a result set's segmentation rules are observable.

### Exact recovery semantics

The tuple:

- parent `resource_version_ref`;
- parent content digest;
- segment byte range;
- segment slice SHA-256;
- heading/source line range;
- serving generation/profile identity

is sufficient for Knowledge Core to resolve the exact parent artifact and exact evidence location without trusting path or copied segment text.

SR-2 does **not** need to expose artifact-store keys/paths, database internals, repository credentials, or raw whole-artifact bytes. A future context/RAG/content-delivery layer may consume exact slices internally, but that is outside SR-1/SR-2 baseline retrieval.

## Failure behavior

A candidate segment generation fails closed when any supported selected source encounters:

- missing/unknown exact parent version;
- serving-ineligible parent at build time;
- artifact digest mismatch;
- non-SHA-256 parent where the accepted retrieval path requires SHA-256;
- strict UTF-8 decode failure;
- reserved lifecycle directive with invalid syntax/placement/duplication;
- lifecycle promotion attempt;
- deterministic size partition impossible without splitting an indivisible fenced block;
- coverage gap/overlap, invalid coordinates, or source-slice digest mismatch;
- duplicate/non-deterministic segment key within a parent/generation;
- database/index write failure before publication;
- generation fencing rejection / late finisher.

On failure:

- the candidate does not become current;
- prior current text generation remains serving;
- no partial source/segment set is represented as accepted;
- safely written derived residue is non-serving/disposable;
- retry starts from the same exact canonical sources and profile and must reproduce deterministic segment payloads.

No failure authorizes a model or heuristic parser fallback.

## Synthetic SR-2 fixture plan

SR-2 should implement a small controlled fixture set with predeclared exact segment boundaries/identities.

### `mixed.md`

Contains:

- `# Atlas Runbook` current material;
- `## Historical procedure` with an exact `superseded` directive and unique token `amberlegacy`;
- `## Current procedure` with unique token `cedarcurrent`;
- a nested `### Verification` child.

Required behavior: default search finds `cedarcurrent` but not `amberlegacy`; historical mode finds the superseded section; the word `Historical` by itself is not the lifecycle cause.

### `heading-only-lifecycle-negative.md`

Contains a heading named `## Historical` but **no** directive under a current parent.

Required behavior: it remains current. This falsifies any heuristic lifecycle inference from heading text.

### `structure.md`

Contains preamble, nested ATX levels including a skipped level, Setext-looking text, lists, a Markdown table, block quote, front matter-like text, a fenced code block containing fake `# headings` and fake `kc:retrieval-lifecycle` text, plus normal headings after the fence.

Required behavior: only allowed outside-fence ATX headings define blocks/directives; exact source coverage reconstructs the file.

### `large.md`

Contains one section exceeding `hard_max_bytes` with deterministic blank-line and line-boundary candidates plus a continuation query token.

Required behavior: continuation boundaries and keys are exactly reproducible; every emitted part is within hard maximum.

### `oversize-fence.md`

Contains one fenced code region larger than `hard_max_bytes` with no legal external boundary.

Required behavior: candidate generation fails and previous generation remains current.

### `plain.txt`

Contains paragraph/line structure exceeding the soft target but no Markdown semantics.

Required behavior: deterministic root/continuation segmentation by byte/line rules only.

### `duplicate.md` / duplicate logical source

Include identical bytes both at separate coordinates and in a different logical Resource.

Required behavior: source-slice digests may match, but segment keys remain distinct by coordinates/parent version.

## Tiny real-document pilot plan

Only after synthetic SR-2 gates pass, use a tiny explicit manifest/pilot pinned to one exact repository commit. Do not broadly import the repository.

Candidate real documents:

1. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md` — current design, nested headings, lists, code blocks, tables, and enough structure to exercise normal segmentation.
2. `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md` — explicit whole-document superseded source to prove parent lifecycle fences every segment.
3. `docs/architecture/knowledge-core/CURRENT_STATE.md` — deliberately useful negative control for mixed temporal prose: headings/content alone must not create section lifecycle. Unless the canonical source later gains explicit directives, segments inherit the parent lifecycle.
4. `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md` — larger nested technical Markdown with code/table/list constructs and deterministic continuation pressure if size parameters require it.

Before applying the tiny pilot, predeclare expected source commit/blob proofs, document lifecycle/authority, segment counts or exact selected boundary assertions, known query-to-segment outcomes, and current/historical behavior. The same deterministic segmenter is used; no hand-split copies are permitted.

## Falsifiable SR-2 acceptance gates

SR-2 is not accepted until all applicable gates below pass, with PostgreSQL gates run on real PostgreSQL.

### SR2-G1 — canonical evidence remains unchanged

Building/rebuilding segment retrieval creates no new `Resource` or `ResourceVersion`, does not change parent artifact bytes/digest, does not rewrite repository observations/bindings, and stores no copied canonical section body as a new canonical resource.

### SR2-G2 — exact deterministic source partition

For every successfully segmented supported fixture, segment ordinals are contiguous, ranges are ordered/non-overlapping/gap-free, each source-slice SHA-256 matches exact artifact bytes, and concatenating slices reconstructs exact parent bytes/digest.

### SR2-G3 — deterministic heading/preamble structure

Predeclared preamble, ATX heading blocks, nested/skipped-level heading paths, source lines, and byte boundaries for `structure.md` match exactly. Setext-looking text does not become structure.

### SR2-G4 — fence/list/table handling

Heading/directive-like text inside fenced code remains ordinary source content. Lists, tables, block quotes, front matter-like text, and ordinary comments are not reclassified as lifecycle or authority metadata. Exact coverage still holds.

### SR2-G5 — deterministic large-block continuation

`large.md` partitions according to the fixed soft/hard byte algorithm, every part is at most `hard_max_bytes`, continuation heading context is preserved, and repeated builds choose identical boundaries.

### SR2-G6 — unbreakable oversized fence fails closed

`oversize-fence.md` cannot be legally partitioned without splitting a fence, so the candidate build fails, no candidate becomes current, and the previously current retrieval generation continues serving unchanged.

### SR2-G7 — stable segment identities

Two rebuilds from the same exact parent versions and same profile produce identical ordered segment keys, coordinates, slice digests, heading paths, and lifecycle projection even though generation UUIDs differ.

### SR2-G8 — edit/rename/duplicate identity behavior

- rename/path-only change with the same exact `ResourceVersion` preserves segment keys;
- content edit/heading rename/section move creates a new parent `ResourceVersion` and new segment keys;
- identical text at different source coordinates has distinct segment keys;
- identical bytes in different logical Resources/ResourceVersions have distinct segment keys.

### SR2-G9 — exact parent provenance

Every segment hit resolves to one exact logical `Resource`, exact `ResourceVersion`, parent SHA-256 digest, canonical revision, approved repository/source metadata, serving generation/profile, and exact byte/line location. No result is keyed only by path, heading text, or segment digest.

### SR2-G10 — inherited metadata and no segment authority escalation

Authority rank and approved source metadata are inherited from the parent source. There is no segment-scope authority override. Generated headings/path strings cannot modify authority/currentness.

### SR2-G11 — explicit lifecycle directive, no heuristic lifecycle

Under a current parent, exact allowed `unknown`/`superseded` directives reduce lifecycle as specified. A heading named `Historical` without a directive remains current. Reserved malformed/misplaced/duplicate directives fail segmentation.

### SR2-G12 — lifecycle cannot be promoted

Fixtures attempting `unknown -> current`, `superseded -> current`, or descendant promotion above an ancestor directive fail the candidate build. They are not silently clamped or accepted.

### SR2-G13 — mixed-status current/historical retrieval

Default query of `mixed.md` returns current eligible section tokens and excludes the explicitly superseded `amberlegacy` section. `include_superseded=true` recovers the exact historical segment with the same parent/version and exact section coordinates.

### SR2-G14 — current-generation publication isolation

A complete candidate segment generation settles as the sole current `DerivedKind.TEXT` generation. Old RF-2/older segment rows may remain historical but are not mixed with current hits. A failed/late candidate never replaces a newer current generation.

### SR2-G15 — RF-2 cutover has no serving gap

Before first segment-generation settlement, accepted RF-2 whole-document retrieval remains usable. Failed SR-2 build leaves it unchanged. After successful settlement, serving switches to the segment projection atomically and uses exactly one current generation.

### SR2-G16 — deterministic segment ranking

Controlled equal/near-equal fixtures prove ordering by lexical score, effective lifecycle, inherited authority, parent canonical revision, parent version ref, segment ordinal, and final segment key. At least ten repeated queries against the same generation return the identical ordered segment-key list.

### SR2-G17 — parent serving fence dominates stale segment rows

After indexing, restrict/fence a parent version/resource. Normal purge removes its segment rows where applicable. Reintroduce a stale matching derived row deliberately; service-time parent eligibility still suppresses every hit from that parent before response limiting.

### SR2-G18 — bounded query/service contract

Whitespace-only query is rejected; irrelevant/stop-word-only query has bounded empty behavior; `limit` remains bounded and is applied after serving eligibility. A service-only client can search with the existing caller boundary and no DB/artifact/repository credentials.

### SR2-G19 — no storage/internal leakage and no copied body projection

API/OpenAPI response does not expose database URL/credentials, artifact key/backend/path, repository credentials/root, raw SQL, or artifact-store internals. Derived PostgreSQL state contains coordinates/digests/metadata/`tsvector`, not copied canonical segment body text.

### SR2-G20 — no model dependency

Synthetic build and lexical retrieval pass in an environment with no language-model endpoint, key, model process, tokenizer, embedding service, or vector database. Segment boundaries/keys/ranking remain identical regardless of model availability.

### SR2-G21 — profile change forces rebuild without canonical mutation

Changing one segmentation-profile parameter changes profile/config digest and produces a new derived generation/segment-key set while parent `ResourceVersion` refs/artifacts remain unchanged. Old and new profile rows never mix in one current result set.

### SR2-G22 — tiny real-document pilot

After G1-G21 pass, the explicitly pinned tiny real-document set is segmented by the same machinery with predeclared provenance/query assertions. Parent-superseded material remains historical, structure/fence handling matches exact source, the mixed-temporal negative control does not acquire inferred lifecycle, and no unlisted/broad repository content is imported.

## Explicit deferred work

SR-1/SR-2 do not authorize or decide beyond what the baseline contract needs:

- embeddings/vector search;
- semantic query expansion or LLM reranking;
- RAG/context-window assembly or answer synthesis;
- model-based section classification/currentness inference;
- automatic document discovery/document-key assignment;
- broad ACL/Vera/RiskCardOCR/research/legacy corpus import;
- PDF/DOCX/HTML/image/OCR extraction;
- cross-version semantic section identity/tracking;
- semantic deduplication/diversification;
- segment-scope authority rank or execution permission;
- Authority integration or autonomous execution;
- production rollout/security/TLS/credential/service-supervision/backup work;
- machine-reboot persistence qualification.

A model may later assist optional semantic retrieval/reranking/synthesis only after deterministic baseline retrieval is accepted. It must not become required for canonical storage, source identity, segmentation, lifecycle provenance, or baseline lexical retrieval.

## SR-2 implementation boundary

The next separately authorized task may implement only the smallest code/migration/test/API slice needed to satisfy SR2-G1 through SR2-G22.

SR-2 may introduce the derived segment table/migration, deterministic segmenter, segment-generation builder, segment search/result schemas, RF-2-compatible cutover behavior, and bounded synthetic/tiny-real tests required by these gates.

It must stop after those gates and durable completion evidence. Do not begin embeddings, RAG, broad import, Authority, or execution.

## SR-1 stop boundary

**SR-1 is complete when this design and the controlling state/handoff documentation are committed. Do not implement the segmenter, migration, schema, index, route changes, fixtures, or real pilot during SR-1.**
