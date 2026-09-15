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

G22 remains separate from G1–G21. Preserve full Git history for exact pinned corpus objects. The existing [KC workflow](../../../.github/workflows/knowledge-core.yml) applies migrations, runs fast/PostgreSQL/G22 selectors and rehearses RI-4 and SR-2 host restart tools. CI rehearsal is not a replacement for separately recorded intended-host evidence.

The older RF-2 exact-corpus pilot deliberately skips when current checkout bytes differ from its pinned corpus; that is not permission to rewrite its manifest or relabel historical evidence. RI-3, RI-4 and G22 use exact historical Git objects. Their retained machine-readable manifests keep original source paths, commits and blob identities.

For documentation-only changes, verify scope, links/read order, unchanged evidence blobs, manifest pins and non-document bytes. Do not run models, mutate an existing canonical corpus, or rerun completed intended-host acceptance merely to reorganize prose. For behavior changes, run relevant deterministic gates and any separately authorized host qualification required by the changed boundary.

## KC Usable V1 bootstrap operator boundary

Task 1 provides a replaceable bootstrap admission facility. It is not a deployed standalone Authority service and is not attached to every low-level KC route.

| Setting | Current meaning |
|---|---|
| `KNOWLEDGE_CORE_BIND_HOST` | Listener/deployment host selection; defaults to `127.0.0.1`. Configuration, not permanent topology. |
| `KNOWLEDGE_CORE_BOOTSTRAP_KEY` | Shared bootstrap API key. Keep the actual value outside source control, prompts and KC knowledge content. |
| `X-Knowledge-Key` | Request header carrying the bootstrap API key. |
| `local_owner` | Fixed bootstrap principal after successful admission; not the final multi-principal Authority design. |

The admitted operation classes are `kc.store`, `kc.search`, `kc.get_source`, and `kc.status`. Caller-supplied `X-Knowledge-Caller` does not override the bootstrap principal. The existing retrieval Authority evaluator remains a separate downstream seam.

`POST /v1/kc/store` is implemented when the trusted host explicitly supplies `BootstrapAdmission`. It requires `Idempotency-Key`. Exact replay must resolve to the same canonical source/Resource/ResourceVersion/observation/decision evidence; reuse with changed content/source/project inputs must fail. Derived generation/snapshot identity is not part of that idempotency guarantee and may advance during retry/recovery or another accepted complete-corpus publication.

Do not use the bootstrap path as justification to expose arbitrary entity/assertion/resource CRUD, raw SQL, database credentials, artifact-store authority, FalkorDB credentials, direct Graphiti mutation, or remote access without a separate bounded decision.

## Task 2 source-neutral evidence and lexical boundary

Task 2A froze the pure-domain governed-source contract. Task 2B added durable source-neutral evidence and deterministic legacy repository mapping. Task 2C made repository import a verified producer of generic evidence. Task 2D moved live SR-2 selection/lineage/publication to complete generic snapshots. Task 2E added the first non-Git producer and authenticated direct-note store. Task 2E.1 corrected audit findings before read-side work. Task 2F now completes the source-neutral lexical evidence/serving boundary.

Current operating rules:

- repository commit/path/blob/manifest verification remains inside the repository producer;
- complete-corpus selection policy and select/exclude overlap validation belong to the generic governed snapshot seam, not the repository adapter;
- direct notes use authenticated `local_owner` submission evidence plus exact canonical byte custody; do not fabricate Git proof;
- source identity, canonical Resource/Version, observation, decision, project membership and corpus snapshot identity remain separate;
- project membership does not become source identity; same-source direct-note updates preserve/union prior project memberships;
- direct-note project keys are bounded to 255 characters before canonical writes;
- re-observation of the same ResourceVersion remains distinct evidence;
- one observation cannot be selected in one snapshot under competing governance decisions;
- complete-corpus snapshots, not producer-local subsets, feed the one-current-TEXT publication boundary;
- only settled repository evidence can become accepted repository-derived generic evidence;
- SR-2 candidate construction verifies canonical ResourceVersion/artifact SHA-256, strict UTF-8, deterministic segmentation, governance decision and snapshot lineage without requiring Git proof for non-Git sources;
- repository fields on generic SR-2 lineage/segments are compatibility metadata, not generic identity;
- publication rechecks expected governed-snapshot predecessor under the generation lock before cutover;
- a serving-predecessor race is retryable and `kc_store` reports `text_state=pending`; other derived build/invariant failures report `text_state=failed`;
- canonical note evidence settles before derived publication; failed/pending publication does not erase canonical evidence or the prior valid serving generation;
- one logical `kc_store` call composes deterministic child operations for Resource creation/ResourceVersion ingest plus a no-canonical-revision governed-admission parent operation, preserving one-canonical-revision-per-operation;
- `text_state=indexed` means the requested note was included in a successfully published TEXT generation. After Task 2F, notes in the accepted current SR-2 generation are searchable through the accepted lexical contract;
- legacy RF-2 remains available for historical reconstruction from an empty/RF-2 state but cannot publish over established SR-2;
- historical RI-3/RI-4 evidence retains original RF-2 interpretation. Current restart rehearsals are retrieval-mode neutral;
- the SR-2 host rehearsal validates source-neutral V2 generation/config and generic observation/decision/snapshot lineage while retaining exact repository compatibility provenance.

