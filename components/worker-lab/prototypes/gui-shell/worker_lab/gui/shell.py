"""Application shell: header, sidebar navigation, and swappable content area."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from worker_lab.gui import theme
from worker_lab.gui.views.attempts import AttemptsView
from worker_lab.gui.views.benchmark_advisory import BenchmarkAdvisoryView
from worker_lab.gui.views.definitions import DefinitionsView
from worker_lab.gui.views.evidence_results import EvidenceResultsView
from worker_lab.gui.views.invocations import InvocationsView
from worker_lab.gui.views.overview import OverviewView

_SECTIONS = (
    ("overview", "Overview", OverviewView),
    ("definitions", "Definitions", DefinitionsView),
    ("attempts", "Attempts", AttemptsView),
    ("invocations", "Invocations", InvocationsView),
    ("evidence_results", "Results / Evidence / Failures", EvidenceResultsView),
    ("benchmark_advisory", "Benchmark Evidence (Advisory)", BenchmarkAdvisoryView),
)


class AppShell(ttk.Frame):
    """Header + sidebar + swappable content area. Not wired to WorkerLabApplicationService yet."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, style="Shell.TFrame")
        theme.configure_styles(self)
        self._views: dict[str, ttk.Frame] = {}

        self._build_header()
        body = ttk.Frame(self, style="Shell.TFrame")
        body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        self._build_content(body)

        self.show_section("overview")

    def _build_header(self) -> None:
        header = ttk.Frame(self, style="Header.TFrame", height=58)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        ttk.Label(header, text="Worker Lab Console", style="HeaderTitle.TLabel").pack(side="left", padx=16)
        # future: bind this label to HealthDTO.execution_ready once wired
        ttk.Label(header, text="Execution: UNKNOWN", style="HeaderStatus.TLabel").pack(side="right", padx=16)

    def _build_sidebar(self, body: ttk.Frame) -> None:
        sidebar = ttk.Frame(body, style="Sidebar.TFrame", width=200)
        sidebar.pack(fill="y", side="left")
        sidebar.pack_propagate(False)
        for key, label, _ in _SECTIONS:
            ttk.Button(
                sidebar,
                text=label,
                style="Nav.TButton",
                command=lambda k=key: self.show_section(k),
            ).pack(fill="x", padx=8, pady=(8, 0))

    def _build_content(self, body: ttk.Frame) -> None:
        content = ttk.Frame(body, style="Content.TFrame")
        content.pack(fill="both", expand=True, side="left")
        for key, _, view_cls in _SECTIONS:
            view = view_cls(content)
            view.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._views[key] = view

    def show_section(self, key: str) -> None:
        view = self._views.get(key)
        if view is not None:
            view.tkraise()
