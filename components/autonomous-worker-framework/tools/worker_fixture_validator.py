from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = "autonomy_smoke"
EXPECTED_CONTENT = {
    "A": b"STATE=A\n",
    "B": b"STATE=B\n",
}


class FixtureSetupError(RuntimeError):
    """Raised when the requested fixture path/state is not safe or supported."""


class FixtureValidationError(RuntimeError):
    """Raised when fixture state does not match the expected deterministic state."""


@dataclass(frozen=True)
class FixtureResult:
    path: str
    expected_state: str
    observed: str


def resolve_fixture_path(value: str, *, root: Path | None = None) -> tuple[str, Path]:
    raw = str(value or "").strip().replace("\\", "/")
    if not raw:
        raise FixtureSetupError("fixture path is required")
    candidate = Path(raw)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise FixtureSetupError("fixture path must be repository-relative and may not traverse upward")
    normalized = candidate.as_posix()
    if normalized == FIXTURE_ROOT or not normalized.startswith(f"{FIXTURE_ROOT}/"):
        raise FixtureSetupError(f"fixture path must be inside {FIXTURE_ROOT}/")
    repo_root = (root or ROOT).resolve()
    resolved = (repo_root / candidate).resolve()
    fixture_root = (repo_root / FIXTURE_ROOT).resolve()
    if resolved == fixture_root or fixture_root not in resolved.parents:
        raise FixtureSetupError(f"fixture path must resolve inside {FIXTURE_ROOT}/")
    return normalized, resolved


def _describe_bytes(data: bytes) -> str:
    if data in EXPECTED_CONTENT.values():
        for state, expected in EXPECTED_CONTENT.items():
            if data == expected:
                return f"STATE={state} with required LF newline"
    return repr(data)


def validate_fixture(
    path: str,
    expected_state: str,
    *,
    root: Path | None = None,
) -> FixtureResult:
    state = str(expected_state or "").strip().upper()
    if state not in {"A", "B", "ABSENT"}:
        raise FixtureSetupError("expected state must be A, B, or ABSENT")

    normalized, resolved = resolve_fixture_path(path, root=root)

    if state == "ABSENT":
        if resolved.exists():
            observed = "directory" if resolved.is_dir() else _describe_bytes(resolved.read_bytes())
            raise FixtureValidationError(
                f"expected {normalized} to be absent; observed {observed}"
            )
        return FixtureResult(normalized, state, "absent")

    if not resolved.exists():
        raise FixtureValidationError(f"expected {normalized} to be STATE={state}; file is absent")
    if not resolved.is_file():
        raise FixtureValidationError(f"expected {normalized} to be a file; observed non-file path")

    observed = resolved.read_bytes()
    expected = EXPECTED_CONTENT[state]
    if observed != expected:
        raise FixtureValidationError(
            f"expected {normalized} bytes {expected!r}; observed {observed!r}"
        )

    return FixtureResult(normalized, state, _describe_bytes(observed))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a deterministic worker commissioning fixture without mutating it. "
            "Supported exact states are STATE=A\\n, STATE=B\\n, or ABSENT."
        )
    )
    parser.add_argument("path", help=f"repository-relative path inside {FIXTURE_ROOT}/")
    parser.add_argument("expected", choices=("A", "B", "ABSENT"), help="expected exact fixture state")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = validate_fixture(args.path, args.expected)
    except FixtureSetupError as exc:
        print(f"FIXTURE_SETUP_FAILED: {exc}", file=sys.stderr)
        return 2
    except FixtureValidationError as exc:
        print(f"FIXTURE_STATE_MISMATCH: {exc}", file=sys.stderr)
        return 1

    print("Fixture validation PASS")
    print(f"  path: {result.path}")
    print(f"  expected_state: {result.expected_state}")
    print(f"  observed: {result.observed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
