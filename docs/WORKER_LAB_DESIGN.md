# Worker Lab Design

**Status:** Active approved design direction; implementation details remain subject to validated refinement.
**Read when:** Planning or implementing Worker Lab.

## Mission

Worker Lab is a local-first learning, proving, and evaluation platform for software workers. It turns small application-building exercises into retained evidence, failure knowledge, reusable playbooks, and objective graduation decisions.

It does not retrain the underlying Codex model. It improves the system around the model: context, contracts, prompts, exercises, tests, evaluation, failure handling, evidence, controller judgment, and approved implementation patterns.

## Product boundary

Worker Lab will be a durable third repository named `worker-lab`.

Its upstream execution/security engine is `autonomous-worker-framework`. Its protected production consumer is `advanced-mine-asset-inspection` (Mine Tracker). Worker Lab must call the framework through explicit contracts and must not copy framework security logic or Mine Tracker product source into itself.

It owns:

- curriculum and exercise definitions;
- exercise-template versions;
- attempt identity and lifecycle;
- content-addressed input and result evidence;
- deterministic evaluation results;
- failure classification and retrospectives;
- approved playbooks and promotion history;
- worker capability/graduation records;
- human-readable approval packets;
- a later local read-only dashboard.

It does not own:

- Codex authentication, sandbox, or credential controls;
- general worker execution and repository handoff machinery;
- Mine Tracker product direction or production authority;
- automatic merge permission;
- model training or model-weight changes;
- worker-controlled evaluator or graduation changes.

## Users

### Product owner

Needs understandable evidence of what a worker attempted, whether it worked, what failed, what risk remains, and whether prior state can be restored.

### Trusted controller

Defines curricula and protected evaluation rules, authorizes attempts, reviews actual diffs and evidence, classifies failures, promotes patterns, and decides graduation.

### Planner worker

Reads an exercise and starting repository, then proposes a bounded implementation plan, relevant context, exact writable paths, acceptance criteria, tests, and risks.

### Coding worker

Implements one contracted exercise task in an isolated worktree under the framework's existing restrictions.

### Verifier

Evaluates the exact candidate against immutable exercise expectations and records evidence without changing the candidate or evaluation rules.

## Core workflow

```text
Curriculum definition
  -> versioned exercise template
  -> immutable attempt inputs
  -> read-only worker proposal
  -> trusted task contract
  -> isolated coding attempt
  -> framework boundary checks
  -> deterministic evaluation
  -> independent review
  -> evidence and failure classification
  -> approval packet
  -> retain evidence / discard exercise checkout
  -> update framework or approved playbook only after review
```

## Core records

### Curriculum

- curriculum ID and version;
- purpose and difficulty;
- capabilities under evaluation;
- prerequisite curricula;
- exercise sequence;
- graduation contribution.

### Exercise

- exercise ID and version;
- template repository identity;
- objective and supplied context;
- exact writable and protected paths;
- acceptance assertions;
- focused and full validation;
- hidden evaluator checks where appropriate;
- prohibited shortcuts;
- expected failure and recovery behavior;
- reference solution identity, if retained.

### Attempt

- immutable attempt ID;
- curriculum/exercise version;
- worker/runtime/model identity;
- starting commit and context digest;
- task digest;
- sandbox and timeout;
- timestamps and lifecycle state;
- candidate identity;
- cleanup outcome.

### Evaluation

- correctness results;
- security/boundary results;
- stability and recovery results;
- modularity review;
- efficiency observations;
- explanation quality;
- exact evidence links/digests;
- pass, fail, needs-review, or not-evaluated per dimension.

Worker Lab should not collapse these dimensions into a misleading single intelligence score.

### Failure record

- first failed boundary;
- expected and observed behavior;
- classification: worker reasoning, context, contract, test, framework, environment, or controller judgment;
- containment and cleanup outcome;
- proposed control or accepted limitation;
- recurrence links.

### Approved playbook

- reviewed pattern and intended use;
- examples and counterexamples;
- required tests and security considerations;
- provenance from successful attempts;
- approving controller and version history;
- supersession status.

## Initial directory concept

```text
worker-lab/
  README.md
  docs/
  lab/
    curriculum.py
    exercises.py
    attempts.py
    evidence.py
    evaluation.py
    failures.py
    playbooks.py
  curricula/
    record-ledger/
      curriculum.json
      exercises/
      templates/
      evaluators/
  tests/
  workspace/          ignored; disposable attempt checkouts
  evidence/           local retained evidence, content addressed
```

