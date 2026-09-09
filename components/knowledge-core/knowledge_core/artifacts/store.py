from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
from uuid import uuid4


class ArtifactIntegrityError(RuntimeError):
    """Raised when immutable artifact bytes do not match their content address."""


@dataclass(frozen=True)
class ArtifactCommit:
    digest_algo: str
    digest: str
    byte_size: int
    backend: str
    key: str


class LocalArtifactStore:
    """Local immutable SHA-256 content-addressed artifact backend."""

    backend_name = "local-sha256-v1"

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / ".staging").mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key_for_digest(digest: str) -> str:
        return f"sha256/{digest[:2]}/{digest[2:4]}/{digest}"

    def _path_for_key(self, key: str) -> Path:
        parts = key.split("/")
        if (
            len(parts) != 4
            or parts[0] != "sha256"
            or len(parts[1]) != 2
            or len(parts[2]) != 2
            or len(parts[3]) != 64
            or any(ch not in "0123456789abcdef" for ch in parts[3])
            or parts[1] != parts[3][:2]
            or parts[2] != parts[3][2:4]
        ):
            raise ArtifactIntegrityError(f"invalid artifact key: {key}")
        return self.root / parts[0] / parts[1] / parts[2] / parts[3]

    def commit_bytes(self, content: bytes) -> ArtifactCommit:
        if not isinstance(content, bytes):
            raise TypeError("artifact content must be bytes")

        digest = sha256(content).hexdigest()
        key = self._key_for_digest(digest)
        target = self._path_for_key(key)
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            self._verify_path(target, digest)
        else:
            staging = self.root / ".staging" / f"{uuid4().hex}.tmp"
            try:
                with staging.open("xb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(staging, target)
            finally:
                if staging.exists():
                    staging.unlink()
            self._verify_path(target, digest)

        return ArtifactCommit(
            digest_algo="sha256",
            digest=digest,
            byte_size=len(content),
            backend=self.backend_name,
            key=key,
        )

    def _verify_path(self, path: Path, expected_digest: str) -> None:
        actual = sha256(path.read_bytes()).hexdigest()
        if actual != expected_digest:
            raise ArtifactIntegrityError(
                f"artifact digest mismatch: expected {expected_digest}, got {actual}"
            )

    def read_bytes(self, key: str) -> bytes:
        path = self._path_for_key(key)
        if not path.is_file():
            raise FileNotFoundError(path)
        content = path.read_bytes()
        expected = key.rsplit("/", 1)[-1]
        actual = sha256(content).hexdigest()
        if actual != expected:
            raise ArtifactIntegrityError(
                f"artifact digest mismatch: expected {expected}, got {actual}"
            )
        return content

    def verify(self, key: str) -> bool:
        self.read_bytes(key)
        return True
