from pathlib import Path

root = Path(__file__).resolve().parents[1]

current = root / "docs" / "CURRENT_STATE.md"
text = current.read_text(encoding="utf-8")
anchor = "`docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` is the remaining reconstruction acceptance plan. No actual provider/model execution occurs during reconstruction."
if anchor not in text:
    raise SystemExit("current-state reconstruction authority sentence missing")
# The exact lowercase phrase is intentionally durable for documentation tests/search.
text = text.replace(anchor, "`docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` is the remaining reconstruction acceptance plan. no actual provider/model execution occurs during reconstruction.", 1)
current.write_text(text, encoding="utf-8")

governance = root / "docs" / "GOVERNANCE.md"
text = governance.read_text(encoding="utf-8")
anchor = "## Fail-closed rules\n\nReject or block when a required protected identity, digest, scope, test, custody record, Provider Binding, source identity, or capability-specific workspace evidence is missing, stale, unknown, or mismatched."
replacement = "## Fail-closed rules\n\nFail closed: reject or block when a required protected identity, digest, scope, test, custody record, Provider Binding, source identity, or capability-specific workspace evidence is missing, stale, unknown, or mismatched."
if anchor not in text:
    raise SystemExit("governance fail-closed anchor missing")
governance.write_text(text.replace(anchor, replacement, 1), encoding="utf-8")
print("Task 8 durable documentation invariants repaired")
