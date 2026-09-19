# M09D — assembled M09 acceptance and closure

**Status:** complete as a closure/acceptance slice.  
**Behavior-bearing controller head:** `d068e012cf34851c761ee58bbfc24d1ca883239b`.

M09D adds no new production behavior. M09A–M09C already implemented the complete M09 surface, and the operator verified that exact behavior-bearing head on the intended Windows host. M09D closes the milestone by binding the existing acceptance evidence to the M09 done criteria and correcting the queue status. M10 remains separate real-work proof.

## M09 assembled surface

The assembled controller exposes:

- `run <plan-file>`
- `status <job-id>`
- `stop <job-id>`
- `reconcile <job-id>`

The sequential path remains:

`select → prepare/authorize → run-task → accept/block → promote → advance`

No M09D change adds automatic corrective retries, model switching, session continuation, compaction, KC behavior, planner behavior, or M10 execution.

## Acceptance evidence

| M09 requirement | Existing durable proof |
|---|---|
| A deterministic two-task job runs in order and B consumes accepted A | `test_m09b_sequential_controller.py::test_two_tasks_run_in_order_and_status_is_read_only` |
| CLI `run` uses the same sequential service path | `test_m09b_sequential_controller.py::test_run_cli_uses_the_same_sequential_service_path` |
| Status is read-only and exposes evidence gaps | `test_two_tasks_run_in_order_and_status_is_read_only`; `test_status_reports_drifted_evidence_without_mutating_job` |
| Failed validation blocks A, suppresses B, and prevents objective completion | `test_m09b_sequential_controller.py::test_failed_a_blocks_b_without_promotion_or_second_worker` |
| Interrupted promotion does not advance B or repeat unverified promotion | `test_m09b_sequential_controller.py::test_interrupted_promotion_never_reserves_b_or_repeats_promotion` |
| Existing active reservation is not silently replaced | `test_m09b_sequential_controller.py::test_existing_active_reservation_is_not_replaced` |
| Stop request is exact, reservation-bound, idempotent, and visible | `test_m09c_stop_reconcile.py::test_stop_request_is_exact_idempotent_and_visible` |
| Reconcile does not invent replacement work for an unstarted reservation | `test_m09c_stop_reconcile.py::test_reconcile_unstarted_reservation_blocks_without_replacement` |
| Accepted A can be reconciled/promoted without rerunning A; later explicit run advances B | `test_m09c_stop_reconcile.py::test_reconcile_finishes_accepted_promotion_without_rerunning_a` |
| Retained accepted task-run evidence can be reconciled without rerunning A; B remains unstarted until explicit run | `test_m09c_stop_reconcile.py::test_reconcile_records_retained_accepted_run_then_waits_for_explicit_run` |
| CLI `stop` and `reconcile` route through the same service boundary | `test_m09c_stop_reconcile.py::test_stop_and_reconcile_cli_route_through_service` |
| Reservation deadline, worker/validator budget containment, and telemetry are bound and retained | focused M09A coverage in `test_m09a_job_execution.py` |

## Intended-host verification retained for closure

At the behavior-bearing M09C head `d068e012cf34851c761ee58bbfc24d1ca883239b`, the operator ran:

- the formerly failing focused CLI fixture after its deterministic-clock correction: **1 passed**;
- the M09C + M09B + M09A and directly affected job/controller/supervision/workflow/validation regression batch: **111 passed**;
- portable-source verification: **3 passed**.

The only earlier failure was a test-fixture clock mismatch in the CLI-routing test. The fixture was corrected without changing M09C stop/reconcile semantics, and the complete affected batch then passed.

M09D changes documentation only, so it does not alter the production source identity that those tests exercised.

## Closure statement

M09 is closed at its stated acceptance boundary:

- sequential execution exists;
- accepted output is the only downstream base;
- failed validation cannot advance a dependent task;
- status reports retained evidence and blockers;
- stop is bound to the owned reservation;
- reconcile is conservative and does not silently rerun accepted work;
- the CLI/service surfaces reuse the existing single-task execution and acceptance machinery.

This closure does **not** claim M10 real-model/two-task proof, exact Pi session reopen, forced compaction, automatic retries, planner/Foreman behavior, KC integration, or the later contextual ACL refactor.

M10, if performed, remains a separate real-work qualification milestone.
