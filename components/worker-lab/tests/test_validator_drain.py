"""Owned-validator drain remains bounded and requires complete process absence."""
import os
from types import SimpleNamespace
import threading

import pytest

from worker_lab import protected_validation as validation
from worker_lab.storage import AtomicRecordStore

pytestmark=pytest.mark.skipif(os.name!='nt',reason='Windows controller identity')


class Process:
    identity='windows-process:v1:12345:123456789'

    def __init__(self,mode,cancellation):
        self.mode=mode
        self.cancellation=cancellation
        self.samples=0
        self.terminated=False
        self.closed=False

    def resume(self):
        pass

    def poll(self):
        return 0

    def active_count(self):
        self.samples+=1
        if self.terminated:
            return 0
        if self.mode=='cancel':
            self.cancellation.set()
        if self.mode=='drain' and self.samples>=3:
            return 0
        return 1

    def terminate(self):
        self.terminated=True

    def close(self):
        self.closed=True


@pytest.mark.parametrize('mode,failure,terminated',[
    ('drain',None,False),
    ('persistent','VALIDATION_CHILDREN_REMAINED',True),
    ('cancel','VALIDATION_CANCELLED',True),
])
def test_owned_drain_requires_zero_and_retains_cancellation(tmp_path,monkeypatch,mode,failure,terminated):
    # Simulate OS accounting behind the existing process-factory seam; no real
    # worker/check verdict or accepted artifact is injected into a task workflow.
    cancellation=threading.Event()
    process=Process(mode,cancellation)
    ticks=iter(i*.3 for i in range(100))
    monkeypatch.setattr(validation.time,'monotonic',lambda:next(ticks))
    monkeypatch.setattr(validation.time,'sleep',lambda seconds:None)
    records=AtomicRecordStore(tmp_path/'state')
    invocation=SimpleNamespace(invocation_id='INVOCATION-DRAIN',identity_digest=lambda:'sha256:'+'a'*64)
    approval=dict(cwd=str(tmp_path),timeout_seconds=1,cleanup_timeout_seconds=1,output_limit_bytes=1024)
    result=validation._run_check(records,'VALIDATION-DRAIN',{'test_id':'T001','argv':['fixture']},
        approval,invocation,'sha256:'+'b'*64,clock=lambda:'2026-09-17T12:00:00Z',
        cancellation=cancellation,process_factory=lambda *args,**kwargs:process)
    assert result['status']==('passed' if failure is None else 'failed')
    assert result['failure']==failure
    assert result['custody']['state']=='ABSENCE_VERIFIED'
    assert result['custody']['active_workload_count']==0
    assert result['custody']['first_failure']==failure
    assert process.terminated is terminated and process.closed
    if mode=='drain':
        assert process.samples>=3
