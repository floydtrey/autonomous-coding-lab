# Durable Decisions

Entries remain active until explicitly superseded.

## ACL-D001 — One private integration repository

**Status:** Active

Autonomous Coding Lab will become one private program and repository containing
Worker Lab, the execution framework, and local-model evaluation tools. Original
repositories remain unchanged recovery sources during migration.

## ACL-D002 — Internal boundaries replace repository boundaries

**Status:** Active

Consolidation does not consolidate authority. Worker Lab, execution security,
and model evaluation remain separate packages and trust boundaries with explicit
dependency direction and tests.

## ACL-D003 — Audit before import

**Status:** Active

No component code is copied before M1 accepts its source identity, provenance,
exclusions, directory path, path repairs, license treatment, and parity plan.

## ACL-D004 — Migration does not change behavior

**Status:** Active

Import and structural migration are separated from refactoring, new features,
prompt changes, dependency upgrades, and authority expansion.

## ACL-D005 — Disposable repositories remain external

**Status:** Active

Worker target repositories and validation workspaces remain separate disposable
Git repositories. The controlling monorepo cannot be its own worker target.
