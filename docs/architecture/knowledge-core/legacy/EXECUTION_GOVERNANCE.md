# Knowledge Core Execution Governance

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Component:** Knowledge Core  
**Status:** active execution rule for bounded architecture and implementation tasks

---

# Purpose

This file defines task-execution rules that protect completed work from being lost when tool, context, or execution limits are approached.

It complements the architecture decisions in `DECISIONS.md` and the bounded build in `IMPLEMENTATION_PLAN_V1.md`.

---

# EG-001 — Documentation and checkpoint reserve

Every bounded task must reserve enough remaining tool capacity to complete its documentation and checkpoint duties before spending the rest of its allowance on implementation, investigation, or validation.

The reserve is part of the task budget, not optional cleanup.

A task is not considered complete until the durable project state records what was accomplished, what was validated, what remains unresolved, and the next authorized boundary.

## Required behavior

Before beginning substantial work, the executing agent should identify the expected completion writes/checks and preserve capacity for them.

At minimum, the reserve must be sufficient to:

1. update the controlling state/decision/handoff document;
2. record material architecture decisions or discovered failures that must survive the chat/session;
3. commit the intended changes;
4. verify the final branch/commit/diff state;
5. record the exact stop point and next separately authorized task.

If remaining tool capacity approaches the reserved completion budget, execution work must stop early enough to perform these checkpoint steps.

Partial implementation with a complete durable checkpoint is preferable to additional implementation that leaves the repository state undocumented or ambiguous.

## Prohibited behavior

Do not:

- consume the final available tool calls on optional investigation, refactoring, polish, or extra validation;
- defer documentation until after all implementation calls have been spent;
- rely on conversation context as the sole record of completed work;
- claim a task is complete when required state/handoff documentation could not be updated;
- begin the next task using capacity reserved for closing the current one.

## Reserve sizing

The exact number of calls may vary by tool/runtime, so this rule does not hard-code one universal numeric reserve.

For GitHub-centered tasks, planning should normally preserve capacity for at least:

- one state/document read if needed for a safe update;
- one or more documentation writes;
- one commit/ref operation when required by the workflow;
- one final branch/diff verification.

If the connector or task structure is known to require more calls, the reserve must be increased before execution begins.

## Mid-task decisions

Material decisions made during a long task should be checkpointed incrementally when practical rather than accumulating an unbounded amount of undocumented state for the end.

This does not require rewriting every architecture document after every small step. Use the smallest durable record that prevents loss, then perform a bounded synthesis when the phase is complete.

---

# EG-002 — Stop safely when capacity becomes uncertain

When the executing agent can no longer confidently complete both the remaining technical work and the required checkpoint with available tool capacity, it must prioritize the checkpoint.

The durable checkpoint should state:

- completed work;
- validation already performed;
- incomplete or unverified work;
- relevant commit/branch identity;
- exact restart point;
- next permitted action.

This is a normal safe-stop condition, not a failure requiring the agent to hide or overstate completion.

---

# Relationship to implementation

The Knowledge Core Kernel implementation must follow these execution-governance rules in addition to its 19 technical acceptance gates.

The final Kernel gate is therefore operational as well as technical: the repository must contain enough durable state that a fresh agent/session can continue without reconstructing the task from chat history.
