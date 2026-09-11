# Repository Coupling Inventory

**Status:** current after runtime reconstruction Task 8.

ACL is a system with optional task/workspace backends. A Git repository is the substrate for the first coding-workspace capability, not ACL target identity.

## Logical identity

Invocation V3 requires logical `target:*` and `workspace:*` identities. Repository names, URLs, branches, remotes, local checkout paths, and `.git` forms are rejected as logical target identity.

## Justified Git-backed workspace mechanics/evidence

The following remain intentionally Git-specific because the current coding slice requires exact source-state evidence:

- Autonomous Worker Framework `repository_state.py`, `repository_handoff.py`, and optional `local_git_publisher.py` mechanics;
- Worker Lab workspace preparation/verification and workspace receipt records;
- Invocation V3 nested Git source state (base commit and workspace receipt/root/path digests);
- Result V3 Git workspace evidence (base/observed head, content digest, changed paths);
- attempt/exercise fields that identify the exact template/base commit for the Git-backed coding capability;
- CLI repository/workspace path arguments used to locate that backend.

These facts are capability/backend evidence. They do not authorize work and do not identify the logical target system.

## Backend-only locators

Local checkout paths supplied to workspace preparation, verification, dispatch, recovery, or publication are process/backend locators. They are not durable universal ACL identity.

## Removed repo-as-system coupling

The current runtime no longer has a monorepo identity contract or repository URL/name as universal ACL identity. Portable source identity uses checkout-relative component paths only to hash the reviewed ACL source tree; it does not identify the task target.

## Task 9 audit rule

Any remaining production/domain field named `repository`, `template_repository`, `target_repository`, branch, remote, or `.git` must be explainable as one of the Git-workspace mechanics/evidence above. If it is used as logical target identity, provider selection, authority, or portable host identity, Task 9 must fail.
