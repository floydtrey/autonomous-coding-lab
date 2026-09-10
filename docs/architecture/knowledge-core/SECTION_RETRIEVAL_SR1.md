# Knowledge Core Section Retrieval — SR-1 Deterministic Segmentation and Retrieval Contract

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Phase:** SR-1 deterministic document segmentation and section retrieval design  
**Status:** **design complete; audit-amended 2026-09-10; SR-2 implementation must be requalified against this amended contract**  
**Original accepted SR-1 commit:** `1d1313844aa4d224bd42c0888970a11e959d9501`  
**Pre-amendment SR-2 candidate:** `2c48a0e73c560fad62028776f375c94162e138be` — **not accepted under this amended contract**  
**Prior accepted phase:** RI-4 intended-host qualification

## 2026-09-10 bounded audit amendment

A bounded independent audit found six inconsistencies or underspecified cases in the original SR-1 contract. The corrections below are accepted as part of SR-1 and supersede any contradictory wording in the original SR-1 text, SR-1 handoff, RI-1/RI-2 wording, or restart documentation.

The corrected rules are:

1. **Structural segmentation and retrieval lifecycle projection are separate deterministic stages.** Structural segmentation depends only on the exact canonical `ResourceVersion` artifact plus the structural segmentation profile. Lifecycle/source-ranking projection additionally depends on an exact governed classification/observation snapshot and the retrieval-projection profile. A complete derived generation is reproducible only when all of those inputs are identified.
2. **Declared lifecycle is preserved; effective lifecycle is monotone.** A section declaration remains exactly what the canonical source declares. Effective lifecycle is the most restrictive of the governed parent-document lifecycle, every applicable ancestor-section declaration, and the section's own declaration. A later parent downgrade cannot make unchanged source bytes fail structural segmentation.
3. **Reserved-control recognition is narrow.** Ordinary prose, inline-code examples, Markdown block quotes/quoted explanations, and fenced-code examples containing `kc:retrieval-lifecycle` are ordinary content. A standalone control-looking HTML-comment line beginning with the reserved control prefix is treated as an attempted control; if malformed, duplicated, or misplaced it fails lifecycle projection rather than silently inheriting a permissive state.
4. **Large-block termination is explicit.** An indivisible UTF-8 source line exceeding `hard_max_bytes` fails deterministic segmentation when no legal external boundary exists. If the remaining suffix is at most `hard_max_bytes`, emit that suffix whole and terminate.
5. **`ResourceVersion` identity is content-addressed within a logical Resource.** A previously unseen byte representation creates a new exact version. If document history is A → B → A, the final A reuses the original A `ResourceVersion`; a new governed observation/receipt/generation records the re-observation. Same version plus same structural profile therefore reproduces the original structural segment identities.
6. **Privacy fencing and derivative deletion are distinct from ordinary supersession.** `RESTRICT`/`ERASE` fences serving access immediately. Derivative cleanup is deterministic/idempotent reconciliation and may occur eagerly. If a parent `ResourceVersion` is actually physically purged/erased, no segment derivative may remain. A retained repository-import superseded parent is historical evidence, not a privacy purge, and may retain non-serving-by-default segment derivatives for explicit historical retrieval.

These corrections do **not** authorize models, embeddings, RAG, Authority, execution, broad corpus import, or any other expansion of SR-2.

## Purpose

SR-1 defines how Knowledge Core derives smaller lexical retrieval units from exact immutable textual `ResourceVersion` artifacts without changing canonical evidence, requiring a model, manually splitting source documents, or allowing a partial derived rebuild to become serving state.

The bounded question remains:

> Given one exact immutable text `ResourceVersion` and one exact governed retrieval observation, how can deterministic machinery derive reproducible source-aligned retrieval units, project lifecycle/source metadata, index and rank those units in PostgreSQL, and return enough provenance to resolve every hit to the exact parent document, exact governed observation, and exact source location?

## Accepted foundation preserved

SR-1 does not reopen the frozen Kernel V1 or accepted RF-2 / RI-2 foundations.

The following remain authoritative:

- `(source_repository_key, source_document_key) -> Resource` is governed logical repository-document identity.
- `ResourceVersion` plus its immutable SHA-256 artifact is exact canonical document evidence.
- `ResourceVersion` identity is unique within a logical Resource by exact content digest; a re-observation of previously seen bytes reuses that exact version.
- Repository import verifies exact manifest-listed Git objects before canonical writes.
- Repository source observations are governed source/classification facts and must remain distinguishable from canonical content identity.
- Retrieval lifecycle and source authority are explicit metadata; they are not inferred from lexical score, path, filename, recency, headings, dates, or generated text.
- `kc_derived.generation` / `generation_source` provide derived-generation lineage and one-current-generation publication fencing.
- serving-time `resource_version_serving_eligible()` remains the final privacy/restriction/deletion fence.
- ordinary clients remain service-only and receive no database, artifact-store, or repository credentials.

