# V1 output-acceptance contract

S05b introduces `worker-lab-output-acceptance:v1`. Writable permission and output
obligations are separate, immutable inputs to independent acceptance.

```json
{
  "schema_version": "worker-lab-output-acceptance:v1",
  "allowed_writable_paths": ["src/a.py", "src/b.py", "src/c.py"],
  "required_changed_paths": ["src/a.py"],
  "required_artifact_paths": ["src/a.py"],
  "required_evidence": ["protected-test-results:v1", "worker-output:v1", "workspace-diff:v1"],
  "allow_noop": false
}
```

All path/evidence arrays are sorted and unique. Paths name exact files, without
patterns or traversal. Required file paths must be within the allowed set, which
must exactly match protected writable authority. A requirement never grants
permission. Required changes mean inclusion in the independently observed diff;
required artifacts mean regular files must exist in the candidate workspace.
Declare both when deletion would not satisfy the requirement. Content correctness
is determined by the protected criterion tests, not by existence alone.

`allow_noop: true` is valid only with an empty `required_changed_paths` array.
It permits, but does not force, an unchanged workspace. Required artifacts must
still exist and every sealed criterion test must pass. With `allow_noop: false`,
at least one allowed path must change even if no particular changed path is
required. Changes outside permission always fail.

## Result evidence

The supported explicit evidence types are:

| Type | Enforced evidence |
| --- | --- |
| `protected-test-results:v1` | Complete passing independent validation stages for the sealed test plan, retained in the result. |
| `workspace-diff:v1` | Independently observed changed paths and workspace content digest, retained in the result and candidate manifest; an empty diff is valid only with explicit no-op permission. |
| `worker-output:v1` | A valid SHA-256 digest of the worker response, retained in the result and candidate manifest. This is an output identity, not proof of a summary's meaning or correctness. |

Unknown evidence types reject. An empty required-evidence list adds no extra
obligations; it does not waive the runtime's mandatory custody, candidate identity,
and complete protected-validation checks. No worker claim can replace those checks.

Independent artifact inspection is bound to the sealed workspace path and the
observed candidate content digest. Missing files and filesystem links reject.

## Admission, transport, and compatibility

- Job Plan schema V2 replaces the old label list in `required_outputs` with this
  contract. Plan and task-definition digests bind it. Admission checks its allowed
  paths against the protected profile and its evidence types against the role.
- New preparation emits Invocation V4, adding `output_acceptance` to the existing
  record machinery and immutable invocation identity. Dispatch task V3 carries
  exactly the same contract; substitution fails.
- AWF's Code Task V2 gives the worker the allowed set and independently checks
  the declared obligations. Its Worker Result V2 permits a clean no-op handoff.
  Changed candidates may still use Worker Result V1.
- Worker Lab Result V4 permits an unchanged candidate only when its matching
  invocation explicitly allows it. Existing custody, source, validation, and
  candidate-manifest machinery remains in use.
- Old Invocation/Result V3 records remain readable. Writable paths are permission,
  so candidate changes are checked as a subset, never by forced equality. Old
  records cannot opt into no-op through missing fields.

Old job plans and output labels such as `changed-files`, `test-results`, and
`implementation-summary` are insufficiently specified and reject; they are not
silently translated. Existing exercise definitions can prepare when their role
names the explicit evidence types above. They receive no-op permission `false`
and no inferred per-file mutation requirement. Roles with ambiguous labels need
an operator-reviewed authority revision before new preparation. This change does
not rewrite installed authority or migrate existing approvals. The synthetic test
profiles explicitly declare the supported evidence types.

The existing job execution stop gate remains in place. Deterministic fixtures
exercise transport and independent acceptance without qualifying or launching a
real provider. S06 subsequently verified its original four acceptance cases
against this implementation: 17 Worker Lab output-acceptance tests and 46
directly affected AWF tests passed, with no further runtime changes required.
