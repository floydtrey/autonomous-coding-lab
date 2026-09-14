# Operations

This guide describes the current reconstructed ACL runtime. It does not authorize model execution.

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

Provider installation observation is an explicit operation and may contact the
named provider endpoint. Run it only when that host/provider is available for ACL:

```text
python -m worker_lab.cli --root <lab-root> observe-provider-installation \
  --model <exact-model-name> \
  --base-url <provider-base-url> \
  --provider-executable <provider-executable>
```

This records installation facts only. It neither proves capability nor grants
execution authority. Capability qualification currently requires an explicitly
supplied service probe runner; there is intentionally no normal CLI command that
can silently supply one.

After qualification, create a Provider Binding for the exact model/configuration and sealed runtime settings. Qualification and binding still do not authorize a task.

```text
python -m worker_lab.cli --root <lab-root> create-provider-binding \
  <binding-id> \
  --qualification-digest sha256:<digest>
```

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

The MA-2 composition is an application-service construction boundary, not a
normal CLI default. An operator must explicitly name the state root, protected
framework root, Provider Binding identity and digest, clock, and contained
runner. The production construction revalidates the durable qualification chain,
installed executable/harness bytes, and portable source identity before starting
the fixed framework adapter command under Windows Job Object custody.

## 6. Candidate review and evidence

A provider/framework success response is not acceptance. Worker Lab reruns protected tests and independently observes capability-specific workspace evidence before producing Result V3 and promoting an attempt to candidate state.

## 7. Containment

Windows Job Objects are the current Windows containment backend. Durable custody is backend-neutral. A different OS requires a compatible containment backend plus qualification; it must not require changing portable source identity.

## 8. Backup and restore

Worker Lab backup/verify/restore commands remain available for durable state. Always verify a backup before relying on it for recovery.

## 9. Benchmarking

Local Model Bench is advisory and separate from runtime authority. Benchmark a model/configuration before role assignment when useful, then qualify the chosen exact runtime through the provider qualification path. Benchmark scores alone are never Provider Binding evidence.

## Current stop condition

Reconstruction Tasks 1–9 are complete. Model-admission preparation is active,
but real provider qualification and model execution remain stopped until the
user separately authorizes a supervised run.
