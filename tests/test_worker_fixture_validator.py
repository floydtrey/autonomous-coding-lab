from pathlib import Path

import pytest

from tools import worker_fixture_validator as validator


def _fixture(tmp_path: Path, content: bytes | None) -> Path:
    root = tmp_path / "autonomy_smoke"
    root.mkdir()
    path = root / "fixture_state.txt"
    if content is not None:
        path.write_bytes(content)
    return path


def test_accepts_exact_state_a(tmp_path, monkeypatch):
    _fixture(tmp_path, b"STATE=A\n")
    monkeypatch.setattr(validator, "ROOT", tmp_path)

    result = validator.validate_fixture("autonomy_smoke/fixture_state.txt", "A")

    assert result.expected_state == "A"
    assert result.observed == "STATE=A with required LF newline"


def test_accepts_exact_state_b(tmp_path, monkeypatch):
    _fixture(tmp_path, b"STATE=B\n")
    monkeypatch.setattr(validator, "ROOT", tmp_path)

    result = validator.validate_fixture("autonomy_smoke/fixture_state.txt", "b")

    assert result.expected_state == "B"
    assert result.observed == "STATE=B with required LF newline"


def test_accepts_absent_state(tmp_path, monkeypatch):
    _fixture(tmp_path, None)
    monkeypatch.setattr(validator, "ROOT", tmp_path)

    result = validator.validate_fixture("autonomy_smoke/fixture_state.txt", "ABSENT")

    assert result.observed == "absent"


def test_rejects_missing_file_when_state_expected(tmp_path, monkeypatch):
    _fixture(tmp_path, None)
    monkeypatch.setattr(validator, "ROOT", tmp_path)

    with pytest.raises(validator.FixtureValidationError, match="file is absent"):
        validator.validate_fixture("autonomy_smoke/fixture_state.txt", "A")


def test_rejects_wrong_state(tmp_path, monkeypatch):
    _fixture(tmp_path, b"STATE=A\n")
    monkeypatch.setattr(validator, "ROOT", tmp_path)

    with pytest.raises(validator.FixtureValidationError, match="expected .*STATE=B"):
        validator.validate_fixture("autonomy_smoke/fixture_state.txt", "B")


def test_rejects_missing_newline(tmp_path, monkeypatch):
    _fixture(tmp_path, b"STATE=A")
    monkeypatch.setattr(validator, "ROOT", tmp_path)

    with pytest.raises(validator.FixtureValidationError, match="observed b'STATE=A'"):
        validator.validate_fixture("autonomy_smoke/fixture_state.txt", "A")


def test_rejects_extra_content(tmp_path, monkeypatch):
    _fixture(tmp_path, b"STATE=A\nEXTRA\n")
    monkeypatch.setattr(validator, "ROOT", tmp_path)

    with pytest.raises(validator.FixtureValidationError, match="EXTRA"):
        validator.validate_fixture("autonomy_smoke/fixture_state.txt", "A")


def test_rejects_path_outside_fixture_root(tmp_path, monkeypatch):
    monkeypatch.setattr(validator, "ROOT", tmp_path)

    with pytest.raises(validator.FixtureSetupError, match="inside autonomy_smoke"):
        validator.validate_fixture("app/groups.py", "A")


def test_rejects_upward_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(validator, "ROOT", tmp_path)

    with pytest.raises(validator.FixtureSetupError, match="may not traverse upward"):
        validator.validate_fixture("autonomy_smoke/../app/groups.py", "A")


def test_rejects_unknown_state(tmp_path, monkeypatch):
    monkeypatch.setattr(validator, "ROOT", tmp_path)

    with pytest.raises(validator.FixtureSetupError, match="A, B, or ABSENT"):
        validator.validate_fixture("autonomy_smoke/fixture_state.txt", "C")
