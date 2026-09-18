# KC-C01 — Notebook integration contract

Date: 2026-09-18  
Status: **SOURCE REVIEW RECORDED; FIRST HOST INVENTORY REVIEWED; STORAGE/LAUNCH IDENTITY STILL PENDING. C01 is not complete.**  
Repository: `floydtrey/autonomous-coding-lab`; working branch: `kc-console-v1`.  
Reviewed branch checkpoint: `9f4dcbf1a306ef18911d721c8dca7d99633d46f1`; application baseline: `73f049bf87174b2fffee00728395eca8e40a0020`.  
Governing task list: `KC_CONSOLE_V1_EXECUTION.md`. Source conversation identifier has not been supplied.

This is the C01 source/configuration contract, not a new implementation or live qualification. It incorporates the supplied external archive and prior response evidence without treating historical runs as current deployment. C02, C03 and C07 remain unstarted. No repository separation, data move, model work or unrelated ACL change is authorized here.

## 1. Required pipeline and reuse boundary

```text
Local notebook UI (new, opt-in)
 -> authenticated owner-facing KC operations (bounded addition)
 -> existing DirectNoteStoreKnowledgeKernel and exact-write authority seam
 -> PostgreSQL Resource / ResourceVersion + governed capture evidence
 -> existing LocalArtifactStore for immutable original UTF-8 bytes
 -> existing complete-corpus SR-2 publication
 -> existing PostgreSQL lexical retrieval / exact evidence
```

The recent-note/original/export path must read authorized canonical captures even when text publication is pending or failed. It must not reconstruct originals from search excerpts or use browser storage as the notebook database.

**Reuse:** `api/app.py`, `application/direct_note_store.py`, the resource/operation and governed-evidence kernels, `artifacts/store.py`, `application/consumer_read.py`, lexical/unified retrieval, existing schemas/migrations and authority interfaces. File paths in this contract are relative to `components/knowledge-core/` unless stated otherwise.

**Not on the required notebook path:** Cowork/Mason, the external APISIX gateway, Graphiti/FalkorDB, Ollama, embedding/reranking services or a new database. The standard launcher supplies no graph binding and packaging makes Graphiti optional. This is source evidence supporting the model-free composition, not an executed clean-environment startup test.

## 2. Verified existing service contract

The following operations exist when the host supplies `BootstrapAdmission`. Successful `X-Knowledge-Key` admission maps to fixed principal `local_owner`; a caller header cannot substitute a different principal. Canonical write authorization is additional, not implied by this key.

| Operation | Existing request / result | Notebook treatment |
| --- | --- | --- |
| `POST /v1/kc/store` | Body: `content`, `project`, `source_type="user_note"`, optional `source_id` and timezone-aware `source_event_time`; header: `Idempotency-Key`. Response includes `stored`, `canonical_state`, source/resource/version IDs, SHA-256 and separate text-publication state. | Reuse canonical producer and exact-write gate. Add only owner admission, capture metadata and receipt fields needed below. |
| `POST /v1/kc/search` | `query`, `limit` (1–50, default 10), `include_superseded` (default false). Results carry exact resource/version IDs, lexical scores/content and optional segment/source provenance. Graph evidence is a separate optional lane. | Reuse lexical retrieval. Display excerpts and provenance, not a generated answer. |
| `POST /v1/kc/get-source` | Exact `resource_version_ref`; returns original content, digest, size and retrieval-generation identity after current-generation membership and serving checks. | Retain existing semantics. A separate bounded canonical-note read is needed for captures outside the serving text index. |
| `GET /v1/kc/status` | Canonical revision, text state/generation/count, retrieval/lineage mode and graph state. | Reuse for read/index state. It does not establish save authorization or report a separate write-capability state. |
| `POST /v1/kc/memory-candidates` | Worker proposal with `pending` / `not_stored` meaning. | Never use as the notebook Save operation. |

The reviewed `api/app.py` and `_base_app.py` do not offer consumer recent-note enumeration or note export. Their low-level ResourceVersion read returns metadata, not original content. Do not work around these gaps by giving the browser raw SQL, artifact paths, or low-level CRUD access.

The current search request has no project or notebook-only filter. V1 may display the existing authorized KC result corpus with accurate source labels; do not silently claim note-only/project-scoped searching. Do not filter a capped result list client-side and then present it as a complete backend search.

