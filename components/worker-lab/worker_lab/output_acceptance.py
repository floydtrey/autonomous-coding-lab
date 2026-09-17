"""Explicit output obligations; permission never implies mandatory mutation."""
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

from .canonical import canonical_digest
from .errors import LabValidationError

OUTPUT_ACCEPTANCE_SCHEMA = "worker-lab-output-acceptance:v1"
EVIDENCE_TYPES = ("protected-test-results:v1", "worker-output:v1", "workspace-diff:v1")


def invalid(message):
    raise LabValidationError("OUTPUT_ACCEPTANCE_INVALID", message)


def paths(value):
    if not isinstance(value, list) or any(not isinstance(p, str) for p in value):
        invalid("output paths must be a list of exact relative files")
    if value != sorted(set(value)):
        invalid("output paths must be sorted and unique")
    for p in value:
        path = PurePosixPath(p)
        if (not p or p == "." or p != p.strip() or p != path.as_posix() or path.is_absolute() or
                any(c in p for c in "\\:*?[]\x00") or
                any(part.lower() in (".", "..", ".git") or part.endswith((".", " ")) for part in path.parts)):
            invalid("output paths must be normalized exact relative files")
    return tuple(value)


@dataclass(frozen=True)
class OutputAcceptance:
    schema_version: str
    allowed_writable_paths: tuple[str, ...]
    required_changed_paths: tuple[str, ...]
    required_artifact_paths: tuple[str, ...]
    required_evidence: tuple[str, ...]
    allow_noop: bool

    @classmethod
    def from_mapping(cls, value):
        if not isinstance(value, dict) or set(value) != set(cls.__dataclass_fields__):
            invalid("required outputs need an explicit versioned output-acceptance contract; labels are insufficient")
        if value["schema_version"] != OUTPUT_ACCEPTANCE_SCHEMA or type(value["allow_noop"]) is not bool:
            invalid("unsupported output schema or non-boolean no-op permission")
        allowed, changed, artifacts = (paths(value[k]) for k in (
            "allowed_writable_paths", "required_changed_paths", "required_artifact_paths"))
        if not allowed or not set(changed + artifacts) <= set(allowed):
            invalid("required files must be within the explicit writable permission")
        if changed and value["allow_noop"]:
            invalid("required changes contradict no-op permission")
        evidence = value["required_evidence"]
        if (not isinstance(evidence, list) or any(e not in EVIDENCE_TYPES for e in evidence)
                or evidence != sorted(set(evidence))):
            invalid("result evidence must use explicit supported versioned types")
        return cls(OUTPUT_ACCEPTANCE_SCHEMA, allowed, changed, artifacts, tuple(evidence), value["allow_noop"])

    def to_dict(self):
        return {k: list(v) if isinstance(v, tuple) else v for k, v in asdict(self).items()}

    def digest(self):
        return canonical_digest(self.to_dict())

    def validate_changes(self, changed_paths):
        changed = paths(list(changed_paths))
        if not set(changed) <= set(self.allowed_writable_paths):
            invalid("candidate changed a path outside writable permission")
        if not set(self.required_changed_paths) <= set(changed):
            invalid("candidate is missing a required change")
        if not changed and not self.allow_noop:
            invalid("unchanged candidate lacks explicit no-op permission")

    def validate_artifacts(self, workspace: Path | None):
        if self.required_artifact_paths and workspace is None:
            invalid("required artifacts need independent workspace inspection")
        for relative in self.required_artifact_paths:
            root = workspace.resolve(strict=True)
            target = root
            for part in PurePosixPath(relative).parts:
                target = target / part
                if target.is_symlink() or target.is_junction():
                    invalid("required artifact must not traverse a filesystem link")
            if not target.is_file() or not target.resolve().is_relative_to(root):
                invalid(f"required artifact is missing or unsafe: {relative}")

    def validate_evidence(self, available):
        if not set(self.required_evidence) <= set(available):
            invalid("required result evidence is missing")