## Core SR-1 decisions

1. **Canonical evidence stays whole.** A section/segment is never a new canonical `Resource`, `ResourceVersion`, or copied source document.
2. **Structural segmentation is source-deterministic.** The same exact `ResourceVersion` plus the same structural segmentation profile reproduces the same ordered structural segment identities, coordinates, source-slice digests, heading paths, and structural kinds regardless of lifecycle classification.
3. **Lifecycle/search projection is governed-snapshot-deterministic.** The same structural segments plus the same exact governed observation/classification snapshot and retrieval-projection profile reproduce the same effective lifecycle, inherited source/ranking metadata, and lexical projection.
4. **The source bytes are partitioned, not rewritten.** Segment source spans cover the exact artifact bytes in source order with no overlap and no gaps. Concatenating exact segment slices by ordinal reconstructs the exact parent artifact byte-for-byte.
5. **Markdown structure is deliberately narrow.** V1 uses deterministic ATX-heading structure plus fenced-code awareness. It does not require a general semantic Markdown interpreter.
6. **No model decides segmentation or currentness.** Parent lifecycle comes from governed observation/classification input. Optional section lifecycle comes only from the exact source-controlled declaration grammar below.
7. **Declarations cannot promote effective currentness.** A less-restrictive child declaration is preserved as source evidence but cannot override a more-restrictive document or ancestor state.
8. **PostgreSQL remains baseline retrieval.** Segment lexical search extends RF-2 native full-text search and deterministic ranking.
9. **Publication remains atomic at generation level.** A candidate segment generation is non-serving until all selected supported parent sources and governed projection inputs verify and the generation settles current.
10. **Parent serving fences dominate every child.** Restricting/erasing/fencing a parent `ResourceVersion` or logical `Resource` makes all of its derived segments non-serving even if stale derived rows remain.
11. **SR-2 preserves the RF-2 serving transition.** A previously current whole-document RF-2 generation remains serving until a complete segment generation is published; no empty/partial cutover is allowed.

## Canonical, governed, and derived boundaries

### Canonical content identity

Structural segmentation consumes:

- exact `resource_version_ref`;
- exact immutable artifact bytes;
- `content_digest_algo`, `content_digest`, byte size, media type, and canonical revision identity.

Within one logical `Resource`, an exact previously seen content digest identifies the existing `ResourceVersion`. Re-observation does not manufacture a duplicate exact version.

### Governed retrieval observation/classification

Lifecycle/source-ranking projection consumes an exact governed snapshot containing, directly or by immutable reference, the facts that produced retrieval classification for that version. For repository import this includes at least:

- manifest/observation identity;
- source repository key/locator;
- source document key;
- exact source commit, path, and Git blob;
- exact `resource_version_ref`;
- classification;
- explicit document retrieval lifecycle;
- authority rank;
- rationale and approved source metadata used by retrieval.

The physical representation may use an immutable observation ID, manifest digest plus document key, or another exact stable reference, but a serving generation must make the exact governed snapshot set recoverable. `resource_version_ref` alone is insufficient because the same exact bytes may be re-observed later under a different lifecycle/classification.

### Derived / rebuildable state

Disposable projection state includes:

- structural profile identity/digest;
- retrieval-projection profile identity/digest;
- ordered structural segment rows;
- heading path and structural kind;
- byte/line coordinates;
- exact source-slice digest;
- deterministic segment key;
- source-declared section lifecycle and directive coordinates;
- effective lifecycle and effective-control provenance;
- inherited retrieval annotations copied for ranking/filtering convenience;
- weighted PostgreSQL `tsvector`;
- lexical score;
- derived generation identity and exact governed input lineage.

No derived segment is evidence independent of its exact parent `ResourceVersion` and governed retrieval observation.

## Supported media

SR-2 preserves RF-2's bounded supported media:

- `text/markdown`, strict UTF-8;
- `text/plain`, strict UTF-8.

Unsupported media remain intentionally non-indexable. SR-1 does not define PDF, DOCX, HTML, image, OCR, or other extraction pipelines.

The exact artifact is read through the accepted artifact store and its SHA-256 identity is verified before segmentation. Decoding is strict UTF-8. Canonical bytes are never normalized or rewritten.

## Deterministic profiles and reproducibility

### Structural segmentation profile

Rules that can change structural source partitioning or structural segment identity belong to an explicit structural profile. V1 retains the profile identity:

`kc-section-segmentation-v1`

Its canonical configuration includes at least:

- supported media set;
- strict UTF-8 decoding rule;
- Markdown ATX-heading/fence grammar version;
- large-block split parameters;
- exact segment-key serialization version.

