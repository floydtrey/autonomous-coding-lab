# Knowledge Core Graphiti Qualification Baseline — KC-G0

**Status:** evidence captured; clean-host reproduction still pending

## Purpose

Freeze the local Graphiti/FalkorDB/Ollama qualification evidence before Graphiti is introduced behind a Knowledge Core projection boundary. This is an evidence record, not authorization to activate Graphiti in KC.

Existing KC decisions remain controlling: PostgreSQL is canonical (KC-D002), Authority is a separate deterministic boundary (KC-D004), retrieval is authorization-first (KC-D014), derived projections are lineage-bound/rebuildable (KC-D015), and canonical writes are idempotent (KC-D018).

Graphiti-specific identity must never become canonical KC identity.

## Observed local baseline

- `graphiti-core 0.30.2`
- FalkorDB local Docker endpoint: `localhost:6379`
- Ollama `0.34.0`
- embedding model: `nomic-embed-text:latest`, dimension 768
- extraction model: `qwen3.5:9b`
- dedicated alias: `graphiti-qwen35-9b-32k`
- runtime context: 32768
- qualification generation allowance: 12288
- reasoning/thinking: disabled
- structured output: JSON schema

The local integration used a separate `OpenAIGenericClient` subclass that supplied `reasoning_effort="none"`; upstream Graphiti source was restored after debugging. KC should retain that adapter pattern rather than patching the backend.

## Diagnosed failure evidence

The initial `LLM returned an empty response` case was isolated to thinking enabled with a 4096 runtime context. Entity/edge work succeeded, later generation consumed the available context, and no final structured answer was emitted. A direct structured-output request with reasoning disabled succeeded.

Classification:

```text
not Graphiti structured-output failure
not fundamental Qwen tool/reasoning inability
cause: thinking + 4096 runtime context exhausted completion before final JSON
```

## Successful local plumbing proof

A basic local episode proved:

- Graphiti initialization
- FalkorDB connection
- local Ollama structured JSON
- local embeddings
- graph ingestion
- graph search
- 32K runtime context
- reasoning disabled

This proves plumbing only, not trusted knowledge quality.

## Partial-projection evidence

A later correction/temporal experiment produced missing-endpoint warnings while the high-level episode calls still returned. The same experiment also reused the default graph scope and retrieved material from an earlier test.

Therefore that run is not valid temporal qualification. It did prove two important failure classes:

1. namespace contamination must be prevented by explicit projection/retrieval scope;
2. a successful backend call can still yield an incomplete projection.

KC must never equate `add_episode()` returning with trusted memory being stored.

## Existing KC foundations to reuse

The active branch is ahead of the older Graphiti handoff assumptions. It already has canonical PostgreSQL/resource history, content-addressed artifacts, idempotent operation identity, governed repository import, deterministic structural segmentation, generation-bound derived retrieval, exact source provenance, serving fences, and KC Consumer V1 segment-content serving.

Graphiti integration must extend these foundations rather than create a competing canonical ingestion/history system.

## Required invariants

Before graph-backed results can become trusted KC context:

1. canonical source evidence survives graph-backend failure;
2. canonical ingestion disposition and projection disposition remain separate;
3. every trusted graph result maps back to exact KC-owned evidence;
4. graph relationships never grant Authority;
5. Authority/scope filtering occurs before protected content reaches an LLM;
6. projection warnings and missing endpoints become durable machine-readable evidence;
7. incomplete projection cannot silently become accepted;
8. projection/retrieval namespace is explicit;
9. backend/model/config identity is recorded for projection attempts;
10. graph backend identifiers are correlation data, not durable KC identity;
11. derived graph state is rebuildable from canonical KC evidence;
12. an uncorrelated graph result is not trusted model context.

## Gate state

**Evidence capture: PASS.** The known successful and failed local configurations and the architectural consequences are now frozen here.

**Clean-host reproduction: PENDING.** Do not call KC-G0 fully accepted until the successful basic path is reproduced from a controlled host configuration and its evidence is preserved. Prefer reproducing it through the real KC projection boundary rather than another disposable demo.

## Next bounded task

Do not integrate Graphiti yet. The next task is the minimum deterministic retrieval-Authority boundary: caller identity must no longer be required syntactically and then discarded. It must fail closed, remain provider-neutral, preserve existing KC provenance/serving fences, and be replaceable by the separate Authority service accepted in KC-D004.
