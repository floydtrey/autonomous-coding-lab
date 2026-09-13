# Knowledge Core Projection Validation V1

## Purpose

This boundary independently validates an already durable projection attempt before KC can ever treat that external derived projection as trustworthy.

It preserves the separation:

```text
canonical source committed
!= projection attempted
!= backend succeeded
!= projection validated
!= result authorized for model context
```

No graph backend participates in Authority, and no projection result is promoted into retrieval by this V1.

## Deterministic validation identity

Each validation run has a KC-owned stable `validation_id`.

The validation request digest binds:

- the KC-owned projection `attempt_id`;
- the immutable projection-attempt request digest;
- validator identity and version;
- ruleset identity and digest;
- validator configuration digest.

Replaying a settled validation with the same identity and exact inputs returns the same durable evidence without invoking the validator again. Reusing the identity with different inputs fails closed.

A quarantined validation may be retried under a new validation identity. A terminal `validated`, `incomplete`, or `rejected` decision is not overwritten by a second validation run.

## Validation outcomes

The provider-neutral outcomes are:

- `validated` — the projection attempt reported `succeeded`, at least one deterministic check ran, and every recorded check passed;
- `incomplete` — at least one deterministic check failed because required projected material is missing or incomplete;
- `rejected` — at least one deterministic check failed an integrity/invariant requirement;
- `quarantined` — KC cannot safely determine trust, including validator failure, malformed validation evidence, or indeterminate checks.

An attempt with projection disposition `failed` or `quarantined` is not eligible for validation. An attempt already marked `incomplete` cannot be promoted to `validated`.

## Exact validation evidence

Each check records:

- stable provider-neutral `check_code`;
- outcome: `passed`, `failed`, or `indeterminate`;
- deterministic JSON evidence;
- KC-computed SHA-256 evidence digest;
- optional diagnostic detail.

Provider-owned node, edge, episode, or object IDs may appear later as diagnostic evidence if a backend validator needs them, but they are not KC durable identity and are never sufficient to establish trust by themselves.

The validation record also preserves the exact projection-attempt request digest that was inspected.

## Failure behavior

Validator exceptions are durably recorded as `quarantined` validation evidence. They do not disappear, become implicit success, mutate canonical knowledge, or authorize retrieval.

Projection validation writes only the control/evidence ledger and the attempt's validation summary. It does not create canonical semantic revisions.

## Deferred intentionally

This V1 does not:

- call Graphiti or any other graph backend itself;
- define Graphiti-specific completeness or temporal checks;
- promote validated projections into retrieval;
- bypass the deterministic Authority boundary;
- change ACL execution authority.

The next integration step may implement a projection adapter and backend-specific validator behind these provider-neutral contracts, while keeping PostgreSQL canonical and retrieval untrusted until both validation and Authority gates pass.
