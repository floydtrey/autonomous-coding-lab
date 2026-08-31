from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCHEMA_VERSION = "acl-structure-inventory:v1"
FINDINGS_VERSION = "acl-structure-findings:v1"
CONNECTIONS_VERSION = "acl-structure-connections:v1"

WINDOWS_ABSOLUTE = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|//)")
URL = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
QUOTED = re.compile(r"(?P<quote>['\"`])(?P<value>.*?)(?P=quote)")
POWERSHELL_ENV = re.compile(r"\$env:([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)
PYTHON_ENV = re.compile(
    r"(?:os\.environ(?:\.get)?\s*\[?\s*|os\.getenv\s*\()"
    r"['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]"
)


@dataclass(frozen=True)
class GitEntry:
    mode: str
    object_id: str
    size: int
    path: str


def _git(repo: Path, *args: str, text: bool = False) -> bytes | str:
    command = [
        "git",
        "-c",
        f"safe.directory={repo.as_posix()}",
        "-C",
        str(repo),
        *args,
    ]
    process = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.returncode != 0:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Git command failed ({' '.join(command)}): {detail}")
    if text:
        return process.stdout.decode("utf-8", errors="surrogateescape").strip()
    return process.stdout


def resolve_commit(repo: Path, requested: str) -> str:
    return str(_git(repo, "rev-parse", f"{requested}^{{commit}}", text=True))


def resolve_tree(repo: Path, commit: str, prefix: str | None = None) -> str:
    expression = f"{commit}:{prefix}" if prefix else f"{commit}^{{tree}}"
    return str(_git(repo, "rev-parse", expression, text=True))


def list_tree(repo: Path, commit: str) -> list[GitEntry]:
    raw = _git(repo, "ls-tree", "-r", "-l", "-z", "--full-tree", commit)
    assert isinstance(raw, bytes)
    entries: list[GitEntry] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, path_bytes = record.split(b"\t", 1)
        parts = metadata.decode("ascii").split()
        if len(parts) != 4 or parts[1] != "blob":
            continue
        mode, _, object_id, size_text = parts
        path = path_bytes.decode("utf-8", errors="surrogateescape")
        entries.append(GitEntry(mode, object_id, int(size_text), path))
    return sorted(entries, key=lambda item: item.path)


def read_blob(repo: Path, object_id: str) -> bytes:
    raw = _git(repo, "cat-file", "blob", object_id)
    assert isinstance(raw, bytes)
    return raw


def language_for(path: str, binary: bool) -> str:
    if binary:
        return "binary"
    suffix = PurePosixPath(path).suffix.lower()
    name = PurePosixPath(path).name.lower()
    return {
        ".py": "python",
        ".ps1": "powershell",
        ".psm1": "powershell",
        ".json": "json",
        ".toml": "toml",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".txt": "text",
        ".ini": "ini",
        ".cfg": "config",
    }.get(suffix, "git-config" if name in {".gitignore", ".gitattributes"} else "text")


def role_for(path: str, language: str) -> str:
    normalized = path.lower()
    name = PurePosixPath(path).name.lower()
    if normalized.startswith("tests/") or name.startswith("test_"):
        return "test"
    if normalized.startswith("docs/") or language in {"markdown", "text"}:
        return "documentation"
    if name in {"pyproject.toml", "package.json"} or language in {
        "json",
        "toml",
        "yaml",
        "ini",
        "config",
    }:
        return "configuration"
    if normalized.startswith("tools/") or language == "powershell":
        return "tool"
    if normalized.startswith("src/") or language == "python":
        return "source"
    return "asset"


def decode_text(data: bytes) -> tuple[str | None, str, str]:
    if b"\0" in data[:8192]:
        return None, "binary", "binary"
    line_endings = "crlf" if b"\r\n" in data else "lf"
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig", line_endings
    try:
        return data.decode("utf-8"), "utf-8", line_endings
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace"), "utf-8-replace", line_endings


def classify_path(value: str, expression: str = "") -> str | None:
    stripped = value.strip()
    combined = f"{expression} {stripped}"
    if not stripped and not any(
        marker in expression for marker in ("__file__", ":tools/", ":tools\\")
    ):
        return None
    if URL.match(stripped):
        return "url"
    if WINDOWS_ABSOLUTE.match(stripped):
        return "absolute_host"
    if stripped.startswith("HEAD:") or re.match(r"^[0-9a-f]{7,40}:", stripped):
        return "git_object_path"
    if ":tools/" in combined or ":tools\\" in combined:
        return "git_object_path"
    if "$PSScriptRoot" in combined or "__file__" in combined:
        return "file_relative"
    if "Path.cwd" in combined or "os.getcwd" in combined or stripped == ".":
        return "cwd_relative"
    if stripped.startswith("../") or stripped.startswith("..\\"):
        return "hierarchy_relative"
    if stripped.startswith("./") or stripped.startswith(".\\"):
        return "cwd_relative"
    if stripped.startswith(("components/", "components\\")):
        return "repo_root_relative"
    if stripped.startswith(
        (
            "tools/",
            "tools\\",
            "tests/",
            "tests\\",
            "docs/",
            "docs\\",
            "src/",
            "src\\",
            "config/",
            "config\\",
            "worker_lab/",
            "localbench/",
        )
    ):
        return "component_root_relative"
    if "$env:" in combined or "os.environ" in combined or "os.getenv" in combined:
        return "configuration_derived"
    if "/" in stripped or "\\" in stripped:
        return "dynamic_or_relative"
    return None


def _record_path(
    records: list[dict[str, Any]],
    seen: set[tuple[int, int, str, str]],
    *,
    value: str,
    expression: str,
    line: int,
    column: int,
) -> None:
    path_type = classify_path(value, expression)
    if path_type is None:
        return
    key = (line, column, expression, path_type)
    if key in seen:
        return
    seen.add(key)
    records.append(
        {
            "line": line,
            "column": column,
            "expression": expression[:500],
            "literal": value[:500],
            "path_type": path_type,
        }
    )


class PythonStructureVisitor(ast.NodeVisitor):
    def __init__(self, source: str) -> None:
        self.source = source
        self.imports: list[dict[str, Any]] = []
        self.functions: list[dict[str, Any]] = []
        self.classes: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []
        self.git_object_lookups: list[dict[str, Any]] = []
        self.environment_variables: set[str] = set()
        self.path_references: list[dict[str, Any]] = []
        self._path_seen: set[tuple[int, int, str, str]] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append({"module": alias.name, "line": node.lineno})

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.imports.append(
            {
                "module": node.module or "",
                "names": [alias.name for alias in node.names],
                "line": node.lineno,
            }
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append({"name": node.name, "line": node.lineno})
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes.append({"name": node.name, "line": node.lineno})
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        function = ast.unparse(node.func) if hasattr(ast, "unparse") else "call"
        expression = ast.get_source_segment(self.source, node) or function
        if (
            function == "_git"
            and any(
                isinstance(argument, ast.Constant) and argument.value == "show"
                for argument in node.args
            )
            and (
                "worker_lab_adapter" in expression
                or "ADAPTER_RELATIVE_PATH" in expression
            )
        ):
            self.git_object_lookups.append(
                {"line": node.lineno, "expression": expression[:500]}
            )
        if "__file__" in expression:
            _record_path(
                self.path_references,
                self._path_seen,
                value="",
                expression=expression,
                line=node.lineno,
                column=node.col_offset,
            )
        if any(
            marker in function
            for marker in (
                "subprocess.",
                "os.system",
                "Path",
                "open",
                "read_text",
                "read_bytes",
                "write_text",
                "write_bytes",
                "resolve",
                "getenv",
            )
        ):
            self.calls.append({"function": function, "line": node.lineno})
        for argument in [*node.args, *(keyword.value for keyword in node.keywords)]:
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                _record_path(
                    self.path_references,
                    self._path_seen,
                    value=argument.value,
                    expression=expression,
                    line=getattr(argument, "lineno", node.lineno),
                    column=getattr(argument, "col_offset", node.col_offset),
                )
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, ast.Div):
            expression = ast.get_source_segment(self.source, node) or ast.unparse(node)
            _record_path(
                self.path_references,
                self._path_seen,
                value="",
                expression=expression,
                line=node.lineno,
                column=node.col_offset,
            )
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        expression = ast.get_source_segment(self.source, node) or ast.unparse(node)
        _record_path(
            self.path_references,
            self._path_seen,
            value="",
            expression=expression,
            line=node.lineno,
            column=node.col_offset,
        )
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            _record_path(
                self.path_references,
                self._path_seen,
                value=node.value,
                expression=node.value,
                line=getattr(node, "lineno", 1),
                column=getattr(node, "col_offset", 0),
            )


def generic_path_references(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[int, int, str, str]] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in QUOTED.finditer(line):
            _record_path(
                records,
                seen,
                value=match.group("value"),
                expression=match.group("value"),
                line=line_number,
                column=match.start("value"),
            )
        if "$PSScriptRoot" in line:
            _record_path(
                records,
                seen,
                value="$PSScriptRoot",
                expression=line.strip(),
                line=line_number,
                column=line.index("$PSScriptRoot"),
            )
        for match in re.finditer(r"(?:[A-Za-z]:[\\/]|\\\\)[^\s`'\"<>|]+", line):
            _record_path(
                records,
                seen,
                value=match.group(0),
                expression=match.group(0),
                line=line_number,
                column=match.start(),
            )
    return records


def analyze_text(path: str, language: str, text: str) -> dict[str, Any]:
    structures: dict[str, Any] = {
        "imports": [],
        "functions": [],
        "classes": [],
        "calls": [],
        "git_object_lookups": [],
        "environment_variables": sorted(
            set(PYTHON_ENV.findall(text)) | set(POWERSHELL_ENV.findall(text))
        ),
    }
    path_references = generic_path_references(text)
    parse_error: str | None = None
    if language == "python":
        try:
            tree = ast.parse(text, filename=path)
            visitor = PythonStructureVisitor(text)
            visitor.visit(tree)
            structures.update(
                {
                    "imports": visitor.imports,
                    "functions": visitor.functions,
                    "classes": visitor.classes,
                    "calls": visitor.calls,
                    "git_object_lookups": visitor.git_object_lookups,
                    "environment_variables": sorted(
                        set(structures["environment_variables"])
                        | visitor.environment_variables
                    ),
                }
            )
            existing = {
                (item["line"], item["column"], item["expression"], item["path_type"])
                for item in path_references
            }
            for item in visitor.path_references:
                key = (item["line"], item["column"], item["expression"], item["path_type"])
                if key not in existing:
                    path_references.append(item)
                    existing.add(key)
        except SyntaxError as exc:
            parse_error = f"{exc.msg} at line {exc.lineno}"
    elif language == "json":
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            parse_error = f"{exc.msg} at line {exc.lineno}"
    elif language == "toml":
        try:
            import tomllib

            tomllib.loads(text)
        except Exception as exc:  # parser evidence, not execution authority
            parse_error = str(exc)

    lowered = text.lower()
    signals = sorted(
        signal
        for signal, present in {
            "git_repo_root": "rev-parse" in lowered and "show-toplevel" in lowered,
            "git_path_output": ("--name-only" in lowered and "diff" in lowered)
            or "ls-files" in lowered,
            "component_root_join": bool(
                re.search(r"\bROOT\s*/|join-path\s+\$PSScriptRoot", text, re.IGNORECASE)
            ),
            "component_relative_test_selector": "startswith(\"tests/\")" in text
            or "startswith('tests/')" in text,
            "component_path_normalization": "_component_relative_paths" in text
            and ".relative_to(" in text
            and ".removeprefix(" in text,
            "adapter_root_object": "tools/worker_lab_adapter.py" in text
            and '"show"' in text,
            "adapter_standalone_identity": path == "tools/worker_lab_adapter.py"
            and "Path(__file__).resolve().parents[1]" in text
            and '"rev-parse", "HEAD"' in text
            and '"status", "--porcelain=v1"' in text,
            "framework_standalone_pin": "autonomous-worker-framework" in lowered
            and bool(re.search(r"[A-Za-z]:[\\/]", text)),
            "subprocess_boundary": "subprocess" in lowered or "start-process" in lowered,
        }.items()
        if present
    )
    return {
        "structures": structures,
        "path_references": sorted(
            path_references,
            key=lambda item: (
                item["line"],
                item["column"],
                item["path_type"],
                item["expression"],
            ),
        ),
        "signals": signals,
        "parse_error": parse_error,
    }


def inventory_component(component: dict[str, Any]) -> dict[str, Any]:
    repo = Path(component["source_repo"]).resolve()
    requested = component["source_commit"]
    commit = resolve_commit(repo, requested)
    if commit != requested:
        raise RuntimeError(
            f"{component['code']} commit mismatch: manifest={requested}, resolved={commit}"
        )
    tree = resolve_tree(repo, commit)
    entries = list_tree(repo, commit)
    cache: dict[str, tuple[bytes, str | None, str, str]] = {}
    files: list[dict[str, Any]] = []
    for entry in entries:
        if entry.object_id not in cache:
            blob = read_blob(repo, entry.object_id)
            text, encoding, line_endings = decode_text(blob)
            cache[entry.object_id] = (blob, text, encoding, line_endings)
        blob, text, encoding, line_endings = cache[entry.object_id]
        language = language_for(entry.path, text is None)
        destination_path = str(
            PurePosixPath(component["destination_prefix"]) / PurePosixPath(entry.path)
        )
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
        file_id = f"{component['code']}:{entry.path}"
        for index, reference in enumerate(analysis["path_references"], start=1):
            reference["reference_id"] = f"{file_id}#PATH-{index:04d}"
        files.append(
            {
                "file_id": file_id,
                "component": component["code"],
                "source_path": entry.path,
                "destination_path": destination_path,
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
    imported_verification: dict[str, Any] | None = None
    imported = component.get("imported")
    if imported:
        integration_repo = Path(imported["repo"]).resolve()
        integration_commit = resolve_commit(integration_repo, imported["commit"])
        imported_tree = resolve_tree(
            integration_repo, integration_commit, imported["prefix"]
        )
        imported_verification = {
            "repo": str(integration_repo),
            "commit": integration_commit,
            "prefix": imported["prefix"],
            "subtree": imported_tree,
            "matches_source_tree": imported_tree == tree,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "component": component["code"],
        "name": component["name"],
        "source_repo": str(repo),
        "source_commit": commit,
        "source_tree": tree,
        "destination_prefix": component["destination_prefix"],
        "file_count": len(files),
        "byte_count": sum(item["size"] for item in files),
        "language_counts": dict(sorted(language_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "path_type_counts": dict(sorted(path_counts.items())),
        "imported_verification": imported_verification,
        "files": files,
    }


def _finding_id(component: str, rule: str, file_id: str, line: int) -> str:
    digest = hashlib.sha1(f"{file_id}:{line}:{rule}".encode()).hexdigest()[:8].upper()
    return f"{component}-{rule}-{digest}"


def build_findings(inventories: Iterable[dict[str, Any]]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for inventory in inventories:
        component = inventory["component"]
        for file in inventory["files"]:
            signals = set(file["signals"])
            if (
                component == "AWF"
                and file["source_path"] == "tools/local_validate.py"
                and {
                    "git_path_output",
                    "component_root_join",
                    "component_relative_test_selector",
                }
                <= signals
                and "component_path_normalization" not in signals
            ):
                findings.append(
                    {
                        "finding_id": "AWF-PATH-008",
                        "status": "FAIL",
                        "severity": "high",
                        "repair_class": "MECHANICAL_REPAIR",
                        "component": component,
                        "file_id": file["file_id"],
                        "source_path": file["source_path"],
                        "destination_path": file["destination_path"],
                        "line": next(
                            (
                                function["line"]
                                for function in file["structures"].get("functions", [])
                                if function["name"] == "discover_changed_paths"
                            ),
                            1,
                        ),
                        "summary": "Quick validation consumes monorepo-root Git paths as component-relative paths and can select zero stages.",
                        "evidence": "git path output + ROOT join + tests/ prefix selector",
                    }
                )
            if file["role"] in {"source", "tool", "configuration", "test"}:
                if "adapter_standalone_identity" in signals:
                    findings.append(
                        {
                            "finding_id": "AWF-IDENTITY-STANDALONE",
                            "status": "KNOWN_GAP",
                            "severity": "high",
                            "repair_class": "SEMANTIC_REVIEW",
                            "component": component,
                            "file_id": file["file_id"],
                            "source_path": file["source_path"],
                            "destination_path": file["destination_path"],
                            "line": 344,
                            "summary": "Adapter runtime identity treats its component directory as the whole Git repository and checks whole-repository HEAD/status.",
                            "evidence": "Path(__file__).parents[1] + git rev-parse HEAD + git status",
                        }
                    )
                if "adapter_root_object" in signals:
                    is_runtime_adapter = (
                        component == "AWF"
                        and file["source_path"] == "tools/worker_lab_adapter.py"
                    ) or (
                        component == "WLAB"
                        and file["source_path"] == "worker_lab/framework_client.py"
                    )
                    if is_runtime_adapter:
                        object_reference = next(
                            (
                                item
                                for item in file["path_references"]
                                if item["path_type"] == "git_object_path"
                            ),
                            None,
                        )
                        lookup = next(
                            iter(file["structures"].get("git_object_lookups", [])),
                            None,
                        )
                        findings.append(
                            {
                                "finding_id": _finding_id(component, "GIT-OBJECT", file["file_id"], 1),
                                "status": "KNOWN_GAP",
                                "severity": "high",
                                "repair_class": "SEMANTIC_REVIEW",
                                "component": component,
                                "file_id": file["file_id"],
                                "source_path": file["source_path"],
                                "destination_path": file["destination_path"],
                                "line": (
                                    object_reference["line"]
                                    if object_reference
                                    else lookup["line"] if lookup else 1
                                ),
                                "summary": "Git object lookup assumes the adapter is at repository-root tools/.",
                                "evidence": "HEAD:tools/worker_lab_adapter.py",
                            }
                        )
                if "framework_standalone_pin" in signals:
                    reference = next(
                        (
                            item
                            for item in file["path_references"]
                            if item["path_type"] == "absolute_host"
                            and "autonomous-worker-framework"
                            in (item["literal"] + item["expression"]).lower()
                        ),
                        None,
                    )
                    if reference:
                        findings.append(
                            {
                                "finding_id": _finding_id(
                                    component,
                                    "FRAMEWORK-PIN",
                                    file["file_id"],
                                    reference["line"],
                                ),
                                "status": "KNOWN_GAP",
                                "severity": "high",
                                "repair_class": "SEMANTIC_REVIEW",
                                "component": component,
                                "file_id": file["file_id"],
                                "source_path": file["source_path"],
                                "destination_path": file["destination_path"],
                                "line": reference["line"],
                                "summary": "Active code/configuration pins the standalone framework repository.",
                                "evidence": reference["literal"],
                            }
                        )
                if file["role"] == "configuration":
                    for reference in file["path_references"]:
                        if reference["path_type"] != "absolute_host":
                            continue
                        findings.append(
                            {
                                "finding_id": _finding_id(
                                    component,
                                    "EXTERNAL-PATH",
                                    file["file_id"],
                                    reference["line"],
                                ),
                                "status": "KNOWN_GAP",
                                "severity": "medium",
                                "repair_class": "EXTERNAL_RUNTIME",
                                "component": component,
                                "file_id": file["file_id"],
                                "source_path": file["source_path"],
                                "destination_path": file["destination_path"],
                                "line": reference["line"],
                                "summary": "Tracked configuration contains a machine-local absolute path.",
                                "evidence": reference["literal"],
                            }
                        )
            if file["parse_error"]:
                findings.append(
                    {
                        "finding_id": _finding_id(component, "PARSE", file["file_id"], 1),
                        "status": "UNKNOWN",
                        "severity": "medium",
                        "repair_class": "SEMANTIC_REVIEW",
                        "component": component,
                        "file_id": file["file_id"],
                        "source_path": file["source_path"],
                        "destination_path": file["destination_path"],
                        "line": 1,
                        "summary": "The language parser could not interpret this tracked file.",
                        "evidence": file["parse_error"],
                    }
                )
    ordered = sorted(
        {item["finding_id"]: item for item in findings}.values(),
        key=lambda item: (item["component"], item["finding_id"]),
    )
    return {
        "schema_version": FINDINGS_VERSION,
        "counts": dict(sorted(Counter(item["status"] for item in ordered).items())),
        "findings": ordered,
    }


def build_connections(inventories: Iterable[dict[str, Any]]) -> dict[str, Any]:
    connections: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, int]] = set()
    package_targets = {"worker_lab": "WLAB", "localbench": "LMB"}
    for inventory in inventories:
        source_component = inventory["component"]
        for file in inventory["files"]:
            for imported in file["structures"].get("imports", []):
                root = imported.get("module", "").split(".", 1)[0]
                target = package_targets.get(root)
                if target and target != source_component:
                    key = (source_component, target, file["file_id"], imported["line"])
                    if key not in seen:
                        seen.add(key)
                        connections.append(
                            {
                                "connection_id": f"{source_component}-TO-{target}-{len(connections)+1:04d}",
                                "source_component": source_component,
                                "target_component": target,
                                "connection_type": "python_import",
                                "file_id": file["file_id"],
                                "line": imported["line"],
                                "evidence": imported.get("module", ""),
                            }
                        )
            for reference in file["path_references"]:
                combined = (reference["literal"] + " " + reference["expression"]).lower()
                target = None
                if "autonomous-worker-framework" in combined or "worker_lab_adapter.py" in combined:
                    target = "AWF"
                elif "worker-lab" in combined or "worker_lab" in combined:
                    target = "WLAB"
                elif "local-model-bench" in combined or "localbench" in combined:
                    target = "LMB"
                if target and target != source_component:
                    key = (source_component, target, file["file_id"], reference["line"])
                    if key not in seen:
                        seen.add(key)
                        connections.append(
                            {
                                "connection_id": f"{source_component}-TO-{target}-{len(connections)+1:04d}",
                                "source_component": source_component,
                                "target_component": target,
                                "connection_type": "path_or_process_reference",
                                "file_id": file["file_id"],
                                "line": reference["line"],
                                "reference_id": reference["reference_id"],
                                "evidence": reference["literal"],
                            }
                        )
    return {
        "schema_version": CONNECTIONS_VERSION,
        "connection_count": len(connections),
        "connections": connections,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(rendered, encoding="utf-8", newline="\n")


def generate(manifest_path: Path, output_dir: Path) -> int:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "acl-source-snapshots:v1":
        raise RuntimeError("Unsupported snapshot manifest schema")
    inventories: list[dict[str, Any]] = []
    for component in manifest["components"]:
        inventory = inventory_component(component)
        inventories.append(inventory)
        write_json(output_dir / f"{component['code'].lower()}.json", inventory)
    findings = build_findings(inventories)
    connections = build_connections(inventories)
    summary = {
        "schema_version": "acl-structure-summary:v1",
        "components": [
            {
                "component": item["component"],
                "source_commit": item["source_commit"],
                "source_tree": item["source_tree"],
                "file_count": item["file_count"],
                "byte_count": item["byte_count"],
                "path_type_counts": item["path_type_counts"],
                "imported_verification": item["imported_verification"],
            }
            for item in inventories
        ],
        "finding_counts": findings["counts"],
        "connection_count": connections["connection_count"],
        "excluded_repositories": manifest.get("excluded_repositories", []),
    }
    write_json(output_dir / "findings.json", findings)
    write_json(output_dir / "connections.json", connections)
    write_json(output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate deterministic structural inventories from exact Git trees."
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("migration/inventory/snapshots.json")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("migration/inventory")
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return generate(args.manifest.resolve(), args.output_dir.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
