"""Attempt list, detail, and static lifecycle stepper.

future: populate the RecordTable from WorkerLabApplicationService.list_records("attempts"),
the DetailPane from .show_record("attempts", attempt_id), and update the selected-state
badge from the record's AttemptState on row selection.
"""
from __future__ import annotations

from tkinter import ttk

from worker_lab.gui.widgets.detail_pane import DetailPane
from worker_lab.gui.widgets.record_table import RecordTable
from worker_lab.gui.widgets.state_badge import StateBadge

_COLUMNS = [
    ("attempt_id", "Attempt ID", 200),
    ("state", "State", 120),
    ("exercise_id", "Exercise ID", 160),
    ("sandbox_mode", "Sandbox Mode", 120),
    ("updated_at", "Updated At", 160),
]

# DRAFT -> READY -> RUNNING -> CANDIDATE -> EVALUATING -> {PASSED, FAILED, NEEDS_REVIEW} -> CLOSED
_LIFECYCLE = ("DRAFT", "READY", "RUNNING", "CANDIDATE", "EVALUATING", "PASSED / FAILED / NEEDS_REVIEW", "CLOSED")


class AttemptsView(ttk.Frame):
    """Read-only attempt list, lifecycle stepper reference, and detail pane."""

    def __init__(self, master) -> None:
        super().__init__(master, style="View.TFrame")
        ttk.Label(self, text="Attempts", style="ViewTitle.TLabel").pack(anchor="w", padx=16, pady=(16, 4))
        RecordTable(self, _COLUMNS).pack(fill="x", padx=16)

        stepper = ttk.Frame(self, style="View.TFrame")
        stepper.pack(fill="x", padx=16, pady=(12, 0))
        for index, name in enumerate(_LIFECYCLE):
            ttk.Label(stepper, text=name, style="ViewBody.TLabel").pack(side="left")
            if index < len(_LIFECYCLE) - 1:
                ttk.Label(stepper, text=" → ", style="ViewBody.TLabel").pack(side="left")
        ttk.Label(self, text="ABORTED is reachable from any non-terminal state", style="ViewBody.TLabel").pack(
            anchor="w", padx=16, pady=(0, 12)
        )

        selection = ttk.Frame(self, style="View.TFrame")
        selection.pack(fill="x", padx=16)
        ttk.Label(selection, text="Selected attempt state:", style="ViewBody.TLabel").pack(side="left", padx=(0, 8))
        StateBadge(selection).pack(side="left")

        DetailPane(self).pack(fill="both", expand=True, padx=16, pady=(12, 16))
