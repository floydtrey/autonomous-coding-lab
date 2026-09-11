from pathlib import Path

app_path = Path("components/worker-lab/worker_lab/application_service.py")
text = app_path.read_text(encoding="utf-8")

imports = '''from .integration_v3 import INVOCATION_SCHEMA_V3, InvocationRecordV3, ResultRecordV3
from .service_runtime_v3 import (
    WorkspaceDispatchRunner,
    authorize_invocation as authorize_invocation_v3,
    cancel_invocation as cancel_invocation_v3,
    dispatch_invocation as dispatch_invocation_v3,
    load_invocation_record,
    load_result_record,
    prepare_invocation as prepare_invocation_v3,
    recover_invocation as recover_invocation_v3,
    reject_invocation as reject_invocation_v3,
    review_candidate as review_candidate_v3,
)
'''
if "from .service_runtime_v3 import (" not in text:
    anchor = "\n\nHEALTH_SCHEMA = "
    if anchor not in text:
        raise SystemExit("application service import anchor differs")
    text = text.replace(anchor, "\n" + imports + anchor, 1)

text = text.replace(
    "    invocation: InvocationRecord\n    attempt: AttemptRecord\n",
    "    invocation: InvocationRecord | InvocationRecordV3\n    attempt: AttemptRecord\n",
    1,
)

old = '''        workspace_write_adapter: WorkspaceWriteAdapter | None = None,
        sealed_test_executor: SealedTestExecutor | None = None,
    ) -> None:
'''
new = '''        workspace_write_adapter: WorkspaceWriteAdapter | None = None,
        sealed_test_executor: SealedTestExecutor | None = None,
        workspace_dispatch_runner: WorkspaceDispatchRunner | None = None,
    ) -> None:
'''
if old not in text:
    raise SystemExit("constructor signature anchor differs")
text = text.replace(old, new, 1)

old = '''        if sealed_test_executor is not None and not callable(sealed_test_executor):
            raise LabValidationError("SERVICE_COMMAND_INVALID", "sealed test executor must be callable")
        if custody_backend is not None and (
'''
new = '''        if sealed_test_executor is not None and not callable(sealed_test_executor):
            raise LabValidationError("SERVICE_COMMAND_INVALID", "sealed test executor must be callable")
        if workspace_dispatch_runner is not None and not callable(workspace_dispatch_runner):
            raise LabValidationError("SERVICE_COMMAND_INVALID", "V3 workspace dispatch runner must be callable")
        if custody_backend is not None and (
'''
if old not in text:
    raise SystemExit("constructor validation anchor differs")
text = text.replace(old, new, 1)

old = '''        self._workspace_write_adapter = workspace_write_adapter or _execute_workspace_write_adapter
        self._sealed_test_executor = sealed_test_executor or _run_sealed_test
'''
new = '''        self._workspace_write_adapter = workspace_write_adapter or _execute_workspace_write_adapter
        self._sealed_test_executor = sealed_test_executor or _run_sealed_test
        self._workspace_dispatch_runner = workspace_dispatch_runner
'''
if old not in text:
    raise SystemExit("constructor assignment anchor differs")
text = text.replace(old, new, 1)

for name in (
    "review_candidate",
    "prepare_invocation",
    "authorize_invocation",
    "reject_invocation",
    "cancel_invocation",
    "dispatch_invocation",
    "recover_invocation",
):
    old = f"    def {name}(\n"
    new = f"    def _legacy_{name}(\n"
    if old not in text:
        raise SystemExit(f"legacy method anchor missing: {name}")
    text = text.replace(old, new, 1)

