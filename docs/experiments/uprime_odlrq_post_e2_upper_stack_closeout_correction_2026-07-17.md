# U-prime / ODLRQ post-E2 upper-stack closeout CI correction

Date: 2026-07-17 (Asia/Tokyo)

Status: `MECHANICAL_CLOSEOUT_CI_CLASSIFICATION_RECORDED`

This document is a narrow, document-only correction recorded after the
immutable closeout's natural CI completed.  It changes no semantic source,
artifact byte, equation, fixture, schema, tier, threshold, endpoint, test,
runner, or accepted ref.  It is a direct child of the closeout commit, is
published only on
`codex/uprime-post-e2-upper-stack-closeout-correction`, and is never merged into
the accepted semantic line.

## 1. Immutable closeout identity

```text
closeout_commit_sha = ee7a1c01dba376881d20962de664f4908acc7b0d
closeout_parent_sha = f1df8dd5d92706d907091e6add463fb6c9ca7130
closeout_tree_sha   = ebc93e941df405b50f425f8c844de2597eaca1f4
accepted_i0_tree    = c15e50c683263b50c8ddf371938785d03353b1fc
```

The closeout commit contains exactly its one registered document and seven
artifact paths.  All seven artifact byte counts, SHA-256 values, strict public
verification results, source-commit binding, tiers, coverage values, and
dispositions remain exactly as recorded there.

The accepted semantic I0 candidate and accepted refs remain byte-identical at
`f1df8dd5d92706d907091e6add463fb6c9ca7130`.  Their distinct green CI runs were:

```text
candidate  29569429286 / 87849472845
accepted   29569953649 / 87851123891
result     2638 passed, 8 skipped, 161 deselected
```

## 2. Observed closeout CI

The immutable closeout's natural CI was:

```text
run/job  29571586666 / 87856392726
result   10 failed, 2628 passed, 8 skipped, 161 deselected
```

The previously registered prediction in section 6 of the closeout document
was one topology failure and `2637 passed`.  The observed run contained that
exact topology failure plus nine already classified nominal/runtime failures.
This document supersedes only that predicted count for this already observed
immutable sidecar.

## 3. Exact ten-failure decomposition

One failure is the registered closeout topology control:

```text
tests/test_uprime_u2_u4_development.py::
  test_u24_b0_anchor_contiguous_budget_and_terminal_topology
```

It reports the expected build-row overflow after adding the closeout terminal
paths.  The guard's immutable identity core predates those paths.  Correcting
that guard would require changing control source outside the closeout allowlist;
the governing authority deliberately records the red sidecar instead.

The other nine failures are these S0 tests:

```text
test_s0_authority_references_distinguish_live_and_digest_bindings_and_firewall_me0
test_s0_global_measure_rows_recompute_normalization_and_zero_mass_rules
test_s0_predictive_distance_separates_node_edge_cross_and_numeric_terms
test_s0_declared_lplus_enumerates_complete_primitive_universe_and_builds_exact_positive_majorant
test_s0_counted_coverage_and_target_residuals_abstain_without_four_of_four
test_s0_radius_morphism_is_typed_fine_to_coarse_column_stochastic
test_s0_granularity_morphism_derives_edge_map_and_composes_in_frozen_order
test_s0_finite_remainder_recomputes_all_six_composites_without_infinite_claim
test_s0_strict_wire_caps_type_substitution_and_mutation_fail_closed
```

Every one stops at the same shared assertion in
`tests/test_odlrq_similarity.py:496`.  The Linux runner re-solved the nominal
floating-point MaxEnt fixture and produced:

```text
observed Linux wire SHA-256
  97B5DDA5500D4194949E9D3AE10D2EF9D4139AA809BBBF373677F6295D90D749
frozen Windows-runtime wire SHA-256
  DCA363A6C8CC15ED13C4182DE7BFD2F68293E83C1766419B439C1AE8309C42E3
```

This is the exact root cause already observed and classified by activation
correction commit `6975c0a52cd64ff468614184adbdf6eafdc7e546` for runs
`29561412405 / 87824486788` and `29562169223 / 87826792439`.  The closeout
sidecar changed no Python source, so the reappearance is CI/runtime variation,
not an artifact-dependent semantic change.

## 4. Scientific disposition

No I0 test, artifact schema/order/cap check, strict predecessor verifier,
positive operator, exact-rational propagation, coverage witness, morphism,
finite-remainder check, or hard-channel firewall failed.  Before publication,
all seven emitted artifacts passed accepted-I0's public strict verifier; an
independent adversarial audit rechecked their bytes and content with zero
blocking findings.

The scientific disposition therefore remains unchanged:

```text
hard chain coverage  4/4 complete
hard bound/threshold 3/4 <= 3/4
hard disposition     PASS
nominal support      2/3 incomplete, non-hard
diagnostic total     17/20, non-hard
artifact disposition CPU_SYNTHETIC_U2_U4_ARTIFACTS_EMITTED
```

The ten-failure closeout badge is a known combination of one topology control
and nine nominal cross-LAPACK byte-identity checks.  It is not a theoretical
refutation and not evidence that any published artifact failed verification.
No rerun, artifact replacement, accepted-line rewrite, threshold change, or
tier promotion is requested or permitted.

This correction itself is bookkeeping for an already observed public CI result.
Its natural CI may reproduce the same ten failures; such reproduction is not a
new scientific endpoint.  Any different failure must be diagnosed as an
engineering/governance defect under the existing anti-fractal rule.
