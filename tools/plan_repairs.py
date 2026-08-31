from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from tools.inventory_trees import write_json
except ModuleNotFoundError:  # direct script execution from the repository root
    from inventory_trees import write_json


REPAIR_REGISTRY = {
    "AWF-PATH-008": {
        "transformation": "normalize_git_paths_to_component_root",
        "additional_files": [
            "components/autonomous-worker-framework/tests/test_local_validate.py"
        ],
        "required_validation": [
            "focused local-validator regression tests",
            "documented framework full validation",
            "structural inventory regeneration",
        ],
    }
}


def build_plan(inventory_dir: Path) -> dict[str, Any]:
    findings = json.loads(
        (inventory_dir / "findings.json").read_text(encoding="utf-8")
    )["findings"]
    inventories = {
        component: json.loads(
            (inventory_dir / f"{component.lower()}.json").read_text(encoding="utf-8")
        )
        for component in ("AWF", "WLAB", "LMB")
    }
    changes: list[dict[str, Any]] = []
    for finding in findings:
        registered = REPAIR_REGISTRY.get(finding["finding_id"])
        if not registered:
            continue
        if finding["status"] != "FAIL" or finding["repair_class"] != "MECHANICAL_REPAIR":
            raise RuntimeError(
                f"Registered repair is not an active mechanical failure: {finding['finding_id']}"
            )
        file = next(
            item
            for item in inventories[finding["component"]]["files"]
            if item["file_id"] == finding["file_id"]
        )
        changes.append(
            {
                "change_id": f"M2-{finding['finding_id']}",
                "finding_id": finding["finding_id"],
                "classification": finding["repair_class"],
                "starting_blob": file["git_blob"],
                "files": [finding["destination_path"], *registered["additional_files"]],
                "transformation": registered["transformation"],
                "required_validation": registered["required_validation"],
                "automatic_commit": False,
            }
        )
    return {
        "schema_version": "acl-structure-repair-plan:v1",
        "change_count": len(changes),
        "changes": changes,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a guarded repair plan from mechanical inventory findings."
    )
    parser.add_argument(
        "--inventory-dir", type=Path, default=Path("migration/inventory")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("migration/inventory/repair-plan.json")
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = build_plan(args.inventory_dir.resolve())
    write_json(args.output.resolve(), plan)
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
