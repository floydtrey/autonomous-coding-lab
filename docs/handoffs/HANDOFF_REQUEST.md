# Exact Project Consolidation Handoff Request

Replace only `<HANDOFF-ID>` and `<SOURCE-LABEL>` before sending this request to a
source conversation. Do not otherwise shorten or reinterpret it.

---

Prepare a consolidation handoff for this conversation.

Handoff ID: `<HANDOFF-ID>`

Source label: `<SOURCE-LABEL>`

This handoff will be reconciled against the existing private
`autonomous-coding-lab` repository. Your conversation is a knowledgeable witness
for its own work, not the authority for the combined architecture.

## Operating boundary

1. Stop feature development. Do not implement, refactor, merge, copy source
   files, commit, push, clean, delete, move, install, or publish anything.
2. Inspect the local repository and files already in your scope when available.
   Read that repository's `AGENTS.md` and active routing/current-state documents
   before reporting its state.
3. Do not invent repository state. If you cannot inspect something directly,
   mark it `UNVERIFIED` and explain why.
4. Treat chat history as evidence, not proof. Label a claim `CHAT-ONLY` when it
   is supported only by conversation memory.
5. Do not wait for a long-running test. Record its exact run ID, last observed
   status, completed/total count, observation timestamp, and result path. Mark
   its outcome `PENDING`.
6. Do not expose credentials, tokens, secret values, private operational data,
   unrestricted environment dumps, model binaries, or large raw logs.
7. Do not resolve disagreements with other projects. Report the disagreement
   and the evidence available to this conversation.
8. Return exactly one Markdown document in your final response. Do not surround
   it with commentary. Title it `PROJECT CONSOLIDATION HANDOFF — <HANDOFF-ID>`.

## Evidence vocabulary

Use only these evidence labels:

- `VERIFIED` — directly confirmed from current Git, filesystem, configuration,
  or a completed test during this handoff.
- `RECORDED` — stated in an identified tracked document or retained result, but
  not independently rerun during this handoff.
- `CHAT-ONLY` — present only in conversation history.
- `PROPOSED` — designed or recommended but not implemented.
- `UNKNOWN` — insufficient evidence.

Use only these implementation states:

- `IMPLEMENTED`
- `PARTIALLY IMPLEMENTED`
- `NOT IMPLEMENTED`
- `SUPERSEDED`
- `UNKNOWN`

Use only these readiness states:

- `PASS`
- `BLOCKED`
- `PENDING`
- `NOT APPLICABLE`
- `UNKNOWN`

## Required document

Produce every section below. Write `None identified` when a section truly has no
items. Do not omit a section.

### Handoff Metadata

Include:

- handoff ID and source label;
- preparation timestamp with timezone;
- conversation/task title and ID if visible;
- repository name and absolute local path;
- branch, exact full HEAD commit, exact HEAD tree ID, upstream relation, remotes,
  tags relevant to current authority, and exact working-tree status;
- the commands or files used to verify those facts;
- whether the report covers one repository, multiple repositories, or
  discussion-only work.

If multiple repositories are involved, give each a separate identity row.

### 1. Purpose and Scope

State what this work owns, the problem it solves, its intended consumers, and
what it explicitly does not own.

### 2. Current State

Separate:

- completed and verified behavior;
- implemented but not freshly verified behavior;
- partial work;
- proposals and discussion;
- active or unfinished work.

Every important statement must carry an evidence label and point to a file,
commit, test, result, or explicit chat-only basis.

### 3. Repository and Preservation State

Describe tracked modifications, staged changes, untracked files, ignored runtime
data, unreadable paths, generated artifacts, active processes, local-only
commits, missing remotes, and anything at risk of being lost. State exactly what
must be preserved and what must not be copied. Do not recommend committing
generated, ignored, secret-bearing, or unexplained material.

### 4. Architecture and Durable Decisions

For every important decision, provide:

| Decision | Implementation state | Evidence label | Evidence | Consolidation effect |
|---|---|---|---|---|

Clearly identify superseded and conflicting decisions rather than silently
choosing among them.