## 3. Owner admission and default project

**Verified gap:** `tools/kc_bootstrap_service.py::build_app` supplies bootstrap admission but no `canonical_store_authority_evaluator`. `authority/store.py` treats a missing evaluator as unavailable; `api/app.py` maps it to HTTP 503 `CANONICAL_STORE_AUTHORITY_UNAVAILABLE`. An explicit denial maps to HTTP 403 `CANONICAL_STORE_NOT_AUTHORIZED`. This concerns the standard source launcher; the live host may use another composition that must be identified first.

The existing exact-write request binds principal, deterministic operation ID, project, content SHA-256, optional source ID and event time. `BootstrapContract` has no project registry/default/allowlist; store validation of a nonblank project of at most 255 characters is not project authorization.

**C02 design boundary:** reuse an existing host owner-admission arrangement if the inventory identifies one. Otherwise add a small opt-in console owner admission, separate from the worker bootstrap credential. Authenticate the local owner session; bind its Save action to the exact submission and configured project scope before using the existing producer. Do not install a global allow-all evaluator, trust a browser `approved=true` field, or give worker bootstrap requests the console's permission. Include new metadata in the console submission/authority fingerprint.

Select default project key `inbox` (display label Inbox) for a fresh console configuration, unless the verified host already has an appropriate configured default. The default must be within the host-configured allowed set; project controls expose only that set. This is a proposed configuration choice, not a claim that `inbox` is already configured or authorized on the tower.

Keep UI and owner routes in the existing local FastAPI service, with opt-in registration and same-origin requests. Use authenticated owner sessions and cross-origin request protections; render submitted content as text, not executable HTML. Do not embed backend credentials in static JavaScript, URLs, logs, exports or repository files. No multi-user account platform is required.

## 4. Metadata and submission identity

| UI field | Existing durable support | Required mapping |
| --- | --- | --- |
| Original content | ResourceVersion + SHA-256 artifact; `content` is not stripped by store validation. | Preserve submitted UTF-8 text and line breaks. Never prepend metadata or replace source text with a summary. |
| Title | Not in the direct-note request or governed capture fields. | Nullable user title in immutable capture metadata; otherwise derive a first-nonempty-line display title. Preserve whether a title was user-supplied. |
| Project | Parent store operation result/payload and governed snapshot membership. | Preserve selected project with the capture independently of index success; reuse existing project semantics. |
| Category | No notebook category field; governance classification is a different concept. | Capture metadata, default `Note`; do not reuse governance classification or turn saving into policy approval. |
| Source description / URLs | No direct-note API field; `source_id` is logical identity, not a citation URL. | Optional user-supplied capture metadata. No origin guessing, network fetch or automatic verification. |
| Capture time | `GovernedSourceObservationRecord.observed_at`, set by the server. | Return/export this exact original capture time; retry does not create a new capture time. |
| Original date/time | Existing `source_event_time` requires a timezone-aware datetime. | Preserve date-only input separately as a date with its precision. Use existing event-time field only for an actual timezone-aware timestamp; do not invent midnight or a timezone. |
| Record / submission IDs | Principal + idempotency key produces deterministic operation UUID; source identity defaults to `note-{operation_id}`. Canonical result includes observation and resource/version IDs. | One new opaque submission key per deliberate Save; freeze and reuse the full submission for retries. Return capture/observation identity as well as source/version IDs. |

**Smallest durable extension selected for C02:** an immutable direct-note capture-metadata record in the existing PostgreSQL governed-capture layer, bound to observation/operation identity and exact ResourceVersion. It stores the supplied notebook fields and their versioned request fingerprint, not a second copy of original content. Persist it with settled capture admission; do not acknowledge a complete save while supplied metadata is missing. Existing operation-result/evidence mechanisms remain authoritative for replay.

Do not key metadata only by content hash or ResourceVersion: different captures can reuse bytes while retaining distinct observations. Extend replay identity for new metadata-bearing submissions without changing old requests' digest interpretation. No edits to old migrations or retroactive rewriting of original captures.

An exact retry reuses the same source/resource/version/observation. Different content, project, source date or metadata with the same submission identity is a conflict, not a successful replay. A deliberate identical second Save receives a different key/source identity; content-addressed artifact reuse must not collapse the two notes. If an earlier request's outcome is uncertain, retain its frozen retry payload separately from any edited new draft.

