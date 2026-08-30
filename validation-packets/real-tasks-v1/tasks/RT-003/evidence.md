# RT-003 evidence packet

During a resumed unattended run, these observations were captured close
together:

- `checkpoint.json` reported 46 of 90 completed cases.
- A direct count of `models/*/cases/*.json` returned 46 terminal case files.
- `localbench evaluate --run <RUN>` evaluated 46 cases: 18 Vera, 18 Qwen 7B,
  and 10 DeepSeek 6.7B.
- `summary.csv` contained 31 data rows: 18 Vera and 13 Qwen 7B cases.
- The run had previously failed at 31 of 90 because replacing
  `checkpoint.json` raised `PermissionError`; it was then resumed in the same
  result directory.
- Model requests after resume continued successfully.

Relevant source facts to verify rather than assume:

- Case results are written individually under each model's `cases/` directory.
- The checkpoint count is derived from terminal case files.
- Evaluation discovers terminal case files independently.
- Summary generation has its own lifecycle and output file.

No evidence of missing or malformed raw case JSON was observed.
