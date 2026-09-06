# Failed, Abandoned, and Heavily Redesigned Agent Attempts — Task 4

**Accessed:** 2026-09-05  
**Task:** Find failed, abandoned, or heavily redesigned attempts relevant to ACL and future Vera work.  
**Status:** complete; historical/transition research only. No individual ranked-project deep research was begun.

## Method and classification rules

This task does **not** treat low activity, a repository move, a rename, or an unpopular design as proof of failure. A project is classified only when primary evidence supports one of the following:

- **maintenance-only / superseded** — upstream explicitly says new feature development has stopped and points to a successor;
- **unsupported / deprecated legacy** — upstream says the implementation is no longer supported or security-maintained;
- **archived / abandoned repository** — the canonical repository is archived/read-only or upstream explicitly says it is no longer maintained;
- **heavily redesigned** — upstream explicitly describes a ground-up rewrite, complete redesign, or a materially different successor architecture;
- **status unresolved** — activity has stalled, but there is no authoritative statement sufficient to classify the project.

Observed status and architecture changes are separated from inferred causes. Where maintainers do not explain *why* a project stopped, this file does not invent a reason.

## High-value transition cases

### 1. Microsoft AutoGen → AutoGen 0.4 rewrite → Microsoft Agent Framework

**Classification:** heavily redesigned, then maintenance-only / superseded.

**Observed facts**
- AutoGen's v0.2→v0.4 migration guide says v0.4 was a **from-the-ground-up rewrite** using an asynchronous, event-driven architecture.
- Microsoft states that the rewrite was intended to address **observability, flexibility, interactive control, and scale**.
- The v0.4 redesign introduced a layered Core / AgentChat / Extensions model and replaced v0.2 APIs with breaking changes.
- The current `microsoft/autogen` README says AutoGen is now in **maintenance mode**, will receive no new features/enhancements, is community managed, and new users should use **Microsoft Agent Framework**. Existing users are directed to a migration guide.
- Microsoft describes Agent Framework as AutoGen's enterprise-ready successor with long-term support.

**Primary sources**
- https://github.com/microsoft/autogen
- https://microsoft.github.io/autogen/0.4.4/user-guide/agentchat-user-guide/migration-guide.html
- https://microsoft.github.io/autogen/0.2/blog/2024/10/02/new-autogen-architecture-preview/
- https://github.com/microsoft/autogen/discussions/7066
- https://github.com/microsoft/agent-framework

**ACL/Vera lesson**
- The transition is direct evidence that multi-agent abstractions that work for experimentation can still require a runtime-level redesign once **observability, cancellation/control, modularity, and scale** become first-class requirements.
- Centralized/event-driven runtime mechanics can make message flow easier to observe and debug than loosely coupled agent-to-agent conversations.
- A migration can preserve concepts while breaking APIs. ACL should later evaluate behavior and evidence across migrations, not assume source-code compatibility equals semantic compatibility.

**Warning**
- This is not evidence that “multi-agent systems failed.” AutoGen remained influential and its ideas continued into successor architectures. The supported conclusion is that the original architecture was materially redesigned and later superseded.

---

### 2. SWE-agent → SWE-agent 1.0 rewrite → mini-SWE-agent

**Classification:** heavily redesigned, then maintenance-only / superseded.

**Observed facts**
- SWE-agent's 1.0 migration documentation says the codebase was **nearly rewritten from scratch** and moved execution into the separate SWE-ReX backend.
- Current SWE-agent documentation says **mini-swe-agent has superseded SWE-agent**, most current development effort is on mini-swe-agent, and SWE-agent is now **maintenance-only**.
- mini-swe-agent deliberately removes most scaffold complexity: one Bash tool, independent `subprocess` actions instead of a persistent stateful shell, and a linear message history.
- The mini-swe-agent maintainers explicitly describe independent subprocess execution as important for stability and position the project as radically simpler while retaining comparable performance.
- Current mini-swe-agent issues also show that simplification does **not** remove lifecycle engineering: examples include child processes surviving command timeouts, provider streams stalling within bounded runs, and shell/platform assumptions causing failures.

**Primary sources**
- https://swe-agent.com/latest/
- https://swe-agent.com/latest/installation/migration/
- https://mini-swe-agent.com/latest/faq/
- https://github.com/SWE-agent/mini-swe-agent
- https://github.com/SWE-agent/mini-swe-agent/issues/826
- https://github.com/SWE-agent/mini-swe-agent/issues/874

**ACL/Vera lesson**
- **Scaffold complexity must continuously justify itself.** A sophisticated harness can become a research artifact that obscures model behavior or creates more failure surfaces than it removes.
- Separating execution into a dedicated runtime is a recurring design move worth studying later.
- Stateless/independent action execution can improve reproducibility and recovery compared with opaque long-lived shell state.
- Minimal control flow still needs explicit process trees, timeouts, cancellation, provider-stream bounds, and platform semantics.

