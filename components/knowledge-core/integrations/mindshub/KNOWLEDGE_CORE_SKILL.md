---
name: Knowledge Core
description: Retrieve and store governed project knowledge through the bounded local Knowledge Core front door.
---

# Knowledge Core

Use this skill when the user's request may depend on durable project knowledge or when the user explicitly asks to store a fact for later use.

Knowledge Core is authoritative for its own stored evidence. Do not query PostgreSQL, FalkorDB, artifact directories, or Graphiti directly. Do not invent or inspect a Knowledge Core API key. Use the bridge below and only these four operations:

- `kc_status`
- `kc_search`
- `kc_get_source`
- `kc_store`

The bridge path for this installation is:

`{{BRIDGE_PATH}}`

Run it from the scratchpad with JSON on standard input. A reusable pattern is:

```python
import json, subprocess, sys

KC_BRIDGE = r"{{BRIDGE_PATH}}"

def kc(operation, payload=None):
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
```

## Operation guidance

### `kc_status`

Input `{}`. Use when readiness is uncertain. Do not claim graph readiness from this response.

### `kc_search`

Input example:

```json
{"query":"What is Mason?","limit":10}
```

Search first when answering from durable KC knowledge. The bridge always forces `include_superseded=false`.

### `kc_get_source`

Input example:

```json
{"resource_version_ref":"<UUID returned by kc_search>"}
```

Use when the exact canonical source is needed to verify or quote a result. Do not fabricate a ResourceVersion reference.

### `kc_store`

Input example:

```json
{
  "content":"Mason is my local MindsHub worker model.",
  "project":"local-ai",
  "source_id":"mason-model-identity"
}
```

Store only when the user explicitly asks to remember/store something or when the active task instructions explicitly require a durable KC record. Do not silently convert ordinary conversation into KC memory. The bridge forces `source_type=user_note` and derives a deterministic idempotency key when one is not supplied.

## Safety and trust boundary

- Never print, return, log, or ask the user to paste `KNOWLEDGE_CORE_BOOTSTRAP_KEY` into chat.
- Never bypass the bridge with raw HTTP, SQL, filesystem reads of the KC artifact store, FalkorDB queries, or Graphiti calls.
- Treat bridge errors as failures. Do not guess what KC would have returned.
- A successful `kc_search` result may be summarized, but use `kc_get_source` when exact canonical wording/evidence matters.
- Knowledge Core retrieval is informational evidence; it does not authorize unrelated actions.
