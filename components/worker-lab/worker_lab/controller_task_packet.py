from __future__ import annotations
import hashlib, json, re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence
from uuid import UUID
from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .models import AttemptRecord, AttemptState
from .operator_control import validate_controller_identity

CONTROLLER_TASK_PACKET_SCHEMA = "worker-lab-controller-task-packet:v1"
KNOWLEDGE_CORE_EVIDENCE_SCHEMA = "worker-lab-knowledge-core-segment-evidence:v1"
AUTHORITY_EFFECT = "informational-only"
_MAX_USER_REQUEST_BYTES = 4096
_MAX_EVIDENCE_ITEMS = 4
_MAX_EVIDENCE_CONTENT_BYTES = 20000
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

class ControllerTaskService(Protocol):
    def show_record(self, collection: str, identity: str): ...
    def prepare_invocation(self, attempt_id: str, workspace_root, prompt: str): ...

@dataclass(frozen=True)
class KnowledgeCoreSegmentEvidence:
    schema_version: str
    query: str
    generation_id: str
    source_revision_highwater: int
    generation_config_digest: str
    structural_profile_id: str
    structural_profile_digest: str
    projection_profile_id: str
    projection_profile_digest: str
    resource_ref: str
    resource_version_ref: str
    repository: str
    source_path: str
    source_version: str
    lifecycle_state: str
    governing_manifest_digest: str
    projection_snapshot_digest: str
    source_repository_key: str
    source_document_key: str
    segment_key: str
    segment_ordinal: int
    source_byte_start: int
    source_byte_end: int
    source_line_start: int
    source_line_end: int
    source_slice_sha256: str
    content: str

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @classmethod
    def from_mapping(cls, value: Any) -> "KnowledgeCoreSegmentEvidence":
        data = _object(value, set(cls.__dataclass_fields__), "knowledge evidence")
        if data["schema_version"] != KNOWLEDGE_CORE_EVIDENCE_SCHEMA:
            raise LabValidationError("CONTROLLER_PACKET_SCHEMA_INVALID", "knowledge evidence schema is unsupported")
        content = _content(data["content"])
        encoded = content.encode("utf-8")
        if len(encoded) > _MAX_EVIDENCE_CONTENT_BYTES:
            raise LabValidationError("CONTROLLER_PACKET_OVERSIZED", "knowledge evidence content exceeds limit")
        slice_digest = _hex64(data["source_slice_sha256"], "source_slice_sha256")
        if hashlib.sha256(encoded).hexdigest() != slice_digest:
            raise LabValidationError("CONTROLLER_PACKET_EVIDENCE_INVALID", "knowledge evidence content differs from its canonical segment digest")
        start = _nonnegative_int(data["source_byte_start"], "source_byte_start")
        end = _positive_int(data["source_byte_end"], "source_byte_end")
        if end <= start or end - start != len(encoded):
            raise LabValidationError("CONTROLLER_PACKET_EVIDENCE_INVALID", "knowledge evidence byte coordinates differ from content")
        line_start = _positive_int(data["source_line_start"], "source_line_start")
        line_end = _positive_int(data["source_line_end"], "source_line_end")
        if line_end < line_start:
            raise LabValidationError("CONTROLLER_PACKET_EVIDENCE_INVALID", "knowledge evidence line coordinates are invalid")
        lifecycle = _text(data["lifecycle_state"], "lifecycle_state")
        if lifecycle != "current":
            raise LabValidationError("CONTROLLER_PACKET_LIFECYCLE_INVALID", "Controller Task Packet v1 accepts current Knowledge Core evidence only")
        for field in ("generation_id", "resource_ref", "resource_version_ref"):
            _uuid(data[field], field)
        return cls(
            KNOWLEDGE_CORE_EVIDENCE_SCHEMA,
            _text(data["query"], "query"),
            str(data["generation_id"]),
            _nonnegative_int(data["source_revision_highwater"], "source_revision_highwater"),
            _digest(data["generation_config_digest"], "generation_config_digest"),
            _text(data["structural_profile_id"], "structural_profile_id"),
            _digest(data["structural_profile_digest"], "structural_profile_digest"),
            _text(data["projection_profile_id"], "projection_profile_id"),
            _digest(data["projection_profile_digest"], "projection_profile_digest"),
            str(data["resource_ref"]),
            str(data["resource_version_ref"]),
            _text(data["repository"], "repository"),
            _text(data["source_path"], "source_path"),
            _text(data["source_version"], "source_version"),
            lifecycle,
            _text(data["governing_manifest_digest"], "governing_manifest_digest"),
            _text(data["projection_snapshot_digest"], "projection_snapshot_digest"),
            _text(data["source_repository_key"], "source_repository_key"),
            _text(data["source_document_key"], "source_document_key"),
            _text(data["segment_key"], "segment_key"),
            _nonnegative_int(data["segment_ordinal"], "segment_ordinal"),
            start, end, line_start, line_end, slice_digest, content,
        )

