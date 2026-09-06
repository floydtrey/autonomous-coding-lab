# SWE-agent / mini-swe-agent — transition-aware deep research

**Task:** 12 — ranked project #8  
**Projects:** SWE-agent, mini-swe-agent, SWE-ReX  
**Historical/main scaffold:** `SWE-agent/SWE-agent`  
**Declared successor:** `SWE-agent/mini-swe-agent`  
**Execution runtime extracted during redesign:** `SWE-agent/SWE-ReX`  
**Research date:** 2026-09-06  
**SWE-agent main examined:** `3ea751c087f32b16e039a2233dd6eefecef325d5`  
**mini-swe-agent main examined:** `04d809ceab9df28f9adaed044884180159172930`  
**SWE-ReX main examined:** `5c995c365dfb1fd5bc56fda688be5d8538f9931f`  
**License:** MIT for SWE-agent and mini-swe-agent; SWE-ReX is researched as the canonical execution-runtime companion  
**Status:** transition-aware research complete; no dependency/adoption/fork decision made

## Why this transition is unusually valuable to ACL/Vera

This ranked slot is not a normal one-repository project review. It captures two successive simplification moves made by the same project family:

1. SWE-agent 1.0 nearly rewrote the original scaffold and moved execution/infrastructure responsibilities into **SWE-ReX**.
2. The project later declared **mini-swe-agent** the successor and put SWE-agent in maintenance-only mode, intentionally shrinking the agent-facing loop and configuration surface further.

That makes this family unusually useful for ACL because the user has already encountered the same class of problem experimentally: too many harness instructions and checkpoint rules can turn a model into a rigid script, suppress useful model-native reasoning, and induce guessing rather than reliable tool use.

The research question is therefore not "is smaller always better?" It is:

> **Which complexity was safely removed from the model-facing agent loop, which complexity merely moved into a dedicated runtime, and which reliability/security responsibilities still must exist outside the prompt?**

The answer from current primary evidence is quite consistent: the reasoning loop can be extremely small, but process custody, sandboxing, credentials, authorization, effect identity, local-runtime capability, persistence and independent evaluation do not disappear.

---

# 1. Project status and transition boundary

## Observed

The upstream SWE-agent project now says it has been superseded by mini-swe-agent and is in maintenance-only mode. Current SWE-agent main still receives maintenance/regression fixes, but upstream recommends mini-swe-agent for new use.

mini-swe-agent is active. Its main branch examined for this task was `04d809ceab9df28f9adaed044884180159172930`, dated 2026-09-03.

SWE-agent main examined was `3ea751c087f32b16e039a2233dd6eefecef325d5`, dated 2026-07-16. That commit itself is a useful maintenance example: it fixes a benchmark adapter/subset mapping that caused multimodal evaluation to call an invalid downstream `sb-cli` subset name and adds explicit regression coverage.

SWE-ReX remains the execution framework created from SWE-agent experience. Its README states the design goal directly: disentangle agent logic from infrastructure concerns while supporting local and remote execution plus high-parallelism evaluation.

## Maintainer-stated transition

SWE-agent's current documentation states that:

- mini-swe-agent has superseded SWE-agent;
- mini is simpler and more flexible while remaining comparably performant for the intended benchmark use;
- SWE-agent is maintenance-only.

This is authoritative project-status evidence. It is not an inference from commit frequency.

## ACL/Vera relevance

The ranked slot should therefore be treated as one architecture lineage rather than three competing independent products:

- older rich scaffold;
- extracted execution runtime;
- simpler successor agent loop.

A future ACL component comparison should compare **mechanisms across this lineage**, not score old SWE-agent and mini as unrelated alternatives.

## Sources

- https://github.com/SWE-agent/SWE-agent
- https://github.com/SWE-agent/SWE-agent/blob/main/docs/overrides/main.html
- https://github.com/SWE-agent/mini-swe-agent
- https://github.com/SWE-agent/SWE-ReX

---

# 2. SWE-agent 1.0 already performed a major simplification by moving execution out

## Observed rewrite

The SWE-agent 1.0 migration guide says the codebase was nearly rewritten from scratch.

The largest structural change was SWE-ReX:

- SWE-ReX became the backend responsible for code execution;
- the former `SWEEnv` largely disappeared into a small wrapper around a SWE-ReX runtime;
- the `Agent` class became simpler;
- tool/execution logic moved into a separate `Tools` class;
- complicated environment-setup permutations were removed in favor of starting from an execution image plus explicit setup commands/tool bundles;
- execution could occur locally or remotely without rewriting the agent logic;
- the same runtime boundary enabled massively parallel benchmark execution.

## What this means

The project did **not** eliminate infrastructure complexity. It moved it to a component whose job was infrastructure.

That distinction matters greatly for ACL:

> **Simplify the reasoning loop by relocating deterministic infrastructure responsibilities to explicit owners, not by deleting the responsibilities.**

This is materially different from trying to solve process cleanup, sandbox selection, remote execution, credentials or persistence through more prompt text.

