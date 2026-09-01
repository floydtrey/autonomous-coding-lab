"""Entry point for the Worker Lab Console desktop shell (design phase, not yet wired)."""
from __future__ import annotations

import tkinter as tk

from worker_lab.gui.shell import AppShell


def main() -> None:
    root = tk.Tk()
    root.title("Worker Lab Console")
    root.minsize(820, 600)
    root.geometry("960x660")
    # future: construct WorkerLabApplicationService(root_path) here and pass it into AppShell
    AppShell(root).pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()
