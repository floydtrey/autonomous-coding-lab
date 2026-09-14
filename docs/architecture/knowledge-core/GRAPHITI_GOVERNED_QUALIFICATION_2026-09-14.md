# Graphiti Governed-Document Qualification — Accepted 2026-09-14

## Status

**ACCEPTED**

The Knowledge Core governed-document Graphiti correction passed its first real
17-segment host qualification on 2026-09-14.

This qualification closes the semantic invalidation / provider-controlled
retirement defect for the governed-document projection policy at this boundary.

Retrieval-quality optimization is separate future work and is not required for
this acceptance.

## Qualified implementation boundary

Repository branch:

`architecture/knowledge-core`

Implementation HEAD prior to this qualification seal:

`6376419e369ea9ecfe58a19fa233bbfca90ad703`

Relevant governed ruleset:

`kc-graphiti-governed-document-v3`

Validator:

`kc-graphiti-live-validator`, version `3`

Graphiti:

`graphiti-core 0.30.2`

LLM:

`graphiti-qwen38-27b-32k`

Embedder:

`nomic-embed-text:latest`

## Accepted real-host attempt

Projection attempt:

`ea7eba74-912f-5e88-9271-f59670066d88`

Validation:

`df9eabde-5a63-5f70-9478-27b74bd07684`

Namespace:

`kc:graphiti-governed-document-v1-q1`

Scope:

`project:knowledge-core`

Canonical fixture:

`docs/architecture/knowledge-core/CURRENT_STATE.md`

Projected segments:

`17`

## Result

- Projection disposition: `succeeded`
- Validation state: `validated`
- Source bindings: `17 / 17`
- Validation checks: `7 / 7 passed`
- Projection-integrity warnings: `0`
- Search probe results: `10`
- Search results with canonical attribution: `10 / 10`

### Governed lifecycle inventory

- Inventory complete: `true`
- Edge count inspected: `48`
- Source contribution count: `48`
- Retired edges: `0`
- Missing attribution edges: `0`
- Unknown-source edges: `0`
- Wrong-partition edges: `0`
- Multi-source edge anomalies: `0`

Expected and observed physical partition:

`kc_da882fc9ed8a7b0764b618562951`

Lifecycle inventory digest:

`sha256:270bc4634d33e12628b317cf16f85a7ab943d0664f04a462aa06bf4a6dddb103`

## Validation checks

All required checks passed:

1. `attempt-contract`
2. `source-binding-contract`
3. `projection-integrity-warnings`
4. `source-episodes-present`
5. `governed-lifecycle-inventory`
6. `namespace-search-isolation`
7. `search-source-attribution`

The lifecycle validation specifically confirmed complete edge inspection, zero
provider-controlled retirement, and exact current-source attribution.

## Acceptance interpretation

This qualification demonstrates that, under the governed-document policy:

- PostgreSQL/KC remains canonical.
- Graphiti remains a derived projection and retrieval layer.
- Graphiti semantic contradiction decisions do not control governed-document lifecycle.
- No provider-controlled retirement occurred.
- Projection integrity was inspected before trust admission.
- Every inspected graph edge had acceptable KC source attribution.
- Trusted search results were correlated back to canonical KC evidence.
- Namespace/physical projection isolation passed validation.

The original unsafe semantic invalidation defect is therefore considered
corrected and qualified for this policy boundary.

This acceptance does **not** claim that Graphiti retrieval ranking or answer
quality is optimal. Those are separate retrieval-quality concerns and should
only be revisited when they materially affect a consumer.

## Historical attempts retained

Earlier failed/interrupted attempts remain in KC evidence and are intentionally
not deleted.

Notably:

- `3ecf4f80-201f-5b89-9872-0595d1f4d92f`
  - `incomplete`
  - `unvalidated`
  - five Graphiti endpoint warnings

- `0838fb5d-71a5-568d-8668-2900bb1081b3`
  - interrupted during recovery
  - remained `pending / unvalidated`

These are historical evidence and should not be mistaken for the accepted
qualification above.

## Next-stage note

Do not continue modifying Graphiti qualification simply to improve already
accepted edge cases.

The next architectural review should reassess Knowledge Core as a whole,
identify the current usable consumer boundary, and determine the minimum work
required to expose KC safely to consumers such as MindsHub/Qwen, ACL, and
eventually Vera.