The profile is canonical UTF-8 JSON with sorted object keys, separators `,` and `:` and `ensure_ascii=false`; its identity is `sha256:<hex>` over those exact bytes.

A structural rule change that can alter boundaries, coordinates, structural heading paths, source slices, or segment keys requires a different structural profile digest.

### Retrieval-projection profile

Rules that can change lifecycle/control interpretation, lexical projection, or ranking belong to the retrieval projection configuration. It must identify at least:

- lifecycle-directive grammar version;
- effective-lifecycle reduction rule;
- lexical language/configuration;
- lexical weighting/projection rules;
- deterministic ranking fields/order;
- the structural profile digest used by the generation.

A complete generation's configuration/lineage must bind the structural profile, retrieval projection rules, and exact governed observation/classification snapshots. Operational timestamps and generation UUIDs are not reproducibility inputs.

### Initial size parameters

The V1 structural profile fixes:

- `soft_target_bytes = 16384`;
- `hard_max_bytes = 32768`.

These are byte limits, not token limits.

## Exact line and byte model

Coordinates use:

- `source_byte_start`: zero-based inclusive;
- `source_byte_end`: zero-based exclusive;
- `source_line_start`: one-based inclusive;
- `source_line_end`: one-based inclusive logical line containing the final byte of a non-empty segment.

`LF` and `CRLF` are recognized while exact original bytes remain unchanged. Split points occur only at exact line boundaries, never inside a UTF-8 code point or line-ending sequence.

An empty document produces one deterministic zero-length root segment `[0,0)`, lines `1..1`, with SHA-256 of empty bytes and an empty lexical vector.

## Markdown structural scan

### ATX headings

Outside fenced code, a structural heading requires:

- zero through three leading ASCII spaces;
- one through six `#` characters;
- then ASCII space/tab or end-of-line.

Heading level is the marker count. Display text removes the opening marker/required separator, trims surrounding ASCII whitespace, and removes an optional closing run of `#` only when separated from heading text by ASCII whitespace.

Setext headings are ordinary body text. Front matter, HTML, block quotes, lists, tables, and ordinary comments do not create structure by themselves. Skipped heading levels are allowed; no missing level is invented.

### Fenced code

A fence opener outside a fence has zero through three leading ASCII spaces followed by at least three identical backticks or tildes. A closer uses the same character, at least the opener length, zero through three leading spaces, and only ASCII whitespace after the fence run.

An unclosed fence extends to EOF. Heading-like or control-like text inside a fence is ordinary code/content.

### Heading path

The parser maintains the normal heading-level stack. Each structural segment stores active heading elements with:

- level;
- display text;
- exact source line;
- exact heading byte start/end.

Heading path is navigation/context metadata only. It does not imply lifecycle, authority, truth, or execution permission.

## Base structural blocks

- Bytes before the first recognized heading form one non-empty `preamble` block.
- Every recognized ATX heading begins one `section` block ending immediately before the next recognized ATX heading of any level or EOF.
- Child subsection bytes are separate blocks; hierarchy is carried by heading path, not duplicated content.
- Non-empty Markdown with no recognized ATX heading becomes one root `document` block.
- Non-empty `text/plain` becomes one root `document` block with empty heading path and no Markdown lifecycle declarations.

Every canonical byte belongs to exactly one base block.

## Deterministic large-block continuation

A base block of at most `hard_max_bytes` is emitted whole.

For an oversized block, repeat from the current cursor:

1. If the entire remaining suffix is at most `hard_max_bytes`, emit it whole and terminate.
2. Otherwise consider legal boundaries greater than the cursor and no farther than `hard_max_bytes`, excluding boundaries inside an indivisible fenced-code region.
3. Prefer the eligible blank-line boundary whose resulting piece length is closest to `soft_target_bytes`; ties choose the lower byte offset.
4. If no eligible blank-line boundary exists, choose the greatest eligible ordinary line boundary at or before `hard_max_bytes`.
5. If no legal boundary exists, fail deterministic structural segmentation. This includes an indivisible fenced-code region crossing the hard maximum **and any indivisible UTF-8 source line whose byte length exceeds `hard_max_bytes` without a legal external boundary**.
6. Continue until exhausted.

A boundary is immediately after the complete original line-ending sequence. No byte is dropped or duplicated. The first part retains its base kind; later parts are `continuation`. All parts retain the same heading path. `part_index` is one-based and `part_count` is deterministic.

No tokenizer, embedding model, language model, sentence model, or semantic-similarity algorithm participates.

## Section lifecycle declaration and projection

### Document lifecycle is governed observation input

Each indexed parent has an explicit governed document lifecycle:

- `current`;
- `unknown`;
- `superseded`.

