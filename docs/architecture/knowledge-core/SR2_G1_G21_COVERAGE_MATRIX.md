# Knowledge Core SR-2 Slice 7 — Active G1–G21 Qualification Coverage Matrix

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Slice:** SR-2 Slice 7 qualification closure  
**Controlling contract:** `SECTION_RETRIEVAL_SR1.md`, gates SR2-G1 through SR2-G21  
**Architecture decision:** `DECISIONS.md` / KC-D025  
**Starting documentation checkpoint:** `3bd753a895bdd7b72bd9cb8e02ef82ed583aacd7`  
**Qualified runtime/test/workflow checkpoint:** `7570425231c0f1804c800ad4c6809f6261d82416`  
**Qualification run:** GitHub Actions `34457756458` — success  
**Status:** **G1–G21 independently qualified and checkpointed**  
**G22 status:** **independently qualified afterward at `c75a6be2e832bdc29fda0e4a6eab7de28da90668` — Actions `34462565404` success**

## Qualification result

The published Slice 7 closure commit passed without any production-code repair or architecture change:

- migrations through `0012_sr2_segments`: passed;
- fast suite, selected by `not postgresql and not sr2_real_pilot`: **75 passed**, 1 guarded older RF-2 exact-corpus skip, 38 deselected;
- PostgreSQL suite, selected by `postgresql and not sr2_real_pilot`: **36 passed**, 2 guarded older RF-2 exact-corpus skips, 76 deselected;
- RI-4 restart/replay rehearsal: passed, including application reconstruction, artifact integrity, current/historical retrieval, exact replay, PostgreSQL restart, and provenance verification.

The guarded `test_real_corpus_pilot.py` skips are the older RF-2 immutable pilot refusing to relabel changed documentation as historical source evidence. They are not SR2-G22 and are not accepted as G22 execution.

## Purpose

This matrix is the active, reviewable map from every amended SR-2 synthetic qualification gate G1–G21 to concrete committed tests. It replaces conversation-only audit notes as the closure control surface.

It does not redefine any gate. `SECTION_RETRIEVAL_SR1.md` remains authoritative. Existing accepted Slice 1–6 tests are reused where they already prove a gate; Slice 7 adds only cross-boundary or missing qualification evidence identified by the completed audit.

G22 is intentionally documented separately in `SR2_G22_QUALIFICATION.md`; this matrix preserves the independent G1–G21 prerequisite evidence rather than folding the later real-document pilot backward into the synthetic closure.

## Qualification boundary

The G1–G21 qualification suites are:

```text
python -m pytest -q -m "not postgresql and not sr2_real_pilot"
python -m pytest -q -m "postgresql and not sr2_real_pilot"
```

`sr2_real_pilot` is reserved for SR2-G22 and remains excluded from both G1–G21 commands. G22 is executed separately with:

```text
python -m pytest -q -m "sr2_real_pilot"
```

The pre-existing `tests/test_real_corpus_pilot.py` is an older RF-2-era immutable pilot fixture. It is not relabeled as SR2-G22 and is not accepted as SR2-G22 evidence.

## Coverage matrix

