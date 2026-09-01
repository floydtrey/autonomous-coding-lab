# Repository Instructions for AI and Coding Agents

These instructions govern the entire Autonomous Coding Lab repository. Historical `AGENTS.md` files under `docs/legacy/` are evidence only and do not govern current work.

## Required startup

1. Read `docs/START_HERE.md`.
2. Read `docs/CURRENT_STATE.md`.
3. Read only the task-specific document routed by `START_HERE.md`.
4. Inspect `git status` before writing and preserve work that is not yours.

Do not load all legacy or migration documents during routine startup.

## Authority and safety

- Treat the user's current request as the scope boundary.
- Configuration, installed software, prior tests, and historical capability do not grant execution authority.
- Do not run a worker, model, adapter execution mode, or alter an external/product repository without explicit current authorization.
- Planner and Local Model Bench outputs are advisory. Worker Lab must validate and authorize any resulting task contract.
- Worker Lab owns task authority, policy, role, lifecycle, and evidence acceptance.
- The framework owns execution security and repository containment. Do not duplicate or weaken those controls elsewhere.
- Stop at the first unresolved identity, authority, scope, or cleanliness contradiction.

## Scope discipline

- Complete the requested unit of work, validate it once at the appropriate level, and stop.
- Do not repeat a check whose accepted evidence is still current unless the relevant inputs changed.
- Do not create new governance files, test frameworks, recovery artifacts, or milestones unless the task requires them.
- Do not turn documentation cleanup into runtime adaptation, or runtime adaptation into redesign.
- Record a newly discovered problem; do not repair it unless repair is inside the current request.
- Prefer a small reversible change over a broad cleanup.
- Never stage, commit, push, publish, merge, or delete material unless the user requested that action.

## Repository boundaries

- `components/worker-lab/` is the control plane.
- `components/autonomous-worker-framework/` is the execution/security engine.
- `components/local-model-bench/` is independent advisory evaluation infrastructure.
- `config/` and root tools may connect components but cannot become a fourth authority source.
- `docs/legacy/` and `migration/inventory/` preserve evidence; they are not active instructions.

## Validation

Use the smallest test that covers the changed behavior, then the relevant component suite if the change can affect that component. Run a full repository-wide gate only for an integration checkpoint or when explicitly requested. Never run workers or local models merely to validate documentation.

When reporting completion, distinguish:

- accepted checkpoint evidence;
- validation performed on the current working tree;
- known but unmodified problems;
- actions intentionally not taken.
