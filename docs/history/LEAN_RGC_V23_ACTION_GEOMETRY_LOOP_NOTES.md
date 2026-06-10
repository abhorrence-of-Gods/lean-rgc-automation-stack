# Lean-RGC v23: Action Geometry integrated retrieval

v23 connects the v20 Action Geometry Registry to the qgen / iterate loop.

The main new path is:

```text
base audit responses
  -> qgen coker residual / normal
  -> action geometry registry E(a) = (r, Gamma, c, cost, uncertainty)
  -> action-geometry retrieval
  -> micro-audit retrieved actions
  -> coker / robust-coker acceptance
  -> next-round merge
```

All outputs remain chart-level witnesses.  An action geometry candidate is not a
canonical proof object.  Canonical promotion still requires parent obstruction
non-payment, a dual certificate, and least-repair evidence.

## Main pipeline flags

```bash
--action-geometry
--action-geometry-use-qgen-normals
--audit-action-geometry-candidates
--action-geometry-accept-coker
--action-geometry-robust-coker-accept
```

## Main iterate flags

```bash
--action-geometry
--action-geometry-use-qgen-normals
--audit-action-geometry-candidates
--action-geometry-accept-coker
--action-geometry-merge-actions
--action-geometry-merge-policy all|accepted-only|robust-only
```

## Principal artifacts

```text
action_geometry/action_geometry.jsonl
action_geometry/action_geometry_candidates_scored.jsonl
action_geometry/action_geometry_candidates.jsonl
action_geometry/action_geometry_response_normal.json
action_geometry/action_geometry_carrier_normal.json
action_geometry_audit/responses.jsonl
action_geometry_acceptance_report.json
action_geometry_accepted_actions.jsonl
action_geometry_robust_acceptance_report.json
action_geometry_robust_accepted_actions.jsonl
```

v23 is the first loop in which the search can retrieve from audited action
geometry rather than only from a human tactic template grammar.
