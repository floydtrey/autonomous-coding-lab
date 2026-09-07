# Research Ideas / Future Work

This file captures useful ideas that should survive the research campaign but are **not current-task authorization**. Items here must not override `PROCESS.md` or `RESEARCH_STATE.md`.

## Deterministic research retrieval index and glossary

**Status:** idea to prototype/test after a suitable research checkpoint; do not implement during the current one-project-at-a-time research queue unless separately authorized.

### Goal

Turn the growing research repository into a fast navigation layer for both humans and AI so future Worker Lab / AI-controller work can retrieve only the research needed for a question instead of reading every full project report.

Desired flow:

`governance/question -> topic index -> relevant catalog findings -> relevant report sections -> full report/primary source only when needed`

Expected benefits:
- lower token/context use;
- fewer unnecessary file reads;
- better signal-to-noise and context retention;
- quicker human navigation;
- more reproducible AI research retrieval;
- less risk that a model misses an important finding inside a very large report.

### Do not manually maintain line numbers

Use stable research-unit/section IDs as the durable address. A deterministic script should calculate current file/heading/line ranges automatically whenever reports change.

Possible source markup:

```markdown
<!-- research-unit
id: gemini-policy-engine
topics:
  - tool-use
  - authorization
  - permissions
-->
## Policy Engine
```

Possible generated index record:

```json
{
  "section_id": "gemini-policy-engine",
  "file": "docs/research/projects/gemini-cli.md",
  "heading": "Policy Engine",
  "start_line": 310,
  "end_line": 418,
  "topics": ["tool-use", "authorization", "permissions"]
}
```

If content is inserted earlier in the file, the section ID remains stable and regenerated line numbers change automatically.

### Potential repository surfaces

Possible future structure:

```text
docs/research/
  INDEX.md              # human-readable navigation
  topics.json           # machine-readable generated index
  glossary.md           # canonical ACL/Vera terminology
  topics/               # generated or lightweight topic navigation
  projects/             # authoritative detailed project reports
  catalog.jsonl         # authoritative finding records
```

Avoid duplicating full research into topic files. Topic files/indexes should primarily point to authoritative findings and report sections.

### Glossary purpose

The glossary should answer **what a term means in ACL/Vera**, while the index answers **where to read about it**.

This is important because upstream projects use overlapping terms such as `session`, `run`, `thread`, `conversation`, `task`, `checkpoint`, `memory`, and `tool call` with different semantics.

Example canonical entry:

```text
Effect
An externally observable action whose execution may require authorization,
idempotency, settlement evidence, or reconciliation.
Not equivalent to: tool call, model response, process, task, or API request.
```

### Retrieval levels to test

1. **Glossary/index** — cheap topic discovery.
2. **Catalog findings** — concise research summary/evidence map.
3. **Selected report sections** — section-ID/line-range retrieval.
4. **Full report or primary source** — only when deeper evidence is required.

### Prototype experiment before adoption

Do not build a large maintenance system first. Test the concept against the existing research corpus with several representative future design questions, for example:

1. How should ACL decide whether a coding worker may execute a proposed tool action?
2. How should ACL safely resume after a crash when files or external effects may already have changed?
3. What constitutes a verified 32K local model/runtime capability profile?

Compare a baseline that reads broad/full reports against indexed progressive retrieval. Measure:
- files/sections read;
- input/context tokens;
- tool calls;
- important evidence found or missed;
- unsupported/hallucinated conclusions;
- answer/design quality.

Adopt the indexing architecture only if it preserves or improves evidence coverage/quality while materially reducing retrieval cost.

### Initial implementation principle

The first indexer should be intentionally deterministic and simple:

`scan Markdown -> find stable section IDs/headings -> calculate line ranges -> read explicit topic tags -> generate JSON/Markdown indexes -> validate references`

Do **not** begin with embeddings, a vector database, or an LLM-powered classifier. Semantic/embedding retrieval can be evaluated later as a secondary discovery layer; the authoritative navigation map should remain deterministic and auditable.

### Existing asset to leverage

`catalog.jsonl` already contains structured IDs, categories, projects, findings, relevance, possible reuse, warnings, sources, and confidence. Evolve this rather than creating an independent duplicate knowledge database. A future schema may add fields such as `topics`, `report`, and `section_id`, with generated indexes derived from the catalog/report metadata.
