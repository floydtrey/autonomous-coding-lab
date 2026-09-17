"""Promoted S09 fixed-operation bridge; no model-supplied authority."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.pydantic_ollama_worker import BoundedFileTools, PydanticWorkerError


def main():
    request = json.load(sys.stdin)
    # The adapter supplies this grant; it is never part of model tool arguments.
    grant = request["grant"]
    files = BoundedFileTools(Path(grant["root"]),
        readable_paths=tuple(grant["readable_paths"]),
        writable_paths=tuple(grant["writable_paths"]))
    args = request["args"]
    if request["operation"] == "acl_read_file" and set(args) == {"path"}:
        return files.read_file(args["path"])
    if request["operation"] == "acl_write_file" and set(args) == {"path", "content", "expected_sha256"}:
        return files.write_file(args["path"], args["content"], args["expected_sha256"])
    raise ValueError("unknown operation or arguments")


if __name__ == "__main__":
    try:
        print(json.dumps({"ok": True, "result": json.loads(main())}, ensure_ascii=True))
    except Exception as exc:
        print(json.dumps({"ok": False, "code": exc.code if isinstance(exc, PydanticWorkerError)
                         else "ACL_BRIDGE_INVALID", "message": str(exc)}, ensure_ascii=True))
        sys.exit(1)
