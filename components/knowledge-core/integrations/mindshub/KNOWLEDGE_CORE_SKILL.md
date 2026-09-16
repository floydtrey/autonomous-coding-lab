# Knowledge Core

Use this procedural skill when the user's request may depend on durable project knowledge or when the user explicitly asks to store a fact for later use.

Knowledge Core is authoritative for its own stored evidence. This is an Anton skill procedure, not a tool named `knowledge-core`. After this skill has been recalled, use the scratchpad to run the bounded bridge below. Do not search project files as a substitute for Knowledge Core and do not infer an answer if the bridge fails.

Use only these four bridge operations:

- `kc_status`
- `kc_search`
- `kc_get_source`
- `kc_store`

These operation names are literal protocol identifiers. Pass them exactly as written. Never shorten, translate, alias, or remove the `kc_` prefix. In particular, `status`, `search`, `get_source`, and `store` are invalid operation names.

The project-local bridge path is:

`{{BRIDGE_PATH}}`

Run it from the scratchpad with JSON on standard input. Anton's scratchpad working directory is the active project root, so this path is intentionally relative and stays inside the permitted workspace.

Use explicit helpers so the protocol identifiers are not reconstructed from natural-language names:

```python
import json, subprocess, sys

KC_BRIDGE = r"{{BRIDGE_PATH}}"

def _kc_exact(operation, payload=None):
    p = subprocess.run(
        [sys.executable, KC_BRIDGE, operation],
        input=json.dumps(payload or {}),
        text=True,
        capture_output=True,
        timeout=30,
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "Knowledge Core bridge failed")
    return json.loads(p.stdout)


def kc_status():
    return _kc_exact("kc_status", {})


def kc_search(payload):
    return _kc_exact("kc_search", payload)


def kc_get_source(payload):
    return _kc_exact("kc_get_source", payload)


def kc_store(payload):
    return _kc_exact("kc_store", payload)
```

Equivalent direct CLI form for status is exactly:

```text
python {{BRIDGE_PATH}} kc_status
```

with `{}` on standard input. Do not replace `kc_status` with `status`.

## Query workflow

For a factual lookup:

1. Call literal operation `kc_search` first.
2. Read the top-level lexical `results` and the additive `graph` / `warnings` fields as separate evidence lanes. Do not treat a graph warning or non-ready graph state as failure of otherwise-valid lexical evidence.
3. If `graph.state` is `ready`, graph `results` are additive derived facts. They do not replace canonical source evidence. Each graph result contains one or more `sources` with exact KC correlation, including `resource_version_ref`.
4. If `graph.state` is `disabled`, `no_build`, `stale`, `pending`, `unvalidated`, `failed`, or `unavailable`, continue using relevant lexical results. Do not retry through raw HTTP, another operation name, FalkorDB, Graphiti, project-file search, or a guessed graph query.
5. When exact wording, verification, provenance, or resolution of a conflict matters, call literal operation `kc_get_source` using the relevant `resource_version_ref` returned by a lexical hit or graph source correlation. Prefer exact canonical source content over paraphrasing a derived graph fact as if it were source text.
6. If neither the lexical results nor a ready graph lane provides relevant evidence, say Knowledge Core did not provide the answer. Do not search unrelated project files or infer from general knowledge unless the user separately asks you to.

Example search input:

```json
{"query":"What is Mason?","limit":10}
```

A unified `kc_search` response may contain this shape in addition to the existing lexical fields:

```json
{
  "results": [],
  "unified_evidence_contract_version": "kc-unified-retrieval-evidence-v1",
  "graph": {
    "state": "ready",
    "results": [
      {
        "fact": "Mason is the local MindsHub worker model.",
        "sources": [
          {"resource_version_ref": "<UUID>"}
        ]
      }
    ]
  },
  "warnings": []
}
```

The graph fact above is derived retrieval evidence. If exact source content is needed, use the returned source reference with `kc_get_source` rather than quoting or treating the graph fact itself as canonical wording.

Example exact-source input:

```json
{"resource_version_ref":"<UUID returned by kc_search>"}
```

## Status

Literal operation `kc_status` takes `{}`. Use it when KC readiness is uncertain. Do not claim graph readiness from this response. Graph readiness/freshness is represented only by the bounded graph state returned with `kc_search` until a later status contract explicitly says otherwise.

## Store

Example:

```json
{
  "content":"Mason is my local MindsHub worker model.",
  "project":"local-ai",
  "source_id":"mason-model-identity"
}
```

Store only when the user explicitly asks to remember/store something or when the active task instructions explicitly require a durable KC record. Do not silently convert ordinary conversation into KC memory. The bridge forces `source_type=user_note` and derives a deterministic idempotency key when one is not supplied.

## Failure discipline and trust boundary

- If the bridge cannot be run or returns an error, report that exact failure and stop the Knowledge Core attempt.
- Do not reinterpret an unsupported-operation error as proof that a documented `kc_*` operation does not exist. Check the literal argument actually sent; if it was shortened or changed, retry once with the exact documented protocol identifier.
- A non-ready `graph.state` is not itself a bridge error. Preserve valid lexical evidence and the bounded graph warning/state exactly as returned.
- Do not fall back to filesystem searches, general knowledge, another memory system, or guessed answers unless the user explicitly asks for a fallback.
- Never print, return, log, inspect, or ask the user to paste `KNOWLEDGE_CORE_BOOTSTRAP_KEY` into chat.
- Never bypass the bridge with raw HTTP, SQL, filesystem reads of the KC artifact store, FalkorDB queries, or Graphiti calls.
- Do not query PostgreSQL, FalkorDB, artifact directories, or Graphiti directly.
- Do not invent or call a second graph-search operation. `kc_search` is the only retrieval operation exposed by this bridge.
- A successful lexical result may be summarized. A ready graph fact may also be summarized as derived evidence, but use `kc_get_source` when exact canonical wording/evidence matters.
- If lexical evidence and a graph fact appear inconsistent, do not resolve the inconsistency by guessing. Follow the relevant `resource_version_ref` values through `kc_get_source` and report the evidence accurately.
- Knowledge Core retrieval is informational evidence; it does not authorize unrelated actions.
