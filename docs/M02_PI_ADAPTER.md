# M02 — Connected Pi adapter

M02 connects Worker Lab's existing dispatch client to AWF's existing
`BoundProviderExecutor`, the Node adapter, the S07-pinned Pi SDK, and S09's bounded
file implementation. It implements the replacement queue's M02 only. There is no
production activation, implicit launcher, server/model auto-loader or new agent loop.

## Execution path

`dispatch_workspace_write` resolves the durable binding and its exact settings.
An explicitly supplied `make_pi_dispatch_runner` supplies the bound executor to
AWF. AWF builds the admitted context and scope as before. The executor binds that
rendered context in `acl-pi-request:v2`, preserving M01 V1 parsing, then sends one
canonical JSONL request to the isolated Node entrypoint. JSONL output consists of
ordered events followed by one terminal result. EOF, trailing output, mismatched
identities or missing settlement are never success.

The runner requires explicit absolute host paths, an explicit launcher callable
and a controller-owned outcome sink. It does not construct or activate a process
supervisor. The normal CLI/service still injects no runner. M03 must implement the
activation/launch-intent/custody/absence gate before real dispatch is enabled. The
M02 test launcher is a deterministic test fixture, not production containment.

The single Pi configuration uses the existing Provider Binding/store and runtime
requirement/settings record vocabulary. Pi's candidate digest binds the entire
configured worker; changing configured context or any other significant identity
invalidates an old binding. Its legacy `host_provider_qualification_digest` field
holds a versioned **readiness observation digest** for this path. This deliberately
does not claim the deferred broad S16 capability/session/compaction qualification.
The Pydantic capability-qualification path remains intact.

`check_runtime_readiness` consumes trusted local endpoint `/api/version`,
`/api/tags` and `/api/ps` observations. The caller explicitly creates the binding;
no network request is made by that constructor. Node repeats those checks before
importing/starting Pi: exact provider version, model name/content/metadata/
quantization, preloaded model and adequate observed server context. The complete
readiness identity must match the bound observation. SDK package/version,
dependency-lock digest and Node version are checked against M01's configuration.
Pi's `contextWindow` alone never establishes server readiness. There is no new
context benchmark campaign.

## Authority and outcomes

Only `acl_read_file`, `acl_write_file` and `acl_report_outcome` are exposed. The
file tools/bridge are promoted from S09 and still call the existing
`BoundedFileTools`: exact paths, stale-write digest, canonical paths, size/encoding
limits and atomic replacement remain enforced. The tools receive a copied grant
from admission, never model-supplied authority.

All file/outcome calls share one queue. A write queued before an outcome finishes
before that outcome freezes mutations. A write queued after it rejects without
changing the candidate. The bridge performs the write synchronously and returns
only after replacement, so an accepted terminal claim cannot race an in-flight
write. Deadline and tool limits remain bounded; process-absence evidence is M03.

The structured claim is one of completed, needs_continuation, blocked or failed,
with summary and remaining-work/blocker fields. Missing/malformed/duplicate claims
do not succeed. Provider text cannot substitute for the outcome tool. A claim only
becomes a successful worker result after `agent_settled`, a successful authoritative
final stop reason and idle state. An intermediate `agent_end` or resolved prompt
is insufficient. Settled errors remain failures even after a completed claim.

The outcome sink receives the worker result before AWF's existing candidate checks.
Incomplete outcomes raise a structured error rather than entering the successful
candidate path. Existing validation/acceptance APIs retain their meaning; this task
does not implement M04 persistence, M05 validator execution modes or M06 acceptance.
Session references are informational; reopen/continuation is not implemented.
The `acl-pi-result:v2` message keeps unavailable token measurements null while
measured request/tool counts survive; V1 result parsing remains compatible and
retains its original all-known-or-null usage semantics.

## Resource isolation tests and evidence

Pi gets explicit model, API/endpoint, scoped model, tool allowlist, in-memory
settings and a new in-memory session. Extensions, skills, templates, themes and
context discovery are disabled. Appended system prompts and agent-file lists are
explicitly cleared. The installed-SDK fixture exposed that `noContextFiles` alone
does not suppress global `APPEND_SYSTEM.md`; the explicit override fixes that path.

The end-to-end fixture traverses Worker Lab → AWF → Node adapter → **installed Pi
0.85.1 SDK**, with deterministic HTTP responses replacing the model endpoint. It
performs real bounded file reads/writes in a disposable repository, records an
outcome, settles and passes the existing independent fixed fixture check. Hostile
project/global resource files are planted and must never reach requests or execute.
This is installed-SDK/host fixture evidence, **not a real-model run or qualification**.

Other fixtures cover denied paths, stale writes, both mixed write/outcome orderings,
malformed/duplicate/missing outcomes, early agent-end, absent settlement, settled
errors, provider failure without retry, unknown usage and truncated output.

M03 remains necessary for explicit enablement, minimal process environment, durable
launch intent, owned-process identity/cleanup and the real edit/cancellation cases.
M02 does not authorize unsandboxed candidate tests or claim owned-process absence.