current_methods = r'''    def review_candidate(self, attempt_id: str) -> CandidateReviewDTO:
        attempt_id = _identity(attempt_id)
        self._require_present_data_root()
        timeline = self.show_attempt_timeline(attempt_id)
        attempt = AttemptRecord.from_mapping(timeline.attempt.record)
        if attempt.candidate_digest is None:
            raise LabValidationError(
                "SERVICE_CANDIDATE_MISSING", "attempt has no retained candidate identity"
            )
        if len(timeline.invocations) != 1 or len(timeline.results) != 1 or len(timeline.custody) != 1:
            raise LabValidationError(
                "SERVICE_CANDIDATE_IDENTITY_INVALID",
                "candidate requires exactly one invocation, result, and custody record",
            )
        if timeline.invocations[0].record.get("schema_version") != INVOCATION_SCHEMA_V3:
            return self._legacy_review_candidate(attempt_id)
        invocation = InvocationRecordV3.from_mapping(timeline.invocations[0].record)
        result = ResultRecordV3.from_mapping(timeline.results[0].record)
        custody = ProcessCustodyRecord.from_mapping(timeline.custody[0].record)
        reviewed = review_candidate_v3(
            self.data_root / "state",
            attempt=attempt,
            invocation=invocation,
            result=result,
            custody=custody,
        )
        evidence = tuple(
            item for item in timeline.evidence
            if verify_evidence(self.data_root, item.summary.identity).attempt_id == attempt_id
        )
        return CandidateReviewDTO(
            WORKSPACE_WRITE_CANDIDATE_REVIEW_SCHEMA,
            attempt.candidate_digest,
            timeline.attempt,
            timeline.invocations[0],
            timeline.results[0],
            timeline.custody[0],
            reviewed.retained_framework_candidate_digest,
            reviewed.changed_paths,
            tuple(stage.to_dict() for stage in reviewed.validation_stages),
            evidence,
            timeline.failures,
            reviewed.first_failure_boundary,
        )

    def prepare_invocation(
        self,
        attempt_id: str,
        workspace_root: Path,
        prompt: str,
        *,
        logical_target_id: str,
        provider_binding_id: str,
        provider_binding_digest: str,
    ) -> OperationResultDTO:
        attempt_id = _identity(attempt_id)
        workspace_root = _absolute_path_argument(workspace_root, "workspace root")
        self._require_present_data_root()
        invocation = prepare_invocation_v3(
            self.data_root,
            attempt_id=attempt_id,
            workspace_root=workspace_root,
            prompt=prompt,
            logical_target_id=logical_target_id,
            provider_binding_id=provider_binding_id,
            provider_binding_digest=provider_binding_digest,
        )
        return _operation_result(
            "prepare-invocation",
            "invocation",
            invocation.invocation_id,
            invocation,
        )

    def authorize_invocation(
        self,
        invocation_id: str,
        expected_identity_digest: str,
        controller_identity: str,
    ) -> OperationResultDTO:
        invocation_id = _identity(invocation_id)
        self._require_present_data_root()
        invocation = authorize_invocation_v3(
            self.data_root,
            invocation_id=invocation_id,
            expected_identity_digest=expected_identity_digest,
            controller_identity=controller_identity,
            authorized_at=self._clock(),
        )
        return _operation_result(
            "authorize-invocation", "invocation", invocation_id, invocation
        )

    def reject_invocation(
        self,
        invocation_id: str,
        expected_identity_digest: str,
    ) -> OperationResultDTO:
        invocation_id = _identity(invocation_id)
        self._require_present_data_root()
        invocation = reject_invocation_v3(
            self.data_root,
            invocation_id=invocation_id,
            expected_identity_digest=expected_identity_digest,
        )
        return _operation_result(
            "reject-invocation", "invocation", invocation_id, invocation
        )

    def cancel_invocation(
        self,
        invocation_id: str,
        expected_identity_digest: str,
        controller_identity: str,
    ) -> OperationResultDTO:
        invocation_id = _identity(invocation_id)
        self._require_present_data_root()
        invocation = cancel_invocation_v3(
            self.data_root,
            invocation_id=invocation_id,
            expected_identity_digest=expected_identity_digest,
            controller_identity=controller_identity,
        )
        return _operation_result(
            "cancel-invocation", "invocation", invocation_id, invocation
        )

    def dispatch_invocation(
        self,
        invocation_id: str,
        expected_identity_digest: str,
        controller_identity: str,
        workspace_root: Path,
    ) -> OperationResultDTO:
        invocation_id = _identity(invocation_id)
        workspace_root = _absolute_path_argument(workspace_root, "workspace root")
        self._require_present_data_root()
        attempt = dispatch_invocation_v3(
            self.data_root,
            invocation_id=invocation_id,
            expected_identity_digest=expected_identity_digest,
            controller_identity=controller_identity,
            workspace_root=workspace_root,
            clock=self._clock,
            workspace_dispatch_runner=self._workspace_dispatch_runner,
            sealed_test_executor=self._sealed_test_executor,
        )
        return _operation_result(
            "dispatch-invocation", "attempt", attempt.attempt_id, attempt
        )

    def recover_invocation(
        self,
        invocation_id: str,
        expected_identity_digest: str,
        controller_identity: str,
        workspace_root: Path,
    ) -> RecoveryResultDTO:
        invocation_id = _identity(invocation_id)
        workspace_root = _absolute_path_argument(workspace_root, "workspace root")
        self._require_present_data_root()
        recovered = recover_invocation_v3(
            self.data_root,
            invocation_id=invocation_id,
            expected_identity_digest=expected_identity_digest,
            controller_identity=controller_identity,
            workspace_root=workspace_root,
            clock=self._clock,
            custody_backend=self._custody_backend,
        )
        return RecoveryResultDTO(
            recovered.controller_identity,
            recovered.invocation,
            recovered.attempt,
            recovered.custody,
            recovered.workspace,
        )

'''
anchor = "    def _legacy_review_candidate(\n"
if anchor not in text:
    raise SystemExit("current method insertion anchor missing")
