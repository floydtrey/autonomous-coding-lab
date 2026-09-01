# GUI prompt-learning experiment

This is a deliberately small, disconnected experiment. It does not call a
model, edit Worker Lab, read MineTracker, or collect live metrics.

## Files

- `reference_gui.py` — static Tkinter GUI that can be copied into disposable
  test folders.
- `direct-worker-template.md` — fill this out and send it directly to a worker.
- `planner-template.md` — fill this out and send it with the GUI to a Planner;
  if ready, copy the Planner's final `WORKER PROMPT` to the worker.

## Manual comparison

1. Copy `reference_gui.py` into a fresh folder for each attempt.
2. Save the exact filled-in prompt beside that copy.
3. Keep direct-worker and Planner-assisted attempts separate.
4. Inspect generated Python before running it; model output is untrusted code.
5. Run the reference and candidate GUIs side by side.
6. Record what changed, what was misunderstood, and which wording would have
   prevented the misunderstanding.

No automation is required until the model roles and prompt formats are chosen.
