from pathlib import Path


def test_graphiti_live_runner_compiles() -> None:
    path = Path(__file__).resolve().parents[1] / "tools" / "graphiti_host_phase_live.py"
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
