# Structural Inventory

This directory contains deterministic, machine-readable analysis of the exact
tracked Git trees selected for consolidation. Ignored files, runtime output,
working-copy residue, and excluded repositories are not inputs.

Generate the inventories from the ACL repository root:

```powershell
python -B tools\inventory_trees.py
python -B tools\plan_repairs.py
python -B tools\inventory_integration.py
```

Query only the evidence needed for a review:

```powershell
python -B tools\query_inventory.py --status FAIL
python -B tools\query_inventory.py --repair SEMANTIC_REVIEW
python -B tools\query_inventory.py --path-type absolute_host --component WLAB
python -B tools\query_inventory.py --connects WLAB AWF
python -B tools\query_inventory.py --current --path-type absolute_host --component WLAB
python -B tools\query_inventory.py --current --connects WLAB AWF
python -B tools\query_inventory.py --delta --component WLAB
```

`snapshots.json` is the human-reviewed input. The component inventories bind
every current file to its source commit/tree/blob, source and destination path,
content digest, language, role, extracted code structure, and typed path
references. `findings.json`, `connections.json`, `summary.json`, and
`repair-plan.json` are reproducible derived outputs.

Source findings remain immutable provenance after integration repairs. The
separate `resolutions.json` binds a resolved finding to exact monorepo commit,
tree, destination blobs, and validation evidence without rewriting the source
snapshot.

`framework-m2-identity-evidence.json` records the exact clean commit verified by
the unwired framework-only identity checker. It is checkpoint evidence, not the
runtime policy and not execution authority; the runtime policy is the canonical
`config/monorepo-identity.json` file.

`current-awf.json` and `current-wlab.json` inventory every tracked file in the
imported component subtrees at one exact monorepo commit. `integration-delta.json`
compares those files with the immutable source inventories, including exact
path-reference and code-structure changes. `current-findings.json`,
`current-connections.json`, and `integration-summary.json` are derived from the
integrated trees. The integration scan fails closed if either component scope is
dirty and does not read or execute component worktree code.

`integration-repair-plan.json` groups the four remaining current-tree findings
into one guarded semantic packet. It explicitly disables automatic rewriting:
the remaining absolute pin and repository-root Git assumptions participate in
runtime identity and therefore require reviewed code plus negative tests.

The tools read source repositories through Git object commands and never import
or execute component code. A repair plan does not grant edit, execution, commit,
push, or publication authority.
