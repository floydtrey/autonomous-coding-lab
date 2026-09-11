from __future__ import annotations

import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_setuptools_discovery_is_limited_to_worker_lab() -> None:
    config = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    discovery = config["tool"]["setuptools"]["packages"]["find"]

    assert discovery == {
        "where": ["."],
        "include": ["worker_lab*"],
        "namespaces": False,
    }
