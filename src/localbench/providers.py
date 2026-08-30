from __future__ import annotations

import json
import os
import hashlib
import secrets
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .models import ProviderResponse


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class Provider(ABC):
    def __init__(self, provider_id: str, settings: dict[str, Any]):
        self.provider_id = provider_id
        self.settings = settings
        self.base_url = settings.get("base_url", "").rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json", "Accept": "application/json"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout_seconds: float = 30,
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self._url(path), data=body, headers=self._headers(), method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                response_body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")[:8000]
            raise ProviderError(
                f"HTTP {exc.code} from {self.provider_id}",
                status_code=exc.code,
                body=response_body,
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"cannot reach {self.provider_id}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ProviderError(f"request to {self.provider_id} timed out") from exc
        try:
            value = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                f"invalid JSON from {self.provider_id}", body=response_body[:8000]
            ) from exc
        if not isinstance(value, dict):
            raise ProviderError(f"unexpected JSON shape from {self.provider_id}")
        return value

    @abstractmethod
    def model_metadata(self, model: str, timeout_seconds: float) -> dict[str, Any] | None:
        raise NotImplementedError

    def runtime_metadata(self, timeout_seconds: float) -> dict[str, Any] | None:
        return None

    @abstractmethod
    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        options: dict[str, Any],
        timeout_seconds: float,
    ) -> ProviderResponse:
        raise NotImplementedError

    def unload_model(self, model: str, timeout_seconds: float) -> dict[str, Any] | None:
        return None


class OllamaProvider(Provider):
    def runtime_metadata(self, timeout_seconds: float) -> dict[str, Any] | None:
        return self._request("GET", "/api/version", timeout_seconds=timeout_seconds)

    def model_metadata(self, model: str, timeout_seconds: float) -> dict[str, Any] | None:
        response = self._request("GET", "/api/tags", timeout_seconds=timeout_seconds)
        candidates = response.get("models", [])
        requested_base = model.split(":", 1)[0]
        for candidate in candidates:
            candidate_name = candidate.get("model") or candidate.get("name")
            if candidate_name == model:
                return candidate
        if ":" not in model:
            for candidate in candidates:
                candidate_name = candidate.get("model") or candidate.get("name", "")
                if candidate_name in {model, f"{model}:latest"} or candidate_name.split(":", 1)[0] == requested_base:
                    return candidate
        return None

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        options: dict[str, Any],
        timeout_seconds: float,
    ) -> ProviderResponse:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        ollama_options = dict(options)
        keep_alive = ollama_options.pop("keep_alive", self.settings.get("keep_alive"))
        if ollama_options:
            payload["options"] = ollama_options
        if keep_alive is not None:
            payload["keep_alive"] = keep_alive
        raw = self._request(
            "POST", "/api/chat", payload=payload, timeout_seconds=timeout_seconds
        )
        message = raw.get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise ProviderError("Ollama response did not contain message.content")

        def seconds(name: str) -> float | None:
            value = raw.get(name)
            return value / 1_000_000_000 if isinstance(value, (int, float)) else None

        prompt_tokens = raw.get("prompt_eval_count")
        output_tokens = raw.get("eval_count")
        return ProviderResponse(
            content=content,
            raw=raw,
            prompt_tokens=prompt_tokens if isinstance(prompt_tokens, int) else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) else None,
            total_tokens=(prompt_tokens + output_tokens)
            if isinstance(prompt_tokens, int) and isinstance(output_tokens, int)
            else None,
            provider_total_seconds=seconds("total_duration"),
            load_seconds=seconds("load_duration"),
            prompt_eval_seconds=seconds("prompt_eval_duration"),
            generation_seconds=seconds("eval_duration"),
            finish_reason=raw.get("done_reason"),
        )

    def unload_model(self, model: str, timeout_seconds: float) -> dict[str, Any] | None:
        return self._request(
            "POST",
            "/api/chat",
            payload={"model": model, "messages": [], "stream": False, "keep_alive": 0},
            timeout_seconds=timeout_seconds,
        )


