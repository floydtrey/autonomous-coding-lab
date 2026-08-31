from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def query(args: argparse.Namespace) -> list[dict[str, Any]]:
    root = args.inventory_dir.resolve()
    prefix = "current-" if args.current else ""
    if args.delta:
        report = load_json(root / "integration-delta.json")
        return [
            row
            for component in report["components"]
            if not args.component or component["component"] == args.component
            for row in component["changes"]
        ]
    if args.connects:
        source, target = args.connects
        rows = load_json(root / f"{prefix}connections.json")["connections"]
        return [
            row
            for row in rows
            if row["source_component"] == source
            and row["target_component"] == target
        ]
    findings = load_json(root / f"{prefix}findings.json")["findings"]
    if args.finding:
        return [row for row in findings if row["finding_id"] == args.finding]
    if args.status or args.repair:
        return [
            row
            for row in findings
            if (not args.component or row["component"] == args.component)
            and (not args.status or row["status"] == args.status)
            and (not args.repair or row["repair_class"] == args.repair)
        ]
    if args.path_type:
        components = [args.component.lower()] if args.component else ["awf", "wlab", "lmb"]
        rows: list[dict[str, Any]] = []
        for component in components:
            path = root / f"{prefix}{component}.json"
            if not path.exists():
                continue
            inventory = load_json(path)
            for file in inventory["files"]:
                for reference in file["path_references"]:
                    if reference["path_type"] == args.path_type:
                        rows.append(
                            {
                                "component": inventory["component"],
                                "file_id": file["file_id"],
                                "source_path": file["source_path"],
                                "destination_path": file["destination_path"],
                                **reference,
                            }
                        )
        return rows
    return [
        row
        for row in findings
        if not args.component or row["component"] == args.component
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query ACL structural inventories.")
    parser.add_argument(
        "--inventory-dir", type=Path, default=Path("migration/inventory")
    )
    parser.add_argument("--component", choices=("AWF", "WLAB", "LMB"))
    parser.add_argument("--status", choices=("PASS", "FAIL", "KNOWN_GAP", "UNKNOWN"))
    parser.add_argument(
        "--repair",
        choices=(
            "NO_CHANGE",
            "MECHANICAL_REPAIR",
            "SEMANTIC_REVIEW",
            "EXTERNAL_RUNTIME",
            "HISTORICAL_ONLY",
            "EXCLUDED",
        ),
    )
    parser.add_argument("--path-type")
    parser.add_argument("--finding")
    parser.add_argument("--connects", nargs=2, metavar=("SOURCE", "TARGET"))
    parser.add_argument("--current", action="store_true")
    parser.add_argument("--delta", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = query(args)
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        for row in rows:
            identifier = (
                row.get("finding_id")
                or row.get("connection_id")
                or row.get("reference_id")
                or row.get("file_id")
            )
            status = row.get(
                "status", row.get("path_type", row.get("connection_type", ""))
            )
            location = row.get("destination_path", row.get("file_id", ""))
            line = row.get("line")
            suffix = f":{line}" if line else ""
            summary = row.get(
                "summary", row.get("evidence", row.get("expression", ""))
            )
            print(
                f"{status:12} {identifier or '-':36} "
                f"{location}{suffix} - {summary}"
            )
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