text = text.replace(anchor, current_methods + anchor, 1)

old = '"invocations": _CollectionSpec("state", "invocations", InvocationRecord.from_mapping, lambda item: item.invocation_id, _state("state")),'
new = '"invocations": _CollectionSpec("state", "invocations", load_invocation_record, lambda item: item.invocation_id, _state("state")),'
if old not in text:
    raise SystemExit("invocation collection anchor differs")
text = text.replace(old, new, 1)
old = '"results": _CollectionSpec("state", "results", ResultRecord.from_mapping, lambda item: item.invocation_id, _state("process_outcome")),'
new = '"results": _CollectionSpec("state", "results", load_result_record, lambda item: item.invocation_id, _state("process_outcome")),'
if old not in text:
    raise SystemExit("result collection anchor differs")
text = text.replace(old, new, 1)
old = "record.identity_digest() if isinstance(record, InvocationRecord) else None,"
new = "record.identity_digest() if isinstance(record, (InvocationRecord, InvocationRecordV3)) else None,"
if old not in text:
    raise SystemExit("operation result identity anchor differs")
text = text.replace(old, new, 1)

app_path.write_text(text, encoding="utf-8")

controller_path = Path("components/worker-lab/worker_lab/controller_task_packet.py")
text = controller_path.read_text(encoding="utf-8")
old = "    def prepare_invocation(self, attempt_id: str, workspace_root, prompt: str): ..."
new = '''    def prepare_invocation(
        self, attempt_id: str, workspace_root, prompt: str, *,
        logical_target_id: str, provider_binding_id: str, provider_binding_digest: str,
    ): ...'''
if old not in text:
    raise SystemExit("controller protocol anchor differs")
text = text.replace(old, new, 1)

old = '''def prepare_controller_task_invocation(
    service: ControllerTaskService, *, attempt_id: str, workspace_root,
    controller_identity: str, user_request: str, kc_search_response: Mapping[str, Any],
    result_indexes: Sequence[int] = (0,),
) -> PreparedControllerInvocation:
'''
new = '''def prepare_controller_task_invocation(
    service: ControllerTaskService, *, attempt_id: str, workspace_root,
    logical_target_id: str, provider_binding_id: str, provider_binding_digest: str,
    controller_identity: str, user_request: str, kc_search_response: Mapping[str, Any],
    result_indexes: Sequence[int] = (0,),
) -> PreparedControllerInvocation:
'''
if old not in text:
    raise SystemExit("controller prepare signature anchor differs")
