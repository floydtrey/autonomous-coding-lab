# M08 — accepted local snapshots and downstream input

The controller can promote an exact M06 acceptance into a separate clean local
repository. `promote_accepted_task` rechecks the accepted candidate, stopped-worker
and validator evidence, review and retained diff. It copies a file inventory bound
to the accepted content digest and commits only the accepted changes. Ignored new
files remain part of the inventory. Promotion does not require a candidate ZIP.
An accepted no-op retains the base commit without making an empty commit.

The worker candidate and its original HEAD remain unchanged. The artifact root is
operator-supplied and separate from protected lab state and worker workspaces.
There is no remote publication, worker commit/push tool or automatic upgrade of a
running ACL installation. Supported model/context settings remain configurable.

The protected state records `snapshot-intents`, `snapshot-prepared` and
`accepted-snapshots`. Each final receipt binds acceptance, candidate, source base,
snapshot commit, exact source bytes and checkout metadata. Git uses the existing
sanitized helpers. Changed metadata is rejected before Git inspection; replacement
refs and grafts cannot supply false ancestry. Checkout attributes preserve source
line endings and literal Unicode or special filenames.

Repeated promotion verifies and returns the same artifact. A published repository
with a matching embedded and protected prepared receipt can finish bookkeeping
after interruption. An incomplete stage or missing proof blocks; it never creates
a replacement commit by guessing. Completed artifacts can be verified without
retaining the original mutable worker candidate. Artifact drift blocks handoff.

The service exposes `promote_accepted_task`, `attach_job_artifact` and
`prepare_job_input`. After M07 reserves the next task, `prepare_job_input` selects a
verified snapshot whose real Git history contains all previously accepted outputs.
It returns no overlay for the first task. Missing promotions or divergent histories
block; there is no automatic merge. Attaching an artifact never changes acceptance.

A downstream input record preserves the original approved plan and authority
profile. It changes only the starting commit and hashes of the existing context
files, using the verified snapshot inventory. Read/write scope, context membership
and purposes, policy, role, checks and output obligations remain approved as before.
The input is stored at a content-addressed `job-inputs` reference and embedded in
the version 2 job-task definition. Version 1 definitions remain supported for the
initial base.

Pass the returned `input_binding` and its repository to `admit_job_task`, then use
the existing `prepare_workspace` operation. Admission and preparation both verify
the exact snapshot source. Preparation retains the entire accepted source tree,
including files outside the next task's context. Binding the prepared invocation to
the M07 reservation verifies the same accepted lineage; substituting the original
template or another accepted branch cannot authorize the task.

This is the M08 publication and preparation API. The assembled sequential execution
commands and job deadline supervision remain M09 work. Generic job execution stays
disabled until that integration is complete. M08 verification uses deterministic
worker outcomes with real local Git and protected checks; it makes no new real-model
or complete sequential-run claim.
