"""Color, font, and ttk style constants shared by every Worker Lab Console widget."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

BACKGROUND = "#17191d"
PANEL = "#22252b"
TEXT = "#f2f2f2"
MUTED_TEXT = "#9a9ea6"
ACCENT = "#4c8dff"

NEUTRAL_BADGE = "#5a5f68"

# Attempt states, invocation states, and evidence verification_state share one color map.
STATE_COLORS: dict[str, str] = {
    "DRAFT": "#5a5f68",
    "READY": "#4c8dff",
    "RUNNING": "#e0a83e",
    "CANDIDATE": "#a06be0",
    "EVALUATING": "#e0a83e",
    "PASSED": "#3fae5c",
    "FAILED": "#d1503f",
    "NEEDS_REVIEW": "#d19a3f",
    "CLOSED": "#5a5f68",
    "ABORTED": "#d1503f",
    "PREPARED": "#5a5f68",
    "AUTHORIZED": "#4c8dff",
    "DISPATCHING": "#e0a83e",
    "COMPLETED": "#3fae5c",
    "UNCERTAIN": "#d19a3f",
    "REJECTED": "#d1503f",
    "unverified": "#5a5f68",
    "verified": "#3fae5c",
    "invalid": "#d1503f",
}


def state_badge_color(state: str | None) -> str:
    """Return the badge color for a lifecycle/verification state, gray if unknown or unset."""
    if state is None:
        return NEUTRAL_BADGE
    return STATE_COLORS.get(state, NEUTRAL_BADGE)


def configure_styles(widget: tk.Misc) -> None:
    """Register the shared ttk styles used by the shell and every view."""
    style = ttk.Style(widget)
    style.configure("Shell.TFrame", background=BACKGROUND)
    style.configure("Header.TFrame", background=PANEL)
    style.configure("Sidebar.TFrame", background=PANEL)
    style.configure("Content.TFrame", background=BACKGROUND)
    style.configure("HeaderTitle.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 14, "bold"))
    style.configure("HeaderStatus.TLabel", background=PANEL, foreground=MUTED_TEXT, font=("Segoe UI", 10))
    style.configure("Nav.TButton", font=("Segoe UI", 10))
    style.configure("View.TFrame", background=BACKGROUND)
    style.configure("ViewTitle.TLabel", background=BACKGROUND, foreground=TEXT, font=("Segoe UI", 13, "bold"))
    style.configure("ViewBody.TLabel", background=BACKGROUND, foreground=MUTED_TEXT, font=("Segoe UI", 10))
    style.configure("EmptyState.TLabel", background=BACKGROUND, foreground=MUTED_TEXT, font=("Segoe UI", 9, "italic"))
    style.configure("Advisory.TLabel", background="#3a2f12", foreground="#e0c060", font=("Segoe UI", 9, "bold"))