Legacy notes remain readable. Missing title/category/source metadata is displayed as derived/default/unsupplied, not fabricated historical data. Derive legacy project from verified settled evidence where available; otherwise show it as unknown rather than silently assigning Inbox.

## 5. Bounded additions assigned to the existing tasks

### C02 — Add, recent notes, original

- Add opt-in owner admission and the capture-metadata extension above. Reuse canonical operations and authority checks; do not replace the backend.
- Implement canonical-note enumeration using settled direct-note observations, identity/ownership and serving eligibility, not the current TEXT generation. Order by original capture time with a stable identifier tie-breaker; use bounded cursor pagination. Include notes with failed/pending publication and eligible legacy notes.
- Implement exact canonical-note read by capture/version identity, verifying the relationship, authorized scope, Resource/ResourceVersion serving eligibility, artifact size, SHA-256 and UTF-8. This is not unrestricted historical ResourceVersion access. Preserve the existing current-index `get-source` route for other evidence.
- Return a receipt separating canonical settlement from current search readiness. A ready status or configured secret alone is not proof that Save succeeded. Preserve drafts on rejected, failed and uncertain requests.

Proposed placement: static UI under `knowledge_core/console/`, an opt-in router under `knowledge_core/api/`, small capture/read additions beside the existing direct-note application code, one versioned storage extension/migration if needed. These are selected implementation locations, not existing files. Package assets rather than depending on the process working directory or an ACL root path.

### C03 — Search and status

Use the confirmed lexical operation and `resource_version_ref` / governed observation identity for evidence follow-through. Use source provenance's actual capture time and source kind; do not fabricate repository fields for non-Git notes. Add notebook metadata by exact identity, not fuzzy matching titles/text.

A successful empty results list means no matches. Transport, authentication, authorization, database or integrity failure is an unavailable/failed query, never an empty success. Expose bounded read readiness and configured owner-write admission separately; never claim database write durability from a read-only health probe. A save receipt is authoritative for that submitted write. Graph UI label: `Not required for this release / integration unverified`.

### C07 — Export and launcher

Reuse canonical enumeration and exact-original read; do not export only search-index members or the first page of results. A readable JSON export contains original content, supplied metadata, original capture/source times with precision, record/observation/version IDs and content digest. Complete all pages with a fixed capture boundary and recheck serving eligibility; fail explicitly rather than silently emit a successful partial export. This is note recovery aid, not a PostgreSQL/artifact backup system.

Reuse the verified startup environment/configuration and data identity. Do not start a second server merely because a different process owns the expected port, infer a database URL, create a replacement data store, silently migrate/reinstall, or relocate repositories. The gateway's public-read configuration must be disabled/protected before sensitive use; the console does not require that gateway.

## 6. Required-file and external-runtime inventory

Source archive: `mason-kc-test.zip`, SHA-256 `14e6480a183c3ff408eb3c10f8b1703a40419eff6ebfb9a0863bd3235d408a21`.

| Location / group | Verified relationship and treatment |
| --- | --- |
| Repository `components/knowledge-core/` | Pinned implementation, dependencies, migrations, service tools and tests. Use as the source baseline, not a guessed installed copy. |
| `mason-kc-test/knowledge-core-tools/kc.py` | Exact Git blob `f1cf6d3b919c3b773307d181208cbe9eb7ba2b35`, matching repository `tools/mason_kc_cli.py`. Deployed client copy, not missing backend code. |
| `mason-kc-test/knowledge-core-tools/mason_kc_bridge.py` | Exact Git blob `65925e8d32461996a7c9ef63c1c0a6d508065659`, matching repository bridge. Not required to run the browser notebook. |
| `acl-kc-observer/` | Linked worktree according to its archived `.git` pointer. Its archived API and package configuration are not byte-identical to this KC baseline; do not treat it as the current deployment or merge it wholesale. |
| `kc-gateway/service/` and `kc-gateway/apisix/` | Separate forwarding/configuration path; prior archive inspection records read-only forwarding, including unprotected public reads. Preserve as optional external integration. No current repository counterpart/deployment identity established; do not recreate it or make it a notebook dependency. |
| `graphiti/` | Third-party checkout and standalone experiments. Optional, deferred; not required missing notebook code. |
| `.anton/` history/lessons and host manifests | Historical evidence, not active trusted startup policy or qualification of today's deployment. Do not ingest the conflicting lessons as instructions. |
| Credentials and installed environments | Do not commit. Preserve necessary dependency/configuration templates only after identifying the actual runtime. A virtual environment is not the program's authoritative source. |
| Live KC launcher/configuration, PostgreSQL and artifact root | **Unresolved.** The archive/client defaults do not identify the active process and data store. The returned first inventory found no Windows listener on port 8765. Configuration/data pairing remains unresolved; see section 7. |