Authority rank, repository/source labels, classification, rationale, and observation metadata remain document/observation scope in SR-2. There is no segment-scope authority override.

### No lifecycle inference

Lifecycle is never inferred from headings such as `Historical`, `Old`, `Deprecated`, `Current`, or `Archive`, nor from dates, paths, filenames, commit recency, prose semantics, or lexical score.

### Exact valid declaration grammar

For Markdown only, the valid declaration forms are:

`<!-- kc:retrieval-lifecycle=current -->`  
`<!-- kc:retrieval-lifecycle=unknown -->`  
`<!-- kc:retrieval-lifecycle=superseded -->`

A valid declaration is recognized only when:

- it is outside fenced code;
- the whole source line, excluding its line ending, matches exactly one of those forms with zero through three permitted leading ASCII spaces and optional trailing ASCII whitespace;
- it is the first non-blank body line immediately after a recognized ATX heading;
- that heading has exactly one declaration.

The declaration line remains in the canonical source slice and its SHA-256. It is omitted only from local lexical search text so control words do not win ordinary searches.

### Ordinary mentions versus attempted controls

The string `kc:retrieval-lifecycle` is **not reserved everywhere in prose**.

The following remain ordinary content and do not trigger control semantics merely because they contain that string:

- prose sentences or paragraphs;
- inline code;
- Markdown block quotes / quoted explanations;
- fenced code;
- examples whose line does not begin as a standalone control-looking HTML comment.

A non-fenced line is a **control-looking attempted directive** when, after zero through three leading ASCII spaces, its first bytes are the reserved HTML-comment control prefix `<!-- kc:retrieval-lifecycle`.

For such an attempted-control line:

- exact valid grammar + exact required position + uniqueness => record the declaration;
- malformed value/syntax => reject lifecycle projection for that parent;
- valid or malformed control-looking line in an invalid position => reject lifecycle projection;
- duplicate attempted declaration for the same heading => reject lifecycle projection.

This narrow rule detects likely control typos without making documentation that merely discusses the token unsegmentable.

### Declared versus effective lifecycle

A source declaration is evidence about that exact source text. It is not rewritten when document classification changes.

Lifecycle restrictiveness order is:

`current < unknown < superseded`

For each section, effective lifecycle is the maximum/more-restrictive value across:

1. governed parent-document lifecycle;
2. every applicable ancestor-section declaration;
3. the section's own declaration, if any.

Therefore:

- parent `current`, child declares `unknown` => effective `unknown`;
- parent `current`, ancestor declares `superseded`, descendant declares `current` => descendant declaration remains `current`, effective remains `superseded`;
- parent `unknown`, child declares `current` => declaration remains `current`, effective remains `unknown`;
- parent later changes from `current` to `superseded` while canonical bytes are unchanged => structural segment identities stay unchanged and every child's effective lifecycle becomes `superseded` in the new governed projection;
- a retained retired/superseded document can always publish historical retrieval without rewriting its canonical section declarations.

A less-restrictive declaration is **not** a structural segmentation error and is not rejected as a lifecycle “promotion attempt.” It simply cannot promote effective lifecycle.

### Declaration/effective provenance

Derived state must preserve enough information to audit both layers:

- governed parent lifecycle and exact governed observation/classification identity;
- section's own declared lifecycle, if any, and exact directive source line/coordinates;
- effective lifecycle;
- whether the effective restriction is controlled by document state, the section's own declaration, or an ancestor declaration;
- controlling directive coordinates when an ancestor/own declaration supplies the effective restriction.

Unlabeled sections have no source declaration. Their effective state is computed from document and ancestor inputs.

## Segment source integrity and identity

Every structural segment records:

- exact parent `resource_version_ref`;
- zero-based `segment_ordinal`;
- structural kind;
- base-block ordinal;
- one-based `part_index` / `part_count`;
- exact byte and line coordinates;
- exact `heading_path`;
- SHA-256 of the exact source slice;
- deterministic `segment_key`.

### Deterministic segment key

The structural segment key is SHA-256 over canonical UTF-8 JSON containing exactly:

```json
{
  "key_version": 1,
  "profile_digest": "sha256:<structural-profile-digest>",
  "resource_version_ref": "canonical-lowercase-uuid",
  "segment_ordinal": 0,
  "source_byte_start": 0,
  "source_byte_end": 123,
  "source_slice_sha256": "..."
}
```

Serialization uses sorted keys, separators `,` and `:` and `ensure_ascii=false`; stored form is `sha256:<hex>`.

Consequences:

- rebuild of the same exact version + same structural profile produces the same structural keys;
- path/rename metadata change with the same exact version does not change keys;
- a previously unseen content representation creates a new `ResourceVersion` and therefore new keys;
- A → B → A reuses A's original exact `ResourceVersion`, therefore A's original structural keys reappear under the same structural profile;
- moving/renaming a heading within newly different document bytes creates or selects the corresponding exact content version and keys for that version;
- identical slice bytes at different coordinates remain distinct by ordinal/coordinates;
- identical artifact bytes in different logical Resources remain distinct because their `resource_version_ref` differs;
- structural profile change produces a new structural key space without mutating canonical evidence.

A segment key is a derived locator, not a permanent cross-version semantic section identity and not an observation identity.

## Exact coverage invariant

For every successfully segmented supported non-empty parent version:

- first segment starts at byte `0`;
- last segment ends at exact artifact size;
- adjacent ranges meet exactly;
- ordinals are contiguous `0..N-1`;
- each slice SHA-256 matches the exact canonical bytes at that range;
- concatenating ranges reconstructs exact parent bytes and parent digest.

## Lexical projection

PostgreSQL full-text search remains fixed to `english` for this baseline.

For each segment:

1. exact local source text, excluding only a recognized lifecycle declaration line, receives weight `A`;
2. active source-derived heading-path display text receives weight `B`.

Conceptually:

```text
setweight(to_tsvector('english', local_search_text), 'A')
||
setweight(to_tsvector('english', heading_context_text), 'B')
```

No copied decoded segment body is required in PostgreSQL. The parent artifact remains the exact text source.

## Derived PostgreSQL representation — contract level

SR-2 may add a separate derived segment-search representation such as:

`kc_derived.resource_segment_text_search`

Required semantics include:

- serving/historical `generation_id`;
- exact parent `resource_version_ref`;
- structural segment ordinal/key/kind/base block/part coordinates;
- exact byte/line coordinates and source-slice SHA-256;
- heading path;
- own declared lifecycle and declaration coordinates when present;
- governed parent lifecycle;
- effective lifecycle and effective-control provenance;
- exact governed observation/classification lineage sufficient to reproduce inherited lifecycle/source metadata;
- inherited authority/source labels;
- weighted `search_vector`.

The exact physical columns may be adjusted in SR-2 to satisfy these semantics. Segment body text must not become copied canonical evidence.

The existing `kc_derived.resource_text_search` remains the RF-2 legacy whole-document projection for historical/transition compatibility.

## Generation and rebuild contract

Segment retrieval remains `DerivedKind.TEXT` so the accepted one-current-text-generation fence remains the publication boundary.

For each selected exact parent version, generation lineage must also identify the exact governed observation/classification snapshot used to project lifecycle, authority, source path/version, and related metadata. Merely listing the `ResourceVersion` is insufficient for complete SR-2 reproducibility.

### Complete-build rule

For every selected supported source:

1. exact parent version and governed observation/classification snapshot resolve;
2. artifact integrity verifies;
3. strict UTF-8 decode succeeds;
4. deterministic structural segmentation succeeds;
5. exact coverage/digest invariants succeed;
6. attempted lifecycle controls validate;
7. effective lifecycle is computed by the monotone most-restrictive rule;
8. inherited source/ranking metadata is projected from the exact governed snapshot;
9. all segment rows and lexical vectors are produced;
10. only then may the candidate generation settle current.

Any failure leaves the previous current generation serving. There is no model fallback, heuristic fallback, silent whole-document substitution, or partial-source publication.

### Rebuild reproducibility

Two different reproducibility claims are intentionally distinguished:

- **Structural rebuild:** same exact parent `ResourceVersion` set + same structural profile => identical ordered structural keys, coordinates, slice digests, heading paths, and structural kinds.
- **Complete retrieval-generation rebuild:** same structural inputs + same exact governed observation/classification snapshot set + same retrieval-projection profile => identical lifecycle/source-ranking/lexical payloads, aside from generation UUID and operational timestamps.

A different governed snapshot may legitimately produce a different effective lifecycle or inherited ranking metadata for the same structural segments and keys.

## RF-2 transition compatibility

Before a complete SR-2 generation is current, accepted RF-2 whole-document retrieval remains serving. A failed candidate cannot change serving results. After successful settlement exactly the new segment projection serves, and old whole-document and new segment rows never mix in one result set.

## Retrieval behavior

Use PostgreSQL `websearch_to_tsquery('english', query)`, `@@`, and `ts_rank_cd()` against only the applicable current text generation.

`include_superseded=false` remains default. Filtering uses effective segment lifecycle:

- `superseded` excluded by default;
- `current` and `unknown` eligible;
- `include_superseded=true` enables historical segment hits.

A document or ancestor restriction always dominates a less-restrictive descendant declaration.

### Deterministic total order

