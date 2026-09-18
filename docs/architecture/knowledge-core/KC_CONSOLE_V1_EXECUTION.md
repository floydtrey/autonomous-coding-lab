# KC Console V1 — execution task list and C01 checkpoint

Date: 2026-09-18

## Execution identity

- Repository: `floydtrey/autonomous-coding-lab`.
- Confirmed KC source baseline: `73f049bf87174b2fffee00728395eca8e40a0020` on `architecture/knowledge-core`.
- Isolated implementation branch: `kc-console-v1`, created from that exact baseline.
- Source conversation: the current handoff-review conversation. A chat URL/identifier has not been supplied; do not invent one.
- Basis: the uploaded “KC Console V1 — PostgreSQL-first implementation plan,” the external-evidence review, and the subsequent agreement to inventory the pipeline before implementing, without relocating KC yet.
- Current task: **C01, in progress — source contract recorded; host identity pending**. C02, C03 and C07 have not started. The current source review and proposed integration mappings are in [KC_C01_INTEGRATION_CONTRACT.md](KC_C01_INTEGRATION_CONTRACT.md). This is not live tower qualification or a completed C01 gate.

## Product and release boundary

A shortcut opens a small local browser application with Add, Search, recent notes, original-record inspection and basic Status. It uses KC's authorized service interface, not an independent database application.

V1 is finished when the user can open KC, save real information, find it after a KC service restart, inspect the exact original, and export the original plus essential metadata — without a generative, embedding or reranking model service and without Graphiti.

Saving preserves information; it does not verify its claims or adopt it as policy. Originals remain intact. No assistant, automated organization or answer generation is part of V1.

## Task order and status

| Order | Task | Status |
| --- | --- | --- |
| 1 | KC-C01 — Trace the required pipeline and confirm the PostgreSQL integration contract | IN PROGRESS — host identity pending |
| 2 | KC-C02 — Implement Add, recent notes and exact-original inspection | NOT STARTED |
| 3 | KC-C03 — Implement Search, evidence display and basic status | NOT STARTED |
| 4 | KC-C07 — Package daily use and verify the real workflow | NOT STARTED |

The gaps found inside C01 belong to these tasks. Do not turn each gap into a new project or silently expand the release boundary.

## KC-C01 — Required pipeline and integration contract

**Purpose:** Identify what KC already provides, where the working deployment gets it, and the smallest additions the notebook actually needs.

**Scope:**

1. Trace the ordinary note workflow: client/console -> authorized KC service -> canonical PostgreSQL records and original-content artifact store -> text publication/search -> exact-original read. Classify the gateway and graph as optional paths rather than prerequisites.
2. Identify the actual launcher, Python environment, loaded code location, configuration source, database identity and artifact root. Distinguish live evidence from archived/configured values. GitHub-first investigation is preferred; use one narrow tower inventory where live facts cannot be established remotely. Restart/persistence acceptance remains C07.
3. Inventory external files needed by this workflow. For each, record its role, location, repository counterpart and comparison result, or mark that relationship unknown. Distinguish unique required code from matching deployed copies, test evidence, credentials, data, virtual environments and third-party source. Preserve unique required scripts/configuration templates; do not commit secrets or copy the whole archive.
4. Inspect the actual save, search, original-read, recent-notes, status and export operations. Confirm authentication, canonical-write authorization, project/default configuration, retries and duplicate identity. A worker memory candidate is not an explicit user's saved note.
5. Map user-facing metadata to real durable fields. Content is required; title is optional with a first-nonempty-line display fallback; project defaults to a configured authorized Inbox/selected project; category defaults to Note; source description/URLs and original event/publication date are optional; capture time and record/submission IDs are automatic. These are requirements, not presumed API fields. Never modify original content just to insert metadata or invent its source.
6. Select the smallest console location in the existing KC stack. Confirm the required route can operate without any model service or Graphiti. Identify only bounded necessary backend additions. Record path/package/configuration dependencies relevant to a later repository separation; do not perform that migration.

**Deliverable:** A short integration contract with verified operations and mappings, the required-file/runtime map, minimal backend gaps, the console location and outstanding tower checks.

**Done when:** Every V1 screen and export has a verified operation or a specifically bounded missing operation; required runtime files are accounted for or explicitly unresolved; no endpoint, authorization rule, storage location or live status is guessed. Source findings and deployment assumptions are clearly separate. Do not declare C01 complete while an unresolved active-runtime question could cause implementation against the wrong code or storage.

**Excluded:** Repository relocation, moving data, repository-wide architecture review, unrelated ACL work, graph qualification, model selection and redesigning KC.