Additional exact archive comparisons performed during this task:

| Archived observer file | Archive Git blob | Pinned repository Git blob | Result |
| --- | --- | --- | --- |
| `knowledge_core/api/app.py` | `f4d372c208ecdc2afd2a555d67390cc290643cd2` | `ac5a72f6aba5c9ca640e11fec8c5e124d3945b69` | Different |
| `pyproject.toml` | `4848dd538d0c170af4f0fa5b5571e7ed61302211` | `e18e33768ffe3a3a43df0782e2031380db1f64a0` | Different |
| `knowledge_core/artifacts/store.py` | `99885aa0c322eef12247dc7f09ce05fb1d389b62` | same | Exact match |
| `knowledge_core/storage/resource_models.py` | `ddf0e0c028f5c3e2f45227a3aa8a22ce93c34aff` | same | Exact match |

The comparisons prove only these file relationships. They do not establish the entire observer tree's age, synchronization, or active imports. No new required backend implementation was recovered from the archive; the existence of an uncollected custom live launcher remains unresolved.

## 7. Runtime completion gate and later relocation

Before C01 closes, identify the active listener/process and launcher, Python executable/environment and resolved KC module path, source revision or loaded-file identity, configuration source, credential-free database host/port/database identity, actual artifact directory and any external required custom files. Confirm the intended configured project/owner admission. A shell environment value is only a hint unless tied to the service process/configuration.

### First host inventory received and reviewed

Source: `KC-C01-inventory-20260918-073217-1b7afc.zip`, SHA-256 `cc5cf6fb75fcb5f7576e0bc43883a78790b27a1edddfcf515db735aded7fbe78`. Its `inventory.json` was captured at `2026-09-18T12:32:17.7458140Z` (September 18, 2026, 7:32 a.m. America/Chicago). The JSON SHA-256 is `992e1632e4afe2b39721c78e07f36c534630e0b659482cd6170ea39c71f12dc3`.

- `WindowsListeners` and `ListenerAndAncestorProcesses` are empty for the checked port 8765. The recorded warning says no Windows TCP listener was found; the collector did not start a service. This does not establish absence on another port, inside Linux, or loss of stored data.
- All 12 collected Process/User/Machine hints for `KNOWLEDGE_CORE_DATABASE_URL`, `KNOWLEDGE_CORE_ARTIFACT_ROOT`, `KNOWLEDGE_CORE_BOOTSTRAP_KEY` and `KNOWLEDGE_CORE_PORT` have `Present: false`. These are not the environment of a separate running process, and do not rule out shell-local settings or configuration files.
- The shallow listing confirms five KC source/package filenames and three gateway requirement/environment filenames in the locations searched. It neither hashes their code nor proves they are active. No Python/KC import, database connection, artifact-root content or Docker volume was identified.
- Accordingly, host identity is NOT resolved. Do not mark C01 complete, run migrations, create new storage, or start a guessed service configuration.

### Targeted historical candidates, not verified current values

Prior setup conversation records contain two different storage pairings. These are discovery hints from prior setup messages, not new file or live evidence:

| Candidate | Historical database location | Historical artifact root | Startup/configuration leads |
| --- | --- | --- | --- |
| A | `127.0.0.1:55434/knowledge_core_sr2_host` | `%LOCALAPPDATA%\KnowledgeCore\task4-host-qualification-01\artifacts` | `C:\AI\start-kc-cowork-stack.bat`; earlier Docker container named `knowledge-core-sr2-host-62329544d83c` |
| B | `127.0.0.1:55433/knowledge_core_sr2_host` | `C:\KC\sr2-host\artifacts` | `C:\KC\Run_KC_Governed_Qualification.bat`; historical service logs/PID location under `C:\KC` |

