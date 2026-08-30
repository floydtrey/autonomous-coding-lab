# RT-004: Redact credentials from persisted provider errors

## Situation

Provider configs can read an API key from an environment variable. HTTP error
bodies and malformed-response bodies are retained in `ProviderError`, then copied
into case or fatal error records for later review. A faulty local endpoint may
echo an `Authorization` header, bearer token, API key, or request diagnostic in
its response. Results are designed to be committed to Git.

## Authorized outcome

Prevent configured credential values from appearing in persisted benchmark
errors while preserving useful provider diagnostics.

Requirements:

- R1 Never persist the configured API-key value or the same value in a Bearer
  token when an endpoint echoes it in an HTTP or malformed-JSON response body.
- R2 Apply redaction before an error object reaches case results, manifests,
  stdout, or stderr; do not rely on callers remembering to sanitize it.
- R3 Preserve error type, HTTP status, provider identity, and non-sensitive body
  text needed for diagnosis.
- R4 Use a clear replacement marker and prevent partial secret exposure.
- R5 Preserve existing behavior for providers without credentials and responses
  that contain no configured secret.
- R6 Do not log, return, or embed the secret in a new metadata field, exception
  message, test failure, or debug output.
- R7 Keep environment-variable credential handling and public provider APIs
  backward compatible and dependency-free.
- R8 Add local fake-server tests for HTTP errors, invalid JSON, secret-free
  errors, absent credential variables, and secrets containing regex or JSON
  metacharacters.

## Authorized files

- `src/localbench/providers.py`
- `src/localbench/runner.py`
- `src/localbench/util.py`
- Test files under `tests/`
- Credential-safety documentation in `README.md`

Do not contact a real provider, change model execution order, weaken stored error
evidence wholesale, or alter prompt/result schemas unrelated to redaction.

## Completion evidence

Report changed files, tests, the redaction boundary, preserved diagnostic fields,
and a scan showing the synthetic secret is absent from all generated artifacts.
