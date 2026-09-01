"""Health & installation-status view.

future: populate the field grids below from
WorkerLabApplicationService.health() (HealthDTO) and
WorkerLabApplicationService.installation_status() (InstallationStatusDTO / DoctorReport).
"""
from __future__ import annotations

from tkinter import ttk

_HEALTH_FIELDS = (
    "schema_version",
    "status",
    "data_root_state",
    "execution_ready",
    "collection_counts",
)
_INSTALLATION_FIELDS = (
    "installation_id",
    "manifest_digest",
    "execution_authority",
    "component_digests",
    "python_digest",
    "python_version",
    "codex_digest",
    "codex_version",
    "execution_ready",
)


class OverviewView(ttk.Frame):
    """Health and installation-status placeholders. No values are populated yet."""

    def __init__(self, master) -> None:
        super().__init__(master, style="View.TFrame")
        ttk.Label(self, text="System Health", style="ViewTitle.TLabel").pack(anchor="w", padx=16, pady=(16, 4))
        self._render_field_grid(_HEALTH_FIELDS)

        ttk.Label(self, text="Installation Status", style="ViewTitle.TLabel").pack(anchor="w", padx=16, pady=(16, 4))
        self._render_field_grid(_INSTALLATION_FIELDS)

    def _render_field_grid(self, field_names: tuple[str, ...]) -> None:
        grid = ttk.Frame(self, style="View.TFrame")
        grid.pack(fill="x", padx=16)
        for row, name in enumerate(field_names):
            ttk.Label(grid, text=name, style="ViewBody.TLabel").grid(row=row, column=0, sticky="w", padx=(0, 12))
            ttk.Label(grid, text="—", style="ViewBody.TLabel").grid(row=row, column=1, sticky="w")
