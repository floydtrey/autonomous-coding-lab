from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from localbench.cli import main
from localbench.evaluate import evaluate_run


def plan_record() -> dict:
    content = {
        "response_type": "plan",
        "status": "ready",
        "requirements": [{"id": "R1", "interpretation": "Keep output isolated."}],
        "assumptions": [],
        "blocking_questions": [],
        "affected_components": ["evaluation"],
        "steps": [{
            "id": "P1",
            "objective": "Write the snapshot.",
            "requirement_ids": ["R1"],
            "dependencies": [],
            "verification": ["Canonical files are unchanged."],
        }],
        "risks": [{"risk": "overwrite", "mitigation": "refuse existing output"}],
        "verification_strategy": ["Compare file hashes."],
    }
    return {
        "status": "success",
        "suite_id": "snapshot-assessment",
        "case_id": "plan",
        "model": {"id": "model-a", "name": "model-a", "provider": "fake"},
        "case_metadata": {"evaluation": {
            "kind": "plan",
            "expected_status": "ready",
            "requirement_ids": ["R1"],
            "max_items": 2,
        }},
        "response": {"content": json.dumps(content), "finish_reason": "stop"},
    }


class SnapshotEvaluationAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        cases = self.root / "models" / "001-model" / "cases"
        cases.mkdir(parents=True)
        (self.root / "manifest.json").write_text(json.dumps({
            "run_id": "live-run",
            "status": "running",
            "models": [{"sequence": 1, "id": "model-a"}],
        }), encoding="utf-8")
        (self.root / "checkpoint.json").write_text(
            '{"status":"running","progress":{"completed":1,"total":2}}\n',
            encoding="utf-8",
        )
        (cases / "0001.json").write_text(json.dumps(plan_record()), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def _control_bytes(self) -> dict[str, bytes]:
        return {
            str(path.relative_to(self.root)): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file() and "snapshots" not in path.parts
        }

    def test_snapshot_preserves_every_preexisting_run_file(self):
        for name in ("evaluation.json", "evaluation.csv", "evaluation.md"):
            (self.root / name).write_text(f"canonical-{name}\n", encoding="utf-8")
        before = self._control_bytes()

        report = evaluate_run(self.root, snapshot="review-001")

        self.assertEqual(before, self._control_bytes())
        output = self.root / "snapshots" / "review-001"
        self.assertEqual(
            sorted(path.name for path in output.iterdir()),
            ["evaluation.csv", "evaluation.json", "evaluation.md"],
        )
        self.assertEqual(report["snapshot"]["name"], "review-001")
        self.assertEqual(report["snapshot"]["manifest_status"], "running")
        self.assertEqual(report["snapshot"]["terminal_case_files"], 1)
        self.assertEqual(report["snapshot"]["created_at"], report["generated_at"])

    def test_cli_supports_snapshot_and_default_remains_canonical(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["evaluate", "--run", str(self.root), "--snapshot", "cli-snap"])
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "snapshots" / "cli-snap" / "evaluation.json").is_file())
        self.assertFalse((self.root / "evaluation.json").exists())

        with contextlib.redirect_stdout(io.StringIO()):
            code = main(["evaluate", "--run", str(self.root)])
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "evaluation.json").is_file())

    def test_unsafe_and_existing_snapshot_names_are_refused(self):
        for unsafe in ("../escape", "nested/name", "", "."):
            with self.subTest(name=unsafe), self.assertRaises(ValueError):
                evaluate_run(self.root, snapshot=unsafe)

        evaluate_run(self.root, snapshot="immutable")
        marker = self.root / "snapshots" / "immutable" / "marker.txt"
        marker.write_text("keep\n", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            evaluate_run(self.root, snapshot="immutable")
        self.assertEqual(marker.read_text(encoding="utf-8"), "keep\n")


if __name__ == "__main__":
    unittest.main()
