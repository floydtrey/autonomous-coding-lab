# ACL Core

This component is the clean Core rebuild for Autonomous Coding Lab.

Core supplies mechanisms only:

- opaque identity and correlation;
- configurable structured diagnostics;
- authority ceilings, grants, narrowing, and mechanical enforcement;
- generic target and resource references;
- tool registration and grant enforcement;
- replaceable adapter registration and invocation;
- narrow syntax and transport normalization.

Core does not contain Controller workflow logic, AI role behavior, model selection,
retry policy, KC semantics, Git/GitHub assumptions, JobPlan logic, validation
policy, or task completion logic.

## Diagnostics

Diagnostics are emitted by Core operations themselves when those operations are
called. No separate logger process is required.

They are disabled by default. Configure them in process with
`configure_diagnostics(...)`, or externally with:

- `ACL_CORE_LOG_ENABLED=1`
- `ACL_CORE_LOG_LEVEL=DEBUG`
- `ACL_CORE_LOG_PATH=logs/acl-core.jsonl`
- `ACL_CORE_LOG_STDERR=0`

Supported levels are OFF, ERROR, INFO, and DEBUG.

Each JSONL record includes timestamp, severity, component, operation, event,
current correlation identifiers, and operation-specific details.

## Build status

This package is intentionally being built before its dedicated test campaign.
The previous ACL implementation remains the reference and parts bin. Pipeline
testing and systematic debugging come after the surrounding layers exist.
