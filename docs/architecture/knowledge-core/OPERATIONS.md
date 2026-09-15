# Knowledge Core — Operations and Evidence

**Authoritative current KC operating reference.** Start with [CURRENT_STATE.md](CURRENT_STATE.md) and preserve [ARCHITECTURE.md](ARCHITECTURE.md). This document distinguishes recorded acceptance from commands for future authorized work.

## Development and verification

Work from `components/knowledge-core` with Python 3.12+ and an appropriate environment:

```powershell
python -m pip install -e ".[test]"
python -m pytest -q -m "not postgresql and not sr2_real_pilot"
```

For database qualification, use a dedicated disposable PostgreSQL database: the test fixtures truncate KC application schemas. Set `KNOWLEDGE_CORE_DATABASE_URL` and, where applicable, `KNOWLEDGE_CORE_POSTGRES_TEST_URL` for that database, then follow the existing ordered gates:

```powershell
python -m alembic upgrade head
python -m pytest -q -m "postgresql and not sr2_real_pilot"
python -m pytest -q -m "sr2_real_pilot"
```

G22 remains separate from G1–G21. Preserve full Git history for exact pinned corpus objects. The existing [KC workflow](../../../.github/workflows/knowledge-core.yml) applies migrations, runs fast/PostgreSQL/G22 selectors and rehearses RI-4 and SR-2 host restart tools. CI rehearsal is not a replacement for recorded intended-host evidence.

The older RF-2 exact-corpus pilot deliberately skips when current checkout bytes differ from its pinned corpus; that is not permission to rewrite the manifest or relabel the evidence. RI-3, RI-4 and G22 use exact historical Git objects. Their four JSON manifests remain at their original paths with original content; documentation moves do not change their source identities.

For documentation-only changes, verify scope, links/read order, unchanged evidence blobs, manifest pins and non-document bytes. Do not run models, mutate an existing canonical corpus, or rerun completed host acceptance merely to reorganize prose. For behavior changes, run relevant deterministic gates and any separately authorized host qualification required by the changed boundary.

## KC Usable V1 bootstrap operator boundary

Task 1 provides a replaceable bootstrap admission facility. It is not a deployed standalone Authority service and is not attached to every existing low-level KC route. Task 2E composes it with the bounded `POST /v1/kc/store` front door only when the trusted host explicitly supplies `BootstrapAdmission`.

Current bootstrap configuration names are:

| Setting | Current meaning |
|---|---|
| `KNOWLEDGE_CORE_BIND_HOST` | Listener/deployment host selection for the future front-door host. Defaults to `127.0.0.1`; this is configuration, not a permanent architecture invariant. |
| `KNOWLEDGE_CORE_BOOTSTRAP_KEY` | Required shared bootstrap API key. Keep the actual value outside source control, prompts, and KC knowledge content. |
| `X-Knowledge-Key` | Request header carrying the bootstrap API key. |
| `local_owner` | Fixed bootstrap principal emitted after successful admission. It is not the final multi-principal Authority design. |

The admitted operation classes are `kc.store`, `kc.search`, `kc.get_source`, and `kc.status`. Caller-supplied `X-Knowledge-Caller` does not override the bootstrap principal. The existing retrieval Authority evaluator remains a separate downstream seam.

For `kc_store`, the request also carries `Idempotency-Key`. Exact replay must resolve to the same canonical evidence; reuse with different request content/source/project inputs must fail. Do not use Task 1/2E as justification to expose arbitrary entity/assertion/resource CRUD, raw SQL, database credentials, artifact-store authority, FalkorDB credentials, or direct Graphiti mutation.

## Task 2 source-neutral evidence boundary

Task 2A froze the pure-domain governed-source contract in `knowledge_core/domain/governed_sources.py`. Task 2B added durable source-neutral evidence and deterministic legacy repository mapping. Task 2C made the live repository-import service an SR-2 producer that settles corresponding generic governed evidence without weakening exact Git verification. Task 2D moved live SR-2 selection, lineage and publication onto complete source-neutral governed snapshots while retaining repository/Git provenance only as compatibility metadata for repository sources. Task 2E adds the first non-Git producer and authenticated direct-note store front door.

