# Knowledge Core — Retrieval / Import Handoff

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **RI-3 tiny persistent operational pilot is complete. Awaiting separate authorization for RI-4 local-host persistence/recovery qualification.**

## Accepted checkpoints

- Frozen Kernel V1: `9e904f49480055615bb0cf32360dbdc8400e117c`
- PostgreSQL qualification: `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`
- RF-2 retrieval: `479a918762e919851e19fee3b36cc1d95e78f3e8` — CI `34371352821`
- First curated real-corpus retrieval pilot: `40849bd4de261089a030e09677568c3b4cf1a862` — CI `34373589343`
- RI-1 repository-import design: `f7f12c04163ecbe3b6143191008cf393726b8def`
- RI-2 governed importer: `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad` — CI `34416061086`
- RI-3 persistent operational pilot: `de77c2707b283b9765ebde1a369a8da78a5a847c` — CI `34417659798`
- RI-3 completion record: `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI3.md`
- RI-3 fixed allowlist: `docs/architecture/knowledge-core/RI3_PERSISTENT_PILOT_MANIFEST.json`

## Accepted foundation

Kernel V1 remains frozen. RF-2 exact whole-ResourceVersion lexical retrieval and RI-2 governed repository import remain the accepted production-code foundation.

Stable document identity remains:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

RI-2 retains exact SHA-1 Git source verification, explicit Manifest V2 allowlists, manifest chaining, omission safety, explicit lifecycle/authority/classification, stable edit/rename identity, explicit retirements, exact replay, stale-state/source rejection, failed-publication isolation, and generation fencing. Ordinary retrieval clients still receive no repository/database/artifact credentials.

## RI-3 accepted result

RI-3 adds no production Knowledge Core module. It qualifies persistence/replay using the existing RI-2 importer and RF-2 retrieval.

The fixed source commit is `3e675f0ffb584d6b270e0a7c52428c74a5496be3`. The pilot manifest contains only:

1. `CURRENT_STATE.md` as current;
2. `REPOSITORY_IMPORT_RI2.md` as current;
3. `REPOSITORY_IMPORT_RI1.md` as superseded historical.

Process 1 constructs a service against PostgreSQL plus a persistent `LocalArtifactStore`, plans/applies the manifest, verifies retrieval, and verifies exact artifacts/provenance. Process 1 exits.

Process 2 starts with fresh engine/session/store/reader/app/client objects against the same stores. It proves the accepted receipt and same text generation are already serving before replay, reproduces current and historical retrieval, then reapplies the exact manifest. Replay returns the same receipt and creates no additional persistent state.

Accepted snapshot across that process boundary:

```text
3 document bindings
1 settled import receipt
3 source observations
3 Resources
3 ResourceVersions
3 RF-2 search rows
3 persisted SHA-256 artifact files
```

Default retrieval excludes RI-1. Explicit superseded retrieval returns RI-1 with its exact pinned source version/path.

Knowledge Core CI now uses full Git history (`fetch-depth: 0`) because the RI-3 regression pins an immutable historical source commit. This is CI source availability only; repository import remains bounded to manifest-listed exact paths.

## Exact RI-3 validation

Run `34417659798` checked out exact implementation `de77c2707b283b9765ebde1a369a8da78a5a847c` and passed:

```text
PostgreSQL 18
Alembic through 0010_ri2
Fast: 48 passed, 1 expected historical-fixture skip, 18 deselected
PostgreSQL: 16 passed, 2 expected historical-fixture skips, 49 deselected
Workflow: success
```

## Critical boundary

RI-3 proves persistence across **application-process reconstruction while the same PostgreSQL service/database and artifact directory persist**.

It does not prove PostgreSQL server/container restart, machine reboot, store recreation, production filesystem/credential/service configuration, backup/restore, or disaster recovery. CI storage remains temporary at workflow scope.

Do not convert the RI-3 pilot classifications into broad corpus policy without explicit review.

## Startup instructions

Before the next repository-import task:

1. Work from `architecture/knowledge-core`.
2. Read root `AGENTS.md`, `docs/START_HERE.md`, `docs/CURRENT_STATE.md`, and `docs/DEVELOPMENT.md`.
3. Read:
   - `docs/architecture/knowledge-core/CURRENT_STATE.md`
   - `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md`
   - `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI3.md`
   - `docs/architecture/knowledge-core/RI3_PERSISTENT_PILOT_MANIFEST.json`
   - `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md`
   - `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
   - `components/knowledge-core/README.md`
4. Verify branch/HEAD before writing.
5. Preserve frozen Kernel V1, RF-2 semantics, and RI-2 stable import identity/provenance.
6. Perform only the separately authorized bounded task.

## Next separately authorized task

### RI-4 — local-host persistence/recovery qualification

Candidate scope: another tiny explicitly reviewed allowlist using deliberately persistent PostgreSQL and artifact locations on the intended host; prove service/application reconstruction and PostgreSQL/service restart against the same stores, exact replay, current/historical retrieval, artifact integrity, and exact provenance. Backup/restore belongs here only with separate authorization.

Do not broaden into production-scale corpus import, automatic discovery/classification, ACL/Vera/RiskCardOCR import, chunking, embeddings/RAG, Authority, or execution.

## Stop boundary

**RI-3 is complete. Do not begin RI-4 without explicit user authorization.**