## KC-C02 — Add, recent notes and original-record inspection

**Purpose:** Make direct capture useful before adding model behavior.

**Scope:** Implement the text-entry form and optional metadata controls, Save to KC, accurate save receipts, recent notes and exact-original display. Add only the C01-confirmed backend gaps necessary for those features, including the authorized user-save path and durable metadata mapping. Keep canonical saving distinct from search-index readiness and worker proposals.

Preserve drafts after failed or uncertain requests. Reuse one submission identity for retries; a deliberately separate save gets a new identity, even when its content is identical. Reuse existing KC idempotency rather than inventing a parallel store. A stored note must not be presented as lost merely because text publication is pending/failed; define its receipt, original-read and recent-note behavior accordingly.

**Deliverable:** Working Add, recent-note and inspection screens backed by KC's canonical storage.

**Done when:** Focused implementation tests cover content and supplied-metadata round trips, whitespace/Unicode preservation, exact-original identity, accurate receipts, failed/uncertain-save draft retention, retry duplicate prevention and intentional separate saves. Automated tests are not live persistence qualification.

**Excluded:** File uploads, website fetching, bulk imports, model-generated metadata, graph extraction, a general document-management system and editing/deleting originals.

**Dependency/location:** C01; GitHub-first implementation and tests on the isolated KC branch.

## KC-C03 — Search, evidence and basic status

**Purpose:** Make stored notes findable without a model.

**Scope:** Wire the search box to the confirmed PostgreSQL-backed text retrieval operation. Show matching records/excerpts, available source details, capture dates and Open original. Do not describe lexical search as semantic or conversational merely because it accepts sentences. The retrieved notes are the answer; no generated answer is added.

Distinguish “No matching notes found” from “Search is unavailable; your query was not completed.” Show required service/storage-operation availability, including the difference between read readiness and write authorization. Do not infer save availability from a healthy search response. Label Graphiti “Not required for this release / integration unverified.”

**Deliverable:** Search, evidence inspection and honest basic operational status.

**Done when:** Tests cover matches, genuine empty results, retrieval failure, opening the correct original and operation without model/Graphiti dependencies.

**Excluded:** New semantic-search infrastructure, agents, query rewriting, graph visualization, generated answers and comprehensive monitoring.

**Dependency/location:** C02; GitHub-first implementation and tests.

**Milestone after C03:** Core notebook functionality is implemented, not yet accepted against the tower's persistent deployment.

## KC-C07 — Daily launcher, export and real-use acceptance

**Purpose:** Make the notebook usable without constructing a sequence of terminal commands.

**Scope:** Provide a saved launcher/shortcut and short guide. Reuse correct running dependencies; explain unavailable dependencies and precise recovery actions. Do not silently reinstall software, start unrelated services or create duplicate servers. Identify/protect or disable the previously observed public read path before sensitive daily use; public access is not a V1 feature.

Provide readable export of captured originals and essential metadata, reusing an existing authorized operation where available. This is a practical recovery aid, not a full disaster-recovery system. Use five genuine notes the user wants to keep, not a new benchmark project.

**Deliverable:** Saved launcher, operating guide, note export and a recorded tower acceptance result.

**Done when:** The user launches the console, saves with an accurate receipt, reopens the console and restarts the relevant KC service without losing the note, finds it through search/recent notes, opens the exact submitted original and obtains a readable export. The workflow runs with model services and Graphiti absent/off. Controlled save-failure tests remain implementation tests; do not deliberately disrupt the user's live database.

**Excluded:** Bulk history ingestion, model evaluation, graph rollout, public access, repository/data relocation and an indefinite pilot.

**Dependency/location:** C01-C03; GitHub-first packaging, then tower deployment and acceptance.

## Deferred — not prerequisites or authorized V1 implementation

- C04: model-assisted organization/correction, with preserved originals.
- C05: verify and connect canonical-note-to-Graphiti-to-evidence retrieval. Standalone graph tests and lexical KC search do not prove this path.
- C06: evidence-grounded generated answers, separate from original records.
- Standalone KC repository migration: after V1 works. Relocate code separately from data, preserve storage identity and verify existing notes before retiring the old installation.
- Cowork lesson repair, new model benchmarks and unrelated ACL tasks.

## Drift controls

Work one task at a time. End each task with changed files, tests actually run, known limits and the next allowed step. Mark progress explicitly; do not imply a task is complete because some files exist. Do not recreate a component until the identified repository and external runtime locations have been checked. Keep new code/configuration KC-owned and avoid new hardcoded dependencies on the ACL checkout. Do not merge into or switch the tower's unrelated working branch. A clean Git checkout is not a data backup. Keep source evidence separate from host evidence.

