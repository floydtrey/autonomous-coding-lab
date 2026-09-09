# Knowledge Core Repository Import RI-4 — Local-Host Persistence / Recovery Qualification

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Starting RI-3 checkpoint:** `3d12f205d15c310bce0718c56c0866befccd90ec`  
**RI-4 harness checkpoint:** `934850d5830d4a5d89ec32b04630435a027e816f`  
**CI rehearsal:** GitHub Actions run `34418809968` — **success**  
**Manifest:** `docs/architecture/knowledge-core/RI4_HOST_QUALIFICATION_MANIFEST.json`  
**Status:** **RI-4 harness implemented and restart behavior reproduced in CI. Intended-host qualification is still pending and RI-4 is not yet accepted as complete.**

## Purpose

RI-4 closes the remaining persistence gap left by RI-3: PostgreSQL itself must restart while canonical/import/generation state remains on a persistent database volume, the Knowledge Core application must be reconstructed afterward, and the same persistent artifact directory must continue to verify.

This task remains a qualification exercise, not production deployment.

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
```

The additional RI-4 harness step then succeeded using Docker server `28.0.4`.

Observed RI-4 qualification state before and after PostgreSQL restart/replay:

```text
document bindings: 3
settled import receipts: 1
source observations: 3
Resources: 3
ResourceVersions: 3
RF-2 search rows: 3
text generations: 1
artifact integrity checks: 3 passed
manifest digest: 160b4ba2966305108a1a381a5996c93d8c22cced36fe2fa4baa99d9e6a554927
```

The serving generation before restart and after restart was the same within the qualification run. Default retrieval excluded the RI-2 historical document. Explicit superseded retrieval returned only `REPOSITORY_IMPORT_RI2.md` with source version `3d12f205d15c310bce0718c56c0866befccd90ec`. Exact replay returned the original settled receipt and the complete durable snapshot was unchanged.

CI therefore proves the harness and RI-2/RF-2 behavior can survive a PostgreSQL container restart with a retained volume in a Linux runner.

## Intended-host run

RI-4 is not complete until the same harness succeeds on the intended local host.

Prerequisites:

- Python 3.12;
- Docker Desktop/Engine running Linux containers;
- Git checkout containing full repository history;
- Knowledge Core installed with test extras: `python -m pip install -e ".[test]"`.

From `components/knowledge-core`, choose a **new empty directory outside the repository** and run:

```powershell
python tools\ri4_host_qualification.py `
  --repository-root ..\.. `
  --state-root "$env:LOCALAPPDATA\KnowledgeCore\ri4-host-qualification-01"
```

Do not add `--cleanup` to the intended-host qualification. On success, preserve the generated `RI4_HOST_QUALIFICATION_EVIDENCE.json`, the artifact directory, and the stopped Docker container/volume until the evidence has been reviewed.

If loopback port `55432` is already in use, select another unused port with `--port`.

## Acceptance remaining

The intended-host evidence must show:

- `status = success`;
- `postgres_restart_verified = true`;
- `application_reconstruction_verified = true`;
- `exact_replay_verified = true`;
- `current_historical_retrieval_verified = true`;
- `artifact_integrity_verified = true`;
- `provenance_verified = true`;
- `backup_restore_performed = false`;
- one settled receipt and exactly three bindings/observations/Resources/ResourceVersions/search rows before and after replay;
- exact source commit `3d12f205d15c310bce0718c56c0866befccd90ec`.

Only after that host evidence is reviewed should RI-4 be marked complete.

## Explicit non-claims

RI-4 currently does not qualify or authorize:

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

**RI-4 host harness and CI rehearsal are complete. Stop here until the intended host can run the recorded qualification command. Do not start production deployment, backup/restore, or broader corpus import.**
