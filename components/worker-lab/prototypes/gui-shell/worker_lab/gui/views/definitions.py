"""Curricula / Exercises / Roles / Policies browser.

future: populate each RecordTable from
WorkerLabApplicationService.list_records(<collection>) and each DetailPane from
.show_record(<collection>, identity) on row selection.
"""
from __future__ import annotations

from tkinter import ttk

from worker_lab.gui.widgets.detail_pane import DetailPane
from worker_lab.gui.widgets.record_table import RecordTable

_TABS: dict[str, list[tuple[str, str, int]]] = {
    "Curricula": [
        ("curriculum_id", "Curriculum ID", 160),
        ("status", "Status", 80),
        ("title", "Title", 240),
        ("capabilities", "Capabilities", 100),
    ],
    "Exercises": [
        ("exercise_id", "Exercise ID", 160),
        ("version", "Version", 70),
        ("curriculum_id", "Curriculum ID", 140),
        ("sandbox_mode", "Sandbox Mode", 120),
        ("objective", "Objective", 260),
    ],
    "Roles": [
        ("role_id", "Role ID", 140),
        ("version", "Version", 70),
        ("purpose", "Purpose", 320),
    ],
    "Policies": [
        ("policy_id", "Policy ID", 140),
        ("version", "Version", 70),
        ("invariant_count", "Invariants", 100),
    ],
}


class DefinitionsView(ttk.Frame):
    """Tabbed read-only browser for curriculum, exercise, role, and policy definitions."""

    def __init__(self, master) -> None:
        super().__init__(master, style="View.TFrame")
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=16, pady=16)
        for name, columns in _TABS.items():
            tab = ttk.Frame(notebook, style="View.TFrame")
            notebook.add(tab, text=name)
            RecordTable(tab, columns).pack(fill="x", pady=(0, 12))
            DetailPane(tab).pack(fill="both", expand=True)
