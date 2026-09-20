# Knowledge Core ownership boundary

This document answers one question: **what belongs in Knowledge Core?**

## Product definition

Knowledge Core is a provider-neutral service for governed durable knowledge.

A capability belongs in KC when its primary responsibility is one of:

1. canonical knowledge identity/history;
2. exact source custody/provenance;
3. admission or governance of knowledge;
4. authorization to KC knowledge;
5. deterministic retrieval over KC knowledge;
6. derived knowledge projection with canonical source correlation;
7. privacy/restriction/deletion of KC-managed knowledge;
8. KC service/API operation.

A capability does not belong in KC merely because an AI client uses it.

## Included in KC

### Canonical semantic kernel

Entities, assertions, occurrences, resources, resource versions, provenance links, semantic profiles, temporal/history behavior, operation/idempotency controls, identity transitions, generations, deletion/restriction state, and governed source evidence.

### Knowledge admission

Direct authenticated notes, source-neutral observations/governance, memory-candidate staging, and verified Git repository ingestion.

Repository import is a KC feature because it transforms an external source into governed KC evidence. It does not make KC part of the source repository or of any consuming agent.

### Authorization

KC principals, service credentials, groups, scopes, grants, resource visibility/sensitivity, ownership/origin identity, and deterministic authorization decisions.

KC authorization answers: **may this principal perform this KC operation against this knowledge/scope?**

It does not answer: **may this AI execute an external action?**

### Retrieval

Deterministic segmentation, PostgreSQL lexical search, exact-source retrieval, lifecycle filtering, and source correlation.

### Derived graph projection

Provider-neutral projection evidence plus the optional hardened Graphiti/FalkorDB implementation. Graph state is derived and rebuildable. Graph facts cannot enlarge knowledge authority.

### Consumer service

The authenticated, bounded `/v1/kc/*` network surface and its server-side configuration.

## Explicitly outside KC

The following are client/application responsibilities and must not be reintroduced into the KC core:

- ACL Controller/Planner/Worker/Reviewer/Determiner lifecycle;
- any agent execution loop or task scheduler;
- tool/filesystem/process/network permissions outside KC;
- Vera action authority;
- purchasing/payment approval;
- browser control;
- smart-home/device control;
- voice-command identity;
- MFA/passkeys/device enrollment;
- general user login/session management;
- model/harness loading and routing;
- Cowork/MindsHub conversation wrappers;
- Mason-specific bridge/CLI/skill installation;
- client context compaction/continuation;
- ChatGPT-specific transport code.

Clients may implement these features and call KC through the consumer API.

## Optional adapters versus core

Provider implementations are allowed when they implement a KC-owned abstraction without defining KC's semantics.

Current example:

- `knowledge_core_providers/graphiti*.py` implements the provider-neutral projection interface.

Client adapters do not belong in this repository. A future ACL KC client, Vera KC client, web extension, or ChatGPT importer should live with that client or in a separate integration package.

## Security consequence

Separating these responsibilities prevents a compromised client from inheriting KC infrastructure authority.

The intended path is:

```text
client credential
  -> KC authentication
  -> KC authorization
  -> bounded semantic operation
  -> canonical/derived KC data
```

not:

```text
client
  -> PostgreSQL / FalkorDB / artifact filesystem / model server
```

## Review boundary

Security review of this repository should focus on:

- KC credential authentication and revocation;
- principal/scope confusion;
- grant resolution and resource-policy enforcement;
- direct-object authorization;
- SQL retrieval filtering;
- canonical write admission;
- provenance/source-correlation integrity;
- graph-derived information laundering;
- TOCTOU authorization around external providers;
- stale projection resurrection;
- privacy/restriction/deletion behavior;
- secret/log/error leakage;
- exposed HTTP routes;
- deployment assumptions for PostgreSQL, artifact storage, FalkorDB, and model runtimes.

Agent execution security belongs to the consuming agent project and should be reviewed there separately.
