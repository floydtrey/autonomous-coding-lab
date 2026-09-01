# Governance

## Governing principle

No component may grant itself more authority. Human intent, task authorization, execution capability, evidence, acceptance, and publication are separate decisions.

## Authority chain

1. The human defines the scope and grants any consequential permission.
2. Worker Lab resolves versioned policy, role, exercise, context, tests, and attempt identity.
3. The framework enforces execution security and the target boundary.
4. Evaluators produce evidence bound to the exact attempt and candidate.
5. A trusted controller accepts or rejects the result.
6. Publication and merge occur only through a separately authorized path.

If any required identity or approval is absent, the operation stops.

## Configuration is not authorization

An installed executable, model, provider URL, manifest entry, role file, or enabled feature only makes a capability addressable. It does not authorize a specific attempt. Likewise, a previous successful run does not authorize another run.

`config/` may identify installed components and integration expectations. It must not silently encode task approval.

## Protected definitions

Worker Lab policies, roles, curricula, exercises, context manifests, and evaluator catalogs affect what a worker may do and how it is judged. They are authority-bearing records. Changes require trusted review, versioning, immutable identity, and tests that preserve deny-wins behavior.

A worker must never modify the policy, task, expected evaluator behavior, or evidence rules governing its own attempt.

## Model and planner governance

- Local Model Bench evidence is advisory.
- Deterministic JSON/format success is not semantic correctness.
- Planner output is an untrusted proposal until requirements, dependencies, scope, ambiguity, and test coverage are validated.
- A coding worker cannot approve its own work.
- Model selection is role-specific; success in structured extraction does not prove planning, coding, diagnosis, or review fitness.
- Human review remains required until objective role-graduation evidence is accepted.

## Execution boundary

The framework permits only explicit `read-only` or `workspace-write` sandboxes. Full-access modes fail closed. ChatGPT-managed authentication is required; `OPENAI_API_KEY` and `CODEX_API_KEY` are forbidden for worker execution. GitHub credential-like environment variables are stripped.

Workers do not commit, push, merge, change Git configuration, or hold publication credentials. The target repository must be separate, explicitly named, identity-bound, and clean at the required starting commit.

Execution remains disabled for the consolidated installation until a bilateral installed-component identity contract is accepted and a specific attempt is authorized. The current installation-manifest v2 candidate records `DISABLED` execution and a `DEFERRED` Worker Lab participant. Worker Lab and the framework adapter enforce that policy independently; a valid manifest or runtime identity does not supersede it.

## Change authority

| Change | Required decision |
|---|---|
| Documentation correction | Normal scoped review |
| Component implementation | Component tests and scoped review |
| Cross-component protocol or identity | Bilateral tests, full affected suites, security review |
| Worker/model execution | Explicit task authorization and current identity preflight |
| External/product repository access | Explicit repository and operation scope |
| Commit, push, publish, or merge | Separate explicit authorization |
| Destructive cleanup or irreversible migration | Named targets, backup/rollback plan, explicit approval |

## Evidence and acceptance

Evidence must bind the relevant source/install identity, attempt, target commit, candidate, environment, test catalog, and result. A passing provider request, process exit code, or test subset is not interchangeable with whole-task acceptance.

Historical evidence remains useful when its inputs have not changed. Do not recreate it for ceremony. Revalidate when code, configuration, identity, environment-sensitive behavior, or the acceptance claim changes.

## Scope withdrawal

When a deeply integrated program capability is removed, treat removal as a forward change, not a request to erase history:

1. Freeze new work on the withdrawn capability.
2. Identify entrypoints, dependencies, shared infrastructure, data, tests, and documentation.
3. Separate capability-specific code from shared code.
4. Remove integrations in dependency order with regression evidence.
5. Preserve compatibility or data migration where required.
6. Put irreversible data deletion behind explicit approval.
7. Record what was intentionally retained and why.

Workers may implement bounded removal tasks, but the trusted controller owns the scope and the decision to destroy data.

## Anti-drift rule

One task should produce one bounded outcome and one proportionate validation record. Discoveries outside scope are reported, not automatically repaired. Accepted checks are not rerun unless their inputs changed. This rule exists to prevent circular audits from replacing forward progress.
