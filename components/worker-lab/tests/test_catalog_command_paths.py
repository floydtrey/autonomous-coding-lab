import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "curricula" / "catalogs" / "worker-lab-v3.json"


def test_protected_pytest_catalog_commands_reference_existing_tests():
    value = json.loads(CATALOG.read_text(encoding="utf-8"))
    missing = []
    for test in value["tests"]:
        command = test.get("command", [])
        if command[:4] != ["python", "-m", "pytest", "-q"]:
            continue
        for item in command[4:]:
            if isinstance(item, str) and item.startswith("tests/") and not (ROOT / item).is_file():
                missing.append((test["test_id"], item))
    assert missing == []
