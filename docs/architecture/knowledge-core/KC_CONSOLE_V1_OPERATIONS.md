# KC Console V1 — Daily Use and C07 Tower Acceptance

Date: 2026-09-18

## Scope

This guide covers KC-C07 only: package daily use, export captured notes, protect/disable the legacy public-read gateway, deploy the already-qualified console against the verified tower Knowledge Core data identity, and perform the real-use acceptance.

C01-C03 are complete. This guide does not authorize Graphiti rollout, model work, bulk history ingestion, repository relocation, unrelated ACL changes, or a second Knowledge Core database.

## Verified tower identity carried forward from C01

The intended KC notebook deployment is the existing Cowork-era KC data pairing, without Cowork or a model server:

- existing PostgreSQL container: `knowledge-core-sr2-host-62329544d83c`;
- existing host database port: `55434`;
- existing database name: `knowledge_core_sr2_host`;
- existing immutable-artifact root: `%LOCALAPPDATA%\KnowledgeCore\task4-host-qualification-01\artifacts`;
- KC loopback port: `8765`;
- existing configuration source used only for one-time migration to the new console config: `C:\AI\start-kc-cowork-stack.bat`.

The existing launcher also starts Cowork and a local model and runs migrations. Do **not** use it as the daily notebook launcher.

## Deployment layout

Do not switch or merge the tower's active ACL checkout merely to deploy KC Console V1.

Use a separate Git worktree at a deployment path such as:

`C:\Projects\kc-console-v1`

The daily launcher resolves KC relative to its own checkout, so there is no hardcoded ACL repository root inside the launcher. The later standalone-repository move can replace this worktree without changing the database/artifact identity.

The populated host config remains outside Git at:

`%LOCALAPPDATA%\KnowledgeCore\console-v1\console.env`

It contains credentials and must not be committed.

## One-time deployment order

1. Create/update the separate `kc-console-v1` worktree at the accepted GitHub branch head.
2. Create the KC component-local Python 3.12 virtual environment and install `.[service]`.
3. Run `tools\windows\Prepare-KCConsoleConfig.ps1`.
   - It reads the verified existing launcher without executing it.
   - It preserves the existing DB URL, artifact root, bootstrap key, bind host, port, and PostgreSQL-container identity.
   - It generates a separate console-owner key.
   - It writes the populated config outside Git.
4. Run `tools\windows\Disable-KCLegacyGateway.ps1`.
   - It records the existing `kc-api` / `kc-apisix` restart/running state.
   - It sets their restart policies to `no` and stops them.
   - It does not delete containers.
   - `Restore-KCLegacyGateway.ps1` can restore the recorded state later if an external integration is deliberately reintroduced.
5. Run `tools\windows\Apply-KCConsoleMigration.ps1`.
   - This is the only C07 helper that applies Alembic migrations.
   - It uses the configured existing database.
   - It does not start KC, Cowork, a model, or Graphiti.
6. Run `tools\windows\Install-KCConsoleShortcut.ps1`.
7. Launch the new **Knowledge Core** Desktop shortcut.
   - It starts only the configured existing KC PostgreSQL container when needed.
   - It starts only `kc_bootstrap_service.py`.
   - It does not kill an unknown process already using port 8765.
   - It does not run migrations.
   - It does not start Cowork, llama.cpp, Ollama, Graphiti, FalkorDB, or another model service.
   - The shortcut copies the separate console-owner key to the clipboard for the local login unless that option is disabled.

## Daily use

Open the **Knowledge Core** Desktop shortcut.

The console provides:

- Add note;
- Recent notes;
- exact Original;
- PostgreSQL lexical Search with evidence;
- bounded Status;
- JSON **Export notes**.

A successful save receipt proves canonical settlement for that submission. Search-index readiness is reported separately.

The JSON export is `kc-console-export-v1`. It contains each authorized direct-note original plus capture/source metadata, observation/submission/resource/version identities and SHA-256 digest. The export freezes the eligible observation set first and rechecks every original while assembling it. If an included note becomes unavailable or fails integrity checks, the endpoint returns an error instead of a successful partial export.

The export is a human-readable recovery aid. It is not a substitute for PostgreSQL/artifact-store backup and restore.

## Gateway privacy requirement

Public read access is not part of KC Console V1.

Before storing sensitive daily information:

- the legacy `kc-api` and `kc-apisix` containers must be stopped with restart disabled, or equivalently protected by a separately verified access-control design;
- the previously observed public-read URL must no longer return KC data;
- the local console must remain reachable only through the loopback-bound KC service.

C07 acceptance uses the **disabled gateway** path. Restoring the gateway later is a separate deliberate action.

## Real-use acceptance

Use five genuine notes the owner wants to retain. Do not create another benchmark project merely for C07.

For the five-note acceptance:

1. Confirm model services, Cowork and Graphiti are not required/running for the notebook workflow.
2. Save five genuine notes using the console and retain each successful canonical receipt.
3. Confirm all five appear in Recent.
4. Search for distinctive terms from the saved notes and confirm the correct evidence/results.
5. Open each exact Original and compare with what was submitted.
6. Export notes and confirm all five originals plus metadata are present in the JSON.
7. Stop only the KC console service with `Stop-KCConsole.ps1`; leave the persistent stores intact.
8. Start KC again from the Desktop shortcut.
9. Confirm the five notes still appear in Recent, Search, Original, and Export.
10. Record the accepted branch head, migration head, gateway-disabled state, database container identity and artifact root.

No model or Graphiti service is permitted as a hidden prerequisite for this acceptance.

## Failure handling

- If port 8765 belongs to an unknown process, stop and identify it; the daily launcher deliberately does not kill it.
- If the expected PostgreSQL container is absent, stop. Do not create a replacement database.
- If migration reports a database other than the configured existing KC database, stop.
- If the console cannot read an existing note after migration, stop before saving new real information.
- A search failure is not an empty search.
- An export failure is not a successful partial export.
- Do not use the legacy Cowork stack launcher to recover C07.

## Completion gate

C07 is complete only after:

- the GitHub implementation remains green;
- the legacy public-read path is disabled/protected;
- the dedicated KC-only launcher and Desktop shortcut work;
- the tested migration is applied to the verified existing KC database;
- five genuine notes survive a KC service restart;
- Recent, Search, exact Original and JSON Export all work after restart;
- model services and Graphiti remain unnecessary for the accepted workflow.

Repository separation remains deferred until after this gate.
