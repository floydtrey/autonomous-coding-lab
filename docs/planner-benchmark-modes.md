# Planner Benchmark Modes

ACL now keeps two Planner benchmarks with different purposes. Results from the two
modes must not be treated as interchangeable.

## Semantic-only benchmark

Tool: `tools/planner_output_benchmark.py`

Mode: `SEMANTIC_ONLY`

Purpose:

- compare raw planning quality across local models;
- observe decomposition, inspection choices, tool use, speed, and handoff quality;
- avoid forcing the production Planner response contract.

This benchmark intentionally bypasses the production semantic response validator,
semantic-to-ExecutionPlan compiler, plan intake, and production Planner profile.
A semantic-only success does **not** prove production compatibility.

## Production integration benchmark

Tool: `tools/planner_integration_benchmark.py`

Config: `config/planner_integration_benchmark.json`

Mode: `PRODUCTION_INTEGRATION`

Purpose:

- run a candidate through the actual Planner profile and agent adapter;
- use the production read-only tool profile and authority grant;
- require `acl-planner-semantic:v1`;
- validate and compile the semantic response into ACL's internal `ExecutionPlan`;
- optionally persist the plan through normal plan intake;
- capture ACL telemetry and raw role artifacts;
- record `ollama ps` observations around candidate execution.

Determiner is bypassed deliberately. Each case supplies the accepted work type and
complexity so this benchmark isolates Planner integration. Worker execution is not
started.

For each candidate the benchmark copies the repository's current `config/` directory
into the benchmark output directory and edits only the selected Planner runtime entry
for that candidate. This prevents benchmark-only prompts, tools, authority, or response
contracts from drifting away from production.

## Interpreting results

Use semantic-only results to answer:

> Can this model understand the work and produce a useful plan?

Use production-integration results to answer:

> Can this model do that through ACL's real Planner harness and semantic boundary?

Keep separate observations for:

- semantic planning quality;
- decomposition quality;
- read-only tool selection and efficiency;
- response-contract reliability;
- correction/retry count;
- context-pressure telemetry;
- elapsed time;
- actual Ollama residency/context observations.

A model can be semantically strong and integration-weak. That is evidence about the
model/harness seam, not grounds to rewrite the Controller around one benchmark result.
