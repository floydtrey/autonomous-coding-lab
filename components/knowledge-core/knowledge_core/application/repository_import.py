from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import PurePosixPath
import re
from typing import Mapping
from uuid import UUID, uuid4

from sqlalchemy import select

from knowledge_core.application.repository_source import RepositorySourceReader
from knowledge_core.application.retrieval import RetrievalServiceKnowledgeKernel
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind
from knowledge_core.domain.repository_import import (
    ImportAction,
    RepositoryImportPlan,
    RepositoryImportReceiptSnapshot,
    RepositorySourceProof,
)
from knowledge_core.domain.resources import ResourceLocatorKind
from knowledge_core.domain.retrieval import RetrievalLifecycleState, TextIndexSource
from knowledge_core.storage.repository_import_models import (
    RepositoryDocumentBinding,
    RepositoryImportReceipt,
    RepositorySourceObservation,
)
from knowledge_core.storage.resource_models import ResourceVersion


_HEX_OBJECT = re.compile(r"^[0-9a-f]{40,64}$")
_SUPPORTED_MEDIA = {"text/plain", "text/markdown"}
_ALLOWED_LIFECYCLE = {"current", "unknown", "superseded"}
_ALLOWED_HISTORY_POLICY = "retain_prior_versions_as_superseded"
_GLOB_CHARS = set("*?[]")


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _git_blob_sha(content: bytes) -> str:
    digest = sha1()
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return digest.hexdigest()


def _receipt_snapshot(row: RepositoryImportReceipt) -> RepositoryImportReceiptSnapshot:
    return RepositoryImportReceiptSnapshot(
        manifest_digest=row.manifest_digest,
        previous_manifest_digest=row.previous_manifest_digest,
        source_repository_key=row.source_repository_key,
        source_commit=row.source_commit,
        status=row.status,
        plan_digest=row.plan_digest,
        resulting_text_generation_id=row.resulting_text_generation_id,
    )


