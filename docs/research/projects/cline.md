# Cline Deep Research

**Task:** ranked project deep research #2  
**Project:** Cline  
**Canonical repository:** https://github.com/cline/cline  
**Research date:** 2026-09-05  
**Status:** deep research complete; no adoption/fork/build decision made

## Why Cline is being studied

Cline is relevant to ACL/Vera because it is not only a model client. Its current repository contains a coding-agent runtime, stateful orchestration layer, local and hosted model adapters, file and shell tools, approval policy, checkpoints, context compaction, sub-agents, hooks, telemetry, schedules and a local hub that can keep agent runtimes alive independently of one attached UI client.

This report does **not** ask whether Cline is the best coding agent. It asks which mechanisms, failure modes and invariants reduce uncertainty for ACL/Vera.

The research intentionally did not expand into the separate Cline Kanban repository or attempt a cross-project winner comparison. Those would be later tasks.

## Executive assessment

Cline remains a justified Tier-A research target.

Its highest information value for ACL is not its prompt design. It is the set of operational problems exposed by a real coding-agent product under continuous use:

1. separating a stateless agent loop from stateful session/orchestration ownership;
2. enforcing some policy in runtime/tool hooks instead of relying on model instructions;
3. keeping transcript identity, workspace checkpoints and recovery semantics coherent across retries, compaction and restarts;
4. representing local/provider capabilities explicitly enough that context-window and tool behavior reach the actual wire protocol;
5. detecting repeated tool loops and consecutive mistakes outside the model's reasoning prompt;
6. preserving stable agent/session/tool-call identifiers in telemetry and persistence;
7. distinguishing convenience guards from security boundaries.

Cline also provides strong negative evidence. Current issues and recent fixes show that apparently safe features such as Plan mode, checkpoint restore, auto-approval, ignore files and provider wrappers can fail when their enforcement boundary is incomplete or when two lifecycle/permission systems disagree.

The resulting ACL lesson is **not** “copy Cline.” It is: use Cline's hard-earned failure surfaces to define explicit invariants before ACL workers receive long-running write/shell authority.

---

## 1. Project status and engineering signal

### Observed

The canonical `cline/cline` repository is active and not archived. At research time it was receiving commits through 2026-09-04. The README describes Cline as an open-source coding agent available in IDE and terminal surfaces, with local-model support, Plan/Act modes, approvals, checkpoints, MCP/plugins and other agent features.

The current SDK architecture is being published as multiple packages. `@cline/core` was version `0.0.82` when checked and describes itself as the Cline Core SDK for Node Runtime.

Primary sources:
- https://github.com/cline/cline
- https://github.com/cline/cline/blob/main/README.md
- https://github.com/cline/cline/blob/main/sdk/ARCHITECTURE.md
- https://github.com/cline/cline/blob/main/sdk/packages/core/package.json

### Interpretation

Activity is a positive maintenance signal, but the low SDK package version and the density of recent architecture migrations/fixes indicate a rapidly changing surface. That favors studying mechanisms and tests now while deferring any dependency/pinning decision until the later build-versus-reuse phase.

**Confidence:** high.

---

## 2. Architecture: stateless agent loop, stateful orchestration

### Observed

Cline's SDK architecture explicitly separates layers:

- `@cline/shared` — shared contracts/types, paths, hooks and common utilities.
- `@cline/llms` — provider/model catalogs, provider contracts and model execution adapters.
- `@cline/agents` — the stateless runtime loop, tool orchestration, runtime events and turn preparation.
- `@cline/core` — stateful orchestration: sessions, persistence, settings, tools, plugin loading, compaction, telemetry, hub and schedules.
- host applications — VS Code, CLI and other surfaces.

The architecture document explicitly says the agent runtime should not own persistence or host lifecycle. Core owns session lifecycle and durable artifacts around it.

The local hub architecture also separates an authority runtime from attached clients. A UI/client can attach or detach while the runtime persists. Session status is reported from the runtime/persistence layer rather than invented by clients.

Primary source:
- https://github.com/cline/cline/blob/main/sdk/ARCHITECTURE.md

### ACL/Vera relevance

This aligns strongly with ACL's need to let a local model reason naturally while keeping durable task state, project ownership, scheduling and recovery in a deterministic harness layer.

Candidate invariant:

> Model execution may be stateless or replaceable; authoritative project/session lifecycle must live in a separate stateful owner with durable identifiers and persistence.

This also reduces coupling between model/provider replacement and ACL project state.

### Warning

Layer separation does not automatically make state correct. Cline's recent checkpoint, abort/restart and compaction bugs demonstrate that the boundaries still require explicit lifecycle semantics and tests.

**Confidence:** high.

---

## 3. Session identity, provenance and long-running runtimes

### Observed

Cline's core telemetry/runtime types distinguish root agents, sub-agents, team leads and teammates and carry identifiers including agent ID, conversation ID, parent agent ID and team fields.

