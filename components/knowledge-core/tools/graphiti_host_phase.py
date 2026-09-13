from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
from uuid import UUID, uuid5

from sqlalchemy import select

from knowledge_core.application.graph_retrieval import GraphProjectionRetrievalKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.authority.retrieval import (
    RetrievalAuthorityDecision,
    RetrievalAuthorityOperation,
    RetrievalAuthorityRequest,
)
from knowledge_core.domain.generations import DerivedKind
from knowledge_core.domain.projection_adapter import ProjectionAdapterExecutionError
from knowledge_core.domain.projection_evidence import ProjectionDisposition
from knowledge_core.domain.projection_validation import ProjectionValidationOutcome
from knowledge_core_providers.graphiti import (
    GraphitiLocalConfig,
    GraphitiProjectionAdapter,
    GraphitiProjectionValidator,
)
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.section_retrieval_models import ResourceSegmentTextSearch


_CALLER = "graphiti-host-qualification"
_ATTEMPT_NAMESPACE = UUID("447c7e9c-a04a-583f-b7ff-610421a94e28")
_VALIDATION_NAMESPACE = UUID("af266821-90cf-52cb-83a6-0df8bd3796ed")


def _stable_uuid(namespace: UUID, payload: dict[str, object]) -> UUID:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return uuid5(namespace, sha256(canonical.encode("utf-8")).hexdigest())


def _json_default(value):
    if isinstance(value, UUID):
        return str(value)
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _print(payload: dict[str, object]) -> None:
    print(json.dumps(payload, default=_json_default, sort_keys=True, indent=2))


class _QualificationGraphAuthority:
    def __init__(self, *, namespace_key: str, scope_key: str):
        self.namespace_key = namespace_key
        self.scope_key = scope_key

    def evaluate_retrieval(
        self,
        request: RetrievalAuthorityRequest,
    ) -> RetrievalAuthorityDecision:
        allowed = (
            request.caller_principal_ref == _CALLER
            and request.operation is RetrievalAuthorityOperation.SEARCH_GRAPH
            and request.namespace_key == self.namespace_key
            and request.scope_key == self.scope_key
            and not request.include_superseded
        )
        return RetrievalAuthorityDecision(
            allowed=allowed,
            decision_ref="graphiti-host:validated-graph-search",
            reason_code=(
                "qualification-caller-operation-and-scope-match"
                if allowed
                else "qualification-boundary-mismatch"
            ),
        )


def _list_sources(kernel: GraphProjectionRetrievalKnowledgeKernel) -> int:
    current = kernel.current_generation(derived_kind=DerivedKind.TEXT)
    if current is None:
        _print({"status": "no-current-text-generation", "sources": []})
        return 2
    rows = kernel.session.execute(
        select(
            ResourceSegmentTextSearch.source_path,
            ResourceSegmentTextSearch.source_repository_key,
            ResourceSegmentTextSearch.source_document_key,
            ResourceSegmentTextSearch.resource_version_ref,
        )
        .where(
            ResourceSegmentTextSearch.generation_id == current.generation_id,
            ResourceSegmentTextSearch.effective_lifecycle_state != "superseded",
        )
        .distinct()
        .order_by(ResourceSegmentTextSearch.source_path)
    ).all()
    sources = []
    for path, repository_key, document_key, resource_version_ref in rows:
        plan = kernel.build_sr2_projection_plan(
            resource_version_refs=(resource_version_ref,)
        )
        first = plan.segments[0] if plan.segments else None
        preview = ""
        if first is not None:
            preview = " ".join(first.body.split())[:240]
        sources.append(
            {
                "source_path": path,
                "source_repository_key": repository_key,
                "source_document_key": document_key,
                "resource_version_ref": str(resource_version_ref),
                "segment_count": len(plan.segments),
                "first_segment_key": first.segment_key if first is not None else None,
                "preview": preview,
            }
        )
    _print(
        {
            "status": "ok",
            "generation_id": str(current.generation_id),
            "source_count": len(sources),
            "sources": sources,
        }
    )
    return 0


