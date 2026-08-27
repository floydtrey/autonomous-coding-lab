# Numbered Test Catalog

**Catalog:** `WORKER_LAB_TESTS:v1`
**Rule:** Select the union of applicable profiles, include prerequisites once, run cheapest checks first, and stop at the first failed boundary. Unmapped changed paths fail closed.

## Stable tests

| ID | Cost | Purpose | Command |
|---|---|---|---|
| T001 | millisecond | Canonical identity and strict record contracts | `python -m pytest -q tests/test_canonical.py tests/test_models.py` |
| T002 | millisecond | Test catalog selection and dependency rules | `python -m pytest -q tests/test_test_catalog.py` |
| T003 | millisecond | Attempt lifecycle and relationship integrity | `python -m pytest -q tests/test_lifecycle.py tests/test_validation.py` |
| T004 | second | Atomic storage, containment, and corruption behavior | `python -m pytest -q tests/test_storage.py` |
| T005 | second | Backup, restore, and operator-interface behavior | `python -m pytest -q tests/test_backup.py tests/test_cli.py` |
| T006 | second | Phase/milestone full suite | `python -m pytest -q` |

## Versioned profiles

| Profile | Tests | Select for |
|---|---|---|
| `RECORD_CHANGE:v1` | T001 | canonical or record-model changes |
| `CATALOG_CHANGE:v1` | T001, T002 | numbered test definitions or selection logic |
| `ATTEMPT_CHANGE:v1` | T001, T003 | attempt lifecycle or relationship changes |
| `STORAGE_CHANGE:v1` | T001, T004 | paths, persistence, atomic writes, or corruption handling |
| `BACKUP_CLI_CHANGE:v1` | T001, T004, T005 | backup, restore, or CLI changes |
| `MILESTONE:v1` | T001-T006 | candidate, integration, release, and rollback drills |

Retirement never reuses an ID. A retired test remains recorded with its replacement. Profile or
test behavior changes require a new profile/catalog version rather than silently changing retained evidence.
