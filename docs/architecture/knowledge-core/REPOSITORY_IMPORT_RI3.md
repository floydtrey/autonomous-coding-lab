# Knowledge Core Repository Import RI-3 — Persistent Operational Pilot

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Starting RI-2 checkpoint:** `3e675f0ffb584d6b270e0a7c52428c74a5496be3`  
**RI-3 pilot implementation:** `de77c2707b283b9765ebde1a369a8da78a5a847c`  
**Implementation CI:** GitHub Actions run `34417659798` — **success**  
**Manifest:** `docs/architecture/knowledge-core/RI3_PERSISTENT_PILOT_MANIFEST.json`  
**Status:** **RI-3 complete as a bounded persistence/replay qualification. No production Knowledge Core Python changed and no broad or production corpus was imported.**

## Purpose

RI-3 tests the already-accepted RI-2 repository importer under a more operational persistence shape. It does not redesign import semantics. The pilot asks whether an exact approved manifest can be applied into PostgreSQL plus filesystem-backed immutable artifact storage, the application can be reconstructed in a separate Python process, the accepted generation can still serve, and the exact manifest can replay without adding state.

## Fixed pilot corpus

The manifest pins exactly three already-governed Knowledge Core Markdown documents to source commit `3e675f0ffb584d6b270e0a7c52428c74a5496be3`:

| Document key | Exact path | Git blob | Lifecycle |
|---|---|---|---|
| `kc-current-state` | `docs/architecture/knowledge-core/CURRENT_STATE.md` | `d6f33cb5aa98888e4c600bbcc7fd71ccb3f37c71` | `current` |
| `kc-ri2-completion` | `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md` | `bc12a15dbac70e1ba538e313ce87dfed41b9e831` | `current` |
| `kc-ri1-design` | `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI1.md` | `457472f7928994ab40e1c8f4faea7e70e93b7449` | `superseded` |

The user authorized RI-3 as a bounded pilot. These classifications are pilot test inputs; this record does not promote them into a broad production corpus policy.

## Pilot shape

`tests/test_ri3_persistent_operational_pilot.py` starts with a migrated PostgreSQL database and a persistent temporary artifact directory. It launches two independent Python processes through `tests/ri3_pilot_process.py`.

### Process 1 — apply

Process 1 reconstructs the database engine/session factory, `LocalArtifactStore`, exact local `GitRepositorySourceReader`, import-capable FastAPI application, and TestClient. It:

1. plans the fixed Manifest V2;
2. applies it through the service boundary;
3. verifies the settled import receipt/current text generation;
4. performs normal and explicit historical retrieval;
5. records resource/import/provenance counts;
6. verifies every persisted artifact through its SHA-256 content address.

### Process 2 — restart/replay

Process 1 exits. Process 2 constructs fresh engine/session/store/reader/app/client objects pointing at the same PostgreSQL database and the same artifact root. Before replay it proves that:

- the settled receipt still exists;
- the same text generation is serving;
- current retrieval still works;
- superseded RI-1 material remains explicitly retrievable.

It then plans and applies the exact same manifest. RI-2 recognizes it as an accepted replay, returns the same receipt, and creates no new durable state.

## Accepted persistent snapshot

After first apply and again after reconstructed-process replay:

```text
repository_document_binding: 3
repository_import_receipt: 1 settled
repository_source_observation: 3
Resource: 3
ResourceVersion: 3
RF-2 search rows: 3
persisted SHA-256 artifact files: 3
```

Every source observation remained tied to the exact pinned source commit/path/Git blob and exact Resource/ResourceVersion. Each ResourceVersion artifact key reverified successfully from the persisted artifact root.

## Retrieval checks

Current-only search for `validated implementation` returned current RI-2/current-state material from the accepted generation and no superseded result.

Search for `falsification` with the default `include_superseded=false` returned no result. The same query with `include_superseded=true` returned exactly `REPOSITORY_IMPORT_RI1.md`, lifecycle `superseded`, with `source_version` equal to the pinned source commit.

The reconstructed second process produced the same serving generation before replay.

## Exact validation

Implementation run `34417659798` checked out exact RI-3 implementation `de77c2707b283b9765ebde1a369a8da78a5a847c` and passed:

```text
PostgreSQL 18
Alembic 0001_task1 -> 0010_ri2: passed
Fast: 48 passed, 1 expected pinned-historical-pilot skip, 18 deselected, 2 upstream warnings
PostgreSQL: 16 passed, 2 expected pinned-historical-pilot skips, 49 deselected, 2 upstream warnings
Workflow: success
```

The additional PostgreSQL test over RI-2 is the RI-3 two-process persistence/replay qualification. The existing historical RF-2 fixture skips remain intentional and unrelated to RI-3.

## CI history requirement

RI-3 deliberately references an immutable historical source commit. A finite shallow checkout would eventually age that source commit out as later branch commits are added. The Knowledge Core workflow therefore uses full Git history (`fetch-depth: 0`) for durable exact-source regression. This changes CI checkout availability only; the importer itself remains bounded to manifest-listed exact paths and does not scan or auto-import repository history.

## What RI-3 proves

RI-3 proves that, while PostgreSQL and the artifact directory remain intact, RI-2 import state, immutable artifact bytes, generation state, retrieval behavior, exact provenance, and replay idempotency survive complete reconstruction of the Knowledge Core application in a separate Python process.

## What RI-3 does not prove

RI-3 does **not** qualify:

- PostgreSQL server/container restart or machine reboot persistence;
- destruction/recreation of either persistent store;
- backup/restore or disaster recovery;
- production filesystem paths, permissions, service accounts, secrets, TLS, firewalling, repository credentials, or service supervision;
- production approval of this three-document pilot classification as a broader corpus policy;
- automatic repository discovery/classification/document-key assignment;
- broad ACL/Vera/RiskCardOCR/research/legacy import;
- SHA-256-format Git repositories;
- chunking/section lifecycle, PDF/DOCX/HTML extraction/OCR, embeddings/vector search, or RAG;
- Authority integration or autonomous execution.

The PostgreSQL service and artifact directory used by CI are temporary to the workflow run; persistence is demonstrated across application-process boundaries inside that controlled run, not across GitHub-hosted runner replacement.

## Next separately authorized task

Candidate **RI-4 — local-host persistence/recovery qualification**: use another tiny explicitly reviewed manifest with deliberately persistent PostgreSQL and artifact locations on the intended host, prove service/database restart against the same stores, exact replay, current/historical retrieval, and provenance. Backup/restore should be included only if separately authorized.

## Stop boundary

**RI-3 is complete. Do not begin RI-4, production deployment, or broader corpus import without separate user authorization.**
