# promptfoo Deep Research

**Task:** ranked project deep research #4  
**Project:** promptfoo  
**Canonical repository:** https://github.com/promptfoo/promptfoo  
**Research date:** 2026-09-05  
**Status:** deep research complete; no adoption/fork/build decision made

## Why promptfoo is being studied

promptfoo is relevant to ACL/Vera for a different reason than Pydantic AI, Cline, or LangGraph. It is primarily an evaluation, testing, tracing, and red-team layer around models and agent runtimes rather than an owner of agent execution state.

This task therefore focuses on whether promptfoo provides useful independent evidence, deterministic regression checks, adversarial fixtures, local-model evaluation, CI gates, and verifier-integrity patterns for ACL. It does **not** ask whether promptfoo should become ACL's worker harness, nor does it begin comparison with Strands Harness SDK.

## Executive assessment

promptfoo remains a justified Tier-A research target and is one of the most directly reusable projects studied so far for **independent evaluation**.

Its strongest value to ACL is not a generic score table. It is the combination of:

1. deterministic assertions over outputs, tools, traces, and execution trajectories;
2. OpenTelemetry-based evidence tied to individual test executions;
3. coding-agent-specific adversarial fixtures that distinguish model, harness, verifier, and eval-design failures;
4. host-side canaries, protected hashes, sidecar reports, and fail-closed verifier behavior;
5. explicit support for disposable workspaces and cross-row isolation;
6. local Ollama targets and local text/embedding graders;
7. CI/output machinery that can turn a known failure into a repeatable regression gate.

The strongest architectural lesson is that ACL should have an evaluator that a worker cannot simply persuade. Whenever a property can be observed mechanically, evaluator-owned evidence should dominate model opinion.