class RepositoryImportKnowledgeKernel(RetrievalServiceKnowledgeKernel):
    """RI-2 governed repository import over exact Git object proofs."""

    def __init__(
        self,
        *args,
        source_readers: Mapping[str, RepositorySourceReader],
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.source_readers = dict(source_readers)

    def _latest_settled_receipt(
        self,
        repository_key: str,
    ) -> RepositoryImportReceipt | None:
        return self.session.execute(
            select(RepositoryImportReceipt)
            .where(
                RepositoryImportReceipt.source_repository_key == repository_key,
                RepositoryImportReceipt.status == "settled",
            )
            .order_by(
                RepositoryImportReceipt.settled_at.desc(),
                RepositoryImportReceipt.manifest_digest.desc(),
            )
            .limit(1)
        ).scalar_one_or_none()

    def _validate_path(self, path: object) -> str:
        if not isinstance(path, str) or not path or "\\" in path:
            raise KnowledgeInvariantError(
                "manifest path must be a normalized repository-relative path"
            )
        if any(ch in path for ch in _GLOB_CHARS):
            raise KnowledgeInvariantError("manifest paths cannot contain glob patterns")
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
            raise KnowledgeInvariantError("manifest path traversal is not allowed")
        normalized = pure.as_posix()
        if normalized != path or normalized.startswith("/"):
            raise KnowledgeInvariantError("manifest path must already be normalized")
        return path

    def _normalize_manifest(self, manifest: dict) -> dict:
        if not isinstance(manifest, dict):
            raise KnowledgeInvariantError("repository import manifest must be an object")
        required = {
            "schema_version",
            "manifest_id",
            "source_repository_key",
            "repository_locator",
            "source_commit",
            "previous_manifest_digest",
            "history_policy",
            "entries",
            "retirements",
        }
        missing = required - set(manifest)
        if missing:
            raise KnowledgeInvariantError(
                "repository import manifest is missing required fields: "
                + ", ".join(sorted(missing))
            )
        if manifest["schema_version"] != 2:
            raise KnowledgeInvariantError("repository import schema_version must be 2")
        for field in ("manifest_id", "source_repository_key", "repository_locator"):
            if not isinstance(manifest[field], str) or not manifest[field].strip():
                raise KnowledgeInvariantError(f"{field} must be a non-empty string")
        source_commit = manifest["source_commit"]
        if not isinstance(source_commit, str) or not _HEX_OBJECT.fullmatch(source_commit):
            raise KnowledgeInvariantError(
                "source_commit must be an exact Git object id"
            )
        previous = manifest["previous_manifest_digest"]
        if previous is not None and (
            not isinstance(previous, str)
            or not re.fullmatch(r"[0-9a-f]{64}", previous)
        ):
            raise KnowledgeInvariantError(
                "previous_manifest_digest must be null or SHA-256 hex"
            )
        if manifest["history_policy"] != _ALLOWED_HISTORY_POLICY:
            raise KnowledgeInvariantError(
                f"history_policy must be {_ALLOWED_HISTORY_POLICY}"
            )
        if not isinstance(manifest["entries"], list) or not isinstance(
            manifest["retirements"], list
        ):
            raise KnowledgeInvariantError("entries and retirements must be arrays")

        normalized_entries = []
        keys = set()
        paths = set()
        entry_required = {
            "source_document_key",
            "path",
            "git_blob_sha",
            "media_type",
            "classification",
            "retrieval_lifecycle",
            "authority_rank",
            "rationale",
        }
        for raw in manifest["entries"]:
            if not isinstance(raw, dict):
                raise KnowledgeInvariantError("manifest entries must be objects")
            missing_entry = entry_required - set(raw)
            if missing_entry:
                raise KnowledgeInvariantError(
                    "manifest entry is missing required fields: "
                    + ", ".join(sorted(missing_entry))
                )
            key = raw["source_document_key"]
            if not isinstance(key, str) or not key.strip():
                raise KnowledgeInvariantError("source_document_key must be non-empty")
            if key in keys:
                raise KnowledgeInvariantError(
                    "duplicate source_document_key in manifest"
                )
            keys.add(key)
            path = self._validate_path(raw["path"])
            if path in paths:
                raise KnowledgeInvariantError("duplicate active path in manifest")
            paths.add(path)
            blob = raw["git_blob_sha"]
            if not isinstance(blob, str) or not _HEX_OBJECT.fullmatch(blob):
                raise KnowledgeInvariantError(
                    "git_blob_sha must be an exact Git object id"
                )
            if raw["media_type"] not in _SUPPORTED_MEDIA:
                raise KnowledgeInvariantError(
                    "repository import media type is unsupported"
                )
            if raw["retrieval_lifecycle"] not in _ALLOWED_LIFECYCLE:
                raise KnowledgeInvariantError("invalid retrieval_lifecycle")
            if raw["authority_rank"] is not None and (
                isinstance(raw["authority_rank"], bool)
                or not isinstance(raw["authority_rank"], int)
            ):
                raise KnowledgeInvariantError(
                    "authority_rank must be an integer or null"
                )
            for field in ("classification", "rationale"):
                if not isinstance(raw[field], str) or not raw[field].strip():
                    raise KnowledgeInvariantError(
                        f"{field} must be a non-empty string"
                    )
            continuity = raw.get("continuity_rationale")
            if continuity is not None and (
                not isinstance(continuity, str) or not continuity.strip()
            ):
                raise KnowledgeInvariantError(
                    "continuity_rationale must be null or non-empty"
                )
            supersedes = raw.get("supersedes_document_key")
            if supersedes is not None and (
                not isinstance(supersedes, str) or not supersedes.strip()
            ):
                raise KnowledgeInvariantError(
                    "supersedes_document_key must be null or non-empty"
                )
            normalized_entries.append(dict(raw))

        normalized_retirements = []
        retired_keys = set()
        for raw in manifest["retirements"]:
            if not isinstance(raw, dict):
                raise KnowledgeInvariantError("retirements must be objects")
            for field in (
                "source_document_key",
                "reason",
                "historical_retrieval",
            ):
                if field not in raw:
                    raise KnowledgeInvariantError(
                        f"retirement missing required field: {field}"
                    )
            key = raw["source_document_key"]
            if (
                not isinstance(key, str)
                or not key.strip()
                or key in retired_keys
                or key in keys
            ):
                raise KnowledgeInvariantError(
                    "retirement document key must be unique and not active"
                )
            retired_keys.add(key)
            if not isinstance(raw["reason"], str) or not raw["reason"].strip():
                raise KnowledgeInvariantError("retirement reason must be non-empty")
            if raw["historical_retrieval"] not in {"retain", "exclude"}:
                raise KnowledgeInvariantError(
                    "historical_retrieval must be retain or exclude"
                )
            replacement = raw.get("replacement_document_key")
            if replacement is not None and (
                not isinstance(replacement, str) or not replacement.strip()
            ):
                raise KnowledgeInvariantError(
                    "replacement_document_key must be null or non-empty"
                )
            normalized_retirements.append(dict(raw))

        normalized = dict(manifest)
        normalized["entries"] = normalized_entries
        normalized["retirements"] = normalized_retirements
        return normalized

    def _source_reader(self, manifest: dict) -> RepositorySourceReader:
        key = manifest["source_repository_key"]
        reader = self.source_readers.get(key)
        if reader is None:
            raise KnowledgeInvariantError(
                "source_repository_key is not configured on this service"
            )
        if reader.repository_locator != manifest["repository_locator"]:
            raise KnowledgeInvariantError(
                "repository locator does not match governed repository configuration"
            )
        return reader

    def _verify_sources(
        self,
        manifest: dict,
        reader: RepositorySourceReader,
    ) -> tuple[RepositorySourceProof, ...]:
        proofs = []
        for entry in manifest["entries"]:
            proof = reader.read_exact(
                source_commit=manifest["source_commit"],
                path=entry["path"],
            )
            if proof.object_type != "blob" or proof.object_mode not in {
                "100644",
                "100755",
            }:
                raise KnowledgeInvariantError(
                    "repository import accepts only regular Git blobs"
                )
            if (
                proof.source_commit != manifest["source_commit"]
                or proof.path != entry["path"]
            ):
                raise KnowledgeInvariantError(
                    "repository reader returned mismatched source identity"
                )
            if proof.git_blob_sha != entry["git_blob_sha"]:
                raise KnowledgeInvariantError(
                    "manifest Git blob does not match exact source object"
                )
            if len(proof.git_blob_sha) == 40 and _git_blob_sha(
                proof.content
            ) != proof.git_blob_sha:
                raise KnowledgeInvariantError(
                    "Git blob identity does not match exact source bytes"
                )
            try:
                proof.content.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                raise KnowledgeInvariantError(
                    "repository import text must be strict UTF-8"
                ) from exc
            proofs.append(proof)
        return tuple(proofs)

    def _prior_entry_map(
        self,
        receipt: RepositoryImportReceipt | None,
    ) -> dict[str, dict]:
        if receipt is None:
            return {}
        return {
            entry["source_document_key"]: entry
            for entry in receipt.manifest_json.get("entries", [])
        }

    def _prior_retirement_keys(
        self,
        receipt: RepositoryImportReceipt | None,
    ) -> set[str]:
        if receipt is None:
            return set()
        return {
            item["source_document_key"]
            for item in receipt.manifest_json.get("retirements", [])
        }

    def _observation_for_manifest(
        self,
        manifest_digest: str,
        document_key: str,
    ) -> RepositorySourceObservation | None:
        return self.session.execute(
            select(RepositorySourceObservation).where(
                RepositorySourceObservation.manifest_digest == manifest_digest,
                RepositorySourceObservation.source_document_key == document_key,
            )
        ).scalar_one_or_none()

    def _binding(
        self,
        repository_key: str,
        document_key: str,
    ) -> RepositoryDocumentBinding | None:
        return self.session.get(
            RepositoryDocumentBinding,
            {
                "source_repository_key": repository_key,
                "source_document_key": document_key,
            },
        )

    def _matching_version(
        self,
        resource_ref: UUID,
        content: bytes,
    ) -> ResourceVersion | None:
        digest = sha256(content).hexdigest()
        return self.session.execute(
            select(ResourceVersion).where(
                ResourceVersion.resource_ref_id == resource_ref,
                ResourceVersion.content_digest_algo == "sha256",
                ResourceVersion.content_digest == digest,
            )
        ).scalar_one_or_none()

    def plan_repository_import(self, manifest: dict) -> RepositoryImportPlan:
        normalized = self._normalize_manifest(manifest)
        manifest_digest = _canonical_digest(normalized)
        replay = self.session.get(RepositoryImportReceipt, manifest_digest)
        if replay is not None and replay.status == "settled":
            return RepositoryImportPlan(
                manifest=normalized,
                manifest_digest=manifest_digest,
                previous_manifest_digest=normalized["previous_manifest_digest"],
                expected_current_generation_id=replay.resulting_text_generation_id,
                actions=(),
                source_proofs=(),
                plan_digest=replay.plan_digest,
                replay_receipt=_receipt_snapshot(replay),
            )

        repository_key = normalized["source_repository_key"]
        previous = self._latest_settled_receipt(repository_key)
        expected_previous = previous.manifest_digest if previous is not None else None
        if normalized["previous_manifest_digest"] != expected_previous:
            raise KnowledgeInvariantError(
                "manifest chain does not match the latest accepted manifest"
            )

        previous_keys = set(self._prior_entry_map(previous)) | self._prior_retirement_keys(
            previous
        )
        next_keys = {
            entry["source_document_key"] for entry in normalized["entries"]
        } | {
            retirement["source_document_key"]
            for retirement in normalized["retirements"]
        }
        if previous_keys - next_keys:
            raise KnowledgeInvariantError(
                "manifest silently omits previously managed document keys"
            )

        reader = self._source_reader(normalized)
        proofs = self._verify_sources(normalized, reader)

        previous_entries = self._prior_entry_map(previous)
        actions = []
        for entry, proof in zip(normalized["entries"], proofs, strict=True):
            key = entry["source_document_key"]
            binding = self._binding(repository_key, key)
            if binding is None:
                actions.append(ImportAction(key, "create_resource"))
                continue

            matching = self._matching_version(binding.resource_ref, proof.content)
            old = previous_entries.get(key)
            if old is None:
                actions.append(
                    ImportAction(
                        key,
                        "reuse_version" if matching is not None else "create_version",
                        binding.resource_ref,
                        matching.ref_id if matching is not None else None,
                    )
                )
                continue

            path_changed = old["path"] != entry["path"]
            blob_changed = old["git_blob_sha"] != entry["git_blob_sha"]
            if (
                path_changed
                and blob_changed
                and not entry.get("continuity_rationale")
            ):
                raise KnowledgeInvariantError(
                    f"rename-plus-edit requires continuity_rationale: {key}"
                )
            metadata_changed = any(
                old.get(field) != entry.get(field)
                for field in (
                    "classification",
                    "retrieval_lifecycle",
                    "authority_rank",
                    "rationale",
                )
            )
            if matching is None:
                action = "create_version"
            elif path_changed:
                action = "add_locator"
            elif metadata_changed:
                action = "classification_only"
            else:
                action = "reuse_version"
            actions.append(
                ImportAction(
                    key,
                    action,
                    binding.resource_ref,
                    matching.ref_id if matching is not None else None,
                )
            )

        current = self._generation_kernel().current_generation(
            derived_kind=DerivedKind.TEXT
        )
        current_id = current.generation_id if current is not None else None
        plan_payload = {
            "manifest_digest": manifest_digest,
            "previous_manifest_digest": expected_previous,
            "expected_current_generation_id": str(current_id) if current_id else None,
            "actions": [
                {
                    "source_document_key": item.source_document_key,
                    "action": item.action,
                    "resource_ref": str(item.resource_ref) if item.resource_ref else None,
                    "resource_version_ref": (
                        str(item.resource_version_ref)
                        if item.resource_version_ref
                        else None
                    ),
                }
                for item in actions
            ],
            "source_proofs": [
                {
                    "source_commit": proof.source_commit,
                    "path": proof.path,
                    "git_blob_sha": proof.git_blob_sha,
                    "sha256": sha256(proof.content).hexdigest(),
                    "object_mode": proof.object_mode,
                    "object_type": proof.object_type,
                }
                for proof in proofs
            ],
        }
        return RepositoryImportPlan(
            manifest=normalized,
            manifest_digest=manifest_digest,
            previous_manifest_digest=expected_previous,
            expected_current_generation_id=current_id,
            actions=tuple(actions),
            source_proofs=proofs,
            plan_digest=_canonical_digest(plan_payload),
        )

    def _ensure_receipt(
        self,
        plan: RepositoryImportPlan,
    ) -> RepositoryImportReceipt:
        row = self.session.get(RepositoryImportReceipt, plan.manifest_digest)
        if row is None:
            row = RepositoryImportReceipt(
                manifest_digest=plan.manifest_digest,
                previous_manifest_digest=plan.previous_manifest_digest,
                source_repository_key=plan.manifest["source_repository_key"],
                source_commit=plan.manifest["source_commit"],
                plan_digest=plan.plan_digest,
                status="applying",
                manifest_json=plan.manifest,
                resulting_text_generation_id=None,
                created_at=self._now(),
                settled_at=None,
            )
            self.session.add(row)
        else:
            if row.status == "settled":
                return row
            row.plan_digest = plan.plan_digest
            row.status = "applying"
            row.manifest_json = plan.manifest
        self._commit()
        return row

    def _record_observation(
        self,
        *,
        plan: RepositoryImportPlan,
        entry: dict,
        resource_ref: UUID,
        resource_version_ref: UUID,
    ) -> None:
        existing = self._observation_for_manifest(
            plan.manifest_digest,
            entry["source_document_key"],
        )
        if existing is not None:
            if (
                existing.resource_ref != resource_ref
                or existing.resource_version_ref != resource_version_ref
                or existing.git_blob_sha != entry["git_blob_sha"]
                or existing.path != entry["path"]
            ):
                raise KnowledgeInvariantError(
                    "failed import residue conflicts with exact retry"
                )
            return
        self.session.add(
            RepositorySourceObservation(
                observation_id=uuid4(),
                manifest_digest=plan.manifest_digest,
                source_repository_key=plan.manifest["source_repository_key"],
                source_document_key=entry["source_document_key"],
                source_commit=plan.manifest["source_commit"],
                path=entry["path"],
                git_blob_sha=entry["git_blob_sha"],
                resource_ref=resource_ref,
                resource_version_ref=resource_version_ref,
                classification=entry["classification"],
                retrieval_lifecycle=entry["retrieval_lifecycle"],
                authority_rank=entry["authority_rank"],
                rationale=entry["rationale"],
            )
        )
        self._commit()

    def _settled_observations_for_document(
        self,
        repository_key: str,
        document_key: str,
    ) -> list[RepositorySourceObservation]:
        return self.session.scalars(
            select(RepositorySourceObservation)
            .join(
                RepositoryImportReceipt,
                RepositoryImportReceipt.manifest_digest
                == RepositorySourceObservation.manifest_digest,
            )
            .where(
                RepositorySourceObservation.source_repository_key == repository_key,
                RepositorySourceObservation.source_document_key == document_key,
                RepositoryImportReceipt.status == "settled",
            )
            .order_by(
                RepositoryImportReceipt.settled_at,
                RepositorySourceObservation.observation_id,
            )
        ).all()

    def _generation_sources(
        self,
        plan: RepositoryImportPlan,
        current_versions: dict[str, UUID],
    ) -> list[TextIndexSource]:
        manifest = plan.manifest
        repository_key = manifest["source_repository_key"]
        result_by_version: dict[UUID, TextIndexSource] = {}

        for entry in manifest["entries"]:
            key = entry["source_document_key"]
            current_ref = current_versions[key]
            for observation in self._settled_observations_for_document(
                repository_key,
                key,
            ):
                if observation.resource_version_ref == current_ref:
                    continue
                result_by_version[observation.resource_version_ref] = TextIndexSource(
                    resource_version_ref=observation.resource_version_ref,
                    lifecycle_state=RetrievalLifecycleState.SUPERSEDED,
                    authority_rank=observation.authority_rank,
                    repository=manifest["repository_locator"],
                    source_path=observation.path,
                    source_version=observation.source_commit,
                )
            result_by_version[current_ref] = TextIndexSource(
                resource_version_ref=current_ref,
                lifecycle_state=RetrievalLifecycleState(
                    entry["retrieval_lifecycle"]
                ),
                authority_rank=entry["authority_rank"],
                repository=manifest["repository_locator"],
                source_path=entry["path"],
                source_version=manifest["source_commit"],
            )

        for retirement in manifest["retirements"]:
            if retirement["historical_retrieval"] != "retain":
                continue
            observations = self._settled_observations_for_document(
                repository_key,
                retirement["source_document_key"],
            )
            if not observations:
                raise KnowledgeInvariantError(
                    "cannot retain retirement without an accepted source observation"
                )
            latest = observations[-1]
            result_by_version[latest.resource_version_ref] = TextIndexSource(
                resource_version_ref=latest.resource_version_ref,
                lifecycle_state=RetrievalLifecycleState.SUPERSEDED,
                authority_rank=latest.authority_rank,
                repository=manifest["repository_locator"],
                source_path=latest.path,
                source_version=latest.source_commit,
            )
        return list(result_by_version.values())

    def apply_repository_import(
        self,
        *,
        manifest: dict,
        expected_plan_digest: str,
        before_publish_hook=None,
    ) -> RepositoryImportReceiptSnapshot:
        plan = self.plan_repository_import(manifest)
        if plan.replay_receipt is not None:
            if expected_plan_digest != plan.plan_digest:
                raise KnowledgeInvariantError(
                    "plan digest does not match accepted replay"
                )
            return plan.replay_receipt
        if expected_plan_digest != plan.plan_digest:
            raise KnowledgeInvariantError(
                "repository import plan is stale or unapproved"
            )

        receipt = self._ensure_receipt(plan)
        if receipt.status == "settled":
            return _receipt_snapshot(receipt)

        foundation = self.bootstrap_resource_test_profile()
        current_versions: dict[str, UUID] = {}
        proof_by_path = {proof.path: proof for proof in plan.source_proofs}
        action_by_key = {
            action.source_document_key: action for action in plan.actions
        }
        try:
            for entry in plan.manifest["entries"]:
                key = entry["source_document_key"]
                proof = proof_by_path[entry["path"]]
                action = action_by_key[key]
                binding = self._binding(
                    plan.manifest["source_repository_key"],
                    key,
                )
                if binding is None:
                    resource = self.create_resource(
                        kind_revision_ref=foundation.artifact_kind_revision_ref
                    )
                    binding = RepositoryDocumentBinding(
                        source_repository_key=plan.manifest[
                            "source_repository_key"
                        ],
                        source_document_key=key,
                        resource_ref=resource.resource_ref,
                    )
                    self.session.add(binding)
                    self._commit()

                version = self._matching_version(
                    binding.resource_ref,
                    proof.content,
                )
                if version is None:
                    snapshot = self.ingest_resource_version(
                        resource_ref=binding.resource_ref,
                        content=proof.content,
                        ingestion_kind_revision_ref=(
                            foundation.resource_ingestion_kind_revision_ref
                        ),
                        media_type=entry["media_type"],
                        locator_kind=ResourceLocatorKind.PATH,
                        locator_text=entry["path"],
                    )
                    version_ref = snapshot.resource_version_ref
                else:
                    if action.action == "add_locator":
                        snapshot = self.ingest_resource_version(
                            resource_ref=binding.resource_ref,
                            content=proof.content,
                            ingestion_kind_revision_ref=(
                                foundation.resource_ingestion_kind_revision_ref
                            ),
                            media_type=entry["media_type"],
                            locator_kind=ResourceLocatorKind.PATH,
                            locator_text=entry["path"],
                        )
                        version_ref = snapshot.resource_version_ref
                    else:
                        version_ref = version.ref_id
                current_versions[key] = version_ref
                self._record_observation(
                    plan=plan,
                    entry=entry,
                    resource_ref=binding.resource_ref,
                    resource_version_ref=version_ref,
                )

            if before_publish_hook is not None:
                before_publish_hook()

            generation = self.build_text_generation(
                sources=self._generation_sources(plan, current_versions)
            )
            receipt = self.session.get(
                RepositoryImportReceipt,
                plan.manifest_digest,
            )
            receipt.status = "settled"
            receipt.resulting_text_generation_id = generation.generation_id
            receipt.settled_at = self._now()
            self._commit()
            return _receipt_snapshot(receipt)
        except Exception:
            self.session.rollback()
            receipt = self.session.get(
                RepositoryImportReceipt,
                plan.manifest_digest,
            )
            if receipt is not None and receipt.status != "settled":
                receipt.status = "failed"
                self._commit()
            raise
