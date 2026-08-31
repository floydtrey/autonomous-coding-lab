from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]


class ValidationSetupError(RuntimeError):
    """Raised when local validation cannot determine a safe execution plan."""


@dataclass(frozen=True)
class Stage:
    name: str
    command: tuple[str, ...]
    failure_code: str


@dataclass(frozen=True)
class StageResult:
    stage: Stage
    return_code: int
    elapsed_seconds: float

    @property
    def passed(self) -> bool:
        return self.return_code == 0


def _run_capture(command: Sequence[str]) -> str:
    process = subprocess.run(
        list(command),
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode != 0:
        detail = (process.stderr or process.stdout or "command failed").strip()
        raise ValidationSetupError(f"{' '.join(command)} failed: {detail}")
    return process.stdout


def _normalize_paths(lines: Iterable[str]) -> set[str]:
    paths: set[str] = set()
    for raw in lines:
        value = raw.strip().replace("\\", "/")
        if value:
            paths.add(value)
    return paths


def _git_lines(*args: str) -> set[str]:
    return _normalize_paths(_run_capture(("git", *args)).splitlines())


def resolve_base(explicit_base: str | None = None) -> str:
    candidates = [explicit_base] if explicit_base else ["main"]
    last_error: Exception | None = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            value = _run_capture(("git", "merge-base", "HEAD", candidate)).strip()
            if value:
                return value
        except ValidationSetupError as exc:
            last_error = exc
    if last_error:
        raise ValidationSetupError(
            "Could not resolve a validation base. Pass --base explicitly or ensure main exists."
        ) from last_error
    raise ValidationSetupError("Could not resolve a validation base.")


def discover_changed_paths(base: str) -> list[str]:
    changed: set[str] = set()
    changed |= _git_lines("diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD")
    changed |= _git_lines("diff", "--name-only", "--diff-filter=ACMR")
    changed |= _git_lines("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    changed |= _git_lines("ls-files", "--others", "--exclude-standard")
    return sorted(changed)


def _existing_files(paths: Iterable[str], suffix: str | None = None) -> list[str]:
    selected: list[str] = []
    for value in paths:
        if suffix is not None and not value.endswith(suffix):
            continue
        if (ROOT / value).is_file():
            selected.append(value)
    return selected


def quick_stages(changed_paths: Sequence[str]) -> list[Stage]:
    stages: list[Stage] = []
    python_files = _existing_files(changed_paths, ".py")
    changed_tests = [
        path
        for path in python_files
        if path.startswith("tests/") and Path(path).name.startswith("test_")
    ]

    if python_files:
        stages.append(
            Stage(
                name="Compile changed Python",
                command=(sys.executable, "-m", "py_compile", *python_files),
                failure_code="LOCAL_COMPILE_FAILED",
            )
        )
    if changed_tests:
        stages.append(
            Stage(
                name="Run changed Python tests",
                command=(sys.executable, "-m", "pytest", "-q", *changed_tests),
                failure_code="LOCAL_FOCUSED_TESTS_FAILED",
            )
        )
    return stages


def full_stages() -> list[Stage]:
    return [
        Stage(
            name="Compile framework Python",
            command=(sys.executable, "-m", "compileall", "-q", "tools", "tests"),
            failure_code="LOCAL_COMPILE_FAILED",
        ),
        Stage(
            name="Run full framework test suite",
            command=(sys.executable, "-m", "pytest", "-q"),
            failure_code="LOCAL_FULL_TESTS_FAILED",
        ),
    ]


def validate_stage_requirements(stages: Sequence[Stage]) -> None:
    for executable in {stage.command[0] for stage in stages}:
        if Path(executable).is_absolute():
            if not Path(executable).is_file():
                raise ValidationSetupError(f"Required executable does not exist: {executable}")
        elif shutil.which(executable) is None:
            raise ValidationSetupError(f"Required executable is not on PATH: {executable}")


def run_stages(stages: Sequence[Stage]) -> list[StageResult]:
    results: list[StageResult] = []
    for index, stage in enumerate(stages, start=1):
        print(f"[{index}/{len(stages)}] {stage.name}")
        print("  $ " + " ".join(stage.command))
        started = time.monotonic()
        process = subprocess.run(list(stage.command), cwd=ROOT, check=False)
        elapsed = time.monotonic() - started
        result = StageResult(stage, process.returncode, elapsed)
        results.append(result)
        if result.passed:
            print(f"  PASS ({elapsed:.2f}s)")
        else:
            print(
                f"  FAIL {stage.failure_code} "
                f"(exit {process.returncode}, {elapsed:.2f}s)"
            )
            break
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Autonomous Worker Framework validation locally."
    )
    parser.add_argument(
        "mode",
        choices=("quick", "full"),
        nargs="?",
        default="quick",
    )
    parser.add_argument("--base")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.mode == "full":
            stages = full_stages()
        else:
            base = resolve_base(args.base)
            changed_paths = discover_changed_paths(base)
            print(f"Quick validation base: {base}")
            if changed_paths:
                print("Changed paths:")
                for path in changed_paths:
                    print(f"  - {path}")
            else:
                print("No changed paths detected.")
            stages = quick_stages(changed_paths)

        if not stages:
            print("No applicable local validation stages were required.")
            return 0

        validate_stage_requirements(stages)
        results = run_stages(stages)
    except ValidationSetupError as exc:
        print(f"LOCAL_VALIDATION_SETUP_FAILED: {exc}", file=sys.stderr)
        return 2

    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