class OpenAICompatibleProvider(Provider):
    def _headers(self) -> dict[str, str]:
        headers = super()._headers()
        env_name = self.settings.get("api_key_env")
        if env_name:
            value = os.environ.get(env_name)
            if not value:
                raise ProviderError(f"required environment variable {env_name!r} is not set")
            headers["Authorization"] = f"Bearer {value}"
        elif self.settings.get("api_key"):
            headers["Authorization"] = f"Bearer {self.settings['api_key']}"
        return headers

    def model_metadata(self, model: str, timeout_seconds: float) -> dict[str, Any] | None:
        response = self._request("GET", "/models", timeout_seconds=timeout_seconds)
        for candidate in response.get("data", []):
            if candidate.get("id") == model:
                return candidate
        return None

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        options: dict[str, Any],
        timeout_seconds: float,
    ) -> ProviderResponse:
        payload = {"model": model, "messages": messages, "stream": False, **options}
        raw = self._request(
            "POST", "/chat/completions", payload=payload, timeout_seconds=timeout_seconds
        )
        try:
            choice = raw["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("OpenAI-compatible response has no assistant content") from exc
        if not isinstance(content, str):
            raise ProviderError("OpenAI-compatible assistant content is not text")
        usage = raw.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
        timings = raw.get("timings", {})
        if not isinstance(timings, dict):
            timings = {}
        if not isinstance(prompt_tokens, int):
            value = timings.get("prompt_n")
            prompt_tokens = value if isinstance(value, int) else None
        if not isinstance(output_tokens, int):
            value = timings.get("predicted_n")
            output_tokens = value if isinstance(value, int) else None
        if not isinstance(total_tokens, int) and isinstance(prompt_tokens, int) and isinstance(output_tokens, int):
            total_tokens = prompt_tokens + output_tokens

        def milliseconds(name: str) -> float | None:
            value = timings.get(name)
            return value / 1000 if isinstance(value, (int, float)) else None

        return ProviderResponse(
            content=content,
            raw=raw,
            prompt_tokens=prompt_tokens if isinstance(prompt_tokens, int) else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) else None,
            total_tokens=total_tokens if isinstance(total_tokens, int) else None,
            prompt_eval_seconds=milliseconds("prompt_ms"),
            generation_seconds=milliseconds("predicted_ms"),
            finish_reason=choice.get("finish_reason"),
        )