The historical server command used Windows Python and `tools/kc_bootstrap_service.py` from the KC component. It supplied settings to that process; the standard launcher itself does not load a `.env` file. Neither the more recent message, a familiar container name, an open port, nor an existing artifact directory is sufficient by itself to select a pairing.

Next host collection: `Get-KC-C01RuntimeCandidates.ps1`, a read-only diagnostic supplied with this checkpoint. It checks the specific historical launcher locations and shallow associated configuration filenames; extracts only allowlisted settings with credentials withheld; reports existence of the two candidate artifact roots without reading notes; lists current listeners on 8765/55433/55434; and requests selected Docker metadata, plus names of running WSL distributions without entering them. It does not execute launchers, run Python/KC imports, start services/containers, query databases, move files, or run migrations. Only a new report/ZIP is written. It has not been executed on the user's Windows host; its own URL/key redaction self-checks must pass before it collects real settings.

After that result, bind one intended existing launcher to its Python/import source and actual database/artifact pair. Resolve any conflict with a narrow identity check, not a fresh empty database or wholesale archive import. If no service is running, explicitly distinguish an identified stopped installation from proof of loaded runtime; record the precise remaining read-only or controlled-start verification before C01 closes.

Relocation dependencies to record: environment/launcher import paths, package assets and migrations, absolute data/configuration roots, and optional gateway upstream settings. Keep the actual database and artifact identity unchanged during a later code move. `LocalArtifactStore` creates its configured root when absent; a newly created empty directory must not be mistaken for recovered knowledge. Repository separation remains deferred.

## 8. Verification and task status

Performed: live GitHub branch/checkpoint read; targeted source/schema/operating-contract inspection; archive-to-repository file hash comparisons; parsing and hashing the returned first Windows inventory. The prior six-file comparison record was preserved, and this continuation additionally confirmed the observer control-model blob matches the pinned source (`c73a4f1e239cd13d64384401de504fa532a5bbdc`). No application behavior changed. No archived serialized code was executed.

Not performed: application unit/integration tests, model-free clean-environment startup, database writes/migrations, independent access to the tower, resolved live imports/configuration, or restart/persistence acceptance. The supplied first Windows inventory was reviewed; it did not resolve an active KC process. A direct source-archive download into the analysis runtime was unavailable; GitHub source reads and selected mounted-archive comparisons were used instead. No test result is inferred from earlier CI or archived responses.

C02/C03 tests must cover owner versus worker admission, denied/default projects, exact original/metadata round trips, legacy notes, identical separate submissions, changed-payload conflicts, interrupted retries, indexing failures with canonical read/list still usable, canonical restrictions during read/export, true empty searches versus failures, and model/graph independence. Use the existing test structure, not another benchmark project. PostgreSQL fixtures can truncate KC schemas: run them only against a dedicated disposable database, never the tower's knowledge database.

**Next allowed action:** inspect the targeted historical runtime candidates, resolve the intended existing installation and storage identity, reconcile only necessary external runtime files, and finalize this contract. C01 remains in progress. Do not start C02 or mark live readiness complete on the strength of this source review.

## Primary source index

All code references were read at the pinned source or at its unchanged documentation-only descendant:

- `tools/kc_bootstrap_service.py`; `api/app.py`; `api/_base_app.py`.
- `api/bootstrap_admission.py`; `api/bootstrap_contract.py`; `authority/store.py`.
- `api/store_schemas.py`; `api/consumer_schemas.py`; `api/retrieval_schemas.py`.
- `application/direct_note_store.py`; `application/consumer_read.py`.
- `storage/resource_models.py`; `storage/governed_source_models.py`; `artifacts/store.py`; `pyproject.toml`.
- Repository `docs/architecture/knowledge-core/ARCHITECTURE.md` and `OPERATIONS.md` for invariants and test-isolation rules; source code takes precedence over stale progress prose.
- Supplied `mason-kc-test.zip` and `KC_EXTERNAL_EVIDENCE_REVIEW.md`; archive observations are not live host observations.


## Continuation artifacts

- `KC_C01_HOST_INVENTORY_REVIEW.json`: credential-free extraction of the submitted inventory findings and exact file comparisons.
- `Get-KC-C01RuntimeCandidates.ps1`: bounded read-only host follow-through, supplied as a conversation attachment; Windows execution remains pending.

This continuation changes documentation only in GitHub. C02/C03/C07 and repository migration remain unstarted. No helper was executed against the tower.
