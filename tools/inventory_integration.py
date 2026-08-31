from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from tools.inventory_trees import (
        analyze_text,
        build_connections,
        build_findings,
        decode_text,
        language_for,
        list_tree,
        read_blob,
        resolve_commit,
        resolve_tree,
        role_for,
        write_json,
    )
except ModuleNotFoundError:  # direct script execution from the repository root
    from inventory_trees import (
        analyze_text,
        build_connections,
        build_findings,
        decode_text,
        language_for,
        list_tree,
        read_blob,
        resolve_commit,
        resolve_tree,
        role_for,
        write_json,
    )


INVENTORY_VERSION = "acl-integrated-structure-inventory:v1"
DELTA_VERSION = "acl-source-integration-delta:v1"
SUMMARY_VERSION = "acl-integration-structure-summary:v1"
DEFAULT_COMPONENTS = ("AWF", "WLAB")


def _git_bytes(repo: Path, *args: str) -> bytes:
    process = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={repo.as_posix()}",
            "-C",
            str(repo),
            *args,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.returncode != 0:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Git integration check failed: {detail}")
    return process.stdout


def require_clean_components(repo: Path, prefixes: list[str]) -> None:
    status = _git_bytes(
        repo,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--",
        *prefixes,
    )
    if status:
        raise RuntimeError("Imported component scope is dirty; integration scan stopped")


