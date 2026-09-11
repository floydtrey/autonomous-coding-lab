# Portable Source Identity V2

## Purpose

Portable Source Identity V2 answers one question: **which reviewed ACL source/component bytes are this runtime built from?**

It does not answer whether a host, provider, model, containment backend, or task is qualified or authorized.

## Contract

Manifest: `config/portable-source-manifest.json`  
Schema: `acl-portable-source-manifest:v2`  
Source identity: `acl-runtime-source:v2`  
Verifier: `tools/verify_portable_source.py`

The manifest contains:

- Autonomous Worker Framework current runtime dependency closure;
- Worker Lab Python production tree;
- Local Model Bench Python production tree;
- exact SHA-256 file-set digests;
- an explicit separation policy declaring host qualification, provider capability qualification, local activation, and task authorization external to source identity.

It contains no Windows requirement, CPU architecture, Python executable path/version, provider/model state, participant activation state, or execution-ready flag.

## Digest model

Each component digest is the canonical SHA-256 of ordered entries:

```text
{"path": <component-relative path>, "sha256": <file bytes digest>}
```

The framework uses an explicit current runtime closure. Worker Lab and Local Model Bench use their production Python trees. Paths are checkout-relative and path traversal/symlink indirection is rejected at the verification boundary.

## Separation policy

- `host_qualification = separate-evidence`
- `provider_capability_qualification = separate-evidence`
- `local_activation = local-operator-state`
- `task_authorization = worker-lab-invocation-v3`

A source checkout is never enabled by editing this manifest. If a host-level kill switch/activation mechanism is introduced, it must be local operator state outside committed source identity.

## Verification

Run from any compatible checkout:

```text
python tools/verify_portable_source.py
```

A `MATCH` report proves exact source bytes only. It does **not** prove host compatibility, provider capability, local activation, or task authorization.

## Portability meaning

Moving ACL to another compatible host should require host/containment/provider qualification, not edits to source identity merely because paths, OS details, Python executable location, GPU/runtime, or provider installation differ.
