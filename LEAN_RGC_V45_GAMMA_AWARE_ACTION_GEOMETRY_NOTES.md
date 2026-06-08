# Lean-RGC v45: Gamma-aware Action Geometry Retrieval

v45 connects the v44 learned finite-chart propagation model `Gamma(a)` to Action Geometry retrieval.

The retrieval score can now use a tail-native value chart

```text
Q_{Gamma,H}(r) = sum_{k=0}^H discount^k Gamma(a)^k r
```

instead of only the local response vector `r(a)`.  It also penalizes learned propagation instability using either spectral radius or coker-normal amplification proxies.

## New / extended flags

Standalone:

```bash
lean-rgc action-geometry-retrieve \
  --registry action_geometry.jsonl \
  --response-normal '{"goal.eq": 1.0}' \
  --gamma-aware \
  --gamma-value-mode finite_horizon \
  --gamma-horizon 4 \
  --gamma-value-weight 1.0 \
  --gamma-tail-risk-mode spectral \
  --out action_geometry_candidates_scored.jsonl
```

Pipeline / iterate:

```bash
--action-geometry-use-gamma-transition
--action-geometry-gamma-value-mode local|finite_horizon|stationary|resolvent
--action-geometry-gamma-horizon 4
--action-geometry-gamma-discount 1.0
--action-geometry-gamma-tail-value-weight 1.0
--action-geometry-gamma-stability-margin 0.05
--action-geometry-gamma-tail-risk-mode spectral|normal_amplification|none
```

If `--action-geometry-use-gamma-transition` is enabled, the pipeline learns a gamma transition model from the current audit transitions before Action Geometry scoring, patches the registry for retrieval, and records the patch report in `action_geometry/action_geometry_gamma_patch_for_retrieval_report.json`.

## Status

This is a finite audit chart / witness.  It is not a canonical propagation operator.

The score now distinguishes:

- `local_response_score`: direct one-step response.
- `gamma_tail_response_score`: finite-horizon or resolvent tail value.
- `gamma_tail_value_gain`: difference between tail value and local response.
- `tail_risk`: instability penalty from learned Gamma.

## Theory mapping

Before v45:

```text
S(a) = phi^R(r(a)) + phi^C(c(a)) - TailRisk(proxy) - Cost - Audit
```

v45:

```text
S(a) = phi^R(Q_Gamma,H(r(a))) + phi^C(c(a)) - TailRisk(Gamma(a)) - Cost - Audit
```

where `Q_Gamma,H` is a finite-chart tail-native response value.