class LlamaCppProvider(OpenAICompatibleProvider):
    """Own a loopback-only llama-server for one configured GGUF model."""

    def __init__(self, provider_id: str, settings: dict[str, Any]):
        super().__init__(provider_id, settings)
        self._process: subprocess.Popen[bytes] | None = None
        self._log_handle: Any = None
        self._log_path: Path | None = None
        self._session_api_key = secrets.token_urlsafe(32)
        self._verified_sha256: str | None = None
        self._started_at: float | None = None

    def _headers(self) -> dict[str, str]:
        headers = Provider._headers(self)
        headers["Authorization"] = f"Bearer {self._session_api_key}"
        return headers

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _log_tail(self) -> str:
        if self._log_handle:
            self._log_handle.flush()
        if not self._log_path or not self._log_path.exists():
            return ""
        return self._log_path.read_text(encoding="utf-8", errors="replace")[-12000:]

    def _probe_ready(self, timeout_seconds: float) -> bool:
        request = urllib.request.Request(
            self._url("/models"), headers=self._headers(), method="GET"
        )
        try:
            with urllib.request.urlopen(request, timeout=min(timeout_seconds, 3)) as response:
                return 200 <= response.status < 300
        except (urllib.error.URLError, TimeoutError):
            return False

    def _ensure_started(self, timeout_seconds: float) -> None:
        if self._process and self._process.poll() is None:
            return
        server_path = Path(self.settings["server_path"]).resolve()
        model_path = Path(self.settings["model_path"]).resolve()
        if not server_path.is_file():
            raise ProviderError(f"llama.cpp server not found: {server_path}")
        if not model_path.is_file():
            raise ProviderError(f"GGUF model not found: {model_path}")
        expected = str(self.settings.get("model_sha256", "")).lower()
        self._verified_sha256 = self._file_sha256(model_path)
        if expected and self._verified_sha256 != expected:
            raise ProviderError(
                f"GGUF SHA-256 mismatch: expected {expected}, got {self._verified_sha256}"
            )
        parsed = urllib.parse.urlparse(self.base_url)
        host = parsed.hostname or ""
        port = parsed.port
        if host not in {"127.0.0.1", "localhost", "::1"} or not port:
            raise ProviderError("managed llama.cpp must use a loopback base_url with an explicit port")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if probe.connect_ex(("127.0.0.1" if host == "localhost" else host, port)) == 0:
                raise ProviderError(f"managed llama.cpp port is already in use: {host}:{port}")

        log = tempfile.NamedTemporaryFile(
            mode="w+b", prefix="localbench-llama-", suffix=".log", delete=False
        )
        self._log_handle = log
        self._log_path = Path(log.name)
        alias = str(self.settings.get("alias") or model_path.stem)
        args = [
            str(server_path), "-m", str(model_path), "--alias", alias,
            "--host", host, "--port", str(port), "--api-key", self._session_api_key,
            "--no-webui", "--ctx-size", str(int(self.settings.get("ctx_size", 4096))),
        ]
        threads = self.settings.get("threads")
        if threads is not None:
            args.extend(["--threads", str(int(threads))])
        extra_args = self.settings.get("server_args", [])
        if not isinstance(extra_args, list) or any(not isinstance(item, str) for item in extra_args):
            raise ProviderError("llama.cpp server_args must be a list of strings")
        args.extend(extra_args)
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self._process = subprocess.Popen(
            args,
            cwd=server_path.parent,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        self._started_at = time.time()
        deadline = time.monotonic() + min(
            timeout_seconds, float(self.settings.get("startup_timeout_seconds", 180))
        )
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                tail = self._log_tail()
                self._stop_server()
                raise ProviderError(f"llama-server exited while loading the GGUF: {tail}")
            if self._probe_ready(3):
                return
            time.sleep(0.5)
        tail = self._log_tail()
        self._stop_server()
        raise ProviderError(f"llama-server did not become ready in time: {tail}")

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout_seconds: float = 30,
    ) -> dict[str, Any]:
        self._ensure_started(timeout_seconds)
        return Provider._request(
            self, method, path, payload=payload, timeout_seconds=timeout_seconds
        )

    def runtime_metadata(self, timeout_seconds: float) -> dict[str, Any] | None:
        self._ensure_started(timeout_seconds)
        server_path = Path(self.settings["server_path"]).resolve()
        model_path = Path(self.settings["model_path"]).resolve()
        try:
            version = subprocess.run(
                [str(server_path), "--version"],
                cwd=server_path.parent,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                check=False,
            )
            version_text = (version.stdout + version.stderr).strip()
        except (OSError, subprocess.SubprocessError) as exc:
            version_text = f"unavailable: {exc}"
        return {
            "managed": True,
            "pid": self._process.pid if self._process else None,
            "base_url": self.base_url,
            "server_path": str(server_path),
            "server_version": version_text,
            "model_path": str(model_path),
            "model_size_bytes": model_path.stat().st_size,
            "model_sha256": self._verified_sha256,
        }

    def model_metadata(self, model: str, timeout_seconds: float) -> dict[str, Any] | None:
        metadata = super().model_metadata(model, timeout_seconds)
        if metadata is None:
            return None
        return {
            **metadata,
            "gguf_path": str(Path(self.settings["model_path"]).resolve()),
            "gguf_sha256": self._verified_sha256,
        }

    def _stop_server(self) -> dict[str, Any]:
        process = self._process
        record: dict[str, Any] = {"managed": True, "pid": process.pid if process else None}
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
                record["forced"] = True
        if process:
            record["exit_code"] = process.returncode
        record["log_tail"] = self._log_tail()
        if self._log_handle:
            self._log_handle.close()
            self._log_handle = None
        if self._log_path:
            self._log_path.unlink(missing_ok=True)
            self._log_path = None
        self._process = None
        return record

    def unload_model(self, model: str, timeout_seconds: float) -> dict[str, Any] | None:
        return self._stop_server()


def make_provider(provider_id: str, settings: dict[str, Any]) -> Provider:
    if settings["type"] == "ollama":
        return OllamaProvider(provider_id, settings)
    if settings["type"] == "openai_compatible":
        return OpenAICompatibleProvider(provider_id, settings)
    if settings["type"] == "llama_cpp":
        return LlamaCppProvider(provider_id, settings)
    raise ValueError(f"unsupported provider type: {settings['type']}")