Architecture material also records session provenance/initiator information and supports runtimes that outlive a single attached UI client. Long-running shell process handling includes explicit process identity and detached process behavior rather than assuming that a lost client means a process ended.

Primary sources:
- https://github.com/cline/cline/blob/main/sdk/ARCHITECTURE.md
- https://github.com/cline/cline/blob/main/sdk/packages/core/src/services/telemetry/core-events.ts
- https://github.com/cline/cline/blob/main/sdk/packages/shared/src/agents/types.ts

### ACL/Vera relevance

ACL already wants project/task/subtask IDs for troubleshooting. Cline provides evidence that identity should extend further:

- project ID;
- task/work-item ID;
- conversation/session ID;
- agent instance ID;
- parent/creator agent ID;
- run ID;
- iteration number;
- tool-call ID;
- external effect/idempotency identity.

A durable identity graph is more reliable than reconstructing parentage from transcript ordering or filenames.

**Confidence:** high.

---

## 4. Plan mode: why prompt-only policy failed

### Observed

Cline historically kept command execution available in Plan mode for investigation while relying substantially on prompting to discourage mutations.

Commit `472f9c88c5fda6cc6c60e9e08e04fccbf905e487` states directly that weaker models routinely ignored that instruction. Cline added a core `beforeTool` plan-mode guard so file-editing shell commands are rejected before normal tool policy/user approval.

The current command guard blocks many obvious mutation forms: file-manipulation commands, mutating Git/package-manager operations, in-place editing flags, redirects, common download-to-file patterns and Windows/PowerShell equivalents.

However, the source explicitly says it is a blacklist, **not a shell interpreter**. It documents false negatives such as Python code that writes files and mutations hidden inside quoted shell commands.

Current open issue #13586 demonstrates the exact gap: in Plan mode a model could not use the editor, so it wrote files through Python invoked by `run_commands` using `pathlib.Path.write_text` / `open(..., 'w')`.

Primary sources:
- https://github.com/cline/cline/commit/472f9c88c5fda6cc6c60e9e08e04fccbf905e487
- https://github.com/cline/cline/blob/main/sdk/packages/core/src/extensions/tools/command-guard.ts
- https://github.com/cline/cline/issues/13586

### ACL/Vera lesson

This is direct evidence supporting the user's earlier ACL lesson: do not spend scarce local-model context trying to encode every policy as prose.

Candidate invariant:

> A role declared read-only must receive capabilities that are actually read-only. Prompt text, command-name blacklists and user intention are not substitutes for authority separation.

For ACL, a planner/research worker should ideally receive no write-capable filesystem handle and no unrestricted shell. If shell inspection is necessary, it should run inside a stronger execution boundary or through read-only structured tools.

### Important nuance

Cline's guard is still useful as defense-in-depth and workflow feedback. The lesson is not “blacklists are useless”; it is that they must not be the final security boundary.

**Confidence:** high.

---

## 5. Approval and auto-approval semantics

### Observed

Cline exposes per-category approval settings for reads, edits, commands, browser and MCP behavior. Its user documentation recommends cautious defaults and describes YOLO mode as dangerous because it removes approval prompts broadly.

The auto-approve documentation says terminal safety is not a fixed hardcoded allowlist: the model marks commands with a `requires_approval` signal based on the command/arguments. This means command classification can depend on model output unless a stronger host policy intercepts it.

The SDK permission guide contains another important default: tools that are not listed in `toolPolicies` are enabled and auto-approved by default. Cline's application layer compensates by marking its controlled tools as not auto-approved and routing them through approval settings.

Cline also removed per-tool MCP auto-approve UI that was not actually enforced, leaving the global MCP approval toggle as the operative control.

Primary sources:
- https://github.com/cline/cline/blob/main/docs/features/auto-approve.mdx
- https://github.com/cline/cline/blob/main/docs/sdk/guides/permission-handling.mdx
- https://github.com/cline/cline/blob/main/apps/vscode/src/sdk/sdk-tool-policies.ts
- https://github.com/cline/cline/blob/main/sdk/CHANGELOG.md

### ACL/Vera relevance

Several invariants follow:

1. policy UI must match runtime semantics;
2. unregistered/unclassified tools should not silently inherit authority;
3. approval is a workflow decision, not a sandbox;
4. “safe command” labels generated by a model must not be the only gate for privileged execution;
5. ACL should prefer default-deny/exhaustive policy for extension/plugin tools.

This is especially important if Vera eventually loads third-party tools or plugins dynamically.

**Confidence:** high.

---

## 6. Provider wrappers can create a second authority system

### Observed

Open issue #13146 concerns Cline's Claude Code provider. The reporter reproduced a state where Claude Code's native file/shell permission system was active, but its working directory/settings/approval callback were not coherently wired into Cline's own approval model. Cline's auto-approve settings therefore could not authorize those native tools.

The issue remains open and was reopened; it is assigned to Cline maintainer Saoud Rizwan.

Primary source:
- https://github.com/cline/cline/issues/13146

### ACL/Vera relevance

