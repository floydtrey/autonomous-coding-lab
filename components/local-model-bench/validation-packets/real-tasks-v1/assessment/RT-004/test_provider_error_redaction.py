from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from localbench.config import load_config
from localbench.providers import OpenAICompatibleProvider, ProviderError
from localbench.runner import BenchmarkRunner
from localbench.suites import load_suite


class EchoErrorHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _write(self, status: int, body: bytes, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/v1/models":
            self._write(200, json.dumps({
                "data": [{"id": "echo-http"}, {"id": "echo-invalid"}]
            }).encode("utf-8"))
        else:
            self._write(404, b'{"error":"missing"}')

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        authorization = self.headers.get("Authorization", "")
        if payload.get("model") == "echo-http":
            body = json.dumps({
                "error": "synthetic rejection",
                "authorization": authorization,
                "diagnostic": "keep-this-detail",
            }).encode("utf-8")
            self._write(400, body)
            return
        if payload.get("model") == "echo-invalid":
            self._write(
                200,
                f"not-json authorization={authorization} keep-invalid-detail".encode("utf-8"),
                "text/plain",
            )
            return
        self._write(400, b'{"error":"plain diagnostic"}')


class ServerFixture:
    def __enter__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), EchoErrorHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}/v1"
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class ProviderErrorRedactionAssessmentTests(unittest.TestCase):
    secret = 'sk-local.*[x]"quoted\\path-value'
    env_name = "LOCALBENCH_ASSESSOR_SECRET"

    def provider(self, base_url: str, *, credential: bool = True):
        settings = {"type": "openai_compatible", "base_url": base_url}
        if credential:
            settings["api_key_env"] = self.env_name
        return OpenAICompatibleProvider("assessment-provider", settings)

    def assert_secret_absent(self, text: str):
        self.assertFalse(self.secret in text, "configured credential leaked")
        escaped = json.dumps(self.secret, ensure_ascii=False)[1:-1]
        self.assertFalse(escaped in text, "JSON-escaped credential leaked")

    def test_http_and_invalid_json_errors_are_redacted_but_useful(self):
        with ServerFixture() as fixture, patch.dict(
            os.environ, {self.env_name: self.secret}, clear=False
        ):
            provider = self.provider(fixture.base_url)
            for model, retained in (
                ("echo-http", "keep-this-detail"),
                ("echo-invalid", "keep-invalid-detail"),
            ):
                with self.subTest(model=model), self.assertRaises(ProviderError) as raised:
                    provider.chat(model, [{"role": "user", "content": "test"}], {}, 2)
                body = raised.exception.body or ""
                self.assert_secret_absent(body)
                self.assertIn("[REDACTED]", body)
                self.assertIn(retained, body)

    def test_runner_never_persists_the_synthetic_secret(self):
        with tempfile.TemporaryDirectory() as temp, ServerFixture() as fixture, patch.dict(
            os.environ, {self.env_name: self.secret}, clear=False
        ):
            root = Path(temp)
            suite_path = root / "suite.json"
            suite_path.write_text(json.dumps({
                "suite_id": "redaction",
                "cases": [{"id": "echo", "prompt": "trigger local fake"}],
            }), encoding="utf-8")
            config_path = root / "config.json"
            config_path.write_text(json.dumps({
                "schema_version": 1,
                "result_root": "results",
                "providers": {"fake": {
                    "type": "openai_compatible",
                    "base_url": fixture.base_url,
                    "api_key_env": self.env_name,
                }},
                "models": [{"id": "fake", "provider": "fake", "name": "echo-http"}],
                "run": {"timeout_seconds": 2, "retries": 0, "unload_after_model": False},
            }), encoding="utf-8")
            config, config_hash = load_config(config_path)
            run_dir = BenchmarkRunner(
                config,
                config_path,
                config_hash,
                [load_suite(suite_path)],
                run_id="redaction-run",
            ).run()

            corpus = "\n".join(
                path.read_text(encoding="utf-8", errors="replace")
                for path in run_dir.rglob("*")
                if path.is_file()
            )
            self.assert_secret_absent(corpus)
            self.assertIn("[REDACTED]", corpus)
            self.assertIn("keep-this-detail", corpus)
            result = json.loads(next(run_dir.glob("models/*/cases/*.json")).read_text())
            self.assertEqual(result["error"]["http_status"], 400)
            self.assertEqual(result["error"]["type"], "ProviderError")

    def test_credential_free_error_is_preserved_and_missing_env_fails_cleanly(self):
        with ServerFixture() as fixture:
            provider = self.provider(fixture.base_url, credential=False)
            with self.assertRaises(ProviderError) as raised:
                provider.chat("plain-error", [{"role": "user", "content": "test"}], {}, 2)
            self.assertIn("plain diagnostic", raised.exception.body or "")

            with patch.dict(os.environ, {}, clear=True):
                missing = self.provider(fixture.base_url)
                with self.assertRaises(ProviderError) as missing_error:
                    missing.chat("echo-http", [{"role": "user", "content": "test"}], {}, 2)
                self.assertIn(self.env_name, str(missing_error.exception))
                self.assertIsNone(missing_error.exception.body)


if __name__ == "__main__":
    unittest.main()
