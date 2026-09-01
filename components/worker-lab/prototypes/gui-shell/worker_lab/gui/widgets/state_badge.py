"""Colored label for lifecycle/verification states. Renders a neutral placeholder until wired."""
from __future__ import annotations

import tkinter as tk

from worker_lab.gui import theme


class StateBadge(tk.Label):
    """Displays AttemptState / InvocationState / evidence verification_state as a colored badge."""

    def __init__(self, master, state: str | None = None) -> None:
        super().__init__(master, font=("Segoe UI", 9, "bold"), padx=8, pady=2)
        self.set_state(state)

    def set_state(self, state: str | None) -> None:
        """Future hook: called with the record's current state once wired to the service."""
        self.configure(text=state if state else "—", background=theme.state_badge_color(state), foreground=theme.TEXT)
