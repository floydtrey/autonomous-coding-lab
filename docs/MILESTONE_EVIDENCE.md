# Phase 1 Milestone Evidence

**Milestone:** `v0.1.1-phase1`
**Date:** 2026-08-27
**Scope:** Synthetic Worker Lab records and local recovery only

## Validation

- Focused protected-record and CLI acceptance: 57 passed.
- Complete Worker Lab suite: 170 passed, 1 expected Windows symlink capability test skipped.
- Complete suite from the external rollback clone: 170 passed, 1 expected skip.
- Python compilation and Git whitespace checks: passed.

## Durable-data recovery

- Backup: `C:\Users\MineTrackerWorker\backups\worker-lab\worker-lab-v0.1.1-phase1-data-99c0b58`
- Restored tree: `C:\Users\MineTrackerWorker\backups\worker-lab\worker-lab-v0.1.1-phase1-restore-99c0b58`
- Backup manifest SHA-256: `91f7b1fda771f1711ccd3f1f86f02174f5326d992362c34853aba2beee673b8d`
- Result: six files from the explicit durable roots `curricula/` and `state/` verified before and
  after restore. Repository internals, source, tests, docs, caches, temporary files, and disposable
  workspaces were excluded.

## Git rollback

- Preflight bundle: `C:\Users\MineTrackerWorker\backups\worker-lab\worker-lab-phase1-preflight-99c0b58.bundle`
- Preflight bundle SHA-256: `0a1cecca3ca309f575ad29df3bb2d51d5aaf64cf0701587b79ac8ee04e0de0f3`
- Rollback checkout: `C:\Users\MineTrackerWorker\backups\worker-lab\worker-lab-phase1-rollback-99c0b58`
- Recovered commit: `99c0b581a28b09ab34f9e9b2a8dcbef48380ff48`
- Bundle verification: complete history, valid refs, and exact recovered HEAD.
- Final tagged bundle: `C:\Users\MineTrackerWorker\backups\worker-lab\worker-lab-v0.1.1-phase1.bundle`

The preflight bundle proves rollback before the immutable tag is created. The final bundle is created
from the same validated history after `v0.1.1-phase1` is attached to the final documentation commit.
