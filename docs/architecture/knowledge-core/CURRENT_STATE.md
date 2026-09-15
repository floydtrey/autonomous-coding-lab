# Knowledge Core — Current State

**Authoritative KC status and restart point. Updated 2026-09-15.**
Branch: `architecture/knowledge-core`. Documentation consolidation baseline:
`2678e7666fbcba50b64d8839ea0592a8d992e916`.
Latest accepted KC Usable V1 implementation checkpoint:
`5f6cdef96c9d4fcd36db8821df9c0156148080ae`.

## Read order and authority

After the repository [agent rules](../../../AGENTS.md), read these three current KC documents:

1. **This document** — accepted status, remaining work, and restart boundary.
2. [ARCHITECTURE.md](ARCHITECTURE.md) — current invariants and service/consumer contracts.
3. [OPERATIONS.md](OPERATIONS.md) — development, qualification, evidence index, and checkpoint rules.

These are the only authoritative current KC documents. [legacy/](legacy/README.md) holds frozen historical documents and accepted evidence outside the default read order. Old status, stop-gate and next-task prose in the archive describes earlier checkpoints and must not be resumed as current instructions. Archiving a decision or qualification record does not revoke its accepted invariants or evidence.

[Root current state](../../CURRENT_STATE.md) governs ACL runtime and execution authority. KC provides informational evidence; it does not authorize execution. ACL remains **DISABLED**. KC qualification does not activate ACL.

## What is accepted and usable

| Area | Current boundary |
|---|---|
| Kernel V1 and PostgreSQL | Accepted canonical history, identities, exact source provenance, idempotency, concurrency and serving fences. |
| Governed repository import | Accepted bounded exact-object import, stable document identity, governed observations and persistence/recovery. Repository import remains a strongly verified Git producer while downstream governed evidence/publication/retrieval is source-neutral. |
| RF-2 lexical retrieval | Accepted whole-document PostgreSQL baseline retained for historical qualification/reconstruction. A central fence prevents RF-2 from replacing an established SR-2 current TEXT generation. |
| SR-2 segmentation/publication | Accepted KC-D025/SR-1 implementation; G1–G22 green. Task 2D made live SR-2 selection/lineage/publication consume complete source-neutral governed snapshots. |
| SR-2 intended host | Accepted Windows/PostgreSQL restart/recovery, structural reconstruction, provenance, segment serving and replay. Current CI restart rehearsals remain green through Task 3. |
| KC Consumer V1 / lexical API | Task 2F accepted. `POST /v1/retrieval/search` remains the Authority-first semantic search route over `kc-lexical-evidence-v2`; mixed repository + direct-note evidence is source-neutral and exact. |
| KC Usable V1 bootstrap access | Task 1 accepted. Bind host remains configurable/default `127.0.0.1`; shared-key admission maps accepted bootstrap calls to fixed principal `local_owner`. This is replaceable bootstrap policy, not final Authority or permanent topology. |
| Source-neutral governed-source contract | Task 2A accepted. Logical source identity, Resource/ResourceVersion identity, immutable observations, governance decisions, project membership and complete retrieval snapshots are separate. |
| Source-neutral governed evidence persistence | Task 2B accepted behind migration `0016_governed_source_evidence.py`. |
| Repository producer integration | Task 2C accepted. Repository import produces matching generic governed evidence and cannot be silently downgraded by the legacy RF-2 writer. |
| Source-neutral SR-2 publication | Task 2D accepted behind migration `0017_sr2_source_neutral_lineage.py`; generic observation/decision/snapshot lineage is authoritative and repository fields are nullable compatibility provenance. |
| Direct-note `kc_store` front door | Task 2E + 2E.1 accepted. Authenticated `user_note` submissions create exact canonical evidence, merge into the complete corpus, preserve project memberships across same-source updates, classify retryable predecessor races separately from permanent derived failures, and retain canonical data if derived publication fails. |
| Task 2 source-neutral ingestion/read boundary | Accepted through 2F. Direct notes and repository evidence coexist in one current generation and are searchable through exact generic provenance after reconstruction/restart. |
| **Usable V1 simple read surface** | **Task 3 accepted.** With explicit `BootstrapAdmission`, `POST /v1/kc/search`, `POST /v1/kc/get-source`, and `GET /v1/kc/status` provide shared-key local reads as `local_owner`. Search reuses the accepted Task 2 lexical evidence contract; source follow-through is limited to current-generation, serving-eligible exact ResourceVersions and revalidates immutable byte size/SHA-256; status exposes bounded canonical/text readiness without storage internals. |
| Projection attempt and validation ledgers | Implemented durable, separate provider-attempt and independent validation evidence. Provider success alone is insufficient. |
| Governed Graphiti backend | Accepted historical governed-document projection, immutable build isolation, lifecycle validation and trusted canonical result correlation. Its current plan input/reference-time path is still repository-shaped; mixed-source graph generalization is Task 4. |
| Public graph consumer API | Not exposed/promoted. Trusted graph retrieval exists in the application kernel; public front-door reads remain lexical. |
| ACL consumer boundary | Governed segment evidence can enter Controller Task Packet V1 as informational context; execution remains disabled. Existing repository-shaped ACL compatibility does not redefine generic KC identity. |
| Mason / MindsHub | Integration not implemented in this checkout. Task 5 is planned after Task 4. |
| Vera | Future consumer work. |

