"""Local Model Bench advisory evidence view.

Local Model Bench is advisory-only infrastructure; it is not part of the Worker Lab
lifecycle and cannot authorize or execute work (see docs/ARCHITECTURE.md). This view is
styled distinctly from the authoritative Worker Lab state views above.

future: LMB has no shared application-service DTO yet, so wiring here is undecided;
this view stays a freeform placeholder until that decision is made.
"""
from __future__ import annotations

from tkinter import ttk

from worker_lab.gui.widgets.record_table import RecordTable

_COLUMNS = [
    ("run_id", "Run ID", 160),
    ("model", "Model", 160),
    ("suite", "Suite", 160),
    ("summary", "Summary", 260),
]


class BenchmarkAdvisoryView(ttk.Frame):
    """Advisory Local Model Bench run/model/result summaries, visually distinct from Worker Lab state."""

    def __init__(self, master) -> None:
        super().__init__(master, style="View.TFrame")
        ttk.Label(
            self,
            text="Advisory evidence — not authoritative for Worker Lab state",
            style="Advisory.TLabel",
        ).pack(fill="x", padx=16, pady=(16, 8))
        ttk.Label(self, text="Local Model Bench Evidence", style="ViewTitle.TLabel").pack(
            anchor="w", padx=16, pady=(0, 4)
        )
        RecordTable(self, _COLUMNS).pack(fill="both", expand=True, padx=16, pady=(0, 16))
