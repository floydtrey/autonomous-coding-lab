# M07 — durable job selection

The controller stores one aggregate for an explicitly approved existing job plan.
The aggregate pins the plan revision and digest, controller identity, dependencies,
task states, attempt reservations, results, acceptance records and optional accepted
snapshot references. It uses the existing plan and authority validators.

`WorkerLabApplicationService` exposes `create_job`, `read_job`,
`reserve_next_job_task`, `bind_job_attempt` and `record_job_task_result`. These
operations do not launch a worker. Creating a job requires the exact approved plan
digest. Selection requires the current job digest and records one reservation before
the caller admits or prepares the selected task. A prepared invocation is bound to
that reservation before any future authorization. A reservation cannot be replaced
with another attempt or duplicated by replay.

Selection follows the approved plan's deterministic order and requires every
prerequisite's protected M06 acceptance record. Worker completion and passing check
labels do not count as acceptance. Failed, blocked and unresolved review outcomes
suppress dependent tasks. Recording a result reloads the durable M06 report and
revalidates successful acceptance; callers cannot provide a success verdict.

The controller/job lock and expected record digest exclude competing decisions.
The reservation survives restart. Task attempt limits and wall-time deadlines are
recorded from the approved plan. Uncertain worker or validator state blocks further
selection. Atomic replacement of the aggregate does not make all the attempt,
invocation, outcome and acceptance files transactional: missing or inconsistent
cross-record evidence requires attention and cannot justify another launch.

M07 is a coordination API, not the assembled sequential runner. Job-task execution
remains disabled by the existing authorization boundary until M09 connects the
reserved deadline to worker and validator supervision. M08 supplies verified local
snapshots and downstream source preparation. The sequential `run`, `status`, `stop`
and `reconcile` commands remain M09 work; no automatic retry or parallel scheduler
is introduced here.

Verification: 39 focused job/plan tests and 10 existing job-admission regressions
passed. Coordinator cases use deterministic M06-boundary fixtures; no model was
launched for M07. Source identities are refreshed for this checkpoint.