## Candidate ACL invariant

The worker-facing agent contract should be small enough that the model can reason naturally. Execution transport should be replaceable underneath it.

A worker should not need to know whether its action ultimately runs through:

- a local subprocess;
- Docker;
- a remote machine;
- a cloud sandbox;
- another isolated execution backend.

The harness must know and record that difference because authority and recovery semantics depend on it.

## Sources

- https://github.com/SWE-agent/SWE-agent/blob/main/docs/installation/migration.md
- https://github.com/SWE-agent/SWE-ReX/blob/main/README.md
- https://github.com/SWE-agent/SWE-ReX/blob/main/docs/architecture.md

---

# 3. SWE-ReX: capable execution underneath a simpler agent contract

## Observed architecture

SWE-ReX exposes a deployment/runtime split:

1. a `Deployment` starts the target environment;
2. it provides a `RemoteRuntime`;
3. a FastAPI server in the remote/container environment translates requests into a `LocalRuntime`;
4. local and remote runtimes expose compatible interfaces;
5. the runtime supports file operations, one-off execution and persistent interactive sessions;
6. multiple interactive sessions can run in parallel.

The runtime can therefore retain sophistication that an individual agent does not need to expose as first-class reasoning concepts.

## Why mini's use of SWE-ReX is especially informative

Current mini-swe-agent includes SWE-ReX-backed environments, but mini's adapter still sends an individual `RexCommand` through the deployment runtime for each mini action.

In other words, mini can borrow a capable execution backend while preserving a deliberately simple action contract.

That is an important ACL pattern:

> **Backend capability does not have to become model-facing complexity.**

ACL can eventually support stronger sandboxes, remote nodes or specialized execution services without teaching every local model a large tool ontology.

## Boundary

SWE-ReX describes a runtime for interacting with sandboxed execution environments. That does not by itself define ACL's complete security policy. Image trust, mounts, networking, credentials, resource limits, secret projection and evidence ownership still require explicit deployment policy.

## Sources

- https://github.com/SWE-agent/SWE-ReX/blob/main/docs/architecture.md
- https://github.com/SWE-agent/SWE-ReX/blob/main/README.md
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/environments/extra/swerex_docker.py

---

# 4. mini-swe-agent's useful simplification: one general capability and linear control flow

## Current control flow

Current mini's default agent is a small coordinator:

1. initialize system/task messages;
2. query the model;
3. execute the returned action or actions;
4. format observations;
5. append them to the history;
6. repeat until a terminal flow-control message appears.

The current docs summarize the core step as effectively:

`step = execute_actions(query())`

Deterministic limits remain outside prompt prose, including:

- step limit;
- cost limit;
- wall-time limit;
- consecutive format-error handling.

Flow-control exceptions distinguish submission, limits, malformed model output and user interruption.

## Current default capability

The default v2 model advertises one native function tool:

`bash(command: string)`

The parser:

- requires a tool call;
- parses JSON arguments;
- rejects unknown tools;
- rejects missing `command`;
- preserves provider `tool_call_id` into the action/result relationship;
- returns concrete format feedback to the model when the structure is invalid.

This gives a model enormous practical coding capability through one small schema.

## Why this is useful to ACL

This supports the user's earlier experimental observation: small/local models can become worse when too much behavior is hard-coded into prompt rules.

A minimal worker interface can leave implementation tactics to the model while deterministic harness code enforces only the boundaries that actually require enforcement.

## Critical caveat

A single Bash tool is **not** narrow authority.

Bash can:

- read/write arbitrary accessible files;
- invoke Git;
- invoke Python/PowerShell/Node or any installed interpreter;
- open network connections;
- read environment variables;
- invoke system tools;
- launch child processes.

So mini demonstrates **low schema/scaffold complexity**, not least privilege.

## Sources

- https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/advanced/control_flow.md
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/agents/default.py
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/models/utils/actions_toolcall.py

---

# 5. Important generation change: mini v2 now uses native tool calling

## Documentation mismatch resolved by the v2 migration guide

Some current FAQ text still describes mini's original approach as not using language-model tool calling and instead parsing fenced Bash blocks from text.

That description is historically important but no longer describes the default v2 path.

Current v2 migration documentation explicitly states:

- native tool calling is now the default;
- the default model calls one Bash tool;
- text/regex parsing remains available as a legacy/compatibility model class;
- action parsing and observation formatting moved into the model adapter;
- the Agent became an even simpler coordinator.

Current source confirms this: `LitellmModel._query()` calls `litellm.completion(..., tools=[BASH_TOOL])`.

## ACL lesson

The architectural invariant survived while the wire mechanism changed.

The important property is not "never use native tool calling." It is:

> **Keep the model-facing action vocabulary small and make the adapter replaceable.**

For local workers, ACL could support:

- verified native tool calling where the exact model/runtime handles it reliably;
- a text/grammar fallback where native tool calling is weak or incompatible.

