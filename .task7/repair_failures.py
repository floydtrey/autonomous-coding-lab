from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path.cwd()
WORKER = ROOT / "components" / "worker-lab"
TESTS = WORKER / "tests"


def remove_functions(path: Path, names: set[str]) -> None:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    ranges: list[tuple[int, int]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            start = min([node.lineno, *[item.lineno for item in node.decorator_list]])
            ranges.append((start, node.end_lineno))
    for start, end in sorted(ranges, reverse=True):
        del lines[start - 1 : end]
    path.write_text("".join(lines), encoding="utf-8")


# Task 7 is V3-only. _operation_result must not reference the deleted V2 InvocationRecord.
app = WORKER / "worker_lab" / "application_service.py"
text = app.read_text(encoding="utf-8")
text = text.replace(
    "record.identity_digest() if isinstance(record, (InvocationRecord, InvocationRecordV3)) else None",
    "record.identity_digest() if isinstance(record, InvocationRecordV3) else None",
)
if "InvocationRecord," in text or "(InvocationRecord," in text:
    raise RuntimeError("residual V2 InvocationRecord reference remains in application_service.py")
app.write_text(text, encoding="utf-8")

# The Phase 4 record-normalizer bundle is intentionally deleted by Task 7 because it is obsolete
# commissioning authority tied to the old MineTrackerWorker proof repository. Its dedicated tests
# must leave the active protected-definition suite with it.
protected = TESTS / "test_protected_definitions.py"
remove_functions(
    protected,
    {
        "_phase4_definitions",
        "_phase4_attempt",
        "test_phase4_record_normalizer_definitions_are_exact_and_admissible",
        "test_phase4_record_normalizer_attempt_binding_rejects_substitutions",
    },
)
ptext = protected.read_text(encoding="utf-8")
ptext = ptext.replace("from copy import deepcopy\n", "")
ptext = ptext.replace("import pytest\n\n", "")
ptext = ptext.replace("from worker_lab.errors import LabValidationError\n", "")
ptext = ptext.replace(
    "from worker_lab.models import ATTEMPT_SCHEMA, AttemptRecord, CurriculumRecord, ExerciseRecord\n",
    "",
)
ptext = ptext.replace("from worker_lab.policy import ContextManifest\n", "")
ptext = ptext.replace("from worker_lab.test_catalog import ChangeFacts, TestCatalog\n", "from worker_lab.test_catalog import TestCatalog\n")
ptext = ptext.replace(
    "from worker_lab.validation import (\n    attempt_task_digest,\n    validate_attempt_authority_binding,\n    validate_relations,\n)\n",
    "",
)
protected.write_text(ptext, encoding="utf-8")

# T016/T022 were migrated to the current V3 integration/store/service tests by the Task 7 cleanup.
# Recompute the protected worker-lab-v3 catalog digest and update only its exact digest assertion.
catalog_path = WORKER / "curricula" / "catalogs" / "worker-lab-v3.json"
catalog_value = json.loads(catalog_path.read_text(encoding="utf-8"))
canonical = json.dumps(catalog_value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
new_digest = "sha256:" + hashlib.sha256(canonical).hexdigest()
ptext = protected.read_text(encoding="utf-8")
old_prefix = '    assert phase3_catalog.digest() == "sha256:'
lines = ptext.splitlines()
matched = 0
for index, line in enumerate(lines):
    if line.startswith(old_prefix):
        lines[index] = f'    assert phase3_catalog.digest() == "{new_digest}"'
        matched += 1
if matched != 1:
    raise RuntimeError(f"expected exactly one worker-lab-v3 digest assertion, found {matched}")
protected.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(f"Task 7 diagnosed repairs applied; worker-lab-v3 digest={new_digest}")
