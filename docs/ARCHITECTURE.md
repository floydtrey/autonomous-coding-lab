# Architecture

ACL is a supervised system for turning a user objective into one bounded, independently verified task execution. Repository mechanics are optional backend details, not the system abstraction.

## Authority plane

Worker Lab owns the protected definition and lifecycle of work:

- curriculum/exercise, policy, role, context manifest, and test catalog;
- attempts and workspace receipts;
- Controller Task Packet identity;
- runtime requirement and sealed runtime settings;
- provider capability qualification and Provider Binding;
- Invocation/Result V3 lifecycle;
- containment/custody evidence;
- independent result/candidate acceptance.

A provider, model, harness, or worker cannot self-authorize or self-certify acceptance.

## Informational knowledge plane

Knowledge Core stores and retrieves governed information. Controller Task Packet V1 binds exact Knowledge Core evidence into the task prompt while marking it informational-only. Retrieved content cannot add readable/writable paths, tools, tests, capabilities, publication authority, or lifecycle authority.

## Execution plane

Autonomous Worker Framework receives one canonical dispatch envelope and independently validates the protected identities/scope. It reconstructs the bounded task and invokes one explicitly supplied provider executor whose adapter, tool surface, Provider Binding, and runtime settings match the sealed request.

The provider receives only ACL-owned tools. Current bounded coding tools are exact-file read/write operations. Shell, process, arbitrary network, Git publication, approval, and unrestricted directory traversal are not implied provider capabilities.

## Provider model

The provider path is data-driven:

```text
installation observation
  -> controlled capability qualification
  -> Provider Binding
  -> Worker Lab task authorization
  -> bounded dispatch
```

Observation describes installed facts. Qualification proves the required controlled tool/context behavior. Provider Binding freezes the exact qualified combination for authorization. None of these layers is local activation by itself.

Pydantic AI + Ollama is the first adapter implementation. Another supported provider/model should require new observation/qualification/binding data, not changes to Worker Lab authority contracts.

## Containment

Durable process custody uses a provider-neutral V2 contract. Windows Job Objects implement the current Windows backend. A future Linux backend must fit the same authority/custody contract rather than changing Invocation/Result identity.

## Identity layers

1. **Portable source identity** — reviewed ACL component bytes (`acl-portable-source-manifest:v2`).
2. **Host/provider observation** — platform, Python/harness, provider executable/API, model metadata.
3. **Capability qualification** — controlled proof that the exact observed configuration satisfies required behavior.
4. **Provider Binding** — immutable provider/model/settings identity used before task authorization.
5. **Local activation/containment state** — operator/host state, never committed source identity.
6. **Task authorization** — one exact Worker Lab invocation and controller decision.

## Target/workspace boundary

Invocation V3 uses logical target/workspace identities. For the current coding slice, Git-backed source state is nested capability-specific evidence: base commit, workspace receipt/root/path digests, observed head, content digest, and changed paths.

Repository names, URLs, remotes, branch names, checkout paths, and `.git` are not logical ACL target identity.

## Acceptance boundary

Worker success is only a claim. Worker Lab independently checks durable custody, exact request/binding identities, authorized changed paths, sealed tests, candidate/result identity, and workspace evidence before lifecycle promotion.

Workers do not commit, push, merge, publish, or approve their own result unless a separate protected publication capability is explicitly introduced and authorized.

## Advisory benchmark

Local Model Bench is independent and advisory. Its measurements can help choose which model/configuration to qualify for a role. Benchmark output never modifies Worker Lab policy, Provider Binding, or task authorization.
