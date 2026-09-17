# V1 job plans and bounded admission

S02 originally defined `worker-lab-job-plan:v1` in `worker_lab/job_plan.py`.
S05b now requires schema V2 with an explicit [V1 output-acceptance contract](OUTPUT_ACCEPTANCE_V1.md)
in `required_outputs`; old label lists reject rather than receiving inferred semantics. S03 adds a
standalone iterative dependency-cycle check in that module. S04 adds the
admission-only `worker-lab-job-task:v1` bridge in `worker_lab/job_admission.py`.
There is no scheduler, Foreman, sequential controller, or new worker runner.

## Plan contract

A plan has a schema, `plan_id`, positive integer `revision`, an objective, and
nonempty tasks. The objective binds `objective_id`, user text, and a logical
`target:<id>`; a checkout path cannot stand in for that target identity.

Every task binds:

- `task_id`, description, and explicit dependency IDs;
- acceptance criteria with stable `criterion_id`, nonblank description, and
  protected catalog `test_ids`;
- `authority_ref` with profile ID, version, and exact SHA-256 digest;
- versioned `required_outputs` distinguishing writable permission, required
  changes/files, result evidence, and explicit no-op permission;
- a budget with positive `max_attempts` and `max_wall_seconds`.

Unknown/missing fields, duplicate task or criterion IDs, missing dependencies,
malformed criteria and invalid budgets reject. Dependencies, task IDs, criterion
IDs, and set-like fields are canonicalized deterministically. Direct or indirect
cycles reject with `JOB_PLAN_DEPENDENCY_CYCLE` and a concrete path, where each
task depends on the next. The validator does not generate an execution schedule.

Parsed plans and their nested values are frozen. Canonical JSON determines the
plan digest. Changing any approved value requires a new revision and approval;
admission refuses replacement of a stored revision with different content.
Approval is supplied by the trusted operator/controller boundary as
`approved_by` and `approved_plan_digest`. Parsing JSON alone is not approval,
authentication, Provider Binding, or execution authority.

## Authority and admission

`WorkerLabApplicationService.admit_job_task(plan, task_id, target_repository,
approved_by=..., approved_plan_digest=...)` resolves the profile from
`<lab>/job-authorities/<profile_id>/v<version>.json`. This is a protected
operator-installed input, never generated from worker requests.

The `worker-lab-job-authority:v1` profile pins the logical target, policy, role,
context manifest, catalog, exact writable/protected paths, test profiles, and
capability restrictions. The profile digest covers the complete bundle. Admission
checks the approved plan digest, exact profile reference, target, criterion test
coverage, required outputs, authority compatibility, clean Git source state, and
exact context bytes before creating a DRAFT attempt. Existing files named as
writable scope must be files, not directories. No credentials are stored here.

Job attempts use the reserved `JOBTASK-` prefix and retain their complete typed
definition under `state/job-tasks/<attempt_id>.json`; approved plans are retained
under `state/job-plans/<plan_id>/v<revision>.json`. Missing job definitions fail
closed rather than falling back to exercise loading. Existing exercise admission
remains available and retains its existing behavior.

The narrow adapter reuses the existing bounded-definition validator in memory.
It creates no curriculum or exercise files. To preserve Invocation V3 and packet
V1, legacy `exercise_id`/`exercise_version` fields carry a deterministic job-task
key/revision, while `curriculum_id` carries a deterministic job key. These keys
are not curriculum membership. The definition/task digests seal the entire job
plan, task, criteria/test IDs, outputs, budget, approval, and authority bundle.

The admitted attempt can use existing workspace preparation, Controller Task
Packet canonicalization, and the existing invocation preparation machinery.
S05b emits Invocation V4 with the sealed output contract and dispatch task V3.
S05 permits self-contained
tasks to use `no_context=True`, producing a V2 packet with explicit `context_mode:
"none"` and zero evidence items. Existing evidence-bearing V1 packets remain
valid. No KC search response is fabricated. See [Controller Task Packet](CONTROLLER_TASK_PACKET_V1.md).
V3 preparation checks the approved logical target and
recorded controller identity and retains the existing explicit Provider Binding
and source-identity gates.

S04 stops at PREPARED. Job invocation authorization rejects with
`JOB_TASK_EXECUTION_NOT_IMPLEMENTED` until a later execution gate implements
dependency readiness and budget enforcement. Admission is not permission to run
dependent work, spend a budget, or start workers. Those fields are preserved now
without adding scheduling or enforcement machinery. No provider is qualified by
the deterministic test fixtures.

## Canonical fixtures and checks

`components/worker-lab/tests/fixtures/two-task-job-plan.json` has tasks A and B,
with B depending on A. The adjacent `record-model-authority.json` and
`record-docs-authority.json` are complete, digest-pinned synthetic authority
fixtures. `tests/job_fixture.py` recreates their exact disposable Git baseline.
They specify authority without inventing it at admission time; they are not live
deployment profiles or provider qualification records. When a predecessor changes
the baseline, later work needs an explicitly reviewed context/profile and plan
revision before execution; admission does not silently rebase approved authority.

Run from `components/worker-lab`:

```text
python -m pytest -q tests/test_job_plan.py tests/test_job_admission.py
```

The focused tests cover parsing, revision identity, deterministic cycle errors,
authority resolution and substitution rejection, immutable stored revisions,
and the first canonical task through packet/V3 preparation without curriculum
records. The full Worker Lab suite retains exercise-backed regression coverage.
