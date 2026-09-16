# Knowledge Core Task 6H — Context Compaction Core

Date: 2026-09-16

## Accepted checkpoint

- Accepted behavior-bearing checkpoint: `15a41adb0cabda49f8fed189114d12092a2ce438`.
- Base accepted Task 6G merge: `7955cbd9e40c6854b4260acfeda096c58a2bcf55`.
- Pull request: #17, `KC Task 6H: deterministic context compaction core`.
- Qualification: GitHub Actions `35065713770`, fully green on the exact behavior checkpoint.

## Qualified files

The behavior checkpoint changes exactly these Task 6H files relative to the accepted Task 6G merge:

- `components/knowledge-core/knowledge_core/integrations/context_compaction.py`;
- `components/knowledge-core/tests/test_task6h_context_compaction.py`.

Later Task 6H commits are documentation/evidence only and do not change these qualified bytes.

## Accepted behavior

Task 6H adds a model-free client/integration-layer working-context contract. It does not make Knowledge Core own short-term conversation state. KC remains the durable knowledge/evidence system; the worker wrapper may use this bounded structure as transient working memory.

`kc-worker-context-checkpoint-v1` preserves:

- the current objective;
- immutable constraints;
- exact KC/evidence references;
- completed work;
- current state;
- blockers;
- recent actions and outcomes;
- exact source/output references;
- optional deterministic reduced tool-output excerpts;
- optional previous-checkpoint digest for explicit chaining.

Checkpoint payloads are canonical-JSON digestible and capped at 32 KiB UTF-8. The same ordered inputs produce the same digest/rendering. The core performs no model summarization and does not invent conclusions about omitted history.

`kc-tool-output-reduction-v1` provides bounded deterministic reduction for large tool output. Short output is preserved exactly. Long output selects bounded head/tail lines plus lines matching a fixed diagnostic vocabulary, preserving original line numbers. Every reduction retains the exact raw-output reference, SHA-256, byte count, line count, selected lines, and omitted-line count.

The reduced excerpt is not canonical evidence and is not a substitute for the referenced complete output. A caller that cannot retain an exact raw-output reference cannot use this reducer as the accepted compaction path.

## Explicit non-scope

Task 6H does not:

- wire compaction into MindsHub/Cowork or Mason;
- decide when a live conversation should compact;
- calculate model-specific token budgets;
- run a tokenizer, LLM, provider, or model;
- call KC search/store APIs;
- create or promote a memory candidate;
- write canonical KC knowledge;
- change graph retrieval/build behavior;
- change Worker Lab portable source identity;
- activate ACL execution;
- create a scheduler or background loop.

Those runtime integration choices remain Task 6I.

## Qualification

Actions `35065713770` passed on exact head `15a41adb0cabda49f8fed189114d12092a2ce438`:

1. PostgreSQL migrations;
2. fast semantic suite, including Task 6H deterministic compaction tests;
3. PostgreSQL G1–G21 qualification suite;
4. pinned SR-2 G22 real-document pilot;
5. RI-4 local-host restart rehearsal;
6. SR-2 local-host segment restart/replay rehearsal.

Focused Task 6H tests verify deterministic checkpoint digest/rendering, previous-checkpoint chaining, required section preservation, bounded checkpoint growth, exact raw-output identity, exact preservation of short output, repeatable long-output reduction, diagnostic/boundary line retention, and fail-closed rejection of a missing raw-output reference.

## Next boundary

Task 6H acceptance authorizes Task 6I: integrate the accepted compaction/checkpoint contract and Task 6G memory-candidate handling into the endpoint wrapper around Mason/Cowork. Task 6I is the first slice in this sequence that necessarily depends on the local worker runtime for end-to-end qualification. Task 6J remains the later comparative qualification campaign.