1. lexical score descending;
2. effective lifecycle `current`, `unknown`, `superseded`;
3. inherited `authority_rank` ascending, NULL last;
4. parent `resource_version.created_revision_id` descending;
5. parent `resource_version_ref` ascending;
6. segment ordinal ascending;
7. segment key ascending.

Multiple relevant segments from one parent may appear. Grouping/diversification/semantic reranking/context assembly remain deferred.

### Serving eligibility and response limit

Before emitting a hit, recheck `resource_version_serving_eligible(parent_resource_version_ref)`. A stale row from a fenced parent is suppressed regardless of index membership. Apply the bounded response limit after serving eligibility.

## Privacy fencing, supersession, and derivative cleanup

Three states must not be conflated:

1. **Repository/import supersession or retirement-retain:** historical lifecycle classification. Canonical parent evidence remains. Segment derivatives may remain/rebuild as historical and are excluded by default retrieval.
2. **Privacy `RESTRICT` / `ERASE` fence:** serving access is denied immediately for parent and every child. Serving-time eligibility remains mandatory even if stale derivative rows exist.
3. **Physical canonical purge/erasure:** derivative reconciliation is mandatory and idempotent. After the parent version is actually purged/erased, no segment derivative may remain for that parent.

Derivative cleanup may occur eagerly at restriction time, as the accepted Task 6/RF-2 implementation already does. The contract does not make derivative-row deletion the primary serving fence.

## Retrieval result/API contract

The route remains:

`POST /v1/retrieval/search`

with existing request fields `query`, bounded `limit`, and `include_superseded`.

A segment-mode response must preserve RF-2 parent provenance and add exact child/projection provenance sufficient to recover:

- logical `resource_ref`;
- exact parent `resource_version_ref` and content digest;
- serving generation ID/high-water;
- structural profile digest and retrieval projection identity;
- exact governed observation/classification identity used by the generation;
- segment key/ordinal/kind/base block/part coordinates;
- source byte/line range and slice SHA-256;
- heading path;
- parent lifecycle;
- own declared lifecycle/directive coordinates if present;
- effective lifecycle and effective-control provenance;
- inherited authority/repository/source metadata;
- lexical score.

The API must not expose artifact-store keys/paths, DB credentials, repository credentials, raw SQL, or raw whole-artifact bytes.

## Failure behavior

A candidate fails closed on conditions including:

- missing exact parent version or governed observation snapshot;
- serving-ineligible parent at build time;
- artifact digest mismatch;
- unsupported digest requirement;
- strict UTF-8 failure;
- malformed, misplaced, or duplicate **standalone control-looking lifecycle comment**;
- deterministic structural partition impossible because an indivisible fence or ordinary source line crosses the hard maximum without a legal boundary;
- coverage/coordinate/source-slice digest failure;
- duplicate/non-deterministic structural segment key;
- DB/index write failure;
- generation fencing rejection / late finisher.

A less-restrictive valid declaration under a more-restrictive document/ancestor is **not** a failure; effective lifecycle remains restricted.

On failure the candidate does not become current, prior current retrieval remains serving, and no partial source/segment set is accepted.

## Synthetic SR-2 fixture plan

SR-2 fixtures must include at least:

### `mixed.md`
Current parent, explicit superseded section token `amberlegacy`, current section token `cedarcurrent`, and nested child. Default search excludes `amberlegacy`; historical mode returns it with exact declared/effective provenance.

### `heading-only-lifecycle-negative.md`
A heading named `Historical` without a declaration remains governed solely by document/ancestor lifecycle.

### `lifecycle-parent-downgrade.md`
Contains an own/descendant declaration of `current`. Build once under governed parent `current`, then project the **same exact `ResourceVersion`** under parent `superseded`. Structural keys/coordinates remain identical; effective lifecycle becomes superseded; publication succeeds.

### `lifecycle-ancestor-restriction.md`
Ancestor declares `superseded`, descendant declares `current`. Both declarations remain source-derived; descendant effective lifecycle remains superseded.

### `control-discussion.md`
Contains the reserved token in ordinary prose, inline code, block quotes, and fenced code. All are ordinary content. Separate standalone malformed/misplaced/duplicate control-looking comments fail lifecycle projection.

### `structure.md`
Preamble, nested/skipped ATX levels, Setext-looking text, lists, table, block quote, front-matter-like text, fenced fake headings/controls, and normal headings after the fence. Exact source coverage reconstructs the file.

### `large.md`
Exercises deterministic blank-line/line-boundary continuation and an explicit final suffix that fits the hard maximum and must be emitted whole.

### `oversize-fence.md`
Indivisible fence larger than hard max fails candidate construction and leaves previous generation serving.

### `oversize-line.txt`
One indivisible UTF-8 source line larger than hard max fails deterministically without splitting the line.

### `duplicate.md`
Identical slices at separate coordinates and/or logical Resources prove digest equality does not collapse segment identity.

