# M03 — one explicitly enabled Pi attempt

The supervision implementation extends the existing Windows Job Object helpers
and Process Custody V2 records. It connects to M02's launcher seam and Worker Lab
dispatch. M03's required real-model edit and cancellation checks passed on the
intended Windows host at 128K. This scoped compatibility milestone is complete;
it does not declare final ACL task acceptance or authorize M04.

The first authorized real-model run loaded the exact model at 128K, but Ollama's
OpenAI endpoint reloaded it at its 4K server default. It made the allowed edit,
then exhausted the initial four-request budget without a valid completed outcome.
Owned absence was verified and the unrelated process survived. This is preserved
as failed evidence, not a passing M03 run.

The adapter now rechecks runtime identity/context before each model request,
after response headers, before tools execute, and after settlement. A context
reset fails before tool calls from that response can execute. Transport errors
retain their actual cause, including request-budget exhaustion. Request/tool
budgets are explicit configuration options with new binding/activation identities;
the selected budgets are eight requests and eight tool calls, with retries still
disabled. The selected context remains 128K.

Pi's argument conversion also required a strict raw outcome check through its
`prepareArguments` hook: malformed empty strings must not become valid nulls.
The installed-SDK regression proves rejection. Outcome fields have explicit schema
descriptions, and the worker prompt states its budget and terminal sequence.
Bounded diagnostics record tool names, paths and claim/error details.