## C01 checkpoint — initial source audit, 2026-09-18

### Verified at the pinned KC baseline

1. `knowledge_core/api/app.py` composes the existing service and exposes authenticated consumer operations when bootstrap admission is supplied: `POST /v1/kc/store`, `POST /v1/kc/search`, `POST /v1/kc/get-source`, `GET /v1/kc/status`, plus the separate `POST /v1/kc/memory-candidates` proposal route. The notebook must not use that proposal route as Save.
2. `tools/kc_bootstrap_service.py` constructs the SQLAlchemy engine/session factory and LocalArtifactStore from `KNOWLEDGE_CORE_DATABASE_URL` and `KNOWLEDGE_CORE_ARTIFACT_ROOT`. It supplies bootstrap admission but no `canonical_store_authority_evaluator`. `authority/store.py` rejects a missing evaluator, and `api/app.py` maps that condition to HTTP 503 `CANONICAL_STORE_AUTHORITY_UNAVAILABLE`. This is a source-level finding about this launcher, not a claim that the tower currently runs it or that no alternative evaluator exists elsewhere.
3. `application/direct_note_store.py` preserves UTF-8 content through the existing Resource foundation, derives an operation UUID from principal plus idempotency key and replays settled operations with matching request identity. Canonical storage and text publication are separate. A publication failure can leave a canonically stored note with failed/pending text status. The console must keep this distinction visible.
4. `application/consumer_read.py::read_current_source` reads and verifies original artifact bytes, but requires the version to belong to the current TEXT generation and remain serving-eligible. That route alone does not satisfy original inspection for a saved note whose indexing failed or is pending. C01 must specify a bounded authorized canonical-note read path without bypassing eligibility/access checks.
5. `api/store_schemas.py` exposes content, project, source_type, source_id and source_event_time. Optional title, category and source-description fields are not provided by this request contract. Their durable mapping remains to be defined; do not add UI fields that are silently discarded, overload source_id with a citation URL or prepend metadata to the original text.
6. The reviewed standard `api/app.py` plus `_base_app.py` do not expose a consumer recent-notes listing or note-export operation. The low-level resource-version endpoint returns metadata, not the original bytes. Specify minimal additions/reuse; do not expose unguarded low-level routes to work around the consumer boundary.
7. `pyproject.toml` already uses FastAPI and lists Graphiti as an optional extra. The standard bootstrap passes no graph-search binding. This supports reusing the KC stack; model-free import/startup/retrieval still needs the task's implementation/runtime checks rather than being declared proved from packaging alone.

All paths above are under `components/knowledge-core/`. Primary evidence is the actual pinned implementation, not claims in old planning documents.

### Outstanding C01 work at the initial checkpoint — historical progress note

- Identify the actual live launcher/import environment and the safe-to-record database/artifact/configuration identities. Shell defaults and uploaded historical test settings are not substitutes.
- Finish the required external-file inventory and determine whether an existing host-authorized save implementation can be reused.
- Seal the durable metadata mapping, authorized default project, recent-note enumeration/export design and canonical-original access for notes outside the current text index.
- Select the small console composition/authorization arrangement and document focused tests for C02/C03. Do not turn missing host authorization into a global allow-all decision.
- Record the public-gateway privacy action and local-deployment checks for C07.

No KC application behavior, database records, tower services or existing branches were changed in the initial checkpoint. No implementation tests or live persistence tests had been run. That checkpoint created only this isolated branch and its initial execution document.

## C01 checkpoint — source contract recorded, host identity pending

The current [integration contract](KC_C01_INTEGRATION_CONTRACT.md) records verified operations, capture metadata and retry identity, owner admission/default-project requirements, bounded canonical enumeration/original read/export, console placement and the required external-file map. Proposed additions are explicitly distinguished from existing code.

Six exact archive-to-repository file comparisons were performed. The installed Mason CLI/bridge match. The observer archive's API and package configuration differ from the pinned KC implementation; its artifact store and Resource models match. This is not whole-worktree synchronization or active-deployment proof.

The live KC launcher, Python/import location, actual database and artifact directory, and any custom host admission remain unresolved. The previously supplied `Get-KC-C01Inventory.ps1` output ZIP has not been returned. Receive that narrow inventory, resolve only the remaining runtime facts, and finalize C01 before C02. Do not substitute archived settings or the collecting shell's environment for the service's actual configuration.

Changes in this checkpoint are documentation only. No application tests, database writes/migrations, model execution, tower service changes or persistence qualification were performed. All four task boundaries and the deferred repository move remain unchanged.
