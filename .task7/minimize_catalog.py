from __future__ import annotations

import json
import subprocess
from pathlib import Path

BASE = "1867b66c9e076a986838d3284eb3a15088b1cb08"
REL = "components/worker-lab/curricula/catalogs/worker-lab-v3.json"
PATH = Path(REL)


def base_bytes() -> bytes:
    result = subprocess.run(
        ["git", "show", f"{BASE}:{REL}"],
        check=True,
        capture_output=True,
    )
    return result.stdout


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one exact occurrence, found {count}")
    return text.replace(old, new, 1)


original_bytes = base_bytes()
original_text = original_bytes.decode("utf-8")
original_value = json.loads(original_text)
text = original_text

old_command = '''                      "command":  [
                                      "python",
                                      "-m",
                                      "pytest",
                                      "-q",
                                      "tests/test_integration.py",
                                      "tests/test_invocation_store.py"
                                  ],'''
new_command = '''                      "command":  [
                                      "python",
                                      "-m",
                                      "pytest",
                                      "-q",
                                      "tests/test_integration_v3.py",
                                      "tests/test_invocation_store_v3.py",
                                      "tests/test_application_service_v3.py"
                                  ],'''
# The same old command appears exactly in T016 and T022.
if text.count(old_command) != 2:
    raise RuntimeError(f"expected two legacy V3-catalog command blocks, found {text.count(old_command)}")
text = text.replace(old_command, new_command, 2)

old_paths = '''                      "path_prefixes":  [
                                            "worker_lab/framework_adapter.py",
                                            "worker_lab/integration.py",
                                            "worker_lab/invocation_store.py"
                                        ],'''
new_paths = '''                      "path_prefixes":  [
                                            "worker_lab/integration_v3.py",
                                            "worker_lab/invocation_store_v3.py",
                                            "worker_lab/service_runtime_v3.py"
                                        ],'''
if text.count(old_paths) != 2:
    raise RuntimeError(f"expected two legacy V3-catalog path blocks, found {text.count(old_paths)}")
text = text.replace(old_paths, new_paths, 2)

text = replace_once(
    text,
    '                      "name":  "Evidence substitution and result identity",',
    '                      "name":  "V3 integration identity and acceptance",',
    "T016 name",
)
text = replace_once(
    text,
    '                      "name":  "Exact integration candidate verification",',
    '                      "name":  "Exact V3 integration candidate verification",',
    "T022 name",
)
text = replace_once(
    text,
    '                      "purpose":  "Reject substituted adapter responses, invocation identities, and strict result records.",',
    '                      "purpose":  "Verify current V3 invocation/result identity, storage, dispatch, and independent candidate acceptance.",',
    "T016 purpose",
)
text = replace_once(
    text,
    '                      "purpose":  "Verify the exact adapter result binds the prepared Worker Lab invocation.",',
    '                      "purpose":  "Verify current V3 invocation/result identity, storage, dispatch, and independent candidate acceptance.",',
    "T022 purpose",
)

updated_value = json.loads(text)
original_by_id = {item["test_id"]: item for item in original_value["tests"]}
updated_by_id = {item["test_id"]: item for item in updated_value["tests"]}
if original_by_id.keys() != updated_by_id.keys():
    raise RuntimeError("protected test IDs changed")
for test_id in original_by_id:
    if test_id not in {"T016", "T022"} and original_by_id[test_id] != updated_by_id[test_id]:
        raise RuntimeError(f"unintended protected test change: {test_id}")

expected_command = [
    "python", "-m", "pytest", "-q",
    "tests/test_integration_v3.py",
    "tests/test_invocation_store_v3.py",
    "tests/test_application_service_v3.py",
]
expected_paths = [
    "worker_lab/integration_v3.py",
    "worker_lab/invocation_store_v3.py",
    "worker_lab/service_runtime_v3.py",
]
expected = {
    "T016": ("V3 integration identity and acceptance", expected_command, expected_paths),
    "T022": ("Exact V3 integration candidate verification", expected_command, expected_paths),
}
for test_id, (name, command, paths) in expected.items():
    item = updated_by_id[test_id]
    if item["name"] != name or item["command"] != command or item["path_prefixes"] != paths:
        raise RuntimeError(f"{test_id} does not match intended V3 authority")
    if item["purpose"] != "Verify current V3 invocation/result identity, storage, dispatch, and independent candidate acceptance.":
        raise RuntimeError(f"{test_id} purpose differs")

PATH.write_text(text, encoding="utf-8")
print("worker-lab-v3 catalog minimized; only T016/T022 semantics changed")
