import json
from pathlib import Path

from worker_lab.cli import main
from tests.test_models import curriculum_mapping, exercise_mapping


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_validate_definition_and_invalid_failure(tmp_path: Path, capsys) -> None:
    path = tmp_path / "curriculum.json"
    write_json(path, curriculum_mapping())
    assert main(["validate-definition", str(path)]) == 0
    assert capsys.readouterr().out.startswith("VALID sha256:")
    path.write_text("{}", encoding="utf-8")
    assert main(["validate-definition", str(path)]) == 2
    assert "ERROR RECORD_SCHEMA_INVALID" in capsys.readouterr().err


def test_definition_inspection_and_attempt_lifecycle(tmp_path: Path, capsys) -> None:
    write_json(tmp_path / "curricula" / "curricula" / "record-ledger.json", curriculum_mapping())
    write_json(tmp_path / "curricula" / "exercises" / "record-model" / "v1.json", exercise_mapping())
    assert main(["--root", str(tmp_path), "list-curricula"]) == 0
    assert "record-ledger\tactive" in capsys.readouterr().out
    assert main(["--root", str(tmp_path), "create-attempt", "--exercise", "record-model", "--version", "1"]) == 0
    created = json.loads(capsys.readouterr().out)
    attempt_id = created["attempt_id"]
    assert created["state"] == "DRAFT"
    assert main(["--root", str(tmp_path), "show-attempt", attempt_id]) == 0
    assert json.loads(capsys.readouterr().out)["attempt_id"] == attempt_id