That is preferable to forcing every model/runtime combination through one nominally standardized mechanism.

## Sources

- https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/advanced/v2_migration.md
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/models/litellm_model.py
- https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/faq.md

---

# 6. Independent actions deliberately remove persistent-shell state

## Historical/current design intent

mini's design deliberately favors independent action execution rather than making the agent responsible for a long-lived shell session.

The default prompt reminds the model that directory and environment changes are not persistent between actions, and tells it to compose state into the command when needed.

This trades convenience for a simpler lifecycle:

- no long-lived shell state to reconstruct;
- fewer hidden cwd/environment mutations;
- fewer interactive shell termination semantics;
- clearer command/result boundaries;
- simpler benchmark trajectories.

## Important nuance

SWE-ReX still supports persistent interactive sessions when a workload actually requires them. mini simply does not make that sophistication the default agent contract.

## ACL/Vera lesson

Default local coding workers should prefer stateless/independent actions unless a task demonstrably needs persistent interactive state.

If ACL later exposes a persistent shell, debugger, REPL or browser session, that should be a separate explicitly owned runtime resource with:

- stable resource identity;
- lease/owner;
- lifecycle state;
- cancellation and cleanup semantics;
- checkpoint/reacquisition rules.

Do not make hidden shell state an accidental property of every worker.

## Sources

- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/config/mini.yaml
- https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/faq.md
- https://github.com/SWE-agent/SWE-ReX/blob/main/docs/architecture.md

---

# 7. Minimal local execution is deliberately unsandboxed

## Shipped environment boundary

Current mini documentation is explicit:

- the default `mini` CLI uses the local environment;
- `LocalEnvironment` executes directly on the host;
- it provides **no isolation**;
- isolated benchmark use should select Docker/Singularity/SWE-ReX/etc.

Current `LocalEnvironment` launches the model-generated shell command with the effective environment:

`os.environ | self.config.env`

That means a local worker command can read any host environment variables visible to the mini process.

## Why this matters to Vera

A future Vera/ACL worker may have access to:

- model-provider keys;
- GitHub tokens;
- service/API credentials;
- local paths;
- SSH/credential-helper state;
- other user-session environment values.

A minimal shell loop running directly under Vera's full environment would inherit far more authority than its coding task requires.

## Candidate ACL invariant

**Local convenience mode and least-privilege worker mode are different products.**

ACL workers should receive an explicit minimal child environment rather than ambient `os.environ` by default.

The model should not need to know this; the execution layer should enforce it.

## Sources

- https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/advanced/environments.md
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/environments/local.py

---

# 8. Container execution improves isolation, but provisioning is still authority

## Current Docker environment

mini's Docker environment:

- starts a detached container;
- executes individual commands via `docker exec`;
- forwards only explicitly configured host environment variables through `forward_env`;
- can add configured environment values;
- accepts caller-supplied Docker `run_args`;
- removes/stops the container during cleanup.

This is a much better secret-projection default than inheriting the entire host environment.

## But the backend is configurable authority

Caller-controlled `run_args` can materially change isolation through mounts, networking, privileges and other Docker options.

Therefore:

> **"Docker environment" is a transport/runtime label, not a complete permission profile.**

This independently validates the same boundary found in Strands, Codex and OpenHands.

## Cleanup warning

The current Docker cleanup method launches a background shell command that tries `docker stop`, then `docker rm -f` on failure.

The caller does not synchronously await and verify that the cleanup completed before `cleanup()` returns.

For ACL, `cleanup_requested` and `environment_settled` must be separate states.

## Sources

- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/environments/docker.py
- https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/advanced/environments.md

---

# 9. Closed process-leak bug #826: simplicity did not remove process-tree custody

## Failure

Issue #826 reported that the former local timeout path used `subprocess.run(shell=True, timeout=...)` and could kill only the immediate shell while leaving model-launched grandchildren alive.

The report showed Python scripts becoming orphaned under init and continuing to consume CPU after the agent had already received a timeout and moved on.

## Current fix pattern

Current `LocalEnvironment` now:

- uses `Popen`;
- starts a new POSIX session;
- on timeout kills the process group;
- drains the process output afterwards.

This is a concrete example of exactly the failure class ACL has already identified in Codex/OpenHands.

## ACL invariant

A tool timeout must settle the **owned process tree**, not just return a timeout message to the model.

A run is not stopped merely because its top-level shell or async task has stopped.

## Source

- https://github.com/SWE-agent/mini-swe-agent/issues/826
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/environments/local.py

---

# 10. Current process-kill race report: settlement paths need their own error handling

## Reported edge case

A later upstream report identified a race in the current POSIX timeout sequence: the process group can disappear between `TimeoutExpired` and `os.killpg`, causing `ProcessLookupError` before the subsequent output-drain call.

The report was closed as not planned, and a project contributor questioned whether the reproducer demonstrated a real encountered failure.

Therefore this task does **not** classify it as a confirmed production bug.

## Why retain it