@dataclass(frozen=True)
class ControllerTaskPacket:
    schema_version: str
    attempt_id: str
    controller_identity: str
    user_request: str
    exercise_id: str
    exercise_version: int
    starting_commit: str
    authority_effect: str
    knowledge_evidence: tuple[KnowledgeCoreSegmentEvidence, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "attempt_id": self.attempt_id,
            "controller_identity": self.controller_identity,
            "user_request": self.user_request,
            "exercise_id": self.exercise_id,
            "exercise_version": self.exercise_version,
            "starting_commit": self.starting_commit,
            "authority_effect": self.authority_effect,
            "knowledge_evidence": [item.to_dict() for item in self.knowledge_evidence],
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    @classmethod
    def from_mapping(cls, value: Any) -> "ControllerTaskPacket":
        data = _object(value, set(cls.__dataclass_fields__), "controller task packet")
        if data["schema_version"] != CONTROLLER_TASK_PACKET_SCHEMA:
            raise LabValidationError("CONTROLLER_PACKET_SCHEMA_INVALID", "controller task packet schema is unsupported")
        evidence_raw = data["knowledge_evidence"]
        if not isinstance(evidence_raw, list) or not 1 <= len(evidence_raw) <= _MAX_EVIDENCE_ITEMS:
            raise LabValidationError("CONTROLLER_PACKET_EVIDENCE_INVALID", "controller task packet requires one to four evidence items")
        evidence = tuple(KnowledgeCoreSegmentEvidence.from_mapping(item) for item in evidence_raw)
        request = _text(data["user_request"], "user_request")
        if len(request.encode("utf-8")) > _MAX_USER_REQUEST_BYTES:
            raise LabValidationError("CONTROLLER_PACKET_OVERSIZED", "controller user request exceeds limit")
        controller = validate_controller_identity(data["controller_identity"])
        if data["authority_effect"] != AUTHORITY_EFFECT:
            raise LabValidationError("CONTROLLER_PACKET_AUTHORITY_INVALID", "Knowledge Core evidence cannot grant Worker Lab authority")
        commit = _text(data["starting_commit"], "starting_commit")
        if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit):
            raise LabValidationError("CONTROLLER_PACKET_IDENTITY_INVALID", "starting commit is invalid")
        return cls(
            CONTROLLER_TASK_PACKET_SCHEMA,
            _text(data["attempt_id"], "attempt_id"),
            controller,
            request,
            _text(data["exercise_id"], "exercise_id"),
            _positive_int(data["exercise_version"], "exercise_version"),
            commit,
            AUTHORITY_EFFECT,
            evidence,
        )

@dataclass(frozen=True)
class PreparedControllerInvocation:
    packet: ControllerTaskPacket
    invocation: Any

    @property
    def packet_digest(self) -> str:
        return self.packet.digest()

