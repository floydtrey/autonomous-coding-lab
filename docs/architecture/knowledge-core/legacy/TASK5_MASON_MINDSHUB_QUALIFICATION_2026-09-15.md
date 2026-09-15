# Task 5 Mason / MindsHub qualification — 2026-09-15

This record preserves the intended-host qualification evidence for the bounded Task 5 Mason -> Knowledge Core consumer path. It does not qualify Graphiti, remote access, generalized Authority, automatic Cowork routing, or arbitrary tool access.

## Qualified boundary

The accepted Task 5 path is:

```text
MindsHub/Cowork Mason
  -> Anton procedural-memory `recall_skill("knowledge-core")`
  -> Anton scratchpad
  -> project-local `knowledge-core-tools/mason_kc_bridge.py`
  -> loopback Knowledge Core bootstrap API
  -> accepted lexical/current canonical evidence
```

The bridge exposes exactly four literal protocol operations:

```text
kc_status
kc_search
kc_get_source
kc_store
```

The bridge remains fail-closed for unsupported operation names and does not provide SQL, FalkorDB, Graphiti-maintenance, artifact-store, arbitrary HTTP, or arbitrary KC access.

## Host observations

The configured Cowork project was `Mason-KC-Test`, backed by `C:\Projects\mason-kc-test`.

Installer verification established:

- the Cowork skill `knowledge-core` was enabled and scoped to `Mason-KC-Test`;
- the project-local bridge existed at `C:\Projects\mason-kc-test\knowledge-core-tools\mason_kc_bridge.py`;
- project `.anton\.env` contained both required KC environment names without exposing the key value;
- direct project-local `kc_status` execution returned `ok=true`, `text_state=ready`, canonical revision `9`, and text source count `4`.

The live MindsHub/Cowork Mason model alias was `qwen3.5-9b-worker`.

## Live skill and retrieval evidence

A bounded skill/status test proved:

1. `recall_skill` with label `knowledge-core` succeeded.
2. Anton reached the project-local bridge through scratchpad.
3. One model-generated invocation shortened `kc_status` to `status`; the strict bridge rejected it with `unsupported Knowledge Core operation: status`.
4. Repeating with the literal CLI argument `kc_status` succeeded and returned the ready status above.

The accepted factual-retrieval test then asked Mason to search Knowledge Core for `Who is Mason?` and retrieve the canonical source. Mason:

1. used the Knowledge Core skill;
2. executed `kc_search`;
3. followed the returned ResourceVersion with `kc_get_source`;
4. returned the exact canonical content:

```text
Mason is my local MindsHub worker model.
```

The reported provenance was a current direct user note in project `local-ai`, item key `task4-mason-note`. The accepted answer came from KC retrieval plus canonical source follow-through, not from project-file or general-knowledge fallback.

## Hardening outcome

The observed `status` abbreviation did not justify weakening the bridge protocol. Instead, the skill was hardened so `kc_status`, `kc_search`, `kc_get_source`, and `kc_store` are documented as literal protocol identifiers that must never be shortened, translated, aliased, or stripped of the `kc_` prefix. Explicit helpers carry the literal strings.

This is instruction-level hardening only; the accepted bridge security boundary remains exact.

## Acceptance

Task 5 explicit Mason -> KC retrieval is accepted when the corresponding branch CI is green. Graphiti Task 4/4.1 qualification is independent because this path consumes the already accepted canonical/lexical KC front door and does not require graph readiness.
