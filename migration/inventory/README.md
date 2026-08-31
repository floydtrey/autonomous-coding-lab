# Structural Inventory

This directory contains deterministic, machine-readable analysis of the exact
tracked Git trees selected for consolidation. Ignored files, runtime output,
working-copy residue, and excluded repositories are not inputs.

Generate the inventories from the ACL repository root:

```powershell
python -B tools\inventory_trees.py
python -B tools\plan_repairs.py
```

Query only the evidence needed for a review:

```powershell
python -B tools\query_inventory.py --status FAIL
python -B tools\query_inventory.py --repair SEMANTIC_REVIEW
python -B tools\query_inventory.py --path-type absolute_host --component WLAB
python -B tools\query_inventory.py --connects WLAB AWF
```

`snapshots.json` is the human-reviewed input. The component inventories bind
every current file to its source commit/tree/blob, source and destination path,
content digest, language, role, extracted code structure, and typed path
references. `findings.json`, `connections.json`, `summary.json`, and
`repair-plan.json` are reproducible derived outputs.

The tools read source repositories through Git object commands and never import
or execute component code. A repair plan does not grant edit, execution, commit,
push, or publication authority.
