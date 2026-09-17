# S09 server, path and remediation checks

Observed 2026-09-17. Ollama 0.34.1 is running as PID 19816 from
`C:\Users\floyd_dev\AppData\Local\Programs\Ollama\ollama.exe serve`, listening
on 127.0.0.1:11434. `/api/version`, `/api/tags`, `/api/show` and `/api/ps`
responded successfully. No restart was necessary. Pi is an embedded SDK/CLI in
this spike; it does not require another listening server.

`OLLAMA_MODELS` is `C:\AI\Models\Ollama` in the process/user environment.
The original model manifest is under
`manifests\registry.ollama.ai\library\qwen2.5-coder\7b` in that directory.
Its SHA-256 matches the original probe model digest. All four manifest layer
files exist and match their declared sizes. This is not a full weight hash audit.
The repository-local Pi CLI and `file-bridge.py` exist at their configured paths;
the earlier six passing adapter tests already exercised the explicit Python path.
The failed model calls never reached that bridge, so their failure is not a
workspace path lookup error. One generated text response did invent an absolute
path; ACL would reject it if it were submitted as a tool argument.

## Template check and attempted correction

The installed template digest is
`1e65450c30670713aa47fe23e8b9662bdf4065e81cc8e3cbfaa98924fcc0d320`.
The config's historical diff_ids and official registry template identify
`e94a8ecb9327ded799604a2e478659bc759230fe316c50d686358f932f52776c`.
The latter blob was not locally present. Its downloaded bytes were verified
against that digest. The local template changes two instruction lines, replacing
XML-tag wording and adding a no-backticks/no-other-text instruction.

Using Ollama's supported create API, created a separate diagnostic alias
`acl-s09-qwen25-official:7b` from the existing weights with the official template.
The original tag was not changed; no model weights were downloaded. The alias
remains installed for reproducibility. A single bounded 256-token direct request
still returned JSON in assistant content with no native tool call. Restoring the
official template therefore did not establish a fix.

[Trial evidence](../../docs/evidence/S09_OFFICIAL_TEMPLATE_TRIAL.json) includes
creation status, template, exact request and response. Reproduction source is
`official-template-trial.mjs`; it intentionally refuses to overwrite an existing
alias. The preceding diagnosis evidence remains unchanged.

## Research and recommendation

- [Ollama issue 12174](https://github.com/ollama/ollama/issues/12174) reports the same qwen2.5-coder symptom. This is supporting history, not proof of our exact internal cause.
- [Pinned Ollama 0.34.1 parser](https://raw.githubusercontent.com/ollama/ollama/v0.34.1/tools/tools.go) searches for the template's tool marker before parsing calls; call-shaped text alone need not produce native calls.
- [Official Qwen2.5-Coder template](https://ollama.com/library/qwen2.5-coder:7b/blobs/e94a8ecb9327) supplied the verified comparison.
- [Supported create API](https://docs.ollama.com/api/create) supports an existing model plus template override, allowing an isolated trial.
- [Qwen3.5 model page](https://ollama.com/library/qwen3.5) advertises tool support; local `qwen3.5:9b` is already installed, about 6.1 GiB, and `/api/show` reports tools capability.

Recommended next step: explicitly select and qualify `qwen3.5:9b` on the same
endpoint, starting with exact selection and native tool calls, then S09's real
read/edit and independent validation. Capability labels are not qualification.
No alternative model inference was run in this investigation. If retaining the
old model is mandatory, further raw-generation/parser investigation is a separate
bounded task, not a proven quick fix. S09 remains blocked; no S10 work was done.
