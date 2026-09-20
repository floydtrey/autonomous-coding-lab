# Security

## Security model

Knowledge Core assumes all network clients are untrusted until authenticated.

Authentication establishes a principal. Authorization then independently decides which KC operations, scopes, and resources that principal may use.

A valid credential is not global KC authority.

## Important invariants

- Principal UUIDs are identity, not credentials.
- Service secrets are stored as hashes, not recoverable plaintext.
- Disabled principals and revoked/expired credentials fail closed.
- Non-owner operations require explicit operation capability.
- Resource visibility/sensitivity and scope/resource grants are evaluated separately.
- Explicit deny wins for non-owner principals.
- Owner-locked classification cannot be weakened by an AI/service principal.
- Hardened search applies authorization before lexical ranking/limit.
- Exact source retrieval reauthorizes before artifact bytes are read.
- Graph facts require authorized correlation to every supporting canonical resource.
- Graph authorization is rechecked after external provider calls.
- Derived provider failure cannot invalidate canonical knowledge.

## Backend isolation

PostgreSQL, artifact storage, FalkorDB, and model/embedder runtimes are backend infrastructure.

Do not expose them directly to ordinary clients. Clients should receive only bounded KC API credentials.

## Secrets

Do not commit:

- database passwords;
- bootstrap keys;
- service tokens;
- FalkorDB credentials;
- model-provider API keys.

Do not place reusable secrets into KC merely because KC can technically store arbitrary text. Prefer a dedicated secret manager and store references/metadata where practical.

## Known defense-in-depth gap

PostgreSQL Row Level Security under a separate restricted runtime database role is not yet claimed complete.

The application authorization layer and SQL candidate filtering are the current enforcement path. PostgreSQL must therefore remain private and the KC runtime database credential must not be shared with clients.

Do not represent ordinary RLS policies run under a table-owner/BYPASSRLS role as completing this gate.

## Owner bootstrap

The owner/bootstrap credential is a migration and owner-control path with broad authority. It should be strongly protected and should not be distributed to autonomous clients.

Long-term human authentication such as OIDC/WebAuthn/MFA is intentionally outside the KC core and may front the service later.

## Reporting/review focus

Prioritize review of authentication bypass, IDOR/direct-object access, scope confusion, grant precedence, resource-policy downgrade, SQL authorization filtering, graph source laundering, TOCTOU authorization, stale projection resurrection, route exposure, and credential leakage.