**Watchlist implication**
- Task 3 ranked SWE-agent at #8. That entry should now be treated as a **transition-aware historical slot**: when reached, later research should study the SWE-agent→mini-swe-agent redesign and the current mini-swe-agent implementation rather than treating legacy SWE-agent as the current endpoint.

---

### 3. OpenAI Swarm → OpenAI Agents SDK

**Classification:** experimental predecessor explicitly replaced by a production successor.

**Observed facts**
- Swarm's upstream README describes it as **experimental and educational**, not intended for production, and says it has been **replaced by the OpenAI Agents SDK**.
- The Agents SDK documentation calls itself a **production-ready upgrade** of Swarm.
- The successor retains a small primitive set—agents, handoffs/agents-as-tools, tools, and guardrails—while adding production-oriented capabilities such as tracing and broader lifecycle/runtime support.

**Primary sources**
- https://github.com/openai/swarm
- https://github.com/openai/openai-agents-python
- https://github.com/openai/openai-agents-python/blob/main/docs/index.md

**ACL/Vera lesson**
- Experimental repositories should be treated as **pattern demonstrations**, not automatically as production dependencies.
- A good prototype can survive by carrying forward its simplest abstractions while adding the operational concerns omitted from the experiment.
- Early project labels such as “experimental,” “educational,” and “no official support” are meaningful lifecycle metadata and should not be ignored because the repository is popular.

**Warning**
- `openai/swarm` is not GitHub-archived, demonstrating that the GitHub archive flag alone is insufficient to determine whether upstream considers a project current.

---

### 4. AutoGPT Classic → AutoGPT Platform

**Classification:** unsupported legacy experiment replaced by a materially different maintained platform.

**Observed facts**
- AutoGPT's own Classic README says Classic was an **experimental project**, its initial research phase has concluded, it is **unsupported**, and its dependencies will not be updated.
- The AutoGPT security policy explicitly excludes the Classic folder from security support and warns that the legacy code has known vulnerabilities/dependency issues.
- The maintained AutoGPT Platform describes agents as explicit **workflows** assembled from blocks, with deployment controls, triggers, monitoring, and analytics.
- Classic was centered on an autonomous model loop that decomposed goals, selected actions, and chained tasks; the current maintained platform is substantially more explicit and workflow-oriented.

**Primary sources**
- https://github.com/Significant-Gravitas/AutoGPT/blob/master/classic/README.md
- https://github.com/Significant-Gravitas/AutoGPT/blob/master/SECURITY.md
- https://github.com/Significant-Gravitas/AutoGPT
- https://github.com/Significant-Gravitas/AutoGPT/blob/master/docs/content/index.md

**ACL/Vera lesson**
- A research demonstration of open-ended autonomy is not automatically an operational architecture.
- The maintained successor's emphasis on explicit blocks, workflows, lifecycle controls, and monitoring is a useful counterpoint to “let the model keep deciding what to do next.”
- Unsupported legacy agent code should be treated as historical evidence, not a dependency candidate, even if the project name remains active elsewhere in the same repository.

**Causal boundary**
- Upstream clearly documents the architectural shift but does not establish one single reason for it. This task does not claim that Classic was replaced *because* free-form autonomy failed.

---

### 5. Original BabyAGI → archived snapshot → self-building function framework

**Classification:** original architecture archived; project materially reconceived.

**Observed facts**
- The current BabyAGI README says the original March 2023 task-planning project was archived into `babyagi_archive` as a September 2024 snapshot.
- The current project explicitly says earlier attempts to expand BabyAGI led to the conclusion that the optimal path was **“the simplest thing that can build itself.”**
- The new architecture centers on a function framework that stores, manages, executes, and tracks function dependencies, authentication secrets, and logs rather than simply expanding the original task-generation/prioritization loop.
- Upstream also cautions that the project is experimental and not intended for production use.

**Primary sources**
- https://github.com/yoheinakajima/babyagi
- https://github.com/yoheinakajima/babyagi_archive

**ACL/Vera lesson**
- This is unusually explicit maintainer evidence that **adding more machinery to an autonomous loop can lead back toward simplification**.
- Self-modifying/self-building systems move risk into function provenance, dependency tracking, secret handling, mutation history, and rollback. Those boundaries matter more than the novelty of recursive self-extension.
- Keeping an immutable historical snapshot is valuable for comparing redesigns without rewriting project history.

---

### 6. GPT-Engineer → archived research CLI → Lovable / managed product direction

**Classification:** archived open-source experiment with an explicit product evolution.

