from __future__ import annotations

import os

# These must be established before graphiti_core is imported. The hardened
# adapter also reasserts them at build time in case another caller imported
# Graphiti earlier in the process.
os.environ["SEMAPHORE_LIMIT"] = "1"
os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "false"

from knowledge_core_providers.graphiti_hardened import (
    HardenedGraphitiProjectionAdapter,
)

import graphiti_source_neutral_sync as task4_sync


# Reuse the accepted Task 4 source-neutral operator/validation flow verbatim;
# only replace the provider runtime with the Task 4.1 hardened adapter.
task4_sync.GraphitiProjectionAdapter = HardenedGraphitiProjectionAdapter


if __name__ == "__main__":
    raise SystemExit(task4_sync.main())
