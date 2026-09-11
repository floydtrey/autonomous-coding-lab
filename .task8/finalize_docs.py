from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "docs" / "CURRENT_STATE.md"
text = path.read_text(encoding="utf-8")
old = '''## Validation status

Task 8 focused source-identity/V3 validation passes on Linux CI, demonstrating that source identity does not require Windows host claims. The final Task 8 checkpoint still requires the complete surviving component suites, source-manifest verification, current-document scan, and exact-byte validation before publication.
'''
new = '''## Task 8 acceptance evidence

The materialized Task 8 candidate passed the complete current deterministic gate on Linux CI:

- Autonomous Worker Framework: **76 passed**;
- Worker Lab: **325 passed, 1 skipped** because symlink creation was unavailable on the runner;
- root source/inventory tests: **12 passed**;
- portable source identity V2 verifier: all components `MATCH`;
- Autonomous Worker Framework: 8-file closure at `sha256:edac32b728348d6a2e2c7521d1c846e5021fe6e40f33db70e7df625d1ca584c5`;
- Local Model Bench: 10-file production tree at `sha256:139331ea42c914575d1119125a702ac5de2129b9bedc235bfc189700e8265afc`;
- Worker Lab: 29-file production tree at `sha256:08a13548f9e193c85ae1280a56386237e1c3903467eb6681602827340825ab96`;
- portable source report contains no execution authority, host requirements, Python executable, or execution-readiness claim;
- current production/config scan for removed portable-V1/commissioning architecture: empty;
- current operating-document scan for obsolete runtime architecture: empty;
- protected pytest catalog paths are now mechanically checked to reference existing test files.

All provider/capability behavior in these tests remained injected or mocked. No actual provider/model request or capability qualification was performed.
'''
if text.count(old) != 1:
    raise SystemExit(f"validation status block count: {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Task 8 acceptance evidence recorded")
