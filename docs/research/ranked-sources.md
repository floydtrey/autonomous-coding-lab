# Ranked Recurring Sources — Task 3

**Accessed:** 2026-09-05  
**Task:** Rank the recurring source channels established in Task 1 for ACL/Vera research.  
**Interpretation:** this is a **review-priority ranking** based on expected technical signal per unit of attention. It does not replace the evidence ladder in `sources.md`.

## Method

Source priority uses the following heuristic:

1. **Primary-evidence authority — 30%**
2. **Breadth of direct ACL/Vera relevance — 25%**
3. **Reproducibility / actionability — 20%**
4. **Cadence / timeliness — 15%**
5. **Auditability / stable versioning — 10%**

A lower-ranked authoritative source may still control a specific question. For example, a NIST publication can outrank a GitHub issue when the question is formal risk terminology, even though GitHub ranks higher for the routine watch cycle.

## Ranked watch queue

### 1. Upstream GitHub repositories
- **Why #1:** fastest path from a signal to implementation evidence—code, tests, commits, releases, issues, discussions, security advisories and maintainers' decisions.
- **Best use:** verify every consequential project claim; watch releases/changelogs and targeted hard-problem changes rather than all commits.
- **Failure mode:** activity volume and popularity are not quality. Use narrow ACL/Vera questions.
- **Entry:** https://github.com/

### 2. OWASP GenAI Security Project / Agentic Security Initiative
- **Why #2:** directly maps to ACL/Vera's highest-consequence boundaries: prompt injection, tool abuse, excessive autonomy, memory/context poisoning, MCP, agent controls and governance.
- **Best use:** maintain the threat/control vocabulary and nominate attack classes for deterministic ACL/Vera tests.
- **Failure mode:** guidance is not proof a concrete implementation is safe.
- **Entries:**
  - https://genai.owasp.org/
  - https://genai.owasp.org/initiatives/agentic-security-initiative/

### 3. SWE-bench + Berkeley Function Calling Leaderboard (BFCL)
- **Why #3:** actionable external signals for the two capabilities ACL needs to distinguish: software-engineering task performance and structured tool/function calling.
- **Best use:** nominate model/harness candidates and detect methodology changes, then reproduce behavior in ACL-owned tests.
- **Failure mode:** leaderboard rank is not ACL reliability; harness, context, contamination and cost assumptions differ.
- **Entries:**
  - https://www.swebench.com/
  - https://gorilla.cs.berkeley.edu/leaderboard.html

### 4. arXiv recent feeds — cs.SE / cs.MA / cs.CR
- **Why #4:** broad early-discovery stream for harness engineering, long-horizon evaluation, multi-agent reliability and security research before ideas reach production frameworks.
- **Best use:** targeted keyword scan two or three times per week; retain papers only when methods/artifacts answer an ACL/Vera question.
- **Failure mode:** preprints are discovery, not validation.
- **Entries:**
  - https://arxiv.org/list/cs.SE/recent
  - https://arxiv.org/list/cs.MA/recent
  - https://arxiv.org/list/cs.CR/recent

### 5. Model Context Protocol specification + upstream repository
- **Why #5:** current protocol work directly covers tool/resource contracts, progress, cancellation, errors, long-running Tasks and authorization context—the seams ACL will otherwise invent itself.
- **Best use:** compare ACL interfaces against stable protocol concepts while keeping local authorization policy separate.
- **Failure mode:** protocol compatibility does not establish trust in a tool/server.
- **Entries:**
  - https://modelcontextprotocol.io/specification/
  - https://github.com/modelcontextprotocol/modelcontextprotocol

### 6. Hugging Face function-calling model filter + Daily Papers
- **Why #6:** efficient discovery for new open/local tool-use models, quantizations and model research, with links into runtimes such as llama.cpp/vLLM/Ollama.
- **Best use:** nominate models for ACL's benchmark; follow model cards and upstream runtime issues only after nomination.
- **Failure mode:** tags, downloads, likes and trending status are not capability evidence.
- **Entries:**
  - https://huggingface.co/models?other=function-calling
  - https://huggingface.co/papers