text = text.replace(old, new, 1)
old = '    invocation = service.prepare_invocation(attempt_id, workspace_root, packet.to_json())\n'
new = '''    invocation = service.prepare_invocation(
        attempt_id, workspace_root, packet.to_json(),
        logical_target_id=logical_target_id,
        provider_binding_id=provider_binding_id,
        provider_binding_digest=provider_binding_digest,
    )
'''
if old not in text:
    raise SystemExit("controller service call anchor differs")
text = text.replace(old, new, 1)
controller_path.write_text(text, encoding="utf-8")

cli_path = Path("components/worker-lab/worker_lab/cli.py")
text = cli_path.read_text(encoding="utf-8")
old = '''    command.add_argument("--workspace-root", required=True, type=Path)
    command.add_argument("--prompt-file", required=True, type=Path)
    command.set_defaults(handler=_service_prepare_invocation)
'''
new = '''    command.add_argument("--workspace-root", required=True, type=Path)
    command.add_argument("--prompt-file", required=True, type=Path)
    command.add_argument("--logical-target-id", required=True)
    command.add_argument("--provider-binding-id", required=True)
    command.add_argument("--provider-binding-digest", required=True)
    command.set_defaults(handler=_service_prepare_invocation)
'''
if old not in text:
    raise SystemExit("CLI parser anchor differs")
text = text.replace(old, new, 1)
old = '''    return _service(args).prepare_invocation(
        args.attempt_id,
        args.workspace_root,
        prompt,
    ).to_json()
'''
new = '''    return _service(args).prepare_invocation(
        args.attempt_id,
        args.workspace_root,
        prompt,
        logical_target_id=args.logical_target_id,
        provider_binding_id=args.provider_binding_id,
        provider_binding_digest=args.provider_binding_digest,
    ).to_json()
'''
if old not in text:
    raise SystemExit("CLI prepare handler anchor differs")
text = text.replace(old, new, 1)
cli_path.write_text(text, encoding="utf-8")

test_path = Path("components/worker-lab/tests/test_controller_task_packet.py")
text = test_path.read_text(encoding="utf-8")
old = '''        def prepare_invocation(self, attempt_id, workspace_root, prompt):
            assert attempt_id == attempt.attempt_id
            assert str(workspace_root) == "workspace-root"
            captured["prompt"] = prompt
            return FakeInvocation(prompt)
'''
new = '''        def prepare_invocation(
            self, attempt_id, workspace_root, prompt, *,
            logical_target_id, provider_binding_id, provider_binding_digest,
        ):
            assert attempt_id == attempt.attempt_id
            assert str(workspace_root) == "workspace-root"
            assert logical_target_id == "target:record-model"
            assert provider_binding_id == "BINDING-0001"
            assert provider_binding_digest == "sha256:" + "a" * 64
            captured["prompt"] = prompt
            return FakeInvocation(prompt)
'''
if old not in text:
    raise SystemExit("controller test fake anchor differs")
text = text.replace(old, new, 1)
old = '''        attempt_id=attempt.attempt_id,
        workspace_root="workspace-root",
        controller_identity="trusted-controller",
'''
new = '''        attempt_id=attempt.attempt_id,
        workspace_root="workspace-root",
        logical_target_id="target:record-model",
        provider_binding_id="BINDING-0001",
        provider_binding_digest="sha256:" + "a" * 64,
        controller_identity="trusted-controller",
'''
if old not in text:
    raise SystemExit("controller test invocation anchor differs")
text = text.replace(old, new, 1)
test_path.write_text(text, encoding="utf-8")