The current source still has the relevant unguarded kill-then-drain sequence, so it remains a useful adversarial fixture:

- target exits exactly during timeout handling;
- kill reports already gone;
- output still needs draining;
- final state must remain deterministic.

## ACL lesson

Cleanup code is not secondary/error-path code. For long-running autonomous workers, timeout/cancel cleanup is a first-class correctness path that needs deterministic tests.

---

# 11. Open #874: loop-level limits do not bound a stalled provider call

## Failure report

Open issue #874 reports mini-swe-agent 2.4.2 hanging when an OpenAI-compatible provider begins a tool-call stream and then stalls before completing the argument chunk.

The external reproducer reaches its own hard timeout rather than mini returning a controlled provider-stream timeout.

The issue is still open. This task therefore records it as current failure evidence for the documented version/scenario, not as proof every current provider or current main is affected.

## Architectural lesson

The agent's wall-time/step loop cannot enforce a deadline while control is blocked inside a model-provider call unless the provider/transport itself has a bounded timeout/cancellation path.

ACL needs distinct owners for:

- model connection timeout;
- provider stream idle timeout;
- total model request deadline;
- tool process timeout;
- remote runtime timeout;
- total task/run deadline.

These cannot be replaced by one outer `while`-loop timer.

## Source

- https://github.com/SWE-agent/mini-swe-agent/issues/874

---

# 12. Open #872: tool-call correlation is not yet exactly-once execution identity

## Failure report

Open issue #872 reports a deterministic mock provider causing mini-swe-agent 2.4.2 to report completed results repeatedly for the same provider-issued Bash tool-call IDs.

The provided reproduction observed very large repeated result counts before the bounded test stopped.

The current parser does preserve provider `tool_call_id` on the action and result, but that alone does not establish a durable execution fence preventing the same ID from being executed/reported again.

## ACL/Vera significance

This is a very important distinction:

> **Correlation ID != idempotency/effect ID.**

For ACL, a tool/effect identity should record at minimum:

- proposed;
- authorized/denied;
- started;
- completed/failed/unknown-after-crash;
- result identity;
- whether a duplicate request was replayed, suppressed or reconciled.

A repeated provider/tool event must not silently repeat an external side effect.

## Source

- https://github.com/SWE-agent/mini-swe-agent/issues/872
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/models/utils/actions_toolcall.py

---

# 13. Current tool extensibility pressure: #889

## Observed

Current `LitellmModel._query()` hardcodes the tool list as `[BASH_TOOL]`.

Open issue #889 points out that adding a second model-native tool currently requires copying/overriding the larger `_query` method rather than overriding one narrow tool-list seam.

## Interpretation

This is not necessarily a design defect. The one-tool contract is part of mini's simplicity.

It does, however, expose a choice ACL will eventually need to make:

- keep workers on a tiny general-purpose shell interface and enforce authority underneath it; or
- expose a larger set of typed first-class tools for actions where semantic policy/evidence is valuable.

## Likely ACL direction to test later

Do not choose yet.

A useful future experiment is to benchmark local workers under:

1. one Bash tool;
2. Bash plus a few high-value typed ACL tools;
3. fully typed filesystem/Git/test tools.

Measure both task success and authority/evidence quality.

## Source

- https://github.com/SWE-agent/mini-swe-agent/issues/889
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/models/litellm_model.py

---

# 14. Security boundary is intentionally outside the minimal core

## Current shipped observation

The default mini execution path does not contain a Strands-Cedar/Codex-style deterministic authorization engine before each model-generated Bash command.

The task text is rendered into model-visible input, the model chooses Bash, and the selected environment executes it subject to that environment's actual OS/container authority.

Open RFC #953 proposes optional deterministic execution policy for untrusted task text, including secret/egress/Git-remote controls and audit receipts.

A participant reviewing the current path noted the lack of a pre-execution policy hook. Another participant explicitly resisted adding the complexity to the core. A follow-up suggested an optional environment wrapper.

This task does not attribute maintainer status to those commenters without separate evidence and does not treat the RFC as shipped functionality.

## Why the debate is useful

It makes the design tension explicit:

- minimal core has research/hackability value;
- production/private-repo use still needs deterministic execution policy;
- adding policy logic directly into every model/scaffold path risks recreating the complexity mini was designed to escape.

## ACL/Vera lesson

A strong synthesis with prior projects is:

> **Keep the minimal worker loop. Wrap the effect boundary.**

ACL can preserve a mini-like model interface while an outer execution layer owns:

- filesystem roots;
- credentials;
- network destinations;
- Git/ref authority;
- command/effect policy;
- approval;
- idempotency;
- evidence.

## Source

- https://github.com/SWE-agent/mini-swe-agent/issues/953
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/environments/local.py

---

# 15. Model-facing timeout feedback can create compensation loops

## Current open report

Issue #950 reports that after the model sees a 30-second command timeout, it may begin inserting `sleep 29` into later commands in an attempt to work around the observed runtime behavior.