The contract separates source identity, source-to-Resource binding, producer evidence, immutable observation/admission, KC governance decision, project membership and complete retrieval snapshot identity. Snapshot semantic identity binds predecessor, selection policy, selected/excluded evidence and governance, but excludes snapshot record creation time. Evidence, project-membership and snapshot-member ordering are canonicalized so persistence/replay equality follows those semantic rules rather than incidental insertion order.

Task 2B durable state is introduced by migration `0016_governed_source_evidence.py` and includes source-neutral binding, observation, producer-evidence, governance-decision, retrieval-snapshot, snapshot-member, project-membership and exclusion records. Separate legacy mapping records preserve explicit correlation back to existing repository observations, governing selections and receipts rather than mutating historical RI evidence. Task 2D migration `0017_sr2_source_neutral_lineage.py` extends SR-2 generation lineage with generic governed observation, decision and snapshot references while retaining nullable legacy repository observation/manifest fields for compatibility.

Current operating rules:

- repository-specific commit/path/blob/manifest verification remains inside the repository producer;
- direct local notes use authenticated `local_owner` submission evidence plus exact canonical byte custody; do not fabricate Git repository, commit, path, blob or manifest proof;
- new durable source-neutral evidence uses versioned schema/digest semantics rather than changing historical evidence interpretation;
- project membership does not become source identity;
- re-observation of the same ResourceVersion remains distinct evidence;
- one observation cannot be current in one snapshot under competing governance decisions;
- complete-corpus governed snapshots, not producer-local subsets, feed the one-current TEXT publication boundary;
- only settled repository evidence can become accepted repository-derived generic evidence; applying/failed receipts remain ineligible;
- the live repository-import HTTP service uses the SR-2 producer and assembles a complete successor governed snapshot before publication;
- the direct-note producer merges each accepted note into the same complete predecessor-bound corpus, preserving unrelated repository/non-repository members;
- SR-2 candidate construction verifies canonical ResourceVersion/artifact SHA-256, deterministic segmentation, governance decision and snapshot lineage without requiring Git proof for non-Git sources;
- repository sources retain commit/path/blob/manifest provenance as compatibility metadata, but generic SR-2 lineage is authoritative for the source-neutral publication path;
- publication rechecks the governed snapshot predecessor under the generation publication lock before cutover, preventing stale or partial producers from dropping newer current knowledge;
- canonical direct-note Resource/ResourceVersion and governed observation/decision/snapshot evidence settle before derived publication. If SR-2 build/publication fails, the prior current TEXT generation remains serving and the canonical note is retained for exact retry;
- one logical `kc_store` call composes deterministic ledger operations for source Resource creation when needed, ResourceVersion ingest, and a no-canonical-revision governed-admission parent operation, preserving the one-canonical-revision-per-operation invariant;
- exact `kc_store` replay after application reconstruction returns the same canonical Resource/ResourceVersion and serving generation/snapshot; changed reuse of the same idempotency key is rejected;
- successful direct-note inclusion is currently reported as `text_state=indexed`, not `searchable`: the accepted SR-2 generation contains the note, but the public lexical reader/evidence response still inner-joins repository-shaped provenance and is Task 2F work;
- legacy RF-2 remains available for historical qualification/reconstruction from an empty/RF-2 state, but the generation fence rejects RF-2 publication over an established SR-2 current TEXT generation;
- RI-3/RI-4 historical evidence retains its original RF-2 interpretation. Current restart rehearsals are retrieval-mode neutral and validate exact repository provenance, canonical/artifact integrity, serving, lifecycle, restart recovery and replay rather than requiring the obsolete RF-2 physical row shape;
- the SR-2 host rehearsal validates the accepted source-neutral V2 generation/config identity and generic observation/decision/snapshot lineage while still verifying exact repository compatibility provenance and deterministic reconstruction;
- Task 2E does not generalize the lexical read/evidence contract and does not run Graphiti/model work. Task 2F is the next authorized bounded slice.

## Graphiti operator boundary

