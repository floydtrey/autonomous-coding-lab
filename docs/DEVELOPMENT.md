# Development

## Bounded changes

Make one architectural change at a time. Verify branch/HEAD/tree, preserve fail-closed semantics, run focused tests first, then the relevant full suites. Do not restore obsolete compatibility paths to satisfy stale tests; update tests to the current contract when equivalent coverage exists.

## Portable source identity

`config/portable-source-manifest.json` is behavior-bearing source identity. When a production component in its closure changes, recompute that component's exact file-set digest in the same bounded change.

Use:

```text
python tools/verify_portable_source.py
```

The verifier checks source bytes only. It must work independently of operating system, Python executable path, provider installation, local activation, and task authorization.

Do not add host fields or activation state back to the source manifest.

## Component testing

- Autonomous Worker Framework tests run from `components/autonomous-worker-framework`.
- Worker Lab tests run from `components/worker-lab`.
- portable source tests run from repository root.
- Knowledge Core has its own governed test/qualification workflow.

Use injected/mock provider runners for deterministic reconstruction tests. A test that needs a real model/provider is outside Tasks 1–9 unless separately authorized.

## Contract evolution

Version a durable schema when behavior-bearing semantics change. Keep logical target/workspace identity independent of repository location. Keep provider/model/settings inside qualification/binding. Keep host/process facts inside host/containment evidence.

Do not use a broad field rename to hide responsibility ambiguity; move the fact to the layer that owns it.

## Documentation

Current operating truth belongs in the root documents linked by `README.md`. Git history is historical documentation. Do not create a second legacy operating tree.

Research under `docs/research/` must be clearly treated as advisory evidence. Knowledge Core architecture/evidence under `docs/architecture/knowledge-core/` remains current for that component, but root `docs/CURRENT_STATE.md` controls ACL runtime status.

## Git workspace mechanics

The first coding slice uses Git for exact source-state evidence and optional publication tooling. Those mechanics must remain behind the coding-workspace/backend boundary and must not become universal ACL target identity.
