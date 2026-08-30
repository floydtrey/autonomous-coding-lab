from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .util import atomic_write_json, read_json, utc_now


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def _unique_ids(items: Any) -> tuple[bool, list[str]]:
    if not isinstance(items, list):
        return False, []
    ids: list[str] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            return False, []
        ids.append(item["id"])
    return len(ids) == len(set(ids)), ids


def _valid_graph(items: list[dict[str, Any]]) -> tuple[bool, str]:
    valid_ids, ids = _unique_ids(items)
    if not valid_ids:
        return False, "items need unique string ids"
    known = set(ids)
    graph: dict[str, list[str]] = {}
    positions = {item_id: index for index, item_id in enumerate(ids)}
    for item in items:
        dependencies = item.get("dependencies")
        if not _string_list(dependencies) and dependencies != []:
            return False, f"{item['id']} dependencies must be a string list"
        dependencies = dependencies or []
        if any(dep not in known for dep in dependencies):
            return False, f"{item['id']} references an unknown dependency"
        if any(positions[dep] >= positions[item["id"]] for dep in dependencies):
            return False, f"{item['id']} dependency is not earlier in output order"
        graph[item["id"]] = dependencies

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return False
        if node in visited:
            return True
        visiting.add(node)
        if not all(visit(dep) for dep in graph[node]):
            return False
        visiting.remove(node)
        visited.add(node)
        return True

    if not all(visit(node) for node in ids):
        return False, "dependency cycle detected"
    return True, "dependency ids are valid, acyclic, and ordered"


def _plan_contract(document: dict[str, Any], maximum: int) -> tuple[bool, str, list[dict[str, Any]]]:
    required = {
        "response_type", "status", "requirements", "assumptions", "blocking_questions",
        "affected_components", "steps", "risks", "verification_strategy",
    }
    if not required.issubset(document):
        return False, f"missing keys: {sorted(required - set(document))}", []
    if not all(_string_list(document[key]) or document[key] == [] for key in (
        "assumptions", "blocking_questions", "affected_components", "verification_strategy"
    )):
        return False, "plan list fields must contain strings", []
    requirements = document.get("requirements")
    if not isinstance(requirements, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("id"), str)
        or not isinstance(item.get("interpretation"), str)
        for item in requirements
    ):
        return False, "requirements must contain id and interpretation", []
    risks = document.get("risks")
    if not isinstance(risks, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("risk"), str)
        or not isinstance(item.get("mitigation"), str)
        for item in risks
    ):
        return False, "risks must contain risk and mitigation", []
    steps = document.get("steps")
    if not isinstance(steps, list) or len(steps) > maximum:
        return False, f"steps must be an array with at most {maximum} items", []
    if document.get("status") == "ready" and not steps:
        return False, "ready plans require at least one step", []
    if document.get("status") == "blocked" and (steps or not document.get("blocking_questions")):
        return False, "blocked plans require questions and no implementation steps", []
    for step in steps:
        if not isinstance(step, dict):
            return False, "every step must be an object", []
        if not isinstance(step.get("objective"), str) or not step["objective"].strip():
            return False, "every step needs an objective", []
        if not _string_list(step.get("requirement_ids")):
            return False, "every step needs requirement_ids", []
        if not _string_list(step.get("verification")):
            return False, "every step needs verification entries", []
    return True, "plan contract is complete", steps


def _task_contract(document: dict[str, Any], maximum: int) -> tuple[bool, str, list[dict[str, Any]]]:
    required = {
        "response_type", "status", "source_plan_status", "requirement_ids",
        "blocking_questions", "tasks",
    }
    if not required.issubset(document):
        return False, f"missing keys: {sorted(required - set(document))}", []
    if not _string_list(document.get("requirement_ids")):
        return False, "task set needs requirement_ids", []
    if not (_string_list(document.get("blocking_questions")) or document.get("blocking_questions") == []):
        return False, "blocking_questions must be a string array", []
    tasks = document.get("tasks")
    if not isinstance(tasks, list) or len(tasks) > maximum:
        return False, f"tasks must be an array with at most {maximum} items", []
    if document.get("status") == "ready" and not tasks:
        return False, "ready task sets require at least one task", []
    if document.get("status") == "blocked" and (tasks or not document.get("blocking_questions")):
        return False, "blocked task sets require questions and no implementation tasks", []
    for task in tasks:
        if not isinstance(task, dict):
            return False, "every task must be an object", []
        scope = task.get("scope")
        if not isinstance(scope, dict) or not {"include", "exclude"}.issubset(scope):
            return False, "every task needs include/exclude scope", []
        if not all(_string_list(scope.get(key)) or scope.get(key) == [] for key in ("include", "exclude")):
            return False, "task scope values must be string arrays", []
        for key in ("objective", "worker_instruction"):
            if not isinstance(task.get(key), str) or not task[key].strip():
                return False, f"every task needs {key}", []
        for key in ("requirement_ids", "implementation_work", "acceptance_criteria", "tests"):
            if not _string_list(task.get(key)):
                return False, f"every task needs non-empty {key}", []
    return True, "task contract is complete", tasks