**Observed facts**
- `AntonOsika/gpt-engineer` was archived by its owner on **2026-04-22** and is read-only.
- Its README calls it the original code-generation experimentation platform and identifies it as a **precursor to Lovable** / the managed `gptengineer.app` direction.
- The README points users who want a maintained hackable CLI to Aider rather than claiming the original CLI remains the maintained path.

**Primary sources**
- https://github.com/AntonOsika/gpt-engineer
- https://github.com/AntonOsika/gpt-engineer/blob/main/README.md

**ACL/Vera lesson**
- Open research tooling and a later commercial/product architecture can diverge. A successful product evolution does not guarantee the original open harness remains maintained.
- ACL should later evaluate **maintainer continuity and ownership of critical infrastructure**, not only technical capability.
- Historical code can remain valuable for design comparison even when it is no longer a viable dependency.

**Causal boundary**
- Archival and successor/product direction are documented; this task does not infer that the CLI was archived because of a specific technical failure.

---

### 7. GPT Pilot → unmaintained repository → prolonged supply-chain compromise

**Classification:** explicitly unmaintained; severe maintenance/security failure.

**Observed facts**
- GPT Pilot's README says the repository is **not being maintained anymore** and directs users toward Pythagora.
- Upstream reports that a malicious commit pushed on **2025-08-24** inserted a credential-stealing supply-chain worm into `core/telemetry/`.
- The malicious code remained until an external report in June 2026; files were removed on **2026-06-11**.
- The README explicitly says the repository was no longer actively maintained, **which is why the malicious commit went unnoticed for an extended period**.
- The repository itself is not GitHub-archived, again showing that archive state is not a complete maintenance signal.

**Primary source**
- https://github.com/Pythagora-io/gpt-pilot/blob/main/README.md

**ACL/Vera lesson**
- **Maintenance status is a security boundary.** Previously trusted agent code cannot remain implicitly trusted after maintainership lapses.
- Agent systems are especially sensitive because they routinely hold API keys, Git credentials, cloud credentials, SSH keys, and permission to execute code.
- Later ACL dependency governance should consider provenance, pinned versions/commits, security advisories, maintainer activity, and an explicit policy for retiring or quarantining stale dependencies.
- Repository inactivity can be more dangerous than a simple broken build: stale privileged code can become a supply-chain foothold.

**Warning**
- This finding is about the documented repository compromise and maintenance lapse; it does not attribute the malicious commit to the legitimate maintainers.

---

### 8. AgentGPT → archived repository with no documented successor cause

**Classification:** archived / abandoned repository; cause unresolved.

**Observed facts**
- `reworkd/AgentGPT` was archived by the owner on **2026-01-28** and is read-only.
- Main-branch activity had already largely stopped in 2025.
- A May 2025 community discussion reported outdated Docker/dependency behavior and asked whether Reworkd had stopped maintaining the project; it received no maintainer response.
- Open issues remained when the repository was archived.

**Primary sources**
- https://github.com/reworkd/AgentGPT
- https://github.com/reworkd/AgentGPT/activity
- https://github.com/reworkd/AgentGPT/discussions/1669

**ACL/Vera lesson**
- An archive flag can establish that the repository is no longer an active development target, but **it does not explain the cause**.
- Stale infrastructure/dependencies can make an otherwise conceptually interesting agent unusable before model quality is even relevant.
- Historical projects should not be reverse-engineered into a narrative of failure unless maintainers or artifacts support that narrative.

---

## Status unresolved: Aider

**Classification:** unresolved; do not call abandoned.

**Observed facts**
- `Aider-AI/aider` is **not archived**.
- The latest canonical repository activity observed in the campaign remains **2026-05-22**.
- An August 28, 2026 community issue asks whether the project is feature-complete, unmaintained, or awaiting a maintainer and notes a growing issue/PR backlog. It is not an authoritative maintainer declaration.
- Community forks such as `aider-ce` are active and explicitly describe themselves as community-driven continuations/experimentation, but no primary source establishes one as Aider's official successor.

**Primary / discovery sources**
- https://github.com/Aider-AI/aider
- https://github.com/Aider-AI/aider/issues/5647
- https://github.com/ErichBSchulz/aider-ce

**ACL/Vera lesson**
- **Silence is not classification evidence.** A stalled commit stream plus community concern is an early-warning signal, not proof of abandonment.
- Fork activity is useful discovery evidence for unmet maintenance demand, but canonical/successor status must be established independently.

**Follow-up**
- Recheck only if an authoritative maintainer statement, release, archive action, ownership transfer, or canonical successor appears. Do not consume project-deep-research time speculating about personal circumstances.

---

## Explicit non-failure transitions / false-positive controls

