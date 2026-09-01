# Local Model Bench

Local Model Bench is the advisory model-evaluation component of Autonomous Coding Lab. It runs repeatable JSON or Markdown prompt suites against Ollama, managed llama.cpp/GGUF, and OpenAI-compatible local endpoints.

It is not a Worker Lab or framework runtime dependency, and its results cannot authorize worker execution.

## Use

For current setup, unattended-run, status, resume, and result-handling instructions, read [`../../docs/OPERATIONS.md`](../../docs/OPERATIONS.md). For the component boundary, read [`../../docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md).

Component examples remain under `configs/`, `suites/`, `scripts/`, and `validation-packets/`. Historical standalone instructions and benchmark decisions are preserved under [`../../docs/legacy/local-model-bench/`](../../docs/legacy/local-model-bench/README.md).

## Local help

After running `scripts\bootstrap.ps1`:

```powershell
.\.venv\Scripts\python.exe -m localbench --help
.\.venv\Scripts\python.exe -m localbench validate --config .\configs\ollama-16gb.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
