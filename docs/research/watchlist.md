# Initial Watchlist

This list contains two different things:
1. seed project/security candidates that still require later activity/relevance research; and
2. the recurring **source channels** established by the completed landscape-mapping task.

The project candidates below remain deliberately unranked. Ranking them now would begin the next research task.

## Coding-agent / harness candidates
- OpenHands
- SWE-agent
- Aider
- Cline

## Orchestration / agent-runtime candidates
- LangGraph
- AutoGen
- CrewAI
- LlamaIndex agent components

## Local-model infrastructure to watch
- Ollama ecosystem
- llama.cpp ecosystem
- Hugging Face model/runtime discussions relevant to tool use and structured output

## Security / governance candidates
- OWASP AI Agent Security Cheat Sheet
- OWASP Agent Memory Guard
- OWASP secure-agent-playbook
- MITRE ATLAS
- NIST AI risk/security guidance

## Recurring source watch stack — mapped in Task 1

### Core / primary
- Upstream GitHub releases, changelogs, advisories, issues, discussions, and selected PRs for watched projects.
- arXiv recent feeds: cs.SE, cs.MA, cs.CR; cs.AI as a cross-list/search overflow.
- Hugging Face function-calling model filter and Daily Papers.
- SWE-bench official leaderboards/news.
- Berkeley Function Calling Leaderboard (BFCL) and changelog.
- OWASP GenAI Security Project and Agentic Security Initiative.
- MITRE ATLAS machine-readable data releases.
- GitHub Advisory Database and OSV.
- NIST AI and Agentic AI pages.
- Model Context Protocol specification/upstream repository.
- Agent2Agent protocol specification/upstream repository.
- OpenTelemetry GenAI semantic-conventions repository.

### Discovery only; verify upstream
- r/LocalLLaMA
- Hacker News
- Hugging Face Forums
- publicly searchable project Discord/forum discussions

### Low priority
- generic AI news aggregation
- GitHub Trending/Topics without follow-up verification
- vendor marketing without primary technical evidence
- social accounts until the later people/projects task identifies which accounts actually produce recurring signal

See `sources.md` for cadence, evidence, caveats, and the evidence ladder.

## Questions reserved for later ranking

Do not answer these during landscape mapping:
- Is the project active?
- Does it support local/open models in practice, not merely in documentation?
- How does it handle tool contracts and malformed model output?
- Who owns workflow control: model or harness?
- How are state, checkpoints, retries, and recovery handled?
- How are sandboxes, filesystem/network boundaries, and secrets handled?
- How is success independently validated?
- What failures recur in issues/discussions?
- Is there a reusable component that would save ACL work?
- Is the project healthy enough to watch, contribute to, fork, or collaborate with?