| Gate | Primary committed qualification evidence | What is mechanically proved |
|---|---|---|
| **G1** canonical evidence / governed observation separation | `test_sr2_acceptance_closure.py::test_sr2_g1_g7_complete_rebuild_is_reproducible_without_source_mutation`; `test_sr2_segment_generation.py::test_sr2_slice5_builds_validated_nonserving_candidate_and_preserves_rf2` | Rebuilding segment candidates leaves canonical `Resource`/`ResourceVersion`, artifact bytes, and governed observations unchanged while derived generation/profile/source lineage is created separately. |
| **G2** exact deterministic partition | `test_sr2_structural_segmentation.py::test_sr2_g2_g3_g4_exact_partition_headings_fences_and_control_discussion` | Ordered contiguous ranges reconstruct exact bytes; slice SHA-256 values and ordinals match. |
| **G3** heading/preamble structure | `test_sr2_structural_segmentation.py::test_sr2_g2_g3_g4_exact_partition_headings_fences_and_control_discussion` | Preamble, ATX hierarchy, skipped levels, lines, and Setext negative behavior are deterministic. |
| **G4** fences/lists/tables/control discussion | `test_sr2_structural_segmentation.py::test_sr2_g2_g3_g4_exact_partition_headings_fences_and_control_discussion`; `test_sr2_lifecycle_projection.py::test_sr2_g11_exact_controls_and_ordinary_mentions_are_distinguished` | Fenced pseudo-controls/headings and ordinary prose/inline/block-quote control discussion remain content; non-structural Markdown stays non-structural. |
| **G5** deterministic continuation / suffix | `test_sr2_structural_segmentation.py::test_sr2_g5_large_continuation_has_predeclared_boundaries_and_final_suffix` | Fixed soft/hard splitting, stable repeated boundaries, preserved heading context, and whole final suffix termination. |
| **G6** oversized indivisible fail-closed | `test_sr2_structural_segmentation.py::test_sr2_g6_oversized_indivisible_line_and_fence_fail_closed`; `test_sr2_acceptance_closure.py::test_sr2_g6_oversized_structural_failure_keeps_rf2_current_and_serving` | Oversized line/fence cannot split illegally; end-to-end build failure leaves prior RF-2 current and serving. |
| **G7** structural vs complete-generation reproducibility | `test_sr2_structural_segmentation.py::test_sr2_g7_g8_structural_identity_is_content_profile_and_parent_bound`; `test_sr2_lifecycle_projection.py::test_sr2_g7_g12_parent_downgrade_reprojects_same_structural_keys`; `test_sr2_projection_lineage.py::test_sr2_g7_g9_projection_snapshot_digest_binds_exact_governed_inputs`; `test_sr2_acceptance_closure.py::test_sr2_g1_g7_complete_rebuild_is_reproducible_without_source_mutation` | Structural identity is stable for exact version/profile independent of lifecycle; complete persisted derived payload is identical only under the same governed snapshot/profile inputs. |
| **G8** edit/rename/duplicate/A→B→A identity | `test_sr2_structural_segmentation.py::test_sr2_g7_g8_structural_identity_is_content_profile_and_parent_bound`; `test_sr2_acceptance_closure.py::test_sr2_g8_identical_slices_at_distinct_coordinates_keep_distinct_keys`; `test_sr2_governed_source_selection.py::test_sr2_slice4_a_b_a_reuses_canonical_and_structural_identity_with_new_lineage`; `test_sr2_acceptance_closure.py::test_sr2_g8_path_only_reobservation_reuses_version_and_structural_keys` | Changed bytes/new parents change key space; identical slices at distinct coordinates stay distinct; A→B→A reuses A identity with new observation lineage; path-only re-observation reuses exact version and structural keys. |
| **G9** exact parent + governed projection provenance | `test_sr2_projection_lineage.py::test_sr2_g9_projection_lineage_migration_has_exact_foreign_keys`; `test_sr2_serving_cutover.py::test_sr2_slice6_rf2_to_sr2_cutover_has_no_gap_no_mix_and_public_provenance`; `test_sr2_acceptance_closure.py::test_sr2_g1_g7_complete_rebuild_is_reproducible_without_source_mutation` | Persisted lineage binds generation+version to exact observation/governing manifest/projection snapshot; public segment hits expose exact parent/segment governed provenance. |
| **G10** inherited metadata / no authority escalation | `test_sr2_segment_generation.py::test_sr2_slice5_builds_validated_nonserving_candidate_and_preserves_rf2`; `test_sr2_lifecycle_projection.py::test_heading_named_historical_does_not_infer_lifecycle`; `test_sr2_acceptance_closure.py::test_sr2_g16_reachable_ranking_discriminators_and_repeat_order_are_stable` | Authority/source metadata comes from governed parent observation, headings cannot infer lifecycle, and authority participates only as inherited ranking metadata. |
| **G11** lifecycle grammar / no heuristics | `test_sr2_lifecycle_projection.py::test_sr2_g11_exact_controls_and_ordinary_mentions_are_distinguished`; `test_sr2_lifecycle_projection.py::test_sr2_g11_control_looking_malformed_misplaced_and_duplicate_fail`; `test_sr2_lifecycle_projection.py::test_heading_named_historical_does_not_infer_lifecycle`; `test_sr2_lifecycle_projection.py::test_plain_text_control_like_content_has_no_directive_semantics` | Exact eligible controls are recognized; malformed/misplaced/duplicate standalone attempts fail; ordinary mentions/fences/plain text/headings do not gain control semantics. |
| **G12** declarations cannot promote | `test_sr2_lifecycle_projection.py::test_sr2_g12_ancestor_superseded_child_current_preserves_declaration`; `test_sr2_lifecycle_projection.py::test_sr2_g12_less_restrictive_child_cannot_promote_document`; `test_sr2_acceptance_closure.py::test_sr2_g12_restrictive_cases_publish_and_parent_downgrade_reuses_keys` | Unknown+child-current, superseded+child-current, ancestor-superseded+descendant-current all publish with declaration preserved/effective restriction; current→superseded same bytes republishes with stable keys. |
| **G13** mixed current/historical retrieval | `test_sr2_serving_cutover.py::test_sr2_slice6_rf2_to_sr2_cutover_has_no_gap_no_mix_and_public_provenance`; `test_sr2_serving_cutover.py::test_sr2_slice6_section_import_atomically_settles_receipt_and_promotes_generation`; `test_sr2_acceptance_closure.py::test_sr2_g13_g17_g18_retirement_is_historical_and_privacy_fence_precedes_limit` | Unknown/current remain normally eligible, superseded excluded by default, and explicit historical mode recovers retained exact segment provenance. |
| **G14** current-generation isolation | `test_sr2_serving_cutover.py::test_sr2_slice6_section_import_atomically_settles_receipt_and_promotes_generation`; `test_sr2_serving_cutover.py::test_sr2_slice6_failed_and_late_candidates_cannot_replace_current`; `test_sr2_acceptance_closure.py::test_sr2_g21_structural_and_projection_profile_cutovers_are_distinct_and_nonmutating` | Exactly one text generation serves; failed/late candidates cannot replace it; successive valid profile publications supersede rather than mix. |
| **G15** RF-2 cutover no gap | `test_sr2_serving_cutover.py::test_sr2_slice6_rf2_to_sr2_cutover_has_no_gap_no_mix_and_public_provenance`; `test_sr2_acceptance_closure.py::test_sr2_g6_oversized_structural_failure_keeps_rf2_current_and_serving` | Whole-document RF-2 remains serving while candidate builds/fails; successful publication atomically switches to segment mode. |
| **G16** deterministic ranking | `test_sr2_acceptance_closure.py::test_sr2_g16_reachable_ranking_discriminators_and_repeat_order_are_stable`; `test_sr2_acceptance_closure.py::test_sr2_g16_profile_declares_exact_deterministic_total_order` | Reachable lexical/lifecycle/authority/canonical-revision/segment-ordinal discriminators order deterministically and repeated queries return identical identities; configuration locks the full total order through version-ref and final segment-key safeguards without fabricating impossible duplicate canonical segment identities. |
| **G17** parent fence / derivative reconciliation | `test_sr2_serving_cutover.py::test_sr2_slice6_privacy_reconciliation_deletes_segments_and_serving_fence_blocks_stale_reinsert`; `test_sr2_acceptance_closure.py::test_sr2_g13_g17_g18_retirement_is_historical_and_privacy_fence_precedes_limit`; `test_task6_deletion.py::test_identical_fence_retry_replays_one_case` | Privacy fence immediately suppresses children even after stale reinsertion; cleanup is replayable/idempotent; retirement-retain remains historical evidence rather than privacy purge. Physical `ResourceVersion` purge is not an implemented V1 operation, so the gate's conditional post-purge clause has no applicable fixture. |
| **G18** bounded query/service contract | `test_sr2_acceptance_closure.py::test_sr2_g18_g19_g20_public_contract_is_bounded_and_has_no_model_dependency`; `test_sr2_acceptance_closure.py::test_sr2_g13_g17_g18_retirement_is_historical_and_privacy_fence_precedes_limit`; `test_sr2_acceptance_closure.py::test_sr2_g16_reachable_ranking_discriminators_and_repeat_order_are_stable`; `test_task11_gate19_service_only.py::test_gate19_client_has_no_database_or_storage_contract` | Blank/out-of-range requests reject; stop-word-only query returns bounded empty results; response limit is applied after serving eligibility; ordinary client remains HTTP/service-only. |
| **G19** no internal leakage / no copied body | `test_sr2_segment_generation.py::test_sr2_slice5_segment_table_has_lineage_fk_and_no_body_copy`; `test_sr2_serving_cutover.py::test_sr2_slice6_rf2_to_sr2_cutover_has_no_gap_no_mix_and_public_provenance`; `test_task11_gate19_service_only.py::test_gate19_client_has_no_database_or_storage_contract`; `test_sr2_acceptance_closure.py::test_sr2_g18_g19_g20_public_contract_is_bounded_and_has_no_model_dependency` | Segment derived table has no copied canonical body; response/OpenAPI/public schema omit DB/artifact/internal credential fields. |
| **G20** no model dependency | `test_sr2_acceptance_closure.py::test_sr2_g18_g19_g20_public_contract_is_bounded_and_has_no_model_dependency`; deterministic tests in `test_sr2_structural_segmentation.py` and `test_sr2_lifecycle_projection.py` | Package/runtime source contains no LLM/tokenizer/vector-service dependency imports or API-key coupling; segmentation/lifecycle remain deterministic Python and lexical retrieval PostgreSQL-native. |
| **G21** profile/config rebuild isolation | `test_sr2_structural_segmentation.py::test_sr2_g21_structural_profile_change_changes_digest_and_key_space`; `test_sr2_segment_generation.py::test_sr2_slice5_generation_config_binds_structural_and_projection_profiles`; `test_sr2_acceptance_closure.py::test_sr2_g21_structural_and_projection_profile_cutovers_are_distinct_and_nonmutating` | Structural-profile change changes structural digest/key space; projection-only change preserves structural keys while changing projection/config lineage; successive publications do not mutate canonical evidence or mix generations. |

