# Controller Task Packet V1

**Status:** accepted non-executing vertical-slice checkpoint

**Accepted implementation checkpoint:** `64641aa978d4d4902b4a47439e256b0f50df136b`

**Execution authority:** `DISABLED`

## Purpose

Controller Task Packet V1 closes the first governed handoff from Knowledge Core retrieval into the existing Worker Lab / Autonomous Worker Framework workspace-write path without allowing retrieved content to become authority.

The packet is the canonical invocation prompt. Its exact UTF-8 bytes are therefore bound by the existing Worker Lab `prompt_digest` and are revalidated by the framework before worker execution can be reached.

## Authority boundary

The packet may carry:

- the original user request;
- the protected exercise identity and starting commit;
- controller identity;
- up to four current Knowledge Core segment evidence records;
- exact retrieved segment content and provenance.

Knowledge Core evidence is **informational only**. It cannot grant or modify:

- writable paths;
- readable target-repository paths;
- sandbox mode;
- policy or role identity;
- tests or validation commands;
- acceptance criteria;
- capabilities;
- publication or Git authority.

Those fields remain sourced from the protected Worker Lab exercise, policy, role, context manifest, test catalog, workspace receipt, and invocation lifecycle.

## Knowledge Core evidence contract

`worker-lab-knowledge-core-segment-evidence:v1` preserves enough provenance to bind content to the serving generation and source slice, including generation/profile identities, resource/version references, repository/path/version, lifecycle state, byte and line coordinates, source-slice SHA-256, and exact segment content.

Only `current` lifecycle evidence is accepted by this v1 handoff. Content SHA-256 and byte length are revalidated before the packet is accepted.

## Framework handoff

The Autonomous Worker Framework recognizes `worker-lab-controller-task-packet:v1` only when the prompt is canonical JSON and packet identity matches the authorized invocation. It exposes the user request and Knowledge Core evidence to the implementation prompt under an explicit informational-only boundary.

Legacy plain-text workspace-write prompts remain supported. This checkpoint does not require broad cleanup of historical Codex-specific paths.

## Accepted validation

On the current Windows development laptop at branch checkpoint `64641aa978d4d4902b4a47439e256b0f50df136b`:

- Worker Lab Controller Task Packet focused suite: **3 passed**;
- Autonomous Worker Framework Controller Task Packet focused suite: **3 passed**;
- portable installation verification: all three components `MATCH`;
- working tree after validation: clean;
- provider runtime qualified: `false`;
- execution authority: `DISABLED`;
- execution ready: `false`.

The focused framework tests use an injected fake executor against temporary repositories. No Codex, Qwen, local model, provider runtime, real worker, production adapter execution, authorization, dispatch, target product repository, commit, push, merge, or publication occurred.

## Closed boundary

The vertical-slice dependency chain is now:

1. Knowledge Core exact retrieval — accepted;
2. Knowledge Core Consumer V1 exact content serving — accepted;
3. portable ACL installation/host identity — accepted;
4. Controller Task Packet V1 / Knowledge Core evidence handoff — accepted;
5. provider-neutral worker/runtime seam — next;
6. select and qualify one local harness/provider;
7. first supervised end-to-end vertical slice.

## Deferred cleanup

Do not broaden this checkpoint into a general stale-code cleanup. Historical Codex/Terra assumptions, old Phase 1–4 proof records, legacy absolute paths, and unused prototype paths may remain until the first vertical slice exists unless they directly block the next dependency.