The report proposes misleading the model with a shorter displayed timeout. That proposed remedy is not adopted here.

## ACL lesson

The more general finding is useful:

> **Tool observations are part of the model's behavioral environment.**

A model can learn to game or compensate for literal harness details that were intended only as diagnostics.

ACL should distinguish:

- operator/evidence telemetry;
- model-facing actionable feedback.

Model feedback should be truthful but semantic, for example:

- `command exceeded action deadline`;
- `use a bounded or background-safe strategy`;
- `long-running work requires the long-task interface`.

Do not expose irrelevant internal timing trivia merely because it exists in the runtime exception.

## Source

- https://github.com/SWE-agent/mini-swe-agent/issues/950

---

# 16. Local-model support is broad, but metadata and realized capability remain separate

## Current support

mini uses LiteLLM by default and documents local-provider configuration through `model_kwargs`, provider names and `api_base`.

The local-model guide includes:

- Ollama-compatible registry examples;
- custom OpenAI-compatible endpoints;
- a concrete local vLLM example;
- custom model registry metadata for context/cost information;
- warnings that model/provider names must match exactly.

The legacy text-based parser remains available alongside default native tool calling.

## ACL relevance

This combination is attractive for ACL local workers because it gives two compatibility strategies:

- native Bash tool calling for verified model/runtime tuples;
- text/regex action extraction as a fallback for models whose native tool protocol is unreliable.

However, the model registry is still metadata/configuration. A declared context window or provider label is not proof that the actual server honors it.

## Candidate deployment identity

An ACL local worker benchmark should record:

- exact model artifact/name;
- quantization where relevant;
- runtime and version;
- adapter/model class;
- endpoint/API mode;
- actual context limit;
- tool-calling mode;
- stream behavior;
- request/idle timeouts;
- retry configuration;
- hardware/runtime settings.

## Global configuration warning

The docs note that `MSWEA_COST_TRACKING=ignore_errors` is global and affects all models.

That is a small but useful reminder: global configuration can leak across otherwise independent model profiles. ACL should prefer per-run/per-worker deployment profiles for behavior-affecting settings.

## Sources

- https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/models/local_models.md
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/models/litellm_model.py
- https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/advanced/v2_migration.md

---

# 17. Retry is bounded, but retry ownership remains specific to the model-request layer

## Current model retry

mini's retry helper uses Tenacity with:

- configurable max attempts;
- default 10 attempts;
- exponential wait;
- explicit abort exception classes.

Authentication, unsupported parameters, missing model, permission denial and context-window errors are among errors that abort rather than being blindly retried.

## ACL lesson

This is a useful thin retry mechanism, but its scope should remain explicit:

- model transport retry is not tool retry;
- tool retry is not effect retry;
- format correction is not provider retry;
- crash recovery is not retry.

This reinforces the Pydantic/Strands findings that retry classes need separate budgets and reasons.

## Source

- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/models/utils/retry.py

---

# 18. Linear trajectory persistence is excellent evidence, but not a checkpoint

## Current behavior

The default agent can save its trajectory after each loop iteration.

The serialized evidence includes:

- messages;
- model configuration/type;
- environment configuration/type;
- model statistics/cost/call data;
- tool results;
- raw provider response metadata where available;
- timestamps/return codes/raw output in tool-result `extra` fields;
- version/format information;
- terminal exit status/submission.

The v2 migration guide also explicitly warns that exact message structure can vary by provider/API representation.

## What was not found

Task 12 did not find a mini-swe-agent durable resume/checkpoint system that reconstructs a partially completed world from a saved trajectory. Repository search for a resume mechanism did not produce one.

Therefore:

> **A mini trajectory is an evidence/reproducibility artifact, not proof of safe resumability.**

It does not capture or reconcile:

- arbitrary workspace state;
- external API/network effects;
- still-running processes;
- container cleanup state;
- credentials/grants;
- idempotency/effect settlement.

## ACL lesson

Keep the simple append-oriented trajectory idea, but layer it underneath ACL's authoritative task/checkpoint/effect model rather than asking the transcript to become that model.

## Sources

- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/agents/default.py
- https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/advanced/v2_migration.md
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/models/utils/actions_toolcall.py

---

# 19. Model-visible observations can be bounded while raw evidence remains richer

## Current default

The default mini configuration bounds oversized command output rendered back to the model: large output is represented using a head/tail plus elided-character count.

The tool-result formatter separately stores raw output in the message's `extra` evidence fields.

## ACL relevance

This is a useful separation:

- **model context** should be bounded and optimized for continued reasoning;
- **audit/debug evidence** can retain richer execution detail subject to security/retention policy.

This is the same four-plane distinction emerging across the research campaign:

1. model-visible context;
2. UI/operator presentation;
3. durable runtime/task state;
4. audit/effect evidence.

Do not force full raw logs back into a small local model merely to preserve evidence.

## Sources

- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/config/mini.yaml
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/models/utils/actions_toolcall.py

---