### Task 2F lexical serving rules

The public lexical response advertises `evidence_contract_version="kc-lexical-evidence-v2"`.

For current source-neutral SR-2 generations:

- segment provenance advertises `provenance_contract_version="governed-source-sr2-v2"`;
- before lexical matches are served, KC loads every current `TextGenerationSource`, requires complete generic observation/decision/snapshot/projection lineage, requires one governing snapshot, reconstructs that snapshot through the generic governed-evidence kernel, and compares the exact ResourceVersion set to both the generation lineage rows and canonical generation-source set;
- each lineage row must exactly match generic observation, governance decision, snapshot and projection digest plus any explicit repository compatibility mapping;
- any partial/mixed generic lineage, multiple-snapshot ambiguity, missing ResourceVersion ownership, source-set mismatch or tampered lineage fails closed;
- matching segment metadata must agree with the generic governance decision and any exact repository compatibility projection;
- exact canonical artifact byte size/SHA-256 and segment slice SHA-256 are rechecked when content is served;
- parent Resource/ResourceVersion serving eligibility is rechecked after lexical matching, so privacy restriction/erasure dominates stale derived rows;
- direct notes expose generic source kind/origin/collection/item identity, project memberships, producer/version, generic observation ID/digest, governance decision ID/digest, snapshot/projection digests, source times, governance policy/rationale/time and exact structural/lifecycle coordinates;
- direct-note repository/path/version/manifest fields stay null;
- repository-backed V2 results expose the same generic evidence plus exact repository compatibility fields. To retain accepted repository consumer/G22 behavior, `segment.governed_observation_id` remains the legacy verified repository observation ID when a legacy mapping exists; `segment.governed_source_observation_id` is the unambiguous generic observation ID;
- accepted historical pre-2D SR-2 generations with no generic lineage stay on explicit `repository-sr2-v1` provenance. They are not silently relabeled as V2;
- public search remains Authority-first through the existing injected retrieval evaluator. Task 2F did not create bootstrap `kc_search`; that is Task 3.

Focused 2F qualification additionally proves:

- repository and direct-note content are jointly searchable in the same accepted current generation;
- the same mixed corpus remains searchable after application/session reconstruction;
- no artifact-store path/backend, database URL or raw SQL detail is exposed in the tested public responses;
- a restricted direct-note Resource disappears from retrieval while an unrelated repository result remains serving;
- tampering with generic projection lineage causes retrieval to fail closed;
- two public `kc_store` writers forced against one predecessor deterministically produce one published result and one retryable `pending`; exact replay of the pending request preserves canonical Resource/Version identity and publishes a successor containing both notes;
- existing Task 2E/2E.1 tests retain publication-failure durability, changed-idempotency reuse rejection, project-union and retryability classification coverage.

Task 2 is accepted through this boundary. **Task 3 is the next authorized slice.** Do not absorb Task 3 bootstrap read tools, Graphiti mixed-source work, Mason integration or new source connectors into Task 2 maintenance.

## Graphiti operator boundary

The optional dependency is installed with:

```powershell
python -m pip install -e ".[test,graphiti]"
```

The adapter pins `graphiti-core[falkordb]==0.30.2`. Use an explicitly chosen existing KC database/artifact root with current governed SR-2 sources; apply needed migrations only within the authorized environment.

Available entry points under `components/knowledge-core/tools/`:

| Tool | Purpose |
|---|---|
| `graphiti_host_phase.py` | Lists current canonical sources or runs projection, validation and trusted search; emits result JSON. |
| `graphiti_host_phase_monitored.py` | Wraps host qualification with host resource telemetry. |
| `graphiti_host_phase_live.py` | Preflight, live progress/event journal and final summary. |
| `sr2_host_qualification.py` | Bounded SR-2 restart/recovery with the pinned G22 corpus. |
| `ri4_host_qualification.py` | Historical RI-4 restart/recovery harness; current rehearsal is retrieval-mode neutral while accepted historical record retains RF-2 semantics. |