### 7. GitHub Advisory Database + OSV
- **Why #7:** machine-readable, version-aware vulnerability signal that becomes increasingly valuable as ACL adopts real dependencies.
- **Best use:** today, landscape scanning; later, package/version-specific checks tied to reachability.
- **Failure mode:** an advisory does not prove ACL is exploitable.
- **Entries:**
  - https://github.com/advisories
  - https://osv.dev/

### 8. MITRE ATLAS
- **Why #8:** stable adversarial-AI taxonomy with versioned machine-readable tactics, techniques, mitigations and case studies.
- **Best use:** map security regression cases and threat-model coverage to stable identifiers.
- **Failure mode:** taxonomy coverage is not implementation-specific risk evidence.
- **Entry:** https://github.com/mitre-atlas/atlas-data

### 9. NIST AI / Agentic AI
- **Why #9:** slower but authoritative anchor for evaluation terminology, standards, interoperability, governance and risk management.
- **Best use:** cross-check ACL/Vera governance/evaluation vocabulary and consequential design requirements.
- **Failure mode:** intentionally general guidance can lag fast-moving implementation details.
- **Entries:**
  - https://www.nist.gov/artificial-intelligence
  - https://www.nist.gov/agentic-ai

### 10. OpenTelemetry GenAI semantic conventions
- **Why #10:** likely prevents ACL from inventing incompatible names for traces, spans, metrics, model calls and MCP/tool telemetry.
- **Best use:** revisit when ACL formalizes observability/evidence schemas.
- **Failure mode:** conventions are still evolving; pin versions and distinguish stable from experimental fields.
- **Entry:** https://github.com/open-telemetry/semantic-conventions-genai

### 11. Agent2Agent (A2A) protocol
- **Why #11:** useful standards stream for future remote-agent delegation, discovery and long-running task communication.
- **Why lower:** ACL has not yet demonstrated a need for cross-framework remote-agent interoperability; MCP/tool and internal worker contracts are more immediate.
- **Failure mode:** interoperability is not orchestration policy or trust.
- **Entries:**
  - https://a2a-protocol.org/latest/
  - https://github.com/a2aproject/A2A

### 12. r/LocalLLaMA
- **Why #12:** the strongest practitioner-discovery source in the mapped set for local-runtime regressions, quantization/hardware quirks and reproducible configuration reports.
- **Best use:** early warning only; promote posts with versions, hashes, settings and artifacts into upstream verification.
- **Failure mode:** anecdotal consensus is not evidence.
- **Entry:** https://www.reddit.com/r/LocalLLaMA/new/

### 13. Hugging Face Forums
- **Why #13:** useful for model/runtime edge cases and low-VRAM deployment questions after a specific candidate is known.
- **Failure mode:** forum advice requires verification against model cards, code/issues or reproducible tests.
- **Entry:** https://discuss.huggingface.co/

### 14. Hacker News
- **Why #14:** wide, fast discovery of projects, papers, postmortems and practitioner criticism.
- **Why lower:** high noise and indirect sourcing; most useful as a link finder.
- **Failure mode:** comment consensus is never primary evidence.
- **Entry:** https://news.ycombinator.com/newest

### 15. Public project Discords / chat communities
- **Why #15:** can reveal operational pain and maintainer context unavailable elsewhere.
- **Why lowest:** difficult to search, cite, deduplicate and archive; poor foundation for an auditable research branch.
- **Rule:** use only when an upstream project points there and promote a finding to a stable source whenever possible.

## Practical ranked review loop

1. Check upstream project releases/targeted changes for the currently ranked project queue.
2. Scan OWASP and vulnerability/security sources for new authority or threat changes.
3. Check SWE-bench/BFCL and Hugging Face when model/harness selection is active.
4. Scan targeted arXiv feeds for new mechanisms or evidence that could alter the queue.
5. Check MCP and other standards when tool/lifecycle interfaces are being designed.
6. Use practitioner sources to find leads, never to close consequential findings without verification.

## Stop boundary

This source ranking only sets review priority. It does not start a recurring monitor, change ACL architecture, deep-research a source topic, or supersede the Task 1 evidence ladder.
