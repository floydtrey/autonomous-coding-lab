# Knowledge Core Repository Import RI-4 — Local-Host Persistence / Recovery Qualification

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Starting RI-3 checkpoint:** `3d12f205d15c310bce0718c56c0866befccd90ec`  
**RI-4 harness checkpoint:** `934850d5830d4a5d89ec32b04630435a027e816f`  
**CI rehearsal:** GitHub Actions run `34418809968` — **success**  
**Manifest:** `docs/architecture/knowledge-core/RI4_HOST_QUALIFICATION_MANIFEST.json`  
**Intended-host evidence:** `docs/architecture/knowledge-core/RI4_INTENDED_HOST_EVIDENCE.md` — **success**  
**Status:** **RI-4 accepted complete. The intended Windows host reproduced the CI-proven restart/recovery behavior with persistent PostgreSQL and artifact state.**

## Purpose

RI-4 closes the remaining persistence gap left by RI-3: PostgreSQL itself must restart while canonical/import/generation state remains on a persistent database volume, the Knowledge Core application must be reconstructed afterward, and the same persistent artifact directory must continue to verify.

This remains a qualification exercise, not production deployment.

## Fixed RI-4 allowlist

The manifest pins exactly three already-governed Knowledge Core Markdown files to source commit `3d12f205d15c310bce0718c56c0866befccd90ec`:

| Document key | Exact path | Git blob | Lifecycle |
|---|---|---|---|
| `kc-current-state-ri4` | `docs/architecture/knowledge-core/CURRENT_STATE.md` | `16555df9ac80ec739dcf5cf2a5937d14c176b06b` | `current` |
| `kc-ri3-completion-ri4` | `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI3.md` | `f4b7f1a56086660741521b938d7c9e9304ee514e` | `current` |
| `kc-ri2-completion-ri4` | `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md` | `bc12a15dbac70e1ba538e313ce87dfed41b9e831` | `superseded` |

These classifications are RI-4 qualification inputs only. They do not authorize a broader corpus.

## Harness

`components/knowledge-core/tools/ri4_host_qualification.py` is the operator/orchestration entrypoint. It:

1. requires an explicit repository root and a new empty state directory outside the Git repository;
2. verifies the exact pinned commit and every manifest Git blob before starting;
3. verifies the selected loopback port is available;
4. requires a reachable Docker engine;
5. creates a unique PostgreSQL 18 container and unique Docker named volume;
6. binds PostgreSQL only to `127.0.0.1`;
7. uses a qualification-only local trust-auth database with no production credential claim;
8. migrates the isolated database through Alembic head;
9. runs the first Knowledge Core application process through `ri4_host_phase.py`;
10. restarts the PostgreSQL container while retaining the named volume;
11. waits for PostgreSQL readiness;
12. launches a second independent Knowledge Core application process against the same database volume and artifact directory;
13. proves current/historical retrieval, exact artifact integrity, exact provenance, same generation, and accepted-manifest replay;
14. verifies replay creates no additional durable state;
15. writes `RI4_HOST_QUALIFICATION_EVIDENCE.json`;
16. stops the qualification container at the end.

Without `--cleanup`, the stopped container, Docker volume, evidence file, and artifact directory remain for inspection. CI passes `--cleanup` after all assertions.

Backup/restore is not performed.

## CI rehearsal result

Run `34418809968` checked out exact harness checkpoint `934850d5830d4a5d89ec32b04630435a027e816f`.

Baseline validation:

```text
PostgreSQL 18
Alembic 0001_task1 -> 0010_ri2: passed
Fast: 48 passed, 1 expected pinned historical-fixture skip, 18 deselected
PostgreSQL: 16 passed, 2 expected pinned historical-fixture skips, 49 deselected
RI-4 restart qualification harness: passed
Workflow: success
```

The RI-4 harness step used Docker server `28.0.4` and reported all required restart/recovery assertions passing.

## Intended-host result

The same harness was then run successfully on the intended Windows host without `--cleanup`.

Observed environment:

```text
Docker Desktop server: 29.7.2
PostgreSQL image: postgres:18
loopback port: 55432
state root: C:\Users\floyd\AppData\Local\KnowledgeCore\ri4-host-qualification-01
```

Generated evidence:

```text
status: success
postgres_restart_verified: true
application_reconstruction_verified: true
exact_replay_verified: true
current_historical_retrieval_verified: true
artifact_integrity_verified: true
provenance_verified: true
backup_restore_performed: false
```

Persistent state before restart and after recovery/replay remained exactly:

```text
document bindings: 3
settled import receipts: 1
source observations: 3
Resources: 3
ResourceVersions: 3
RF-2 search rows: 3
text generations: 1
verified SHA-256 artifacts: 3
```

The serving generation remained `da8ab02c-8819-43d0-9d39-e3098398c8e1`. Exact replay reused the original settled receipt and created no additional durable state.

Default retrieval still excluded the RI-2 historical document. Explicit superseded retrieval returned `REPOSITORY_IMPORT_RI2.md` with source version `3d12f205d15c310bce0718c56c0866befccd90ec`. All three provenance records independently verified their SHA-256 artifacts after restart.

The complete durable summary is recorded in `RI4_INTENDED_HOST_EVIDENCE.md`; the generated qualification state remains preserved outside the repository for inspection.

## RI-4 acceptance

RI-4 is accepted complete for the bounded capability it tested:

- PostgreSQL 18 container restart with a retained Docker named volume;
- application reconstruction in a separate Python process;
- reuse of the persistent artifact directory;
- current/historical retrieval continuity;
- exact manifest replay without duplicate durable state;
- exact repository/import provenance continuity;
- SHA-256 artifact integrity across restart.

The intended-host evidence closes the only item that remained after CI rehearsal.

## Explicit non-claims

RI-4 does not qualify or authorize:

- machine reboot persistence;
- Docker Desktop restart across a Windows reboot;
- destruction/recreation of the PostgreSQL volume or artifact directory;
- backup/restore or disaster recovery;
- production credentials, TLS, firewall policy, Windows service supervision, production filesystem ACLs, or unattended startup;
- production use of trust authentication;
- broad ACL/Vera/RiskCardOCR/research/legacy import;
- automatic repository discovery/classification/document-key assignment;
- SHA-256-format Git repositories;
- chunking, extraction/OCR, embeddings/vector search, RAG, Authority, or autonomous execution.

## Stop boundary

**RI-4 is complete. Do not infer authorization for production deployment, backup/restore, broader corpus import, chunking, embeddings/RAG, Authority, or execution work from this qualification.**
