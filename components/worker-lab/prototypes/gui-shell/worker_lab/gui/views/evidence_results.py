"""Results / Evidence / Failures browser.

future: populate each RecordTable from
WorkerLabApplicationService.list_records(<"results"|"evidence"|"failures">) and each
DetailPane from .show_record(<collection>, identity); update the Evidence tab's
StateBadge from the record's verification_state on row selection.
"""
from __future__ import annotations

from tkinter import ttk

from worker_lab.gui.widgets.detail_pane import DetailPane
from worker_lab.gui.widgets.record_table import RecordTable
from worker_lab.gui.widgets.state_badge import StateBadge

_RESULT_COLUMNS = [
    ("invocation_id", "Invocation ID", 200),
    ("process_outcome", "Process Outcome", 140),
    ("first_failure_boundary", "First Failure Boundary", 200),
    ("retryable", "Retryable", 90),
]
_EVIDENCE_COLUMNS = [
    ("evidence_digest", "Evidence Digest", 160),
    ("evidence_type", "Evidence Type", 140),
    ("test_id", "Test ID", 90),
    ("verification_state", "Verification State", 140),
]
_FAILURE_COLUMNS = [
    ("failure_id", "Failure ID", 160),
    ("classification", "Classification", 160),
    ("first_failed_boundary", "First Failed Boundary", 200),
]


class EvidenceResultsView(ttk.Frame):
    """Tabbed read-only browser for results, evidence, and failures."""

    def __init__(self, master) -> None:
        super().__init__(master, style="View.TFrame")
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=16, pady=16)

        results_tab = ttk.Frame(notebook, style="View.TFrame")
        notebook.add(results_tab, text="Results")
        RecordTable(results_tab, _RESULT_COLUMNS).pack(fill="x", pady=(0, 12))
        DetailPane(results_tab).pack(fill="both", expand=True)

        evidence_tab = ttk.Frame(notebook, style="View.TFrame")
        notebook.add(evidence_tab, text="Evidence")
        RecordTable(evidence_tab, _EVIDENCE_COLUMNS).pack(fill="x", pady=(0, 8))
        selection = ttk.Frame(evidence_tab, style="View.TFrame")
        selection.pack(fill="x", pady=(0, 8))
        ttk.Label(selection, text="Selected verification state:", style="ViewBody.TLabel").pack(
            side="left", padx=(0, 8)
        )
        StateBadge(selection).pack(side="left")
        DetailPane(evidence_tab).pack(fill="both", expand=True)

        failures_tab = ttk.Frame(notebook, style="View.TFrame")
        notebook.add(failures_tab, text="Failures")
        RecordTable(failures_tab, _FAILURE_COLUMNS).pack(fill="x", pady=(0, 12))
        DetailPane(failures_tab).pack(fill="both", expand=True)
