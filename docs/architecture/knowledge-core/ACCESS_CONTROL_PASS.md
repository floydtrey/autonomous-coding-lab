# Knowledge Core Access-Control / Graph Integration Pass

Status: ACTIVE  
Working branch: `kc-authorization-model`  
Base branch: `architecture/knowledge-core`  
Base commit: `af0b29bf9da5aa861e6eb9354d6f1698d2d33950`

## Purpose

Finish the minimum KC security and graph seams required before ACL becomes a real KC consumer, while preserving a clean path toward Vera, remote authenticated clients, temporary project grants, and larger multi-user deployments.

This pass is intentionally divided into handoff-safe milestones. Do not start the next milestone until the current milestone has code, tests, and this file updated with a sealed checkpoint.

## Durable design decisions

1. A display name is never a security identity.
2. Every human, AI role, service, importer, or future application is represented by an immutable UUID principal.
3. A human-readable principal code is a convenience identifier and may change without changing the UUID identity.
4. Authentication, knowledge authorization, and external action authority are separate concerns.
5. PostgreSQL remains canonical truth for knowledge and authorization metadata.
6. Graphiti/FalkorDB remains a rebuildable derived projection. It never becomes the authority for access control.
7. Graph-derived evidence may be returned only when KC can authorize the correlated canonical source evidence for the caller.
8. ACL must never receive owner/bootstrap authority. ACL roles receive independent principals and bounded grants.
9. ACL does not receive delete/restrict/admin authority in the initial profile.
10. Temporary project access is represented by grants with validity windows, not by rewriting every knowledge item.
11. Explicit deny and owner-locked restrictions must not be weakened by an AI classifier.
12. Automatic classification may make data more restrictive, but must not autonomously make explicitly protected data less restrictive.
13. Powerful legacy semantic mutation routes must not be exposed to untrusted network clients merely because they provide `X-Knowledge-Caller`.
14. Public hosting does not imply public reachability. PostgreSQL, FalkorDB, Graphiti, model runtimes, artifact storage, and admin interfaces are not public consumer surfaces.

## Vocabulary

### Principal

Immutable actor identity. Examples include owner, human user, ACL Planner, ACL Worker, Vera, or a bootstrap/import service.

Canonical identity: UUID `principal_ref`.

Convenience identity: unique mutable `principal_code`.

### Scope

The bounded working context in which authority applies, e.g. `project:acl`, `project:vera`, or a future directory/resource scope.

### Access policy

Rules controlling which principals/groups may perform which KC operations against which scopes/resources.

### Source lifecycle

Independent from secrecy. Examples: active, completed, superseded, failed, archived. Retrieval can exclude failed/superseded evidence by default without pretending that it is secret.

## Milestones

### KC-A — Principal and credential foundation

Goal: establish durable UUID principals and independently revocable service credentials without changing current KC consumer-route semantics yet.

Required:
- principal persistence;
- service-credential persistence;
- high-entropy secret generation;
- hashes only in PostgreSQL (never raw service secrets);
- deterministic credential parsing/authentication;
- revocation and principal disable behavior;
- tests;
- existing owner bootstrap remains intact during migration.

Stop condition:
- principal/credential storage and authentication tests pass;
- no ACL credential created yet;
- no permission grants implemented yet.

### KC-B — Scope and authorization model

Goal: implement the central decision model.

Required concepts:
- scopes;
- operation grants;
- principal grants and group-ready schema;
- validity windows for temporary access;
- explicit deny;
- resource/source access metadata;
- owner/origin principal;
- visibility/sensitivity/lifecycle metadata;
- single authorization evaluator used by consumer operations.

PostgreSQL RLS is defense in depth, not a replacement for KC authorization.

### KC-C — Consumer API hardening

Goal: replace single-key `local_owner` admission for non-owner clients.

Required:
- authenticated principal admission;
- authorization for status/search/get-source/store/memory-propose;
- get-source must reauthorize the exact resource;
- no direct-object authorization bypass;
- legacy mutation API isolated from untrusted network clients.

### KC-D — Production Graphiti wiring

Goal: use the already-implemented Graphiti adapter in the normal KC service.

Required:
- hardened Graphiti adapter constructed from configuration;
- `UnifiedGraphSearchBinding` supplied by the normal service launcher;
- governed projection scheduling after canonical/text changes;
- projection validation;
- graph failure never rolls back canonical truth;
- restrictions/erasure prevent derived graph resurrection;
- graph retrieval authorization derives from canonical source correlations.

### KC-E — ACL principals and grants

Initial role principals:
- ACL Controller
- ACL Determiner
- ACL Planner
- ACL Worker
- ACL Reviewer

Each role gets its own immutable principal and credential/grant set.

Initial ACL policy:
- allow bounded status/search/get-source/store/memory-propose as required by role;
- deny delete/restrict/admin/identity mutation/raw semantic mutation;
- default active project scope is ACL;
- cross-project access requires explicit/temporary grant;
- failed/superseded project material excluded unless deliberately requested and authorized.

### KC-F — Controlled bootstrap/import surface

Goal: allow ChatGPT or another importer to help populate initial datasets without owner authority.

Importer writes candidate/staging records with provenance. Promotion to canonical state is separately governed.

## Handoff protocol

At each milestone boundary update this section with:

- branch;
- exact HEAD;
- completed files/migrations;
- tests run and results;
- unresolved risks;
- next milestone and its exact first task.

A new chat should inspect this file and the referenced branch before making changes. Conversation memory is supplemental, not the source of truth.

## Current checkpoint

