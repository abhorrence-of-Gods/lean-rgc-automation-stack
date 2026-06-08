# Lean-RGC v25: Quotient Coordinate Generation

v25 adds the first implementation of **quotient-coordinate generation**.

Earlier qgen generated candidate chart labels such as `qgen_residual_goal_eq` and then routed those labels to candidate tactics.  v25 instead mines finite coker normals and turns them into linear quotient-coordinate candidates:

\[
q_\phi(d)=\langle \phi,d\rangle.
\]

These coordinates are not canonical observables.  They are finite response-chart candidates.  Canonical promotion still requires parent non-payment, a dual certificate, and least repair.

## New command

```bash
lean-rgc quotient-coordinates \
  --responses runs/round_00/audit/responses.jsonl \
  --out runs/round_00/quotient_coordinates
```

Outputs:

```text
quotient_coordinate_report.json
state_coker_normals.jsonl
quotient_coordinates.jsonl
quotient_coordinate_action_scores.jsonl
quotient_coordinate_selected_actions.jsonl
```

## Meaning

For each state, v25 computes a finite coker residual

\[
\zeta_s = D_s - \operatorname{Proj}_{K_s}D_s
\]

and its normal \(\phi_s\).  Coker normals are then clustered by cosine similarity.  Each cluster yields a coordinate candidate

\[
q_\lambda(d)=\langle \phi_\lambda,d\rangle.
\]

This is the first step from

```text
residual -> defect label -> tactic candidate
```

toward

```text
residual -> coker normal -> quotient coordinate -> action retrieval
```

## Status

All v25 outputs have witness/chart status:

```text
quotient_coordinate_candidate_not_canonical_parent_nonpaid_least_repair_required
```

They should be audited and promoted only via POMS.
