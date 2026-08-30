# RT-001: Survive transient Windows checkpoint reader locks

## Observed failure

An unattended Windows benchmark stopped after 31 of 90 cases. The model request
itself had not failed. The fatal error occurred when `atomic_write_json` attempted
to replace `checkpoint.json` while the separate status watcher was reading it:

```text
PermissionError: [WinError 5] Access is denied:
'.checkpoint.json.<random>.tmp' -> 'checkpoint.json'
```

The watcher reads the manifest and checkpoint every two seconds. Antivirus or
indexing software may also open these files briefly.

## Authorized outcome

Repair checkpoint/result JSON persistence so a brief Windows reader lock does
not abort an otherwise healthy unattended run.

Requirements:

- R1 Preserve the temporary-file, flush, fsync, and atomic-replace durability
  strategy. Do not write JSON directly into the destination file.
- R2 Retry only the transient permission failure around the replace operation.
- R3 Bound retries by count or elapsed time. A persistent lock must still raise
  an error instead of hanging forever or reporting false success.
- R4 Preserve the old destination until a replacement succeeds.
- R5 Clean up the temporary file after terminal failure.
- R6 Add deterministic automated coverage for both a transient lock that clears
  and a persistent lock that does not.
- R7 Preserve existing public function signatures, result schemas, checkpoint
  schemas, and watcher behavior.
- R8 Keep the change dependency-free and Windows-compatible.

## Authorized files

- `src/localbench/util.py`
- Test files under `tests/`

Do not change the runner, providers, suite/config schemas, PowerShell scripts, or
existing result data.

## Completion evidence

Run the existing unit test suite and report:

- files changed;
- tests executed and their result;
- the retry bound selected and why;
- how terminal cleanup and persistent failure are preserved.
