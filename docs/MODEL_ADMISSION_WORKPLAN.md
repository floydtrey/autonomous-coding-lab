# ACL Model Admission Workplan

**Status:** Active — MA-1 accepted; MA-2 next

**Last updated:** 2026-09-13

**Source conversation:** Codex task — ACL model insertion readiness

**Working branch:** `feat/model-admission-operator-path`, based on
`architecture/knowledge-core` at `ee241be`

**Execution authority:** `DISABLED`

## Goal

Make ACL ready to receive an explicitly selected local model for a protected
role without changing source code for each model and without treating Benchmark
Lab as an execution dependency.

The first accepted outcome is one supervised, disposable coding-worker vertical
slice. Planner and verifier admission follow as separate role packets after the
coding path is proven.

## Non-interference boundary

The user's Local Model Bench campaign is currently running on the intended host.
Until the user reports that campaign complete:

- do not contact Ollama or inspect its live model inventory;
- do not run provider installation observation or capability qualification;
- do not launch a model-backed ACL worker;
- do not read or modify `C:\Projects\local-model-bench` or its results/logs;
- use GitHub Actions and deterministic fake-provider tests for validation.

Source edits, documentation, and deterministic tests must preserve this boundary.

## Accepted starting state

- Runtime reconstruction Tasks 1–9 are complete.
- Invocation/Result V3 and Provider Binding V1 are implemented.
- The framework has a provider-neutral dispatch adapter and a Pydantic AI +
  Ollama bounded-file provider adapter.
- Source identity verification reports every protected component as `MATCH`.
- Root tests passed 12 tests during the readiness review.
- Focused Worker Lab admission/dispatch tests passed 40 tests.
- Focused framework provider/dispatch/repository tests passed 28 tests.
- No real provider/model request occurred during the review.

## Blocking gaps

1. The normal Worker Lab CLI cannot persist provider observations,
   qualifications, or Provider Bindings.
2. There is no production capability-probe runner for the protected Ollama
   candidate.
3. There is no production composition from Worker Lab dispatch through the
   framework adapter to one exact bound provider executor.
4. The active tree has no current curriculum/exercise/context packet for a
   disposable V3 coding task.
5. Only the coding-worker role has a runtime requirement and provider path;
   planner and verifier are definitions only.
6. Runtime-core CI is not active on the current architecture branch.

## Ordered delivery

### MA-1 — Durable admission records and operator surface

Add service and CLI operations to:

- observe one installed provider/model without claiming capability;
- run a separately authorized controlled capability probe;
- persist exact observation and qualification evidence;
- create, list, and inspect an immutable Provider Binding;
- reject duplicate, stale, mismatched, or model-substituted records.

No command may silently execute a capability probe. The probe runner must remain
an explicit input at the service boundary.

**Gate:** deterministic service/CLI tests prove the record lifecycle with fake
observers and fake probe evidence; no Ollama request occurs.

**Accepted:** implementation commit `500a6b5`; GitHub Actions run
`34756466201` passed portable source verification, 12 repository tests, 333
Worker Lab tests (one known environment-dependent symlink skip), and 76
Autonomous Worker Framework tests on Windows. No local provider/model request
was made.

### MA-2 — Production runner composition

Add one explicit operator composition that binds:

- the selected Provider Binding and qualification evidence;
- protected runtime settings;
- the provider-neutral framework dispatch adapter;
- the Pydantic AI + Ollama bounded-file executor;
- Windows Job Object custody and durable absence evidence.

There must be no default model, provider, binding, or fallback. The normal
non-executing service remains safe when no runner is supplied.

**Gate:** end-to-end deterministic tests use an injected fake model runner and
prove exact identity, custody, changed-path, sealed-test, and candidate evidence.

### MA-3 — Disposable coding-worker packet

Add one current V3 curriculum, exercise, context manifest, and protected test
profile for a small disposable repository. It must allow one bounded source-file
change and forbid network, shell, dependencies, commit, push, merge,
publication, and external/product-repository access.

**Gate:** definition and preparation tests prove the packet resolves without a
provider call.

### MA-4 — Runtime-core CI and documentation closure

Add GitHub Actions coverage for portable source identity, root tests, Worker Lab,
and the framework. Update source identity only after behavior-bearing files are
final. Reconcile `CURRENT_STATE`, `OPERATIONS`, and this workplan with the exact
accepted commit and test evidence.

**Gate:** GitHub Actions passes on the exact branch head while execution remains
disabled.

**Progress:** the Windows runtime-core workflow and MA-1 source identity update
are accepted. This gate remains open because later MA-2/MA-3 behavior-bearing
changes must update source identity and pass the same workflow.

### MA-5 — Supervised real-model vertical slice

This stage waits until the benchmark no longer owns host resources and the user
explicitly authorizes the exact model and disposable target.

Perform observation, controlled qualification, Provider Binding, one invocation,
independent acceptance, candidate review, process-absence verification, and
return to disabled state.

**Gate:** exactly one disposable coding attempt reaches independently reviewable
candidate state; no publication occurs.

### MA-6 — Additional role admission

Add verifier and planner/Foreman requirements, settings, tool surfaces, and
role-specific qualification packets one at a time. Benchmark evidence may guide
model selection but does not replace ACL qualification.

## Resume point

**MA-1 is accepted. Resume at MA-2.** Compose the existing Worker Lab V3
dispatch boundary, framework dispatch adapter, bounded-file provider executor,
and Windows Job custody behind one explicit operator construction. Preserve the
no-default provider/model/binding/runner rule and prove the path with an injected
fake model runner before adding any real-provider command.

Before continuing, verify the working branch and read this file plus
`docs/CURRENT_STATE.md`. Do not begin MA-5 while the Local Model Bench campaign
is running.