def _check(name: str, passed: bool, weight: int, detail: str) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "weight": weight,
        "earned": weight if passed else 0,
        "detail": detail,
    }


def evaluate_case(record: dict[str, Any]) -> dict[str, Any] | None:
    spec = record.get("case_metadata", {}).get("evaluation")
    if not isinstance(spec, dict):
        return None
    checks: list[dict[str, Any]] = []
    transport_ok = record.get("status") == "success" and isinstance(record.get("response"), dict)
    checks.append(_check("transport_success", transport_ok, 5, str(record.get("status"))))
    finish_reason = (record.get("response") or {}).get("finish_reason")
    complete = finish_reason not in {"length", "max_tokens"}
    checks.append(_check("not_truncated", complete, 5, f"finish_reason={finish_reason}"))
    content = (record.get("response") or {}).get("content", "")
    document: dict[str, Any] | None = None
    parse_detail = "response is unavailable"
    if transport_ok and isinstance(content, str):
        try:
            parsed = json.loads(content.strip())
            if isinstance(parsed, dict):
                document = parsed
                parse_detail = "exact JSON object"
            else:
                parse_detail = "JSON root is not an object"
        except json.JSONDecodeError as exc:
            parse_detail = f"invalid JSON at line {exc.lineno} column {exc.colno}"
    checks.append(_check("json_object", document is not None, 15, parse_detail))

    kind = str(spec.get("kind", ""))
    expected_status = str(spec.get("expected_status", "ready"))
    expected_requirements = [str(item) for item in spec.get("requirement_ids", [])]
    maximum = int(spec.get("max_items", 7))
    response_type_ok = bool(document and document.get("response_type") == kind)
    checks.append(_check("response_type", response_type_ok, 5, f"expected {kind}"))
    status_ok = bool(document and document.get("status") == expected_status)
    checks.append(_check("decision_status", status_ok, 10, f"expected {expected_status}"))

    contract_ok = False
    contract_detail = "JSON unavailable"
    items: list[dict[str, Any]] = []
    if document:
        if kind == "plan":
            contract_ok, contract_detail, items = _plan_contract(document, maximum)
        elif kind == "task_set":
            contract_ok, contract_detail, items = _task_contract(document, maximum)
        else:
            contract_detail = f"unknown evaluation kind {kind!r}"
    forbidden = [str(item).casefold() for item in spec.get("forbidden_substrings", [])]
    present_forbidden = [item for item in forbidden if item and item in str(content).casefold()]
    if present_forbidden:
        contract_ok = False
        contract_detail += f"; forbidden content: {present_forbidden}"
    checks.append(_check("contract_shape", contract_ok, 10, contract_detail))

    declared: list[str] = []
    if document:
        if kind == "plan" and isinstance(document.get("requirements"), list):
            declared = [item.get("id") for item in document["requirements"] if isinstance(item, dict)]
        elif kind == "task_set" and isinstance(document.get("requirement_ids"), list):
            declared = document["requirement_ids"]
    requirement_ok = set(declared) == set(expected_requirements) and len(declared) == len(set(declared))
    checks.append(_check(
        "requirement_set", requirement_ok, 10,
        f"expected={expected_requirements}; declared={declared}",
    ))

    item_contract_ok, item_ids = _unique_ids(items)
    if expected_status == "blocked" and items == []:
        item_contract_ok = True
    checks.append(_check("item_ids", item_contract_ok, 10, f"ids={item_ids}"))

    referenced: list[str] = []
    for item in items:
        if isinstance(item.get("requirement_ids"), list):
            referenced.extend(item["requirement_ids"])
    traceability_ok = (
        expected_status == "blocked" and not referenced
    ) or (
        set(referenced) == set(expected_requirements)
        and all(item in expected_requirements for item in referenced)
    )
    checks.append(_check(
        "requirement_traceability", traceability_ok, 10,
        f"referenced={sorted(set(referenced))}",
    ))

    if not items:
        graph_ok = expected_status == "blocked"
        graph_detail = "no items expected for blocked response" if graph_ok else "no items"
    else:
        graph_ok, graph_detail = _valid_graph(items)
    checks.append(_check("dependency_graph", graph_ok, 10, graph_detail))

    semantic_specs = spec.get("semantic_checks", [])
    semantic_hits: list[str] = []
    folded = str(content).casefold()
    for semantic in semantic_specs:
        if not isinstance(semantic, dict):
            continue
        alternatives = [str(item).casefold() for item in semantic.get("any_of", [])]
        if any(item and item in folded for item in alternatives):
            semantic_hits.append(str(semantic.get("label", "unnamed")))
    semantic_ok = not semantic_specs or len(semantic_hits) == len(semantic_specs)
    checks.append(_check(
        "semantic_anchors", semantic_ok, 10,
        f"matched={semantic_hits}; expected={len(semantic_specs)}",
    ))

    hard_check_names = {
        "transport_success", "not_truncated", "json_object", "response_type",
        "decision_status", "contract_shape", "item_ids", "dependency_graph",
    }
    hard_failures = [item["name"] for item in checks if item["name"] in hard_check_names and not item["passed"]]
    return {
        "model_id": record.get("model", {}).get("id"),
        "model_name": record.get("model", {}).get("name"),
        "provider": record.get("model", {}).get("provider"),
        "suite_id": record.get("suite_id"),
        "case_id": record.get("case_id"),
        "kind": kind,
        "expected_status": expected_status,
        "deterministic_score": sum(item["earned"] for item in checks),
        "maximum_score": sum(item["weight"] for item in checks),
        "hard_fail": bool(hard_failures),
        "hard_failures": hard_failures,
        "checks": checks,
    }


