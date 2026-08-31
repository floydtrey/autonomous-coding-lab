# RT-002: Create non-destructive partial evaluation snapshots

## Situation

`localbench evaluate --run <RUN>` can be useful before a long run finishes, but
it always writes the canonical `evaluation.json`, `evaluation.csv`, and
`evaluation.md`. A partial review therefore looks final and may overwrite an
earlier report. The runner later overwrites those same names at completion.

## Authorized outcome

Add an optional snapshot mode to the existing `evaluate` command. The default
command and canonical report names must remain unchanged.

Requirements:

- R1 Add `--snapshot NAME` to `localbench evaluate`. Without it, retain the
  existing command behavior and filenames exactly.
- R2 Validate `NAME` as a safe identifier and keep all output inside
  `<run>/snapshots/<NAME>/`.
- R3 Refuse to overwrite an existing snapshot directory. Do not add a force or
  recursive-delete option.
- R4 Write `evaluation.json`, `evaluation.csv`, and `evaluation.md` inside the
  snapshot directory using the same scores and case ordering as canonical
  evaluation.
- R5 Record that the report is a snapshot, its creation time, manifest status,
  and the number of terminal case files observed.
- R6 A snapshot taken during a running benchmark must read only terminal case
  files already present and must not modify the manifest, checkpoint, raw case
  files, canonical reports, or model process.
- R7 Preserve the public `evaluate_run(run_dir)` behavior for existing Python
  callers. Any API extension must be additive.
- R8 Add deterministic tests for default behavior, snapshot behavior, unsafe
  names, existing destinations, and a simulated running manifest.

## Authorized files

- `src/localbench/cli.py`
- `src/localbench/evaluate.py`
- `src/localbench/util.py` only if reusing existing safe-ID validation
- Test files under `tests/`
- The evaluation section of `README.md`

Do not change scoring weights, prompt suites, providers, runner ordering, result
schemas, or existing result data.

## Completion evidence

Report files changed, tests run, the exact snapshot path rule, and proof that a
snapshot did not alter canonical run files.