### `aba-version-history`
Governed import history A → B → A for the same document key proves the final A reuses A's original `ResourceVersion` and structural segment keys while recording a new observation/receipt/generation.

## Tiny real-document pilot

Only after synthetic gates pass, use a tiny explicit manifest pinned to one exact repository commit. Candidate documents may include:

1. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md` — now intentionally valid as a document that discusses the lifecycle token in prose/inline code;
2. `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md` — whole-document superseded source;
3. `docs/architecture/knowledge-core/CURRENT_STATE.md` — mixed temporal prose negative control;
4. `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md` — nested technical Markdown.

Before applying, predeclare source commit/blob proofs, governed observation/classification inputs, expected structural boundary assertions, query outcomes, and current/historical behavior. Do not hand-split source copies.

The existing pre-amendment SR-2 pilot manifest is not automatically accepted by this amendment; pilot selection/expected assertions must be revalidated during the later SR-2 correction pass.

## Falsifiable SR-2 acceptance gates

SR-2 is not accepted until every applicable gate below passes on the amended contract. PostgreSQL gates run on real PostgreSQL. Passing pre-amendment tests is not acceptance evidence for a changed gate.

### SR2-G1 — canonical evidence and governed observation separation
Building/rebuilding segment retrieval creates no new canonical section Resource/ResourceVersion and does not rewrite parent artifact bytes/digest or existing governed observations/bindings. The generation identifies the exact governed observation/classification inputs separately from canonical content identity.

### SR2-G2 — exact deterministic source partition
Structural ordinals/ranges are ordered, gap-free/non-overlapping, slice SHA-256 values match exact artifact bytes, and concatenation reconstructs exact parent bytes/digest.

### SR2-G3 — deterministic heading/preamble structure
Predeclared preamble, ATX blocks, nested/skipped heading paths, source lines, and byte boundaries match exactly; Setext-looking text is not structure.

### SR2-G4 — fence/list/table/control-discussion handling
Fenced heading/control-like text remains ordinary source. Lists, tables, block quotes, front matter, ordinary comments, prose discussion, inline-code control examples, and quoted control examples are not reclassified as lifecycle or authority metadata. Exact coverage still holds.

### SR2-G5 — deterministic large-block continuation and suffix termination
`large.md` follows the fixed soft/hard byte algorithm, every part is within hard max, continuation heading context is preserved, repeated structural builds choose identical boundaries, and a remaining suffix at or below hard max is emitted whole and terminates the split.

### SR2-G6 — indivisible oversized regions fail closed
Both an unbreakable oversized fenced region and an indivisible ordinary UTF-8 line exceeding hard max fail structural segmentation without splitting bytes/lines; previous current retrieval remains serving.

### SR2-G7 — structural identity versus complete-generation reproducibility
Two structural rebuilds from the same exact parent versions and same structural profile produce identical ordered segment keys, coordinates, slice digests, heading paths, and kinds independent of governed lifecycle snapshot. Two complete retrieval-generation rebuilds are required to reproduce lifecycle/source-ranking/lexical payloads only when the exact governed observation/classification snapshot set and retrieval-projection profile also match.

### SR2-G8 — edit/rename/duplicate/A→B→A identity behavior
- path-only metadata change with the same exact `ResourceVersion` preserves structural keys;
- a previously unseen content representation uses a different exact parent version and structural key space;
- A → B → A for one logical Resource reuses A's original version and structural keys while creating a new governed observation/receipt/generation;
- identical slice text at different coordinates has distinct keys;
- identical bytes in different logical Resources remain distinct by parent version identity.

### SR2-G9 — exact parent and governed projection provenance
Every hit resolves to exact logical Resource, exact ResourceVersion/digest/revision, exact governed observation/classification snapshot, approved repository/source metadata, serving generation/profiles, and exact byte/line location. No result is keyed only by path, heading, segment digest, or ResourceVersion without its governed projection provenance.

### SR2-G10 — inherited metadata and no authority escalation
Authority rank and approved source metadata come from the exact governed parent observation. There is no segment authority override. Generated headings/path strings cannot modify authority/currentness.

### SR2-G11 — lifecycle control grammar and no heuristic lifecycle
Exact eligible standalone directives are recognized and source coordinates retained. Ordinary prose, inline code, block quotes/quoted explanations, and fenced examples containing the reserved token remain ordinary content. A standalone control-looking reserved-prefix comment that is malformed, misplaced, or duplicated fails lifecycle projection explicitly. Headings/content never infer lifecycle.

### SR2-G12 — declarations cannot promote effective lifecycle
Less-restrictive valid declarations are preserved rather than rejected. Effective lifecycle is always the most restrictive of governed document lifecycle + all applicable ancestor declarations + own declaration. Test `unknown` document + child `current`, `superseded` document + child `current`, and ancestor `superseded` + descendant `current`; all must publish with effective restriction preserved. Reproject the same exact parent after `current -> superseded`; structural keys remain unchanged and publication succeeds with effective children superseded.

### SR2-G13 — mixed-status current/historical retrieval
Default query returns current/unknown eligible sections and excludes effectively superseded `amberlegacy`. Historical mode recovers the exact segment with unchanged parent/version/structural coordinates plus declared/effective lifecycle provenance.

### SR2-G14 — current-generation publication isolation
A complete candidate settles as the sole current `DerivedKind.TEXT` generation. Older RF-2/segment rows may remain historical but are not mixed. Failed/late candidates never replace newer current state.

### SR2-G15 — RF-2 cutover has no serving gap
RF-2 whole-document retrieval remains usable before first segment settlement and after failed candidate builds. Successful settlement switches atomically to exactly one segment generation.

### SR2-G16 — deterministic segment ranking
Controlled equal/near-equal fixtures prove ordering by lexical score, effective lifecycle, inherited authority, parent canonical revision, parent version ref, segment ordinal, and segment key. Repeated queries against one generation return identical ordered identities.

### SR2-G17 — parent serving fence and derivative reconciliation
After indexing, `RESTRICT`/`ERASE` a parent version/resource and prove immediate parent serving ineligibility suppresses every child before response limiting even if a stale matching derived row is deliberately present. Prove derivative cleanup is idempotent/reconcilable. If the parent is actually physically purged/erased in an applicable fixture, prove no segment derivative remains. Separately prove repository-import supersession/retirement-retain does not invoke privacy purge and remains available only through explicit historical retrieval.

### SR2-G18 — bounded query/service contract
Whitespace-only query is rejected; irrelevant/stop-word-only behavior is bounded; response limit is bounded and applied after eligibility; normal client requires no DB/artifact/repository credentials.

### SR2-G19 — no internal leakage / no copied body
API/OpenAPI does not expose database URLs/credentials, artifact keys/backends/paths, repository credentials/root, raw SQL, or artifact-store internals. Derived state stores structural/projection metadata and `tsvector`, not a copied canonical segment body as evidence.

### SR2-G20 — no model dependency
Build and lexical retrieval pass with no LLM endpoint/key/process, tokenizer, embedding service, or vector database. Structural boundaries/keys and governed lifecycle projection do not vary with model availability.

### SR2-G21 — profile/config change forces correct rebuild without canonical mutation
Changing a structural rule changes structural profile digest and corresponding structural key space. Changing only lifecycle/lexical/ranking projection configuration changes retrieval generation/config lineage without falsely claiming canonical content mutation. Old/new current projections never mix.

### SR2-G22 — tiny real-document pilot
Only after G1-G21 pass, the exact pinned tiny real-document set is segmented/projected by the same machinery. The pilot must prove exact governed observation lineage, literal discussion of `kc:retrieval-lifecycle` does not poison documents, parent-superseded material remains historical, structural handling matches exact source, temporal prose does not infer lifecycle, and no unlisted repository content is imported.

## Explicit deferred work

SR-1/SR-2 do not authorize:

- embeddings/vector search;
- semantic query expansion or model reranking;
- RAG/context-window assembly or answer synthesis;
- model-based lifecycle/currentness classification;
- automatic document discovery/document-key assignment;
- broad ACL/Vera/RiskCardOCR/research/legacy corpus import;
- PDF/DOCX/HTML/image/OCR extraction;
- cross-version semantic section identity/tracking;
- semantic deduplication/diversification;
- segment-scope authority or execution permission;
- Authority integration or autonomous execution;
- production rollout/security/TLS/credential/service-supervision/backup expansion;
- machine-reboot persistence qualification.

A future model may assist semantic retrieval/reranking/synthesis only after deterministic baseline retrieval is accepted. It must not become required for canonical storage, source identity, structural segmentation, governed lifecycle provenance, or baseline lexical retrieval.

## SR-2 implementation boundary after audit

SR-2 is already authorized, but the pre-amendment candidate commit `2c48a0e73c560fad62028776f375c94162e138be` was built against the superseded original SR-1 rules and is **not accepted**.

This documentation amendment intentionally does **not** repair Python, tests, migration state, API schemas, or the real-pilot manifest. The next SR-2 implementation step must first compare that candidate against the amended G1-G22 contract, then make only the minimum corrections required and requalify from synthetic gates through the tiny pilot.

Do not continue into embeddings, RAG, broad import, Authority, execution, or unrelated deployment work.

## Stop boundary for this amendment

**The audit amendment changes the controlling SR-1 contract only. No SR-2 runtime or test fix is authorized by this documentation step itself.**