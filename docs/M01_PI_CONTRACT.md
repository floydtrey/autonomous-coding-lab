# M01 — One local worker configuration and adapter protocol

M01 implements configuration and serialization only. It does not launch Pi,
install a dispatch runner, qualify a provider, or activate execution. The Minimum
Usable ACL M01 assignment supersedes the older S10–S15 implementation order for
this work; their retained evidence remains useful.

## One explicit configuration

`config/pi-local-worker.json` identifies the S09-selected `qwen3.8:27b` Q4_K_M
model by exact name and content digest, Ollama 0.34.1, the explicit loopback
OpenAI-compatible endpoint/API, Pi 0.85.1 and its dependency-lock digest, Node
24.19.0, ACL adapter/tool identities, runtime requirement, settings and limits.
There is no model fallback, server loader, discovery or multi-profile registry.

Context is an operator option: common presets are 4096, 8192, 32768, 131072 and
262144 tokens, and other explicit positive safe-integer sizes are supported. The
initial file selects **131072 (128K)** following the user's hardware/context
guidance. `intended_pi_worker(context_tokens=...)` creates a fresh declaration;
`load_pi_worker(path, expected_digest=...)` resolves a supplied file against a
separately trusted canonical SHA-256 identity. The builder defaults to the selected
128K preference. Selecting another size updates both the
requested/effective-context requirement and settings digest. An old admitted pin
rejects the changed configuration, even when the incoming frame recomputes its
own digest. Changing other execution settings/model/package requires deliberate
revision of this one protected declaration, not an implicit fallback.

The existing RuntimeSettingsProfile vocabulary and coding-worker runtime
requirement are reused. The selected defaults disable retries and compaction,
with 180 seconds per attempt, 60 seconds per provider request, 30 seconds per file
tool call, eight requests, eight file calls and 2048 output tokens per request.
Existing Pydantic settings and qualification semantics are unchanged.

M05A replaces equality-to-defaults with a strict supported schema. The protected
JSON and separately approved digest control output, deadlines, request/tool counts,
context, local endpoint and exact Node/Pi/Ollama/model/lockfile identities. Changing
these values requires no source edit. Output must fit the requested context;
provider/tool deadlines must fit the attempt deadline, which remains within the
protected runtime requirement of 900 seconds. Endpoints support canonical HTTP
loopback hosts (`127.0.0.1`, `localhost`, `[::1]`), an explicit valid port and `/v1`.
Protocol, file-tool authority, single concurrency, authentication policy and
no-fallback/no-retry invariants remain fixed. Nested settings digests must match.
Re-pinning requires fresh matching readiness/compatibility observations, Provider
Binding and explicit activation; old identities reject. No upgrade or model load
is automatic. The current 131072-token configuration bytes are unchanged by M05A.

The configured context is a requirement, not observed capacity. S09 demonstrated
4K, and the user's prior 128K operation is not new ACL qualification evidence.
`validate_effective_pi_worker` rejects insufficient independently established
context. M02 must apply the selected context to Pi metadata and verify that the
prestarted endpoint has matching capacity; changing Pi metadata alone is not
enough. No server setting was changed in M01.

## Wire contract

`worker_lab/pi_protocol.py` and AWF `tools/pi_protocol.mjs` define canonical UTF-8
JSON frames, bounded to 262144 bytes. Object keys are ASCII, values support Unicode
text and safe integers, and floats, duplicate keys, noncanonical bytes, excessive
nesting, trailing data and unknown top-level fields reject. Transport framing and
process supervision belong to M02 and later work. A frame is one payload without
a trailing newline; no stdout log text can be mistaken for a result.

| Frame | Bound information |
| --- | --- |
| `acl-pi-request:v1` | Full existing invocation, exact task and Controller Task Packet, one worker config/digest, absolute workspace root, grant digest, issuance time and absolute deadline |
| `acl-pi-event:v1` | Exact request digest, ordered sequence, started/settled/stopped/error kind and bounded detail |
| `acl-pi-result:v1` | Exact request digest, status, stop reason, summary, remaining work/blocker, nullable session/usage/candidate references |

Python uses the existing InvocationRecordV3 parser (including V4), packet/prompt
identity checks, WorkspaceWriteTask parser and dispatch-state checks. The grant
digest covers the complete invocation, including authorization custody, logical
workspace/source-state identity and exact readable/writable scope, plus the
workspace root. The request digest transitively binds all of those fields.
Absolute deadlines must be live and within the configured attempt budget.

The future trusted parent supplies Node **separate expected request and worker
digests**, obtained after Python admission/configuration checks. Node checks exact
canonical bytes against both before exposing the request. Never use incoming
frame values as trusted pins. These pins are integrity checks, not authentication
against a compromised parent. Python result/event parsers likewise require the
trusted configuration digest and original request bytes. Ordered event checks
reject duplicates/gaps; terminal results may be received after a deadline.

Statuses are `completed`, `needs_continuation`, `blocked`, `failed`, `cancelled`,
`timed_out`, and `protocol_error`. Blocked/continuation claims require remaining
work or a blocker. Missing evidence remains null, not invented zero usage. Artifact
references include path and digest and stay within the writable grant. References
and completion claims do not establish file existence, successful validation,
settlement, process absence or acceptance. Those remain ACL responsibilities.

## M02 prerequisites and limits

No larger blocker prevents implementing the next adapter. Existing production
Provider Binding/capability qualification still protects only the Pydantic/Ollama
candidate/settings. M01 deliberately does not manufacture a Pi qualification or
register Pi as a qualified production adapter. The protocol carries existing
Provider Binding/authority identities as references; parsing alone cannot verify
durable evidence. Before production launch, the trusted integration must resolve
those references to Pi-specific observation/qualification/binding evidence and
verify exact installed package, model, endpoint, context and configuration.
An old Pydantic binding is never authorization for Pi.

M02 must also implement the Pi executor, resource/tool isolation and actual budget
enforcement, settlement/outcome collection and subsequent custody integration.
The current protocol fixture only parses and serializes deterministic data: it
imports no Pi package and runs no model, network request or workspace tools.

Tests cover every execution-significant configuration leaf, all five context
presets plus a custom 64K size, separately pinned tampering, deadlines, malformed frames on both sides,
lossless Python→Node→Python requests, Node results/events, usage/session/artifact
preservation and fail-closed result correlation. See the task completion report
for exact commands and results. Portable source closure includes the Node codec.