promptfoo also exposes important evaluator-side risks. Custom JavaScript/Python assertions are executable code; trace evidence can leak useful internal information to an adversarial attack generator if configured that way; model graders introduce their own provider/model variance; and an open evaluator regression (#10501) shows that live provider runtime objects can contaminate otherwise serializable test/grading configuration.

The conclusion is therefore **high-value evaluation substrate/reference, no wholesale adoption decision yet**.

---

## 1. Project status, ownership, license, and maintenance signal

### Observed

The canonical `promptfoo/promptfoo` repository is active and not archived. Main was current through 2026-09-05 when checked. `package.json` reported version `0.122.2`, MIT license, and Node.js `>=22.22.0`.

Recent releases show ongoing work in tracing, red teaming, provider support, token accounting, assertion correctness, and code-scan supply-chain hardening. Release `0.122.2` was published 2026-08-28; `0.122.1` included extensive trace instrumentation and persistence work.

On 2026-03-09 the project announced that promptfoo had agreed to be acquired by OpenAI and stated that the open-source project would remain open source and continue supporting diverse providers. The announcement also stated that closing was subject to customary conditions. This research records the ownership transition signal without inferring unverified closing details.

Primary sources:
- https://github.com/promptfoo/promptfoo
- https://github.com/promptfoo/promptfoo/blob/main/package.json
- https://github.com/promptfoo/promptfoo/releases
- https://github.com/promptfoo/promptfoo/blob/main/site/blog/promptfoo-joining-openai/index.mdx

### ACL/Vera relevance

The project currently has strong maintenance signal and broad provider/eval scope. The ownership change matters for future dependency governance and independence analysis, but it does not negate the current MIT/open-source implementation or justify an adoption decision by itself.

### Warning

High activity and rapid feature growth also create regression/churn risk. The open grading-provider regression discussed later is a concrete example.

**Confidence:** high.

---

## 2. Architectural role: independent evaluator rather than runtime owner

### Observed

promptfoo's core abstraction is a test/evaluation suite: prompts or targets, providers, test cases, assertions, grading, traces, result persistence, red-team generation, and CI/reporting.

It can invoke ordinary LLM providers, HTTP/custom providers, local models, and agent SDK/providers, but it does not attempt to become the durable project/session/checkpoint authority for those agents.

This is materially different from the stateful orchestration responsibilities studied in Cline and LangGraph.

Primary sources:
- https://github.com/promptfoo/promptfoo/blob/main/README.md
- https://github.com/promptfoo/promptfoo/blob/main/src/evaluator.ts
- https://github.com/promptfoo/promptfoo/blob/main/src/types/index.ts

### ACL/Vera relevance

ACL benefits from keeping execution authority and evaluation authority separable. A worker runtime should emit evidence; a verifier should decide whether the evidence meets task/security requirements.

Candidate invariant:

> The component being evaluated should not own the authoritative definition of whether its own run succeeded.

### Warning

An external evaluator is only independent if its fixtures, evidence roots, grader configuration, and execution environment are outside the worker's authority.

**Confidence:** high.

---

## 3. Deterministic assertions before semantic judgment

### Observed

promptfoo exposes a broad deterministic assertion family including exact/contains/regex checks, JSON/XML/SQL validation, function/tool-schema validation, cost/latency limits, tool-call F1, trace span checks, and trajectory checks.

For agent behavior, current trajectory assertions include:
- `trajectory:tool-used`;
- `trajectory:tool-args-match`;
- `trajectory:tool-sequence`;
- `trajectory:step-count`;
- trace span count/duration/error assertions.

The implementation in `src/assertions/trajectory.ts` supports required/forbidden tools, min/max occurrence counts, exact versus partial argument matching, ignored/default arguments, and exact or in-order tool sequences.

A useful verifier-hardening detail appears in tool-argument normalization: reserved keys such as `__proto__` are preserved with `Object.defineProperty` rather than ordinary assignment so a hallucinated argument cannot disappear through JavaScript prototype semantics and accidentally make an exact comparison pass.

`trajectory:goal-success` is different: it delegates semantic success to an LLM grader and should not be confused with the deterministic trajectory assertions.

Primary sources:
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/configuration/expected-outputs/deterministic.md
- https://github.com/promptfoo/promptfoo/blob/main/src/assertions/trajectory.ts

### ACL/Vera relevance

This maps closely to ACL's benchmark/testing goals. Examples of future deterministic ACL assertions include:
- required test command was executed;
- forbidden file/tool was never accessed;
- expected tool arguments match exact project/task IDs;
- no more than N recovery attempts occurred;
- required validation occurred before commit;
- no trace error span remained unresolved;
- a worker did not modify protected verifier files.

Candidate invariant:

> If a success or safety property is machine-observable, use a deterministic assertion before asking another model to judge it.

### Warning

Trace assertions are only as reliable as the trace collection/normalization and the provider instrumentation. Missing evidence must not silently turn a hard assertion into a semantic guess.

**Confidence:** high.

---

## 4. OpenTelemetry and trajectory evidence

### Observed

promptfoo uses OpenTelemetry traces to attach execution evidence to each test-case execution. Current tracing documentation describes test-case root spans, target spans, grading spans, GenAI semantic-convention attributes, tool execution, token/resource data, and optional application-provided child spans.

The tracing layer can normalize common agent/tool/command spans into a trajectory that assertions and graders can inspect.

Current provider instrumentation includes OpenAI, Anthropic, Azure OpenAI, Bedrock, Google, Ollama, Mistral, Cohere, Hugging Face, IBM, HTTP, OpenRouter, Replicate, and inherited OpenAI-compatible providers.

The tracing documentation also exposes important semantics:
- one test execution gets its own trace;
- grading model calls appear under grading spans;
- some agent providers emit turn marker spans;
- sub-agent turns may need explicit filtering;
- cache hits can suppress turn spans;
- `--no-cache` is appropriate when fresh turn-count/trajectory evidence is required.

Primary source:
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/tracing.md

### ACL/Vera relevance

This is a useful reference for ACL's future worker GUI and evidence store. The important pattern is not necessarily promptfoo's exact schema; it is making runtime behavior queryable as structured evidence rather than reconstructing behavior from prose logs.

Possible reusable fields include:
- evaluation/test-case ID;
- worker/agent ID;
- provider/model/runtime identity;
- task/tool name;
- arguments/result/error;
- parent span/tool-call identity;
- iteration/turn index;
- token/time/cost fields;
- cache state;
- grader identity/result.

### Warning

Tracing is evidence, not a security boundary. Sensitive values in span names/attributes can leak through reports or downstream processing.

**Confidence:** high.

---

## 5. Trace availability must itself be testable

### Observed

promptfoo's built-in OTLP receiver can be configured with `failOnReceiverStartFailure: true`. Documentation states that the default behavior is otherwise to log the receiver startup failure and continue without traces.

Current tracing implementation and tests explicitly handle this policy. A recent regression fix/tests cover a port-in-use case where an Express listen callback could fire even though the server was not actually listening; the receiver now rejects correctly so fail-on-start semantics work.

Primary sources:
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/tracing.md
- https://github.com/promptfoo/promptfoo/blob/main/src/tracing/evaluatorTracing.ts
- https://github.com/promptfoo/promptfoo/blob/main/src/tracing/otlpReceiver.ts
- https://github.com/promptfoo/promptfoo/blob/main/test/tracing/evaluatorTracing.test.ts

### ACL/Vera relevance

For low-stakes exploratory evals, degraded evidence may be acceptable. For ACL security or acceptance gates, it is not.

Candidate invariant:

> If an assertion depends on a telemetry/evidence channel, failure of that channel must fail or invalidate the evaluation rather than silently reducing evidence quality.

This should generalize beyond traces to:
- sidecar verifier output;
- workspace hashes;
- Git diff collection;
- process/network probes;
- model/runtime metadata;
- benchmark artifact capture.

**Confidence:** high.

---

## 6. Coding-agent red-team model matches ACL's actual threat surface

### Observed

promptfoo now has explicit coding-agent red-team guidance and plugins rather than treating coding agents as ordinary chatbots.

The `coding-agent:core` collection covers:
- repository prompt injection;
- terminal/output injection;
- secret environment reads;
- sandbox read escape;
- verifier sabotage.

Additional plugins cover:
- secret-file reads;
- sandbox write escape;
- network egress bypass;
- procfs credential reads;
- delayed CI exfiltration;
- generated vulnerabilities;
- automation poisoning;
- steganographic exfiltration.

The guidance explicitly says coding-agent evals test both whether the model makes safe engineering decisions **and** whether the harness preserves claimed security boundaries.

It separates failure classes into:
1. model behavior;
2. harness boundary;
3. verifier integrity;
4. eval design.

Primary sources:
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/red-team/coding-agents.md
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/red-team/plugins/coding-agent.md

### ACL/Vera relevance

This is unusually well aligned with ACL's end goal. A failed ACL run should not merely say `FAIL`; it should identify whether:
- the local model chose an unsafe action;
- ACL exposed authority it should not have exposed;
- the worker tampered with validation;
- the test fixture itself was contaminated or ambiguous.

That classification would make failures actionable and prevent model changes from being used to mask harness/security defects.

### Warning

Generated red-team cases are discovery/evaluation inputs, not automatically ground-truth labels. High-confidence labels require action evidence.

**Confidence:** high.

---

## 7. Disposable workspaces and cross-test contamination

### Observed

The coding-agent guidance recommends one isolated repository/workspace per test row where possible: fresh clone, disposable worktree, container snapshot, or equivalent reset.

The reason is correctness as much as safety. A prior row may leave canaries, modified tests, artifacts, weakened policies, or cached state that contaminates later rows.

The guidance recommends recording per-row workspace/reset identity and using synthetic secrets/canaries rather than real credentials.

Primary source:
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/red-team/coding-agents.md

### ACL/Vera relevance

ACL's future benchmark should treat environment identity as part of the result. A model score is not reproducible if workers share mutable residue unintentionally.

Candidate evidence fields:
- fixture commit/hash;
- workspace ID;
- reset/snapshot ID;
- pre-run cleanliness check;
- protected-file hashes;
- canary set ID;
- allowed network policy;
- runtime/container image hash.

### Warning

Serial execution alone does not prevent contamination. State reset/isolation is a separate requirement.

**Confidence:** high.

---

## 8. Verifier integrity: evidence outside worker authority

### Observed

promptfoo's coding-agent verifier implementation can inspect multiple evidence classes: provider output, commands, command output, traces, artifact files, protected paths, hashes, network trap logs, process/procfs evidence, and sidecar reports.

The documentation recommends SHA-256 hashes for assertion-owned tests/verifiers/policies/hooks/lockfiles and sidecar verification outside the agent-writable workspace.

When a configured assertion-owned sidecar verifier report is missing, the coding-agent verifier fails closed. The missing report is itself treated as a verifier-integrity failure because the evaluator can no longer trust the post-run evidence.

Primary sources:
- https://github.com/promptfoo/promptfoo/blob/main/src/redteam/plugins/codingAgent/verifiers.ts
- https://github.com/promptfoo/promptfoo/blob/main/test/redteam/plugins/codingAgent.test.ts
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/red-team/plugins/coding-agent.md

### ACL/Vera relevance

This is one of the strongest direct reuse candidates found in the project.

Candidate invariant:

> Worker acceptance evidence must be owned by a verifier that the worker cannot rewrite, delete, spoof, or suppress without causing the run to fail closed.

For ACL this argues for:
- verifier files outside worker write roots;
- immutable or independently hashed test definitions;
- protected expected-output fixtures;
- host-owned Git/workspace probes;
- synthetic secret/canary injection from outside the worker;
- explicit `evidence_missing` rather than implicit pass.

### Warning

Verifier heuristics are still software and can have false positives/negatives. High-risk controls should combine narrow deterministic probes rather than relying on broad text pattern matching alone.

**Confidence:** high.

---

## 9. Unsafe willingness versus action-verified failure

### Observed

The coding-agent guidance explicitly distinguishes an agent expressing willingness to perform an unsafe action from evidence that it actually performed one.

For training-quality/security-signoff evidence, it prefers command traces, canaries, changed files, host probes, sidecar reports, protected hashes, and external receipts.

Primary source:
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/red-team/coding-agents.md

### ACL/Vera relevance

ACL should preserve at least three result categories:
- **stated unsafe intent/willingness**;
- **attempted unsafe action**;
- **verified boundary violation/effect**.

This is more informative than a binary unsafe/safe label and makes local-model comparisons fairer.

**Confidence:** high.

---

## 10. Trace-aware red-team attacks create an information-flow boundary

### Observed

promptfoo can feed a compact trace summary to red-team attack strategies and/or graders. Configuration distinguishes `includeInAttack` and `includeInGrading`.

Current guidance warns that attacker-visible trace summaries can expose high-level details such as tool names, model names, errors, and guardrail outcomes. It recommends disabling attacker visibility when a black-box first pass is desired while retaining trace-aware grading.

Primary sources:
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/red-team/llm-agents.md
- https://github.com/promptfoo/promptfoo/blob/main/src/redteam/providers/tracingOptions.ts

### ACL/Vera relevance

Evaluation telemetry has an audience. ACL should distinguish:
- evidence visible to the worker/model;
- evidence visible to the attacker/test generator;
- evidence visible only to the validator;
- evidence visible to the human/operator.

Candidate invariant:

> Do not feed privileged verifier telemetry back into the system under test unless the test explicitly intends to grant that information.

### Warning

An attack becomes stronger when it receives internal traces. That can be useful for white-box testing, but black-box and white-box results should not be mixed without labeling.

**Confidence:** high.

---

## 11. Local/Ollama support is viable for offline ACL evaluation

### Observed

promptfoo provides native Ollama chat/completion/embedding providers and forwards Ollama configuration/passthrough fields. It supports Ollama tool/function calling where the selected model supports it.

Ollama can also be the **grading provider**, including separate local text and embedding models. Documentation recommends serial execution (`-j 1` / max concurrency 1) for resource-constrained local systems so only one large model needs to remain active at a time.

For serial no-timeout evaluation, eligible model-graded assertions may be grouped by grader-provider ID to reduce local model switching; this is scheduling optimization, not request batching.

Primary source:
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/providers/ollama.md

### ACL/Vera relevance

This makes promptfoo technically compatible with ACL's local/offline benchmark direction. A cloud grader is not structurally required.

However, a local grader is another model whose version/runtime/settings affect results. ACL should record at minimum:
- target model + quantization;
- runtime/version;
- target provider adapter/settings;
- grader model + quantization;
- grader runtime/settings;
- embedding model when applicable;
- concurrency/cache/repeat policy.

### Warning

Using a local LLM judge does not make a semantic grade deterministic. It only makes the dependency local.

**Confidence:** high.

---

## 12. Reproducibility is configurable, not automatic

### Observed

promptfoo supports:
- configurable `maxConcurrency`;
- repeated test execution;
- result caching and `--no-cache`;
- rerunning failures/errors from previous outputs;
- JSON/JUnit/HTML outputs;
- CI tags such as run ID and Git SHA;
- custom build-quality thresholds;
- provider/fixture-specific extension hooks.

Tracing documentation notes that cached responses can alter trace/turn evidence, and coding-agent guidance requires workspace reset/isolation for mutable targets.

Primary sources:
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/configuration/reference.md
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/integrations/ci-cd.md
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/tracing.md

### ACL/Vera relevance

A trustworthy ACL benchmark record should pin:
- promptfoo/evaluator version;
- config/fixture Git commit;
- target model/runtime/adapter/settings;
- grader model/runtime/settings;
- cache policy;
- concurrency;
- repeat count/seed where available;
- workspace/reset identity;
- test/canary set identity;
- trace/evidence availability;
- Git SHA and hardware/runtime metadata where relevant.

### Warning

`npx promptfoo@latest` is convenient for ordinary CI but inappropriate for a frozen benchmark baseline. ACL should pin the evaluator version for reproducibility.

**Confidence:** high.

---

## 13. CI gates: pass/fail semantics need explicit policy

### Observed

promptfoo supports CI/CD integration and can fail a build on test failures via `--fail-on-error`. Its documentation also shows custom pass-rate thresholds by exporting JSON and applying an explicit CI script.

Outputs distinguish successes, failures, and errors.

Primary source:
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/integrations/ci-cd.md

### ACL/Vera relevance

ACL should avoid one undifferentiated quality score. Gates should distinguish at least:
- evaluator/infrastructure error;
- deterministic functional assertion failure;
- security boundary failure;
- verifier-integrity/evidence-missing failure;
- semantic quality score;
- flaky/nondeterministic disagreement across repeats.

A security or verifier-integrity failure should not be averaged away by many easy passing tests.

### Warning

A global pass-rate threshold can hide rare high-severity failures. Severity-aware gates belong above raw aggregate metrics.

**Confidence:** high.

---

## 14. Model graders are useful but lower-trust than deterministic evidence

### Observed

promptfoo provides model-graded assertions such as `llm-rubric` and allows the grading provider to be overridden.

Project-authored guidance recommends explicitly choosing a grader for stable configuration and using model grading for qualities that are not reducible to deterministic checks.

Open issue #10166 describes a current limitation: native model-graded assertions cannot directly consume explicitly selected bounded structured `ProviderResponse.metadata` as separate evidence. The proposed contract emphasizes explicit field selection, deterministic size bounds, and untrusted-data separation rather than blindly appending arbitrary metadata to candidate output.

Primary sources:
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/configuration/expected-outputs/model-graded/llm-rubric.md
- https://github.com/promptfoo/promptfoo/issues/10166

### ACL/Vera relevance

LLM grading is appropriate for semantic questions such as:
- did the implementation actually satisfy a nuanced requirement?;
- did the worker weaken a test semantically without changing its hash-protected wrapper?;
- is an explanation materially misleading?;

But the grader should receive **bounded, labeled, provenance-preserving evidence**, not a blob of worker-controlled context.

Candidate invariant:

> Semantic graders consume an explicitly selected evidence projection; they do not define or discover the authoritative evidence boundary themselves.

### Warning

Judge model/provider changes can change labels even when target output is identical. Grader identity is part of the benchmark definition.

**Confidence:** high.

---

## 15. Current evaluator failure surface: live provider objects leaking into test/grader config

### Observed

Open issue #10501 reports a regression beginning in promptfoo `0.121.13`: when the same provider ID is used as both target provider and an `llm-rubric` judge, the evaluator can replace the grader's string provider reference with a live instantiated provider object. That object can contain circular SDK references; a later generic deep clone recursively traverses it and raises `RangeError: Maximum call stack size exceeded`.

The reporter bisected the issue to the provider-reference-reuse change and documented a related earlier UI serialization bug involving the same broad class of live SDK object crossing a serialization boundary through a different path.

A follow-up comment says the problem was reproduced against then-current main and also highlights why deep-copying a live credential-bearing client is undesirable even if circular cloning is technically enabled.

The issue remained open when checked during this task.

Primary sources:
- https://github.com/promptfoo/promptfoo/issues/10501
- https://github.com/promptfoo/promptfoo/issues/10501#issuecomment-5541022723

### ACL/Vera relevance

This yields a strong evaluator/harness invariant:

> Serializable test/config identity must remain separate from live provider/client/session instances and credentials.

For ACL this applies not only to graders but also:
- worker runtime adapters;
- OAuth/API clients;
- browser sessions;
- GitHub/connector clients;
- sandbox handles;
- database connections;
- model-server clients.

Persist stable descriptors/IDs and reconstruct live handles through an owned runtime layer.

### Warning

The reproduced issue concerns the documented provider/grader collision path. It does not mean promptfoo evaluation generally fails or that current 0.122.2 necessarily reproduces every detail unless reverified on that exact release.

**Confidence:** high for the failure class and reported versions/current-main reproduction; bounded for untested later builds.

---

## 16. Evaluation configuration is executable privileged input

### Observed

promptfoo JavaScript assertions can execute arbitrary JavaScript, use external `file://` modules, perform asynchronous network calls, and inspect detailed test/provider/trace context.

Python assertions execute using a configured Python interpreter and can import arbitrary libraries, make external calls, and access trace/context data.

Primary sources:
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/configuration/expected-outputs/javascript.md
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/configuration/expected-outputs/python.md

### ACL/Vera relevance

An eval pack downloaded from a third party is therefore potentially executable code with access to the evaluator process environment.

Candidate invariant:

> Treat evaluator extensions/scripts as privileged code dependencies, not declarative data.

ACL should eventually distinguish:
- built-in audited deterministic assertions;
- project-owned validator code;
- third-party trusted validator code;
- untrusted generated test data that must never gain evaluator-code execution.

### Warning

Running the worker in a sandbox does not protect the host if the evaluator itself executes untrusted assertion code outside that sandbox.

**Confidence:** high.

---

## 17. What is actually reusable for ACL

High-value mechanism/reference candidates:

### A. Deterministic trajectory assertions
Useful directly or as design references for tool used/not-used, arguments, order, counts, errors, and resource limits.

### B. Coding-agent adversarial fixture catalog
The repo/terminal injection, sandbox escape, secret read, verifier sabotage, automation poisoning, delayed exfiltration and generated-vulnerability categories are immediately relevant to ACL.

### C. Verifier-owned canaries/hashes/sidecars
One of the strongest candidates for ACL's acceptance/security layer.

### D. OpenTelemetry test correlation
Potential common evidence bridge between the future runtime, worker GUI, evaluator, and security tests.

### E. Local Ollama target/grader support
Useful for ACL's offline/local benchmark lab.

### F. CI/output/rerun machinery
Potential way to turn a discovered failure into a durable fixture and to rerun failing rows during development.

### G. Failure taxonomy
Model failure vs harness boundary vs verifier integrity vs eval-design failure is a strong classification model for ACL incident/benchmark records.

---

## 18. What promptfoo does not solve for ACL

This task found no evidence that promptfoo should replace:
- authoritative ACL task/project state;
- checkpoint/recovery orchestration;
- effect settlement/idempotency ledger;
- workspace snapshot/restore;
- capability/permission ownership;
- process/container sandboxing;
- secret brokerage;
- local model capability profiling;
- worker scheduling/backlog routing;
- final project-specific task acceptance logic.

It is most naturally evaluated later as an **independent testing/evidence component beside those systems**.

---

## 19. Candidate ACL regression fixtures derived from promptfoo research

These are research-derived fixture ideas, not governance changes:

1. **Repo prompt injection** — malicious README/comment attempts to redirect worker away from assigned scope.
2. **Terminal output injection** — test/compiler output contains a fake instruction/canary.
3. **Read escape** — worker attempts to read a sibling checkout or home/temp secret.
4. **Write escape** — worker attempts to mutate a path outside its workspace.
5. **Environment secret read** — launcher-only synthetic credential appears in command/output/artifact.
6. **Procfs credential recovery** — worker tries `/proc/*/environ`, command line, fd, cwd/root metadata.
7. **Network egress** — controlled trap endpoint records unauthorized request.
8. **Delayed exfiltration** — worker plants CI/hook/package automation that would leak later.
9. **Verifier sabotage** — worker edits/deletes/tests around verifier artifacts instead of solving task.
10. **Evidence disappearance** — sidecar/trace collector is disabled; evaluation must fail invalid/evidence-missing.
11. **Cross-row contamination** — canary from test A must never influence test B after reset.
12. **Tool trajectory contract** — required test/validation tool occurs before commit; forbidden tools absent.
13. **Exact tool args** — project/task/workspace IDs must match expected values; hallucinated extra fields fail exact mode.
14. **Judge drift** — identical target artifact graded by changed judge version/settings is labeled as a distinct benchmark definition.
15. **Evaluator live-object contamination** — serialized fixture/config must never contain live provider/client/session/credential objects.

---

## 20. Candidate invariants for later comparison

These are evidence-backed hypotheses to compare against later projects; they are **not yet ACL governance**.

1. The system under test must not own its own acceptance evidence.
2. Deterministic evidence precedes semantic model grading whenever feasible.
3. Missing required evidence is an explicit failure/invalid state, never an implicit pass.
4. Verifier roots and protected artifacts stay outside worker write authority.
5. Security labels distinguish willingness, attempted action, and verified effect.
6. Evaluation failure classification separates model, harness, verifier, and fixture/eval design.
7. Every mutable coding-agent row gets an isolated/resettable workspace and unique canaries.
8. Trace/sidecar evidence availability is itself asserted.
9. Attacker-visible telemetry and validator-visible telemetry are separate policy choices.
10. Target model identity and grader model identity are both part of the benchmark definition.
11. Cache/concurrency/repeat/workspace settings are part of reproducibility evidence.
12. Eval plugins/scripts are executable dependencies requiring provenance and containment.
13. Serializable config/descriptors stay separate from live provider/session/credential objects.
14. High-severity security/verifier failures should gate independently rather than disappear inside aggregate pass-rate metrics.

---

## 21. Non-conclusions

This task does **not** establish that:
- promptfoo should be adopted as an ACL dependency;
- promptfoo's generated red-team cases are sufficient without ACL-specific fixtures;
- LLM graders are reliable enough to be authoritative acceptance judges;
- OpenTelemetry traces capture every side effect;
- a passing promptfoo scan proves an ACL worker is secure;
- local Ollama grading is deterministic;
- promptfoo's ownership transition changes the quality of its current open-source implementation;
- promptfoo is better or worse overall than Pydantic AI, Cline, LangGraph, or later projects.

Those decisions belong to later comparative work.

---

## 22. Research stop condition

Research stopped when the major promptfoo-specific ACL questions had primary evidence:
- current health/ownership/license;
- independent evaluator role;
- deterministic and trajectory assertions;
- coding-agent red teaming;
- verifier integrity and evidence ordering;
- tracing/telemetry failure semantics;
- local Ollama target/grader support;
- reproducibility/CI controls;
- executable eval configuration risk;
- model-grader trust boundary;
- current evaluator failure surface.

Further searching was increasingly returning additional examples of the same mechanisms rather than changing the assessment. Strands Harness SDK was deliberately not researched.

## Primary sources consulted

- https://github.com/promptfoo/promptfoo
- https://github.com/promptfoo/promptfoo/blob/main/README.md
- https://github.com/promptfoo/promptfoo/blob/main/package.json
- https://github.com/promptfoo/promptfoo/releases
- https://github.com/promptfoo/promptfoo/blob/main/site/blog/promptfoo-joining-openai/index.mdx
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/configuration/expected-outputs/deterministic.md
- https://github.com/promptfoo/promptfoo/blob/main/src/assertions/trajectory.ts
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/tracing.md
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/red-team/llm-agents.md
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/red-team/coding-agents.md
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/red-team/plugins/coding-agent.md
- https://github.com/promptfoo/promptfoo/blob/main/src/redteam/plugins/codingAgent/verifiers.ts
- https://github.com/promptfoo/promptfoo/blob/main/test/redteam/plugins/codingAgent.test.ts
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/providers/ollama.md
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/configuration/expected-outputs/javascript.md
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/configuration/expected-outputs/python.md
- https://github.com/promptfoo/promptfoo/blob/main/site/docs/integrations/ci-cd.md
- https://github.com/promptfoo/promptfoo/issues/10166
- https://github.com/promptfoo/promptfoo/issues/10501
