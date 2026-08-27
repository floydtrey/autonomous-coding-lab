# Architecture

## Purpose

The framework turns a human-approved goal into a bounded, inspectable software candidate. Codex supplies reasoning and coding ability. The framework supplies identity, scope, isolation, validation, evidence, and stop conditions.

It is not a second product authority, an autonomous publisher, or a replacement for trusted review.

## System map

```text
Human goal
   |
   v
Trusted controller (this ChatGPT development conversation)
   |  defines scope, risk, acceptance, context, and authority
   v
Task contract + repository context packet
   |  bound to exact target HEAD and content digests
   +--------------------+
   |                    |
   v                    v
Read-only Codex probe   Workspace-write Codex worker
analysis/proposal       isolated target worktree
   |                    |
   +---------+----------+
             v
Framework boundary checks
exact paths, unchanged HEAD, clean diff, stop on failure
             |
             v
Trusted focused validation -> trusted full validation
             |
             v
Identity-bound candidate commit and repository handoff
             |
             v
Draft pull request + read-only exact-candidate verification
             |
             v
One-time exact-head merge authorization
             |
             v
Protected main CI -> evidence closeout -> branch/worktree cleanup
```

## Components

| Component | Responsibility | Explicitly does not do |
|---|---|---|
| `consumer_profile.py` | Defines Mine Tracker authority files, protected paths, product invariants, and authoritative validation. Produces content-addressed context packets. | Change consumer files or infer permission to work. |
| `context_probe.py` | Runs a Codex analysis against an exact context packet in `read-only` mode and proves the repository stayed clean. | Implement or publish changes. |
| `code_task.py` | Runs one general code task in `workspace-write`, requires exact changed paths, rejects commits/head movement, and runs trusted validation. | Repair, commit, push, or merge. |
| `codex_runtime.py` | Enforces the audited Codex version, ChatGPT auth, sanitized environment, explicit sandbox, separate repository, and execution timeout. | Accept API-key auth or danger/full access. |
| `task_contract.py` | Defines the earlier deterministic commissioning task contract. | Represent arbitrary product tasks. |
| `local_worker_harness.py` | Runs deterministic fixture jobs, boundary checks, validation, and one bounded fixture-repair attempt. | Grant general repair authority. |
| `worker_result.py` | Validates structured worker evidence and derives handoff readiness. | Trust worker prose as proof. |
| `repository_handoff.py` | Rebinds a ready result to current candidate bytes and repository identity. | Publish or merge. |
| `local_git_publisher.py` | Creates a verified local candidate commit from a validated fixture result. | Decide correctness or obtain approval. |
| Mine Tracker verification workflow | Binds issue, digest, PR, branch, head, base, exact path, and authoritative tests. | Write, repair, queue, or merge. |

## Trust boundaries

### Trusted controller

The active ChatGPT development conversation is the maintainer/controller. It may inspect and change both repositories, review code, create evidence records, publish candidates, and consume an exact one-time merge authorization under the user's standing authority.

### Restricted worker

The Codex subprocess is untrusted execution. Prompts are instructions, not authority. Its output is accepted only when filesystem, Git identity, scope, and trusted validation independently agree.

### Verifier

Verification examines the exact candidate commit against the current `main`. It has read-only repository permission. A green result is evidence, not merge permission.

### Publisher

Publication is mechanical transport of an already validated candidate into a commit/branch/PR. It is deliberately not a separate AI authority and cannot approve its own output.

### Consumer repository

Mine Tracker remains authoritative for its product direction, governance, tests, and protected areas. Consumer rules narrow worker authority; framework defaults never widen it.

## Identity chain

The evidence chain is designed to make stale or substituted work fail closed:

```text
consumer profile digest
  -> context packet digest + target HEAD
  -> task digest + exact expected paths
  -> candidate content/commit identity
  -> PR head + current main base
  -> verification run
  -> one-time merge authorization
  -> merge commit + post-merge CI
```

If `main`, the candidate head, context bytes, protected guidance, or changed paths move, prior evidence is stale and must not be reused.
