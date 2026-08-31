"""Static GUI reference for prompt-interpretation experiments.

This prototype deliberately has no model, filesystem, project, or Worker Lab
integration. It is only a small visual target that can be copied and modified
in disposable test folders.
"""

import tkinter as tk


BACKGROUND = "#17191d"
PANEL = "#22252b"
BORDER = "#343840"
TEXT = "#f2f2f2"
MUTED = "#9aa2ac"
ACCENT = "#4678bd"


class PromptTestGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Worker Lab - Prompt Test Reference")
        self.geometry("960x660")
        self.minsize(820, 600)
        self.configure(bg=BACKGROUND)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_sidebar()
        self._build_content()
        self._build_status_bar()

    def _build_header(self):
        header = tk.Frame(self, bg="#111317", height=58)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_propagate(False)

        tk.Label(
            header,
            text="WORKER LAB",
            bg="#111317",
            fg=TEXT,
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left", padx=18)

        tk.Label(
            header,
            text="Prompt Interpretation Test",
            bg="#111317",
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(side="right", padx=18)

    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg="#1d2025", width=180)
        sidebar.grid(row=1, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        for label in ("Overview", "Projects", "Workers", "Results"):
            tk.Button(
                sidebar,
                text=label,
                anchor="w",
                bg="#1d2025",
                fg="#d9dde3",
                activebackground="#30343b",
                activeforeground=TEXT,
                relief="flat",
                bd=0,
                padx=18,
                pady=12,
                font=("Segoe UI", 10),
            ).pack(fill="x")

    def _card(self, parent):
        return tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

    def _build_content(self):
        content = tk.Frame(self, bg=BACKGROUND)
        content.grid(row=1, column=1, sticky="nsew")

        tk.Label(
            content,
            text="GUI Prompt Test",
            bg=BACKGROUND,
            fg=TEXT,
            font=("Segoe UI", 19, "bold"),
        ).pack(anchor="w", padx=24, pady=(24, 4))

        tk.Label(
            content,
            text="A static reference used to compare how different prompts are interpreted.",
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=24, pady=(0, 18))

        body = tk.Frame(content, bg=BACKGROUND)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        summary = self._card(body)
        summary.pack(fill="x", pady=(0, 12))

        tk.Label(
            summary,
            text="Reference Project",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=16, pady=(14, 5))

        tk.Label(
            summary,
            text="Mine Inspection and Asset Tracker",
            bg=PANEL,
            fg="#c8cdd4",
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=16)

        tk.Label(
            summary,
            text="This display is sample data only. No project is connected.",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=16, pady=(4, 14))

        preview = self._card(body)
        preview.pack(fill="both", expand=True)

        tk.Label(
            preview,
            text="Layout Preview",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=16, pady=(14, 10))

        display = tk.Frame(preview, bg="#2b3037", height=190)
        display.pack(fill="both", expand=True, padx=16)
        display.pack_propagate(False)

        tk.Label(
            display,
            text="CONTENT AREA",
            bg="#2b3037",
            fg="#737c87",
            font=("Segoe UI", 14, "bold"),
        ).place(relx=0.5, rely=0.45, anchor="center")

        actions = tk.Frame(preview, bg=PANEL)
        actions.pack(fill="x", padx=16, pady=14)

        tk.Button(
            actions,
            text="Secondary Action",
            bg="#343942",
            fg=TEXT,
            relief="flat",
            padx=14,
            pady=7,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            actions,
            text="Primary Action",
            bg=ACCENT,
            fg=TEXT,
            relief="flat",
            padx=14,
            pady=7,
        ).pack(side="right")

    def _build_status_bar(self):
        status = tk.Frame(self, bg="#101215", height=28)
        status.grid(row=2, column=0, columnspan=2, sticky="ew")
        status.grid_propagate(False)

        tk.Label(
            status,
            text="Static reference - no model connection",
            bg="#101215",
            fg="#8f97a1",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=12, pady=5)


if __name__ == "__main__":
    PromptTestGui().mainloop()
