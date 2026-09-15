from __future__ import annotations

import json
import sys

from knowledge_core.integrations.mindshub import (
    MasonKnowledgeCoreBridge,
    MasonKnowledgeCoreBridgeError,
    MasonKnowledgeCoreConfig,
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "usage: mason_kc_bridge.py <kc_status|kc_search|kc_get_source|kc_store>",
                }
            ),
            file=sys.stderr,
        )
        return 2

    operation = args[0]
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            raise MasonKnowledgeCoreBridgeError("bridge input must be a JSON object")
        bridge = MasonKnowledgeCoreBridge(MasonKnowledgeCoreConfig.from_env())
        result = bridge.execute(operation, payload)
    except (json.JSONDecodeError, MasonKnowledgeCoreBridgeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, "operation": operation, "result": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
