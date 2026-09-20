# ACL Planner Handoff V1

Status: proposed model-facing execution handoff for the Task 7 Planner-contract repair.

This document defines only the Planner output used when Worker execution is required.
It does not replace the current Controller execution structures yet. Task 2 will parse
this handoff and translate it into the existing internal ACL structures.

## Purpose

Planner's job is to understand a larger request and turn it into an ordered series of
bounded Worker prompts.

Planner does not serialize ACL Controller state, select runtimes, grant authority, or
reproduce the internal ExecutionPlan schema.

The model-facing contract is intentionally small:

```text
STATUS: READY

OBJECTIVE:
<overall objective>

CONSTRAINTS:
<global constraints that apply to every task>

T01: <short task name>
<self-contained Worker prompt>

T02: <short task name>
<self-contained Worker prompt>

END_PLAN
```

## Required fields

### STATUS

For this execution handoff, the first nonblank line must be:

```text
STATUS: READY
```

Other Planner dispositions remain on the existing path until their repair task is
handled separately.

### OBJECTIVE

`OBJECTIVE:` is required.

Its body is free-form text extending until `CONSTRAINTS:` or the first Task heading.
It states the overall result the ordered Task sequence is intended to achieve.

The objective is semantic information. ACL must not invent or rewrite it during
parsing.

### CONSTRAINTS

`CONSTRAINTS:` is optional.

Its body is free-form text extending until the first Task heading. It contains global
instructions that apply to every Worker Task, such as scope boundaries, preservation
requirements, or explicit do-not-change instructions.

These are semantic constraints, not ACL authority grants. ACL may enforce stricter
policy than Planner states here.

### Tasks

At least one Task is required.

A Task begins only when a line starts with an ordered Task heading:

```text
T01:
T02:
T03:
```

The canonical heading form is:

```text
TNN: <short task name>
```

where `NN` is a zero-padded sequential number beginning with `01`.

Everything after one Task heading belongs to that Task's Worker prompt until the next
Task heading, `END_PLAN`, or end of file.

Example:

```text
T02: Implement calculator changes
Modify calculator.py according to the requirements identified in T01.
Preserve the module docstring. Add no imports.
```

The Task body must be a usable Worker prompt, not merely a label such as "fix bug" or
"run tests". It should contain enough local intent for the Worker to perform that
bounded step when combined with ACL-provided overall objective, global constraints,
and relevant prior Task results.

Planner owns the decomposition and Task wording.

ACL owns Task execution state.

## Ordering

V1 Task order is positional and sequential.

```text
T01 -> T02 -> T03 -> ...
```

Planner does not emit dependency arrays for this handoff.

ACL executes one Task at a time through the existing loop.

Task labels must:

- begin at `T01`
- increase by one
- not repeat
- appear at the beginning of a line

A string such as `"verify T01 behavior"` inside normal prose is not a Task heading.

## END_PLAN

`END_PLAN` is the preferred explicit terminator.

The parser must also accept end of file as the end of the final Task so a missing
terminator does not destroy an otherwise usable plan.

Text after `END_PLAN` is not part of any Task.

## Example: Task 7

```text
STATUS: READY

OBJECTIVE:
Update the calculator implementation to satisfy task_spec.txt and tax_rules.json,
and produce the required result.json output.

CONSTRAINTS:
Do not modify anything outside worker_probe_case2.
Preserve the calculator module docstring.
Add no imports.
Do not modify task_spec.txt or tax_rules.json.

T01: Inspect the calculator requirements
Read task_spec.txt, tax_rules.json, and calculator.py. Determine the exact required
behavior and identify the implementation changes needed. Do not modify files yet.
Return a concise finding that the next task can use.

T02: Implement the calculator change
Using the requirements and the result of T01, modify calculator.py to implement the
required tax_rate behavior, negative-rate rejection, subtotal calculation, tax
application, and configured rounding. Preserve the module docstring and add no imports.

T03: Create the required result file
Create result.json with the values required by task_spec.txt and tax_rules.json.
Do not modify the source requirement files.

T04: Verify the completed work
Check calculator.py and result.json against the supplied requirements. Confirm the
required behavior is represented and that no unrelated files were modified.

END_PLAN
```

## Information Planner does not emit in this handoff

The following are not part of Planner Handoff V1:

- ACL plan IDs or workflow IDs
- Pass state
- Task execution state
- runtime, model, provider, harness, server, or port
- token, timeout, retry, or continuation budgets
- authority grants
- ACL capability IDs
- ACL tool IDs
- read/write/create/delete permission arrays
- workspace serialization
- project metadata already known by ACL
- tracking boilerplate
- evidence boilerplate
- continuation boilerplate
- empty arrays or null placeholders
- dependency arrays
- internal reference IDs
- canonical ExecutionPlan serialization

ACL may derive or attach these mechanically after parsing where existing internal
components require them.

## Contract boundary

Planner owns:

- the overall objective
- global semantic constraints
- how the work is decomposed into ordered Tasks
- each Task name
- each Task's Worker prompt

ACL owns:

- parsing
- deterministic Task identity from T01/T02/etc.
- queue state
- execution order
- authority and policy enforcement
- workspace boundaries
- runtime selection
- persistence
- retries and continuation state
- audit and evidence state
- translation into existing internal Controller structures

The translation layer must not invent new semantic work. If the handoff is too
ambiguous to compile without inventing Planner intent, it must fail visibly rather
than guess.

## Task 1 acceptance criteria

Task 1 is complete when:

1. The execution handoff has one small, model-facing format.
2. Ordered T01/T02/... prompts remain Planner-owned.
3. The Task body can be extracted by line-delimited boundaries.
4. EOF can terminate the final Task.
5. Planner is not required to emit Controller bookkeeping.
6. No active runtime/parser behavior has been changed yet.
