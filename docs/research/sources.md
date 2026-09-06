# Source Map

Task 1 landscape mapping completed 2026-09-05. This file catalogs recurring places worth watching for ACL and future Vera work. It ranks **source channels**, not individual agent projects or people; project/person ranking belongs to later tasks.

## Selection criteria

A recurring source is high value when it:
- publishes new material often enough to justify watching;
- exposes primary evidence, reproducible artifacts, or clearly sourced analysis;
- maps directly to ACL/Vera concerns: coding agents, harnesses, local models, tool contracts, long-running execution, recovery, observability, memory, permissions, and agent security;
- has stable URLs, changelogs, version history, machine-readable data, or other features that make findings auditable;
- provides enough signal to justify the review cost.

## Evidence ladder

Use sources in this order:

1. **Discovery signal** — a feed, forum, paper index, leaderboard change, advisory, issue, or discussion reveals something worth checking.
2. **Primary verification** — follow the signal to the upstream repository, specification, paper, release notes, issue/PR, benchmark methodology, advisory, or standards body.
3. **Corroboration** — for consequential claims, compare an independent benchmark, standard, reproduced result, or second primary source.
4. **Catalog** — record the evidence, date, relevance, warning/caveat, confidence, and follow-up question in `catalog.jsonl`.

Community posts are leads unless they contain reproducible artifacts that can be independently checked.

## Tier A — core recurring watch sources

### 1. Upstream GitHub repositories

**Watch:** releases/tags/changelogs first; security advisories; then targeted issues, discussions, pull requests, and maintainer decisions.

**Cadence:** weekly digest plus event-driven checks when ACL is evaluating or using a project.

**Why it matters:** implementation decisions, regressions, breaking changes, recovery behavior, permission models, and real failure reports usually appear upstream before they are summarized elsewhere. The current seed project list in `watchlist.md` remains intentionally unranked until the next task.

**Noise control:** do not watch every commit or every issue globally. Prefer releases/changelogs and narrow searches around ACL questions.

Stable entry point: https://github.com/

### 2. arXiv recent feeds: Software Engineering, Multiagent Systems, Cryptography and Security

**Watch:**
- https://arxiv.org/list/cs.SE/recent
- https://arxiv.org/list/cs.MA/recent
- https://arxiv.org/list/cs.CR/recent
- use cs.AI as an overflow/search category when a relevant paper is cross-listed.

**Cadence:** scan two or three times per week; save only papers matching the research questions.

**Evidence:** on 2026-09-05 the current cs.SE feed contained work on software-engineering agents, harness engineering, trajectory-aware agent evaluation, long-horizon training, vulnerability-patching agents, and agent-harness evolution. The same-day cs.MA and cs.CR feeds contained agent reliability/monitoring and AI-agent security work.

**Search terms:** `agent`, `coding agent`, `software engineering agent`, `harness`, `tool use`, `function calling`, `long horizon`, `checkpoint`, `recovery`, `memory`, `multi-agent`, `prompt injection`, `sandbox`, `permission`, `security`.

**Warning:** arXiv is a preprint/discovery stream, not a quality guarantee. Verify methods and artifacts before adopting conclusions.

### 3. Hugging Face model and paper discovery

**Watch:**
- function-calling model filter: https://huggingface.co/models?other=function-calling
- Daily Papers: https://huggingface.co/papers
- model cards/discussions only after a model becomes relevant.

**Cadence:** two or three times per week during active local-model evaluation; otherwise weekly.

**Evidence:** the function-calling filter showed 2,360 tagged models when checked on 2026-09-05 and exposes runtime/ecosystem links including llama.cpp, vLLM, Ollama, MLX, and others. Daily Papers provides daily/weekly/monthly views and currently surfaces agent-training and terminal-agent research.

**Warning:** model tags, likes, downloads, and trending rank are discovery metadata, not proof of reliable tool calling. Any candidate still needs ACL-owned benchmark evidence and upstream runtime verification.

### 4. Coding-agent and tool-use benchmarks

