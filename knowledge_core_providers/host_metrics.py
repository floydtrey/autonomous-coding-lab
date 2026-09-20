from __future__ import annotations

import csv
import ctypes
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import shutil
import subprocess
import threading
import time
from typing import Any


_GIB = 1024 ** 3


def _round(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(float(value), digits)


def _gib(value: int | None) -> float | None:
    return None if value is None else round(value / _GIB, 3)


def _percent(used: int | None, total: int | None) -> float | None:
    if used is None or total is None or total <= 0:
        return None
    return round((used / total) * 100.0, 2)


def _safe_float(value: str) -> float | None:
    value = value.strip()
    if not value or value.upper() in {"N/A", "[N/A]", "NOT SUPPORTED"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _windows_memory_snapshot() -> dict[str, int]:
    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("GlobalMemoryStatusEx failed")
    return {
        "ram_total_bytes": int(status.ullTotalPhys),
        "ram_available_bytes": int(status.ullAvailPhys),
        "ram_used_bytes": int(status.ullTotalPhys - status.ullAvailPhys),
        # Windows exposes the commit limit/availability through the PageFile fields.
        "commit_limit_bytes": int(status.ullTotalPageFile),
        "commit_available_bytes": int(status.ullAvailPageFile),
        "commit_used_bytes": int(status.ullTotalPageFile - status.ullAvailPageFile),
    }


def _linux_memory_snapshot() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        parts = raw.strip().split()
        if not parts:
            continue
        multiplier = 1024 if len(parts) > 1 and parts[1].lower() == "kb" else 1
        try:
            values[key] = int(parts[0]) * multiplier
        except ValueError:
            continue
    total = values.get("MemTotal")
    available = values.get("MemAvailable")
    if total is None or available is None:
        raise RuntimeError("/proc/meminfo did not expose MemTotal/MemAvailable")
    result = {
        "ram_total_bytes": total,
        "ram_available_bytes": available,
        "ram_used_bytes": total - available,
    }
    commit_limit = values.get("CommitLimit")
    committed = values.get("Committed_AS")
    if commit_limit is not None and committed is not None:
        result.update(
            {
                "commit_limit_bytes": commit_limit,
                "commit_available_bytes": max(commit_limit - committed, 0),
                "commit_used_bytes": committed,
            }
        )
    return result


def _memory_snapshot() -> dict[str, int]:
    if os.name == "nt":
        return _windows_memory_snapshot()
    if Path("/proc/meminfo").exists():
        return _linux_memory_snapshot()
    raise RuntimeError(f"memory telemetry is unsupported on {platform.system()}")


def _windows_cpu_counters() -> tuple[int, int]:
    class FileTime(ctypes.Structure):
        _fields_ = [("low", ctypes.c_ulong), ("high", ctypes.c_ulong)]

    idle = FileTime()
    kernel = FileTime()
    user = FileTime()
    if not ctypes.windll.kernel32.GetSystemTimes(
        ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
    ):
        raise OSError("GetSystemTimes failed")

    def value(item: FileTime) -> int:
        return (int(item.high) << 32) | int(item.low)

    idle_value = value(idle)
    total_value = value(kernel) + value(user)
    return idle_value, total_value


def _linux_cpu_counters() -> tuple[int, int]:
    first = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()
    if not first or first[0] != "cpu":
        raise RuntimeError("/proc/stat did not expose aggregate CPU counters")
    counters = [int(item) for item in first[1:]]
    idle = counters[3] + (counters[4] if len(counters) > 4 else 0)
    return idle, sum(counters)


def _cpu_counters() -> tuple[int, int]:
    if os.name == "nt":
        return _windows_cpu_counters()
    if Path("/proc/stat").exists():
        return _linux_cpu_counters()
    raise RuntimeError(f"CPU telemetry is unsupported on {platform.system()}")


def _gpu_snapshot() -> list[dict[str, Any]]:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        raise RuntimeError("nvidia-smi was not found on PATH")
    completed = subprocess.run(
        [
            executable,
            "--query-gpu=index,name,memory.total,memory.used,utilization.gpu,utilization.memory,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"nvidia-smi failed ({completed.returncode}): {detail}")
    rows: list[dict[str, Any]] = []
    for values in csv.reader(completed.stdout.splitlines()):
        if len(values) < 8:
            continue
        rows.append(
            {
                "index": int(values[0].strip()),
                "name": values[1].strip(),
                "vram_total_mib": _safe_float(values[2]),
                "vram_used_mib": _safe_float(values[3]),
                "gpu_utilization_percent": _safe_float(values[4]),
                "memory_utilization_percent": _safe_float(values[5]),
                "temperature_c": _safe_float(values[6]),
                "power_w": _safe_float(values[7]),
            }
        )
    return rows


def _ollama_ps_snapshot() -> dict[str, Any]:
    executable = shutil.which("ollama")
    if executable is None:
        return {"available": False, "output": None, "error": "ollama was not found on PATH"}
    try:
        completed = subprocess.run(
            [executable, "ps"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except Exception as exc:  # best-effort host evidence only
        return {"available": False, "output": None, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "available": completed.returncode == 0,
        "output": completed.stdout.strip() or None,
        "error": (completed.stderr.strip() or None) if completed.returncode != 0 else None,
    }


class HostResourceTelemetry:
    """Best-effort host telemetry for real provider qualification runs.

    Sampling must never decide Knowledge Core trust or fail a qualification. Missing host
    facilities are reported in ``sampling_errors`` while the provider run continues normally.
    """

    def __init__(
        self,
        *,
        sample_interval_seconds: float = 1.0,
        gpu_interval_seconds: float = 2.0,
    ) -> None:
        if sample_interval_seconds <= 0:
            raise ValueError("sample_interval_seconds must be positive")
        if gpu_interval_seconds <= 0:
            raise ValueError("gpu_interval_seconds must be positive")
        self.sample_interval_seconds = float(sample_interval_seconds)
        self.gpu_interval_seconds = float(gpu_interval_seconds)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._started_monotonic: float | None = None
        self._started_at: str | None = None
        self._stopped_summary: dict[str, Any] | None = None
        self._previous_cpu: tuple[int, int] | None = None
        self._sample_count = 0
        self._gpu_sample_count = 0
        self._errors: list[str] = []
        self._memory_start: dict[str, int] | None = None
        self._memory_last: dict[str, int] | None = None
        self._memory_peaks: dict[str, int] = {}
        self._cpu_peak_percent: float | None = None
        self._gpu: dict[int, dict[str, Any]] = {}
        self._ollama_start: dict[str, Any] | None = None

    def _record_error(self, source: str, exc: Exception) -> None:
        message = f"{source}: {type(exc).__name__}: {exc}"
        with self._lock:
            if message not in self._errors:
                self._errors.append(message)

    def _sample_memory(self) -> None:
        try:
            snapshot = _memory_snapshot()
        except Exception as exc:  # telemetry is deliberately fail-open
            self._record_error("memory", exc)
            return
        with self._lock:
            if self._memory_start is None:
                self._memory_start = dict(snapshot)
            self._memory_last = dict(snapshot)
            for key in ("ram_used_bytes", "commit_used_bytes"):
                value = snapshot.get(key)
                if value is not None:
                    self._memory_peaks[key] = max(self._memory_peaks.get(key, 0), value)

    def _sample_cpu(self) -> None:
        try:
            idle, total = _cpu_counters()
        except Exception as exc:  # telemetry is deliberately fail-open
            self._record_error("cpu", exc)
            return
        previous = self._previous_cpu
        self._previous_cpu = (idle, total)
        if previous is None:
            return
        idle_delta = idle - previous[0]
        total_delta = total - previous[1]
        if total_delta <= 0:
            return
        utilization = max(0.0, min(100.0, ((total_delta - idle_delta) / total_delta) * 100.0))
        with self._lock:
            if self._cpu_peak_percent is None or utilization > self._cpu_peak_percent:
                self._cpu_peak_percent = utilization

    def _sample_gpu(self) -> None:
        try:
            snapshots = _gpu_snapshot()
        except Exception as exc:  # telemetry is deliberately fail-open
            self._record_error("gpu", exc)
            return
        with self._lock:
            self._gpu_sample_count += 1
            for snapshot in snapshots:
                index = int(snapshot["index"])
                aggregate = self._gpu.setdefault(
                    index,
                    {
                        "index": index,
                        "name": snapshot["name"],
                        "vram_total_mib": snapshot["vram_total_mib"],
                        "start_vram_used_mib": snapshot["vram_used_mib"],
                        "end_vram_used_mib": snapshot["vram_used_mib"],
                        "peak_vram_used_mib": snapshot["vram_used_mib"],
                        "peak_gpu_utilization_percent": snapshot["gpu_utilization_percent"],
                        "peak_memory_utilization_percent": snapshot["memory_utilization_percent"],
                        "peak_temperature_c": snapshot["temperature_c"],
                        "peak_power_w": snapshot["power_w"],
                    },
                )
                aggregate["end_vram_used_mib"] = snapshot["vram_used_mib"]
                for target, source in (
                    ("peak_vram_used_mib", "vram_used_mib"),
                    ("peak_gpu_utilization_percent", "gpu_utilization_percent"),
                    ("peak_memory_utilization_percent", "memory_utilization_percent"),
                    ("peak_temperature_c", "temperature_c"),
                    ("peak_power_w", "power_w"),
                ):
                    value = snapshot[source]
                    current = aggregate[target]
                    if value is not None and (current is None or value > current):
                        aggregate[target] = value

    def _sample_once(self, *, include_gpu: bool) -> None:
        self._sample_memory()
        self._sample_cpu()
        if include_gpu:
            self._sample_gpu()
        with self._lock:
            self._sample_count += 1

    def _run(self) -> None:
        next_gpu = time.monotonic() + self.gpu_interval_seconds
        while not self._stop_event.wait(self.sample_interval_seconds):
            now = time.monotonic()
            include_gpu = now >= next_gpu
            self._sample_once(include_gpu=include_gpu)
            if include_gpu:
                next_gpu = now + self.gpu_interval_seconds

    def start(self) -> "HostResourceTelemetry":
        if self._started_monotonic is not None:
            return self
        self._started_monotonic = time.monotonic()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._ollama_start = _ollama_ps_snapshot()
        self._sample_once(include_gpu=True)
        self._thread = threading.Thread(
            target=self._run,
            name="kc-host-resource-telemetry",
            daemon=True,
        )
        self._thread.start()
        return self

    def stop(self) -> dict[str, Any]:
        if self._stopped_summary is not None:
            return self._stopped_summary
        if self._started_monotonic is None:
            self.start()
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=max(self.sample_interval_seconds * 2.0, 2.0))
        self._sample_once(include_gpu=True)
        stopped_at = datetime.now(timezone.utc).isoformat()
        duration = time.monotonic() - (self._started_monotonic or time.monotonic())
        ollama_end = _ollama_ps_snapshot()

        with self._lock:
            start = dict(self._memory_start or {})
            end = dict(self._memory_last or {})
            peak_ram = self._memory_peaks.get("ram_used_bytes")
            peak_commit = self._memory_peaks.get("commit_used_bytes")
            ram_total = end.get("ram_total_bytes") or start.get("ram_total_bytes")
            commit_limit = end.get("commit_limit_bytes") or start.get("commit_limit_bytes")
            gpus = []
            for item in sorted(self._gpu.values(), key=lambda value: value["index"]):
                copy = dict(item)
                total_vram = copy.get("vram_total_mib")
                peak_vram = copy.get("peak_vram_used_mib")
                copy["peak_vram_used_percent"] = (
                    _round((peak_vram / total_vram) * 100.0)
                    if peak_vram is not None and total_vram not in (None, 0)
                    else None
                )
                for key in (
                    "vram_total_mib",
                    "start_vram_used_mib",
                    "end_vram_used_mib",
                    "peak_vram_used_mib",
                    "peak_gpu_utilization_percent",
                    "peak_memory_utilization_percent",
                    "peak_temperature_c",
                    "peak_power_w",
                ):
                    copy[key] = _round(copy.get(key))
                gpus.append(copy)

            self._stopped_summary = {
                "telemetry_version": 1,
                "platform": platform.platform(),
                "logical_cpu_count": os.cpu_count(),
                "started_at_utc": self._started_at,
                "stopped_at_utc": stopped_at,
                "duration_seconds": round(duration, 3),
                "sample_interval_seconds": self.sample_interval_seconds,
                "gpu_sample_interval_seconds": self.gpu_interval_seconds,
                "sample_count": self._sample_count,
                "gpu_sample_count": self._gpu_sample_count,
                "ram": {
                    "total_gib": _gib(ram_total),
                    "start_used_gib": _gib(start.get("ram_used_bytes")),
                    "end_used_gib": _gib(end.get("ram_used_bytes")),
                    "peak_used_gib": _gib(peak_ram),
                    "peak_used_percent": _percent(peak_ram, ram_total),
                },
                "commit": {
                    "limit_gib": _gib(commit_limit),
                    "start_used_gib": _gib(start.get("commit_used_bytes")),
                    "end_used_gib": _gib(end.get("commit_used_bytes")),
                    "peak_used_gib": _gib(peak_commit),
                    "peak_used_percent": _percent(peak_commit, commit_limit),
                },
                "cpu": {"peak_utilization_percent": _round(self._cpu_peak_percent)},
                "gpus": gpus,
                "ollama_start": self._ollama_start,
                "ollama_end": ollama_end,
                "sampling_errors": list(self._errors),
            }
            return self._stopped_summary