### OpenDevin → OpenHands
- OpenHands explicitly identifies itself as formerly OpenDevin and remains actively maintained.
- An old OpenDevin fork can be stale while the canonical OpenHands project is current.
- **Lesson:** a rename or canonical-repository move is not abandonment.

Primary sources:
- https://github.com/OpenHands/OpenHands
- https://github.com/OpenHands/OpenHands/issues/8797

### Block Goose → AAIF Goose
- Goose moved from `block/goose` to `aaif-goose/goose` under the Agentic AI Foundation / Linux Foundation and remains actively developed.
- Goose publishes current roadmaps and governance and describes the move as strengthening neutral long-term stewardship.
- **Lesson:** organizational migration can be a continuity/stewardship improvement rather than a project failure.

Primary sources:
- https://github.com/aaif-goose/goose
- https://github.com/aaif-goose/goose/discussions/7709
- https://github.com/aaif-goose/goose/blob/main/GOVERNANCE.md

These controls reinforce the Task 2 rule: track canonical project identity separately from repository paths and organization names.

## Cross-cutting failure/redesign lessons for ACL and Vera

### 1. Complexity repeatedly gets cut back
AutoGen and SWE-agent both underwent major rewrites; SWE-agent then moved to an even smaller successor. BabyAGI explicitly describes simplification as the lesson from earlier expansion. The recurring signal is not “always use a tiny harness,” but **every layer of agent-specific machinery should have measurable value and a clear owner**.

### 2. Runtime mechanics outlive prompt cleverness
The strongest redesign reasons are operational: observability, cancellation, interactive control, scale, process lifecycle, state handling, and execution isolation. These are harness/runtime responsibilities that prompts cannot reliably substitute for.

### 3. Free-form autonomy and production automation are different products
AutoGPT's maintained direction emphasizes blocks, workflows, deployment, monitoring, and controlled triggers. Swarm's successor adds guardrails and tracing. The recurring operational move is toward **explicit boundaries around when and how autonomy runs**.

### 4. Minimalism does not remove failure handling
mini-swe-agent demonstrates that even a one-tool, linear-history scaffold still needs correct timeout propagation, child-process cleanup, provider-stream deadlines, and cross-platform shell semantics. ACL should not confuse a small codebase with a complete reliability model.

### 5. Maintenance state belongs in the trust model
GPT Pilot provides direct evidence that privileged stale agent code can become a supply-chain risk. `archived=false` is not enough. Trust needs a broader maintenance/provenance signal.

### 6. Successor migrations need behavioral evidence
AutoGen's breaking rewrite and successor migration show why later ACL comparisons should preserve pinned tasks, models, tools, environment, outputs, failures, and limits before/after a framework change. “The app still starts” is not sufficient proof that agent behavior was preserved.

### 7. Separate project identity from architecture identity
OpenDevin→OpenHands and Block→AAIF Goose are continuity events, while AutoGPT Classic→Platform and BabyAGI's rewrite are architecture changes. A research catalog should track aliases, successors, and architecture generations separately.

### 8. Archive the experiment; do not silently mutate history
BabyAGI's archived snapshot is a useful model: preserve the old design so later researchers can compare what changed. ACL's own experiments should likewise remain reproducible rather than being overwritten by the latest architecture.

## Questions this task leaves for later work

These are **not** answered here because they belong to later project/security/deep-research tasks:

- Which specific components from the successors should ACL reuse versus reimplement?
- How well do Pydantic AI, Cline, LangGraph, Strands, Codex, OpenHands, mini-swe-agent, or Agents SDK behave with ACL's local models under controlled benchmarks?
- Which lifecycle/security lessons should become formal ACL governance invariants?
- Which memory architectures remain safe under poisoning, rollback, multi-user scope, and long-lived identity requirements?
- What collaboration or contribution opportunities exist with current maintainers?

## Diminishing-return stop condition

The search stopped after multiple independent architecture families produced the same high-value patterns and additional candidates were either weakly documented, still active, or would require speculative cause analysis. The evidence set includes:

- explicit ground-up rewrites;
- explicit maintenance-only/successor declarations;
- unsupported legacy code;
- archived repositories;
- an explicit simplification-driven redesign;
- a documented maintenance-related supply-chain incident;
- an unresolved-status control; and
- rename/organization-move controls that should **not** be mislabeled failures.

Further broad discovery is unlikely to change the cross-cutting lessons enough to justify beginning another historical-project lane during this task.

## Stop boundary

Task 4 ends with this transition/failure map, catalog/watchlist updates, and the next-task state update. It does **not** start the ranked project-by-project deep-research queue, change ACL governance or runtime code, run workers/models, recommend adoption, or begin collaboration analysis.