def evaluate_run(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    if not (run_dir / "manifest.json").is_file():
        raise FileNotFoundError(f"run directory has no manifest.json: {run_dir}")
    results: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("models/*/cases/*.json")):
        evaluated = evaluate_case(read_json(path))
        if evaluated:
            results.append(evaluated)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        grouped[str(item["model_id"])].append(item)
    models: list[dict[str, Any]] = []
    manifest = read_json(run_dir / "manifest.json")
    order = {item["id"]: item["sequence"] for item in manifest.get("models", [])}
    for model_id, items in grouped.items():
        maximum = sum(item["maximum_score"] for item in items)
        earned = sum(item["deterministic_score"] for item in items)
        models.append({
            "sequence": order.get(model_id),
            "model_id": model_id,
            "model_name": items[0]["model_name"],
            "provider": items[0]["provider"],
            "evaluated_cases": len(items),
            "hard_failures": sum(item["hard_fail"] for item in items),
            "deterministic_score": earned,
            "maximum_score": maximum,
            "percent": round(earned / maximum * 100, 2) if maximum else 0,
        })
    models.sort(key=lambda item: (item.get("sequence") or 9999, item["model_id"]))
    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "run_id": manifest.get("run_id"),
        "note": "Deterministic contract score; semantic quality still requires review.",
        "models": models,
        "cases": results,
    }
    atomic_write_json(run_dir / "evaluation.json", report)

    csv_fields = [
        "model_id", "model_name", "provider", "suite_id", "case_id", "kind",
        "expected_status", "deterministic_score", "maximum_score", "hard_fail",
        "hard_failures", "failed_checks",
    ]
    csv_path = run_dir / "evaluation.csv"
    temp_path = run_dir / ".evaluation.csv.tmp"
    with temp_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for item in results:
            writer.writerow({
                **{key: item.get(key) for key in csv_fields},
                "hard_failures": ";".join(item["hard_failures"]),
                "failed_checks": ";".join(
                    check["name"] for check in item["checks"] if not check["passed"]
                ),
            })
    temp_path.replace(csv_path)

    lines = [
        "# Deterministic benchmark evaluation",
        "",
        "This score measures JSON/contract compliance, traceability, dependency validity,",
        "completion, and configured semantic anchors. It does not replace human review.",
        "",
        "| Model | Cases | Hard failures | Score |",
        "|---|---:|---:|---:|",
    ]
    for model in models:
        lines.append(
            f"| {model['model_id']} | {model['evaluated_cases']} | "
            f"{model['hard_failures']} | {model['deterministic_score']}/{model['maximum_score']} "
            f"({model['percent']}%) |"
        )
    lines.extend(["", "## Case details", ""])
    for model in models:
        lines.append(f"### {model['model_id']}")
        lines.append("")
        lines.append("| Case | Score | Hard failure | Failed checks |")
        lines.append("|---|---:|---:|---|")
        for item in grouped[model["model_id"]]:
            failed = ", ".join(check["name"] for check in item["checks"] if not check["passed"])
            lines.append(
                f"| {item['case_id']} | {item['deterministic_score']}/{item['maximum_score']} | "
                f"{'yes' if item['hard_fail'] else 'no'} | {failed or '-'} |"
            )
        lines.append("")
    (run_dir / "evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
