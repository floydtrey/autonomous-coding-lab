# Knowledge Core — Retrieval / Import Handoff

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **RI-2 minimal governed repository import is implemented and validated. Awaiting separate authorization for RI-3 tiny persistent operational pilot.**

## Accepted checkpoints

- Frozen Kernel V1: `9e904f49480055615bb0cf32360dbdc8400e117c`
- PostgreSQL qualification: `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`
- RF-1 retrieval design: `bf31baddb8efdc90ce7a1f1f4c6420d7b9f2cd3b`
- RF-2 retrieval implementation: `479a918762e919851e19fee3b36cc1d95e78f3e8` — CI `34371352821`
- First curated real-corpus retrieval pilot: `40849bd4de261089a030e09677568c3b4cf1a862` — CI `34373589343`
- Pinned historical-pilot replay fence: `cbbc4f9e89b571f1d6dd7704f68aa393f03f6aa1`
- RI-1 repository-import design: `f7f12c04163ecbe3b6143191008cf393726b8def`
- RI-2 validated implementation: `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad`
- RI-2 CI: `34416061086` — success
- RI-2 completion record: `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md`

## Accepted behavior

Kernel V1 remains frozen and RF-2 retrieval remains unchanged.

RI-2 implements RI-1's stable repository-import identity:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

Path and content hash are not logical identity. Content edits preserve the Resource and create new exact ResourceVersions; rename-only preserves the exact ResourceVersion and adds a locator/source observation; rename+edit requires explicit continuity; different document keys remain distinct even with identical bytes.

Manifest V2 is an explicit allowlist chained to the previous accepted manifest digest. Every previously managed key must remain active or be explicitly retired. Omission is invalid. Retirement is retrieval/import lifecycle, not privacy deletion.

All manifest-listed source objects are verified before import writes, and apply replans/reverifies before publication. The concrete Git reader is host-configured, reads only explicit exact commit/path blobs, accepts regular blobs only, and is qualified for **40-character SHA-1 Git object IDs only**. SHA-256-format Git repository support is not claimed.

Migration `0010_ri2` adds stable document bindings, import receipts, and exact source observations in `kc_control`. Canonical content continues to use existing Resource/ResourceVersion plus immutable artifacts; serving continues to use RF-2 text generations.

Exact accepted-manifest replay is idempotent. Classification-only updates create no ResourceVersion but publish new retrieval metadata. Explicit retirement supports retain-as-historical or exclude-from-retrieval. Failed import before generation publication leaves the previous generation serving; exact retry reconciles safe append-only residue.

Ordinary `create_app()` remains import-incapable. Import requires `create_repository_import_app()` with server-injected governed readers and exposes only `/v1/repository-import/plan` and `/v1/repository-import/apply` in addition to ordinary retrieval. Client contracts contain no repository root/credentials, database URL, or artifact internals.

## Exact RI-2 validation

GitHub Actions run `34416061086` checked out `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad` and passed:

```text
PostgreSQL 18
Alembic 0001_task1 -> 0010_ri2
Fast: 48 passed, 1 intentional historical-pilot skip, 17 deselected
PostgreSQL: 15 passed, 2 intentional historical-pilot skips, 49 deselected
Workflow: success
```

RI2-G1 through RI2-G18 all passed. Detailed gate disposition is in `REPOSITORY_IMPORT_RI2.md`.

## Important limitations

Do not infer capabilities beyond RI-2:

- no broad or production persistent corpus;
- no automatic repository discovery/traversal/globs;
- no automatic classification, document-key assignment, or rename heuristics;
- no SHA-256 Git repository support;
- no separately qualified reactivation-after-retirement behavior;
- replacement/supersedes metadata remains in accepted manifest state rather than a new canonical semantic relationship;
- import currently reuses the existing resource bootstrap whose stable profile name remains `resource-test`;
- no chunk/section retrieval, PDF/DOCX/HTML extraction/OCR, embeddings, RAG, semantic expansion, Authority, or worker execution;
- no production repository credential/network/process-boundary qualification.

## Startup instructions

Before the next repository-import task:

1. Work from `architecture/knowledge-core`.
2. Read root `AGENTS.md`, `docs/START_HERE.md`, and root `docs/CURRENT_STATE.md`.
3. Read:
   - `docs/architecture/knowledge-core/CURRENT_STATE.md`
   - `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI1.md`
   - `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md`
   - `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md`
   - `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF2.md`
   - `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
   - `components/knowledge-core/README.md`
4. Verify branch/HEAD before writing.
5. Preserve frozen Kernel V1, RF-2 retrieval invariants, and RI-2 stable import identity/provenance.
6. Perform only the separately authorized bounded task.

## Next separately authorized task

### RI-3 — tiny persistent operational import pilot

Candidate scope:

- one human-approved Manifest V2;
- only a very small Knowledge Core documentation set;
- server-configured local SHA-1 Git reader;
- deliberately configured persistent local PostgreSQL and immutable artifact storage;
- plan/apply, service/process restart, exact replay, current/historical retrieval, and exact source/import/resource/generation provenance checks;
- record findings and stop.

Do not auto-discover files or expand to broad ACL/Vera/RiskCardOCR import. Chunking, embeddings, RAG, semantic expansion, Authority, and execution remain separate future work.

## Stop boundary

**RI-2 is complete. Do not begin RI-3 or broader import without separate user authorization.**