To inspect source list without touching Graphiti:

```powershell
python tools\graphiti_host_phase.py `
  --artifact-root "<existing KC artifact root>" `
  --list-sources
```

The accepted 2026-09-14 graph run used LLM alias `graphiti-qwen38-27b-32k`, embedder `nomic-embed-text:latest`, Graphiti `0.30.2`, ruleset `kc-graphiti-governed-document-v3`, validator version `3`. Tool defaults can name an older 9B alias; explicitly choose model configuration for any future authorized run.

Inspect durable attempt/validation/binding evidence before recovery. Exact settled replay does not reproject. Changing attempt salt intentionally creates a new attempt/build and is a recovery decision, not a casual retry. Retain failed, incomplete, pending and quarantined attempts. Never erase failure evidence to produce a clean-looking acceptance history.

A host PASS requires successful projection, complete independent validation, Authority-first retrieval, at least one trusted result and exact canonical correlation. The Task 2 lexical acceptance does not qualify mixed-source Graphiti input; that is Task 4.

## Accepted evidence

These are recorded acceptance checkpoints. Linked historical files retain their exact pre-consolidation scope. Current scope and restart instructions are in [CURRENT_STATE.md](CURRENT_STATE.md).

| Boundary | Exact checkpoint / evidence | Accepted scope |
|---|---|---|
| Kernel V1 | `9e904f49480055615bb0cf32360dbdc8400e117c`; [completion](legacy/IMPLEMENTATION_PLAN_V1.md) | Gates 1–19; frozen kernel semantics. |
| PostgreSQL | `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`; [record](legacy/POSTGRES_QUALIFICATION.md); [Actions 34364589918](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34364589918) | Real migrations, races/locking, idempotency, rollback and generation fencing. |
| RF-2 | `479a918762e919851e19fee3b36cc1d95e78f3e8`; [record](legacy/RETRIEVAL_FOUNDATION_RF2.md); [Actions 34371352821](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34371352821) | Whole-document lexical retrieval. |
| RI-2 | `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad`; [record](legacy/REPOSITORY_IMPORT_RI2.md); [Actions 34416061086](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34416061086) | Bounded governed repository import. |
| RI-3 / RI-4 | [RI-3](legacy/REPOSITORY_IMPORT_RI3.md), [RI-4](legacy/REPOSITORY_IMPORT_RI4.md), [intended-host evidence](legacy/RI4_INTENDED_HOST_EVIDENCE.md); host harness `934850d5830d4a5d89ec32b04630435a027e816f` | Durable application reconstruction and intended-host PostgreSQL restart/replay for historical RF-2. |
| SR-2 G1–G21 | `7570425231c0f1804c800ad4c6809f6261d82416`; [coverage matrix](legacy/SR2_G1_G21_COVERAGE_MATRIX.md); [Actions 34457756458](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34457756458) | Independently green prerequisite for G22. |
| SR-2 G22 | `c75a6be2e832bdc29fda0e4a6eab7de28da90668`; [record](legacy/SR2_G22_QUALIFICATION.md); [Actions 34462565404](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34462565404) | Tiny three-document pinned pilot; G1–G22 accepted. |
| SR-2 intended host | `c3bfac41eb3a1787d5b770274370b5e59f082eb4`; [record](legacy/SR2_INTENDED_HOST_QUALIFICATION.md); [supporting CI 34475309465](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34475309465) | Windows restart/recovery, segment serving, artifact/structure/profile/provenance integrity and replay. |
| Governed Graphiti | `6376419e369ea9ecfe58a19fa233bbfca90ad703`; [accepted record](legacy/GRAPHITI_GOVERNED_QUALIFICATION_2026-09-14.md) | 17 segments, 17 bindings, 7 checks, 10 attributed results, zero integrity/lifecycle anomalies for its exact repository-shaped input. |
| KC Usable V1 Task 1 | `b9e708f2892f3a7303fa50ccadc64c26f5b9bf46`; [Actions 34877670577](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34877670577) | Bootstrap bind/key, fixed `local_owner`, bounded admitted operations, spoof-resistant mapping. Full workflow green. |
| KC Usable V1 Task 2A | `cbfecbfada73e1210ceae0185a31664bf073a479`; [Actions 34923452994](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34923452994) | Source-neutral governed-source pure-domain contract and adversarial source-shaped fixtures. |
| KC Usable V1 Task 2B | `6910e9abba320e272b34b0528846f289d3d8eb14`; [Actions 34925025743](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34925025743) | Migration `0016`; source-neutral durable evidence/snapshot persistence and deterministic settled-repository mapping. |
| KC Usable V1 Task 2C | `30d1ec2ce13ae8c95afc4ac2b9d54d959f36b3bd`; [Actions 34927229037](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34927229037) | Live repository SR-2 producer, generic evidence settlement, mapping-failure rollback, RF-2 downgrade fence. |
| KC Usable V1 Task 2D | `08d76ab86f011c30a103b080b7fce821bf71c45c`; [Actions 34929951401](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34929951401) | Migration `0017`; source-neutral SR-2 selection/lineage/publication, mixed-source complete snapshots, non-Git generation without fake Git proof, predecessor fencing and restart/replay. |
| KC Usable V1 Task 2E | `9c89e30b9f0fa264180ac57a3e41d01ca0c74699`; [Actions 34931501178](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34931501178) | Authenticated direct-note `kc_store`, deterministic canonical idempotency, complete mixed corpus publication and derived-failure recovery. |
| KC Usable V1 Task 2E.1 | `c0864a1d1ed76bdd5e289308f85f2b8b4d0499ba`; [PR Actions 34934614070](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34934614070); [post-merge Actions 34935097246](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34935097246) | Pre-2F audit corrections: generic snapshot-policy ownership, retryable predecessor conflicts, fail-vs-pending, project bound/union and corrected canonical idempotency guarantee. |
| **KC Usable V1 Task 2F** | **`f48200f50ee1c2652e32b56592f6ad86fe83c898`; [Actions 34936164155](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34936164155)** | **`kc-lexical-evidence-v2`; complete V2 lineage validation before serving; mixed repository+note public search and reconstruction; honest null non-Git repository fields; explicit historical repository mode; G22 compatibility alias + distinct generic observation ID; artifact/slice/eligibility rechecks; lineage-tamper fail-closed; restriction dominance; concurrent store convergence. Migrations, fast suite, PostgreSQL qualification, G22, RI-4 and SR-2 restart/replay all green. No Graphiti or Task 3 front-door work.** |

