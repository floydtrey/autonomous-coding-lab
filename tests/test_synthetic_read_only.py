from pathlib import Path
from tempfile import TemporaryDirectory

from worker_lab.attempt_store import AttemptStore
from worker_lab.synthetic_read_only import (
    SYNTHETIC_PROFILE_ID,
    SYNTHETIC_TEST_ID,
    _create_attempt,
    _invocation,
    _make_template,
    _run_sealed_test,
    _write_authority,
)
from worker_lab.test_catalog import ChangeFacts, TestRunner as CatalogRunner
from worker_lab.workspace import prepare_workspace


def test_synthetic_authority_seals_one_read_only_invocation() -> None:
    # The protected workspace primitive correctly rejects any child of the
    # Worker Lab repository, so this fixture deliberately uses the OS temp root.
    with TemporaryDirectory(prefix="worker-lab-synthetic-") as directory:
        root = Path(directory)
        template = root / "template"
        lab = root / "lab"
        workspace_root = root / "workspaces"
        workspace_root.mkdir()
        _make_template(template)
        records = _write_authority(lab, template)
        attempt = _create_attempt(lab, records)
        receipt = prepare_workspace(
            lab, attempt.attempt_id, template, workspace_root, occurred_at=attempt.updated_at
        )
        ready = AttemptStore(lab / "state").read(attempt.attempt_id)
        invocation, prompt = _invocation(
            lab, ready, records, receipt, workspace_root / attempt.attempt_id
        )
        assert invocation.sandbox_mode == "read-only"
        assert invocation.writable_paths == ()
        assert invocation.test_ids == (SYNTHETIC_TEST_ID,)
        assert prompt
        definition = records[-1].tests[0]
        assert definition.runner is CatalogRunner.COMMAND
        assert _run_sealed_test(definition, workspace_root / attempt.attempt_id) == 0
        assert records[-1].select(ChangeFacts(()), profile_ids=(SYNTHETIC_PROFILE_ID,)).test_ids == (
            SYNTHETIC_TEST_ID,
        )
