from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
import sys
import traceback

import graphiti_host_phase
from knowledge_core_providers.host_metrics import HostResourceTelemetry


def _json_default(value):
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, default=_json_default, sort_keys=True, indent=2))


def _sample_interval() -> float:
    raw = os.environ.get("KC_HOST_METRICS_SAMPLE_SECONDS", "1.0")
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError("KC_HOST_METRICS_SAMPLE_SECONDS must be a number") from exc
    if value <= 0:
        raise RuntimeError("KC_HOST_METRICS_SAMPLE_SECONDS must be positive")
    return value


def main() -> int:
    telemetry = HostResourceTelemetry(
        sample_interval_seconds=_sample_interval(),
        gpu_interval_seconds=max(_sample_interval(), 2.0),
    ).start()
    captured = io.StringIO()
    try:
        with redirect_stdout(captured):
            exit_code = graphiti_host_phase.main()
    except BaseException as exc:
        metrics = telemetry.stop()
        text = captured.getvalue().strip()
        payload: dict[str, object] = {
            "status": "qualification-exception",
            "error": f"{type(exc).__name__}: {exc}",
            "host_metrics": metrics,
        }
        if text:
            payload["captured_stdout"] = text
        _emit(payload)
        traceback.print_exc(file=sys.stderr)
        if isinstance(exc, SystemExit) and isinstance(exc.code, int):
            return exc.code
        return 1

    metrics = telemetry.stop()
    text = captured.getvalue().strip()
    if not text:
        payload = {
            "status": "qualification-produced-no-json",
            "host_metrics": metrics,
        }
        _emit(payload)
        return exit_code if isinstance(exit_code, int) else 1

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = {
            "status": "qualification-output-not-json",
            "captured_stdout": text,
        }
    if not isinstance(payload, dict):
        payload = {
            "status": "qualification-output-not-object",
            "captured_output": payload,
        }
    payload["host_metrics"] = metrics
    _emit(payload)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
