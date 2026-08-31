# Worker Policy and Role Model

**Status:** Protected Phase 1 authority
**Policy:** `core-worker-policy:v1`

## Precedence

Effective authority is the intersection of permanent policy capability, role capability, and task
scope, minus every applicable denial. Lower layers may narrow authority; they cannot grant authority
missing from a higher layer. Any denial wins.

```text
non-overridable invariants
  -> permanent capabilities
  -> versioned role maximum
  -> exact task scope
  -> temporary exercise restrictions
```

An assignment requiring a capability unavailable to its role, or denied by the role or exercise,
fails with `ROLE_UNSUPPORTED`. The controller must correct the role or task contract; the worker
must not improvise a broader role.

## Protected definitions

- `curricula/policies/core-worker-policy/v1.json` defines permanent invariants and capabilities.
- `curricula/roles/*/v1.json` defines the maximum authority of each worker role.
- Exercise records select an exact policy, role, sandbox, context manifest, catalog, and temporary
  restriction set.
- Attempt identity binds the digests of all those resolved records.

Workers may read these definitions when included in their exact context, but may not modify the
policy, role, evaluator, test selection, evidence-integrity, or graduation rules judging their
current attempt.

## Logging

Authoritative execution logs are captured by the framework outside the candidate workspace. A
worker-authored journal is untrusted output and is writable only when the exercise explicitly
permits it. Temporary restrictions may remove that privilege.

## Context manifests

Every readable source file supplied to a worker is listed by normalized repository-relative path,
SHA-256 content digest, and purpose. The manifest also binds the separate target repository and
starting Git commit. Missing, changed, extra, absolute, traversal, drive-qualified, and backslash
paths fail closed before execution.
