from pathlib import Path

ROOT = Path.cwd()

plan_path = ROOT / "docs" / "RUNTIME_CORE_RECONSTRUCTION_PLAN.md"
plan = plan_path.read_text(encoding="utf-8")
old_status = "**Status:** approved plan; Tasks 1-6 complete; Task 7 next"
new_status = "**Status:** approved plan; Tasks 1-7 complete; Task 8 next"
if old_status not in plan and new_status not in plan:
    raise RuntimeError("reconstruction plan status anchor missing")
plan = plan.replace(old_status, new_status, 1)

task7_heading = "### Task 7 — remove obsolete active-tree implementation\n\n"
status_line = "**Status:** complete in the Task 7 reconstruction checkpoint.\n\n"
if task7_heading + status_line not in plan:
    if task7_heading not in plan:
        raise RuntimeError("Task 7 heading missing")
    plan = plan.replace(task7_heading, task7_heading + status_line, 1)

stop_gate = (
    "**Stop gate:** repository scan finds no obsolete runtime architecture in current production code/configuration and no stale documents capable of being mistaken for current architecture; any surviving repository-specific contract is explicitly justified as a Git-backed workspace/backend concern.\n\n"
)
accepted = """**Accepted Task 7 boundary:** the obsolete Codex/Terra/MineTrackerWorker commissioning runtime, old V2 bridge/invocation/read-only execution path, synthetic execution path, old installation/monorepo manifests, production Mine Tracker profile, commissioning-only proof bundle, and superseded current handoff/workplan documents are removed from the active tree. Retained application-service/lifecycle/runtime-selection/provider-qualification paths are current V3-only; Windows Job Objects remain only as the current containment backend and Git facts remain bounded workspace/source-state evidence. The protected Worker Lab V3 integration tests T016/T022 now target the current V3 integration/store/application-service acceptance path. Portable V1 identity was mechanically refreshed for the reduced current tree only; true host-independent portable identity V2 remains Task 8. The surviving framework suite passed 76 tests, Worker Lab passed 319 tests with one environment-only symlink skip, portable installation passed 4 tests, and the production/configuration obsolete-reference scan was empty. Execution remained `DISABLED`; no provider/model request or actual capability qualification was performed.\n\n"""
if accepted not in plan:
    if stop_gate not in plan:
        raise RuntimeError("Task 7 stop-gate anchor missing")
    plan = plan.replace(stop_gate, stop_gate + accepted, 1)
plan_path.write_text(plan, encoding="utf-8")

current_path = ROOT / "docs" / "CURRENT_STATE.md"
current = current_path.read_text(encoding="utf-8")
section = """## Runtime reconstruction Task 7 — accepted checkpoint

Task 7 removes obsolete active-tree runtime/commissioning implementation after the current V3 replacements were accepted. It does not perform the portable-identity V2 redesign or enable execution.

Accepted changes:

- deleted obsolete Codex/Terra commissioning modules, the old local commissioning harness/fixture contracts, and old Worker Lab V2 bridge/client/invocation/read-only/synthetic execution modules rather than retaining compatibility shims;
- deleted `config/installation-manifest.json` and `config/monorepo-identity.json`; current operator health/installation inspection uses the disabled portable manifest rather than the obsolete Codex-era installation contract;
- removed the embedded production Mine Tracker consumer profile and the active Phase 4 record-normalizer proof bundle tied to the old `MineTrackerWorker` repository;
- retained Windows Job Object custody/absence evidence as the current containment backend while removing the obsolete V2 Windows adapter runner;
- retained Git repository/head/change evidence only where the coding-workspace, handoff, publication, or source-state boundary requires it; repository identity is not restored as ACL logical target identity;
- current application-service record handling, lifecycle binding, runtime selection, provider qualification, and tests no longer depend on the deleted V2/commissioning modules;
- protected Worker Lab V3 tests T016/T022 now exercise `test_integration_v3.py`, `test_invocation_store_v3.py`, and `test_application_service_v3.py`; the protected catalog digest was re-baselined for that explicit authority change;
- superseded `docs/VS_CODE_HANDOFF.md` and `docs/WORKPLAN.md` were removed because they could be mistaken for current instructions;
- portable V1 byte identity was refreshed only to describe the reduced current tree: Autonomous Worker Framework is 8 files at `sha256:edac32b728348d6a2e2c7521d1c846e5021fe6e40f33db70e7df625d1ca584c5`, Worker Lab is 29 files at `sha256:8b92b879d555d3c695318809895947b0a6ac9b1e87cf6caef5db5ad7541549e7`, and Local Model Bench remains 10 files at `sha256:139331ea42c914575d1119125a702ac5de2129b9bedc235bfc189700e8265afc`;
- execution authority remains `DISABLED`; no provider/model request or actual capability qualification was performed.

Validation on the Task 7 materialized candidate:

- Python production compilation and current Worker Lab service imports passed;
- complete surviving Autonomous Worker Framework suite: 76 passed;
- complete surviving Worker Lab suite: 319 passed, 1 skipped because symlink creation was unavailable on the Linux runner;
- portable installation contract: 4 passed;
- production/configuration scan returned zero references for the retired Codex/Terra/MineTrackerWorker/commissioning/V2 bridge/legacy-manifest terms targeted by Task 7.

"""
marker = "## Current stop condition\n"
if section not in current:
    if marker not in current:
        raise RuntimeError("CURRENT_STATE stop-condition anchor missing")
    current = current.replace(marker, section + marker, 1)

next_gate = """## Immediate next gate

Begin only **Task 8 — portable identity V2 and documentation cleanup** from
`docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` in a later bounded task.

Task 8 rebuilds the portable component/source identity around the now-current modules,
separates source identity from host qualification/local activation, and cleans current
documentation to describe one system-centered architecture. Do not broaden Task 8 into
actual provider/model execution; that remains behind the Task 9 reconstruction
acceptance gate and separate authorization.
"""
head = current.find("## Immediate next gate\n")
if head < 0:
    raise RuntimeError("CURRENT_STATE next-gate anchor missing")
current = current[:head] + next_gate
current_path.write_text(current, encoding="utf-8")

print("Task 7 checkpoint documentation materialized")
