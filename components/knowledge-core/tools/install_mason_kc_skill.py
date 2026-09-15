from __future__ import annotations

import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import shutil
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


_SKILL_LABEL = "knowledge-core"
_SKILL_DISPLAY_NAME = "Knowledge Core"
_PROJECT_BRIDGE_RELATIVE = Path("knowledge-core-tools") / "mason_kc_bridge.py"


def _require_loopback_url(value: str, *, name: str) -> str:
    normalized = value.strip().rstrip("/")
    parsed = urlsplit(normalized)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit(f"{name} must be a loopback http URL for Task 5 V1")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise SystemExit(f"{name} must not include a path/query/fragment")
    return normalized


def _upsert_env(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(values)
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            if key in remaining:
                output.append(f"{key}={remaining.pop(key)}")
                continue
        output.append(line)
    if output and output[-1] != "":
        output.append("")
    output.extend(f"{key}={value}" for key, value in remaining.items())
    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def _request_json(method: str, url: str, payload: dict | None = None):
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Cowork returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise SystemExit(f"Cowork is unreachable: {exc.reason}") from exc
    return json.loads(raw) if raw else {}


def _normalized_path(value: str | Path) -> str:
    path = Path(value).expanduser()
    try:
        path = path.resolve()
    except OSError:
        path = path.absolute()
    return os.path.normcase(os.path.normpath(str(path)))


def _resolve_cowork_project_name(cowork_url: str, project_dir: Path) -> str:
    projects = _request_json("GET", f"{cowork_url}/api/v1/projects/")
    if not isinstance(projects, list):
        raise SystemExit("Cowork returned an invalid project list")

    expected = _normalized_path(project_dir)
    for project in projects:
        if not isinstance(project, dict) or not project.get("path"):
            continue
        if _normalized_path(str(project["path"])) != expected:
            continue
        name = str(project.get("name") or "").strip()
        if not name:
            raise SystemExit("Cowork project matched the folder but has no project name")
        return name

    raise SystemExit(
        "Cowork has not registered the requested project folder. Open/adopt the "
        f"project in Cowork first: {project_dir}"
    )


def _install_project_bridge(project_dir: Path, source_bridge: Path) -> Path:
    target = project_dir / _PROJECT_BRIDGE_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_bridge, target)
    return target


def _register_skill(cowork_url: str, instructions: str, project_name: str) -> dict:
    collection_url = f"{cowork_url}/api/v1/skills/"
    skills = _request_json("GET", collection_url)
    if isinstance(skills, dict):
        items = skills.get("skills") or skills.get("items") or skills.get("data") or []
    else:
        items = skills

    existing = None
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("id") == _SKILL_LABEL or item.get("label") == _SKILL_LABEL:
                existing = item
                break

    project_names: set[str] = {project_name}
    if existing and isinstance(existing.get("projects"), list):
        project_names.update(
            str(value).strip()
            for value in existing["projects"]
            if str(value).strip()
        )

    payload = {
        "label": _SKILL_LABEL,
        "name": _SKILL_DISPLAY_NAME,
        "description": "Retrieve and store governed durable project knowledge through local Knowledge Core.",
        "instructions": instructions,
        "enabled": True,
        "projects": sorted(project_names),
    }
    if existing and existing.get("id"):
        return _request_json(
            "PUT",
            f"{cowork_url}/api/v1/skills/{existing['id']}",
            payload,
        )
    return _request_json("POST", collection_url, payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install the bounded Knowledge Core skill for local MindsHub Cowork/Anton."
    )
    parser.add_argument("--project-dir", required=True)
    parser.add_argument(
        "--cowork-url",
        required=True,
        help=(
            "Loopback URL of the running Cowork sidecar. Packaged Cowork uses a "
            "per-user port, so Task 5 deliberately does not assume 26866."
        ),
    )
    parser.add_argument("--knowledge-core-url", default="http://127.0.0.1:8765")
    args = parser.parse_args(argv)

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        raise SystemExit(f"project directory does not exist: {project_dir}")
    cowork_url = _require_loopback_url(args.cowork_url, name="Cowork URL")
    kc_url = _require_loopback_url(args.knowledge_core_url, name="Knowledge Core URL")
    project_name = _resolve_cowork_project_name(cowork_url, project_dir)

    key = os.environ.get("KNOWLEDGE_CORE_BOOTSTRAP_KEY", "")
    if not key:
        key = getpass("Knowledge Core bootstrap key: ")
    if not key:
        raise SystemExit("Knowledge Core bootstrap key must not be empty")

    env_path = project_dir / ".anton" / ".env"
    _upsert_env(
        env_path,
        {
            "KNOWLEDGE_CORE_BASE_URL": kc_url,
            "KNOWLEDGE_CORE_BOOTSTRAP_KEY": key,
        },
    )

    tool_dir = Path(__file__).resolve().parent
    source_bridge = (tool_dir / "mason_kc_bridge.py").resolve()
    bridge_path = _install_project_bridge(project_dir, source_bridge)

    template_path = (
        tool_dir.parent / "integrations" / "mindshub" / "KNOWLEDGE_CORE_SKILL.md"
    ).resolve()
    relative_bridge = _PROJECT_BRIDGE_RELATIVE.as_posix()
    instructions = template_path.read_text(encoding="utf-8").replace(
        "{{BRIDGE_PATH}}", relative_bridge
    )
    skill = _register_skill(cowork_url, instructions, project_name)

    print(
        json.dumps(
            {
                "status": "configured",
                "project_dir": str(project_dir),
                "cowork_project_name": project_name,
                "workspace_env": str(env_path),
                "knowledge_core_url": kc_url,
                "cowork_url": cowork_url,
                "bridge_path": str(bridge_path),
                "bridge_relative_path": relative_bridge,
                "skill": skill,
                "restart_required": True,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