# 20. Evaluation harness correctness is itself part of the trusted evidence chain

## Current maintenance evidence

The SWE-agent main commit examined during this task fixes an evaluation adapter mapping for SWE-bench multimodal runs.

The previous mapping generated a downstream `sb-cli` subset value that the evaluation tool rejected. The fix maps to the accepted `swe-bench-m` identity and makes unsupported subsets fail with a clear error rather than a generic lookup failure.

## Why this matters to ACL

A benchmark result can be wrong or unavailable even if the worker itself behaved correctly when:

- benchmark subset identity is wrong;
- fixture/environment mapping is wrong;
- evaluator version differs;
- workspace contamination occurs;
- harness adapter silently changes behavior.

This reinforces promptfoo's lesson that evaluator integrity and harness-boundary failure need separate classification from model failure.

## Source

- https://github.com/SWE-agent/SWE-agent/commit/3ea751c087f32b16e039a2233dd6eefecef325d5

---

# 21. Supply-chain maintenance is visible in the current mini dependency policy

## Observed

Current mini `pyproject.toml` explicitly excludes LiteLLM versions `1.82.7` and `1.82.8` with the comment that those versions were compromised.

This task does not deep-research the LiteLLM incident because LiteLLM has its own later ranked slot. The direct mini dependency constraint is nevertheless relevant evidence that a privileged coding-agent scaffold must actively carry supply-chain policy.

## ACL lesson

A tiny agent loop does not reduce the importance of dependency governance.

For privileged worker software, ACL should eventually record:

- dependency version/commit;
- trust/advisory status;
- blocked versions;
- rationale/evidence;
- re-review/retirement conditions.

## Source

- https://github.com/SWE-agent/mini-swe-agent/blob/main/pyproject.toml

---

# 22. What was deliberately removed versus retained versus moved

## Moved out of the reasoning loop

### Into SWE-ReX / execution adapters

- local-versus-remote execution transport;
- container/cloud deployment;
- richer shell/interactive runtime machinery;
- parallel runtime sessions;
- infrastructure-specific command execution.

### Into model adapters

mini v2 moved:

- action parsing;
- observation formatting;
- native-tool versus text-parser differences;
- provider-specific response representation.

### Into environment adapters

- local versus Docker/Singularity/SWE-ReX/Modal execution;
- environment projection;
- command timeout implementation;
- cleanup behavior.

## Deliberately simplified or removed from mini's default user experience

- large multi-tool scaffold as the default;
- persistent shell state in the normal action contract;
- complex environment setup logic in the agent;
- several older dedicated model/provider classes;
- rotating API-key feature;
- dedicated GitHub issue runner;
- v2 alternate visual UI whose maintenance complexity exceeded adoption.

## Retained because it still matters

- explicit model/environment protocols;
- cost/step/run limits;
- retries;
- malformed-output recovery;
- trajectory saving;
- provider/runtime configurability;
- isolated execution options;
- benchmark runners;
- current native tool-call IDs and raw evidence;
- process timeout handling.

## Still intentionally outside mini's minimal core

- comprehensive permission/authorization policy;
- production credential brokerage;
- durable checkpoint/resume;
- exactly-once external effect ledger;
- distributed writer leases/fencing;
- independent acceptance verifier;
- full long-running project/dependency scheduler.

These are precisely the responsibilities ACL needs outside a mini-like local worker loop.

---

# 23. Candidate ACL/Vera invariants from Task 12

These are research-derived candidates, not implementation decisions.

1. **Make model-facing complexity earn its place.** Do not add a prompt/tool abstraction merely because a larger framework exposes one.
2. **Move deterministic infrastructure out of the agent loop rather than encoding it in prompts.**
3. **Use a small replaceable action protocol.** One Bash-like capability is a valid benchmark baseline, not automatically the final authority model.
4. **Backend sophistication need not be model-facing sophistication.** Remote/container execution can live under the same small action interface.
5. **Independent actions should be the default.** Persistent interactive sessions are explicit leased runtime resources, not ambient hidden state.
6. **Local execution receives no implicit trust bonus.** Host subprocess mode is full host authority unless separately constrained.
7. **Child environment is explicit/minimal.** Do not forward the supervisor's whole environment to a worker by default.
8. **Container label is not permission policy.** Record mounts/network/user/credentials/resources separately.
9. **Cleanup requested != cleanup completed.** Environment settlement needs evidence.
10. **Timeout settles the whole owned process tree.** Top-level shell/coroutine death is insufficient.
11. **Each blocking plane has its own timeout/cancellation owner.** An outer loop deadline cannot bound a stuck provider stream.
12. **Tool-call correlation IDs are not enough.** External effects require durable exactly-once/idempotency state.
13. **Authorization wraps the effect boundary.** Keep it outside prompt prose and preferably outside model-specific adapters.
14. **Model-facing feedback and operator telemetry are separate representations.** Give the model truthful actionable semantics, not raw implementation trivia by default.
15. **Native tool calling is a capability, not a universal requirement.** Preserve a fallback action encoding for local runtimes that fail native tool-call probes.
16. **Retry layers remain separate.** Provider retry must not silently become effect replay.
17. **Trajectory != checkpoint.** Conversation evidence alone cannot justify auto-resume.
18. **Model-visible output can be truncated while evidence remains richer.** Context budget and audit retention are different policies.
19. **Evaluator/harness adapters are trusted evidence code.** Benchmark mapping/version failures need their own classification.
20. **Dependency provenance matters even for tiny workers.** A minimal source tree can still import a large privileged supply chain.

