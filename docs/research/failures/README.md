# Failure Research

Catalog real failures, abandoned approaches, and redesigns.

Look for:
- agents narrating instead of making required tool calls;
- malformed structured/tool output;
- runaway loops and retry storms;
- premature task completion claims;
- context loss or stale state;
- failures across restart/resume;
- weak validation that accepts incorrect work;
- local-model incompatibilities;
- excessive latency/cost;
- tool or permission overreach;
- prompt injection through retrieved content;
- poisoned persistent memory;
- multi-agent error propagation.

Each entry should state trigger, consequence, workaround/repair, and the ACL design implication.