**Watch:**
- SWE-bench official leaderboards/news: https://www.swebench.com/
- Berkeley Function Calling Leaderboard (BFCL) and changelog: https://gorilla.cs.berkeley.edu/leaderboard.html

**Cadence:** weekly during model/harness selection; otherwise on benchmark/changelog updates.

**Evidence:** SWE-bench maintains multiple official benchmark views (Verified, Multimodal, Multilingual, Lite, Full), identifies open-weight entries, and reports `% Resolved`. BFCL V4 explicitly evaluates function/tool calling, distinguishes native function calling from prompt workarounds, publishes reproducibility information, and states that it is updated periodically.

**Why it matters:** SWE-bench provides an external signal for coding-agent capability; BFCL is a stronger recurring signal for structured tool contracts and function-calling behavior.

**Warning:** leaderboard performance is not ACL reliability. Benchmark contamination, harness differences, cost/context assumptions, and task mismatch must be checked before using scores to select a worker.

### 5. OWASP GenAI and Agentic Security Initiative

**Watch:**
- https://genai.owasp.org/
- https://genai.owasp.org/initiatives/agentic-security-initiative/

**Cadence:** weekly news/resource scan; monthly review for new standards, threat work, guides, and landscape reports.

**Evidence:** OWASP maintains recurring GenAI resources, a newsletter covering tools/threat intelligence/initiatives, an Agentic Security Initiative focused on autonomous agents and multi-step workflows, current 2026 agent-security guidance, secure MCP material, an Agent Control Standard, and an open weekly working-group meeting.

**Why it matters:** this is a high-signal source for prompt injection, tool abuse, memory/context poisoning, approval/authority problems, multi-agent risk, MCP security, and governance boundaries relevant to both ACL and Vera.

### 6. MITRE ATLAS data

**Watch:** https://github.com/mitre-atlas/atlas-data

**Cadence:** monthly.

**Evidence:** the official ATLAS data repository states that ATLAS releases monthly content updates and publishes versioned, machine-readable tactics, techniques, mitigations, relationships, and case studies.

**Why it matters:** ATLAS gives ACL/Vera a stable adversarial taxonomy that can later be mapped to threat models, tests, and security gates.

### 7. Open-source vulnerability feeds: GitHub Advisory Database and OSV

**Watch:**
- https://github.com/advisories
- https://osv.dev/

**Cadence:** weekly landscape review now; later, package-specific monitoring whenever ACL adopts dependencies.

**Evidence:** GitHub Advisory Database is searchable/filterable across reviewed advisories, CVEs, ecosystems, and severity. During this task its newest entries included vulnerabilities in AI/runtime software, showing that the feed can surface agent-stack risks quickly. OSV aggregates multiple vulnerability databases in a machine-readable schema and supports queries by package version or commit.

**Why it matters:** once ACL's dependency set is known, these become direct early-warning sources for runtime, parser, web, sandbox, and agent-tool dependencies.

**Warning:** vulnerability feeds identify affected software; they do not by themselves show whether ACL is exploitable. Confirm affected versions and reachable code paths.

### 8. NIST AI / Agentic AI

**Watch:**
- https://www.nist.gov/artificial-intelligence
- https://www.nist.gov/agentic-ai

**Cadence:** monthly and event-driven when new standards, evaluation work, or guidance appears.

**Evidence:** NIST's AI program links Agentic AI, AI measurement/evaluation, security, standards, the AI Risk Management Framework, and related resources. Its Agentic AI page says current work focuses on trustworthiness, evaluation/testing, standards, interoperability, governance, and risk management, including the AI Agent Standards Initiative.

**Why it matters:** NIST is a slower-moving but authoritative anchor for evaluation terminology, risk management, interoperability, and governance.

### 9. Model Context Protocol (MCP) specification and upstream repository

**Watch:**
- current specification: https://modelcontextprotocol.io/specification/
- upstream repository: https://github.com/modelcontextprotocol/modelcontextprotocol

**Cadence:** release/specification-driven plus a weekly check when ACL is actively designing tool boundaries.

