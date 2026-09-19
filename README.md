# ACL Next

ACL Next is the clean rebuild of Autonomous Coding Lab.

This branch intentionally contains only the new implementation. The previous ACL
remains in repository history and on its existing branches as reference material,
but it is not part of this working tree and must not be imported as a runtime
dependency.

## Current scope

The first implemented layer is Core V0:

- identity and correlation;
- structured diagnostics;
- authority ceilings, grants, narrowing, and enforcement;
- generic resources and targets;
- generic tools and tool enforcement;
- replaceable adapter contracts;
- narrow transport normalization.

Core intentionally does not contain Controller workflow, AI roles, JobPlan,
validation policy, KC semantics, Git/GitHub assumptions, or old Worker Lab code.

Development proceeds by adding the new layers directly to this clean tree and
using the prior ACL only as external reference when a proven mechanism is worth
adapting.
