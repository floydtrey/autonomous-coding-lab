# Direct worker prompt template

Replace every `[FILL IN]` section. Attach `reference_gui.py` when the request is
to modify the existing GUI. Do not attach a hidden comparison image or desired
answer unless reproducing that image is explicitly the task.

---

You are modifying a disposable, single-file Python Tkinter GUI prototype.

## Starting file

`reference_gui.py` is attached and is the only file authorized for modification.

## Requested result

[FILL IN: Describe what you want the user to see or what behavior should change.]

## Exact change

[FILL IN: Identify the element, action, direction, or dimension to change.]

## Reference point

[FILL IN: State what the change is relative to—for example, the content panel,
application window, map viewport, selected widget, or button group.]

## Preserve

[FILL IN: List layout, position, size, colors, text, behavior, or unrelated code
that must remain unchanged.]

## Acceptance checks

- [FILL IN: A visible or testable condition that proves the change is correct.]
- [FILL IN: A condition that proves unrelated behavior was preserved.]

## Ambiguity rule

If the request does not identify enough information to make the change safely,
stop and ask concise clarification questions instead of guessing.

## Worker output

Modify only the authorized file. Return the complete revised file if you cannot
edit it directly. Also provide a short summary of what changed and any checks
performed. Do not add model connections, filesystem operations, networking,
dependencies, or unrelated features.
