# Knowledge Core SR-2 G22 — Tiny Pinned Real-Document Qualification

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Controlling contract:** `SECTION_RETRIEVAL_SR1.md`, gate SR2-G22  
**G1–G21 prerequisite checkpoint:** `7570425231c0f1804c800ad4c6809f6261d82416` — Actions `34457756458` success  
**Pinned source commit:** `bb42835442c03478da2b61c3f79b1c41c26e4e92`  
**Qualified G22 runtime/test/workflow checkpoint:** `c75a6be2e832bdc29fda0e4a6eab7de28da90668`  
**Qualification run:** GitHub Actions `34462565404` — **success**  
**Status:** **SR2-G22 accepted complete. G1–G22 are independently green.**

## Purpose

SR2-G22 is the post-synthetic acceptance pilot required by the amended SR-1 contract. It exercises the accepted SR-2 repository-import, deterministic segmentation, governed lifecycle projection, segment-generation persistence, publication, and PostgreSQL lexical serving path against a tiny immutable set of real repository documents.

It does not broaden the corpus or change the SR-1/KC-D025 architecture.

## Pinned corpus

`SR2_G22_REAL_DOCUMENT_PILOT_MANIFEST.json` pins exactly three Markdown sources from commit `bb42835442c03478da2b61c3f79b1c41c26e4e92`:

| Document key | Exact path | Git blob | Parent lifecycle |
|---|---|---|---|
| `sr2-g22-contract` | `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md` | `d6029b8c81810736c71b49606057a5afb4ef8f65` | `current` |
| `sr2-g22-current-state` | `docs/architecture/knowledge-core/CURRENT_STATE.md` | `c92357c2334ac89b7f79b5ba5620f7f1c8305775` | `current` |
| `sr2-g22-pause-handoff` | `docs/architecture/knowledge-core/SR2_SLICE7_PAUSE_HANDOFF.md` | `d9ed9d01f2c3847632b8aeef58e7d907b02ca622` | `superseded` |

The manifest contains no retirements. No unlisted repository content is authorized or imported by the pilot.

The three sources deliberately provide:

- a current real document containing literal discussion of `kc:retrieval-lifecycle`;
- a current real document containing historical/temporal prose that must not infer lifecycle;
- a real document whose parent lifecycle is explicitly governed as `superseded`.

## Qualification test

`components/knowledge-core/tests/test_sr2_g22_real_document_pilot.py` is marked with both:

```text
postgresql
sr2_real_pilot
```

The normal G1–G21 selectors continue to exclude `sr2_real_pilot`. G22 is executed by its own workflow step:

```text
python -m pytest -q -m "sr2_real_pilot"
```

The test verifies, using the same accepted SR-2 machinery:

1. every source is read from the exact pinned Git commit and matches the exact pinned blob SHA;
2. only the three manifest paths become governed observations and segment-generation sources;
3. each persisted derived source is bound to its exact governed observation, governing manifest, and projection snapshot;
4. deterministic structural segmentation recomputed from exact Git bytes matches persisted segment ordinals, keys, kinds, part metadata, byte/line coordinates, and slice SHA-256 values;
5. concatenating persisted segment byte ranges reconstructs each exact source document without gaps or overlap;
6. literal lifecycle-token discussion in the SR-1 contract produces no section lifecycle declaration and remains effectively `current` under its current parent;
7. historical/temporal prose in `CURRENT_STATE.md` produces no lifecycle declaration and remains effectively `current` under its current parent;
8. the historical pause handoff remains effectively `superseded`, is excluded from default retrieval, and appears only when superseded retrieval is explicitly requested;
9. representative current and historical queries return the expected governed document and exact source provenance;
10. repeated identical searches return stable result identities.

## Initial pilot failure and disposition

Initial candidate commit `f263f72899e35afe48ec41c04092d2ee3e7a3375` ran in Actions `34460547851` and failed only at a pilot query assertion. The query `qualified runtime test workflow checkpoint` required all four PostgreSQL search terms to occur in one segment, which was stricter than the segment-local lexical serving contract.

All source pinning, governed lineage, exact structural reconstruction, lifecycle, corpus-boundary, and historical-serving assertions preceding that query had passed. The failure therefore did not expose a production defect or architecture ambiguity.

The test-only correction changed the current-state query to `qualified runtime`, preserving the intended assertion while respecting segment-local retrieval semantics. No production code, schema, migration, SR-1 rule, or KC-D025 decision changed.

## Accepted qualification evidence

Actions `34462565404`, on exact checkpoint `c75a6be2e832bdc29fda0e4a6eab7de28da90668`, completed successfully:

```text
migrations through 0012_sr2_segments: passed
fast G1–G21 selector: 75 passed, 1 guarded RF-2 skip, 39 deselected
PostgreSQL G1–G21 selector: 36 passed, 2 guarded RF-2 skips, 77 deselected
SR2-G22 selector: 1 passed, 114 deselected
RI-4 restart/replay rehearsal: success
```

The RI-4 rehearsal also reported all required booleans true:

```text
application_reconstruction_verified: true
artifact_integrity_verified: true
current_historical_retrieval_verified: true
exact_replay_verified: true
postgres_restart_verified: true
provenance_verified: true
```

The guarded `test_real_corpus_pilot.py` skips remain the older RF-2 immutable pilot refusing to relabel changed documentation as its historical evidence. They are not G22 skips or failures.

Dependency deprecation warnings and the expected duplicate-operation-key log from idempotency/retry qualification were not acceptance failures and were not broadened into this bounded task.

## Disposition

SR2-G22 is accepted complete. G1–G22 are now independently green without a production-code repair or architecture change.

The next qualification boundary is the intended Windows/PostgreSQL host. The prior RI-4 intended-host evidence qualified RF-2 whole-`ResourceVersion` retrieval; it does **not** by itself qualify SR-2 segment serving. A subsequent bounded host qualification must exercise the accepted SR-2 section-retrieval path rather than relabel the prior RF-2 host run.

## Stop boundary

**Do not infer authorization for embeddings, vector search, RAG/context assembly, broad corpus import, model-based lifecycle inference, automatic classification/document-key assignment, Authority, autonomous execution, or production deployment from G22 acceptance.**
