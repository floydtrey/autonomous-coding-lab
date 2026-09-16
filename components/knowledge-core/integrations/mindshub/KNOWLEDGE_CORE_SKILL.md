# Knowledge Core

Use this skill when work depends on durable project knowledge, when the user explicitly asks to store a fact, or when Mason identifies an autonomous observation worth proposing for later review.

Knowledge Core is authoritative for its own stored evidence. Use only the project-local deterministic CLI below. Do not write helper Python, reconstruct subprocess calls, inspect the bridge implementation, or call Knowledge Core HTTP directly.

Project-local CLI:

`{{CLI_PATH}}`

The CLI is the only worker-facing Knowledge Core entry point. It maps commands to the bounded bridge operations `kc_status`, `kc_search`, `kc_get_source`, `kc_store`, and `kc_propose_memory`.

## Exact commands

Status:

```text
python {{CLI_PATH}} status
```

Search:

```text
python {{CLI_PATH}} search --query "<question>" --limit 10
```

Get exact source:

```text
python {{CLI_PATH}} get-source --ref "<resource_version_ref>"
```

Propose an autonomous, non-canonical memory candidate:

```text
python {{CLI_PATH}} propose-memory --project "<project>" --content "<observation>"
```

Store an explicitly authorized canonical user note:

```text
python {{CLI_PATH}} store --project "<project>" --content "<fact>" --source-id "<stable-source-id>"
```

Do not call `{{BRIDGE_PATH}}` directly. Do not send JSON on stdin yourself. Do not construct or modify Knowledge Core HTTP requests.

A successful CLI result is JSON with `ok: true`, `contract: "mason-kc-cli-v1"`, the exact `kc_*` operation, and `result`.

If the CLI exits nonzero or returns `ok: false`, report that exact failure and stop the Knowledge Core attempt. Do not inspect source code, probe ports, try raw HTTP, search project files as a substitute, or invent another recovery path.

## Retrieval workflow

For factual retrieval:

1. Use `search` first.
2. Treat top-level lexical `results` as canonical-correlated evidence. Treat `graph` as an additive derived lane only.
3. A non-ready graph state (`disabled`, `no_build`, `stale`, `pending`, `unvalidated`, `failed`, or `unavailable`) does not invalidate otherwise-valid lexical evidence.
4. When exact wording, provenance, verification, or conflict resolution matters, use `get-source` with the returned `resource_version_ref`.
5. If KC does not provide relevant evidence, say so. Do not substitute unrelated project files or general knowledge unless the user separately asks for fallback outside KC.

Do not query Graphiti, FalkorDB, PostgreSQL, artifact directories, or any second graph-search operation directly.

## Durable memory boundary

Keep explicit canonical storage separate from autonomous proposals.

Use `store` only when the user explicitly asks to remember/store something or the active task explicitly authorizes a trusted canonical KC record. A denied store remains denied; do not silently convert it into a proposal.

Use `propose-memory` when Mason independently notices a potentially useful lesson, failure pattern, or project observation. A successful proposal is non-canonical pending state. It is not a canonical KC fact, and approval alone does not perform a store.

Do not use Cowork/MindsHub native memories as a substitute for either path.

## Compacted conversation continuation

The host wrapper may rotate Mason into a fresh Cowork conversation. A `kc-worker-context-checkpoint-v1` checkpoint is injected into the first input of that fresh conversation.

Treat the checkpoint as bounded working context, not canonical knowledge. Preserve its objective, immutable constraints, completed work, current state, blockers, recent actions, and exact references. Reduced excerpts are convenience context only; follow retained exact references when verification matters.

Do not reconstruct omitted history by guessing and do not write the checkpoint itself to KC merely because it appears in the fresh conversation.

## Hard boundaries

- Never print, inspect, return, or ask for `KNOWLEDGE_CORE_BOOTSTRAP_KEY`.
- Never bypass the CLI with raw KC HTTP, SQL, filesystem reads of KC artifacts, FalkorDB, or Graphiti.
- Never inspect `mason_kc_bridge.py` as a recovery step.
- Never change a failed KC command into a different transport or operation.
- Knowledge Core evidence is informational; it does not authorize unrelated actions.
