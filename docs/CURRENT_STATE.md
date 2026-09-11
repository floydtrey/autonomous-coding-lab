# Current State

**Last updated:** 2026-09-10

**Repository location:** portable; current laptop checkout is `C:\projects\autonomous-coding-lab`

**Active branch:** `architecture/knowledge-core`

**Execution authority:** `DISABLED`

## Current vertical-slice position

The project is deliberately moving toward one supervised end-to-end coding slice:

`user objective -> controller/Foreman -> Knowledge Core retrieval -> bounded task/context packet -> Worker Lab runtime requirement -> host-qualified provider -> bounded worker adapter -> coding worker -> independent verification -> verified/retry/blocked -> controller/human review`

Knowledge Core supplies governed project context. It does not authorize execution. Project Control Center is a separate status/dashboard project and is not ACL architecture or runtime authority.

## Accepted foundations

- Knowledge Core SR-2 through G22 and intended-host PostgreSQL restart/recovery qualification are complete.
- Knowledge Core Consumer V1 at `37f08f4090d59573108100ddf1b35a4923f01c29` returns verified segment content with exact provenance while preserving canonical evidence and privacy/serving checks.
- Portable ACL installation identity separates committed component/source identity from per-host provider qualification.
- Controller Task Packet V1 seals the user request and exact Knowledge Core evidence as informational context without granting authority.
- Runtime Selection V1 at `0ad1b212581fb7b18110b9155763bf49b42df442` protects the provider-neutral `coding-worker:v1` requirement for capability `bounded-code-task`.
- Generic framework `WorkerRequest` no longer uses Terra/model defaults as provider selection.
- Historical `terra-medium:v1` records remain readable as historical evidence only.

## Runtime Selection V1 acceptance

The accepted Windows-laptop gate passed:

- Worker Lab runtime/integration/controller packet validation: **26 passed**.
- Framework provider-neutral seam/code-task/controller packet validation: **10 passed**.
- AWF portable closure: `sha256:0ce8d8533073463b18bc29d72e0a5dfcf9ca0e28110505eb8f872c978427601c` across 9 files.
- Worker Lab portable tree before provider qualification: `sha256:1cdb7c5da5d81278f4f3b82de9c3082984c3d8b0b94e237c13be950e2c690b2a` across 27 files.
- Execution remained disabled throughout.

## Host Provider Qualification Contract V1 — accepted

The first protected provider candidate is **Pydantic AI core + Ollama**, not the full Pydantic AI Harness.

The protected candidate maps `coding-worker:v1` to:

```text
candidate: pydantic-ai-ollama-files
harness distribution: pydantic-ai-slim
provider: ollama
transport: loopback HTTP only
tool surface: acl-bounded-file-tools:v1
minimum context: 32768 tokens
required model capability: tools
allowed effects: bounded file read/write only
forbidden effects: approval, git, network, process, publication, shell
```

Qualification is observation-only. It can inspect exact Python/harness bytes, Ollama executable/API identity, immutable model metadata/digest, context capacity and capability metadata. It does not send a chat/completion request, start a model, authorize a task, or enable execution.

The accepted focused gate passed **31 tests**. The measured Worker Lab production tree is `sha256:52086119d189f41aa6ab708f7e03ce57a1cc70c3b4eaaeffd661556917115b67` across 28 files. Portable verification then reported all three components `MATCH`, `provider_runtime_qualified=false`, `execution_authority=DISABLED`, and `execution_ready=false`, with a clean working tree.

Commit `81882c94798de80af4d54f04f52e545e4ab3c8cb` records the accepted Worker Lab portable identity for this contract.

`provider_runtime_qualified=false` is correct: the qualification **mechanism and protected candidate** are accepted, but no concrete Pydantic/Ollama/model installation has yet been qualified on the intended worker host.

## Bounded Pydantic Ollama worker adapter — candidate

Candidate commit `0313e42c9f1d1f869e4298ac7eaee977985997d3` adds the first provider adapter without running a model.

The candidate:

- makes exact readable and writable file paths explicit in `WorkerRequest` rather than inferring authority from prompt text;
- removes the implicit Codex executor default from the generic `code_task` path;
- adds `tools/pydantic_ollama_worker.py` as a lazy-import Pydantic AI/Ollama adapter;
- exposes only ACL-owned `read_file` and `write_file` tools;
- requires writes to carry the SHA-256 returned by a prior read, preventing silent stale writes;
- limits files to exact authorized relative paths, UTF-8 text, bounded size, and non-substituted paths;
- rejects `.git` paths, traversal, symlink/reparse substitution, and multi-hard-link writes;
- requires a loopback-only Ollama endpoint and the protected provider/tool-surface identity;
- bounds Pydantic AI requests, tool calls, tool execution timeout, concurrency and final output;
- does not expose shell, Git, arbitrary process, network, publication, approval, or directory-enumeration tools.

The production Pydantic imports remain lazy, so deterministic acceptance tests require neither Pydantic AI nor Ollama and do not contact a provider.

The portable manifest now enumerates the new adapter in the AWF runtime closure, but its AWF aggregate digest intentionally remains the pre-candidate value until the canonical Windows checkout measures the new 10-file closure. Therefore the candidate is **not accepted yet**.

## Known next integration boundary

The historical framework CLI still contains a Codex-specific production runtime path. It must not be allowed to silently satisfy `coding-worker:v1`. After the bounded adapter is accepted, the next integration task is to bind one exact Host Provider Qualification record into the workspace-write dispatch path and make the framework fail closed rather than falling back to Codex.

That integration must preserve this order:

`portable identity -> protected runtime requirement -> exact host provider qualification -> task authorization -> dispatch -> independent verification`

Provider qualification is evidence, never authorization.

## Current stop condition

Execution remains disabled. Do not authorize or dispatch the historical September 1 Phase 4 invocation. Do not install Codex merely to satisfy the legacy `acl-installation-manifest:v2`. Do not run Pydantic AI, Ollama chat/completions, or a local coding model as part of the current adapter acceptance gate.

The historical September 1 state remains byte-preserved at `docs/legacy/CURRENT_STATE_2026-09-01.md`.

## Immediate next gate

Validate the bounded Pydantic/Ollama adapter candidate using deterministic injected runners only, then measure the exact 10-file AWF portable closure and refresh its manifest digest.

After that, implement the qualification-to-dispatch binding and explicit no-Codex-fallback rule. The first actual model execution remains reserved for the separately authorized supervised vertical-slice proof.