Milestone: KC-A  
State: SEALED / QUALIFIED

Qualified implementation head: `2b8d19d2dcce7fb05613b26a32d221e53848155f`  
Qualification workflow: Knowledge Core run `35484175117`  
Draft PR: #33

Completed:
- `knowledge_core/domain/principals.py`: UUID-backed principal and credential domain types;
- `knowledge_core/storage/principal_models.py`: durable principal/service-credential tables;
- `knowledge_core/application/principal_auth.py`: principal creation, high-entropy service-key issuance, hash-only persistence, authentication, credential revocation, and principal disable behavior;
- migration `0019_principal_authentication.py`;
- metadata/migration model registration;
- `tests/test_kca_principal_authentication.py`;
- issued plaintext tokens are excluded from dataclass repr;
- existing owner bootstrap remains unchanged and no ACL credential exists yet.

Qualification results on the implementation head:
- PostgreSQL migrations: PASS;
- fast semantic suite: PASS;
- PostgreSQL G1-G21 qualification suite: PASS;
- SR-2 G22 pinned real-document pilot: PASS;
- RI-4 local-host restart rehearsal: PASS;
- SR-2 local-host segment restart rehearsal: PASS.

Known current-state facts carried forward:
- current consumer bootstrap admission still maps one shared key to `local_owner`; KC-A intentionally did not replace route admission;
- normal KC service launcher does not yet supply a Graphiti unified-search binding;
- Graphiti provider/validation/source-correlation implementation already exists;
- deletion/restriction kernel exists internally but is not exposed by the `/v1/kc/*` consumer API;
- legacy base API has mutation routes whose `X-Knowledge-Caller` header is identification, not authentication.

Unresolved by design:
- no scopes/grants/resource access policy yet;
- no PostgreSQL RLS yet;
- no authenticated-principal route wiring yet;
- no ACL/Vera/ChatGPT credentials have been created.

Next milestone: KC-B — Scope and authorization model.

Exact first task for KC-B:
Inspect the existing governed-source/project metadata and define the minimal canonical authorization schema/evaluator without duplicating existing source governance. Preserve the distinction between project/lifecycle relevance and confidentiality.


## KC-B working checkpoint

State: SEALED / QUALIFIED

Branch: `kc-authorization-model`  
Parent milestone: qualified KC-A branch `kc-auth-foundation`

KC-B authorization semantics selected before implementation:

- global operation grants are capabilities to invoke KC operations; they do not by themselves disclose non-public resources;
- resource access is independently governed by the resource's current access policy;
- `public`: any authenticated principal with the required operation capability may read;
- `personal`: the resource owner may read; other principals require an exact resource grant;
- `scoped`: requires an applicable scope grant or exact resource grant;
- `private`: requires an exact resource grant;
- `credential` and `financial` sensitivity require an exact resource grant for non-owner principals even when a broader scope grant exists;
- owner-type principals bypass ordinary grants and retain all KC authority;
- explicit deny wins over allow for non-owner principals;
- grants support validity windows/revocation for temporary project releases;
- scopes are hierarchical and carry lifecycle (active/completed/failed/archived), but lifecycle does not silently become an authorization rule;
- access policies are append-only revisions with a current pointer so security changes retain history;
- ACL/model request bodies must not be trusted to self-select owner, sensitivity, or privileged scope. KC-C will derive/store those from authenticated context and trusted classification policy;
- PostgreSQL RLS remains required defense-in-depth, but activation is deferred until KC-C can set authenticated principal/scope context on each DB transaction without breaking existing service paths.


### KC-B sealed qualification

Qualified implementation head: `f63a5d9262c12e21226bdd7115c496ca5434d466`  
Qualification workflow: Knowledge Core run `35484747499`  
Draft PR: #34

Completed:
- hierarchical authorization scopes with independent lifecycle state;
- principal groups and time-bounded memberships;
- principal/group grants with global, scope, and resource targets;
- explicit allow/deny, validity windows, expiration, and revocation;
- append-only resource access policy revisions and current-policy pointer;
- resource-to-scope policy membership;
- visibility classes: public, personal, scoped, private;
- sensitivity classes: normal, protected, credential, financial;
- owner bypass and owner-controlled classification locks;
- credential/financial access requires exact resource grant for non-owner/non-personal-owner callers;
- central deterministic authorization evaluator;
- tests for human personal/public behavior, ACL project isolation, parent/child directory scopes, temporary grants, groups, sensitive data, deny precedence, failed-project lifecycle separation, and locked-policy history;
- migration `0020_authorization_model.py`.

Qualification results:
- PostgreSQL migrations: PASS;
- fast semantic suite: PASS;
- PostgreSQL G1-G21 qualification suite: PASS;
- SR-2 G22 pinned real-document pilot: PASS;
- RI-4 local-host restart rehearsal: PASS;
- SR-2 local-host segment restart rehearsal: PASS.

RLS status:
- schema/evaluator are ready for DB-session enforcement;
- RLS activation remains intentionally deferred to KC-C, because KC must first bind an authenticated principal/scope to each database transaction. Enabling RLS before that seam exists would either break current service paths or create a privileged bypass.

Next milestone: KC-C — Consumer API hardening.

Exact first KC-C task:
Replace the non-owner shared-bootstrap admission path with database-backed principal authentication for consumer requests while retaining a bounded owner bootstrap migration path. Then apply the central evaluator to status/search/get-source/store/memory-propose, with exact-resource reauthorization on get-source and authorization-aware search filtering. Do not create ACL credentials until those routes are proven.