def _attempt_payload(
    *,
    plan,
    adapter: GraphitiProjectionAdapter,
    namespace_key: str,
    scope_key: str,
    attempt_salt: str,
) -> dict[str, object]:
    return {
        "generation_id": str(plan.generation_id),
        "profile_id": plan.profile_id,
        "profile_digest": plan.profile_digest,
        "sources": [
            [str(ref), revision]
            for ref, revision in sorted(plan.sources, key=lambda item: str(item[0]))
        ],
        "namespace_key": namespace_key,
        "scope_key": scope_key,
        "adapter_identity": adapter.descriptor.adapter_identity,
        "adapter_version": adapter.descriptor.adapter_version,
        "adapter_config_digest": adapter.descriptor.config_digest,
        "attempt_salt": attempt_salt,
    }


def _trusted_result_payload(snapshot) -> list[dict[str, object]]:
    results = []
    for hit in snapshot.results:
        results.append(
            {
                "provider_hit_id": hit.provider_hit_id,
                "fact": hit.fact,
                "valid_at": hit.valid_at,
                "invalid_at": hit.invalid_at,
                "sources": [
                    {
                        "resource_version_ref": str(source.resource_version_ref),
                        "source_revision_id": source.source_revision_id,
                        "source_path": source.source_path,
                        "source_version": source.source_version,
                        "segment_key": source.segment_key,
                        "source_slice_sha256": source.source_slice_sha256,
                        "source_line_start": source.source_line_start,
                        "source_line_end": source.source_line_end,
                        "content_preview": " ".join(source.body.split())[:320],
                    }
                    for source in hit.sources
                ],
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Real KC -> Graphiti/FalkorDB/Ollama -> validation -> Authority -> "
            "canonical-correlation host qualification. No fake graph backend is used."
        )
    )
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--list-sources", action="store_true")
    parser.add_argument("--source-path", action="append", default=[])
    parser.add_argument("--query")
    parser.add_argument("--namespace", default="kc:graphiti-live")
    parser.add_argument("--scope", default="project:knowledge-core")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--attempt-salt",
        default="primary",
        help=(
            "Stable explicit retry discriminator. Leave at 'primary' for normal exact replay; "
            "change only after inspecting a quarantined/incomplete prior attempt."
        ),
    )
    parser.add_argument("--falkor-host", default=os.environ.get("FALKORDB_HOST", "localhost"))
    parser.add_argument("--falkor-port", type=int, default=int(os.environ.get("FALKORDB_PORT", "6379")))
    parser.add_argument("--ollama-base-url", default="http://localhost:11434/v1")
    parser.add_argument("--llm-model", default="graphiti-qwen35-9b-32k")
    parser.add_argument("--embed-model", default="nomic-embed-text:latest")
    args = parser.parse_args()

    database_url = os.environ.get("KNOWLEDGE_CORE_DATABASE_URL")
    if not database_url:
        raise RuntimeError("KNOWLEDGE_CORE_DATABASE_URL is required")

    engine = create_database_engine(database_url)
    sessions = create_session_factory(engine)
    artifacts = LocalArtifactStore(Path(args.artifact_root).resolve())
    session = sessions()
    kernel = GraphProjectionRetrievalKnowledgeKernel(session, artifact_store=artifacts)
    try:
        if args.list_sources:
            return _list_sources(kernel)
        if not args.source_path:
            parser.error("at least one --source-path is required unless --list-sources is used")
        if not args.query or not args.query.strip():
            parser.error("--query is required unless --list-sources is used")
        if args.limit < 1 or args.limit > 50:
            parser.error("--limit must be between 1 and 50")

        try:
            installed_graphiti = version("graphiti-core")
        except PackageNotFoundError as exc:
            raise RuntimeError(
                "graphiti-core is not installed; install the Knowledge Core graphiti extra first"
            ) from exc
        if installed_graphiti != "0.30.2":
            raise RuntimeError(
                f"live qualification requires graphiti-core 0.30.2; found {installed_graphiti}"
            )

        config = GraphitiLocalConfig(
            falkor_host=args.falkor_host,
            falkor_port=args.falkor_port,
            falkor_username=os.environ.get("FALKORDB_USERNAME"),
            falkor_password=os.environ.get("FALKORDB_PASSWORD"),
            ollama_base_url=args.ollama_base_url,
            ollama_api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
            llm_model=args.llm_model,
            embed_model=args.embed_model,
        )
        adapter = GraphitiProjectionAdapter(config)
        resource_version_refs = kernel.resolve_current_sr2_resource_versions(
            source_paths=tuple(args.source_path)
        )
        plan = kernel.build_sr2_projection_plan(
            resource_version_refs=resource_version_refs
        )
        attempt_id = _stable_uuid(
            _ATTEMPT_NAMESPACE,
            _attempt_payload(
                plan=plan,
                adapter=adapter,
                namespace_key=args.namespace,
                scope_key=args.scope,
                attempt_salt=args.attempt_salt,
            ),
        )

        try:
            execution = asyncio.run(
                kernel.execute_sr2_projection(
                    attempt_id=attempt_id,
                    namespace_key=args.namespace,
                    scope_key=args.scope,
                    resource_version_refs=resource_version_refs,
                    adapter=adapter,
                )
            )
        except ProjectionAdapterExecutionError as exc:
            attempt = kernel.read_projection_attempt(attempt_id)
            _print(
                {
                    "status": "projection-quarantined",
                    "error": str(exc),
                    "attempt_id": str(attempt_id),
                    "disposition": attempt.disposition.value,
                    "warnings": list(attempt.warnings),
                    "errors": list(attempt.errors),
                }
            )
            return 3

        attempt = execution.attempt
        if attempt.disposition is not ProjectionDisposition.SUCCEEDED:
            _print(
                {
                    "status": "projection-not-successful",
                    "attempt_id": str(attempt.attempt_id),
                    "replayed": execution.replayed,
                    "disposition": attempt.disposition.value,
                    "warnings": list(attempt.warnings),
                    "errors": list(attempt.errors),
                }
            )
            return 3

        source_bindings = kernel.read_projection_source_bindings(attempt_id)
        validator = GraphitiProjectionValidator(
            adapter=adapter,
            segments=plan.segments,
            source_bindings=source_bindings,
            namespace_key=args.namespace,
            scope_key=args.scope,
            projection_profile_id=plan.profile_id,
            probe_query=args.query,
        )
        validation_id = _stable_uuid(
            _VALIDATION_NAMESPACE,
            {
                "attempt_id": str(attempt_id),
                "validator_identity": validator.descriptor.validator_identity,
                "validator_version": validator.descriptor.validator_version,
                "ruleset_digest": validator.descriptor.ruleset_digest,
                "config_digest": validator.config_digest,
            },
        )
        validation = kernel.validate_projection_attempt(
            validation_id=validation_id,
            attempt_id=attempt_id,
            validator=validator,
            config_digest=validator.config_digest,
        )
        if validation.outcome is not ProjectionValidationOutcome.VALIDATED:
            _print(
                {
                    "status": "projection-not-validated",
                    "attempt_id": str(attempt_id),
                    "validation_id": str(validation_id),
                    "validation_outcome": validation.outcome.value,
                    "error_code": validation.error_code,
                    "error_detail": validation.error_detail,
                    "source_bindings": [asdict(binding) for binding in source_bindings],
                    "checks": [asdict(check) for check in validation.checks],
                }
            )
            return 4

        authority = _QualificationGraphAuthority(
            namespace_key=args.namespace,
            scope_key=args.scope,
        )
        trusted = asyncio.run(
            kernel.search_validated_projection(
                adapter=adapter,
                authority_evaluator=authority,
                caller_principal_ref=_CALLER,
                namespace_key=args.namespace,
                scope_key=args.scope,
                query=args.query,
                limit=args.limit,
            )
        )
        result = {
            "status": "pass" if trusted.results else "validated-but-no-trusted-results",
            "graphiti_core_version": installed_graphiti,
            "attempt_id": str(attempt_id),
            "attempt_replayed": execution.replayed,
            "projection_disposition": attempt.disposition.value,
            "projection_warning_count": len(attempt.warnings),
            "source_binding_count": len(source_bindings),
            "source_bindings": [asdict(binding) for binding in source_bindings],
            "validation_id": str(validation_id),
            "validation_outcome": validation.outcome.value,
            "validation_checks": [asdict(check) for check in validation.checks],
            "namespace_key": args.namespace,
            "scope_key": args.scope,
            "physical_partition": adapter.partition_key(
                namespace_key=args.namespace,
                scope_key=args.scope,
                projection_profile_id=plan.profile_id,
            ),
            "generation_id": str(plan.generation_id),
            "projected_source_paths": list(args.source_path),
            "projected_segment_count": len(plan.segments),
            "trusted_result_count": len(trusted.results),
            "trusted_results": _trusted_result_payload(trusted),
        }
        _print(result)
        return 0 if trusted.results else 5
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
