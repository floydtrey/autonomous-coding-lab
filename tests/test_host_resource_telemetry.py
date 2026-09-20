from __future__ import annotations

from knowledge_core_providers import host_metrics


def test_host_resource_telemetry_captures_peaks_without_affecting_kc(monkeypatch):
    gib = 1024 ** 3
    memory_samples = iter(
        [
            {
                "ram_total_bytes": 64 * gib,
                "ram_available_bytes": 54 * gib,
                "ram_used_bytes": 10 * gib,
                "commit_limit_bytes": 80 * gib,
                "commit_available_bytes": 68 * gib,
                "commit_used_bytes": 12 * gib,
            },
            {
                "ram_total_bytes": 64 * gib,
                "ram_available_bytes": 44 * gib,
                "ram_used_bytes": 20 * gib,
                "commit_limit_bytes": 80 * gib,
                "commit_available_bytes": 50 * gib,
                "commit_used_bytes": 30 * gib,
            },
        ]
    )
    cpu_samples = iter([(100, 1000), (110, 1100)])
    gpu_samples = iter(
        [
            [
                {
                    "index": 0,
                    "name": "Test GPU",
                    "vram_total_mib": 12288.0,
                    "vram_used_mib": 6000.0,
                    "gpu_utilization_percent": 55.0,
                    "memory_utilization_percent": 45.0,
                    "temperature_c": 60.0,
                    "power_w": 120.0,
                }
            ],
            [
                {
                    "index": 0,
                    "name": "Test GPU",
                    "vram_total_mib": 12288.0,
                    "vram_used_mib": 11000.0,
                    "gpu_utilization_percent": 96.0,
                    "memory_utilization_percent": 91.0,
                    "temperature_c": 72.0,
                    "power_w": 188.0,
                }
            ],
        ]
    )

    monkeypatch.setattr(host_metrics, "_memory_snapshot", lambda: next(memory_samples))
    monkeypatch.setattr(host_metrics, "_cpu_counters", lambda: next(cpu_samples))
    monkeypatch.setattr(host_metrics, "_gpu_snapshot", lambda: next(gpu_samples))
    monkeypatch.setattr(
        host_metrics,
        "_ollama_ps_snapshot",
        lambda: {"available": True, "output": "graphiti-test", "error": None},
    )

    telemetry = host_metrics.HostResourceTelemetry(
        sample_interval_seconds=60.0,
        gpu_interval_seconds=60.0,
    ).start()
    summary = telemetry.stop()

    assert summary["sample_count"] == 2
    assert summary["gpu_sample_count"] == 2
    assert summary["ram"]["total_gib"] == 64.0
    assert summary["ram"]["peak_used_gib"] == 20.0
    assert summary["ram"]["peak_used_percent"] == 31.25
    assert summary["commit"]["peak_used_gib"] == 30.0
    assert summary["commit"]["peak_used_percent"] == 37.5
    assert summary["cpu"]["peak_utilization_percent"] == 90.0
    assert summary["gpus"][0]["peak_vram_used_mib"] == 11000.0
    assert summary["gpus"][0]["peak_gpu_utilization_percent"] == 96.0
    assert summary["gpus"][0]["peak_temperature_c"] == 72.0
    assert summary["ollama_start"]["available"] is True
    assert summary["ollama_end"]["available"] is True
    assert summary["sampling_errors"] == []
