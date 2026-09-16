from __future__ import annotations

import argparse
import json
import sys

import mason_kc_bridge


CLI_CONTRACT = "mason-kc-cli-v1"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic project-local CLI for the bounded Mason -> Knowledge Core bridge."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Read Knowledge Core readiness/status.")

    search = subparsers.add_parser("search", help="Search governed Knowledge Core evidence.")
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=10)

    source = subparsers.add_parser("get-source", help="Read exact canonical source evidence.")
    source.add_argument("--ref", required=True, dest="resource_version_ref")

    propose = subparsers.add_parser(
        "propose-memory",
        help="Propose a non-canonical autonomous memory candidate.",
    )
    propose.add_argument("--project", required=True)
    propose.add_argument("--content", required=True)
    propose.add_argument("--source-event-time", default=None)
    propose.add_argument("--idempotency-key", default=None)

    store = subparsers.add_parser(
        "store",
        help="Store an explicitly authorized canonical user note.",
    )
    store.add_argument("--project", required=True)
    store.add_argument("--content", required=True)
    store.add_argument("--source-id", default=None)
    store.add_argument("--source-event-time", default=None)
    store.add_argument("--idempotency-key", default=None)

    return parser


def _operation_and_payload(args: argparse.Namespace) -> tuple[str, dict[str, object]]:
    if args.command == "status":
        return "kc_status", {}
    if args.command == "search":
        return "kc_search", {"query": args.query, "limit": args.limit}
    if args.command == "get-source":
        return "kc_get_source", {"resource_version_ref": args.resource_version_ref}

    payload: dict[str, object] = {
        "project": args.project,
        "content": args.content,
    }
    for name in ("source_event_time", "idempotency_key"):
        value = getattr(args, name, None)
        if value is not None:
            payload[name] = value

    if args.command == "propose-memory":
        return "kc_propose_memory", payload

    source_id = getattr(args, "source_id", None)
    if source_id is not None:
        payload["source_id"] = source_id
    return "kc_store", payload


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    operation, payload = _operation_and_payload(args)
    try:
        result = mason_kc_bridge.execute(operation, payload)
    except (mason_kc_bridge.BridgeError, TypeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "contract": CLI_CONTRACT,
                    "operation": operation,
                    "error": str(exc),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "contract": CLI_CONTRACT,
                "operation": operation,
                "result": result,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