---

# 24. Proposed ACL regression fixtures derived from this lineage

Future test candidates only; nothing was implemented in Task 12.

## Agent simplicity / adapter tests

1. Run the same bounded code-repair task with one Bash tool versus a small typed tool set and compare success, tokens and failure modes.
2. Switch a worker from native tool calling to text-based action parsing without changing authoritative task/effect semantics.
3. Run identical action sequences through local, Docker and remote/SWE-ReX-like adapters and assert the evidence contract remains stable.

## Authority tests

4. Give task text an injected instruction to read a host secret; local-host worker must not receive that secret under the ACL production profile.
5. Container with deliberately dangerous mount/run arguments must be rejected by ACL policy even though the backend itself accepts the arguments.
6. Git/network/credential authority remains independent from generic shell availability.

## Process/cancellation tests

7. Model launches shell→Python→grandchild infinite loop; timeout settles all owned descendants.
8. Target exits during timeout kill race; cleanup still drains output and records deterministic terminal state.
9. Docker/container cleanup is slow/fails; run remains `cleanup_pending` or `unresolved`, never falsely `settled`.
10. Provider sends partial tool-call stream then stalls; provider idle deadline returns controlled failure without hanging the worker.

## Effect/idempotency tests

11. Provider repeats the same tool-call ID; execution effect occurs at most once.
12. Crash after effect start but before result persistence becomes `unknown_after_crash`, not silently retried.
13. Provider retry after transport ambiguity cannot repeat a previously settled destructive action.

## Evidence/recovery tests

14. Model-facing output is truncated but full verifier evidence remains available outside model context.
15. Saved trajectory exists but workspace/effect state is incomplete; auto-resume refuses.
16. Benchmark adapter maps a task/subset to an invalid evaluator identity; classify as harness/eval failure, not model failure.

## Local-model tests

17. Exact local runtime fails native Bash-tool protocol; capability profile downgrades to text parser before a retry storm.
18. Declared context metadata disagrees with realized runtime limit; benchmark records realized capability and fails profile verification.
19. Global model setting changes one worker; sibling worker profile remains unaffected.

---

# 25. Reusable mechanisms worth later comparison

No adoption decision is made here. The strongest concrete candidates are:

## From mini-swe-agent

- tiny inspectable agent loop;
- one-tool baseline;
- model-adapter ownership of parsing/observation formatting;
- independent command execution semantics;
- explicit cost/step/run limits;
- format-error feedback;
- simple protocol/duck-typing extension model;
- per-step trajectory persistence;
- bounded model-facing command output plus richer raw evidence;
- native-tool and legacy-text duality for model compatibility.

## From SWE-ReX

- deployment/runtime separation;
- interchangeable local/remote runtime interface;
- capable execution backend hidden below simple agent contract;
- remote/container execution;
- richer interactive sessions only when needed;
- scalable parallel execution.

## From SWE-agent history

- migration evidence showing which complexity was worth extracting;
- benchmark/evaluation tooling discipline;
- explicit maintenance/successor status rather than silent abandonment.

---

# 26. What not to copy uncritically

1. Do not use mini's default host-local execution profile as ACL's production security model.
2. Do not forward the entire supervisor environment to model-generated shell commands.
3. Do not equate one Bash schema with narrow authority.
4. Do not rely on container selection alone to define mounts/network/credentials.
5. Do not treat asynchronous fire-and-forget cleanup as settled cleanup.
6. Do not let `tool_call_id` remain transcript-only correlation if an action has an external effect.
7. Do not rely on outer agent-loop wall time to interrupt a stalled provider stream.
8. Do not treat a linear trajectory as resumable authoritative state.
9. Do not expose raw runtime implementation detail to the model merely because it is useful to operators.
10. Do not enlarge the worker protocol until ACL-specific benchmark evidence shows the extra abstraction pays for itself.

---

# 27. Cross-project validation without selecting a winner

Task 12 independently validates several findings from earlier Tier-A projects:

## Validates Pydantic / Strands / Cline

- model/runtime compatibility is more specific than provider-name compatibility;
- retry classes need explicit ownership;
- process/runtime controls belong outside prompt prose;
- tool validation is separate from execution authority.

## Validates Codex / OpenHands

- process-tree settlement is distinct from cancellation state;
- local workspace/container identity is distinct from authority;
- credentials/environment projection require their own policy;
- outer deterministic boundaries can coexist with a flexible reasoning loop.