The optional dependency is installed with `python -m pip install -e ".[test,graphiti]"`. The adapter pins `graphiti-core[falkordb]==0.30.2`. Use an explicitly chosen existing KC database/artifact root with current governed SR-2 sources; apply needed migrations only within the authorized environment.

Available entry points:

| Tool under `components/knowledge-core/tools/` | Purpose |
|---|---|
| `graphiti_host_phase.py` | Lists current canonical sources or runs projection, validation and trusted search; emits result JSON. |
| `graphiti_host_phase_monitored.py` | Wraps host qualification with host resource telemetry. |
| `graphiti_host_phase_live.py` | Preflight, live progress/event journal and final summary around the qualification path. |
| `sr2_host_qualification.py` | Bounded SR-2 restart/recovery with the pinned G22 corpus. |
| `ri4_host_qualification.py` | Historical RI-4 restart/recovery harness; current rehearsal is retrieval-mode neutral while its accepted historical record retains RF-2 semantics. |

To inspect the current source list without touching Graphiti:

```powershell
python tools\graphiti_host_phase.py `
  --artifact-root "<existing KC artifact root>" `
  --list-sources
```

For a subsequent authorized graph run, choose a returned source, a grounded query, explicit namespace/scope and exact intended model configuration. The accepted 2026-09-14 model alias was `graphiti-qwen38-27b-32k`; the tools still default to `graphiti-qwen35-9b-32k`. Explicitly pass `--llm-model` to avoid confusing those profiles. The embedder was `nomic-embed-text:latest`; endpoint defaults are FalkorDB localhost:6379 and Ollama `http://localhost:11434/v1`. Defaults do not establish current host availability or qualification.

The live launcher accepts `--preflight-only`, `--evidence-file`, `--run-root` and `--no-clear` in addition to the source/query/config flags. It writes `events.jsonl` and `summary.json` under the chosen run root / attempt ID. Preserve relevant output before reusing a run directory; observer output is separate from durable KC acceptance evidence. The observer/preflight files added at baseline `d9966e2` are not independently claimed to have been covered by the earlier `6376419` acceptance record.

Inspect durable attempt/validation/binding evidence before recovery. Exact settled replay does not reproject. Changing `--attempt-salt` intentionally creates a new attempt/build and is a recovery decision, not a casual retry. Retain failed, incomplete, pending and quarantined attempts. Never erase failure evidence to produce a clean-looking acceptance history.

A host PASS requires successful projection, complete independent validation, Authority-first retrieval, at least one trusted result and exact canonical correlation. Zero probe results alone need not reject projection validation, but zero final trusted results fails end-to-end host qualification. This documentation does not activate ACL or authorize a new live run.

## Accepted evidence

These are recorded acceptance checkpoints. Linked historical files retain their exact pre-consolidation Git blob bytes; their old next-task prose is historical. Current scope and restart instructions are in [CURRENT_STATE.md](CURRENT_STATE.md).

