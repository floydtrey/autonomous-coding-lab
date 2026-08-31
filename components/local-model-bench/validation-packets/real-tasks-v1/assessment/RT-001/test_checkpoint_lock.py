from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from localbench.util import atomic_write_json


class CheckpointLockAssessmentTests(unittest.TestCase):
    def test_transient_replace_lock_is_retried(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "checkpoint.json"
            target.write_text('{"old": true}\n', encoding="utf-8")
            real_replace = os.replace
            calls = 0

            def transient_lock(source, destination):
                nonlocal calls
                calls += 1
                if calls <= 3:
                    raise PermissionError("synthetic reader lock")
                return real_replace(source, destination)

            with patch("localbench.util.os.replace", side_effect=transient_lock):
                atomic_write_json(target, {"new": True})

            self.assertGreaterEqual(calls, 4)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"new": True})
            self.assertEqual(list(target.parent.glob(".checkpoint.json.*.tmp")), [])

    def test_persistent_replace_lock_raises_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "checkpoint.json"
            original = '{"old": true}\n'
            target.write_text(original, encoding="utf-8")

            with (
                patch(
                    "localbench.util.os.replace",
                    side_effect=PermissionError("persistent synthetic lock"),
                ) as replace,
                patch("localbench.util.time.sleep"),
            ):
                with self.assertRaises(PermissionError):
                    atomic_write_json(target, {"new": True})

            self.assertGreater(replace.call_count, 1)
            self.assertLessEqual(replace.call_count, 100)
            self.assertEqual(target.read_text(encoding="utf-8"), original)
            self.assertEqual(list(target.parent.glob(".checkpoint.json.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
