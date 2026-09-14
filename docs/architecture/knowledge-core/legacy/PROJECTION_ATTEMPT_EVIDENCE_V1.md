# Knowledge Core Projection Attempt / Evidence V1

## Purpose

This boundary records durable provider-neutral evidence about attempts to build or update an external derived projection. It does not make the projection canonical and does not make successful backend transport trustworthy.

PostgreSQL canonical knowledge remains authoritative. A projection backend may fail completely without deleting, mutating, or replacing the source evidence that motivated the attempt.

## Durable identity

Each attempt has a KC-owned stable `attempt_id`. Replaying the same identity with the exact same inputs returns the same durable attempt. Reusing it with different inputs fails closed.

Backend-owned node, edge, episode, document, or object identifiers are not part of durable KC identity and are not required by this V1 contract.

## Evidence recorded

The control ledger records:

- projection kind and provider-neutral target kind;
- namespace and logical scope;
- backend identity/version as replaceable implementation metadata;
- profile/config identity or digests;
- exact canonical KC source references and source revisions;
- deterministic request digest;
- start/settlement timestamps;
- disposition: `pending`, `succeeded`, `incomplete`, `failed`, or `quarantined`;
- warnings and errors;
- independent validation state.

## Trust boundary

`disposition=succeeded` means only that the projection attempt reported backend success. V1 leaves `validation_state=unvalidated`. A later validation gate must independently prove the projected result before any graph-backed result can become trusted KC retrieval context.

Therefore:

```text
canonical source committed
!= projection attempted
!= backend succeeded
!= projection validated
!= result authorized for model context
```

## Deferred intentionally

This V1 does not:

- call Graphiti or any other projection backend;
- store provider-owned object IDs as KC identity;
- validate node/edge completeness or temporal correctness;
- promote projection results into retrieval;
- change Authority behavior;
- change ACL execution authority.
