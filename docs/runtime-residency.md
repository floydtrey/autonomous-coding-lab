# Serial Runtime Residency and Recovery

ACL V1 treats model residency as Controller-owned execution state.

## Bootstrap versus recovery

The Determiner is the bootstrap role only for a genuinely new request. It is
never the generic model loaded after a restart or disconnect.

Before each role invocation ACL resolves the configured profile/model, verifies
that the OpenAI-compatible service is actually serving that model, and persists
a runtime checkpoint beneath the configured Controller state root.

For a nonterminal interrupted workflow, recovery uses the persisted resolved
runtime target that actually began the attempt. It does not re-bootstrap through
Determiner and it does not silently accept a different model merely because the
server is healthy.

## Checkpoint identity

A runtime checkpoint retains:

- workflow and attempt identity;
- role and profile identity;
- adapter and harness identity;
- exact resolved model alias;
- exact runtime base URL;
- the resolved profile launcher command/cwd used for that attempt;
- checkpoint state;
- an optional return target for temporary role switches.

In-flight targets are pinned. Editing model/profile environment configuration
while an attempt is interrupted does not silently migrate that attempt.

## Serial model verification

`config/runtime_residency.json` defines the serial OpenAI-compatible service
probe. Role profiles define their own model environment and optional launcher
environment.

The generic local-service bootstrap is disabled for the model server. This
prevents a universal Worker launcher from being started before ACL knows which
role/model is required.

When the desired model is already reported by `/models`, ACL reuses it. When
it is absent, ACL uses the launcher configured by the selected role profile. If
the wrong model is resident and no launcher is configured, ACL fails with a
model-mismatch error instead of sending the request to the wrong model.

A role-specific launcher is responsible for replacing any incompatible
single-model server when necessary. Host paths remain environment configuration,
not repository constants.

## Recovery

For an interrupted role:

1. read the durable workflow and runtime checkpoint;
2. verify the current role/profile still matches the checkpoint;
3. restore/verify the checkpoint's exact model;
4. query/recover the adapter attempt when supported;
5. for an unqueryable stateless adapter, mark the checkpoint
   `RECOVERY_REQUIRED` before releasing the workflow for a rerun;
6. the rerun is forced back onto the checkpoint model even if current model
   configuration has changed.

Completed/cancelled/failed role attempts move their checkpoint out of the active
state.

## Temporary Worker -> Planner switches

The checkpoint format also retains a return target. Before a future live Worker
consultation ACL can mark the Worker target `PAUSED_FOR_SWITCH`, run Planner
serially, then expose the exact Worker model/profile as `RETURN_REQUIRED`.
This prevents Planner/Determiner bootstrap behavior from erasing the model that
must resume the Pass.

Full live Worker context reconstruction and consultation-disconnect replay remain
part of Worker integration; the durable runtime identity needed for that
recovery is established here.


## Optional Windows llama.cpp switch launcher

`tools/runtime/Switch-LlamaServerModel.ps1` is a host utility for the current
Windows development machine. It is not required by the Controller architecture.

The script:

- derives the dedicated port from `ACL_OPENAI_COMPAT_BASE_URL` unless supplied;
- refuses to stop a listener unless it is `llama-server`;
- when a server executable is configured, refuses to stop a different
  `llama-server` binary;
- waits for the old listener to release the port;
- starts the requested Hugging Face GGUF or local GGUF with the requested alias.

The Controller profile can receive a complete launcher command through
`runtime_launcher_command_json_env`. Current role variables are:

- Determiner: `ACL_DETERMINER_LAUNCH_COMMAND_JSON`
- Planner: `ACL_PLANNER_LAUNCH_COMMAND_JSON`

This keeps host paths, quantization choices, and model download sources outside
Python source and outside mandatory repository configuration. Other operating
systems can provide different launcher commands using the same Controller
interface.


### llama.cpp fit and reasoning defaults

The Windows switch launcher leaves `--gpu-layers` unset by default and enables
`--fit on`, allowing llama.cpp to choose a VRAM-safe offload instead of forcing
all layers onto a device that cannot hold them. An explicit `-GpuLayers` value
remains available for controlled experiments.

For ACL role execution the launcher also uses `--reasoning off`,
`--no-reasoning-preserve`, and `--reasoning-budget 0`. Planner contract
correction already carries the rejected structured response explicitly, so
retaining hidden reasoning history is unnecessary and can increase context/use.
