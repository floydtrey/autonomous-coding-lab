"""Public M08 handoff with real M06 evidence and an explicitly seeded job fixture."""
import json
import os
from pathlib import Path

import pytest

from tests.test_accepted_snapshot import ready, promote, tmp_path
from tests.test_job_input import task_inputs
from tests.test_job_plan import FIXTURE
from worker_lab.application_service import WorkerLabApplicationService
from worker_lab.attempt_store import AttemptStore
from worker_lab.canonical import canonical_digest
from worker_lab.invocation_store_v3 import InvocationStoreV3
from worker_lab.job_admission import JobAuthorityProfile, load_task_authorities
from worker_lab.job_runner import JobRecord, _deadline
from worker_lab.models import AttemptState
from worker_lab.storage import AtomicRecordStore

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='protected native-check evidence fixture')


def test_public_job_handoff_preserves_accepted_bytes_and_original_authority(tmp_path, monkeypatch):
    _, lab, outcome, accepted, artifacts = ready(tmp_path, monkeypatch)
    snapshot = promote(lab, outcome, accepted, artifacts)
    profile, plan = task_inputs(lab, outcome)
    a_profile = JobAuthorityProfile.from_mapping(json.loads(
        (FIXTURE.parent / 'record-model-authority.json').read_text(encoding='utf-8')))
    AtomicRecordStore(lab / 'job-authorities').write('record-model-authority/v1.json', a_profile)
    profile_path = lab / 'job-authorities/record-docs-authority/v1.json'
    original_profile_bytes = profile_path.read_bytes()
    controller = snapshot.to_dict()['controller_identity']
    stamp = accepted.to_dict()['recorded_at']
    service = WorkerLabApplicationService(lab, clock=lambda: stamp)
    job = service.create_job('JOB-HANDOFF', plan, approved_by=controller, approved_plan_digest=plan.digest())

    # This is a prepared M07 aggregate fixture, not a job execution. Actual M06
    # fixture evidence supplies A's attempt, invocation and immutable acceptance;
    # JOBTASK execution remains disabled until the M09 controller is assembled.
    records = AtomicRecordStore(lab / 'state')
    result = outcome.to_dict()
    invocation = InvocationStoreV3(records.root).read(result['invocation_id'])
    value = job.to_dict()
    value['tasks']['A'].update(state='accepted', acceptance=dict(
        path=f"task-acceptances/{result['attempt_id']}.json", digest=accepted.digest(),
        candidate_digest=accepted.to_dict()['candidate']['content_digest']), attempts=[dict(
            reservation_id=canonical_digest({'fixture': 'accepted-M06-A'}), reserved_at=stamp,
            deadline_at=_deadline(stamp, plan.task('A').budget.max_wall_seconds),
            attempt_id=result['attempt_id'], invocation_id=invocation.invocation_id,
            invocation_digest=invocation.identity_digest(), run_reference=None, run_digest=None)])
    records.write('jobs/JOB-HANDOFF.json', JobRecord.from_mapping(value))

    attached = service.attach_job_artifact('JOB-HANDOFF', task_id='A', controller_identity=controller,
        acceptance_digest=accepted.digest(), artifact_reference=snapshot.to_dict()['reference'],
        artifact_digest=snapshot.digest())
    assert attached.to_dict()['tasks']['A']['artifact'] == {
        'path': snapshot.to_dict()['reference'], 'digest': snapshot.digest()}
    reserved = service.reserve_next_job_task('JOB-HANDOFF', controller_identity=controller,
        expected_job_digest=attached.digest())
    assert reserved.to_dict()['active']['task_id'] == 'B'
    binding = service.prepare_job_input('JOB-HANDOFF', controller_identity=controller,
        reservation_id=reserved.to_dict()['active']['reservation_id'])
    assert binding.to_dict()['snapshot_digest'] == snapshot.digest()
    repository = Path(snapshot.to_dict()['repository'])
    admitted = service.admit_job_task(plan, 'B', repository, approved_by=controller,
        approved_plan_digest=plan.digest(), input_binding=binding)
    workspaces = tmp_path / 'downstream'
    workspaces.mkdir()
    service.prepare_workspace(admitted.identity, repository, workspaces)

    attempt = AttemptStore(records.root).read(admitted.identity)
    definition, _, _, context, _ = load_task_authorities(lab, attempt)
    assert attempt.state is AttemptState.READY
    assert (workspaces / admitted.identity / 'record_ledger/models.py').read_bytes() == b'VALUE = 2\n'
    assert definition.writable_paths == ('README.md',)
    assert 'record_ledger/models.py' not in definition.writable_paths
    assert context.starting_commit == snapshot.to_dict()['snapshot_commit']
    assert definition.profile == profile
    assert definition.plan == plan
    assert profile_path.read_bytes() == original_profile_bytes
    assert service.read_job('JOB-HANDOFF').to_dict()['active'] == reserved.to_dict()['active']