This is a useful architectural warning independent of that provider's eventual fix:

> Wrapping another agent/harness does not automatically preserve the outer harness's authority model.

An embedded agent can introduce:
- a second tool namespace;
- a second approval system;
- a second working-directory/root concept;
- different credential loading;
- native tools that bypass outer checkpoints/diffs/telemetry;
- inconsistent cancellation and retry semantics.

If ACL later hosts external coding agents as workers, the integration contract must state who owns tool execution and permissions. One coherent option is to use an external agent purely as a text/model transport and keep all side-effect tools in ACL. Another is to explicitly bridge the external agent's native tool authorization into ACL. Mixing both implicitly is unsafe and hard to reason about.

**Confidence:** high on the architectural lesson; issue-specific root cause remains an open upstream matter.

---

## 7. File editing: strong previews, but real overwrite failures still occur

### Observed

Cline's SDK `apply_patch` executor computes a patch preview before applying changes. It parses update/delete targets against current contents and rejects unmatched hunks. Relative paths are normally constrained to the configured working directory.

A current safety fix is especially informative. Commit `adbfbd97d352c82f7001273365f6a4bac38b5adb` fixed `apply_patch` **Add File** silently overwriting an existing file. The parser already had a “File already exists” guard, but the executor had only loaded UPDATE/DELETE targets, so ADD did not know the target already existed; `fs.writeFile` then replaced it. The fix loads ADD targets and includes regression coverage proving existing content remains unchanged.

Primary sources:
- https://github.com/cline/cline/blob/main/sdk/packages/core/src/extensions/tools/executors/apply-patch.ts
- https://github.com/cline/cline/commit/adbfbd97d352c82f7001273365f6a4bac38b5adb

### ACL/Vera relevance

The value of this bug is the invariant it exposes:

> A safety rule is only real if the execution layer has the state required to evaluate it immediately before mutation.

Parser validation alone was insufficient because the required target-existence state was absent.

ACL file mutation should therefore consider:
- explicit create-vs-overwrite semantics;
- preview/diff before execution;
- expected version/hash where concurrent edits are possible;
- target type checks;
- authoritative workspace root;
- post-write verification;
- regression tests built from real destructive failures.

### Warning

The examined Cline `apply_patch` implementation does not establish a general compare-and-swap/expected-hash contract across the gap between preview and final write. That should not be inferred from patch parsing alone.

**Confidence:** high.

---

## 8. Path containment and ignore rules are not the same thing

### Observed

The current `.clineignore` documentation explicitly says the original feature is not a security/access-control boundary. It filtered automatic context, but explicit mentions or shell commands could still access ignored files.

Cline is moving toward an enforced `PreToolUse` hook example that can cancel reads/edits/commands matching ignore patterns. Even that hook documents limitations:
- shell token checking is not a full shell parser;
- symlinks are not resolved;
- hooks are disabled in CLI YOLO mode;
- paths outside the workspace are outside the `.clineignore` policy scope.

Primary source:
- https://github.com/cline/cline/blob/main/docs/customization/clineignore.mdx

### ACL/Vera relevance

Context filtering, access policy and OS isolation should be separate concepts.

Candidate design split:
- **context filter:** what information is automatically shown to a model;
- **tool policy:** what named resources/actions a worker may request;
- **filesystem containment:** what paths the process can reach;
- **OS/container isolation:** what the process can actually access even after parser/guard failure.

Using one mechanism for all four creates false confidence.

**Confidence:** high.

---

## 9. Checkpoints: workspace snapshots are valuable but difficult

### Observed

Cline checkpoints use a shadow Git mechanism to capture project state and allow restore of workspace, chat, or both. Documentation says checkpoints are created around tool use and include project changes, including untracked files in the current design.

Recent commit `8d078f59bdb63f3d80a7e71668fe2f4066002c44` repaired multiple checkpoint invariants:

- some SDK surfaces failed to create checkpoints because a hook assumed a different ordering of user-prompt insertion;
- an in-memory counter could overwrite valid snapshots after restart;
- low-level runtime continuations/tool-result messages distorted run numbering relative to user-visible turns;
- compaction summaries could span folded turns incorrectly;
- plain Git stash snapshots omitted untracked files;
- restore needed a pre-restore recovery snapshot and safe handling of files created after the checkpoint.

Issue #13550 then revealed a separate restore hazard: restoring an old checkpoint could move the user's real branch pointer with `git reset --hard`, knocking later commits off the branch.

Commit `89c2efa970a115d0815942e4eb69f1a74f9d3b5e` fixed that by refusing workspace restore if HEAD moved from the checkpoint base and by using Git `update-ref` compare-and-swap to close the race between verification and branch movement.

Primary sources:
- https://github.com/cline/cline/blob/main/docs/core-workflows/checkpoints.mdx
- https://github.com/cline/cline/commit/8d078f59bdb63f3d80a7e71668fe2f4066002c44
- https://github.com/cline/cline/issues/13550
- https://github.com/cline/cline/commit/89c2efa970a115d0815942e4eb69f1a74f9d3b5e

