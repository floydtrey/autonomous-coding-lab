from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

from knowledge_core.integrations.context_compaction import (
    ContextReference,
    ContextReferenceKind,
    RecentAction,
    RecentActionOutcome,
    WorkingContextCheckpoint,
)
from knowledge_core.integrations.cowork_wrapper import (
    ContextRotationPolicy,
    CoworkClientConfig,
    CoworkTurnResult,
    LocalCoworkClient,
    MasonCoworkWrapper,
)


COWORK_CONTRACT_VERSION = "v0.26.9.14.2"
KC_CLI_CONTRACT = "mason-kc-cli-v1"
_FORBIDDEN_FALLBACK_MARKERS = (
    "http://127.0.0.1:8765",
    "/v1/kc/",
    "mason_kc_bridge.py",
    "X-Knowledge-Key",
)

INITIAL_CONTEXT = """Task 6I intended-host qualification.
Use only the enabled Knowledge Core procedural skill and its installed deterministic CLI.
Do not call kc_store during this qualification. Do not write helper Python, call the bridge
directly, use raw KC HTTP/SQL/filesystem fallback, query Graphiti/FalkorDB directly, or use
Cowork native memories. If a KC CLI command fails, report that failure and stop that KC attempt.
"""

STATUS_PROMPT = f"""Use the Knowledge Core skill now. Run its exact status CLI command.
Report the returned text state and graph state. In your final report include the CLI contract
value `{KC_CLI_CONTRACT}` and operation `kc_status` exactly as returned. Do not write helper
code, inspect the bridge, call raw HTTP, or use any fallback outside the Knowledge Core CLI.
"""

CONTINUATION_PROMPT = f"""Continue only from the working-context checkpoint supplied in this
fresh conversation's first turn. State the checkpoint digest you received, then use the
Knowledge Core skill and run its exact status CLI command. Report the returned text state and
graph state and include CLI contract `{KC_CLI_CONTRACT}` and operation `kc_status` exactly.
Do not reconstruct omitted history, write helper code, inspect the bridge, call raw HTTP, or
use another fallback.
"""

