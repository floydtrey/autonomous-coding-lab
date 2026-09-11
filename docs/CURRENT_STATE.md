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

The accepted focused gate passed **31 tests**. The measured Worker Lab production tree is `sha256:52086119d189f41aa6ab708f7e03ce57a1cc70c3b4eaaeffd661556917115b67` across 28 files. Portable verification reported all three components `MATCH`, `provider_runtime_qualified=false`, `execution_authority=DISABLED`, and `execution_ready=false`, with a clean working tree.

Commit `81882c94798de80af4d54f04f52e545e4ab3c8cb` records the accepted Worker Lab portable identity for this contract.

`provider_runtime_qualified=false` remains correct: the qualification mechanism and protected candidate are accepted, but no concrete Pydantic/Ollama/model installation has yet been qualified on the intended worker host.

## Bounded Pydantic Ollama worker adapter — accepted

The bounded adapter was introduced at `0313e42c9f1d1f869e4298ac7eaee977985997d3`, followed by the Windows exact-byte regression correction and portable-closure consistency guard.

Accepted behavior:

- exact readable and writable file paths are explicit in `WorkerRequest` rather than inferred from prompt text;
- generic `code_task` has no implicit Codex executor fallback;
- `tools/pydantic_ollama_worker.py` exposes only ACL-owned `read_file` and `write_file` tools;
- writes require the SHA-256 returned by a prior read, preventing silent stale writes;
- reads preserve exact file bytes after UTF-8 decoding rather than normalizing Windows CRLF to LF;
- files are limited to exact authorized relative paths, UTF-8 text, bounded size, and non-substituted paths;
- `.git` paths, traversal, symlink/reparse substitution, and multi-hard-link writes are rejected;
- the provider endpoint must be loopback-only and the protected provider/tool-surface identity must match;
- Pydantic AI requests, tool calls, tool execution timeout, concurrency and final output are bounded;
- shell, Git, arbitrary process, network, publication, approval, and directory-enumeration tools are not exposed.

The deterministic focused adapter gate passed **14 tests** after correcting the cross-platform newline fixture. The portable-verifier contract regression passed **4 tests**. The accepted Windows portable verification then reported:

- Autonomous Worker Framework: `sha256:cb76f6ed59a5fb57b5b22faa31103fd285302b042b2bb3af7722b41e580d1414` across 10 files — `MATCH`;
- Local Model Bench: `sha256:139331ea42c914575d1119125a702ac5de2129b9bedc235bfc189700e8265afc` across 10 files — `MATCH`;
- Worker Lab: `sha256:52086119d189f41aa6ab708f7e03ce57a1cc70c3b4eaaeffd661556917115b67` across 28 files — `MATCH`;
- `provider_runtime_qualified=false`;
- `execution_authority=DISABLED`;
- `execution_ready=false`;
- working tree clean.

Commit `99a581f7ddf75041a8f3584966ce8652bf6afc13` is the accepted portable-verifier consistency checkpoint for this state.

## Remaining dispatch integration boundary

The historical framework CLI still contains a Codex-specific production runtime path. It must not silently satisfy `coding-worker:v1`.

The next integration task is to bind **one exact Host Provider Qualification identity** into workspace-write authorization before dispatch, then route that exact binding to the Pydantic/Ollama worker adapter. The read-only historical Codex path may remain unchanged for evidence compatibility.

A key architectural requirement is now explicit: provider selection cannot happen after authorization without being covered by an immutable authorization identity. The project must not reuse a generic `provider-qualified` placeholder as permission to select "whatever provider is currently installed" at dispatch time.

The required order remains:

`portable identity -> protected runtime requirement -> exact host provider qualification -> task authorization -> dispatch -> independent verification`

Provider qualification is evidence, never authorization.

## Current stop condition

Execution remains disabled. Do not authorize or dispatch the historical September 1 Phase 4 invocation. Do not install Codex merely to satisfy the legacy `acl-installation-manifest:v2`. Do not run Pydantic AI, Ollama chat/completions, or a local coding model as part of dispatch-integration development.

The historical September 1 state remains byte-preserved at `docs/legacy/CURRENT_STATE_2026-09-01.md`.

## Immediate next gate

Design and implement **Provider Binding / Dispatch V1** with deterministic injected executors only.

The preferred architecture is to make the exact provider-qualification identity part of a new immutable authorization binding rather than overloading the existing `model` field or allowing runtime-time provider selection. Preserve historical invocation evidence compatibility, make workspace-write fail closed when no exact provider binding exists, and add an explicit no-Codex-fallback invariant.

Stop before any actual model execution. The first real provider/model run remains reserved for the separately authorized supervised vertical-slice proof.