def inventory_integrated_component(
    repo: Path,
    commit: str,
    source_inventory: dict[str, Any],
) -> dict[str, Any]:
    component = source_inventory["component"]
    prefix = source_inventory["destination_prefix"]
    subtree = resolve_tree(repo, commit, prefix)
    entries = list_tree(repo, f"{commit}:{prefix}")
    files: list[dict[str, Any]] = []
    cache: dict[str, tuple[bytes, str | None, str, str]] = {}
    for entry in entries:
        if entry.object_id not in cache:
            blob = read_blob(repo, entry.object_id)
            text, encoding, line_endings = decode_text(blob)
            cache[entry.object_id] = (blob, text, encoding, line_endings)
        blob, text, encoding, line_endings = cache[entry.object_id]
        language = language_for(entry.path, text is None)
        analysis = (
            analyze_text(entry.path, language, text)
            if text is not None
            else {
                "structures": {},
                "path_references": [],
                "signals": [],
                "parse_error": None,
            }
        )
        file_id = f"{component}:{entry.path}"
        for index, reference in enumerate(analysis["path_references"], start=1):
            reference["reference_id"] = f"{file_id}#PATH-{index:04d}"
        files.append(
            {
                "file_id": file_id,
                "component": component,
                "source_path": entry.path,
                "destination_path": str(PurePosixPath(prefix) / entry.path),
                "git_mode": entry.mode,
                "git_blob": entry.object_id,
                "sha256": hashlib.sha256(blob).hexdigest().upper(),
                "size": entry.size,
                "encoding": encoding,
                "line_endings": line_endings,
                "language": language,
                "role": role_for(entry.path, language),
                **analysis,
            }
        )
    language_counts = Counter(item["language"] for item in files)
    role_counts = Counter(item["role"] for item in files)
    path_counts = Counter(
        reference["path_type"]
        for item in files
        for reference in item["path_references"]
    )
    return {
        "schema_version": INVENTORY_VERSION,
        "component": component,
        "name": source_inventory["name"],
        "monorepo": str(repo),
        "monorepo_commit": commit,
        "component_prefix": prefix,
        "component_tree": subtree,
        "source_commit": source_inventory["source_commit"],
        "source_tree": source_inventory["source_tree"],
        "file_count": len(files),
        "byte_count": sum(item["size"] for item in files),
        "language_counts": dict(sorted(language_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "path_type_counts": dict(sorted(path_counts.items())),
        "files": files,
    }


def _without_reference_id(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key != "reference_id"}


def _list_delta(
    before: list[Any],
    after: list[Any],
    *,
    ignored_fields: frozenset[str] = frozenset(),
) -> dict[str, list[Any]] | None:
    def keyed(items: list[Any]) -> dict[str, Any]:
        return {
            json.dumps(
                (
                    {
                        key: value
                        for key, value in item.items()
                        if key not in ignored_fields
                    }
                    if isinstance(item, dict)
                    else item
                ),
                sort_keys=True,
                ensure_ascii=False,
            ): item
            for item in items
        }

    old = keyed(before)
    new = keyed(after)
    removed = [old[key] for key in sorted(set(old) - set(new))]
    added = [new[key] for key in sorted(set(new) - set(old))]
    if not removed and not added:
        return None
    return {"added": added, "removed": removed}


def structural_delta(
    source_file: dict[str, Any], integrated_file: dict[str, Any]
) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    source_paths = [
        _without_reference_id(item) for item in source_file["path_references"]
    ]
    integrated_paths = [
        _without_reference_id(item) for item in integrated_file["path_references"]
    ]
    path_delta = _list_delta(
        source_paths,
        integrated_paths,
        ignored_fields=frozenset({"line", "column"}),
    )
    if path_delta:
        changes["path_references"] = path_delta
    signal_delta = _list_delta(source_file["signals"], integrated_file["signals"])
    if signal_delta:
        changes["signals"] = signal_delta
    structure_changes: dict[str, Any] = {}
    keys = sorted(
        set(source_file["structures"]) | set(integrated_file["structures"])
    )
    for key in keys:
        delta = _list_delta(
            source_file["structures"].get(key, []),
            integrated_file["structures"].get(key, []),
            ignored_fields=frozenset({"line"}),
        )
        if delta:
            structure_changes[key] = delta
    if structure_changes:
        changes["structures"] = structure_changes
    if source_file["parse_error"] != integrated_file["parse_error"]:
        changes["parse_error"] = {
            "source": source_file["parse_error"],
            "integrated": integrated_file["parse_error"],
        }
    if not changes:
        changes["content_only"] = True
    return changes


def build_component_delta(
    source_inventory: dict[str, Any], integrated_inventory: dict[str, Any]
) -> dict[str, Any]:
    source_files = {item["source_path"]: item for item in source_inventory["files"]}
    integrated_files = {
        item["source_path"]: item for item in integrated_inventory["files"]
    }
    changes: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for path in sorted(set(source_files) | set(integrated_files)):
        source_file = source_files.get(path)
        integrated_file = integrated_files.get(path)
        if source_file is None:
            status = "ADDED"
        elif integrated_file is None:
            status = "REMOVED"
        elif source_file["git_blob"] == integrated_file["git_blob"]:
            status = "UNCHANGED"
        else:
            status = "MODIFIED"
        counts[status] += 1
        if status == "UNCHANGED":
            continue
        row: dict[str, Any] = {
            "file_id": f"{source_inventory['component']}:{path}",
            "relative_path": path,
            "integrated_path": str(
                PurePosixPath(source_inventory["destination_prefix"]) / path
            ),
            "status": status,
            "source_blob": source_file["git_blob"] if source_file else None,
            "integrated_blob": (
                integrated_file["git_blob"] if integrated_file else None
            ),
        }
        if status == "MODIFIED":
            row["structural_delta"] = structural_delta(source_file, integrated_file)
        changes.append(row)
    return {
        "component": source_inventory["component"],
        "source_commit": source_inventory["source_commit"],
        "source_tree": source_inventory["source_tree"],
        "component_prefix": integrated_inventory["component_prefix"],
        "integrated_tree": integrated_inventory["component_tree"],
        "change_counts": {
            status: counts.get(status, 0)
            for status in ("UNCHANGED", "MODIFIED", "ADDED", "REMOVED")
        },
        "changes": changes,
    }


def generate(
    repo: Path,
    commitish: str,
    inventory_dir: Path,
    component_codes: tuple[str, ...],
) -> int:
    repo = repo.resolve()
    commit = resolve_commit(repo, commitish)
    head = resolve_commit(repo, "HEAD")
    if commit != head:
        raise RuntimeError("Integration scan requires the current monorepo HEAD")
    monorepo_tree = resolve_tree(repo, commit)
    source_inventories = {
        code: json.loads(
            (inventory_dir / f"{code.lower()}.json").read_text(encoding="utf-8")
        )
        for code in component_codes
    }
    prefixes = [
        source_inventories[code]["destination_prefix"] for code in component_codes
    ]
    require_clean_components(repo, prefixes)

    integrated: list[dict[str, Any]] = []
    deltas: list[dict[str, Any]] = []
    for code in component_codes:
        current = inventory_integrated_component(repo, commit, source_inventories[code])
        integrated.append(current)
        deltas.append(build_component_delta(source_inventories[code], current))
        write_json(inventory_dir / f"current-{code.lower()}.json", current)

    findings = build_findings(integrated)
    connections = build_connections(integrated)
    delta_report = {
        "schema_version": DELTA_VERSION,
        "monorepo_commit": commit,
        "monorepo_tree": monorepo_tree,
        "components": deltas,
    }
    summary = {
        "schema_version": SUMMARY_VERSION,
        "monorepo_commit": commit,
        "monorepo_tree": monorepo_tree,
        "components": [
            {
                "component": item["component"],
                "component_prefix": item["component_prefix"],
                "component_tree": item["component_tree"],
                "file_count": item["file_count"],
                "byte_count": item["byte_count"],
                "path_type_counts": item["path_type_counts"],
                "change_counts": delta["change_counts"],
            }
            for item, delta in zip(integrated, deltas, strict=True)
        ],
        "finding_counts": findings["counts"],
        "connection_count": connections["connection_count"],
    }
    write_json(inventory_dir / "current-findings.json", findings)
    write_json(inventory_dir / "current-connections.json", connections)
    write_json(inventory_dir / "integration-delta.json", delta_report)
    write_json(inventory_dir / "integration-summary.json", summary)
    if resolve_commit(repo, "HEAD") != commit:
        raise RuntimeError("Monorepo commit changed during integration scan")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory imported component trees and compare them with preserved source inventories."
        )
    )
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument(
        "--inventory-dir", type=Path, default=Path("migration/inventory")
    )
    parser.add_argument(
        "--component",
        action="append",
        choices=DEFAULT_COMPONENTS,
        dest="components",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    components = tuple(args.components) if args.components else DEFAULT_COMPONENTS
    return generate(
        args.repo,
        args.commit,
        args.inventory_dir.resolve(),
        components,
    )


if __name__ == "__main__":
    raise SystemExit(main())
