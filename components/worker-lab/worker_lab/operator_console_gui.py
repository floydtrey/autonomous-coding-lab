"""Tkinter operator console for the existing M09 sequential controller."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from .errors import LabValidationError
from .operator_console import OperatorConsoleBackend, RunJobRequest, protected_files_from_text


class OperatorConsoleApp(ttk.Frame):
    POLL_MS = 1000

    def __init__(self, master: tk.Misc, *, initial_root: Path) -> None:
        super().__init__(master, padding=10)
        self.pack(fill="both", expand=True)

        self._events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._loaded_plan_path: Path | None = None
        self._loaded_plan_digest: str | None = None
        self._loaded_plan_job_id: str | None = None
        self._running_job_id: str | None = None
        self._polling = False

        self.data_root = tk.StringVar(value=str(initial_root.resolve()))
        self.plan_file = tk.StringVar()
        self.job_id = tk.StringVar()
        self.controller_identity = tk.StringVar()
        self.target_repository = tk.StringVar()
        self.workspace_root = tk.StringVar()
        self.artifact_root = tk.StringVar()
        self.provider_binding_id = tk.StringVar()
        self.acknowledge_unsandboxed = tk.BooleanVar(value=False)
        self.review_required = tk.BooleanVar(value=False)
        self.archive_limit = tk.StringVar(value="0")

        self.status_job_id = tk.StringVar()
        self.status_controller = tk.StringVar()
        self.status_artifact_root = tk.StringVar()

        self.plan_summary = tk.StringVar(value="No plan loaded.")
        self.job_summary = tk.StringVar(value="No job selected.")

        self._build()
        self.after(200, self._drain_events)

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        root_bar = ttk.LabelFrame(self, text="ACL data root")
        root_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        root_bar.columnconfigure(0, weight=1)
        ttk.Entry(root_bar, textvariable=self.data_root).grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ttk.Button(root_bar, text="Browse…", command=self._browse_data_root).grid(row=0, column=1, padx=(0, 8), pady=8)

        panes = ttk.Panedwindow(self, orient="horizontal")
        panes.grid(row=1, column=0, sticky="nsew")

        left = ttk.Frame(panes, padding=(0, 0, 8, 0))
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=2)

        self._build_run_form(left)
        self._build_status(right)

    def _build_run_form(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)

        frame = ttk.LabelFrame(parent, text="Run approved job")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(frame, text="Plan file").grid(row=row, column=0, sticky="w", padx=8, pady=(8, 4))
        ttk.Entry(frame, textvariable=self.plan_file).grid(row=row, column=1, sticky="ew", padx=4, pady=(8, 4))
        ttk.Button(frame, text="Browse…", command=self._browse_plan).grid(row=row, column=2, padx=(4, 8), pady=(8, 4))
        row += 1

        ttk.Button(frame, text="Load / preview plan", command=self._load_plan).grid(
            row=row, column=0, columnspan=3, sticky="ew", padx=8, pady=4
        )
        row += 1
        ttk.Label(frame, textvariable=self.plan_summary, wraplength=430, justify="left").grid(
            row=row, column=0, columnspan=3, sticky="ew", padx=8, pady=(2, 8)
        )
        row += 1

        row = self._entry_row(frame, row, "Job ID (blank = plan ID)", self.job_id)
        row = self._entry_row(frame, row, "Controller identity", self.controller_identity)
        row = self._path_row(frame, row, "Target repository", self.target_repository, directory=True)
        row = self._path_row(frame, row, "Workspace root", self.workspace_root, directory=True)
        row = self._path_row(frame, row, "Artifact root", self.artifact_root, directory=True)
        row = self._entry_row(frame, row, "Provider binding ID", self.provider_binding_id)

        ttk.Label(frame, text="Protected validation files (one absolute path per line)").grid(
            row=row, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 2)
        )
        row += 1
        self.protected_files = tk.Text(frame, height=5, wrap="none")
        self.protected_files.grid(row=row, column=0, columnspan=2, sticky="nsew", padx=(8, 4), pady=4)
        ttk.Button(frame, text="Add file…", command=self._add_protected_file).grid(
            row=row, column=2, sticky="n", padx=(4, 8), pady=4
        )
        frame.rowconfigure(row, weight=1)
        row += 1

        ttk.Checkbutton(
            frame,
            text="I approve the named local checks as unsandboxed host-code execution",
            variable=self.acknowledge_unsandboxed,
        ).grid(row=row, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 2))
        row += 1
        ttk.Checkbutton(frame, text="Require explicit review", variable=self.review_required).grid(
            row=row, column=0, columnspan=3, sticky="w", padx=8, pady=2
        )
        row += 1
        row = self._entry_row(frame, row, "Candidate ZIP limit bytes (0 = omit)", self.archive_limit)

        self.run_button = ttk.Button(frame, text="Run previewed plan", command=self._run_job)
        self.run_button.grid(row=row, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 8))

    def _build_status(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)

        controls = ttk.LabelFrame(parent, text="Job control")
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(controls, text="Job ID").grid(row=row, column=0, sticky="w", padx=8, pady=(8, 4))
        ttk.Entry(controls, textvariable=self.status_job_id).grid(row=row, column=1, sticky="ew", padx=4, pady=(8, 4))
        ttk.Button(controls, text="Refresh", command=self._refresh_status).grid(row=row, column=2, padx=(4, 8), pady=(8, 4))
        row += 1

        ttk.Label(controls, text="Controller identity").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(controls, textvariable=self.status_controller).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(controls, text="Stop", command=self._stop_job).grid(row=row, column=2, padx=(4, 8), pady=4)
        row += 1

        ttk.Label(controls, text="Artifact root (for reconcile)").grid(row=row, column=0, sticky="w", padx=8, pady=(4, 8))
        ttk.Entry(controls, textvariable=self.status_artifact_root).grid(row=row, column=1, sticky="ew", padx=4, pady=(4, 8))
        ttk.Button(controls, text="Reconcile", command=self._reconcile_job).grid(
            row=row, column=2, padx=(4, 8), pady=(4, 8)
        )

        ttk.Label(parent, textvariable=self.job_summary, font=("TkDefaultFont", 10, "bold")).grid(
            row=1, column=0, sticky="ew", pady=(8, 4)
        )

        notebook = ttk.Notebook(parent)
        notebook.grid(row=2, column=0, sticky="nsew")

        status_tab = ttk.Frame(notebook)
        raw_tab = ttk.Frame(notebook)
        activity_tab = ttk.Frame(notebook)
        notebook.add(status_tab, text="Tasks")
        notebook.add(raw_tab, text="Raw status")
        notebook.add(activity_tab, text="Activity")

        status_tab.columnconfigure(0, weight=1)
        status_tab.rowconfigure(0, weight=1)
        columns = ("task", "state", "attempts", "attempt", "blocker")
        self.task_table = ttk.Treeview(status_tab, columns=columns, show="headings")
        headings = {
            "task": "Task",
            "state": "State",
            "attempts": "Attempts",
            "attempt": "Latest attempt",
            "blocker": "Blocker",
        }
        widths = {"task": 80, "state": 100, "attempts": 70, "attempt": 180, "blocker": 280}
        for key in columns:
            self.task_table.heading(key, text=headings[key])
            self.task_table.column(key, width=widths[key], stretch=True)
        self.task_table.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(status_tab, orient="vertical", command=self.task_table.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.task_table.configure(yscrollcommand=yscroll.set)

        raw_tab.columnconfigure(0, weight=1)
        raw_tab.rowconfigure(0, weight=1)
        self.raw_status = tk.Text(raw_tab, wrap="none", state="disabled")
        self.raw_status.grid(row=0, column=0, sticky="nsew")

        activity_tab.columnconfigure(0, weight=1)
        activity_tab.rowconfigure(0, weight=1)
        self.activity = tk.Text(activity_tab, wrap="word", state="disabled")
        self.activity.grid(row=0, column=0, sticky="nsew")

    def _entry_row(self, frame: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> int:
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(frame, textvariable=variable).grid(row=row, column=1, columnspan=2, sticky="ew", padx=(4, 8), pady=4)
        return row + 1

    def _path_row(
        self,
        frame: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        *,
        directory: bool,
    ) -> int:
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(frame, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        command = lambda: self._browse_path(variable, directory=directory)
        ttk.Button(frame, text="Browse…", command=command).grid(row=row, column=2, padx=(4, 8), pady=4)
        return row + 1

    def _backend(self) -> OperatorConsoleBackend:
        root = Path(self.data_root.get().strip()).expanduser()
        if not str(root):
            raise LabValidationError("OPERATOR_CONSOLE_INPUT_INVALID", "data root is required")
        return OperatorConsoleBackend(root)

    def _browse_data_root(self) -> None:
        self._browse_path(self.data_root, directory=True)

    def _browse_plan(self) -> None:
        value = filedialog.askopenfilename(title="Select ACL job plan", filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if value:
            self.plan_file.set(value)
            self._invalidate_plan_preview()

    def _browse_path(self, variable: tk.StringVar, *, directory: bool) -> None:
        value = filedialog.askdirectory() if directory else filedialog.askopenfilename()
        if value:
            variable.set(value)

    def _add_protected_file(self) -> None:
        value = filedialog.askopenfilename(title="Select protected validation input")
        if value:
            current = self.protected_files.get("1.0", "end").strip()
            updated = value if not current else current + "\n" + value
            self.protected_files.delete("1.0", "end")
            self.protected_files.insert("1.0", updated)

    def _invalidate_plan_preview(self) -> None:
        self._loaded_plan_path = None
        self._loaded_plan_digest = None
        self._loaded_plan_job_id = None
        self.plan_summary.set("No plan loaded.")

    def _load_plan(self) -> None:
        try:
            path = Path(self.plan_file.get().strip())
            loaded = self._backend().load_plan(path)
        except (LabValidationError, OSError) as exc:
            self._show_error(exc)
            return
        self._loaded_plan_path = loaded.path
        self._loaded_plan_digest = loaded.digest
        self._loaded_plan_job_id = loaded.job_id
        self.plan_file.set(str(loaded.path))
        if not self.job_id.get().strip():
            self.job_id.set(loaded.job_id)
        self.plan_summary.set(
            f"Plan: {loaded.plan.plan_id}  revision {loaded.plan.revision}\n"
            f"Digest: {loaded.digest}\n"
            f"Objective: {loaded.objective}\n"
            f"Tasks: {len(loaded.plan.tasks)}"
        )
        self._log(f"Previewed plan {loaded.plan.plan_id} at {loaded.digest}.")

    def _run_job(self) -> None:
        try:
            if self._loaded_plan_path is None or self._loaded_plan_digest is None:
                raise LabValidationError(
                    "OPERATOR_CONSOLE_PLAN_REQUIRED",
                    "load and preview the plan before running it",
                )
            current_plan_path = Path(self.plan_file.get().strip()).expanduser().resolve()
            if current_plan_path != self._loaded_plan_path:
                raise LabValidationError(
                    "OPERATOR_CONSOLE_PLAN_CHANGED",
                    "plan path changed after preview; reload the plan",
                )
            archive_limit = self._parse_archive_limit()
            protected = protected_files_from_text(self.protected_files.get("1.0", "end"))
            request = RunJobRequest(
                plan_file=self._loaded_plan_path,
                approved_plan_digest=self._loaded_plan_digest,
                job_id=self.job_id.get().strip() or None,
                controller_identity=self.controller_identity.get().strip(),
                target_repository=Path(self.target_repository.get().strip()),
                workspace_root=Path(self.workspace_root.get().strip()),
                artifact_root=Path(self.artifact_root.get().strip()),
                provider_binding_id=self.provider_binding_id.get().strip(),
                protected_files=protected,
                acknowledge_unsandboxed=self.acknowledge_unsandboxed.get(),
                review_required=self.review_required.get(),
                candidate_archive_limit_bytes=archive_limit,
            )
            if not request.acknowledge_unsandboxed:
                raise LabValidationError(
                    "OPERATOR_CONSOLE_APPROVAL_REQUIRED",
                    "explicitly acknowledge the named unsandboxed local validation checks before launch",
                )
            backend = self._backend()
            job_id = request.job_id or self._loaded_plan_job_id
            if not job_id:
                raise LabValidationError("OPERATOR_CONSOLE_INPUT_INVALID", "job ID is unavailable")
        except (LabValidationError, OSError, ValueError) as exc:
            self._show_error(exc)
            return

        self._running_job_id = job_id
        self.status_job_id.set(job_id)
        self.status_controller.set(request.controller_identity)
        self.status_artifact_root.set(str(request.artifact_root.expanduser().resolve()))
        self.run_button.configure(state="disabled")
        self._log(f"Launching job {job_id}.")
        self._start_polling()

        def work() -> None:
            try:
                result = backend.run_job(request)
            except Exception as exc:  # GUI boundary: surface exact application error to operator.
                self._events.put(("run-error", exc))
            else:
                self._events.put(("run-result", result))

        threading.Thread(target=work, name=f"acl-job-{job_id}", daemon=True).start()

    def _parse_archive_limit(self) -> int | None:
        value = self.archive_limit.get().strip()
        if not value:
            return None
        number = int(value)
        if number < 0:
            raise ValueError("candidate ZIP limit cannot be negative")
        return number

    def _start_polling(self) -> None:
        if self._polling:
            return
        self._polling = True
        self.after(self.POLL_MS, self._poll_status)

    def _poll_status(self) -> None:
        if not self._polling:
            return
        job_id = self._running_job_id
        if not job_id:
            self._polling = False
            return
        try:
            value = self._backend().status(job_id)
        except LabValidationError as exc:
            if exc.code not in {"JOB_MISSING", "STORAGE_RECORD_MISSING", "SERVICE_RECORD_MISSING"}:
                self._log(f"Status poll: {exc.code}: {exc.summary}")
        except OSError as exc:
            self._log(f"Status poll error: {exc}")
        else:
            self._render_status(value)
        if self._polling:
            self.after(self.POLL_MS, self._poll_status)

    def _refresh_status(self) -> None:
        job_id = self.status_job_id.get().strip()
        if not job_id:
            messagebox.showinfo("ACL Console", "Enter a job ID first.")
            return
        try:
            value = self._backend().status(job_id)
        except (LabValidationError, OSError) as exc:
            self._show_error(exc)
            return
        self._render_status(value)
        self._log(f"Refreshed status for {job_id}.")

    def _stop_job(self) -> None:
        self._run_control_action("stop")

    def _reconcile_job(self) -> None:
        self._run_control_action("reconcile")

    def _run_control_action(self, action: str) -> None:
        job_id = self.status_job_id.get().strip()
        controller = self.status_controller.get().strip()
        if not job_id or not controller:
            messagebox.showinfo("ACL Console", "Job ID and controller identity are required.")
            return
        backend = self._backend()
        artifact_text = self.status_artifact_root.get().strip()

        def work() -> None:
            try:
                if action == "stop":
                    value = backend.stop(job_id, controller_identity=controller)
                else:
                    artifact = Path(artifact_text) if artifact_text else None
                    value = backend.reconcile(
                        job_id,
                        controller_identity=controller,
                        artifact_root=artifact,
                    )
            except Exception as exc:
                self._events.put(("control-error", (action, exc)))
            else:
                self._events.put(("control-result", (action, value)))

        self._log(f"Requesting {action} for {job_id}.")
        threading.Thread(target=work, name=f"acl-{action}-{job_id}", daemon=True).start()

    def _drain_events(self) -> None:
        while True:
            try:
                kind, payload = self._events.get_nowait()
            except queue.Empty:
                break
            if kind == "run-result":
                self._polling = False
                self.run_button.configure(state="normal")
                self._render_status(payload)
                self._log(f"Job {payload.get('job_id', self._running_job_id)} returned {payload.get('status', 'unknown')}.")
            elif kind == "run-error":
                self._polling = False
                self.run_button.configure(state="normal")
                self._show_error(payload)
            elif kind == "control-result":
                action, value = payload
                self._render_status(value)
                self._log(f"{action.title()} completed for {value.get('job_id', 'job')}.")
            elif kind == "control-error":
                action, exc = payload
                self._log(f"{action.title()} failed.")
                self._show_error(exc)
        self.after(200, self._drain_events)

    def _render_status(self, value: dict) -> None:
        job_id = value.get("job_id", "")
        status = value.get("status", "unknown")
        complete = value.get("objective_complete", False)
        active = value.get("active")
        active_text = "none" if active is None else f"{active.get('task_id', '?')} / {active.get('reservation_id', '?')}"
        self.job_summary.set(
            f"Job {job_id} — {status} | objective_complete={complete} | active={active_text}"
        )
        self.status_job_id.set(job_id or self.status_job_id.get())

        for item in self.task_table.get_children():
            self.task_table.delete(item)
        for task in value.get("tasks", []):
            last = task.get("last_attempt") or {}
            blocker = task.get("blocker") or {}
            self.task_table.insert(
                "",
                "end",
                values=(
                    task.get("task_id", ""),
                    task.get("state", ""),
                    task.get("attempt_count", 0),
                    last.get("attempt_id", "") or "",
                    blocker.get("code", "") or "",
                ),
            )

        self._set_text(self.raw_status, json.dumps(value, indent=2, sort_keys=True))

    def _log(self, text: str) -> None:
        self.activity.configure(state="normal")
        self.activity.insert("end", text.rstrip() + "\n")
        self.activity.see("end")
        self.activity.configure(state="disabled")

    def _show_error(self, exc: Exception) -> None:
        if isinstance(exc, LabValidationError):
            message = f"{exc.code}: {exc.summary}"
        else:
            message = str(exc)
        self._log("ERROR " + message)
        messagebox.showerror("ACL Console", message)

    @staticmethod
    def _set_text(widget: tk.Text, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="worker-lab-console")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Worker Lab data root (default: current directory)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    root = tk.Tk()
    root.title("ACL Worker Console")
    root.geometry("1240x780")
    root.minsize(1040, 680)
    OperatorConsoleApp(root, initial_root=args.root)
    root.mainloop()


if __name__ == "__main__":
    main()
