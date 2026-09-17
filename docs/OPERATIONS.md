# Operations

This guide describes the current reconstructed ACL runtime. It does not authorize model execution.

The sequential controller does **not** exist yet. The commands below are component-level operations, not an automated V1 workflow. The next implementation milestone is that controller, initially using exact-file worker authority and controller-side validation.

## 1. Verify portable source identity

From the repository root:

```text
python tools/verify_portable_source.py
```

A valid report uses `acl-portable-source-report:v2` and reports every component as `MATCH`. The report intentionally contains no host qualification, provider qualification, activation, or execution-readiness claim.

## 2. Inspect Worker Lab source status

From `components/worker-lab` with the package importable:

```text
python -m worker_lab.cli source-status
python -m worker_lab.cli doctor
```

Both validate the same committed source identity. They do not qualify the host/provider and do not enable execution.

## 3. Host/provider qualification boundary

Provider installation observation records the actual host/Python/harness/provider/model facts. Controlled capability qualification additionally proves the protected bounded-file tool fixture and requested context target.

There is no default capability probe runner. Do not perform real capability qualification during reconstruction unless separately authorized.

After qualification, create a Provider Binding for the exact model/configuration and sealed runtime settings. Qualification and binding still do not authorize a task.

## 4. Prepare a V3 invocation

The current CLI preparation surface requires a logical target and exact Provider Binding:

```text
python -m worker_lab.cli --root <lab-root> prepare-invocation <attempt-id> \
  --workspace-root <workspace> \
  --prompt-file <controller-task-packet.json> \
  --logical-target-id target:<logical-name> \
  --provider-binding-id <binding-id> \
  --provider-binding-digest sha256:<digest>
```

The prompt must be the canonical Controller Task Packet expected by the protected attempt. Git checkout paths are workspace locators, not logical target IDs.

## 5. Authorization and dispatch

Authorization requires the exact prepared invocation identity and controller identity. Dispatch additionally requires the exact workspace and an injected current V3 dispatch runner.

The normal CLI constructs no provider runner. Therefore source verification, doctor, preparation, and authorization do not silently start a model/provider. Missing runner/provider/custody evidence fails closed.

## 6. Candidate review and evidence

A provider/framework success response is not acceptance. Worker Lab reruns protected tests and independently observes capability-specific workspace evidence before producing Result V3 and promoting an attempt to candidate state.

Initial V1 workers read and write only exact authorized files. Protected test execution and result validation belong to the controller side through Worker Lab; workers receive no shell or test-process authority.

## 7. Containment

Windows Job Objects are the current Windows containment backend. Durable custody is backend-neutral. A different OS requires a compatible containment backend plus qualification; it must not require changing portable source identity.

## 8. Backup and restore

Worker Lab backup/verify/restore commands remain available for durable state. Always verify a backup before relying on it for recovery.

## 9. Benchmarking

Local Model Bench is advisory and separate from runtime authority. Benchmark a model/configuration before role assignment when useful, then qualify the chosen exact runtime through the provider qualification path. Benchmark scores alone are never Provider Binding evidence.

## Current stop condition

Task 9 passed at its reconstruction checkpoint. Execution remains `DISABLED`; this acceptance neither supplies the missing sequential controller nor qualifies a provider. Real capability qualification, model execution, and persistent activation still require separate explicit authorization. No provider or Pi integration is declared qualified by this guide.
