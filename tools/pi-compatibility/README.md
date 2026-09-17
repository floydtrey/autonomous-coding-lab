# S07 — Pi Windows host compatibility

**Result: PASS**, observed 2026-09-17. The installed SDK imports and exposes
`createAgentSession`; the installed CLI starts with `--version` and reports
`0.85.1`. Both child processes exited 0 with empty stderr.

- Package: `@earendil-works/pi-coding-agent@0.85.1`, the audited release.
- Node requirement: `>=22.19.0`; observed Node: `24.19.0`.
- Host: Windows x64, OS release `10.0.26200`.
- Observed package manager: pnpm `11.19.0`. npm was not available on PATH.
- Installation: 126 packages; lifecycle scripts disabled with `--ignore-scripts`.
- [Retained host evidence](../../docs/evidence/S07_PI_HOST_COMPATIBILITY.json)
  includes actual executable/package paths, outputs, timestamps, and lock/probe hashes.

The upstream [release package manifest](https://github.com/earendil-works/pi/blob/v0.85.1/packages/coding-agent/package.json)
declares the package identity and Node minimum. `package.json` pins the direct
dependency exactly; `pnpm-lock.yaml` fixes the resolved dependency graph and
integrities. Local installation and package-store directories are ignored by Git.

## Reproduce

From this directory, with Node meeting the stated requirement and pnpm 11.19.0:

```powershell
pnpm.cmd install --frozen-lockfile --ignore-scripts --store-dir .store
node probe.mjs
```

The probe writes `evidence.local.json` by default; an optional first argument
selects the output file. It uses bounded child processes, an isolated temporary
home, and an environment without inherited provider credentials or Node options.
It imports the SDK and runs only the CLI version path. It does not instantiate a
session, select/contact a model endpoint, or modify production dispatch.

The initial Codex sandbox run failed to spawn both child processes with `EPERM`.
The same probe passed when permitted to spawn outside that sandbox. This was an
execution-environment restriction, not a Pi import failure.

This establishes S07 host import/startup compatibility only. It does not qualify
tools, model connectivity, sessions, cancellation, compaction, or ACL execution.
S08 and the later qualification tasks remain separate. Installed role authority,
production source identity, and the disabled execution state are unchanged.

[S08 exact model/endpoint selection results and reproduction](S08.md) are recorded separately.

[S09 bounded file-tool results and blocker](S09.md) retain the failed real-model case.

[S09 completed with Qwen3.8 27B Q4 and detailed diagnostics](S09_27B.md).
