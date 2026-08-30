# Source Inventory

**Status:** Preliminary M0 observations; not an import manifest

| Component | Source path | HEAD | Visibility | Import blocker or question |
|---|---|---|---|---|
| Worker Lab | `C:\Users\MineTrackerWorker\repos\worker-lab` | `ca55e30ccbcbf2318d73b3ef8a65f66bb9e1e684` | Private | Nine local commits not on remote; untracked history export; unreadable test-temp directories |
| Execution framework | `C:\Users\MineTrackerWorker\repos\autonomous-worker-framework` | `3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd` | Local only | No remote; unreadable test-temp directories; durable separate-repository decisions require replacement mapping |
| Local Model Bench | `C:\Users\MineTrackerWorker\repos\awf-live-consumer-smoke\2026-08-29\referenced-chatgpt-conversation-this-is-an\outputs\local-model-bench` | `4a023c8230365c3098a6dff71fa9623cac059cdd` | Public | Active ignored run must finish; decide which results become durable evidence |

## Required M1 inventory fields

For each source, record:

- branch, exact HEAD, tags, remote and ahead/behind state;
- tracked file manifest and license status;
- package/import layout and entry points;
- current test commands and last independently verified results;
- external absolute paths and cross-repository references;
- generated, ignored, untracked, temporary, secret-bearing, and large files;
- current authority documents and known stale conflicts;
- import-history method and initial landing path;
- selected evidence artifacts and explicit exclusions.
