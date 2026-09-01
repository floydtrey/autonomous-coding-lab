"""Reusable read-only record detail widget: title, key/value grid, collapsible raw record."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class DetailPane(ttk.Frame):
    """Shows a selected record's fields plus a collapsible raw-record viewer. Empty by default."""

    def __init__(self, master) -> None:
        super().__init__(master, style="View.TFrame")
        self.title_label = ttk.Label(self, text="No record selected", style="ViewTitle.TLabel")
        self.title_label.pack(anchor="w", pady=(0, 8))

        self.fields_frame = ttk.Frame(self, style="View.TFrame")
        self.fields_frame.pack(fill="x")

        self._raw_visible = False
        self._raw_toggle = ttk.Button(self, text="Show raw record", command=self._toggle_raw)
        self._raw_toggle.pack(anchor="w", pady=(8, 0))

        self.raw_text = tk.Text(self, height=8, state="disabled", wrap="word")
        # future: populate from RecordDetailDTO.record once wired

    def _toggle_raw(self) -> None:
        self._raw_visible = not self._raw_visible
        if self._raw_visible:
            self.raw_text.pack(fill="both", expand=True, pady=(4, 0))
            self._raw_toggle.configure(text="Hide raw record")
        else:
            self.raw_text.pack_forget()
            self._raw_toggle.configure(text="Show raw record")

    def set_fields(self, fields: list[tuple[str, str]]) -> None:
        """Future hook: populate key/value rows once wired to a RecordDetailDTO summary."""
        for child in self.fields_frame.winfo_children():
            child.destroy()
        for row, (key, value) in enumerate(fields):
            ttk.Label(self.fields_frame, text=key, style="ViewBody.TLabel").grid(
                row=row, column=0, sticky="w", padx=(0, 12)
            )
            ttk.Label(self.fields_frame, text=value, style="ViewBody.TLabel").grid(row=row, column=1, sticky="w")
