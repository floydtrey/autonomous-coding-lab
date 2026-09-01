"""Invocation list, detail, and static lifecycle stepper.

future: populate the RecordTable from WorkerLabApplicationService.list_records("invocations"),
the DetailPane from .show_record("invocations", invocation_id), and update the selected-state
badge from the record's InvocationState on row selection.
"""
from __future__ import annotations

from tkinter import ttk

from worker_lab.gui.widgets.detail_pane import DetailPane
from worker_lab.gui.widgets.record_table import RecordTable
from worker_lab.gui.widgets.state_badge import StateBadge

_COLUMNS = [
    ("invocation_id", "Invocation ID", 200),
    ("state", "State", 120),
    ("attempt_id", "Attempt ID", 200),
    ("operation", "Operation", 140),
    ("model", "Model", 140),
]

# PREPARED -> AUTHORIZED -> DISPATCHING -> {COMPLETED, UNCERTAIN, REJECTED, ABORTED}
_LIFECYCLE = ("PREPARED", "AUTHORIZED", "DISPATCHING", "COMPLETED / UNCERTAIN / REJECTED / ABORTED")


class InvocationsView(ttk.Frame):
    """Read-only invocation list, lifecycle stepper reference, and detail pane."""

    def __init__(self, master) -> None:
        super().__init__(master, style="View.TFrame")
        ttk.Label(self, text="Invocations", style="ViewTitle.TLabel").pack(anchor="w", padx=16, pady=(16, 4))
        RecordTable(self, _COLUMNS).pack(fill="x", padx=16)

        stepper = ttk.Frame(self, style="View.TFrame")
        stepper.pack(fill="x", padx=16, pady=(12, 12))
        for index, name in enumerate(_LIFECYCLE):
            ttk.Label(stepper, text=name, style="ViewBody.TLabel").pack(side="left")
            if index < len(_LIFECYCLE) - 1:
                ttk.Label(stepper, text=" → ", style="ViewBody.TLabel").pack(side="left")

        selection = ttk.Frame(self, style="View.TFrame")
        selection.pack(fill="x", padx=16)
        ttk.Label(selection, text="Selected invocation state:", style="ViewBody.TLabel").pack(side="left", padx=(0, 8))
        StateBadge(selection).pack(side="left")

        DetailPane(self).pack(fill="both", expand=True, padx=16, pady=(12, 16))