### ACL/Vera relevance

Cline's checkpoint history is one of this task's highest-value evidence sets.

Candidate invariants:

1. conversation turns, internal retries and tool continuations need distinct identities;
2. checkpoint identity must survive restart and compaction;
3. workspace snapshots must explicitly define tracked, untracked and ignored-file behavior;
4. restore is itself a destructive/concurrent operation and needs a precondition/CAS guard;
5. user Git history must not be collateral state for an agent checkpoint mechanism;
6. create a recovery point before destructive restore;
7. restore should refuse when assumptions no longer hold rather than silently “best effort.”

### Critical boundary

Cline's workspace checkpoint does **not** imply reversal of arbitrary external side effects. A shell command may change a database, cloud service, remote Git repository, installed package or other state that shadow Git cannot rewind.

ACL should therefore keep workspace checkpoint state separate from the external-effect ledger / uncertain-side-effect problem already identified in Task 5.

**Confidence:** high.

---

## 10. Checkpoint performance is part of reliability

### Observed

Issue #13131 reports checkpoint creation blocking the request path for roughly 90 seconds per turn in a large Git repo under a Windows cloud-sync filesystem filter. The issue isolated the delay to the checkpoint feature.

Primary source:
- https://github.com/cline/cline/issues/13131

### ACL/Vera relevance

A safety mechanism that serializes expensive workspace snapshots into every model turn can become operationally disabling.

ACL should measure:
- checkpoint latency;
- bytes/files scanned;
- delta size;
- storage growth;
- retention/GC time;
- impact on first-token latency;
- fallback behavior when checkpoint creation fails.

This matters for the user's goal of workers operating for hours: persistence overhead accumulates even if model inference speed is not the primary concern.

**Confidence:** medium-high; issue report is specific to one environment but the architecture risk is general.

---

## 11. Local model support: native runtime details matter

### Observed

Cline officially supports local runtimes including Ollama and LM Studio.

A particularly important regression/fix occurred during the SDK migration. Commit `7f9d2e96d9bd21dae9a2626ad3f83f0d11b47e06` explains that Ollama had been routed through a generic OpenAI-compatible endpoint, which could not express Ollama's `options.num_ctx`. Models therefore loaded at Ollama's 4096-token server default, truncating Cline's prompt and breaking features.

Cline restored native Ollama routing, maps the configured context setting into the wire request, and uses a 32768 default because 4096 is insufficient for its prompts. The same configured value feeds UI/context-management budgeting.

Cline's model metadata also explicitly records capabilities such as tools, streaming, reasoning, images, structured output and token limits.

Primary sources:
- https://github.com/cline/cline/blob/main/docs/running-models-locally/overview.mdx
- https://github.com/cline/cline/commit/7f9d2e96d9bd21dae9a2626ad3f83f0d11b47e06
- https://github.com/cline/cline/blob/main/sdk/packages/shared/src/llms/model-info.ts

### ACL/Vera relevance

This is direct evidence against treating “OpenAI-compatible” as a sufficient local-runtime contract.

The same model can behave differently depending on:
- transport endpoint;
- server defaults;
- actual context allocation;
- tool-call parser;
- structured-output enforcement;
- streaming behavior;
- provider adapter.

ACL benchmarking should identify **model + runtime + adapter + settings**, not only model name.

**Confidence:** high.

---

## 12. Capability metadata: unknown must be an explicit policy choice

### Observed

Cline's `ModelInfo` has explicit capability metadata. However, current helpers intentionally treat missing/empty capability lists as unspecified and can assume tool/image support for backward compatibility/dynamic models.

The VS Code session factory contains comments/fixes around custom model capability projection, including avoiding accidental tool disablement when a dynamic custom model has no authoritative capability list.

Primary sources:
- https://github.com/cline/cline/blob/main/sdk/packages/shared/src/llms/model-info.ts
- https://github.com/cline/cline/blob/main/apps/vscode/src/sdk/cline-session-factory.ts

### ACL/Vera relevance

“Unknown” is not a technical fact; it is a policy state.

For low-risk UI features, optimistic defaulting may be fine. For ACL authority/tool use, unknown should normally trigger benchmark/probe/downgrade rather than silently become `supports_tools=true`.

Candidate ACL states:
- supported and verified;
- supported by upstream but not ACL-verified;
- unsupported;
- unknown;
- temporarily degraded due to runtime/version regression.

**Confidence:** high.

---

## 13. Context overflow: classify, shrink deterministically, retry once

### Observed

Commit `cdcaa744223465a9bf5beb4d5b5a5316d4a4ea65` added SDK context-overflow classification and recovery.

Important behaviors:
- provider errors are classified before flattening into generic strings;
- overflow triggers forced compaction even if token estimation was wrong;
- recovery uses a deterministic basic compaction path rather than depending on another LLM request;
- a custom compactor may be used only if its result is acceptable; fallback remains available;
- the runtime retries once per run;
- non-shrinking/empty/inadequate compaction results are rejected;
- telemetry records the error class and recovery mode;
- terminal cases fail with actionable messages instead of repeatedly resending a doomed request.

