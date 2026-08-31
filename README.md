# Autonomous Coding Lab

Private integration repository for the Worker Lab product, its bounded execution
framework, and the local-model evaluation tools that select and validate worker
roles.

## Current status

M1 governance is accepted. The execution framework's exact history and tree are
imported, standalone and prefixed full validation pass, and the known quick
validator prefix defect is isolated as P-008. Worker Lab and Local Model Bench
remain outside the monorepo pending their later import gates. Execution remains
disabled.

Start with [`docs/START_HERE.md`](docs/START_HERE.md).

Source-conversation witness reports and the exact reusable request live under
[`docs/handoffs/`](docs/handoffs/README.md).

Deterministic file, structure, path, and connection inventories live under
[`migration/inventory/`](migration/inventory/README.md).

## Intended components

- Worker Lab: task authority, roles, lifecycle, curricula, evidence, and review.
- Execution framework: sandboxed worker execution and repository boundaries.
- Local Model Bench: model selection, prompt experiments, and validation packets.

The product will be one program and one private repository, while these
responsibilities remain separate internal trust boundaries.
