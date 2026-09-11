from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "tools" / "verify_portable_source.py"
text = path.read_text(encoding="utf-8")
old = 'component = _object(raw, {"root", "production_root", "scope", "digest", "files"}, allow_optional={"files"})'
new = 'component = _object(raw, {"root", "production_root", "scope", "digest"}, allow_optional={"files"})'
if text.count(old) != 1:
    raise SystemExit(f"optional-files verifier anchor count: {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Task 8 V2 verifier optional-files rule repaired")