The exact structure should be validated during implementation rather than treated as frozen architecture.

## Security and integrity

- local-only and single-user initially;
- synthetic exercise data only;
- no Mine Tracker runtime or private operational data;
- no production credentials;
- immutable/versioned attempt inputs;
- separate repository/worktree per attempt;
- expected evaluator behavior cannot be changed by the worker during an attempt;
- hidden checks remain outside worker-writable scope;
- evidence is content addressed and bound to task/candidate identity;
- GitHub publication is optional and disabled by default;
- exercise checkouts can be discarded without losing retained evidence;
- playbook and graduation changes require trusted-controller review.

## Headless MVP

The first usable version has no dashboard and no multi-worker scheduler.

It needs:

1. strict curriculum and exercise schemas;
2. deterministic local storage for definitions and attempt metadata;
3. exercise-template creation from exact Git identity;
4. isolated attempt workspace creation and cleanup;
5. invocation of the Autonomous Worker Framework;
6. deterministic evaluator execution with stop-at-first-failure semantics;
7. structured evidence and failure records;
8. backup and restore of Lab metadata/evidence;
9. a command-line interface for listing curricula, starting an authorized attempt, evaluating it, and producing an approval packet.

The framework remains responsible for worker runtime security. Worker Lab orchestrates approved exercises and retains their learning evidence.

## First curriculum: Local Record Ledger

The first curriculum builds a generic local safety-observation ledger in bounded stages:

1. strict domain record and validation;
2. atomic JSON persistence and corruption detection;
3. create/list/filter CLI behavior;
4. deterministic CSV import/export and duplicate handling;
5. summary reporting;
6. invalid-input and interrupted-write scenarios;
7. backup/restore and rollback drill;
8. deliberately injected regression and containment test;
9. approval packet and retrospective.

This curriculum is useful to workers because successful, independently reviewed patterns can become approved Lab playbooks. It is useful to us because its behavior is easy to inspect and its failure modes exercise real security and stability concerns.

## Later curricula

- modular local web utility: API/persistence/UI separation, SQLite transactions, migrations, accessibility, browser checks, backup/upgrade/rollback;
- local OCR document library: immutable originals, content hashes, provenance, confidence, adapter isolation, malicious-file handling, dependency/license review, search, and reprocessing history;
- standalone Vera: deferred until deterministic curricula are dependable, then used for planning/tool-use evaluation rather than as an early proving surface.

## Development tracks

### Track A — Mine Tracker completion

The trusted controller may continue ordinary Mine Tracker development under existing governance. Experimental workers do not change Mine Tracker product source until graduation.

### Track B — Worker Lab and proving

Workers build bounded Lab modules and exercise applications. Failures are expected evidence. Framework controls and playbooks improve only after independent review.

Keeping these tracks separate prevents worker research from blocking Mine Tracker completion while also preventing Mine Tracker from becoming the experimental environment.

## Implementation phases

### Phase 1 — Contracts and local storage

Create the repository, schemas, deterministic serialization, validation, and tests. Trusted controller authors the protected contracts.

### Phase 2 — Exercise factory and attempt lifecycle

Create versioned templates, isolated workspaces, attempt state transitions, cleanup, and evidence identity.

### Phase 3 — Framework integration

Invoke read-only proposals and bounded code tasks through the existing framework. Preserve separate responsibilities rather than copying framework code.

### Phase 4 — Record Ledger curriculum

Run real worker attempts, record failures, rehearse recovery, and promote only independently verified patterns.

### Phase 5 — Approval packets and read-only dashboard

Build understandable evidence presentation from real data. The first dashboard is observational, not an execution console.

### Phase 6 — Additional curricula and graduation review

Add the modular web and OCR curricula, satisfy `PROVING_PROGRAM.md`, and decide whether limited Mine Tracker product work reduces expected effort and risk.

## Explicit non-goals for the first version

- multiple concurrent coding workers;
- workers modifying their own evaluation;
- automatic curriculum generation with authority;
- automatic playbook promotion;
- generalized self-repair;
- cloud service or shared multi-user deployment;
- production data ingestion;
- autonomous Mine Tracker changes;
- a sophisticated graphical dashboard;
- a standalone Vera implementation.
