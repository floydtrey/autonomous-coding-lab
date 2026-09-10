# Portable Installation Identity

**Status:** accepted non-executing portability checkpoint

**Accepted implementation checkpoint:** `17a81ebcfffcb43a92f1ab44d8a10b89e75e9517`

**Execution authority:** `DISABLED`

## Purpose

ACL installation identity is split into two layers so the same reviewed repository can be used on different Windows hosts without editing repository authority for usernames, drive letters, executable locations, or provider-specific launchers.

1. The committed **portable installation contract** identifies reviewed ACL component bytes, component scopes, minimum Windows/Python compatibility, and the disabled activation policy.
2. **Host/runtime qualification** records machine-specific executable paths, executable hashes, provider identity, and provider-specific readiness separately.

A host may therefore satisfy portable repository identity while provider runtime remains unqualified and execution remains unavailable.

## Portable authority

The portable contract is `config/portable-installation-manifest.json`, schema `acl-portable-installation-manifest:v1`.

It intentionally contains no absolute host path and no Codex, Qwen, Ollama, llama.cpp, or other provider executable identity. Provider identity is governed by `host-qualified-separately:v1`.

The portable baseline requires:

- Windows;
- CPython 3.12 on AMD64;
- exact Autonomous Worker Framework runtime-dependency closure;
- exact Local Model Bench Python production tree;
- exact Worker Lab Python production tree;
- `execution_authority = DISABLED`;
- Autonomous Worker Framework `AVAILABLE`;
- Local Model Bench `ADVISORY`;
- Worker Lab `DEFERRED`.

The verifier is `tools/verify_portable_installation.py`. It hashes installed bytes directly and does not import Worker Lab as its trust root. It does not launch a worker, model, provider, framework adapter, or target-repository command.

## Accepted component identities

At the accepted checkpoint:

- Autonomous Worker Framework: `sha256:c256608be92ee21852e9ee407ac3446787fbe8f4122679475b69e8949909e7dd`;
- Local Model Bench: `sha256:139331ea42c914575d1119125a702ac5de2129b9bedc235bfc189700e8265afc`;
- Worker Lab: `sha256:15ee7b4e978e8d1facf79968c9e9d14f002b020d891cfca04aa9b391e896f12d`.

## Windows checkout normalization

Component identity is byte-exact. Local Model Bench now carries `.gitattributes` rules matching the deterministic source/config/documentation checkout policy already used by the execution components. Python source is materialized as LF even when global Git configuration has `core.autocrlf=true`.

An existing clone created before these attributes may retain old working-tree bytes even after pulling the attributes file. If portable verification reports a Local Model Bench digest mismatch, first inspect the working tree and line endings. For a known-clean clone, rematerialize only `components/local-model-bench/src/localbench` from `HEAD` under the current attributes and verify again. Do not change the portable manifest to bless host-specific legacy checkout bytes.

A fresh clone on the new tower should receive the current attributes during its first checkout and should not require this one-time migration.

## Accepted laptop qualification evidence

The portable verifier was exercised on the current Windows development laptop after canonical Local Model Bench rematerialization.

Observed host:

- repository root: `C:\Projects\autonomous-coding-lab`;
- platform: Windows;
- Python: CPython 3.12.10 AMD64;
- Python executable: `C:\Program Files\Python312\python.exe`;
- Python SHA-256: `sha256:4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`.

Accepted result:

- all three portable component identities: `MATCH`;
- manifest SHA-256: `sha256:cd26f5d74e9fc11bff296e98ea0760badc619659d9d559f754dd43e13970fdb8`;
- `provider_runtime_qualified = false`;
- `execution_authority = DISABLED`;
- `execution_ready = false`.

Focused verifier tests passed: **3 passed**. No worker, model, provider runtime, adapter execution mode, authorization, dispatch, target test, commit, push, or external/product-repository operation occurred.

## Legacy execution manifest

`config/installation-manifest.json` is retained because the accepted Worker Lab/Autonomous Worker Framework execution path still consumes its strict v2 identity, including a historically pinned Codex runtime. It is **not** the portable host-installation authority.

Accordingly, `worker-lab doctor` may reject a machine that does not have that exact historical Codex runtime even when the portable ACL installation is valid. That is an execution-path compatibility result, not a portable-installation failure.

Do not rewrite the legacy manifest around a laptop or tower merely to make `doctor` green. The future selected worker/harness provider must receive its own host qualification and then be integrated behind ACL-owned authority and task/result contracts.

## New tower bootstrap boundary

For the new computer:

1. clone/check out the accepted ACL repository normally;
2. confirm the working tree is clean;
3. install a compatible CPython 3.12 AMD64 runtime;
4. run `python .\tools\verify_portable_installation.py` from the repository root;
5. require all component identities to report `MATCH` and execution to remain disabled;
6. qualify the selected local worker/harness runtime separately only after that provider has been chosen;
7. do not activate execution merely because portable or provider qualification succeeds.

Absolute paths and executable hashes observed on the tower belong to host qualification evidence, not to the portable repository contract.

## Closed and deferred boundaries

This checkpoint closes the repository/host portability problem exposed by the stale `MineTrackerWorker` installation assumptions.

It does **not**:

- qualify a local-model provider or third-party harness;
- authorize Worker Lab or framework execution;
- migrate the legacy Codex execution manifest;
- prove a real workspace-write worker run;
- select a Qwen model;
- implement controller planning or dispatch.

Provider/runtime qualification is deliberately deferred until the vertical slice selects its worker harness. The next implementation work should continue along the shortest vertical-slice dependency path while execution remains disabled.