### 5. Directory, Path, and Environment Assumptions

Record repository roots, package roots, working-directory assumptions, absolute
paths, relative-path resolution, virtual environments, executables, model/data
locations, output directories, temporary/workspace locations, and path-derived
identity checks. Distinguish historical paths from active code/configuration.

### 6. Interfaces, Schemas, and Dependencies

List every interface another component can rely upon: commands, entry points,
subprocess protocols, APIs, file schemas, IDs, state machines, evidence records,
configuration formats, prompt formats, and dependency direction. Identify the
owning component and whether compatibility is tested.

### 7. Roles, Authority, and Workflow

Explain Planner, Task Creator, Builder/Coder, Reviewer/Diagnostician, verifier,
trusted controller, local-model, cloud-escalation, publication, and merge roles
where applicable. State both permitted and forbidden actions. Distinguish
technical capability from currently authorized behavior.

### 8. Tests and Validation Evidence

Provide:

| Test/suite/run | Exact command or run ID | Last result | Evidence label | What it proves | What it does not prove |
|---|---|---|---|---|---|

Include focused tests, full suites, deterministic evaluation, manual review,
expected skips, failures, interrupted/resumed runs, pending runs, and tests that
must be repeated after consolidation. Never equate provider success with answer
quality or a passing unit suite with production authority.

### 9. Known Problems and Technical Debt

Include concrete bugs, incomplete migrations, temporary workarounds, stale
documentation, format mismatches, portability issues, duplicated logic,
unverified assumptions, and deferred validation.

### 10. Cross-Project Conflicts and Possible Duplication

Identify suspected conflicts involving repository ownership, path hierarchy,
task IDs, worker/task systems, prompts, authority, schemas, dependency gates,
resume behavior, GUI/backend boundaries, model routing, cloud escalation,
persistence, GitHub, and local versus remote responsibilities. Do not resolve a
conflict without objective evidence.

### 11. Dangerous Assumptions

List anything that could cause data loss, path escape, weakened security,
invalid evidence, duplicated work, destructive cleanup, broken recovery,
unintended publication, or architecture lock-in.

### 12. Must Preserve

List exact files, commits, tags, histories, tests, schemas, evidence, decisions,
behaviors, and pending result paths that must remain recoverable even if this
implementation is not selected.

### 13. May Replace, Archive, or Discard

Separate:

- safe to replace after parity;
- historical material to archive but retain;
- generated/runtime material to exclude;
- items whose disposition remains unknown.

Do not authorize deletion. The consolidation task decides disposition later.

### 14. Recommended Canonical Direction

Give this source conversation's recommendation, explicitly labeled
`PROPOSED`. Explain dependency direction and how to preserve boundaries inside
one repository. Do not present the recommendation as accepted architecture.

### 15. Open Decisions

List decisions this conversation cannot safely make alone. For each, name the
evidence or other handoff required to resolve it.

### 16. Pre-Consolidation Actions

List only concrete actions required before import, each with an owner, reason,
readiness state, and verification method. A pending long-running test may be
carried forward rather than blocking handoff preparation.

### 17. First Actions for the Consolidation Task

Give a strictly ordered inspection and reconciliation sequence. The first step
must be to compare this witness report with Git evidence and the existing merger
contract. Stop before implementation or source import.

### Pre-Merge Readiness Checklist

Use a table with these exact rows and one readiness state per row:

- exact source identity known;
- working-tree differences classified;
- local-only commits protected;
- generated/runtime data excluded;
- credentials/private data excluded;
- license/distribution status known;
- authority boundary documented;
- interfaces and schemas inventoried;
- path assumptions inventoried;
- focused validation identified;
- full validation identified;
- pending runs recorded without assumed outcome;
- rollback identity available;
- conflicts requiring other handoffs identified;
- safe to begin source import.

For the final row, use `BLOCKED` unless every prerequisite has verified evidence
and the existing merger contract has accepted the import milestone.

### Consolidation Warning Summary

Finish with the three to seven facts or risks the consolidation task must not
miss. Each warning must cite its evidence label and source.

