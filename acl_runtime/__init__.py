"""Reusable ACL Next runtime entrypoints.

Keep package import side-effect free so `python -m acl_runtime.runner` does not
pre-import the module it is about to execute.
"""
from .services import LocalServiceConfig, LocalServiceSupervisor, ProbeResult, ProbeState


def run_program(*args, **kwargs):
    from .runner import run_program as _run_program
    return _run_program(*args, **kwargs)


__all__ = [
    "LocalServiceConfig",
    "LocalServiceSupervisor",
    "ProbeResult",
    "ProbeState",
    "run_program",
]