Ollama's OpenAI API cannot set context per request; see its
[context configuration documentation](https://docs.ollama.com/api/openai-compatibility#setting-the-local-context-size).
Preloading alone does not establish persistent effective context for this path.
The operator authorized restarting the existing server and retaining 128K as the
preferred default. The exact app/server identities were checked before restart,
`OLLAMA_CONTEXT_LENGTH=131072` was saved in the user environment, and the restarted
server confirmed that setting. The model name and digest remain unchanged.

## Launch and activation

`set_pi_activation` is an explicit operator operation against a protected local
state directory. It binds the selected configuration digest, controller identity
and current source manifest digest. No committed configuration enables execution.
Missing, disabled or changed activation blocks process creation. Dispatch checks
activation again immediately before creating the child. The ordinary CLI/service
still has no implicit runner; M04 owns the single-task entrypoint integration.

`make_supervised_pi_dispatch_runner` supplies the Windows launcher to the existing
Pi dispatch factory. The launcher requires the exact durable DISPATCHING
invocation and Provider Binding, current source identity, canonical host paths,
the admitted clean workspace and a matching request/deadline. State, framework,
SDK installation and Pi agent resources must be separate from the worker workspace.

M05A also checks the configured Node/Python installations and Python startup
locations before any selected interpreter executes, and again before creation.
Candidate overlap, reparse aliases, candidate-directed venv homes or restricted
library paths reject. The fixed stdlib-only Python bridge uses `-I -S -B` so
site-packages `.pth` and `sitecustomize` startup code cannot execute. These are
execution-dependency checks; they grant no new file tools or OS sandbox. Supported
venv settings use the standard first `home = ...` line pointing to a base Python
installation; ambiguous, duplicate or chained homes reject before execution.

A controller file lock allows one attempt per protected state directory. Launch
intent is durably written before process creation and records invocation/attempt,
request, grant, configuration, activation, controller process, deadline and exact
command. An existing invocation intent cannot be reused. Any earlier intent with
unresolved custody blocks a replacement, including a crash between writing intent
and creating its custody record. Recovery never adopts or kills by name or port.

## Windows lifetime management

`OwnedWindowsProcess` creates the child suspended with
`PROC_THREAD_ATTRIBUTE_JOB_LIST`; job membership is established during process
creation, rather than afterward. The job uses kill-on-close and its handle is not
inherited. An explicit handle list passes only the request/stdout/stderr handles.
The child's PID and creation time are recorded in custody before it resumes.
This requires the existing Windows backend on Windows 10 or later. See Microsoft's
[process attribute documentation](https://learn.microsoft.com/en-us/windows/desktop/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute).

Controller death closes the owned job even in the creation-to-record window.
Restart still treats incomplete evidence as uncertain; kill-on-close is not used
to fabricate a durable observation of absence.

The child gets an explicit environment with isolated resource/temp locations and
necessary Windows variables. Ambient PATH, credentials, proxy settings, Python
search paths and Node injection options are not inherited. Executables use
explicit paths. This manages workload lifetime and environment; it is **not** a
filesystem, network or account-permission sandbox. The model retains only the
existing exact-file tools.

The supervisor monitors the absolute attempt deadline, a controller cancellation
event and log size. On failure it terminates only its owned job and queries job
accounting until zero or a bounded cleanup deadline. Success also requires no
remaining owned child. Only observed zero workload yields ABSENCE_VERIFIED. An
accounting or durable-record failure blocks output from reaching AWF's candidate
checks. Process creation failures without a retained job handle stay uncertain.

Custody now permits verified absence following an assigned but never dispatched
child. That does not permit acceptance: the existing acceptance path separately
requires request-sent evidence, successful exit and no first failure.

## Evidence and limits

Deterministic tests cover disabled launch, activation mismatch, durable ordering,
duplicate launch, unresolved prior intent, concurrent controllers, assignment or
resume failures, unavailable job accounting and minimal environment. Windows host
tests cover suspension, owned descendant cleanup, timeout/cancellation while an
unrelated process survives, and controller death before recording child custody.
An installed-SDK test traverses Worker Lab and the real Windows supervisor with
fixture HTTP responses. That remains fixture evidence, not a real-model run.

`tools/pi-compatibility/supervision_probe.py` is an explicit compatibility probe,
not a second production CLI. It uses a fixed, trusted task and independent file
check; it does not import or execute candidate-authored code. Its edit mode must
produce only the allowed `target.py` change plus a completed, settled claim and
verified absence. Its cancel mode requests cancellation after the real Pi session
starts, checks owned absence and leaves an unrelated test process untouched.
Each probe uses a fresh evidence directory and disables its local activation on
exit. It never loads a model or starts a server. The prestarted shared provider is
not owned by the worker job and is not terminated by cancellation.

Readiness failures are recorded as host-readiness-only evidence with zero launch.
Real-model evidence must be collected after the exact configured model is loaded
with adequate observed context. The probe reads the selected configuration rather
than fixing a context size. The current selection is 128K; available settings remain
modular as established in M01.

On 2026-09-17, `M03-real-edit-05` passed using qwen3.8:27b Q4_K_M,
Ollama 0.34.1 and Pi 0.85.1: six requests and six tool calls produced only the
authorized target.py change, a completed/stop outcome and a passing independent
check. The candidate contained exactly ten bytes, `VALUE = 2` followed by LF.
`M03-real-cancel-01` passed with PI_CANCELLED after the real session started.
Both recorded ABSENCE_VERIFIED with zero owned processes, preserved the unrelated
test process and authority file, and disabled their local activation on exit.
The shared Ollama server remains at the operator's preferred 131072-token default.

Earlier failed attempts are retained: context reset/request exhaustion (01),
invalid outcome (02), budget exhaustion (03), and a missing final newline caught
by the independent check despite a completed claim (04). The probe now states
the exact ten bytes explicitly; its check was not weakened. This is one passing
bounded edit, not a reliability benchmark or a test of a full 128K input.

Final affected checks: 168 Worker Lab Python tests, 12 Node adapter tests, and
12 root source/inventory tests passed; portable source components match. The
broader AWF Python suite was not rerun; its pre-existing documentation assertion
failure reported in M02 remains outside this change.

M04 outcome persistence/CLI, M05 protected validator execution modes and M06 final
acceptance remain out of scope. Process logs and custody here are supervision
evidence, not a successful ACL task verdict. The running checkout is not upgraded.
