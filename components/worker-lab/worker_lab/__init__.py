"""Protected contracts for the local Worker Lab."""

from .canonical import canonical_digest, canonical_json
from .models import (
    AttemptRecord,
    AttemptState,
    CurriculumRecord,
    EvidenceRecord,
    ExerciseRecord,
    FailureRecord,
    WorkspaceReceipt,
    WorkspaceReceiptState,
)
from .policy import ContextManifest, PolicyRecord, RoleRecord
from .test_catalog import TestCatalog
from .workspace import canonical_path_digest, discard_workspace, prepare_workspace, verify_workspace

__all__ = [
    "AttemptRecord",
    "AttemptState",
    "CurriculumRecord",
    "EvidenceRecord",
    "ExerciseRecord",
    "FailureRecord",
    "WorkspaceReceipt",
    "WorkspaceReceiptState",
    "ContextManifest",
    "PolicyRecord",
    "RoleRecord",
    "TestCatalog",
    "canonical_digest",
    "canonical_json",
    "canonical_path_digest",
    "discard_workspace",
    "prepare_workspace",
    "verify_workspace",
]