def knowledge_evidence_from_search_response(response: Mapping[str, Any], *, result_indexes: Sequence[int] = (0,)) -> tuple[KnowledgeCoreSegmentEvidence, ...]:
    fields = {
        "query", "generation_id", "source_revision_highwater", "retrieval_mode",
        "generation_config_digest", "structural_profile_id", "structural_profile_digest",
        "projection_profile_id", "projection_profile_digest", "results",
    }
    data = _object(response, fields, "Knowledge Core search response")
    if data["retrieval_mode"] != "segment":
        raise LabValidationError("CONTROLLER_PACKET_EVIDENCE_INVALID", "Controller Task Packet v1 requires segment-mode Knowledge Core evidence")
    results = data["results"]
    indexes = tuple(result_indexes)
    if (
        not isinstance(results, list) or not results or not indexes
        or len(indexes) > _MAX_EVIDENCE_ITEMS
        or any(isinstance(i, bool) or not isinstance(i, int) or i < 0 for i in indexes)
        or indexes != tuple(sorted(set(indexes))) or indexes[-1] >= len(results)
    ):
        raise LabValidationError("CONTROLLER_PACKET_EVIDENCE_INVALID", "selected Knowledge Core results are invalid")
    common = {
        "query": _text(data["query"], "query"),
        "generation_id": _text(data["generation_id"], "generation_id"),
        "source_revision_highwater": _nonnegative_int(data["source_revision_highwater"], "source_revision_highwater"),
        "generation_config_digest": _digest(data["generation_config_digest"], "generation_config_digest"),
        "structural_profile_id": _text(data["structural_profile_id"], "structural_profile_id"),
        "structural_profile_digest": _digest(data["structural_profile_digest"], "structural_profile_digest"),
        "projection_profile_id": _text(data["projection_profile_id"], "projection_profile_id"),
        "projection_profile_digest": _digest(data["projection_profile_digest"], "projection_profile_digest"),
    }
    items = []
    for index in indexes:
        hit = results[index]
        if not isinstance(hit, Mapping) or not isinstance(hit.get("segment"), Mapping):
            raise LabValidationError("CONTROLLER_PACKET_EVIDENCE_INVALID", "Knowledge Core result lacks segment provenance")
        segment = hit["segment"]
        lifecycle = _text(hit.get("lifecycle_state"), "lifecycle_state")
        if lifecycle != "current" or segment.get("effective_lifecycle_state") != "current":
            raise LabValidationError("CONTROLLER_PACKET_LIFECYCLE_INVALID", "Controller Task Packet v1 accepts current Knowledge Core evidence only")
        item = {
            "schema_version": KNOWLEDGE_CORE_EVIDENCE_SCHEMA,
            **common,
            "resource_ref": _text(hit.get("resource_ref"), "resource_ref"),
            "resource_version_ref": _text(hit.get("resource_version_ref"), "resource_version_ref"),
            "repository": _text(hit.get("repository"), "repository"),
            "source_path": _text(hit.get("source_path"), "source_path"),
            "source_version": _text(hit.get("source_version"), "source_version"),
            "lifecycle_state": lifecycle,
            "governing_manifest_digest": _text(segment.get("governing_manifest_digest"), "governing_manifest_digest"),
            "projection_snapshot_digest": _text(segment.get("projection_snapshot_digest"), "projection_snapshot_digest"),
            "source_repository_key": _text(segment.get("source_repository_key"), "source_repository_key"),
            "source_document_key": _text(segment.get("source_document_key"), "source_document_key"),
            "segment_key": _text(segment.get("segment_key"), "segment_key"),
            "segment_ordinal": segment.get("segment_ordinal"),
            "source_byte_start": segment.get("source_byte_start"),
            "source_byte_end": segment.get("source_byte_end"),
            "source_line_start": segment.get("source_line_start"),
            "source_line_end": segment.get("source_line_end"),
            "source_slice_sha256": _text(segment.get("source_slice_sha256"), "source_slice_sha256"),
            "content": _content(hit.get("content")),
        }
        items.append(KnowledgeCoreSegmentEvidence.from_mapping(item))
    return tuple(items)