## G16 reachability note

The accepted audit explicitly rejected manufacturing invalid duplicate canonical segment identities merely to force the final `segment_key` tiebreaker. For one valid parent generation, `(resource_version_ref, segment_ordinal)` already identifies a unique segment row. Slice 7 therefore:

1. behaviorally exercises ranking discriminators that are reachable through valid canonical/import state;
2. repeats queries to prove stable ordered identities; and
3. asserts the complete governed profile order, including `resource_version_ref`, `segment_ordinal`, and final `segment_key`, so those deterministic safeguards cannot silently disappear.

That is qualification of the contract without weakening canonical identity constraints for a synthetic test.

## G22 closure

The G1–G21 checkpoint prerequisite was satisfied before G22 execution. SR2-G22 was then independently qualified under `@pytest.mark.sr2_real_pilot` at runtime/test/workflow checkpoint `c75a6be2e832bdc29fda0e4a6eab7de28da90668`, Actions `34462565404` — success.

The pilot uses `SR2_G22_REAL_DOCUMENT_PILOT_MANIFEST.json`, pins exactly three real documents to source commit `bb42835442c03478da2b61c3f79b1c41c26e4e92`, and imports no unlisted repository content. It proves exact governed lineage, structural reconstruction from exact Git bytes, harmless literal lifecycle-token discussion, no temporal-prose lifecycle inference, parent-superseded historical behavior, exact source provenance, and repeat-stable retrieval identities.

The separate G22 selector passed **1 test with 114 deselected**. The G1–G21 selectors remained separately green in the same run: fast **75 passed**, PostgreSQL **36 passed**. The durable evidence is `SR2_G22_QUALIFICATION.md`.

No G22 evidence was backfilled from orphaned blobs, the older RF-2 real-corpus fixture, unpinned working-tree documents, or the earlier G1–G21 qualification run.

## Intended-host boundary

The G22 prerequisite is now satisfied. **User-PC testing is required for the next qualification**, but the existing RI-4 Windows evidence must not be relabeled as SR-2 proof: RI-4 qualified its bounded RF-2 whole-document serving path.

The next bounded work must construct or identify an intended-host qualification entrypoint that actually exercises the accepted SR-2 segment-serving path, then execute that entrypoint on the intended Windows/PostgreSQL host and record durable host evidence.
