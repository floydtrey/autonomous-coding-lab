import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
expected_framework_files = [
    "tools/code_task.py",
    "tools/consumer_profile.py",
    "tools/dispatch_adapter.py",
    "tools/pydantic_ollama_worker.py",
    "tools/repository_handoff.py",
    "tools/repository_state.py",
    "tools/worker_result.py",
    "tools/worker_runtime.py",
]

manifest_path = root / "config" / "portable-source-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["components"]["autonomous-worker-framework"]["files"] = expected_framework_files
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

path = root / "tools" / "verify_portable_source.py"
text = path.read_text(encoding="utf-8")
old_rule = 'component = _object(raw, {"root", "production_root", "scope", "digest", "files"}, allow_optional={"files"})'
new_rule = 'component = _object(raw, {"root", "production_root", "scope", "digest"}, allow_optional={"files"})'
if text.count(old_rule) != 1:
    raise SystemExit(f"optional-files verifier anchor count: {text.count(old_rule)}")
text = text.replace(old_rule, new_rule, 1)
old_files = '''_FRAMEWORK_FILES = (\n    "tools/code_task.py",\n    "tools/consumer_profile.py",\n    "tools/dispatch_adapter.py",\n    "tools/local_git_publisher.py",\n    "tools/local_validate.py",\n    "tools/pydantic_ollama_worker.py",\n    "tools/repository_handoff.py",\n    "tools/repository_state.py",\n)'''
new_files = '''_FRAMEWORK_FILES = (\n    "tools/code_task.py",\n    "tools/consumer_profile.py",\n    "tools/dispatch_adapter.py",\n    "tools/pydantic_ollama_worker.py",\n    "tools/repository_handoff.py",\n    "tools/repository_state.py",\n    "tools/worker_result.py",\n    "tools/worker_runtime.py",\n)'''
if text.count(old_files) != 1:
    raise SystemExit(f"framework closure verifier anchor count: {text.count(old_files)}")
path.write_text(text.replace(old_files, new_files, 1), encoding="utf-8")
print("Task 8 V2 verifier repaired and Task 7 framework closure preserved")