| Boundary | Exact checkpoint / evidence | Accepted scope |
|---|---|---|
| Kernel V1 | `9e904f49480055615bb0cf32360dbdc8400e117c`; [completion](legacy/IMPLEMENTATION_PLAN_V1.md) | Gates 1–19; frozen kernel semantics. |
| PostgreSQL | `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`; [record](legacy/POSTGRES_QUALIFICATION.md); [Actions 34364589918](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34364589918) | Real migrations, races/locking, idempotency, rollback and generation fencing. |
| RF-2 | `479a918762e919851e19fee3b36cc1d95e78f3e8`; [record](legacy/RETRIEVAL_FOUNDATION_RF2.md); [Actions 34371352821](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34371352821) | Whole-document lexical retrieval. |
| RI-2 | `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad`; [record](legacy/REPOSITORY_IMPORT_RI2.md); [Actions 34416061086](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34416061086) | Bounded governed repository import. Later KC-D025 clarifications do not relabel earlier test coverage. |
| RI-3 / RI-4 | [RI-3](legacy/REPOSITORY_IMPORT_RI3.md), [RI-4](legacy/REPOSITORY_IMPORT_RI4.md), [intended-host evidence](legacy/RI4_INTENDED_HOST_EVIDENCE.md); host harness `934850d5830d4a5d89ec32b04630435a027e816f` | Durable application reconstruction and intended-host PostgreSQL restart/replay for RF-2; not SR-2 evidence. |
| SR-2 G1–G21 | `7570425231c0f1804c800ad4c6809f6261d82416`; [coverage matrix](legacy/SR2_G1_G21_COVERAGE_MATRIX.md); [Actions 34457756458](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34457756458) | Independently green prerequisite for G22. |
| SR-2 G22 | `c75a6be2e832bdc29fda0e4a6eab7de28da90668`; [record](legacy/SR2_G22_QUALIFICATION.md); [Actions 34462565404](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34462565404) | Tiny three-document pinned pilot; G1–G22 accepted. |
| SR-2 intended host | `c3bfac41eb3a1787d5b770274370b5e59f082eb4`; [record](legacy/SR2_INTENDED_HOST_QUALIFICATION.md); [supporting CI 34475309465](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34475309465) | Windows run 2026-09-10: restart/recovery, segment serving, artifact/structure/profile/provenance integrity and replay. |
| Governed Graphiti | `6376419e369ea9ecfe58a19fa233bbfca90ad703`; [accepted 2026-09-14 record](legacy/GRAPHITI_GOVERNED_QUALIFICATION_2026-09-14.md) | 17 segments, 17 bindings, 7 checks, 10 attributed results, zero integrity/lifecycle anomalies. |
| KC Usable V1 Task 1 | `b9e708f2892f3a7303fa50ccadc64c26f5b9bf46`; [Actions 34877670577](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34877670577) | Bootstrap bind configuration, shared-key admission, fixed `local_owner`, bounded operation classes, spoof-resistant principal mapping, and deterministic request rejection. Full existing KC workflow green. Not a full Authority service or remote-exposure qualification. |
| KC Usable V1 Task 2A | `cbfecbfada73e1210ceae0185a31664bf073a479`; [Actions 34923452994](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34923452994) | Source-neutral governed-source pure-domain contract and adversarial Git/note/chat/email/benchmark-shaped fixtures. Full existing KC workflow green. No persistence, migration, serving, Graphiti or public-route behavior changed. |
| KC Usable V1 Task 2B | `6910e9abba320e272b34b0528846f289d3d8eb14`; [Actions 34925025743](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34925025743) | Source-neutral durable evidence/snapshot persistence, migration `0016`, deterministic settled-repository legacy mapping, non-Git-shaped persistence, fail-closed non-settled mapping, replay stability and semantic-order normalization. Full existing KC workflow green. Serving/publication, repository producer wiring, Graphiti and public routes unchanged. |
| KC Usable V1 Task 2C | `30d1ec2ce13ae8c95afc4ac2b9d54d959f36b3bd`; [Actions 34927229037](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34927229037) | Live repository API uses SR-2; SR-2 settlement materializes matching generic governed evidence; generic-mapping failure preserves the prior current generation; replay remains stable; legacy RF-2 cannot replace established SR-2; current RI-3/RI-4 rehearsals are mode-neutral. Full existing KC workflow green. SR-2 downstream source selection/lineage remains repository-shaped for Task 2D. |
| KC Usable V1 Task 2D | `08d76ab86f011c30a103b080b7fce821bf71c45c`; [Actions 34929951401](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34929951401) | Source-neutral SR-2 snapshot selection, generic observation/decision/snapshot lineage via migration `0017`, complete mixed-source successor assembly, non-Git candidate construction without fake Git proof, predecessor-checked atomic publication, prior-generation preservation on stale/failed publication, repository compatibility provenance, and restart/replay qualification. Full KC workflow green. No `kc_store`, direct-note public route, source-neutral lexical response contract or Graphiti generalization yet. |
| KC Usable V1 Task 2E | `9c89e30b9f0fa264180ac57a3e41d01ca0c74699`; [Actions 34931501178](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34931501178) | Authenticated `user_note` `kc_store` front door with fixed `local_owner`, deterministic parent/child idempotency preserving one-canonical-revision-per-operation, exact canonical Resource/ResourceVersion plus generic observation/decision evidence, complete mixed repository+note SR-2 successor publication, exact replay after app reconstruction, changed-key-reuse rejection, and forced derived-failure recovery preserving canonical evidence and prior serving generation. Successful inclusion is `indexed`, not yet public source-neutral `searchable`; no Graphiti/model work. Full KC workflow green. |