Primary source:
- https://github.com/cline/cline/commit/cdcaa744223465a9bf5beb4d5b5a5316d4a4ea65

### ACL/Vera relevance

This is a strong bounded-recovery pattern:

> Classify deterministic failure, transform state in a deterministic way, prove progress, spend a small bounded retry budget, then stop/escalate.

That is materially better for small local workers than a generic “try again N times” rule.

**Confidence:** high.

---

## 14. Compaction is part of state correctness, not merely token savings

### Observed

Recent Cline compaction fixes include:

- migrated legacy sessions ignored the historical truncation range and could restart with millions of tokens (`fed502e3...`);
- OpenAI-compatible compaction could hit the wrong provider endpoint and silently fall back to basic compaction (`fe75eb62...`);
- manual `/compact` could persist a sidecar/UI success while the model still received the un-compacted canonical transcript (`fe75eb62...`);
- provider/model context metadata could disagree with the real runtime budget;
- shallow sessions with very large output limits could truncate the first user task incorrectly (`be97d951...`);
- older large-file overflow behavior could enter repeat-failure loops when no shrinking occurred (#5251; historical evidence).

Primary sources:
- https://github.com/cline/cline/commit/fed502e3cf0de3d1a474258513df6e5e8842d389
- https://github.com/cline/cline/commit/fe75eb62715d61853f53a1ea2e0db04ee429f31f
- https://github.com/cline/cline/commit/be97d951fa34b2ab4ad42e88f424a37c3dcff6a5
- https://github.com/cline/cline/issues/5251

### ACL/Vera relevance

Compaction changes the worker's effective evidence. It therefore needs provenance and tests like any other state transformation.

ACL should distinguish:
- canonical transcript/evidence;
- provider-facing working context;
- compaction summary/derived context;
- omitted ranges;
- current file/workspace state;
- task/checkpoint state.

A UI saying “compacted” is not evidence that the model actually received the intended compacted state.

**Confidence:** high.

---

## 15. Abort/restart durability

### Observed

Commit `d011d049a13a04a58fb04d72666c35da6b4f1853` addressed sessions losing context after cancelling slow self-hosted requests and the hub subsequently restarting.

The root causes crossed layers:
- abort-family unhandled rejections could kill the shared hub daemon;
- aborted turns were not flushed to disk;
- lazy persistence could leave seeded history memory-only;
- recovery then reconstructed an empty session from disk.

The fix persisted aborted-turn transcript state and broadened abort-family handling so cancellation did not kill every resident session.

Primary source:
- https://github.com/cline/cline/commit/d011d049a13a04a58fb04d72666c35da6b4f1853

### ACL/Vera relevance

Cancellation is not an exception to persistence design. It is a normal lifecycle transition.

Candidate invariant:

> Before a run is considered safely stopped/recoverable, durable state must reflect every user-visible accepted input and every completed/uncertain side effect required for continuation.

A supervisor stopping a stuck local worker should not erase the evidence needed by the replacement worker.

**Confidence:** high.

---

## 16. Repeated mistakes and tool-loop detection

### Observed

Current agent execution types expose:
- `maxConsecutiveMistakes` (default documented as 6), covering API failures, invalid tool calls and iterations where every tool call fails;
- a host decision path that can continue with guidance or stop;
- repeated identical tool-call loop detection with configurable soft/hard thresholds;
- CLI defaults documented as soft threshold 3 and hard threshold 5;
- a soft intervention can inject recovery guidance; the hard threshold enters the mistake-limit decision path.

Primary source:
- https://github.com/cline/cline/blob/main/sdk/packages/shared/src/agents/types.ts

### ACL/Vera relevance

This is one of Cline's strongest alignments with the user's earlier ACL experiment.

Instead of forcing the model to obey many prompt-level decision rules, ACL can observe execution symptoms:
- same tool + same arguments repeated;
- consecutive invalid schema/tool calls;
- repeated command/file failure;
- repeated provider/runtime error;
- no progress between iterations.

Then the harness can:
1. warn/reframe;
2. downgrade/change tool strategy;
3. checkpoint/stop;
4. escalate to supervisor/review.

The model retains room to reason naturally until measurable failure behavior appears.

**Confidence:** high.

---

## 17. Parallel tool identity must use call IDs

### Observed

A historical Cline fix changed parallel tool-call tracking from tool name to `call_id`. Using tool name as the identity allowed two calls to the same tool in one turn to overwrite each other's tracking/results.

Current event types consistently expose `toolCallId` alongside tool name and agent/conversation metadata.

Primary sources:
- current event types: https://github.com/cline/cline/blob/main/sdk/packages/shared/src/agents/types.ts
- repository history around parallel tool-call tracking (observed during Task 6 commit review)

### ACL/Vera relevance

Tool names are classifications, not identities.

Every concurrent action needs an immutable call/effect ID. This becomes even more important with multiple workers, repeated file reads, parallel tests and parent/child delegation.

**Confidence:** high.

---

## 18. Sub-agents: separate context is useful; permission claims still need enforcement

### Observed

Cline's sub-agent documentation describes focused parallel agents with separate context/token budgets. It says sub-agents can read/search/list and run read-only commands, while edits, browser, MCP, web search and nested sub-agents are unavailable.

The same current command-guard source that supports Plan mode documents that shell mutation detection is incomplete. Therefore the documentation's “read-only commands” claim should be interpreted as intended capability/policy, not proof of OS-level read-only execution.

Primary sources:
- https://github.com/cline/cline/blob/main/docs/features/subagents.mdx
- https://github.com/cline/cline/blob/main/sdk/packages/core/src/extensions/tools/command-guard.ts

### ACL/Vera relevance

Useful mechanism candidates:
- isolated child context;
- explicit child tool set;
- separate usage/cost accounting;
- bounded child lifetime/budget;
- no recursive delegation by default.

But ACL should enforce child authority with real capability separation, not only shell-command classification.

**Confidence:** high.

---

## 19. Hooks are a stronger seam than prompt rules, but they inherit parser limitations

### Observed

Cline provides lifecycle hooks including pre-tool interception. Recent changes moved Plan-mode command blocking into a built-in `beforeTool` extension so it catches the SDK shell tool and host replacements consistently before normal approval.

The `.clineignore` migration similarly recommends a `PreToolUse` hook to cancel access instead of relying on context filtering.

Recent hook fixes also had to preserve tool-call identity when injecting hook context and sanitize hook-generated markup so one tool's context could not spoof another tool's identity.

Primary sources:
- https://github.com/cline/cline/commit/472f9c88c5fda6cc6c60e9e08e04fccbf905e487
- https://github.com/cline/cline/blob/main/docs/customization/clineignore.mdx
- https://github.com/cline/cline/commit/8fe5a196c486ecf84cf730bb37994a0d01746f2b

### ACL/Vera relevance

Hooks are an attractive ACL extension point for:
- policy checks;
- audit/evidence capture;
- secret redaction;
- validation;
- approval escalation;
- checkpoint/effect recording.

However, a hook can only enforce what it can parse and what all execution paths actually pass through. Hook policy must therefore be paired with capability confinement and tests proving no bypass path exists.

**Confidence:** high.

---

## 20. Telemetry: measure the trajectory, not only task completion

### Observed

Cline core telemetry defines explicit events for:
- session start/end;
- task created/restarted/completed;
- conversation turns;
- token usage;
- mode changes;
- tool use;
- diff-edit failure;
- provider API/stream failures;
- mistake-limit reached;
- sub-agent/team creation and completion;
- compaction execution/skips/emergency budgets;
- tool timeout;
- Plan-mode command blocks;
- workspace initialization/path resolution.

Telemetry identity fields can include agent, conversation, parent, team, run, iteration and tool-call IDs.

Primary source:
- https://github.com/cline/cline/blob/main/sdk/packages/core/src/services/telemetry/core-events.ts

### ACL/Vera relevance

This strongly supports the user's desire for a visual monitor and measurable worker success.

ACL's eventual GUI should be backed by events rather than scraping model text. Candidate metrics:
- current lifecycle state;
- run/iteration/tool-call count;
- tool success/failure by category;
- repeat-loop/mistake interventions;
- checkpoint latency/failure;
- compaction events and before/after context size;
- provider/runtime error class;
- token/cost/latency;
- escalation/review count;
- child-agent lineage and budgets;
- validation results.

### Warning

Operational telemetry is not automatically an evaluation system. ACL still needs deterministic task fixtures and success criteria; Cline telemetry mainly demonstrates the evidence substrate.

**Confidence:** high.

---

## 21. Long-running telemetry/storage must have physical retention controls

### Observed

Issue #13580 reports a Cline hub event SQLite database growing to about 40 GB after months of usage. The report found logical row retention but no file-space reclamation (`VACUUM`/incremental vacuum), so the SQLite file retained its high-water allocation.

Primary source:
- https://github.com/cline/cline/issues/13580

### ACL/Vera relevance

For ten-hour/day or continuous workers, “we delete old rows” is not the same as “storage is bounded.”

ACL should define:
- logical retention;
- physical disk bound;
- WAL/checkpoint policy;
- compaction/vacuum policy;
- artifact retention by severity/value;
- max storage per project/run;
- archive/export rules.

**Confidence:** medium-high; issue evidence is user-reported but the described SQLite behavior is technically coherent and directly inspectable.

---

## 22. Checkpoints and side-effect evidence should remain separate

### Observed

Cline checkpoints are primarily workspace/history recovery mechanisms. Cline can also run arbitrary commands and interact with external systems.

### Inference for ACL

A safe ACL recovery model likely needs at least three separate records:

1. **conversation/context state** — what the model knew/saw;
2. **workspace snapshot** — filesystem/Git state;
3. **external-effect ledger** — commands/API calls/actions that may have changed state outside the workspace, including uncertain-after-crash effects.

No one of these substitutes for the other two.

This is an inference derived from Cline checkpoint scope plus the Task 5 persistence findings; it is not a claim that Cline promises to solve all three.

**Confidence:** high as an ACL design hypothesis; requires later cross-project validation.

---

## 23. What appears reusable as a mechanism

These are **research candidates**, not adoption decisions.

### High-value candidates

#### A. Stateless agent / stateful core split
Keep provider/model loop replaceable while project/session/persistence authority remains deterministic.

#### B. Runtime interception before tool execution
Use hooks/policy seams for observable enforcement rather than embedding every rule in the prompt.

#### C. Explicit mistake and loop detection
Detect measurable failure behavior and escalate without micromanaging the model's reasoning.

#### D. Durable workspace checkpoint identity
Use one semantic turn/run model across retries, compaction and restart; protect restore with preconditions and CAS.

#### E. Model + runtime capability records
Treat context, tools, media, structured output and provider operations as explicit capabilities with verified/unknown states.

#### F. Native local-runtime adapters where wire semantics differ
Do not force every local backend through a generic OpenAI-compatible adapter when backend-specific controls matter.

#### G. Event/telemetry identity graph
Emit structured lifecycle/tool/provider/compaction events carrying stable session/agent/run/tool-call identifiers.

#### H. Context-overflow recovery with progress proof
Classify, deterministically shrink, verify shrinkage, retry once, then stop/escalate.

---

## 24. What should not be copied blindly

### A. Model-supplied command approval classification as a final gate
Useful signal; insufficient authority boundary.

### B. Permissive default for unlisted SDK tools
Convenient for SDK users; contrary to ACL's likely least-authority extension posture.

### C. Shell blacklist as read-only isolation
Useful workflow guard; explicitly incomplete.

### D. Workspace checkpoints as universal rollback
They cannot undo arbitrary external side effects.

### E. Unknown capability => optimistic support for privileged features
Compatibility-friendly but risky for local autonomous workers.

### F. Layering another agent runtime without one clear tool-authority owner
The Claude Code provider issue demonstrates the ambiguity this can create.

### G. Persistence on the critical path without performance/storage budgets
Checkpoint and event-log issues show the operational cost.

---

## 25. Failure surfaces that deserve ACL regression fixtures later

When ACL reaches implementation/benchmark work, Cline suggests concrete tests:

1. **Planner shell bypass** — try Python/PowerShell/quoted shell write paths while planner is read-only.
2. **Existing-file create** — “Add File” must not overwrite an existing target.
3. **Concurrent file change** — preview/read then external modification before write.
4. **Checkpoint after retry/internal continuation** — restore should map to the correct user-visible task turn.
5. **Checkpoint after compaction** — turn identity and workspace checkpoint remain aligned.
6. **Checkpoint across process restart** — no in-memory-only counter may redefine existing snapshots.
7. **Untracked file restore** — define and verify exact semantics.
8. **User commit after checkpoint** — restore refuses rather than orphaning commit history.
9. **Restore race** — branch changes after validation but before restore must fail closed.
10. **Local Ollama context mismatch** — configured context must reach the actual backend wire setting.
11. **Repeated identical tool call** — soft intervention then hard escalation.
12. **Overflow recovery** — same doomed request is not resent forever.
13. **Abort during slow local stream** — accepted transcript survives supervisor stop/restart.
14. **Unknown tool capability** — ACL chooses explicit downgrade/probe rather than implicit privileged support.
15. **Embedded worker provider** — native tools cannot escape outer authority/telemetry/checkpoint policy unnoticed.
16. **Telemetry retention** — long run cannot grow storage without a physical bound.

These are candidate fixtures, not implementation work authorized by this research branch.

---

## 26. Direct relation to the user's earlier ACL experiment

The user's earlier small-context harness became overconstrained because many rules and forced decision limits consumed context and pushed the local model toward guessing.

Cline supplies independent evidence for a different approach:

- model instructions describe intent;
- structured tool interfaces describe available actions;
- runtime hooks enforce selected policy;
- capability grants remove inaccessible actions entirely;
- mistake/loop detectors react to measurable execution failure;
- checkpoint/persistence layers record reality;
- telemetry lets a supervisor/GUI observe behavior.

This allows the local model to spend more of its context budget solving the task rather than simulating a policy engine in prose.

This is an **ACL inference**, not a claim that Cline itself was designed around the user's experiment.

---

## 27. Cline versus later comparison — deliberately deferred

This task does not decide:

- Cline vs Pydantic AI;
- Cline vs LangGraph;
- whether ACL should import `@cline/core`;
- whether ACL should fork Cline;
- whether Cline should become the ACL worker harness;
- whether the separate Cline Kanban project maps to ACL backlog/orchestration needs;
- whether Cline's team-agent implementation should replace ACL's planned planner/worker structure.

Those questions require evidence from the remaining Tier-A projects and later component-by-component comparison.

---

## 28. Current open questions worth carrying forward

1. Can a later framework provide durable task/checkpoint semantics without coupling recovery to the user's Git branch?
2. Which project has the clearest external-side-effect/idempotency model?
3. How should ACL express read-only authority so shell access cannot reintroduce writes?
4. Which model/runtime capability system best represents empirically verified local behavior rather than catalog assumptions?
5. Can telemetry/event schemas from current projects converge enough that ACL avoids inventing incompatible terms?
6. Which project provides the strongest default-deny plugin/tool composition?
7. How should ACL preserve canonical evidence while giving small models aggressively compact working context?
8. What is the correct process boundary for running model-generated code on the user's machine?

These should inform later project research without changing the queue now.

---

## 29. Overall research judgment

**Research value:** very high.  
**Maintenance signal:** high.  
**Interface stability:** mixed / rapidly evolving SDK and host architecture.  
**Local-model relevance:** high.  
**Authority/security completeness:** useful layered controls, but multiple current mechanisms explicitly remain workflow guards rather than hard security isolation.  
**Checkpoint/recovery relevance:** very high.  
**Observability relevance:** high.  
**Immediate adoption recommendation:** intentionally not made.

Cline validates several ACL directions while also showing where superficially reasonable designs break under real use. The strongest takeaway is architectural:

> Keep model freedom and operational authority separate. Let the model choose how to solve the bounded task; let the harness own what the worker can actually do, how failures are classified, what state is durable, and when progress is safe enough to continue.

That principle should remain a hypothesis until the remaining ranked projects are researched.

---

## Primary evidence index

Architecture / status:
- https://github.com/cline/cline
- https://github.com/cline/cline/blob/main/README.md
- https://github.com/cline/cline/blob/main/sdk/ARCHITECTURE.md
- https://github.com/cline/cline/blob/main/sdk/packages/core/package.json

Permissions / authority:
- https://github.com/cline/cline/blob/main/docs/features/auto-approve.mdx
- https://github.com/cline/cline/blob/main/docs/sdk/guides/permission-handling.mdx
- https://github.com/cline/cline/blob/main/apps/vscode/src/sdk/sdk-tool-policies.ts
- https://github.com/cline/cline/commit/472f9c88c5fda6cc6c60e9e08e04fccbf905e487
- https://github.com/cline/cline/blob/main/sdk/packages/core/src/extensions/tools/command-guard.ts
- https://github.com/cline/cline/issues/13586
- https://github.com/cline/cline/issues/13146
- https://github.com/cline/cline/blob/main/docs/customization/clineignore.mdx

File/edit safety:
- https://github.com/cline/cline/blob/main/sdk/packages/core/src/extensions/tools/executors/apply-patch.ts
- https://github.com/cline/cline/commit/adbfbd97d352c82f7001273365f6a4bac38b5adb

Checkpoint/recovery:
- https://github.com/cline/cline/blob/main/docs/core-workflows/checkpoints.mdx
- https://github.com/cline/cline/commit/8d078f59bdb63f3d80a7e71668fe2f4066002c44
- https://github.com/cline/cline/issues/13550
- https://github.com/cline/cline/commit/89c2efa970a115d0815942e4eb69f1a74f9d3b5e
- https://github.com/cline/cline/issues/13131
- https://github.com/cline/cline/commit/d011d049a13a04a58fb04d72666c35da6b4f1853

Local models / context:
- https://github.com/cline/cline/blob/main/docs/running-models-locally/overview.mdx
- https://github.com/cline/cline/blob/main/sdk/packages/shared/src/llms/model-info.ts
- https://github.com/cline/cline/blob/main/apps/vscode/src/sdk/cline-session-factory.ts
- https://github.com/cline/cline/commit/7f9d2e96d9bd21dae9a2626ad3f83f0d11b47e06
- https://github.com/cline/cline/commit/cdcaa744223465a9bf5beb4d5b5a5316d4a4ea65
- https://github.com/cline/cline/commit/fed502e3cf0de3d1a474258513df6e5e8842d389
- https://github.com/cline/cline/commit/fe75eb62715d61853f53a1ea2e0db04ee429f31f
- https://github.com/cline/cline/commit/be97d951fa34b2ab4ad42e88f424a37c3dcff6a5

Loops / sub-agents / telemetry:
- https://github.com/cline/cline/blob/main/sdk/packages/shared/src/agents/types.ts
- https://github.com/cline/cline/blob/main/docs/features/subagents.mdx
- https://github.com/cline/cline/blob/main/sdk/packages/core/src/services/telemetry/core-events.ts
- https://github.com/cline/cline/issues/13580

## Stop boundary

Cline deep research ends here. No LangGraph deep research, cross-project winner selection, dependency/fork decision, ACL/Vera runtime change or worker/model execution was begun.