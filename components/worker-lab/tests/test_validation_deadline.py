"""M09A deadline races: real record stores; simulated clock/owned processes.

No provider request or real child is launched. Windows process-lifetime proofs
remain in test_pi_supervision.py and test_protected_validation.py.
"""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from worker_lab import protected_validation as validation
from worker_lab.storage import AtomicRecordStore

EPOCH_MS = 1_790_000_000_000
DIGEST = 'sha256:' + 'a' * 64


class Clock:
    def __init__(self):
        self.elapsed_ms = 0
        self.wall_offset_ms = 0

    def time_ns(self):
        return (EPOCH_MS + self.elapsed_ms + self.wall_offset_ms) * 1_000_000

    def monotonic(self):
        return self.elapsed_ms / 1000

    def sleep(self, seconds):
        self.elapsed_ms += round(seconds * 1000)

    def timestamp(self):
        return datetime.fromtimestamp(self.time_ns() / 1_000_000_000,
            timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


class Process:
    identity = 'windows-process:v1:200:1234'

    def __init__(self, timer, *, poll_ms=0, running=False, children=False,
                 stuck_cleanup=False, backward_wall=False):
        self.timer = timer
        self.poll_ms = poll_ms
        self.running = running
        self.children = children
        self.stuck_cleanup = stuck_cleanup
        self.backward_wall = backward_wall
        self.resumed = self.killed = self.closed = False
        self.polled = False

    def resume(self):
        self.resumed = True

    def poll(self):
        if self.killed:
            return -1
        if not self.polled:
            self.polled = True
            self.timer.elapsed_ms += self.poll_ms
            if self.backward_wall:
                self.timer.wall_offset_ms -= 5000
        return None if self.running else 0

    def active_count(self):
        if self.killed:
            return 1 if self.stuck_cleanup else 0
        return 1 if self.children or self.running else 0

    def terminate(self):
        self.killed = True

    def close(self):
        self.closed = True


@pytest.fixture
def setup(tmp_path, monkeypatch):
    timer = Clock()
    monkeypatch.setattr(validation, 'time', timer)
    # Host identity observation is a fixture, not a claim about real OS custody.
    monkeypatch.setattr(validation, 'process_creation_time_for_pid', lambda pid: 1)
    records = AtomicRecordStore(tmp_path.resolve() / 'state')
    invocation = SimpleNamespace(invocation_id='INVOCATION-DEADLINE', identity_digest=lambda: DIGEST)
    approval = dict(timeout_seconds=30, cleanup_timeout_seconds=1,
        output_limit_bytes=1024, cwd=str(tmp_path.resolve()))

    def run(factory, *, test_id='T001', deadline_ms=EPOCH_MS + 1000):
        return validation._run_check(records, 'VALIDATION-DEADLINE',
            {'test_id': test_id, 'argv': ['fixture-only']}, approval, invocation, DIGEST,
            clock=timer.timestamp, cancellation=None, process_factory=factory,
            absolute_deadline_unix_ms=deadline_ms)

    return timer, records, approval, run


@pytest.mark.parametrize('phase,reason,resumed', [
    ('creation', 'JOB_WALL_BUDGET_EXHAUSTED', False),
    ('exit', 'JOB_WALL_BUDGET_EXHAUSTED', True),
    ('running', 'JOB_WALL_BUDGET_EXHAUSTED', True),
    ('children', 'JOB_WALL_BUDGET_EXHAUSTED', True),
    ('own-check', 'VALIDATION_TIMED_OUT', True),
    ('own-check-children', 'VALIDATION_TIMED_OUT', True),
    ('backward-wall', 'JOB_WALL_BUDGET_EXHAUSTED', True),
])
def test_expiration_at_each_owned_phase_is_not_a_pass(setup, phase, reason, resumed):
    timer, records, approval, run = setup
    own_limit = phase.startswith('own-check')
    if own_limit:
        approval['timeout_seconds'] = 1
    process = Process(timer,
        poll_ms=1000 if phase in {'exit', 'own-check', 'backward-wall'} else 0,
        running=phase == 'running', children=phase in {'children', 'own-check-children'},
        backward_wall=phase == 'backward-wall')

    def factory(*args, **kwargs):
        if phase == 'creation':
            timer.elapsed_ms += 1000
        return process

    value = run(factory, deadline_ms=EPOCH_MS + (9000 if own_limit else 1000))
    assert value['status'] == 'failed', value
    assert value['failure'] == reason
    assert value['custody']['state'] == 'ABSENCE_VERIFIED'
    assert value['custody']['active_workload_count'] == 0
    assert process.resumed is resumed
    assert process.killed and process.closed
    saved = records.read('validation-logs/VALIDATION-DEADLINE/T001/result.json', lambda x: x)
    assert saved == value


@pytest.mark.parametrize('when', ['already-expired', 'preparation'])
def test_no_creation_after_remaining_time_is_consumed(setup, monkeypatch, when):
    timer, records, approval, run = setup
    original = validation.validator_environment

    def environment(home):
        value = original(home)
        if when == 'preparation':
            timer.elapsed_ms += 1000
        return value

    monkeypatch.setattr(validation, 'validator_environment', environment)
    deadline = EPOCH_MS if when == 'already-expired' else EPOCH_MS + 1000
    result = run(lambda *a, **k: pytest.fail('expired validator was created'), deadline_ms=deadline)
    assert result['failure'] == 'JOB_WALL_BUDGET_EXHAUSTED'
    assert result['status'] == 'failed'
    assert result['validator_identity'] is None
    assert result['custody']['state'] == 'ABSENCE_VERIFIED'
    assert result['custody']['request_sent'] is False


def test_successive_checks_share_the_same_absolute_deadline(setup):
    timer, records, approval, run = setup
    first, second = Process(timer, poll_ms=600), Process(timer, poll_ms=600)
    a = run(lambda *a, **k: first, test_id='T001')
    b = run(lambda *a, **k: second, test_id='T002')
    c = run(lambda *a, **k: pytest.fail('new check after shared deadline'), test_id='T004')
    assert a['status'] == 'passed'
    assert b['status'] == c['status'] == 'failed'
    assert b['failure'] == c['failure'] == 'JOB_WALL_BUDGET_EXHAUSTED'
    assert not first.killed and second.killed
    assert c['validator_identity'] is None
    assert all(r['custody']['state'] == 'ABSENCE_VERIFIED' for r in (a, b, c))


def test_timeout_cleanup_is_bounded_and_does_not_invent_absence(setup):
    timer, records, approval, run = setup
    process = Process(timer, running=True, stuck_cleanup=True)
    result = run(lambda *a, **k: process)
    assert result['status'] == 'uncertain'
    assert result['failure'] == 'JOB_WALL_BUDGET_EXHAUSTED'
    assert result['custody']['state'] == 'UNCERTAIN'
    assert result['custody']['active_workload_count'] == 1
    assert process.killed and process.closed
    assert timer.elapsed_ms <= 2050  # 1s execution + 1s approved cleanup + poll tolerance.


def test_timely_exit_still_passes_without_terminating_work(setup):
    timer, records, approval, run = setup
    process = Process(timer, poll_ms=500)
    result = run(lambda *a, **k: process)
    assert result['status'] == 'passed'
    assert result['failure'] is None
    assert result['custody']['state'] == 'ABSENCE_VERIFIED'
    assert process.resumed and process.closed and not process.killed