The SR-2 intended-host record locates raw JSON at the historical host path `C:\Users\floyd\AppData\Local\KnowledgeCore\sr2-host-qualification-01\SR2_HOST_QUALIFICATION_EVIDENCE.json`. That raw dump is not committed and was not newly inspected during consolidation. The same record excludes machine reboot, backup/restore and production deployment claims.

The Graphiti record preserves namespace `kc:graphiti-governed-document-v1-q1`, scope `project:knowledge-core`, physical partition `kc_da882fc9ed8a7b0764b618562951` and lifecycle inventory digest `sha256:270bc4634d33e12628b317cf16f85a7ab943d0664f04a462aa06bf4a6dddb103`. Earlier attempts `3ecf4f80-201f-5b89-9872-0595d1f4d92f` (incomplete/unvalidated, five warnings) and `0838fb5d-71a5-568d-8668-2900bb1081b3` (interrupted, pending/unvalidated) remain history, not the current accepted attempt.

## Archive and source identity

[legacy/README.md](legacy/README.md) maps every old document path to its preserved archive file and Git blob. Historical cross-references inside those files are left unchanged to preserve exact evidence bytes; resolve them using that map or their original commit. The complete Git history is retained; use `git log --follow -- <archive-path>` or an exact `git show <commit>:<original-path>` for lineage. No history rewrite or evidence deletion is part of this consolidation.

The four retained machine-readable manifests are [RF-2](REAL_CORPUS_PILOT_MANIFEST.json), [RI-3](RI3_PERSISTENT_PILOT_MANIFEST.json), [RI-4](RI4_HOST_QUALIFICATION_MANIFEST.json), and [G22](SR2_G22_REAL_DOCUMENT_PILOT_MANIFEST.json). They are executable evidence inputs, not additional current guidance. Preserve original source paths, commits and blobs even where the current documentation moved.

A file move changes repository presentation only. Existing canonical records/artifacts, governed metadata and Graphiti builds remain untouched. A later documentation import must explicitly govern lifecycle and identity transitions; `legacy/` does not automatically make a source superseded. Keep accepted evidence available for explicit historical retrieval, while directing normal project context to the three current documents.

## Documentation consolidation verification — 2026-09-14

Compared with baseline `d9966e2cfc89b62d7597aee9af085e31e8732878`, this documentation checkpoint preserves all 25 original document blobs in the archive and all 305 non-Markdown tree entries unchanged. The three current documents and repository/component routers passed local link/anchor checks; all 19 historical source/blob pins across the four manifests still resolve exactly. Current-document whitespace checks passed; original Markdown whitespace in frozen evidence was intentionally retained.

The existing fast KC suite passed: **117 passed, 1 guarded RF-2 exact-corpus skip, 40 deselected**. An initial sandbox run could not create temporary fixtures; rerunning with a dedicated temporary directory and appropriate filesystem access passed. Portable source verification reported every component `MATCH`. PostgreSQL, G22 and live-host/model qualification were not rerun for this documentation-only change. No implementation, test, migration, manifest or workflow bytes changed.

## Checkpoint discipline — EG-001 / EG-002

Reserve enough task capacity to update durable documentation, record validation and unresolved issues, commit intended changes, and verify final branch/HEAD/diff before starting another task. A task is not complete while its only state record is a chat. Record material decisions during long work when practical.

At every material checkpoint update current status/next boundary, the architecture only if its contract changed, and this evidence index with exact commits/runs and limits. Do not create a new competing current-state or pause-handoff document. If capacity becomes uncertain, stop implementation early enough to record completed/unverified work and an exact restart point. Preserve incomplete work honestly rather than claiming acceptance.