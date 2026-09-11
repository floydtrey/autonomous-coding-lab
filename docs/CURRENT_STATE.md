# Current State

**Last updated:** 2026-09-10

**Repository location:** portable; current laptop checkout is `C:\projects\autonomous-coding-lab`

**Active branch:** `architecture/knowledge-core`

**Runtime Selection V1 code checkpoint:** `0ad1b212581fb7b18110b9155763bf49b42df442`

**Portable identity refresh checkpoint:** `01259212a41bc5a9943686a147165c9abd8268b4`

**Execution authority:** `DISABLED`

## Current vertical-slice position

The project is deliberately moving toward one supervised end-to-end coding slice:

`user objective -> controller/Foreman -> Knowledge Core retrieval -> bounded task/context packet -> worker harness -> coding worker -> independent verification -> verified/retry/blocked -> controller/human review`

Knowledge Core supplies governed project context. It does not authorize execution. Project Control Center is a separate status/dashboard project and is not ACL architecture or runtime authority.

### Completed or accepted foundations

- Knowledge Core SR-2 through G22 and intended-host PostgreSQL restart/recovery qualification are complete. Knowledge Core Consumer V1 at `37f08f4090d59573108100ddf1b35a4923f01c29` can return verified segment content with exact provenance while preserving canonical evidence and privacy/serving checks.
- The portable ACL installation identity separates committed component/source identity from per-host provider qualification. `config/portable-installation-manifest.json` is the current portability contract for the new vertical-slice path.
- The portable manifest requires Windows, CPython 3.12, and AMD64, but does not commit an absolute Python path or provider executable path. Provider identity is qualified separately and does not grant authorization.
- Controller Task Packet V1 is present and remained green in the Runtime Selection V1 focused acceptance run.
- Runtime Selection V1 introduces the protected Worker Lab requirement `coding-worker:v1` for capability `bounded-code-task`. New task preparation uses provider-qualified model/reasoning selectors rather than naming a concrete provider or model.
- Historical `terra-medium:v1` invocation records remain parseable for evidence compatibility. They are not the selected runtime requirement for new work.
- `components/autonomous-worker-framework/tools/worker_runtime.py` no longer gives generic `WorkerRequest` objects implicit Terra defaults; a provider-qualified runtime must supply its actual runtime values behind the framework boundary.

### Runtime Selection V1 acceptance evidence

On the current Windows laptop at code checkpoint `0ad1b212581fb7b18110b9155763bf49b42df442`:

- Worker Lab focused runtime/integration/controller packet validation: **26 passed**.
- Framework provider-neutral seam/code-task/controller packet validation: **10 passed**.
- The working tree was clean before and after validation.
- Measured Autonomous Worker Framework portable closure: `sha256:0ce8d8533073463b18bc29d72e0a5dfcf9ca0e28110505eb8f872c978427601c` across 9 files.
- Measured Worker Lab portable production tree: `sha256:1cdb7c5da5d81278f4f3b82de9c3082984c3d8b0b94e237c13be950e2c690b2a` across 27 files.
- `execution_authority=DISABLED` throughout. No worker, model, provider, adapter execution mode, authorization, or dispatch was run by this acceptance gate.

Commit `01259212a41bc5a9943686a147165c9abd8268b4` records those exact component identities in the portable manifest. A final on-host run of `python .\tools\verify_portable_installation.py` against that refreshed manifest is still required before calling the portable identity checkpoint fully re-qualified on this laptop.

## Installation authority split

`config/portable-installation-manifest.json` is the active component/host-compatibility contract for the new provider-neutral vertical-slice path.

`config/installation-manifest.json` (`acl-installation-manifest:v2`) is retained as the disabled legacy Codex proof/execution contract. It contains machine-specific pinned Python/Codex identities and must not be treated as portable host authority or edited merely to fit the current laptop or new tower.

The governing rule is:

`portable component identity -> host/provider qualification -> task-specific authorization -> execution`

Passing an earlier stage never implies the next stage. In particular, **provider qualified does not mean execution authorized**.

## Current stop condition

Execution stays disabled. Do not authorize or dispatch the historical prepared Phase 4 invocation, do not install Codex merely to satisfy the legacy v2 manifest, and do not select or run a local model as part of identity reconciliation.

The historical September 1 Phase 4 packet and earlier phase evidence remain valid historical records but are no longer the active next gate. The byte-preserved prior `docs/CURRENT_STATE.md` snapshot is archived at `docs/legacy/CURRENT_STATE_2026-09-01.md`.

## Immediate next gate

After the refreshed portable manifest passes the on-host verifier, perform **Host Provider Qualification V1** as a bounded design/implementation task:

1. define the exact provider-qualification evidence that satisfies `coding-worker:v1` without changing task scope or authority;
2. select one provider/harness candidate using the existing research, not a new broad research campaign;
3. bind provider executable/runtime/model identity to the host separately from the portable component manifest;
4. prove that provider qualification alone leaves execution disabled;
5. stop before the first real worker/model execution unless a separate supervised vertical-slice authorization is explicitly granted.

The first actual provider execution is reserved for the supervised vertical-slice proof.

## Historical state

The complete accepted state and Phase 1-4 development history through 2026-09-01 is preserved at `docs/legacy/CURRENT_STATE_2026-09-01.md`. Consult it for old proof identities, disposable run records, prior test counts, and the legacy Codex execution history; do not use its old "Immediate next gate" as current authority.
