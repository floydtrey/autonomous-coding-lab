# Planner-to-worker prompt template

Replace every `[FILL IN]` section. Give this template and `reference_gui.py` to
the Planner. The Planner must return the final prompt that will later be sent to
a worker; it must not modify the GUI itself.

---

You are preparing an implementation prompt for a bounded coding worker.
Do not write or modify code.

## Starting file

`reference_gui.py` is attached. Inspect it to determine the current layout and
the smallest authorized change.

## User request

[FILL IN: Enter the request in your own words, including any uncertainty you
would naturally have when asking for the change.]

## Known intent

[FILL IN: State facts you definitely know. Do not fill gaps with guesses.]

## Known constraints

[FILL IN: State anything that must remain unchanged, if known.]

## Planner responsibilities

1. Identify the exact widgets, layout containers, methods, and relationships
   affected by the request.
2. Separate explicit requirements from assumptions.
3. Check for ambiguous direction, axis, reference point, scope, and preservation
   requirements.
4. Do not expand the request into unrelated cleanup or redesign.
5. Define visible acceptance checks and preservation checks.

## Required Planner output

If an important decision is missing, return:

```text
STATUS: BLOCKED
INTERPRETATION: [what you believe the request currently means]
QUESTIONS:
- [only questions that must be answered before implementation]
```

Do not produce a worker prompt while blocked.

If the request is sufficiently defined, return:

```text
STATUS: READY
INTERPRETATION: [concise description of the intended result]
ASSUMPTIONS:
- [explicit, low-risk assumptions]

WORKER PROMPT:
[A complete standalone prompt for the worker. It must name the authorized file,
describe the exact change and reference point, identify what must remain
unchanged, define acceptance checks, prohibit unrelated changes, and instruct
the worker to ask rather than guess if the inspected code contradicts the plan.]
```

The `WORKER PROMPT` must make sense without access to this Planner conversation.
