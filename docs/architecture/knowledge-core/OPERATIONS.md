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

## Graphiti operator boundary

The optional dependency is installed with `python -m pip install -e ".[test,graphiti]"`. The adapter pins `graphiti-core[falkordb]==0.30.2`. Use an explicitly chosen existing KC database/artifact root with current governed SR-2 sources; apply needed migrations only within the authorized environment.

Available entry points:

| Tool under `components/knowledge-core/tools/` | Purpose |
|---|---|
| `graphiti_host_phase.py` | Lists current canonical sources or runs projection, validation and trusted search; emits result JSON. |
| `graphiti_host_phase_monitored.py` | Wraps host qualification with host resource telemetry. |
| `graphiti_host_phase_live.py` | Preflight, live progress/event journal and final summary around the qualification path. |
| `sr2_host_qualification.py` | Bounded SR-2 restart/recovery with the pinned G22 corpus. |
| `ri4_host_qualification.py` | Earlier RF-2 whole-document restart/recovery qualification. |

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

These are preserved checkpoint records, not new test results from this documentation update. All linked historical files retain their exact pre-consolidation Git blob bytes. Their old next-task prose is historical; current scope is in [CURRENT_STATE.md](CURRENT_STATE.md).

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