**Evidence:** the current 2026-07-28 specification covers resources, prompts, tools, progress, cancellation, error reporting, security/trust principles, and an opt-in Tasks extension for asynchronous long-running operations with durable handles. The upstream repository exposes specification evolution through issues, pull requests, discussions, schemas, and proposal material.

**Why it matters:** MCP directly overlaps ACL's tool contracts, long-running operations, cancellation, approvals, and trust boundaries.

**Warning:** track the specification and security guidance, not just third-party MCP server catalogs. Protocol support does not make a server trustworthy.

### 10. Agent2Agent (A2A) protocol

**Watch:**
- https://a2a-protocol.org/latest/
- https://github.com/a2aproject/A2A

**Cadence:** release/roadmap-driven; weekly while ACL is considering multi-agent interoperability.

**Evidence:** A2A is an open protocol for agent-to-agent interoperability, with specification, release notes, roadmap, task lifecycle, streaming/asynchronous operations, governance, issues, and discussions. The documentation explicitly positions MCP as agent-to-tool communication and A2A as agent-to-agent communication.

**Why it matters:** it is a recurring standards source for delegation, remote-agent boundaries, task lifecycle, discovery, and cross-framework interoperability without forcing ACL to adopt a specific orchestration framework.

### 11. OpenTelemetry GenAI semantic conventions

**Watch:** https://github.com/open-telemetry/semantic-conventions-genai

**Cadence:** release/changelog-driven; monthly until ACL reaches observability implementation work.

**Evidence:** the project defines GenAI-specific OpenTelemetry conventions for spans, metrics, events, GenAI clients, MCP, and provider-specific behavior, with an active changelog/issues/PR workflow.

**Why it matters:** it can prevent ACL from inventing incompatible telemetry vocabulary for long-running workers, tool calls, traces, errors, and later cross-system observability.

## Tier B — practitioner discovery sources; verification required

### LocalLLaMA

https://www.reddit.com/r/LocalLLaMA/new/

Useful for early reports on local inference runtimes, quantization, GPU/CPU behavior, model quirks, context limits, and reproducible performance/failure tests. Some posts include exact builds, hashes, settings, scripts, and failure timelines.

**Rule:** treat every conclusion as anecdotal until reproduced or tied to upstream issues/artifacts.

### Hacker News

https://news.ycombinator.com/newest

High-frequency discovery stream for new projects, technical writeups, postmortems, research papers, and practitioner criticism. Use `new`, `show`, comments, and historical search to discover leads.

**Rule:** follow the link to the primary source; comment consensus is not evidence.

### Hugging Face Forums

https://discuss.huggingface.co/

Useful for operational edge cases around models, runtimes, low-VRAM deployment, tool use, and model cards.

**Rule:** verify against model/runtime documentation, issues, code, or a reproducible test.

### Project Discords and chat communities

Use only when a primary repository/documentation page points there and the discussion is relevant.

**Warning:** many chat systems are hard to search, cite, or archive. They are not core evidence stores unless a finding can be captured in a stable public source.

## Tier C — low-priority or situational sources

- GitHub Trending/Topics: good for discovery, weak for technical validation.
- Generic AI news aggregators: high volume and duplicated reporting; use only to locate a primary source.
- Vendor marketing pages: use for release discovery, not for comparative reliability claims.
- Social accounts: defer individual account selection to the later people/projects task.
- Conference/OpenReview pages: useful when validating a specific research thread, but not necessary as a daily general-purpose feed when arXiv and targeted paper searches already cover the discovery layer.

## Practical review loop

A sustainable manual or automated watch cycle should be:

1. Scan Tier A changes.
2. Scan Tier B only for new failure reports or candidates not already seen.
3. Deduplicate by canonical project/paper/advisory/specification URL.
4. Escalate only items that touch an ACL/Vera research question.
5. Verify consequential claims upstream.
6. Add a catalog entry with observed fact separated from inference.
7. Do not promote a project/person merely because it appears frequently; activity/ranking is a later task.

## Stop condition for this task

The landscape is sufficiently mapped when each major ACL/Vera concern has at least one recurring primary source and one discovery/corroboration path. This task does **not** determine which individual agent project, maintainer, or account is best.
