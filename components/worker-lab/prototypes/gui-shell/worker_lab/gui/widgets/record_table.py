"""Reusable read-only record list widget (Treeview wrapper). Renders empty until wired."""
from __future__ import annotations

from tkinter import ttk


class RecordTable(ttk.Frame):
    """Displays record summaries in columns. No rows are shown until ``set_rows`` is called."""

    def __init__(self, master, columns: list[tuple[str, str, int]]) -> None:
        super().__init__(master, style="View.TFrame")
        column_ids = [key for key, _, _ in columns]
        self.tree = ttk.Treeview(self, columns=column_ids, show="headings", height=8)
        for key, label, width in columns:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True, side="top")

        self._empty_state = ttk.Label(self, text="No data source connected", style="EmptyState.TLabel")
        self._empty_state.pack(fill="x", pady=(4, 0))

    def set_rows(self, rows: list[tuple]) -> None:
        """Future hook: replace displayed rows once wired to WorkerLabApplicationService.list_records()."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            self.tree.insert("", "end", values=row)
        self._empty_state.configure(text="" if rows else "No data source connected")