The SR-2 intended-host record locates raw JSON at the historical host path `C:\Users\floyd\AppData\Local\KnowledgeCore\sr2-host-qualification-01\SR2_HOST_QUALIFICATION_EVIDENCE.json`. That raw dump is not committed and was not newly inspected during Task 2F. Historical intended-host acceptance excludes machine reboot, backup/restore and production deployment claims.

The Graphiti record preserves namespace `kc:graphiti-governed-document-v1-q1`, scope `project:knowledge-core`, physical partition `kc_da882fc9ed8a7b0764b618562951` and lifecycle inventory digest `sha256:270bc4634d33e12628b317cf16f85a7ab943d0664f04a462aa06bf4a6dddb103`. Earlier failed/interrupted attempts remain history, not acceptance.

## Archive and source identity

[legacy/README.md](legacy/README.md) maps old document paths to preserved archive files and Git blobs. Historical cross-references inside frozen evidence may retain original paths; resolve them using that map or exact Git history. No history rewrite or evidence deletion is part of current work.

The four retained machine-readable manifests are [RF-2](REAL_CORPUS_PILOT_MANIFEST.json), [RI-3](RI3_PERSISTENT_PILOT_MANIFEST.json), [RI-4](RI4_HOST_QUALIFICATION_MANIFEST.json), and [G22](SR2_G22_REAL_DOCUMENT_PILOT_MANIFEST.json). They are executable evidence inputs, not additional current guidance.

A file move changes repository presentation only. Existing canonical records/artifacts, governed metadata and graph builds remain untouched. A later documentation import must explicitly govern lifecycle and identity transitions; `legacy/` does not automatically make a source superseded.

## Checkpoint discipline — EG-001 / EG-002

Reserve enough task capacity to update durable documentation, record validation and unresolved issues, commit intended changes, and verify final branch/HEAD/diff before starting another task. A task is not complete while its only state record is a chat.

At every material checkpoint update current status/next boundary, the architecture only if its contract changed, and this evidence index with exact commits/runs and limits. Do not create a competing current-state or pause-handoff document. If capacity becomes uncertain, stop implementation early enough to record completed/unverified work and an exact restart point. Preserve incomplete work honestly rather than claiming acceptance.