MEMORY_PROPOSAL_PROMPT = f"""For this qualification, treat the following sentence as a
self-initiated worker observation rather than a user-directed canonical memory:
"Task 6I host qualification observed successful fresh-conversation continuation."
Use the Knowledge Core skill's exact propose-memory CLI command with project "knowledge-core".
Do not call kc_store. Report candidate_id, state, canonical_state, CLI contract
`{KC_CLI_CONTRACT}`, and operation `kc_propose_memory` exactly. Do not write helper code,
inspect the bridge, or call raw HTTP.
"""


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bounded intended-host qualification for KC Task 6I."
    )
    parser.add_argument(
        "--project-id",
        required=True,
        help="Existing Cowork project ID with the Knowledge Core skill enabled.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional Cowork model alias; omit to use the project/account default.",
    )
    parser.add_argument(
        "--cowork-base-url",
        default="http://127.0.0.1:26866/api/v1",
        help="Loopback Cowork API base URL ending in /api/v1.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=600.0,
        help="Per-request Cowork HTTP timeout. Default: 600 seconds.",
    )
    parser.add_argument(
        "--context-limit-tokens",
        type=int,
        required=True,
        help=(
            "Configured model context limit recorded with evidence. Cowork "
            f"{COWORK_CONTRACT_VERSION} does not expose response token usage."
        ),
    )
    parser.add_argument(
        "--compact-trigger-tokens",
        type=int,
        required=True,
        help=(
            "Intended automatic compaction trigger recorded with evidence. "
            "Token-triggered rotation is not qualified by this host test because "
            f"Cowork {COWORK_CONTRACT_VERSION} does not expose usage."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="task6i-host-evidence",
        help="Directory for non-secret qualification evidence files.",
    )
    parser.add_argument(
        "--exercise-memory-proposal",
        action="store_true",
        help=(
            "Explicitly opt in to creating one non-canonical pending KC memory "
            "candidate during the host test."
        ),
    )
    return parser.parse_args(argv)


def _write_text(path: Path, text: str) -> str:
    path.write_text(text, encoding="utf-8")
    return sha256(text.encode("utf-8")).hexdigest()


def _turn_payload(turn: CoworkTurnResult) -> dict[str, object]:
    return {
        "response_id": turn.response_id,
        "conversation_id": turn.conversation_id,
        "status": turn.status,
        "model": turn.model,
        "output_text": turn.output_text,
        "usage": (
            {
                "input_tokens": turn.usage.input_tokens,
                "output_tokens": turn.usage.output_tokens,
                "observed_context_tokens": turn.usage.observed_context_tokens,
            }
            if turn.usage is not None
            else None
        ),
    }


def _cli_semantic_gate(turn: CoworkTurnResult, operation: str) -> dict[str, object]:
    text = turn.output_text
    forbidden = [marker for marker in _FORBIDDEN_FALLBACK_MARKERS if marker in text]
    contract_present = KC_CLI_CONTRACT in text
    operation_present = operation in text
    passed = (
        turn.status == "completed"
        and bool(text.strip())
        and contract_present
        and operation_present
        and not forbidden
    )
    return {
        "passed": passed,
        "contract_present": contract_present,
        "operation_present": operation_present,
        "forbidden_fallback_markers": forbidden,
    }


def _checkpoint(
    *,
    first_turn: CoworkTurnResult,
    first_turn_ref: str,
    first_turn_sha256: str,
) -> WorkingContextCheckpoint:
    output_ref = ContextReference(
        kind=ContextReferenceKind.TOOL_OUTPUT,
        ref=first_turn_ref,
        sha256_hex=first_turn_sha256,
    )
    return WorkingContextCheckpoint(
        objective="Complete Task 6I intended-host wrapper qualification without canonical writes.",
        immutable_constraints=(
            "Use only the installed Knowledge Core CLI for KC operations.",
            "Do not call kc_store during this qualification.",
            "Do not bypass the CLI with raw KC HTTP, bridge inspection, or filesystem fallback.",
            "Do not use Cowork native memories as durable KC memory.",
        ),
        evidence_refs=(),
        completed_work=(
            "Created the initial Cowork conversation and requested KC status through the installed CLI.",
        ),
        current_state=(
            "Initial Cowork turn completed; continue in a fresh conversation from this checkpoint."
        ),
        blockers=(),
        recent_actions=(
            RecentAction(
                action="Requested kc_status through the Knowledge Core skill CLI.",
                outcome=(
                    RecentActionOutcome.SUCCEEDED
                    if first_turn.status == "completed"
                    else RecentActionOutcome.FAILED
                ),
                refs=(output_ref,),
            ),
        ),
        source_output_refs=(output_ref,),
    )


def run(args: argparse.Namespace) -> dict[str, object]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    client = LocalCoworkClient(
        CoworkClientConfig(
            base_url=args.cowork_base_url,
            timeout_seconds=args.timeout_seconds,
        )
    )
    wrapper = MasonCoworkWrapper(
        cowork_client=client,
        project_id=args.project_id,
        model=args.model,
        context_policy=ContextRotationPolicy(
            context_limit_tokens=args.context_limit_tokens,
            compact_trigger_tokens=args.compact_trigger_tokens,
        ),
    )

    initial_conversation = wrapper.start_conversation(
        initial_context=INITIAL_CONTEXT,
        title="KC Task 6I host qualification - initial",
    )
    first_turn = wrapper.send_turn(STATUS_PROMPT)
    first_path = output_dir / "01-initial-status-output.txt"
    first_sha = _write_text(first_path, first_turn.output_text)

    checkpoint = _checkpoint(
        first_turn=first_turn,
        first_turn_ref=first_path.as_uri(),
        first_turn_sha256=first_sha,
    )
    rotation = wrapper.rotate_for_checkpoint(
        checkpoint,
        title="KC Task 6I host qualification - continuation",
    )

    second_turn = wrapper.send_turn(CONTINUATION_PROMPT)
    second_path = output_dir / "02-continuation-status-output.txt"
    second_sha = _write_text(second_path, second_turn.output_text)

    proposal_turn = None
    proposal_sha = None
    if args.exercise_memory_proposal:
        proposal_turn = wrapper.send_turn(MEMORY_PROPOSAL_PROMPT)
        proposal_path = output_dir / "03-memory-proposal-output.txt"
        proposal_sha = _write_text(proposal_path, proposal_turn.output_text)

    first_rotation_signal = None
    if first_turn.usage is not None:
        first_rotation_signal = wrapper.needs_context_rotation(first_turn)

    checkpoint_rotation_pass = (
        initial_conversation == rotation.previous_conversation_id
        and rotation.new_conversation_id != rotation.previous_conversation_id
        and wrapper.conversation_id == rotation.new_conversation_id
    )
    transport_pass = (
        first_turn.status == "completed"
        and second_turn.status == "completed"
        and bool(first_turn.output_text.strip())
        and bool(second_turn.output_text.strip())
        and (
            proposal_turn is None
            or (
                proposal_turn.status == "completed"
                and bool(proposal_turn.output_text.strip())
            )
        )
    )
    mechanical_pass = checkpoint_rotation_pass and transport_pass

    first_cli_gate = _cli_semantic_gate(first_turn, "kc_status")
    second_cli_gate = _cli_semantic_gate(second_turn, "kc_status")
    kc_cli_path_pass = bool(first_cli_gate["passed"] and second_cli_gate["passed"])

    proposal_cli_gate = None
    memory_boundary_pass = True
    if proposal_turn is not None:
        proposal_cli_gate = _cli_semantic_gate(proposal_turn, "kc_propose_memory")
        proposal_text = proposal_turn.output_text
        memory_boundary_pass = bool(
            proposal_cli_gate["passed"]
            and "pending" in proposal_text
            and "not_stored" in proposal_text
        )

    automated_semantic_gate_pass = kc_cli_path_pass and memory_boundary_pass
    qualification_candidate_pass = mechanical_pass and automated_semantic_gate_pass

    usage_state = (
        "available"
        if first_turn.usage is not None and second_turn.usage is not None
        else f"unavailable-from-cowork-responses-{COWORK_CONTRACT_VERSION}"
    )

    evidence: dict[str, object] = {
        "contract": "kc-task6i-host-qualification-v3",
        "cowork_contract_version": COWORK_CONTRACT_VERSION,
        "kc_cli_contract": KC_CLI_CONTRACT,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cowork_base_url": client.config.base_url,
        "cowork_timeout_seconds": client.config.timeout_seconds,
        "project_id": args.project_id,
        "model": args.model,
        "context_policy": {
            "context_limit_tokens": args.context_limit_tokens,
            "compact_trigger_tokens": args.compact_trigger_tokens,
            "usage_state": usage_state,
            "first_turn_triggered_normal_policy": first_rotation_signal,
            "automatic_token_rotation_qualified": False,
            "automatic_token_rotation_reason": (
                f"Cowork {COWORK_CONTRACT_VERSION} non-streaming Response "
                "does not expose token usage; external telemetry remains required."
            ),
        },
        "initial_conversation_id": initial_conversation,
        "continuation_conversation_id": rotation.new_conversation_id,
        "checkpoint_digest": checkpoint.checkpoint_digest,
        "checkpoint_injection": "first-input-of-fresh-conversation",
        "initial_status_turn": _turn_payload(first_turn),
        "initial_status_output_sha256": first_sha,
        "continuation_status_turn": _turn_payload(second_turn),
        "continuation_status_output_sha256": second_sha,
        "memory_proposal_exercised": bool(args.exercise_memory_proposal),
        "memory_proposal_turn": (
            _turn_payload(proposal_turn) if proposal_turn is not None else None
        ),
        "memory_proposal_output_sha256": proposal_sha,
        "transport_pass": transport_pass,
        "checkpoint_rotation_pass": checkpoint_rotation_pass,
        "mechanical_pass": mechanical_pass,
        "initial_cli_gate": first_cli_gate,
        "continuation_cli_gate": second_cli_gate,
        "proposal_cli_gate": proposal_cli_gate,
        "kc_cli_path_pass": kc_cli_path_pass,
        "memory_boundary_pass": memory_boundary_pass,
        "automated_semantic_gate_pass": automated_semantic_gate_pass,
        "qualification_candidate_pass": qualification_candidate_pass,
        "semantic_review_required": True,
        "semantic_review_checks": [
            "Initial and continuation turns actually used the installed Knowledge Core CLI rather than merely repeating its contract marker.",
            "Fresh continuation turn received the rendered 6H checkpoint and did not guess omitted history.",
            "If memory proposal was exercised, Mason used the CLI proposal path rather than kc_store and reported non-canonical pending state.",
            "No Cowork native memory or raw KC/SQL/filesystem/bridge-inspection fallback was used.",
            "Automatic token-triggered rotation is not claimed by this qualification because the pinned Cowork response contract exposes no token usage.",
        ],
    }

    evidence_path = output_dir / "task6i-host-qualification.json"
    evidence_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    evidence["evidence_path"] = str(evidence_path)
    return evidence


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        evidence = run(args)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"{exc.__class__.__name__}: {exc}",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps({"ok": True, **evidence}, indent=2, ensure_ascii=False))
    return 0 if evidence["qualification_candidate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
