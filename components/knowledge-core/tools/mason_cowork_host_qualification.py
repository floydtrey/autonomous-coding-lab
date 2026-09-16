from __future__ import annotations

import argparse
from dataclasses import asdict
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


INITIAL_GOAL = """Task 6I intended-host qualification.
Use the enabled Knowledge Core procedural skill and its exact kc_* operation names.
Do not call kc_store during this qualification. Do not use raw KC HTTP, SQL,
filesystem fallback, Graphiti/FalkorDB directly, or Cowork native memories.
This run may inspect KC status/retrieval and, only when the operator explicitly
enables it, create one non-canonical memory candidate through kc_propose_memory.
"""

STATUS_PROMPT = """Use the Knowledge Core skill now. Call literal operation kc_status exactly.
Report the returned text state and graph state. Do not substitute another operation
name and do not use a fallback outside the Knowledge Core bridge.
"""

CONTINUATION_PROMPT = """Continue only from the working-context checkpoint in this new
conversation goal. State the checkpoint digest you received, then call literal
operation kc_status exactly and report the returned text state and graph state.
Do not reconstruct omitted conversation history by guessing.
"""

MEMORY_PROPOSAL_PROMPT = """For this qualification, treat the following sentence as a
self-initiated worker observation rather than a user-directed canonical memory:
"Task 6I host qualification observed successful fresh-conversation continuation."
Use literal operation kc_propose_memory with project "knowledge-core". Do not call
kc_store. Report the returned candidate_id, state, and canonical_state.
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
        help="Optional Cowork model alias; omit to use the project default.",
    )
    parser.add_argument(
        "--skill-id",
        action="append",
        default=[],
        help="Optional Cowork skill ID to activate for each turn; repeat as needed.",
    )
    parser.add_argument(
        "--cowork-base-url",
        default="http://127.0.0.1:26866/api/v1",
        help="Loopback Cowork API base URL ending in /api/v1.",
    )
    parser.add_argument(
        "--context-limit-tokens",
        type=int,
        required=True,
        help="Configured model context limit used only for the qualification policy.",
    )
    parser.add_argument(
        "--compact-trigger-tokens",
        type=int,
        required=True,
        help="Normal wrapper compaction trigger; must be below the context limit.",
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
            "Use only the bounded Knowledge Core bridge for KC operations.",
            "Do not call kc_store during this qualification.",
            "Do not use Cowork native memories as durable KC memory.",
        ),
        evidence_refs=(),
        completed_work=(
            "Created the initial Cowork conversation and requested literal kc_status.",
        ),
        current_state=(
            "Initial Cowork turn completed; continue in a fresh conversation from this checkpoint."
        ),
        blockers=(),
        recent_actions=(
            RecentAction(
                action="Requested literal kc_status through the Knowledge Core skill.",
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
        CoworkClientConfig(base_url=args.cowork_base_url)
    )
    wrapper = MasonCoworkWrapper(
        cowork_client=client,
        project_id=args.project_id,
        model=args.model,
        skill_ids=tuple(args.skill_id),
        context_policy=ContextRotationPolicy(
            context_limit_tokens=args.context_limit_tokens,
            compact_trigger_tokens=args.compact_trigger_tokens,
        ),
    )

    initial_conversation = wrapper.start_conversation(
        goal=INITIAL_GOAL,
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

    mechanical_pass = (
        initial_conversation == rotation.previous_conversation_id
        and rotation.new_conversation_id != rotation.previous_conversation_id
        and wrapper.conversation_id == rotation.new_conversation_id
        and first_turn.status == "completed"
        and second_turn.status == "completed"
        and first_turn.usage is not None
        and second_turn.usage is not None
        and (proposal_turn is None or proposal_turn.status == "completed")
    )

    evidence: dict[str, object] = {
        "contract": "kc-task6i-host-qualification-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cowork_base_url": client.config.base_url,
        "project_id": args.project_id,
        "model": args.model,
        "skill_ids": list(args.skill_id),
        "context_policy": {
            "context_limit_tokens": args.context_limit_tokens,
            "compact_trigger_tokens": args.compact_trigger_tokens,
            "first_turn_triggered_normal_policy": first_rotation_signal,
        },
        "initial_conversation_id": initial_conversation,
        "continuation_conversation_id": rotation.new_conversation_id,
        "checkpoint_digest": checkpoint.checkpoint_digest,
        "initial_status_turn": _turn_payload(first_turn),
        "initial_status_output_sha256": first_sha,
        "continuation_status_turn": _turn_payload(second_turn),
        "continuation_status_output_sha256": second_sha,
        "memory_proposal_exercised": bool(args.exercise_memory_proposal),
        "memory_proposal_turn": (
            _turn_payload(proposal_turn) if proposal_turn is not None else None
        ),
        "memory_proposal_output_sha256": proposal_sha,
        "mechanical_pass": mechanical_pass,
        "semantic_review_required": True,
        "semantic_review_checks": [
            "Initial turn actually invoked literal kc_status through the enabled Knowledge Core skill.",
            "Continuation turn received the checkpoint and again used literal kc_status without guessing omitted history.",
            "If memory proposal was exercised, Mason used kc_propose_memory rather than kc_store and reported non-canonical candidate state.",
            "No Cowork native memory or raw KC/SQL/filesystem fallback was used.",
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
    return 0 if evidence["mechanical_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