## Validates promptfoo

- evaluator/harness failure must be distinguished from model failure;
- trajectories are valuable evidence but acceptance should be independently verified.

## Adds a distinct lesson

The lineage provides unusually direct maintainer evidence that **scaffold simplification itself can be a successful architectural move** when complexity is deliberately relocated into appropriate lower-level components.

That is stronger than merely observing that a small codebase is aesthetically attractive.

---

# 28. Project maturity and maintenance assessment

## SWE-agent

- explicit maintenance-only state;
- superseded for new use by mini-swe-agent;
- still receiving targeted fixes;
- valuable historical/reference code, not a default new-dependency candidate without a special reason.

## mini-swe-agent

- active current development;
- package metadata classifies it as **Alpha**;
- substantial v2 breaking changes have already occurred;
- intentionally optimized for simplicity/hackability/research;
- current open issues expose real provider/tool/idempotency/timeout boundaries;
- no evidence in this task justifies treating its minimal core as a production security/runtime layer by itself.

## SWE-ReX

- purpose-built execution abstraction from SWE-agent experience;
- supports runtime/platform breadth and parallelism;
- relevant as an execution-component reference even though mini can also use simpler direct environments.

## Dependency maintenance signal

mini currently excludes specific compromised LiteLLM versions in dependency metadata. This is a positive example of explicit supply-chain response, while also emphasizing that an agent's effective trusted computing base is much larger than its own line count.

---

# 29. Overall Task 12 assessment

The SWE-agent → SWE-ReX → mini-swe-agent transition is one of the most directly relevant research cases for ACL so far because it closely mirrors the user's own experimental lesson.

The important conclusion is **not** "use mini-swe-agent" and not "all agents should be 100 lines."

The evidence supports a more precise architecture principle:

> **Keep the model-facing worker loop as small and native as practical. Put complexity only where deterministic ownership is required: execution adapters, sandbox/permission policy, process custody, credentials, effect identity, recovery and independent evaluation.**

The project lineage also shows the inverse warning: deleting scaffold complexity does not delete operational responsibility.

mini's current failure surfaces prove that even a very small loop still needs robust answers for:

- process-tree cleanup;
- provider stream timeouts;
- duplicate tool/effect identity;
- ambient credentials;
- sandbox provisioning;
- cleanup settlement;
- local-runtime capability;
- trajectory versus checkpoint semantics;
- evaluation harness integrity.

For ACL/Vera, mini-swe-agent is therefore strongest as a **minimal worker-loop/control-flow reference and benchmark baseline**, while SWE-ReX is strongest as an **execution-runtime separation reference**. Neither by itself replaces ACL's planned authoritative project scheduler, dependency gates, effect ledger, protected verifier, credential governance, checkpoint/recovery layer or Vera memory system.

No dependency, fork, wrapper, architecture winner or implementation decision is made in Task 12.

---

# Primary evidence index

## SWE-agent transition / status

- https://github.com/SWE-agent/SWE-agent
- https://github.com/SWE-agent/SWE-agent/blob/main/docs/overrides/main.html
- https://github.com/SWE-agent/SWE-agent/blob/main/docs/installation/migration.md
- https://github.com/SWE-agent/SWE-agent/commit/3ea751c087f32b16e039a2233dd6eefecef325d5

## mini-swe-agent architecture / configuration

- https://github.com/SWE-agent/mini-swe-agent
- https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/faq.md
- https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/advanced/control_flow.md
- https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/advanced/v2_migration.md
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/agents/default.py
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/config/mini.yaml
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/models/litellm_model.py
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/models/utils/actions_toolcall.py
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/models/utils/retry.py

## Execution / sandbox

- https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/advanced/environments.md
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/environments/local.py
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/environments/docker.py
- https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/environments/extra/swerex_docker.py
- https://github.com/SWE-agent/SWE-ReX/blob/main/README.md
- https://github.com/SWE-agent/SWE-ReX/blob/main/docs/architecture.md

## Local models

- https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/models/local_models.md

## Current/recent failure evidence

- https://github.com/SWE-agent/mini-swe-agent/issues/826
- https://github.com/SWE-agent/mini-swe-agent/issues/872
- https://github.com/SWE-agent/mini-swe-agent/issues/874
- https://github.com/SWE-agent/mini-swe-agent/issues/889
- https://github.com/SWE-agent/mini-swe-agent/issues/950
- https://github.com/SWE-agent/mini-swe-agent/issues/953

## Dependency / maintenance metadata

- https://github.com/SWE-agent/mini-swe-agent/blob/main/pyproject.toml

---

# Stop boundary

Task 12 ends after recording the SWE-agent → SWE-ReX → mini-swe-agent transition, current mini v2 architecture, execution/sandbox/process/local-model/evidence/security failure boundaries, reusable mechanisms and ACL/Vera candidate invariants.

**llama.cpp research is not part of Task 12 and must not begin until separately authorized.**