Acceptance applies to recorded checkpoints and bounded scenarios. It is not a claim of production deployment, comprehensive answer quality, machine reboot/backup qualification, or fresh qualification of every future file. Exact records are indexed in [OPERATIONS.md](OPERATIONS.md#accepted-evidence).

## Latest accepted Graphiti result

The [2026-09-14 acceptance record](legacy/GRAPHITI_GOVERNED_QUALIFICATION_2026-09-14.md) seals implementation checkpoint `6376419e369ea9ecfe58a19fa233bbfca90ad703`:

- Graphiti `0.30.2`, LLM alias `graphiti-qwen38-27b-32k`, embedder `nomic-embed-text:latest`.
- Ruleset `kc-graphiti-governed-document-v3`; validator `kc-graphiti-live-validator`, version `3`.
- Attempt `ea7eba74-912f-5e88-9271-f59670066d88`; validation `df9eabde-5a63-5f70-9478-27b74bd07684`.
- Projection `succeeded`, validation `validated`, 17/17 source bindings, 7/7 checks passed, zero integrity warnings.
- 10/10 returned search results had canonical attribution.
- Complete inventory of 48 edges / 48 source contributions; zero retired, missing-attribution, unknown-source, wrong-partition or multi-source anomalies.

This accepted graph result predates the source-neutral Task 2 changes. It remains valid historical evidence for its exact repository-shaped input/build, not qualification of mixed-source graph planning. Retrieval ranking and answer quality remain separate concerns.

## KC Usable V1 — current objective

**Usable V1 goal:** a local consumer can store governed information, retrieve it in a fresh session, inspect exact canonical source evidence, and later use validated Graphiti retrieval without direct access to PostgreSQL, the artifact store, or FalkorDB.

The store/search/source/status portion of that goal is now accepted through Task 3. The remaining Usable V1 work is explicit mixed-source Graphiti synchronization/validation, then Mason tooling and dogfooding.

Bootstrap choices are intentionally replaceable. The initial service address is configurable and starts at `127.0.0.1`; localhost is a deployment choice, not a permanent architecture rule. Initial access uses shared-key authentication and bootstrap principal `local_owner`. The existing Authority seam remains intact; generalized Authority is deferred until broader consumers, permissions, remote access, or a demonstrated policy problem requires it.

Accepted local consumer operations are:

```text
kc_store
kc_search
kc_get_source
kc_status
```

Graph maintenance remains separate:

```text
store -> canonical Resource/ResourceVersion -> governed text retrieval
      -> graph pending -> explicit Graphiti sync -> validation -> trusted graph
```

Graph failure or delay must not invalidate successfully stored canonical evidence or otherwise valid text retrieval.

## Task 2 source-model audit result

The read-only audit at checkpoint `f6f049f54789381ffa581ca9b28930a4d98ee450` found that canonical Resource/ResourceVersion/artifact storage was largely source-neutral while governed retrieval embedded repository/Git assumptions in source selection, durable lineage, generation construction/publication, lexical serving/public schemas, Graphiti plan reconstruction/reference time and downstream evidence schemas.

Task 2 corrected the ingestion-through-lexical-serving path without weakening Git verification or replacing canonical identity. Repository import is now one verified producer of generic governed evidence, not the definition of every source.

The accepted model keeps distinct:

1. Resource — KC logical canonical object.
2. ResourceVersion — exact canonical bytes/content identity.
3. Governed source identity — logical origin item; project is not origin identity.
4. Observation/admission evidence — a specific capture/submission of an exact ResourceVersion.
5. Governance decision — lifecycle/classification/rank inputs admitted by KC.
6. Governed retrieval snapshot — immutable complete selected corpus and policy inputs.
7. Project/context membership — separate, potentially many-to-many association.

Time semantics remain distinct where available: source event time, source revision time, KC observation/admission time, and derived-provider reference-time policy.

One-current-TEXT fencing remains. Producers publish complete predecessor-bound corpus snapshots rather than producer-local subsets. Publication checks the expected serving predecessor under the generation lock, so stale competing writers cannot erase newer contributions. Task 2F extends this discipline to reads: the complete current SR-2 source lineage is reconstructed and checked before a result is trusted.

Historical repository manifests, observations, digests, accepted generations, migrations and graph qualifications retain their original interpretation. The legacy RF-2 importer remains available for historical qualification/reconstruction from an empty/RF-2 state but cannot replace established SR-2.

## Bounded task sequence

Work sequentially. Do not silently absorb later tasks into an earlier task.

### Task 1 — bootstrap access contract — ACCEPTED

Implementation checkpoint `b9e708f2892f3a7303fa50ccadc64c26f5b9bf46`; full workflow [Actions 34877670577](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34877670577) green.

Accepted: configurable bind default `127.0.0.1`, shared key `X-Knowledge-Key`, fixed `local_owner`, spoof-resistant principal mapping, bounded admitted operations `kc.store`, `kc.search`, `kc.get_source`, `kc.status`. This is not generalized Authority or remote-exposure qualification.

### Task 2 — source-neutral governed ingestion + lexical evidence — ACCEPTED

Task 2 is accepted across bounded slices 2A–2F. It establishes one source-neutral path from verified producer evidence through canonical ResourceVersion, governed observation/decision, complete SR-2 publication and exact lexical serving.

#### Task 2A — generic governed-source contract — ACCEPTED

Checkpoint `cbfecbfada73e1210ceae0185a31664bf073a479`; [Actions 34923452994](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34923452994) green.

Pure-domain contract separates source identity, Resource binding, evidence refs, observation, decision, project membership and complete predecessor-bound snapshot. Git/note/chat/email/benchmark-shaped fixtures challenge shape only; future connectors are not implemented.

#### Task 2B — generic durable evidence + legacy mapping — ACCEPTED

Checkpoint `6910e9abba320e272b34b0528846f289d3d8eb14`; [Actions 34925025743](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34925025743) green.

Migration `0016_governed_source_evidence.py` persists source-neutral bindings, observations, producer evidence, decisions, snapshots, project memberships and exclusions. Deterministic legacy mappings correlate settled repository evidence without rewriting historical RI records.

#### Task 2C — repository import becomes a verified producer — ACCEPTED

Checkpoint `30d1ec2ce13ae8c95afc4ac2b9d54d959f36b3bd`; [Actions 34927229037](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34927229037) green.

The live repository path publishes SR-2, settles matching generic evidence, fails closed if mapping cannot complete, preserves prior current serving state on failure, and adds the RF-2→SR-2 downgrade fence.

#### Task 2D — source-neutral SR-2 selection, lineage and publication — ACCEPTED

Checkpoint `08d76ab86f011c30a103b080b7fce821bf71c45c`; [Actions 34929951401](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34929951401) green.

Migration `0017_sr2_source_neutral_lineage.py` adds generic observation/decision/snapshot/projection lineage while retaining nullable repository compatibility fields. V2 generation validates canonical artifact SHA-256/size, strict UTF-8, deterministic segmentation and generic governance without requiring Git proof. Complete successor publication is predecessor-checked and atomic.

#### Task 2E — direct-note producer + `kc_store` — ACCEPTED

Checkpoint `9c89e30b9f0fa264180ac57a3e41d01ca0c74699`; [Actions 34931501178](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34931501178) green.

Authenticated `source_type="user_note"` through `POST /v1/kc/store`; fixed `local_owner`; deterministic parent/child operation composition; exact canonical SHA-256 evidence; complete mixed repository+note successor generation; canonical-first durability on derived failure; exact canonical replay after application reconstruction.

#### Task 2E.1 — pre-2F audit corrections — ACCEPTED

Implementation checkpoint `c0864a1d1ed76bdd5e289308f85f2b8b4d0499ba`; PR qualification [Actions 34934614070](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34934614070) and real-branch post-merge [Actions 34935097246](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34935097246) green.

Accepted corrections: generic snapshot policy ownership, retryable predecessor-conflict classification, `failed` versus `pending`, 255-character project prevalidation, same-source project-membership union, and accurate canonical idempotency wording. No migration or lexical/Graphiti expansion.

#### Task 2F — source-neutral lexical evidence + Task 2 qualification — ACCEPTED

Implementation checkpoint `f48200f50ee1c2652e32b56592f6ad86fe83c898`; full Knowledge Core workflow [Actions 34936164155](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34936164155) green.

Accepted: `kc-lexical-evidence-v2`, `governed-source-sr2-v2`, mixed repository+note search, exact generic provenance, explicit repository compatibility, complete-generation lineage validation before serving, artifact/slice/eligibility rechecks, restriction dominance, lineage-tamper fail-closed behavior, and concurrent store convergence. Historical pre-2D SR-2 retains explicit repository evidence semantics.

### Task 3 — simple read surface — ACCEPTED

Implementation checkpoint `5f6cdef96c9d4fcd36db8821df9c0156148080ae`; full Knowledge Core workflow [Actions 34937735966](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34937735966) green on the unchanged rerun after one transient RI-4 host-harness migration startup failure.

Implemented and qualified:

- with explicit `BootstrapAdmission`, `POST /v1/kc/search`, `POST /v1/kc/get-source`, and `GET /v1/kc/status` are exposed; without bootstrap admission they are absent;
- all three require `X-Knowledge-Key` and use their existing Task 1 operation classes, mapping successful admission to fixed principal `local_owner`;
- `kc_search` reuses the accepted Task 2 lexical reader and `kc-lexical-evidence-v2`; it does not create a second search/index path. If the trusted host also supplies the separate retrieval Authority evaluator, that evaluator remains an additional fail-closed policy layer for bootstrap search;
- `kc_get_source` accepts a ResourceVersion reference returned by search and only serves it when it belongs to the current TEXT generation and remains serving-eligible. It revalidates the current SR-2 contract, reads the exact immutable artifact, checks byte size and SHA-256, requires strict UTF-8, and exposes no artifact path/backend or database internals;
- unknown, non-current, or restricted source requests return nondisclosing 404 rather than becoming a UUID-based bypass around serving fences;
- `kc_status` reports bounded canonical/text readiness (`empty` or `ready`), current text generation/highwater/source count, retrieval mode, lineage mode, evidence-contract version and generation-config digest without claiming graph readiness or exposing storage credentials;
- operation scoping is enforced independently: a bootstrap contract admitting only `kc.status` receives 403 for search/source and 200 for status;
- the usability milestone is achieved in qualification: store `Mason is my local MindsHub worker model`, reconstruct the application/client boundary, ask `What is Mason?` through `kc_search`, receive the fact with exact generic provenance, then follow its ResourceVersion through `kc_get_source` and verify exact content/SHA-256;
- privacy restriction remains dominant across both `kc_search` and `kc_get_source` after application reconstruction;
- migrations, fast suite, PostgreSQL suite including focused Task 3 tests, pinned G22, RI-4 restart rehearsal, and SR-2 restart/replay rehearsal pass. The first workflow attempt reached RI-4 after all prior gates passed but its isolated temporary-host `alembic upgrade head` subprocess exited before the harness surfaced stderr; rerunning the identical job without code changes passed RI-4 and every remaining gate, so no compatibility patch was made.

Task 3 does **not** add Graphiti synchronization, Mason/MindsHub tools, new source connectors, generalized Authority, remote exposure, or a new database migration.

### Task 4 — separate Graphiti synchronization — NEXT AUTHORIZED SLICE

Generalize graph plan input/reference-time semantics only as required for generic governed SR-2 sources, then add an explicit bounded sync for eligible canonical/text material. Preserve the accepted projection ledger, immutable-build isolation, required validation checks, Authority-first trusted retrieval and exact canonical correlations. New knowledge may remain graph-pending without blocking storage.

**Accept when:** a bounded mixed-source batch projects successfully through independent validation; failed/interrupted graph work leaves canonical/text retrieval usable; only validated builds enter trusted graph retrieval; at least one graph result resolves to exact generic KC evidence.

**Stop:** no permanent scheduler, generalized queue/workflow platform, cross-generation graph reuse, or GPU/model orchestrator unless separately justified and qualified.

**Current authorization:** Task 4 only. Checkpoint before Task 5.

### Task 5 — Mason / MindsHub tools

Expose only `kc_store`, `kc_search`, `kc_get_source`, and `kc_status` to Mason through the governed front door. Keep Graphiti synchronization operator-controlled initially.

**Accept when:** a fresh Mason session can store/retrieve KC context and answer a stored project question without direct database, artifact-store, FalkorDB, or Graphiti mutation access.

### Task 6 — dogfood KC on KC

Ingest the authoritative KC context and selected active project knowledge and use normal retrieval during project work.

**Accept when:** KC provides enough context to resume bounded work without loading large historical handoffs. Improve demonstrated retrieval weaknesses only; if access control proves inadequate, separate Authority rather than extending ad-hoc permissions.

## Explicitly deferred from Usable V1

Do not expand the current phase into generalized Authority, multiple roles, direct remote KC exposure, Vera/ACL permission systems, continuous Graphiti processing, model/GPU scheduling infrastructure, broad automatic account/web ingestion, complex UI/workflow infrastructure, destructive autonomous maintenance, or arbitrary provider/database access.

The source-neutral contract can support future chat/email/file/benchmark sources, but Task 2 did not implement those connectors. Binary/PDF/MIME extraction, assistant-summary derivation, broad multi-project policy and cross-generation graph reuse remain future bounded work unless a concrete later acceptance dependency requires them.

## Documentation and graph context

Keep these three documents sufficient to start work without a running graph. Store detailed historical context/evidence under `legacy/` and retrieve it only for the bounded question at hand. Update these documents at every material checkpoint instead of adding another current-state/handoff file.

Moving a file into `legacy/` **does not change KC lifecycle or an existing graph**. A future governed import must explicitly classify historical documents, handle prior source identities/retirements deliberately, and publish the resulting retrieval generation. Neither filenames nor archive prose determine lifecycle. Do not silently edit pinned qualification manifests or relabel historical evidence to make it current.