def build_controller_task_packet(
    attempt: AttemptRecord, *, controller_identity: str, user_request: str,
    kc_search_response: Mapping[str, Any], result_indexes: Sequence[int] = (0,),
) -> ControllerTaskPacket:
    if attempt.state is not AttemptState.READY:
        raise LabValidationError("CONTROLLER_PACKET_ATTEMPT_INVALID", "controller task packet requires a READY attempt")
    packet = ControllerTaskPacket.from_mapping({
        "schema_version": CONTROLLER_TASK_PACKET_SCHEMA,
        "attempt_id": attempt.attempt_id,
        "controller_identity": controller_identity,
        "user_request": user_request,
        "exercise_id": attempt.exercise_id,
        "exercise_version": attempt.exercise_version,
        "starting_commit": attempt.starting_commit,
        "authority_effect": AUTHORITY_EFFECT,
        "knowledge_evidence": [item.to_dict() for item in knowledge_evidence_from_search_response(kc_search_response, result_indexes=result_indexes)],
    })
    if len(packet.to_json().encode("utf-8")) > 32768:
        raise LabValidationError("CONTROLLER_PACKET_OVERSIZED", "controller task packet exceeds Worker Lab prompt limit")
    return packet

def prepare_controller_task_invocation(
    service: ControllerTaskService, *, attempt_id: str, workspace_root,
    controller_identity: str, user_request: str, kc_search_response: Mapping[str, Any],
    result_indexes: Sequence[int] = (0,),
) -> PreparedControllerInvocation:
    detail = service.show_record("attempts", attempt_id)
    attempt = AttemptRecord.from_mapping(detail.record)
    packet = build_controller_task_packet(
        attempt, controller_identity=controller_identity, user_request=user_request,
        kc_search_response=kc_search_response, result_indexes=result_indexes,
    )
    invocation = service.prepare_invocation(attempt_id, workspace_root, packet.to_json())
    if invocation.to_dict()["record"].get("prompt_digest") != packet.digest():
        raise LabValidationError("CONTROLLER_PACKET_IDENTITY_INVALID", "prepared invocation does not seal the exact Controller Task Packet")
    return PreparedControllerInvocation(packet, invocation)

def parse_controller_task_packet(raw: str) -> ControllerTaskPacket:
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LabValidationError("CONTROLLER_PACKET_SCHEMA_INVALID", "controller task packet is not JSON") from exc
    packet = ControllerTaskPacket.from_mapping(value)
    if packet.to_json() != raw:
        raise LabValidationError("CONTROLLER_PACKET_SCHEMA_INVALID", "controller task packet must use canonical JSON")
    return packet

def _object(value: Any, fields: set[str], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise LabValidationError("CONTROLLER_PACKET_FIELDS_INVALID", f"{name} fields are missing or unknown")
    return value

def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or "\x00" in value:
        raise LabValidationError("CONTROLLER_PACKET_FIELDS_INVALID", f"{field} must be trimmed non-empty text")
    return value


def _content(value: Any) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise LabValidationError("CONTROLLER_PACKET_FIELDS_INVALID", "content must be non-empty UTF-8 text")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise LabValidationError("CONTROLLER_PACKET_FIELDS_INVALID", "content must be UTF-8 text") from exc
    return value

def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LabValidationError("CONTROLLER_PACKET_FIELDS_INVALID", f"{field} must be positive")
    return value

def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LabValidationError("CONTROLLER_PACKET_FIELDS_INVALID", f"{field} must be non-negative")
    return value

def _uuid(value: Any, field: str) -> UUID:
    text = _text(value, field)
    try:
        parsed = UUID(text)
    except ValueError as exc:
        raise LabValidationError("CONTROLLER_PACKET_FIELDS_INVALID", f"{field} must be a UUID") from exc
    if str(parsed) != text:
        raise LabValidationError("CONTROLLER_PACKET_FIELDS_INVALID", f"{field} must use canonical UUID text")
    return parsed

def _digest(value: Any, field: str) -> str:
    text = _text(value, field)
    if not _DIGEST_RE.fullmatch(text):
        raise LabValidationError("CONTROLLER_PACKET_FIELDS_INVALID", f"{field} must be a sha256 digest")
    return text

def _hex64(value: Any, field: str) -> str:
    text = _text(value, field)
    if not _HEX64_RE.fullmatch(text):
        raise LabValidationError("CONTROLLER_PACKET_FIELDS_INVALID", f"{field} must be lowercase SHA-256 hex")
    return text
